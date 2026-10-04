"""One finite Turtle compatibility/permission case; no market replay.

Original hooks and installed indicators drive real shared-account fills.
Independent Decimal wallet checks use the accepted hand reference. Historical
sources are ordinary modules in STATE; no production financial function is
copied or rewritten, and no old test suite is invoked.
"""
from copy import deepcopy
from decimal import Decimal as D, ROUND_DOWN, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import polars as pl
import pytest

from scripts.investment import turtle_perpetual_bridge as bridge_module
from scripts.investment import turtle_direction_mask as mask
from scripts.investment import perpetual_closing_exempt_account as closing
from scripts.investment import perpetual_directional as engine

ROOT = Path(__file__).resolve().parents[1]
STATE = Path('/home/xflops/coin-state').resolve()
PRIOR = '8288569c4ff673ebab3161ba17782ccec69c3411'
HAND_PATH = 'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
HAND_SHA = '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'
BAR, MINUTE, DAY = 14_400_000_000, 60_000_000, 86_400_000_000
FIRST = 1_748_736_000_000_000
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
TOL = D('1e-7')


def test_no_add_preserves_actual_callbacks_protection_and_ordered_risk(tmp_path):
    assert tmp_path.resolve().is_relative_to(STATE)
    protected = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in (
        'src/quant/perpetual_account.py', 'scripts/investment/perpetual_closing_exempt_account.py',
        'third_party/jesse_example_turtle_rules/turtle_rules_original.py')}
    assert hashlib.sha256((ROOT / HAND_PATH).read_bytes()).hexdigest() == HAND_SHA

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    hand = load('d060_independent_hand', ROOT / HAND_PATH)

    def historical(name, path):
        content = subprocess.run(['git', 'show', PRIOR + ':' + path], cwd=ROOT,
            check=True, capture_output=True).stdout
        target = tmp_path / (name + '.py')
        target.write_bytes(content)
        return load(name, target), hashlib.sha256(content).hexdigest()

    old_bridge, old_bridge_sha = historical('d060_prior_bridge', 'scripts/investment/turtle_perpetual_bridge.py')
    assert old_bridge_sha == '6056ead6e354df08dbdfa8cb19db2f70bc0d10a4f76035640779914d4a7c213b'
    # Only obsolete local-source hash barriers are disabled in this isolated
    # historical module. Vendor pins, strategy body and all order logic remain.
    old_bridge.DEPENDENCY_PINS = {}

    def candles(stamp, symbols=SYMBOLS, latest=None):
        opens = np.arange(stamp - 240 * BAR, stamp, BAR, dtype=np.int64)
        result = {s: np.column_stack((opens / 1000, np.full(240, 100.), np.full(240, 100.),
            np.full(240, 120.), np.full(240, 80.), np.full(240, 1000.))) for s in symbols}
        if latest:
            for s, values in latest.items():
                result[s][-1, 1:5] = values
        return result

    def available(frames):
        return {s: v[:, 0].astype(np.int64) * 1000 + BAR for s, v in frames.items()}

    entry = candles(FIRST, latest={'BTCUSDT': (100., 100., 125., 75.),
        'ETHUSDT': (100., 100., 119., 79.)})
    add_time = FIRST + BAR
    add = candles(add_time, latest={'BTCUSDT': (100., 145., 160., 100.),
        'ETHUSDT': (100., 65., 100., 50.)})
    for s in SYMBOLS:
        add[s][:-1] = entry[s][1:]

    def make(factory, *, symbols=SYMBOLS, **kwargs):
        account = closing.USDTLinearPerpetualAccount(symbols=symbols)
        account.update_marks(FIRST, {s: dict(price='100', close_us=FIRST, available_us=FIRST) for s in symbols})
        return factory(account, **kwargs)

    default = make(bridge_module.TurtlePerpetualBridge)
    explicit = make(bridge_module.TurtlePerpetualBridge, allow_pyramiding=True)
    enabled_mask = make(mask.TurtlePerpetualBridge, mode='LONG_SHORT')
    prior = make(old_bridge.TurtlePerpetualBridge)
    no_add = make(mask.TurtlePerpetualBridge, mode='LONG_SHORT', allow_pyramiding=False)
    hands = {s: hand.HandLedger(D(0)) for s in SYMBOLS}
    marks = dict.fromkeys(SYMBOLS, D(100))
    maximum = dict(wallet_USDT=D(0), NAV_USDT=D(0), fees_USDT=D(0), funding_USDT=D(0))
    evidence = []

    def check_hand(bridge, label):
        with localcontext() as context:
            context.prec = 50
            wallet = D(10000) + sum((h.wallet for h in hands.values()), D(0))
            nav = wallet + sum((h.unrealized(marks[s]) for s, h in hands.items()), D(0))
            actual = bridge.account.free_cash + sum((p.isolated_balance for p in bridge.account.positions.values()), D(0))
            errors = dict(wallet_USDT=abs(actual - wallet), NAV_USDT=abs(bridge.account.nav() - nav),
                fees_USDT=abs(bridge.account.fees - sum((h.fees for h in hands.values()), D(0))),
                funding_USDT=abs(bridge.account.funding_cash - sum((h.funding_cash for h in hands.values()), D(0))))
            for key, error in errors.items():
                maximum[key] = max(maximum[key], error)
                assert error <= TOL
            assert bridge.account.unpaid_liability == 0
            assert bridge.account.free_cash >= 0
            for s in SYMBOLS:
                assert bridge.account.positions[s].quantity == hands[s].quantity
            evidence.append(dict(stage=label, NAV=str(nav), wallet=str(wallet),
                quantities={s: str(h.quantity) for s, h in hands.items()}))

    def fill(bridge, order, opening, mids, capacity=None, *, reference=False):
        s = order['symbol']
        requested = D(str(order['quantity']))
        limit = requested if capacity is None else D(str(capacity))
        fill_id = order['id'] + ':' + str(order['attempts'])
        receipt = bridge.account.execute_fill(s, order['side'], requested, opening + 1,
            order['signal_us'], fill_id, execution_mid_price=mids[s], quote_available_us=opening,
            available_quantity=limit, reduce_only=order['reduce_only'])
        if reference:
            direction = D(1) if order['side'] == 'BUY' else D(-1)
            quantity = (min(requested, limit) / D('1e-8')).to_integral_value(rounding=ROUND_DOWN) * D('1e-8')
            if order['reduce_only']:
                quantity = min(quantity, abs(hands[s].quantity))
            actual = sum((D(r['decimal_strings']['quantity']) for r in receipt['fills']), D(0))
            assert actual == (quantity if quantity * mids[s] >= 10 or order['reduce_only'] else D(0))
            for row in receipt['fills']:
                price = mids[s] * (1 + direction * D('.0008'))
                q = D(row['decimal_strings']['quantity'])
                assert D(row['decimal_strings']['fill_price']) == price
                assert D(row['decimal_strings']['fee_amount']) == q * price * D('.00055')
                hands[s].fill(direction * q, price, '.00055')
        bridge.on_fill(order['id'], receipt)
        bridge.note_attempt(order['id'], opening + 1, receipt)
        if reference:
            check_hand(bridge, order['kind'])
        return receipt

    def complete(bridge, stamp, mids, *, reference=False, partial_first=False):
        for attempt in range(1, 6):
            opening = stamp + attempt * MINUTE
            for order in bridge.due_orders(opening, mids):
                cap = order['quantity'] / 2 if partial_first and attempt == 1 else None
                fill(bridge, order, opening, mids, cap, reference=reference)
        assert not any(bridge.pending.values())

    # Default enabled behavior matches exact prior two-asset logic, including
    # callbacks, quantity/cost/latency and original sub-step expiry handling.
    for bridge in (default, explicit, enabled_mask, prior, no_add):
        bridge.on_bar_close(FIRST, entry, np.zeros((30, 2)), FIRST,
            availability_us_by_symbol=available(entry))
        assert bridge.due_orders(FIRST, marks) == []
        assert [r['side'] for r in bridge.due_orders(FIRST + MINUTE, marks)] == ['BUY', 'SELL']
        complete(bridge, FIRST, marks, reference=bridge is no_add, partial_first=bridge is no_add)
        assert all(bridge.rules[s].current_pyramiding_levels == 1 for s in SYMBOLS)
        assert sum(r['name'] == 'on_open_position' for r in bridge.callbacks.values()) == 2
    for bridge in (explicit, enabled_mask, prior):
        assert bridge.account.snapshot() == default.account.snapshot()
        assert bridge.targets_frame().equals(default.targets_frame())
        assert bridge.journal == default.journal and bridge.stops == default.stops

    # No-add still submits and pays for mandatory reductions. Quantity is
    # legally rounded toward zero; no threshold/capacity/fee is relaxed.
    risk_time = FIRST + 10 * MINUTE
    target = {s: no_add.account.positions[s].quantity / 2 for s in SYMBOLS}
    no_add.force_targets(target, risk_time, 'RISK_REDUCTION')
    due = no_add.due_orders(risk_time + MINUTE, marks)
    assert len(due) == 2 and all(r['reduce_only'] and r['kind'] == 'RISK_REDUCTION' for r in due)
    for order in due:
        fill(no_add, order, risk_time + MINUTE, marks, reference=True)
    assert not any(no_add.pending.values())
    assert all(abs(no_add.account.positions[s].quantity) <= abs(target[s]) for s in SYMBOLS)

    marks = {'BTCUSDT': D(145), 'ETHUSDT': D(65)}
    for bridge in (default, explicit, enabled_mask, prior, no_add):
        bridge.account.update_marks(add_time, {s: dict(price=marks[s], close_us=add_time,
            available_us=add_time) for s in SYMBOLS})
        before = {s: bridge.account.positions[s].quantity for s in SYMBOLS}
        bridge.on_bar_close(add_time, add, np.zeros((30, 2)), FIRST,
            availability_us_by_symbol=available(add))
        assert {s: bridge.account.positions[s].quantity for s in SYMBOLS} == before
        if bridge is no_add:
            assert not any(r['kind'] == 'ADD' for r in bridge.intents.values())
            assert any(r['event'] == 'PROACTIVE_ADD_SUPPRESSED' for r in bridge.journal)
            assert all(bridge.rules[s].current_pyramiding_levels == 1 for s in SYMBOLS)
        else:
            assert all(r['kind'] == 'ADD' for r in bridge.due_orders(add_time + MINUTE, marks))
            complete(bridge, add_time, marks, partial_first=True)
            assert all(bridge.rules[s].current_pyramiding_levels == 2 for s in SYMBOLS)
            assert sum(r['name'] == 'on_increased_position' for r in bridge.callbacks.values()) == 2
    for bridge in (explicit, enabled_mask, prior):
        assert bridge.account.snapshot() == default.account.snapshot()
        assert bridge.targets_frame().equals(default.targets_frame())
        assert bridge.journal == default.journal and bridge.stops == default.stops
    check_hand(no_add, 'NO_ADD_OBSERVATION')

    # STOP wins over a same-observation proactive ADD and remains active
    # through partial fills, same-mode recovery and receipt replays.
    stop_time = add_time + BAR
    stop_bars = candles(stop_time, latest={'BTCUSDT': (145., 200., 210., 145.),
        'ETHUSDT': (65., 20., 65., 10.)})
    for s in SYMBOLS:
        stop_bars[s][:-1] = add[s][1:]
    for bridge in (default, no_add):
        bridge.account.update_marks(stop_time, {s: dict(price=marks[s], close_us=stop_time,
            available_us=stop_time) for s in SYMBOLS})
        bridge.observe_stop(stop_time, {s: dict(open_us=stop_time - MINUTE,
            available_us=stop_time, high=210, low=10) for s in SYMBOLS})
        pending = deepcopy(bridge.pending)
        bridge.on_bar_close(stop_time, stop_bars, np.zeros((30, 2)), FIRST,
            availability_us_by_symbol=available(stop_bars))
        assert bridge.pending == pending
        assert all(bridge.intents[v]['kind'] == 'STOP' for v in pending.values())
        assert bridge.due_orders(stop_time, marks) == []
    assert no_add._new('BTCUSDT', 'BUY', '.1', stop_time, 'ADD') is None
    assert all(no_add.intents[v]['kind'] == 'STOP' for v in no_add.pending.values())

    # Funding at the eligible open uses owned q and a strictly earlier mark;
    # actual fill follows at open+1us, with no short-sale principal in wallet.
    opening = stop_time + MINUTE
    for s, rate in [('BTCUSDT', D('.001')), ('ETHUSDT', D('-.001'))]:
        q = no_add.account.positions[s].quantity
        receipt = no_add.account.apply_funding(s, 'd060:' + s, opening, rate, opening)
        expected = -q * marks[s] * rate
        assert D(receipt['decimal_strings']['signed_funding_USDT']) == expected
        hands[s].funding(marks[s], rate, rate_unit='EXPLICIT_SYNTHETIC_FRACTION', signed_quantity_before_event=q)
    check_hand(no_add, 'OWNED_FUNDING_BEFORE_FILL')
    mids = {'BTCUSDT': D(45), 'ETHUSDT': D(160)}
    for order in no_add.due_orders(opening, mids):
        fill(no_add, order, opening, mids, order['quantity'] / 2, reference=True)
    assert all(no_add.pending.values())
    saved_account, saved_bridge = no_add.account.snapshot(), no_add.snapshot()
    no_add = mask.TurtlePerpetualBridge.from_snapshot(closing.USDTLinearPerpetualAccount.from_snapshot(saved_account),
        saved_bridge, mode='LONG_SHORT', allow_pyramiding=False)
    assert no_add.snapshot() == saved_bridge
    with pytest.raises(ValueError):
        mask.TurtlePerpetualBridge.from_snapshot(no_add.account, saved_bridge, mode='LONG_ONLY', allow_pyramiding=False)
    with pytest.raises(ValueError):
        mask.TurtlePerpetualBridge.from_snapshot(no_add.account, saved_bridge, mode='LONG_SHORT', allow_pyramiding=True)
    altered = deepcopy(saved_bridge)
    altered['allow_pyramiding'] = True
    altered['bridge']['allow_pyramiding'] = True
    with pytest.raises(ValueError):
        mask.TurtlePerpetualBridge.from_snapshot(no_add.account, altered, mode='LONG_SHORT', allow_pyramiding=True)
    renamed = deepcopy(enabled_mask.snapshot())
    renamed['allow_pyramiding'] = False
    renamed['bridge']['allow_pyramiding'] = False
    disabled_configuration = dict(renamed['bridge']['configuration'], allow_pyramiding=False, maximum_accepted_levels=1)
    renamed['bridge']['configuration'] = disabled_configuration
    renamed['bridge']['source_receipt']['configuration'] = disabled_configuration
    with pytest.raises(ValueError):
        mask.TurtlePerpetualBridge.from_snapshot(enabled_mask.account, renamed, mode='LONG_SHORT', allow_pyramiding=False)
    # Same receipt cannot re-trigger reduction callback or charge another fee.
    fill_id = next(reversed(no_add.processed))
    intent_id = no_add.processed[fill_id]['intent_id']
    old_receipt = no_add.account.fill_requests[fill_id]['receipt']
    before = no_add.snapshot()
    assert no_add.on_fill(intent_id, old_receipt)['replayed']
    assert no_add.note_attempt(intent_id, opening + 1, old_receipt)['replayed']
    assert no_add.snapshot() == before
    for order in no_add.due_orders(opening + MINUTE, mids):
        fill(no_add, order, opening + MINUTE, mids, reference=True)
    assert all(p.quantity == 0 for p in no_add.account.positions.values())
    assert not any(no_add.stops.values()) and not any(no_add.pending.values())
    assert all(no_add.rules[s].current_pyramiding_levels == 0 for s in SYMBOLS)

    # A genuine raw channel exit remains enabled with proactive ADD disabled.
    exited = make(mask.TurtlePerpetualBridge, mode='LONG_ONLY', allow_pyramiding=False)
    exited.on_bar_close(FIRST, entry, np.zeros((30, 2)), FIRST)
    complete(exited, FIRST, dict.fromkeys(SYMBOLS, D(100)))
    exit_bars = candles(add_time, latest={'BTCUSDT': (100., 70., 119., 60.)})
    for s in SYMBOLS:
        exit_bars[s][:-1] = entry[s][1:]
    exited.on_bar_close(add_time, exit_bars, np.zeros((30, 2)), FIRST)
    assert exited.intents[exited.pending['BTCUSDT']]['kind'] == 'EXIT'
    complete(exited, add_time, dict.fromkeys(SYMBOLS, D(100)))
    assert exited.account.positions['BTCUSDT'].quantity == 0

    # Terminal cancellation/reduction also remains a real paid fill path.
    terminal = make(mask.TurtlePerpetualBridge, mode='LONG_ONLY', allow_pyramiding=False)
    terminal.on_bar_close(FIRST, entry, np.zeros((30, 2)), FIRST)
    complete(terminal, FIRST, dict.fromkeys(SYMBOLS, D(100)))
    terminal.force_targets(dict.fromkeys(SYMBOLS, D(0)), risk_time, 'TERMINAL')
    assert terminal.due_orders(risk_time, dict.fromkeys(SYMBOLS, D(100))) == []
    complete(terminal, risk_time, dict.fromkeys(SYMBOLS, D(100)))
    assert terminal.terminal and terminal.account.fees > 0
    assert all(p.quantity == 0 for p in terminal.account.positions.values())

    # N=3 account order determines covariance columns, output and intent order.
    # Opposite returns with zero signed net still generate positive gross risk.
    symbols = ('SOLUSDT', 'ETHUSDT', 'BTCUSDT')
    many = make(mask.TurtlePerpetualBridge, symbols=symbols, mode='LONG_SHORT', allow_pyramiding=False)
    many_bars = candles(FIRST, symbols, latest={'BTCUSDT': (100., 100., 131., 81.),
        'ETHUSDT': (100., 100., 119., 69.), 'SOLUSDT': (100., 100., 119., 81.)})
    alternating = np.where(np.arange(30) % 2, .3, -.3)
    returns = np.column_stack((np.zeros(30), -alternating, alternating))
    many.on_bar_close(FIRST, many_bars, returns, FIRST)
    rows = many.targets_frame().to_dicts()
    assert [r['symbol'] for r in rows] == list(symbols)
    assert abs(sum(r['raw_signed_target'] for r in rows)) <= 1e-15
    raw = np.clip(np.asarray([r['raw_signed_target'] for r in rows]), -.3, .3)
    if np.abs(raw).sum() > .6:
        raw *= .6 / np.abs(raw).sum()
    centered = returns - returns.mean(axis=0)
    covariance = centered.T @ centered / 29 * 365
    sigma = float(np.sqrt(raw @ covariance @ raw))
    expected = raw * min(1., .1 / sigma)
    assert sigma > .1 and np.abs(expected).sum() > 0
    np.testing.assert_allclose([r['target_weight'] for r in rows], expected, rtol=0, atol=1e-12)
    assert many.risk_receipts[0]['covariance_assets'] == 3
    assert [r['symbol'] for r in many.due_orders(FIRST + MINUTE, dict.fromkeys(symbols, D(100)))] == ['ETHUSDT', 'BTCUSDT']
    ordered = ('BTCUSDT', 'SOLUSDT', 'ETHUSDT')
    permuted = make(mask.TurtlePerpetualBridge, symbols=ordered, mode='LONG_SHORT', allow_pyramiding=False)
    permuted.on_bar_close(FIRST, many_bars, returns[:, [2, 0, 1]], FIRST)
    actual_by_symbol = {r['symbol']: r['target_weight'] for r in rows}
    for r in permuted.targets_frame().to_dicts():
        assert abs(r['target_weight'] - actual_by_symbol[r['symbol']]) <= 1e-12
    wrong = deepcopy(many.snapshot())
    wrong['bridge']['symbols'] = list(ordered)
    with pytest.raises(ValueError):
        mask.TurtlePerpetualBridge.from_snapshot(many.account, wrong, mode='LONG_SHORT', allow_pyramiding=False)
    assert mask.TurtlePerpetualBridge.from_snapshot(many.account, many.snapshot(),
        mode='LONG_SHORT', allow_pyramiding=False).snapshot() == many.snapshot()

    # Future/late/missing warmup and mismatched N risk input reject without
    # changing the already committed prefix; no symbol silently disappears.
    prefix = many.snapshot()
    bad = deepcopy(many_bars)
    bad['BTCUSDT'] = bad['BTCUSDT'][:-1]
    with pytest.raises(ValueError):
        many.on_bar_close(FIRST, bad, returns, FIRST)
    late = available(many_bars)
    late['BTCUSDT'][-1] += 1
    with pytest.raises(ValueError):
        many.on_bar_close(FIRST, many_bars, returns, FIRST, availability_us_by_symbol=late)
    future = {s: np.vstack((v, [FIRST / 1000, 999., 999., 1000., 998., 1.])) for s, v in many_bars.items()}
    poisoned = deepcopy(future)
    for values in poisoned.values():
        values[-1, 1:] *= 7
    for source in (future, poisoned):
        with pytest.raises(ValueError):
            many.on_bar_close(FIRST, source, returns, FIRST)
        closed = {s: v[v[:, 0] * 1000 + BAR <= FIRST] for s, v in source.items()}
        assert many.on_bar_close(FIRST, closed, returns, FIRST) == many.bar_receipts[str(FIRST)]
    with pytest.raises(ValueError):
        many.on_bar_close(FIRST, many_bars, returns[:, :2], FIRST)
    assert many.snapshot() == prefix
    with pytest.raises(ValueError):
        make(mask.TurtlePerpetualBridge, mode='LONG_ONLY', allow_pyramiding=1)

    # The normal engine's default daily route remains exactly the historical
    # route on one finite day. No event strategy and no legacy suite are run.
    old_engine, old_engine_sha = historical('d060_prior_engine', 'scripts/investment/perpetual_directional.py')
    end = FIRST + DAY
    daily = pl.DataFrame([dict(symbol=s, close_us=FIRST, close=100.) for s in SYMBOLS],
        schema={'symbol': pl.String, 'close_us': pl.Int64, 'close': pl.Float64})
    window = dict(start=FIRST, end=end, symbols=SYMBOLS, daily=daily,
        events=[dict(symbol='BTCUSDT', event_us=FIRST + 10 * MINUTE, raw_rate=.001)],
        market={s: {k: np.full(1440, 1_000_000. if k == 'quote_volume' else 100.)
            for k in ('open', 'close', 'quote_volume', 'mark')} for s in SYMBOLS})

    def fixed_target(bars, decisions, mode):
        rows = [dict(symbol=s, available_us=int(t), target_weight=.1,
            raw_signed_target=.1, mode=mode) for t in decisions for s in SYMBOLS]
        return pl.DataFrame(rows), dict(scope='FINITE_DEFAULT_COMPATIBILITY_FIXTURE')

    cost, unit = engine.COSTS[0], engine.UNITS[0]
    baseline = old_engine.simulate(window, 'LONG_ONLY', cost, unit,
        target_factory=fixed_target, account_factory=closing.USDTLinearPerpetualAccount)
    current = engine.simulate(window, 'LONG_ONLY', cost, unit,
        target_factory=fixed_target, account_factory=closing.USDTLinearPerpetualAccount)
    assert current['minute'].equals(baseline['minute']) and current['targets'].equals(baseline['targets'])
    for key in ('summary', 'trades', 'funding', 'rejections', 'breaches', 'target_meta'):
        assert current[key] == baseline[key]
    assert current['summary']['terminal_cash_realized'] and current['summary']['fees_USDT'] > 0
    assert current['summary']['funding_owned_events'] == 1

    # One real optional-event route: first-minute capacity is zero, subsequent
    # ENTRY fragments remain legal in no-add mode. A coupon at an open settles
    # owned inventory with the earlier mark before that open+1us fragment.
    from types import SimpleNamespace
    event_window = dict(window, events=[dict(symbol='BTCUSDT', event_us=FIRST + 2 * MINUTE, raw_rate=.001)],
        market={s: {k: np.full(1440, 60_000. if k == 'quote_volume' else
            120. if k == 'high' else 80. if k == 'low' else 1000. if k == 'volume' else 100.)
            for k in ('open', 'close', 'quote_volume', 'mark', 'high', 'low', 'volume')} for s in SYMBOLS})

    def decision(bridge, histories, stamp):
        frame = entry if stamp == FIRST else add if stamp == add_time else candles(stamp)
        bridge.on_bar_close(stamp, frame, np.zeros((30, 2)), FIRST)

    event_module = SimpleNamespace(FOUR_HOURS=BAR, prepare_signal_context=lambda _: {},
        decision=decision, bridge_factory=lambda account, mode: mask.TurtlePerpetualBridge(
            account, mode, allow_pyramiding=False))
    routed = engine.simulate(event_window, 'LONG_ONLY', cost, unit,
        account_factory=closing.USDTLinearPerpetualAccount, event_strategy=event_module)
    assert routed['summary']['completion'] == 'COMPLETE_CONDITIONAL_ACCOUNT'
    assert routed['summary']['terminal_cash_realized']
    assert not any(row['kind'] == 'ADD' for row in routed['target_meta']['journal'] if row['event'] == 'INTENT_SUBMITTED')
    assert any(row['event'] == 'PROACTIVE_ADD_SUPPRESSED' for row in routed['target_meta']['journal'])
    coupon = routed['funding'][0]
    assert coupon['owned'] and coupon['event_us'] == FIRST + 2 * MINUTE
    assert coupon['mark_close_us'] < coupon['event_us']
    tied = [r for r in routed['trades'] if r['event_us'] == coupon['event_us'] + 1]
    assert tied and all(r['symbol'] == 'BTCUSDT' and r['side'] == 'BUY' for r in tied)
    event_hand = hand.HandLedger(D(10000))
    ordered_events = sorted([(r['event_us'], 1, r) for r in routed['trades']]
        + [(r['event_us'], 0, r) for r in routed['funding']], key=lambda r: (r[0], r[1]))
    for _, kind, row in ordered_events:
        if kind == 0:
            assert D(row['decimal_strings']['quantity']) == event_hand.quantity
            expected_fund = -event_hand.quantity * D(100) * D('.001')
            assert D(row['decimal_strings']['signed_funding_USDT']) == expected_fund
            event_hand.funding(100, '.001', rate_unit='EXPLICIT_SYNTHETIC_FRACTION',
                signed_quantity_before_event=event_hand.quantity)
        else:
            signed = D(row['decimal_strings']['quantity']) * (1 if row['side'] == 'BUY' else -1)
            event_hand.fill(signed, row['decimal_strings']['fill_price'], '.00055')
    assert event_hand.quantity == 0
    assert abs(D(routed['summary']['decimal_strings']['NAV']) - event_hand.wallet) <= TOL

    for name, value in protected.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value
    (tmp_path / 'turtle_no_add_evidence.json').write_text(json.dumps(dict(
        scope='ONE_FINITE_SYNTHETIC_COMPATIBILITY_CASE_NOT_MARKET_OR_INVESTMENT_RESULT',
        old_bridge_sha256=old_bridge_sha, old_engine_sha256=old_engine_sha,
        no_add_summary=no_add.account.summary(), stages=evidence,
        maximum_hand_errors_USDT={k: str(v) for k, v in maximum.items()},
        no_add_journal=no_add.journal, ordered_covariance_symbols=list(symbols),
        event_route_summary=routed['summary'], event_route_coupon=coupon,
        event_route_hand_wallet=str(event_hand.wallet)), indent=2, allow_nan=False) + '\n')
