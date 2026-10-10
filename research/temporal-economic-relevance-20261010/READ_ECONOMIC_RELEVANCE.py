"""Read frozen forecasts and charged standalone NAV paths; no fit or rollout."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

FOLDS = ("20230703", "20231002", "20240101", "20240401")
CONTRASTS = ("VOL_MINUS_SHORT", "VOL_MINUS_CS")
DAY_US = 86400000000
FORECAST_FILES = {
    "PREDICTIONS.csv": "e1b97a5c37af7dbd1344c1d710b616f4701d92f3634802ed66d34530cd2b9319",
    "RESULT.json": "7d9ea04eacac0a8206a8427ed50368877e6ca87edca8175fcafb5c79e0e022bc",
    "PREFIX_SCALERS_COEFFICIENTS.npz": (
        "9bcce9d3a361a048671977295dcdcca46a3b6c5f90e0855a3f291d3d4851b71b"
    ),
}
CONTROL_MANIFESTS = dict(
    zip(
        FOLDS,
        [
            "80edc91bb22c9987c73aed0d87941c140f7286ce72637db5b540741d9c0c2907",
            "9c3818341ce3ffb8879868f484d2ab1e11f35ab7ff77f4b4b4a8ce9c2e105def",
            "62ec3efa0d02c964ffcc59fb16f679740b9854556f1aefa3aeefd5737836b14f",
            "99f07ef591581a51babb0b4a8b3079310f24a8bfe0e91b09103c4a68ffa82130",
        ],
        strict=True,
    )
)
PROTOCOL = dict(
    schema="READ_ONLY_FROZEN21_FORECAST_STANDALONE_EXPERT_RELEVANCE_V1",
    frozen_forecast_commit="c574f2c4db9661ac1e29167f0bfbd30014e62410",
    contrasts=list(CONTRASTS),
    orientation="positive_market_forecast_favors_VOL_in_both_contrasts;no_sign_flip",
    horizon="marked_NAV[k+21]/NAV[k]-1_of_existing_continuous_standalone_control",
    outcomes="all_saved_costs_funding_ramp_eligibility_and_endogenous_CS_risk_reductions_retained",
    primary="42full21activeinterval_windows_perfold;fixed_disjoint0_21_only",
    boundary="start42_has20activeintervals_plus_paidclose;separate;original_third_disjoint_span_retained_and_flagged",
    direction_rule="sign(frozen_market_return_forecast)==sign(expert_return_contrast);threshold0_fixed;ties_reported",
    comparisons=[
        "frozen_prefix_mean_market_forecast",
        "always_VOL",
        "always_other",
        "zero_information_fair_sign_expected50percent_on_nonties",
    ],
    association="Pearson_linear_and_Spearman_average_tie_ranks_perfold;no_pool_or_pvalues",
    limitations="path_state_conditioned_marked_outcomes_not_fresh21day_accounts_or_realizable_switching_profits_or_native_results",
    no_training=True,
    no_threshold_search=True,
    no_rollouts=True,
    no_downloads=True,
    effective_N="UNKNOWN;42overlap_windows_and2full_disjoint_spans_not_independent_sample_counts",
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ranks(a):
    order = np.argsort(a, kind="stable")
    result = np.empty(len(a), float)
    first = 0
    while first < len(a):
        last = first + 1
        while last < len(a) and a[order[last]] == a[order[first]]:
            last += 1
        result[order[first:last]] = (first + last - 1) / 2
        first = last
    return result


def correlation(a, b):
    if len(a) < 2 or np.ptp(a) == 0 or np.ptp(b) == 0:
        return None
    return float(np.corrcoef(a, b)[0, 1])


def association(forecast, contrast, prefix_mean):
    if not np.isfinite(forecast).all() or not np.isfinite(contrast).all():
        raise ValueError("Finite frozen signal and actual saved outcomes required")
    nonzero = contrast != 0
    direction = np.sign(contrast[nonzero])

    def agreement(p):
        return float(np.mean(np.sign(p[nonzero]) == direction)) if nonzero.any() else None

    return dict(
        n=len(forecast),
        Pearson=correlation(forecast, contrast),
        Spearman=correlation(ranks(forecast), ranks(contrast)),
        direction_agreement=agreement(forecast),
        contrast_ties=int((~nonzero).sum()),
        signal_zero_count=int((forecast == 0).sum()),
        prefix_mean_direction_agreement=agreement(np.full(len(forecast), prefix_mean)),
        prefix_mean_association=None,
        constant_association="UNDEFINED_no_variation",
        always_VOL_direction_agreement=float(np.mean(direction > 0)) if nonzero.any() else None,
        always_other_direction_agreement=float(np.mean(direction < 0)) if nonzero.any() else None,
        zero_information_expected_agreement=0.5 if nonzero.any() else None,
        contrast_mean=float(contrast.mean()),
        forecast_mean=float(forecast.mean()),
    )


def windows(nav):
    if nav.shape != (64,) or not np.isfinite(nav).all() or np.any(nav <= 0) or nav[0] != 10000:
        raise ValueError("One complete positive standalone63step wallet NAV required")
    starts = np.arange(43)
    return nav[starts + 21] / nav[starts] - 1


def maturity(decisions, labels, start):
    if (
        not len(decisions)
        or decisions.shape != labels.shape
        or np.any(decisions >= start)
        or not np.array_equal(labels, decisions + 21 * DAY_US)
        or np.any(labels >= start)
    ):
        raise ValueError("Frozen forecast prefix requires full21day labels strictly before fold")
    return dict(training_labels=len(decisions), latest_label_available_us=int(labels.max()))


def read_forecasts(root):
    folder = root / "research/temporal-horizon21-probe-20261010"
    sources = {}
    for name, digest in FORECAST_FILES.items():
        if sha(folder / name) != digest:
            raise ValueError("Forecast, scaler or coefficient bytes differ from pinned c574f2c")
        sources[str((folder / name).relative_to(root))] = digest
    result = json.loads((folder / "RESULT.json").read_text())
    audits = {}
    with np.load(folder / "PREFIX_SCALERS_COEFFICIENTS.npz", allow_pickle=False) as z:
        for fold in result["folds"]:
            date, start = fold["fold"], fold["first_forward_decision_us"]
            audit = maturity(
                z[date + "_train_decisions"], z[date + "_train_label_available"], start
            )
            if (
                audit["training_labels"] != fold["training_overlapping_labels"]
                or audit["latest_label_available_us"] != fold["latest_training_label_available_us"]
            ):
                raise ValueError("Frozen prefix maturity receipt must reconcile")
            audits[date] = audit
    with (folder / "PREDICTIONS.csv").open() as f:
        predictions = list(csv.DictReader(f))
    return predictions, sources, audits


def read_bundle(root, suffix):
    project = (
        "temporal-april-transfer-20261009"
        if suffix == "20240401"
        else "temporal-prequential-transfer-20261009"
    )
    folder = root / "research" / project / "forward" / ("FOLD_" + suffix)
    if sha(folder / "MANIFEST.json") != CONTROL_MANIFESTS[suffix]:
        raise ValueError("Frozen original wallet manifest identity required")
    manifest = json.loads((folder / "MANIFEST.json").read_text())
    for name, entry in manifest["files"].items():
        if sha(folder / name) != entry["SHA256"]:
            raise ValueError("Frozen control bundle bytes changed")
    result = json.loads((folder / "RESULT.json").read_text())
    with np.load(folder / "PAIRED_PATHS.npz", allow_pickle=False) as z:
        paths = {k: z[k].copy() for k in z.files}
    with np.load(folder / "CURRENT_CONTEXT63.npz", allow_pickle=False) as z:
        context = {k: z[k].copy() for k in z.files}
    clock = paths["decision_us"]
    if len(clock) != 63 or not np.all(np.diff(clock) == DAY_US):
        raise ValueError("One genuine contiguous original forward wallet required")
    np.testing.assert_array_equal(clock, context["decision_us"])
    np.testing.assert_array_equal(
        context["symbol_order"], ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"]
    )
    np.testing.assert_array_equal(
        context["expert_order"],
        [
            "CASH",
            "VOL_MANAGED_HOLD",
            "PUBLIC_SMA50_200_SIGNED",
            "DONCHIAN_EXIT10",
            "CSMOM21",
            "MOMENTUM30_SHORT_ONLY",
        ],
    )
    if not np.array_equal(context["surrogate_prices"][-1], context["surrogate_prices"][-2]):
        raise ValueError("Expected knownflat paid terminal suffix")
    if np.any(context["target_available_us"] > clock[:, None]):
        raise ValueError("Causal expert eligibility/target clocks required")
    if np.any(context["expert_input_available_us"] > clock[:, None]):
        raise ValueError("Causal cached expert inputs required")
    np.testing.assert_array_equal(context["outcome_available_us"][:-1], clock[1:] + 60000001)
    assert context["outcome_available_us"][-1] == context["outcome_available_us"][-2]
    assert not np.any(context["surrogate_funding_coeff"][-1])
    audit = {}
    for name, k in [("VOL", 1), ("CS", 4), ("SHORT", 5)]:
        record = result["policies"][name]
        nav = paths[name + "_nav"]
        np.testing.assert_allclose(nav[-1] - 10000, record["net_PnL"], rtol=0, atol=2e-8)
        if not record["paid_terminal_cash"] or np.any(paths[name + "_targets"][-1]):
            raise ValueError("Saved terminal paidflat identity required")
        if not context["expert_eligible"][:, k].all():
            raise ValueError("Expected frozen controls eligible throughout; never discard days")
        audit[name] = dict(
            risk_events=record["risk_events"],
            charged_risk_reduction=record["charged_reduction_cost"],
            fees=record["fees"],
            spread=record["spread"],
            slippage=record["slippage"],
            funding=record["funding"],
            eligible_days=int(context["expert_eligible"][:, k].sum()),
            flat_target_days=int(np.all(context["expert_targets"][:, k] == 0, axis=1).sum()),
            read_saved_NAV_including_risk_reductions=True,
        )
    return (
        clock,
        paths,
        context,
        audit,
        {
            str((folder / n).relative_to(root)): sha(folder / n)
            for n in ["MANIFEST.json", "RESULT.json", "PAIRED_PATHS.npz", "CURRENT_CONTEXT63.npz"]
        },
    )


def run(root, output):
    if output.exists():
        raise FileExistsError("Exclusive read-only diagnostic output required")
    all_predictions, sources, forecast_audits = read_forecasts(root)
    blocks, csv_rows = [], []
    for suffix in FOLDS:
        date = suffix[:4] + "-" + suffix[4:6] + "-" + suffix[6:]
        predictions = [
            r
            for r in all_predictions
            if r["fold"] == date and r["target"] == "CORE5_mean_21day_asset_cumulative_return"
        ]
        if len(predictions) != 43:
            raise ValueError("Exactly the frozen43 horizon starts required")
        clock, paths, context, audit, hashes = read_bundle(root, suffix)
        sources.update(hashes)
        np.testing.assert_array_equal([int(r["decision_us"]) for r in predictions], clock[:43])
        np.testing.assert_array_equal(
            [int(r["label_available_us"]) for r in predictions], clock[:43] + 21 * DAY_US
        )
        assert [r["fixed_disjoint"] == "True" for r in predictions] == [
            k in [0, 21, 42] for k in range(43)
        ]
        forecast = np.array([float(r["ridge"]) for r in predictions])
        means = np.array([float(r["training_mean"]) for r in predictions])
        if np.ptp(means) != 0:
            raise ValueError("Frozen prefix mean comparison required")
        outcomes = {name: windows(paths[name + "_nav"]) for name in ["VOL", "CS", "SHORT"]}
        contrasts = {
            "VOL_MINUS_SHORT": outcomes["VOL"] - outcomes["SHORT"],
            "VOL_MINUS_CS": outcomes["VOL"] - outcomes["CS"],
        }
        scores = {}
        for name, y in contrasts.items():
            scores[name] = dict(
                full21active_overlap=association(forecast[:42], y[:42], means[0]),
                full21active_disjoint=association(forecast[[0, 21]], y[[0, 21]], means[0]),
                all43_saved_path_windows=association(forecast, y, means[0]),
                all_three_original_disjoint_path_spans=association(
                    forecast[[0, 21, 42]], y[[0, 21, 42]], means[0]
                ),
            )
            for k in range(43):
                csv_rows.append(
                    dict(
                        fold=date,
                        contrast=name,
                        start_index=k,
                        decision_us=int(clock[k]),
                        forecast_market_return=float(forecast[k]),
                        prefix_mean_forecast=float(means[k]),
                        expert_return_contrast=float(y[k]),
                        VOL_return=float(outcomes["VOL"][k]),
                        other_return=float(
                            outcomes["SHORT" if name.endswith("SHORT") else "CS"][k]
                        ),
                        label_available_us=int(context["outcome_available_us"][k + 20]),
                        full21_active_intervals=k < 42,
                        active_intervals=21 if k < 42 else 20,
                        includes_paid_close=k == 42,
                        original_disjoint_span=k in [0, 21, 42],
                    )
                )
        blocks.append(
            dict(
                fold=date,
                frozen_forecast_prefix=forecast_audits[date],
                audit=audit,
                full21active_starts=42,
                fixed_full_disjoint_spans=2,
                third_original_disjoint_span="20active_intervals_plus_paidflat_cost;conditional_boundary_result_only",
                scores=scores,
            )
        )
    output.mkdir(parents=True)
    with (output / "PAIRED_ASSOCIATIONS.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(csv_rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)
    result = dict(
        status="READ_ONLY_STANDALONE_PATH_ASSOCIATIONS_COMPLETE_WITH_BOUNDARY_LIMITATION",
        protocol=PROTOCOL,
        sources=sources,
        folds=blocks,
        paired_rows=344,
        fits=0,
        economic_rollouts=0,
        inference=0,
        downloads=0,
        native_results=False,
    )
    (output / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(status=result["status"], paired_rows=344, fits=0, rollouts=0)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.root, args.output)
