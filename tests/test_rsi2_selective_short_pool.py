"""One fixture for original selective RSI2 hooks and real short settlement."""
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import polars as pl
import pytest

from scripts.investment import multi_asset_financial_audit as independent
from scripts.investment import perpetual_closing_exempt_account as account_module
from scripts.investment import public_rsi2_adapter as original
from scripts.investment import public_sma_perpetual as shared
from scripts.investment import rsi2_daily_pool_target as target


def test_selective_rsi2_short_original_hooks_shared_risk_and_wallet(tmp_path):
    assert tmp_path.resolve().is_relative_to(Path('/home/xflops/coin-state').resolve())
    symbols = ('ETHUSDT', 'BTCUSDT', 'SOLUSDT')
    day, minute = shared.DAY_US, 60_000_000
    # Genuine kernel paths: oversold above the trend, overbought below the
    # trend, and a falling non-overbought asset that must never become short.
    prices = {
        symbols[0]: np.asarray([50.] * 230 + [500.] * 6 + [100.] * 5 +
                               [101., 100., 100., 999.]),
        symbols[1]: np.asarray([400.] * 230 + [50.] * 6 + [300.] * 5 +
                               [299.9, 300., 300., 777.]),
        symbols[2]: np.asarray([100.] * 239 + [50.] * 5 + [777.]),
    }
    frames = []
    for symbol in symbols:
        close = prices[symbol]
        opened = np.arange(len(close), dtype=np.int64) * day
        frames.append(pl.DataFrame(dict(symbol=[symbol] * len(close), open_us=opened,
            close_us=opened+day, available_us=opened+day, open=close,
            high=close+.1, low=close-.1, close=close, volume=np.ones(len(close)))))
    bars = pl.concat(frames)
    decisions = np.arange(240, 245, dtype=np.int64) * day
    long_states = np.asarray([[1, 0, 0], [1, 0, 0], [0, 0, 0], [1, 0, 0], [1, 0, 0]])
    short_states = np.asarray([[0, -1, 0], [0, -1, 0], [0, 0, 0], [0, -1, 0], [0, -1, 0]])
    expected_states = dict(LONG_ONLY=long_states, SHORT_ONLY=short_states,
        LONG_SHORT=long_states+short_states, CASH=np.zeros_like(long_states))

    def checked_reference(input_bars, calendar, production, mode, membership=None):
        window = dict(start=int(calendar[0]), end=int(calendar[-1])+day,
            bars={s: input_bars.filter(pl.col('symbol') == s).sort('close_us') for s in symbols},
            eligible_by_decision=membership)
        reference = independent.target_reference(window, symbols, 'EQUAL',
            strategy_id=target.STRATEGY_ID, mode=mode)
        exact = ['available_us', 'symbol', 'mode', 'eligibility_reason']
        assert reference.select(exact).equals(production.select(exact))
        assert np.allclose(reference.select('target_weight', 'raw_signed_target').to_numpy(),
            production.select('target_weight', 'raw_signed_target').to_numpy(), rtol=0, atol=1e-13)
        return window

    results, metadata, reference_windows = {}, {}, {}
    for mode in target.MODES:
        results[mode], metadata[mode] = target.fixed_targets(bars, decisions, mode, symbols=symbols)
        reference_windows[mode] = checked_reference(bars, decisions, results[mode], mode)
        assert metadata[mode]['rules'] == target.rules_for_mode(mode)
        assert metadata[mode]['mode'] == mode and metadata[mode]['symbols'] == list(symbols)
        assert metadata[mode]['complete_daily_warmup'] == 240
        assert metadata[mode]['rsi_parameters'] == target.PARAMETERS
        for row, decision in enumerate(decisions):
            index = int(decision//day)-1
            raw = expected_states[mode][row] * (.6/len(symbols))
            past = np.column_stack([np.diff(prices[s][index-30:index+1]) /
                prices[s][index-30:index] for s in symbols])
            centered = past-past.mean(axis=0)
            covariance = centered.T@centered/29*365
            sigma = math.sqrt(max(float(raw@covariance@raw), 0.))
            expected = raw*min(1., .10/sigma) if sigma else raw
            rows = results[mode].filter(pl.col('available_us') == decision)
            assert rows['symbol'].to_list() == list(symbols)
            assert np.allclose(rows['raw_signed_target'].to_numpy(), raw, rtol=0, atol=1e-13)
            assert np.allclose(rows['target_weight'].to_numpy(), expected, rtol=0, atol=1e-13)
            assert np.abs(rows['target_weight'].to_numpy()).sum() <= .6
            assert np.abs(rows['target_weight'].to_numpy()).max() <= .3
            assert metadata[mode]['risk'][row]['covariance_symbol_order'] == list(symbols)
    first = results['LONG_SHORT'].filter(pl.col('available_us') == decisions[0])
    assert first['raw_signed_target'].to_list() == [.6/3, -.6/3, 0.]
    assert float(first['raw_signed_target'].sum()) == 0.
    assert 0 < float(first['target_weight'].abs().sum()) < .4
    assert metadata['LONG_SHORT']['risk'][0]['unscaled_signed_covariance_annual_vol'] > .10
    assert metadata['LONG_SHORT']['original_long_and_short_and_exit_hooks_reused']
    assert metadata['SHORT_ONLY']['original_short_entry_and_short_exit_hooks_reused']
    assert not metadata['SHORT_ONLY']['original_long_entry_and_long_exit_hooks_reused']
    assert not metadata['SHORT_ONLY']['original_whole_balance_order_hooks_called']
    assert 'original_short_and_whole_balance_order_hooks_called' not in metadata['SHORT_ONLY']

    # State independently advances by invoking the actual unmodified class
    # hooks. Opposite trend alone is not a short entry; neither direction
    # reenters on the same completed stamp that called liquidate.
    Rules = original._load_public_hooks()
    raw_hook_witnesses = []
    for asset_index, symbol in enumerate(symbols):
        hook, state = Rules(), 0
        for row, decision in enumerate(decisions):
            index = int(decision//day)-1
            values = prices[symbol][index-239:index+1]
            opened_ms = np.arange(index-239, index+1) * (day//1000)
            hook.candles = np.column_stack((opened_ms, values, values,
                values+.1, values-.1, np.ones(len(values))))
            hook.price = float(values[-1])
            hook.is_long, hook.is_short = state == 1, state == -1
            exits = []
            hook.liquidate = lambda: exits.append(True)
            can_long, can_short = bool(hook.should_long()), bool(hook.should_short())
            if state:
                hook.update_position()
                if exits:
                    state = 0
            elif can_long:
                state = 1
            elif can_short:
                state = -1
            assert state == expected_states['LONG_SHORT'][row, asset_index]
            raw_hook_witnesses.append(dict(symbol=symbol, decision_us=int(decision),
                price=hook.price, fast_SMA=float(hook.fast_sma), slow_SMA=float(hook.slow_sma),
                RSI2=float(hook.rsi), should_long=can_long, should_short=can_short,
                exit_called=bool(exits), state_after=state))
            if asset_index == 1 and row == 1:
                assert hook.price == hook.fast_sma == 300. and state == -1 and not exits
            if asset_index == 1 and row == 2:
                assert hook.rsi >= 90 and can_short and exits and state == 0
            if asset_index == 0 and row == 2:
                assert hook.rsi <= 10 and can_long and exits and state == 0
            if asset_index == 2:
                assert hook.price < hook.slow_sma and not can_long and not can_short and state == 0
    # Exact predicate thresholds use the real original method with explicit
    # scalar inputs, alongside the genuine-kernel state chain above.
    edge = SimpleNamespace(price=99., slow_sma=100., rsi=90., vars=dict(target.PARAMETERS))
    assert Rules.should_short(edge)
    edge.rsi = np.nextafter(90., -np.inf)
    assert not Rules.should_short(edge)
    edge.rsi, edge.price = 90., 100.
    assert not Rules.should_short(edge)  # Trend equality blocks entry.
    edge.price, edge.rsi = 101., 10.
    assert Rules.should_long(edge)
    edge.rsi = np.nextafter(10., np.inf)
    assert not Rules.should_long(edge)
    edge.price, edge.fast_sma, edge.is_short, edge.is_long = 100., 100., True, False
    edge_exits = []
    edge.liquidate = lambda: edge_exits.append(True)
    Rules.update_position(edge)
    assert not edge_exits  # Both exact trend and exit inequalities have no band.

    reordered, reordered_meta = target.fixed_targets(bars.reverse(), decisions, 'LONG_SHORT',
        symbols=symbols[::-1])
    left = results['LONG_SHORT'].sort(['available_us', 'symbol'])
    right = reordered.sort(['available_us', 'symbol'])
    assert left.select('available_us', 'symbol', 'mode', 'eligibility_reason').equals(
        right.select('available_us', 'symbol', 'mode', 'eligibility_reason'))
    assert np.allclose(left.select('target_weight', 'raw_signed_target').to_numpy(),
        right.select('target_weight', 'raw_signed_target').to_numpy(), rtol=0, atol=1e-13)
    assert reordered_meta['symbols'] == list(symbols[::-1])
    future = bars.with_columns([pl.when(pl.col('close_us') > decisions[1])
        .then(pl.col(c)*1000).otherwise(pl.col(c)).alias(c) for c in ('open', 'high', 'low', 'close')])
    prefix, prefix_meta = target.fixed_targets(future, decisions[:2], 'LONG_SHORT', symbols=symbols)
    assert prefix.equals(results['LONG_SHORT'].filter(pl.col('available_us') <= decisions[1]))
    assert prefix_meta['risk'] == metadata['LONG_SHORT']['risk'][:2]
    checked_reference(future, decisions[:2], prefix, 'LONG_SHORT')

    short = bars.filter(pl.col('close_us') < decisions[0])
    missing = bars.filter(~((pl.col('symbol') == symbols[1]) & (pl.col('close_us') == day)))
    delayed = bars.with_columns(pl.when((pl.col('symbol') == symbols[1]) & (pl.col('close_us') == day))
        .then(pl.lit(int(decisions[0])+1)).otherwise(pl.col('available_us')).alias('available_us'))
    for bad in (short, missing, delayed):
        rows, _ = target.fixed_targets(bad, decisions[:1], 'SHORT_ONLY', symbols=symbols)
        btc = rows.filter(pl.col('symbol') == symbols[1])
        assert btc['target_weight'][0] == btc['raw_signed_target'][0] == 0.
        assert btc['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP'
        checked_reference(bad, decisions[:1], rows, 'SHORT_ONLY')
    gap = bars.filter(~((pl.col('symbol') == symbols[1]) & (pl.col('close_us') == decisions[1])))
    gapped, _ = target.fixed_targets(gap, decisions[:3], 'LONG_SHORT', symbols=symbols)
    assert gapped.filter(pl.col('available_us') == decisions[0]).equals(first)
    assert gapped.filter((pl.col('symbol') == symbols[1]) &
        (pl.col('available_us') >= decisions[1]))['raw_signed_target'].eq(0.).all()
    checked_reference(gap, decisions[:3], gapped, 'LONG_SHORT')
    membership = {int(d): symbols if row != 1 else (symbols[0], symbols[2])
                  for row, d in enumerate(decisions[:3])}
    exited, _ = target.fixed_targets(bars, decisions[:3], 'LONG_SHORT', symbols=symbols,
        eligible_by_decision=membership)
    removed = exited.filter((pl.col('available_us') == decisions[1]) & (pl.col('symbol') == symbols[1]))
    assert removed['raw_signed_target'][0] == 0. and removed['eligibility_reason'][0] == 'POOL_EXIT'
    restored = exited.filter((pl.col('available_us') == decisions[2]) & (pl.col('symbol') == symbols[1]))
    assert restored['raw_signed_target'][0] == -.6/3  # Reset state, not stale held-short exit.
    checked_reference(bars, decisions[:3], exited, 'LONG_SHORT', membership)
    with pytest.raises(ValueError, match='UTC daily'):
        target.fixed_targets(bars, decisions+1, 'LONG_SHORT', symbols=symbols)
    with pytest.raises(ValueError, match='equal'):
        target.fixed_targets(bars, decisions, 'LONG_SHORT', symbols=symbols, allocation='INVERSE_VOL_30D')
    with pytest.raises(ValueError, match='direction'):
        target.fixed_targets(bars, decisions, 'UNKNOWN', symbols=symbols)

    # The original default adapter is loaded from its exact accepted Git
    # revision in STATE; comparing two new paths alone is insufficient.
    old_source = subprocess.check_output(['git', 'show',
        '61316ff1865437b8cc7a286e0e2aad95bdc67340:scripts/investment/rsi2_daily_pool_target.py'],
        cwd=shared.public.ROOT)
    old_sha = hashlib.sha256(old_source).hexdigest()
    assert old_sha == '6e9aa37dad81f754543653acdfccbc75aa96750afff55e817e654debce10bd79'
    old_path = tmp_path/'accepted_long_rsi2_adapter.py'
    old_path.write_bytes(old_source)
    old_spec = importlib.util.spec_from_file_location('d059_accepted_long_adapter', old_path)
    old_adapter = importlib.util.module_from_spec(old_spec)
    old_spec.loader.exec_module(old_adapter)
    old_long, old_meta = old_adapter.fixed_targets(bars, decisions, symbols=symbols)
    default, default_meta = target.fixed_targets(bars, decisions, symbols=symbols)
    assert old_long.equals(default) and old_meta == default_meta == metadata['LONG_ONLY']
    assert target.RULES == old_adapter.RULES and target.PARAMETERS == old_adapter.PARAMETERS

    # Real SHORT_ONLY output routes to SELL, actual isolated margin and the
    # shared USDT wallet. HandLedger never imports producer finance. The
    # synthetic funding fractions do not certify any historical source unit.
    reference_path = shared.public.ROOT/'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py'
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest() == (
        '3600a29fe6d4fac13e7b34fd1d2a31f922b8bb4f9e2c1649950ebe6029b5e81a')
    spec = importlib.util.spec_from_file_location('d059_hand_reference', reference_path)
    reference = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = reference
    spec.loader.exec_module(reference)
    D = Decimal
    account = account_module.USDTLinearPerpetualAccount(symbols=symbols)
    hand = reference.HandLedger(D('10000'))
    selected = results['SHORT_ONLY'].filter((pl.col('available_us') == decisions[0]) &
        (pl.col('symbol') == symbols[1]))['target_weight'][0]
    assert selected < 0
    quantity = (D(str(abs(selected)))*D('10000')/D('100')/D('0.00000001')).to_integral_value(
        rounding=ROUND_DOWN)*D('0.00000001')
    assert quantity*D('99.92') >= 10
    signal, exit_signal = int(decisions[0]), int(decisions[2])

    def observe(stamp, btc_mark):
        account.update_marks(stamp, {s: dict(price=btc_mark if s == symbols[1] else '100',
            close_us=stamp, available_us=stamp) for s in symbols})

    observe(signal-minute, '99')
    unowned = account.apply_funding(symbols[1], 'fresh-flat', signal, '.001', signal)
    assert unowned['owned'] is False and unowned['signed_funding_USDT'] == 0.
    opened = account.execute_fill(symbols[1], 'SELL', quantity, signal+minute+1,
        signal, 'selective-short-entry', execution_mid_price='100', quote_available_us=signal+minute)
    assert opened['status'] == 'FILLED' and opened['fills'][0]['leg'] == 'OPEN'
    hand.fill(-quantity, '99.92', '.00055')
    assert account.positions[symbols[1]].quantity == -quantity
    assert account.positions[symbols[1]].isolated_balance == quantity*D('99.92')
    wallet = account.free_cash+sum(p.isolated_balance for p in account.positions.values())
    assert wallet == hand.wallet < 10000  # No short-sale principal credited.
    bridge_errors = [abs(account.nav()-hand.equity('99'))]
    observe(int(decisions[1])-minute, '90')
    positive = account.apply_funding(symbols[1], 'owned-positive', int(decisions[1]), '.001', int(decisions[1]))
    hand.funding('90', '.001', rate_unit='EXPLICIT_SYNTHETIC_FRACTION', signed_quantity_before_event=-quantity)
    assert positive['owned'] and positive['decimal_strings']['signed_funding_USDT'] == str(quantity*D('90')*D('.001'))
    before_duplicate = account.snapshot()
    assert account.apply_funding(symbols[1], 'owned-positive', int(decisions[1]), '.001', int(decisions[1])) == positive
    assert account.snapshot() == before_duplicate
    observe(exit_signal-minute, '90')
    negative = account.apply_funding(symbols[1], 'owned-negative-rate', exit_signal, '-.002', exit_signal)
    hand.funding('90', '-.002', rate_unit='EXPLICIT_SYNTHETIC_FRACTION', signed_quantity_before_event=-quantity)
    assert positive['signed_funding_USDT'] > 0. and negative['signed_funding_USDT'] < 0.
    assert negative['owned'] and negative['mark_close_us'] < exit_signal
    closing_target = results['SHORT_ONLY'].filter((pl.col('available_us') == exit_signal) &
        (pl.col('symbol') == symbols[1]))['target_weight'][0]
    assert closing_target == 0.
    closed = account.execute_fill(symbols[1], 'BUY', quantity, exit_signal+minute+1,
        exit_signal, 'selective-short-exit', execution_mid_price='90', quote_available_us=exit_signal+minute,
        reduce_only=True)
    assert closed['status'] == 'FILLED' and closed['fills'][0]['leg'] == 'CLOSE'
    hand.fill(quantity, '90.072', '.00055')
    bridge_errors.extend([abs(account.nav()-hand.equity('90')), abs(account.free_cash-hand.wallet),
        abs(account.fees-hand.fees), abs(account.funding_cash-hand.funding_cash),
        abs(account.realized_PnL-hand.realized)])
    summary = account.summary()
    assert max(bridge_errors) <= D('1e-20') and hand.bridge('10000', '90') == 0
    assert all(p.quantity == p.isolated_balance == 0 for p in account.positions.values())
    assert account.unpaid_liability == 0 and summary['account_status'] == 'ACTIVE'
    assert D(summary['decimal_strings']['gross_PnL_same_quantities']) == quantity*D('10')
    assert account.execution_cost == quantity*D('.152')
    assert all(t['decimal_strings']['fee_amount'] == t['decimal_strings']['fee_USDT_mid'] for t in account.trades)
    assert len(account.trades) == 2 and account.trades[0]['side'] == 'SELL' and account.trades[1]['side'] == 'BUY'
    (tmp_path/'rsi2_selective_short_evidence.json').write_text(json.dumps(dict(
        strategy_id=target.STRATEGY_ID, modes=list(target.MODES), rules=target.rules_for_mode('LONG_SHORT'),
        target_rows={m: f.to_dicts() for m, f in results.items()}, raw_hook_witnesses=raw_hook_witnesses,
        independent_state_witnesses={m: w['independent_RSI2_state_witnesses'] for m, w in reference_windows.items()},
        accepted_long_source_sha256=old_sha, default_LONG_ONLY_exact=True,
        account_trades=account.trades, account_funding=account.funding, account_summary=summary,
        funding_unit='EXPLICIT_SYNTHETIC_FRACTION_NOT_SOURCE_CERTIFICATION',
        maximum_hand_bridge_error=str(max(bridge_errors)), hand_final_wallet=str(hand.wallet)),
        allow_nan=False), encoding='utf-8')
