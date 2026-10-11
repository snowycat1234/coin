"""Frozen saved-policy arithmetic; no model imports, learning or wallet construction."""
import argparse
import csv
import hashlib
import json
import math
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT = ROOT / "research/slow-momentum-cpd-cost-feasibility-20261011"
PROTOCOL_SHA = "75bf5b62e8495808ea0763e22669e97f5834c83af88f20323e391049553582da"
SOURCES = {
    2048: ("slow-momentum-cpd-sharpe-continuation-20261011",
           "2d391cdaa5cfdaade0b7c98b89cd5ae0df2cdeb4f9b1d7308b0160acc866cfac"),
    1024: ("slow-momentum-cpd-sharpe-20261011",
           "a5e48ddc6f739fd26ab05a0e09ba7ed511375de203b6f5015751759586690f3a"),
}
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
ARMS = ("trend", "trend_cpd")
POLICIES = tuple(f"{arm}_{suffix}" for arm in ARMS
                 for suffix in ("seed2001", "seed2002", "seed2003", "ensemble"))
BLOCKS = (("2023-01-01", "2023-07-01", 180),
          ("2023-07-01", "2024-01-01", 183),
          ("2024-01-01", "2024-05-01", 120))
RATE = .15 / math.sqrt(365)
FEE, SPREAD, SLIP = .00055, .0004, .0004
DAY_US = 86_400_000_000


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def write_json(path, value):
    with Path(path).open("x") as handle:
        json.dump(value, handle, indent=2, allow_nan=False)
        handle.write("\n")


def utc_us(value):
    return int(datetime.fromisoformat(value).replace(tzinfo=timezone.utc).timestamp() * 1e6)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def preserved():
    counts = {}
    for name in ("slow-momentum-cpd-20261011", "slow-momentum-cpd-sharpe-20261011",
                 "slow-momentum-cpd-training-diagnostic-20261011",
                 "slow-momentum-cpd-sharpe-continuation-20261011"):
        manifest = json.loads((ROOT / "research" / name / "DELIVERY_MANIFEST.json").read_text())
        for path, identity in manifest["files"].items():
            raw = (ROOT / path).read_bytes()
            if sha(raw) != identity["sha256"] or len(raw) != identity["bytes"]:
                raise ValueError("Frozen evidence changed: " + path)
        counts[name] = len(manifest["files"])
    old = json.loads((ROOT / "research/slow-momentum-cpd-20261011/results/RESULT.json").read_text())
    for path, identity in old["source_files"].items():
        assert sha((ROOT / path).read_bytes()) == identity
    external = []
    for fit in old["fits"]:
        path = Path("/workspace/slow-momentum-state") / f"{fit['arm']}-seed{fit['seed']}.pt"
        assert sha(path.read_bytes()) == fit["checkpoint_sha256"]
        external.append(str(path))
    proposal = json.loads((ROOT / "research/slow-momentum-cpd-training-diagnostic-20261011/CONTINUATION_PROPOSAL.json").read_text())
    for name, identity in proposal["predecessor"]["model_checkpoint_lineage_sha256"].items():
        path = Path("/workspace/slow-momentum-sharpe-state") / name
        assert sha(path.read_bytes()) == identity
        external.append(str(path))
    return {"status": "BYTE_UNCHANGED", "manifest_files": counts,
            "original_fit_sources": len(old["source_files"]), "external_model_files": len(external)}


def verify_cost():
    path = ROOT / "research/recover-frozen-runner-20261009/FINANCIAL_CONFIG.json"
    assert sha(path.read_bytes()) == "84cb7726bbd38a700cc9b31c456b5b8bf5f93d3b4948293bd05ea6ea19cafd68"
    from scripts.investment.bybit_cost_inputs import scenario_config
    cost = json.loads(path.read_text())["cost"]
    config = scenario_config(cost)
    assert (float(config.fee_rate), float(config.half_spread_bps) / 1e4,
            float(config.slippage_bps) / 1e4) == (FEE, SPREAD, SLIP)
    assert cost["id"] == "BASE27" and cost["second_debit_execution_cost"] is False
    return {"config_sha256": sha(path.read_bytes()), "id": "BASE27",
            "fee_bps": 5.5, "half_spread_bps": 4, "slippage_bps": 4,
            "nominal_per_side_bps": 13.5, "historical_native_rate_certified": False}


