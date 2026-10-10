import hashlib
import json
import subprocess

import numpy as np
import torch

from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_short_expansion.checkpoint import (
    _validate_model_state,
    _validate_rng,
    _validate_saved_optimizer,
)
from modules.temporal_two_expert.checkpoint import _restore_rng, model_identity
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.inputs import Standardizer, digest

from .protocol import MODELS, ROOT, SCALER


def commit_bytes(commit, name):
    data = subprocess.run(
        ["git", "show", commit + ":" + name], cwd=ROOT, check=True, capture_output=True
    ).stdout
    return hashlib.sha256(data).hexdigest()


def shared_scaler():
    scalers = []
    for entry in MODELS.values():
        folder = ROOT / entry["folder"]
        for name in ("SCALER.json", "SCALER.npz", entry["file"], "TERMINAL.json", "RUN.json"):
            if sha(folder / name) != commit_bytes(entry["commit"], entry["folder"] + "/" + name):
                raise ValueError("Pinned model source commit bytes changed")
        meta = json.loads((folder / "SCALER.json").read_text())
        with np.load(folder / "SCALER.npz", allow_pickle=False) as z:
            scaler = Standardizer(z["mean"], z["scale"], z["count"], meta["provenance"])
        if scaler.identity != SCALER or scaler.provenance["real_row_count"] != 907:
            raise ValueError("The requested common907 scaler is required")
        scalers.append(scaler)
    for name in ("mean", "scale", "count"):
        np.testing.assert_array_equal(getattr(scalers[0], name), getattr(scalers[1], name))
    return scalers[0]


def validate_epoch(snapshot, entry):
    config = snapshot["binding"]["specification"]
    if (
        snapshot["step"] != 256
        or config["max_steps"] != 256
        or snapshot["model_identity"] != entry["model_identity"]
        or config["model_contract"]["base_contract"]["seed"] != 20261009
        or config["optimizer"]["lr"] != 0.0003
        or config["model_contract"]["base_contract"]["standardizer_identity"] != SCALER
        or snapshot["binding"]["run_id"] != digest(config)
    ):
        raise ValueError("Exact specified LOW_LR3E4 fresh256 snapshot required; never April512")


def frozen_model(name, scaler):
    entry = MODELS[name]
    folder = ROOT / entry["folder"]
    path = folder / entry["file"]
    if sha(path) != entry["checkpoint_SHA256"]:
        raise ValueError("Exact specified checkpoint SHA required before restricted load")
    snapshot = torch.load(path, map_location="cpu", weights_only=True)
    validate_epoch(snapshot, entry)
    model, _ = initialize(scaler)
    optimizer = torch.optim.Adam(
        model.parameters(), lr=0.0003, betas=(0.9, 0.999), eps=1e-8, weight_decay=0, foreach=False
    )
    config = snapshot["binding"]["specification"]
    if (
        config["model_contract"] != model.contract
        or config["torch_version"] != str(torch.__version__)
        or config["numpy_version"] != str(np.__version__)
        or not config["cpu_only"]
        or not config["deterministic_algorithms"]
        or torch.get_num_threads() != 1
        or not torch.are_deterministic_algorithms_enabled()
    ):
        raise ValueError("Frozen model/runtime/scaler contract changed")
    for graph in (config.get("sources", {}), config["algorithm"]["versioned_sources"]):
        for source, value in graph.items():
            if sha(ROOT / source) != value:
                raise ValueError("Frozen fitting source changed")
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    if (
        terminal["status"] != "FIXED256_COMPLETE"
        or terminal["completed_updates"] != 256
        or terminal["checkpoint_SHA256"] != sha(path)
    ):
        raise ValueError("Frozen terminal256 binding required")
    _validate_model_state(model, snapshot["model"], entry["model_identity"])
    _validate_saved_optimizer(
        model, optimizer, snapshot["optimizer"], 256, {n: 0 for n, _ in model.named_parameters()}
    )
    _validate_rng(snapshot["rng"])
    model.load_state_dict(snapshot["model"], strict=True)
    optimizer.load_state_dict(snapshot["optimizer"])
    _restore_rng(snapshot["rng"])
    if model_identity(model) != entry["model_identity"] or model.parameter_count != 13699:
        raise ValueError("Exact frozen model identity/count required")
    return model, optimizer, snapshot
