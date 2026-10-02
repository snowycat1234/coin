"""Fill only the omitted TRAIN calendar tail; inherit frozen V2 statistics."""
from __future__ import annotations

import argparse
import copy
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

import numpy as np
import polars as pl
from quant import resources
from quant.paths import ROOT, STATE
from quant.research_fast.dataset import BAR_US, DAY_US, START, LOCKED, FastSequenceDataset, day_us, file_sha
from quant.research_fast.trade_flow_v2 import require

sys.path.insert(0, str(ROOT))
from scripts.research_v8 import nonoverlap_mechanism_v2 as previous
from scripts.research_v8 import labels_v5 as labels
from scripts.research_v8.registry import FIELDS, append_event

PROTOCOL = ROOT / "protocols/NONOVERLAP_CALENDAR_SUPPLEMENT_V8_V3.json"
MINUTE_US = 60_000_000


def canonical_sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def unchanged_statistics(report):
    return [{"fold": fold["fold"], "variants": [{name: value for name, value in variant.items()
        if name not in ("calendar_minutes", "invalid_or_immature")} for variant in fold["variants"]]}
        for fold in report["folds"]]


def bitwise_equal(first, second):
    require(first.columns == second.columns and first.schema == second.schema and first.equals(second),
            "Original row schema, values or IDs changed")
    for name, dtype in first.schema.items():
        if dtype in (pl.Float64, pl.Float32):
            valid = ~first[name].is_null().to_numpy()
            one, two = first[name].to_numpy(), second[name].to_numpy()
            integer = np.uint64 if dtype == pl.Float64 else np.uint32
            require(np.array_equal(one.view(integer)[valid], two.view(integer)[valid]), "Float target/data bits changed: " + name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--state-directory", type=Path, required=True)
    args = parser.parse_args()
    output, work = args.output.resolve(), args.state_directory.resolve()
    require(output.is_relative_to(ROOT / "reports/fast_research") and not output.exists(), "Exclusive small result required")
    require(work.is_relative_to(STATE) and not work.exists(), "Exclusive D-native STATE required")
    require(bool(os.environ.get("COIN_TASK_ID")), "Actual bounded/progress task required")
    spec = previous._json(PROTOCOL)
    for key in ("parent_report", "parent_protocol", "source_receipt", "label_audit", "label_adapter", "source_adapter", "fold_contract", "environment_lock"):
        require(file_sha(ROOT / spec[key]) == spec[key + "_sha256"], "Frozen supplement binding changed: " + key)
    parent = previous._json(ROOT / spec["parent_report"])
    require(parent["status"] == "PASS_DIAGNOSTIC_EXECUTION_NOT_P1_GATE", "Accepted parent execution required")
    source = previous._json(ROOT / spec["source_receipt"])
    audit = previous._json(ROOT / spec["label_audit"])
    gates = previous._json(ROOT / spec["fold_contract"])
    require(audit["status"] == "PASS_CONTRACT_IMPLEMENTATION" and source["status"] == "PASS_SHARED_V8_SOURCE_VIEW_153D", "Exact accepted label/source receipts required")
    require(parent["registration_start"]["protocol_hash"] == spec["parent_protocol_sha256"]
        and parent["registration_start"]["data_manifest_hash"] == spec["source_receipt_sha256"]
        and parent["registration_start"]["label_audit_sha256"] == spec["label_audit_sha256"], "Parent start provenance differs")
    inherited_hashes = parent["source_hashes"] | source["source_hashes"] | audit["verified_source_hashes"]
    for name, digest in inherited_hashes.items():
        require(file_sha(ROOT / name) == digest, "Frozen inherited source changed: " + name)
    environment = source["registration_start"]["hyperparameters"]["environment"]
    require(Path(sys.prefix).resolve() == Path(environment["sys_prefix"]).resolve()
        and environment["lock_sha256"] == spec["environment_lock_sha256"], "Accepted native clean environment required")
    require([item["id"] for item in gates["folds"]] == spec["all_fold_ids"]
        and parent["registration_start"]["all_folds"] == gates["folds"], "Same frozen folds required")
    windows, wanted = [], set()
    lag = gates["maximum_nominal_label_lag_seconds"] * 1_000_000
    embargo = gates["embargo_seconds"] * 1_000_000
    for fold in gates["folds"]:
        train, validation, test, end = [day_us(date.fromisoformat(fold[key])) for key in
            ("train_start", "validation_start", "test_start", "test_end_exclusive")]
        require(day_us(START) <= train < validation < test < end < day_us(LOCKED), "Explicit development dates only")
        cutoff = validation - embargo - lag - 1
        decisions = np.arange((cutoff + MINUTE_US - 1) // MINUTE_US * MINUTE_US, validation, MINUTE_US, dtype=np.int64)
        require(len(decisions) == 20 and np.all(decisions > cutoff), "Only the original20 omitted TRAIN minutes")
        lower, upper = int(decisions[0] - 256 * BAR_US), int(decisions[-1] + lag)
        day, last = datetime.fromtimestamp(lower // 1_000_000, UTC).date(), datetime.fromtimestamp((upper - 1) // 1_000_000, UTC).date()
        while day <= last:
            wanted.add(day)
            day += timedelta(days=1)
        windows.append((fold, decisions, lower, upper, cutoff))
    require(len(wanted) == 8, "Eight source days only; no full diagnostic rerun")
    sources = inherited_hashes | {str(PROTOCOL.relative_to(ROOT)): file_sha(PROTOCOL),
        str(Path(__file__).resolve().relative_to(ROOT)): file_sha(Path(__file__)),
        spec["parent_protocol"]: spec["parent_protocol_sha256"]}
    old_calendar_hashes = {}
    for fold in parent["folds"]:
        path = Path(fold["calendar_path"]).resolve()
        require(path.is_relative_to(STATE) and file_sha(path) == fold["calendar_sha256"], "Frozen parent calendar changed")
        old_calendar_hashes[str(path)] = fold["calendar_sha256"]
    work.mkdir()
    for name in (str(PROTOCOL.relative_to(ROOT)), str(Path(__file__).resolve().relative_to(ROOT))):
        saved = work / "source-snapshot" / name
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, saved)
    exact = [sys.executable, str(Path(__file__).resolve()), "--output", str(output), "--state-directory", str(work)]
    binding = {"git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "source_hashes": sources, "parent_report_sha256": spec["parent_report_sha256"],
        "parent_calendar_hashes": old_calendar_hashes, "source_receipt_sha256": spec["source_receipt_sha256"],
        "label_audit_sha256": spec["label_audit_sha256"], "environment_lock_sha256": spec["environment_lock_sha256"],
        "python": sys.executable, "sys_prefix": sys.prefix, "exact_command": shlex.join(exact),
        "required_outer_wrapper": "scripts/with_task_progress.sh (inside bounded.sh)", "task_id": os.environ["COIN_TASK_ID"],
        "wanted_source_UTC_days": sorted(map(str, wanted)), "expected_source_shards": 32, "expected_added_rows": 240,
        "new_model_fits": 0, "new_hypotheses": 0, "resources": resources.status()}
    with (work / "RUN_BINDING.json").open("x") as stream:
        json.dump(binding, stream, indent=2, allow_nan=False)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id="v8-nonoverlap-calendar-supplement-20261002-v3", event_id="v8-nonoverlap-calendar-supplement-20261002-v3:START",
        event_type="FORMAL_START", git_commit=binding["git_commit"], data_manifest_hash=spec["source_receipt_sha256"], protocol_hash=file_sha(PROTOCOL),
        feature_set="UNCHANGED_PAST256_AVAILABILITY_ONLY_CALENDAR_BOUNDARY_REPAIR", labels=spec["variants"], model_family="NONE",
        hyperparameters={"new_fits": 0, "new_hypotheses": 0, "old_statistic_reruns": 0, "added_minutes_per_fold_variant": 20},
        seed="NOT_APPLICABLE_DETERMINISTIC", thresholds=parent["registration_start"]["thresholds"], cost_assumptions="UNCHANGED_NO_EXECUTION_OR_ECONOMIC_RESULT",
        all_folds=gates["folds"], success_failure="START", reason_for_next_experiment="Restore full TRAIN calendar after explicit boundary review; every added row remains ineligible",
        result_influenced_later_choice=False, run_binding_sha256=file_sha(work / "RUN_BINDING.json"), binding=binding)
    registered = append_event(ROOT / "reports/experiment_registry.jsonl", event)
    report = copy.deepcopy(parent)
    report.update(status="FAIL_CALENDAR_COMPLETENESS_SUPPLEMENT_NOT_P1_GATE", created_utc=datetime.now(UTC).isoformat(),
        parent_report_path=spec["parent_report"], parent_report_sha256=spec["parent_report_sha256"], parent_registration_start=parent["registration_start"],
        registration_start=registered, source_hashes=sources, run_binding_sha256=file_sha(work / "RUN_BINDING.json"),
        classification="SCREENING_MECHANISM_CALENDAR_CORRECTNESS_SUPPLEMENT_ONLY", supplement={"new_model_fits": 0, "new_hypotheses": 0, "fold_checks": []})
    statistics_sha = canonical_sha(unchanged_statistics(parent))
    started, progress = time.monotonic(), previous.Progress()
    progress.value["detail"] = "仅补训练日历末20分钟；240新增行均不得评分，原96统计保持"
    try:
        progress.update("核对32显式来源", 0, 32, "档案")
        shards = previous.accepted_shards(source, wanted)
        require(len(shards) == 32, "Only32 accepted source shards")
        dataset = FastSequenceDataset(shards, mode="smoke")
        progress.update("32显式来源已核", 32, 32, "档案")
        report["supplement"]["source_shards"] = len(shards)
        report["supplement"]["dataset_sha256"] = dataset.contract_sha256
        added_rows = 0
        for index, (fold, decisions, lower, upper, cutoff) in enumerate(windows):
            old_result = next(value for value in parent["folds"] if value["fold"] == fold["id"])
            new_result = next(value for value in report["folds"] if value["fold"] == fold["id"])
            old = pl.read_parquet(old_result["calendar_path"]).sort(["decision_us", "label_variant"])
            require(old.height == 27340 * 3, "Frozen original calendar count changed")
            joint = dataset.joint_rows(lower, upper)
            additions = []
            for variant in spec["variants"]:
                frame = labels.label_table(joint, decisions, variant, split="TRAIN", signal_kind="OBSERVED_FUTURE_FLOW_DIAGNOSTIC")
                labels.assert_nonoverlap(frame)
                frame = frame.with_columns(pl.lit(cutoff).alias("split_maturity_deadline_us"),
                    (pl.col("label_valid") & (pl.col("label_mature_us") <= cutoff)).fill_null(False).alias("diagnostic_outcome_valid"))
                require(not frame["diagnostic_outcome_valid"].any(), "Added TRAIN tail must never enter scored observations")
                additions.append(frame.select(old.columns))
            added = pl.concat(additions).sort(["decision_us", "label_variant"])
            require(added.height == 60, "Exactly60 added calendar rows per fold")
            combined = pl.concat([old, added]).sort(["decision_us", "label_variant"])
            preserved = combined.filter(~((pl.col("split") == "TRAIN") & (pl.col("decision_us") >= decisions[0])))
            bitwise_equal(old, preserved)
            bitwise_equal(old.filter(pl.col("diagnostic_outcome_valid")), combined.filter(pl.col("diagnostic_outcome_valid")))
            for variant in spec["variants"]:
                one = combined.filter(pl.col("label_variant") == variant)
                labels.assert_nonoverlap(one)
                train_start, validation_start, test_start, test_end = [day_us(date.fromisoformat(fold[key])) for key in
                    ("train_start", "validation_start", "test_start", "test_end_exclusive")]
                for split, low, high in (("TRAIN", train_start, validation_start), ("OOS_SCREENING", test_start, test_end)):
                    values = one.filter(pl.col("split") == split)["decision_us"].to_numpy()
                    require(np.array_equal(values, np.arange(low, high, MINUTE_US, dtype=np.int64)), "Complete split calendar differs: " + split)
                item = next(value for value in new_result["variants"] if value["variant"] == variant)
                require(item["train_valid"] == one.filter((pl.col("split") == "TRAIN") & pl.col("diagnostic_outcome_valid")).height
                    and item["test_valid"] == one.filter((pl.col("split") == "OOS_SCREENING") & pl.col("diagnostic_outcome_valid")).height, "Original scored counts changed")
                item["calendar_minutes"] += 20
                item["invalid_or_immature"] += 20
                require(item["calendar_minutes"] == one.height, "Updated calendar count mismatch")
            path = work / f"{fold['id']}-nonoverlap-full-calendar-v3.parquet"
            combined.write_parquet(path)
            roundtrip = pl.read_parquet(path).sort(["decision_us", "label_variant"])
            bitwise_equal(combined, roundtrip)
            new_result.update(calendar_path=str(path), calendar_sha256=file_sha(path))
            report["supplement"]["fold_checks"].append({"fold": fold["id"], "old_calendar_sha256": old_result["calendar_sha256"],
                "new_calendar_sha256": new_result["calendar_sha256"], "added_rows": added.height, "added_outcome_valid_rows": 0,
                "full_TRAIN_minutes_per_variant": 17280, "OOS_minutes_per_variant": 10080,
                "fit_cutoff_us_unchanged": cutoff, "original_all_rows_bitwise_unchanged": True, "original_scored_rows_bitwise_unchanged": True})
            added_rows += added.height
            progress.update("补齐完整训练日历并核对原统计", index + 1, 4, "fold", 已新增无资格行=added_rows)
        require(added_rows == spec["expected_added_rows"], "Added calendar total differs")
        require(canonical_sha(unchanged_statistics(report)) == statistics_sha, "Original96 descriptive pair statistics changed")
        require(spec["parent_report_sha256"] == file_sha(ROOT / spec["parent_report"])
            and all(file_sha(Path(path)) == digest for path, digest in old_calendar_hashes.items()), "Original parent artifacts changed")
        require(sources == {name: file_sha(ROOT / name) for name in sources}, "Source bytes changed during supplement")
        report["supplement"].update(added_rows=added_rows, added_outcome_valid_rows=0, expected_statistic_pairs=96,
            original_statistics_canonical_sha256=statistics_sha, new_statistics_canonical_sha256=statistics_sha,
            source_bytes_unchanged=True, original_artifacts_unchanged=True,
            parent_scope_gap_preserved="V2 omitted20 TRAIN calendar minutes per variant/fold; V3 restores them without granting retrospective V2 full-calendar acceptance")
        report["status"] = "PASS_CALENDAR_COMPLETENESS_SUPPLEMENT_NOT_P1_GATE"
    except Exception as error:
        report.update(error_type=type(error).__name__, reason=str(error))
        raise
    finally:
        report.update(elapsed_seconds=time.monotonic() - started, peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024, resources=resources.status())
        with output.open("x") as stream:
            json.dump(report, stream, indent=2, ensure_ascii=False, allow_nan=False)
        append_event(ROOT / "reports/experiment_registry.jsonl", {**event, "event_id": event["experiment_id"] + ":RESULT",
            "event_type": "FORMAL_RESULT", "success_failure": report["status"], "artifact_path": str(output.relative_to(ROOT)), "artifact_sha256": file_sha(output)})
        progress.stop.set()
        print(json.dumps({"status": report["status"], "output": str(output)}), flush=True)


if __name__ == "__main__":
    main()
