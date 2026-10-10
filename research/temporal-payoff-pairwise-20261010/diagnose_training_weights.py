"""Read-only TRAIN economic-weight concentration, not a causal influence study."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from modules.temporal_payoff_pairwise.objective import PAIRS
from modules.temporal_purged_supervised.inputs import install_io_guard, io_receipt


def concentration(values):
    v = np.asarray(values, dtype=float).ravel()
    assert np.isfinite(v).all() and np.all(v >= 0) and v.sum() > 0
    result = {"observations": len(v), "total": float(v.sum()), "maximum": float(v.max())}
    for fraction in (0.01, 0.05):
        count = int(np.ceil(len(v) * fraction))
        result[f"top{int(fraction * 100)}percent"] = {
            "observations": count,
            "share": float(np.sort(v)[-count:].sum() / v.sum()),
        }
    return result


def run(state, out, destination):
    io = install_io_guard(state)
    plan = json.loads((out / "PLAN.json").read_text())
    label_path = state / "balanced-history/LABELS.json"
    label_sha = hashlib.sha256(label_path.read_bytes()).hexdigest()
    assert label_sha == plan["data"]["label_SHA256"]
    rows = json.loads(label_path.read_text())
    saved = np.load(out / "EPOCH20_TRAIN_PREFERENCES.npz")
    keyed = {row["decision_us"]: row for row in rows}
    selected = [keyed[int(d)] for d in saved["decision_us"]]
    u = saved["utility"]
    np.testing.assert_array_equal(u, [r["hindsight_fixed_policy_21day_utility"] for r in selected])
    assert len(u) == 744 and all(r["label_available_us"] < 1672531200000000 for r in selected)
    gaps = np.stack([np.abs(u[:, i] - u[:, j]) for i, j in PAIRS], 1)
    date_weights = gaps.sum(1)
    year = np.array([str(np.datetime64(int(d), "us"))[:4] for d in saved["decision_us"]])
    regime = np.array([r["regime"] for r in selected])
    groups = {}
    for name, labels in [
        ("year", year),
        ("regime", regime),
        ("year_regime", np.char.add(np.char.add(year, "/"), regime)),
    ]:
        groups[name] = []
        for label in sorted(set(labels)):
            ix = labels == label
            groups[name].append(
                {
                    "name": label,
                    "rows": int(ix.sum()),
                    "pair_gap_weight_share": float(gaps[ix].sum() / gaps.sum()),
                    "SHORT_pair_weight_share_of_all": float(
                        gaps[ix][:, [2, 4, 5]].sum() / gaps.sum()
                    ),
                    "SHORT_favoring_weight": float(np.maximum(u[ix, 3, None] - u[ix, :3], 0).sum()),
                    "SHORT_opposing_weight": float(np.maximum(u[ix, :3] - u[ix, 3, None], 0).sum()),
                }
            )
        groups[name].sort(key=lambda g: g["pair_gap_weight_share"], reverse=True)
    names = ["CASH", "VOL", "CS", "SHORT"]
    pairs = []
    for k, (i, j) in enumerate(PAIRS):
        delta = u[:, i] - u[:, j]
        pairs.append(
            {
                "pair": [names[i], names[j]],
                "share_of_all_pair_weight": float(gaps[:, k].sum() / gaps.sum()),
                "favors_first_weight": float(np.maximum(delta, 0).sum()),
                "favors_second_weight": float(np.maximum(-delta, 0).sum()),
                "concentration": concentration(gaps[:, k]),
            }
        )
    largest = np.argsort(date_weights)[-10:][::-1]
    result = {
        "schema": "TRAIN_ONLY_PAIR_GAP_CONCENTRATION_V1",
        "new_fits": 0,
        "audit2024_scoring": "NOT_RUN",
        "label_SHA256": label_sha,
        "TRAIN_rows": 744,
        "gap_weight_definition": (
            "Unclipped absolute utility gap; common TRAIN scale and 20 equal epochs "
            "cancel in contribution shares"
        ),
        "all_pair_cells": concentration(gaps),
        "date_total_weights": concentration(date_weights),
        "SHORT_pair_share": float(gaps[:, [2, 4, 5]].sum() / gaps.sum()),
        "nonSHORT_pair_share": float(gaps[:, [0, 1, 3]].sum() / gaps.sum()),
        "pairs": pairs,
        "groups": groups,
        "largest10_date_weights": [
            {
                "date": str(np.datetime64(int(saved["decision_us"][i]), "us"))[:10],
                "regime": selected[i]["regime"],
                "winner": names[selected[i]["winner"]],
                "sum_abs_pair_gaps": float(date_weights[i]),
                "utilities": u[i].tolist(),
            }
            for i in largest
        ],
        "interpretation_limit": (
            "These are target loss-weight shares, not realized loss/gradient attribution. "
            "Preference errors, changing representations and clipping alter training influence. "
            "Concentration is descriptive; causation would require a separate matched experiment."
        ),
        "IO": io_receipt(io),
    }
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: result[key]
                for key in [
                    "all_pair_cells",
                    "date_total_weights",
                    "SHORT_pair_share",
                    "nonSHORT_pair_share",
                    "groups",
                ]
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--destination", required=True)
    args = parser.parse_args()
    run(Path(args.state), Path(args.out), Path(args.destination))
