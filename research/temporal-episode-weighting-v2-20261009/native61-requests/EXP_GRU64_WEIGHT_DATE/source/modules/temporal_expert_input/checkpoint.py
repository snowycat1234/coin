"""Strict atomic checkpoints for two new readouts with distinct Adam birth ages.

The frozen short adapter supplies optimizer, tensor, RNG and source validators.
This isolated adaptation changes only the admitted parameter births and snapshot
schema; its immutable generations retain the same atomic publication protocol.
"""

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
    run_guard,
)
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import digest

SCHEMA = "TEMPORAL_CURRENT_EXPERT_INPUT_CHECKPOINT_V1"
NEW_PARAMETERS = {"r_head.weight", "r_head.bias", "expert_projection.weight"}
validate_moments = frozen.validate_moments


def _births(model, binding):
    specification = binding["specification"]
    algorithm = specification["algorithm"]
    parent_step, births = algorithm["parent"]["step"], algorithm["parameter_birth_steps"]
    named = dict(model.named_parameters())
    if (
        type(parent_step) is not int
        or parent_step < 0
        or type(specification["max_steps"]) is not int
        or specification["max_steps"] < parent_step
        or not isinstance(births, dict)
        or set(births) != set(named)
        or {name for name in named if not name.startswith("base.")} != NEW_PARAMETERS
        or named["expert_projection.weight"].shape != (32, 18)
        or named["r_head.weight"].shape != (1, 32)
        or named["r_head.bias"].shape != (1,)
    ):
        raise ValueError("Exact base and two new readouts with explicit parameter births required")
    if any(
        type(b) is not int or b != (0 if name.startswith("base.") else parent_step)
        for name, b in births.items()
    ):
        raise ValueError("Base birth0 and both new readout births at warm parent step required")
    return births, parent_step


def _verify_binding(model, optimizer, binding, sources, *, completed=False):
    frozen._verify_optimizer_contract(model, optimizer)
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
    frozen._verify_sources(binding, sources)
    root = Path(__file__).resolve().parents[2]
    current = {str(p.relative_to(root)) for p in Path(__file__).parent.glob("*.py")}
    if not current.issubset(specification["algorithm"]["versioned_sources"]):
        raise ValueError("Every current expert-input module source must be bound")
    return _births(model, binding)


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
    match = (
        frozen._GENERATION.fullmatch(pointer["file"]) if isinstance(pointer["file"], str) else None
    )
    if (
        pointer["schema"] != SCHEMA
        or match is None
        or int(match[1]) != pointer["step"]
        or pointer["run_id"] != binding["run_id"]
        or not isinstance(pointer["SHA256"], str)
        or frozen._HEX.fullmatch(pointer["SHA256"]) is None
        or not isinstance(pointer["model_identity"], str)
        or frozen._HEX.fullmatch(pointer["model_identity"]) is None
    ):
        raise ValueError("Exact checkpoint pointer step/run/model identity required")
    frozen._progress(pointer["step"], pointer["elapsed_seconds"], binding, parent_step)
    if sha(directory / pointer["file"]) != pointer["SHA256"]:
        raise ValueError("Exact checkpoint bytes required before safe deserialization")
    return pointer


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
    """Fsync an immutable completed-update generation before advancing its pointer."""
    directory = Path(directory)
    births, parent_step = _verify_binding(model, optimizer, binding, sources, completed=True)
    if json.loads((directory / "RUN.json").read_text()) != binding:
        raise ValueError("Immutable run/input/config/split identity differs")
    frozen._progress(step, elapsed_seconds, binding, parent_step)
    validate_moments(model, optimizer, step, births)
    frozen._validate_model_state(model, model.state_dict(), model_identity(model))
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
    """Validate all bytes/state before restoring model, Adam and exact saved RNG."""
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
    frozen._progress(state["step"], state["elapsed_seconds"], binding, parent_step)
    frozen._validate_model_state(model, state["model"], state["model_identity"])
    frozen._validate_saved_optimizer(model, optimizer, state["optimizer"], state["step"], births)
    frozen._validate_rng(state["rng"])
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
