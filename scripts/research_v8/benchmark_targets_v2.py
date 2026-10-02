"""V2 integer/development receipt guards over preserved V1 fixed target rules."""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import polars as pl

if __package__:
    from . import benchmark_targets as _v1
    from . import labels_v3 as _time
else:
    import benchmark_targets as _v1
    import labels_v3 as _time

ROOT, SYMBOLS, TARGET_SCHEMA = _v1.ROOT, _v1.SYMBOLS, _v1.TARGET_SCHEMA
DAY_US, MINUTE_US, MEMBERS = _v1.DAY_US, _v1.MINUTE_US, _v1.MEMBERS
file_sha, frame_sha, require = _v1.file_sha, _v1.frame_sha, _v1.require
TargetPlan = _v1.TargetPlan
IMPLEMENTATION_VERSION = "V8_BENCHMARK_TARGET_INTENTS_V2_20261002"


def calendar_array(calendar):
    values = _time._minute_decisions(calendar, "benchmark calendar")
    require(len(values) >= 2 and np.all(np.diff(values) == MINUTE_US), "Identical complete minute decision calendar required")
    return values


def _integer_timestamp_columns(frame, names, *, allow_end=False):
    require(set(names) <= set(frame.columns), "Explicit timestamp columns required")
    for name in names:
        require(frame.schema[name] == pl.Int64, "Original integer timestamp schema required")
        known = frame[name].drop_nulls().to_numpy()
        if len(known):
            _time._timestamps(known, name, allow_end=allow_end)


@dataclass(frozen=True)
class FrozenReturnPredictions(_v1.FrozenReturnPredictions):
    def validate(self, calendar):
        calendar_array(calendar)
        for name in ("decision_us", "available_us"):
            require(self.frame.schema[name] == pl.Int64, "Frozen forecasts require original integer timestamps")
            _time._timestamps(self.frame[name].to_numpy(), f"frozen {name}")
        _time._stamp(self.receipt["fit_cutoff_us"], "frozen fit cutoff")
        _time._stamp(self.receipt["max_fitting_label_mature_us"], "frozen fitted maturity", allow_end=True)
        _time._duration(self.receipt["embargo_us"], "frozen embargo")
        _time._minute_decisions(self.receipt["forecast_decision_us"], "frozen forecast calendar")
        _time._integer_array(self.receipt["forecast_row_ids"], "frozen forecast row IDs")
        _time._integer_array(self.receipt["fit_row_ids"], "frozen fitting row IDs")
        _v1.FrozenReturnPredictions.validate(self, calendar)


def _version(plan):
    return TargetPlan(plan.strategy_id, plan.targets, plan.calendar_ledger,
        {**plan.receipt, "implementation_version": IMPLEMENTATION_VERSION,
         "preserved_V1_rule_source_sha256": file_sha(ROOT / "scripts/research_v8/benchmark_targets.py"),
         "integer_development_calendar_validated_before_coercion": True})


def fixed_targets(identifier, minute_closes, calendar, *, daily_returns=None, frozen_predictions=None):
    calendar = calendar_array(calendar)
    if identifier in ("SPOT_BUY_AND_HOLD", "VOL_MANAGED_BUY_AND_HOLD", "FIXED_TREND", "FIXED_MEAN_REVERSION"):
        _integer_timestamp_columns(minute_closes, ("close_us", "available_us"))
    if identifier == "VOL_MANAGED_BUY_AND_HOLD" and daily_returns is not None:
        _integer_timestamp_columns(daily_returns, ("day_end_us", "available_us"), allow_end=True)
    if frozen_predictions is not None:
        # Verify even a caller-supplied V1 receipt before the reused entry point.
        FrozenReturnPredictions(frozen_predictions.frame, frozen_predictions.receipt, frozen_predictions.model_artifact).validate(calendar)
    return _version(_v1.fixed_targets(identifier, minute_closes, calendar,
        daily_returns=daily_returns, frozen_predictions=frozen_predictions))


def causal_vol_multiplier(daily_returns, decision_us):
    _time._stamp(decision_us, "risk decision")
    _integer_timestamp_columns(daily_returns, ("day_end_us", "available_us"), allow_end=True)
    return _v1.causal_vol_multiplier(daily_returns, decision_us)


def partial_equal_risk_ensemble(plans, calendar, *, preregistered_missing_members):
    return _version(_v1.partial_equal_risk_ensemble(plans, calendar_array(calendar),
        preregistered_missing_members=preregistered_missing_members))


assert_paired_comparison = _v1.assert_paired_comparison


