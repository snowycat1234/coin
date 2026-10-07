import numpy as np
import pandas as pd
import pytest
import torch
from .teachers import future_direction,training_teacher_view,robust_gap_scale
from .policy_model import OraclePolicyTransformer,policy_objective
from .policy_portfolio import policy_targets
from .train_policy import InferenceSamples

def test_direction_requires_whole_horizon_and_does_not_bridge_missing_day():
    close=np.arange(1.,41.)[:,None]*np.ones((1,2));close[15,1]=np.nan
    y=future_direction(close,np.ones_like(close,dtype=bool))
    assert y[0,0]==30 and np.isnan(y[0,1]) and np.isnan(y[-1]).all()

def test_training_teacher_requires_maturity_before_embargo_cutoff_and_never_locked():
    dates=pd.date_range('2025-01-01',periods=100,tz='UTC')
    u=np.tile([.2,.1,0.],(100,2,1)).astype('float32')
    d=dict(dates=dates,label_end=dates+pd.Timedelta(days=61,seconds=60),ready=np.ones((100,2),bool),
           expert_utilities=[u,u.copy()],direction30=np.ones((100,2)),relative=np.ones((100,2,3)))
    result=training_teacher_view(d,[0,1],dates[70],[True,False])
    assert result['expert_valid'][0].sum()==2 and result['teachers_are_training_targets_only']
    with pytest.raises(ValueError,match='Unmature'):training_teacher_view(d,[30],dates[70],[True,True])
    with pytest.raises(ValueError,match='locked'):training_teacher_view(d,[0],pd.Timestamp('2026-03-02',tz='UTC'),[True,True])

def test_gap_scale_uses_only_valid_training_examples_and_rejects_ties_as_weight():
    u=np.array([[3.,2.,0.],[2.,0.,0.],[999.,0.,0.],[1.,1.,1.]])
    assert robust_gap_scale(u,np.array([True,True,False,True]))==1.5

def test_policy_targets_full_half_scale_without_temperature_or_seed_selection():
    p=np.tile([.8,.1,.1],(2,4,1));sma=np.array([[-1.,1.,-1.,1.]]*2);active=np.ones((2,4),bool)
    pred=dict(policy_probability=p,relative=np.tile(np.arange(4.)[:,None],(2,1,3)))
    for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):
        full=policy_targets(pred,sma,active,mapping,'FULL');half=policy_targets(pred,sma,active,mapping,'HALF')
        assert np.array_equal(half,full*.5) and np.abs(full).sum(1).max()<=.6+1e-9
    with pytest.raises(ValueError):policy_targets(pred,sma,active,'NEUTRAL','POSTHOC_WINNER')

def test_float32_probability_roundoff_cannot_exceed_registered_target_gross():
    p=np.tile(np.array([.8,.2000001,0.],dtype='float32'),(1,10,1))
    pred=dict(policy_probability=p,relative=np.zeros((1,10,3)))
    weights=policy_targets(pred,np.ones((1,10)),np.ones((1,10),bool),'DIRECTIONAL','FULL')
    assert np.abs(weights).sum()<=.6+1e-12

def test_primary_policy_loss_moves_toward_best_action_and_masks_invalid_teacher():
    logits=torch.zeros(1,3,2,3,requires_grad=True)
    out=dict(policy_logits=logits,utility=torch.zeros(1,3,2,2),relative=torch.zeros(1,3,2,3),
             regime=torch.zeros(1,3,3),direction30_logits=torch.zeros(1,3,2))
    z=torch.zeros(1,2,2);mask=torch.zeros_like(z,dtype=torch.bool)
    r=torch.zeros(1,2,3);rm=torch.zeros_like(r,dtype=torch.bool)
    g=torch.zeros(1,3);gm=torch.zeros_like(g,dtype=torch.bool)
    experts=torch.tensor([[[0.,2.,1.],[float('nan')]*3]])
    loss=policy_objective(out,z,mask,r,rm,g,gm,experts,torch.tensor([[True,False]]),torch.zeros(1,2),torch.zeros(1,2,dtype=torch.bool),1.)
    loss.backward()
    assert torch.isfinite(loss) and (logits.grad[0,:,0,1]<0).all() and (logits.grad[0,:,0,[0,2]]>0).all()
    assert (logits.grad[0,:,1]==0).all()

def test_model_inference_accepts_only_past_features_and_masks_not_teachers():
    torch.set_num_threads(1);torch.manual_seed(3)
    net=OraclePolicyTransformer(2,assets=4,length=8,width=16,heads=4,patch=2).eval()
    x=torch.randn(1,8,4,2);m=torch.ones_like(x,dtype=torch.bool);a=torch.ones(1,8,4,dtype=torch.bool)
    with torch.no_grad():out=net(x,m,a)
    assert out['policy_logits'].shape==(1,3,4,3) and torch.isfinite(out['policy_logits']).all()
    assert out['relative'].shape==(1,3,4,3)

def test_inference_dataset_never_reads_labels_even_when_none_exist():
    d=dict(x=np.ones((300,4,2)),availability=np.ones((300,4),bool))
    batch=InferenceSamples(d,[299],(np.zeros(2),np.ones(2)))[0]
    assert len(batch)==3 and batch[0].shape==(256,4,2)
