"""Causal features, mature labels and bounded soft weights only."""
import numpy as np
import polars as pl
import pytest
from scripts.investment.regime_ranking_screen import features,rule_weights,bounded_path,maturity_folds,DAY

def test_features_future_perturbation_and_label_maturity():
    first=1_735_689_600_000_000;times=first+np.arange(1,501,dtype=np.int64)*DAY
    bars=pl.DataFrame(dict(symbol=['BTCUSDT']*500,close_us=times,available_us=times,close=100+np.arange(500)*.1+np.sin(np.arange(500)/10)))
    decisions=times[[210,270,330,390,450]];before=features(bars,decisions);cut=int(decisions[2])
    future=bars.with_columns(pl.when(pl.col('close_us')>cut).then(pl.col('close')*8).otherwise(pl.col('close')).alias('close'))
    assert features(future,decisions)[:3]==before[:3]
    bad=bars.with_columns(pl.when(pl.col('close_us')==cut).then(pl.col('available_us')+1).otherwise(pl.col('available_us')).alias('available_us'))
    with pytest.raises(AssertionError):features(bad,decisions)
    folds=maturity_folds(decisions,decisions+60*DAY,min_history=2)
    assert len(folds)==3 and folds[0]['mature_indices']==[0,1]
    with pytest.raises(AssertionError):maturity_folds(decisions,decisions+60*DAY+1,min_history=2)

def test_one_fixed_map_soft_l1_limit_cash_and_signed_forecast_identity():
    names=['CASH','HOLD','SMA200_SIGNED','OTHER'];cash=np.array([1.,0.,0.,0.])
    down=rule_weights(names,dict(slow=-1,fast=-1,high_vol=False));rebound=rule_weights(names,dict(slow=-1,fast=1,high_vol=False))
    assert np.array_equal(down,[.25,0,.75,0]) and np.array_equal(rebound,[.5,.5,0,0])
    high=rule_weights(names,dict(slow=-1,fast=-1,high_vol=True));assert np.array_equal(high,[.625,0,.375,0])
    w=bounded_path([down,rebound,down],cash)
    assert np.max(np.linalg.norm(np.diff(np.vstack([cash,w]),axis=0),ord=1,axis=1))<=.5+1e-15
    assert np.allclose(w.sum(axis=1),1) and (w>=0).all()
    assert np.array_equal(bounded_path([down,rebound,high],cash)[:2],w[:2])
    assert np.array_equal(rule_weights(names,dict(slow=0,fast=-1,high_vol=False)),cash)
