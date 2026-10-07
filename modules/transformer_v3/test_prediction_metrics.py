import numpy as np
from .prediction_metrics import metrics

def test_rank_spread_and_direct_policy_regret_are_not_wallet_pnl():
    relative=np.tile(np.array([-3.,-1.,1.,3.])[None,:,None],(2,1,3))
    u=np.tile(np.array([0.,2.,1.]),(2,4,1));active=np.ones((2,4),bool)
    pred=dict(relative=relative,policy_probability=np.tile([0.,1.,0.],(2,4,1)))
    r=metrics(pred,relative,u,active)
    assert np.isclose(r['rank_IC_mean'],1.) and r['pairwise_hit_rate']==1.
    assert r['top2_minus_bottom2_30d_realized_future_spread_mean']==4.
    assert r['mean_soft_policy_oracle_regret']==r['mean_argmax_action_oracle_regret']==0.
    assert r['expert_action_hit_rate_non_tie']==1. and r['not_a_trade_availability_filter']

def test_unmature_future_diagnostics_remain_missing_without_censoring_targets():
    pred=dict(relative=np.zeros((2,4,3)),policy_probability=np.tile([1/3]*3,(2,4,1)))
    r=metrics(pred,np.full((2,4,3),np.nan),np.full((2,4,3),np.nan),np.ones((2,4),bool))
    assert r['valid_rank_days']==0 and r['valid_expert_asset_samples']==0
    assert r['rank_IC_mean'] is None and r['mean_soft_policy_oracle_regret'] is None
