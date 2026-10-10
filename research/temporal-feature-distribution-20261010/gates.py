"""Read-only GRU gate diagnostics; verify manual recurrence against frozen Torch GRU."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from torch.nn import functional as F

from modules.temporal_added_history_july.models import frozen_model, shared_scaler
from modules.temporal_added_history_july.protocol import ORDER
from modules.temporal_two_expert.checkpoint import model_identity

p = argparse.ArgumentParser()
p.add_argument("--state", type=Path, required=True)
p.add_argument("--output", type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[2]
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
with np.load(
    a.state / "feature-input/verified/features/CORE5_PRE_MAY2024.npz", allow_pickle=False
) as z:
    clock = z["completed_day_available_us"]
    values = z["x"]
    valid = z["feature_observed_mask"] & z["close_observed_mask"][..., None]
    observed = z["close_observed_mask"]


def dates(s, e):
    return np.arange(
        np.datetime64(s, "us").astype("int64"),
        np.datetime64(e, "us").astype("int64") + 86400000000,
        86400000000,
    )


def windows(d):
    idx = np.searchsorted(clock, d)[:, None] - np.arange(63, -1, -1)[None, :]
    return values[idx], valid[idx], observed[idx]


old = np.concatenate(
    [
        dates(s, e)
        for s, e in [
            ("2022-01-02", "2022-02-24"),
            ("2022-05-04", "2022-07-30"),
            ("2022-08-01", "2022-10-01"),
            ("2022-10-03", "2023-02-23"),
            ("2023-02-25", "2024-04-29"),
        ]
    ]
)
groups = {
    "old_training_windows": windows(old),
    "added_2021_windows": windows(dates("2021-01-01", "2021-12-31")),
}
for name, folder in [
    ("July_seen", "temporal-july-frozen-transfer-20261010/results"),
    ("Q4_seen", "temporal-selected-refit-q4-20261010/q4-results"),
]:
    with np.load(root / "research" / folder / "FEATURE_ROWS.npz", allow_pickle=False) as z:
        idx = np.arange(63, len(z["values"]))[:, None] - np.arange(63, -1, -1)[None, :]
        groups[name] = (z["values"][idx], z["valid"][idx], z["step_valid"][idx])
results = {}
with torch.no_grad():
    for name in ORDER:
        model, _, _ = frozen_model(name, shared_scaler())
        before = model_identity(model)
        model.eval()
        g = model.base.encoder
        models = {}
        for label, (x, v, o) in groups.items():
            totals = np.zeros(3, dtype=np.int64)
            denom = 0
            err = 0.0
            maxpre = np.zeros(3)
            evaluated = 0
            for b in range(0, len(x), 32):
                mask = torch.tensor(v[b : b + 32])
                obs = torch.tensor(o[b : b + 32]).permute(0, 2, 1).reshape(-1, 64)
                raw = torch.tensor(x[b : b + 32], dtype=torch.float64)
                clean = torch.where(mask, raw, model.base.mean)
                z = (
                    torch.cat(((clean - model.base.mean) / model.base.scale, mask.double()), dim=-1)
                    .permute(0, 2, 1, 3)
                    .reshape(-1, 64, 48)
                )
                inp = F.linear(z, g.weight_ih_l0, g.bias_ih_l0)
                h = torch.zeros((len(z), 32), dtype=torch.float64)
                for t in range(64):
                    hr, hz, hn = F.linear(h, g.weight_hh_l0, g.bias_hh_l0).chunk(3, dim=-1)
                    ir, iz, inn = inp[:, t].chunk(3, dim=-1)
                    rp, zp = ir + hr, iz + hz
                    np_ = inn + torch.sigmoid(rp) * hn
                    keep = obs[:, t]
                    denom += int(keep.sum()) * 32
                    for j, (pre, cut) in enumerate(
                        zip((rp, zp, np_), (8.0, 8.0, 4.0), strict=True)
                    ):
                        q = pre[keep].abs()
                        totals[j] += int((q > cut).sum())
                        maxpre[j] = max(maxpre[j], float(q.max()) if q.numel() else 0.0)
                    new = (1 - torch.sigmoid(zp)) * torch.tanh(np_) + torch.sigmoid(zp) * h
                    h = torch.where(keep[:, None], new, h)
                if bool(obs.all()):
                    _, native = g(z)
                    err = max(err, float((native[0] - h).abs().max()))
                    evaluated += len(z)
            assert err < 1e-12
            models[label] = dict(
                windows=len(x),
                observed_gate_positions=denom,
                fraction_reset_abs_pre_gt8=float(totals[0] / denom),
                fraction_update_abs_pre_gt8=float(totals[1] / denom),
                fraction_candidate_abs_pre_gt4=float(totals[2] / denom),
                maximum_abs_preactivations=maxpre.tolist(),
                native_recurrence_max_error=err,
                native_parity_asset_windows=evaluated,
            )
        assert model_identity(model) == before
        results[name] = models
out = dict(
    status="FROZEN_ENCODER_ONLY_DIAGNOSTIC",
    results=results,
    policy_inferences=0,
    wallet_runs=0,
    optimizer_updates=0,
    scaler_fits=0,
    limits=(
        "Overlapping windows and correlated gate positions are not independent "
        "observations. Saturation is descriptive and is not proof of the economic "
        "failure mechanism. No forward policy outputs or model selection."
    ),
)
a.output.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out))
