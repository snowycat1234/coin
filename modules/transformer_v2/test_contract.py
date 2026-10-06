import numpy as np
import pytest
import torch
from .model import CrossAssetTransformer,causal_mask,pairwise_rank_loss
from .portfolio import directional,market_neutral

def model():
    torch.manual_seed(4)
    return CrossAssetTransformer(3,assets=4,length=16,patch=2,width=16,heads=4).eval()

def inputs():
    x=torch.randn(2,16,4,3);mask=torch.ones_like(x,dtype=torch.bool);available=torch.ones(2,16,4,dtype=torch.bool)
    return x,mask,available

def test_cross_asset_axis_and_shapes():
    m=model();x,f,a=inputs()
    with torch.no_grad():first=m(x,f,a);x[:,:,1]+=8;second=m(x,f,a)
    assert first['utility'].shape==(2,3,4,2)
    assert not torch.allclose(first['utility'][:,:,0],second['utility'][:,:,0])
    assert sum(p.numel() for p in m.parameters())<10_000_000

def test_masked_assets_cannot_change_other_assets():
    m=model();x,f,a=inputs();a[:,:,1]=False;f[:,:,1]=False
    with torch.no_grad():first=m(x,f,a);x[:,:,1]=float('nan');second=m(x,f,a)
    assert torch.isfinite(second['utility']).all()
    assert torch.allclose(first['utility'][:,:,0],second['utility'][:,:,0])

def test_temporal_mask_blocks_future_tokens():
    m=model();z=torch.randn(2,9,16);other=z.clone();other[:,5:]+=20
    with torch.no_grad():
        first=m.temporal(z,mask=causal_mask(9));second=m.temporal(other,mask=causal_mask(9))
    assert torch.allclose(first[:,:5],second[:,:5],atol=1e-6)

def test_axis_swapping_and_unobserved_universe_fail():
    m=model();x,f,a=inputs()
    with pytest.raises(AssertionError):m(x.transpose(1,2),f.transpose(1,2),a.transpose(1,2))
    with pytest.raises(AssertionError):m(x,f,torch.zeros_like(a))

def test_rank_loss_and_fixed_neutral_caps():
    y=torch.tensor([[3.,2.,1.,0.]]);valid=torch.ones_like(y,dtype=torch.bool)
    assert pairwise_rank_loss(y,y,valid)<pairwise_rank_loss(-y,y,valid)
    weights=market_neutral(y.numpy(),valid.numpy())
    assert np.allclose(weights,[[.15,.15,-.15,-.15]])
    assert np.array_equal(market_neutral(np.ones((1,4)),valid.numpy()),np.zeros((1,4)))
    assert np.allclose(directional(np.zeros((1,4,2)),np.ones((1,4)),valid.numpy()),.1)

def test_missing_prefix_has_finite_training_gradients():
    m=model().train();x,f,a=inputs();a[:,:10,1]=False;f[:,:10,1]=False;x[:,:10,1]=float('nan')
    result=m(x,f,a);result['utility'].square().mean().backward()
    assert all(torch.isfinite(p.grad).all() for p in m.parameters() if p.grad is not None)
