"""Actual two-asset EXIT10 targets versus direct independent financial windows."""
import math

import numpy as np
import polars as pl

from scripts.investment import donchian_daily_pool_target as target
from scripts.investment import multi_asset_financial_audit as independent


def test_two_asset_exit10_active_budget_matches_direct_windows_and_past_risk(monkeypatch):
    day = target.DAY_US
    symbols = ('ZZZUSDT', 'AAAUSDT')  # Account order deliberately differs from sort order.
    a = np.r_[np.full(199, 100.), [110., 112., 114., 98., 110., 116., 117., 118.]]
    b = np.r_[np.full(199, 200.), [200., 200., 200., 205., 205., 190., 208., 209.]]
    prices = dict(zip(symbols, (a, b), strict=True))
    opens = np.arange(len(a), dtype=np.int64) * day
    bars = pl.concat([pl.DataFrame(dict(symbol=[s] * len(a), open_us=opens,
        close_us=opens + day, available_us=opens + day, open=prices[s],
        high=prices[s] + 1., low=prices[s] - 1., close=prices[s],
        volume=np.ones(len(a)))) for s in symbols])
    decisions = np.arange(200, 208, dtype=np.int64) * day
    kwargs = dict(symbols=symbols, allocation='ACTIVE_EQUAL', exit_period=10, reentry_period=20)
    produced, meta = target.fixed_targets(bars, decisions, **kwargs)

    def reference(frame, order=symbols, end=int(decisions[-1]) + day):
        window = dict(start=int(decisions[0]), end=end,
            bars={s: frame.filter(pl.col('symbol') == s).sort('close_us') for s in order})
        # A financial reference must remain a direct window/state implementation,
        # rather than secretly calling the production strategy target factory.
        def forbidden_factory(*args, **options):
            raise AssertionError('Independent financial reference called producer target factory')
        with monkeypatch.context() as patch:
            patch.setattr(target, 'fixed_targets', forbidden_factory)
            result = independent.target_reference(window, order, 'ACTIVE_EQUAL',
                strategy_id=target.strategy_id(10, 20), exit_period=10, reentry_period=20)
        return result, window['independent_Donchian_state_witnesses']

    expected, witnesses = reference(bars)
    assert produced.columns == expected.columns and produced.height == 16
    identity = ['available_us', 'symbol', 'mode', 'eligibility_reason', 'raw_signed_target']
    assert produced.select(identity).equals(expected.select(identity))
    np.testing.assert_allclose(produced['target_weight'].to_numpy(), expected['target_weight'].to_numpy(),
        rtol=0, atol=1e-12)
    assert meta['rules']['exit_period'] == 10 and meta['rules'].get('reentry_period', 20) == 20
    assert meta['strategy_id'] == target.strategy_id(10, 20)
    assert len(witnesses) == 16 and all(w['channel_excludes_current'] for w in witnesses)

    # Hand state sequence distinguishes entry, held position, real exit, delayed
    # prior20 recovery and two simultaneously active members. The idle member's
    # budget cannot push a single asset above .3, even though gross permits .6.
    states = np.array([[1, 0], [1, 0], [1, 0], [0, 1], [0, 1], [1, 0], [1, 1], [1, 1]])
    for offset, decision in enumerate(decisions):
        index = int(decision // day) - 1
        raw = states[offset] * .3
        rows = produced.filter(pl.col('available_us') == decision)
        assert rows['symbol'].to_list() == list(symbols)
        np.testing.assert_allclose(rows['raw_signed_target'].to_numpy(), raw, rtol=0, atol=0)
        history = np.column_stack([prices[s][index - 30:index + 1] for s in symbols])
        returns = np.diff(history, axis=0) / history[:-1]
        means = [math.fsum(float(row[j]) for row in returns) / 30 for j in range(2)]
        covariance = [[365 * math.fsum((float(row[i]) - means[i]) *
            (float(row[j]) - means[j]) for row in returns) / 29 for j in range(2)] for i in range(2)]
        variance = math.fsum(raw[i] * covariance[i][j] * raw[j] for i in range(2) for j in range(2))
        sigma = math.sqrt(max(variance, 0.))
        hand = raw * min(1., .10 / sigma) if sigma else raw
        np.testing.assert_allclose(rows['target_weight'].to_numpy(), hand, rtol=0, atol=1e-12)
        assert not (rows['target_weight'] < 0).any()
        assert max(abs(hand)) <= .3 and math.fsum(abs(v) for v in hand) <= .6
        assert meta['risk'][offset]['covariance_symbol_order'] == list(symbols)
        assert meta['risk'][offset]['covariance_observations'] == 30
        assert meta['risk'][offset]['active_signal_count'] == int(states[offset].sum())
    assert (produced['target_weight'] < produced['raw_signed_target']).any()  # Actual risk scaling binds.

    reversed_order = tuple(reversed(symbols))
    reversed_actual, _ = target.fixed_targets(bars.reverse(), decisions, **dict(kwargs, symbols=reversed_order))
    reversed_expected, _ = reference(bars.reverse(), reversed_order)
    for comparison in (reversed_actual, reversed_expected):
        assert comparison.filter(pl.col('available_us') == decisions[0])['symbol'].to_list() == list(reversed_order)
        np.testing.assert_allclose(produced.sort(['available_us', 'symbol'])['target_weight'].to_numpy(),
            comparison.sort(['available_us', 'symbol'])['target_weight'].to_numpy(), rtol=0, atol=1e-12)

    cut = int(decisions[3])
    future = bars.with_columns([pl.when(pl.col('close_us') > cut).then(pl.col(k) * 7)
        .otherwise(pl.col(k)).alias(k) for k in ('open', 'high', 'low', 'close')])
    changed, changed_meta = target.fixed_targets(future, decisions, **kwargs)
    changed_reference, _ = reference(future)
    prefix = produced.filter(pl.col('available_us') <= cut)
    assert prefix.equals(changed.filter(pl.col('available_us') <= cut))
    np.testing.assert_allclose(prefix['target_weight'].to_numpy(),
        changed_reference.filter(pl.col('available_us') <= cut)['target_weight'].to_numpy(), rtol=0, atol=1e-12)
    assert meta['risk'][:4] == changed_meta['risk'][:4]
    # All market fixture arrays live in memory. The normal pinned strategy code
    # is reused, but no market store, synthetic ROOT or QA output is created.
