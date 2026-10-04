"""Independent state/window arithmetic for the one-factor active sizing change."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import donchian_daily_pool_target as target
from scripts.investment import public_sma_perpetual as shared


def test_active_signal_allocation_preserves_states_caps_covariance_and_causality():
    day = target.DAY_US
    symbols = ('ZZZUSDT', 'AAAUSDT', 'MMMUSDT')
    # Independent staggered breakouts create 0, 1, 2, 3 and then 0 held
    # signals. Large returns make the first two active budgets risk saturated,
    # so higher raw sizing cannot manufacture additional final exposure.
    closes = {
        symbols[0]: np.asarray([100.] * 200 + [150., 151., 152., 98., 999.]),
        symbols[1]: np.asarray([100.] * 201 + [150., 151., 98., 999.]),
        symbols[2]: np.asarray([100.] * 202 + [150., 98., 999.]),
    }
    frames = []
    for symbol in symbols:
        close = closes[symbol]
        opens = np.arange(len(close), dtype=np.int64) * day
        high, low = close + 1., close - 1.
        if symbol == symbols[0]:
            high[200] = 1000.  # Current high must not prevent its own entry.
        frames.append(pl.DataFrame(dict(symbol=[symbol] * len(close),
            open_us=opens, close_us=opens + day, available_us=opens + day,
            open=close, high=high, low=low, close=close,
            volume=np.ones(len(close)))))
    bars = pl.concat(frames)
    decisions = np.arange(199, 205, dtype=np.int64) * day
    active, meta = target.fixed_targets(bars, decisions, symbols=symbols,
        allocation='ACTIVE_EQUAL')
    equal, original_meta = target.fixed_targets(bars, decisions, symbols=symbols)
    states = dict.fromkeys(symbols, False)
    counts = [0, 0, 1, 2, 3, 0]

    def reference_risk(raw, values):
        # Direct centered sums rather than production np.cov/risk helper.
        centered = values - values.mean(axis=0)
        covariance = centered.T @ centered / (len(values) - 1) * 365
        sigma = math.sqrt(max(float(raw @ covariance @ raw), 0.))
        return raw * min(1., .10 / sigma) if sigma else raw.copy(), sigma

    for row, decision in enumerate(decisions):
        index = int(decision // day) - 1
        if index >= 199:
            for symbol in symbols:
                one = bars.filter(pl.col('symbol') == symbol).sort('close_us')
                close = closes[symbol][index]
                upper = max(one['high'].to_list()[index - 20:index])
                lower = min(one['low'].to_list()[index - 20:index])
                mean = sum(closes[symbol][index - 199:index + 1]) / 200
                if states[symbol]:
                    if close < lower:
                        states[symbol] = False
                elif close > upper and close > mean:
                    states[symbol] = True
        count = sum(states.values())
        assert count == counts[row]
        per_active = min(.3, .6 / count) if count else 0.
        raw = np.asarray([per_active if states[s] else 0. for s in symbols])
        observed = active.filter(pl.col('available_us') == decision)
        control = equal.filter(pl.col('available_us') == decision)
        assert observed['symbol'].to_list() == list(symbols)
        assert np.allclose(observed['raw_signed_target'].to_numpy(), raw,
            rtol=0, atol=1e-13)
        assert np.array_equal(observed['raw_signed_target'].to_numpy() != 0.,
            control['raw_signed_target'].to_numpy() != 0.)
        assert observed['eligibility_reason'].to_list() == control['eligibility_reason'].to_list()
        assert meta['risk'][row]['active_signal_count'] == count
        assert meta['risk'][row]['raw_per_active_fraction'] == pytest.approx(per_active)
        if index < 199:
            assert observed['eligibility_reason'].to_list() == ['WARMUP_OR_DATA_GAP'] * 3
            assert meta['risk'][row]['covariance_symbol_order'] == []
            expected, sigma = np.zeros(3), 0.
        else:
            history = np.column_stack([closes[s][index - 30:index + 1] for s in symbols])
            expected, sigma = reference_risk(raw, np.diff(history, axis=0) / history[:-1])
            assert meta['risk'][row]['covariance_observations'] == 30
            assert meta['risk'][row]['covariance_symbol_order'] == list(symbols)
        assert meta['risk'][row]['unscaled_signed_covariance_annual_vol'] == pytest.approx(sigma)
        assert np.allclose(observed['target_weight'].to_numpy(), expected, rtol=0, atol=1e-13)
        assert np.abs(expected).max() <= .3 + 1e-13
        assert np.abs(expected).sum() <= .6 + 1e-13
        if count in (1, 2):
            assert original_meta['risk'][row]['unscaled_signed_covariance_annual_vol'] > .10
            assert sigma > .10
            assert np.allclose(observed['target_weight'].to_numpy(),
                control['target_weight'].to_numpy(), rtol=0, atol=1e-13)

    assert original_meta['rules'] == target.RULES
    assert not original_meta['rules']['inactive_signal_budget_redistributed']
    assert meta['strategy_id'] == original_meta['strategy_id']
    assert meta['rules']['allocation'] == 'ACTIVE_EQUAL'
    assert meta['rules']['inactive_signal_budget_redistributed']
    assert meta['rules']['absolute_target_per_asset'] == .3
    assert meta['rules']['gross_target_cap'] == .6
    assert meta['rules']['past_covariance_daily_returns'] == 30
    assert meta['rules']['completed_daily_eligibility_bars'] == 200

    # Input row order never replaces configured covariance/account identity.
    reordered, reordered_meta = target.fixed_targets(bars.reverse(), decisions,
        symbols=symbols[::-1], allocation='ACTIVE_EQUAL')
    assert reordered_meta['risk'][3]['covariance_symbol_order'] == list(symbols[::-1])
    assert np.allclose(active.sort(['available_us', 'symbol']).select(
        'target_weight', 'raw_signed_target').to_numpy(), reordered.sort(
        ['available_us', 'symbol']).select('target_weight', 'raw_signed_target').to_numpy(),
        rtol=0, atol=1e-13)
    future = bars.with_columns([pl.when(pl.col('close_us') > decisions[3])
        .then(pl.col(field) * 1000).otherwise(pl.col(field)).alias(field)
        for field in ('open', 'high', 'low', 'close')])
    prefix, prefix_meta = target.fixed_targets(future, decisions[:4],
        symbols=symbols, allocation='ACTIVE_EQUAL')
    assert prefix.equals(active.filter(pl.col('available_us') <= decisions[3]))
    assert prefix_meta['risk'] == meta['risk'][:4]
    cash, cash_meta = target.fixed_targets(bars, decisions, 'CASH',
        symbols=symbols, allocation='ACTIVE_EQUAL')
    assert cash['target_weight'].eq(0.).all() and cash['raw_signed_target'].eq(0.).all()
    assert all(r['active_signal_count'] == 0 for r in cash_meta['risk'])

    # Missing bars and explicit pool exits remain in the ordered account;
    # neither becomes an active signal eligible for redistributed capital.
    missing = bars.filter(~((pl.col('symbol') == symbols[0]) & (pl.col('close_us') == 2 * day)))
    absent, absent_meta = target.fixed_targets(missing, decisions[2:3],
        symbols=symbols, allocation='ACTIVE_EQUAL')
    assert absent['eligibility_reason'].to_list() == ['WARMUP_OR_DATA_GAP', 'ELIGIBLE', 'ELIGIBLE']
    assert absent_meta['risk'][0]['active_signal_count'] == 0
    exited, exited_meta = target.fixed_targets(bars, decisions[2:3], symbols=symbols,
        eligible_by_decision={int(decisions[2]): symbols[1:]}, allocation='ACTIVE_EQUAL')
    assert exited['eligibility_reason'].to_list() == ['POOL_EXIT', 'ELIGIBLE', 'ELIGIBLE']
    assert exited_meta['risk'][0]['active_signal_count'] == 0

    # A breakout below SMA200 cannot become active merely to consume budget.
    blocked = bars.with_columns([pl.when(pl.col('symbol') == symbols[0]).then(
        pl.when(pl.col('open_us') < 180 * day).then(200.).otherwise(
        pl.when(pl.col('open_us') < 200 * day).then(90.).otherwise(100.)))
        .otherwise(pl.col(field)).alias(field) for field in ('open', 'close')])
    blocked = blocked.with_columns(pl.when(pl.col('symbol') == symbols[0])
        .then(pl.col('close') + 1.).otherwise(pl.col('high')).alias('high'),
        pl.when(pl.col('symbol') == symbols[0]).then(pl.col('close') - 1.)
        .otherwise(pl.col('low')).alias('low'))
    failed_filter, filter_meta = target.fixed_targets(blocked, decisions[2:3],
        symbols=symbols, allocation='ACTIVE_EQUAL')
    assert failed_filter['raw_signed_target'].eq(0.).all()
    assert filter_meta['risk'][0]['active_signal_count'] == 0

    # The reused signed covariance guard still controls zero-net portfolios;
    # cancellation in net weight must not skip the gross or variance check.
    returns = np.column_stack([np.tile([.1, -.1], 15),
        np.tile([-.1, .1], 15), np.tile([.05, -.05], 15)])
    signed_raw = np.asarray([.3, -.3, 0.])
    signed_expected, signed_sigma = reference_risk(signed_raw, returns)
    signed_actual, signed_meta = shared.signed_risk_weights(signed_raw, returns)
    assert signed_sigma > .10
    assert np.allclose(signed_actual, signed_expected, rtol=0, atol=1e-13)
    assert signed_meta['net_target_weight'] == pytest.approx(0.)
    assert 0. < signed_meta['gross_target_weight'] < .6
