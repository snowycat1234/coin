"""One synthetic integration case for ordered assets in one shared wallet.

Fixed target rows isolate scheduler behavior; this does not certify an alpha
strategy or native instrument filters. All evidence stays in pytest STATE.
"""
from copy import deepcopy
from decimal import Decimal as D, ROUND_DOWN
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import polars as pl

from quant.execution_contract import ExecutionContractV2
from scripts.investment import perpetual_directional as engine
from scripts.investment.perpetual_closing_exempt_account import (
    InstrumentProfile, USDTLinearPerpetualAccount as Closing,
)

MINUTE = 60_000_000
DAY = 86_400_000_000
START = 1_754_006_400_000_000  # 2025-08-01 UTC
CASH_TOL = D('1e-7')
RATIO_TOL = D('1e-10')
STEP = D('1e-8')
REFERENCE = Path(__file__).resolve().parents[1] / 'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
REFERENCE_SHA = '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'


def amount(row, key):
    return D(row.get('decimal_strings', {}).get(key, str(row[key])))


def near(actual, expected, tolerance=CASH_TOL):
    error = abs(D(str(actual)) - D(str(expected)))
    assert error <= tolerance, (actual, expected, tolerance)
    return error


def hand_ledger_class():
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == REFERENCE_SHA
    spec = importlib.util.spec_from_file_location('_multi_asset_hand_reference', REFERENCE)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.HandLedger


def target_factory(symbols, schedule, exit_reasons=None):
    """Reverse rows deliberately: identities, not ordinal rows, own quantities."""
    def targets(_bars, decisions, mode):
        rows = []
        for day, stamp in enumerate(decisions):
            weights = schedule[min(day, len(schedule) - 1)]
            for i in reversed(range(len(symbols))):
                symbol = symbols[i]
                reason = (exit_reasons or {}).get((day, symbol),
                    'POOL_EXIT' if day and weights[i] == 0 else 'ELIGIBLE')
                rows.append(dict(available_us=int(stamp), symbol=symbol,
                    target_weight=float(weights[i]), eligibility_reason=reason))
        return pl.DataFrame(rows), {'scope': 'FIXED_SYNTHETIC_SCHEDULER_TARGETS',
            'symbols': list(symbols), 'mode': mode}
    return targets


def window(symbols, n=2892):
    market = {}
    for i, symbol in enumerate(symbols):
        # Distinct prices reveal any symbol/array-order mismatch, without a
        # price gap or volatility-driven cap change obscuring execution tests.
        price = 100. + i * 10.
        opens = np.full(n, price)
        market[symbol] = dict(open=opens, close=opens.copy(), mark=opens.copy(),
            quote_volume=np.full(n, 100_000_000.))
    decisions = np.arange(START, START + n * MINUTE, DAY, dtype=np.int64)
    daily = pl.DataFrame([dict(symbol=s, close_us=int(t), close=100. + i * 10.)
        for t in decisions for i, s in enumerate(symbols)])
    events = [dict(symbol=s, event_us=START + offset,
        raw_rate=.0002 if i % 2 == 0 else -.0003, reported_interval_hours=8.)
        for i, s in enumerate(symbols)
        for offset in (1000, 3 * MINUTE, 3 * MINUTE + 1000,
                       DAY + MINUTE + 1, DAY + MINUTE + 1000)
        if offset < n * MINUTE]
    events.sort(key=lambda r: (r['event_us'], r['symbol']))
    return dict(symbols=symbols, start=START, end=START + n * MINUTE,
        market=market, daily=daily, events=events, input_proofs=[])


def day_blocks(original):
    result = {k: v for k, v in original.items() if k != 'market'}
    n = (original['end'] - original['start']) // MINUTE
    def blocks():
        for a in range(0, n, 1440):
            b = min(a + 1440, n)
            yield dict(times=START + np.arange(a, b, dtype=np.int64) * MINUTE,
                market={s: {k: v[a:b].copy() for k, v in original['market'][s].items()}
                        for s in reversed(original['symbols'])})
    result['minute_blocks'] = blocks
    return result


