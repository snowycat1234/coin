"""One immutable V8 endpoint cache; no fitting, download, or economic replay.

Only ``joint_rows`` reads source bars. The old prepare_index/__getitem__ paths
are deliberately absent: their future-valid selection is not a decision grid.
"""
from __future__ import annotations

import argparse
from datetime import UTC, date, datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import numpy as np
import polars as pl
from quant import disk, resources
from quant.paths import ROOT, STATE
from quant.research_fast.dataset import BAR_US, DAY_US, START, LOCKED, FastSequenceDataset, day_us, file_sha
from quant.research_fast.trade_flow_v2 import require

sys.path.insert(0, str(ROOT))
from scripts.research_v8 import features_v4 as features, labels_v5 as labels
from scripts.research_v8.nonoverlap_mechanism_v2 import accepted_shards
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS, append_event

PROTOCOL = ROOT / "protocols/SHARED_FEATURE_CACHE_V8_V1.json"
MINUTE_US = 60_000_000
FEATURE_COLUMNS = tuple(f"f{index:03}" for index in range(478))
VARIANTS = ("LEAD_LAG_5M_5M", "EARLY_LATE_150S_GAP5", "EARLY_LATE_150S_GAP10")
SIGNAL_DIFFERENCES = ("signal_kind", "signal_available_us", "earliest_order_us", "earliest_permissible_order_us")


def json_read(path):
    path = Path(path).resolve()
    require(path.is_relative_to(ROOT) and path.is_file() and path.stat().st_size <= 2_000_000,
            "Explicit bounded D-project proof required")
    return json.loads(path.read_text())


def json_write(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, allow_nan=False)
        handle.write("\n")


def calendar(decisions):
    raw = np.asarray(decisions)
    require(raw.ndim == 1 and len(raw) > 0 and np.issubdtype(raw.dtype, np.integer)
            and raw.dtype != np.bool_, "Original one-dimensional integer minute calendar required")
    require(np.all(raw >= day_us(START) + 720 * BAR_US) and np.all(raw < day_us(LOCKED))
            and np.all(raw <= np.iinfo(np.int64).max), "Development-only cache calendar; locked forbidden")
    raw = raw.astype(np.int64, copy=False)
    require(np.all(raw % MINUTE_US == 0) and np.all(np.diff(raw) == MINUTE_US),
            "Complete chronological minute calendar required; no dropping endpoints")
    return raw


def fold_days(folds):
    """Freeze all21 UTC days/fold before touching any source file."""
    result = []
    require([fold["id"] for fold in folds] == ["v8_A", "v8_B", "v8_C", "v8_D"], "Frozen four fold IDs required")
    for fold in folds:
        stamps = [day_us(date.fromisoformat(fold[name])) for name in
                  ("train_start", "validation_start", "test_start", "test_end_exclusive")]
        train, validation, test, end = stamps
        require(day_us(START) + 720 * BAR_US <= train < validation < test < end < day_us(LOCKED),
                "Explicit development fold bounds only")
        require(validation - train == 12 * DAY_US and test - validation == 2 * DAY_US
                and end - test == 7 * DAY_US, "Exactly12/2/7 complete UTC days")
        cutoff = validation - 600_000_000 - 600_000_000 - 1
        for split, lower, upper, deadline, exclusive in (
            ("TRAIN", train, validation, cutoff, False),
            ("VALIDATION", validation, test, test - 600_000_000, True),
            ("OOS_SCREENING", test, end, end, False),
        ):
            for start in range(lower, upper, DAY_US):
                result.append({"fold": fold["id"], "split": split, "start_us": start,
                    "end_us": start + DAY_US, "maturity_deadline_us": deadline,
                    "deadline_exclusive": exclusive, "fit_cutoff_us": cutoff})
    require(len(result) == 84 and sum((row["end_us"] - row["start_us"]) // MINUTE_US
            for row in result) == 120_960, "Full84-day120960-minute calendar required")
    return result


def source_bounds(decisions):
    decisions = calendar(decisions)
    lower, upper = int(decisions[0] - 720 * BAR_US), int(decisions[-1] + 600_000_000)
    require(day_us(START) <= lower < upper <= day_us(LOCKED), "Cache read would enter locked dates")
    return lower, upper


def read_joint(dataset, decisions):
    lower, upper = source_bounds(decisions)  # Guard before any source IO.
    return dataset.joint_rows(lower, upper)


