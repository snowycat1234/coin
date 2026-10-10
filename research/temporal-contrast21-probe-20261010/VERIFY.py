"""Check published coefficients, labels and metrics without additional fitting."""

import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def verify(root, folder, destination):
    if destination.exists():
        raise FileExistsError("Exclusive verification receipt required")
    result = json.loads((folder / "RESULT.json").read_text())
    with np.load(folder / "INPUTS.npz", allow_pickle=False) as z:
        cache = {k: z[k].copy() for k in z.files}
    assert (
        hashlib.sha256((folder / "INPUTS.npz").read_bytes()).hexdigest() == result["cache_SHA256"]
    )
    with np.load(folder / "PREFIX_SCALERS_COEFFICIENTS.npz", allow_pickle=False) as z:
        saved = {k: z[k].copy() for k in z.files}
    with np.load(folder / "TRAIN_STANDALONE_PATHS.npz", allow_pickle=False) as z:
        paths = {k: z[k].copy() for k in z.files}
    assert (
        hashlib.sha256((folder / "TRAIN_STANDALONE_PATHS.npz").read_bytes()).hexdigest()
        == result["prepared_metadata"]["training_path_SHA256"]
    )
    all_rows = []
    for file, count in [("PREDICTIONS.csv", 336), ("TRUNCATED_SPANS.csv", 8)]:
        with (folder / file).open() as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == count
        all_rows.extend(rows)
    # Reconstruct every training label from its own original continuous NAV.
    for wallet in range(5):
        d = paths[f"wallet{wallet}_decisions"]
        starts = np.arange(len(d) - 21)
        ix = np.flatnonzero(cache["train_wallet_id"] == wallet)
        np.testing.assert_array_equal(cache["train_decisions"][ix], d[starts])
        for j, other in enumerate(["SHORT", "CS"]):
            v, o = paths[f"wallet{wallet}_VOL_nav"], paths[f"wallet{wallet}_{other}_nav"]
            y = v[starts + 21] / v[starts] - o[starts + 21] / o[starts]
            np.testing.assert_allclose(cache["train_y"][ix, j], y, atol=1e-15, rtol=0)
        np.testing.assert_array_equal(cache["train_label_available"][ix], d[starts + 21] + 60000001)
    views = dict(
        full21active_overlap=np.arange(42),
        fixed_full_disjoint=np.array([0, 21]),
        truncated20active_plus_paid_close=np.array([42]),
    )
    metric_sets, summaries = 0, []
    old_result = json.loads(
        (root / "research/temporal-economic-relevance-20261010/RESULT.json").read_text()
    )
    for fold_index, fold in enumerate(result["folds"]):
        date = fold["fold"]
        cutoff = int(np.datetime64(date, "us").astype(np.int64))
        ix = np.flatnonzero(
            cache["train_ready"]
            & np.isfinite(cache["train_y"]).all(1)
            & (cache["train_decisions"] < cutoff)
            & (cache["train_label_available"] < cutoff)
        )
        for key in ["train_decisions", "train_label_available", "train_wallet_id"]:
            np.testing.assert_array_equal(saved[date + "_" + key], cache[key][ix])
        x, y = cache["train_x"][ix], cache["train_y"][ix]
        np.testing.assert_array_equal(saved[date + "_mean"], x.mean(0))
        np.testing.assert_array_equal(saved[date + "_scale"], x.std(0))
        np.testing.assert_array_equal(saved[date + "_intercept"], y.mean(0))
        z = (x - saved[date + "_mean"]) / saved[date + "_scale"]
        # Normal-equation residual proves the fixed mean-MSE/lambda1 fit, no refit.
        np.testing.assert_allclose(
            (z.T @ z / len(z) + np.eye(8)) @ saved[date + "_beta"],
            z.T @ (y - y.mean(0)) / len(z),
            atol=2e-16,
            rtol=2e-14,
        )
        assert len(ix) == fold["training_labels"]
        assert saved[date + "_train_label_available"].max() < cutoff
        predicted = (
            (cache["forward_x"][fold_index] - saved[date + "_mean"]) / saved[date + "_scale"]
        ) @ saved[date + "_beta"] + saved[date + "_intercept"]
        for j, target in enumerate(["VOL_MINUS_SHORT", "VOL_MINUS_CS"]):
            selected = sorted(
                [r for r in all_rows if r["fold"] == date and r["target"] == target],
                key=lambda r: int(r["start_index"]),
            )
            assert [int(r["start_index"]) for r in selected] == list(range(43))
            actual = np.array([float(r["observed"]) for r in selected])
            forecast = np.array([float(r["ridge"]) for r in selected])
            np.testing.assert_array_equal(actual, cache["forward_y"][fold_index, :, j])
            np.testing.assert_array_equal(forecast, predicted[:, j])
            for k, row in enumerate(selected):
                assert (
                    int(row["label_available_us"])
                    == int(row["decision_us"])
                    + min(21, 20 if k == 42 else 21) * 86400000000
                    + 60000001
                )
                assert int(row["active_intervals"]) == (21 if k < 42 else 20)
                assert (row["paid_close"] == "True") == (k == 42)
                assert (row["fixed_full_disjoint"] == "True") == (k in [0, 21])
            for view, indices in views.items():
                a = actual[indices]
                nonzero = a != 0
                for name, p in [
                    ("ridge", forecast[indices]),
                    ("prefix_mean", np.full(len(indices), saved[date + "_intercept"][j])),
                ]:
                    record = fold["scores"][target][view][name]
                    mse = float(np.mean((a - p) ** 2))
                    accuracy = float(np.mean(np.sign(a[nonzero]) == np.sign(p[nonzero])))
                    np.testing.assert_allclose(record["MSE"], mse, atol=1e-16, rtol=0)
                    assert (
                        record["sign_agreement"] == accuracy
                        and record["decision_error_rate"] == 1 - accuracy
                    )
                    assert record["contrast_ties"] == int((~nonzero).sum())
                constant = fold["scores"][target][view]["constant_VOL"]
                assert constant["MSE"] is None
                assert constant["sign_agreement"] == float(np.mean(a[nonzero] > 0))
                records = fold["scores"][target][view]
                for name in ["ridge", "prefix_mean"]:
                    record = records[name]
                    expected_skill = 1 - record["MSE"] / records["prefix_mean"]["MSE"]
                    np.testing.assert_allclose(
                        record["MSE_skill_vs_prefix_mean"], expected_skill, atol=1e-15, rtol=0
                    )
                    for ref in ["prefix_mean", "constant_VOL"]:
                        assert (
                            record["sign_improvement_vs_" + ref]
                            == record["sign_agreement"] - records[ref]["sign_agreement"]
                        )
                metric_sets += 1
            current = fold["scores"][target]["full21active_overlap"]
            old = next(f for f in old_result["folds"] if f["fold"] == date)["scores"][target][
                "full21active_overlap"
            ]
            assert (
                current["constant_VOL"]["sign_agreement"] == old["always_VOL_direction_agreement"]
            )
            summary = dict(
                fold=date,
                target=target,
                MSE_skill=current["ridge"]["MSE_skill_vs_prefix_mean"],
                ridge_sign=current["ridge"]["sign_agreement"],
                prefix_mean_sign=current["prefix_mean"]["sign_agreement"],
                constant_VOL_sign=current["constant_VOL"]["sign_agreement"],
                old_market_forecast_sign=old["direction_agreement"],
            )
            summaries.append(summary)
            print(json.dumps(summary, sort_keys=True))
    receipt = dict(
        status="ALL344_FORWARD_ROWS_673_TRAIN_LABELS_COEFFICIENT_EQUATIONS_AND24_METRIC_SETS_RECONCILED",
        forward_rows=344,
        original_training_labels=673,
        metric_sets=metric_sets,
        additional_fits=0,
        old_frozen_market_sign_comparison=summaries,
    )
    assert metric_sets == 24
    destination.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--folder", required=True, type=Path)
    p.add_argument("--receipt", required=True, type=Path)
    a = p.parse_args()
    verify(a.root, a.folder, a.receipt)
