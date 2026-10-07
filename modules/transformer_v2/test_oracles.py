import numpy as np
from .oracles import weights

def test_30day_oracles_do_not_require_unavailable_60day_expert_labels():
    close=np.exp(np.arange(50)[:,None]*np.array([.001,.002,.003,.004])[None,:]);indices=np.array([0,20])
    utility=np.full((2,4,2),np.nan);relative=np.tile(np.array([-.2,-.1,.1,.2])[None,:,None],(2,1,3))
    active=np.ones((2,4),bool);sma=np.ones((2,4))
    direct,valid=weights('DIRECTIONAL_ORACLE',utility,relative,close,indices,active,sma)
    assert valid[0].all() and not valid[1].any() and np.allclose(direct[0],.15) and not direct[1].any()
    ranking,_=weights('CROSS_SECTIONAL_RANK_ORACLE',utility,relative,close,indices,active,sma)
    assert np.allclose(ranking[0],[-.15,-.15,.15,.15])
    expert,valid=weights('EXPERT_ORACLE',utility,relative,close,indices,active,sma)
    assert not valid.any() and not expert.any()

def test_sparse_future_expert_information_cannot_violate_asset_cap():
    u=np.full((1,4,2),np.nan);u[0,0]=[1.,-1.]
    out,valid=weights('EXPERT_ORACLE',u,np.zeros((1,4,3)),np.ones((40,4)),[0],np.ones((1,4),bool),np.ones((1,4)))
    assert valid.sum()==1 and np.isclose(out.sum(),.3) and out.max()<=.3
