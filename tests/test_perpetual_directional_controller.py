"""One new synthetic scheduler case; existing strategy/account suites are reused."""
from copy import deepcopy
from decimal import Decimal as D
import json

import numpy as np
import polars as pl

from quant.execution_contract import ExecutionContractV2
from scripts.investment import perpetual_directional as controller

MINUTE = 60_000_000
START = 1_754_006_400_000_000


def test_new_perpetual_controller_chronology_capacity_risk_and_halt(monkeypatch, tmp_path):
    # The public hooks, covariance and wallet arithmetic already have accepted
    # independent tests. Here a fixed target stub isolates NEW scheduling only.
    def fixed_target(_bars, decisions, mode):
        assert mode == "SHORT_ONLY"
        rows = [dict(available_us=int(t), symbol=s, target_weight=-.3 if s == "BTCUSDT" else 0.)
                for t in decisions for s in controller.SYMBOLS]
        return pl.DataFrame(rows), {"scope": "PREDECLARED_SYNTHETIC_CONTROLLER_TARGET_STUB"}

    monkeypatch.setattr(controller.strategy, "fixed_targets", fixed_target)

    def window(n=12):
        times = START + np.arange(n, dtype=np.int64) * MINUTE
        market = {}
        for symbol in controller.SYMBOLS:
            opens = np.full(n, 100.)
            marked = np.full(n, 100.)
            if symbol == "BTCUSDT":
                opens[4:] = 108.  # Trade-open proxy is independent of mark110.
                marked[3:] = 110.
            market[symbol] = dict(open=opens, close=opens.copy(), mark=marked,
                                   quote_volume=np.full(n, 1_000_000.))
        daily = pl.DataFrame([dict(symbol=s, close_us=START, close=100.) for s in controller.SYMBOLS])
        events = [dict(symbol="BTCUSDT", event_us=START + offset, raw_rate=.001,
                       reported_interval_hours=8.)
                  for offset in (1000, 3 * MINUTE, 3 * MINUTE + 1000, 5 * MINUTE + 1000)]
        return dict(start=START, end=START + n * MINUTE, times=times, market=market,
                    daily=daily, events=events, input_proofs=[])

    base = window()
    case = controller.simulate(base, "SHORT_ONLY", controller.COSTS[0], controller.UNITS[0])
    summary, trades, funding = case["summary"], case["trades"], case["funding"]
    assert summary["completion"] == "COMPLETE_CONDITIONAL_ACCOUNT"
    assert summary["completed_minutes"] == 12 and case["minute"].height == 12
    assert summary["terminal_cash_realized"] and summary["terminal_marked_notional"] == 0
    assert funding[0]["owned"] is False and funding[0]["signed_funding_USDT"] == 0
    assert funding[0]["status"] == "NO_POSITION_NO_PAST_MARK"
    sells = [row for row in trades if row["side"] == "SELL"]
    assert [row["event_us"] for row in sells] == [START + i * MINUTE + 1 for i in (1, 2, 3)]
    assert [row["quantity"] for row in sells] == [10., 10., 9.7]
    assert sells[0]["quantity_after"] == -10. and sells[2]["quantity_after"] == -29.7
    # The exact boundary coupon precedes the third fill; +1ms belongs to the
    # newly filled inventory. No rounding to an ideal eight-hour time occurs.
    exact, jitter = funding[1:3]
    assert exact["event_us"] == START + 3 * MINUTE and exact["quantity"] == -20.
    assert exact["signed_funding_USDT"] == 2.
    assert jitter["event_us"] == START + 3 * MINUTE + 1000 and jitter["quantity"] == -29.7
    assert jitter["signed_funding_USDT"] == 2.97
    assert exact["mark_close_us"] < exact["event_us"] and jitter["mark_close_us"] < jitter["event_us"]
    assert case["breaches"] and case["breaches"][0]["signal_us"] == START + 4 * MINUTE
    drift_fills = [row for row in trades if row["signal_us"] == START + 4 * MINUTE]
    assert len(drift_fills) == 1 and drift_fills[0]["side"] == "BUY"
    assert drift_fills[0]["leg"] == "CLOSE" and drift_fills[0]["mark_price"] == 110.
    assert drift_fills[0]["mid_price"] == 108.
    assert drift_fills[0]["event_us"] == START + 5 * MINUTE + 1
    assert funding[3]["quantity"] == drift_fills[0]["quantity_after"]
    for row in trades:
        assert row["event_us"] >= ExecutionContractV2().earliest_execution_us(row["signal_us"]) + 1
        index = (row["event_us"] - START - 1) // MINUTE
        assert index > 0
        symbol = row["symbol"]
        mid = D(str(base["market"][symbol]["open"][index]))
        assert D(row["decimal_strings"]["execution_mid_price"]) == mid
        # Capacity comes from the previous completed minute, not the fill bar.
        quantity = D(row["decimal_strings"]["quantity"])
        assert quantity * mid <= D(str(base["market"][symbol]["quote_volume"][index - 1])) * D(".001")
        expected_price = mid * (D("1.0008") if row["side"] == "BUY" else D(".9992"))
        assert D(row["decimal_strings"]["fill_price"]) == expected_price
    terminal = [row for row in trades if row["signal_us"] == base["end"] - 6 * MINUTE]
    assert terminal and all(row["side"] == "BUY" and row["leg"] == "CLOSE" for row in terminal)

    changed = deepcopy(base)
    for symbol in controller.SYMBOLS:
        changed["market"][symbol]["open"][6:] *= 1.005
        changed["market"][symbol]["mark"][6:] *= 1.005
        changed["market"][symbol]["quote_volume"][6:] *= 1.02
    future = controller.simulate(changed, "SHORT_ONLY", controller.COSTS[0], controller.UNITS[0])
    cut = START + 6 * MINUTE
    assert case["minute"].filter(pl.col("close_us") <= cut).equals(
        future["minute"].filter(pl.col("close_us") <= cut))
    assert [row for row in case["trades"] if row["event_us"] < cut] == [
        row for row in future["trades"] if row["event_us"] < cut]

    # No liquidity cannot be repaired with a free risk/terminal fill. Five
    # attempts preserve actual q and explicitly end an incomplete account.
    dry = window(16)
    dry["market"]["BTCUSDT"]["quote_volume"][4:] = 0.
    risk_stop = controller.simulate(dry, "SHORT_ONLY", controller.COSTS[0], controller.UNITS[0])
    assert risk_stop["summary"]["completion"] == "NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION"
    assert risk_stop["summary"]["stop_us"] == START + 9 * MINUTE + 1
    assert risk_stop["summary"]["positions"]["BTCUSDT"]["quantity"] == -29.7
    assert len(risk_stop["trades"]) == 3

    # A stop after this minute's mark/fill occurs before its new snapshot is
    # written. Residual MTM must use the current account, not last-row q=0.
    gap = window()
    gap["market"]["BTCUSDT"]["mark"][1:] = 201.
    halted = controller.simulate(gap, "SHORT_ONLY", controller.COSTS[0], controller.UNITS[0])
    assert halted["summary"]["completion"] == "NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED"
    assert halted["summary"]["account_status"] == "BANKRUPT_HALT"
    assert halted["minute"].height == 1 and halted["minute"]["BTCUSDT_quantity"][-1] == 0.
    assert halted["summary"]["positions"]["BTCUSDT"]["quantity"] == -10.
    assert halted["summary"]["terminal_signed_marked_notional"]["BTCUSDT"] == -2010.
    saved_halt = controller.save_case(halted, tmp_path / "halted")
    attribution = saved_halt["summary"]["long_short_marked_contribution"]
    assert saved_halt["summary"]["daily_metrics"] is None
    assert abs(sum(row["net_contribution"] for row in attribution.values()) - saved_halt["summary"]["net_PnL"]) <= 1e-7
    evidence = {"scope": "NEW_CONTROLLER_SYNTHETIC_SCHEDULING_NOT_PUBLIC_ALPHA_OR_NATIVE_EXECUTION",
        "base": {key: case[key] for key in ("summary", "trades", "funding", "breaches", "rejections")},
        "dry_risk_stop": {key: risk_stop[key] for key in ("summary", "trades", "funding", "rejections")},
        "halted_output": saved_halt, "future_prefix_unchanged_until_us": cut}
    (tmp_path / "controller_evidence.json").write_text(json.dumps(evidence, indent=2, sort_keys=True), encoding="utf-8")
