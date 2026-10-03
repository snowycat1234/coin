"""One new synthetic signed-public-target -> fill -> funding -> wallet chain."""
from decimal import Decimal as D, ROUND_DOWN, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import polars as pl
import pytest

from quant.perpetual_account import USDTLinearPerpetualAccount
from scripts.investment import public_sma_perpetual as strategy

ROOT = Path(__file__).resolve().parents[1]
SPOT_SHA = "ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a"
REFERENCE_SHA = "3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a"
MINUTE = 60_000_000
TOL = D("1e-24")


def test_public_four_direction_perpetual_chain(tmp_path):
    # The independent reference has no producer import or market IO. Exact
    # archived bytes make this reference available in a fresh checkout.
    reference_path = ROOT / "docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py"
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest() == REFERENCE_SHA
    assert hashlib.sha256((ROOT / "src/quant/backtest.py").read_bytes()).hexdigest() == SPOT_SHA
    module_spec = importlib.util.spec_from_file_location("perpetual_chain_hand_reference", reference_path)
    reference = importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name] = reference
    module_spec.loader.exec_module(reference)
    reference.hand_reference_checks()
    with pytest.raises(ValueError, match="mixed"):
        USDTLinearPerpetualAccount(market_type="SPOT")

    # Last 200 days genuinely permit a short at the first scoring decision.
    # The next small upward move exits that short through the original hook.
    # ETH is exactly equal throughout and never has a position in any mode.
    day = strategy.DAY_US
    first = 1_735_689_600_000_000
    closes = first + np.arange(1, 202, dtype=np.int64) * day
    btc_prices = np.r_[np.full(150, 100.01), np.full(50, 100.), 100.75]
    rows = []
    for symbol in ("BTCUSDT", "ETHUSDT"):
        prices = btc_prices if symbol == "BTCUSDT" else np.full(201, 100.)
        for close, price in zip(closes, prices, strict=True):
            rows.append(dict(symbol=symbol, open_us=int(close - day), close_us=int(close),
                available_us=int(close), open=float(price), high=float(price + .01),
                low=float(price - .01), close=float(price), volume=1000.))
    bars = pl.DataFrame(rows)
    decisions = closes[199:201]
    output = {"scope": "SYNTHETIC_PUBLIC_SIGNED_TARGET_PERPETUAL_QUOTE_ACCOUNTING_NOT_MARKET_RESULT",
              "spot_source_sha256": SPOT_SHA, "independent_reference_sha256": REFERENCE_SHA,
              "initial_capital_each_counterfactual_USDT": 10000,
              "shared_live_capital_or_mixed_product_claimed": False,
              "cap_buffer": .99, "candidate": "NO_QUALIFIED_CANDIDATE", "modes": {}}
    for mode in strategy.MODES:
        targets, target_receipt = strategy.fixed_targets(bars, decisions, mode)
        assert targets.filter(pl.col("symbol") == "ETHUSDT")["target_weight"].abs().sum() == 0
        btc = targets.filter(pl.col("symbol") == "BTCUSDT")
        if mode in ("SHORT_ONLY", "LONG_SHORT"):
            assert btc["target_weight"][0] < 0 and btc["target_weight"][1] == 0
        elif mode == "LONG_ONLY":
            assert btc["target_weight"][0] == 0 and btc["target_weight"][1] > 0
        else:
            assert btc["target_weight"].abs().sum() == 0
        account = USDTLinearPerpetualAccount()
        hand = reference.HandLedger(D(10000))
        stage_NAV = []
        max_errors = {"NAV_USDT": D(0), "wallet_USDT": D(0), "entry_price": D(0),
                      "fees_USDT": D(0), "funding_USDT": D(0), "realized_USDT": D(0)}

        def check(stage, mark):
            mark = D(str(mark))
            with localcontext() as context:
                context.prec = 50
                differences = {
                    "NAV_USDT": abs(account.nav() - hand.equity(mark)),
                    "wallet_USDT": abs(account.free_cash + sum((p.isolated_balance for p in account.positions.values()), D(0)) - hand.wallet),
                    "entry_price": abs(account.positions["BTCUSDT"].entry_price - hand.entry_fill),
                    "fees_USDT": abs(account.fees - hand.fees),
                    "funding_USDT": abs(account.funding_cash - hand.funding_cash),
                    "realized_USDT": abs(account.realized_PnL - hand.realized),
                }
                assert account.positions["BTCUSDT"].quantity == hand.quantity
                assert account.positions["ETHUSDT"].quantity == 0
                for key, difference in differences.items():
                    max_errors[key] = max(max_errors[key], difference)
                    assert difference <= TOL
                assert abs(hand.bridge("10000", mark)) <= TOL
                stage_NAV.append(dict(stage=stage, account_NAV=str(account.nav()),
                    independent_NAV=str(hand.equity(mark)), free_wallet=str(account.free_cash),
                    isolated_margin=str(account.positions["BTCUSDT"].isolated_balance),
                    signed_quantity=str(hand.quantity), mark=str(mark)))

        def apply_order(delta, mid, execution_us, signal_us, identity, reduce_only=False):
            if delta == 0:
                return
            side = "BUY" if delta > 0 else "SELL"
            requested = abs(delta)
            actual = account.execute_fill("BTCUSDT", side, requested, execution_us,
                signal_us, identity, execution_mid_price=mid,
                quote_available_us=execution_us, reduce_only=reduce_only)
            assert actual["status"] == "FILLED"
            # Independent fixed directional fill price and quote fee. The hand
            # wallet never receives short-sale notional or pays long principal.
            with localcontext() as context:
                context.prec = 50
                direction = D(1) if side == "BUY" else D(-1)
                expected_fill = D(str(mid)) * (1 + direction * D("0.0008"))
                expected_fee = requested * expected_fill * D("0.00055")
                assert len(actual["fills"]) == 1
                row = actual["fills"][0]
                assert D(row["decimal_strings"]["position_delta"]) == delta
                assert D(row["decimal_strings"]["fill_price"]) == expected_fill
                assert D(row["decimal_strings"]["fee_amount"]) == expected_fee
                assert row["fee_asset"] == "USDT"
                hand.fill(delta, expected_fill, ".00055")
            check(identity, mid)

        for index, decision in enumerate(decisions):
            decision = int(decision)
            mid = D("100") if index == 0 else D("100.75")
            account.update_marks(decision, {symbol: {"price": str(mid) if symbol == "BTCUSDT" else "100",
                "close_us": decision, "available_us": decision} for symbol in ("BTCUSDT", "ETHUSDT")})
            check(f"decision-{index}", mid)
            weight = D(str(btc["target_weight"][index])) * D("0.99")
            with localcontext() as context:
                context.prec = 50
                raw_target = weight * hand.equity(mid) / mid
                target = (abs(raw_target) / D("1e-8")).to_integral_value(rounding=ROUND_DOWN) * D("1e-8")
                if raw_target < 0:
                    target = -target
                delta = target - hand.quantity
            apply_order(delta, mid, decision + MINUTE + 1, decision,
                        f"{mode}-decision-{index}", reduce_only=target == 0)
            if index == 0:
                for event_offset, rate in ((4 * 60 * MINUTE, D(".001")),
                                           (8 * 60 * MINUTE, D("-.0005"))):
                    event_us = decision + event_offset
                    coupon = account.apply_funding("BTCUSDT", f"{mode}-funding-{event_offset}",
                                                   event_us, rate, event_us)
                    expected = hand.funding("100", rate, rate_unit="EXPLICIT_SYNTHETIC_FRACTION",
                                            signed_quantity_before_event=hand.quantity)
                    assert D(coupon["decimal_strings"]["signed_funding_USDT"]) == expected
                    assert coupon["mark_close_us"] < event_us
                    check(f"funding-{event_offset}", "100")
        # An explicit common terminal close applies to all four counterfactuals.
        # The LONG_ONLY account may first enter on the newly bullish second day;
        # closing it is terminal accounting, not a claimed SMA exit signal.
        terminal_us = int(decisions[-1]) + 2 * MINUTE
        account.update_marks(terminal_us, {symbol: {"price": "100.75" if symbol == "BTCUSDT" else "100",
            "close_us": terminal_us, "available_us": terminal_us} for symbol in ("BTCUSDT", "ETHUSDT")})
        apply_order(-hand.quantity, D("100.75"), terminal_us + 1,
                    int(decisions[-1]) + MINUTE, f"{mode}-terminal", reduce_only=True)
        check("terminal-flat", "100.75")
        assert hand.quantity == 0 and account.positions["BTCUSDT"].isolated_balance == 0
        if mode in ("SHORT_ONLY", "LONG_SHORT"):
            assert account.trades[0]["side"] == "SELL" and account.trades[0]["quantity_after"] < 0
            assert account.trades[-1]["side"] == "BUY"
            assert account.funding[0]["signed_funding_USDT"] > 0
            assert account.funding[1]["signed_funding_USDT"] < 0
        if mode == "CASH":
            assert account.trades == [] and account.nav() == 10000
        output["modes"][mode] = dict(targets=targets.to_dicts(), target_receipt=target_receipt,
            summary=account.summary(), trades=account.trades, funding=account.funding,
            snapshot=account.snapshot(), NAV_stages=stage_NAV,
            independent_reference_wallet=str(hand.wallet),
            independent_reference_fees=str(hand.fees),
            independent_reference_funding=str(hand.funding_cash),
            maximum_bridge_errors={key: str(value) for key, value in max_errors.items()})
    assert output["modes"]["SHORT_ONLY"]["summary"]["net_PnL"] == output["modes"]["LONG_SHORT"]["summary"]["net_PnL"]
    assert hashlib.sha256((ROOT / "src/quant/backtest.py").read_bytes()).hexdigest() == SPOT_SHA
    (tmp_path / "chain_evidence.json").write_text(json.dumps(output, ensure_ascii=False,
        sort_keys=True, indent=2), encoding="utf-8")
