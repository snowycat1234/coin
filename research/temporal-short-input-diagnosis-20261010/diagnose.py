"""Three predeclared causal-input associations; frozen CE20 scores, no fit/filter."""

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from modules.temporal_purged_supervised.inputs import (
    CUTOFF,
    TRAIN_END,
    install_io_guard,
    io_receipt,
    load_episodes,
)
from modules.temporal_two_expert.inputs import (
    CORE5,
    DAY_US,
    FEATURE_NAMES,
    FeatureTimeline,
    array_digest,
)

FILES = {
    "TRAIN": "EPOCH20_TRAIN_PREDICTIONS.npz",
    "SELECT2023": "EPOCH20_SELECT2023_PREDICTIONS.npz",
    "AUDIT2024_POSTHOC": "AUDIT_PREDICTIONS.npz",
}
GROUPS = {
    "trend_rebound": ["CONTINUING_FALL", "REBOUND_WITHIN_FALL", "NONFALLING20", "UNKNOWN"],
    "volatility_shock": ["HIGH_SHOCK", "ORDINARY", "UNKNOWN"],
    "funding_premium": ["NEGATIVE_BOTH", "POSITIVE_BOTH", "MIXED_OR_ZERO", "UNKNOWN"],
}
CONTRASTS = {
    "trend_rebound": ("REBOUND_WITHIN_FALL", "CONTINUING_FALL"),
    "volatility_shock": ("HIGH_SHOCK", "ORDINARY"),
    "funding_premium": ("NEGATIVE_BOTH", "POSITIVE_BOTH"),
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    with Path(path).open("x") as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")


def feature_inputs(state):
    plan = json.loads((state / "purged-supervised-prefix/PLAN.json").read_text())
    path = state / "data-expansion/training1290/FEATURES.npz"
    assert sha(path) == plan["data"]["inputs"]["training1290/FEATURES.npz"]
    with np.load(path, allow_pickle=False) as z:
        x, mask, observed, clocks = (
            z[k]
            for k in (
                "x",
                "feature_observed_mask",
                "close_observed_mask",
                "completed_day_available_us",
            )
        )
        assert tuple(z["symbol_order"]) == CORE5
    assert np.all(clocks < CUTOFF)
    assert np.array_equal(mask, np.isfinite(x) & observed[..., None])
    timeline = FeatureTimeline(
        x, mask, observed, clocks, np.broadcast_to(clocks[:, None, None], x.shape), sha(path)
    )
    return timeline, plan


def summaries(w):
    """Observed-only CORE5 summaries, never replacing missing inputs with zero."""
    x, valid = w.values, w.valid
    out = {}
    for name in ("mom20", "mom5"):
        j = FEATURE_NAMES.index(name)
        out[name] = np.array(
            [
                np.median(a[m]) if m.sum() >= 3 else np.nan
                for a, m in zip(x[:, -1, :, j], valid[:, -1, :, j], strict=True)
            ]
        )
    j, k = FEATURE_NAMES.index("vol10"), FEATURE_NAMES.index("vol60")
    good = valid[:, -1, :, j] & valid[:, -1, :, k] & (x[:, -1, :, k] > 0)
    out["vol10_over_vol60"] = np.array(
        [
            np.median(a[m] / b[m]) if m.sum() >= 3 else np.nan
            for a, b, m in zip(x[:, -1, :, j], x[:, -1, :, k], good, strict=True)
        ]
    )
    for name in ("funding", "premium"):
        j = FEATURE_NAMES.index(name)
        daily = np.array(
            [
                [np.mean(a[m]) if m.sum() >= 3 else np.nan for a, m in zip(av, mv, strict=True)]
                for av, mv in zip(x[:, -7:, :, j], valid[:, -7:, :, j], strict=True)
            ]
        )
        out[name + "7"] = np.array([a.mean() if np.isfinite(a).all() else np.nan for a in daily])
    return out


def classify(s, cutoff):
    n = len(s["mom20"])
    out = {key: np.full(n, "UNKNOWN", dtype="U24") for key in GROUPS}
    known = np.isfinite(s["mom20"]) & np.isfinite(s["mom5"])
    out["trend_rebound"][known & (s["mom20"] >= 0)] = "NONFALLING20"
    out["trend_rebound"][known & (s["mom20"] < 0) & (s["mom5"] <= 0)] = "CONTINUING_FALL"
    out["trend_rebound"][known & (s["mom20"] < 0) & (s["mom5"] > 0)] = "REBOUND_WITHIN_FALL"
    known = np.isfinite(s["vol10_over_vol60"])
    out["volatility_shock"][known & (s["vol10_over_vol60"] > cutoff)] = "HIGH_SHOCK"
    out["volatility_shock"][known & (s["vol10_over_vol60"] <= cutoff)] = "ORDINARY"
    f, p = s["funding7"], s["premium7"]
    known = np.isfinite(f) & np.isfinite(p)
    out["funding_premium"][known] = "MIXED_OR_ZERO"
    out["funding_premium"][known & (f < 0) & (p < 0)] = "NEGATIVE_BOTH"
    out["funding_premium"][known & (f > 0) & (p > 0)] = "POSITIVE_BOTH"
    return out


def freeze(state, output, io):
    timeline, original = feature_inputs(state)
    prefix = state / "purged-supervised-prefix"
    with np.load(prefix / FILES["TRAIN"], allow_pickle=False) as z:
        d = z["decision_us"].copy()  # No outcomes or probabilities needed for cutpoints.
    assert len(d) == 744 and np.all(d < TRAIN_END)
    w = timeline.windows(d)
    completed = np.unique(w.completed_us)
    provenance = original["data"]["scaler_provenance"]
    assert len(completed) == provenance["real_row_count"] == 850
    assert array_digest(completed) == provenance["completed_us_SHA256"]
    s = summaries(w)
    cutoff = float(np.quantile(s["vol10_over_vol60"][np.isfinite(s["vol10_over_vol60"])], 0.75))
    plan = {
        "schema": "THREE_CAUSAL_INPUT_ASSOCIATIONS_PREDECLARED_V1",
        "frozen_at_UTC": datetime.now(timezone.utc).isoformat(),
        "status": "DEFINITIONS_AND_PREFIX_CUTPOINT_FROZEN_BEFORE_LATER_RELATIONSHIPS",
        "source_SHA256": sha(__file__),
        "original_plan_SHA256": sha(prefix / "PLAN.json"),
        "selection_SHA256": sha(prefix / "SELECTION.json"),
        "scaler_SHA256": sha(prefix / "SCALER.npz"),
        "scaler_identity": original["data"]["scaler_identity"],
        "feature_SHA256": timeline.source_sha256,
        "target_SHA256": original["data"]["inputs"]["training1290/TARGETS.npz"],
        "snapshot": json.loads((prefix / "EPOCH20.json").read_text()),
        "prediction_SHA256": {key: sha(prefix / name) for key, name in FILES.items()},
        "mechanisms": {
            ("trend_rebound"): (
                "Latest completed-day CORE5 medians mom20 and mom5; each needs >=3 "
                "observed assets. Continuing fall: mom20<0,mom5<=0; rebound: "
                "mom20<0,mom5>0; nonfalling20: mom20>=0. Missing stays UNKNOWN."
            ),
            ("volatility_shock"): (
                "Latest completed-day median of per-asset vol10/vol60, needing >=3 "
                "paired valid assets and positive vol60. HIGH_SHOCK iff strictly "
                "above TRAIN decision-date q75, otherwise ORDINARY; missing UNKNOWN."
            ),
            ("funding_premium"): (
                "For each of seven latest completed days, equal mean across >=3 "
                "observed CORE5 assets separately for funding and premium; require "
                "all seven daily means. NEGATIVE_BOTH iff both seven-day means<0; "
                "POSITIVE_BOTH iff both>0; otherwise MIXED_OR_ZERO; missing UNKNOWN."
            ),
        },
        "cutpoints": {
            "mom20": 0.0,
            "mom5": 0.0,
            "vol10_over_vol60_q75": cutoff,
            "funding7": 0.0,
            "premium7": 0.0,
        },
        ("cutpoint_role"): (
            "744 mature TRAIN decision-date inputs only; no TRAIN outcome-"
            "conditioned cutpoint, 2023/2024 summary or search"
        ),
        "prefix_summary_valid": {key: int(np.isfinite(v).sum()) for key, v in s.items()},
        ("funding_semantics"): (
            "feature_frame copies daily funding; funding_windows sums raw "
            "archived calc-time event rates within completed calendar day with "
            "causal completeness bracket. Seven-day mean is mean daily sums, not "
            "one event, 8h rate, actual owned funding PnL or APR. Raw positive "
            "scaling does not affect signs; rate units/publication timing are not"
            " natively certified."
        ),
        ("premium_semantics"): (
            "Completed daily premiumIndexKlines close, not mark-minus-index from "
            "simultaneous owned execution; seven-day mean of daily closes, not "
            "seven-day return or event rate."
        ),
        ("clocks"): (
            "Unchanged completed-day boundary proxy; every valid feature "
            "available<=its completed step<=decision; actual historical exchange "
            "publication time remains UNKNOWN."
        ),
        "contrasts": {k: list(v) for k, v in CONTRASTS.items()},
        ("analysis"): (
            "Condition on original corrected p.argmax==SHORT. Report correct "
            "count/precision, false-positive counts by winning class, SHORT-"
            "minus-VOL and SHORT-minus-best-nonSHORT utility. Three prespecified "
            "between-state contrasts, all states including counterexamples. "
            "Whole-row phase0 anchored at each block first decision and all21 "
            "phases without selection/pooling; 1000 moving21-day-block bootstrap "
            "draws descriptive only."
        ),
        ("counterexample_rule"): (
            "For each mechanism, latest-date tie-broken worst-margin false-"
            "positive and lowest-margin correct SHORT inside each observed state;"
            " also three worst false-positive dates overall. Outcomes rank "
            "illustrations only, never cutpoints, states or policies."
        ),
        ("scope"): (
            "Seen development history; TRAIN fitted, 2023 selected CE20, 2024 "
            "already audited and now posthoc diagnostic only. No new holdout "
            "claim; no 2025 market/outcome/calibration consumption; no model fit,"
            " new inference, filter/strategy output or threshold grid."
        ),
        ("discovery_IO_exception"): (
            "Before the hard diagnostic guard, one broad source grep traversed "
            "2025-named code and acquisition metadata. No 2025 market/outcome "
            "tensors or score-result files were consumed. Do not claim absolute "
            "zero 2025 text IO across source discovery."
        ),
        ("stopping"): (
            "Evaluate exactly these three mechanisms once; no extra "
            "bins/features/intersections chosen from outcomes. Propose at most "
            "one bounded next test, never adopt from posthoc errors."
        ),
        "resources": "one CPU/thread; no GPU/swap; RSS2GB/address4GB/host8GB/wall1200s",
    }
    output.mkdir(exist_ok=False)
    save(output / "PLAN.json", plan)
    save(output / "FREEZE_IO.json", io_receipt(io))
    print(
        json.dumps(
            {"status": plan["status"], "plan_SHA256": sha(output / "PLAN.json"), "cutoff": cutoff}
        ),
        flush=True,
    )


def state_stats(y, gap, best_gap, mask, pred):
    chosen = mask & (pred == 3)
    correct = chosen & (y == 3)
    wrong = chosen & (y != 3)
    n = int(chosen.sum())
    return {
        "all_rows": int(mask.sum()),
        "SHORT_picks": n,
        "correct": int(correct.sum()),
        "incorrect": int(wrong.sum()),
        "precision": float(correct.sum() / n) if n else None,
        "all_state_SHORT_prevalence": float(np.mean(y[mask] == 3)) if mask.any() else None,
        "false_positive_winner_counts_CASH_VOL_CS": np.bincount(y[wrong], minlength=4)[:3].tolist(),
        "mean_SHORT_minus_VOL": float(gap[chosen].mean()) if n else None,
        "mean_SHORT_minus_best_nonSHORT": float(best_gap[chosen].mean()) if n else None,
        "correct_mean_SHORT_minus_VOL": float(gap[correct].mean()) if correct.any() else None,
        "incorrect_mean_SHORT_minus_VOL": float(gap[wrong].mean()) if wrong.any() else None,
        "SHORT_beats_VOL_count": int((chosen & (gap > 0)).sum()),
        "sum_SHORT_minus_VOL": float(gap[chosen].sum()),
    }


def difference(y, gap, pred, group, a, b):
    ma, mb = (pred == 3) & (group == a), (pred == 3) & (group == b)
    if not ma.any() or not mb.any():
        return None
    return np.array([np.mean(y[ma] == 3) - np.mean(y[mb] == 3), gap[ma].mean() - gap[mb].mean()])


def contrast(y, gap, pred, group, a, b):
    value = difference(y, gap, pred, group, a, b)
    if value is None:
        return {"state_A": a, "state_B": b, "status": "INSUFFICIENT_STATES"}
    rng = np.random.default_rng(20261010)
    block = 21
    draws = []
    for _ in range(1000):
        starts = rng.integers(0, len(y) - block + 1, size=int(np.ceil(len(y) / block)))
        ix = (starts[:, None] + np.arange(block)).ravel()[: len(y)]
        delta = difference(y[ix], gap[ix], pred[ix], group[ix], a, b)
        if delta is not None:
            draws.append(delta)
    ci = np.quantile(draws, [0.025, 0.975], axis=0).T.tolist() if draws else [None, None]
    return {
        "state_A": a,
        "state_B": b,
        "precision_A_minus_B": float(value[0]),
        "mean_margin_A_minus_B": float(value[1]),
        "moving21_block_bootstrap95_precision": ci[0],
        "moving21_block_bootstrap95_mean_margin": ci[1],
        "bootstrap_valid_draws": len(draws),
        "bootstrap_draws": 1000,
    }


def description(s, ix, group, d, y, gap, best_gap, expert_state):
    return {
        "date": str(np.datetime64(int(d[ix]), "us").astype("datetime64[D]")),
        "winner": ["CASH", "VOL", "CS", "SHORT"][y[ix]],
        "SHORT_minus_VOL": float(gap[ix]),
        "SHORT_minus_best_nonSHORT": float(best_gap[ix]),
        "states": {k: str(v[ix]) for k, v in group.items()},
        "input_summaries": {k: float(v[ix]) if np.isfinite(v[ix]) else None for k, v in s.items()},
        "current_SHORT_target_gross": float(np.abs(expert_state[ix, 10:15]).sum() * 0.3),
    }


def diagnose(state, output, io):
    plan = json.loads((output / "PLAN.json").read_text())
    assert sha(__file__) == plan["source_SHA256"]
    prefix = state / "purged-supervised-prefix"
    timeline, original = feature_inputs(state)
    assert sha(prefix / "PLAN.json") == plan["original_plan_SHA256"]
    assert sha(prefix / "SELECTION.json") == plan["selection_SHA256"]
    assert sha(prefix / "SCALER.npz") == plan["scaler_SHA256"]
    es, bindings = load_episodes(
        state
    )  # Reuse exact original window/expert-state contracts; no new fit.
    assert bindings == original["data"]["inputs"]
    records, table = {}, []
    for role, filename in FILES.items():
        path = prefix / filename
        assert sha(path) == plan["prediction_SHA256"][role]
        with np.load(path, allow_pickle=False) as z:
            d, y, utility, p = (z[k].copy() for k in ("decision_us", "y", "utility", "p"))
        assert np.array_equal(y, utility.argmax(1)) and p.shape == utility.shape == (len(y), 4)
        assert np.isfinite(p).all() and np.allclose(p.sum(1), 1, rtol=0, atol=1e-12)
        w = timeline.windows(d)
        expert = []
        for i, day in enumerate(d):
            matched = [
                (e, int(np.searchsorted(e.windows.decision_us, day)))
                for e in es
                if e.windows.decision_us[0] <= day <= e.windows.decision_us[-1]
            ]
            assert len(matched) == 1
            e, j = matched[0]
            assert e.windows.decision_us[j] == day
            np.testing.assert_array_equal(w.values[i], e.windows.values[j])
            np.testing.assert_array_equal(w.valid[i], e.windows.valid[j])
            np.testing.assert_array_equal(w.completed_us[i], e.windows.completed_us[j])
            assert np.all(e.expert_input_available_us[j] <= day)
            expert.append(e.expert_state[j])
        expert = np.asarray(expert)
        s = summaries(w)
        groups = classify(s, plan["cutpoints"]["vol10_over_vol60_q75"])
        pred = p.argmax(1)
        gap, best_gap = utility[:, 3] - utility[:, 1], utility[:, 3] - utility[:, :3].max(1)
        short = pred == 3
        r = {
            "rows": len(y),
            "SHORT_picks": int(short.sum()),
            "correct": int((short & (y == 3)).sum()),
            "mean_SHORT_minus_VOL": float(gap[short].mean()),
            "precision": float(np.mean(y[short] == 3)),
            "data_role": "FITTED_TRAIN"
            if role == "TRAIN"
            else "MODEL_SELECTION_2023"
            if role == "SELECT2023"
            else "ALREADY_AUDITED_2024_POSTHOC_ONLY",
            "window_values_digest": array_digest(w.values),
            "window_valid_digest": array_digest(w.valid),
            "expert_state_digest": array_digest(expert),
            "causal_expert_state_exact_original": True,
            "groups": {},
            "contrasts": {},
            "phase_grids": [],
            "counterexamples": {},
        }
        for mechanism, states in GROUPS.items():
            g = groups[mechanism]
            r["groups"][mechanism] = {
                name: state_stats(y, gap, best_gap, g == name, pred) for name in states
            }
            a, b = CONTRASTS[mechanism]
            r["contrasts"][mechanism] = contrast(y, gap, pred, g, a, b)
            illustrations = {}
            for name in states:
                chosen = short & (g == name)
                rows = {}
                for kind, mask in (
                    ("worst_margin_false_positive", chosen & (y != 3)),
                    ("lowest_margin_correct", chosen & (y == 3)),
                ):
                    ix = np.flatnonzero(mask)
                    if len(ix):
                        selected = min(ix, key=lambda k: (gap[k], -int(d[k])))
                        rows[kind] = description(s, selected, groups, d, y, gap, best_gap, expert)
                illustrations[name] = rows
            r["counterexamples"][mechanism] = illustrations
        for phase in range(21):
            take = np.flatnonzero(((d - d[0]) // DAY_US) % 21 == phase)
            grid = {
                "phase": phase,
                "rows": len(take),
                "SHORT_picks": int(short[take].sum()),
                "groups": {},
            }
            for mechanism, states in GROUPS.items():
                grid["groups"][mechanism] = {
                    name: state_stats(
                        y[take],
                        gap[take],
                        best_gap[take],
                        groups[mechanism][take] == name,
                        pred[take],
                    )
                    for name in states
                }
            r["phase_grids"].append(grid)
        wrong = np.flatnonzero(short & (y != 3))
        worst = sorted(wrong, key=lambda k: (gap[k], -int(d[k])))[:3]
        r["three_worst_false_positive_dates"] = [
            description(s, i, groups, d, y, gap, best_gap, expert) for i in worst
        ]
        r["expert_state_context_only"] = {
            name: {
                "rows": int(mask.sum()),
                "mean_current_SHORT_gross": float(np.mean(np.abs(expert[mask, 10:15]).sum(1) * 0.3))
                if mask.any()
                else None,
            }
            for name, mask in (
                ("correct_SHORT", short & (y == 3)),
                ("incorrect_SHORT", short & (y != 3)),
            )
        }
        for i in range(len(d)):
            table.append(
                {
                    "role": role,
                    "decision_us": int(d[i]),
                    "winner": int(y[i]),
                    "predicted": int(pred[i]),
                    "SHORT_minus_VOL": float(gap[i]),
                    "SHORT_minus_best_nonSHORT": float(best_gap[i]),
                    **{k: str(v[i]) for k, v in groups.items()},
                    **{k: float(v[i]) if np.isfinite(v[i]) else "" for k, v in s.items()},
                    "current_SHORT_target_gross": float(np.abs(expert[i, 10:15]).sum() * 0.3),
                }
            )
        records[role] = r
        print(
            json.dumps({"role": role, "groups": r["groups"], "contrasts": r["contrasts"]}),
            flush=True,
        )
    with (output / "ROWS.csv").open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(table[0]))
        writer.writeheader()
        writer.writerows(table)
    assert all(
        sha(prefix / filename) == plan["prediction_SHA256"][role]
        for role, filename in FILES.items()
    )
    assert (
        sha(prefix / plan["snapshot"]["checkpoint"]["path"])
        == plan["snapshot"]["checkpoint"]["SHA256"]
    )
    save(
        output / "EVIDENCE.json",
        {
            "schema": "FROZEN_CE20_THREE_INPUT_ASSOCIATIONS_V1",
            "plan_SHA256": sha(output / "PLAN.json"),
            "model_fits": 0,
            "model_inferences": 0,
            "scaler_fits": 0,
            "strategy_outputs": 0,
            "threshold_grid": 0,
            "original_model_checkpoint_and_prediction_files_unchanged": True,
            "records": records,
            "rows_SHA256": sha(output / "ROWS.csv"),
            ("uncertainty"): (
                "21-day target overlap, 64-day input overlap, persistent regimes and "
                "exposure confounding. Moving21-day-block bootstrap is descriptive "
                "and may still understate dependence. Phase grids share observations "
                "across phases; never pool or select. Small bins can lack either "
                "state. None establishes cause or a viable strategy."
            ),
        },
    )
    save(output / "DIAGNOSE_IO.json", io_receipt(io))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("freeze", "diagnose"))
    p.add_argument("--state", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    io = install_io_guard(a.state)
    (freeze if a.mode == "freeze" else diagnose)(a.state, a.output, io)


if __name__ == "__main__":
    main()
