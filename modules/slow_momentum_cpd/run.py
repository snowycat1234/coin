"""One finite paired historical prediction experiment, with immutable receipts."""

import argparse
import csv
import hashlib
import io
import json
import subprocess
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import polars as pl
import torch
from scipy.stats import spearmanr
from torch import nn

from .core import DAY_US, SYMBOLS, FrozenGP, Scaler, sample_index, trend_features

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "research/slow-momentum-cpd-20261011"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def utc_us(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1e6)


def write_json(path, value):
    with path.open("x") as file:
        json.dump(value, file, indent=2, allow_nan=False)
        file.write("\n")


def recover_archive(repo, destination, protocol):
    """Recover exactly three already-public Git objects, never provider data."""
    source = protocol["source"]
    if destination.exists():
        if sha(destination.read_bytes()) != source["archive_sha256"]:
            raise ValueError("Existing feature archive hash mismatch")
        return
    parts = []
    for part in source["parts"]:
        data = subprocess.check_output(
            ["git", "-C", str(repo), "show", source["commit"] + ":" + source["base"] + part["file"]]
        )
        if sha(data) != part["sha256"] or len(data) != part["bytes"]:
            raise ValueError("Git feature part identity mismatch")
        parts.append(data)
    data = b"".join(parts)
    if sha(data) != source["archive_sha256"]:
        raise ValueError("Recovered feature archive identity mismatch")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("xb") as file:
        file.write(data)


def load_close(archive, protocol):
    """New explicit derivation whitelist: dt, close, complete_kline, symbol only.

    The prior archive's ready-made 24 features are NOT used for this new study.
    Its evidence Parquets are whitelisted to reconstruct eight new trend inputs;
    funding/premium/outcome fields never enter the model. All member bytes verified.
    """
    data = archive.read_bytes()
    if sha(data) != protocol["source"]["archive_sha256"]:
        raise ValueError("Feature archive hash mismatch")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        if len(z.namelist()) != len(set(z.namelist())):
            raise ValueError("Duplicate archive member")
        members = json.loads(z.read("MEMBERS.json"))["files"]
        columns = ["dt", "close", "complete_kline", "symbol"]
        tables = []
        audit = []
        for symbol in SYMBOLS:
            name = f"source_tables_not_model_inputs/daily_features/{symbol}.parquet"
            raw = z.read(name)
            if sha(raw) != members[name]["SHA256"] or len(raw) != members[name]["bytes"]:
                raise ValueError("Price evidence member hash mismatch")
            frame = pl.read_parquet(io.BytesIO(raw), columns=columns)
            frame = frame.filter(
                (pl.col("dt").dt.epoch("us") >= utc_us("2020-01-01"))
                & (pl.col("dt").dt.epoch("us") < utc_us("2024-04-30"))
            )
            if frame["dt"].n_unique() != len(frame) or frame["symbol"].unique().to_list() != [
                symbol
            ]:
                raise ValueError("Duplicate clocks or wrong symbol axis")
            frame = frame.sort("dt")
            stamp = frame["dt"].dt.epoch("us").to_numpy()
            if len(stamp) and np.any(stamp % DAY_US):
                raise ValueError("Non-UTC daily bar start")
            prices = frame["close"].to_numpy().astype(float)
            observed = (
                frame["complete_kline"].fill_null(False).to_numpy()
                & np.isfinite(prices)
                & (prices > 0)
            )
            prices[~observed] = np.nan
            tables.append((stamp, prices))
            audit.append(
                {
                    "symbol": symbol,
                    "member_sha256": sha(raw),
                    "rows": len(frame),
                    "observed": int(observed.sum()),
                    "whitelist": columns,
                }
            )
    calendar = np.arange(utc_us("2020-01-01"), utc_us("2024-04-30"), DAY_US)
    close = np.full((len(calendar), len(SYMBOLS)), np.nan)
    for asset, (stamps, prices) in enumerate(tables):
        close[np.searchsorted(calendar, stamps), asset] = prices
    return calendar + DAY_US, close, audit


class TrendLSTM(nn.Module):
    def __init__(self, hidden=16):
        super().__init__()
        # Both arms retain identical parameter axes/initialisation. Baseline's last
        # two channels are zero, so they cannot add information or receive gradients.
        self.lstm = nn.LSTM(10, hidden, batch_first=True)
        self.output = nn.Linear(hidden, 1)

    def forward(self, x):
        hidden, _ = self.lstm(x)
        return self.output(hidden[:, -1]).squeeze(-1)


def sequences(x, rows, length=63):
    return np.stack([x[t - length + 1 : t + 1, asset] for t, asset in rows]).astype("float32")


def predict(model, x):
    model.eval()
    with torch.no_grad():
        return np.concatenate(
            [model(torch.from_numpy(x[i : i + 256])).numpy() for i in range(0, len(x), 256)]
        ).astype(float)


