"""Independent hand examples for feedback maturity and signed switch costs."""
import numpy as np
import pandas as pd
import pytest

from modules.collector_research.pipeline.economics import proxy_step
from scripts.research.calibrate_expert_following import (
    DAY_US, EXEC_OFFSET_US, first_switch_cost_delta, label_available_at, mature_indices, proxy_rows,
)


def test_weekly_label_not_mature_at_next_week_midnight_or_boundary():
    start = 1704153600000000
    ready = label_available_at(start, 7)
    assert ready == start + 7*DAY_US + EXEC_OFFSET_US + 1
    assert not len(mature_indices(start + 7*DAY_US, [ready]))
    assert not len(mature_indices(ready - 1, [ready]))
    assert mature_indices(ready, [ready]).tolist() == [0]


@pytest.mark.parametrize('previous,target,expected', [(0,.1,0), (10,.1,-1), (10,-.1,1), (10,0,1), (-10,-.1,-1)])
def test_first_switch_delta_hand_reference(previous,target,expected):
    # 10k capital, price100, 10-unit exposure, 10bp cost.
    assert first_switch_cost_delta([previous],10000,[target],[100],.001) == pytest.approx(expected)


def test_partial_close_short_profit_and_signed_funding():
    nav,q,cost,funding,turnover,pnl = proxy_step(10000,np.array([-10.]),np.array([-.05]),
        np.array([100.]),np.array([90.]),np.array([1.]),np.array([True]),.001)
    assert q.tolist() == [-5.]
    assert (pnl,turnover,cost,funding,nav) == (50.,500.,.5,-5.,10054.5)


def test_marked_and_paid_flat_are_different_and_fees_counted_once():
    frame = pd.DataFrame(dict(dt=pd.date_range('2024-01-01', periods=3, tz='UTC'),
        exec_price=[100.,100.,90.],mark_funding_per_unit=[0.,0.,0.],
        funding_interval_complete=[True]*3,complete_kline=[True]*3))
    r=proxy_rows({'A':frame},np.array([0]),np.array([[-.1]]),1,.001,10000)
    assert r['price_pnl']==100
    assert r['marked_net']==99
    assert r['terminal_fee']==.9
    assert r['closed']['net']==pytest.approx(98.1)
    assert r['closed']['fees']==1.9


def test_missing_funding_cannot_become_zero_return():
    with pytest.raises(ValueError, match='Incomplete owned'):
        proxy_step(10000,np.zeros(1),np.array([-.1]),np.array([100.]),np.array([90.]),np.array([np.nan]),np.array([False]),.001)


def test_soft_mixture_cost_uses_net_target_not_average_expert_costs():
    # Equal +10/-10 intents cancel; a flat wallet should make no trade.
    candidates = [np.array([.1]), np.array([-.1])]
    net = sum(candidates)/2
    args = (np.array([100.]),np.array([100.]),np.array([0.]),np.array([True]),.001)
    combined = proxy_step(10000,np.zeros(1),net,*args)
    independent = [proxy_step(10000,np.zeros(1),w,*args)[2] for w in candidates]
    assert combined[2] == 0 and np.mean(independent) == 1
