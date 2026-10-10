"""Freeze one natural vs capped joint regime/decision attention experiment."""
import argparse,json,collections
from pathlib import Path
import numpy as np,torch
from .inputs import training,CUTOFF
from .gradient import request_gradient
from modules.temporal_history_expansion.gradient import request_gradient as old_gradient
from modules.temporal_q4_reserved.terminal import charged_terminal_path
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan
from modules.temporal_short_expansion.adapter import compress
from modules.temporal_neutral_short.model import initialize
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.exact import sha

def run(state,out):
    out=Path(out);out.mkdir(exist_ok=False);es,p,scaler,binding=training(state);cells=[];details=[]
    for ei,e in enumerate(es):
        n=len(e.contexts);u=np.zeros((n,4))
        for j,slot in enumerate([1,4,5],1):
            req=np.zeros((n,6));req[:,slot]=1;target,_=p.mapped_path(compress(req),e.internal.contexts)
            with torch.no_grad():r=charged_terminal_path(torch.tensor(target,dtype=torch.float64),e.prices,e.funding_coeff,plan=BoundaryPlan.full_fill_diagnostic(n));rr=r['net_return'].numpy();u[:,j]=np.log1p(rr)-5*np.minimum(rr,0)**2
        group=[]
        for i,c in enumerate(e.contexts):
            if i+21>n-1:group.append(None);continue
            r30=float(np.mean(np.prod(1+c.past_returns30,axis=0)-1));r5=float(np.mean(np.prod(1+c.past_returns30[-5:],axis=0)-1));reg='SIDE' if abs(r30)<=.05 else ('UP' if r5>=0 else 'UP_PULLBACK') if r30>.05 else ('DOWN' if r5<=0 else 'DOWN_REBOUND')
            future=u[i:i+21].sum(0);winner=int(np.argmax(future));label_ready=int(e.label_available_us[i+20]);assert label_ready<CUTOFF;cell=reg+'/'+['CASH','VOL','CS','SHORT'][winner];group.append(cell);details.append({'wallet':ei,'decision_us':c.decision_us,'label_available_us':label_ready,'regime':reg,'winner':winner,'cell':cell,'hindsight_fixed_policy_21day_utility':future.tolist()})
        cells.append(group)
    counts=collections.Counter(d['cell'] for d in details);raw=np.array([1/np.sqrt(counts[d['cell']]) for d in details]);lo,hi=0.,1000.
    for _ in range(80):
        mid=(lo+hi)/2
        if np.clip(mid*raw,.5,2).mean()<1:lo=mid
        else:hi=mid
    scale=(lo+hi)/2;weights=[np.array([1. if c is None else np.clip(scale/np.sqrt(counts[c]),.5,2) for c in group]) for group in cells];assert abs(np.concatenate(weights).mean()-1)<1e-12;assert all(a[-1]==1 for a in weights)
    # Reuse original financial VJP as the uniform-weight golden.
    rng=np.random.default_rng(41);e=es[0];req=np.zeros((len(e.contexts),6));v=rng.uniform(.2,1,(len(req),4));v/=v.sum(1)[:,None];req[:,[0,1,4,5]]=v
    a,b,_=request_gradient(req,e,p,np.ones(len(req)));c,d,_=old_gradient(req,e,p);np.testing.assert_allclose(a,c,atol=1e-14,rtol=1e-12);np.testing.assert_allclose(b,d,atol=1e-12,rtol=1e-10)
    a,g,_=request_gradient(req,e,p,weights[0]);finite=[]
    for i in [10,30,60]:
        h=1e-6;l=req.copy();r=req.copy();l[i,5]+=h;l[i,1]-=h;r[i,5]-=h;r[i,1]+=h;fd=(request_gradient(l,e,p,weights[0])[0]-request_gradient(r,e,p,weights[0])[0])/(2*h);ad=g[i,5]-g[i,1];np.testing.assert_allclose(fd,ad,atol=2e-8,rtol=2e-3);finite.append({'row':i,'finite_difference':float(fd),'analytic':float(ad)})
    np.savez_compressed(out/'WEIGHTS.npz',**{f'wallet_{i}':w for i,w in enumerate(weights)})
    np.savez_compressed(out/'SCALER.npz',mean=scaler.mean,scale=scaler.scale,count=scaler.count)
    model,_=initialize(scaler)
    plan={'status':'READY_NOT_TRAINED','arms':['NATURAL','BALANCED'],'active_intervals':1290,'decisions':1293,'training_periods':[['2020-10-15','2020-12-31'],['2021-01-01','2021-12-31'],['2022-01-02','2024-04-30']],'training_cutoff_us':CUTOFF,'steps_each':256,'lr':.0003,'parameters':13699,'initialization':'same neutral SHORT prior1/3, fresh same seed; no parent weights','scaler_identity':scaler.identity,'scaler_provenance':scaler.provenance,'initial_model_identity':model_identity(model),'episode_identities':[e.identity for e in es],'source_binding':binding,'weight_rule':'clipped inverse-sqrt count of causal price regime x21day hindsight best fixed-policy utility; mean1,range[.5,2]; final20active days and paid terminal have weight1; no shuffled/reset wallets','labels_not_model_inputs':True,'winner_names':['CASH','VOL','CS','SHORT'],'joint_counts':dict(counts),'weight_ranges':[[float(a.min()),float(a.max())] for a in weights],'weight_SHA256':sha(out/'WEIGHTS.npz'),'uniform_gradient_golden':True,'finite_difference_checks':finite,'teacher_wallets':9,'validation':'2025 fixed continuous annual wallet, now seen-development forward validation; no gradient/scaler/model selection from2025; report both arms regardless of outcome','selection':'fixed256 only; no early-best or grid','resources':'singleCPU,2GBprocess,4GBaddress,8GBhostused,1200secperfit,checkpoint eachstep; noGPU/swap','original_financial_kernels_unchanged':True}
    (out/'PLAN.json').write_text(json.dumps(plan,indent=2)+'\n');(out/'LABELS.json').write_text(json.dumps(details,indent=2)+'\n');print(json.dumps(plan,indent=2))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--state',required=True);a.add_argument('--out',required=True);x=a.parse_args();torch.set_num_threads(1);torch.use_deterministic_algorithms(True);run(x.state,x.out)