def fit_pair(x, target, rows, protocol, state, seed):
    outputs = {}
    initial_shas = []
    for arm in ("trend", "trend_cpd"):
        checkpoint = state / f"{arm}-seed{seed}.pt"
        if checkpoint.exists():
            raise FileExistsError("No silent rerun or checkpoint overwrite")
        torch.manual_seed(seed)
        rng = np.random.default_rng(seed)
        model = TrendLSTM(protocol["training"]["hidden"])
        initial = b"".join(v.detach().numpy().tobytes() for v in model.state_dict().values())
        initial_shas.append(sha(initial))
        optimizer = torch.optim.Adam(model.parameters(), lr=protocol["training"]["lr"])
        inputs = x.copy()
        if arm == "trend":
            inputs[:, :, 8:] = 0
        tx = torch.from_numpy(inputs)
        ty = torch.tensor(target, dtype=torch.float32)
        before = float(np.mean((predict(model, inputs) - target) ** 2))
        started = time.monotonic()
        for update in range(protocol["training"]["updates"]):
            selected = rng.integers(0, len(rows), size=protocol["training"]["batch"])
            model.train()
            optimizer.zero_grad()
            loss = nn.functional.mse_loss(model(tx[selected]), ty[selected])
            if not torch.isfinite(loss):
                raise ValueError("Nonfinite loss: stop, no recipe retry")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            if (update + 1) % 64 == 0:
                print(
                    f"FIT {arm} seed={seed} updates={update + 1} loss={float(loss.detach()):.6f}",
                    flush=True,
                )
        after = float(np.mean((predict(model, inputs) - target) ** 2))
        torch.save(
            {
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "torch_rng": torch.get_rng_state(),
                "numpy_rng": rng.bit_generator.state,
                "updates": protocol["training"]["updates"],
                "seed": seed,
            },
            checkpoint,
        )
        adam_ages = sorted({int(v["step"]) for v in optimizer.state.values()})
        outputs[arm] = (
            model,
            {
                "arm": arm,
                "seed": seed,
                "initial_sha256": sha(initial),
                "checkpoint_sha256": sha(checkpoint.read_bytes()),
                "updates": protocol["training"]["updates"],
                "adam_ages": adam_ages,
                "parameters": sum(p.numel() for p in model.parameters()),
                "training_mse_before": before,
                "training_mse_after": after,
                "seconds": time.monotonic() - started,
            },
        )
    if initial_shas[0] != initial_shas[1]:
        raise AssertionError("Paired initial states differ")
    return outputs


def metrics(y, prediction, rows):
    daily_ic = []
    for t in np.unique(rows[:, 0]):
        select = rows[:, 0] == t
        if select.sum() >= 3 and np.std(prediction[select]) > 0:
            daily_ic.append(float(spearmanr(y[select], prediction[select]).statistic))
    return {
        "n": len(y),
        "days": len(np.unique(rows[:, 0])),
        "mse": float(np.mean((prediction - y) ** 2)),
        "direction_hit": float(np.mean((prediction > 0) == (y > 0))),
        "pooled_pearson": float(np.corrcoef(prediction, y)[0, 1]),
        "mean_daily_rank_ic": float(np.mean(daily_ic)),
        "rank_days": len(daily_ic),
    }


