"""One frozen daily distribution pair. No wallet, live connector or secret access."""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
import platform
import resource
import subprocess
import time
import zipfile
from pathlib import Path

import numpy as np
import polars as pl
import torch
from scipy.stats import norm
from torch import nn

HERE = Path(__file__).resolve().parent
DAY = 86_400_000_000
WHITELIST = ["dt", "high", "low", "close", "quote_volume", "complete_kline"]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def date_us(s: str) -> int:
    return int(np.datetime64(s, "us").astype(np.int64))


def recover(config: dict, state: Path) -> Path:
    """Reuse exact Git objects, never perform an exchange download."""
    archive = state / "FEATURE_ARCHIVE.zip"
    if archive.exists():
        if sha(archive.read_bytes()) != config["archive_sha256"]:
            raise ValueError("cached archive SHA mismatch")
        return archive
    prefix = "research/temporal-feature-data-20261009/"

    def get(name):
        return subprocess.check_output(
            ["git", "show", f'{config["data_commit"]}:{prefix}{name}'], cwd=HERE
        )

    index = json.loads(get("INDEX.json"))
    parts = []
    for part in index["parts"]:
        body = get(part["file"])
        if len(body) != part["bytes"] or sha(body) != part["SHA256"]:
            raise ValueError("archive part mismatch")
        parts.append(body)
    body = b"".join(parts)
    if len(body) != index["bytes"] or sha(body) != config["archive_sha256"]:
        raise ValueError("full archive mismatch")
    archive.write_bytes(body)
    return archive


def load_daily(archive: Path, config: dict):
    """Read only causal primitive columns, plus prior causal feature witnesses."""
    if sha(archive.read_bytes()) != config["archive_sha256"]:
        raise ValueError("archive identity")
    tables, hashes = [], {}
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
        if len(set(names)) != len(names) or any(
            Path(p).is_absolute() or ".." in Path(p).parts for p in names
        ):
            raise ValueError("unsafe archive")
        # Entire packet is 2020–2025 public evidence, not the collector's 2026 lock.
        if z.testzip() is not None:
            raise ValueError("archive CRC")
        members = json.loads(z.read("MEMBERS.json"))["files"]
        for name, spec in members.items():
            body = z.read(name)
            if sha(body) != spec["SHA256"] or len(body) != spec["bytes"]:
                raise ValueError(f"member identity: {name}")
            hashes[name] = spec["SHA256"]
        for symbol in config["symbols"]:
            name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
            df = pl.read_parquet(io.BytesIO(z.read(name)), columns=WHITELIST).sort("dt")
            if df["dt"].n_unique() != df.height:
                raise ValueError("duplicate day")
            tables.append(df)
        witness = np.load(io.BytesIO(z.read("features/CORE5_PRE_MAY2024.npz")), allow_pickle=False)
        if witness["symbol_order"].tolist() != config["symbols"]:
            raise ValueError("asset order")
        witness = {k: witness[k] for k in witness.files}
    # Datetime Parquet dtype can be ns or us; convert explicitly before constructing grid.
    tables = [t.with_columns(pl.col("dt").dt.cast_time_unit("us")) for t in tables]
    tmin = min(int(t["dt"].cast(pl.Int64).min()) for t in tables)
    tmax = max(int(t["dt"].cast(pl.Int64).max()) for t in tables)
    if tmax >= date_us("2026-03-01"):
        raise ValueError("locked period is outside this adapter's domain")
    dates = np.arange(tmin, tmax + DAY, DAY, dtype=np.int64)
    grid = pl.DataFrame({"dt": dates}).with_columns(
        pl.col("dt").cast(pl.Datetime("us", "UTC"))
    )
    close = np.full((len(dates), len(tables)), np.nan)
    ranges, quote = close.copy(), close.copy()
    for asset, df in enumerate(tables):
        a = grid.join(df, on="dt", how="left")
        good = a["complete_kline"].fill_null(False).to_numpy().copy()
        c, h, lo, v = [a[k].to_numpy() for k in ["close", "high", "low", "quote_volume"]]
        good &= np.isfinite(c) & np.isfinite(h) & np.isfinite(lo) & np.isfinite(v)
        good &= (c > 0) & (lo > 0) & (h >= c) & (c >= lo) & (v >= 0)
        close[good, asset] = c[good]
        ranges[good, asset] = np.log(h[good] / lo[good])
        quote[good, asset] = np.log1p(v[good])
    available = dates + DAY
    returns = np.full_like(close, np.nan)
    returns[1:] = np.log(close[1:] / close[:-1])
    common, ix, iw = np.intersect1d(
        available, witness["completed_day_available_us"], return_indices=True
    )
    finite = witness["close_observed_mask"][iw] & np.isfinite(close[ix])
    if not np.array_equal(close[ix][finite], witness["close"][iw][finite]):
        raise ValueError("close witness mismatch")
    mom = witness["x"][iw, :, witness["feature_order"].tolist().index("mom1")]
    finite_r = np.isfinite(returns[ix]) & np.isfinite(mom)
    error = np.abs(returns[ix][finite_r] - np.log1p(mom[finite_r]))
    if np.max(error, initial=0) > 1e-6:
        raise ValueError("return witness mismatch")
    sigma = causal_sigma(returns, config["ewma_decay"], config["sigma_floor"])
    x = np.stack([returns, ranges, quote, sigma], axis=-1)
    # Cross-section at the same completed day; unavailable members remain unavailable.
    counts = np.isfinite(returns).sum(1)
    mean_r = np.divide(np.nansum(returns, axis=1), counts,
                       out=np.full(len(dates), np.nan), where=counts > 0)
    counts_s = np.isfinite(sigma).sum(1)
    mean_s = np.divide(np.nansum(sigma, axis=1), counts_s,
                       out=np.full(len(dates), np.nan), where=counts_s > 0)
    z = np.stack([mean_r, mean_s], axis=-1)
    audit = {
        "archive_sha256": config["archive_sha256"], "source_commit": config["data_commit"],
        "member_sha256": hashes, "symbols": config["symbols"], "whitelist": WHITELIST,
        "original_raw_fresh_verification": "NOT_RUN_RAW_ZIPS_ABSENT",
        "crc_and_declared_member_hashes": "PASS", "close_witness_cells": int(finite.sum()),
        "return_witness_cells": int(finite_r.sum()), "return_witness_max_error": float(error.max()),
        "observed_closes": np.isfinite(close).sum(0).tolist(),
        "daily_grid_start": str(np.datetime64(int(dates[0]), "us")),
        "daily_grid_end": str(np.datetime64(int(dates[-1]), "us")),
        "availability": "historical completed-day proxy; original publication time UNKNOWN",
        "locked_data_access": "NONE", "provider_download_bytes": 0,
    }
    return available, x, z, returns, sigma, audit


