import json
import sqlite3
import tempfile
from pathlib import Path

import pytest

from quant.holdout import HoldoutDenied, HoldoutGrant, evaluate_holdout_once, verify_paper_release
from quant.paths import ROOT, STATE
from quant.research import FEATURE_NAMES, canonical_hash, date_us


@pytest.fixture
def registered():
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="holdout-engineering-", dir=STATE) as directory:
        folder = Path(directory)
        protocol = json.loads((ROOT / "configs/experiments/logistic_v1.json").read_text())
        protocol["version"] = "engineering_holdout_fixture"
        start = date_us(protocol["holdout_start"])
        model = {
            "interval": "1h",
            "configuration": {"interval": "1h", "threshold": 0.55},
            "features": list(FEATURE_NAMES),
            "classes": [0, 1],
            "scaler_mean": [0] * 10,
            "scaler_scale": [1] * 10,
            "coefficients": [0] * 10,
            "intercept": 2,
            "protocol_sha256": canonical_hash(protocol),
            "holdout_revealed": False,
            "training_last_available_us": start - 10_000_000,
            "training_last_label_end_us": start - 1_000_000,
            "validation_end_us": start,
            "provenance": "engineering_simulation",
        }
        report = {
            "status": "HOLDOUT_REQUIRED",
            "holdout_revealed": False,
            "selected_interval": "1h",
            "frozen_model_sha256": canonical_hash(model),
            "protocol_sha256": canonical_hash(protocol),
            "dataset_id": "synthetic-dataset",
            "candidates": {"1h": {"gates": {"development_passed": True}}},
        }
        for name, value in (("summary", report), ("model", model), ("protocol", protocol)):
            (folder / f"{name}.json").write_text(json.dumps(value))
        grant = HoldoutGrant(
            canonical_hash(model),
            canonical_hash(protocol),
            "synthetic-dataset",
            "engineering-root",
            "合成验收，不读取真实留出",
        )
        yield folder, grant, model


def arguments(folder, grant):
    return {
        "development_report_path": folder / "summary.json",
        "model_path": folder / "model.json",
        "protocol_path": folder / "protocol.json",
        "grant": grant,
        "state_db": folder / "tickets.sqlite3",
        "engineering": True,
        "dataset_verifier": lambda: {"dataset_id": "synthetic-dataset"},
        "loader": lambda *_: "synthetic-only",
        "evaluator": lambda *_: {"gates": {"development_passed": True}},
    }


def test_actual_v1_STOP_refuses_before_model_protocol_dataset_or_database(registered):
    folder, grant, _ = registered
    called = []
    with pytest.raises(HoldoutDenied, match="禁止读取留出"):
        evaluate_holdout_once(
            ROOT / "reports/generated/P04/summary.json",
            folder / "nonexistent-model.json",
            folder / "nonexistent-protocol.json",
            grant=grant,
            state_db=folder / "not-created.sqlite3",
            engineering=True,
            dataset_verifier=lambda: called.append("dataset"),
            loader=lambda *_: called.append("holdout"),
        )
    assert not called
    assert not (folder / "not-created.sqlite3").exists()


def test_one_ticket_only_and_engineering_receipt_never_admits_live(registered):
    folder, grant, model = registered
    result = evaluate_holdout_once(**arguments(folder, grant))
    assert result["status"] == "ENGINEERING_ONLY"
    assert not result["real_money_authorized"]
    with pytest.raises(HoldoutDenied, match="已消费"):
        evaluate_holdout_once(**arguments(folder, grant))
    with pytest.raises(HoldoutDenied, match="真实单次留出"):
        verify_paper_release(result, model)
    db = sqlite3.connect(folder / "tickets.sqlite3")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("DELETE FROM attempts")
    with pytest.raises(sqlite3.IntegrityError):
        db.execute("UPDATE receipts SET receipt='{}'")
    db.close()


def test_loader_failure_consumes_without_technical_retry_or_second_read(registered):
    folder, grant, _ = registered
    calls = []

    def failing_loader(*_):
        calls.append("opened synthetic")
        raise OSError("engineering simulated crash")

    kwargs = {**arguments(folder, grant), "loader": failing_loader}
    assert evaluate_holdout_once(**kwargs)["status"] == "INVALID_RUN_CONSUMED"
    with pytest.raises(HoldoutDenied):
        evaluate_holdout_once(**kwargs)
    assert calls == ["opened synthetic"]


def test_frozen_model_change_denied_before_loader(registered):
    folder, grant, model = registered
    model["intercept"] = 10
    (folder / "model.json").write_text(json.dumps(model))
    with pytest.raises(HoldoutDenied, match="不符"):
        evaluate_holdout_once(**arguments(folder, grant))
    assert not (folder / "tickets.sqlite3").exists()


def test_real_evaluator_cannot_be_replaced_by_synthetic_callback(registered):
    folder, grant, _ = registered
    with pytest.raises(HoldoutDenied, match="不能注入"):
        evaluate_holdout_once(**{**arguments(folder, grant), "engineering": False})


def test_forged_paper_status_from_engineering_subledger_is_denied(registered):
    folder, grant, value = registered
    result = evaluate_holdout_once(**arguments(folder, grant))
    forged = {**result, "status": "PAPER_ELIGIBLE", "engineering": False}
    with pytest.raises(HoldoutDenied, match="固定留出消费账本"):
        verify_paper_release(forged, value)


def test_sealed_v1_cannot_be_admitted_using_a_forged_development_summary(registered):
    folder, grant, _ = registered
    report = json.loads((folder / "summary.json").read_text())
    sealed = json.loads((ROOT / "reports/generated/P04/summary.json").read_text())
    report["protocol_sha256"] = sealed["protocol_sha256"]
    (folder / "summary.json").write_text(json.dumps(report))
    with pytest.raises(HoldoutDenied, match="已封存v1"):
        evaluate_holdout_once(**arguments(folder, grant))
    assert not (folder / "tickets.sqlite3").exists()
