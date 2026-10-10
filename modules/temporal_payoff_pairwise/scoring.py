"""Action-regret evaluation; simplex-normalized preferences are not probabilities."""

import numpy as np

from modules.temporal_purged_supervised.scoring import disjoint_indices, wilson


def action_metrics(scores, truth, utility):
    q, y, u = np.asarray(scores), np.asarray(truth), np.asarray(utility)
    if q.shape != u.shape or q.shape != (len(y), 4) or not len(y):
        raise ValueError("Nonempty matching four-action arrays required")
    if not np.isfinite(q).all() or not np.isfinite(u).all() or np.any(q < 0):
        raise ValueError("Finite nonnegative preferences required")
    if not np.allclose(q.sum(1), 1, atol=1e-12, rtol=0):
        raise ValueError("Normalized preferences required")
    pred = q.argmax(1)
    picks, shorts = int((pred == 3).sum()), int((y == 3).sum())
    tp = int(((pred == 3) & (y == 3)).sum())
    conf = np.zeros((4, 4), dtype=int)
    np.add.at(conf, (y, pred), 1)
    chosen = u[np.arange(len(y)), pred]
    return {
        "rows": len(y),
        "opportunity_regret": float((u.max(1) - chosen).mean()),
        "chosen_fixed_policy_utility_mean": float(chosen.mean()),
        "accuracy": float((pred == y).mean()),
        "true_counts": np.bincount(y, minlength=4).tolist(),
        "predicted_counts": np.bincount(pred, minlength=4).tolist(),
        "confusion_true_rows_pred_columns": conf.tolist(),
        "mean_preference_scores": q.mean(0).tolist(),
        "SHORT_true_positive": tp,
        "SHORT_precision": tp / picks if picks else None,
        "SHORT_recall": tp / shorts if shorts else None,
        "SHORT_prevalence": shorts / len(y),
        "SHORT_precision_Wilson95_independence_approximation": wilson(tp, picks),
        "SHORT_recall_Wilson95_independence_approximation": wilson(tp, shorts),
    }


def action_delta(scores, reference, utility):
    ix = np.arange(len(utility))
    return utility[ix, scores.argmax(1)] - utility[ix, reference.argmax(1)]


def comparison(scores, baseline, truth, utility, decision, prior):
    references = {
        "matched_CE20": baseline,
        "constant_VOL": np.tile([0, 1, 0, 0], (len(truth), 1)),
        "training_prior": np.tile(prior, (len(truth), 1)),
    }

    def block(ix):
        return {
            "model": action_metrics(scores[ix], truth[ix], utility[ix]),
            **{
                name: action_metrics(q[ix], truth[ix], utility[ix])
                for name, q in references.items()
            },
            "model_minus_reference_utility": {
                name: float(action_delta(scores[ix], q[ix], utility[ix]).mean())
                for name, q in references.items()
            },
        }

    result = {"overlap": block(np.arange(len(truth)))}
    grids = []
    for phase in range(21):
        ix = disjoint_indices(decision, phase)
        if len(ix):
            grids.append(
                {
                    "phase": phase,
                    "first_decision_us": int(decision[ix[0]]),
                    "last_decision_us": int(decision[ix[-1]]),
                    **block(ix),
                }
            )
    result["disjoint21_phase0"] = grids[0]
    result["disjoint21_all_phases_descriptive_do_not_pool"] = grids
    ix = disjoint_indices(decision)
    rng = np.random.default_rng(20261010)
    draws = rng.integers(0, len(ix), (1000, len(ix)))
    result["phase0_paired_utility_difference_bootstrap95_descriptive"] = {
        name: {
            "rows": len(ix),
            "mean": float((delta := action_delta(scores[ix], q[ix], utility[ix])).mean()),
            "bootstrap95": np.quantile(delta[draws].mean(1), [0.025, 0.975]).tolist(),
        }
        for name, q in references.items()
    }
    result["scope"] = (
        "Continuing fixed-policy21day diagnostic utility; not tradable switching returns"
    )
    result["uncertainty"] = (
        "Overlapping daily horizons; phase 0 is descriptive, residual dependence remains. "
        "Never pool/select the 21 phases."
    )
    return result


def adoption_gate(report):
    """No thresholds/SHORT quota: beat both controls, including fixed phase0."""
    overlap = report["overlap"]["model_minus_reference_utility"]
    phase0 = report["disjoint21_phase0"]["model_minus_reference_utility"]
    checks = {
        f"overlap_strictly_beats_{name}": overlap[name] > 0
        for name in ("matched_CE20", "constant_VOL")
    }
    checks.update(
        {
            f"phase0_not_worse_than_{name}": phase0[name] >= 0
            for name in ("matched_CE20", "constant_VOL")
        }
    )
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "threshold_tuning": "NONE",
        "SHORT_frequency_constraint": "NONE",
    }
