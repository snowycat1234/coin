"""One hand state/risk fixture using the actual pinned upstream SMA hooks."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_sma_perpetual as shared
from scripts.investment import public_sma_pool_target as target


def test_original_sma_pool_hooks_state_budget_order_and_causality(monkeypatch):
    symbols = ('AAAUSDT', 'BBBUSDT', 'CCCUSDT')
    day = shared.DAY_US
    paths = ([101.,99.,98.,104.,777.], [99.,100.,100.,104.,888.], [100.]*5)
    frames, prices_by_symbol = [], {}
    for symbol, last in zip(symbols, paths, strict=True):
        prices = np.asarray([100.]*199 + list(last))
        prices_by_symbol[symbol] = prices
        opens = np.arange(len(prices), dtype=np.int64) * day
        frames.append(pl.DataFrame(dict(symbol=[symbol]*len(prices), open_us=opens,
            close_us=opens+day, available_us=opens+day, open=prices,
            high=prices+.1, low=prices-.1, close=prices, volume=np.ones(len(prices)))))
    bars = pl.concat(frames)
    decisions = np.arange(200,204,dtype=np.int64) * day
    original_loader = shared.public._load_public_hooks
    actual_classes = []
    def observed_original_loader():
        cls = original_loader()
        actual_classes.append(cls)
        return cls
    monkeypatch.setattr(shared.public, '_load_public_hooks', observed_original_loader)
    result, meta = target.fixed_targets(bars, decisions, symbols=symbols)
    assert len(actual_classes) == 1 and actual_classes[0].__name__ == 'SMACrossover'
    cls = actual_classes[0]
    assert cls.should_long.__code__.co_filename.startswith(
        str(shared.public.VENDOR/'smacrossover_original.py'))
    assert meta['original_long_and_short_and_exit_hooks_reused']
    assert meta['source'] == shared.public.PINNED_HASHES
    assert meta['strategy_id'] == target.STRATEGY_ID
    assert meta['rules'] == target.RULES and meta['allocation'] == 'EQUAL'
    assert meta['fresh_flat_each_window'] and not meta['native_Jesse_or_Bybit_execution_replicated']

    states = np.asarray([[1,0,0],[1,0,0],[0,0,0],[1,1,0]])
    for i, decision in enumerate(decisions):
        index = int(decision//day)-1
        # Independently read the real hook scalar results against hand means,
        # including equality while held and never activating a bearish short.
        for j, symbol in enumerate(symbols):
            closed = prices_by_symbol[symbol][index-199:index+1]
            fast, slow = float(sum(closed[-50:])/50), float(sum(closed)/200)
            hook = cls()
            hook.candles = np.column_stack((np.arange(200), closed, closed,
                closed+.1, closed-.1, np.ones(200)))
            assert hook.fast_sma == pytest.approx(fast, rel=0, abs=1e-13)
            assert hook.slow_sma == pytest.approx(slow, rel=0, abs=1e-13)
            assert hook.should_long() == (fast > slow)
            assert hook.should_short() == (fast < slow)
            if i==1 and j==0:
                assert fast == slow == 100. and states[i,j] == 1
            if i==2 and j==0:
                assert fast < slow and states[i,j] == 0
            if i==3 and j==0:
                assert fast > slow and states[i-1,j] == 0 and states[i,j] == 1
        raw = states[i] * .2  # Inactive signals retain their share; no redistribution.
        past = np.column_stack([
            np.diff(prices_by_symbol[s][index-30:index+1]) /
            prices_by_symbol[s][index-30:index] for s in symbols])
        centered = past-past.mean(axis=0)
        covariance = centered.T@centered/29*365
        sigma = math.sqrt(max(float(raw@covariance@raw),0.))
        wanted = raw * min(1., .10/sigma) if sigma else raw
        rows = result.filter(pl.col('available_us')==decision)
        assert rows['symbol'].to_list() == list(symbols)
        assert np.allclose(rows['raw_signed_target'].to_numpy(),raw,rtol=0,atol=1e-13)
        assert np.allclose(rows['target_weight'].to_numpy(),wanted,rtol=0,atol=1e-13)
        assert not (rows['target_weight'] < 0).any()

    permuted, _ = target.fixed_targets(bars.reverse(), decisions, symbols=tuple(reversed(symbols)))
    a, b = result.sort(['available_us','symbol']), permuted.sort(['available_us','symbol'])
    assert a.select('available_us','symbol','mode','eligibility_reason').equals(
        b.select('available_us','symbol','mode','eligibility_reason'))
    assert np.allclose(a.select('target_weight','raw_signed_target').to_numpy(),
        b.select('target_weight','raw_signed_target').to_numpy(),rtol=0,atol=1e-13)
    future = bars.with_columns([
        pl.when(pl.col('close_us') > decisions[1]).then(pl.col(c)*1000)
          .otherwise(pl.col(c)).alias(c) for c in ('open','high','low','close')])
    prefix, _ = target.fixed_targets(future, decisions[:2], symbols=symbols)
    assert prefix.equals(result.filter(pl.col('available_us')<=decisions[1]))
    missing = bars.filter(~((pl.col('symbol')==symbols[0]) & (pl.col('close_us')==199*day)))
    frame, _ = target.fixed_targets(missing, decisions[:1], symbols=symbols)
    assert frame['target_weight'].to_list() == [0.,0.,0.]
    assert frame['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP'
    membership = {int(decisions[0]):symbols, int(decisions[1]):symbols[1:]}
    frame, _ = target.fixed_targets(bars, decisions[:2], symbols=symbols,
        eligible_by_decision=membership)
    exited = frame.filter((pl.col('available_us')==decisions[1]) & (pl.col('symbol')==symbols[0]))
    assert exited['target_weight'][0] == 0. and exited['eligibility_reason'][0] == 'POOL_EXIT'
    with pytest.raises(ValueError,match='LONG_ONLY'):
        target.fixed_targets(bars,decisions,symbols=symbols,mode='SHORT_ONLY')
    with pytest.raises(ValueError,match='equal'):
        target.fixed_targets(bars,decisions,symbols=symbols,allocation='INVERSE_VOL_30D')
