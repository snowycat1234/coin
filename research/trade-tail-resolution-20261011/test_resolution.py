"""Meaningful counterexamples to sampled-tail and clock interpretations."""
import json
import numpy as np
import pytest
from tail_resolution import HERE, DAY_US, SYMBOLS, measure_resolution, summarize


def fixture(days=4):
    close = np.full((days, 5), 100.)
    samples = np.full((days, 288, 5), 100.)
    high, low = close.copy(), close.copy()
    # Span both frozen descriptive year roles, without any real price source.
    t = 1640908800000000 + np.arange(days, dtype=np.int64) * DAY_US
    return close, high, low, samples, t


def test_same_closes_can_miss_real_intraminute_tail_and_units():
    close, high, low, samples, t = fixture()
    high[1] = 110
    low[1] = 90
    v = measure_resolution(close, high, low, samples, t, SYMBOLS)
    assert np.all(v['up_5m'][1] == 0) and np.all(v['down_5m'][1] == 0)
    np.testing.assert_array_equal(v['up_gap'][1], np.full(5, np.log(1.1)))
    np.testing.assert_array_equal(v['down_gap'][1], np.full(5, -np.log(.9)))
    np.testing.assert_array_equal(v['up_relative_gap'][1], np.ones(5))
    s = summarize(v)['all_seen']['sides']['up']['per_asset']['BTCUSDT']
    assert s['actual_OHLC_zero_days'] == 2 and s['relative_gap_valid_days'] == 1
    assert s['sampled_zero_but_actual_positive_days'] == 1
    assert s['max_log_price_bp'] == 10000 * np.log(1.1)


def test_unknown_first_anchor_and_true_previous_close_future_invariance():
    close, high, low, samples, t = fixture()
    close[1] = 200
    samples[1] = 200
    high[1] = 220
    v = measure_resolution(close, high, low, samples, t, SYMBOLS)
    assert np.isnan(v['prior_close'][0]).all() and np.isnan(v['up_gap'][0]).all()
    np.testing.assert_array_equal(v['up_OHLC'][1], np.full(5, np.log(2.2)))
    # Later source mutations cannot change completed earlier source dates.
    high[3] = 1000
    w = measure_resolution(close, high, low, samples, t, SYMBOLS)
    for key in v:
        if key != 'symbol_order':
            np.testing.assert_array_equal(v[key][:3], w[key][:3])
    np.testing.assert_array_equal(v['prior_close'][2], np.full(5, 200))


def test_sampled_extrema_equal_OHLC_no_missing_tail_zero_ratio_stays_unknown():
    close, high, low, samples, t = fixture()
    samples[1, 3] = 110
    samples[1, 4] = 90
    high[1] = 110
    low[1] = 90
    v = measure_resolution(close, high, low, samples, t, SYMBOLS)
    assert np.all(v['up_gap'][1:] == 0) and np.all(v['down_gap'][1:] == 0)
    assert np.isnan(v['up_relative_gap'][2:]).all()
    assert v['common_valid'].tolist() == [False, True, True, True]


def test_source_clock_order_boundary_and_containment_rejections():
    close, high, low, samples, t = fixture()
    with pytest.raises(ValueError, match='identity/order'):
        measure_resolution(close, high, low, samples, t, SYMBOLS[::-1])
    shifted = t.copy()
    shifted[1] += 1
    with pytest.raises(ValueError, match='UTC'):
        measure_resolution(close, high, low, samples, shifted, SYMBOLS)
    samples[1, -1] = 101
    with pytest.raises(ValueError, match='boundary'):
        measure_resolution(close, high, low, samples, t, SYMBOLS)
    samples[1, -1] = 100
    samples[1, 0] = 101
    with pytest.raises(ValueError, match='contain'):
        measure_resolution(close, high, low, samples, t, SYMBOLS)
    samples[1, 0] = 0
    with pytest.raises(ValueError, match='positive'):
        measure_resolution(close, high, low, samples, t, SYMBOLS)


def test_frozen_scope_and_prior_flow_decision_parse():
    p = json.loads((HERE / 'PROTOCOL.json').read_text())
    assert p['order'] == list(SYMBOLS)
    flow = json.loads((HERE.parent / 'aggressor-flow-preflight-20261011/FINAL_DECISION.json').read_text())
    assert flow['status'] == 'STOP_REPEAT_TAKER_IMBALANCE_AND_GENERIC_FLOW_IMPACT'
    assert flow['after_correction']['new_fits'] == 0
