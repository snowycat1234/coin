import copy
import hashlib
import json
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from quant.forward_report import (
    DAY_US,
    ZERO_HASH,
    evaluate_forward_records,
    format_forward_report,
    read_forward_report,
    record_digest,
    verify_record_chain,
)


def chain(bodies):
    records = []
    previous = ZERO_HASH
    for seq, body in enumerate(bodies, 1):
        record = {"seq": seq, "version": "engineering_v1", "prev_hash": previous, **body}
        record["hash"] = record_digest(record)
        records.append(record)
        previous = record["hash"]
    return records


def fixture(days=10, scenarios=("candidate", "B2", "fee_x2", "slippage_x2")):
    first = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp() * 1e6)
    records = [{"received_us": first, "kind": "start", "payload": {
        "role": "candidate", "mode": "engineering_simulation", "source": "synthetic",
        "initial_cash": 10000, "qualified_72h_at_start": False}}]
    for day in range(days):
        for scenario in scenarios:
            records.append({"received_us": first + (day + 1) * DAY_US + 1_000_000,
                            "kind": "nav", "payload": {
                                "scenario": scenario, "date": (
                                    datetime(2025, 1, 1) + timedelta(days=day)).date().isoformat(),
                                "nav": 10000 * 1.001 ** (day + 1), "fees": 1.,
                                "execution_costs": .5, "turnover": .1,
                                "stale_exposure": False, "daily_risk_observable": True,
                                "complete_utc_day": True,
                                "timely_recorded": True, "observation_status": "FORWARD",
                                "source": "synthetic"}})
    return chain(records)


def evaluate(records, **kwargs):
    head_hash = records[-1]["hash"] if records else ZERO_HASH
    return evaluate_forward_records(records, head_hash=head_hash,
                                    triggers_verified=True, **kwargs)


def test_empty_or_reference_ledger_has_no_candidate():
    report = evaluate([])
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    reference = fixture()
    bodies = [{k: record[k] for k in ("received_us", "kind", "payload")} for record in reference]
    bodies[0]["payload"]["role"] = "baseline"
    report = evaluate(chain(bodies))
    assert not report["champion"]
    assert "参考记录" in " ".join(report["reasons"])


def test_190_synthetic_days_never_earn_real_180_day_evidence():
    report = evaluate(fixture(190))
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["actual_elapsed_days"] == 0
    assert report["engineering_span_days"] >= 190
    assert not report["champion"]
    assert not report["real_money_authorized"]


def test_missing_stress_is_reported_as_missing_not_zero_return():
    report = evaluate(fixture(190, ("candidate", "B2")))
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["missing_scenarios"] == ["fee_x2", "slippage_x2"]
    assert report["metrics"] == {}
    assert "fee_x2" in format_forward_report(report)


def test_incident_rejects_even_before_minimum_duration():
    records = fixture(10)
    bodies = [{k: record[k] for k in ("received_us", "kind", "payload")} for record in records]
    bodies.append({"received_us": records[-1]["received_us"] + 1, "kind": "incident",
                   "payload": {"reason": "unknown_order_state"}})
    report = evaluate(chain(bodies))
    assert report["status"] == "FAIL"
    assert report["incident_count"] == 1
    assert "zero_incidents" in report["failed_checks"]


def test_hash_chain_detects_nav_rewrite_and_deleted_history():
    original = fixture(10)
    changed = copy.deepcopy(original)
    changed[2]["payload"]["nav"] *= 1.01
    report = evaluate_forward_records(changed, head_hash=original[-1]["hash"],
                                     triggers_verified=True)
    assert report["status"] == "FAIL"
    assert report["failed_checks"] == ["record_integrity"]
    with pytest.raises(ValueError):
        verify_record_chain(original[1:], original[-1]["hash"])


def test_benchmark_must_cover_exact_same_UTC_period():
    records = fixture(190)
    bodies = [{k: record[k] for k in ("received_us", "kind", "payload")} for record in records
              if not (record["kind"] == "nav" and record["payload"]["scenario"] == "B2" and
                      record["payload"]["date"] == "2025-02-01")]
    report = evaluate(chain(bodies))
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert any("B2" in reason and "相同" in reason for reason in report["reasons"])


def test_frozen_version_is_not_spliced_with_another_version():
    records = fixture(190)
    changed = copy.deepcopy(records)
    for record in changed:
        if record["kind"] == "nav" and record["payload"]["scenario"] == "fee_x2":
            record["version"] = "different_version"
    previous = ZERO_HASH
    for record in changed:
        record["prev_hash"] = previous
        record["hash"] = record_digest(record)
        previous = record["hash"]
    report = evaluate(changed, expected_version="engineering_v1")
    assert "fee_x2" in report["missing_scenarios"]
    assert report["status"] == "INSUFFICIENT_EVIDENCE"


def test_sqlite_adapter_reads_without_changing_evidence(tmp_path):
    path = tmp_path / "engineering.sqlite3"
    db = sqlite3.connect(path)
    db.executescript("""
        CREATE TABLE records(seq INTEGER PRIMARY KEY,received_us INTEGER,version TEXT,
                             kind TEXT,payload TEXT,prev_hash TEXT,hash TEXT);
        CREATE TRIGGER records_no_update BEFORE UPDATE ON records
        BEGIN SELECT RAISE(ABORT,'immutable'); END;
        CREATE TRIGGER records_no_delete BEFORE DELETE ON records
        BEGIN SELECT RAISE(ABORT,'immutable'); END;
    """)
    for record in fixture(10):
        db.execute("INSERT INTO records VALUES(?,?,?,?,?,?,?)", (
            record["seq"], record["received_us"], record["version"], record["kind"],
            json.dumps(record["payload"]), record["prev_hash"], record["hash"]))
    db.commit()
    db.close()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    report = read_forward_report(path)
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["actual_elapsed_days"] == 0
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_partial_first_UTC_day_does_not_inflate_observation_count():
    records = fixture(190)
    bodies = [{k: record[k] for k in ("received_us", "kind", "payload")} for record in records]
    bodies[0]["received_us"] += DAY_US // 2
    for body in bodies:
        if body["kind"] == "nav" and body["payload"]["date"] == "2025-01-01":
            body["payload"]["complete_utc_day"] = False
    report = evaluate(chain(bodies))
    assert report["status"] == "INSUFFICIENT_EVIDENCE"
    assert report["daily_observations"] == 189
    assert report["actual_elapsed_days"] == 0
    assert not any("不连续" in reason for reason in report["reasons"])
