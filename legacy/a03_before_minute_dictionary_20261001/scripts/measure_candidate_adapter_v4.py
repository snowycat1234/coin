"""Measure candidate storage with paired startup quotes and separate stage receipts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import resource
import sqlite3
import sys
import time
from pathlib import Path

from quant import disk
from quant.candidate_paper import CandidateCollector, CandidatePaperEngine
from quant.collector import Collector
from quant.paths import ROOT, STATE, VHD
from quant.shadow import DAY_MS, HOUR_MS, MINUTE_MS, ShadowConfig, read_forward_evidence


def load_fixture():
    spec = importlib.util.spec_from_file_location(
        "candidate_adapter_engineering_fixture", ROOT / "tests/test_candidate_adapter.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sizes(folder):
    return {p.name: p.stat().st_size for p in folder.iterdir() if p.is_file()}


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as reader:
        for block in iter(lambda: reader.read(1_048_576), b""):
            sha.update(block)
    return sha.hexdigest()


def attempt_probe(fixture, main_source, folder, ledger):
    """Actual five-minute low-capacity attempts, preserving parent order semantics."""
    folder.mkdir()
    source, journal = folder / "source.sqlite3", folder / "journal.sqlite3"
    with sqlite3.connect(main_source) as reader, sqlite3.connect(source) as writer:
        reader.backup(writer)
        writer.execute("DELETE FROM closed_bars WHERE open_ms>=?", (fixture.END,))
        writer.execute("DELETE FROM quote_minutes")
        writer.commit()
    engine = CandidatePaperEngine(
        source,
        journal,
        predictor=fixture.StubPredictor(),
        decision_policy="A",
        config=ShadowConfig(mode="engineering_simulation"),
        started_ms=fixture.END - HOUR_MS - 500,
        initial_disk=ledger,
    )
    fixture.seed_features(engine)
    fixture.finish_hour(engine)
    collector = CandidateCollector(source, candidate=engine, initial_disk=ledger)
    collector.health_snapshot = lambda at: {
        **fixture.health(at),
        "connected": True,
        "live_session": True,
        "qualification": {"qualified_72h": True},
    }
    begin = fixture.END
    # Populate the collector's own paired quote cache before opening orders.
    # A direct engine quote does not populate Collector._latest_quotes; without
    # this input the first BTC notification sees no ETH quote and correctly
    # cancels every order for health instead of exercising capacity attempts.
    for symbol in fixture.SYMBOLS:
        collector.handle_message(
            {"s": symbol, "u": 1, "b": "100", "a": "100.02",
             "B": "1000", "A": "1000"},
            begin + 100,
        )
    engine.process_tick(
        begin + 200,
        fixture.health(begin + 200),
        [fixture.Quote(s, 100, 100.02, begin + 200, 1) for s in fixture.SYMBOLS],
    )
    collector.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    engine.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    seed_sizes = sizes(folder)
    seed_pages = {
        "source": collector.db.execute("PRAGMA page_count").fetchone()[0],
        "journal": engine.db.execute("PRAGMA page_count").fetchone()[0],
    }
    try:
        before = engine.seq
        for second in range(1, 361):
            now = begin + second * 1000 + 200
            if second % 60 == 0:
                for symbol in fixture.SYMBOLS:
                    raw = {
                        "s": symbol,
                        "t": now - 200 - MINUTE_MS,
                        "T": now - 201,
                        "i": "1m",
                        "x": True,
                        "n": 1,
                        "o": "100",
                        "h": "101",
                        "l": "99",
                        "c": "100",
                        "v": "100000",
                        "q": "0.1",
                        "V": "50000",
                        "Q": "0.05",
                    }
                    collector.handle_message(
                        {"e": "kline", "E": now - 100, "s": symbol, "k": raw}, now - 100
                    )
            for symbol in fixture.SYMBOLS:
                collector.handle_message(
                    {
                        "s": symbol,
                        "u": second + 1,
                        "b": "100",
                        "a": "100.02",
                        "B": "1000",
                        "A": "1000",
                    },
                    now,
                )
        result = {
            "synthetic_seconds": 360,
            "mode": "engineering_simulation",
            "qualification_days": 0,
            "categories": [
                dict(row)
                for row in engine.db.execute(
                    "SELECT kind,COUNT(*) records,"
                    "MAX(LENGTH(CAST(payload AS BLOB))) peak_payload_bytes "
                    "FROM records WHERE seq>? GROUP BY kind",
                    (before,),
                )
            ],
            "attempts": engine.db.execute(
                "SELECT COUNT(*) FROM records WHERE seq>? AND "
                "kind='order_event' AND json_extract(payload,'$.status')='CAPACITY_OR_RISK'",
                (before,),
            ).fetchone()[0],
            "files_before_close": sizes(folder),
            "order_window_seconds": 300,
            "seed_files": seed_sizes,
            "seed_page_count": seed_pages,
            "final_page_count": {
                "source": collector.db.execute("PRAGMA page_count").fetchone()[0],
                "journal": engine.db.execute("PRAGMA page_count").fetchone()[0],
            },
            "database_paths": {"source": str(source), "journal": str(journal)},
        }
        assert result["attempts"] >= 1800, result
    finally:
        collector.close()
        engine.close()
    result["files_after_close"] = sizes(folder)
    result["increment_bytes"] = max(
        0, sum(result["files_after_close"].values()) - sum(seed_sizes.values())
    )
    return result


def runtime_snapshot():
    module_path = Path(sys.modules[CandidatePaperEngine.__module__].__file__).resolve()
    if module_path.parent == (ROOT / "src/quant").resolve():
        return None
    runtime_root = module_path.parent.parent
    if not runtime_root.is_relative_to((STATE / "candidate-runtime").resolve()):
        raise RuntimeError("Unexpected engineering runtime source location")
    path = runtime_root / "SOURCE_MANIFEST.json"
    if path.stat().st_size > 100_000:
        raise RuntimeError("Oversize native source manifest")
    document = json.loads(path.read_text())
    if document["runtime_root"] != str(runtime_root) or not document["no_live_admission"]:
        raise RuntimeError("Native runtime identity differs")
    for name, expected in document["files"].items():
        if Path(name).name != name or Path(name).suffix != ".py":
            raise RuntimeError("Invalid source manifest member")
        if any(digest(root / name) != expected for root in
               (ROOT / "src/quant", runtime_root / "quant")):
            raise RuntimeError("Runtime copy is not the exact current source bytes")
    return {"path": str(path), "sha256": digest(path),
            "release_sha256": document["release_sha256"],
            "source_bytes": document["source_bytes"], "verified_files": len(document["files"])}


def measure(folder: Path, output: Path, test_receipt: Path):
    if folder.exists() or output.exists():
        raise RuntimeError("New measurement paths required; never overwrite evidence")
    if not folder.resolve().is_relative_to(STATE.resolve()):
        raise RuntimeError("Use independent native D-hosted STATE")
    if not output.resolve().is_relative_to((ROOT / "reports").resolve()):
        raise RuntimeError("New report must be inside D-hosted ROOT/reports")
    bound_sources = (
        ROOT / "src/quant/candidate_paper.py",
        ROOT / "src/quant/candidate_strategy.py",
        ROOT / "src/quant/candidate_storage.py",
        ROOT / "tests/test_candidate_adapter.py",
        ROOT / "tests/test_candidate_paper.py",
        ROOT / "tests/test_candidate_storage.py",
        Path(__file__),
    )
    start_source_sha = {str(path.relative_to(ROOT)): digest(path) for path in bound_sources}
    start_runtime = runtime_snapshot()
    test_receipt = test_receipt.resolve()
    if not test_receipt.is_relative_to((ROOT / "reports").resolve()):
        raise RuntimeError("Actual test receipt must remain in D reports")
    test_sha = digest(test_receipt)
    ledger = disk.check(reserve=1_000_000_000)
    folder.mkdir(parents=True)
    fixture = load_fixture()
    started = time.monotonic()
    vhd_start = VHD.stat().st_size
    source, journal = folder / "source.sqlite3", folder / "journal.sqlite3"
    collector = Collector(source, initial_disk=ledger)
    begin = fixture.END
    # All historical warmup is explicitly synthetic. No current-time network or
    # future production credential exists. Received timestamps gate every query.
    for symbol in fixture.SYMBOLS:

        def warm_rows(symbol=symbol):
            for opened in range(begin - 32 * DAY_MS, begin, MINUTE_MS):
                index = (opened - (begin - 32 * DAY_MS)) // MINUTE_MS
                price = str(100 + 0.05 * fixture.math.sin(index / 1440))
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

        collector.db.executemany(
            "INSERT INTO closed_bars VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", warm_rows()
        )
    collector.db.commit()
    collector.close()
    engine = CandidatePaperEngine(
        source,
        journal,
        predictor=fixture.StubPredictor(),
        decision_policy="A",
        config=ShadowConfig(mode="engineering_simulation"),
        started_ms=begin - HOUR_MS - 500,
        initial_disk=ledger,
    )
    fixture.seed_features(engine)
    # Complete the 100th hour through the original received closed-WS ingestion.
    fixture.finish_hour(engine)
    collector = CandidateCollector(source, candidate=engine, initial_disk=ledger)
    collector.health_snapshot = lambda at: {
        **fixture.health(at),
        "connected": True,
        "live_session": True,
        "qualification": {"qualified_72h": True},
    }
    for symbol in fixture.SYMBOLS:
        collector.handle_message(
            {"s": symbol, "u": 1, "b": "100", "a": "100.02",
             "B": "1000", "A": "1000"},
            begin + 100,
        )
    engine.process_tick(
        begin + 200,
        fixture.health(begin + 200),
        [fixture.Quote(s, 100, 100.02, begin + 200, 1) for s in fixture.SYMBOLS],
    )
    collector.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    engine.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    seed_sizes = sizes(folder)
    samples, vhd_peak, peak_bytes = [], VHD.stat().st_size, sum(seed_sizes.values())
    try:
        for second in range(1, 86401):
            now = begin + second * 1000 + 200
            if second % 60 == 0:
                for symbol in fixture.SYMBOLS:
                    row = fixture.minute(symbol, now - 200 - MINUTE_MS, 6000 + second // 60)
                    raw = {
                        "s": symbol,
                        "t": now - 200 - MINUTE_MS,
                        "T": now - 201,
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
                        {"e": "kline", "E": now - 100, "s": symbol, "k": raw}, now - 100
                    )
            for symbol in fixture.SYMBOLS:
                collector.handle_message(
                    {
                        "s": symbol,
                        "u": second + 1,
                        "b": "100",
                        "a": "100.02",
                        "B": "1000",
                        "A": "1000",
                    },
                    now,
                )
            if second % 60 == 0:
                measured = sizes(folder)
                total = sum(measured.values())
                peak_bytes = max(peak_bytes, total)
                vhd_peak = max(vhd_peak, VHD.stat().st_size)
                if second % 3600 == 0:
                    samples.append(
                        {
                            "synthetic_hour": second // 3600,
                            "files": measured,
                            "total_bytes": total,
                            "records": engine.seq,
                        }
                    )
                    print(
                        json.dumps(
                            {
                                "synthetic_hour": second // 3600,
                                "bytes": total,
                                "elapsed_seconds": round(time.monotonic() - started, 2),
                            }
                        ),
                        flush=True,
                    )
        # Both UTC partial days are correctly marked; seal the terminal UTC day
        # boundary through the existing code without manufacturing calendar credit.
        collector.flush_quotes(begin + DAY_MS + 2200, partial=True)
        kinds = [
            dict(row)
            for row in engine.db.execute(
                "SELECT kind,COUNT(*) records,SUM(LENGTH(CAST(payload AS BLOB))) payload_bytes,"
                "MAX(LENGTH(CAST(payload AS BLOB))) peak_payload_bytes FROM records GROUP BY kind"
            )
        ]
        accounts = fixture.copy.deepcopy(engine.state["accounts"])
        scenario_fills = {
            s: engine.db.execute(
                "SELECT COUNT(*) FROM records WHERE kind='fill' "
                "AND json_extract(payload,'$.scenario')=?",
                (s,),
            ).fetchone()[0]
            for s in fixture.SCENARIOS
        }
        source_counts = {
            table: collector.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("closed_bars", "quote_minutes", "events", "sessions")
        }
        source_pages = {
            key: collector.db.execute(f"PRAGMA {key}").fetchone()[0]
            for key in ("page_count", "page_size", "freelist_count")
        }
        journal_pages = {
            key: engine.db.execute(f"PRAGMA {key}").fetchone()[0]
            for key in ("page_count", "page_size", "freelist_count")
        }
        head, seq = engine.head, engine.seq
        preclose = sizes(folder)
    finally:
        collector.close()
        engine.close()
    final_sizes = sizes(folder)
    # Recovery verifies the full hash chain in O(1) record memory, then uses a
    # joint feature anchor and minute tail. No financial/health replay is permitted.
    restored = CandidatePaperEngine(
        source,
        journal,
        predictor=fixture.StubPredictor(),
        decision_policy="A",
        config=ShadowConfig(mode="engineering_simulation"),
        initial_disk=ledger,
    )
    try:
        recovery_ok = restored.state["accounts"] == accounts and restored.seq == seq
        assert recovery_ok and restored.head == head
        assert restored.status()["actual_qualification_days"] == 0
        assert all(value > 0 for value in scenario_fills.values())
    finally:
        restored.close()
    # Preserve the completed normal path even if the separate congestion stage
    # fails. Never turn a failed short probe into full module acceptance.
    normal_output = output.with_name(output.stem + "_NORMAL_PATH.json")
    if ({str(path.relative_to(ROOT)): digest(path) for path in bound_sources}
            != start_source_sha or runtime_snapshot() != start_runtime
            or digest(test_receipt) != test_sha):
        raise RuntimeError("Sources/runtime/tests changed before normal stage receipt")
    normal_result = {
        "status": "COMPLETE_NORMAL_SYNTHETIC_PATH_ONLY",
        "synthetic_seconds": 86400, "quote_event_count": 172800,
        "paired_closed_minutes": 1440, "recovery_exact": recovery_ok,
        "account_fill_counts": scenario_fills, "audit_head": head, "record_count": seq,
        "source_sha256": start_source_sha, "native_runtime_snapshot": start_runtime,
        "test_receipt_sha256": test_sha, "seed_files": seed_sizes,
        "final_files": final_sizes, "hour_samples": samples,
        "database_paths": {"source": str(source), "journal": str(journal)},
        "file_sha256": {name: digest(folder / name) for name in final_sizes
                        if name.endswith("sqlite3")},
        "actual_qualification_days": 0, "capacity_accepted": False,
        "production_authorized": False,
    }
    with normal_output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(normal_result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"normal_stage": str(normal_output), "recovery_exact": recovery_ok}),
          flush=True)
    try:
        probe = attempt_probe(fixture, source, folder / "attempt_probe", ledger)
    except Exception as exc:
        failure_output = output.with_name(output.stem + "_FAILED.json")
        failure = {
            "status": "CONGESTION_STAGE_FAILED_NOT_ACCEPTED",
            "error_type": type(exc).__name__,
            "failure": exc.args[0] if isinstance(exc, AssertionError) else str(exc),
            "normal_stage": {"path": str(normal_output.relative_to(ROOT)),
                             "sha256": digest(normal_output)},
            "source_sha256": start_source_sha, "actual_qualification_days": 0,
            "capacity_accepted": False, "production_authorized": False,
        }
        with failure_output.open("x", encoding="utf-8") as writer:
            writer.write(json.dumps(failure, indent=2, allow_nan=False) + "\n")
        raise
    # read_forward_evidence is intentionally bounded to this one-day engineering
    # fixture; it is not used to materialize an unbounded 180-day journal here.
    evidence = read_forward_evidence(journal)
    assert evidence["head_hash"] == head
    increment = max(0, sum(final_sizes.values()) - sum(seed_sizes.values()))
    peak_payload = {row["kind"]: row["peak_payload_bytes"] for row in kinds}
    for row in probe["categories"]:
        peak_payload[row["kind"]] = max(peak_payload.get(row["kind"], 0), row["peak_payload_bytes"])

    def row_bound(kind):
        # Payload plus two SHA strings, seq/time/key/version/index/tree overhead,
        # whole pages, and a 2x page/index margin. This is intentionally coarse.
        return 2 * ((peak_payload.get(kind, 0) + 2048 + 4095) // 4096) * 4096

    maximum_counts = {
        "checkpoint": 8640 + 2880 + 24 + 49,
        "order_event": (24 * 300 + 2880 + 24) * 8 + 192,
        "heartbeat": 5760,
        "feature_minute": 2880,
        "feature": 48,
        "feature_provider_snapshot": 48,
        "decision": 96,
        "order": 192,
        "fill": (24 * 300 + 2880 + 24) * 8,
        "position": (24 * 300 + 2880 + 24) * 8,
        "round_trip": 24 * 8,
        "nav": 4,
    }
    # A continuously healthy hourly account has at most 300 eligible one-second
    # quote ticks per goal/hour, plus regular minute/hour/day checkpoints.
    healthy_daily_bound = sum(row_bound(kind) * count for kind, count in maximum_counts.items())
    # Healthy/frozen transitions could occur every second and are not rate-limited
    # here. Show that separate stress rather than promise a 180d bound for all faults.
    health_flap_daily_bound = healthy_daily_bound + (86400 + 2880 + 24) * (
        row_bound("checkpoint") + row_bound("incident")
    )
    end_ledger = disk.check(reserve=0)
    micro = ROOT / "data/microstructure_v1"
    current_micro_features = (
        disk.tree_bytes(micro / "features") if (micro / "features").exists() else 0
    )
    current_micro_raw = disk.tree_bytes(micro / "raw") if (micro / "raw").exists() else 0
    micro_remaining = max(0, 8_000_000_000 - current_micro_features) + max(
        0, 4_000_000_000 - current_micro_raw
    )
    # Actual probe counts may expose only 6 active orders if B2 is flat. Scale to
    # all 8 active goals without reducing the parent execution attempt frequency.
    active_probe_scale = max(1.0, 2400 / probe["attempts"])
    # A failed-entry probe can have emptier accounts than a funded account.
    # Scale the entire measured congestion increment by the richer observed
    # checkpoint payload before applying the additional forecast margin.
    probe_checkpoint_peak = max(
        row["peak_payload_bytes"]
        for row in probe["categories"]
        if row["kind"] == "checkpoint"
    )
    active_payload_scale = max(1.0, peak_payload["checkpoint"] / probe_checkpoint_peak)
    active_daily_increment = increment + math.ceil(
        24 * probe["increment_bytes"] * active_probe_scale * active_payload_scale
    )
    active_180d_with_margin = math.ceil(180 * active_daily_increment * 1.25)
    nominal_180d_with_margin = 360 * increment
    reserves = {
        "A07_feature_and_raw_remaining": micro_remaining,
        "public_v3_180d_growth_reserve": 2_000_000_000,
        "A07_native_audit_180d_growth_reserve": 1_000_000_000,
    }
    joint_nominal = end_ledger["total_bytes"] + sum(reserves.values()) + nominal_180d_with_margin
    joint_active = end_ledger["total_bytes"] + sum(reserves.values()) + active_180d_with_margin
    end_source_sha = {str(path.relative_to(ROOT)): digest(path) for path in bound_sources}
    if end_source_sha != start_source_sha:
        raise RuntimeError("Measurement sources changed while executing; refuse result")
    if runtime_snapshot() != start_runtime or digest(test_receipt) != test_sha:
        raise RuntimeError("Runtime snapshot or actual tests changed while executing")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "ENGINEERING_MEASUREMENT_ONLY",
        "normal_stage": {"path": str(normal_output.relative_to(ROOT)),
                         "sha256": digest(normal_output)},
        "source": "synthetic",
        "primary_final_native_bytes": sum(final_sizes.values()),
        "probe_final_native_bytes": sum(probe["files_after_close"].values()),
        "combined_final_native_bytes": sum(final_sizes.values())
        + sum(probe["files_after_close"].values()),
        "no_fits": True,
        "no_network": True,
        "alpha_authorized": False,
        "actual_qualification_days": 0,
        "actual_24h_live_capacity_certified": False,
        "synthetic_seconds": 86400,
        "quote_event_count": 172800,
        "quote_tick_rate_hz": 1,
        "paired_closed_minutes": 1440,
        "model": "explicit StubPredictor constant .01 engineering oracle; not native alpha",
        "native_model_wiring_evidence": {
            "path": str(test_receipt.relative_to(ROOT)), "sha256": test_sha,
        },
        "native_runtime_snapshot": start_runtime,
        "initial_feature_hours": 100,
        "initial_risk_source_days": 32,
        "account_fill_counts": scenario_fills,
        "accounts": accounts,
        "journal_categories": kinds,
        "source_counts": source_counts,
        "source_pages": source_pages,
        "journal_pages": journal_pages,
        "seed_files": seed_sizes,
        "preclose_files": preclose,
        "final_files": final_sizes,
        "sampled_peak_native_file_bytes": peak_bytes,
        "peak_sampling_seconds": 60,
        "hour_samples": samples,
        "actual_24h_increment_bytes": increment,
        "projected_180d_increment_bytes": 180 * increment,
        "nominal_180d_bytes_with_2x_margin_and_seed": sum(seed_sizes.values()) + 360 * increment,
        "low_capacity_probe": probe,
        "maximum_observed_payload_bytes": peak_payload,
        "healthy_hourly_daily_record_count_bounds": maximum_counts,
        "coarse_healthy_hourly_daily_journal_bound_bytes": healthy_daily_bound,
        "coarse_healthy_hourly_180d_journal_bound_bytes": 180 * healthy_daily_bound,
        "sustained_low_capacity_daily_increment_bytes": active_daily_increment,
        "sustained_low_capacity_active_order_scale": active_probe_scale,
        "sustained_low_capacity_observed_checkpoint_payload_scale": active_payload_scale,
        "sustained_low_capacity_180d_growth_with_25pct_margin": active_180d_with_margin,
        "final_disk_snapshot": end_ledger,
        "joint_budget_reserves_bytes": reserves,
        "joint_nominal_180d_projected_total_bytes": joint_nominal,
        "joint_sustained_low_capacity_180d_projected_total_bytes": joint_active,
        "joint_nominal_below_36GB_intake": joint_nominal < 36_000_000_000,
        "joint_sustained_low_capacity_below_36GB_intake": joint_active < 36_000_000_000,
        "budget_limit_bytes": {
            "intake": 36_000_000_000,
            "hard": 40_000_000_000,
            "emergency_spare": 4_000_000_000,
        },
        "budget_reserve_scope": "existing D+full VHD includes both primary/probe fixtures; "
        "add future growth only, no second addition of native seed/file sizes. "
        "A07 reserves cover remaining 8GB features/4GB raw limits, plus 1GB native audit. "
        "Public 2GB reserve uses root metadata: 548864B DB+1071232B WAL in ~7.4h; "
        "not actual 24h certification. Sustained hourly congestion adds measured six-minute "
        "growth 24x/day over nominal, scales to eight active goals and adds 25% margin. "
        "It is a finite diagnostic forecast, not a guarantee under arbitrary health flapping.",
        "health_flap_daily_journal_bound_bytes": health_flap_daily_bound,
        "health_flap_180d_journal_bound_bytes": 180 * health_flap_daily_bound,
        "production_180d_storage_authorized": False,
        "projection_scope": "nominal 2x diagnostic is not a worst-case guarantee. "
        "Coarse bounds include full checkpoint/attempt/page/index allowance; "
        "do not generalize hourly count bounds to legacy15m. Source/audit/other "
        "collectors and 4GB spare must be included in any later storage admission. "
        "The existing disk guard stops intake at quota; generic STOP_v2 still denies production.",
        "global_vhd_start_bytes": vhd_start,
        "global_vhd_end_bytes": VHD.stat().st_size,
        "global_vhd_sampled_peak_bytes": vhd_peak,
        "vhd_attribution": "shared live writers; global delta not attributable to this fixture; "
        "native file bytes lie inside VHD and must not be added to VHD occupancy twice",
        "baseline_disk_snapshot": ledger,
        "max_process_rss_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "elapsed_seconds": time.monotonic() - started,
        "recovery_exact": recovery_ok,
        "audit_head": head,
        "record_count": seq,
        "database_paths": {"source": str(source), "journal": str(journal)},
        "source_sha256": start_source_sha,
        "file_sha256": {
            name: digest(folder / name) for name in final_sizes if name.endswith("sqlite3")
        },
    }
    with output.open("x", encoding="utf-8") as writer:
        writer.write(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(
        json.dumps(
            {
                "report": str(output),
                "growth": increment,
                "elapsed_seconds": report["elapsed_seconds"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--test-receipt", type=Path,
                        default=ROOT / "reports/A03_CANDIDATE_FINAL_TESTS.xml")
    args = parser.parse_args()
    measure(args.directory, args.output, args.test_receipt)
