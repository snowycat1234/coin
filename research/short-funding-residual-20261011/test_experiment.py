import importlib.util
from pathlib import Path
import numpy as np
import pytest

spec = importlib.util.spec_from_file_location('funding_experiment', Path(__file__).with_name('experiment.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def test_event_at_publication_boundary_excluded_and_future_invariant():
    d = 10 * m.DAY
    t = np.arange(2 * m.DAY, 11 * m.DAY, m.DAY // 3)
    r = np.arange(len(t), dtype=float)
    h = np.full(len(t), 8.)
    a = m.settled_window(t, r, h, d)
    assert a[1] == 21 and a[2] < d - m.DAY
    r[t >= d - m.DAY] = 1e12
    assert m.settled_window(t, r, h, d) == a

def test_missing_settled_event_is_input_unavailable():
    d = 10 * m.DAY
    t = np.arange(2 * m.DAY, 9 * m.DAY, m.DAY // 3)
    assert m.settled_window(t, np.ones(21), np.full(21, 8.), d)[0] == 21
    keep = np.arange(21) != 5
    assert m.settled_window(t[keep], np.ones(20), np.full(20, 8.), d)[0] is None

def test_official_settlement_jitter_retains_actual_availability_clock():
    d = 10 * m.DAY
    t = np.arange(2 * m.DAY, 9 * m.DAY, m.DAY // 3)
    t = t + (np.arange(21) % 3) * 6000
    value, count, latest = m.settled_window(t, np.ones(21), np.full(21, 8.), d)
    assert value == 21 and count == 21 and latest == int(t[-1])
    # A late event at the upper boundary remains unavailable, never rounded.
    t[-1] = d-m.DAY+6000
    assert m.settled_window(t, np.ones(21), np.full(21, 8.), d)[0] is None

def test_strict_label_maturity_purges_boundary():
    assert not m.mature(3 * m.DAY, 0, 10 * m.DAY)
    assert m.mature(2 * m.DAY, 0, 10 * m.DAY)
    assert not m.mature(-m.DAY, 0, 10 * m.DAY)

def test_paid_short_entry_and_exit_with_actual_price_ratio():
    from decimal import Decimal as D
    expected = (D(1)-D('.0008'))*(D(1)-D('.00055'))-D('.9')*(D(1)+D('.0008'))*(D(1)+D('.00055'))
    assert m.short_price_cost(100, 90) == pytest.approx(float(expected), abs=1e-15)
    assert m.short_price_cost(100, 100) == pytest.approx(-.0027)
    with pytest.raises(ValueError):
        m.short_price_cost(100, np.nan)

def rows(scale=1.):
    rng = np.random.default_rng(4401)
    x = rng.normal(size=(80, 9))
    x[:, -1] *= scale
    y = 2 * x[:, 0] - x[:, 1] + x[:, -1] / scale * .3
    return [dict(x=a.tolist(), y=float(b), label_end_us=i, decision_us=i-7) for i, (a, b) in enumerate(zip(x, y))]

def test_funding_unit_scale_cancels_in_fit_only_scaler_and_prediction():
    a, b = rows(), rows(.01)
    ma, mb = m.fit(a, True, 1), m.fit(b, True, 1)
    np.testing.assert_allclose(m.predict(a, ma), m.predict(b, mb), atol=1e-12, rtol=0)

def test_closed_form_matches_penalized_normal_equation_and_fit_maturity():
    a = rows()
    model = m.fit(a, True, 1)
    x = np.asarray([r['x'] for r in a])
    design = np.column_stack((np.ones(len(x)), (x-model['mean'])/model['scale']))
    penalty = np.eye(10); penalty[0, 0] = 0
    np.testing.assert_allclose((design.T @ design+penalty) @ model['beta'], design.T @ np.array([r['y'] for r in a]), atol=1e-11)
    assert model['latest_label_end_us'] == 79
    old = model['mean'].copy()
    future = rows(); future[0]['x'] = [1e12]*9
    m.predict(future, model)
    assert model['mean'] == old
