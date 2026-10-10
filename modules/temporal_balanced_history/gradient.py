"""Training-only date weights on intact charged own-wallet utility paths."""
import numpy as np
import torch
from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_q4_reserved.terminal import charged_terminal_path
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan
from modules.temporal_short_expansion.adapter import compress,expand
from modules.temporal_two_expert.exact import verify_prototype

def request_gradient(requests,e,p,date_weights):
    verify_prototype(p);a=np.asarray(date_weights);n=len(e.contexts)
    if a.shape!=(n,) or not np.isfinite(a).all() or np.any(a<=0) or a[-1]!=1:raise ValueError('Fixed positive intact-wallet weights; terminal cost weight1')
    targets,records=p.mapped_path(compress(requests),e.internal.contexts);w=torch.tensor(targets,dtype=torch.float64,requires_grad=True)
    with torch.enable_grad():
        r=charged_terminal_path(w,e.prices,e.funding_coeff,plan=BoundaryPlan.full_fill_diagnostic(n));ret=r['net_return'];utility=torch.log1p(ret)-5*torch.minimum(ret,torch.zeros_like(ret)).square();u=(utility*torch.tensor(a,dtype=torch.float64)).sum();g=torch.autograd.grad(u,w)[0].detach().numpy()
    g=-p.mapping_vjp(g,records,e.internal.contexts)/n;g[:,2]=0
    return -float(u.detach())/n,expand(g),r

def gradients(model,episodes,p,date_weights,batch=32):
    total=sum(len(e.contexts) for e in episodes);loss=0.
    for e,a in zip(episodes,date_weights,strict=True):
        n=len(e.contexts);rng=[];chunks=[]
        with torch.no_grad():
            for start in range(0,n,batch):
                rng.append(torch.get_rng_state().clone());chunks.append(predict_episode(model,e,feature_batch_size=batch,start=start,stop=start+batch).numpy().copy())
        request=np.concatenate(chunks);value,g,_=request_gradient(request,e,p,a);assert np.isfinite(value) and np.isfinite(g).all();final=torch.get_rng_state().clone()
        try:
            for k,start in enumerate(range(0,n,batch)):
                torch.set_rng_state(rng[k]);out=predict_episode(model,e,feature_batch_size=batch,start=start,stop=start+batch);assert torch.equal(out.detach(),torch.tensor(request[start:start+batch],dtype=out.dtype));out.backward(torch.tensor(g[start:start+batch]*(n/total),dtype=out.dtype))
        finally:torch.set_rng_state(final)
        loss+=value*n/total
    return loss
