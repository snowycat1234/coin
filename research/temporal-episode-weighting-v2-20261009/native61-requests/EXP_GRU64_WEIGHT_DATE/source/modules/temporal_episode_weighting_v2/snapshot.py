"""Load one byte-pinned preserved pre-ablation model/Adam/RNG snapshot."""

import json
import math
import shutil
from pathlib import Path

import torch

from modules.temporal_expert_input.checkpoint import SCHEMA, load_checkpoint
from modules.temporal_expert_input.stage import initialize as original_initialize
from modules.temporal_expert_input.stage import sources as original_sources
from modules.temporal_two_expert.checkpoint import _atomic_json, model_identity
from modules.temporal_two_expert.exact import sha

FILE = "step-00000780-ecd1de35052b4f02975e3da43f81f438.pt"
SHA256 = "0f51bd3316f6e1100de518e8283ef3afb1c1148007bbb4d5fa7e3d1375acaddb"
IDENTITY = "2dd1898b9f7e05cd9a7a8418bf7b1c8609c7f50b79c03110e68590e9630522ad"
PRODUCER = "c0c110468cd0deee312e18f159c44b98108d8691"


def preserve(state, output):
    state, output = Path(state), Path(output)
    source = state / "expert-input/GRU64_EXPERT_INPUT_ACTIVE"
    if sha(source / FILE) != SHA256:
        raise ValueError("Exact preserved before-first-evaluation step780 snapshot required")
    old = torch.load(source / FILE, weights_only=True, map_location="cpu")
    binding = json.loads((source / "RUN.json").read_text())
    if (
        old["binding"] != binding
        or old["step"] != 780
        or old["model_identity"] != IDENTITY
        or old["trainer_state"]["history"]
        or old["trainer_state"]["initial_norm"] is not None
        or old["trainer_state"]["completed_stage_updates"] != 0
        or old["training"] is not True
        or binding["specification"]["algorithm"]["versioned_sources"] != original_sources()
    ):
        raise ValueError("Unchanged unique pre-ablation zero-update snapshot required")
    output.mkdir(parents=True, exist_ok=True)
    if (output / FILE).exists():
        if sha(output / FILE) != SHA256:
            raise ValueError("Preserved initial snapshot is immutable")
    else:
        shutil.copyfile(source / FILE, output / FILE)
    pointer = dict(
        schema=SCHEMA,
        file=FILE,
        SHA256=SHA256,
        step=780,
        run_id=binding["run_id"],
        model_identity=IDENTITY,
        elapsed_seconds=old["elapsed_seconds"],
    )
    for name, record in (("RUN.json", binding), ("latest.json", pointer)):
        if (output / name).exists() and json.loads((output / name).read_text()) != record:
            raise ValueError("Preserved initial binding is immutable")
        if not (output / name).exists():
            _atomic_json(output / name, record)
    provenance = dict(
        schema="ONE_IDENTICAL_PRESERVED_PRE_ABLATION_INITIAL_V1",
        source_commit=PRODUCER,
        source_file=FILE,
        snapshot_SHA256=SHA256,
        model_identity=IDENTITY,
        global_base_step=780,
        new_parameter_step=0,
        selection="unique_before_first_training_evaluation;zero_new_updates",
        fresh_initialization=False,
        input_enabled=True,
        parameters=13699,
        development_used_for_selection=False,
    )
    _atomic_json(output / "PROVENANCE.json", provenance)
    return provenance


def initialize(state, scaler):
    folder = Path(state) / "episode-weighting-v2/INITIAL"
    if sha(folder / FILE) != SHA256:
        raise ValueError("One immutable shared initial model/Adam/RNG required")
    model, optimizer, parent, births = original_initialize(state, scaler, True)
    binding = json.loads((folder / "RUN.json").read_text())
    loaded = load_checkpoint(folder, model, optimizer, binding, sources=original_sources)
    if loaded["step"] != 780 or model_identity(model) != IDENTITY:
        raise ValueError("Exact shared model snapshot identity required")
    if torch.count_nonzero(model.expert_projection.weight) or torch.count_nonzero(
        model.r_head.weight
    ):
        raise ValueError("Zero initial projection/short weight required")
    if float(model.r_head.bias.detach()) != math.log(0.01 / 0.99):
        raise ValueError("Original one-percent short initialization required")
    if any(optimizer.state[p] for n, p in model.named_parameters() if not n.startswith("base.")):
        raise ValueError("New readout/projection Adam state must be empty at step780")
    return model, optimizer, parent, births
