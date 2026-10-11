"""Financial/maturity counterexamples are synthetic, never historical results."""
import importlib.util
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

spec=importlib.util.spec_from_file_location('minute_joint',Path(__file__).with_name('experiment.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
from scripts.research.conditional_selector_core import UtilitySelector,chronological_training_mask,nonoverlap_indices
from modules.collector_research.pipeline.economics import proxy_step


def test_signed_adverse_variance_and_cross_asset_hedge():
    w=np.array([[.2,-.2],[.2,.2],[0.,0.]])
    rv1=np.tile([4.,4.],(3,1));rv5=np.tile([2.,2.],(3,1))
    plus=np.tile([3.,1.],(3,1));minus=np.tile([1.,3.],(3,1))
    c=np.tile([[2.,1.],[1.,2.]],(3,1,1));c[-1]=np.nan
    a=m.risk_features(w,rv1,rv5,plus,minus,c)
    np.testing.assert_allclose(a[0],[np.log(2),.25,-.5])
    np.testing.assert_allclose(a[1],[np.log(2),.5,.5])
    np.testing.assert_array_equal(a[2],np.zeros(3))
    c[0,0,0]=np.nan
    assert np.isnan(m.risk_features(w,rv1,rv5,plus,minus,c)[0]).all()


def frames():
    day=pd.date_range('2021-01-01',periods=4,tz='UTC')
    return {'BTCUSDT':pd.DataFrame(dict(dt=day,available_us=day.astype('int64')//1000+m.DAY_US,
        exec_price=[100.,101.,102.,103.],mark_funding_per_unit=[.01,.02,.03,.04],
        funding_interval_complete=True,complete_kline=True,complete_mark=True))}


def test_existing_reference_pays_entry_terminal_and_actual_source_coefficient():
    d=np.array([m.utc('2021-01-02')]);w=np.array([[[0.],[.2],[-.2]]]);ok=np.ones((1,3),bool)
    label=m.one_day_labels(frames(),d,w,ok,[],('BTCUSDT',))
    q=m.CAPITAL*.2/101
    expected_fee=(q*101+q*102)*m.COST;funding=q*.02
    np.testing.assert_allclose(label['label_fees_USDT'][0,1],expected_fee)
    np.testing.assert_allclose(label['label_funding_USDT'][0,1],funding)
    np.testing.assert_allclose(label['label_net_return'][0,1],(q-expected_fee-funding)/m.CAPITAL)
    assert label['label_available_us'][0]==d[0]+m.DAY_US+m.LATENCY_US
    assert label['utility'][0,0]==0


def test_unknown_touched_interval_stays_unknown_even_with_price():
    f=frames();f['BTCUSDT'].loc[1,'mark_funding_per_unit']=np.nan
    d=np.array([m.utc('2021-01-02')]);w=np.array([[[0.],[.2],[-.2]]]);ok=np.ones((1,3),bool)
    a=m.one_day_labels(f,d,w,ok,[],('BTCUSDT',))
    assert a['utility'][0,0]==0 and np.isnan(a['utility'][0,1:]).all()
    with pytest.raises(ValueError,match='entry/exit'):
        proxy_step(10000,np.array([1.]),np.array([0.]),np.array([np.nan]),np.array([102.]),np.array([0.]),np.array([True]),m.COST)


def test_purge_and_disjoint_clock_do_not_count_assets_or_overlap():
    d=m.utc('2021-01-01')+np.arange(100)*m.DAY_US;a=d+m.DAY_US+m.LATENCY_US
    cutoff=m.utc('2021-04-01');valid=np.ones(100,bool)
    mask=chronological_training_mask(d,a,valid,cutoff,embargo_days=1)
    ix=nonoverlap_indices(d,a,mask)
    assert np.all(a[ix]<cutoff-m.DAY_US) and np.all(d[ix[1:]]>=a[ix[:-1]])
    assert len(ix)<mask.sum() and not mask[-1]


def test_scaler_and_ridge_ignore_all_future_features_and_labels():
    # Two synthetic fits test the original API; these are not research trials.
    d=m.utc('2021-01-01')+np.arange(105)*m.DAY_US;a=d+m.DAY_US+m.LATENCY_US
    cutoff=int(d[80]);mask=(a<cutoff)
    x=np.column_stack([np.arange(105),np.arange(105)**2]).astype(float)
    y=np.column_stack([np.zeros(105),np.sin(np.arange(105)),np.cos(np.arange(105))])
    kwargs=dict(fit_available_us=cutoff,feature_available_us=d,feedback_available_us=np.zeros(105,dtype=np.int64))
    first=UtilitySelector('RIDGE',m.SEED).fit(x,y,d,a,mask,cutoff,**kwargs)
    changed=x.copy();changed[~mask]=1e15;future=y.copy();future[~mask]=-1e15
    second=UtilitySelector('RIDGE',m.SEED).fit(changed,future,d,a,mask,cutoff,**kwargs)
    assert len(first.training_indices)==40
    np.testing.assert_array_equal(first.model[0].mean_,second.model[0].mean_)
    np.testing.assert_array_equal(first.model[1].coef_,second.model[1].coef_)


def test_future_held_gap_cannot_change_current_routing_or_erase_calendar():
    d=np.array([m.utc('2022-01-02'),m.utc('2022-01-03')]);symbols=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
    avail=np.arange(d[0]-30*m.DAY_US,d[-1]+m.DAY_US,m.DAY_US,dtype=np.int64)
    w=np.zeros((2,3,5));w[:,1,0]=.2;w[:,2,0]=-.1
    s=dict(decision_us=d,symbol_order=np.array(symbols),targets=w,expert_eligible=np.ones((2,3),bool),
        close_available_us=avail,close=np.full((len(avail),5),100.))
    pred={k:np.tile([0.,4.,-4.],(2,1)) for k in ('A','B','C')};known=np.ones(2,bool);scale={k:1. for k in pred}
    hole=dict(symbol='BTCUSDT',open_ms=int((d[0]+6*3600*1000000)//1000))
    before,_=m.routed_targets(s,pred,known,scale,[]);after,diagnostic=m.routed_targets(s,pred,known,scale,[hole])
    for arm in pred:
        np.testing.assert_array_equal(before[arm+'_targets'],after[arm+'_targets'])
        assert np.any(after[arm+'_targets'][0]!=0) and len(after[arm+'_targets'])==2
        assert diagnostic[arm]['first_uncertifiable_owned_mark']['known_at_us']>int(d[0])
        assert diagnostic[arm]['financial_path_status']=='STOP_UNKNOWN_OWNED_MARK'
    one=m.one_day_labels(frames(),np.array([m.utc('2021-01-02')]),np.array([[[0.],[.2],[-.2]]]),np.ones((1,3),bool),
        [dict(symbol='BTCUSDT',open_ms=int((m.utc('2021-01-02')+6*3600*1000000)//1000))],('BTCUSDT',))
    assert one['utility'][0,0]==0 and np.isnan(one['utility'][0,1:]).all()


def test_future_feature_missing_has_no_effect_on_earlier_budget_copy():
    scores=np.tile([0.,4.,-4.],(3,1));eligible=np.ones((3,3),bool)
    baseline,_=m.budget_path(scores,1.,cash_index=0,eligible=eligible,max_l1=.1)
    eligible[2,1:]=False
    changed,_=m.budget_path(scores,1.,cash_index=0,eligible=eligible,max_l1=.1)
    np.testing.assert_array_equal(changed[:2],baseline[:2])
    np.testing.assert_array_equal(changed[2],[1.,0.,0.])
