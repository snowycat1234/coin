import numpy as np
import pandas as pd
import pytest
from pipeline.economics import allocate_positions, proxy_step, replay
from pipeline.make_labels import feature_frame, future_compound
from pipeline.models import inner_split, scaler_for, transform
from pipeline.train import folds_for


def test_forward_utility_exact_horizon_not_shifted():
    x = pd.Series([.1, .2, .3, .4])
    u = future_compound(x, 2)
    assert u.iloc[0] == pytest.approx(1.1 * 1.2 - 1)
    assert u.iloc[2] == pytest.approx(1.3 * 1.4 - 1)
    assert np.isnan(u.iloc[3])


def test_gap_invalidates_future_utility():
    u = future_compound(pd.Series([.1, np.nan, .2, .3]), 2)
    assert u.iloc[:2].isna().all()
    assert np.isfinite(u.iloc[2])


def test_bankrupt_utility_rejected():
    with pytest.raises(ValueError): future_compound(pd.Series([-.5, -1]), 2)


def test_cash_probability_not_renormalized_to_full_risk():
    a = allocate_positions(np.array([.1, .1]), 2)
    assert np.sum(np.abs(a)) == pytest.approx(.06)
    assert np.sum(np.abs(allocate_positions(np.ones(10), 10))) == pytest.approx(.6)


def test_price_drift_rebalance_has_real_turnover_cost():
    nav, q, fees, *_ = proxy_step(10000, np.array([0.]), np.array([.3]), np.array([100.]), np.array([200.]), np.array([0.]), np.array([True]), .001)
    assert q[0] == 30
    nav2, q2, fees2, *_ = proxy_step(nav, q, np.array([.3]), np.array([200.]), np.array([200.]), np.array([0.]), np.array([True]), .001)
    assert fees2 > 2.0  # old constant-weight difference method would charge zero


def test_short_receives_positive_funding():
    nav, q, fees, funding, *_ = proxy_step(10000, np.zeros(1), np.array([-.3]), np.array([100.]), np.array([100.]), np.array([.01]), np.array([True]), 0.)
    assert funding == pytest.approx(-.3)
    assert nav == pytest.approx(10000.3)


def test_missing_owned_interval_rejected_cash_allowed():
    args = (10000, np.zeros(1), np.array([.3]), np.array([100.]), np.array([np.nan]), np.array([np.nan]), np.array([False]), .001)
    with pytest.raises(ValueError): proxy_step(*args)
    nav, *_ = proxy_step(10000, np.zeros(1), np.zeros(1), np.array([np.nan]), np.array([np.nan]), np.array([np.nan]), np.array([False]), .001)
    assert nav == 10000


def test_exit_missing_price_never_free():
    with pytest.raises(ValueError):
        proxy_step(10000, np.array([10.]), np.zeros(1), np.array([np.nan]), np.array([np.nan]), np.array([np.nan]), np.array([False]), .001)


def replay_frame(n=10):
    return pd.DataFrame(dict(dt=pd.date_range('2022-01-01', periods=n, tz='UTC'), exec_price=np.full(n, 100.),
                            mark_funding_per_unit=np.zeros(n), funding_interval_complete=True, complete_kline=True))


def test_cash_days_and_terminal_liquidation_in_metrics():
    d = replay_frame()
    metric, trace = replay({'BTCUSDT': d}, np.arange(5), np.full((5, 1), .3), 1, .001)
    assert metric['days'] == 5 and metric['terminal_fee'] > 0
    assert metric['mdd'] == pytest.approx(-metric['net_return'])
    assert metric['final_nav'] == trace.nav_after.iloc[-1]
    cash, _ = replay({'BTCUSDT': d}, np.arange(5), np.zeros((5, 1)), 1, .001)
    assert cash['days'] == 5 and cash['net'] == 0


def test_noncontiguous_replay_not_silently_spliced():
    with pytest.raises(ValueError):
        replay({'BTCUSDT': replay_frame()}, np.array([0, 2, 3]), np.ones((3, 1)) * .3, 1, .001)


