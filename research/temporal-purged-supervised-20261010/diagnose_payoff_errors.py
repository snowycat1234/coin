"""Postfit authorized read-only decomposition of existing frozen predictions."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

NAMES = ["CASH", "VOL", "CS", "SHORT"]


def stats(x):
    if not len(x):
        return {"count": 0}
    return {
        "count": len(x),
        "mean": float(np.mean(x)),
        "median": float(np.median(x)),
        "p10": float(np.quantile(x, 0.1)),
        "p90": float(np.quantile(x, 0.9)),
        "sum": float(np.sum(x)),
        "positive_fraction": float(np.mean(x > 0)),
    }


def diagnose(path):
    z = np.load(path)
    p, y, u = z["p"], z["y"], z["utility"]
    pred = p.argmax(1)
    assert p.shape == u.shape == (len(y), 4) and np.array_equal(y, u.argmax(1))
    short = pred == 3
    correct = short & (y == 3)
    incorrect = short & (y != 3)
    improvement = u[np.arange(len(y)), pred] - u[:, 1]
    regret = u.max(1) - u[np.arange(len(y)), pred]
    baseline_regret = u.max(1) - u[:, 1]
    assert abs(regret.mean() - baseline_regret.mean() + improvement.mean()) < 1e-14
    conf = np.zeros((4, 4), dtype=int)
    np.add.at(conf, (y, pred), 1)
    result = {
        "path": path.name,
        "SHA256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(y),
        "class_order": NAMES,
        "confusion_true_rows_pred_columns": conf.tolist(),
        "nonSHORT_truth": {
            "rows": int(np.sum(y != 3)),
            "model_accuracy": float(np.mean(pred[y != 3] == y[y != 3])),
            "constant_VOL_accuracy": float(np.mean(y[y != 3] == 1)),
            "confusion_true_CASH_VOL_CS_rows_all_prediction_columns": conf[:3].tolist(),
        },
        "SHORT_picks": {},
        "regret_decomposition_vs_constant_VOL": {
            "model_mean_regret": float(regret.mean()),
            "constant_VOL_mean_regret": float(baseline_regret.mean()),
            "model_minus_VOL_mean_regret": float(regret.mean() - baseline_regret.mean()),
            "selected_utility_minus_VOL_mean": float(improvement.mean()),
            "correct_SHORT_contribution_per_all_rows": float(improvement[correct].sum() / len(y)),
            "incorrect_SHORT_contribution_per_all_rows": float(
                improvement[incorrect].sum() / len(y)
            ),
            "nonSHORT_picks_contribution_per_all_rows": float(improvement[~short].sum() / len(y)),
        },
        "classwise_primary_logloss": {
            name: {
                "rows": int(np.sum(y == j)),
                "mean_logloss": float(-np.log(p[y == j, j].clip(1e-12)).mean()),
                "predicted_as_correct_class": int(conf[j, j]),
            }
            for j, name in enumerate(NAMES)
            if np.any(y == j)
        },
        "scope": "Frozen hindsight fixed-policy21day utilities, not tradable portfolio profits",
    }
    for name, mask in [("all", short), ("correct", correct), ("incorrect", incorrect)]:
        result["SHORT_picks"][name] = {
            "truth_counts": np.bincount(y[mask], minlength=4).tolist(),
            "SHORT_utility": stats(u[mask, 3]),
            "VOL_utility": stats(u[mask, 1]),
            "SHORT_minus_VOL": stats(u[mask, 3] - u[mask, 1]),
            "SHORT_minus_best_nonSHORT": stats(u[mask, 3] - u[mask, :3].max(1)),
            "opportunity_regret": stats(u[mask].max(1) - u[mask, 3]),
        }
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--destination", required=True)
    a = p.parse_args()
    o = Path(a.out)

    def guard(event, args):
        if event == "open" and args and isinstance(args[0], (str, bytes)):
            if "2025" in str(args[0]):
                raise PermissionError("No2025 IO in postfit decomposition")

    sys.addaudithook(guard)
    result = {
        "schema": "FROZEN_PAYOFF_ERROR_DECOMPOSITION_V1",
        "new_fits": 0,
        "threshold_changes": 0,
        "selection_changes": 0,
        "records": {},
    }
    for name in [
        "EPOCH20_SELECT2023_PREDICTIONS.npz",
        "EPOCH100_SELECT2023_PREDICTIONS.npz",
        "AUDIT_PREDICTIONS.npz",
    ]:
        result["records"][name] = diagnose(o / name)
    Path(a.destination).write_text(json.dumps(result, indent=2) + "\n")
    for name, r in result["records"].items():
        print(
            json.dumps(
                {
                    "name": name,
                    "nonSHORT": r["nonSHORT_truth"],
                    "decomposition": r["regret_decomposition_vs_constant_VOL"],
                    "correct_SHORT_margin": r["SHORT_picks"]["correct"]["SHORT_minus_VOL"],
                    "incorrect_SHORT_margin": r["SHORT_picks"]["incorrect"]["SHORT_minus_VOL"],
                    "classwise_logloss": r["classwise_primary_logloss"],
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    main()
