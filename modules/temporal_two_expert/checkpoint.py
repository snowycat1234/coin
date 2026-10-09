"""Atomic generations, safe loads, exact resume identities, and local run locks."""

from __future__ import annotations

import fcntl
import json
import os
import random
import tempfile
import uuid
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import torch

from .exact import PROTOTYPE_SHA256, RECOVERY_SHA256, sha
from .inputs import array_digest, digest

OPTIMIZER = dict(
    name="Adam",
    lr=0.001,
    betas=[0.9, 0.999],
    eps=1e-8,
    weight_decay=0.0,
    gradient_norm_clip=1.0,
    foreach=False,
)


def source_identity():
    root = Path(__file__).resolve().parents[2]
    paths = sorted(Path(__file__).parent.glob("*.py")) + [
        root / "modules/collector_research/pipeline/make_labels.py",
        root / "modules/collector_research/pipeline/train.py",
    ]
    return {str(p.relative_to(root)): sha(p) for p in paths}


def make_optimizer(model):
    return torch.optim.Adam(
        model.parameters(),
        lr=OPTIMIZER["lr"],
        betas=tuple(OPTIMIZER["betas"]),
        eps=OPTIMIZER["eps"],
        weight_decay=0.0,
        foreach=False,
    )


def model_identity(model):
    return digest(
        dict(
            contract=model.contract,
            arrays={
                k: array_digest(v.detach().cpu().numpy()) for k, v in model.state_dict().items()
            },
        )
    )


def run_binding(
    model,
    *,
    data_split_identity,
    feature_batch_size,
    max_steps,
    checkpoint_every=1,
    max_seconds=120.0,
):
    # Everything that changes gradient/RNG consumption or stopping is bound.
    if (
        type(feature_batch_size) is not int
        or feature_batch_size < 1
        or type(max_steps) is not int
        or max_steps < 1
        or type(checkpoint_every) is not int
        or not 1 <= checkpoint_every <= max_steps
        or not 0 < max_seconds <= 120
    ):
        raise ValueError("Explicit finite step/time/checkpoint budget required")
    record = dict(
        schema="TEMPORAL_TWO_EXPERT_RUN_V1",
        model_contract=model.contract,
        initial_model_identity=model_identity(model),
        data_split_identity=data_split_identity,
        feature_batch_size=feature_batch_size,
        max_steps=max_steps,
        checkpoint_every=checkpoint_every,
        max_seconds=float(max_seconds),
        optimizer=OPTIMIZER,
        sources=source_identity(),
        prototype_SHA256=PROTOTYPE_SHA256,
        recovery_SHA256=RECOVERY_SHA256,
        torch_version=str(torch.__version__),
        numpy_version=str(np.__version__),
        torch_threads=torch.get_num_threads(),
        deterministic_algorithms=torch.are_deterministic_algorithms_enabled(),
        cpu_only=True,
        checkpoint_selection="last_completed_training_step_only",
    )
    return dict(run_id=digest(record), specification=record)


def _sync_directory(directory):
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json(path, record):
    fd, temporary = tempfile.mkstemp(prefix=".pointer-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(record, stream, sort_keys=True, indent=2, allow_nan=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _sync_directory(path.parent)
    finally:
        Path(temporary).unlink(missing_ok=True)


@contextmanager
def run_guard(directory, binding):
    """Reject another live local process or reuse with a different run identity."""
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "run.lock").open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("A duplicate local run already holds this directory") from error
        try:
            manifest = directory / "RUN.json"
            if manifest.exists():
                if json.loads(manifest.read_text()) != binding:
                    raise ValueError("Immutable run/input/config/split identity differs")
            else:
                _atomic_json(manifest, binding)
            yield directory
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def _rng_state():
    numpy_rng = np.random.get_state()
    return dict(
        torch=torch.get_rng_state(),
        python=random.getstate(),
        numpy=dict(
            kind=numpy_rng[0],
            keys=torch.tensor(numpy_rng[1].astype(np.int64)),
            position=numpy_rng[2],
            has_gauss=numpy_rng[3],
            cached_gauss=numpy_rng[4],
        ),
    )


def _restore_rng(rng):
    torch.set_rng_state(rng["torch"])
    random.setstate(rng["python"])
    n = rng["numpy"]
    np.random.set_state(
        (
            n["kind"],
            n["keys"].numpy().astype(np.uint32),
            n["position"],
            n["has_gauss"],
            n["cached_gauss"],
        )
    )


def _verify_optimizer(model, optimizer):
    if type(optimizer) is not torch.optim.Adam or len(optimizer.param_groups) != 1:
        raise ValueError("One matched Adam optimizer group required")
    group = optimizer.param_groups[0]
    if (
        list(map(id, group["params"])) != list(map(id, model.parameters()))
        or group["lr"] != OPTIMIZER["lr"]
        or list(group["betas"]) != OPTIMIZER["betas"]
        or group["eps"] != OPTIMIZER["eps"]
        or group["weight_decay"] != 0.0
        or group["foreach"] is not False
        or group["amsgrad"]
        or group["maximize"]
    ):
        raise ValueError("Optimizer parameters/configuration differ from bound contract")


