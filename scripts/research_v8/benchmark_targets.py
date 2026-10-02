"""Fixed V8 benchmark target intents, not executable fills or economic results.

The three-column target schema is compatible with quant.backtest. That older
simulator's latency/risk differ from V8; schema compatibility is not replay
acceptance. No model fit, market data discovery or engine changes occur here.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import polars as pl

from quant.paths import ROOT
from quant.backtest import DAY_US, MINUTE_US, MAX_WEIGHT, MAX_GROSS, _frame
from quant.research_fast.dataset import LOCKED, START, day_us, file_sha

SYMBOLS = ("BTCUSDT", "ETHUSDT")
TARGET_SCHEMA = {"available_us": pl.Int64, "symbol": pl.String, "target_weight": pl.Float64}
MEMBERS = ("VOL_MANAGED_BUY_AND_HOLD", "FIXED_TREND", "FIXED_MEAN_REVERSION", "FUNDING_BASIS_CARRY", "CURRENT_XGB")
IMPLEMENTATION_VERSION = "V8_BENCHMARK_TARGET_INTENTS_V1_20261002"


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def contracts():
    benchmark = json.loads((ROOT / "protocols/BENCHMARK_CONTRACT_V1.json").read_text())
    costs = json.loads((ROOT / "protocols/EXECUTION_COST_SCENARIOS_V8.json").read_text())
    require(benchmark["contract_id"] == "BENCHMARK_CONTRACT_V1" and costs["contract_id"] == "EXECUTION_COST_SCENARIOS_V8", "Explicit fixed contracts required")
    require(file_sha(ROOT / benchmark["bindings"]["cost_scenarios_path"]) == benchmark["bindings"]["cost_scenarios_sha256"], "Cost scenario specification changed")
    return benchmark, costs


def frame_sha(frame):
    return hashlib.sha256(json.dumps(frame.to_dicts(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def calendar_array(calendar):
    values = np.asarray(calendar, dtype=np.int64)
    require(values.ndim == 1 and len(values) >= 2 and np.all(np.diff(values) == MINUTE_US)
            and np.all(values % MINUTE_US == 0), "Identical complete minute decision calendar required")
    require(values[0] >= day_us(START) and values[-1] < day_us(LOCKED), "Development calendar only; locked access forbidden")
    return values


@dataclass(frozen=True)
class TargetPlan:
    strategy_id: str
    targets: pl.DataFrame
    calendar_ledger: pl.DataFrame
    receipt: dict


def _plan(identifier, calendar, weights, reasons, *, warmup_failed=False, metadata=None):
    require(weights.shape == (len(calendar), 2) and np.isfinite(weights).all()
            and np.all(weights >= 0) and np.all(weights <= MAX_WEIGHT + 1e-12)
            and np.all(weights.sum(axis=1) <= MAX_GROSS + 1e-12), "Frozen unlevered symbol/gross caps")
    rows, ledger = [], []
    for index, stamp in enumerate(calendar):
        for symbol_index, symbol in enumerate(SYMBOLS):
            weight = float(weights[index, symbol_index])
            if index == 0 or weight != weights[index - 1, symbol_index]:
                rows.append({"available_us": int(stamp), "symbol": symbol, "target_weight": weight})
            ledger.append({"decision_us": int(stamp), "available_us": int(stamp), "symbol": symbol,
                "target_weight": weight, "reason": reasons[index][symbol_index],
                "earliest_permissible_order_us": int(stamp) + 5_000_000})
    targets, observed = _frame(rows, TARGET_SCHEMA), pl.DataFrame(ledger)
    receipt = {"implementation_version": IMPLEMENTATION_VERSION, "strategy_id": identifier,
        "status": "NOT_EVALUABLE_PAIRED_FOLD_WARMUP" if warmup_failed else "TARGET_INTENTS_ONLY",
        "calendar_sha256": hashlib.sha256(calendar.tobytes()).hexdigest(), "decision_count": len(calendar),
        "targets_sha256": frame_sha(targets), "warmup_failed": warmup_failed,
        "costs_paid": False, "executed_orders": 0, "economic_metrics": None,
        "P1_economic_gate_passed": False, "candidate_qualification_allowed": False,
        "old_engine_schema_compatible": True, "V8_execution_engine_accepted": False,
        "target_weights_are_intents_not_actual_holdings_or_fills": True,
        "terminal_exit_is_intent_only_needs_feasible_costed_fill": True,
        "paired_comparison_allowed": not warmup_failed, **(metadata or {})}
    return TargetPlan(identifier, targets, observed, receipt)


def causal_vol_multiplier(daily_returns, decision_us):
    """Official seven-completed-day EWMA on caller-bound gross exposure returns.

