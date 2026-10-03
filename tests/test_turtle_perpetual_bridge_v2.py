"""One new Turtle callback/partial/recovery path; no old account suite replay.

Artificial candles use the real pinned Turtle class and official ATR kernel.
All temporary evidence belongs to pytest's independent STATE basetemp.
This case does not certify Jesse intrabar stops or real funding availability.
"""
import ast
from copy import deepcopy
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
from scripts.investment import turtle_perpetual_bridge as bridge_module

ROOT = Path(__file__).resolve().parents[1]
HAND_PATH = ROOT / 'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
HAND_SHA = '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'
HOUR4, MINUTE, DAY = 14_400_000_000, 60_000_000, 86_400_000_000
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
TOL = D('1e-7')


def test_turtle_partial_recovery_and_observed_stop_precedence(tmp_path):
    assert hashlib.sha256(HAND_PATH.read_bytes()).hexdigest() == HAND_SHA
    spec = importlib.util.spec_from_file_location('d047_hand_wallet', HAND_PATH)
    hand_module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = hand_module
    spec.loader.exec_module(hand_module)
    # Deliberately do not call the old hand_reference_checks suite.
    hands = {s: hand_module.HandLedger(D(0)) for s in SYMBOLS}
    account = USDTLinearPerpetualAccount()
    bridge = bridge_module.TurtlePerpetualBridge(account)
    marks = dict.fromkeys(SYMBOLS, D('100'))
    maximum = dict(NAV_USDT=D(0), wallet_USDT=D(0), fees_USDT=D(0), funding_USDT=D(0), realized_USDT=D(0))
    stages = []
    # Midnight scoring begins from flat despite the completed warmup history.
    first = 1_748_736_000_000_000  # 2025-06-01 00:00 UTC, unlocked.
    assert first % DAY == 0

    def candles(decision, latest=None):
        result = {}
        for symbol in SYMBOLS:
            opens = np.arange(decision - 240 * HOUR4, decision, HOUR4, dtype=np.int64)
            frame = np.column_stack((opens / 1000, np.full(240, 100.), np.full(240, 100.),
                                     np.full(240, 120.), np.full(240, 80.), np.full(240, 1000.)))
            if latest:
                frame[-1, 1:5] = latest[symbol]
            result[symbol] = frame
        return result

    def available(frames):
        return {s: frames[s][:, 0].astype(np.int64) * 1000 + HOUR4 for s in SYMBOLS}

    # Allpast constant true ranges are an independent exact ATR seed witness.
    original_class, official_receipt = bridge_module.official_context()
    raw_class = [n for n in ast.parse((bridge_module.VENDOR / 'turtle_rules_original.py').read_bytes()).body
                 if isinstance(n, ast.ClassDef) and n.name == 'TurtleRules']
    assert len(raw_class) == 1
    assert official_receipt['class_ast_sha256'] == hashlib.sha256(ast.dump(
        ast.Module(body=raw_class, type_ignores=[]), include_attributes=False).encode()).hexdigest()
    original = original_class()
    original.before()
    original.candles = candles(first)['BTCUSDT']
    assert abs(float(original.atr) - 40.) < 1e-12
    assert bridge.rules['BTCUSDT'].__class__.__name__ == original_class.__name__ == 'TurtleRules'
    assert bridge.source_receipt['class_ast_sha256'] == official_receipt['class_ast_sha256']

    # A small-ATR proposal exceeds both original per-asset bounds before caps.
    # Exercise the bridge's signed shared cap without fabricating a filled unit.
    cap_account = USDTLinearPerpetualAccount()
    cap_account.update_marks(first, {s: dict(price='100', close_us=first, available_us=first) for s in SYMBOLS})
    cap_bridge = bridge_module.TurtlePerpetualBridge(cap_account)
    cap_bars = candles(first)
    for s in SYMBOLS:
        cap_bars[s][:, 3:5] = [100.5, 99.5]
    cap_bars['BTCUSDT'][-1, 3:5] = [100.6, 99.4]
    cap_bars['ETHUSDT'][-1, 3:5] = [100.4, 99.4]
    cap_bridge.on_bar_close(first, cap_bars, np.zeros((30, 2)), first,
                           availability_us_by_symbol=available(cap_bars))
    cap_rows = cap_bridge.targets_frame().to_dicts()
    assert len(cap_rows) == 2 and sum(abs(r['raw_signed_target']) for r in cap_rows) > .6
    assert max(abs(r['target_weight']) for r in cap_rows) <= .3
    assert sum(abs(r['target_weight']) for r in cap_rows) <= .6
    assert all(D(r['quantity']) * D(100) <= D('2970') for r in cap_bridge.summary_orders().values())
    assert not cap_account.trades
    for attempt in range(1, 6):
        opening = first + attempt * MINUTE
        for order in cap_bridge.due_orders(opening, dict.fromkeys(SYMBOLS, D(100))):
            rejected = cap_account.execute_fill(order['symbol'], order['side'], order['quantity'],
                opening + 1, order['signal_us'], order['id'] + ':' + str(order['attempts']),
                execution_mid_price='100', quote_available_us=opening, available_quantity=0)
            assert not rejected['fills']
            cap_bridge.on_fill(order['id'], rejected)
            cap_bridge.note_attempt(order['id'], opening + 1, rejected)
    assert not cap_account.trades and not any(cap_bridge.pending.values())
    assert all(cap_bridge.rules[s].current_pyramiding_levels == 0 for s in SYMBOLS)
    assert not any(cap_bridge.stops.values())

    def check(label):
        with localcontext() as context:
            context.prec = 50
            expected_wallet = D(10000) + sum((h.wallet for h in hands.values()), D(0))
            expected_nav = expected_wallet + sum((h.unrealized(marks[s]) for s, h in hands.items()), D(0))
            actual_wallet = account.free_cash + sum((p.isolated_balance for p in account.positions.values()), D(0)) - account.unpaid_liability
            errors = dict(NAV_USDT=abs(account.nav() - expected_nav), wallet_USDT=abs(actual_wallet - expected_wallet),
                fees_USDT=abs(account.fees - sum((h.fees for h in hands.values()), D(0))),
                funding_USDT=abs(account.funding_cash - sum((h.funding_cash for h in hands.values()), D(0))),
                realized_USDT=abs(account.realized_PnL - sum((h.realized for h in hands.values()), D(0))))
            for key, value in errors.items():
                maximum[key] = max(maximum[key], value)
                assert value <= TOL
            for s in SYMBOLS:
                assert account.positions[s].quantity == hands[s].quantity
                assert abs(account.positions[s].entry_price - hands[s].entry_fill) <= TOL
                assert account.positions[s].isolated_balance >= 0
            assert account.free_cash >= 0 and account.unpaid_liability == 0
            stages.append(dict(stage=label, NAV=str(account.nav()), wallet=str(actual_wallet),
                               quantities={s: str(h.quantity) for s, h in hands.items()}))

    def update_mark(stamp, prices):
        nonlocal marks
        marks = {s: D(str(prices[s])) for s in SYMBOLS}
        account.update_marks(stamp, {s: dict(price=marks[s], close_us=stamp, available_us=stamp) for s in SYMBOLS})
        check('marks-' + str(stamp))

    def execute(order, open_us, prices, capacity=None, *, duplicate=False):
        s = order['symbol']; event = open_us + 1
        mid = D(str(prices[s])); request = order['quantity']
        limit = request if capacity is None else D(str(capacity))
        identity = order['id'] + ':' + str(order['attempts'])
        receipt = account.execute_fill(s, order['side'], request, event, order['signal_us'], identity,
            execution_mid_price=mid, quote_available_us=open_us, available_quantity=limit,
            reduce_only=order['reduce_only'])
        assert receipt['fills'], 'This path requires a real positive partial or complete execution'
        with localcontext() as context:
            context.prec = 50
            direction = D(1) if order['side'] == 'BUY' else D(-1)
            expected_qty = (min(request, limit) / D('1e-8')).to_integral_value(rounding=ROUND_DOWN) * D('1e-8')
            if order['reduce_only']:
                expected_qty = min(expected_qty, abs(hands[s].quantity))
            expected_price = mid * (1 + direction * D('.0008'))
            assert sum((D(r['decimal_strings']['quantity']) for r in receipt['fills']), D(0)) == expected_qty
            for row in receipt['fills']:
                q = D(row['decimal_strings']['quantity'])
                assert D(row['decimal_strings']['fill_price']) == expected_price
                assert D(row['decimal_strings']['fee_amount']) == q * expected_price * D('.00055')
                hands[s].fill(direction * q, expected_price, '.00055')
        bridge.on_fill(order['id'], receipt)
        bridge.note_attempt(order['id'], event, receipt)
        if duplicate:
            before = deepcopy(bridge.snapshot()); count = len(account.trades)
            repeated = account.execute_fill(s, order['side'], request, event, order['signal_us'], identity,
                execution_mid_price=mid, quote_available_us=open_us, available_quantity=limit,
                reduce_only=order['reduce_only'])
            assert repeated == receipt and len(account.trades) == count
            assert bridge.on_fill(order['id'], repeated)['replayed']
            assert bridge.note_attempt(order['id'], event, repeated)['replayed']
            assert bridge.snapshot() == before
        check(order['kind'] + '-' + s)
        return receipt

    def drain_substep_expiry(signal, first_remaining_attempt):
        # Original requested units need not be exact product quantity steps.
        # Notify genuine zero executions until the original five-attempt budget.
        for attempt in range(first_remaining_attempt, 6):
            opening = signal + attempt * MINUTE
            for order in bridge.due_orders(opening, marks):
                assert order['kind'] in ('ENTRY', 'ADD')
                assert order['quantity'] * marks[order['symbol']] < 10
                rejected = account.execute_fill(order['symbol'], order['side'], order['quantity'], opening + 1,
                    order['signal_us'], order['id'] + ':' + str(order['attempts']), execution_mid_price=marks[order['symbol']],
                    quote_available_us=opening, available_quantity=order['quantity'])
                assert not rejected['fills']
                bridge.on_fill(order['id'], rejected)
                bridge.note_attempt(order['id'], opening + 1, rejected)
        assert not any(bridge.pending.values())
        check('substep-expiry-' + str(signal))

    flat = candles(first)
    bad = deepcopy(flat); bad['BTCUSDT'] = bad['BTCUSDT'][:-1]
    with pytest.raises(ValueError, match='240'):
        bridge.on_bar_close(first, bad, np.zeros((30, 2)), first)
    delayed = available(flat); delayed['BTCUSDT'][-1] += 1
    with pytest.raises(ValueError, match='available'):
        bridge.on_bar_close(first, flat, np.zeros((30, 2)), first, availability_us_by_symbol=delayed)
    assert not bridge.intents and not account.trades

    # Flat receives genuine completed-bar breakouts in both directions.
    entry = candles(first, {'BTCUSDT': (100., 100., 125., 75.), 'ETHUSDT': (100., 100., 119., 79.)})
    update_mark(first, dict.fromkeys(SYMBOLS, 100))
    bridge.on_bar_close(first, entry, np.zeros((30, 2)), first, availability_us_by_symbol=available(entry))
    assert {r['side'] for r in bridge.due_orders(first + MINUTE, marks)} == {'BUY', 'SELL'}
    assert all(bridge.rules[s].current_pyramiding_levels == 0 for s in SYMBOLS)
    # Future observations are excluded, not clamped into the 240 closed slice.
    future = {s: np.vstack((entry[s], np.array([(first / 1000, 999., 999., 1000., 998., 1.)]))) for s in SYMBOLS}
    poisoned = {s: v.copy() for s, v in future.items()}
    for s in SYMBOLS:
        poisoned[s][-1, 1:] *= 7
    other = bridge_module.TurtlePerpetualBridge(USDTLinearPerpetualAccount())
    other.account.update_marks(first, {s: dict(price='100', close_us=first, available_us=first) for s in SYMBOLS})
    closed = {s: poisoned[s][poisoned[s][:, 0] * 1000 + HOUR4 <= first] for s in SYMBOLS}
    other.on_bar_close(first, closed, np.zeros((30, 2)), first, availability_us_by_symbol=available(closed))
    assert other.snapshot() == bridge.snapshot()
    with pytest.raises(ValueError, match='240'):
        other.on_bar_close(first, poisoned, np.zeros((30, 2)), first)
    for order in bridge.due_orders(first + MINUTE, marks):
        execute(order, first + MINUTE, marks)
    drain_substep_expiry(first, 2)
    assert hands['BTCUSDT'].quantity > 0 > hands['ETHUSDT'].quantity
    assert all(bridge.rules[s].current_pyramiding_levels == 1 for s in SYMBOLS)
    assert all(bridge.stops[s]['quantity'] == str(abs(hands[s].quantity)) for s in SYMBOLS)

    add_time = first + HOUR4
    add = candles(add_time, {'BTCUSDT': (100., 145., 160., 100.), 'ETHUSDT': (100., 65., 100., 50.)})
    for s in SYMBOLS:
        add[s][:-1] = entry[s][1:]
    update_mark(add_time, {'BTCUSDT': 145, 'ETHUSDT': 65})
    bridge.on_bar_close(add_time, add, np.zeros((30, 2)), first, availability_us_by_symbol=available(add))
    additions = bridge.due_orders(add_time + MINUTE, marks)
    assert len(additions) == 2 and all(r['kind'] == 'ADD' for r in additions)
    for order in additions:
        execute(order, add_time + MINUTE, marks, order['quantity'] / 2, duplicate=True)
    assert all(bridge.rules[s].current_pyramiding_levels == 2 for s in SYMBOLS)
    account_snapshot, bridge_snapshot = account.snapshot(), bridge.snapshot()
    account = USDTLinearPerpetualAccount.from_snapshot(account_snapshot)
    bridge = bridge_module.TurtlePerpetualBridge.from_snapshot(account, bridge_snapshot)
    assert bridge.snapshot() == bridge_snapshot
    for order in bridge.due_orders(add_time + 2 * MINUTE, marks):
        assert order['kind'] == 'ADD'
        execute(order, add_time + 2 * MINUTE, marks)
    drain_substep_expiry(add_time, 3)
    assert all(bridge.rules[s].current_pyramiding_levels == 2 for s in SYMBOLS)
    for s in SYMBOLS:
        assert bridge.stops[s]['quantity'] == str(abs(hands[s].quantity))
        callbacks = [r for r in bridge.callbacks.values() if r['name'] == 'on_increased_position' and bridge.intents[r['intent_id']]['symbol'] == s]
        assert len(callbacks) == 1
    assert sum((abs(hands[s].quantity) * marks[s] for s in SYMBOLS), D(0)) / account.nav() <= D('.6')
    assert all(abs(hands[s].quantity) * marks[s] / account.nav() <= D('.3') for s in SYMBOLS)

    stop_time = add_time + HOUR4
    update_mark(stop_time, {'BTCUSDT': 200, 'ETHUSDT': 20})
    original_stops = {s: D(bridge.stops[s]['price']) for s in SYMBOLS}
    bridge.observe_stop(stop_time, {s: dict(open_us=stop_time - MINUTE, available_us=stop_time,
        high=D('210'), low=D('10')) for s in SYMBOLS})
    stop_ids = dict(bridge.pending)
    same_observation_add = candles(stop_time, {'BTCUSDT': (145., 200., 210., 145.), 'ETHUSDT': (65., 20., 65., 10.)})
    for s in SYMBOLS:
        same_observation_add[s][:-1] = add[s][1:]
    bridge.on_bar_close(stop_time, same_observation_add, np.zeros((30, 2)), first,
        availability_us_by_symbol=available(same_observation_add))
    assert bridge.pending == stop_ids
    assert all(bridge.intents[i]['kind'] == 'STOP' for i in stop_ids.values())
    assert bridge.due_orders(stop_time, marks) == []  # Same-close fill is forbidden.
    # The more extreme gap is a separate permanent-halt branch, never a rescued fill.
    extreme = USDTLinearPerpetualAccount.from_snapshot(account.snapshot())
    extreme.update_marks(stop_time + MINUTE, {s: dict(price=('50' if s == 'BTCUSDT' else '180'),
        close_us=stop_time + MINUTE, available_us=stop_time + MINUTE) for s in SYMBOLS})
    assert extreme.status in ('BANKRUPT_HALT', 'LIQUIDATION_REQUIRED_HALT')
    assert extreme.halt_witness['symbol'] == 'ETHUSDT'
    with pytest.raises(RuntimeError, match='HALT'):
        extreme.execute_fill('ETHUSDT', 'BUY', abs(extreme.positions['ETHUSDT'].quantity),
            stop_time + MINUTE + 1, stop_time, 'd047-extreme-gap-must-not-trade',
            execution_mid_price='180', quote_available_us=stop_time + MINUTE, reduce_only=True)
    assert len(extreme.trades) == len(account.trades)
    gap_prices = {'BTCUSDT': D('50'), 'ETHUSDT': D('150')}
    update_mark(stop_time + MINUTE, gap_prices)
    for order in bridge.due_orders(stop_time + MINUTE, gap_prices):
        receipt = execute(order, stop_time + MINUTE, gap_prices, abs(hands[order['symbol']].quantity) / 2)
        assert D(receipt['fills'][0]['decimal_strings']['execution_mid_price']) == gap_prices[order['symbol']]
        assert D(receipt['fills'][0]['decimal_strings']['fill_price']) != original_stops[order['symbol']]
        assert bridge.pending[order['symbol']] == order['id'] and bridge.stops[order['symbol']]['triggered']
    assert all(h.quantity != 0 for h in hands.values())
    assert not any(r['name'] == 'on_stop_loss' for r in bridge.callbacks.values())
    partial_stop_snapshot = bridge.snapshot()
    account = USDTLinearPerpetualAccount.from_snapshot(account.snapshot())
    bridge = bridge_module.TurtlePerpetualBridge.from_snapshot(account, partial_stop_snapshot)
    assert bridge.snapshot() == partial_stop_snapshot

    # Funding owns the exact residual before the later final fill; not a real unit claim.
    funding_time = stop_time + 2 * MINUTE
    for s in SYMBOLS:
        expected = hands[s].funding(gap_prices[s], '.001', rate_unit='EXPLICIT_SYNTHETIC_FRACTION',
                                   signed_quantity_before_event=hands[s].quantity)
        receipt = account.apply_funding(s, 'd047-' + s, funding_time, '.001', funding_time)
        assert D(receipt['decimal_strings']['signed_funding_USDT']) == expected
        assert receipt['mark_close_us'] < funding_time
    check('residual-funding-before-close')
    for order in bridge.due_orders(funding_time, gap_prices):
        assert order['kind'] == 'STOP'
        execute(order, funding_time, gap_prices)
    assert all(h.quantity == 0 and account.positions[s].isolated_balance == 0 for s, h in hands.items())
    assert not any(bridge.pending.values()) and not any(bridge.stops.values()) and bridge.halt_reason is None
    assert sum(r['name'] == 'on_stop_loss' for r in bridge.callbacks.values()) == 2
    assert sum(r['name'] == 'on_close_position' for r in bridge.callbacks.values()) == 2
    check('actual-flat')

    # Exercise the newly derived controller, not only the isolated bridge.
    # These 240 artificial minutes form one complete fixed4h aggregate; all
    # price/source arrays are constructed here and never taken from a market.
    from scripts.investment import turtle_perpetual_research_v2 as controller
    simulation, derivation = controller.adapted_simulate()  # compile all anchors before synthetic arrays are used
    count = 240
    warm_rows = [dict(symbol=s, open_us=int(r[0]) * 1000, open=r[1], close=r[2], high=r[3], low=r[4], volume=r[5])
                 for s in SYMBOLS for r in entry[s]]
    risk_rows = [dict(symbol=s, close_us=int(t), available_us=int(t), close=100.) for s in SYMBOLS
                 for t in first + np.arange(-30, 1, dtype=np.int64) * DAY]
    artificial = dict(start=first, end=first + HOUR4,
        times=first + np.arange(count, dtype=np.int64) * MINUTE,
        daily=pl.DataFrame(risk_rows), warmup_4h=pl.DataFrame(warm_rows),
        market={s: dict(open=np.full(count, 100.), close=np.full(count, 100.), mark=np.full(count, 100.),
            high=np.full(count, 101.), low=np.full(count, 99.), volume=np.full(count, 1000.),
            quote_volume=np.full(count, 100000.)) for s in SYMBOLS},
        events=[dict(symbol=s, event_us=first + 120 * MINUTE, raw_rate='.001') for s in SYMBOLS])
    result = simulation(artificial, 'LONG_SHORT', controller.base.COSTS[0], controller.base.UNITS[0])
    assert result['summary']['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT'
    assert result['summary']['completed_minutes'] == count and result['minute'].height == count
    assert len(result['trades']) >= 4 and all(p['quantity'] == 0 for p in result['summary']['positions'].values())
    assert result['summary']['unpaid_liability'] == 0
    assert result['target_meta']['callbacks'] and derivation
    assert {r['side'] for r in result['trades']} == {'BUY', 'SELL'}
    # Independent hand wallet for the new small controller output only.
    controller_hands = {s: hand_module.HandLedger(D(0)) for s in SYMBOLS}
    events = [(r['event_us'], 0, 'FUNDING', r) for r in result['funding']] + [(r['event_us'], 1, 'FILL', r) for r in result['trades']]
    for _, _, kind, row in sorted(events, key=lambda item: (item[0], item[1])):
        h = controller_hands[row['symbol']]
        if kind == 'FUNDING':
            expected = h.funding('100', '.001', rate_unit='EXPLICIT_SYNTHETIC_FRACTION', signed_quantity_before_event=h.quantity)
            assert abs(expected - D(row['decimal_strings']['signed_funding_USDT'])) <= TOL
        else:
            delta = D(row['decimal_strings']['position_delta'])
            expected_price = D(100) * (1 + (D('.0008') if delta > 0 else -D('.0008')))
            assert D(row['decimal_strings']['fill_price']) == expected_price
            h.fill(delta, expected_price, '.00055')
    controller_wallet = D(10000) + sum((h.wallet for h in controller_hands.values()), D(0))
    assert abs(D(result['summary']['decimal_strings']['NAV']) - controller_wallet) <= TOL
    poisoned_window = deepcopy(artificial)
    for s in SYMBOLS:
        poisoned_window['market'][s]['high'][120:] = 10000.
        poisoned_window['market'][s]['low'][120:] = .01
    future_result = simulation(poisoned_window, 'LONG_SHORT', controller.base.COSTS[0], controller.base.UNITS[0])
    assert future_result['targets'].equals(result['targets'])
    assert [r for r in future_result['trades'] if r['event_us'] < first + 120 * MINUTE] == [r for r in result['trades'] if r['event_us'] < first + 120 * MINUTE]
    evidence = dict(scope='ONE_SYNTHETIC_REAL_HOOK_ATR_PARTIAL_CALLBACK_RECOVERY_DELAYED_STOP_SHARED_WALLET_PATH',
        official_source=official_receipt, HandLedger_sha256=HAND_SHA, source_bytes_unchanged=True,
        funding_unit='EXPLICIT_SYNTHETIC_FRACTION_NOT_HISTORICAL_CERTIFICATION',
        independent_maximum_errors_USDT={k: str(v) for k, v in maximum.items()}, stages=stages,
        account_summary=account.summary(), bridge_meta=bridge.meta(), snapshots_preserved=True,
        extreme_gap_no_rescue_halt=extreme.summary(), synthetic_controller_derivation=derivation,
        synthetic_controller_summary=result['summary'], synthetic_controller_targets=result['targets'].to_dicts(),
        native_Jesse_intrabar_or_Bybit_execution_certified=False, candidate='NO_QUALIFIED_CANDIDATE')
    (tmp_path / 'turtle_bridge_evidence.json').write_text(json.dumps(evidence, ensure_ascii=False,
        sort_keys=True, indent=2), encoding='utf-8')
