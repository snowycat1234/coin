import numpy as np
from scripts.research.probe_short_breadth import panel_features,forward_short,group_metric,contrast,shuffle_breadth

def test_leave_one_out_and_ready_peers():
    x=np.ones((260,5))*100
    x[-20:,:]=np.linspace(100,120,20)[:,None]
    x[-20:,0]=np.linspace(100,80,20)
    ready=np.ones_like(x,dtype=bool)
    z=panel_features(x,ready)
    assert z['breadth'][-1,0]==1 and z['breadth'][-1,1]==.75
    ready[-1,4]=False
    assert np.isnan(panel_features(x,ready)['breadth'][-1,0])

def test_future_perturbation_and_gap():
    x=np.tile(np.linspace(100,150,300)[:,None],(1,5));r=np.ones_like(x,dtype=bool)
    before=panel_features(x,r);changed=x.copy();changed[270:]*=3
    after=panel_features(changed,r)
    for key in before:np.testing.assert_allclose(before[key][:270],after[key][:270],equal_nan=True)
    y=forward_short(x,30,.0027);assert np.isclose(y[260,0],1-x[290,0]/x[260,0]-.0027)
    changed[275,0]=np.nan
    assert np.isnan(forward_short(changed,30,.0027)[260,0])

def test_market_block_not_coin_weight_and_conditioning():
    y=np.array([[.1,.1,.1],[.3,np.nan,np.nan]])
    z=group_metric(y,np.ones_like(y,dtype=bool))
    assert z['distinct_market_blocks']==2 and z['asset_labels']==4
    assert np.isclose(z['mean_short_price_edge_after_roundtrip'],.2)
    b=np.array([[.2,.2,.2],[.7,.7,.7]])
    assert np.isclose(contrast(y,np.ones_like(y,dtype=bool),b)['spread'],-.2)

def test_shuffle_keeps_early_late_peer_universe_and_nan_support():
    b=np.array([[np.nan,np.nan],[np.nan,np.nan],[.2,.7],[.4,.8],[.9,.1]])
    ready=np.array([[0,0],[0,0],[1,1],[1,1],[1,0]],dtype=bool)
    fake,sizes=shuffle_breadth(b,ready,[np.ones(5,dtype=bool)],np.random.default_rng(9))
    np.testing.assert_array_equal(np.isfinite(fake),np.isfinite(b))
    np.testing.assert_array_equal(fake[-1],b[-1])
    assert sorted(sizes)==[1,2,2]
