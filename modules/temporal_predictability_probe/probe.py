"""Eight fixed causal aggregates, two next-day targets, four closed-form fits."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from modules.temporal_two_expert.inputs import CORE5, DAY_US, FEATURE_NAMES, MARKET_CONTEXT

FEATURES = (
    "CORE5_mean_mom5",
    "CORE5_mean_mom20",
    "CORE5_mean_vol10",
    "CORE5_mean_vol30",
    "breadth5",
    "breadth20",
    "dispersion20",
    "market_vol20",
)
TARGETS = ("equal_weight_CORE5_next_daily_return", "CORE5_mean_squared_next_daily_asset_return")
FOLDS = ("2023-07-03", "2023-10-02", "2024-01-01", "2024-04-01")
PROTOCOL = dict(
    schema="FIXED_EIGHT_AGGREGATE_TWO_TARGET_PREFIX_RIDGE_V1",
    folds=list(FOLDS),
    forward_decisions=63,
    features=list(FEATURES),
    targets=list(TARGETS),
    feature_selection="canonical_names_fixed_before_forward_scoring;no_selection_or_grid",
    feature_semantics="four_CORE5_means;original_ten_asset_market_context_aggregates_unchanged",
    target="arithmetic_close_to_close_next_calendar_day;mean_asset_return_and_mean_squared_asset_return",
    target_clock="completed_close_at_decision_plus_one_day;real_observations_only;no_paidflat_labels",
    risk_name="daily_squared_asset_return_proxy_NOT_intraday_realized_variance",
    training_dates="original778_date_nomination;both_true_close_labels_observed;all8features_valid;label_available_strictly_before_foldstart",
    standardization="each_prefix_feature_mean_and_population_std_only;zero_std_to1",
    ridge_penalty=1.0,
    objective="mean_squared_error_plus_lambda_squared_slope_norm;unpenalized_intercept",
    target_scaling="none;fractions_and_fraction_squared",
    risk_forecast="clip_linear_forecast_at0_before_scoring;record_raw_negative_count",
    baselines=["same_prefix_training_mean", "causal_previous20_calendar_day_target_mean"],
    trailing_missing="fallback_to_prefix_mean_if_any_of20_true_prior_labels_missing;report_count",
    calibration="forward_bias_meanratio_correlation_and_OLS_actual_on_forecast;descriptive_not_used_to_adjust",
    final_forward_day="true_next_day_label_included;63_forecasts_unlike_policy62intervals_plus_paidclose",
    planned_closed_form_fits=4,
    outputs_per_fit=2,
    coefficients_per_fit=18,
    no_hyperparameter_grid=True,
    no_retuning=True,
    no_policy_or_profit_claim=True,
    classification="historical_project_seen_research;small63day_blocks;not_pristine_OOS",
    no_downloads=True,
    no_wallets=True,
    no_existing_model_changes=True,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def aggregates(x, valid):
    if x.shape != valid.shape or x.shape[1:] != (5, 24):
        raise ValueError("Exact CORE5/named24 feature matrix and masks required")
    indices = [FEATURE_NAMES.index(n) for n in ("mom5", "mom20", "vol10", "vol30")]
    global_indices = [FEATURE_NAMES.index(n) for n in FEATURES[4:]]
    local = x[:, :, indices].astype(np.float64)
    global_values = x[:, :, global_indices].astype(np.float64)
    if not np.array_equal(
        global_values, np.broadcast_to(global_values[:, :1], global_values.shape), equal_nan=True
    ):
        raise ValueError("Original market aggregates must remain identically broadcast")
    values = np.column_stack([local.mean(1), global_values[:, 0]])
    ready = valid[:, :, indices].all((1, 2)) & valid[:, :, global_indices].all((1, 2))
    ready &= np.isfinite(values).all(1)
    return values, ready


def targets(close, observed, clocks):
    if (
        close.shape != observed.shape
        or close.shape[1:] != (5,)
        or not np.all(np.diff(clocks) == DAY_US)
    ):
        raise ValueError("Actual contiguous daily CORE5 closes and explicit masks required")
    if not np.array_equal(observed, np.isfinite(close) & (close > 0)):
        raise ValueError("Truthful positive-close masks required")
    returns = close[1:] / close[:-1] - 1
    good = observed[:-1].all(1) & observed[1:].all(1)
    y = np.full((len(close), 2), np.nan)
    y[:-1, 0] = returns.mean(1)
    y[:-1, 1] = (returns**2).mean(1)
    y[:-1][~good] = np.nan
    available = np.r_[clocks[1:], clocks[-1] + DAY_US]
    return y, available


def prefix_rows(decisions, nominated, feature_ready, y, available, start):
    return np.flatnonzero(
        np.isin(decisions, nominated)
        & feature_ready
        & np.isfinite(y).all(1)
        & (decisions < start)
        & (available < start)
    )


def fit_ridge(x, y):
    if (
        x.ndim != 2
        or y.shape != (len(x), 2)
        or not np.isfinite(x).all()
        or not np.isfinite(y).all()
    ):
        raise ValueError("Finite observed two-target prefix required")
    mean, scale = x.mean(0), x.std(0)
    scale = np.where(scale > 0, scale, 1.0)
    z, intercept = (x - mean) / scale, y.mean(0)
    beta = np.linalg.solve(z.T @ z / len(z) + np.eye(x.shape[1]), z.T @ (y - intercept) / len(z))
    return dict(mean=mean, scale=scale, intercept=intercept, beta=beta)


def predict(fit, x):
    raw = (x - fit["mean"]) / fit["scale"] @ fit["beta"] + fit["intercept"]
    result = raw.copy()
    result[:, 1] = np.maximum(result[:, 1], 0)
    return result, raw


def trailing(y, available, clocks, rows, train_mean):
    result, fallback = [], 0
    for i in rows:
        history = np.arange(max(0, i - 20), i)
        if len(history) != 20 or not np.isfinite(y[history]).all():
            result.append(train_mean)
            fallback += 1
            continue
        if np.any(available[history] > clocks[i]):
            raise ValueError("Trailing forecast cannot read an immature target")
        result.append(y[history].mean(0))
    return np.asarray(result), fallback


def metrics(y, p):
    error = p - y
    variance = float(np.var(p))
    slope = float(np.mean((p - p.mean()) * (y - y.mean())) / variance) if variance > 1e-30 else None
    correlation = float(np.corrcoef(p, y)[0, 1]) if variance > 1e-30 and np.var(y) > 1e-30 else None
    return dict(
        MSE=float(np.mean(error**2)),
        bias=float(error.mean()),
        observed_mean=float(y.mean()),
        forecast_mean=float(p.mean()),
        forecast_to_observed_mean_ratio=float(p.mean() / y.mean()) if y.mean() != 0 else None,
        observed_std=float(y.std()),
        forecast_std=float(p.std()),
        correlation=correlation,
        calibration_slope=slope,
        calibration_intercept=float(y.mean() - slope * p.mean()) if slope is not None else None,
        sign_accuracy=float(np.mean(np.sign(p) == np.sign(y))),
    )


def load(state):
    packet_path = state / "FROZEN_PACKET.json"
    if sha(packet_path) != "0bd135091a913d67fec6af6da1f51a8cda80a09eca1da5a64582ebe68302ddea":
        raise ValueError("Exact prior frozen packet required")
    packet = json.loads(packet_path.read_text())
    parts, files = [], {"FROZEN_PACKET.json": sha(packet_path)}
    for key in ("feature_npz", "development_npz"):
        entry = packet["files"][key]
        path = state / entry["path"]
        if sha(path) != entry["SHA256"]:
            raise ValueError("Exact cached feature/close payload bytes required")
        files[entry["path"]] = sha(path)
        with np.load(path, allow_pickle=False) as z:
            if (
                tuple(z["feature_order"]) != FEATURE_NAMES
                or tuple(z["symbol_order"]) != CORE5
                or tuple(z["aggregate_context_asset_order"]) != MARKET_CONTEXT
            ):
                raise ValueError("Canonical feature/asset order required")
            parts.append(
                {
                    k: z[k].copy()
                    for k in [
                        "x",
                        "feature_observed_mask",
                        "close",
                        "close_observed_mask",
                        "completed_day_available_us",
                        "raw_observation_us",
                    ]
                }
            )
    a = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    clocks = a["completed_day_available_us"]
    if not np.array_equal(clocks, a["raw_observation_us"] + DAY_US) or not np.all(
        np.diff(clocks) == DAY_US
    ):
        raise ValueError("Real causal daily clock and contiguous append required")
    if not np.array_equal(
        a["feature_observed_mask"], np.isfinite(a["x"]) & a["close_observed_mask"][..., None]
    ):
        raise ValueError("Truthful original feature validity required")
    entry = packet["files"]["economic_npz"]
    path = state / entry["path"]
    if sha(path) != entry["SHA256"]:
        raise ValueError("Original date nomination identity required")
    files[entry["path"]] = sha(path)
    with np.load(path, allow_pickle=False) as z:
        nominated = z["decision_us"].copy()  # Dates only; never old paidflat prices/labels/wallets.
    if len(nominated) != 778 or np.any(np.diff(nominated) <= 0):
        raise ValueError("Exact original778 unique dates required")
    x, ready = aggregates(a["x"], a["feature_observed_mask"])
    y, available = targets(a["close"], a["close_observed_mask"], clocks)
    return clocks, x, ready, y, available, nominated, files


def run(state, destination):
    if destination.exists():
        raise FileExistsError("One immutable diagnostic result required")
    clocks, x, ready, y, available, nominated, files = load(state)
    destination.mkdir(parents=True)
    results, forecast_rows, snapshots = [], [], {}
    for date in FOLDS:
        start = int(np.datetime64(date, "us").astype(np.int64))
        train = prefix_rows(clocks, nominated, ready, y, available, start)
        dates = start + np.arange(63) * DAY_US
        rows = np.searchsorted(clocks, dates)
        if (
            np.any(rows >= len(clocks))
            or not np.array_equal(clocks[rows], dates)
            or not ready[rows].all()
            or not np.isfinite(y[rows]).all()
        ):
            raise ValueError("All63 true labels and fixed valid inputs required for " + date)
        if len(train) < 30 or np.any(available[train] >= start):
            raise ValueError("Strict mature prefix required")
        fit = fit_ridge(x[train], y[train])
        prediction, raw = predict(fit, x[rows])
        baseline = np.tile(fit["intercept"], (63, 1))
        trail, fallback = trailing(y, available, clocks, rows, fit["intercept"])
        scores = {}
        for j, target in enumerate(TARGETS):
            scores[target] = {
                name: metrics(y[rows, j], value[:, j])
                for name, value in [
                    ("ridge", prediction),
                    ("training_mean", baseline),
                    ("trailing20", trail),
                ]
            }
            for name in scores[target]:
                row = scores[target][name]
                row["skill_vs_training_mean"] = (
                    1 - row["MSE"] / scores[target]["training_mean"]["MSE"]
                )
                row["skill_vs_trailing20"] = 1 - row["MSE"] / scores[target]["trailing20"]["MSE"]
            for k, i in enumerate(rows):
                forecast_rows.append(
                    dict(
                        fold=date,
                        target=target,
                        decision_us=int(clocks[i]),
                        label_available_us=int(available[i]),
                        observed=float(y[i, j]),
                        ridge=float(prediction[k, j]),
                        raw_ridge=float(raw[k, j]),
                        training_mean=float(baseline[k, j]),
                        trailing20=float(trail[k, j]),
                    )
                )
        result = dict(
            fold=date,
            train_rows=len(train),
            nomination_before_start=int((nominated < start).sum()),
            latest_training_label_available_us=int(available[train].max()),
            first_forward_decision_us=start,
            forecast_rows=63,
            trailing20_fallback_rows=fallback,
            raw_negative_risk_forecasts=int((raw[:, 1] < 0).sum()),
            scores=scores,
        )
        results.append(result)
        for name, value in fit.items():
            snapshots[date + "_" + name] = value
        snapshots[date + "_train_decision_us"] = clocks[train]
        snapshots[date + "_train_label_available_us"] = available[train]
    with (destination / "PREDICTIONS.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(forecast_rows[0]))
        writer.writeheader()
        writer.writerows(forecast_rows)
    np.savez_compressed(destination / "PREFIX_SCALERS_COEFFICIENTS.npz", **snapshots)
    result = dict(
        status="ALL_FOUR_FIXED_PROBE_BLOCKS_COMPLETE",
        protocol=PROTOCOL,
        sources=files,
        folds=results,
        wallet_runs=0,
        deep_training_updates=0,
        downloads=0,
    )
    (destination / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(status=result["status"], prefix_rows=[r["train_rows"] for r in results], fits=4)
        )
    )
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--destination", type=Path, required=True)
    args = parser.parse_args()
    run(args.state, args.destination)


if __name__ == "__main__":
    main()
