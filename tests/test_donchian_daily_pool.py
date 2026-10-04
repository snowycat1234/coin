"""Direct-window reference for the new daily public hooks and shared routing."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import donchian_daily_pool_target as target


def test_donchian_daily_prior_channel_filter_exit_and_shared_past_only_targets():
    day = target.DAY_US
    symbols = ('ZZZUSDT', 'AAAUSDT', 'MMMUSDT')
    # Current-bar high is extreme: including it in the channel would suppress
    # the initial breakout. A later lower breakout exits the actual held state.
    closes = {
        symbols[0]: np.asarray([100.] * 199 + [110., 105., 98., 110., 999.]),
        symbols[1]: np.asarray([200.] * 180 + [90.] * 19 + [100., 100., 100., 100., 999.]),
        symbols[2]: np.full(204, 100.),
    }
    frames = []
    for symbol in symbols:
        close = closes[symbol]
        high, low = close+1., close-1.
        if symbol == symbols[0]:
            high[199] = 1000.
        if symbol == symbols[2]:
            high, low = close.copy(), close.copy()
        opens = np.arange(len(close), dtype=np.int64)*day
        frames.append(pl.DataFrame(dict(symbol=[symbol]*len(close), open_us=opens,
            close_us=opens+day, available_us=opens+day, open=close,
            high=high, low=low, close=close, volume=np.ones(len(close)))))
    bars = pl.concat(frames)
    decisions = np.arange(200, 204, dtype=np.int64)*day
    result, meta = target.fixed_targets(bars, decisions, symbols=symbols)
    states = dict.fromkeys(symbols, False)
    expected_states = [[True, False, False], [True, False, False],
        [False, False, False], [False, False, False]]
    for row, decision in enumerate(decisions):
        raw, past = [], []
        for asset, symbol in enumerate(symbols):
            one = bars.filter(pl.col('symbol') == symbol).sort('close_us')
            index = int(decision//day)-1
            # Independently compute windows without using production hooks.
            upper = max(one['high'].to_list()[index-20:index])
            lower = min(one['low'].to_list()[index-20:index])
            close = closes[symbol][index]
            mean = sum(closes[symbol][index-199:index+1])/200
            before = states[symbol]
            if before:
                if close < lower:
                    states[symbol] = False
            elif close > upper and close > mean:
                states[symbol] = True
            assert states[symbol] == expected_states[row][asset]
            raw.append(.6/len(symbols) if states[symbol] else 0.)
            history = closes[symbol][index-30:index+1]
            past.append(np.diff(history)/history[:-1])
            hook = target._load_public_hooks()()
            observed = one.slice(index-199, 200)
            hook.candles = np.column_stack((observed['open_us'].to_numpy()/1000,
                observed.select('open', 'close', 'high', 'low', 'volume').to_numpy()))
            hook.price, hook.is_long, hook.is_short = float(close), before, False
            assert hook.donchian.upperband == upper and hook.donchian.lowerband == lower
            assert hook.ma_trend == pytest.approx(mean, abs=1e-12)
            assert bool(hook.should_long()) == (close > upper and close > mean)
            assert hook.should_short() is False
            exits = []
            hook.liquidate = lambda: exits.append(True)
            if before:
                hook.update_position()
                assert bool(exits) == (close < lower)
        raw = np.asarray(raw)
        values = np.column_stack(past)
        centered = values-values.mean(axis=0)
        covariance = centered.T@centered/29*365
        sigma = math.sqrt(max(float(raw@covariance@raw), 0.))
        expected = raw*min(1., .10/sigma) if sigma else raw
        actual = result.filter(pl.col('available_us') == decision)
        assert actual['symbol'].to_list() == list(symbols)
        assert np.allclose(actual['raw_signed_target'].to_numpy(), raw, rtol=0, atol=1e-13)
        assert np.allclose(actual['target_weight'].to_numpy(), expected, rtol=0, atol=1e-13)
        assert meta['risk'][row]['covariance_symbol_order'] == list(symbols)
    assert meta['rules'] == target.RULES
    assert meta['public_upstream_sha256'] == target.PINNED_HASHES
    assert meta['original_long_entry_filter_and_exit_hooks_reused']
    assert not meta['upstream_timeframe_prescribed']
    assert not {'source', 'fast_period', 'slow_period'} & meta.keys()
    first = result.filter(pl.col('available_us') == decisions[0])
    assert first['raw_signed_target'].to_list() == [.6/3, 0., 0.]
    # Strict upper equality blocks entry; strict lower equality retains a
    # holding. The entry SMA filter must not become a new holding exit.
    hook = target._load_public_hooks()()
    price = np.full(200, 100.)
    hook.candles = np.column_stack((np.arange(200), price, price,
        np.full(200, 101.), np.full(200, 99.), np.ones(200)))
    hook.price = 101.
    assert not hook.should_long()
    hook.price = 100.
    assert not hook.filter_trend()  # Equality to SMA200 blocks the filter.
    hook.price = 99.
    assert not hook.filter_trend()
    exits = []
    hook.liquidate = lambda: exits.append(True)
    hook.update_position()
    assert not exits  # Equal lower channel, despite price below SMA200.
    hook.price = 98.
    hook.update_position()
    assert exits == [True]
    future = bars.with_columns([pl.when(pl.col('close_us') > decisions[1])
        .then(pl.col(field)*1000).otherwise(pl.col(field)).alias(field)
        for field in ('open', 'high', 'low', 'close')])
    prefix, prefix_meta = target.fixed_targets(future, decisions[:2], symbols=symbols)
    assert prefix.equals(result.filter(pl.col('available_us') <= decisions[1]))
    assert prefix_meta['risk'] == meta['risk'][:2]
    reordered, _ = target.fixed_targets(bars.reverse(), decisions, symbols=symbols[::-1])
    assert np.allclose(result.sort(['available_us', 'symbol']).select(
        'target_weight', 'raw_signed_target').to_numpy(), reordered.sort(
        ['available_us', 'symbol']).select('target_weight', 'raw_signed_target').to_numpy(),
        rtol=0, atol=1e-13)
    cash, _ = target.fixed_targets(bars, decisions, 'CASH', symbols=symbols)
    assert cash['target_weight'].eq(0.).all() and cash['raw_signed_target'].eq(0.).all()
    missing = bars.filter(~((pl.col('symbol') == symbols[0]) & (pl.col('close_us') == day)))
    absent, _ = target.fixed_targets(missing, decisions[:1], symbols=symbols)
    assert absent.filter(pl.col('symbol') == symbols[0])['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP'
    for mode in ('SHORT_ONLY', 'LONG_SHORT'):
        with pytest.raises(ValueError, match='LONG_ONLY/CASH'):
            target.fixed_targets(bars, decisions, mode, symbols=symbols)
