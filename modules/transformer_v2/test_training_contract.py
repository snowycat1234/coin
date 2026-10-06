import numpy as np
import torch
from .train import Samples,predict_forward
from .model import objective,CrossAssetTransformer

def fixture():
    x=np.ones((300,10,2),dtype='float32');x[256:]=999
    available=np.ones((300,10),bool);available[:200,3]=False;x[:200,3]=np.nan
    return dict(x=x,availability=available,ready=available,utility=[np.ones((300,10,2),dtype='float32')]*2,
                relative=np.ones((300,10,3),dtype='float32'),regime=np.ones((300,3),dtype='float32'))

def test_sample_uses_only_past_and_exposes_missing_masks():
    d=fixture();dataset=Samples(d,[255],0,np.ones(10,bool),(np.zeros(2),np.ones(2)),(np.ones(2),np.zeros(3),np.ones(3)))
    batch=dataset[0];assert batch[0].shape==(256,10,2) and batch[0].max()==1
    assert not batch[1][:200,3].any() and not batch[2][:200,3].any()
    assert torch.isfinite(batch[0]).all()

def test_multitask_objective_covers_all_valid_heads():
    d=fixture();dataset=Samples(d,[255],0,np.ones(10,bool),(np.zeros(2),np.ones(2)),(np.ones(2),np.zeros(3),np.ones(3)))
    batch=[v[None] for v in dataset[0]]
    model=CrossAssetTransformer(2,width=16)
    result=predict_forward(model,batch,False);loss=objective(result,*batch[3:],True)
    assert torch.isfinite(loss);loss.backward()
    assert model.regime.weight.grad is not None and model.utility.weight.grad is not None
    assert model.relative.weight.grad is not None
