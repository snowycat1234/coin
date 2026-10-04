"""Independent daily states and covariance verify a fixed target, not NAV, blend."""
import math

import numpy as np
import polars as pl
import pytest

from scripts.investment import hold_donchian_blend_target as target
from scripts.investment import multi_asset_financial_audit as independent


def test_half_hold_half_exit10_is_causal_component_target_blend(monkeypatch):
    day = 86_400_000_000
    symbols = ('ZZZUSDT', 'AAAUSDT')
    a = np.r_[np.full(199, 100.), [100., 110., 112., 98., 110., 116., 117., 118., 120.]]
    b = np.r_[np.full(199, 200.), [200., 200., 200., 205., 205., 190., 208., 209., 210.]]
    prices = dict(zip(symbols, (a, b), strict=True))
    opens = np.arange(len(a), dtype=np.int64) * day
    bars = pl.concat([pl.DataFrame(dict(symbol=[s] * len(a), open_us=opens,
        close_us=opens + day, available_us=opens + day, open=prices[s],
        high=prices[s] + 1., low=prices[s] - 1., close=prices[s],
        volume=np.ones(len(a)))) for s in symbols])
    decisions = np.arange(200, 209, dtype=np.int64) * day

    def reference(frame, order=symbols, membership=None, times=decisions):
        window = dict(start=int(times[0]), end=int(times[-1]) + day,
            bars={s: frame.filter(pl.col('symbol') == s).sort('close_us') for s in order})
        if membership is not None:
            window['eligible_by_decision'] = membership
        def forbidden(*args, **kwargs):
            raise AssertionError('Direct financial reference called production blend targets')
        with monkeypatch.context() as patch:
            patch.setattr(target, 'fixed_targets', forbidden)
            return independent.target_reference(window, order, target.ALLOCATION,
                strategy_id=target.STRATEGY_ID, exit_period=10, reentry_period=20)

    actual, meta = target.fixed_targets(bars, decisions, symbols=symbols)
    ref = reference(bars)
    assert meta['strategy_id'] == target.STRATEGY_ID
    assert meta['rules']['hold_weight'] == meta['rules']['donchian_weight'] == .5
    assert meta['rules']['blend_stage'] == 'AFTER_COMPONENT_RISK_SCALING_NO_EXTRA_RESCALE'
    assert meta['rules']['separate_component_capital'] is False
    assert meta['rules']['component_NAVs_averaged'] is False
    assert actual.columns == ref.columns and actual.height == 2 * len(decisions)
    keys = ['available_us', 'symbol', 'mode', 'eligibility_reason']
    assert actual.select(keys).equals(ref.select(keys))
    np.testing.assert_allclose(actual.select('raw_signed_target', 'target_weight').to_numpy(),
        ref.select('raw_signed_target', 'target_weight').to_numpy(), rtol=0, atol=1e-12)

    def sized(raw, covariance):
        sigma = math.sqrt(max(math.fsum(raw[i] * covariance[i][j] * raw[j]
            for i in range(2) for j in range(2)), 0.))
        return raw * min(1., .10 / sigma) if sigma else raw

    held = [False, False]
    scaled_components_differ = False
    for decision in decisions:
        i = int(decision // day) - 1
        for j, symbol in enumerate(symbols):
            p = prices[symbol]
            previous20_high = max(p[i - 20:i] + 1.)
            previous10_low = min(p[i - 10:i] - 1.)
            trend = math.fsum(float(x) for x in p[i - 199:i + 1]) / 200
            if held[j]:
                held[j] = not (p[i] < previous10_low)
            else:
                held[j] = bool(p[i] > previous20_high and p[i] > trend)
        hold_raw = np.array([.3, .3])
        timing_raw = np.array(held, dtype=float) * .3
        history = np.column_stack([prices[s][i - 30:i + 1] for s in symbols])
        returns = np.diff(history, axis=0) / history[:-1]
        means = [math.fsum(float(row[j]) for row in returns) / 30 for j in range(2)]
        cov = [[365 * math.fsum((float(row[k]) - means[k]) * (float(row[j]) - means[j])
            for row in returns) / 29 for j in range(2)] for k in range(2)]
        hold_target, timing_target = sized(hold_raw, cov), sized(timing_raw, cov)
        wanted = .5 * hold_target + .5 * timing_target
        blended_raw = .5 * hold_raw + .5 * timing_raw
        scaled_components_differ |= not np.allclose(wanted, sized(blended_raw, cov), rtol=0, atol=1e-12)
        rows = actual.filter(pl.col('available_us') == decision)
        assert rows['symbol'].to_list() == list(symbols)
        np.testing.assert_allclose(rows['raw_signed_target'].to_numpy(), blended_raw, rtol=0, atol=1e-13)
        np.testing.assert_allclose(rows['target_weight'].to_numpy(), wanted, rtol=0, atol=1e-12)
        risk = meta['risk'][int(decision // day) - 200]
        np.testing.assert_allclose(risk['component_HOLD_target'], hold_target, rtol=0, atol=1e-12)
        np.testing.assert_allclose(risk['component_EXIT10_target'], timing_target, rtol=0, atol=1e-12)
        assert risk['covariance_symbol_order'] == list(symbols) and risk['past_only']
        assert (rows['target_weight'] >= 0).all()
        assert max(abs(wanted)) <= .3 and math.fsum(abs(v) for v in wanted) <= .6
    assert scaled_components_differ  # Mixing raw then rescaling would be a different experiment.
    first = actual.filter(pl.col('available_us') == decisions[0])
    assert first['raw_signed_target'].to_list() == [.15, .15]
    assert first['target_weight'].to_list() == [.15, .15]  # Both timing signals flat, unused half stays cash.
    assert actual.filter((pl.col('available_us') == 203 * day) &
        (pl.col('symbol') == symbols[0]))['raw_signed_target'][0] == .15  # Exit10 to half HOLD.
    assert actual.filter((pl.col('available_us') == 204 * day) &
        (pl.col('symbol') == symbols[0]))['raw_signed_target'][0] == .15  # No prior20 recovery yet.
    assert actual.filter((pl.col('available_us') == 205 * day) &
        (pl.col('symbol') == symbols[0]))['raw_signed_target'][0] == .3   # Genuine prior20 recovery.

    reversed_symbols = tuple(reversed(symbols))
    reversed_frame, _ = target.fixed_targets(bars.reverse(), decisions, symbols=reversed_symbols)
    reversed_ref = reference(bars.reverse(), reversed_symbols)
    for frame in (reversed_frame, reversed_ref):
        assert frame.filter(pl.col('available_us') == decisions[0])['symbol'].to_list() == list(reversed_symbols)
        np.testing.assert_allclose(actual.sort(['available_us', 'symbol'])['target_weight'].to_numpy(),
            frame.sort(['available_us', 'symbol'])['target_weight'].to_numpy(), rtol=0, atol=1e-12)

    cut = int(decisions[3])
    future = bars.with_columns([pl.when(pl.col('close_us') > cut).then(pl.col(k) * 7)
        .otherwise(pl.col(k)).alias(k) for k in ('open', 'high', 'low', 'close')])
    poisoned, _ = target.fixed_targets(future, decisions, symbols=symbols)
    poisoned_ref = reference(future)
    prefix = actual.filter(pl.col('available_us') <= cut)
    assert prefix.equals(poisoned.filter(pl.col('available_us') <= cut))
    np.testing.assert_allclose(prefix['target_weight'].to_numpy(),
        poisoned_ref.filter(pl.col('available_us') <= cut)['target_weight'].to_numpy(), rtol=0, atol=1e-12)

    membership = {int(d): symbols for d in decisions}
    membership[202 * day] = (symbols[1],)
    removed, _ = target.fixed_targets(bars, decisions, symbols=symbols, eligible_by_decision=membership)
    one = removed.filter((pl.col('available_us') == 202 * day) & (pl.col('symbol') == symbols[0]))
    assert one['target_weight'][0] == one['raw_signed_target'][0] == 0.
    assert one['eligibility_reason'][0] == 'POOL_EXIT'
    # On return, the old timing position must not survive the membership reset.
    assert removed.filter((pl.col('available_us') == 203 * day) &
        (pl.col('symbol') == symbols[0]))['raw_signed_target'][0] == .15
    removed_ref = reference(bars, membership=membership)
    assert removed.select(keys).equals(removed_ref.select(keys))
    np.testing.assert_allclose(removed.select('raw_signed_target', 'target_weight').to_numpy(),
        removed_ref.select('raw_signed_target', 'target_weight').to_numpy(), rtol=0, atol=1e-12)
    gap = bars.filter(~((pl.col('symbol') == symbols[0]) & (pl.col('close_us') == 100 * day)))
    missing, _ = target.fixed_targets(gap, decisions, symbols=symbols)
    unavailable = missing.filter(pl.col('symbol') == symbols[0])
    assert unavailable['target_weight'].to_list() == [0.] * len(decisions)
    assert unavailable['eligibility_reason'].to_list() == ['WARMUP_OR_DATA_GAP'] * len(decisions)
    missing_ref = reference(gap)
    np.testing.assert_allclose(missing.select('raw_signed_target', 'target_weight').to_numpy(),
        missing_ref.select('raw_signed_target', 'target_weight').to_numpy(), rtol=0, atol=1e-12)
    warm_times = np.array([199 * day], dtype=np.int64)
    warming, _ = target.fixed_targets(bars, warm_times, symbols=symbols)
    assert warming['target_weight'].to_list() == [0., 0.]
    assert warming.equals(reference(bars, times=warm_times))

    # A tiny third-member probe catches a blend or reference that quietly sizes
    # HOLD as two assets. The third timing signal remains flat and keeps cash.
    third = bars.filter(pl.col('symbol') == symbols[1]).with_columns(
        pl.lit('MMMUSDT').alias('symbol'))
    three_bars, three_symbols = pl.concat([bars, third]), symbols + ('MMMUSDT',)
    three, _ = target.fixed_targets(three_bars, decisions[:2], symbols=three_symbols)
    three_ref = reference(three_bars, three_symbols, times=decisions[:2])
    np.testing.assert_allclose(three.select('raw_signed_target', 'target_weight').to_numpy(),
        three_ref.select('raw_signed_target', 'target_weight').to_numpy(), rtol=0, atol=1e-12)
    np.testing.assert_allclose(three.filter(pl.col('available_us') == decisions[0])['raw_signed_target'].to_numpy(),
        [.1] * 3, rtol=0, atol=1e-13)
    np.testing.assert_allclose(three.filter(pl.col('available_us') == decisions[1])['raw_signed_target'].to_numpy(),
        [.25, .1, .1], rtol=0, atol=1e-13)
    with pytest.raises((TypeError, ValueError)):
        target.fixed_targets(bars, decisions, symbols=symbols, hold_weight=.6)
    # Arrays are synthetic and in memory; no saved NAVs or independent account
    # balances are averaged. The actual shared account is verified separately.
