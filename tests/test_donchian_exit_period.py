"""Direct completed-window counterexample for the sole exit-period change."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import donchian_daily_pool_target as target


def test_exit10_changes_only_held_exit_state_with_causal_shared_risk():
    day = target.DAY_US
    symbols = ('ZZZUSDT', 'AAAUSDT', 'MMMUSDT')
    length = 216
    a = np.full(length, 100.)
    a[199], a[200:210], a[210:214] = 110., 115., [114., 112., 120., 119.]
    a[214:] = 119.
    b = np.full(length, 200.)
    b[199], b[200:] = 250., 199.
    # C clears its prior20 upper at the first eligible decision, but remains
    # below SMA200; it cannot consume active budget as an entry signal.
    c = np.asarray([200.] * 179 + [90.] * 20 + [100.] * (length - 199))
    closes = dict(zip(symbols, (a, b, c), strict=True))
    frames = []
    for symbol in symbols:
        close = closes[symbol]
        high, low = close + 1., close - 1.
        if symbol == symbols[0]:
            low[210] = 114.  # Equality to prior10 low retains the position.
            low[211] = 1.    # Current low must be excluded at the exit decision.
            high[212] = 1000.  # Current high must not block next-day reentry.
        opens = np.arange(length, dtype=np.int64) * day
        frames.append(pl.DataFrame(dict(symbol=[symbol] * length, open_us=opens,
            close_us=opens + day, available_us=opens + day, open=close,
            high=high, low=low, close=close, volume=np.ones(length))))
    bars = pl.concat(frames)
    decisions = np.arange(199, 216, dtype=np.int64) * day
    default, default_meta = target.fixed_targets(bars, decisions, symbols=symbols,
        allocation='ACTIVE_EQUAL')
    old, old_meta = target.fixed_targets(bars, decisions, symbols=symbols,
        allocation='ACTIVE_EQUAL', exit_period=20)
    new, new_meta = target.fixed_targets(bars, decisions, symbols=symbols,
        allocation='ACTIVE_EQUAL', exit_period=10)
    assert default.equals(old) and default_meta == old_meta
    _, equal_meta = target.fixed_targets(bars, decisions, symbols=symbols)
    assert equal_meta['rules'] == target.RULES
    assert old_meta['strategy_id'] == target.STRATEGY_ID
    assert new_meta['strategy_id'] == 'COIN_JESSE_DONCHIAN20_SMA200_EXIT10_1D_USDM_CONFIGURED_POOL_VARIANT'
    assert new_meta['rules']['exit_predicate'] == 'HELD_LONG_AND_CLOSE_LT_PREVIOUS10_LOW'
    assert new_meta['rules']['exit_period'] == 10
    assert new_meta['rules']['donchian_period'] == 20
    assert new_meta['rules']['trend_filter_applies_only_to_entry']

    for period, observed, meta in ((20, old, old_meta), (10, new, new_meta)):
        states = dict.fromkeys(symbols, False)
        for row, decision in enumerate(decisions):
            index = int(decision // day) - 1
            if index >= 199:
                for symbol in symbols:
                    one = bars.filter(pl.col('symbol') == symbol).sort('close_us')
                    close = closes[symbol][index]
                    upper = max(one['high'].to_list()[index - 20:index])
                    lower = min(one['low'].to_list()[index - period:index])
                    sma = math.fsum(closes[symbol][index - 199:index + 1]) / 200
                    before = states[symbol]
                    if before:
                        states[symbol] = close >= lower
                    elif close > upper and close > sma:
                        states[symbol] = True
            count = sum(states.values())
            share = min(.3, .6 / count) if count else 0.
            raw = np.asarray([share if states[s] else 0. for s in symbols])
            if index < 199:
                expected = np.zeros(3)
                assert meta['risk'][row]['covariance_symbol_order'] == []
            else:
                history = np.column_stack([closes[s][index - 30:index + 1] for s in symbols])
                returns = np.diff(history, axis=0) / history[:-1]
                centered = returns - returns.mean(axis=0)
                covariance = centered.T @ centered / 29 * 365
                sigma = math.sqrt(max(float(raw @ covariance @ raw), 0.))
                expected = raw * min(1., .10 / sigma) if sigma else raw
                assert meta['risk'][row]['covariance_symbol_order'] == list(symbols)
                assert meta['risk'][row]['covariance_observations'] == 30
                assert meta['risk'][row]['unscaled_signed_covariance_annual_vol'] == pytest.approx(sigma)
            one = observed.filter(pl.col('available_us') == decision)
            assert one['symbol'].to_list() == list(symbols)
            assert np.allclose(one['raw_signed_target'].to_numpy(), raw, rtol=0, atol=1e-13)
            assert np.allclose(one['target_weight'].to_numpy(), expected, rtol=0, atol=1e-13)
            assert meta['risk'][row]['active_signal_count'] == count
            assert np.abs(expected).max() <= .3 + 1e-13 and np.abs(expected).sum() <= .6 + 1e-13

    def raw_at(frame, index, symbol):
        return frame.filter((pl.col('available_us') == (index + 1) * day)
            & (pl.col('symbol') == symbol))['raw_signed_target'][0]

    assert raw_at(new, 210, symbols[0]) > 0.  # Strict lower equality holds.
    assert raw_at(new, 211, symbols[0]) == 0. # Exit now, no same-day reentry.
    assert raw_at(old, 211, symbols[0]) > 0.  # Older low belongs only to exit20.
    assert raw_at(new, 212, symbols[0]) > 0.  # Fresh breakout on following day.
    assert raw_at(new, 200, symbols[1]) > 0. # Holding below SMA200 is not an exit.
    assert raw_at(new, 199, symbols[2]) == 0. # Breakout below SMA200 cannot enter.
    changed = old.filter(pl.col('available_us') < 212 * day)
    assert changed.equals(new.filter(pl.col('available_us') < 212 * day))

    cutoff = 211 * day  # Only alter future observations, before exit difference.
    future = bars.with_columns([pl.when(pl.col('close_us') > cutoff)
        .then(pl.col(field) * 1000.).otherwise(pl.col(field)).alias(field)
        for field in ('open', 'high', 'low', 'close')])
    prefix, prefix_meta = target.fixed_targets(future, decisions[decisions <= cutoff],
        symbols=symbols, allocation='ACTIVE_EQUAL', exit_period=10)
    assert prefix.equals(new.filter(pl.col('available_us') <= cutoff))
    assert prefix_meta['risk'] == new_meta['risk'][:len(decisions[decisions <= cutoff])]
    reordered, reordered_meta = target.fixed_targets(bars.reverse(), decisions,
        symbols=symbols[::-1], allocation='ACTIVE_EQUAL', exit_period=10)
    assert reordered_meta['risk'][1]['covariance_symbol_order'] == list(symbols[::-1])
    assert np.allclose(new.sort(['available_us', 'symbol']).select(
        'target_weight', 'raw_signed_target').to_numpy(), reordered.sort(
        ['available_us', 'symbol']).select('target_weight', 'raw_signed_target').to_numpy(),
        rtol=0, atol=1e-13)

    # A gap arrives while A is held; reset must preserve account identity and
    # cannot forward-fill a surviving signal or allocate capital to that asset.
    missing_day = 207 * day
    missing = bars.filter(~((pl.col('symbol') == symbols[0])
        & (pl.col('close_us') == missing_day)))
    reset, reset_meta = target.fixed_targets(missing, decisions, symbols=symbols,
        allocation='ACTIVE_EQUAL', exit_period=10)
    assert reset.filter(pl.col('available_us') < missing_day).equals(
        new.filter(pl.col('available_us') < missing_day))
    after = reset.filter((pl.col('available_us') >= missing_day)
        & (pl.col('symbol') == symbols[0]))
    assert after['raw_signed_target'].eq(0.).all() and after['target_weight'].eq(0.).all()
    assert set(after['eligibility_reason'].to_list()) == {'WARMUP_OR_DATA_GAP'}
    assert all(symbols[0] not in r['covariance_symbol_order']
        for r in reset_meta['risk'] if r['decision_us'] >= missing_day)
    cash, _ = target.fixed_targets(bars, decisions, 'CASH', symbols=symbols,
        allocation='ACTIVE_EQUAL', exit_period=10)
    assert cash['raw_signed_target'].eq(0.).all() and cash['target_weight'].eq(0.).all()
