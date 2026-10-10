"""Expanded-study binding adapter of selected-refit atomic snapshot/validators."""

import json
import os
import tempfile
import uuid
from pathlib import Path

import numpy as np
import torch

from modules.temporal_short_expansion import checkpoint as frozen
from modules.temporal_two_expert.checkpoint import (
    OPTIMIZER,
    _atomic_json,
    _restore_rng,
    _rng_state,
    _sync_directory,
    model_identity,
    run_binding,
)
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

from .protocol import DECISION_SHA, protocol, sources, task

SCHEMA = "NEUTRAL_SHORT1137_TRAIN1273_REFIT_CHECKPOINT_V1"


def optimizer_for(model, settings):
    if settings != task(settings["task_id"]):
        raise ValueError("Only exact approved candidate settings required")
    return torch.optim.Adam(
        model.parameters(),
        lr=settings["lr"],
        betas=(0.9, 0.999),
        eps=1e-8,
        weight_decay=0.0,
        foreach=False,
    )


def binding_for(model, data, settings):
    if settings != task(settings["task_id"]):
        raise ValueError("Only exact approved task settings required")
    result = run_binding(
        model,
        data_split_identity=data,
        feature_batch_size=32,
        max_steps=256,
        max_seconds=1200.0,
        algorithm=dict(
            parent=dict(step=0, fresh=True),
            parameter_birth_steps={n: 0 for n, _ in model.named_parameters()},
            task=settings,
            protocol=protocol(),
            versioned_sources=sources(),
            selected_decision_SHA256=DECISION_SHA,
        ),
    )
    spec = dict(result["specification"])
    spec.update(
        schema="NEUTRAL_SHORT1137_TRAIN1273_REFIT_RUN_V1",
        optimizer=dict(OPTIMIZER, lr=settings["lr"]),
        checkpoint_selection="fixed256_terminal_only;reserve_never_read",
    )
    # Real receipts can contain np.float64 (JSON accepts it, restricted Torch does not).
    # Store the exact same numeric binding using only plain JSON scalar/container types.
    result = dict(run_id=digest(spec), specification=spec)
    return json.loads(json.dumps(result, allow_nan=False))


def verify(model, optimizer, binding, *, completed=False):
    spec = binding["specification"]
    settings = task(spec["algorithm"]["task"]["task_id"])
    if (
        binding != dict(run_id=digest(spec), specification=spec)
        or spec["algorithm"]["task"] != settings
        or spec["algorithm"]["protocol"] != protocol()
        or spec["algorithm"]["selected_decision_SHA256"] != DECISION_SHA
        or spec["model_contract"] != model.contract
        or spec["optimizer"] != dict(OPTIMIZER, lr=settings["lr"])
        or spec["schema"] != "NEUTRAL_SHORT1137_TRAIN1273_REFIT_RUN_V1"
        or spec["max_steps"] != 256
        or spec["feature_batch_size"] != 32
        or spec["max_seconds"] != 1200.0
        or spec["torch_version"] != str(torch.__version__)
        or spec["numpy_version"] != str(np.__version__)
        or spec["torch_threads"] != torch.get_num_threads()
        or spec["deterministic_algorithms"] != torch.are_deterministic_algorithms_enabled()
        or spec["cpu_only"] is not True
        or any(v.device.type != "cpu" for v in model.state_dict().values())
        or (completed and any(p.grad is not None for p in model.parameters()))
    ):
        raise ValueError("Exact study/model/source/recipe/CPU binding required")
    frozen._verify_sources(binding, sources)
    if type(optimizer) is not torch.optim.Adam or len(optimizer.param_groups) != 1:
        raise ValueError("One approved Adam group required")
    group = optimizer.param_groups[0]
    expected = optimizer_for(model, settings).state_dict()["param_groups"][0]
    if optimizer.state_dict()["param_groups"][0] != expected or list(
        map(id, group["params"])
    ) != list(map(id, model.parameters())):
        raise ValueError("Exact approved Adam configuration and parameter order required")
    births = spec["algorithm"]["parameter_birth_steps"]
    if births != {n: 0 for n, _ in model.named_parameters()} or spec["algorithm"]["parent"] != dict(
        step=0, fresh=True
    ):
        raise ValueError("All parameters must be fresh at birth0")
    return births


