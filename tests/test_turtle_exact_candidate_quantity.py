"""UNRUN one genuine risk-identity regression; no market or old suite replay.

Requires the separately reviewed D061 quantity-identity patch to be applied
normally after D060 closes. Official hooks/indicators and the shared account
remain real; fixed synthetic marks reproduce the saved roundtrip counterexample.
"""
from copy import deepcopy
from decimal import Decimal as D, localcontext
import json
from pathlib import Path

import numpy as np
import pytest

from scripts.investment import turtle_direction_mask as mask
from scripts.investment import turtle_perpetual_bridge as bridge_module
from scripts.investment import perpetual_closing_exempt_account as closing

BAR, MINUTE, DAY = bridge_module.BAR_US, bridge_module.MINUTE_US, bridge_module.DAY_US
FIRST = 1_748_736_000_000_000
SYMBOLS = ('SOLUSDT', 'BTCUSDT', 'ETHUSDT')
PRICE = {'SOLUSDT': D(100), 'BTCUSDT': D('69566.1'), 'ETHUSDT': D(100)}
Q = D('0.03836633')


def test_identity_risk_preserves_exact_quantity_and_real_scaled_reductions(tmp_path):
    assert tmp_path.resolve().is_relative_to(Path('/home/xflops/coin-state').resolve())

    def bars(stamp, *, exiting=False):
        opens = np.arange(stamp - 240 * BAR, stamp, BAR, dtype=np.int64)
        frames = {}
        for s in SYMBOLS:
            price = float(PRICE[s])
            width = 1250. if s == 'BTCUSDT' else 20.
            v = np.column_stack((opens / 1000, np.full(240, price), np.full(240, price),
                np.full(240, price + width), np.full(240, price - width), np.full(240, 1000.)))
            v[-1, 3:5] = [price + width * .95, price - width * .95]
            if s == 'BTCUSDT':
                v[-1, 3:5] = ([price + 1200., price - 1300.] if exiting
                    else [price + 1300., price - 1200.])
            frames[s] = v
        return frames

    def onbar(bridge, stamp, returns, *, exiting=False):
        frames = bars(stamp, exiting=exiting)
        return bridge.on_bar_close(stamp, frames, returns, stamp // DAY * DAY,
            availability_us_by_symbol={s: v[:, 0].astype(np.int64) * 1000 + BAR
                for s, v in frames.items()})

    account = closing.USDTLinearPerpetualAccount(symbols=SYMBOLS)
    account.update_marks(FIRST, {s: dict(price=PRICE[s], close_us=FIRST, available_us=FIRST) for s in SYMBOLS})
    bridge = mask.TurtlePerpetualBridge(account, 'LONG_ONLY', allow_pyramiding=False)
    onbar(bridge, FIRST, np.zeros((30, 3)))
    assert bridge.due_orders(FIRST, PRICE) == []

    def execute(bridge, order, opening, capacity):
        old_q = bridge.account.positions[order['symbol']].quantity
        old_fees = bridge.account.fees
        receipt = bridge.account.execute_fill(order['symbol'], order['side'], order['quantity'],
            opening + 1, order['signal_us'], order['id'] + ':' + str(order['attempts']),
            execution_mid_price=PRICE[order['symbol']], quote_available_us=opening,
            available_quantity=capacity, reduce_only=order['reduce_only'])
        bridge.on_fill(order['id'], receipt)
        bridge.note_attempt(order['id'], opening + 1, receipt)
        qty = sum((D(r['decimal_strings']['quantity']) for r in receipt['fills']), D(0))
        if qty:
            direction = D(1) if order['side'] == 'BUY' else D(-1)
            price = PRICE[order['symbol']] * (1 + direction * D('.0008'))
            assert bridge.account.positions[order['symbol']].quantity == old_q + direction * qty
            assert abs(bridge.account.fees - old_fees - qty * price * D('.00055')) <= D('1e-7')
        return receipt

    # Only BTC's genuine official long entry is allowed. A real partial fill
    # commits exactly one level; zero subsequent capacity expires its remainder.
    for attempt in range(1, 6):
        due = bridge.due_orders(FIRST + attempt * MINUTE, PRICE)
        assert len(due) == 1 and due[0]['symbol'] == 'BTCUSDT' and due[0]['kind'] == 'ENTRY'
        if attempt == 1:
            assert due[0]['quantity'] > Q
        execute(bridge, due[0], FIRST + attempt * MINUTE, Q if attempt == 1 else 0)
    assert account.positions['BTCUSDT'].quantity == Q
    assert all(account.positions[s].quantity == 0 for s in ('SOLUSDT', 'ETHUSDT'))
    assert not any(bridge.pending.values())
    assert bridge.rules['BTCUSDT'].current_pyramiding_levels == 1

    # Reproduce the recorded same-weight arithmetic with an explicit synthetic
    # mark observation, rather than changing cash, q, account NAV or strategy.
    # This fixture is not a source-data or historical-price reconstruction.
    with localcontext() as ctx:
        ctx.prec = 40
        recorded_bounded = D('0.03798266669999999880125099414') / D('.99')
        wanted_nav = recorded_bounded * PRICE['BTCUSDT'] / D('0.2710775954910411')
        wallet = account.free_cash + sum((p.isolated_balance for p in account.positions.values()), D(0))
        mark = account.positions['BTCUSDT'].entry_price + (wanted_nav - wallet) / Q
    observed = FIRST + 10 * MINUTE
    account.update_marks(observed, {s: dict(price=mark if s == 'BTCUSDT' else PRICE[s],
        close_us=observed, available_us=observed) for s in SYMBOLS})
    signal = FIRST + BAR
    q_before, fees_before, trade_count = Q, account.fees, len(account.trades)
    stop_before = deepcopy(bridge.stops['BTCUSDT'])
    with localcontext() as ctx:
        ctx.prec = 28  # The existing bridge's outer Decimal arithmetic context.
        raw = float(Q * PRICE['BTCUSDT'] / account.nav())
        old_bounded = D(str(raw)) * account.nav() / PRICE['BTCUSDT']
    assert old_bounded < Q, 'Fixed counterexample must actually witness the old false reduction'
    assert raw < .3 and account.status == 'ACTIVE'
    unchanged = onbar(bridge, signal, np.zeros((30, 3)))
    row = bridge.targets_frame().filter(bridge_module.pl.col('symbol') == 'BTCUSDT').to_dicts()[-1]
    assert row['target_weight'] == row['raw_signed_target']
    assert unchanged['unscaled_signed_covariance_annual_vol'] == 0
    assert bridge.due_orders(signal + MINUTE, PRICE) == []
    assert not any(bridge.pending.values()) and not any(i['kind'] == 'RISK_REDUCTION' for i in bridge.intents.values())
    assert account.positions['BTCUSDT'].quantity == q_before
    assert account.fees == fees_before and len(account.trades) == trade_count
    assert bridge.stops['BTCUSDT'] == stop_before

    # Poisoned late/extra history cannot change this already accepted prefix.
    prefix = bridge.snapshot()
    late = {s: v[:, 0].astype(np.int64) * 1000 + BAR for s, v in bars(signal).items()}
    late['BTCUSDT'][-1] += 1
    with pytest.raises(ValueError):
        bridge.on_bar_close(signal, bars(signal), np.zeros((30, 3)), FIRST,
            availability_us_by_symbol=late)
    future = {s: np.vstack((v, [signal / 1000, 999., 999., 1000., 998., 1.]))
        for s, v in bars(signal).items()}
    with pytest.raises(ValueError):
        bridge.on_bar_close(signal, future, np.zeros((30, 3)), FIRST)
    assert bridge.snapshot() == prefix

    # Same ordered input with true covariance scale<1 must still request and
    # pay for the original .99-buffered, reduce-only product-legal reduction.
    alternating = np.where(np.arange(30) % 2, .08, -.08)
    returns = np.column_stack((np.zeros(30), alternating, -alternating / 3))
    scaled_time = signal + BAR
    outcome = onbar(bridge, scaled_time, returns)
    values = bridge.targets_frame().filter(bridge_module.pl.col('available_us') == scaled_time).to_dicts()
    assert [r['symbol'] for r in values] == list(SYMBOLS)
    raw_vec = np.asarray([r['raw_signed_target'] for r in values])
    centered = returns - returns.mean(axis=0)
    covariance = centered.T @ centered / 29 * 365
    sigma = float(np.sqrt(raw_vec @ covariance @ raw_vec))
    assert sigma > .1
    np.testing.assert_allclose([r['target_weight'] for r in values], raw_vec * (.1 / sigma), atol=1e-12, rtol=0)
    assert outcome['covariance_assets'] == 3
    due = bridge.due_orders(scaled_time + MINUTE, PRICE)
    assert len(due) == 1 and due[0]['symbol'] == 'BTCUSDT'
    assert due[0]['kind'] == 'RISK_REDUCTION' and due[0]['reduce_only'] and due[0]['side'] == 'SELL'
    target = D(bridge.intents[due[0]['id']]['target_quantity'])
    assert 0 < target < Q
    fee0 = account.fees
    execute(bridge, due[0], scaled_time + MINUTE, due[0]['quantity'])
    assert 0 < account.positions['BTCUSDT'].quantity <= target
    assert account.fees > fee0 and not any(bridge.pending.values())

    # Branch from the genuinely restored inventory. Original raw EXIT still
    # submits; a simultaneous active STOP wins, with real next-minute fills.
    account_saved, bridge_saved = account.snapshot(), bridge.snapshot()
    assert bridge_module.VERSION == 'TURTLE_ORDERED_FILL_BRIDGE_V3_EXACT_CANDIDATE'
    legacy_mapping = deepcopy(bridge_saved)
    legacy_mapping['bridge']['version'] = 'TURTLE_ORDERED_FILL_BRIDGE_V2'
    with pytest.raises(ValueError):
        mask.TurtlePerpetualBridge.from_snapshot(account, legacy_mapping,
            mode='LONG_ONLY', allow_pyramiding=False)
    exited_account = closing.USDTLinearPerpetualAccount.from_snapshot(account_saved, expected_symbols=SYMBOLS)
    exited = mask.TurtlePerpetualBridge.from_snapshot(exited_account, bridge_saved,
        mode='LONG_ONLY', allow_pyramiding=False)
    exit_time = scaled_time + BAR
    onbar(exited, exit_time, np.zeros((30, 3)), exiting=True)
    exit_order = exited.due_orders(exit_time + MINUTE, PRICE)
    assert len(exit_order) == 1 and exit_order[0]['kind'] == 'EXIT' and exit_order[0]['reduce_only']
    execute(exited, exit_order[0], exit_time + MINUTE, exit_order[0]['quantity'])
    assert exited_account.positions['BTCUSDT'].quantity == 0
    stopped_account = closing.USDTLinearPerpetualAccount.from_snapshot(account_saved, expected_symbols=SYMBOLS)
    stopped = mask.TurtlePerpetualBridge.from_snapshot(stopped_account, bridge_saved,
        mode='LONG_ONLY', allow_pyramiding=False)
    stopped.observe_stop(exit_time, {s: dict(open_us=exit_time - MINUTE, available_us=exit_time,
        high=float(PRICE[s]) + 2000 if s == 'BTCUSDT' else 120,
        low=float(PRICE[s]) - 10000 if s == 'BTCUSDT' else 80) for s in SYMBOLS})
    pending = deepcopy(stopped.pending)
    onbar(stopped, exit_time, np.zeros((30, 3)), exiting=True)
    assert stopped.pending == pending and stopped.intents[pending['BTCUSDT']]['kind'] == 'STOP'
    assert stopped.due_orders(exit_time, PRICE) == []
    stop_order = stopped.due_orders(exit_time + MINUTE, PRICE)
    assert len(stop_order) == 1 and stop_order[0]['kind'] == 'STOP' and stop_order[0]['reduce_only']
    execute(stopped, stop_order[0], exit_time + MINUTE, stop_order[0]['quantity'])
    assert stopped_account.positions['BTCUSDT'].quantity == 0 and not any(stopped.stops.values())
    (tmp_path / 'exact_candidate_quantity_evidence.json').write_text(json.dumps(dict(
        scope='FIXED_SYNTHETIC_CORRECTNESS_COUNTEREXAMPLE_NOT_NEW_MARKET_RESULT',
        q=str(Q), old_bounded=str(old_bounded), shortfall=str(Q - old_bounded),
        unscaled=unchanged, true_scaled=outcome, scaled_summary=account.summary(),
        exit_summary=exited_account.summary(), stop_summary=stopped_account.summary()),
        indent=2, allow_nan=False) + '\n')