def causal_sigma(returns, decay, floor):
    out = np.full_like(returns, np.nan)
    for asset in range(returns.shape[1]):
        variance = np.nan
        for i, r in enumerate(returns[:, asset]):
            if not np.isfinite(r):
                variance = np.nan
                continue
            variance = r * r if not np.isfinite(variance) else decay * variance + (1-decay) * r*r
            out[i, asset] = max(np.sqrt(variance), floor)
    return out


def build_samples(available, x, z, returns, sigma, config, periods):
    """Keep the real day grid; boundaries constrain label maturity, never feature fit."""
    rows, skipped = [], {"boundary_purge": 0, "missing_past": 0, "missing_future": 0}
    lookback, horizon = config["lookback"], config["horizon"]
    for block, (start, end) in enumerate(periods):
        for i in np.flatnonzero((available >= date_us(start)) & (available < date_us(end))):
            for asset in range(returns.shape[1]):
                if i+horizon >= len(available) or available[i+horizon] >= date_us(end):
                    skipped["boundary_purge"] += 1
                    continue
                if i < lookback-1:
                    skipped["missing_past"] += 1
                    continue
                xx, zz = x[i-lookback+1:i+1, asset], z[i-lookback+1:i+1]
                yy = returns[i+1:i+horizon+1, asset]
                if not np.isfinite(xx).all() or not np.isfinite(zz).all():
                    skipped["missing_past"] += 1
                    continue
                if not np.isfinite(yy).all():
                    skipped["missing_future"] += 1
                    continue
                if not (available[i+horizon] == available[i] + horizon*DAY):
                    raise ValueError("noncontiguous calendar")
                past = returns[i-lookback+1:i+1, asset]
                rows.append((xx, zz, yy, sigma[i, asset], available[i],
                             available[i+horizon], asset, block, past.mean(),
                             max(past.std(ddof=1), config["sigma_floor"])))
    if not rows:
        raise ValueError("no mature samples")
    names = ["x", "z", "y", "sigma", "origin_us", "label_end_us", "asset", "block", "mu", "std"]
    result = {name: np.asarray([r[j] for r in rows]) for j, name in enumerate(names)}
    result["skipped"] = skipped
    return result


