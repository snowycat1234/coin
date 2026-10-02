"""Bind exactly38 sealed Spot minute files; no price rows or fresh QA are read."""
from __future__ import annotations
import argparse, calendar, hashlib, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, date, datetime
from pathlib import Path

ROOT = Path("/mnt/d/codex/coin")
STATE = Path("/home/xflops/coin-state")
NOTE = ROOT / "reports/fast_research/PUBLIC_LONG_DEVELOPMENT_STATIC_REUSE_20261003_V1.json"
NOTE_SHA = "1550f73785c45155589b0df796bdd1a69717c7bccd6c5f280306d0cda6eeabaf"
SCOPE = "DEC2023_JUN2025"
MONTHS = ("2023-12",) + tuple(f"2024-{m:02d}" for m in range(1, 13)) + tuple(f"2025-{m:02d}" for m in range(1, 7))
SYMBOLS = ("BTCUSDT", "ETHUSDT")
PINS = {
    "state/dataset_lock.json": "29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d",
    "reports/generated/DATA_QUALITY_REPORT.json": "27aa56b33b12c1e6085230318bef6bd41cb3d95b23ca8714a35fc9a5b62125cf",
    "configs/dataset_policy.json": "3e1adcfbed86d0cc2414d37934126dcc2ddcdfcbe52b4e74ec58ff3447a7d880",
    "environments/v8/uv.lock": "97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6",
    "reports/fast_research/PUBLIC_LONG_DEVELOPMENT_STATIC_REUSE_20261003_V1.json": NOTE_SHA,
}
SUPPORT_PINS = {
    "scripts/research_v8/registry.py": "081f881f2cb1cdc84b8c098606e9f3235c92fcdd04c0120527bee0d8493068ab",
    "scripts/research_v8/funding_price_source_v2.py": "2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb",
    "scripts/research_v7/oracle_flow_ceiling.py": "959f63f40c3294b6b2b75267b9138202df79223a7e7723397cf06b8d45a1477e",
    "src/quant/paths.py": "3c3e43ddd9ef1f2a52f902869d29e9a0ac5f29f1b5e64362b873290d07f72282",
    "src/quant/disk.py": "4b4c80b309fcff83cc740e8c59ed0a8fcdd56121063a94d854126aa7518277b9",
    "src/quant/resources.py": "e8028c40240bfb0df05228247ad6fee734831a14b9c6ac40acbd0c291b1969a3",
}
STATUS = "PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR"
MAX_OWNED = 10_000_000
sys.path.insert(0, str(ROOT))


