import numpy as np
from .evaluate import prediction_metrics,portfolio_targets

def test_rank_metrics_and_portfolio_mapping():
    relative=np.tile(np.arange(10,dtype=float)[None,:,None],(3,1,3))
    utility=np.zeros((3,10,2));pred=dict(utility=utility,relative=relative)
    active=np.ones((3,10),bool)
    metrics=prediction_metrics(pred,utility,relative,active)
    assert np.isclose(metrics['rank_IC_median'],1) and metrics['cross_sectional_hit_rate']==1
    neutral=portfolio_targets(pred,np.ones((3,10)),active,'NEUTRAL')
    assert np.allclose(neutral.sum(1),0) and np.allclose(abs(neutral).sum(1),.6)
    combined=portfolio_targets(pred,np.ones((3,10)),active,'COMBINED')
    assert np.max(abs(combined).sum(1))<=.6