def fit_scalers(train):
    scalers = {}
    for name in ["x", "z"]:
        a = train[name].reshape(-1, train[name].shape[-1])
        mean, std = a.mean(0), a.std(0)
        std = np.where(std > 1e-8, std, 1.)
        scalers[name] = {"mean": mean, "std": std}
    return scalers


class QLSTM(nn.Module):
    """Small own adapter of the published two LSTM/sorted quantile architecture."""

    def __init__(self, config):
        super().__init__()
        h = config["hidden"]
        self.asset_lstm = nn.LSTM(4, h, batch_first=True)
        self.market_lstm = nn.LSTM(2, h, batch_first=True)
        self.quantile_head = nn.Sequential(nn.Linear(h, h), nn.ReLU(), nn.Linear(h, len(config["quantiles"])))
        self.market_head = nn.Sequential(nn.Linear(h, h), nn.ReLU(), nn.Linear(h, 1))
        nn.init.zeros_(self.quantile_head[-1].weight)
        with torch.no_grad():
            self.quantile_head[-1].bias.copy_(torch.tensor(norm.ppf(config["quantiles"]), dtype=torch.float32))
        nn.init.zeros_(self.market_head[-1].weight)
        nn.init.zeros_(self.market_head[-1].bias)

    def forward(self, x, z, sigma):
        h, _ = self.asset_lstm(x)
        m, _ = self.market_lstm(z)
        normalized = self.quantile_head(h[:, -1]).sort(dim=1).values
        factor = self.market_head(m[:, -1]).clamp(-3., 3.).exp()
        raw = normalized * sigma[:, None] * factor
        return normalized, raw


def pinball_numpy(q, y, taus):
    diff = y[..., None] - q[:, None, :]
    return np.maximum(np.asarray(taus)*diff, (np.asarray(taus)-1)*diff)


def two_stage_loss(normalized, raw, y, sigma, taus):
    t = torch.as_tensor(taus, dtype=y.dtype, device=y.device)
    def loss(q, yy):
        d = yy[:, :, None] - q[:, None, :]
        return torch.maximum(t*d, (t-1)*d).mean()
    return loss(raw*100, y*100) + loss(normalized, y/sigma[:, None])


def quantile_crps(q, y, taus):
    """Exact 2*integral_0^1 rho_u(y-Q(u))du for linear Q and endpoint atoms."""
    q, y = np.asarray(q, dtype=np.float64), np.asarray(y, dtype=np.float64)
    u = np.r_[0., taus, 1.]
    qq = np.concatenate([q[:, :1], q, q[:, -1:]], axis=1)
    out = np.zeros_like(y)
    for j in range(len(u)-1):
        lo, hi = u[j:j+2]
        slope = (qq[:, j+1]-qq[:, j])[:, None] / (hi-lo)
        intercept = qq[:, j, None] - slope*lo
        root = np.divide(y-intercept, slope, out=np.full_like(y, hi), where=slope != 0)
        mid = np.clip(root, lo, hi)
        # A flat segment chooses its sign using y-Q, not an artificial root.
        mid = np.where(slope == 0, np.where(y >= intercept, hi, lo), mid)
        def lower(v):
            return (y-intercept)*v*v/2 - slope*v*v*v/3
        def upper(v):
            return (intercept-y)*v + (slope-intercept+y)*v*v/2 - slope*v*v*v/3
        out += 2*(lower(mid)-lower(lo)+upper(hi)-upper(mid))
    return out


def cdf_at(q, value, taus):
    # Mid-distribution CDF at atoms, compatible with endpoint-atom PIT diagnostics.
    result = []
    for row, y in zip(q, np.broadcast_to(value, (len(q),)), strict=True):
        left = float(np.interp(y, row, taus, left=0., right=1.))
        if y == row[0]:
            left = float(taus[0]/2)
        if y == row[-1]:
            left = float((1+taus[-1])/2)
        result.append(left)
    return np.asarray(result)


def short_net(log_return, fee, execution, funding_per_entry_notional):
    """Unit-price scenario only: funding positive means a receipt for a short."""
    exit_ratio = np.exp(log_return)
    return 1-exit_ratio-(fee+execution)*(1+exit_ratio)+funding_per_entry_notional


