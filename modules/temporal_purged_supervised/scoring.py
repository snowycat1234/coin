"""Predictive scores and fixed-policy opportunity regret, never trading returns."""

import numpy as np

from modules.temporal_two_expert.inputs import DAY_US


def correct(q, weights):
    z = np.asarray(q) / np.asarray(weights)
    return z / z.sum(1, keepdims=True)


def wilson(successes, trials):
    if not trials:
        return None
    z = 1.959963984540054
    p = successes / trials
    center = (p + z * z / (2 * trials)) / (1 + z * z / trials)
    half = z * np.sqrt(p * (1 - p) / trials + z * z / (4 * trials * trials)) / (1 + z * z / trials)
    return [float(center - half), float(center + half)]


def row_scores(prob, truth, utility):
    pred = prob.argmax(1)
    return {
        "logloss": -np.log(prob[np.arange(len(truth)), truth].clip(1e-12)),
        "Brier": ((prob - np.eye(4)[truth]) ** 2).sum(1),
        "accuracy": (pred == truth).astype(float),
        "opportunity_regret": utility.max(1) - utility[np.arange(len(truth)), pred],
    }


def metrics(prob, truth, utility):
    p, y = np.asarray(prob), np.asarray(truth)
    if p.shape != (len(y), 4) or not len(y) or not np.isfinite(p).all():
        raise ValueError("Finite four-class probabilities and nonempty labels required")
    if np.any(p < 0) or not np.allclose(p.sum(1), 1, rtol=0, atol=1e-12):
        raise ValueError("Simplex probabilities required")
    pred = p.argmax(1)
    conf = np.zeros((4, 4), dtype=int)
    np.add.at(conf, (y, pred), 1)
    tp = int(np.sum((pred == 3) & (y == 3)))
    picks, shorts = int(np.sum(pred == 3)), int(np.sum(y == 3))
    precision = tp / picks if picks else None
    prevalence = shorts / len(y)
    return {
        "rows": len(y),
        **{k: float(v.mean()) for k, v in row_scores(p, y, utility).items()},
        "true_counts": np.bincount(y, minlength=4).tolist(),
        "predicted_counts": np.bincount(pred, minlength=4).tolist(),
        "confusion_true_rows_pred_columns": conf.tolist(),
        "mean_probability": p.mean(0).tolist(),
        "SHORT_true_positive": tp,
        "SHORT_precision": precision,
        "SHORT_recall": tp / shorts if shorts else None,
        "SHORT_prevalence": prevalence,
        "SHORT_precision_minus_prevalence": precision - prevalence if picks else None,
        "SHORT_precision_lift": precision / prevalence if picks and shorts else None,
        "SHORT_precision_Wilson95_independence_approximation": wilson(tp, picks),
        "SHORT_recall_Wilson95_independence_approximation": wilson(tp, shorts),
    }


def disjoint_indices(decision, phase=0):
    day = (np.asarray(decision) - int(decision[0])) // DAY_US
    return np.flatnonzero(day % 21 == phase)


def paired_bootstrap(p, reference, truth, utility, draws=1000):
    """Resample disjoint horizon observations; residual serial dependence remains."""
    a, b = row_scores(p, truth, utility), row_scores(reference, truth, utility)
    rng = np.random.default_rng(20261010)
    ix = rng.integers(0, len(truth), size=(draws, len(truth)))
    result = {}
    for key in a:
        delta = a[key] - b[key]
        ci = np.quantile(delta[ix].mean(1), [0.025, 0.975])
        result[key + "_model_minus_prior"] = {
            "mean": float(delta.mean()),
            "bootstrap95": ci.tolist(),
        }
    return {
        "method": "paired IID bootstrap on phase0 disjoint21 horizons; residual serial dependence",
        "draws": draws,
        "rows": len(truth),
        "differences": result,
    }


def report(prob, truth, utility, decision, prior, mean_utility_action):
    constant = np.tile(prior, (len(truth), 1))
    result = {
        "overlap": {
            "model": metrics(prob, truth, utility),
            "training_prior": metrics(constant, truth, utility),
        }
    }
    grids = []
    for phase in range(21):
        ix = disjoint_indices(decision, phase)
        if not len(ix):
            continue
        grid = {
            "phase": phase,
            "first_decision_us": int(decision[ix[0]]),
            "last_decision_us": int(decision[ix[-1]]),
            "model": metrics(prob[ix], truth[ix], utility[ix]),
            "training_prior": metrics(constant[ix], truth[ix], utility[ix]),
            "training_mean_utility_action": int(mean_utility_action),
            "training_mean_utility_regret": float(
                (utility[ix].max(1) - utility[ix, mean_utility_action]).mean()
            ),
        }
        grids.append(grid)
    result["disjoint21_phase0"] = grids[0]
    result["disjoint21_all_phases_descriptive_do_not_pool"] = grids
    ix = disjoint_indices(decision)
    result["disjoint21_phase0_paired_uncertainty"] = paired_bootstrap(
        prob[ix], constant[ix], truth[ix], utility[ix]
    )
    result["overlap"].update(
        {
            "training_mean_utility_action": int(mean_utility_action),
            "training_mean_utility_regret": float(
                (utility.max(1) - utility[:, mean_utility_action]).mean()
            ),
        }
    )
    result["uncertainty_caveat"] = (
        "Daily horizons overlap and are not independent. Phase grids overlap with one another; "
        "never pool them or select a favorable phase. Wilson/phase0 bootstrap are descriptive, "
        "not dependence-robust significance claims; effective samples are small."
    )
    return result
