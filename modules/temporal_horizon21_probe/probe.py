"""Reuse the fixed8-feature ridge recipe; change only the prespecified horizon."""

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from modules.temporal_predictability_probe.probe import (
    FOLDS,
    fit_ridge,
    load,
    metrics,
    predict,
    prefix_rows,
)
from modules.temporal_predictability_probe.probe import (
    PROTOCOL as DAILY_PROTOCOL,
)
from modules.temporal_two_expert.inputs import DAY_US

H = 21
TARGETS = (
    "CORE5_mean_21day_asset_cumulative_return",
    "21day_average_daily_CORE5_squared_asset_return",
)
PROTOCOL = dict(
    DAILY_PROTOCOL,
    schema="ONE_FIXED21DAY_EIGHT_FEATURE_TWO_TARGET_RIDGE_V1",
    horizon_days=H,
    forecast_starts=43,
    targets=list(TARGETS),
    target="mean_asset(close[t+21]/close[t]-1);mean_over21days(mean_over5assets(daily_simple_return_squared))",
    target_clock="complete22actualcloses;available_at_decision_plus21days",
    risk_name="21day_average_daily_squared_asset_return_proxy_NOT_intraday_realized_variance",
    baselines=["same_prefix_training_mean", "causal_latest20_fully_matured21day_target_mean"],
    final_forward_day="43starts;laststart_day42_ends_at_block_exclusive_end;no_outcome_day_outside63dayblock",
    training_dates="original778_nomination;all22closeclocks_in_same_original_wallet;feature_valid;label_end_strictly_before_fold",
    forward="same63daily_outcome_days;start0..42;endpoint<=block_exclusive_end;no_outcome_day_outsideblock",
    baseline="same_prefix_training_mean;mean_latest20_fully_matured21day_targets_at_calendar_starts_t-40..t-21",
    baseline_continuity="each_target_wholly_inside_one_original_wallet_or_current_forward_block;never_splice_gaps",
    trailing_missing="prefix_mean_fallback_if_any20eligible_matured_target_missing;report_count",
    overlap="43overlapping_forecasts_perblock;fixed_disjoint_starts0_21_42_cover63days;statistical_effective_N_unknown",
    outputs_per_fit=2,
    coefficients_per_fit=18,
    planned_closed_form_fits=4,
    no_horizon_grid=True,
    no_continuation=True,
    predecessor="nextday_probe_be9e4ef00cb13a13994c1ab400a7758aca388463_preserved",
)


def horizon_targets(close, observed, clocks, daily):
    if (
        close.shape != observed.shape
        or close.shape[1:] != (5,)
        or not np.all(np.diff(clocks) == DAY_US)
    ):
        raise ValueError("Real contiguous CORE5 close chronology required")
    if not np.array_equal(observed, np.isfinite(close) & (close > 0)):
        raise ValueError("Truthful close masks required")
    y = np.full((len(clocks), 2), np.nan)
    for i in range(len(clocks) - H):
        if observed[i : i + H + 1].all() and np.isfinite(daily[i : i + H]).all():
            y[i, 0] = (close[i + H] / close[i] - 1).mean()
            y[i, 1] = daily[i : i + H, 1].mean()
    return y, clocks + H * DAY_US


def wallet_windows(clocks, nominated):
    # A window must be wholly inside one genuine nominated segment, including
    # its observed endpoint. No price from the next wallet is appropriated.
    spans = np.split(nominated, np.flatnonzero(np.diff(nominated) != DAY_US) + 1)
    valid = np.zeros(len(clocks), bool)
    for span in spans:
        valid |= (clocks >= span[0]) & (clocks + H * DAY_US <= span[-1])
    return valid, [(int(s[0]), int(s[-1]), len(s)) for s in spans]


def forward_rows(clocks, ready, y, start):
    end = start + 63 * DAY_US
    dates = start + np.arange(63 - H + 1) * DAY_US
    rows = np.searchsorted(clocks, dates)
    if np.any(rows >= len(clocks)) or not np.array_equal(clocks[rows], dates):
        raise ValueError("All43 prescribed starts required")
    if (
        not ready[rows].all()
        or not np.isfinite(y[rows]).all()
        or np.any(clocks[rows] + H * DAY_US > end)
    ):
        raise ValueError("Every full21-day outcome must be observed inside the fixed63day block")
    return rows


def trailing21(y, available, clocks, rows, train_mean, wallet_valid, start):
    end = start + 63 * DAY_US
    in_block = (clocks >= start) & (available <= end)
    eligible = wallet_valid | in_block
    forecasts, fallback = [], 0
    for i in rows:
        prior = np.arange(max(0, i - H - 19), i - H + 1)
        if len(prior) != 20 or not eligible[prior].all() or not np.isfinite(y[prior]).all():
            forecasts.append(train_mean)
            fallback += 1
            continue
        if np.any(available[prior] > clocks[i]):
            raise ValueError("Every21day trailing target must mature by its forecast decision")
        forecasts.append(y[prior].mean(0))
    return np.asarray(forecasts), fallback