def acceptance_main():
    import argparse
    import hashlib
    import json
    import os
    import shlex
    import shutil
    import subprocess
    import sys
    from datetime import UTC, datetime
    from quant import resources
    from quant.paths import STATE
    if __package__:
        from .registry import FIELDS, append_event
    else:
        from registry import FIELDS, append_event

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acceptance", action="store_true", required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--run-dir", type=_v1.Path, required=True)
    parser.add_argument("--output", type=_v1.Path, required=True)
    args = parser.parse_args()
    run, output = args.run_dir.resolve(), args.output.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists(), "Exclusive D-native synthetic run directory")
    require(output.is_relative_to((ROOT / "reports/fast_research").resolve()) and not output.exists(), "Exclusive small report required")
    resources.status()
    require(bool(os.environ.get("COIN_TASK_ID")), "Actual long-run progress wrapper required")
    source_paths = ("scripts/research_v8/benchmark_targets.py", "tests/test_v8_benchmark_targets.py",
                    "scripts/research_v8/benchmark_targets_v2.py", "tests/test_v8_benchmark_targets_v2.py",
                    "protocols/BENCHMARK_CONTRACT_V1.json", "protocols/EXECUTION_COST_SCENARIOS_V8.json",
                    "protocols/LABEL_CONTRACT_V8.json", "scripts/research_v8/labels.py",
                    "scripts/research_v8/labels_v2.py", "scripts/research_v8/labels_v3.py",
                    "scripts/research_v8/registry.py", "src/quant/backtest.py", "src/quant/paths.py",
                    "src/quant/resources.py", "scripts/with_task_progress.sh", "scripts/bounded.sh",
                    "environments/v8/uv.lock")
    hashes = {name: file_sha(ROOT / name) for name in source_paths}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    argv = [sys.executable, "-m", "pytest", "tests/test_v8_benchmark_targets_v2.py", "-q",
        f"--basetemp={run / 'pytest'}", "-o", f"cache_dir={run / 'pytest-cache'}", f"--junitxml={run / 'junit.xml'}"]
    run.mkdir()
    for name in source_paths:
        snapshot = run / "source-snapshot" / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, snapshot)
    binding = {"experiment_id": args.experiment_id, "started_utc": datetime.now(UTC).isoformat(),
        "git_commit": head, "dirty_source_hashes": hashes,
        "data_scope": "DETERMINISTIC_SYNTHETIC_FIXTURES_NO_MARKET_IO",
        "data_manifest_hash": hashlib.sha256((hashes["tests/test_v8_benchmark_targets.py"] + hashes["tests/test_v8_benchmark_targets_v2.py"]).encode()).hexdigest(),
        "data_manifest_hash_scope": "Bound synthetic generator and mutation recipe bytes; not a historical market manifest",
        "benchmark_contract_sha256": hashes["protocols/BENCHMARK_CONTRACT_V1.json"],
        "cost_scenarios_sha256": hashes["protocols/EXECUTION_COST_SCENARIOS_V8.json"],
        "environment_lock_sha256": hashes["environments/v8/uv.lock"], "python": sys.executable,
        "seed": 20261002, "all_folds": [], "exact_test_command": shlex.join(argv),
        "actual_adapter_argv": sys.argv, "required_outer_wrapper": "scripts/with_task_progress.sh (inside bounded.sh)",
        "task_id": os.environ["COIN_TASK_ID"], "market_model_fit_calls": 0, "resources": resources.status()}
    with (run / "RUN_BINDING.json").open("x") as stream:
        json.dump(binding, stream, indent=2, allow_nan=False)
    event = dict.fromkeys(FIELDS)
    event.update(experiment_id=args.experiment_id, event_id=args.experiment_id + ":start", event_type="OPERATIONAL_START",
        git_commit=head, data_manifest_hash=binding["data_manifest_hash"], protocol_hash=binding["benchmark_contract_sha256"],
        feature_set="PAST_MINUTE_CLOSE_AND_PAST_DAILY_GROSS_EXPOSURE_RETURNS_SYNTHETIC_ONLY",
        labels="NO_MARKET_LABELS", model_family="NONE", hyperparameters={entry["id"]: entry["parameters"] for entry in _v1.contracts()[0]["benchmarks"]},
        seed=binding["seed"], thresholds={"trend_spans": [60, 240], "MR_entry_exit": [-2, 0], "MR_max_hold_minutes": 60, "XGB_bps": 35},
        cost_assumptions="NOT_PAID_SIGNAL_TARGET_TEST_ONLY", all_folds=[], success_failure="STARTED",
        reason_for_next_experiment="Fix confirmed original calendar dtype coercion while preserving first synthetic acceptance",
        result_influenced_later_choice=False, run_binding_sha256=file_sha(run / "RUN_BINDING.json"),
        source_hashes=hashes, environment_lock_sha256=binding["environment_lock_sha256"], exact_command=binding["exact_test_command"])
    append_event(ROOT / "reports/experiment_registry.jsonl", event)
    child_environment = {**os.environ, "COIN_V8_BENCHMARK_BINDING_FILE": str(run / "RUN_BINDING.json")}
    completed = subprocess.run(argv, cwd=ROOT, env=child_environment)
    unchanged = hashes == {name: file_sha(ROOT / name) for name in source_paths}
    status = "PASS_SYNTHETIC_CAUSAL_BENCHMARK_TARGET_V2_ADAPTER" if completed.returncode == 0 and unchanged else "FAIL_SYNTHETIC_BENCHMARK_TARGET_V2_ACCEPTANCE"
    receipt = {"status": status, "created_utc": datetime.now(UTC).isoformat(), "binding": binding,
        "run_binding_sha256": file_sha(run / "RUN_BINDING.json"), "actual_test_exit_code": completed.returncode,
        "source_bytes_unchanged": unchanged, "junit_path": str(run / "junit.xml"),
        "junit_sha256": file_sha(run / "junit.xml") if (run / "junit.xml").is_file() else None,
        "source_snapshot_preserved": True, "market_inputs_read": False, "market_model_fit_calls": 0,
        "locked_consumed": False, "GPU_hours": 0, "orders_sent": 0, "costs_paid": False,
        "benchmark_economic_gate": "NOT_EVALUATED", "complete_suite_evaluable": False,
        "P1_economic_gate_passed": False, "qualified_candidate": "NONE", "resources": resources.status()}
    with output.open("x") as stream:
        json.dump(receipt, stream, indent=2, allow_nan=False)
    append_event(ROOT / "reports/experiment_registry.jsonl", {**event, "event_id": args.experiment_id + ":result",
        "event_type": "OPERATIONAL_RESULT", "success_failure": status,
        "result_path": str(output.relative_to(ROOT)), "result_sha256": file_sha(output)})
    print(json.dumps({"status": status, "output": str(output), "return_code": completed.returncode}), flush=True)
    raise SystemExit(0 if status.startswith("PASS_") else 1)


if __name__ == "__main__":
    acceptance_main()
