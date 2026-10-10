"""Read-only normalized input coverage; no new scaler, model, fit, or wallet."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

p = argparse.ArgumentParser()
p.add_argument("--state", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
feature = a.state / "feature-input/verified/features/CORE5_PRE_MAY2024.npz"
assert (
    hashlib.sha256(feature.read_bytes()).hexdigest()
    == "f164dc8986727e12446f4a807aed72382e8fd665ad7eda9ba14590811ebc680c"
)
with np.load(feature, allow_pickle=False) as f:
    x = f["x"].astype(float)
    v = f["feature_observed_mask"] & f["close_observed_mask"][..., None]
    clock = f["completed_day_available_us"]
    names = f["feature_order"].tolist()
scaler = (
    root
    / "research/temporal-selected-refit-q4-20261010/frozen/FULL773_LOW_LR3E4_DATE_256/SCALER.npz"
)
with np.load(scaler, allow_pickle=False) as z:
    mean = z["mean"]
    scale = z["scale"]


def timestamp(s):
    return int(np.datetime64(s, "us").astype("int64"))


def rows(start, end):
    d = np.arange(timestamp(start), timestamp(end) + 86400000000, 86400000000, dtype=np.int64)
    return np.unique((np.searchsorted(clock, d)[:, None] - np.arange(64)[None, :]).ravel())


old = np.unique(
    np.concatenate(
        [
            rows(s, e)
            for s, e in [
                ("2022-01-02", "2022-02-24"),
                ("2022-05-04", "2022-07-30"),
                ("2022-08-01", "2022-10-01"),
                ("2022-10-03", "2023-02-23"),
                ("2023-02-25", "2024-04-29"),
            ]
        ]
    )
)
added = rows("2021-01-01", "2021-12-31")
assert len(old) == 907 and len(added) == 428
sets = {
    "original_training_unique_rows": (x[old], v[old]),
    "added_2021_unique_rows": (x[added], v[added]),
}
for label, path in [
    (
        "July_seen",
        root / "research/temporal-july-frozen-transfer-20261010/results/FEATURE_ROWS.npz",
    ),
    ("Q4_seen", root / "research/temporal-selected-refit-q4-20261010/q4-results/FEATURE_ROWS.npz"),
]:
    with np.load(path, allow_pickle=False) as z:
        sets[label] = (z["values"].astype(float), z["valid"])
result = {}
for label, (value, valid) in sets.items():
    scaled = (np.where(valid, value, mean) - mean) / scale
    fields = []
    for i, name in enumerate(names):
        z = scaled[..., i][valid[..., i]]
        fields.append(
            dict(
                name=name,
                observed=int(len(z)),
                missing_fraction=float(1 - valid[..., i].mean()),
                mean_z=float(z.mean()),
                std_z=float(z.std()),
                p99_abs_z=float(np.quantile(np.abs(z), 0.99)),
                max_abs_z=float(np.max(np.abs(z))),
                fraction_abs_z_gt5=float(np.mean(np.abs(z) > 5)),
                fraction_abs_z_gt10=float(np.mean(np.abs(z) > 10)),
            )
        )
    result[label] = dict(
        unique_dates=len(value),
        fields=fields,
        overall_abs_z_gt5=float(np.mean(np.abs(scaled[valid]) > 5)),
        overall_abs_z_gt10=float(np.mean(np.abs(scaled[valid]) > 10)),
    )
out = dict(
    status="READ_ONLY_FROZEN_SCALER_DISTRIBUTION",
    scaler_identity="5c0085131d590e64316de3cc558e906f418bff50bc5d934339609da2c4b045ad",
    feature_SHA256=hashlib.sha256(feature.read_bytes()).hexdigest(),
    unique_added_rows=int(len(set(added) - set(old))),
    overlap_rows=int(len(set(added) & set(old))),
    groups=result,
    thresholds="fixed descriptive 5 and 10 standard deviations; not a selection or clipping rule",
    model_runs=0,
    wallet_runs=0,
    scaler_fits=0,
    limits=(
        "Correlated asset/date features; no causal attribution or inferential significance claim"
    ),
)
a.output.write_text(json.dumps(out, indent=2) + "\n")
for label, r in result.items():
    print(label, r["unique_dates"], ">5", r["overall_abs_z_gt5"], ">10", r["overall_abs_z_gt10"])
    print(sorted(r["fields"], key=lambda z: z["max_abs_z"], reverse=True)[:3])
