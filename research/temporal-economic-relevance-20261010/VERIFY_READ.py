"""Independently reconcile the saved rows/statistics without inference or rollout."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def pearson(x, y):
    if len(x) < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return None
    a, b = x - np.mean(x), y - np.mean(y)
    return float((a @ b) / np.sqrt((a @ a) * (b @ b)))


def rank(x):
    # Independent average-tie calculation, avoiding the reader's sorting routine.
    return np.array([np.sum(x < v) + (np.sum(x == v) - 1) / 2 for v in x])


def verify(root, folder, destination):
    if destination.exists():
        raise FileExistsError("Exclusive verification receipt required")
    result = json.loads((folder / "RESULT.json").read_text())
    with (folder / "PAIRED_ASSOCIATIONS.csv").open() as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 344
    for path, digest in result["sources"].items():
        assert hashlib.sha256((root / path).read_bytes()).hexdigest() == digest
    count = 0
    for block in result["folds"]:
        date = block["fold"]
        family = "april" if date == "2024-04-01" else "prequential"
        bundle = root / f"research/temporal-{family}-transfer-20261009/forward"
        bundle /= "FOLD_" + date.replace("-", "")
        with np.load(bundle / "PAIRED_PATHS.npz", allow_pickle=False) as z:
            paths = {k: z[k].copy() for k in z.files}
        for contrast, scores in block["scores"].items():
            selected = [r for r in rows if r["fold"] == date and r["contrast"] == contrast]
            assert [int(r["start_index"]) for r in selected] == list(range(43))
            other = "SHORT" if contrast == "VOL_MINUS_SHORT" else "CS"
            for k, row in enumerate(selected):
                expected = (
                    paths["VOL_nav"][k + 21] / paths["VOL_nav"][k]
                    - paths[other + "_nav"][k + 21] / paths[other + "_nav"][k]
                )
                np.testing.assert_allclose(
                    float(row["expert_return_contrast"]), expected, atol=1e-15, rtol=0
                )
                assert int(row["decision_us"]) == paths["decision_us"][k]
                assert (
                    int(row["label_available_us"])
                    == paths["decision_us"][min(k + 21, 62)] + 60000001
                )
                assert int(row["active_intervals"]) == (21 if k < 42 else 20)
                assert (row["includes_paid_close"] == "True") == (k == 42)
                assert (row["original_disjoint_span"] == "True") == (k in [0, 21, 42])
            views = dict(
                full21active_overlap=np.arange(42),
                full21active_disjoint=np.array([0, 21]),
                all43_saved_path_windows=np.arange(43),
                all_three_original_disjoint_path_spans=np.array([0, 21, 42]),
            )
            x = np.array([float(r["forecast_market_return"]) for r in selected])
            y = np.array([float(r["expert_return_contrast"]) for r in selected])
            mean = float(selected[0]["prefix_mean_forecast"])
            for name, ix in views.items():
                a, b, saved = x[ix], y[ix], scores[name]
                nonzero = b != 0
                direct = dict(
                    n=len(ix),
                    Pearson=pearson(a, b),
                    Spearman=pearson(rank(a), rank(b)),
                    direction_agreement=float(np.mean(np.sign(a[nonzero]) == np.sign(b[nonzero]))),
                    prefix_mean_direction_agreement=float(
                        np.mean(np.sign(mean) == np.sign(b[nonzero]))
                    ),
                    always_VOL_direction_agreement=float(np.mean(b[nonzero] > 0)),
                    always_other_direction_agreement=float(np.mean(b[nonzero] < 0)),
                    contrast_ties=int((~nonzero).sum()),
                    signal_zero_count=int((a == 0).sum()),
                    contrast_mean=float(np.mean(b)),
                    forecast_mean=float(np.mean(a)),
                )
                for key, value in direct.items():
                    if value is None:
                        assert saved[key] is None
                    else:
                        np.testing.assert_allclose(saved[key], value, atol=2e-14, rtol=0)
                assert saved["prefix_mean_association"] is None
                assert saved["zero_information_expected_agreement"] == 0.5
                count += 1
                if name in ("full21active_overlap", "all_three_original_disjoint_path_spans"):
                    print(date, contrast, name, json.dumps(direct, sort_keys=True))
    receipt = dict(
        status="ALL_PAIRED_ROWS_CLOCKS_NAV_CONTRASTS_AND32_METRIC_SETS_RECONCILED",
        rows=344,
        metric_sets=count,
        fits=0,
        rollouts=0,
        inference=0,
        input_hashes_unchanged=True,
        statistical_effective_N="UNKNOWN",
    )
    assert count == 32
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    verify(args.root, args.results, args.receipt)