The return input is a portfolio's marked exposure return, not realized future
strategy PnL or an ex-post volatility computed over a full evaluation window.
"""
    require({"day_end_us", "available_us", "gross_exposure_return"} <= set(daily_returns.columns), "Explicit daily gross marked exposure inputs required")
    past = daily_returns.filter((pl.col("day_end_us") <= decision_us) & (pl.col("available_us") <= decision_us)).sort("day_end_us")
    if len(past) < 7:
        return None
    times, available, values = (past[key].to_numpy() for key in ("day_end_us", "available_us", "gross_exposure_return"))
    require(len(set(times.tolist())) == len(times) and np.all(times % DAY_US == 0)
            and np.all(available >= times), "Completed unique UTC daily inputs with causal availability")
    if np.any(np.diff(times) != DAY_US) or not np.isfinite(values).all() or np.any(values <= -1):
        return None
    if times[-1] != decision_us // DAY_US * DAY_US:
        return None  # A missing completed day is not guessed or forward filled.
    estimate = float(pl.Series(values).ewm_std(span=7, adjust=False, bias=False, min_samples=7)[-1]) * np.sqrt(365)
    if not np.isfinite(estimate):
        return None
    return min(1., .10 / max(.01, estimate))


def _past_closes(bars, symbol, stamp):
    required = {"symbol", "close_us", "available_us", "close"}
    require(required <= set(bars.columns), "Minute closes need close/availability stamps")
    known = bars.filter((pl.col("symbol") == symbol) & (pl.col("close_us") <= stamp)).sort("close_us")
    if not len(known) or known["close_us"][-1] != stamp:
        return None, "MISSING_CURRENT_CLOSED_MINUTE"
    times, available, prices = (known[key].to_numpy() for key in ("close_us", "available_us", "close"))
    require(len(set(times.tolist())) == len(times) and np.all(times % MINUTE_US == 0), "Duplicate or nonminute close")
    valid = np.isfinite(prices) & (prices > 0) & np.isfinite(available) & (available >= times) & (available <= stamp)
    if not valid[-1]:
        return None, "UNAVAILABLE_CURRENT_CLOSE"
    # Begin after the last unavailable value/time gap. Rebuild official EWMA on
    # the continuous causal segment; unavailable older values never enter state.
    breaks = np.flatnonzero((~valid[:-1]) | (np.diff(times) != MINUTE_US))
    start = int(breaks[-1] + 1) if len(breaks) else 0
    return prices[start:], "AVAILABLE_PAST_ONLY"


@dataclass(frozen=True)
class FrozenReturnPredictions:
    frame: pl.DataFrame
    receipt: dict
    model_artifact: Path

    def validate(self, calendar):
        proof = self.receipt
        require(self.model_artifact.is_file() and file_sha(self.model_artifact) == proof["model_sha256"], "Actual already-frozen artifact SHA required")
        require(frame_sha(self.frame) == proof["predictions_sha256"], "Frozen prediction bytes changed")
        require(proof["labels"] == "V8_NONOVERLAP_DIRECT_RETURN_BASELINE"
                and proof["label_contract_sha256"] == file_sha(ROOT / "protocols/LABEL_CONTRACT_V8.json"), "Legacy overlapping XGB cannot be called V8 matched baseline")
        require(all(len(proof[key]) == 64 and all(c in "0123456789abcdef" for c in proof[key])
                    for key in ("strategy_source_sha256", "data_manifest_sha256")), "Frozen source/data provenance required")
        require(proof["label_implementation_source_sha256"] == file_sha(ROOT / "scripts/research_v8/labels_v3.py"), "Exact current V8 label implementation binding required")
        require(proof["fit_cutoff_us"] + proof["embargo_us"] < int(calendar[0])
                and proof["max_fitting_label_mature_us"] <= proof["fit_cutoff_us"], "Frozen forecast fit must precede mature scored decisions")
        require(tuple(proof["forecast_decision_us"]) == tuple(calendar.tolist())
                and len(proof["forecast_row_ids"]) == len(calendar)
                and len(set(proof["forecast_row_ids"])) == len(calendar)
                and not set(proof["forecast_row_ids"]) & set(proof["fit_row_ids"]), "Exact forecast calendar and excluded fitting row IDs required")
        require(self.frame.height == len(calendar) * 2, "Same complete two-symbol forecast calendar")
        for stamp in calendar:
            rows = self.frame.filter(pl.col("decision_us") == stamp)
            require(set(rows["symbol"].to_list()) == set(SYMBOLS) and len(rows) == 2
                    and rows["predicted_return"].is_finite().all()
                    and rows["available_us"].is_finite().all()
                    and rows["available_us"].max() <= stamp, "Finite past-only forecasts for both symbols required")


def fixed_targets(identifier, minute_closes, calendar, *, daily_returns=None, frozen_predictions=None):
    benchmark, costs = contracts()
    require(identifier in {entry["id"] for entry in benchmark["benchmarks"]} - {"EQUAL_RISK_ENSEMBLE"}, "Only frozen standalone benchmark IDs")
    calendar = calendar_array(calendar)
    weights = np.zeros((len(calendar), 2))
    reasons = [["CASH" for _ in SYMBOLS] for _ in calendar]
    if identifier == "FUNDING_BASIS_CARRY":
        return _plan(identifier, calendar, weights, reasons, metadata={"status": "NOT_EVALUABLE_MISSING_OWN_VENUE_FUNDING_MARGIN_EXECUTION_INPUTS", "paired_comparison_allowed": False,
            "missing_inputs": next(b for b in benchmark["benchmarks"] if b["id"] == identifier)["current_missing_inputs"]})
    if identifier == "CURRENT_XGB" and frozen_predictions is None:
        return _plan(identifier, calendar, weights, reasons, metadata={"status": "NOT_EVALUABLE_NO_V8_FROZEN_PREDICTIONS", "paired_comparison_allowed": False})
    if identifier == "CURRENT_XGB":
        frozen_predictions.validate(calendar)
    holding = [None, None]
    warmup_failed = False
    vol_multiplier = None
    for index, stamp in enumerate(calendar):
        for s, symbol in enumerate(SYMBOLS):
            if identifier == "CASH":
                continue
            if identifier == "CURRENT_XGB":
                value = frozen_predictions.frame.filter((pl.col("decision_us") == stamp) & (pl.col("symbol") == symbol))["predicted_return"][0]
                weights[index, s] = MAX_WEIGHT if value >= .0035 else 0.
                reasons[index][s] = "FROZEN_PAST_ONLY_RETURN_THRESHOLD_35BP_INTENT_NOT_HOLDING_RULE"
                continue
            prices, reason = _past_closes(minute_closes, symbol, int(stamp))
            if prices is None:
                reasons[index][s] = reason
                warmup_failed = True
                continue
            if identifier in ("SPOT_BUY_AND_HOLD", "VOL_MANAGED_BUY_AND_HOLD"):
                if identifier == "VOL_MANAGED_BUY_AND_HOLD":
                    if daily_returns is None:
                        vol_multiplier = None
                    elif s == 0 and (index == 0 or stamp % DAY_US == 0):
                        vol_multiplier = causal_vol_multiplier(daily_returns, int(stamp))
                    if vol_multiplier is None:
                        reasons[index][s] = "INSUFFICIENT_SEVEN_COMPLETED_DAILY_GROSS_RETURNS"
                        warmup_failed = True
                        continue
                weights[index, s] = MAX_WEIGHT * (vol_multiplier if identifier == "VOL_MANAGED_BUY_AND_HOLD" else 1.)
                reasons[index][s] = "CAPPED_HOLD_INTENT" if identifier == "SPOT_BUY_AND_HOLD" else "DAILY_EWMA_DOWNSCALED_HOLD_INTENT"
            elif identifier == "FIXED_TREND":
                if len(prices) < 240:
                    reasons[index][s], warmup_failed = "INSUFFICIENT_CONTIGUOUS_240_MINUTE_WARMUP", True
                    continue
                series = pl.Series(prices)
                fast = series.ewm_mean(span=60, adjust=False, min_samples=240)[-1]
                slow = series.ewm_mean(span=240, adjust=False, min_samples=240)[-1]
                weights[index, s] = MAX_WEIGHT if fast > slow else 0.
                reasons[index][s] = "FIXED_EWMA60_GREATER_THAN_EWMA240" if fast > slow else "FIXED_TREND_FLAT"
            elif identifier == "FIXED_MEAN_REVERSION":
                if len(prices) < 61:
                    reasons[index][s], warmup_failed = "INSUFFICIENT_PRECEDING_60_MINUTE_WARMUP", True
                    holding[s] = None
                    continue
                logs = pl.Series(prices).log()
                mean = logs.rolling_mean(60, min_samples=60).shift(1)[-1]
                std = logs.rolling_std(60, min_samples=60, ddof=0).shift(1)[-1]
                if not np.isfinite(std) or std <= 0:
                    holding[s], reasons[index][s] = None, "ZERO_STD_ABSTAIN"
                    continue
                z = (logs[-1] - mean) / std
                if holding[s] is not None and (z >= 0 or stamp - holding[s] >= 60 * MINUTE_US):
                    holding[s] = None
                    reasons[index][s] = "MR_Z0_OR_60MINUTE_INTENT_EXIT"
                elif holding[s] is None and z <= -2:
                    holding[s] = int(stamp)
                    reasons[index][s] = "MR_PRECEDING60_Z_NEGATIVE2_INTENT_ENTRY"
                else:
                    reasons[index][s] = "MR_HOLD_OR_ABSTAIN"
                weights[index, s] = MAX_WEIGHT if holding[s] is not None else 0.
    weights[-1] = 0  # Intent only; fills/terminal quote feasibility remain unproved.
    reasons[-1] = ["COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL"] * 2
    return _plan(identifier, calendar, weights, reasons, warmup_failed=warmup_failed,
        metadata={"benchmark_contract_sha256": file_sha(ROOT / "protocols/BENCHMARK_CONTRACT_V1.json"),
                  "cost_scenarios_sha256": file_sha(ROOT / "protocols/EXECUTION_COST_SCENARIOS_V8.json"),
                  "cost_scenario_evaluated": None, "full_suite_available": False})


def partial_equal_risk_ensemble(plans, calendar, *, preregistered_missing_members):
    calendar = calendar_array(calendar)
    missing = tuple(member for member in MEMBERS if member not in plans or not plans[member].receipt["paired_comparison_allowed"])
    require(tuple(preregistered_missing_members) == missing, "Missing sleeves must be registered consistently before outcomes")
    require(len(missing) > 0, "This adapter may only name an explicitly partial ensemble")
    weights = np.zeros((len(calendar), 2))
    for member in MEMBERS:
        if member in missing:
            continue
        plan = plans[member]
        require(plan.receipt["calendar_sha256"] == hashlib.sha256(calendar.tobytes()).hexdigest(), "Identical ensemble calendar required")
        for s, symbol in enumerate(SYMBOLS):
            values = plan.calendar_ledger.filter(pl.col("symbol") == symbol).sort("decision_us")
            require(np.array_equal(values["decision_us"].to_numpy(), calendar), "Same sleeve decision IDs")
            weights[:, s] += .2 * values["target_weight"].to_numpy()
    reasons = [["ABSENT_SLEEVE_0_2_BUDGET_REMAINS_CASH_NO_RENORMALIZATION"] * 2 for _ in calendar]
    return _plan("PARTIAL_ENSEMBLE_WITH_CASH_FOR_UNAVAILABLE_SLEEVES", calendar, weights, reasons,
        metadata={"missing_members": list(missing), "cash_reserved_sleeve_budget": len(missing) * .2,
                  "sleeve_budget": .2, "risk_scaling_of_all_sleeves_accepted": False,
                  "economic_comparison_status": "NOT_EVALUABLE_UNTIL_SHARED_SLEEVE_RISK_AND_EXECUTION_ADAPTER",
                  "paired_comparison_allowed": False, "full_ensemble_evaluable": False})


def assert_paired_comparison(plans):
    require(len(plans) >= 2, "At least two paired benchmark plans")
    require(len({plan.receipt["calendar_sha256"] for plan in plans}) == 1, "No strategy-specific scored calendars")
    require(all(plan.receipt["paired_comparison_allowed"] and not plan.receipt["warmup_failed"] for plan in plans), "Entire paired fold NOT_EVALUABLE with missing inputs/warmup")
    return {"common_signal_calendar_verified": True, "economic_scoring_allowed": False,
            "reason": "Target signals only; costs, arrivals, risk and feasible fills not accepted"}


def acceptance_main():
    """Register actual synthetic acceptance before execution, preserve failures."""
    import argparse
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
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run, output = args.run_dir.resolve(), args.output.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists(), "Exclusive D-native synthetic run directory")
    require(output.is_relative_to((ROOT / "reports/fast_research").resolve()) and not output.exists(), "Exclusive small report required")
    resources.status()
    require(bool(os.environ.get("COIN_TASK_ID")), "Actual long-run progress wrapper required")
    source_paths = ("scripts/research_v8/benchmark_targets.py", "tests/test_v8_benchmark_targets.py",
                    "protocols/BENCHMARK_CONTRACT_V1.json", "protocols/EXECUTION_COST_SCENARIOS_V8.json",
                    "protocols/LABEL_CONTRACT_V8.json", "scripts/research_v8/labels_v3.py",
                    "src/quant/backtest.py", "environments/v8/uv.lock")
    hashes = {name: file_sha(ROOT / name) for name in source_paths}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    argv = [sys.executable, "-m", "pytest", "tests/test_v8_benchmark_targets.py", "-q",
        f"--basetemp={run / 'pytest'}", "-o", f"cache_dir={run / 'pytest-cache'}", f"--junitxml={run / 'junit.xml'}"]
    run.mkdir()
    for name in source_paths:
        snapshot = run / "source-snapshot" / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, snapshot)
    binding = {"experiment_id": args.experiment_id, "started_utc": datetime.now(UTC).isoformat(),
        "git_commit": head, "dirty_source_hashes": hashes, "data_scope": "DETERMINISTIC_SYNTHETIC_FIXTURES_NO_MARKET_IO",
        "data_manifest_hash": hashes["tests/test_v8_benchmark_targets.py"], "data_manifest_hash_scope": "Synthetic generator recipe bytes, not historical market manifest",
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
        labels="NO_MARKET_LABELS", model_family="NONE", hyperparameters={b["id"]: b["parameters"] for b in contracts()[0]["benchmarks"]},
        seed=binding["seed"], thresholds={"trend_spans": [60, 240], "MR_entry_exit": [-2, 0], "MR_max_hold_minutes": 60, "XGB_bps": 35},
        cost_assumptions="NOT_PAID_SIGNAL_TARGET_TEST_ONLY", all_folds=[], success_failure="STARTED",
        reason_for_next_experiment="Verify causal fixed benchmark target intents before any economic adapter",
        result_influenced_later_choice=False, run_binding_sha256=file_sha(run / "RUN_BINDING.json"),
        source_hashes=hashes, environment_lock_sha256=binding["environment_lock_sha256"], exact_command=binding["exact_test_command"])
    append_event(ROOT / "reports/experiment_registry.jsonl", event)
    completed = subprocess.run(argv, cwd=ROOT)
    unchanged = hashes == {name: file_sha(ROOT / name) for name in source_paths}
    status = "PASS_SYNTHETIC_CAUSAL_BENCHMARK_TARGET_ADAPTER" if completed.returncode == 0 and unchanged else "FAIL_SYNTHETIC_BENCHMARK_TARGET_ACCEPTANCE"
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
