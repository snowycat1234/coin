import numpy as np

from scripts.research.public_cross_section_momentum import ANCHOR_US, DAY_US, public_targets


SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT', 'ADAUSDT')


def history(days=100):
    times = ANCHOR_US + np.arange(-70, days - 70, dtype=np.int64) * DAY_US
    t = np.arange(days, dtype=float)[:, None]
    rates = np.array([-.004, -.002, -.0005, .0005, .002, .004])[None, :]
    close = 100 * np.exp(t * rates + .002 * np.sin(t * .7 + np.arange(6)[None, :]))
    return close, times


def run(close, times, decisions, symbols=SYMBOLS, allowed=SYMBOLS):
    return public_targets(close, times, decisions, symbols, allowed)


def test_future_perturbation_and_explicit_asset_permutation():
    close, times = history()
    decisions = times[70:]
    before, diag = run(close, times, decisions)
    changed = close.copy()
    changed[85:] *= np.arange(1, 7)[None, :] * 10
    after, _ = run(changed, times, decisions)
    np.testing.assert_allclose(before[:15], after[:15], atol=0, rtol=0)
    permutation = np.array([4, 1, 5, 0, 3, 2])
    reordered, _ = run(close[:, permutation], times, decisions,
                       tuple(SYMBOLS[i] for i in permutation))
    np.testing.assert_allclose(before[:, permutation], reordered, atol=1e-14)
    assert all(t <= decision for t, decision in zip(diag['rank_us'], decisions))
    assert all(x is None or x <= decision for row, decision in
               zip(diag['feature_available_us'], decisions) for x in row)


def test_exact_three_week_return_not_twenty_days():
    close, times = history()
    close[49, 0] = 5.  # At anchor: 70 - 21, excluded by a 20-day lookback.
    weights, diag = run(close, times, times[70:71])
    event = diag['rank_events'][0]
    assert event['rank_us'] == ANCHOR_US
    assert event['momentum'][0] == close[70, 0] / close[49, 0] - 1.
    assert event['momentum'][0] != close[70, 0] / close[50, 0] - 1.
    assert weights[0, 0] > 0  # The 21-day relative winner is long.


def test_fixed_weekly_rank_and_daily_risk_rebalance():
    close, times = history()
    # A mid-week shock changes relative momentum and risk, without reranking.
    close[72:77, 0] *= 1.7
    weights, diag = run(close, times, times[70:78])
    assert diag['rank_us'][:7] == [ANCHOR_US] * 7
    np.testing.assert_array_equal(np.sign(weights[:7]), np.tile(np.sign(weights[0]), (7, 1)))
    assert not np.isclose(abs(weights[0]).sum(), abs(weights[2]).sum())
    assert diag['rank_events'][1]['rank_us'] == ANCHOR_US + 7 * DAY_US
    # Beginning a window on Wednesday restores Monday's rank, including risk
    # and missing-data events between Monday and the first output day.
    partial, partial_diag = run(close, times, times[72:78])
    np.testing.assert_allclose(partial, weights[2:], atol=0, rtol=0)
    assert partial_diag['rank_us'][0] == ANCHOR_US


def test_warmup_missing_clear_and_no_new_entry_before_weekly_rank():
    close, times = history()
    warm, _ = run(close[:30], times[:30], times[29:30])
    assert not warm.any()
    close[72, 0] = np.nan
    weights, diag = run(close, times, times[70:])
    assert weights[0, 0] < 0
    assert np.all(weights[2:, 0] == 0)  # Thirty-day risk history stays incomplete.
    # Missing one whole calendar row invalidates the past contiguous window.
    omitted, _ = run(np.delete(close, 72, axis=0), np.delete(times, 72), times[73:74])
    assert not omitted.any()
    restricted, _ = run(close, times, times[70:71], allowed=SYMBOLS[:3])
    assert not restricted.any()  # Four eligible assets are required.
    assert not diag['current_eligible'][2][0]


def test_missing_before_first_output_is_not_reentered_after_recovery():
    close, times = history(150)
    # A gap clears an originally ranked asset; after 31 complete closes have
    # returned, the asset is only eligible to enter on a scheduled rank.
    close[70, 0] = np.nan
    weights, diag = run(close, times, times[99:108])
    assert weights[0, 0] == 0 and weights[1, 0] == 0
    # Day 101 is Thursday; full risk history has recovered but rank is Monday.
    assert diag['current_eligible'][2][0] and weights[2, 0] == 0
    assert weights[6, 0] < 0  # Day 105 is the next scheduled Monday.
    partial, _ = run(close, times, times[101:108])
    np.testing.assert_allclose(partial, weights[2:], atol=0, rtol=0)


def test_absolute_gross_caps_and_static_pool_order():
    close, times = history()
    weights, diag = run(close, times, times[70:], allowed=SYMBOLS[:5])
    assert np.max(abs(weights)) <= .3 + 1e-12
    assert np.max(abs(weights).sum(1)) <= .6 + 1e-12
    assert np.max(abs(weights.sum(1))) <= 1e-12
    assert np.all(weights[:, 5] == 0)
    assert diag['symbol_order'] == list(SYMBOLS)
