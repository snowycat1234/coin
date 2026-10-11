"""Read-only economic reconstruction; does not instantiate accounts or refit."""
import argparse
from decimal import Decimal as D, localcontext
import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl

SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
MINUTE = 60_000_000
FEE, MMR = D(".00055"), D(".005")


def close(a, b):
    assert abs(a-b) <= D("1e-24"), (str(a), str(b))


def fold(trades, funds, until, inclusive=False):
    positions = {s: {"q": D(0), "e": D(0), "c": D(0)} for s in SYMBOLS}
    free, max_margin = D(10000), D(0)
    events = [(r["event_us"], 1, r) for r in trades] + [(r["event_us"], 0, r) for r in funds]
    for t, kind, r in sorted(events, key=lambda x: (x[0], x[1])):
        if t > until or (t == until and not inclusive):
            break
        p = positions[r["symbol"]]
        if "decimal_strings" not in r:
            assert not kind and not r["owned"] and r["signed_funding_USDT"] == 0
            continue  # Explicit no-position receipt, not a missing funded value.
        x = r["decimal_strings"]
        if not kind:
            amount = D(x["signed_funding_USDT"])
            assert amount >= -free, "Saved path requires explicit collateral funding debit expansion"
            free += amount
            continue
        close(p["q"], D(x["quantity_before"]))
        close(p["e"], D(x["entry_price_before"]))
        size, fill = abs(D(x["position_delta"])), D(x["fill_price"])
        if r.get("liquidation_takeover"):
            close(D(x["takeover_margin_loss"]), p["c"])
            close(D(x["realized_PnL"]), -p["c"])
            close(D(x["free_cash_delta"]), D(0))
        elif r["leg"] == "OPEN":
            close(D(x["margin_allocated"]), size*fill)
            close(D(x["entry_price_after"]), (abs(p["q"])*p["e"]+size*fill)/(abs(p["q"])+size))
        else:
            close(D(x["margin_released"]), p["c"]*size/abs(p["q"]))
            close(D(x["realized_PnL"]), (D(1) if p["q"]>0 else D(-1))*size*(fill-p["e"]))
        p["q"] += D(x["position_delta"])
        p["c"] += D(x["isolated_balance_delta"])
        p["e"] = D(x["entry_price_after"])
        free += D(x["free_cash_delta"])
        close(p["q"], D(x["quantity_after"]))
        assert free >= 0 and p["c"] >= -D("1e-24")
        max_margin = max(max_margin, sum((v["c"] for v in positions.values()), D(0)))
    return positions, free, max_margin


