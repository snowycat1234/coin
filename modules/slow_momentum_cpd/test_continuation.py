"""Synthetic resume/cutoff/stop tests; no real continuation or validation query."""

import copy
import hashlib
import io

import numpy as np
import pytest
import torch
from torch import nn

from . import continuation as c
from .core import FrozenGP, Scaler


class Toy(nn.Module):
    def __init__(self):
        super().__init__()
        self.layer = nn.Linear(10, 1)
        self.drop = nn.Dropout(0.2)

    def forward(self, x):
        return torch.tanh(self.layer(self.drop(x[:, -1])).squeeze(-1))


def initial():
    torch.manual_seed(7)
    model = Toy()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    return {
        "model": model,
        "optimizer": optimizer,
        "rng": np.random.default_rng(7),
        "torch_rng": torch.get_rng_state().clone(),
        "updates": 0,
        "batch_hash": hashlib.sha256(),
        "continuation_batch_hash": hashlib.sha256(),
    }


def test_exact_resume_model_adam_rng_and_next_batch_matches_uninterrupted():
    x = np.random.default_rng(1).normal(size=(24, 3, 10)).astype("float32")
    y = np.linspace(-0.02, 0.03, 24)
    uninterrupted = initial()
    c.advance(uninterrupted, x, y, count=8, batch_size=8)
    interrupted = initial()
    c.advance(interrupted, x, y, count=3, batch_size=8)
    cp = {
        "model": interrupted["model"].state_dict(),
        "optimizer": interrupted["optimizer"].state_dict(),
        "torch_rng": interrupted["torch_rng"],
        "numpy_rng": interrupted["rng"].bit_generator.state,
        "updates": 3,
    }
    buffer = io.BytesIO()
    torch.save(cp, buffer)
    buffer.seek(0)
    loaded = torch.load(buffer, weights_only=True)
    resumed = c.restore(loaded, Toy)
    c.verify_restored(loaded, resumed)
    resumed.update({"batch_hash": hashlib.sha256(), "continuation_batch_hash": hashlib.sha256()})
    c.advance(resumed, x, y, count=5, batch_size=8)
    for a, b in zip(
        uninterrupted["model"].parameters(), resumed["model"].parameters(), strict=True
    ):
        assert torch.equal(a, b)
    for a, b in zip(
        uninterrupted["optimizer"].state.values(), resumed["optimizer"].state.values(), strict=True
    ):
        for key in a:
            assert torch.equal(a[key], b[key])
    assert resumed["updates"] == 8
    assert torch.equal(uninterrupted["torch_rng"], resumed["torch_rng"])
    np.testing.assert_array_equal(
        uninterrupted["rng"].integers(0, 24, 8), resumed["rng"].integers(0, 24, 8)
    )


def curves(values):
    return [[{"full_train_loss": v} for v in values] for _ in range(6)]


def test_common_stop_requires_all_six_three_absolute_changes_and_minimum():
    flat = curves([0, 0.01, -0.005, 0])
    assert c.common_stop(flat, 1280) is None
    assert c.common_stop(flat, 1408) == "COMMON_LOCAL_TRAIN_LOSS_FLAT"
    bad = copy.deepcopy(flat)
    bad[-1][-2]["full_train_loss"] = 0.2
    assert c.common_stop(bad, 1408) is None
    assert c.common_stop(curves([0, -0.1, -0.2, -0.3]), 1536) is None
    assert c.common_stop(bad, 2048) == "COMMON_HARD_CAP2048"


def test_no_validation_access_before_common_stop(monkeypatch):
    monkeypatch.setattr(c.sharpe, "prepare", lambda *a: pytest.fail("validation accessed"))
    with pytest.raises(ValueError, match="forbidden"):
        c.final_validation({}, c.ARCHIVE, None)
    with pytest.raises(AssertionError):
        c.final_validation(
            {("trend", 1): {"updates": 1024}},
            c.ARCHIVE,
            {"status": "COMMON_TRAIN_STOP_FIXED", "common_update": 1408},
        )


