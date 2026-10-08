"""Exact NPZ mapping and original-ramp verification, without real market files."""
import hashlib
import numpy as np
import pytest
from modules.native_action.inputs import BoundE6Inputs
from modules.native_action.teacher import linear_ramp_risk_mapper
from scripts.investment.perpetual_directional import DAY
from test_native_action_teacher import context,simulator


def bound_inputs(tmp_path,*,mismatch=False):
    sim=simulator()
    dates=np.asarray([sim.start+i*DAY for i in range(3)],dtype=np.int64)
    c=context(sim.start)
    desired=np.zeros((3,8,6))
    desired[:,:6]=np.eye(6)
    desired[:,6:]=np.full(6,1/6)
    budgets=np.empty((3,2,6));targets=np.empty((3,2,5))
    for selector in range(2):
        prior=np.asarray(sim.budget)
        for i,t in enumerate(dates):
            p=linear_ramp_risk_mapper(prior,desired[i,6+selector],context(int(t)))
            budgets[i,selector]=p.budget
            targets[i,selector]=p.targets if i<2 else np.zeros(5)
            prior=np.asarray(p.budget)
    if mismatch:budgets[1,0]=np.roll(budgets[1,0],1)
    arrays=dict(decision_us=dates,symbol_order=np.asarray(sim.symbols),
                expert_targets=np.repeat(c.expert_targets[None],3,axis=0),
                expert_available_us=np.repeat(dates[:,None],6,axis=1),
                expert_eligible=np.ones((3,6,5),dtype=bool),past_returns30=np.repeat(c.past_returns30[None],3,axis=0),
                market_features=np.repeat(np.asarray(c.market_features)[None],3,axis=0),
                market_feature_names=np.asarray(c.market_feature_names),market_available_us=dates,
                action_desired_budgets=desired,original_selector_ramped_budgets=budgets,
                original_selector_targets=targets)
    path=tmp_path/'H1.npz';np.savez_compressed(path,**arrays)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    return BoundE6Inputs(path,digest,{k:k for k in arrays},c.binding),sim


def test_explicit_npz_map_rebuilds_original_path_before_local_comparison(tmp_path):
    inputs,sim=bound_inputs(tmp_path)
    report=inputs.validate_original_path(linear_ramp_risk_mapper,sim.budget,0)
    assert report['status']=='EXACT' and report['days']==3
    c=inputs.context_at(sim.cursor)
    assert c.expert_eligible.shape==(6,5)
    assert not c.expert_targets.flags.writeable
    p=inputs.baseline_at(sim,c)
    assert p.name=='STATE_EXACT'
    sim.budget=list(p.budget);sim.advance_day(dict(zip(sim.symbols,p.targets)))
    p2=inputs.baseline_at(sim,inputs.context_at(sim.cursor))
    assert p2.budget==tuple(inputs.arrays['original_selector_ramped_budgets'][1,0])


def test_mismatched_ramp_is_rejected(tmp_path):
    inputs,sim=bound_inputs(tmp_path,mismatch=True)
    with pytest.raises(ValueError,match='ramp mismatch'):
        inputs.validate_original_path(linear_ramp_risk_mapper,sim.budget,0)
