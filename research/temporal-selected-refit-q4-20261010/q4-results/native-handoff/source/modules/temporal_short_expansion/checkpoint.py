"""Atomic warm checkpoints with explicitly bound per-parameter Adam birth steps."""

from __future__ import annotations

import json
import os
import random
import re
import tempfile
import uuid
from pathlib import Path

import numpy as np
import torch

from modules.temporal_two_expert.checkpoint import (
    OPTIMIZER,
    _atomic_json,
    _restore_rng,
    _rng_state,
    _sync_directory,
    _verify_optimizer,
    model_identity,
    run_guard,
    source_identity,
)
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import array_digest, digest

SCHEMA = "TEMPORAL_SHORT_EXPANSION_CHECKPOINT_V1"
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_GENERATION = re.compile(r"step-([0-9]{8,})-[0-9a-f]{32}\.pt\Z")


def _births(model, binding):
    specification = binding["specification"]
    algorithm = specification["algorithm"]
    parent_step = algorithm["parent"]["step"]
    births = algorithm["parameter_birth_steps"]
    named = dict(model.named_parameters())
    if (
        type(parent_step) is not int
        or parent_step < 0
        or type(specification["max_steps"]) is not int
        or specification["max_steps"] < parent_step
        or not isinstance(births, dict)
        or set(births) != set(named)
    ):
        raise ValueError("Every parameter and the warm parent step must be explicitly bound")
    for name, birth in births.items():
        expected = 0 if name.startswith("base.") else parent_step
        if not name.startswith(("base.", "r_head.")) or type(birth) is not int or birth != expected:
            raise ValueError("Base parameters keep age zero birth; new head starts at parent step")
    return births, parent_step


def _verify_sources(binding, sources):
    specification = binding["specification"]
    root = Path(__file__).resolve().parents[2]
    bound = specification["algorithm"]["versioned_sources"]
    if (
        not isinstance(bound, dict)
        or not bound
        or specification["sources"] != source_identity()
        or (sources is not None and (not callable(sources) or sources() != bound))
    ):
        raise ValueError("Exact original and versioned source identities required")
    for name, expected in bound.items():
        if (
            not isinstance(name, str)
            or Path(name).is_absolute()
            or ".." in Path(name).parts
            or not isinstance(expected, str)
            or _HEX.fullmatch(expected) is None
        ):
            raise ValueError("Explicit repository-relative source paths and SHA256 required")
        path = root / name
        if not path.is_file() or sha(path) != expected:
            raise ValueError("Exact original and versioned source identities required")
    # A later new module file also changes the executable source set. Tests are
    # intentionally outside this root glob and do not enter the fitting contract.
    paths = list(Path(__file__).parent.glob("*.py"))
    paths += list((root / "modules/temporal_surrogate_resume_v2").glob("*.py"))
    paths += list((root / "modules/temporal_risk_proxy_v2").glob("*.py"))
    current = {str(p.relative_to(root)) for p in paths}
    if not current.issubset(bound):
        raise ValueError("Every current short-expansion and frozen objective source must be bound")


def _verify_optimizer_contract(model, optimizer):
    _verify_optimizer(model, optimizer)
    group = optimizer.param_groups[0]
    if (
        set(group)
        != {
            "params",
            "lr",
            "betas",
            "eps",
            "weight_decay",
            "amsgrad",
            "foreach",
            "maximize",
            "capturable",
            "differentiable",
            "fused",
        }
        or group["capturable"] is not False
        or group["differentiable"] is not False
        or group["fused"] is not None
    ):
        raise ValueError("Exact full matched Adam configuration required")


def _verify_binding(model, optimizer, binding, sources, *, completed=False):
    _verify_optimizer_contract(model, optimizer)
    specification = binding["specification"]
    if (
        set(binding) != {"run_id", "specification"}
        or digest(specification) != binding["run_id"]
        or specification["model_contract"] != model.contract
        or specification["optimizer"] != OPTIMIZER
        or specification["torch_version"] != str(torch.__version__)
        or specification["numpy_version"] != str(np.__version__)
        or specification["torch_threads"] != torch.get_num_threads()
        or specification["deterministic_algorithms"] != torch.are_deterministic_algorithms_enabled()
        or specification["cpu_only"] is not True
        or any(v.device.type != "cpu" for v in model.state_dict().values())
        or (completed and any(p.grad is not None for p in model.parameters()))
    ):
        raise ValueError("Exact CPU model/run binding with no pending gradients required")
    _verify_sources(binding, sources)
    return _births(model, binding)


