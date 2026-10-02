"""One fixed chronological OOF flow -> impact pilot, four common horizons.

Reuse accepted raw features, sklearn scaling, XGBoost and the existing cash/NAV
accountant. July development only; future-valid selection is not executable.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import resource
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl
from sklearn.preprocessing import StandardScaler
from xgboost import XGBRegressor

from quant import resources
from quant.paths import ROOT, STATE
from quant.research_fast.dataset import (
    START, BAR_US, PAST_BARS, DAY_US, STREAMS, FEATURE_COLUMNS, FastSequenceDataset,
    ShardSpec, day_us, feature_matrix, tabular_view, file_sha, protocol,
)
from quant.research_fast.evaluation import ObservedPrices, economics, sample_id
from oracle_flow_ceiling import Progress, correlations, daily_correlations, exclusive_json

HORIZONS = (5, 15, 30, 60)
LAG_US = 3_610_000_000
EMBARGO_US = 3_600_000_000
SYMBOLS = ("BTCUSDT", "ETHUSDT")
SEED = 20261001


def array_sha(values):
    return hashlib.sha256(np.asarray(values).tobytes()).hexdigest()


def scaler_receipt(scaler):
    return {"implementation": "sklearn.preprocessing.StandardScaler", "mean": scaler.mean_.tolist(),
            "scale": scaler.scale_.tolist(), "var": scaler.var_.tolist(),
            "n_samples_seen": int(scaler.n_samples_seen_)}


class HorizonProxyBatch:
    """Horizon-specific field validation before the unchanged return-only accountant.

