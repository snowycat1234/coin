"""Small synthetic evidence; no live writes, fits or fabricated month of seconds."""

import importlib.util
import json
import sqlite3
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import polars as pl
import pytest

from quant.microstructure import MicrostructureCollector, MicrostructureConfig
from quant.paths import ROOT, STATE

SPEC = importlib.util.spec_from_file_location(
    "audit_microstructure_quality", ROOT / "scripts/audit_microstructure_quality.py"
)
audit = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = audit
SPEC.loader.exec_module(audit)


@pytest.fixture
def evidence():
    with tempfile.TemporaryDirectory(prefix="a07-qa-", dir=STATE) as native:
        with tempfile.TemporaryDirectory(prefix="a07-qa-", dir=ROOT / ".cache/tmp") as data:
            database, store = Path(native) / "source.sqlite3", Path(data)
            writer = MicrostructureCollector(
                MicrostructureConfig(db_path=database, store=store, mode="engineering"),
                disk_check=lambda **kwargs: {"status": "OK"},
            )
            start = audit.FUTURE_START - 24 * audit.DAY
            writer.set_connected(True, received_us=start)
            for second in range(120):
                for symbol in audit.SYMBOLS:
                    writer.ingest(
                        {
                            "u": second + 1,
                            "s": symbol,
                            "b": "100",
                            "a": "102",
                            "B": "10",
                            "A": "20",
                        },
                        received_us=start + second * audit.SECOND + 100,
                    )
            writer.advance(start + 120 * audit.SECOND)
            with writer.db:
                writer.audit(
                    "RAW_PRUNED",
                    {
                        "count": 1,
                        "bytes": 100,
                        "oldest_us": start - 10 * audit.DAY,
                        "latest_us": start - 10 * audit.DAY,
                    },
                )
            writer.close()
            yield database, store


def inspect(evidence, **kwargs):
    return audit.audit_quality(*evidence, **kwargs)


def test_short_real_format_is_readonly_insufficient_and_nullable_is_explicit(evidence):
    database, store = evidence
    frozen = {path: audit.digest(path) for path in (database, *store.rglob("*.parquet"))}
    report = inspect(evidence)
    assert report["integrity"] == "PASS" and report["status"] == "INSUFFICIENT_EVIDENCE"
    assert not report["actual_24h_capacity_accepted"] and report["evidence_stage"] == "QA_ONLY"
    assert report["snapshot"]["read_transaction_released_before_file_scan"]
    assert report["snapshot"]["read_transaction_seconds"] <= 5
    assert report["audit"]["raw_pruned"]["count"] == 1
    assert all(audit.digest(path) == digest for path, digest in frozen.items())
    for stream in report["streams"].values():
        assert not stream["nonfinite"] and not stream["unexpected_missing"]
        assert stream["expected_nullable"]["trade_vwap"] > 0
        assert stream["complete_feature_rows"] == 0
    assert report["capacity"]["projection_is_24h_acceptance"] is False
    assert report["future_since_2026_10_01_utc"]["observed_complete_day_count"] == 0


def rewrite_feature(evidence, transform):
    database, store = evidence
    db = sqlite3.connect(database)
    db.row_factory = sqlite3.Row
    manifest = db.execute("SELECT * FROM manifests WHERE interval_s=1 LIMIT 1").fetchone()
    path = store / manifest["path"]
    transform(pl.read_parquet(path)).write_parquet(path)
    digest, size = audit.digest(path), path.stat().st_size
    triggers = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
    db.execute("DROP TRIGGER manifests_no_update")
    db.execute("DROP TRIGGER audit_no_update")
    db.execute(
        "UPDATE manifests SET sha256=?,bytes=? WHERE path=?", (digest, size, manifest["path"])
    )
    previous = "0" * 64
    for row in db.execute("SELECT * FROM audit ORDER BY seq").fetchall():
        value = json.loads(row["payload"])
        if row["kind"] == "FEATURE_EXPORT" and value["file"] == manifest["path"]:
            value.update(sha256=digest, bytes=size)
        current = audit.fingerprint([row["seq"], row["received_us"], row["kind"], value, previous])
        db.execute(
            "UPDATE audit SET payload=?,previous_sha=?,sha256=? WHERE seq=?",
            (audit.canonical(value).decode(), previous, current, row["seq"]),
        )
        previous = current
    db.execute(triggers["manifests_no_update"])
    db.execute(triggers["audit_no_update"])
    db.commit()
    db.close()


@pytest.mark.parametrize("kind", ["version", "nonfinite", "duplicate"])
def test_sha_rebound_feature_pollution_and_duplicate_time_fail_closed(evidence, kind):
    def transform(frame):
        if kind == "version":
            return frame.with_columns(pl.lit("future_version").alias("version"))
        if kind == "nonfinite":
            return frame.with_columns(pl.lit(float("inf")).alias("OFI_L1"))
        return frame.with_columns(pl.lit(frame["open_us"][0]).alias("open_us"))

    rewrite_feature(evidence, transform)
    report = inspect(evidence)
    assert report["status"] == "FAIL_CLOSED"
    assert not report["actual_24h_capacity_accepted"] and not report["alpha_eligible"]