def identity(source_receipt_sha256, decision):
    return hashlib.sha256(f"V8_ENDPOINT:{source_receipt_sha256}:{decision}".encode()).hexdigest()


def feature_frame(joint, decisions, *, fold, split, source_receipt_sha256, on_endpoint=None):
    decisions = calendar(decisions)
    require(split in ("TRAIN", "VALIDATION", "OOS_SCREENING"), "Explicit cache split required")
    require(len(source_receipt_sha256) == 64 and len(features.NAMES) == len(FEATURE_COLUMNS), "Exact feature and source identity")
    values = np.full((len(decisions), len(FEATURE_COLUMNS)), np.nan, np.float64)
    available, eligible, reasons = [], [], []
    for row, decision in enumerate(decisions):
        try:
            result = features.endpoint_features(joint, int(decision))
        except ValueError as error:
            eligible.append(False)
            available.append(None)
            reasons.append(str(error))
        else:
            require(result.names == features.NAMES and result.values.shape == (478,)
                    and result.decision_us == decision and result.available_us <= decision,
                    "Accepted endpoint output identity/availability changed")
            values[row] = result.values
            eligible.append(True)
            available.append(result.available_us)
            reasons.append(None)
        if on_endpoint is not None:
            on_endpoint(row + 1)
    metadata = pl.DataFrame({"endpoint_id": [identity(source_receipt_sha256, int(t)) for t in decisions],
        "fold": [fold] * len(decisions), "split": [split] * len(decisions), "decision_us": decisions,
        "feature_eligible": eligible, "feature_available_us": pl.Series(available, dtype=pl.Int64),
        "feature_reason": pl.Series(reasons, dtype=pl.String)})
    return metadata.hstack(pl.DataFrame(values, schema=list(FEATURE_COLUMNS), orient="row"))


def label_views(joint, decisions, *, split, maturity_deadline_us, deadline_exclusive):
    decisions = calendar(decisions)
    require(isinstance(maturity_deadline_us, (int, np.integer)) and not isinstance(maturity_deadline_us, bool),
            "Original integer split deadline required")
    require(isinstance(deadline_exclusive, bool), "Explicit maturity-bound convention")
    output = {}
    for variant in VARIANTS:
        frame = labels.label_table(joint, decisions, variant, split=split, signal_kind="PAST_ONLY_PREDICTED_FLOW")
        mature = pl.col("label_mature_us") < maturity_deadline_us if deadline_exclusive else pl.col("label_mature_us") <= maturity_deadline_us
        allowed = (pl.col("label_valid") & mature).fill_null(False)
        frame = frame.with_columns(pl.lit(maturity_deadline_us, dtype=pl.Int64).alias("split_maturity_deadline_us"),
            allowed.alias("offline_maturity_eligible"),
            pl.when(~pl.col("label_valid")).then(pl.lit("INVALID_OFFLINE_LABEL"))
              .when(~allowed).then(pl.lit("IMMATURE_FOR_SPLIT")).otherwise(None).alias("offline_exclusion_reason"))
        require(np.array_equal(frame["decision_us"].to_numpy(), decisions), "Label view dropped a calendar endpoint")
        labels.assert_nonoverlap(frame)
        # This call selects the same targets; it must never build another label.
        direct = labels.direct_return_labels(frame)
        require(not any("__future_flow" in name for name in direct.columns), "Matched DIRECT target selection changed")
        output[variant] = frame
    return output


def same_bits(first, second):
    require(first.columns == second.columns and first.schema == second.schema and first.equals(second),
            "Original schema, row IDs or values changed")
    for name, dtype in first.schema.items():
        if dtype in (pl.Float64, pl.Float32):
            known = ~first[name].is_null().to_numpy()
            one, two = first[name].to_numpy(), second[name].to_numpy()
            unit = np.uint64 if dtype == pl.Float64 else np.uint32
            require(np.array_equal(one.view(unit)[known], two.view(unit)[known]), "Float bits changed: " + name)


def compare_prior(old, views):
    """Targets/IDs/maturity bitexact; only the disclosed signal metadata differs."""
    for variant, new in views.items():
        earlier = old.filter(pl.col("label_variant") == variant).sort("decision_us")
        require(earlier.height == new.height, "Frozen TRAIN/OOS calendar pairing differs")
        columns = [name for name in earlier.columns if name not in (*SIGNAL_DIFFERENCES, "diagnostic_outcome_valid")]
        same_bits(earlier.select(columns), new.select(columns))
        require(np.array_equal(earlier["diagnostic_outcome_valid"].to_numpy(), new["offline_maturity_eligible"].to_numpy()),
                "Frozen maturity-qualified row selection changed")