def evaluate(y, predictions):
    score = {name: metrics(y, p) for name, p in predictions.items()}
    for record in score.values():
        record["skill_vs_training_mean"] = 1 - record["MSE"] / score["training_mean"]["MSE"]
        record["skill_vs_trailing20_matured21"] = (
            1 - record["MSE"] / score["trailing20_matured21"]["MSE"]
        )
    return score


def run(state, destination):
    if destination.exists():
        raise FileExistsError("Exactly one immutable horizon experiment required")
    clocks, x, ready, daily, _, nominated, files = load(state)
    packet = json.loads((state / "FROZEN_PACKET.json").read_text())
    closes, masks = [], []
    for name in ["feature_npz", "development_npz"]:
        with np.load(state / packet["files"][name]["path"], allow_pickle=False) as z:
            closes.append(z["close"].copy())
            masks.append(z["close_observed_mask"].copy())
    y, available = horizon_targets(np.concatenate(closes), np.concatenate(masks), clocks, daily)
    wallet_valid, spans = wallet_windows(clocks, nominated)
    results, rows_out, snapshots = [], [], {}
    for date in FOLDS:
        start = int(np.datetime64(date, "us").astype(np.int64))
        train = prefix_rows(clocks, nominated, ready & wallet_valid, y, available, start)
        rows = forward_rows(clocks, ready, y, start)
        if len(train) < 30 or np.any(available[train] >= start):
            raise ValueError("Whole mature original-wallet labels required")
        fit = fit_ridge(x[train], y[train])
        p, raw = predict(fit, x[rows])
        means = np.tile(fit["intercept"], (len(rows), 1))
        trailing, fallback = trailing21(
            y, available, clocks, rows, fit["intercept"], wallet_valid, start
        )
        disjoint = np.arange(0, len(rows), H)
        assert disjoint.tolist() == [0, 21, 42]
        scores = {}
        for j, target in enumerate(TARGETS):
            values = {
                "ridge": p[:, j],
                "training_mean": means[:, j],
                "trailing20_matured21": trailing[:, j],
            }
            scores[target] = dict(
                overlapping=evaluate(y[rows, j], values),
                disjoint=evaluate(
                    y[rows[disjoint], j], {n: a[disjoint] for n, a in values.items()}
                ),
            )
            for k, i in enumerate(rows):
                rows_out.append(
                    dict(
                        fold=date,
                        target=target,
                        decision_us=int(clocks[i]),
                        label_available_us=int(available[i]),
                        fixed_disjoint=bool(k in disjoint),
                        observed=float(y[i, j]),
                        ridge=float(p[k, j]),
                        raw_ridge=float(raw[k, j]),
                        training_mean=float(means[k, j]),
                        trailing20_matured21=float(trailing[k, j]),
                    )
                )
        coverage = []
        for a, b, _ in spans:
            admitted = train[(clocks[train] >= a) & (clocks[train] <= b)]
            if len(admitted):
                last_end, count = -1, 0
                for i in admitted:
                    if clocks[i] >= last_end:
                        last_end, count = available[i], count + 1
                coverage.append(count)
        results.append(
            dict(
                fold=date,
                training_overlapping_labels=len(train),
                training_disjoint_label_coverage=sum(coverage),
                latest_training_label_available_us=int(available[train].max()),
                first_forward_decision_us=start,
                final_label_available_us=int(available[rows[-1]]),
                block_end_exclusive_us=start + 63 * DAY_US,
                overlapping_forecasts=43,
                disjoint_spans=3,
                disjoint_outcome_days=63,
                statistical_effective_N="UNKNOWN_not43_or3_independent_samples",
                trailing_fallbacks=fallback,
                negative_risk_clipping=int((raw[:, 1] < 0).sum()),
                scores=scores,
            )
        )
        for n, v in fit.items():
            snapshots[date + "_" + n] = v
        snapshots[date + "_train_decisions"] = clocks[train]
        snapshots[date + "_train_label_available"] = available[train]
    destination.mkdir(parents=True)
    with (destination / "PREDICTIONS.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows_out[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows_out)
    np.savez_compressed(destination / "PREFIX_SCALERS_COEFFICIENTS.npz", **snapshots)
    result = dict(
        status="FIXED21DAY_FOUR_BLOCK_PROBE_COMPLETE",
        protocol=PROTOCOL,
        sources=files,
        original_wallet_spans=spans,
        folds=results,
        overlap_forecast_count=172,
        fixed_disjoint_span_count=12,
        statistical_effective_N="UNKNOWN;serial_and_overlapping_dependence",
        fits=4,
        wallets=0,
        downloads=0,
        deep_updates=0,
    )
    (destination / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(
                status=result["status"],
                train=[f["training_overlapping_labels"] for f in results],
                forecasts=172,
                disjoint_spans=12,
            )
        )
    )


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--destination", type=Path, required=True)
    args = p.parse_args()
    run(args.state, args.destination)


if __name__ == "__main__":
    main()