def test_actual_train_reader_never_prepares_validation_or_refits(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("validation/refit path called")

    monkeypatch.setattr(c.sharpe, "prepare", forbidden)
    monkeypatch.setattr(FrozenGP, "fit", forbidden)
    monkeypatch.setattr(Scaler, "fit", forbidden)
    _, _, rows, source = c.training_data(c.ARCHIVE)
    assert len(rows) == 2526 and source["validation_queries"] == 0
    assert (
        source["train_rows_sha256"]
        == "983baa27d9c0105c48b7c7debfea24089c28bff277014e1e43e2b27721d9e50f"
    )


def test_nonfinite_state_is_invalid_and_prior_evidence_preserved():
    unit = initial()
    with torch.no_grad():
        next(unit["model"].parameters())[0, 0] = float("nan")
    with pytest.raises(ValueError, match="NONFINITE"):
        c.finite_state(unit)
    assert (
        c.verify_preservation()["manifest_file_counts"]["slow-momentum-cpd-sharpe-20261011"] == 47
    )


def test_actual_checkpoint_restore_does_not_change_lineage_bytes():
    proposal = c.load_proposal()
    before = {
        name: c.sha((c.ORIGINAL_STATE / name).read_bytes())
        for name in proposal["predecessor"]["model_checkpoint_lineage_sha256"]
    }
    units, receipts = c.resume_units(2526)
    assert len(units) == len(receipts) == 6 and all(
        r["exact_restoration"] == "PASS" for r in receipts
    )
    for seed in c.SEEDS:
        a, b = units[("trend", seed)], units[("trend_cpd", seed)]
        assert a["batch_hash"] is not b["batch_hash"]
        assert a["continuation_batch_hash"] is not b["continuation_batch_hash"]
        replay = np.random.default_rng(seed)
        expected = hashlib.sha256()
        for _ in range(1152):
            expected.update(replay.integers(0, 2526, 128).astype("<i8").tobytes())
        for unit in (a, b):
            for _ in range(128):
                unit["batch_hash"].update(
                    unit["rng"].integers(0, 2526, 128).astype("<i8").tobytes()
                )
            assert unit["batch_hash"].hexdigest() == expected.hexdigest()
    after = {name: c.sha((c.ORIGINAL_STATE / name).read_bytes()) for name in before}
    assert before == after == proposal["predecessor"]["model_checkpoint_lineage_sha256"]


def test_validation_start_is_preserved_on_partial_failure(monkeypatch, tmp_path):
    import json

    stop = {"status": "COMMON_TRAIN_STOP_FIXED", "common_update": 1408}
    (tmp_path / "TRAIN_STOP.json").write_text(json.dumps(stop))

    def failed(*args):
        raise RuntimeError("partial validation read failure")

    monkeypatch.setattr(c.sharpe, "prepare", failed)
    with pytest.raises(RuntimeError, match="partial"):
        c.final_validation({("trend", 1): {"updates": 1408}}, c.ARCHIVE, stop, tmp_path)
    receipt = json.loads((tmp_path / "VALIDATION_STARTED.json").read_text())
    assert receipt["common_update"] == 1408 and receipt["partial_if_interrupted"]
    assert not (tmp_path / "POSITIONS.csv").exists()


def test_independent_audit_accepts_invalid_input_without_bootstrap():
    from .audit_continuation import reconcile_statistics

    result = {
        "status": "INVALID_POLICY_EVALUATION",
        "aggregate": None,
        "gates": None,
        "bootstrap": {"status": "NOT_RUN_INVALID_INPUT", "replicates": 0},
    }
    assert reconcile_statistics([], [], {}, {}, result, [["synthetic"]]) is None
    wrong = copy.deepcopy(result)
    wrong["status"] = "STOP_RAW_POLICY_INCREMENT_NOT_ESTABLISHED"
    with pytest.raises(AssertionError):
        reconcile_statistics([], [], {}, {}, wrong, [["synthetic"]])


def test_independent_audit_tracks_degenerate_joint_bootstrap_draws():
    from .audit_continuation import reconcile_statistics

    days = np.arange(42)
    outcomes = np.repeat(np.where(days < 28, 0.0, 0.02)[:, None], 5, axis=1)
    mask = np.ones((42, 5), dtype=bool)
    positions = {"trend": np.full((3, 42, 5), 0.3), "trend_cpd": np.full((3, 42, 5), 0.6)}
    block = {
        "dates": ["synthetic", "synthetic"],
        "times": days,
        "clock": days * c.DAY_US,
        "mask": mask,
        "outcomes": outcomes,
        "missing": np.empty((0, 2)),
        "position": positions,
    }
    scoring = {"scoring": {"bootstrap": {"replicates": 100, "block_days": 14, "seed": 9901}}}
    result = c.sharpe.score_blocks([block], scoring, np.ones((42, 5)))
    assert result["status"] == "INVALID_POLICY_EVALUATION"
    joint = np.stack([positions[a].mean(axis=0) * outcomes for a in c.sharpe.ARMS], axis=2)
    seed_days = {
        a: [[(positions[a][i] * outcomes).sum(axis=1) / 5] for i in range(3)] for a in c.sharpe.ARMS
    }
    gates = reconcile_statistics(
        [joint], [result["blocks"][0]["ensemble_sharpe_increment"]], seed_days, scoring, result, []
    )
    assert not gates["bootstrap_lower_positive"] and result["bootstrap"]["invalid_replicates"] > 0
