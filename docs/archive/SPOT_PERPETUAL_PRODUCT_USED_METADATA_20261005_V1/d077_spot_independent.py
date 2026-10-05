"""Independent scalar/Decimal audit of saved Spot wallets; no producer imports."""
from __future__ import annotations

import argparse
from collections import defaultdict
from decimal import Decimal, localcontext
import hashlib
import json
import math
from pathlib import Path
import resource
import time

import polars as pl
import numpy as np


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1_048_576), b""):
            digest.update(block)
    return digest.hexdigest()


def dec(value):
    result = Decimal(str(value))
    if not result.is_finite():
        raise AssertionError("nonfinite monetary input")
    return result


def audit_case(case):
    cfg, summary = case["config"], case["summary"]
    if cfg["fee_settlement"] != "RECEIVED_ASSET":
        raise AssertionError("received-asset wallet required")
    artifact = case["artifacts"]["trades"]
    if sha(artifact["path"]) != artifact["sha256"]:
        raise AssertionError("trade source changed")
    frame = pl.read_parquet(artifact["path"])
    if artifact.get("rows", len(frame)) != len(frame):
        raise AssertionError("trade count changed")
    symbols = case.get("symbols", list(summary["open_positions"]))
    if len(set(symbols)) != len(symbols) or not symbols:
        raise AssertionError("ambiguous portfolio identity")
    cash, start_cash = dec(cfg["initial_cash"]), dec(cfg["initial_cash"])
    rate = dec(cfg["fee_bps"]) * dec(cfg["fee_multiplier"]) / 10_000
    exec_rate = (dec(cfg["half_spread_bps"])
                 + dec(cfg["slippage_bps"]) * dec(cfg["slippage_multiplier"])) / 10_000
    inventory = {s: Decimal(0) for s in symbols}
    snapshots = []
    fees = execution_costs = notional_sum = Decimal(0)
    checks = defaultdict(int)
    errors = defaultdict(lambda: Decimal(0))

    def equal(name, expected, actual, tolerance=Decimal("0.000002")):
        gap = abs(expected - dec(actual))
        errors[name] = max(errors[name], gap)
        checks[name] += 1
        if gap > tolerance:
            raise AssertionError(f"{case['id']} {name}: {gap} > {tolerance}")

    previous_clock = None
    for row in frame.iter_rows(named=True):
        s, side = row["symbol"], row["side"]
        if s not in inventory or side not in ("buy", "sell") or not s.endswith("USDT"):
            raise AssertionError("invalid product or side")
        clock = row["execution_us"]
        if (previous_clock is not None and clock < previous_clock
                or clock <= row["signal_us"]
                or row["capacity_open_us"] >= clock):
            raise AssertionError("noncausal or reordered trades")
        previous_clock = clock
        q, fill, mid = map(dec, (row["gross_quantity"], row["fill_price"], row["mid_price"]))
        if min(q, fill, mid) <= 0:
            raise AssertionError("nonpositive fill")
        buy = side == "buy"
        notional = q * fill
        direction = 1 if buy else -1
        equal("fill_direction", mid * (1 + direction * exec_rate), fill)
        equal("gross_quantity", q, row["quantity"], Decimal("0.0000000001"))
        equal("notional", notional, row["notional"])
        if notional > dec(row["capacity"]) + Decimal("0.000002"):
            raise AssertionError("exceeded past-minute capacity")
        step = cfg["lot_step_by_symbol"].get(s)
        if step is not None:
            units = q / dec(step)
            if abs(units - units.to_integral_value()) > Decimal("0.000001"):
                raise AssertionError("gross quantity not on lot step")
        if notional + Decimal("0.000002") < dec(cfg["min_notional"]):
            raise AssertionError("below minimum notional fill")
        if buy:
            fee_amount = q * rate
            fee_asset = s[:-4]
            fee_value = fee_amount * mid
            base_delta, cash_delta = q - fee_amount, -notional
        else:
            if q > inventory[s] + Decimal("0.0000000001"):
                raise AssertionError("borrowed or oversold Spot inventory")
            fee_amount = notional * rate
            fee_asset = "USDT"
            fee_value = fee_amount
            base_delta, cash_delta = -q, notional - fee_amount
        if row["fee_asset"] != fee_asset:
            raise AssertionError("wrong received fee asset")
        equal("fee_amount", fee_amount, row["fee_amount"])
        equal("fee_value", fee_value, row["fee_USDT_mid"])
        equal("fee_total_field", fee_value, row["fee"])
        equal("base_delta", base_delta, row["position_delta"], Decimal("0.0000000001"))
        equal("cash_delta", cash_delta, row["cash_delta"])
        impact = q * abs(fill - mid)
        equal("execution_cost", impact, row["execution_cost"])
        inventory[s] += base_delta
        cash += cash_delta
        if min(cash, inventory[s]) < Decimal("-0.00000001"):
            raise AssertionError("negative shared cash or inventory")
        equal("shared_cash_after", cash, row["cash_after"])
        snapshots.append({"clock": clock, "cash": float(cash),
                          **{s: float(inventory[s]) for s in symbols}})
        fees += fee_value
        execution_costs += impact
        notional_sum += notional
    for s in symbols:
        equal("terminal_inventory", inventory[s], summary["open_positions"][s], Decimal("0.000000001"))
    terminal_marks = case["terminal_marks"]
    nav = cash
    for s in symbols:
        mark = terminal_marks[s]
        price = mark["price"] if isinstance(mark, dict) else mark
        nav += inventory[s] * dec(price)
    equal("terminal_nav", nav, summary["final_nav"], Decimal("0.00001"))
    equal("summary_fees", fees, summary["fees"])
    equal("summary_execution_costs", execution_costs, summary["execution_costs"])
    daily_art = case["artifacts"]["daily_nav"]
    if sha(daily_art["path"]) != daily_art["sha256"]:
        raise AssertionError("daily ledger source changed")
    daily = pl.read_parquet(daily_art["path"])
    equal("daily_final_cash", cash, daily["cash"][-1])
    equal("daily_final_nav", nav, daily["nav"][-1], Decimal("0.00001"))
    equal("daily_fee_sum", fees, sum(map(dec, daily["fees"])))
    equal("daily_execution_sum", execution_costs, sum(map(dec, daily["execution_costs"])))
    # Descriptive daily changes start from full capital; no reset or stitched wallets.
    previous = start_cash
    log_sum = 0.0
    for daily_row in daily.iter_rows(named=True):
        current = dec(daily_row["nav"])
        equal("daily_return_bridge", current / previous - 1, daily_row["return"], Decimal("0.000000001"))
        log_sum += math.log(float(current / previous))
        previous = current
    if abs(log_sum - math.log(float(nav / start_cash))) > 1e-10:
        raise AssertionError("daily log bridge failed")
    minute_risk = None
    minute_art = case["artifacts"].get("minute_nav_inventory",
        case["artifacts"].get("minute_nav_inventory.parquet"))
    if minute_art is not None:
        if sha(minute_art["path"]) != minute_art["sha256"]:
            raise AssertionError("minute ledger changed")
        minute = pl.read_parquet(minute_art["path"])
        clocks = minute["close_us"].to_numpy()
        fill_clocks = np.array([r["clock"] for r in snapshots], dtype=np.int64)
        ix = np.searchsorted(fill_clocks, clocks, side="right")
        cash_array = np.array([float(start_cash)] + [r["cash"] for r in snapshots])[ix]
        nav_array = cash_array.copy()
        notionals = []
        def arrays_equal(name, expected, actual, tolerance=1e-5):
            gap = float(np.max(np.abs(expected - actual))) if len(actual) else 0.0
            errors[name] = dec(gap)
            checks[name] += len(actual)
            if gap > tolerance:
                raise AssertionError(f"minute {name} mismatch {gap}")
        arrays_equal("minute_cash", cash_array, minute["cash"].to_numpy())
        for s in symbols:
            q_array = np.array([0.0] + [r[s] for r in snapshots])[ix]
            arrays_equal("minute_inventory_" + s, q_array,
                         minute["quantity_" + s].to_numpy(), 1e-8)
            mark_array = minute["mark_" + s].to_numpy()
            if not np.all(np.isfinite(mark_array)) or np.any(mark_array <= 0):
                raise AssertionError("invalid saved minute mark")
            value = q_array * mark_array
            nav_array += value
            notionals.append(value)
        arrays_equal("minute_nav", nav_array, minute["nav"].to_numpy())
        if np.any(nav_array <= 0):
            raise AssertionError("nonpositive minute NAV")
        notionals = np.vstack(notionals)
        gross = np.sum(np.abs(notionals), axis=0) / nav_array
        net = np.sum(notionals, axis=0) / nav_array
        arrays_equal("minute_gross", gross, minute["gross_weight"].to_numpy(), 1e-8)
        arrays_equal("minute_net", net, minute["net_weight"].to_numpy(), 1e-8)
        if "day_end_us" in daily.columns:
            day_clocks = daily["day_end_us"].to_numpy()
            day_ix = np.searchsorted(clocks, day_clocks)
            if (np.any(day_ix >= len(clocks))
                    or not np.array_equal(clocks[day_ix], day_clocks)):
                raise AssertionError("daily endpoint absent from minute path")
            arrays_equal("daily_all_nav_from_inventory", nav_array[day_ix], daily["nav"].to_numpy())
            arrays_equal("daily_all_cash_from_fills", cash_array[day_ix], daily["cash"].to_numpy())
            for s in symbols:
                if "quantity_" + s in daily.columns:
                    arrays_equal("daily_inventory_" + s,
                        minute["quantity_" + s].to_numpy()[day_ix],
                        daily["quantity_" + s].to_numpy(), 1e-8)
        absolute_assets = np.abs(notionals) / nav_array
        # Price drift beyond caps is retained as diagnostic, never silently removed.
        minute_risk = {"rows": len(minute), "max_gross": float(np.max(gross)),
            "max_abs_asset": float(np.max(absolute_assets)),
            "gross_above_cap_rows": int(np.count_nonzero(gross > float(cfg["max_gross"]) + 1e-9)),
            "any_asset_above_cap_rows": int(np.count_nonzero(np.any(
                absolute_assets > float(cfg["max_weight"]) + 1e-9, axis=0))),
            "risk_scope": "Full saved close mark path independently reconstructed; drift breach is diagnostic, not waived."}
    return {"id": case["id"], "status": "PASS_INDEPENDENT_SCALAR_DECIMAL_SPOT_RECEIVED_ASSET_CASH_AND_FINAL_NAV",
        "trades": len(frame), "days": len(daily), "checks": dict(checks),
        "max_absolute_errors": {k: str(v) for k, v in errors.items()},
        "reconstructed_terminal_cash": str(cash),
        "reconstructed_terminal_inventory": {k: str(v) for k, v in inventory.items()},
        "reconstructed_terminal_nav": str(nav), "fees_USDT_mid": str(fees),
        "execution_costs": str(execution_costs), "gross_filled_notional": str(notional_sum),
        "full_saved_minute_risk": minute_risk,
        "scope": "No producer account imports; independent fee/inventory/cash/final NAV. Intermediate mark prices and complete risk path require runner market audit; terminal marks are caller-pinned input, not independent source verification."}


def main():
    args = argparse.ArgumentParser()
    args.add_argument("--input", required=True)
    args.add_argument("--output", required=True)
    ns = args.parse_args()
    start = time.perf_counter()
    payload = json.loads(Path(ns.input).read_text(encoding="utf8"))
    with localcontext() as context:
        context.prec = 60
        rows = [audit_case(case) for case in payload["cases"]]
    result = {"status": "PASS_INDEPENDENT_SAVED_SPOT_WALLETS_NOT_NATIVE_OR_ALPHA_CERTIFICATION",
        "input_path": ns.input, "input_sha256": sha(ns.input), "cases": rows,
        "wall_seconds": time.perf_counter() - start,
        "peak_RSS_bytes": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024,
        "producer_imports": False, "market_replay": False, "orders_sent": False,
        "scope": "Decimal independent monetary audit. No Bybit native price/filters, execution quality or investment qualification certification."}
    destination = Path(ns.output)
    if not destination.resolve().is_relative_to(Path("/home/xflops/coin-state")):
        raise ValueError("output must be under D-hosted STATE")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    print(json.dumps({"status": result["status"], "cases": len(rows),
                      "output": str(destination), "wall_seconds": result["wall_seconds"]}))


if __name__ == "__main__":
    main()
