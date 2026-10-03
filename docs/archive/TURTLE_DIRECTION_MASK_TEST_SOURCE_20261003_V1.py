"""UNRUN one direction-mask compatibility path; no new market or old suite.

Real pinned Turtle hooks/ATR propose simultaneous long and short breakouts.
Only flat-entry direction is filtered. Protective opposite-side fills remain
legal; independent HandLedger checks that partial/restore/replay adds no fee.
"""
from copy import deepcopy
from decimal import Decimal as D, ROUND_DOWN, localcontext
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
STATE = Path('/home/xflops/coin-state')
MASK_PATH = 'scripts/investment/turtle_direction_mask.py'
MASK_SHA = '748033f2f9b8b717324ed2db5f28556f5e9e88c1e53af65b07f513a74a2f906f'
HAND_PATH = 'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
HAND_SHA = '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a'
PINS = {
    'scripts/investment/turtle_perpetual_bridge.py': '6056ead6e354df08dbdfa8cb19db2f70bc0d10a4f76035640779914d4a7c213b',
    'scripts/investment/perpetual_closing_exempt_account.py': 'd4c1636be51b067be6b86437cd69f158320f47c258f0d78f0a47f21806c617ac',
    'src/quant/perpetual_account.py': 'cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261',
    'src/quant/backtest.py': 'ee333d4e5cbadb489e5d467619d0872f78ccb2d86d8b5f46eacc69cb63f9829a',
    'third_party/jesse_example_turtle_rules/turtle_rules_original.py': '35e4c3cd69010ca81402277693cb6f7deaf52a284153f20f25d4cf605701408a',
    HAND_PATH: HAND_SHA,
}
HOUR4, MINUTE, DAY = 14_400_000_000, 60_000_000, 86_400_000_000
FIRST = 1_748_736_000_000_000  # Same genuine unlocked fixture epoch; fresh flat.
SYMBOLS = ('BTCUSDT', 'ETHUSDT')
TOL = D('1e-7')


