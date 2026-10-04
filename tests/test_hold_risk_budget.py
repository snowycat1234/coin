"""One independent covariance fixture for the fixed HOLD 8% risk challenge."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_sma_perpetual as shared
from scripts.investment import vol_managed_perpetual_target as target


def test_hold_eight_percent_budget_is_causal_scale_down_not_new_cap(monkeypatch):
    day = shared.DAY_US
    symbols = ('ZZZUSDT', 'AAAUSDT')
    length = 208
    shocks = np.resize(np.array([.045, -.037, .029, -.042, .034, -.025]), length - 1)
    second = .65 * shocks + np.resize(np.array([.004, -.003, -.002, .003]), length - 1)

    def bars_for(multiplier):
        paths = {symbols[0]: np.r_[100., 100. * np.cumprod(1. + multiplier * shocks)],
                 symbols[1]: np.r_[70., 70. * np.cumprod(1. + multiplier * second)]}
        opens = np.arange(length, dtype=np.int64) * day
        bars = pl.concat([pl.DataFrame(dict(symbol=[s] * length, open_us=opens,
            close_us=opens + day, available_us=opens + day, open=paths[s],
            high=paths[s] * 1.001, low=paths[s] * .999, close=paths[s],
            volume=np.ones(length))) for s in symbols])
        return bars, paths

    def reference(raw, returns, budget):
        # Independent scalar centering and cross-products; no production sizing
        # or np.cov calls. Signed off-diagonal contributions are retained.
        weights = [max(-.3, min(.3, float(value))) for value in raw]
        gross = math.fsum(abs(value) for value in weights)
        if gross > .6:
            weights = [value * .6 / gross for value in weights]
        rows = np.asarray(returns)[-30:]
        means = [math.fsum(float(row[j]) for row in rows) / 30 for j in range(len(weights))]
        covariance = [[365 * math.fsum((float(row[i]) - means[i]) *
            (float(row[j]) - means[j]) for row in rows) / 29
            for j in range(len(weights))] for i in range(len(weights))]
        variance = math.fsum(weights[i] * covariance[i][j] * weights[j]
            for i in range(len(weights)) for j in range(len(weights)))
        sigma = math.sqrt(max(variance, 0.))
        scale = min(1., budget / sigma) if sigma else 1.
        return np.array([value * scale for value in weights]), sigma

    def forbidden_sma():
        raise AssertionError('HOLD must reuse constant direction, not SMA alpha')
    monkeypatch.setattr(shared.public, '_load_public_hooks', forbidden_sma)
    bars, paths = bars_for(1.)
    decisions = np.arange(199, 208, dtype=np.int64) * day
    default, default_meta = target.fixed_targets(bars, decisions, symbols=symbols)
    ten, ten_meta = target.fixed_targets(bars, decisions, symbols=symbols, annual_vol_target=.10)
    eight, eight_meta = target.fixed_targets(bars, decisions, symbols=symbols, annual_vol_target=.08)
    assert default.equals(ten) and default_meta == ten_meta
    assert ten_meta['rules']['annual_volatility_target'] == .10
    assert eight_meta['rules']['annual_volatility_target'] == .08
    other_ten = {k: v for k, v in ten_meta['rules'].items() if k != 'annual_volatility_target'}
    other_eight = {k: v for k, v in eight_meta['rules'].items() if k != 'annual_volatility_target'}
    assert other_ten == other_eight
    assert target.RULES['annual_volatility_target'] == .10  # No global rule mutation.
    assert eight.filter(pl.col('available_us') == decisions[0])['target_weight'].to_list() == [0., 0.]
    for offset, decision in enumerate(decisions[1:], start=1):
        index = int(decision // day) - 1
        past = np.column_stack([np.diff(paths[s][index - 30:index + 1]) /
            paths[s][index - 30:index] for s in symbols])
        expected_ten, sigma = reference([.3, .3], past, .10)
        expected_eight, _ = reference([.3, .3], past, .08)
        assert sigma > .10  # Both budgets bind in this volatility regime.
        for frame, meta, expected in ((ten, ten_meta, expected_ten), (eight, eight_meta, expected_eight)):
            rows = frame.filter(pl.col('available_us') == decision)
            assert rows['symbol'].to_list() == list(symbols)
            assert rows['raw_signed_target'].to_list() == [.3, .3]
            np.testing.assert_allclose(rows['target_weight'].to_numpy(), expected, rtol=0, atol=1e-12)
            risk = meta['risk'][offset]
            assert risk['covariance_symbol_order'] == list(symbols)
            assert risk['covariance_observations'] == 30 and risk['past_only']
            assert risk['unscaled_signed_covariance_annual_vol'] == pytest.approx(sigma, abs=1e-12)
            assert risk['gross_target_weight'] == pytest.approx(math.fsum(abs(w) for w in expected))
            assert max(abs(w) for w in expected) <= .3 and math.fsum(abs(w) for w in expected) <= .6
        np.testing.assert_allclose(expected_eight, .8 * expected_ten, rtol=0, atol=1e-12)

    # The new budget is a ceiling, not a mandate to increase exposure in calm
    # markets or to multiply all saved NAV/targets by .8 after the fact.
    calm, calm_paths = bars_for(.001)
    calm_eight, _ = target.fixed_targets(calm, decisions[1:], symbols=symbols, annual_vol_target=.08)
    calm_ten, _ = target.fixed_targets(calm, decisions[1:], symbols=symbols, annual_vol_target=.10)
    assert calm_eight.equals(calm_ten)
    assert calm_eight['target_weight'].to_list() == [.3] * calm_eight.height
    calm_index = int(decisions[-1] // day) - 1
    calm_returns = np.column_stack([np.diff(calm_paths[s][calm_index - 30:calm_index + 1]) /
        calm_paths[s][calm_index - 30:calm_index] for s in symbols])
    _, calm_sigma = reference([.3, .3], calm_returns, .08)
    assert 0 < calm_sigma < .08

    # Zero net does not waive gross or covariance risk. Excess individual raw
    # sizes are capped before evaluating a signed, anti-correlated portfolio.
    opposite = np.column_stack((shocks[-30:], -shocks[-30:]))
    signed_expected, signed_sigma = reference([.9, -.9], opposite, .08)
    signed_actual, signed_risk = shared.signed_risk_weights([.9, -.9], opposite, annual_vol_target=.08)
    assert signed_sigma > .10 and abs(math.fsum(signed_actual)) < 1e-12
    np.testing.assert_allclose(signed_actual, signed_expected, rtol=0, atol=1e-12)
    assert 0 < signed_risk['gross_target_weight'] < .6

    reversed_frame, reversed_meta = target.fixed_targets(bars.reverse(), decisions,
        symbols=tuple(reversed(symbols)), annual_vol_target=.08)
    assert reversed_meta['risk'][-1]['covariance_symbol_order'] == list(reversed(symbols))
    np.testing.assert_allclose(eight.sort(['available_us', 'symbol'])['target_weight'].to_numpy(),
        reversed_frame.sort(['available_us', 'symbol'])['target_weight'].to_numpy(), rtol=0, atol=1e-12)
    cut = int(decisions[4])
    future = bars.with_columns([pl.when(pl.col('close_us') > cut).then(pl.col(k) * 7)
        .otherwise(pl.col(k)).alias(k) for k in ('open', 'high', 'low', 'close')])
    perturbed, perturbed_meta = target.fixed_targets(future, decisions, symbols=symbols, annual_vol_target=.08)
    assert eight.filter(pl.col('available_us') <= cut).equals(perturbed.filter(pl.col('available_us') <= cut))
    assert eight_meta['risk'][:5] == perturbed_meta['risk'][:5]
    cash, _ = shared.fixed_targets(bars, decisions, 'CASH', symbols=symbols,
        direction_factory=target._ConstantLongDirection, annual_vol_target=.08)
    assert cash['target_weight'].to_list() == [0.] * cash.height

    # Fail before warmup/CASH can accidentally evade validation. No files,
    # synthetic ROOT, market source or live collector are involved in this test.
    for invalid in (0., float('nan'), .100001):
        with pytest.raises(ValueError):
            target.fixed_targets(bars, decisions[:1], symbols=symbols, annual_vol_target=invalid)
        with pytest.raises(ValueError):
            shared.fixed_targets(bars, decisions[:1], 'CASH', symbols=symbols,
                direction_factory=target._ConstantLongDirection, annual_vol_target=invalid)