def read_saved(checkpoint):
    name, identity = SOURCES[checkpoint]
    path = ROOT / "research" / name / "results/POSITIONS.csv"
    assert sha(path.read_bytes()) == identity
    rows = list(csv.DictReader(path.open()))
    blocks, offset = [], 0
    for start, end, days in BLOCKS:
        axis = rows[offset:offset + days * 5]
        offset += len(axis)
        if len(axis) != days * 5:
            raise ValueError("Incomplete saved axis")
        positions = np.array([[float(row[k]) for k in POLICIES] for row in axis]).reshape(days, 5, 8)
        vol = np.array([float(row["daily_vol"] or "nan") for row in axis]).reshape(days, 5)
        scaled = np.array([float(row["scaled_next_return"] or "nan") for row in axis]).reshape(days, 5)
        eligible = np.array([int(row["eligible"]) for row in axis]).reshape(days, 5)
        for i, row in enumerate(axis):
            assert row["block"] == start and row["symbol"] == SYMBOLS[i % 5]
            assert int(row["available_us"]) == utc_us(start) + (i // 5) * DAY_US
            assert int(row["label_end_us"]) == int(row["available_us"]) + DAY_US
            assert int(row["label_end_us"]) < utc_us(end)  # equality purged, no bridge
        if not np.isin(eligible, (0, 1)).all() or not np.isfinite(positions).all():
            raise ValueError("Invalid saved eligibility/positions")
        if np.max(np.abs(positions)) > 1 or np.any(positions[eligible == 0] != 0):
            raise ValueError("Position bound/cash eligibility")
        for j in (0, 4):
            np.testing.assert_allclose(positions[:, :, j + 3], positions[:, :, j:j + 3].mean(2), rtol=0, atol=1e-15)
        valid = eligible.astype(bool)
        if not (np.isfinite(vol[valid]).all() and (vol[valid] > 0).all()
                and np.isfinite(scaled[valid]).all()):
            raise ValueError("Missing eligible risk or mature outcome")
        targets = np.zeros_like(positions)
        targets[valid] = RATE * positions[valid] / vol[valid, None] / 5
        returns = np.full_like(vol, np.nan)
        observed = np.isfinite(vol) & (vol > 0) & np.isfinite(scaled)
        returns[observed] = scaled[observed] * vol[observed] / RATE
        blocks.append({"start": start, "end": end, "days": days,
                       "targets": targets, "returns": returns, "scaled": scaled,
                       "positions": positions, "eligible": eligible})
    assert offset == len(rows) == 2415
    return blocks


def arithmetic(targets, returns):
    """Each independent block has a flat entry and drifted, paid proxy exit."""
    w, r = np.asarray(targets, float), np.asarray(returns, float)
    if w.ndim != 2 or r.shape != w.shape or not np.isfinite(w).all():
        raise ValueError("Invalid target/outcome dimensions")
    held = w != 0
    if not np.isfinite(r[held]).all() or np.any(r[held] <= -1):
        raise ValueError("Missing or invalid held return")
    gross = np.zeros_like(w)
    gross[held] = w[held] * r[held]  # no 0*NaN cash contamination
    carried = w + gross
    trades = np.vstack((w[0], w[1:] - carried[:-1], -carried[-1]))
    value = np.abs(trades)
    fee = FEE * value * (1 + np.sign(trades) * (SPREAD + SLIP))
    spread, slip = SPREAD * value, SLIP * value
    costs = fee + spread + slip
    np.testing.assert_allclose(trades.sum(0) + gross.sum(0), 0, atol=1e-14, rtol=0)
    np.testing.assert_allclose(fee.sum(), FEE * value.sum() - FEE * (SPREAD + SLIP) * gross.sum(), atol=1e-14, rtol=0)
    simple = np.vstack((w[0], np.diff(w, axis=0), -w[-1]))
    summary = summarize(w, gross, trades, fee, spread, slip, simple)
    daily = []
    for t in range(len(w)):
        terminal = costs[-1].sum() if t == len(w) - 1 else 0.
        daily.append({"gross_target": float(np.abs(w[t]).sum()), "net_target": float(w[t].sum()),
                      "gross_price_proxy": float(gross[t].sum()),
                      "drift_trade_turnover": float(value[t].sum()),
                      "fee": float(fee[t].sum()), "spread": float(spread[t].sum()),
                      "slippage": float(slip[t].sum()), "terminal_cost_at_label_end": float(terminal),
                      "fixed_cost_adjusted_price_proxy": float(gross[t].sum() - costs[t].sum() - terminal)})
    return summary, daily


def summarize(w, gross, trades, fee, spread, slip, simple):
    g, turnover, c = float(gross.sum()), float(np.abs(trades).sum()), float((fee + spread + slip).sum())
    reference_trade = np.abs(trades) * 10000
    return {"days": len(w), "gross_price_proxy": g, "fixed_cost_adjusted_price_proxy": g - c,
            "drift_trade_turnover": turnover, "descriptive_target_turnover": float(np.abs(simple).sum()),
            "fee": float(fee.sum()), "half_spread": float(spread.sum()), "slippage": float(slip.sum()),
            "fixed_cost_total": c, "entry_cost": float((fee[0] + spread[0] + slip[0]).sum()),
            "terminal_cost": float((fee[-1] + spread[-1] + slip[-1]).sum()),
            "break_even_nominal_per_side_bps": g / turnover * 10000 if turnover > 0 else None,
            "break_even_status": "SIGNED_PRICE_PROXY_ONLY" if turnover > 0 else "UNDEFINED_ZERO_TURNOVER",
            "cost_to_positive_gross_ratio": c / g if g > 0 else None,
            "gross_target_mean": float(np.abs(w).sum(1).mean()), "gross_target_max": float(np.abs(w).sum(1).max()),
            "abs_target_max": float(np.abs(w).max()), "asset_cap_violating_days": int((np.abs(w).max(1) > .3).sum()),
            "gross_cap_violating_days": int((np.abs(w).sum(1) > .6).sum()),
            "nonzero_targets_below_reference_10USDT": int(((np.abs(w) > 0) & (np.abs(w) * 10000 < 10)).sum()),
            "nonzero_trade_changes_below_reference_10USDT": int(((reference_trade > 0) & (reference_trade < 10)).sum()),
            "trade_change_count": int((reference_trade > 0).sum()),
            "per_asset": [{"asset_index": a, "mean_abs_target": float(np.abs(w[:, a]).mean()),
                           "min_signed_target": float(w[:, a].min()), "max_signed_target": float(w[:, a].max()),
                           "gross_price_proxy": float(gross[:, a].sum()),
                           "drift_trade_turnover": float(np.abs(trades[:, a]).sum()),
                           "fixed_cost": float((fee[:, a] + spread[:, a] + slip[:, a]).sum())} for a in range(w.shape[1])]}


def aggregate(parts):
    sums = ("days", "gross_price_proxy", "fixed_cost_adjusted_price_proxy", "drift_trade_turnover",
            "descriptive_target_turnover", "fee", "half_spread", "slippage", "fixed_cost_total",
            "entry_cost", "terminal_cost", "asset_cap_violating_days", "gross_cap_violating_days",
            "nonzero_targets_below_reference_10USDT", "nonzero_trade_changes_below_reference_10USDT", "trade_change_count")
    result = {k: sum(x[k] for x in parts) for k in sums}
    g, t = result["gross_price_proxy"], result["drift_trade_turnover"]
    result.update(break_even_nominal_per_side_bps=g / t * 10000 if t else None,
                  cost_to_positive_gross_ratio=result["fixed_cost_total"] / g if g > 0 else None,
                  gross_target_mean=sum(x["gross_target_mean"] * x["days"] for x in parts) / result["days"],
                  gross_target_max=max(x["gross_target_max"] for x in parts),
                  abs_target_max=max(x["abs_target_max"] for x in parts))
    return result


def evaluate(checkpoint):
    blocks, daily_rows = read_saved(checkpoint), []
    result = {"checkpoint": checkpoint, "positions_sha256": SOURCES[checkpoint][1],
              "symbols": SYMBOLS, "blocks": [], "aggregate": {}}
    for block in blocks:
        summaries = {}
        for j, policy in enumerate(POLICIES):
            summary, daily = arithmetic(block["targets"][:, :, j], block["returns"])
            raw_proxy = np.zeros_like(block["scaled"])
            valid = block["eligible"].astype(bool)
            raw_proxy[valid] = block["positions"][:, :, j][valid] * block["scaled"][valid] / 5
            np.testing.assert_allclose(summary["gross_price_proxy"], raw_proxy.sum(), rtol=0, atol=1e-14)
            summaries[policy] = summary
            for t, row in enumerate(daily):
                row.update(block=block["start"], available_us=utc_us(block["start"]) + t * DAY_US,
                           label_end_us=utc_us(block["start"]) + (t + 1) * DAY_US, policy=policy)
                daily_rows.append(row)
        result["blocks"].append({"start": block["start"], "end_exclusive": block["end"], "policies": summaries})
    for policy in POLICIES:
        result["aggregate"][policy] = aggregate([x["policies"][policy] for x in result["blocks"]])
    result["paired_increment"] = {}
    for suffix in ("seed2001", "seed2002", "seed2003", "ensemble"):
        a, b = (result["aggregate"][f"{arm}_{suffix}"] for arm in ARMS)
        result["paired_increment"][suffix] = {
            k: b[k] - a[k] for k in ("gross_price_proxy", "fixed_cost_adjusted_price_proxy",
                                     "drift_trade_turnover", "fixed_cost_total")}
    result.update(funding="NOT_MEASURED_NOT_KNOWN_ZERO", native_execution="NOT_RUN_NOT_BOUND",
                  shared_wallet_netProfit="UNKNOWN", net_APR="UNKNOWN", reference_capital_USDT=10000,
                  scope="ADDITIVE_STATIC_REFERENCE_PRICE_PROXY_BEFORE_UNMEASURED_FUNDING_NOT_WALLET_WEALTH")
    return result, daily_rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    start = time.monotonic()
    assert sha((EXPERIMENT / "PROTOCOL.json").read_bytes()) == PROTOCOL_SHA
    before, cost = preserved(), verify_cost()
    args.output.mkdir(parents=True, exist_ok=False)
    result, daily = evaluate(2048)
    primary = result["aggregate"]["trend_cpd_ensemble"]
    status = "NO_FIXED_COST_PROXY_MARGIN" if primary["fixed_cost_adjusted_price_proxy"] <= 0 else "FIXED_COST_PROXY_MARGIN_NATIVE_REVIEW_REQUIRED"
    result.update(status=status, protocol_sha256=PROTOCOL_SHA, cost=cost, source_commit=git("rev-parse", "HEAD").decode().strip(),
                  scientific_attempts_cumulative=3, fresh_fits_cumulative=12, updates_cumulative=13824,
                  new_training_updates=0, new_model_inferences=0, wallets=0)
    history, _ = evaluate(1024)
    history.update(role="SEPARATE_HISTORY_REFERENCE_ONLY_NOT_ADOPTION_SELECTION_OR_STOP", primary_checkpoint=2048)
    after = preserved()
    assert before == after
    result.update(preservation=after, elapsed_seconds=time.monotonic() - start)
    write_json(args.output / "RESULT.json", result)
    write_json(args.output / "HISTORY_REFERENCE.json", history)
    with (args.output / "DAILY.csv").open("x", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(daily[0]))
        writer.writeheader()
        writer.writerows(daily)
    total = sum(p.stat().st_size for p in args.output.rglob("*") if p.is_file())
    assert total <= 2_097_152
    print(json.dumps({"status": status, "2048_ensemble": {k: result["aggregate"][k] for k in ("trend_ensemble", "trend_cpd_ensemble")},
                      "paired": result["paired_increment"], "output_bytes": total, "seconds": result["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
