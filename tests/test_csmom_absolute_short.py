"""One fixed absolute-sign confirmation; no wallet or parameter search here."""
import numpy as np

from scripts.research.public_cross_section_momentum import ANCHOR_US, public_targets
from test_public_cross_section_momentum import SYMBOLS, history


def targets(close, times, decisions, *, enabled=None, symbols=SYMBOLS):
    options = {} if enabled is None else {'short_absolute_confirmation': enabled}
    return public_targets(close, times, decisions, symbols, symbols, **options)


def test_default_false_exact_and_positive_market_keeps_long_direction():
    close, times = history()
    close *= np.exp(np.arange(len(times))[:, None] * .01)
    decisions = times[70:]
    original, old_diag = targets(close, times, decisions)
    disabled, disabled_diag = targets(close, times, decisions, enabled=False)
    np.testing.assert_array_equal(disabled, original)
    assert disabled_diag == old_diag
    assert np.any(original < 0)
    confirmed, diag = targets(close, times, decisions, enabled=True)
    assert np.all(confirmed >= 0)
    np.testing.assert_array_equal(confirmed > 0, original > 0)
    assert diag['rank_events'] == old_diag['rank_events']
    # Filtering shorts does not redistribute their raw capital to the longs.
    # A necessary second covariance check may only reduce final long sizes.
    assert np.all(confirmed <= np.maximum(original, 0.) + 1e-14)
    assert np.max(confirmed) <= .15 + 1e-12
    assert np.max(np.abs(confirmed).sum(1)) <= .3 + 1e-12


def test_all_negative_absolute_momentum_preserves_original_shorts_exactly():
    close, times = history()
    close *= np.exp(-np.arange(len(times))[:, None] * .01)
    original, before = targets(close, times, times[70:], enabled=False)
    confirmed, after = targets(close, times, times[70:], enabled=True)
    assert np.any(original < 0)
    np.testing.assert_allclose(confirmed, original, atol=1e-14, rtol=0)
    assert after['rank_events'] == before['rank_events']


def test_midweek_positive_veto_then_negative_restores_same_ranked_short():
    close, times = history()
    # Monday index70 ranks BTC short. Wednesday/Thursday absolute21d becomes
    # positive; Friday returns to the original negative absolute21d path.
    close[72:74, 0] = close[51:53, 0] * 1.02
    decisions = times[70:77]
    original, before = targets(close, times, decisions, enabled=False)
    confirmed, after = targets(close, times, decisions, enabled=True)
    assert original[0, 0] < 0 and confirmed[0, 0] < 0
    assert np.all(original[2:4, 0] < 0)
    assert np.all(confirmed[2:4, 0] == 0)
    assert confirmed[4, 0] < 0
    assert after['rank_us'] == [ANCHOR_US] * 7
    assert after['rank_events'] == before['rank_events']
    np.testing.assert_array_equal(confirmed > 0, original > 0)
    # Once confirmation is again negative, the unchanged raw ranking and
    # identical current covariance inputs recover the baseline target; allow
    # only Float64 rounding from the conservative second covariance check.
    np.testing.assert_allclose(confirmed[4:], original[4:], atol=1e-14, rtol=0)
    partial, _ = targets(close, times, times[74:77], enabled=True)
    np.testing.assert_array_equal(partial, confirmed[4:])


def test_zero_absolute_momentum_is_cash_for_ranked_short():
    close, times = history()
    close *= np.exp(np.arange(len(times))[:, None] * .01)
    close[70, 0] = close[49, 0]
    original, _ = targets(close, times, times[70:71], enabled=False)
    confirmed, _ = targets(close, times, times[70:71], enabled=True)
    assert original[0, 0] < 0
    assert confirmed[0, 0] == 0
    np.testing.assert_array_equal(confirmed > 0, original > 0)


def test_confirmed_targets_are_causal_and_follow_explicit_asset_order():
    close, times = history()
    close[72:74, 0] = close[51:53, 0] * 1.02
    decisions = times[70:]
    original, diag = targets(close, times, decisions, enabled=True)
    changed = close.copy()
    changed[85:] *= np.arange(1, 7)[None, :] * 10
    future, _ = targets(changed, times, decisions, enabled=True)
    np.testing.assert_array_equal(original[:15], future[:15])
    permutation = np.array([4, 1, 5, 0, 3, 2])
    reordered, _ = targets(close[:, permutation], times, decisions, enabled=True,
                           symbols=tuple(SYMBOLS[i] for i in permutation))
    np.testing.assert_allclose(reordered, original[:, permutation], atol=1e-14, rtol=0)
    assert all(rank <= decision for rank, decision in zip(diag['rank_us'], decisions))
    assert all(available is None or available <= decision
               for row, decision in zip(diag['feature_available_us'], decisions)
               for available in row)