def _verify_moments(model, optimizer, step):
    if step == 0:
        if optimizer.state:
            raise ValueError("Step-zero checkpoint must have an unused optimizer")
        return
    for parameter in model.parameters():
        state = optimizer.state.get(parameter, {})
        if (
            set(state) != {"step", "exp_avg", "exp_avg_sq"}
            or float(state["step"]) != step
            or any(not torch.isfinite(v).all() for v in state.values())
            or state["exp_avg"].shape != parameter.shape
            or state["exp_avg_sq"].shape != parameter.shape
            or torch.any(state["exp_avg_sq"] < 0)
        ):
            raise ValueError("Complete finite Adam moments and matching completed step required")


def save_checkpoint(directory, model, optimizer, binding, *, step, elapsed_seconds=0.0):
    """Call inside run_guard after a complete update and zero_grad(set_to_none=True).

    A new immutable generation is fsynced before latest.json changes. A crash
    before pointer replacement leaves the last valid generation resumable.
    """
    directory = Path(directory)
    _verify_optimizer(model, optimizer)
    if (
        json.loads((directory / "RUN.json").read_text()) != binding
        or binding["specification"]["sources"] != source_identity()
        or binding["specification"]["model_contract"] != model.contract
        or model.mean.device.type != "cpu"
        or type(step) is not int
        or not 0 <= step <= binding["specification"]["max_steps"]
        or not np.isfinite(elapsed_seconds)
        or elapsed_seconds < 0
        or any(p.grad is not None for p in model.parameters())
    ):
        raise ValueError("Bound completed CPU update with no pending gradients required")
    _verify_moments(model, optimizer, step)
    pointer_path = directory / "latest.json"
    if pointer_path.exists() and step < json.loads(pointer_path.read_text())["step"]:
        raise ValueError("Checkpoint progress cannot move backwards")
    snapshot = dict(
        schema="TEMPORAL_TWO_EXPERT_CHECKPOINT_V1",
        binding=binding,
        step=step,
        elapsed_seconds=float(elapsed_seconds),
        model=model.state_dict(),
        model_identity=model_identity(model),
        optimizer=optimizer.state_dict(),
        rng=_rng_state(),
        training=model.training,
    )
    final = directory / f"step-{step:08d}-{uuid.uuid4().hex}.pt"
    fd, temporary = tempfile.mkstemp(prefix=".checkpoint-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            torch.save(snapshot, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, final)
        _sync_directory(directory)
        pointer = dict(
            schema=snapshot["schema"],
            file=final.name,
            SHA256=sha(final),
            step=step,
            run_id=binding["run_id"],
            model_identity=snapshot["model_identity"],
        )
        _atomic_json(pointer_path, pointer)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return pointer


def load_checkpoint(directory, model, optimizer, binding):
    """Verify exact bytes before safe weights-only deserialization; restore all RNG."""
    directory = Path(directory)
    _verify_optimizer(model, optimizer)
    pointer = json.loads((directory / "latest.json").read_text())
    name = pointer["file"]
    if (
        Path(name).name != name
        or pointer["run_id"] != binding["run_id"]
        or json.loads((directory / "RUN.json").read_text()) != binding
        or binding["specification"]["sources"] != source_identity()
        or binding["specification"]["model_contract"] != model.contract
        or sha(directory / name) != pointer["SHA256"]
    ):
        raise ValueError(
            "Exact checkpoint bytes and immutable run/source/input/split binding required"
        )
    state = torch.load(directory / name, map_location="cpu", weights_only=True)
    if (
        state["schema"] != "TEMPORAL_TWO_EXPERT_CHECKPOINT_V1"
        or state["binding"] != binding
        or state["step"] != pointer["step"]
        or not 0 <= state["step"] <= binding["specification"]["max_steps"]
        or state["model_identity"] != pointer["model_identity"]
    ):
        raise ValueError("Exact checkpoint step/model identity required")
    model.load_state_dict(state["model"], strict=True)
    if (
        any(not torch.isfinite(v).all() for v in model.state_dict().values())
        or model_identity(model) != state["model_identity"]
    ):
        raise ValueError("Finite exact model snapshot required")
    optimizer.load_state_dict(state["optimizer"])
    _verify_optimizer(model, optimizer)
    _verify_moments(model, optimizer, state["step"])
    model.train(state["training"])
    optimizer.zero_grad(set_to_none=True)
    _restore_rng(state["rng"])
    return dict(
        step=state["step"],
        elapsed_seconds=state["elapsed_seconds"],
        model_identity=state["model_identity"],
        checkpoint_SHA256=pointer["SHA256"],
    )