def short_upper_es(q, taus, alpha=.95):
    # Fixed Gauss-Legendre integration of exp(Q(u))-1 in upper tail.
    nodes, weights = np.polynomial.legendre.leggauss(16)
    u = np.unique(np.r_[alpha, np.asarray(taus)[np.asarray(taus) > alpha], 1.])
    total = np.zeros(len(q))
    for lo, hi in zip(u[:-1], u[1:], strict=True):
        p = lo+(nodes+1)*(hi-lo)/2
        vals = np.stack([np.interp(p, taus, row) for row in q])
        total += np.expm1(vals) @ weights * ((hi-lo)/2)
    return total/(1-alpha)


def metrics(q, data, config):
    taus = config["quantiles"]
    y = data["y"]
    pb = pinball_numpy(q, y, taus)
    crps = quantile_crps(q, y, taus)
    tail = [taus.index(t) for t in [.01, .05, .95, .99]]
    coverage = ((y >= q[:, taus.index(.05), None]) & (y <= q[:, taus.index(.95), None])).mean()
    violations = (y[:, :, None] < q[:, None, :]).mean(axis=(0, 1))
    calibration = {str(t): float(violations[taus.index(t)]) for t in [.01, .05, .5, .95, .99]}
    pit = np.concatenate([cdf_at(q, y[:, h], taus) for h in range(y.shape[1])])
    es = short_upper_es(q, taus)
    result = {
        "crps_log_return": float(crps.mean()), "pinball_log_return": float(pb.mean()),
        "tail_pinball": float(pb[..., tail].mean()), "coverage90": float(coverage),
        "empirical_cdf_at_quantiles": calibration,
        "max_tail_calibration_error": float(max(abs(calibration[str(t)]-t) for t in [.01, .05, .95, .99])),
        "pit_histogram10": np.histogram(pit, np.linspace(0, 1, 11))[0].tolist(),
        "expected_short_price_loss_upper5pct": float(es.mean()),
        "day1_crps_log_return": float(crps[:, 0].mean()),
        "day1_pinball_log_return": float(pb[:, 0].mean()),
        "predicted_down_probability_mean": float(cdf_at(q, 0., taus).mean()),
        "actual_daily_down_frequency": float((y < 0).mean()),
        "tail_quantile_losses": {str(t): float(pb[..., taus.index(t)].mean()) for t in [.01, .05, .95, .99]},
    }
    return result, crps.mean(1)