def validate_moments(model, optimizer, step, births):
    if set(optimizer.state) - set(model.parameters()):
        raise ValueError("Unexpected Adam state")
    for name, parameter in model.named_parameters():
        frozen._validate_adam_state(
            parameter, optimizer.state.get(parameter, {}), step - births[name]
        )


def pointer(directory, binding, name="latest.json"):
    directory = Path(directory)
    record = json.loads((directory / name).read_text())
    match = frozen._GENERATION.fullmatch(record["file"])
    if (
        record["schema"] != SCHEMA
        or record["run_id"] != binding["run_id"]
        or match is None
        or int(match[1]) != record["step"]
        or sha(directory / record["file"]) != record["SHA256"]
    ):
        raise ValueError("Exact immutable snapshot bytes/run/step required")
    frozen._progress(record["step"], record["elapsed_seconds"], binding, 0)
    return record


def save(directory, model, optimizer, binding, *, step, elapsed, history):
    directory = Path(directory)
    births = verify(model, optimizer, binding, completed=True)
    if (
        json.loads((directory / "RUN.json").read_text()) != binding
        or history["completed_updates"] != step
    ):
        raise ValueError("Completed update and exact run/trainer identity required")
    frozen._progress(step, elapsed, binding, 0)
    validate_moments(model, optimizer, step, births)
    frozen._validate_model_state(model, model.state_dict(), model_identity(model))
    if (directory / "latest.json").exists():
        previous = pointer(directory, binding)
        if step < previous["step"] or elapsed < previous["elapsed_seconds"]:
            raise ValueError("Monotonic completed progress required")
    snapshot = dict(
        schema=SCHEMA,
        binding=binding,
        step=step,
        elapsed_seconds=float(elapsed),
        model=model.state_dict(),
        model_identity=model_identity(model),
        optimizer=optimizer.state_dict(),
        rng=_rng_state(),
        training=model.training,
        trainer_state=history,
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
        result = dict(
            schema=SCHEMA,
            file=final.name,
            SHA256=sha(final),
            step=step,
            run_id=binding["run_id"],
            model_identity=snapshot["model_identity"],
            elapsed_seconds=float(elapsed),
        )
        _atomic_json(directory / "latest.json", result)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return result


def load(directory, model, optimizer, binding, *, name="latest.json"):
    directory = Path(directory)
    births = verify(model, optimizer, binding)
    if json.loads((directory / "RUN.json").read_text()) != binding:
        raise ValueError("Immutable run identity differs")
    p = pointer(directory, binding, name)
    state = torch.load(directory / p["file"], map_location="cpu", weights_only=True)
    if (
        state["schema"] != SCHEMA
        or state["binding"] != binding
        or state["step"] != p["step"]
        or state["elapsed_seconds"] != p["elapsed_seconds"]
        or state["model_identity"] != p["model_identity"]
        or type(state["training"]) is not bool
        or state["trainer_state"]["completed_updates"] != p["step"]
    ):
        raise ValueError("Exact snapshot identity/progress required")
    frozen._validate_model_state(model, state["model"], state["model_identity"])
    frozen._validate_saved_optimizer(model, optimizer, state["optimizer"], state["step"], births)
    frozen._validate_rng(state["rng"])
    model.load_state_dict(state["model"], strict=True)
    optimizer.load_state_dict(state["optimizer"])
    validate_moments(model, optimizer, state["step"], births)
    model.train(state["training"])
    model.zero_grad(set_to_none=True)
    _restore_rng(state["rng"])
    return state, p


def retain(directory):
    """Prune only this study's superseded generations after durable pointers exist."""
    directory = Path(directory)
    keep = {
        json.loads(p.read_text())["file"]
        for p in directory.glob("*.json")
        if p.name in {"latest.json", "INITIAL.json", "BEST.json", "MATCHED512.json"}
    }
    for path in directory.glob("step-*.pt"):
        if path.name not in keep and frozen._GENERATION.fullmatch(path.name):
            path.unlink()
