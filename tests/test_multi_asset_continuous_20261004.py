"""One real wallet across a month boundary; synthetic data, no market replay."""
from decimal import Decimal as D
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import polars as pl

from scripts.investment import perpetual_directional as engine
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount

MINUTE, DAY = 60_000_000, 86_400_000_000
START = 1730332800000000  # 2024-10-31 UTC
BOUNDARY = START + DAY  # 2024-11-01 UTC
END = BOUNDARY + 12 * MINUTE
SYMBOLS = ('ETHUSDT', 'BTCUSDT')
REFERENCE_SHA = '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'


def amount(row, name):
    return D(row.get('decimal_strings', {}).get(name, str(row[name])))


def near(actual, expected):
    assert abs(D(str(actual)) - D(str(expected))) <= D('1e-7'), (actual, expected)


def test_one_wallet_owned_funding_crosses_month_without_intermediate_terminal(tmp_path):
    reference = Path(__file__).resolve().parents[1] / 'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
    assert hashlib.sha256(reference.read_bytes()).hexdigest() == REFERENCE_SHA
    spec = importlib.util.spec_from_file_location('_continuous_hand_reference', reference)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    # Exactly 200 complete pre-entry days, plus two finite future daily bars.
    bars = pl.DataFrame([dict(symbol=s, open_us=START+i*DAY,
        close_us=START+(i+1)*DAY, available_us=START+(i+1)*DAY,
        open=100.+.01*((i+1) % 2), close=100.+.01*((i+1) % 2),
        high=100.1+.01*((i+1) % 2), low=99.9+.01*((i+1) % 2), volume=1000.)
        for s in SYMBOLS for i in range(-200, 2)])
    decisions = np.array([START, BOUNDARY], dtype=np.int64)
    def factory(frame, clock, mode):
        return hold.fixed_targets(frame, clock, mode, symbols=SYMBOLS)
    initial_targets, _ = factory(bars, decisions, 'LONG_ONLY')
    assert initial_targets.filter(pl.col('available_us') == START)['target_weight'].to_list() == [.3, .3]
    poisoned = bars.with_columns([
        pl.when(pl.col('close_us') > START).then(pl.col(k)*1.02).otherwise(pl.col(k)).alias(k)
        for k in ('open', 'close', 'high', 'low')])
    future_targets, _ = factory(poisoned, decisions, 'LONG_ONLY')
    assert initial_targets.filter(pl.col('available_us') == START).equals(
        future_targets.filter(pl.col('available_us') == START))

    def minute_blocks():
        for begin, count in ((START, 1440), (BOUNDARY, 12)):
            stamps = begin + np.arange(count, dtype=np.int64)*MINUTE
            market = {s:dict(open=np.full(count, 100.), close=np.full(count, 100.),
                quote_volume=np.full(count, 100_000_000.), mark=np.full(count, 100.)) for s in SYMBOLS}
            if begin == START:
                # At the exact month event, 101 is observable but is not strictly
                # past. The coupon must use 99 from the prior completed minute.
                market['BTCUSDT']['mark'][-2:] = [99., 101.]
            yield dict(times=stamps, market=market)
    window = dict(start=START, end=END, symbols=SYMBOLS, daily=bars,
        events=[dict(symbol='BTCUSDT', event_us=START+1000, raw_rate=.001, reported_interval_hours=8.),
            dict(symbol='BTCUSDT', event_us=BOUNDARY, raw_rate=.001, reported_interval_hours=8.),
            dict(symbol='ETHUSDT', event_us=BOUNDARY, raw_rate=-.0002, reported_interval_hours=8.)],
        minute_blocks=minute_blocks, input_proofs=[])
    accounts = []
    def one_account(config, *, symbols):
        account = USDTLinearPerpetualAccount(config, symbols=symbols)
        accounts.append(account)
        return account
    # This is one simulation with one 10k account, not two monthly simulations.
    case = engine.simulate(window, 'LONG_ONLY', engine.COSTS[0], engine.UNITS[0],
        target_factory=factory, account_factory=one_account)
    assert len(accounts) == 1 and 'market' not in window
    summary = case['summary']
    assert summary['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT'
    assert summary['completed_minutes'] == summary['required_minutes'] == 1452
    assert summary['fresh_flat_no_past_mark_events'] == 1
    assert summary['funding_owned_events'] == 2 and summary['terminal_cash_realized']
    assert len(case['funding']) == 3 and not case['funding'][0]['owned']
    for symbol in SYMBOLS:
        opening = next(t for t in case['trades'] if t['symbol'] == symbol)
        near(amount(opening, 'quantity'), D('29.7'))
        assert opening['event_us'] == START+MINUTE+1
        at_boundary = case['minute'].filter(pl.col('close_us') == BOUNDARY).row(0, named=True)
        near(at_boundary[symbol+'_quantity'], D('29.7'))
        coupon = next(r for r in case['funding'] if r['symbol'] == symbol and r['event_us'] == BOUNDARY)
        assert coupon['owned'] and coupon['mark_close_us'] == BOUNDARY-MINUTE
        mark = D(99) if symbol == 'BTCUSDT' else D(100)
        rate = D('.001') if symbol == 'BTCUSDT' else D('-.0002')
        near(amount(coupon, 'signed_funding_USDT'), -D('29.7')*mark*rate)
        near(amount(coupon, 'mark_price'), mark)
    assert all(t['signal_us'] < BOUNDARY for t in case['trades'] if t['event_us'] < BOUNDARY)
    assert all(t['quantity_after'] != 0 for t in case['trades'] if t['event_us'] < END-5*MINUTE+1)
    assert all(t['signal_us'] == END-6*MINUTE for t in case['trades'] if t['quantity_after'] == 0)

    # Independent mature Decimal wallet reference replays only the recorded
    # synthetic legs/coupons, with one initial capital base for the portfolio.
    hands = {s:module.HandLedger(D(0)) for s in SYMBOLS}
    journal = [(r['event_us'], 1, r) for r in case['trades']]
    journal += [(r['event_us'], 0, r) for r in case['funding']]
    for _, kind, row in sorted(journal, key=lambda r:r[:2]):
        hand = hands[row['symbol']]
        if kind:
            expected = hand.fill(amount(row, 'position_delta'), amount(row, 'fill_price'), D('.00055'))
            near(amount(row, 'fee_amount'), expected['fee'])
        elif row['owned']:
            near(amount(row, 'quantity'), hand.quantity)
            expected = hand.funding(amount(row, 'mark_price'), D(str(row['raw_rate'])),
                rate_unit='EXPLICIT_SYNTHETIC_FRACTION', signed_quantity_before_event=hand.quantity)
            near(amount(row, 'signed_funding_USDT'), expected)
        else:
            assert hand.quantity == 0 and amount(row, 'signed_funding_USDT') == 0
    assert all(hand.quantity == 0 for hand in hands.values())
    expected_net = sum((hand.wallet for hand in hands.values()), D(0))
    near(amount(summary, 'net_PnL'), expected_net)
    near(amount(summary, 'NAV'), D(10000)+expected_net)
    (tmp_path/'continuous_boundary_evidence.json').write_text(json.dumps(dict(
        scope='ONE_SYNTHETIC_MONTH_BOUNDARY_NOT_MARKET_RETURN', account_constructions=len(accounts),
        completed_minutes=summary['completed_minutes'], boundary_owned_coupons=case['funding'][1:],
        final_terminal_signal_us=END-6*MINUTE, initial_capital_USDT=10000,
        independent_expected_net_USDT=str(expected_net), funding_USDT=summary['funding_USDT'],
        future_daily_target_prefix_unchanged=True), indent=2), encoding='utf-8')
