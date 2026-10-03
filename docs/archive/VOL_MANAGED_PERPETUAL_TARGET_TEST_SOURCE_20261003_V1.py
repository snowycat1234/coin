"""ONE UNRUN D044 case: constant-long direction, shared causal risk and calendar."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_sma_perpetual as shared
from scripts.investment import vol_managed_perpetual_target as target
from scripts.investment import perpetual_hold_research as research


def test_fixed_hold_uses_causal_shared_risk_and_calendar(monkeypatch):
    day = target.DAY_US
    first = 1_704_067_200_000_000  # 2024-01-01 UTC, within the distinct213-day profile.
    stamps = first + (np.arange(208, dtype=np.int64) - 199) * day
    pattern = np.array([.035, -.028, .042, -.038, .019, -.021, .026, -.032])
    changes = np.resize(pattern, 207)
    btc = np.r_[100., 100. * np.cumprod(1. + changes)]
    eth_changes = .7 * changes + np.resize(np.array([.005, -.006, -.004, .005]), 207)
    eth = np.r_[70., 70. * np.cumprod(1. + eth_changes)]
    bars = pl.DataFrame([
        dict(symbol=symbol, open_us=int(stamp-day), close_us=int(stamp), available_us=int(stamp),
            open=float(price), high=float(price*1.001), low=float(price*.999),
            close=float(price), volume=1000.)
        for symbol, prices in zip(('BTCUSDT', 'ETHUSDT'), (btc, eth), strict=True)
        for stamp, price in zip(stamps, prices, strict=True)])
    decisions = stamps[199:207]

    def covariance_reference(raw, returns):
        # Independent centered sample-covariance arithmetic, not the production kernel.
        r = np.asarray(returns, dtype=np.float64)[-30:]
        mean = [math.fsum(map(float, r[:,i]))/30 for i in range(2)]
        covariance = np.array([[365 * math.fsum(
            (float(row[i])-mean[i])*(float(row[j])-mean[j]) for row in r)/29
            for j in range(2)] for i in range(2)])
        weights = np.asarray(raw, dtype=np.float64)
        sigma = math.sqrt(max(math.fsum(float(weights[i]*covariance[i,j]*weights[j])
            for i in range(2) for j in range(2)), 0.))
        scale = .10/sigma if sigma > .10 else 1.
        return weights*scale, sigma

    original_modes, original_public = shared.MODES, shared.public
    def forbidden_alpha():
        raise AssertionError('The constant-long benchmark must not execute original SMA hooks')
    monkeypatch.setattr(shared.public, '_load_public_hooks', forbidden_alpha)
    frame, receipt = target.fixed_targets(bars, decisions)
    assert shared.MODES is original_modes and shared.public is original_public
    assert target.signed_risk_weights is shared.signed_risk_weights
    assert frame.columns == ['available_us', 'symbol', 'target_weight', 'raw_signed_target', 'mode']
    assert frame.height == 2*len(decisions) and frame['raw_signed_target'].to_list() == [.3]*frame.height
    assert frame['target_weight'].min() > 0 and frame['target_weight'].max() < .3
    assert frame['available_us'].min() == first  # No warmup targets or warmup holdings.
    assert receipt['mode'] == 'LONG_ONLY' and receipt['original_SMA_alpha_used'] is False
    assert receipt['original_long_and_short_and_exit_hooks_reused'] is False
    assert receipt['Spot_EWMA_strategy_replicated'] is False
    assert receipt['funding_rates_used_for_signal'] is False
    assert 'fast_period' not in receipt and 'slow_period' not in receipt
    assert receipt['candidate_status'] == 'NO_QUALIFIED_CANDIDATE'
    derivation = receipt['namespace_derivation']
    assert len(derivation) == 1 and derivation[0]['changes'] == []
    assert derivation[0]['original_AST_sha256'] == derivation[0]['derived_AST_sha256']
    for offset, decision in enumerate(decisions):
        index = 199 + offset
        returns = np.column_stack((np.diff(btc[index-30:index+1])/btc[index-30:index],
            np.diff(eth[index-30:index+1])/eth[index-30:index]))
        expected, sigma = covariance_reference([.3, .3], returns)
        observed = frame.filter(pl.col('available_us') == int(decision))['target_weight'].to_numpy()
        np.testing.assert_allclose(observed, expected, rtol=0., atol=1e-12)
        proof = receipt['risk'][offset]
        assert sigma > .10 and proof['past_only'] is True and proof['covariance_observations'] == 30
        assert abs(proof['unscaled_signed_covariance_annual_vol']-sigma) <= 1e-12
        assert abs(proof['gross_target_weight']-float(np.abs(expected).sum())) <= 1e-12

    # Exact zero net target still has risk when the legs are anticorrelated.
    opposite = np.column_stack((changes[-30:], -changes[-30:]))
    expected, sigma = covariance_reference([.3, -.3], opposite)
    actual, risk = target.signed_risk_weights([.3, -.3], opposite)
    np.testing.assert_allclose(actual, expected, rtol=0., atol=1e-12)
    assert sigma > .10 and abs(actual.sum()) <= 1e-12 and 0 < np.abs(actual).sum() < .6
    assert risk['gross_target_weight'] > 0 and risk['past_only'] is True

    cut = int(decisions[3])
    poisoned = bars.with_columns(*[
        pl.when(pl.col('close_us') > cut).then(pl.col(name)*7).otherwise(pl.col(name)).alias(name)
        for name in ('open', 'high', 'low', 'close')])
    changed, changed_receipt = target.fixed_targets(poisoned, decisions)
    assert frame.filter(pl.col('available_us') <= cut).equals(
        changed.filter(pl.col('available_us') <= cut))
    assert receipt['risk'][:4] == changed_receipt['risk'][:4]
    with pytest.raises(ValueError, match='Integer nonnegative'):
        target.fixed_targets(bars, decisions.astype(float)+.5)
    with pytest.raises(ValueError, match='Complete independent scoring-day'):
        target.fixed_targets(bars, decisions+1)
    with pytest.raises(ValueError, match='Contiguous daily'):
        target.fixed_targets(bars.filter(~((pl.col('symbol') == 'BTCUSDT')
            & (pl.col('close_us') == int(stamps[100])))), decisions)
    with pytest.raises(ValueError, match='Exactly200 completed available'):
        target.fixed_targets(bars.filter(pl.col('close_us') >= first-198*day), decisions)
    delayed = bars.with_columns(pl.when((pl.col('symbol') == 'ETHUSDT')
        & (pl.col('close_us') == first-7*day)).then(pl.lit(first+day))
        .otherwise(pl.col('available_us')).alias('available_us'))
    with pytest.raises(ValueError, match='Exactly200 completed available'):
        target.fixed_targets(delayed, decisions)
    with pytest.raises(ValueError, match='one fixed LONG_ONLY'):
        target.fixed_targets(bars, decisions, 'SHORT_ONLY')
    # New research metadata routing compiles before arrays, without a source read.
    # The artificial manifest is deliberately not an accepted source qualification.
    manifest = dict(status=research.MANIFEST_STATUS, source_files={str(i):{} for i in range(156)},
        windows=[dict(id=identity, start=start, end_exclusive=end, days=days)
            for identity,start,end,days in research.WINDOWS])
    calls = []
    def metadata_only(proof):
        calls.append(proof)
        return manifest
    monkeypatch.setattr(research.base, 'relative_proof', metadata_only)
    spec = dict(contract_id=research.CONTRACT, rules=research.RULES,
        period_ids=research.PERIODS, cost_scenarios=research.base.COSTS,
        unit_scenarios=research.base.UNITS, frozen_sources=dict(research.PINS),
        input_manifest={'synthetic_metadata_only':True})
    wired = research.context(spec)
    assert calls == [spec['input_manifest']]
    strategy = wired['simulate'].__globals__['strategy']
    assert strategy.MODES == ('LONG_ONLY',) and strategy.fixed_targets is target.fixed_targets
    assert wired['main'].__globals__['strategy'] is strategy
    assert research.STRATEGY_ID == target.STRATEGY_ID
    assert len(research.PERIODS)*len(research.base.COSTS)*len(research.base.UNITS)*len(strategy.MODES) == 12
    simulation = next(row for row in wired['derivation'] if row['function'] == 'simulate')
    assert simulation['changes'] == []
    assert simulation['original_AST_sha256'] == simulation['derived_AST_sha256']