def test_feature_momentum_does_not_cross_gap():
    n = 300
    d = pd.DataFrame(dict(dt=pd.date_range('2022-01-01', periods=n, tz='UTC'), symbol='BTCUSDT',
                         close=np.arange(n) + 100., high=np.arange(n) + 101., low=np.arange(n) + 99.,
                         quote_volume=100., premium=0., funding=.001,
                         complete_kline=True, complete_premium=True, complete_funding=True))
    d.loc[50, 'complete_kline'] = False
    f = feature_frame(d, 20)
    assert np.isnan(f.mom60.iloc[100])
    assert not f.feature_ready.iloc[60]
    assert f.feature_ready.iloc[75]


def test_scaler_ignores_future_rows_and_preserves_per_feature_masks():
    X = {'A': np.array([[1., np.nan], [2., 3.], [9., 90.]], dtype='float32')}
    mu, sd = scaler_for(X, [(0, 'A', 1)], 2)
    before = mu.copy()
    X['A'][2] = 1e9
    mu2, _ = scaler_for(X, [(0, 'A', 1)], 2)
    assert np.array_equal(before, mu2)
    z = transform(X['A'][:1], mu, sd)
    assert z.shape == (1, 4) and np.array_equal(z[0, 2:], [1, 0])


def test_inner_split_full_maturity_purge_and_embargo():
    dates = pd.date_range('2022-01-01', periods=500, tz='UTC')
    items = [(0, 'A', i) for i in range(300)]
    ends = {'A': list(dates + pd.Timedelta(days=61))}
    tr, va = inner_split(items, dates, ends, 60)
    boundary = min(dates[i] for _, _, i in va) - pd.Timedelta(days=60)
    assert max(ends[s][i] for _, s, i in tr) < boundary


def test_validation_eligibility_never_uses_future_label_ready(monkeypatch):
    dates = pd.date_range('2022-01-01', '2024-12-31', tz='UTC')
    n = len(dates)
    d = pd.DataFrame(dict(close=np.ones(n), feature_ready=True, label_ready=True,
                         label_end_at=dates + pd.Timedelta(days=61)))
    monkeypatch.setenv('END_DATE', '2024-12-31')
    f1 = list(folds_for(dates, {'BTCUSDT': d}, 10, 100, 60))[0]
    d.loc[(dates >= f1['start']), 'label_ready'] = False
    f2 = list(folds_for(dates, {'BTCUSDT': d}, 10, 100, 60))[0]
    assert f1['valid'] == f2['valid']


@pytest.mark.parametrize('unit', ['ns', 'us'])
def test_exported_targets_have_explicit_microsecond_completed_day_clock(tmp_path, unit):
    from pipeline.train import save_targets
    dates = pd.date_range('2023-07-01', periods=2, tz='UTC').as_unit(unit)
    p = save_targets(tmp_path, 1, 'TEST', dates, {'calendar': np.array([0, 1])},
                     np.array([[.1], [.2]]), ['BTCUSDT'])
    with np.load(p, allow_pickle=False) as result:
        assert result['decision_us'].tolist() == [1688256000000000, 1688342400000000]
        assert result['symbol_order'].tolist() == ['BTCUSDT']


@pytest.mark.parametrize('name', ['TCN_SHARED', 'GRU_SHARED', 'TRANSFORMER_SHARED'])
def test_neural_one_epoch_cpu_smoke(name):
    torch = pytest.importorskip('torch')
    from pipeline.models import fit_network
    torch.set_num_threads(2)
    rng = np.random.default_rng(42)
    X = {'A': rng.normal(size=(40, 3)).astype('float32')}
    Y = {'A': rng.normal(0, .01, size=(40, 2)).astype('float32')}
    train = [(0, 'A', i) for i in range(7, 27)]
    val = [(0, 'A', i) for i in range(27, 32)]
    mu, sd = scaler_for(X, train, 8)
    pred, epoch, state = fit_network(name, X, Y, train, val, 8, 1, mu, sd, 1, 'cpu', 8, 42, logger=lambda x: None)
    assert pred.shape == (5, 2) and np.isfinite(pred).all() and epoch == 1 and state