@pytest.mark.parametrize("damage", ["missing", "modified"])
def test_committed_feature_loss_is_not_legal_raw_retirement(evidence, damage):
    path = next(evidence[1].rglob("*.parquet"))
    if damage == "missing":
        path.unlink()
    else:
        with path.open("ab") as stream:
            stream.write(b"changed")
    report = inspect(evidence)
    assert report["status"] == "FAIL_CLOSED"
    assert "feature" in report["reason"].lower()


@pytest.mark.parametrize(
    "field",
    [
        "max_file_bytes",
        "max_rows_per_file",
        "max_row_group_bytes",
        "max_total_rows",
        "max_files",
        "max_snapshot_bytes",
    ],
)
def test_predecode_resource_bounds_fail_closed(evidence, field):
    report = inspect(evidence, limits=replace(audit.Limits(), **{field: 1}))
    assert report["status"] == "FAIL_CLOSED"
    assert "bound" in report["reason"]


def test_wal_snapshot_released_before_decode_and_new_exports_are_excluded(evidence, monkeypatch):
    original, injected = audit.scan_file, False

    def concurrent_write(*args, **kwargs):
        nonlocal injected
        if not injected:
            db = sqlite3.connect(evidence[0])
            assert db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()[0] == 0
            db.execute("INSERT INTO outbox(interval_s,payload) VALUES(1,'{}')")
            db.commit()
            db.close()
            (evidence[1] / "features/1s/concurrent.partial").write_bytes(b"uncommitted")
            injected = True
        return original(*args, **kwargs)

    monkeypatch.setattr(audit, "scan_file", concurrent_write)
    report = inspect(evidence)
    assert report["integrity"] == "PASS" and report["snapshot"]["outbox_unexported_rows"] == {}
    assert report["inventory"]["unmanifested_feature_count"] == 1
    assert report["status"] == "INSUFFICIENT_EVIDENCE" and injected


def small_day_summaries(offsets):
    # Aggregated engineering metadata only, O(8*days), no full month of 1s arrays.
    buckets = {
        (symbol, interval): audit.Bucket(symbol, interval)
        for symbol in audit.SYMBOLS
        for interval in audit.INTERVALS
    }
    first = audit.FUTURE_START // audit.DAY
    for (_, interval), bucket in buckets.items():
        for offset in offsets:
            bucket.days[first + offset] = {
                "rows": 86400 // interval,
                "known_seconds": 86400,
                "valid_seconds": 86400,
                "quality_valid_rows": 86400 // interval,
            }
    return buckets


def review_coverage(buckets, **kwargs):
    # Synthetic summaries constructed with matching timestamps; real scans use
    # the bounded CommonSeconds matcher, never this summary inference.
    common = {
        day: min(
            buckets[symbol, 1].days.get(day, {}).get("valid_seconds", 0) for symbol in audit.SYMBOLS
        )
        for day in buckets["BTCUSDT", 1].days
    }
    return audit.coverage(buckets, common_valid_by_day=common, **kwargs)


@pytest.mark.parametrize(
    "days,stage",
    [
        (13, "QA_ONLY"),
        (14, "PREDICTIVE_DIAGNOSTICS_ONLY"),
        (29, "PREDICTIVE_DIAGNOSTICS_ONLY"),
        (30, "PREREGISTRATION_REVIEW_ONLY"),
    ],
)
def test_consecutive_stage_boundaries_require_all_eight_streams(days, stage):
    assert review_coverage(small_day_summaries(range(days)))["evidence_stage"] == stage


def test_disjoint_calendar_span_one_missing_stream_and_audit_gap_do_not_certify():
    fragments = review_coverage(small_day_summaries([*range(7), *range(90, 97)]))
    assert fragments["quality_valid_day_count"] == 14
    assert fragments["longest_consecutive_quality_valid_days"] == 7
    assert fragments["evidence_stage"] == "QA_ONLY"
    buckets = small_day_summaries([0])
    first = audit.FUTURE_START // audit.DAY
    assert not review_coverage(buckets, uncertain_days={first})["actual_24h_quality_accepted"]
    buckets["ETHUSDT", 60].days[first]["rows"] -= 1
    assert not review_coverage(buckets)["actual_24h_capacity_accepted"]
    before = review_coverage(small_day_summaries([-1]), future_only=True)
    assert before["observed_complete_day_count"] == 0


def test_observed_days_allow_review_even_if_quality_requires_isolation():
    buckets = small_day_summaries(range(15))
    first = audit.FUTURE_START // audit.DAY
    buckets["BTCUSDT", 1].days[first]["quality_valid_rows"] -= 1
    buckets["BTCUSDT", 1].days[first]["valid_seconds"] -= 1
    result = review_coverage(buckets, uncertain_days={first + 1})
    assert result["evidence_stage"] == "PREDICTIVE_DIAGNOSTICS_ONLY"
    assert result["quality_valid_day_count"] == 13
    assert result["quality_review_required"] and not result["training_authorized"]