def _validate_adam_state(parameter, state, age):
    if age == 0:
        if state:
            raise ValueError("Newborn Adam parameters require empty optimizer state")
        return
    if not isinstance(state, dict) or set(state) != {"step", "exp_avg", "exp_avg_sq"}:
        raise ValueError("Complete finite Adam moments and exact per-parameter ages required")
    step = state["step"]
    if (
        not isinstance(step, torch.Tensor)
        or step.shape != torch.Size([])
        or step.device.type != "cpu"
        or step.dtype not in (torch.float32, torch.float64)
        or not torch.isfinite(step)
        or float(step) != age
    ):
        raise ValueError("Exact per-parameter Adam age required")
    for name in ("exp_avg", "exp_avg_sq"):
        value = state[name]
        if (
            not isinstance(value, torch.Tensor)
            or value.device.type != "cpu"
            or value.shape != parameter.shape
            or value.dtype != parameter.dtype
            or not torch.isfinite(value).all()
            or (name == "exp_avg_sq" and torch.any(value < 0))
        ):
            raise ValueError("Complete finite shape/dtype-matched Adam moments required")


def validate_moments(model, optimizer, step, parameter_birth_steps):
    """Old parameters age globally; newly added parameters age only after birth."""
    _verify_optimizer_contract(model, optimizer)
    named = dict(model.named_parameters())
    if (
        type(step) is not int
        or set(parameter_birth_steps) != set(named)
        or any(type(b) is not int or not 0 <= b <= step for b in parameter_birth_steps.values())
        or any(p not in set(named.values()) for p in optimizer.state)
    ):
        raise ValueError("Exact parameter births and completed global Adam step required")
    for name, parameter in named.items():
        _validate_adam_state(
            parameter, optimizer.state.get(parameter, {}), step - parameter_birth_steps[name]
        )


def _validate_saved_optimizer(model, optimizer, saved, step, births):
    expected = optimizer.state_dict()
    if (
        not isinstance(saved, dict)
        or set(saved) != {"state", "param_groups"}
        or not isinstance(saved["state"], dict)
        or saved["param_groups"] != expected["param_groups"]
    ):
        raise ValueError("Exact Adam parameter order and full optimizer configuration required")
    identifiers = expected["param_groups"][0]["params"]
    if (
        any(type(identifier) is not int for identifier in saved["state"])
        or any(type(identifier) is not int for identifier in saved["param_groups"][0]["params"])
        or not set(saved["state"]).issubset(identifiers)
    ):
        raise ValueError("Unexpected Adam parameter state")
    for identifier, (name, parameter) in zip(identifiers, model.named_parameters(), strict=True):
        _validate_adam_state(parameter, saved["state"].get(identifier, {}), step - births[name])


def _progress(step, elapsed, binding, parent_step):
    if (
        type(step) is not int
        or not parent_step <= step <= binding["specification"]["max_steps"]
        or type(elapsed) not in (int, float)
        or not np.isfinite(elapsed)
        or elapsed < 0
    ):
        raise ValueError("Finite elapsed time and bound completed global step required")


def _read_pointer(directory, binding, parent_step):
    pointer = json.loads((directory / "latest.json").read_text())
    if set(pointer) != {
        "schema",
        "file",
        "SHA256",
        "step",
        "run_id",
        "model_identity",
        "elapsed_seconds",
    }:
        raise ValueError("Exact checkpoint pointer fields required")
    name = pointer["file"]
    match = _GENERATION.fullmatch(name) if isinstance(name, str) else None
    if (
        pointer["schema"] != SCHEMA
        or match is None
        or int(match[1]) != pointer["step"]
        or pointer["run_id"] != binding["run_id"]
        or not isinstance(pointer["SHA256"], str)
        or _HEX.fullmatch(pointer["SHA256"]) is None
        or not isinstance(pointer["model_identity"], str)
        or _HEX.fullmatch(pointer["model_identity"]) is None
    ):
        raise ValueError("Exact checkpoint pointer step/run/model identity required")
    _progress(pointer["step"], pointer["elapsed_seconds"], binding, parent_step)
    if sha(directory / name) != pointer["SHA256"]:
        raise ValueError("Exact checkpoint bytes required before safe deserialization")
    return pointer


def _validate_model_state(model, values, identity):
    expected = model.state_dict()
    if not isinstance(values, dict) or set(values) != set(expected):
        raise ValueError("Exact model snapshot keys required")
    for name, reference in expected.items():
        value = values[name]
        if (
            not isinstance(value, torch.Tensor)
            or value.device.type != "cpu"
            or value.shape != reference.shape
            or value.dtype != reference.dtype
            or not torch.isfinite(value).all()
        ):
            raise ValueError("Finite shape/dtype-matched exact model snapshot required")
    actual = digest(
        dict(
            contract=model.contract,
            arrays={k: array_digest(v.detach().numpy()) for k, v in values.items()},
        )
    )
    if actual != identity:
        raise ValueError("Exact model snapshot identity required")