def owned_bytes(work):
    return sum(path.stat().st_size for path in work.rglob("*") if path.is_file())


def validate_matrix(matrix):
    decisions = calendar(matrix["decision_us"].to_numpy())
    require(matrix.schema["feature_eligible"] == pl.Boolean and matrix["feature_eligible"].null_count() == 0
            and matrix.schema["feature_available_us"] == pl.Int64,
            "Known Boolean feature eligibility and nullable integer availability required")
    require(all(matrix.schema[name] == pl.Float64 for name in FEATURE_COLUMNS), "One canonical raw Float64 feature matrix")
    values, eligible = matrix.select(FEATURE_COLUMNS).to_numpy(), matrix["feature_eligible"].to_numpy()
    require(values.shape == (len(decisions), 478) and np.isfinite(values[eligible]).all()
            and np.isnan(values[~eligible]).all(), "Eligible features finite; abstentions allNaN, never zero")
    require(matrix["endpoint_id"].n_unique() == len(decisions), "Shared unique endpoint IDs required")
    for row, allowed in enumerate(eligible):
        available, reason = matrix["feature_available_us"][row], matrix["feature_reason"][row]
        require((available is not None and available <= decisions[row] and reason is None) if allowed
                else (available is None and isinstance(reason, str) and bool(reason)), "Feature availability/abstention reason differs")
    return decisions


def commit_day(work, key, matrix, views, *, maximum_bytes=1_000_000_000):
    """Expose a complete immutable day only after every artifact roundtrips."""
    require(work.resolve().is_relative_to(STATE.resolve()) and not work.is_symlink(), "Exclusive native STATE cache required")
    require(key and all(char.isalnum() or char in "_-" for char in key), "Ordinary owned day identity")
    decisions = validate_matrix(matrix)
    require(set(views) == set(VARIANTS), "All three existing variants required")
    for frame in views.values():
        require(np.array_equal(frame["decision_us"].to_numpy(), decisions), "Every target shares the feature calendar")
        labels.assert_nonoverlap(frame)
    temporary, target = work / ("pending-" + key), work / key
    require(not temporary.exists() and not target.exists(), "New day directory required; no evidence overwrite")
    estimate = matrix.estimated_size() + sum(frame.estimated_size() for frame in views.values())
    require(owned_bytes(work) + 2 * estimate + 1_000_000 < maximum_bytes, "Cache plus pending-day1GB budget would be exceeded")
    temporary.mkdir()
    matrix.write_parquet(temporary / "features.parquet", compression="zstd")
    same_bits(matrix, pl.read_parquet(temporary / "features.parquet"))
    for variant, frame in views.items():
        path = temporary / (variant + "-labels.parquet")
        frame.write_parquet(path, compression="zstd")
        same_bits(frame, pl.read_parquet(path))
    artifacts = {path.name: {"sha256": file_sha(path), "bytes": path.stat().st_size}
                 for path in temporary.iterdir() if path.is_file()}
    manifest = {"status": "COMPLETE_ENDPOINT_PARTITION_NOT_ALPHA_EVIDENCE", "rows": len(decisions),
        "full_UTC_day": bool(len(decisions) == 1440 and decisions[0] % DAY_US == 0),
        "first_decision_us": int(decisions[0]), "last_decision_us": int(decisions[-1]),
        "feature_eligible_rows": int(matrix["feature_eligible"].sum()), "feature_names": list(features.NAMES),
        "matrix_sha256": artifacts["features.parquet"]["sha256"], "artifacts": artifacts,
        "labels": {variant: {"label_valid": int(frame["label_valid"].sum()),
            "offline_maturity_eligible": int(frame["offline_maturity_eligible"].sum())} for variant, frame in views.items()},
        "shared_matrix_no_model_specific_rebuild": True, "normalization": "NONE_OFFICIAL_TRAIN_ONLY_SCALER_IN_LATER_CALLER"}
    json_write(temporary / "DAY_MANIFEST.json", manifest)
    require(owned_bytes(work) < maximum_bytes, "Actual new cache plus pending artifacts exceeded1GB")
    temporary.rename(target)
    return {"path": str(target), "manifest_sha256": file_sha(target / "DAY_MANIFEST.json"),
        **{name: value for name, value in manifest.items() if name != "feature_names"}}