def test_empty_known_days_and_short_actual_data_volume_do_not_grant_review():
    buckets = small_day_summaries(range(30))
    for bucket in buckets.values():
        for day in bucket.days.values():
            day["valid_seconds"] = day["quality_valid_rows"] = 0
    result = review_coverage(buckets)
    assert result["observed_complete_day_count"] == 30
    assert result["evidence_stage"] == "QA_ONLY"
    assert not result["preregistered_research_data_review_eligible"]
    assert result["paired_usable_data_days_in_that_period"] == 0
    buckets = small_day_summaries(range(14))
    buckets["ETHUSDT", 1].days[audit.FUTURE_START // audit.DAY]["valid_seconds"] -= 1
    assert review_coverage(buckets)["evidence_stage"] == "QA_ONLY"


def test_paired_market_seconds_use_exact_intersection_and_uncertain_overlap():
    start = audit.FUTURE_START + 100 * audit.SECOND
    matcher = audit.CommonSeconds(
        [(start + 2 * audit.SECOND + 1, start + 3 * audit.SECOND - 1)], audit.Limits()
    )
    for second in range(6):
        symbols = ("BTCUSDT",) if second == 4 else ("ETHUSDT",) if second == 5 else audit.SYMBOLS
        for symbol in symbols:
            flag = audit.FLAGS["STALE_QUOTE"] if second == 3 and symbol == "ETHUSDT" else 0
            matcher.add(
                {
                    "symbol": symbol,
                    "open_us": start + second * audit.SECOND,
                    "quality": flag,
                    "known_seconds": 1,
                    "valid_seconds": int(not flag),
                    "mid": 0 if second == 1 and symbol == "ETHUSDT" else 100.0,
                }
            )
    matcher.flush()
    totals = matcher.report()["totals"]
    assert totals == {
        "matched_seconds": 4,
        "usable_seconds": 1,
        "invalid_or_no_mid_seconds": 2,
        "audit_uncertain_seconds": 1,
        "unpaired_seconds": 2,
    }
    assert matcher.report()["pending_row_limit"] == 2


def test_numeric_string_dtype_is_rejected_before_arrow_decode(evidence, monkeypatch):
    rewrite_feature(evidence, lambda frame: frame.with_columns(pl.col("mid").cast(pl.String)))

    def forbidden_decode(*args, **kwargs):
        raise AssertionError("bad numeric schema reached data decode")

    monkeypatch.setattr(audit.pq.ParquetFile, "iter_batches", forbidden_decode)
    result = inspect(evidence)
    assert result["status"] == "FAIL_CLOSED"
    assert "dtype" in result["reason"]


def test_retrospective_trade_gap_excludes_prior_unflagged_seconds(evidence):
    database, _ = evidence
    start = audit.FUTURE_START - 24 * audit.DAY
    detail = {
        "symbol": "BTCUSDT",
        "from": 1,
        "to": 15,
        "from_received_us": start + 30 * audit.SECOND + 100,
        "to_received_us": start + 33 * audit.SECOND + 100,
    }
    with sqlite3.connect(database) as db:
        seq, previous = db.execute(
            "SELECT seq,sha256 FROM audit ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        stamp = detail["to_received_us"]
        db.execute(
            "INSERT INTO audit VALUES(?,?,?,?,?,?)",
            (
                seq + 1,
                stamp,
                "AGG_ID_GAP",
                audit.canonical(detail).decode(),
                previous,
                audit.fingerprint([seq + 1, stamp, "AGG_ID_GAP", detail, previous]),
            ),
        )
    report = inspect(evidence)
    assert report["integrity"] == "PASS"
    assert report["common_usable_1s_market_data"]["totals"]["audit_uncertain_seconds"] >= 4
    assert report["audit"]["uncertainty_kind_counts"]["AGG_ID_GAP"] == 1


def test_source_paths_and_limits_cannot_escape_D_or_enlarge():
    with pytest.raises(audit.QualityRejected, match="paths"):
        audit.audit_quality(Path("/mnt/c/untrusted.sqlite3"), ROOT / "data/microstructure_v1")
    with pytest.raises(ValueError, match="reduced"):
        audit.Limits(batch_rows=2049)


def test_injected_clock_is_explicit_engineering_provenance(evidence):
    report = inspect(evidence, now_us=audit.FUTURE_START + 40 * audit.DAY)
    assert report["engineering_fixture_hook"] is True
    assert report["evidence_stage"] == "QA_ONLY"
    assert not report["actual_24h_capacity_accepted"]
    assert not report["training_authorized"]


def test_report_is_new_only_and_output_cannot_escape_project():
    with tempfile.TemporaryDirectory(prefix="a07-qa-output-", dir=ROOT / "reports") as folder:
        path = Path(folder) / "report.json"
        audit.save_report({"status": "INSUFFICIENT_EVIDENCE"}, path)
        original = path.read_bytes()
        with pytest.raises(FileExistsError):
            audit.save_report({"status": "PASS"}, path)
        assert path.read_bytes() == original
    with pytest.raises(audit.QualityRejected, match="D project reports"):
        audit.save_report({}, Path("/mnt/c/unsafe-report.json"))