def run(source, targets):
    return engine.simulate(source, 'LONG_SHORT', engine.COSTS[0], engine.UNITS[0],
        target_factory=targets, account_factory=Closing)


def same_result(left, right):
    # The scheduler exposes attempts/rejections rather than an order journal.
    for key in ('trades', 'funding', 'rejections', 'breaches', 'extrema', 'summary', 'target_meta'):
        assert left[key] == right[key], key
    assert left['targets'].equals(right['targets'])
    assert left['minute'].columns == right['minute'].columns
    for key in left['minute'].columns:
        a, b = left['minute'][key].to_numpy(), right['minute'][key].to_numpy()
        if key == 'close_us':
            assert np.array_equal(a, b)
        else:
            tol = float(RATIO_TOL if key.endswith('weight') else CASH_TOL)
            np.testing.assert_allclose(a, b, rtol=0, atol=tol)


def independent_wallet(case, source, HandLedger):
    """Per-asset zero-initial quote changes plus ONE 10k capital base.

    Mature Decimal signed-position arithmetic independently replays recorded
    fills/funding. It never calls an engine/account valuation or fill function.
    """
    hands = {s: HandLedger(D(0)) for s in source['symbols']}
    combined = [(r['event_us'], 1, i, 'trade', r) for i, r in enumerate(case['trades'])]
    combined += [(r['event_us'], 0, i, 'funding', r) for i, r in enumerate(case['funding'])]
    combined.sort(key=lambda item: item[:3])  # coupons before same-time fills
    cursor = 0
    fees = cost = turnover = mid_cash = D(0)
    max_cash = max_ratio = D(0)
    used_capacity = {}
    for minute in case['minute'].iter_rows(named=True):
        stamp = minute['close_us']
        while cursor < len(combined) and combined[cursor][0] <= stamp:
            event, _, _, kind, row = combined[cursor]
            symbol = row['symbol']; hand = hands[symbol]
            if kind == 'funding':
                near(amount(row, 'quantity'), hand.quantity)
                past = (event - START - 1) // MINUTE - 1
                if past < 0:
                    assert hand.quantity == 0 and not row['owned']
                    assert row['status'] == 'NO_POSITION_NO_PAST_MARK'
                    near(amount(row, 'signed_funding_USDT'), 0)
                else:
                    mark = D(str(source['market'][symbol]['mark'][past]))
                    assert row['mark_close_us'] == START + (past + 1) * MINUTE < event
                    near(amount(row, 'mark_price'), mark)
                    coupon = hand.funding(mark, D(str(row['raw_rate'])),
                        rate_unit='EXPLICIT_SYNTHETIC_FRACTION',
                        signed_quantity_before_event=hand.quantity)
                    near(amount(row, 'signed_funding_USDT'), coupon)
                    assert row['owned'] is bool(hand.quantity)
            else:
                index = (event - START - 1) // MINUTE
                assert event == START + index * MINUTE + 1 and index > 0
                assert event >= ExecutionContractV2().earliest_execution_us(row['signal_us']) + 1
                mid = D(str(source['market'][symbol]['open'][index]))
                delta, q = amount(row, 'position_delta'), amount(row, 'quantity')
                assert abs(delta) == q and q > 0 and q % STEP == 0
                assert (delta > 0) == (row['side'] == 'BUY')
                fill = mid * (D('1.0008') if delta > 0 else D('.9992'))
                near(amount(row, 'execution_mid_price'), mid)
                near(amount(row, 'fill_price'), fill)
                near(amount(row, 'quantity_before'), hand.quantity)
                expected = hand.fill(delta, fill, D('.00055'))
                near(amount(row, 'quantity_after'), hand.quantity)
                near(amount(row, 'entry_price_after'), hand.entry_fill)
                near(amount(row, 'realized_PnL'), expected['realized_PnL'])
                near(amount(row, 'fee_amount'), expected['fee'])
                execution = q * abs(fill - mid)
                near(amount(row, 'execution_cost'), execution)
                fees += expected['fee']; cost += execution
                turnover += q * fill; mid_cash -= delta * mid
                key = symbol, index
                used_capacity[key] = used_capacity.get(key, D(0)) + q
                assert used_capacity[key] * mid <= D(str(
                    source['market'][symbol]['quote_volume'][index - 1])) * D('.001')
            cursor += 1
        index = (stamp - START) // MINUTE - 1
        wallet = D(10000) + sum((h.wallet for h in hands.values()), D(0))
        unrealized = D(0); gross = net = D(0)
        for symbol, hand in hands.items():
            mark = D(str(source['market'][symbol]['mark'][index]))
            signed = hand.quantity * mark
            unrealized += hand.unrealized(mark); gross += abs(signed); net += signed
            max_cash = max(max_cash, near(minute[symbol + '_quantity'], hand.quantity),
                near(minute[symbol + '_signed_marked_notional'], signed))
        nav = wallet + unrealized
        max_cash = max(max_cash, near(minute['nav'], nav),
            near(D(str(minute['free_cash'])) + D(str(minute['isolated_balance'])), wallet),
            near(minute['cumulative_fees'], fees), near(minute['cumulative_execution_costs'], cost),
            near(minute['cumulative_funding'], sum((h.funding_cash for h in hands.values()), D(0))))
        max_ratio = max(max_ratio, near(minute['gross_weight'], gross / nav, RATIO_TOL),
            near(minute['net_signed_weight'], net / nav, RATIO_TOL))
        assert minute['free_cash'] >= 0 and minute['isolated_balance'] >= 0
    assert cursor == len(combined) and all(h.quantity == 0 for h in hands.values())
    summary = case['summary']
    net = sum((h.wallet for h in hands.values()), D(0))
    funding = sum((h.funding_cash for h in hands.values()), D(0))
    for key, expected in (('net_PnL', net), ('gross_PnL_same_quantities', mid_cash),
            ('fees_USDT', fees), ('execution_cost_USDT', cost), ('funding_USDT', funding),
            ('gross_fill_turnover_USDT', turnover)):
        max_cash = max(max_cash, near(amount(summary, key), expected))
    near(net, mid_cash - fees - cost + funding)
    return dict(maximum_cash_error_USDT=str(max_cash), maximum_ratio_error=str(max_ratio),
        verified_minutes=case['minute'].height, verified_trade_legs=len(case['trades']))