The accountant's four-slot array API consumes only slot 1. Slot 0 stores the real
Spot flow label; auxiliary slots are unused zeros and are never scored/reported.
This adapter deliberately does not label them as RV or 30s truth.
"""
    def __init__(self, frame, dataset_sha, minutes, entry_price, exit_price, observed, start, end):
        self.decision_us = frame["decision_us"].to_numpy()
        self.sample_ids = tuple(sample_id(dataset_sha, t) for t in self.decision_us)
        self.start_us, self.end_us = start, end
        self.observed = observed
        self.entry_us = np.column_stack([frame[f"spot_{s}__entry_{minutes}m_us"].to_numpy() for s in SYMBOLS])
        self.exit_us = np.column_stack([frame[f"spot_{s}__exit_{minutes}m_us"].to_numpy() for s in SYMBOLS])
        self.entry_price, self.exit_price = entry_price.copy(), exit_price.copy()
        self.truth = np.zeros((len(frame), 2, 4), np.float64)
        for s, symbol in enumerate(SYMBOLS):
            self.truth[:, s, 0] = frame[f"spot_{symbol}__flow_{minutes}m"].to_numpy()
            self.truth[:, s, 1] = frame[f"spot_{symbol}__return_{minutes}m_proxy"].to_numpy()
        for array in (self.truth, self.entry_price, self.exit_price, self.entry_us, self.exit_us):
            if not np.isfinite(array).all():
                raise ValueError("Finite horizon price/label fields required")
        decision = self.decision_us[:, None]
        if not (np.all(np.diff(self.decision_us) > 0)
                and np.all(self.decision_us >= start)
                and np.all(self.decision_us + LAG_US <= end)
                and np.all(self.entry_us >= decision + 5_000_000)
                and np.all(self.entry_us <= decision + 7_000_000)
                and np.all(self.exit_us >= decision + minutes * 60_000_000 + 5_000_000)
                and np.all(self.exit_us <= decision + minutes * 60_000_000 + 7_000_000)
                and np.all(self.entry_price > 0) and np.all(self.exit_price > 0)
                and np.allclose(self.exit_price / self.entry_price - 1, self.truth[:, :, 1], rtol=0, atol=1e-13)
                and all(p.available_us[-1] <= end for p in observed)):
            raise ValueError("Horizon price anchors/common maturity/chronology do not match")


def economic_summary(batch, prediction, directory, policy, minutes):
    shaped = np.zeros(batch.truth.shape)
    shaped[:, :, 1] = prediction
    output = {}
    for spread in (2, 4, 8):
        result = economics(batch, shaped, assumed_spread_bps=spread)
        prefix = directory / f"{policy}-{minutes}m-spread{spread}"
        result.trades.write_parquet(prefix.with_name(prefix.name + "-trades.parquet"))
        result.daily_nav.write_parquet(prefix.with_name(prefix.name + "-daily.parquet"))
        summary = result.summary
        notional = float(result.trades["reference_notional"].sum())
        returns = result.daily_nav["nav"].to_numpy() / np.r_[10000., result.daily_nav["nav"].to_numpy()[:-1]] - 1
        summary.update({"comparison_period_days": 7,
            "conditional_short_window_cagr_proxy": summary["annual_return"],
            "long_term_net_apr_proven": False,
            "break_even_roundtrip_cost_bps": 2 * summary["gross_pnl"] / notional * 10000 if notional else None,
            "break_even_formula": "2 * actual_same_quantity_gross_pnl / two_sided_reference_notional * 10000",
            "actual_two_sided_reference_notional": notional,
            "fee_fraction_initial_nav": summary["fees"] / 10000,
            "slippage_fraction_initial_nav": notional * 8 / 20000 / 10000,
            "spread_fraction_initial_nav": notional * spread / 20000 / 10000,
            "worst_1d_net_return": float(returns.min()),
            "worst_3d_compound_return": float(min(np.prod(1 + returns[i:i+3]) - 1 for i in range(len(returns)-2))),
            "terminal_positions_flat": bool(result.daily_nav["BTC_quantity"][-1] == 0 and result.daily_nav["ETH_quantity"][-1] == 0),
            "capacity_proven": False, "horizon_minutes": minutes,
            "accountant_reused_unchanged": "quant.research_fast.evaluation.economics",
            "unused_auxiliary_slots_never_scored": True})
        if abs(summary["gross_proxy_return"] - summary["estimated_cost"] - summary["net_proxy_return"]) > 1e-12:
            raise ValueError("Gross minus cost must equal actual net NAV return")
        output[str(spread)] = summary
    return output


def execute(args, progress):
    started = time.monotonic()
    run = args.run_dir.resolve()
    if not run.is_relative_to(STATE.resolve()) or run.exists():
        raise ValueError("New exclusive native STATE run directory required")
    run.mkdir()
    prior_path = ROOT / "reports/fast_research/V7_ORACLE_FLOW_HORIZON_20261002_V1.json"
    prior = json.loads(prior_path.read_text())
    prior_run = Path(prior["run_dir"])
    if json.loads((prior_run / "COMPLETE.json").read_text())["report_sha256"] != file_sha(prior_path):
        raise ValueError("Original oracle receipt differs")
    for key, sha in prior["binding"]["source_hashes"].items():
        if file_sha(ROOT / key) != sha:
            raise ValueError("Original oracle source binding differs")
    common = prior_run / "oracle_common_endpoints.parquet"
    if file_sha(common) != prior["artifacts"][common.name]:
        raise ValueError("Immutable common endpoints differ")
    frame = pl.read_parquet(common)
    decisions = frame["decision_us"].to_numpy()
    first = day_us(START)
    validation_start, test_start, test_end = first + 12 * DAY_US, first + 14 * DAY_US, first + 21 * DAY_US
    train = np.flatnonzero(decisions < validation_start - EMBARGO_US - LAG_US)
    validation = np.flatnonzero((decisions >= validation_start) & (decisions + LAG_US <= test_start - EMBARGO_US))
    test = np.flatnonzero((decisions >= test_start) & (decisions + LAG_US <= test_end))
    if {"train": len(train), "validation": len(validation), "test": len(test)} != prior["label_check"]["counts"]:
        raise ValueError("Exactly the same original four-horizon splits required")
    blocks = []
    for block, (start_day, end_day) in enumerate(((3, 6), (6, 9), (9, 12))):
        lower, upper = first + start_day * DAY_US, first + end_day * DAY_US
        fit = train[decisions[train] + LAG_US <= lower - EMBARGO_US]
        forecast = train[(decisions[train] >= lower) & (decisions[train] < upper)]
        if not len(fit) or not len(forecast):
            raise ValueError("Each chronological OOF block needs preceding mature data")
        blocks.append((block, lower, upper, fit, forecast))
    oof_rows = np.sort(np.concatenate([b[4] for b in blocks]))
    if len(oof_rows) != len(np.unique(oof_rows)):
        raise ValueError("OOF forecast blocks cannot overlap")
    source_keys = ("src/quant/research_fast/dataset.py", "src/quant/research_fast/labels.py",
                   "src/quant/research_fast/evaluation.py", "src/quant/metrics.py",
                   "scripts/research_v7/oracle_flow_ceiling.py", "scripts/research_v7/oof_flow_impact.py",
                   "protocols/fast_research_v6.json")
    hashes = {k: file_sha(ROOT / k) for k in source_keys}
    settings = {k: v for k, v in next(c for c in protocol()["configs"] if c["id"] == "XGB-S").items() if k not in ("id", "kind")}
    feature_names = [f"{stat}__{column}" for stat in ("last", "mean", "popstd") for column in FEATURE_COLUMNS]
    feature_names += [f"{symbol}__{state}" for symbol in SYMBOLS for state in ("past_logrv", "past_log_liquidity", "past_basis")]
    binding = {"status": "PREREGISTERED_V7_DEVELOPMENT_OOF_FLOW_IMPACT_PILOT",
        "prior_oracle_report_sha256": file_sha(prior_path), "prior_common_endpoints_sha256": file_sha(common),
        "dataset_sha256": prior["binding"]["dataset_sha256"], "source_hashes": hashes,
        "horizons_minutes": HORIZONS, "common_counts": {"train": len(train), "validation": len(validation), "test": len(test), "OOF_M2_direct_train": len(oof_rows)},
        "normalization": "canonical raw204 tabular(feature_matrix(past256)) + six oracle current-state features; one sklearn endpoint-summary scaler fit on each model's eligible fitting rows, never future/OOS rows; M2/direct share one exact OOF-row scaler",
        "feature_names": feature_names, "M1_features": "same 210 past-only features", "direct_features": "same 210 past-only features",
        "M2_features": "same 210 past-only features + four ORIGINAL-UNIT strictly chronological OOF predicted future flows",
        "M2_training_true_future_flow_inputs": False, "validation_used_for_selection": False,
        "fixed_settings": settings, "seed": SEED, "planned_fits": 24, "HPO": False,
        "OOF_blocks": [{"block": b, "forecast_start_us": lower, "forecast_stop_us": upper,
                        "max_fitting_label_available_us": int(decisions[fit].max() + LAG_US),
                        "fitting_label_deadline_us": lower - EMBARGO_US,
                        "fit_rows": len(fit), "forecast_rows": len(forecast),
                        "fit_indices_sha256": array_sha(fit), "forecast_indices_sha256": array_sha(forecast)}
                       for b, lower, upper, fit, forecast in blocks],
        "max_label_lag_seconds": 3610, "embargo_seconds": 3600,
        "no_gpu": True, "CPU_budget_seconds": 1800, "incremental_RAM_budget_bytes": 2000000000,
        "aggregate_RAM_hard_limit_bytes": 5000000000,
        "cost": {"fee_roundtrip_bps": 20, "slippage_roundtrip_bps": 8, "spread_roundtrip_bps": [2, 4, 8], "prediction_threshold_bps": 35},
        "risk": {"initial_nav": 10000, "new_buy_symbol_net_nav_max": .3, "new_buy_gross_net_nav_max": .6, "leverage": 0},
        "scope": "July development only, already-viewed rolling00 test, future-valid conditional samples, NOT unseen OOS or deployable qualification"}
    exclusive_json(run / "RUN_BINDING.json", binding)
    for name, array in (("decision_us", decisions), ("train_indices", train), ("validation_indices", validation), ("test_indices", test), ("OOF_indices", oof_rows)):
        np.save(run / (name + ".npy"), array, allow_pickle=False)
    sources = []
    for offset, (name, sha) in enumerate(prior["binding"]["manifests"].items()):
        path = ROOT / name
        if file_sha(path) != sha:
            raise ValueError("Accepted source manifest changed")
        sources.append(ShardSpec.from_manifest(path))
        progress.update("OOF 核对原120档来源", offset + 1, 120, "文件")
    dataset = FastSequenceDataset(sources, mode="smoke")
    if dataset.contract_sha256 != binding["dataset_sha256"]:
        raise ValueError("OOF must use exactly the same original 30-day dataset")
    state_names = feature_names[204:]
    x = np.empty((len(frame), 210), np.float32)
    x[:, 204:] = frame.select(state_names).to_numpy()
    entries = np.empty((len(test), 2), np.float64)
    exits = {h: np.empty((len(test), 2), np.float64) for h in HORIZONS}
    marks = [[] for _ in SYMBOLS]
    feature_checks = []
    for day in range(30):
        lower, upper = max(first, first + day * DAY_US - PAST_BARS * BAR_US), min(first + 30 * DAY_US, first + (day + 1) * DAY_US + LAG_US)
        joint = dataset.joint_rows(lower, upper)
        values = feature_matrix(joint)
        rows = np.flatnonzero((decisions >= first + day * DAY_US) & (decisions < first + (day + 1) * DAY_US))
        for row in rows:
            position = (int(decisions[row]) - lower) // BAR_US
            past = values[position - PAST_BARS:position]
            if past.shape != (256, 68):
                raise ValueError("Only exact already-closed past256 tensor can make canonical204")
            x[row, :204] = tabular_view(past)
        if len(rows):
            feature_checks.append({"utc_day_index": day, "rows": len(rows), "last_past_available_equals_decision": True})
        selected_test_positions = np.flatnonzero((decisions[test] >= first + day * DAY_US) & (decisions[test] < first + (day + 1) * DAY_US))
        for s, symbol in enumerate(SYMBOLS):
            for test_position in selected_test_positions:
                decision = int(decisions[test[test_position]])
                position = (decision - lower) // BAR_US
                entries[test_position, s] = joint[f"spot_{symbol}__open"][position + 1]
                for h in HORIZONS:
                    exits[h][test_position, s] = joint[f"spot_{symbol}__open"][position + h * 12 + 1]
            observed = joint.filter((pl.col("timestamp") >= first + day * DAY_US)
                                    & (pl.col("timestamp") < first + (day + 1) * DAY_US)
                                    & (pl.col(f"spot_{symbol}__available_us") >= test_start - PAST_BARS * BAR_US)
                                    & (pl.col(f"spot_{symbol}__available_us") <= test_end)
                                    & pl.col(f"spot_{symbol}__close").is_not_null()).select(
                                        pl.col(f"spot_{symbol}__available_us").alias("available_us"),
                                        pl.col(f"spot_{symbol}__close").alias("close"))
            if len(observed):
                marks[s].append(observed)
        progress.update("构建同一past204 / 当前state6", day + 1, 30, "UTC 日", 累计样本=int(np.searchsorted(decisions, first + (day+1)*DAY_US)))
    if not np.isfinite(x).all():
        raise ValueError("All shared current-state features must remain finite")
    np.save(run / "past_features210.npy", x, allow_pickle=False)
    np.save(run / "test_entry_prices.npy", entries, allow_pickle=False)
    for h, values in exits.items():
        np.save(run / f"test_exit_prices_{h}m.npy", values, allow_pickle=False)
    observed = tuple(ObservedPrices(pl.concat(pieces)["available_us"].to_numpy(), pl.concat(pieces)["close"].to_numpy()) for pieces in marks)
    for s, prices in enumerate(observed):
        np.save(run / f"observed-{SYMBOLS[s]}-times.npy", prices.available_us, allow_pickle=False)
        np.save(run / f"observed-{SYMBOLS[s]}-closes.npy", prices.close, allow_pickle=False)
    test_frame = frame.filter(pl.Series(np.isin(np.arange(len(frame)), test)))
    model_records, horizon_results, fit_counter = [], [], 0

    def fit_model(path, input_values, targets, fit_rows, x_scaler, y_scaler, *, role, horizon, deadline, forecast_rows):
        nonlocal fit_counter
        if time.monotonic() - started > 1800:
            raise RuntimeError("Fixed pilot CPU wall-clock budget exhausted; do not refit/restart silently")
        path.mkdir(parents=True)
        progress.update("OOF / control / impact 固定拟合", fit_counter, 24, "模型", 当前模型=role, 周期分钟=horizon)
        model = XGBRegressor(**settings, random_state=SEED)
        begin = time.monotonic()
        model.fit(input_values, y_scaler.transform(targets[fit_rows]))
        model.save_model(path / "model.json")
        np.save(path / "fit_indices.npy", fit_rows, allow_pickle=False)
        np.save(path / "forecast_indices.npy", forecast_rows, allow_pickle=False)
        record = {"role": role, "horizon_minutes": horizon, "fit_rows": len(fit_rows), "fit_first_decision_us": int(decisions[fit_rows[0]]),
                  "fit_last_decision_us": int(decisions[fit_rows[-1]]), "fit_max_label_available_us": int(decisions[fit_rows[-1]] + LAG_US),
                  "label_deadline_us": deadline, "forecast_first_decision_us": int(decisions[forecast_rows[0]]) if len(forecast_rows) else None,
                  "forecast_rows": len(forecast_rows), "fit_seconds": time.monotonic() - begin,
                  "fit_indices_sha256": array_sha(fit_rows), "forecast_indices_sha256": array_sha(forecast_rows),
                  "model_sha256": file_sha(path / "model.json"), "path": str(path.relative_to(run)),
                  "input_scaler": scaler_receipt(x_scaler), "target_scaler": scaler_receipt(y_scaler)}
        if record["fit_max_label_available_us"] > deadline:
            raise ValueError("All fitting targets must have matured before the declared deadline")
        exclusive_json(path / "FIT_RECEIPT.json", record)
        model_records.append({k: v for k, v in record.items() if k not in ("input_scaler", "target_scaler")})
        fit_counter += 1
        progress.update("OOF / control / impact 固定拟合", fit_counter, 24, "模型", 当前模型=role, 周期分钟=horizon)
        return model

    final_feature_scaler = StandardScaler().fit(x[train])
    impact_feature_scaler = StandardScaler().fit(x[oof_rows])
    for h in HORIZONS:
        y_flow = frame.select([f"{s}__flow_{h}m" for s in STREAMS]).to_numpy()
        y_return = frame.select([f"spot_{s}__return_{h}m_proxy" for s in SYMBOLS]).to_numpy()
        oof = np.full(y_flow.shape, np.nan, np.float64)
        for block, lower, upper, fit, forecast in blocks:
            scaler = StandardScaler().fit(x[fit])
            target_scaler = StandardScaler().fit(y_flow[fit])
            path = run / f"horizon-{h}m" / f"M1-OOF-{block}"
            model = fit_model(path, scaler.transform(x[fit]), y_flow, fit, scaler, target_scaler,
                              role=f"M1-OOF-{block}", horizon=h, deadline=lower - EMBARGO_US, forecast_rows=forecast)
            oof[forecast] = target_scaler.inverse_transform(model.predict(scaler.transform(x[forecast])))
            np.save(path / "forecast_original_units.npy", oof[forecast], allow_pickle=False)
        if not np.isfinite(oof[oof_rows]).all() or np.isfinite(oof[np.setdiff1d(np.arange(len(frame)), oof_rows)]).any():
            raise ValueError("M2 cannot receive any in-sample or non-OOF training flows")
        np.save(run / f"horizon-{h}m" / "OOF-predicted-flow.npy", oof, allow_pickle=False)
        flow_scaler = StandardScaler().fit(y_flow[train])
        final = fit_model(run / f"horizon-{h}m" / "M1-final", final_feature_scaler.transform(x[train]), y_flow, train,
                          final_feature_scaler, flow_scaler, role="M1-final", horizon=h,
                          deadline=validation_start - EMBARGO_US, forecast_rows=np.r_[validation, test])
        final_predictions = {name: flow_scaler.inverse_transform(final.predict(final_feature_scaler.transform(x[rows])))
                             for name, rows in (("validation", validation), ("test", test))}
        for name, values in final_predictions.items():
            np.save(run / f"horizon-{h}m" / f"M1-{name}-predicted-flow.npy", values, allow_pickle=False)
        predicted_flow_scaler = StandardScaler().fit(oof[oof_rows])
        impact_target_scaler = StandardScaler().fit(y_return[oof_rows])
        # Both branches see identical fitting rows and the same train-only past-state scaler.
        past_train = impact_feature_scaler.transform(x[oof_rows])
        impact_train = np.column_stack([past_train, predicted_flow_scaler.transform(oof[oof_rows])])
        direct = fit_model(run / f"horizon-{h}m" / "DIRECT-past-only", past_train, y_return, oof_rows,
                           impact_feature_scaler, impact_target_scaler, role="DIRECT-past-only", horizon=h,
                           deadline=validation_start - EMBARGO_US, forecast_rows=np.r_[validation, test])
        impact = fit_model(run / f"horizon-{h}m" / "M2-OOF-flow-impact", impact_train, y_return, oof_rows,
                           impact_feature_scaler, impact_target_scaler, role="M2-OOF-flow-impact", horizon=h,
                           deadline=validation_start - EMBARGO_US, forecast_rows=np.r_[validation, test])
        exclusive_json(run / f"horizon-{h}m" / "PREDICTED_FLOW_SCALER.json", scaler_receipt(predicted_flow_scaler))
        np.save(run / f"horizon-{h}m" / "M2-train-predicted-flow.npy", oof[oof_rows], allow_pickle=False)
        outputs = []
        batch = HorizonProxyBatch(test_frame, dataset.contract_sha256, h, entries, exits[h], observed, test_start, test_end)
        for name, model in (("DIRECT", direct), ("OOF_TWO_STAGE", impact)):
            predictions, metrics = {}, {}
            for split, indices in (("validation", validation), ("test", test)):
                inputs = impact_feature_scaler.transform(x[indices])
                if name == "OOF_TWO_STAGE":
                    inputs = np.column_stack([inputs, predicted_flow_scaler.transform(final_predictions[split])])
                value = impact_target_scaler.inverse_transform(model.predict(inputs))
                predictions[split] = value
                np.save(run / f"horizon-{h}m" / f"{name}-{split}-return-predictions.npy", value, allow_pickle=False)
                metrics[split] = {symbol: {**correlations(value[:, s], y_return[indices, s]),
                    "MAE_bps": float(np.mean(np.abs(value[:, s] - y_return[indices, s])) * 10000),
                    "zero_prediction_MAE_bps": float(np.mean(np.abs(y_return[indices, s])) * 10000),
                    "mean_prediction_bps": float(value[:, s].mean() * 10000),
                    "mean_truth_bps": float(y_return[indices, s].mean() * 10000)} for s, symbol in enumerate(SYMBOLS)}
            progress.update("同成本 / 风险 NAV 历史回放", (HORIZONS.index(h)*2)+(name == "OOF_TWO_STAGE"), 8, "对比", 周期分钟=h, 路线=name)
            economic = economic_summary(batch, predictions["test"], run / f"horizon-{h}m", name, h)
            outputs.append({"policy": name, "return_metrics": metrics, "economics": economic,
                "daily_test_return_association": {symbol: daily_correlations(decisions[test], predictions["test"][:, s], y_return[test, s]) for s, symbol in enumerate(SYMBOLS)}})
        horizon_results.append({"horizon_minutes": h,
            "M1_test_flow": {s: {**correlations(final_predictions["test"][:, i], y_flow[test, i]),
                "MAE": float(np.mean(np.abs(final_predictions["test"][:, i] - y_flow[test, i]))),
                "zero_prediction_MAE": float(np.mean(np.abs(y_flow[test, i]))),
                "mean_prediction": float(final_predictions["test"][:, i].mean()),
                "mean_truth": float(y_flow[test, i].mean())} for i, s in enumerate(STREAMS)},
            "M1_OOF_flow": {s: correlations(oof[oof_rows, i], y_flow[oof_rows, i]) for i, s in enumerate(STREAMS)},
            "M2_training_rows_sha256": array_sha(oof_rows), "true_future_flow_M2_inputs": False,
            "direct_two_stage_comparison": outputs})
    if fit_counter != 24 or time.monotonic() - started > 1800:
        raise ValueError("Exactly one fixed 24-fit recipe within the declared budget required")
    after = {k: file_sha(ROOT / k) for k in hashes}
    if after != hashes or file_sha(common) != binding["prior_common_endpoints_sha256"]:
        raise ValueError("Original sources/common labels changed")
    artifacts = {str(p.relative_to(run)): file_sha(p) for p in run.rglob("*") if p.is_file()}
    output = {"status": "V7_DEVELOPMENT_CHRONOLOGICAL_OOF_FLOW_IMPACT_PILOT_COMPLETE",
        "created_utc": datetime.now(UTC).isoformat(), "run_dir": str(run), "binding": binding,
        "binding_sha256": file_sha(run / "RUN_BINDING.json"), "feature_checks": feature_checks,
        "feature_shape": list(x.shape), "OOF_M2_training_rows": len(oof_rows),
        "fits_completed": fit_counter, "model_receipts": model_records, "horizons": horizon_results,
        "elapsed_seconds": time.monotonic() - started,
        "process_peak_ram_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "shared_cgroup": resources.status(), "gpu_hours": 0, "source_sha256_after": after,
        "artifacts": artifacts,
        "claim_limits": ["July development already inspected, one test regime, not unseen screening or long-term APR evidence.",
            "Every horizon shares original 9,281 future-valid conditional test endpoints. This filter is not causal inference.",
            "Real flow labels score M1 and fit preceding-mature M1 models; only strictly OOF flow predictions enter M2 fitting.",
            "Final M1 12-day fit and early OOF M1 3/6/9-day fits have differing training distributions; no calibration selected from test.",
            "No BBO, queue, actual impact/funding/borrow proof. Same frozen 20+8+2/4/8bps costs are assumptions, not actual executable fills.",
            "Seven-day annualization is a conditional CAGR proxy with large sampling uncertainty, not a long-term net APR claim.",
            "No locked data, GPU, account keys, leverage, money or original source/evidence modifications."]}
    exclusive_json(args.output, output)
    exclusive_json(run / "COMPLETE.json", {"status": output["status"], "report_sha256": file_sha(args.output), "report": str(args.output)})
    progress.update("OOF 两阶段与直接return对照完成", 24, 24, "固定模型", 样本=len(test), M2训练行=len(oof_rows))
    print(json.dumps({"status": output["status"], "output": str(args.output), "fits": fit_counter}, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output = args.output.resolve()
    if not args.output.is_relative_to((ROOT / "reports/fast_research").resolve()) or args.output.exists():
        raise ValueError("New exclusive small research report required")
    resources.status()
    progress = Progress()
    try:
        with (STATE / ".fr-first-round.lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            execute(args, progress)
    finally:
        progress.stop.set()
        progress.thread.join(timeout=3)


if __name__ == "__main__":
    main()
