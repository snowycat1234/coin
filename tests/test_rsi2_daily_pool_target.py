"""One real-hook fixture for daily RSI2 context, state and shared risk routing."""
import math
import hashlib
import importlib.util
import subprocess

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_rsi2_adapter as original
from scripts.investment import public_sma_perpetual as shared
from scripts.investment import rsi2_daily_pool_target as target
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import multi_asset_financial_audit as independent


def test_rsi2_daily_original_hooks_240_context_state_and_shared_risk(tmp_path):
    symbols = ('ZZZUSDT', 'AAAUSDT', 'MMMUSDT')
    day = shared.DAY_US
    # A large gain followed by five completed flat bars and a pullback makes
    # RSI genuinely oversold while price remains above the slow trend SMA.
    # The rebound is above SMA5 yet still oversold: exit and entry would both
    # be true on that same bar without the shared held-exit-first policy.
    active = np.asarray([50.] * 230 + [500.] * 6 + [100.] * 5 + [101., 100., 100., 999.])
    prices = {symbols[0]: active, symbols[1]: np.full(len(active), 100.),
        symbols[2]: np.asarray([200.] * 205 + list(np.linspace(50., 70., len(active)-205)))}
    frames = []
    for symbol in symbols:
        close = prices[symbol]
        opened = np.arange(len(close), dtype=np.int64) * day
        frames.append(pl.DataFrame(dict(symbol=[symbol] * len(close), open_us=opened,
            close_us=opened+day, available_us=opened+day, open=close,
            high=close+.1, low=close-.1, close=close, volume=np.ones(len(close)))))
    bars = pl.concat(frames)
    decisions = np.arange(240, 245, dtype=np.int64) * day

    def checked_reference(input_bars, calendar, production, membership=None):
        window = dict(start=int(calendar[0]), end=int(calendar[-1])+day,
            bars={s: input_bars.filter(pl.col('symbol') == s).sort('close_us') for s in symbols},
            eligible_by_decision=membership)
        reference = independent.target_reference(window, symbols, 'EQUAL', strategy_id=target.STRATEGY_ID)
        exact = ['available_us', 'symbol', 'mode', 'eligibility_reason']
        assert reference.select(exact).equals(production.select(exact))
        assert np.allclose(reference.select('target_weight', 'raw_signed_target').to_numpy(),
            production.select('target_weight', 'raw_signed_target').to_numpy(), rtol=0, atol=1e-13)
        return window

    result, meta = target.fixed_targets(bars, decisions, symbols=symbols)
    independent_window = checked_reference(bars, decisions, result)
    assert meta['strategy_id'] == target.STRATEGY_ID and meta['rules'] == target.RULES
    assert meta['symbols'] == list(symbols) and meta['rsi_parameters'] == target.PARAMETERS
    assert meta['complete_daily_warmup'] == meta['scalar_candle_window'] == 240
    assert meta['original_long_entry_and_long_exit_hooks_reused']
    assert not meta['original_long_and_short_and_exit_hooks_reused']
    assert not meta['original_short_and_whole_balance_order_hooks_called']
    assert not meta['native_Jesse_or_Bybit_execution_replicated']
    assert not meta['upstream_timeframe_prescribed']
    assert not {'fast_period', 'slow_period', 'equality_holds_current_position', 'source'} & meta.keys()

    rules = original._load_public_hooks()
    candles = lambda values: np.column_stack((np.arange(len(values)), values, values,
        values+.1, values-.1, np.ones(len(values))))
    expected_states = np.asarray([[1, 0, 0], [1, 0, 0], [0, 0, 0], [1, 0, 0], [1, 0, 0]])
    raw_hook_witnesses = []
    for asset_index, symbol in enumerate(symbols):
        hook, state = rules(), False
        for row, decision in enumerate(decisions):
            index = int(decision//day)-1
            hook.candles = candles(prices[symbol][index-239:index+1])
            hook.price = float(prices[symbol][index])
            hook.is_long, hook.is_short = state, False
            exits = []
            hook.liquidate = lambda: exits.append(True)
            can_enter, can_short = bool(hook.should_long()), bool(hook.should_short())
            if state:
                hook.update_position()
                if exits:
                    state = False
            elif can_enter:
                state = True
            assert state == bool(expected_states[row, asset_index])
            raw_hook_witnesses.append(dict(symbol=symbol, decision_us=int(decision),
                price=hook.price, fast_SMA=float(hook.fast_sma), slow_SMA=float(hook.slow_sma),
                RSI2=float(hook.rsi), should_long=can_enter, should_short=can_short,
                exit_called=bool(exits), held_after=state))
            if symbol == symbols[0] and row == 1:
                assert hook.price == hook.fast_sma == 100. and state and not exits
            if symbol == symbols[0] and row == 2:
                assert hook.rsi <= 10 and can_enter and exits and not state
            if symbol == symbols[1]:
                assert hook.price == hook.slow_sma and not can_enter and not state
            if symbol == symbols[2]:
                assert can_short and not can_enter and not state

    for row, decision in enumerate(decisions):
        index = int(decision//day)-1
        raw = expected_states[row] * (.6/len(symbols))
        past = np.column_stack([np.diff(prices[s][index-30:index+1]) /
            prices[s][index-30:index] for s in symbols])
        centered = past-past.mean(axis=0)
        covariance = centered.T@centered/29*365
        sigma = math.sqrt(max(float(raw@covariance@raw), 0.))
        expected = raw*min(1., .10/sigma) if sigma else raw
        rows = result.filter(pl.col('available_us') == decision)
        assert rows['symbol'].to_list() == list(symbols)
        assert np.allclose(rows['raw_signed_target'].to_numpy(), raw, rtol=0, atol=1e-13)
        assert np.allclose(rows['target_weight'].to_numpy(), expected, rtol=0, atol=1e-13)
        assert (rows['target_weight'] >= 0).all() and (rows['target_weight'] <= rows['raw_signed_target']).all()
        assert float(rows['target_weight'].sum()) <= .6 and float(rows['target_weight'].max()) <= .3
        assert meta['risk'][row]['covariance_symbol_order'] == list(symbols)
    first = result.filter(pl.col('available_us') == decisions[0])
    assert first['raw_signed_target'].to_list() == [.6/3, 0., 0.]
    assert 0 < first['target_weight'][0] < .2  # Actual downscaling, no inactive-budget redistribution.

    cash, cash_meta = target.fixed_targets(bars, decisions, symbols=symbols, mode='CASH')
    assert cash['target_weight'].eq(0.).all() and cash['raw_signed_target'].eq(0.).all()
    assert cash_meta['mode'] == 'CASH' and cash_meta['rules'] == target.RULES
    reordered, reordered_meta = target.fixed_targets(bars.reverse(), decisions, symbols=symbols[::-1])
    assert reordered_meta['symbols'] == list(symbols[::-1])
    left, right = result.sort(['available_us', 'symbol']), reordered.sort(['available_us', 'symbol'])
    assert left.select('available_us', 'symbol', 'mode', 'eligibility_reason').equals(
        right.select('available_us', 'symbol', 'mode', 'eligibility_reason'))
    assert np.allclose(left.select('target_weight', 'raw_signed_target').to_numpy(),
        right.select('target_weight', 'raw_signed_target').to_numpy(), rtol=0, atol=1e-13)
    future = bars.with_columns([pl.when(pl.col('close_us') > decisions[1]).then(pl.col(c)*1000)
        .otherwise(pl.col(c)).alias(c) for c in ('open', 'high', 'low', 'close')])
    prefix, prefix_meta = target.fixed_targets(future, decisions[:2], symbols=symbols)
    assert prefix.equals(result.filter(pl.col('available_us') <= decisions[1]))
    assert prefix_meta['risk'] == meta['risk'][:2]
    checked_reference(future, decisions[:2], prefix)

    # 239 complete bars cannot mature scalar240; a missing or delayed bar
    # anywhere in that window also fails closed, even outside the last200.
    short = bars.filter(pl.col('close_us') < decisions[0])
    missing = bars.filter(~((pl.col('symbol') == symbols[0]) & (pl.col('close_us') == day)))
    delayed = bars.with_columns(pl.when((pl.col('symbol') == symbols[0]) & (pl.col('close_us') == day))
        .then(pl.lit(int(decisions[0])+1)).otherwise(pl.col('available_us')).alias('available_us'))
    for bad in (short, missing, delayed):
        rows, _ = target.fixed_targets(bad, decisions[:1], symbols=symbols)
        assert rows['target_weight'].eq(0.).all() and rows['raw_signed_target'].eq(0.).all()
        assert rows['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP'
        checked_reference(bad, decisions[:1], rows)
    membership = {int(decisions[0]): symbols, int(decisions[1]): symbols[1:]}
    exited, _ = target.fixed_targets(bars, decisions[:2], symbols=symbols,
        eligible_by_decision=membership)
    removed = exited.filter((pl.col('available_us') == decisions[1]) & (pl.col('symbol') == symbols[0]))
    assert removed['raw_signed_target'][0] == removed['target_weight'][0] == 0.
    assert removed['eligibility_reason'][0] == 'POOL_EXIT'
    checked_reference(bars, decisions[:2], exited, membership)
    fresh, _ = target.fixed_targets(bars, decisions[1:2], symbols=symbols)
    assert fresh.filter(pl.col('symbol') == symbols[0])['raw_signed_target'][0] == .6/3
    with pytest.raises(ValueError, match='UTC daily'):
        target.fixed_targets(bars, decisions+1, symbols=symbols)
    for mode in ('SHORT_ONLY', 'LONG_SHORT'):
        with pytest.raises(ValueError, match='LONG_ONLY/CASH'):
            target.fixed_targets(bars, decisions, symbols=symbols, mode=mode)
    with pytest.raises(ValueError, match='equal'):
        target.fixed_targets(bars, decisions, symbols=symbols, allocation='INVERSE_VOL_30D')

    # Compare with the exact pre-change shared source from Git, loaded only
    # as an ordinary temporary STATE module. A new-default vs new-explicit
    # comparison alone would not detect a change shared by both code paths.
    old_source = subprocess.check_output(['git', 'show',
        'HEAD:scripts/investment/public_sma_perpetual.py'], cwd=shared.public.ROOT)
    old_sha = hashlib.sha256(old_source).hexdigest()
    assert old_sha == '37e126709d479fd4f99487e3a8a66deda8889286154e2f6ed04d180a2987ca47'
    old_path = tmp_path/'pre_rsi240_shared.py'
    old_path.write_bytes(old_source)
    old_spec = importlib.util.spec_from_file_location('pre_rsi240_shared', old_path)
    old_shared = importlib.util.module_from_spec(old_spec)
    old_spec.loader.exec_module(old_shared)
    default, default_meta = shared.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols)
    explicit, explicit_meta = shared.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols,
        completed_bar_count=200)
    assert default.equals(explicit) and default_meta == explicit_meta
    old_default, old_meta = old_shared.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols)
    assert default.equals(old_default) and default_meta == old_meta
    reference, reference_meta = hold.fixed_targets(bars, decisions, symbols=symbols)
    direct, direct_meta = shared.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols,
        direction_factory=hold._ConstantLongDirection, completed_bar_count=200)
    assert reference.equals(direct) and reference_meta['risk'] == direct_meta['risk']
    old_hold, old_hold_meta = old_shared.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols,
        direction_factory=hold._ConstantLongDirection)
    assert reference.equals(old_hold) and reference_meta['risk'] == old_hold_meta['risk']
    assert reference_meta['complete_daily_warmup'] == 200
    assert reference['raw_signed_target'].eq(.6/3).all()
    import json
    (tmp_path/'rsi2_daily_target_evidence.json').write_text(json.dumps(dict(
        strategy_id=target.STRATEGY_ID, scalar_context=240,
        raw_hook_witnesses=raw_hook_witnesses, target_rows=result.to_dicts(),
        independent_state_witnesses=independent_window['independent_RSI2_state_witnesses'],
        independent_kernel_metadata=independent_window['official_RSI_kernel_metadata'],
        old_shared_source_sha256=old_sha, default200_unchanged=True,
        HOLD_default_unchanged=True), allow_nan=False))