def run(state, output):
    hashes, rows, case_checks = {}, [], []
    tape_path = state / "minute-source/WINDOW_MARKET.npz"
    hashes[str(tape_path.relative_to(state))] = hashlib.sha256(tape_path.read_bytes()).hexdigest()
    tape = np.load(tape_path, allow_pickle=False)
    marks = {int(t)+MINUTE: D(str(float(p))) for t,p in zip(tape["times"], tape["DOGEUSDT_mark"])}
    with localcontext() as ctx:
        ctx.prec = 50
        for directory in sorted((state / "economics").iterdir()):
            if not directory.is_dir():
                continue
            data = {}
            for name in ("trades.json", "funding.json", "liquidations.json", "summary.json"):
                raw = (directory/name).read_bytes()
                hashes[str((directory/name).relative_to(state))] = hashlib.sha256(raw).hexdigest()
                data[name] = json.loads(raw)
            trades, funds, summary = data["trades.json"], data["funding.json"], data["summary.json"]
            minute = pl.read_parquet(directory/"minute_nav_inventory.parquet", columns=["close_us", "free_cash", "DOGEUSDT_quantity"])
            hashes[str((directory/"minute_nav_inventory.parquet").relative_to(state))] = hashlib.sha256((directory/"minute_nav_inventory.parquet").read_bytes()).hexdigest()
            final, free, max_margin = fold(trades, funds, int(minute["close_us"].max())+1, True)
            close(free, D(summary["decimal_strings"]["free_cash"]))
            assert all(abs(p["q"])+abs(p["c"]) <= D("1e-24") for p in final.values())
            assert D(summary["decimal_strings"]["unpaid_liability"]) == 0
            for w in data["liquidations.json"]:
                t = w["event_us"]
                before, free_before, _ = fold(trades, funds, t)
                after, free_after, _ = fold(trades, funds, t, True)
                p = before["DOGEUSDT"]
                q, e, c = abs(p["q"]), p["e"], p["c"]
                assert p["q"] < 0
                close(c, q*e)
                close(q, abs(D(w["quantity"])))
                close(c, D(w["isolated_margin_lost"]))
                close(e, D(w["entry_price"]))
                close(marks[t], D(w["mark_price"]))
                extra = c-q*e
                modern = (2*e*q+extra/(1+FEE))/(q*(1+MMR))
                old = e*(2-MMR)+extra/q
                assert marks[t-MINUTE] < modern <= marks[t]
                assert not any(r["symbol"] == "DOGEUSDT" and abs(r["event_us"]-t) <= 5*MINUTE for r in funds)
                assert not any(t-MINUTE < r["event_us"] <= t and not r.get("liquidation_takeover") for r in trades)
                assert not any(t-MINUTE < r["event_us"] <= t for r in funds)
                close(free_before, free_after)
                assert after["DOGEUSDT"]["q"] == 0
                next_fill = next(r for r in trades if r["symbol"] == "DOGEUSDT" and r["event_us"] > t)
                flat = minute.filter((pl.col("close_us") >= t) & (pl.col("close_us") < next_fill["event_us"]))
                assert flat["DOGEUSDT_quantity"].eq(0).all() and next_fill["signal_us"] > t
                assert next_fill["leg"] == "OPEN" and D(next_fill["decimal_strings"]["fee_amount"]) > 0
                equity = c-q*(marks[t]-e)
                close(D(w["bankruptcy_price"]), e+c/q)
                rows.append(dict(case=directory.name, event_us=t, phase=w["phase"], q=str(q), entry=str(e),
                    margin=str(c), mark=str(marks[t]), previous_mark=str(marks[t-MINUTE]),
                    modern_mark_MM_LP=str(modern), prior_entry_MM_LP=str(old),
                    trigger_under_prior_rule_at_observed_minute=bool(marks[t]>=old),
                    bankruptcy=str(e+c/q), pre_takeover_equity=str(equity),
                    takeover_NAV_delta_at_same_mark=str(-equity), free_cash_unchanged=str(free_before),
                    expected_fee_to_close_reserve_not_PnL_adjustment=str(2*q*e*FEE),
                    flat_minutes=int(flat.height), new_signal_us=next_fill["signal_us"],
                    reentry_us=next_fill["event_us"], reentry_entry=next_fill["decimal_strings"]["entry_price_after"],
                    reentry_fee=next_fill["decimal_strings"]["fee_amount"]))
            case_checks.append(dict(case=directory.name, unpaid_liability=0, minimum_observed_free_cash=float(minute["free_cash"].min()),
                conservative_all_leg_close_reserve_upper_bound=str(2*max_margin*FEE),
                final_cash_reconstruction_error=str(free-D(summary["decimal_strings"]["free_cash"]))))
    result = dict(status="PASS_SAVED_CONDITIONAL_ECONOMIC_SEMANTICS", scientific_fits=0, historical_wallet_reruns=0,
        old_financial_source="d82cfca41a76f12aea60ea2608a5c5d26670d7c55394cb07619b69fdffd2619a",
        inputs=hashes, witnesses=rows, cases=case_checks,
        prior_rule_trigger_disagreement_count=sum(not r["trigger_under_prior_rule_at_observed_minute"] for r in rows),
        scope="Modern mark-based MM rule applied to 2021 Binance market using assumed Bybit costs/tier. Not native 2021 liquidation validation. No post-takeover counterfactual.",
        close_fee_scope="Fee reserve omitted from allocation; reserve is a cash partition, not an extra paid fee or local corrected PnL. Full-path implementation required before claiming native equivalence.",
        sources=["https://www.bybit.com/en/help-center/article/Understanding-the-Adjustment-and-Impact-of-the-New-Margin-Calculation",
                 "https://www.bybit.com/en/help-center/article/Order-Cost-USDT-Contract",
                 "https://www.bybit.com/en/help-center/article/UTA-Trading-Rules-Liquidation-Process"])
    output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n")
    print(json.dumps({"events":len(rows),"prior_rule_disagreements":result["prior_rule_trigger_disagreement_count"],"wallet_reruns":0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.state, args.output)