def verified_bindings():
    spec = json_read(PROTOCOL)
    proofs = {}
    for name, binding in spec["frozen_proofs"].items():
        require(file_sha(ROOT / binding["path"]) == binding["sha256"], "Frozen proof changed: " + name)
        proof = json_read(ROOT / binding["path"])
        require(proof["status"] == binding["status"], "Accepted proof status changed: " + name)
        proofs[name] = proof
    hashes = dict(spec["frozen_sources"])
    for binding in spec["frozen_proofs"].values():
        hashes[binding["path"]] = binding["sha256"]
    for name in ("label_audit", "feature_audit"):
        hashes.update(proofs[name]["verified_source_hashes"])
    hashes.update(proofs["source_receipt"]["source_hashes"])
    for path, digest in hashes.items():
        require(file_sha(ROOT / path) == digest, "Frozen dependency changed: " + path)
    environment = proofs["source_receipt"]["registration_start"]["hyperparameters"]["environment"]
    require(Path(sys.prefix).resolve() == Path(environment["sys_prefix"]).resolve()
            and spec["environment_lock_sha256"] == environment["lock_sha256"] == file_sha(ROOT / "environments/v8/uv.lock")
            and not any("research-env-v6" in entry or "/coin/.venv/" in entry for entry in sys.path), "Accepted native clean CPU runtime required")
    gates = json_read(ROOT / "protocols/P1_GATE_V8.json")
    require(gates["folds"] == spec["folds"] and gates["maximum_nominal_label_lag_seconds"] == gates["embargo_seconds"] == 600,
            "Frozen four-fold lag/embargo contract differs")
    require(tuple(spec["variants"]) == VARIANTS and spec["feature_count"] == len(features.NAMES) == 478,
            "Fixed shared cache identity changed")
    for name in (str(PROTOCOL.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT)),
                 "tests/test_v8_shared_feature_cache_v1.py", "scripts/research_v8/registry.py", "src/quant/resources.py",
                 "src/quant/disk.py", "src/quant/paths.py", "scripts/with_task_progress.sh", "scripts/bounded.sh", "scripts/env.sh"):
        hashes[name] = file_sha(ROOT / name)
    return spec, proofs, hashes


