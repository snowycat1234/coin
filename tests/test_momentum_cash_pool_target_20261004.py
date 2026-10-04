"""One hand state/covariance fixture for the fixed past30 long/cash mechanism."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_sma_perpetual as shared
from scripts.investment import momentum_cash_pool_target as target


def test_past30_momentum_cash_state_order_budget_and_causality(monkeypatch):
    symbols = ('ZZZUSDT', 'AAAUSDT', 'MMMUSDT')
    day = shared.DAY_US
    paths = ([101., 110., 99., 104., 777.],
             [99., 100., 101., 102., 888.], [100.] * 5)
    frames, prices_by_symbol = [], {}
    for symbol, last in zip(symbols, paths, strict=True):
        prices = np.asarray([100.] * 199 + list(last))
        if symbol == symbols[0]:
            # Volatile past returns force genuine downscaling. The first
            # 30-day reference is100 while adjacent references are110, so a
            # 29/31-day indexing mistake changes the first entry.
            prices[168] = prices[170] = 110.
            prices[173:199] = [80., 120.] * 13
        prices_by_symbol[symbol] = prices
        opened = np.arange(len(prices), dtype=np.int64) * day
        frames.append(pl.DataFrame(dict(symbol=[symbol] * len(prices), open_us=opened,
            close_us=opened + day, available_us=opened + day, open=prices,
            high=prices + .1, low=prices - .1, close=prices, volume=np.ones(len(prices)))))
    bars = pl.concat(frames)
    decisions = np.arange(200, 204, dtype=np.int64) * day

    def forbidden_sma_loader():
        raise AssertionError('Momentum must not load original SMA/Jesse hooks')
    monkeypatch.setattr(shared.public, '_load_public_hooks', forbidden_sma_loader)
    result, meta = target.fixed_targets(bars, decisions, symbols=symbols)
    assert meta['strategy_id'] == target.STRATEGY_ID and meta['rules'] == target.RULES
    assert meta['symbols'] == list(symbols) and meta['allocation'] == 'EQUAL'
    assert meta['momentum_completed_daily_return_days'] == 30
    assert meta['equality_exits_held_long'] and meta['close_then_wait_next_daily_decision_to_reenter']
    assert not meta['original_long_and_short_and_exit_hooks_reused']
    assert not meta['original_SMA_alpha_used'] and not meta['direction_context_is_Jesse_strategy']
    assert not meta['public_momentum_strategy_replicated']
    assert not {'fast_period', 'slow_period', 'equality_holds_current_position', 'source'} & meta.keys()

    # Positive entry -> exact equality exit -> bearish flat -> new positive
    # entry. The second asset enters only on its first strictly positive day.
    states = np.asarray([[1, 0, 0], [0, 0, 0], [0, 1, 0], [1, 1, 0]])
    for i, decision in enumerate(decisions):
        index = int(decision // day) - 1
        raw = states[i] * .2
        past = np.column_stack([
            np.diff(prices_by_symbol[s][index-30:index+1]) /
            prices_by_symbol[s][index-30:index] for s in symbols])
        centered = past - past.mean(axis=0)
        covariance = centered.T @ centered / 29 * 365
        sigma = math.sqrt(max(float(raw @ covariance @ raw), 0.))
        wanted = raw * min(1., .10 / sigma) if sigma else raw
        rows = result.filter(pl.col('available_us') == decision)
        assert rows['symbol'].to_list() == list(symbols)
        assert np.allclose(rows['raw_signed_target'].to_numpy(), raw, rtol=0, atol=1e-13)
        assert np.allclose(rows['target_weight'].to_numpy(), wanted, rtol=0, atol=1e-13)
        assert (rows['target_weight'] >= 0).all()
        assert (rows['target_weight'] <= rows['raw_signed_target']).all()
        assert meta['risk'][i]['covariance_symbol_order'] == list(symbols)
    first = result.filter(pl.col('available_us') == decisions[0])
    assert first['raw_signed_target'].to_list() == [.6 / len(symbols), 0., 0.]
    assert 0 < first['target_weight'][0] < .2  # Neither inactivity nor risk increases its budget.
    assert result.filter(pl.col('available_us') == decisions[1])['target_weight'].to_list() == [0., 0., 0.]

    # Actual direction hook: exact equality while flat blocks entry; equality
    # while held exits. A short is never requested, including a bearish bar.
    hook = target._MomentumCashDirection()
    close = np.full(200, 100.)
    hook.candles = np.column_stack((np.arange(200), close, close, close, close, np.ones(200)))
    assert not hook.should_long() and not hook.should_short()
    exits = []
    hook.is_long, hook.is_short, hook.liquidate = True, False, lambda: exits.append('EXIT')
    hook.update_position()
    assert exits == ['EXIT']
    hook.candles[-1, 2] = 99.
    assert not hook.should_long() and not hook.should_short()
    hook.update_position()
    assert exits == ['EXIT', 'EXIT']

    permuted, reordered_meta = target.fixed_targets(bars.reverse(), decisions,
        symbols=tuple(reversed(symbols)))
    assert reordered_meta['symbols'] == list(reversed(symbols))
    a, b = result.sort(['available_us', 'symbol']), permuted.sort(['available_us', 'symbol'])
    assert a.select('available_us', 'symbol', 'mode', 'eligibility_reason').equals(
        b.select('available_us', 'symbol', 'mode', 'eligibility_reason'))
    assert np.allclose(a.select('target_weight', 'raw_signed_target').to_numpy(),
        b.select('target_weight', 'raw_signed_target').to_numpy(), rtol=0, atol=1e-13)
    future = bars.with_columns([
        pl.when(pl.col('close_us') > decisions[1]).then(pl.col(c) * 1000)
          .otherwise(pl.col(c)).alias(c) for c in ('open', 'high', 'low', 'close')])
    prefix, prefix_meta = target.fixed_targets(future, decisions[:2], symbols=symbols)
    assert prefix.equals(result.filter(pl.col('available_us') <= decisions[1]))
    assert prefix_meta['risk'] == meta['risk'][:2]

    shortage = bars.filter(pl.col('close_us') < 200 * day)
    missing = bars.filter(~((pl.col('symbol') == symbols[0]) & (pl.col('close_us') == 199 * day)))
    delayed = bars.with_columns(pl.when((pl.col('symbol') == symbols[0]) &
        (pl.col('close_us') == 199 * day)).then(pl.lit(200 * day + 1))
        .otherwise(pl.col('available_us')).alias('available_us'))
    for bad in (shortage, missing, delayed):
        frame, _ = target.fixed_targets(bad, decisions[:1], symbols=symbols)
        assert frame['target_weight'].to_list() == [0., 0., 0.]
        assert frame['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP'

    # The member is still bullish when removed, so POOL_EXIT really cancels
    # an existing logical holding; its identity remains in the target rows.
    bullish = bars.with_columns([
        pl.when((pl.col('symbol') == symbols[0]) & (pl.col('close_us') == decisions[1]))
          .then(pl.lit(price)).otherwise(pl.col(column)).alias(column)
        for column, price in (('open', 120.), ('high', 120.1), ('low', 119.9), ('close', 120.))])
    membership = {int(decisions[0]): symbols, int(decisions[1]): symbols[1:]}
    frame, _ = target.fixed_targets(bullish, decisions[:2], symbols=symbols,
        eligible_by_decision=membership)
    exited = frame.filter((pl.col('available_us') == decisions[1]) & (pl.col('symbol') == symbols[0]))
    assert exited['raw_signed_target'][0] == exited['target_weight'][0] == 0.
    assert exited['eligibility_reason'][0] == 'POOL_EXIT'
    with pytest.raises(ValueError, match='UTC daily'):
        target.fixed_targets(bars, decisions + 1, symbols=symbols)
    with pytest.raises(ValueError, match='LONG_ONLY'):
        target.fixed_targets(bars, decisions, symbols=symbols, mode='SHORT_ONLY')
    with pytest.raises(ValueError, match='equal'):
        target.fixed_targets(bars, decisions, symbols=symbols, allocation='INVERSE_VOL_30D')