def clustered_ci(data, difference, config):
    # Fixed date clusters, joint across all assets; weight by real sample count.
    width = config["bootstrap"]["calendar_block_days"]*DAY
    groups = {}
    for i, (t, block) in enumerate(zip(data["origin_us"], data["block"], strict=True)):
        start = date_us(config["evaluation"][int(block)][0])
        groups.setdefault((int(block), int((t-start)//width)), []).append(i)
    totals = np.asarray([difference[ix].sum() for ix in groups.values()])
    counts = np.asarray([len(ix) for ix in groups.values()])
    rng = np.random.default_rng(config["bootstrap"]["seed"])
    boot = []
    for _ in range(config["bootstrap"]["replicates"]):
        # Stratify calendar blocks; do not let a short period disappear from resamples.
        picked = []
        keys = list(groups)
        for b in sorted(set(k[0] for k in keys)):
            indexes = np.asarray([i for i, k in enumerate(keys) if k[0] == b])
            picked.extend(rng.choice(indexes, len(indexes), replace=True))
        picked = np.asarray(picked)
        boot.append(float(totals[picked].sum()/counts[picked].sum()))
    return {
        "model_minus_control": float(difference.mean()),
        "ci95": np.quantile(boot, [.025, .975]).tolist(),
        "calendar_clusters": len(groups), "clusters_per_block": {
            str(b): sum(k[0] == b for k in groups) for b in sorted(set(k[0] for k in groups))
        }, "cluster_observation_counts": counts.tolist(),
        "method": "paired stratified nonoverlapping44-day calendar clusters; adjacent boundary dependence remains",
        "replicates": config["bootstrap"]["replicates"],
    }


def tensors(data, scalers):
    return tuple(torch.tensor(a, dtype=torch.float32) for a in [
        (data["x"]-scalers["x"]["mean"])/scalers["x"]["std"],
        (data["z"]-scalers["z"]["mean"])/scalers["z"]["std"], data["y"], data["sigma"]
    ])


def train_model(train, val, config, state):
    torch.manual_seed(config["seed"])
    np.random.seed(config["seed"])
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    scalers = fit_scalers(train)
    a, v = tensors(train, scalers), tensors(val, scalers)
    model = QLSTM(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=config["learning_rate"], weight_decay=config["weight_decay"])
    generator = torch.Generator().manual_seed(config["seed"])
    best, best_state, best_epoch, patience, log = np.inf, None, None, 0, []
    for epoch in range(1, config["epochs"]+1):
        model.train()
        order = torch.randperm(len(a[0]), generator=generator)
        total = 0.
        for ix in order.split(config["batch_size"]):
            optimizer.zero_grad()
            normalized, raw = model(a[0][ix], a[1][ix], a[3][ix])
            loss = two_stage_loss(normalized, raw, a[2][ix], a[3][ix], config["quantiles"])
            if not torch.isfinite(loss):
                raise ValueError("nonfinite train loss")
            loss.backward()
            optimizer.step()
            total += loss.item()*len(ix)
        model.eval()
        with torch.no_grad():
            normalized, raw = model(v[0], v[1], v[3])
            vl = two_stage_loss(normalized, raw, v[2], v[3], config["quantiles"]).item()
        if vl < best:
            best, best_epoch, patience = vl, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            patience += 1
        log.append({"epoch": epoch, "train_loss": total/len(a[0]), "validation_loss": vl})
        print(json.dumps(log[-1]), flush=True)
        if patience >= config["patience"]:
            break
    model.load_state_dict(best_state)
    model.eval()
    torch.save({"state_dict": best_state, "config": config, "scalers": scalers}, state/"model.pt")
    np.savez(state/"scalers.npz", **{f"{k}_{j}": d for k, v in scalers.items() for j, d in v.items()})
    return model, scalers, {"epochs": log, "best_epoch": best_epoch, "best_validation_loss": best,
                            "parameters": sum(p.numel() for p in model.parameters())}


def run(config, state):
    archive = recover(config, state)
    available, x, z, r, sigma, audit = load_daily(archive, config)
    roles = {
        "train": build_samples(available, x, z, r, sigma, config, [config["train"]]),
        "validation": build_samples(available, x, z, r, sigma, config, [config["validation"]]),
        "evaluation": build_samples(available, x, z, r, sigma, config, config["evaluation"]),
    }
    # Labels are daily maturity timestamps; validation/test labels may never enter TRAIN.
    labels = {k: set(int(t) for t in (d["origin_us"][:, None]+np.arange(1, config["horizon"]+1)*DAY).ravel())
              for k, d in roles.items()}
    if labels["train"] & labels["validation"] or labels["train"] & labels["evaluation"] or labels["validation"] & labels["evaluation"]:
        raise ValueError("label role overlap")
    split = {}
    for name, d in roles.items():
        split[name] = {
            "asset_origins": len(d["y"]), "distinct_origins": len(np.unique(d["origin_us"])),
            "unique_label_days": len(labels[name]), "skipped": d["skipped"],
            "first_origin": str(np.datetime64(int(d["origin_us"].min()), "us")),
            "last_label_maturity": str(np.datetime64(int(d["label_end_us"].max()), "us")),
            "asset_counts": np.bincount(d["asset"], minlength=len(config["symbols"])).tolist(),
        }
    dump(state/"DATA_AUDIT.json", audit)
    dump(state/"SPLIT_AUDIT.json", {"roles": split, "label_overlap": 0})
    print(json.dumps({"stage": "DATA_READY", "roles": split}), flush=True)
    model, scalers, fit = train_model(roles["train"], roles["validation"], config, state)
    ev = roles["evaluation"]
    inp = tensors(ev, scalers)
    with torch.no_grad():
        q = model(inp[0], inp[1], inp[3])[1].numpy().astype(np.float64)
    base = ev["mu"][:, None] + ev["std"][:, None]*norm.ppf(config["quantiles"])
    mm, mc = metrics(q, ev, config)
    bm, bc = metrics(base, ev, config)
    ci = clustered_ci(ev, mc-bc, config)
    blocks = []
    for block, period in enumerate(config["evaluation"]):
        ix = ev["block"] == block
        d = {k: v[ix] for k, v in ev.items() if isinstance(v, np.ndarray)}
        blocks.append({"period": period, "asset_origins": int(ix.sum()), "distinct_origins": int(np.unique(ev["origin_us"][ix]).size),
                       "model": metrics(q[ix], d, config)[0], "control": metrics(base[ix], d, config)[0]})
    g = config["gate"]
    gain = 1-mm["crps_log_return"]/bm["crps_log_return"]
    gates = {
        "crps_gain_at_least_1pct": gain >= g["min_crps_relative_gain"],
        "paired_upper95_below_zero": ci["ci95"][1] < 0,
        "pinball_improves": mm["pinball_log_return"] < bm["pinball_log_return"],
        "tail_pinball_no_more_than_5pct_worse": all(
            mm["tail_quantile_losses"][str(t)] <= bm["tail_quantile_losses"][str(t)]*g["max_tail_pinball_ratio"]
            for t in [.01, .05, .95, .99]
        ),
        "calibration_no_more_than_1pp_worse": mm["max_tail_calibration_error"] <= bm["max_tail_calibration_error"]+g["max_calibration_error_increase"],
        "every_calendar_block_no_worse": all(b["model"]["crps_log_return"] <= b["control"]["crps_log_return"] for b in blocks),
    }
    if not np.isfinite(q).all() or np.any(np.diff(q, axis=1) < 0):
        raise ValueError("invalid quantiles")
    np.savez_compressed(state/"predictions.npz", origin_us=ev["origin_us"], label_end_us=ev["label_end_us"],
                        asset=ev["asset"], block=ev["block"], y=ev["y"], q_model=q, q_control=base,
                        taus=config["quantiles"], crps_model=mc, crps_control=bc)
    result = {
        "classification": config["classification"], "model": mm, "control": bm,
        "crps_relative_gain": gain, "paired_cluster_uncertainty": ci, "calendar_blocks": blocks,
        "gate": gates, "decision": "DISTRIBUTION_GATE_PASS_ECONOMIC_REVIEW_REQUIRED" if all(gates.values()) else "PAUSE_RECIPE_NO_RETRAIN",
        "economic_wallets": "NOT_RUN_DISTRIBUTION_GATE_FAILED" if not all(gates.values()) else "NOT_RUN_REQUIRES_NATIVE_DECISION_PROTOCOL",
        "fit": fit, "split": split, "data_audit_sha256": sha((state/"DATA_AUDIT.json").read_bytes()),
        "source_sha256": {p.name: sha(p.read_bytes()) for p in HERE.iterdir() if p.suffix in [".py", ".sh"] or p.name in ["config.json", "PROTOCOL.md", "SOURCES.md"]},
        "config_sha256": sha((HERE/"config.json").read_bytes()),
        "external_artifacts": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
                               for p in [state/"model.pt", state/"scalers.npz", state/"predictions.npz", state/"DATA_AUDIT.json", state/"SPLIT_AUDIT.json"]},
        "environment": {"python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__, "polars": pl.__version__,
                        "device": "cpu", "threads": torch.get_num_threads(), "deterministic_algorithms": True},
        "scope": {"fits": 1, "hyperparameter_trials": 1, "provider_download_bytes": 0, "locked_access": "NONE", "original_Q1_Q2_ledgers": "MISSING"},
    }
    dump(state/"RESULT.json", result)
    print(json.dumps({"stage": "COMPLETE", "decision": result["decision"], "model_crps": mm["crps_log_return"],
                      "control_crps": bm["crps_log_return"], "gain": gain, "gates": gates}), flush=True)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    state = args.state.resolve()
    if state.exists():
        raise ValueError("fresh experiment state required; retained attempts must not be overwritten")
    state.mkdir(parents=True)
    config = json.loads((HERE/"config.json").read_text())
    receipt = {"started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "config_sha256": sha((HERE/"config.json").read_bytes()),
               "source_git_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=HERE, text=True).strip(), "stage": "STARTED"}
    dump(state/"ATTEMPT.json", receipt)
    start = time.monotonic()
    try:
        run(config, state)
        receipt["stage"] = "SUCCESS"
    except BaseException as exc:
        receipt.update(stage="FAILED", error_type=type(exc).__name__, error=str(exc))
        raise
    finally:
        receipt["elapsed_seconds"] = time.monotonic()-start
        receipt["max_rss_bytes"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
        receipt["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        dump(state/"ATTEMPT.json", receipt)


if __name__ == "__main__":
    main()