def full_cache(spec, proofs, work, progress, report):
    days = fold_days(spec["folds"])
    wanted = set()
    for row in days:
        lower, upper = source_bounds(np.arange(row["start_us"], row["end_us"], MINUTE_US, dtype=np.int64))
        cursor, final = date.fromisoformat(datetime.fromtimestamp(lower // 1_000_000, UTC).date().isoformat()), datetime.fromtimestamp((upper - 1) // 1_000_000, UTC).date()
        while cursor <= final:
            wanted.add(cursor)
            cursor += timedelta(days=1)
    progress.update("核对四流已验收来源", 0, 4 * len(wanted), "文件")
    dataset = FastSequenceDataset(accepted_shards(proofs["source_receipt"], wanted), mode="smoke")
    report.update(dataset_sha256=dataset.contract_sha256, selected_source_days=len(wanted), source_shards=4 * len(wanted))
    prior = {fold["fold"]: fold for fold in proofs["calendar_report"]["folds"]}
    prior_frame, prior_fold = None, None
    source_sha = spec["frozen_proofs"]["source_receipt"]["sha256"]
    for ordinal, row in enumerate(days):
        if prior_fold != row["fold"]:
            bound = prior[row["fold"]]
            path = Path(bound["calendar_path"]).resolve()
            require(path.is_relative_to(STATE.resolve()) and file_sha(path) == bound["calendar_sha256"], "Frozen V3 calendar changed")
            prior_frame, prior_fold = pl.read_parquet(path), row["fold"]
        decisions = np.arange(row["start_us"], row["end_us"], MINUTE_US, dtype=np.int64)
        joint = read_joint(dataset, decisions)
        def updated(count):
            progress.value = {**progress.value, "phase": "缓存同一478维过去特征", "completed": ordinal * 1440 + count,
                "total": 120_960, "unit": "分钟端点", "metrics": {"fold": row["fold"], "split": row["split"], "完成整日": ordinal}}
            if count % 60 == 0:
                progress.update("缓存同一478维过去特征", ordinal * 1440 + count, 120_960, "分钟端点",
                    fold=row["fold"], split=row["split"], 完成整日=ordinal)
        matrix = feature_frame(joint, decisions, fold=row["fold"], split=row["split"], source_receipt_sha256=source_sha, on_endpoint=updated)
        views = label_views(joint, decisions, split=row["split"], maturity_deadline_us=row["maturity_deadline_us"], deadline_exclusive=row["deadline_exclusive"])
        if row["split"] != "VALIDATION":
            old = prior_frame.filter(pl.col("decision_us").is_between(int(decisions[0]), int(decisions[-1]), closed="both"))
            compare_prior(old, views)
        key = row["fold"] + "_" + datetime.fromtimestamp(row["start_us"] // 1_000_000, UTC).date().isoformat()
        report["days"].append(commit_day(work, key, matrix, views))
        require(owned_bytes(work) < spec["maximum_new_owned_bytes"], "Actual cache budget exceeded")
        report["completed_minutes"] += 1440
    require(len(report["days"]) == 84 and report["completed_minutes"] == 120_960, "No incomplete full-cache PASS")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--tiny-smoke", action="store_true")
    mode.add_argument("--build-cache", action="store_true")
    parser.add_argument("--cache-audit", type=Path)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run, output = args.run_dir.resolve(), args.output.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists(), "New exclusive D-native run directory required")
    require(output.is_relative_to((ROOT / "reports/fast_research").resolve()) and not output.exists(), "New small result required")
    require(bool(os.environ.get("COIN_TASK_ID")), "Actual bounded task progress required")
    state = resources.status()
    # Prebind first so proof/environment failures also produce a failure receipt.
    spec = json_read(PROTOCOL)
    hashes = {name: file_sha(ROOT / name) for name in spec["frozen_sources"]}
    hashes.update({str(Path(__file__).resolve().relative_to(ROOT)): file_sha(Path(__file__)),
        str(PROTOCOL.relative_to(ROOT)): file_sha(PROTOCOL),
        "tests/test_v8_shared_feature_cache_v1.py": file_sha(ROOT / "tests/test_v8_shared_feature_cache_v1.py"),
        "environments/v8/uv.lock": file_sha(ROOT / "environments/v8/uv.lock")})
    for proof in spec["frozen_proofs"].values():
        hashes[proof["path"]] = file_sha(ROOT / proof["path"])
    exact = [sys.executable, str(Path(__file__).resolve()), *sys.argv[1:]]
    test_command = [sys.executable, "-m", "pytest", "tests/test_v8_shared_feature_cache_v1.py", "-q",
        "--basetemp=" + str(run / "pytest"), "-o", "cache_dir=" + str(run / "pytest-cache"),
        "--junitxml=" + str(run / "junit.xml")]
    binding = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_hashes": hashes, "protocol_sha256": hashes[str(PROTOCOL.relative_to(ROOT))],
        "environment_lock_sha256": hashes["environments/v8/uv.lock"], "exact_command": shlex.join(exact),
        "required_outer_wrapper": "scripts/with_task_progress.sh (bounded)", "python": sys.executable, "sys_prefix": sys.prefix,
        "task_id": os.environ["COIN_TASK_ID"], "data_scope": "SYNTHETIC_ONLY" if args.tiny_smoke else "ACCEPTED_153D_DEVELOPMENT_SUBSET",
        "source_receipt_sha256": spec["frozen_proofs"]["source_receipt"]["sha256"], "all_folds": spec["folds"],
        "frozen_proofs": spec["frozen_proofs"], "exact_test_command": shlex.join(test_command) if args.tiny_smoke else None,
        "synthetic_recipe_sha256": hashes["tests/test_v8_shared_feature_cache_v1.py"] if args.tiny_smoke else None,
        "seed": 20261002 if args.tiny_smoke else "NOT_APPLICABLE_DETERMINISTIC", "resources": state}
    run.mkdir()
    json_write(run / "RUN_BINDING.json", binding)
    for name in hashes:
        saved = run / "source-snapshot" / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, saved)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id, event_id=args.experiment_id + ":START", event_type="OPERATIONAL_START",
        git_commit=binding["git_commit"], data_manifest_hash=binding["synthetic_recipe_sha256"] or binding["source_receipt_sha256"],
        protocol_hash=binding["protocol_sha256"], feature_set="SHARED_V8_PAST720_FIXED478_RAW_FLOAT64",
        labels=list(VARIANTS), model_family="NONE", hyperparameters={"fits": 0, "normalization": "NONE", "no_old_dataset_index": True},
        seed=binding["seed"], thresholds="NO_MODEL_TARGET_OR_RECIPE_SELECTION", cost_assumptions="NO_ECONOMIC_REPLAY",
        all_folds=spec["folds"], success_failure="START", reason_for_next_experiment="Single shared past-only cache for strict OOF surprise versus matched DIRECT",
        result_influenced_later_choice=False, exact_command=binding["exact_command"], source_hashes=hashes,
        environment_lock_sha256=binding["environment_lock_sha256"], run_binding_sha256=file_sha(run / "RUN_BINDING.json"),
        data_scope=binding["data_scope"], market_models_fit=0, locked_consumed=False)
    registered = append_event(ROOT / "reports/experiment_registry.jsonl", event)
    report = {"status": "FAIL_SHARED_FEATURE_CACHE", "registration_start": registered, "binding": binding,
        "run_dir": str(run), "run_binding_sha256": file_sha(run / "RUN_BINDING.json"), "days": [], "completed_minutes": 0,
        "market_inputs_read": False, "market_models_fit": 0, "locked_consumed": False, "orders_sent": 0,
        "candidate": "NONE", "candidate_status": "NO_QUALIFIED_CANDIDATE", "P1_gate": "NOT_READY"}
    progress, started = Progress(), time.monotonic()
    progress.value["detail"] = "共享过去特征缓存；不拟合模型、不做经济评价"
    try:
        require(pl.thread_pool_size() <= 2 and all(int(os.environ.get(name, "2")) <= 2 for name in
            ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")), "At most2 shared CPU numerical/Polars threads required")
        spec, proofs, all_hashes = verified_bindings()
        json_write(run / "VERIFIED_DEPENDENCIES.json", all_hashes)
        report["verified_source_hashes"] = all_hashes
        progress.update("核对缓存磁盘预留", 0, None, "扫描")
        report["disk"] = {"scan_started_utc": datetime.now(UTC).isoformat(), **disk.check(10_000_000 if args.tiny_smoke else 1_000_000_000),
            "scan_finished_utc": datetime.now(UTC).isoformat()}
        if args.tiny_smoke:
            command = test_command
            json_write(run / "EXACT_TEST_COMMAND.json", command)
            progress.update("合成缓存入口验收", 0, None, "用例")
            result = subprocess.run(command, cwd=ROOT, check=False)
            report["test_exit_code"] = result.returncode
            if (run / "junit.xml").is_file():
                suites = ET.parse(run / "junit.xml").getroot()
                report["junit_counts"] = {key: sum(int(suite.attrib.get(key, "0")) for suite in suites.iter("testsuite"))
                    for key in ("tests", "failures", "errors", "skipped")}
                report["junit_sha256"] = file_sha(run / "junit.xml")
            require(result.returncode == 0, "Synthetic cache checks failed; preserve source and outputs")
            report["status"] = "PASS_TINY_SYNTHETIC_SHARED_CACHE_NOT_MARKET_CACHE"
            progress.update("合成缓存入口验收完成", report["junit_counts"]["tests"], report["junit_counts"]["tests"], "用例")
        else:
            require(args.cache_audit is not None, "Independent cache audit required before full84-day execution")
            audit = json_read(args.cache_audit)
            require(audit["status"] == "PASS_SHARED_FEATURE_CACHE_IMPLEMENTATION"
                and all(audit["verified_source_hashes"].get(name) == digest for name, digest in all_hashes.items()),
                "Independent audit must bind every active cache dependency")
            report["cache_audit_sha256"] = file_sha(args.cache_audit)
            report["market_inputs_read"] = True
            full_cache(spec, proofs, run, progress, report)
            report["status"] = "PASS_COMPLETE_SHARED_CACHE_SCREENING_ONLY"
        require(all_hashes == {name: file_sha(ROOT / name) for name in all_hashes}, "Source changed during execution")
        report["source_bytes_unchanged"] = True
    except Exception as error:
        report.update(status="FAIL_SHARED_FEATURE_CACHE", error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(), elapsed_seconds=time.monotonic() - started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, resources=resources.status(), owned_bytes=owned_bytes(run))
        json_write(output, report)
        append_event(ROOT / "reports/experiment_registry.jsonl", {**event, "event_id": args.experiment_id + ":RESULT",
            "event_type": "OPERATIONAL_RESULT", "success_failure": report["status"], "artifact_path": str(output.relative_to(ROOT)),
            "artifact_sha256": file_sha(output), "test_exit_code": report.get("test_exit_code")})
        progress.stop.set()
        progress.thread.join(timeout=3)
        print(json.dumps({"status": report["status"], "output": str(output)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