def need(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    with Path(path).open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return digest


def load(path):
    path = Path(path)
    need(path.is_file() and not path.is_symlink() and path.stat().st_size < 2_000_000,
         "Explicit bounded ordinary metadata required")
    return json.loads(path.read_text())


def write(path, value):
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def opened(day):
    return int(datetime.combine(day, datetime.min.time(), UTC).timestamp()) * 1_000_000


def metadata_rows(spec):
    need(spec["source_scope"] == SCOPE and tuple(spec["source_calendar"]) == MONTHS and
         tuple(spec["symbols"]) == SYMBOLS, "Only exact38-file source calendar")
    need(spec["warmup_start"] == "2023-12-01" and spec["period_start"] == "2024-01-01" and
         spec["period_end_exclusive"] == "2025-07-01" and spec["warmup_days"] == 31 and
         spec["research_days"] == 547 and spec["source_files"] == 38 and
         spec["days_per_symbol"] == 578 and spec["actual_minute_rows"] == 1_664_640,
         "Frozen source and scoring bounds; source metadata only")
    for relative, digest in PINS.items():
        need(sha(ROOT / relative) == digest and spec["frozen_sources"].get(relative) == digest,
             "Sealed metadata/environment changed: " + relative)
    need(sha(NOTE) == NOTE_SHA and spec["static_note_sha256"] == NOTE_SHA and
         spec["static_note_path"] == str(NOTE), "Exact prior static-note identity")
    lock, qa, policy, note = (load(ROOT / "state/dataset_lock.json"),
        load(ROOT / "reports/generated/DATA_QUALITY_REPORT.json"),
        load(ROOT / "configs/dataset_policy.json"), load(NOTE))
    need(lock["quality_report_sha256"] == PINS["reports/generated/DATA_QUALITY_REPORT.json"] and
         lock["dataset_policy_sha256"] == PINS["configs/dataset_policy.json"] and
         lock["dataset_id"] == qa["dataset_id"] == note["dataset_id"] and
         lock["holdout_start_utc"] == "2026-03-01T00:00:00Z" and
         lock["holdout_end_exclusive_utc"] == "2026-09-01T00:00:00Z",
         "Original sealed dataset identity and locked bounds")
    need(policy["holdout_start_utc"] == lock["holdout_start_utc"] and
         policy["holdout_end_exclusive_utc"] == lock["holdout_end_exclusive_utc"],
         "Locked policy identity")
    need(note["status"] == "STATIC_METADATA_DRAFT_NOT_NEW_SOURCE_ACCEPTANCE_OR_ECONOMIC_RUN" and
         note["source_files_current_bytes_verified"] is False, "Note is a plan, not acceptance")
    expected = {(symbol, month) for symbol in SYMBOLS for month in MONTHS}
    notes = {(row["symbol"], row["month"]): row for row in note["sources"]}
    need(len(note["sources"]) == 38 and set(notes) == expected, "Exact38 static metadata rows")
    rows = []
    for symbol in SYMBOLS:
        for month in MONTHS:
            name = f"{symbol}-1m-{month}.zip"
            matches = [row for row in qa["sources"] if row["source"] == name]
            need(len(matches) == 1, "One exact original QA row: " + name)
            quality = matches[0]
            relative = f"data/normalized/spot/{symbol}/1m/{month}.parquet"
            path = ROOT / relative
            first = date.fromisoformat(month + "-01")
            last = date(first.year + first.month // 12, first.month % 12 + 1, 1)
            count = calendar.monthrange(first.year, first.month)[1] * 1440
            need(date(2023, 12, 1) <= first < last <= date(2025, 7, 1),
                 "Source dates rejected before market-file IO")
            need(notes[symbol, month]["source"] == name and
                 notes[symbol, month]["old_quality"] == quality and
                 notes[symbol, month]["normalized_path"] == str(path) and
                 notes[symbol, month]["normalized_sha256"] == lock["minute_files"][relative],
                 "QA row, explicit path and sealed minuteSHA must agree")
            need(quality["timestamp_unit"] in ("milliseconds", "microseconds") and
                 quality["rows"] == quality["expected_rows"] == count and
                 quality["first_open_us"] == opened(first) and
                 quality["last_open_us"] == opened(last) - 60_000_000 and
                 all(quality[key] == 0 for key in
                     ("missing_rows", "duplicate_rows", "bad_timestamps", "bad_values", "gaps", "quarantined_rows")) and
                 not quality["incomplete_days"] and not quality["quarantined_days"] and
                 not quality["nonstandard_closes"], "Only complete original sealed monthly QA")
            rows.append(dict(symbol=symbol, month=month, normalized_path=str(path),
                normalized_sha256=lock["minute_files"][relative], rows=count,
                timestamp_unit=quality["timestamp_unit"], old_quality=quality))
    return rows


def stream_source(record):
    path = Path(record["normalized_path"])
    expected = ROOT / "data/normalized/spot" / record["symbol"] / "1m" / (record["month"] + ".parquet")
    need((record["symbol"], record["month"]) in {(s, m) for s in SYMBOLS for m in MONTHS} and
         path == expected and path.resolve() == expected and not path.is_symlink(),
         "Explicit locked-excluding path rejected before file open")
    before = path.stat()
    need(path.is_file() and before.st_size == record["old_quality"]["normalized_bytes"],
         "Original sealed normalized byte count")
    digest = hashlib.sha256()
    count = 0
    with path.open("rb") as stream:
        while block := stream.read(1_048_576):
            digest.update(block)
            count += len(block)
    after = path.stat()
    need((before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns) ==
         (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) and
         count == before.st_size and digest.hexdigest() == record["normalized_sha256"],
         "Source changed or byteSHA differs from frozen original")
    return dict(record, actual_bytes_streamed=count, current_normalized_sha256=digest.hexdigest(),
        row_count_verification="REUSED_SEALED_QA_EXACT_BYTE_SHA_NOT_ROWS_REREAD",
        normalized_clock_unit="ORIGINAL_NORMALIZATION_MICROSECONDS_NOT_NEW_SCHEMA_CHECK")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    work, output, protocol = args.run_dir.resolve(), args.output.resolve(), args.protocol.resolve()
    need(work.is_relative_to(STATE) and not work.exists() and
         output.parent == ROOT / "reports/fast_research" and not output.exists() and
         protocol.parent == ROOT / "protocols", "Exclusive nativeSTATE and project receipt/protocol")
    need(os.environ.get("COIN_TASK_ID") and os.environ.get("WSL_DISTRO_NAME") == "hpc_linux" and
         sys.prefix == str(STATE / "v8-clean-env-20261002-v2") and
         all(os.environ.get(name) == "2" for name in
             ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "POLARS_MAX_THREADS")),
         "Progress task, frozen cleanWSL and explicitCPU2 required")
    work.mkdir()
    started = time.monotonic()
    spec = load(protocol)
    binding = dict(task_id=os.environ["COIN_TASK_ID"], protocol_path=str(protocol.relative_to(ROOT)),
        protocol_sha256=sha(protocol), source_sha256=sha(__file__), source_path=str(Path(__file__).resolve()),
        command=shlex.join([sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]),
        git_commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        sys_prefix=sys.prefix, environment_lock_sha256=PINS["environments/v8/uv.lock"],
        spec=spec, seed="NOT_APPLICABLE_SOURCE_METADATA_ONLY")
    write(work / "RUN_BINDING.json", binding)
    from scripts.research_v8.registry import FIELDS, append_event
    from scripts.research_v8.funding_price_source_v2 import progress_writer, owned_bytes
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=spec["experiment_id"], git_commit=binding["git_commit"],
        data_manifest_hash=PINS["state/dataset_lock.json"], protocol_hash=binding["protocol_sha256"],
        feature_set="NONE_SOURCE_ONLY", labels="NONE", model_family="NONE", hyperparameters=spec,
        seed="NOT_APPLICABLE", thresholds={"source_files": 38, "no_market_rows": True},
        cost_assumptions="NOT_EVALUATED_FIXED_COSTS_NOT_CHANGED", all_folds="547D_DEVELOPMENT_PLUS31D_WARMUP",
        reason_for_next_experiment="Reuse sealed inputs for fixed public strategy long development falsification",
        result_influenced_later_choice="SOURCE_BINDING_ONLY_NO_ECONOMIC_RESULTS")
    write(work / "START.json", append_event(ROOT / "reports/experiment_registry.jsonl", dict(event,
        event_id=spec["experiment_id"] + ":START", event_type="OPERATIONAL_SOURCE_METADATA_REUSE_START",
        success_failure="START_BEFORE38_SOURCE_BYTE_HASHES")))
    progress, exit_code = progress_writer(38), 1
    report = dict(status="FAIL_LONG_547D_SEALED_SOURCE_REUSE", binding=binding, sources=[],
        market_price_rows_read=False, fresh_QA_performed=False, parquet_schema_or_footer_read=False,
        raw_ZIP_or_CRC_read=False, download_performed=False, source_modified=False, locked_consumed=False,
        classification="PREVIOUSLY_SEEN_DEVELOPMENT_SCREENING", economics="NOT_EVALUATED",
        candidate_status="NO_QUALIFIED_CANDIDATE", models_fit=0, orders_sent=0, GPU=0)
    try:
        need(spec["source_sha256"] == binding["source_sha256"] and
             spec["run_dir"] == str(work) and spec["output"] == str(output.relative_to(ROOT)) and
             0 < spec["maximum_wall_seconds"] <= 300 and
             0 < spec["maximum_new_owned_bytes"] <= MAX_OWNED, "Frozen helper/output/budget identity")
        need(spec["frozen_sources"] == {**PINS, **SUPPORT_PINS},
             "Only exact metadata/code dependencies; never hash arbitrary market paths")
        for relative, digest in spec["frozen_sources"].items():
            path = ROOT / relative
            need(path.resolve().is_relative_to(ROOT) and sha(path) == digest, "Frozen helper dependency changed")
        from quant import disk, resources
        report["resources_before"] = resources.status()
        report["disk_check_started_utc"] = datetime.now(UTC).isoformat()
        report["disk_budget_check_calls"] = 1
        report["disk_budget_before"] = disk.check(MAX_OWNED)
        report["disk_check_completed_utc"] = datetime.now(UTC).isoformat()
        planned = metadata_rows(spec)
        progress.update("复用旧QA，逐档核验冻结Parquet字节", 0, 38, "文件")
        for record in planned:
            need(time.monotonic() - started <= spec["maximum_wall_seconds"], "Fixed metadata budget")
            report["sources"].append(stream_source(record))
            progress.update("已核验冻结Parquet字节", len(report["sources"]), 38, "文件")
        need(len(report["sources"]) == 38 and sum(row["rows"] for row in report["sources"]) == 1_664_640 and
             sha(protocol) == binding["protocol_sha256"] and sha(__file__) == binding["source_sha256"],
             "Complete fixed source count and unchanged run identity")
        end_pins = {relative: sha(ROOT / relative) for relative in spec["frozen_sources"]}
        need(end_pins == spec["frozen_sources"] and sha(NOTE) == NOTE_SHA,
             "Metadata, support sources or portable static note changed during source binding")
        report["metadata_and_support_pins_reverified_at_end"] = end_pins
        report["portable_static_note_sha256_at_end"] = NOTE_SHA
        report["resources_after"] = resources.status()
        report["owned_file_bytes_before_final_receipts"] = owned_bytes(work)
        report["owned_before_final_receipts_scope"] = "EXCLUSIVE_RUN_DIR_BEFORE_REPORT_AND_RESULT"
        need(owned_bytes(work) + len(json.dumps(report, indent=2, ensure_ascii=False).encode()) + 65_536 <=
             spec["maximum_new_owned_bytes"], "Source-only owned artifacts must remain within10MB")
        report.update(status=STATUS, source_files=38, days_per_symbol=578, actual_minute_rows=1_664_640,
            complete_days_across_symbols=1156, old_qualified_calendar_evidence_reused=True,
            row_count_verification="REUSED_SEALED_QA_EXACT_BYTE_SHA_NOT_ROWS_REREAD",
            source_scope=SCOPE, source_calendar=list(MONTHS))
        exit_code = 0
    except Exception as error:
        report.update(error_type=type(error).__name__, reason=str(error))
        if "resources_after" not in report:
            try:
                from quant import resources
                report["resources_after"] = resources.status()
            except Exception as resource_error:
                report["resources_after_error"] = {"type": type(resource_error).__name__, "reason": str(resource_error)}
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(), actual_operation_exit_code=exit_code,
            elapsed_seconds=time.monotonic() - started,
            WSL_python_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
            source_files_completed=len(report["sources"]))
        write(output, report)
        write(work / "RESULT.json", append_event(ROOT / "reports/experiment_registry.jsonl", dict(event,
            event_id=spec["experiment_id"] + ":RESULT", event_type="OPERATIONAL_SOURCE_METADATA_REUSE_RESULT",
            success_failure=report["status"], output_path=str(output.relative_to(ROOT)), output_sha256=sha(output),
            actual_task_id=binding["task_id"], actual_operation_exit_code=exit_code)))
        progress.stop.set()
        progress.thread.join(timeout=3)
        actual_owned = owned_bytes(work) + output.stat().st_size
        need(actual_owned <= spec["maximum_new_owned_bytes"] <= MAX_OWNED,
             "Actual exclusive run files and output report exceed10MB")
        print(json.dumps(dict(status=report["status"], output=str(output), sha256=sha(output), actual_exit=exit_code,
            actual_owned_file_bytes=actual_owned, owned_scope="EXCLUSIVE_RUN_DIR_PLUS_OUTPUT_REPORT_AFTER_RESULT",
            wrapper_stdout_or_progress_global_metadata_excluded=True)))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())