def test_real_turtle_direction_mask_stop_partial_and_mode_recovery(tmp_path):
    assert tmp_path.resolve().is_relative_to(STATE)
    assert MASK_SHA is not None
    assert hashlib.sha256((ROOT / MASK_PATH).read_bytes()).hexdigest() == MASK_SHA
    for path, digest in PINS.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest

    def load(name, path):
        spec = importlib.util.spec_from_file_location(name, ROOT / path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    mask = load('d049_direction_mask_case', MASK_PATH)
    hand_module = load('d049_original_hand_ledger', HAND_PATH)
    from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Account
    results = []

    def bars():
        frames = {}
        opens = np.arange(FIRST - 240 * HOUR4, FIRST, HOUR4, dtype=np.int64)
        for symbol in SYMBOLS:
            frames[symbol] = np.column_stack((opens / 1000, np.full(240, 100.),
                np.full(240, 100.), np.full(240, 120.), np.full(240, 80.), np.full(240, 1000.)))
        frames['BTCUSDT'][-1, 1:5] = (100., 130., 140., 95.)
        frames['ETHUSDT'][-1, 1:5] = (100., 70., 105., 60.)
        return frames

    def available(frames):
        return {s: frames[s][:, 0].astype(np.int64) * 1000 + HOUR4 for s in SYMBOLS}

    for mode, allowed in (('LONG_ONLY', {'BTCUSDT': 'BUY'}),
                          ('SHORT_ONLY', {'ETHUSDT': 'SELL'}), ('CASH', {})):
        account = Account()
        prices = dict.fromkeys(SYMBOLS, D(100))
        account.update_marks(FIRST, {s: dict(price=prices[s], close_us=FIRST, available_us=FIRST) for s in SYMBOLS})
        bridge = mask.TurtlePerpetualBridge(account, mode=mode)
        hands = {s: hand_module.HandLedger(D(0)) for s in SYMBOLS}
        maximum = D(0)

        def check():
            nonlocal maximum
            with localcontext() as context:
                context.prec = 50
                wallet = D(10000) + sum((h.wallet for h in hands.values()), D(0))
                nav = wallet + sum((h.unrealized(prices[s]) for s, h in hands.items()), D(0))
                observed_wallet = account.free_cash + sum((p.isolated_balance for p in account.positions.values()), D(0))
                errors = (abs(nav - account.nav()), abs(wallet - observed_wallet),
                          abs(account.fees - sum((h.fees for h in hands.values()), D(0))))
                maximum = max(maximum, *errors)
                assert maximum <= TOL and account.unpaid_liability == 0
                for s in SYMBOLS:
                    assert account.positions[s].quantity == hands[s].quantity
                    if mode == 'LONG_ONLY':
                        assert hands[s].quantity >= 0
                    elif mode == 'SHORT_ONLY':
                        assert hands[s].quantity <= 0
                    else:
                        assert hands[s].quantity == 0

        def observe(t, new_prices):
            nonlocal prices
            prices = {s: D(str(new_prices[s])) for s in SYMBOLS}
            account.update_marks(t, {s: dict(price=prices[s], close_us=t, available_us=t) for s in SYMBOLS})
            check()

        def execute(order, opening, capacity=None):
            s = order['symbol']; limit = order['quantity'] if capacity is None else capacity
            args = dict(symbol=s, side=order['side'], quantity=order['quantity'], event_us=opening + 1,
                signal_us=order['signal_us'], fill_id=order['id'] + ':' + str(order['attempts']),
                execution_mid_price=prices[s], quote_available_us=opening,
                available_quantity=limit, reduce_only=order['reduce_only'])
            receipt = account.execute_fill(**args)
            assert receipt['fills']
            with localcontext() as context:
                context.prec = 50
                q = (min(order['quantity'], limit) / D('1e-8')).to_integral_value(rounding=ROUND_DOWN) * D('1e-8')
                if order['reduce_only']:
                    q = min(q, abs(hands[s].quantity))
                direction = D(1) if order['side'] == 'BUY' else D(-1)
                fill = prices[s] * (1 + direction * D('.0008'))
                assert sum((D(r['decimal_strings']['quantity']) for r in receipt['fills']), D(0)) == q
                assert all(abs(D(r['decimal_strings']['fill_price']) - fill) <= TOL for r in receipt['fills'])
                hands[s].fill(direction * q, fill, '.00055')
            bridge.on_fill(order['id'], receipt)
            bridge.note_attempt(order['id'], opening + 1, receipt)
            check()
            return receipt, args

        frames = bars()
        bridge.on_bar_close(FIRST, frames, np.zeros((30, 2)), FIRST,
                            availability_us_by_symbol=available(frames))
        for symbol, raw_pair in (('BTCUSDT', (True, False)), ('ETHUSDT', (False, True)):
            rule = bridge.rules[symbol]
            raw = type(rule)
            assert (raw.should_long(rule), raw.should_short(rule)) == raw_pair
            assert rule.should_long() == (symbol in allowed and allowed[symbol] == 'BUY')
            assert rule.should_short() == (symbol in allowed and allowed[symbol] == 'SELL')
        orders = bridge.due_orders(FIRST + MINUTE, prices)
        assert {o['symbol']: o['side'] for o in orders} == allowed
        assert all(not o['reduce_only'] for o in orders)
        targets = bridge.targets_frame().to_dicts()
        assert len(targets) == 2 and all(r['mode'] == mode for r in targets)
        assert all(r['target_weight'] == 0 for r in targets if r['symbol'] not in allowed)
        if mode == 'CASH':
            assert all(r['target_weight'] == 0 for r in targets)
        else:
            assert all(r['target_weight'] >= 0 if mode == 'LONG_ONLY' else r['target_weight'] <= 0
                       for r in targets)
        prefix = deepcopy(bridge.snapshot())
        assert prefix['direction_mode'] == mode and bridge.meta()['direction_mode'] == mode
        future = deepcopy(frames)
        future['BTCUSDT'][-1, 0] += HOUR4 / 1000
        future['BTCUSDT'][-1, 1:5] = (100000., 100000., 100001., 99999.)
        with pytest.raises(ValueError):
            bridge.on_bar_close(FIRST, future, np.zeros((30, 2)), FIRST,
                                availability_us_by_symbol=available(future))
        assert bridge.snapshot() == prefix and bridge.targets_frame().to_dicts() == targets
        for order in orders:
            execute(order, FIRST + MINUTE)
        if mode == 'CASH':
            assert account.trades == [] and not any(bridge.pending.values()) and not any(bridge.stops.values())
            restored_account = Account.from_snapshot(account.snapshot())
            with pytest.raises(ValueError):
                mask.TurtlePerpetualBridge.from_snapshot(restored_account, prefix, mode='LONG_ONLY')
            bridge = mask.TurtlePerpetualBridge.from_snapshot(restored_account, prefix, mode=mode)
            account = restored_account
            assert bridge.snapshot() == prefix and bridge.direction_mode == mode
            check()
            results.append(dict(mode=mode, trades=0, maximum_wallet_error_USDT=str(maximum)))
            continue

        # First full minute AFTER the entry stop is armed, never its unknown
        # intraminute path. Gap execution uses the real next eligible quote.
        stop_time = FIRST + 3 * MINUTE
        observe(stop_time, {'BTCUSDT': 70, 'ETHUSDT': 130})
        bridge.observe_stop(stop_time, {s: dict(open_us=stop_time - MINUTE,
            available_us=stop_time, high=('110' if s == 'BTCUSDT' else '170'),
            low=('40' if s == 'BTCUSDT' else '90')) for s in SYMBOLS})
        assert bridge.due_orders(stop_time, prices) == []
        observe(stop_time + MINUTE, {'BTCUSDT': 45, 'ETHUSDT': 160})
        stop_orders = bridge.due_orders(stop_time + MINUTE, prices)
        assert len(stop_orders) == 1 and stop_orders[0]['kind'] == 'STOP' and stop_orders[0]['reduce_only']
        stop = stop_orders[0]; symbol = stop['symbol']
        assert stop['side'] != allowed[symbol]  # Forbidden ENTRY side must remain a legal protective CLOSE.
        partial, call = execute(stop, stop_time + MINUTE, abs(hands[symbol].quantity) / 2)
        assert partial['status'] == 'PARTIAL' and hands[symbol].quantity != 0
        snapshot = deepcopy(bridge.snapshot())
        restored_account = Account.from_snapshot(account.snapshot())
        bad_mode = 'SHORT_ONLY' if mode == 'LONG_ONLY' else 'LONG_ONLY'
        with pytest.raises(ValueError):
            mask.TurtlePerpetualBridge.from_snapshot(restored_account, snapshot, mode=bad_mode)
        # Editing the outer label cannot reclassify the original inner source
        # receipt or historical ENTRY as another permitted direction.
        relabeled = deepcopy(snapshot)
        relabeled['direction_mode'] = bad_mode
        with pytest.raises(ValueError):
            mask.TurtlePerpetualBridge.from_snapshot(restored_account, relabeled, mode=bad_mode)
        account = restored_account
        bridge = mask.TurtlePerpetualBridge.from_snapshot(account, snapshot, mode=mode)
        assert bridge.snapshot() == snapshot
        before_replay = deepcopy(bridge.snapshot())
        repeated = account.execute_fill(**call)
        assert repeated == partial and bridge.on_fill(stop['id'], repeated)['replayed']
        assert bridge.note_attempt(stop['id'], call['event_us'], repeated)['replayed']
        assert bridge.snapshot() == before_replay
        check()
        observe(stop_time + 2 * MINUTE, prices)
        remaining = bridge.due_orders(stop_time + 2 * MINUTE, prices)
        assert len(remaining) == 1 and remaining[0]['reduce_only'] and remaining[0]['kind'] == 'STOP'
        execute(remaining[0], stop_time + 2 * MINUTE)
        assert all(p.quantity == 0 for p in account.positions.values())
        assert not any(bridge.pending.values()) and not any(bridge.stops.values())
        assert sum(c['name'] == 'on_stop_loss' for c in bridge.callbacks.values()) == 1
        check()
        results.append(dict(mode=mode, trades=len(account.trades), final_summary=account.summary(),
                            maximum_wallet_error_USDT=str(maximum), restored_mode_identity_preserved=True))

    for path, digest in PINS.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
    (tmp_path / 'turtle_direction_mask_evidence.json').write_text(json.dumps(dict(
        scope='ONE_SYNTHETIC_DIRECTION_MASK_STOP_RESTORE_PATH_NOT_NEW_MARKET_OR_NATIVE_FILTER_PROOF',
        mask_source_sha256=MASK_SHA, unchanged_source_hashes=PINS, cases=results,
        forbid_direction_is_not_opposite_signal=True, quantity_profile_certified=False,
        market_arrays_read=False, old_suite_replayed=False, orders_sent=0), indent=2, sort_keys=True), encoding='utf-8')