def _validate_rng(rng):
    if not isinstance(rng, dict) or set(rng) != {"torch", "python", "numpy"}:
        raise ValueError("Complete saved RNG state required")
    n = rng["numpy"]
    if (
        not isinstance(n, dict)
        or set(n) != {"kind", "keys", "position", "has_gauss", "cached_gauss"}
        or n["kind"] != "MT19937"
        or not isinstance(n["keys"], torch.Tensor)
        or n["keys"].device.type != "cpu"
        or n["keys"].dtype != torch.int64
        or n["keys"].shape != (624,)
        or torch.any(n["keys"] < 0)
        or torch.any(n["keys"] > 2**32 - 1)
        or type(n["position"]) is not int
        or not 0 <= n["position"] <= 624
        or type(n["has_gauss"]) is not int
        or n["has_gauss"] not in (0, 1)
        or not np.isfinite(n["cached_gauss"])
    ):
        raise ValueError("Exact NumPy RNG state required")
    try:
        torch.Generator(device="cpu").set_state(rng["torch"])
        random.Random().setstate(rng["python"])
        np.random.RandomState().set_state(
            (
                n["kind"],
                n["keys"].numpy().astype(np.uint32),
                n["position"],
                n["has_gauss"],
                n["cached_gauss"],
            )
        )
    except (TypeError, ValueError, RuntimeError) as error:
        raise ValueError("Exact saved RNG state required") from error


def save_checkpoint(
    directory,
    model,
    optimizer,
    binding,
    *,
    step,
    elapsed_seconds=0.0,
    trainer_state=None,
    sources=None,
):
    """Save only a complete update; fsync its immutable generation before pointer swap."""
    directory = Path(directory)
    births, parent_step = _verify_binding(model, optimizer, binding, sources, completed=True)
    if json.loads((directory / "RUN.json").read_text()) != binding:
        raise ValueError("Immutable run/input/config/split identity differs")
    _progress(step, elapsed_seconds, binding, parent_step)
    validate_moments(model, optimizer, step, births)
    _validate_model_state(model, model.state_dict(), model_identity(model))
    if trainer_state is not None and not isinstance(trainer_state, dict):
        raise ValueError("Trainer state must be an explicit dictionary")
    if (directory / "latest.json").exists():
        previous = _read_pointer(directory, binding, parent_step)
        if step < previous["step"] or elapsed_seconds < previous["elapsed_seconds"]:
            raise ValueError("Checkpoint progress cannot move backwards")
    snapshot = dict(
        schema=SCHEMA,
        binding=binding,
        step=step,
        elapsed_seconds=float(elapsed_seconds),
        model=model.state_dict(),
        model_identity=model_identity(model),
        optimizer=optimizer.state_dict(),
        rng=_rng_state(),
        training=model.training,
        trainer_state=trainer_state or {},
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
            schema=SCHEMA,
            file=final.name,
            SHA256=sha(final),
            step=step,
            run_id=binding["run_id"],
            model_identity=snapshot["model_identity"],
            elapsed_seconds=float(elapsed_seconds),
        )
        _atomic_json(directory / "latest.json", pointer)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return pointer


def load_checkpoint(directory, model, optimizer, binding, *, sources=None):
    """Validate exact bytes/config/ages before restoring model, optimizer and all RNG."""
    directory = Path(directory)
    births, parent_step = _verify_binding(model, optimizer, binding, sources)
    if json.loads((directory / "RUN.json").read_text()) != binding:
        raise ValueError("Immutable run/input/config/split binding differs")
    pointer = _read_pointer(directory, binding, parent_step)
    state = torch.load(directory / pointer["file"], map_location="cpu", weights_only=True)
    if (
        not isinstance(state, dict)
        or set(state)
        != {
            "schema",
            "binding",
            "step",
            "elapsed_seconds",
            "model",
            "model_identity",
            "optimizer",
            "rng",
            "training",
            "trainer_state",
        }
        or state["schema"] != SCHEMA
        or state["binding"] != binding
        or state["step"] != pointer["step"]
        or state["elapsed_seconds"] != pointer["elapsed_seconds"]
        or state["model_identity"] != pointer["model_identity"]
        or type(state["training"]) is not bool
        or not isinstance(state["trainer_state"], dict)
    ):
        raise ValueError("Exact checkpoint step/model/trainer identity required")
    _progress(state["step"], state["elapsed_seconds"], binding, parent_step)
    _validate_model_state(model, state["model"], state["model_identity"])
    _validate_saved_optimizer(model, optimizer, state["optimizer"], state["step"], births)
    _validate_rng(state["rng"])
    model.load_state_dict(state["model"], strict=True)
    optimizer.load_state_dict(state["optimizer"])
    validate_moments(model, optimizer, state["step"], births)
    model.train(state["training"])
    optimizer.zero_grad(set_to_none=True)
    _restore_rng(state["rng"])
    return dict(
        step=state["step"],
        elapsed_seconds=state["elapsed_seconds"],
        model_identity=state["model_identity"],
        checkpoint_SHA256=pointer["SHA256"],
        trainer_state=state["trainer_state"],
    )


__all__ = [
    "SCHEMA",
    "load_checkpoint",
    "model_identity",
    "run_guard",
    "save_checkpoint",
    "validate_moments",
]
