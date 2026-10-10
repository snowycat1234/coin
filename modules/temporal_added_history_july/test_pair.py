import copy
import json
from types import SimpleNamespace

import numpy as np
import pytest

from modules.temporal_two_expert.inputs import digest

from . import data
from . import protocol as settings
from .evaluate import checked_request
from .models import validate_epoch
from .protocol import MODELS, SCALER


def snapshot():
    config = dict(
        max_steps=256,
        model_contract=dict(base_contract=dict(seed=20261009, standardizer_identity=SCALER)),
        optimizer=dict(lr=0.0003),
    )
    return dict(
        step=256,
        model_identity=MODELS["FULL773_256"]["model_identity"],
        binding=dict(specification=config, run_id=digest(config)),
    )


def test_reject_april512_wrong_scaler_and_wrong_model_substitution():
    expected = MODELS["FULL773_256"]
    valid = snapshot()
    validate_epoch(valid, expected)
    for key, value in (
        ("step", 512),
        ("model_identity", MODELS["EXPANDED1137_256"]["model_identity"]),
    ):
        bad = copy.deepcopy(valid)
        bad[key] = value
        with pytest.raises(ValueError):
            validate_epoch(bad, expected)
    bad = copy.deepcopy(valid)
    config = bad["binding"]["specification"]
    config["model_contract"]["base_contract"]["standardizer_identity"] = "legacy_April_scaler"
    bad["binding"]["run_id"] = digest(config)
    with pytest.raises(ValueError):
        validate_epoch(bad, expected)


def test_paired_output_mask_canonical_slots_and_simplex():
    episode = SimpleNamespace(eligible=np.ones((63, 6), dtype=bool))
    model = SimpleNamespace(contract=dict(allowed_actions=["CASH", "VOL_MANAGED_HOLD", "CSMOM21"]))
    request = np.tile([0.1, 0.5, 0, 0, 0.4, 0], (63, 1))
    checked_request(request, episode, model)
    episode.eligible[9, 4] = False
    with pytest.raises(ValueError):
        checked_request(request, episode, model)
    episode.eligible[9, 4] = True
    request[9, 2] = 0.1
    with pytest.raises(ValueError):
        checked_request(request, episode, model)


def test_public_prescore_gate_rejects_source_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "ROOT", tmp_path)
    monkeypatch.setattr(settings, "DEST", tmp_path / "paired")
    settings.DEST.mkdir()
    graph = {"code.py": "frozen_SHA"}
    monkeypatch.setattr(settings, "sources", lambda: graph)
    ready = settings.DEST / "PRESCORE.json"
    ready.write_text(json.dumps(dict(protocol=settings.protocol(), sources=graph)))
    publication = tmp_path / "public.json"
    publication.write_text(
        json.dumps(
            dict(
                status="PASS_ALL_PUBLIC_BYTES",
                remote_SHA="fixture",
                files=[dict(path="paired/PRESCORE.json", SHA256=settings.sha(ready))],
            )
        )
    )
    settings.public_gate(publication)
    monkeypatch.setattr(settings, "sources", lambda: {"code.py": "changed"})
    with pytest.raises(ValueError, match="changed"):
        settings.public_gate(publication)


def test_saved_control_manifest_cannot_remove_result_entry(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "ROOT", tmp_path)
    monkeypatch.setattr(data, "OLD", tmp_path / "old")
    monkeypatch.setattr(data, "load", lambda *args: (None, None, None, None))
    data.OLD.mkdir()
    path = data.OLD / "MANIFEST.json"
    path.write_text(json.dumps(dict(files={"RESULT.json": dict(SHA256="original")})))
    original_SHA = settings.sha(path)
    monkeypatch.setattr(data, "commit_bytes", lambda *args: original_SHA)
    path.write_text(json.dumps(dict(files={})))
    with pytest.raises(ValueError, match="Pinned original July manifest"):
        data.inputs(None, None)
