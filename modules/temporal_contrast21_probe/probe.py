"""Change only the targets of the frozen eight-feature, lambda1 ridge recipe."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from modules.temporal_predictability_probe.probe import FEATURES, FOLDS, fit_ridge, metrics
from modules.temporal_two_expert.inputs import DAY_US

H = 21
TARGETS = ("VOL_MINUS_SHORT", "VOL_MINUS_CS")
PROTOCOL = dict(
    schema="ONE_FIXED21DAY_SIGNED_STANDALONE_CONTRAST_RIDGE_V1",
    features=list(FEATURES),
    targets=list(TARGETS),
    folds=list(FOLDS),
    ridge_penalty=1.0,
    objective="mean_squared_error_plus_lambda_squared_slope_norm;unpenalized_intercept",
    standardization="same_prefix_feature_mean_and_population_std;zero_std_to1",
    target_scaling="none;signed_fractional_NAV_return_differences",
    outputs=2,
    coefficients_per_fit=18,
    planned_fits=4,
    target="(VOL_NAV[k+21]/VOL_NAV[k]-1)-(other_NAV[k+21]/other_NAV[k]-1)",
    wallet="each_original_standalone_cash10000_path;existing_ramp_mapper_costs_funding_risk_reductions_paid_terminal",
    path_state="inherited_standalone_holdings;not_fresh21day_wallets_or_realizable_shared_wallet_switching",
    training="original778_nomination;full21activeintervals_in_one_original_wallet;all8features_valid;actual_outcome_clock_strictly_before_fold",
    forward="same_original63decision_blocks;42full21active_windows;fixed_disjoint0_21",
    truncated="start42_has20activeintervals_plus_paidclose;separate_secondary_record_never_full21_training_or_primary_score",
    predictions="both_outputs_signed;no_nonnegative_risk_clip",
    direction="sign(forecast)==sign(contrast);zero_threshold_fixed;zero_prediction_abstains;contrast_ties_excluded_and_counted",
    baselines=["same_prefix_contrast_mean", "constant_VOL_action"],
    constant_VOL_error="decision_error1-sign_agreement;MSE_undefined_for_action_without_forecast_magnitude",
    classification="repeatedly_examined_historical_development;not_new_pristine_OOS",
    effective_N="UNKNOWN;42overlap_windows_and2full_disjoint_spans_are_not_independent_sample_counts",
    no_grid=True,
    no_threshold_optimization=True,
    no_neural_training=True,
    no_downloads=True,
    no_native_rollouts=True,
    no_shared_wallet_policy=True,
    stop="exactly_one_specification_four_closed_form_fits_regardless_of_outcome;no_continuation",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def path_windows(decisions, outcome_available, nav):
    """Preserve chronology; expose the final paid-close span as a different label."""
    n = len(decisions)
    if (
        n < H + 1
        or nav.shape != (n + 1,)
        or outcome_available.shape != decisions.shape
        or not np.all(np.diff(decisions) == DAY_US)
        or not np.isfinite(nav).all()
        or np.any(nav <= 0)
        or nav[0] != 10000
        or np.any(outcome_available[:-1] < decisions[:-1] + DAY_US)
    ):
        raise ValueError("One complete causal positive standalone wallet required")
    starts = np.arange(n - H)
    values = nav[starts + H] / nav[starts] - 1
    available = outcome_available[starts + H - 1]
    boundary = n - H  # 20 active intervals and the original last paid close.
    return (
        starts,
        values,
        available,
        dict(
            start_index=boundary,
            decision_us=int(decisions[boundary]),
            outcome_available_us=int(outcome_available[-1]),
            value=float(nav[-1] / nav[boundary] - 1),
            active_intervals=20,
            includes_paid_close=True,
        ),
    )


def prefix_rows(cache, start):
    return np.flatnonzero(
        cache["train_ready"]
        & np.isfinite(cache["train_y"]).all(1)
        & (cache["train_decisions"] < start)
        & (cache["train_label_available"] < start)
    )


def predict_signed(fit, x):
    return (x - fit["mean"]) / fit["scale"] @ fit["beta"] + fit["intercept"]


def score(y, prediction, prefix_mean):
    nonzero = y != 0
    baselines = dict(ridge=prediction, prefix_mean=np.full(len(y), prefix_mean))
    records = {}
    for name, p in baselines.items():
        record = metrics(y, p)
        agreement = (
            float(np.mean(np.sign(p[nonzero]) == np.sign(y[nonzero]))) if nonzero.any() else None
        )
        record.update(
            sign_agreement=agreement,
            decision_error_rate=1 - agreement if agreement is not None else None,
            contrast_ties=int((~nonzero).sum()),
            zero_forecasts=int((p == 0).sum()),
        )
        records[name] = record
    constant_agreement = float(np.mean(y[nonzero] > 0)) if nonzero.any() else None
    records["constant_VOL"] = dict(
        sign_agreement=constant_agreement,
        decision_error_rate=1 - constant_agreement if constant_agreement is not None else None,
        MSE=None,
        MSE_reason=PROTOCOL["constant_VOL_error"],
        contrast_ties=int((~nonzero).sum()),
    )
    for name in baselines:
        record = records[name]
        record["MSE_skill_vs_prefix_mean"] = (
            1 - record["MSE"] / records["prefix_mean"]["MSE"]
            if records["prefix_mean"]["MSE"] > 0
            else None
        )
        for baseline in ("prefix_mean", "constant_VOL"):
            ref = records[baseline]["sign_agreement"]
            record["sign_improvement_vs_" + baseline] = (
                record["sign_agreement"] - ref if ref is not None else None
            )
    return records


def run(cache_path, metadata_path, destination):
    if destination.exists():
        raise FileExistsError("One immutable fixed-specification result required")
    metadata = json.loads(metadata_path.read_text())
    if sha(cache_path) != metadata["cache_SHA256"]:
        raise ValueError("Frozen prepared cache identity required")
    with np.load(cache_path, allow_pickle=False) as z:
        cache = {k: z[k].copy() for k in z.files}
    records, rows, boundary_rows, snapshots = [], [], [], {}
    for fold_index, date in enumerate(FOLDS):
        start = int(np.datetime64(date, "us").astype(np.int64))
        train = prefix_rows(cache, start)
        if len(train) < 30 or np.any(cache["train_label_available"][train] >= start):
            raise ValueError("Complete mature original-wallet prefix required")
        # Exactly one shared two-output fit; no alternate target/penalty/threshold.
        fit = fit_ridge(cache["train_x"][train], cache["train_y"][train])
        x, y = cache["forward_x"][fold_index], cache["forward_y"][fold_index]
        decisions, available = (
            cache["forward_decisions"][fold_index],
            cache["forward_label_available"][fold_index],
        )
        np.testing.assert_array_equal(decisions, start + np.arange(43) * DAY_US)
        np.testing.assert_array_equal(available[:42], decisions[:42] + H * DAY_US + 60000001)
        if y.shape != (43, 2) or not np.isfinite(x).all() or not np.isfinite(y).all():
            raise ValueError("All42full and one explicitly partial forward labels required")
        p = predict_signed(fit, x)
        scores = {}
        for j, target in enumerate(TARGETS):
            scores[target] = dict(
                full21active_overlap=score(y[:42, j], p[:42, j], fit["intercept"][j]),
                fixed_full_disjoint=score(y[[0, 21], j], p[[0, 21], j], fit["intercept"][j]),
                truncated20active_plus_paid_close=score(y[42:, j], p[42:, j], fit["intercept"][j]),
            )
            for k in range(43):
                row = dict(
                    fold=date,
                    target=target,
                    start_index=k,
                    decision_us=int(decisions[k]),
                    label_available_us=int(available[k]),
                    observed=float(y[k, j]),
                    ridge=float(p[k, j]),
                    prefix_mean=float(fit["intercept"][j]),
                    constant_VOL_action=1,
                    active_intervals=21 if k < 42 else 20,
                    paid_close=k == 42,
                    fixed_full_disjoint=k in [0, 21],
                )
                (rows if k < 42 else boundary_rows).append(row)
        by_wallet = {
            str(int(w)): int((cache["train_wallet_id"][train] == w).sum())
            for w in np.unique(cache["train_wallet_id"][train])
        }
        records.append(
            dict(
                fold=date,
                training_labels=len(train),
                labels_by_original_wallet=by_wallet,
                latest_training_label_available_us=int(cache["train_label_available"][train].max()),
                first_forward_decision_us=start,
                full21active_forward_windows=42,
                fixed_full_disjoint_spans=2,
                truncated_span=1,
                scores=scores,
            )
        )
        for key, value in fit.items():
            snapshots[date + "_" + key] = value
        for key in ["train_decisions", "train_label_available", "train_wallet_id"]:
            snapshots[date + "_" + key] = cache[key][train]
    destination.mkdir(parents=True)
    for name, data in [("PREDICTIONS.csv", rows), ("TRUNCATED_SPANS.csv", boundary_rows)]:
        with (destination / name).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(data)
    np.savez_compressed(destination / "PREFIX_SCALERS_COEFFICIENTS.npz", **snapshots)
    result = dict(
        status="ONE_FIXED21DAY_DIRECT_CONTRAST_PROBE_COMPLETE_STOPPED",
        protocol=PROTOCOL,
        prepared_metadata=metadata,
        cache_SHA256=sha(cache_path),
        folds=records,
        fits=4,
        coefficients_per_fit=18,
        primary_rows=len(rows),
        truncated_rows=len(boundary_rows),
        neural_updates=0,
        native_rollouts=0,
        downloads=0,
        continuation=False,
        shared_wallet_switching_results=False,
    )
    (destination / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            dict(
                status=result["status"],
                labels=[r["training_labels"] for r in records],
                fits=4,
                primary_rows=len(rows),
                truncated_rows=len(boundary_rows),
            )
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    run(args.cache, args.metadata, args.destination)
