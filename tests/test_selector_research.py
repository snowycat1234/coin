"""No fitting: label arithmetic, true availability and embargo counterexamples."""
import numpy as np
import polars as pl
import pytest
from scripts.research import selector_data as data

def test_expert_forward_label_indices_and_unknown_tail():
    times=data.stamp('2022-01-01')+np.arange(730)*data.DAY
    lib={}
    for expert in data.EXPERTS:
        nav=np.full(730,10000.) if expert=='CASH' else 10000+np.arange(1,731)*(10 if expert=='HOLD' else -1)
        lib[expert,'FIXTURE']=dict({'daily_nav.parquet':pl.DataFrame(dict(day_end_us=times+data.DAY,nav=nav))})
    clock,relative,utility,ends=data.labels(lib,'FIXTURE',30)
    assert utility[0,1]==10300/10000-1
    assert utility[700,1]==17300/17000-1 and np.isnan(utility[701:]).all()
    assert (utility[:701,2]==0).all() and np.allclose(relative[:701].sum(axis=1),0,atol=1e-14)
    assert np.array_equal(clock,times) and np.array_equal(ends,times+30*data.DAY)

def test_purge_plus_full_horizon_embargo_and_soft_weight_prefix():
    times=np.arange(730,dtype=np.int64)*data.DAY;h=90;start=273*data.DAY
    train,valid=data.fold_indices(times,times+h*data.DAY,h,start,start+92*data.DAY,90)
    assert train[-1]==93 and (times+h*data.DAY)[train].max()<=start-h*data.DAY
    assert valid[0]==273 and valid[-1]==364
    with pytest.raises(AssertionError):data.fold_indices(times,times+h*data.DAY,h,150*data.DAY,200*data.DAY,90)
    pred=np.array([[.02,0.,-.01],[.01,.02,0.],[-.02,0.,.01]])
    path=data.soft_path(pred,.02,.1);assert (path>=0).all() and np.allclose(path.sum(axis=1),1)
    assert np.linalg.norm(np.diff(np.vstack([[0.,0.,1.],path]),axis=0),ord=1,axis=1).max()<=.1+1e-12
    future=pred.copy();future[-1]*=30;assert np.array_equal(data.soft_path(future,.02,.1)[:2],path[:2])

def test_full_feature_availability_and_future_perturbation_without_fit():
    n=1095;times=data.stamp('2021-01-01')+np.arange(1,n+1,dtype=np.int64)*data.DAY
    price=100+np.arange(n)*.1+4*np.sin(np.arange(n)/12)
    bars=pl.DataFrame(dict(symbol=['BTCUSDT']*n,close_us=times,available_us=times,open=price,
        close=price,high=price+2,low=price-2,volume=1000+np.arange(n)*.3+20*np.sin(np.arange(n)/9)))
    names=['distance20','distance50','distance100','distance200','slope50','slope100','slope200',
        'momentum5','momentum20','momentum60','momentum120','momentum200','rv10','rv30','rv60','rv200',
        'drawdown20','drawdown60','drawdown200','vol_of_vol','rebound_velocity','volume_momentum','volume_zscore','atr_normalized','rsi','donchian_position']
    before=data.features(bars,names);cut=data.stamp('2023-06-01')
    changed=bars.with_columns(*[pl.when(pl.col('close_us')>cut).then(pl.col(k)*3).otherwise(pl.col(k)).alias(k) for k in ('open','close','high','low','volume')])
    after=data.features(changed,names)
    assert before.filter(pl.col('decision_us')<=cut).equals(after.filter(pl.col('decision_us')<=cut))
    assert before['decision_us'].equals(before['feature_available_us'].rename('decision_us'))
    late=bars.with_columns((pl.col('available_us')+1).alias('available_us'))
    with pytest.raises(AssertionError):data.features(late,names)