def test_ordered_multi_asset_shared_wallet_blocks_exits_and_causality(tmp_path):
    HandLedger = hand_ledger_class()
    sets = [('ETHUSDT', 'BTCUSDT'), ('SOLUSDT', 'BTCUSDT', 'ADAUSDT'),
        ('SOLUSDT', 'BTCUSDT', 'ADAUSDT', 'ETHUSDT', 'XRPUSDT', 'BNBUSDT',
         'DOGEUSDT', 'LINKUSDT', 'LTCUSDT', 'DOTUSDT')]
    evidence = {'scope': 'SYNTHETIC_SHARED_WALLET_SCHEDULING_AND_DECIMAL_BRIDGE_NOT_ALPHA_OR_NATIVE_FILTERS',
        'tolerances': {'cash_USDT': str(CASH_TOL), 'ratio': str(RATIO_TOL)}, 'cases': []}
    for symbols in sets:
        first = [.12, -.12] + [0.] * (len(symbols) - 2) if len(symbols) < 10 else [
            .04 if i % 2 == 0 else -.04 for i in range(len(symbols))]
        second = [0., .08] + ([.08] if len(symbols) == 3 else [])
        if len(symbols) == 10:
            second += [.035 if i % 2 == 0 else -.035 for i in range(2, 10)]
        targets = target_factory(symbols, [first, second, [0.] * len(symbols)])
        original = window(symbols)
        case = run(original, targets)
        same_result(case, run(day_blocks(original), targets))
        assert case['summary']['symbols'] == list(symbols)
        assert case['summary']['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT'
        assert case['summary']['completed_minutes'] == 2892
        assert case['summary']['terminal_cash_realized'] and case['summary']['fees_USDT'] > 0
        for i, symbol in enumerate(symbols):
            if first[i] == 0:
                continue
            initial = next(r for r in case['trades'] if r['symbol'] == symbol)
            expected = (D(str(abs(first[i]))) * D('.99') * D(10000) /
                D(str(100. + i * 10.)) / STEP).to_integral_value(rounding=ROUND_DOWN) * STEP
            near(amount(initial, 'quantity'), expected)
            assert initial['side'] == ('BUY' if first[i] > 0 else 'SELL')
            assert initial['event_us'] == START + MINUTE + 1
        at_rebalance = [r for r in case['trades'] if r['event_us'] == START + DAY + MINUTE + 1]
        first_open = next(i for i, r in enumerate(at_rebalance) if r['leg'] == 'OPEN')
        assert first_open > 0 and all(r['leg'] == 'CLOSE' for r in at_rebalance[:first_open])
        assert all(r['leg'] == 'OPEN' for r in at_rebalance[first_open:])
        evidence['cases'].append(dict(symbols=list(symbols), **independent_wallet(case, original, HandLedger)))
        if len(symbols) == 3:
            three_case, three_source, three_targets = case, original, targets

    # A terminal signal in the last minute of day0 executes at day1 +1us.
    # Day1's huge volume must not replace the prior day's tiny known capacity.
    boundary = window(sets[0], 1445)
    for symbol in sets[0]:
        boundary['market'][symbol]['quote_volume'][1439] = 1000.
    boundary_targets = target_factory(sets[0], [[.12, -.12], [.12, -.12]])
    crossed = run(boundary, boundary_targets)
    same_result(crossed, run(day_blocks(boundary), boundary_targets))
    partial = [r for r in crossed['trades'] if r['event_us'] == START + DAY + 1]
    assert len(partial) == 2 and all(r['leg'] == 'CLOSE' for r in partial)
    for row in partial:
        mid = amount(row, 'mid_price')
        expected = (D(1) / mid / STEP).to_integral_value(rounding=ROUND_DOWN) * STEP
        near(amount(row, 'quantity'), expected)
        assert amount(row, 'quantity') * amount(row, 'fill_price') < 10
    independent_wallet(crossed, boundary, HandLedger)

    # Flat later-joining ADA may have no mark even after the other assets trade.
    joining = day_blocks(three_source)
    def joining_blocks():
        for a, b, active in ((0, 4, sets[1][:2]), (4, 1440, sets[1]),
                             (1440, 2880, sets[1]), (2880, 2892, sets[1])):
            yield dict(times=START + np.arange(a, b, dtype=np.int64) * MINUTE,
                market={s: {k: v[a:b] for k, v in three_source['market'][s].items()} for s in active})
    joining['minute_blocks'] = joining_blocks
    joined = run(joining, three_targets)
    assert joined['summary']['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT'
    absent_coupon = next(r for r in joined['funding'] if r['symbol'] == 'ADAUSDT'
        and r['event_us'] == START + 3 * MINUTE + 1000)
    assert absent_coupon['status'] == 'NO_POSITION_NO_PAST_MARK' and not absent_coupon['owned']
    assert any(r['symbol'] == 'ADAUSDT' and r['leg'] == 'OPEN' for r in joined['trades'])
    assert joined['trades'] == three_case['trades']
    assert joined['minute'].equals(three_case['minute'])

    # A zero target is a mandatory exit, not ordinary five-attempt expiry.
    dry = window(sets[0], 1452)
    for symbol in sets[0]:
        dry['market'][symbol]['quote_volume'][1440:] = 0.
    exits = target_factory(sets[0], [[.12, -.12], [0., 0.]],
        {(1, sets[0][1]): 'WARMUP_OR_DATA_GAP'})
    stopped = run(dry, exits)
    assert stopped['summary']['completion'] == 'NOT_EVALUABLE_UNEXECUTABLE_ASSET_EXIT'
    assert stopped['summary']['stop_us'] == START + DAY + 5 * MINUTE + 1
    assert stopped['summary']['completed_minutes'] < stopped['summary']['required_minutes']
    assert all(stopped['summary']['positions'][s]['quantity'] != 0 for s in sets[0])
    assert all(r['event_us'] < START + DAY for r in stopped['trades'])

    missing = day_blocks(three_source)
    def missing_blocks():
        for a, b in ((0, 4), (4, 1440), (1440, 2880), (2880, 2892)):
            active = sets[1] if a == 0 else sets[1][1:]
            yield dict(times=START + np.arange(a, b, dtype=np.int64) * MINUTE,
                market={s: {k: v[a:b] for k, v in three_source['market'][s].items()} for s in active})
    missing['minute_blocks'] = missing_blocks
    unavailable = run(missing, three_targets)
    assert unavailable['summary']['completion'] == 'NOT_EVALUABLE_MISSING_HELD_ASSET_EXECUTION_OR_MARK'
    assert unavailable['summary']['stop_us'] == START + 4 * MINUTE
    assert unavailable['minute'].height == 4
    assert unavailable['summary']['positions']['SOLUSDT']['quantity'] > 0
    assert unavailable['summary']['terminal_marked_notional'] > 0

    # Zero desired net exposure never excuses a >.6 shared gross allocation.
    crowded = window(sets[2], 18)
    alternating = [.08 if i % 2 == 0 else -.08 for i in range(10)]
    assert sum(D(str(v)) for v in alternating) == 0
    guarded = run(crowded, target_factory(sets[2], [alternating]))
    assert guarded['summary']['maximum_actual_gross_weight'] <= .6 + float(RATIO_TOL)
    assert any(r.get('reason') == 'POST_FILL_EXPOSURE_CAP_REJECTED' for r in guarded['rejections'])
    assert guarded['summary']['terminal_cash_realized']

    # A configured coarse lot can overshoot a frozen risk target toward zero.
    # That successful reduction must not become five false residual attempts.
    drift = window(sets[1], 18)
    drift['market']['SOLUSDT']['mark'][3:] = 110.
    profiles = {s: InstrumentProfile(quantity_step='.1') for s in sets[1]}
    def coarse_account(config, *, symbols):
        return Closing(config, symbols=symbols, instrument_profiles=profiles)
    corrected = engine.simulate(drift, 'LONG_SHORT', engine.COSTS[0], engine.UNITS[0],
        target_factory=target_factory(sets[1], [[.29, -.29, 0.]]), account_factory=coarse_account)
    assert corrected['summary']['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT'
    assert corrected['breaches'] and corrected['breaches'][0]['signal_us'] == START + 4 * MINUTE
    reduced = [r for r in corrected['trades'] if r['signal_us'] == START + 4 * MINUTE]
    assert reduced and all(r['leg'] == 'CLOSE' and amount(r, 'quantity') % D('.1') == 0 for r in reduced)
    assert all(r['event_us'] == START + 5 * MINUTE + 1 for r in reduced)
    independent_wallet(corrected, drift, HandLedger)

    cut_index = 1450; cut = START + cut_index * MINUTE
    poisoned = deepcopy(three_source)
    for prices in poisoned['market'].values():
        for key in ('open', 'close', 'mark'):
            prices[key][cut_index:] *= 1.01
        prices['quote_volume'][cut_index:] *= .5
    poisoned['events'] = [{**r, 'raw_rate': .123 if r['event_us'] >= cut else r['raw_rate']}
                          for r in poisoned['events']]
    poisoned['daily'] = poisoned['daily'].with_columns(pl.when(pl.col('close_us') > cut)
        .then(pl.col('close') * 1.1).otherwise(pl.col('close')).alias('close'))
    future = run(poisoned, three_targets)
    assert three_case['minute'].filter(pl.col('close_us') <= cut).equals(
        future['minute'].filter(pl.col('close_us') <= cut))
    for key in ('trades', 'funding', 'rejections'):
        assert [r for r in three_case[key] if r['event_us'] < cut] == [
            r for r in future[key] if r['event_us'] < cut]
    evidence.update(cross_day_capacity_uses_previous_completed_quote=True,
        missing_held_asset_completion=unavailable['summary']['completion'],
        unexecutable_exit_completion=stopped['summary']['completion'],
        future_prefix_unchanged_through_us=cut, original_reference_sha256=REFERENCE_SHA)
    (tmp_path / 'multi_asset_replay_evidence.json').write_text(
        json.dumps(evidence, indent=2, sort_keys=True), encoding='utf-8')
