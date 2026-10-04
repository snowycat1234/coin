"""Independent windows distinguish initial entry from armed short reentry."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import donchian_daily_pool_target as target


def test_reentry10_requires_real_exit_preserves_first20_and_causal_shared_risk():
    day = target.DAY_US
    symbols = ('ZZZUSDT', 'AAAUSDT', 'MMMUSDT')
    length = 218
    a = np.full(length, 100.)
    a[199:201], a[201:211] = [110., 160.], 170.
    a[211:216], a[216:] = [169., 167., 171., 173., 174.], 174.
    b = np.full(length, 200.)
    b[200], b[201:] = 250., 199.
    c = np.full(length, 200.)
    c[180:200], c[200:202], c[202:212], c[212:] = 90., [250., 80.], 90., 100.
    closes = dict(zip(symbols, (a, b, c), strict=True))
    frames = []
    for symbol in symbols:
        close = closes[symbol]
        high, low = close + 1., close - 1.
        if symbol == symbols[0]:
            high[185] = 150.  # Initial10 breakout below initial20 must stay flat.
            high[200] = 300.  # Exclude current entry bar; later blocks first20.
            low[211] = 169.   # Exact prior10 lower equality holds the long.
            low[212] = 1.     # Exclude current exit low, or exit would be missed.
        opens = np.arange(length, dtype=np.int64) * day
        frames.append(pl.DataFrame(dict(symbol=[symbol] * length, open_us=opens,
            close_us=opens + day, available_us=opens + day, open=close,
            high=high, low=low, close=close, volume=np.ones(length))))
    bars = pl.concat(frames)
    decisions = np.arange(199, 219, dtype=np.int64) * day
    kwargs = dict(symbols=symbols, allocation='ACTIVE_EQUAL', exit_period=10)
    control, control_meta = target.fixed_targets(bars, decisions, **kwargs)
    explicit_control, explicit_meta = target.fixed_targets(bars, decisions,
        reentry_period=20, **kwargs)
    assert control.equals(explicit_control) and control_meta == explicit_meta
    default, default_meta = target.fixed_targets(bars, decisions, symbols=symbols)
    explicit_default, explicit_default_meta = target.fixed_targets(bars, decisions,
        symbols=symbols, exit_period=20, reentry_period=20)
    assert default.equals(explicit_default) and default_meta == explicit_default_meta
    assert default_meta['rules'] == target.RULES
    new, new_meta = target.fixed_targets(bars, decisions, reentry_period=10, **kwargs)
    assert new_meta['strategy_id'] == target.strategy_id(10, reentry_period=10)
    assert new_meta['strategy_id'] != control_meta['strategy_id']
    assert new_meta['rules'] == target.strategy_rules('ACTIVE_EQUAL', 10, reentry_period=10)

    # Reference uses direct high/low slices, explicit held/armed bits, and
    # centered covariance. It never calls production hooks or risk helpers.
    for period, observed, metadata in ((20, control, control_meta), (10, new, new_meta)):
        held = dict.fromkeys(symbols, False)
        armed = dict.fromkeys(symbols, False)
        for row, decision in enumerate(decisions):
            i = int(decision // day) - 1
            if i >= 199:
                for symbol in symbols:
                    one = bars.filter(pl.col('symbol') == symbol).sort('close_us')
                    close = float(closes[symbol][i])
                    lower = min(one['low'].to_list()[i - 10:i])
                    upper_period = period if armed[symbol] else 20
                    upper = max(one['high'].to_list()[i - upper_period:i])
                    sma = math.fsum(closes[symbol][i - 199:i + 1]) / 200
                    if held[symbol]:
                        if close < lower:
                            held[symbol], armed[symbol] = False, True
                    elif close > upper and close > sma:
                        held[symbol], armed[symbol] = True, False
            count = sum(held.values())
            size = min(.3, .6 / count) if count else 0.
            raw = np.asarray([size if held[s] else 0. for s in symbols])
            if i < 199:
                expected = np.zeros(3)
                assert metadata['risk'][row]['covariance_symbol_order'] == []
            else:
                history = np.column_stack([closes[s][i - 30:i + 1] for s in symbols])
                returns = np.diff(history, axis=0) / history[:-1]
                centered = returns - returns.mean(axis=0)
                covariance = centered.T @ centered / 29 * 365
                sigma = math.sqrt(max(float(raw @ covariance @ raw), 0.))
                expected = raw * min(1., .10 / sigma) if sigma else raw
                assert metadata['risk'][row]['covariance_symbol_order'] == list(symbols)
                assert metadata['risk'][row]['covariance_observations'] == 30
                assert metadata['risk'][row]['unscaled_signed_covariance_annual_vol'] == pytest.approx(sigma)
            actual = observed.filter(pl.col('available_us') == decision)
            assert actual['symbol'].to_list() == list(symbols)
            assert np.allclose(actual['raw_signed_target'].to_numpy(), raw, rtol=0, atol=1e-13)
            assert np.allclose(actual['target_weight'].to_numpy(), expected, rtol=0, atol=1e-13)
            assert metadata['risk'][row]['active_signal_count'] == count
            assert np.abs(expected).max() <= .3 + 1e-13 and np.abs(expected).sum() <= .6 + 1e-13

    def raw_at(frame, index, symbol):
        return frame.filter((pl.col('available_us') == (index + 1) * day)
            & (pl.col('symbol') == symbol))['raw_signed_target'][0]

    assert raw_at(new, 199, symbols[0]) == 0.  # Not armed: first20 required.
    assert raw_at(new, 200, symbols[0]) > 0.   # Current high300 excluded.
    assert raw_at(new, 211, symbols[0]) > 0.   # Strict low equality holds.
    assert raw_at(new, 212, symbols[0]) == 0.  # Real exit, no same-day entry.
    assert raw_at(new, 213, symbols[0]) == 0.  # Strict reentry-high equality.
    assert raw_at(new, 214, symbols[0]) > 0.   # Armed10 high but not first20.
    assert raw_at(control, 214, symbols[0]) == 0.
    assert raw_at(new, 201, symbols[1]) > 0.   # SMA only entry, not held exit.
    assert raw_at(new, 200, symbols[2]) > 0.
    assert raw_at(new, 201, symbols[2]) == 0.
    assert raw_at(new, 212, symbols[2]) == 0.  # Armed10 breakout below SMA.
    assert control.filter(pl.col('available_us') <= 214 * day).equals(
        new.filter(pl.col('available_us') <= 214 * day))

    # A current extreme high does not block reentry at that same close.
    extreme = bars.with_columns(pl.when((pl.col('symbol') == symbols[0])
        & (pl.col('open_us') == 214 * day)).then(1000.)
        .otherwise(pl.col('high')).alias('high'))
    current, _ = target.fixed_targets(extreme, decisions[decisions <= 215 * day],
        reentry_period=10, **kwargs)
    assert current.equals(new.filter(pl.col('available_us') <= 215 * day))

    # Pool reset clears armed state, so the same short breakout cannot become
    # a first entry when the asset returns to the configured account.
    memberships = {int(t): symbols for t in decisions}
    memberships[214 * day] = symbols[1:]
    reset_pool, _ = target.fixed_targets(bars, decisions,
        eligible_by_decision=memberships, reentry_period=10, **kwargs)
    assert raw_at(reset_pool, 214, symbols[0]) == 0.
    assert reset_pool.filter((pl.col('available_us') == 214 * day)
        & (pl.col('symbol') == symbols[0]))['eligibility_reason'][0] == 'POOL_EXIT'

    # A late bar creates a real availability gap while armed; after availability
    # returns the contiguous200 context is valid, but arm must remain reset.
    gap = bars.with_columns(pl.when((pl.col('symbol') == symbols[0])
        & (pl.col('open_us') == 213 * day)).then(216 * day)
        .otherwise(pl.col('available_us')).alias('available_us'))
    reset_gap, _ = target.fixed_targets(gap, decisions, reentry_period=10, **kwargs)
    assert raw_at(reset_gap, 215, symbols[0]) == 0.
    assert reset_gap.filter((pl.col('available_us') == 216 * day)
        & (pl.col('symbol') == symbols[0]))['eligibility_reason'][0] == 'ELIGIBLE'
    assert reset_gap.filter((pl.col('available_us') == 214 * day)
        & (pl.col('symbol') == symbols[0]))['eligibility_reason'][0] == 'WARMUP_OR_DATA_GAP'

    cutoff = 214 * day
    future = bars.with_columns([pl.when(pl.col('close_us') > cutoff)
        .then(pl.col(field) * 1000.).otherwise(pl.col(field)).alias(field)
        for field in ('open', 'high', 'low', 'close')])
    prefix, prefix_meta = target.fixed_targets(future, decisions[decisions <= cutoff],
        reentry_period=10, **kwargs)
    assert prefix.equals(new.filter(pl.col('available_us') <= cutoff))
    assert prefix_meta['risk'] == new_meta['risk'][:len(decisions[decisions <= cutoff])]
    reordered, reordered_meta = target.fixed_targets(bars.reverse(), decisions,
        symbols=symbols[::-1], allocation='ACTIVE_EQUAL', exit_period=10, reentry_period=10)
    assert reordered_meta['risk'][1]['covariance_symbol_order'] == list(symbols[::-1])
    assert np.allclose(new.sort(['available_us', 'symbol']).select(
        'target_weight', 'raw_signed_target').to_numpy(), reordered.sort(
        ['available_us', 'symbol']).select('target_weight', 'raw_signed_target').to_numpy(),
        rtol=0, atol=1e-13)
    cash, _ = target.fixed_targets(bars, decisions, 'CASH', reentry_period=10, **kwargs)
    assert cash['target_weight'].eq(0.).all() and cash['raw_signed_target'].eq(0.).all()
    with pytest.raises(ValueError):
        target.fixed_targets(bars, decisions, symbols=symbols, exit_period=20, reentry_period=10)