def block_bootstrap(rows, loss_difference, replicates=1000, width=14, seed=9901):
    # Resample within each declared block; do not wrap across calendar gaps.
    daily = []
    for block_rows, block_difference in zip(rows, loss_difference, strict=True):
        days = np.unique(block_rows[:, 0])
        if np.any(np.diff(days) != 1):
            raise ValueError("Bootstrap cannot compress or bridge missing calendar dates")
        daily.append(np.array([block_difference[block_rows[:, 0] == t].mean() for t in days]))
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(replicates):
        draws = []
        for values in daily:
            starts = rng.integers(
                0, len(values) - width + 1, size=int(np.ceil(len(values) / width))
            )
            draws.append(np.concatenate([values[s : s + width] for s in starts])[: len(values)])
        samples.append(np.concatenate(draws).mean())
    return {
        "mean_daily_loss_improvement": float(np.concatenate(daily).mean()),
        "ci95": np.quantile(samples, [0.025, 0.975]).tolist(),
        "replicates": replicates,
        "block_days": width,
        "seed": seed,
        "effective_independent_n": "UNKNOWN",
        "scope": "conditional development uncertainty; not independent OOS",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--recover-only", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    state = args.state.resolve()
    if not state.is_relative_to(Path("/workspace")):
        raise ValueError("Independent workspace state required")
    state.mkdir(parents=True, exist_ok=True)
    protocol = json.loads((EXPERIMENT / "PROTOCOL.json").read_text())
    archive = state / "source/features.zip"
    recover_archive(ROOT, archive, protocol)
    if args.recover_only:
        available, close, audit = load_close(archive, protocol)
        print(
            json.dumps(
                {
                    "archive_sha256": sha(archive.read_bytes()),
                    "symbols": SYMBOLS,
                    "calendar_rows": len(available),
                    "observed": np.isfinite(close).sum(axis=0).tolist(),
                    "sources": audit,
                },
                indent=2,
            )
        )
        return
    if args.preflight:
        available, close, audit = load_close(archive, protocol)
        features, returns, vol = trend_features(close)
        splits = [protocol["training"]["dates"], *protocol["validation"]]
        counts = []
        for dates in splits:
            rows = sample_index(features, returns, vol, available, *map(utc_us, dates))
            counts.append(
                {
                    "dates": dates,
                    "samples": len(rows),
                    "per_asset": np.bincount(rows[:, 1], minlength=5).tolist(),
                    "latest_label_end_us": int(available[rows[:, 0] + 1].max()),
                    "boundary_us": utc_us(dates[1]),
                }
            )
        write_json(
            state / "PREFLIGHT.json",
            {
                "source_audit": audit,
                "splits": counts,
                "real_fits": 0,
                "wallets": 0,
                "source_archive_sha256": sha(archive.read_bytes()),
            },
        )
        print(json.dumps(counts, indent=2))
        return
    if (state / "ATTEMPT.json").exists():
        raise FileExistsError("One scientific attempt only; inspect the retained attempt")
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    write_json(
        state / "ATTEMPT.json",
        {
            "attempt": 1,
            "start_utc": datetime.now(timezone.utc).isoformat(),
            "recipe_retries": 0,
            "protocol_sha256": sha((EXPERIMENT / "PROTOCOL.json").read_bytes()),
        },
    )
    started = time.monotonic()
    available, close, audit = load_close(archive, protocol)
    features, returns, vol = trend_features(close)
    start, end = map(utc_us, protocol["training"]["dates"])
    train_rows = sample_index(features, returns, vol, available, start, end)
    if len(train_rows) < 1000:
        raise ValueError("Insufficient complete, mature training samples")
    print(f"TRAIN samples={len(train_rows)}; fitting training-only GP", flush=True)
    gp = FrozenGP.fit(returns, available, start, end, maxiter=protocol["gp"]["maxiter"])
    cp = gp.transform(returns)
    all_features = np.concatenate((features, cp), axis=2)
    scaler, used = Scaler.fit(all_features, train_rows)
    train_x = sequences(scaler.transform(all_features), train_rows)
    target = (
        returns[train_rows[:, 0] + 1, train_rows[:, 1]] / vol[train_rows[:, 0], train_rows[:, 1]]
    )
    gp_info = {
        "mean": gp.mean,
        "scale": gp.scale,
        "stationary_log_parameters": gp.stationary.tolist(),
        "change_log_parameters": gp.change.tolist(),
        "locations": gp.locations.tolist(),
        "fit": gp.fit_info,
        "scaler_mean": scaler.mean.tolist(),
        "scaler_scale": scaler.scale.tolist(),
        "scaler_unique_rows": int(used.sum()),
        "scaler_latest_available_us": int(available[np.flatnonzero(used.any(axis=1))[-1]]),
        "training_samples": len(train_rows),
        "latest_training_label_end_us": int(available[train_rows[:, 0] + 1].max()),
    }
    write_json(state / "FROZEN_TRAINING.json", gp_info)
    blocks = []
    for dates in protocol["validation"]:
        rows = sample_index(features, returns, vol, available, *map(utc_us, dates))
        if len(rows) < 300:
            raise ValueError("Insufficient common validation samples")
        blocks.append(
            {
                "dates": dates,
                "rows": rows,
                "x": sequences(scaler.transform(all_features), rows),
                "y": returns[rows[:, 0] + 1, rows[:, 1]] / vol[rows[:, 0], rows[:, 1]],
                "predictions": {"trend": [], "trend_cpd": []},
            }
        )
    fits = []
    for seed in protocol["training"]["seeds"]:
        pair = fit_pair(train_x, target, train_rows, protocol, state, seed)
        for arm, (model, receipt) in pair.items():
            fits.append(receipt)
            for block in blocks:
                inputs = block["x"].copy()
                if arm == "trend":
                    inputs[:, :, 8:] = 0
                block["predictions"][arm].append(predict(model, inputs))
        write_json(state / f"FIT_SEED_{seed}.json", fits[-2:])
    reports = []
    differences = []
    seed_differences = np.zeros(len(protocol["training"]["seeds"]))
    with (state / "PREDICTIONS.csv").open("x", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "block",
                "available_us",
                "label_end_us",
                "symbol",
                "scaled_next_return",
                "trend_seed2001",
                "trend_seed2002",
                "trend_seed2003",
                "cpd_seed2001",
                "cpd_seed2002",
                "cpd_seed2003",
            ]
        )
        for block in blocks:
            rows, y = block["rows"], block["y"]
            a = np.asarray(block["predictions"]["trend"])
            b = np.asarray(block["predictions"]["trend_cpd"])
            baseline, treatment = a.mean(axis=0), b.mean(axis=0)
            ma, mb = metrics(y, baseline, rows), metrics(y, treatment, rows)
            seed_differences += np.sum((a - y) ** 2 - (b - y) ** 2, axis=1)
            differences.append((baseline - y) ** 2 - (treatment - y) ** 2)
            reports.append(
                {
                    "dates": block["dates"],
                    "trend": ma,
                    "trend_cpd": mb,
                    "relative_mse_skill": 1 - mb["mse"] / ma["mse"],
                    "daily_rank_ic_increment": mb["mean_daily_rank_ic"] - ma["mean_daily_rank_ic"],
                    "train_mean_mse": float(np.mean((y - target.mean()) ** 2)),
                    "per_seed_relative_skill": (
                        1 - np.mean((b - y) ** 2, axis=1) / np.mean((a - y) ** 2, axis=1)
                    ).tolist(),
                }
            )
            for i, (t, asset) in enumerate(rows):
                writer.writerow(
                    [
                        block["dates"][0],
                        int(available[t]),
                        int(available[t + 1]),
                        SYMBOLS[asset],
                        y[i],
                        *a[:, i].tolist(),
                        *b[:, i].tolist(),
                    ]
                )
    bootstrap = block_bootstrap([b["rows"] for b in blocks], differences)
    conditions = {
        "positive_skill_in_at_least_two_blocks": sum(r["relative_mse_skill"] > 0 for r in reports)
        >= 2,
        "positive_skill_for_at_least_two_seeds": int((seed_differences > 0).sum()) >= 2,
        "aggregate_date_mean_improvement_positive": bootstrap["mean_daily_loss_improvement"] > 0,
        "bootstrap_lower_bound_positive": bootstrap["ci95"][0] > 0,
        "mean_rank_ic_increment_at_least_001": np.mean(
            [r["daily_rank_ic_increment"] for r in reports]
        )
        >= 0.01,
    }
    passed = all(bool(v) for v in conditions.values())
    result = {
        "status": "PREDICTION_GATE_PASS_NATIVE_REQUIRED"
        if passed
        else "STOP_PREDICTION_INCREMENT_NOT_ESTABLISHED",
        "evidence": "REAL_PROJECT_SEEN_HISTORICAL_PREDICTION_ADAPTATION",
        "paper_exact_reproduction": "NOT_RUN",
        "fast_reversion_trading_evidence": "NOT_ESTABLISHED",
        "scientific_attempts": 1,
        "lstm_fits": len(fits),
        "gp_fit_groups": 1,
        "gp_optimizer_calls": 2,
        "validation_fit_calls": 0,
        "oracle_targets": False,
        "sweeps": 0,
        "recipe_retries": 0,
        "wallet_accounts": 0,
        "native_wallet": "NOT_RUN_PENDING_GATE_AND_COMPLETE_INPUTS"
        if passed
        else "NOT_RUN_PREDECLARED_PREDICTION_GATE_FAILED",
        "financial_profit_or_apr": "UNKNOWN_NOT_MEASURED",
        "source_commit": protocol["source"]["commit"],
        "research_source_commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "protocol_sha256": sha((EXPERIMENT / "PROTOCOL.json").read_bytes()),
        "source_files": {
            str(p.relative_to(ROOT)): sha(p.read_bytes())
            for p in sorted((ROOT / "modules/slow_momentum_cpd").glob("*.py"))
        },
        "source_audit": audit,
        "frozen_training_sha256": sha((state / "FROZEN_TRAINING.json").read_bytes()),
        "prediction_sha256": sha((state / "PREDICTIONS.csv").read_bytes()),
        "train_samples": len(train_rows),
        "fits": fits,
        "blocks": reports,
        "bootstrap": bootstrap,
        "gate_conditions": {k: bool(v) for k, v in conditions.items()},
        "locked_access": "NONE",
        "original_Q1_Q2_2026_ledgers": "UNAVAILABLE_NOT_RECONSTRUCTED",
        "environment": {
            "torch": torch.__version__,
            "numpy": np.__version__,
            "polars": pl.__version__,
            "device": "CPU",
            "threads": 1,
            "model_reasoning_configuration": "UNKNOWN",
        },
        "elapsed_experiment_seconds": time.monotonic() - started,
    }
    write_json(state / "RESULT.json", result)
    print(
        json.dumps(
            {"status": result["status"], "blocks": reports, "gate": conditions},
            default=bool,
            indent=2,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
