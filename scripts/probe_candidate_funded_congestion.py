"""Finite funded congestion engineering diagnostic; no fit, network or acceptance."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
import resource
import sqlite3
import sys
import time
import xml.etree.ElementTree as ET
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from quant import disk
from quant.candidate_paper import SCENARIOS, CandidateCollector, CandidatePaperEngine
from quant.collector import Collector
from quant.paths import ROOT, STATE
from quant.resources import status
from quant.shadow import DAY_MS, HOUR_MS, MINUTE_MS, Quote, ShadowConfig, read_forward_evidence


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            result.update(block)
    return result.hexdigest()


def sizes(folder):
    return {path.name: path.stat().st_size for path in folder.iterdir() if path.is_file()}


def runtime_snapshot():
    module_path = Path(sys.modules[CandidatePaperEngine.__module__].__file__).resolve()
    root = module_path.parent.parent
    if not root.is_relative_to((STATE / "candidate-runtime").resolve()):
        raise RuntimeError("Exact native engineering runtime snapshot required")
    path = root / "SOURCE_MANIFEST.json"
    if path.stat().st_size > 100_000:
        raise RuntimeError("Native manifest exceeds bound")
    document = json.loads(path.read_text())
    if (
        document["runtime_root"] != str(root)
        or not document["no_live_admission"]
        or len(document["files"]) != 42
    ):
        raise RuntimeError("Expected immutable 42-source runtime")
    for name, expected in document["files"].items():
        if Path(name).name != name or Path(name).suffix != ".py":
            raise RuntimeError("Invalid runtime source member")
        if any(
            digest(folder / name) != expected for folder in (ROOT / "src/quant", root / "quant")
        ):
            raise RuntimeError("Native and ROOT sources differ")
    return {
        "path": str(path),
        "sha256": digest(path),
        "release_sha256": document["release_sha256"],
        "source_bytes": document["source_bytes"],
        "verified_files": 42,
    }


def fixture_module():
    spec = importlib.util.spec_from_file_location(
        "funded_congestion_synthetic_fixture", ROOT / "tests/test_candidate_adapter.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def quote(collector, fixture, now, update_id, bid):
    for symbol in fixture.SYMBOLS:
        collector.handle_message(
            {
                "s": symbol,
                "u": update_id,
                "b": str(bid),
                "a": str(bid + 0.02),
                "B": "1000",
                "A": "1000",
            },
            now,
        )


def closed_minute(collector, fixture, opened, index, *, pressure=False, last_funding=False):
    for symbol in fixture.SYMBOLS:
        row = fixture.minute(symbol, opened, index)
        if pressure or last_funding:
            row.update(
                open=100 if last_funding else 98,
                high=100.03 if last_funding else 98.03,
                low=97.98,
                close=98,
                volume=100000,
                quote_volume=0.1,
                taker_buy_base=50000,
                taker_buy_quote=0.05,
            )
        raw = {
            "s": symbol,
            "t": opened,
            "T": opened + MINUTE_MS - 1,
            "i": "1m",
            "x": True,
            "n": 100,
            **{
                dest: str(row[src])
                for dest, src in (
                    ("o", "open"),
                    ("h", "high"),
                    ("l", "low"),
                    ("c", "close"),
                    ("v", "volume"),
                    ("q", "quote_volume"),
                    ("V", "taker_buy_base"),
                    ("Q", "taker_buy_quote"),
                )
            },
        }
        collector.handle_message(
            {"e": "kline", "E": opened + MINUTE_MS + 100, "s": symbol, "k": raw},
            opened + MINUTE_MS + 100,
        )


def account_states(engine):
    return {
        scenario: {
            "account": copy.deepcopy(engine.state["accounts"][scenario]),
            "controls": copy.deepcopy(engine.state["account_controls"][scenario]),
        }
        for scenario in SCENARIOS
    }


def fills_by_account(engine):
    return {
        scenario: {
            symbol: engine.db.execute(
                "SELECT COUNT(*) FROM records WHERE kind='fill' "
                "AND json_extract(payload,'$.scenario')=? "
                "AND json_extract(payload,'$.symbol')=? AND json_extract(payload,'$.side')='buy'",
                (scenario, symbol),
            ).fetchone()[0]
            for symbol in ("BTCUSDT", "ETHUSDT")
        }
        for scenario in SCENARIOS
    }


def checkpoint_sizes(engine, after):
    peak_encoded = peak_decoded = count = 0
    for row in engine.db.execute(
        "SELECT * FROM records WHERE kind='checkpoint' AND seq>?", (after,)
    ):
        expanded = engine.decode_financial_checkpoint(row)
        decoded_bytes = json.dumps(
            expanded, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
        ).encode()
        count += 1
        peak_encoded = max(peak_encoded, len(row["payload"].encode()))
        peak_decoded = max(peak_decoded, len(decoded_bytes))
    return {
        "records": count,
        "encoded_peak_bytes": peak_encoded,
        "decoded_peak_bytes": peak_decoded,
    }


def pages(collector, engine):
    return {
        "source": collector.db.execute("PRAGMA page_count").fetchone()[0],
        "journal": engine.db.execute("PRAGMA page_count").fetchone()[0],
        "page_size": engine.db.execute("PRAGMA page_size").fetchone()[0],
    }


def measure(folder, document):
    fixture = fixture_module()
    begin = fixture.END - HOUR_MS
    source, journal = folder / "source.sqlite3", folder / "journal.sqlite3"
    seed = Collector(source, initial_disk=document["baseline_disk"])
    try:
        for symbol in fixture.SYMBOLS:

            def rows(symbol=symbol):
                for index in range(32 * 1440):
                    opened = begin - 32 * DAY_MS + index * MINUTE_MS
                    price = str(100 + 0.05 * math.sin(index / 1440))
                    yield (
                        symbol,
                        opened,
                        opened + MINUTE_MS - 1,
                        price,
                        price,
                        price,
                        price,
                        "100000",
                        "10000000",
                        100,
                        opened + MINUTE_MS,
                        opened + MINUTE_MS + 100,
                        "websocket",
                        opened + MINUTE_MS + 100,
                        1,
                    )

            seed.db.executemany(
                "INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", rows()
            )
        seed.db.commit()
    finally:
        seed.close()
    document["synthetic_input_lineage"] = {
        "risk_warmup_minutes_per_symbol": 32 * 1440,
        "historical_feature_hours": 100,
        "risk_warmup_source_sha256": digest(source),
        "risk_ohlc_formula": "100 + 0.05 * sin(index / 1440)",
        "risk_source_labels": "websocket labels in explicit engineering_simulation fixture only",
        "reused_existing_source": False,
        "old_source_rows_or_contract_rewritten": False,
        "account_cash_positions_or_holding_clocks_directly_modified": False,
        "funding_seconds": 3600,
        "pressure_seconds": 360,
        "funding_bid": 100,
        "bid_from_funding_second_3595": 98,
        "last_funding_minute_and_all_pressure_minutes_quote_volume": 0.1,
    }
    engine = collector = None
    try:
        engine = CandidatePaperEngine(
            source,
            journal,
            predictor=fixture.StubPredictor(),
            decision_policy="A",
            config=ShadowConfig(mode="engineering_simulation"),
            started_ms=begin - 500,
            initial_disk=document["baseline_disk"],
        )
        fixture.seed_features(engine, hours=100)
        collector = CandidateCollector(
            source, candidate=engine, initial_disk=document["baseline_disk"]
        )
        collector.health_snapshot = lambda at: {
            **fixture.health(at),
            "connected": True,
            "live_session": True,
            "qualification": {"qualified_72h": True},
        }
        quote(collector, fixture, begin + 100, 1, 100)
        engine.process_tick(
            begin + 200,
            fixture.health(begin + 200),
            [Quote(s, 100, 100.02, begin + 200, 1) for s in fixture.SYMBOLS],
        )
        for second in range(1, 3601):
            now = begin + second * 1000 + 200
            if second % 60 == 0:
                closed_minute(
                    collector,
                    fixture,
                    now - 200 - MINUTE_MS,
                    6000 + second // 60,
                    last_funding=second == 3600,
                )
            quote(collector, fixture, now, second + 1, 98 if second >= 3595 else 100)
            if second % 900 == 0:
                print(
                    json.dumps(
                        {"funding_seconds": second, "initial_buy_fills": fills_by_account(engine)}
                    ),
                    flush=True,
                )
        probe = document["probe"] = {
            "stage": "ACTUAL_FUNDED_PRESSURE_STARTED",
            "mode": "engineering_simulation",
            "qualification_days": 0,
            "synthetic_seconds": 360,
            "order_window_seconds": 300,
            "initial_accounts": account_states(engine),
            "initial_buy_fills": fills_by_account(engine),
            "initial_checkpoint_sizes": checkpoint_sizes(engine, 0),
            "database_paths": {"source": str(source), "journal": str(journal)},
        }
        if not all(
            value > 0 for counts in probe["initial_buy_fills"].values() for value in counts.values()
        ):
            raise RuntimeError("Funding trajectory did not fill both assets in all four accounts")
        if not all(
            row["account"]["positions"][symbol] > 0
            for row in probe["initial_accounts"].values()
            for symbol in fixture.SYMBOLS
        ):
            raise RuntimeError("Funding trajectory did not preserve actual held positions")
        before = engine.seq
        # Closed backup snapshots give exact initial committed file sizes without
        # restarting the active accounts or cancelling the measured pending orders.
        collector.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        engine.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        baseline = folder / "initial-closed-snapshot"
        baseline.mkdir()
        for name, reader in (("source.sqlite3", collector.db), ("journal.sqlite3", engine.db)):
            with closing(sqlite3.connect(baseline / name)) as writer:
                reader.backup(writer)
        probe["initial_closed_snapshot_files"] = sizes(baseline)
        probe["initial_closed_snapshot_sha256"] = {
            name: digest(baseline / name) for name in sizes(baseline)
        }
        probe["initial_live_files"] = sizes(folder)
        probe["initial_page_count"] = pages(collector, engine)
        pressure_begin = begin + HOUR_MS
        samples = []
        for second in range(1, 361):
            now = pressure_begin + second * 1000 + 200
            if second % 60 == 0:
                closed_minute(
                    collector, fixture, now - 200 - MINUTE_MS, 6060 + second // 60, pressure=True
                )
            quote(collector, fixture, now, second + 3601, 98)
            if second % 60 == 0:
                samples.append(
                    {"pressure_second": second, "files": sizes(folder), "records": engine.seq}
                )
        probe.update(
            final_accounts=account_states(engine),
            final_buy_fills=fills_by_account(engine),
            checkpoint_sizes=checkpoint_sizes(engine, before),
            final_page_count=pages(collector, engine),
            samples=samples,
            categories=[
                dict(row)
                for row in engine.db.execute(
                    "SELECT kind,COUNT(*) records,SUM(LENGTH(CAST(payload AS BLOB))) payload_bytes,"
                    "MAX(LENGTH(CAST(payload AS BLOB))) peak_payload_bytes "
                    "FROM records WHERE seq>? GROUP BY kind",
                    (before,),
                )
            ],
            attempts=engine.db.execute(
                "SELECT COUNT(*) FROM records WHERE seq>? AND kind='order_event' "
                "AND json_extract(payload,'$.status')='CAPACITY_OR_RISK'",
                (before,),
            ).fetchone()[0],
            order_status_counts=dict(
                engine.db.execute(
                    "SELECT json_extract(payload,'$.status'),COUNT(*) FROM records "
                    "WHERE seq>? AND kind='order_event' GROUP BY json_extract(payload,'$.status')",
                    (before,),
                )
            ),
            records_before_pressure=before,
            records_final=engine.seq,
            head_hash=engine.head,
            actual_qualification_days=engine.status()["actual_qualification_days"],
        )
        if probe["attempts"] < 1800:
            raise RuntimeError("Funded pressure window did not exercise 1800 capacity attempts")
        if probe["actual_qualification_days"] != 0:
            raise RuntimeError("Engineering trajectory must not create real qualification")
    finally:
        if engine is not None:
            document.setdefault("probe", {}).update(
                last_available_accounts=account_states(engine),
                last_available_buy_fills=fills_by_account(engine),
            )
        if collector is not None:
            collector.close()
        if engine is not None:
            engine.close()
        document["final_closed_files"] = sizes(folder)
    probe["final_closed_files"] = sizes(folder)
    database_names = ("source.sqlite3", "journal.sqlite3")
    probe["database_increment_bytes"] = sum(
        probe["final_closed_files"][name] - probe["initial_closed_snapshot_files"][name]
        for name in database_names
    )
    probe["all_file_increment_bytes"] = sum(probe["final_closed_files"].values()) - sum(
        probe["initial_live_files"].values()
    )
    probe["increment_bytes"] = max(
        0, probe["database_increment_bytes"], probe["all_file_increment_bytes"]
    )
    probe["final_database_sha256"] = {name: digest(folder / name) for name in database_names}
    evidence = read_forward_evidence(journal, include_records=False)
    probe["readonly_chain_verified"] = (
        evidence["seq"] == probe["records_final"] and evidence["head_hash"] == probe["head_hash"]
    )
    if not probe["readonly_chain_verified"]:
        raise RuntimeError("Immutable journal chain differs from actual measured final state")
    probe["stage"] = "FINITE_ENGINEERING_TRAJECTORY_COMPLETED"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-receipt", type=Path, required=True)
    args = parser.parse_args()
    folder, output, tests = (
        value.resolve() for value in (args.directory, args.output, args.test_receipt)
    )
    if (
        not folder.is_relative_to(STATE.resolve())
        or not folder.name.startswith("a03-funded-")
        or folder.exists()
        or output.exists()
        or not output.is_relative_to((ROOT / "reports").resolve())
        or not tests.is_relative_to((ROOT / "reports").resolve())
    ):
        raise ValueError("Fresh native engineering folder and exclusive D report required")
    suites = ET.parse(tests).getroot().findall(".//testsuite")
    test_count = sum(int(row.attrib["tests"]) for row in suites)
    if sum(int(row.attrib["tests"]) for row in suites) < 76 or any(
        int(row.attrib.get(key, 0)) for row in suites for key in ("errors", "failures", "skipped")
    ):
        raise RuntimeError("Actual complete passing regression receipt required")
    paths = (
        Path(__file__),
        ROOT / "tests/test_candidate_adapter.py",
        ROOT / "tests/test_candidate_paper.py",
        ROOT / "tests/test_candidate_storage.py",
        ROOT / "src/quant/candidate_paper.py",
        ROOT / "src/quant/candidate_strategy.py",
        ROOT / "src/quant/candidate_storage.py",
    )
    before = {str(path.relative_to(ROOT)): digest(path) for path in paths}
    runtime = runtime_snapshot()
    started = time.monotonic()
    document = {
        "status": "FUNDED_CONGESTION_ENGINEERING_DIAGNOSTIC_ONLY",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "source_hashes": before,
        "native_runtime_snapshot": runtime,
        "test_receipt": {"path": str(tests), "sha256": digest(tests), "tests": test_count},
        "resources_before": status(),
        "baseline_disk": disk.check(reserve=100_000_000),
        "capacity_accepted": False,
        "production_authorized": False,
        "training_fits": 0,
        "network_requests": 0,
        "actual_qualification_days": 0,
        "limits": "Finite synthetic input path; no 180d storage or alpha qualification",
    }
    folder.mkdir()
    failure = None
    try:
        measure(folder, document)
        if (
            before != {str(path.relative_to(ROOT)): digest(path) for path in paths}
            or runtime != runtime_snapshot()
            or digest(tests) != document["test_receipt"]["sha256"]
        ):
            raise RuntimeError("Bound implementation or test receipt changed during measurement")
    except Exception as error:
        failure = error
        document.update(
            status="FUNDED_CONGESTION_FIXTURE_FAILED_NOT_ACCEPTED",
            error_type=type(error).__name__,
            error=str(error),
        )
    document.update(
        elapsed_seconds=time.monotonic() - started,
        resources_after=status(),
        process_max_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
    )
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(document, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "status": document["status"],
                "probe": document.get("probe"),
                "elapsed_seconds": document["elapsed_seconds"],
            }
        )
    )
    if failure is not None:
        raise failure


if __name__ == "__main__":
    main()
