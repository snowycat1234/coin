"""Independent scalar Decimal check of labeled training proxies and packet hashes."""
import argparse
from decimal import Decimal as D, localcontext
import hashlib, json, os
from pathlib import Path
import resource


def verify(repo):
    import numpy as np
    here=repo/'research/recover-frozen-runner-20261009';packet=here/'short-candidate-contexts';read=lambda p:json.loads(p.read_bytes())
    manifest=read(packet/'CONTEXT_PACKET.json');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    for n,h in manifest['source_sha256'].items():assert sha(repo/n)==h,n
    for r in manifest['artifacts']:
        p=here/r['path'];assert sha(p)==r['sha256'] and p.stat().st_size==r['bytes'],r['path']
    with np.load(here/'temporal-economics/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz',allow_pickle=False) as z:base={k:z[k].copy() for k in z.files}
    targets=[base['expert_targets']];train=base['decision_us'];ep=base['episode_id']
    for p in (here/'short-contexts/TRAIN778_SHORT_CONTEXTS.npz',packet/'TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz'):
        with np.load(p,allow_pickle=False) as z:
            assert np.array_equal(z['decision_us'],train) and np.array_equal(z['episode_id'],ep)
            assert np.array_equal(z['expert_asset_eligible'][:,0],base['expert_asset_eligible'][:,1])
            assert (z['asset_context_available_us'][z['expert_asset_eligible'][:,0]]<=np.broadcast_to(train[:,None],(778,5))[z['expert_asset_eligible'][:,0]]).all()
            targets.append(z['expert_targets'].copy())
    targets=np.concatenate(targets,axis=1)
    assert len(train)==778 and (train<1714521600000000).all() and (base['end_execution_us']<1714521600000000).all()
    with np.load(packet/'TRAIN778_SHORT_COMPLEMENTARITY_PROXIES.npz',allow_pickle=False) as z:proxy={k:z[k].copy() for k in z.files}
    assert np.array_equal(proxy['decision_us'],train) and proxy['expert_order'].tolist()==manifest['diagnostic_expert_order']
    maxerr={k:0. for k in ('net_return','utility','price_return','signed_funding_return','cost_return','daily_endpoint_drawdown')}
    with localcontext() as c:
        c.prec=50
        for label,continuous in [('fresh_paid_daily_',False),('continuous_episode_',True)]:
            for e in range(5):
                nav=D(10000);q=[D(0)]*5
                for i in range(778):
                    if not continuous or i==0 or ep[i]!=ep[i-1]:nav=D(10000);q=[D(0)]*5
                    before=nav;p0=[D(str(float(x))) for x in base['start_price'][i]];p1=[D(str(float(x))) for x in base['end_price'][i]];fp=[D(str(float(x))) for x in base['funding_per_unit'][i]]
                    new=[before*D(str(float(targets[i,e,j])))/p0[j] for j in range(5)]
                    cost=sum(abs(new[j]-q[j])*p0[j] for j in range(5))*D('.00135')
                    price=sum(new[j]*(p1[j]-p0[j]) for j in range(5));fund=sum(new[j]*fp[j] for j in range(5));nav+=price-cost-fund;q=new
                    if not continuous or i==777 or ep[i+1]!=ep[i]:cost+=sum(abs(q[j])*p1[j] for j in range(5))*D('.00135');nav-=sum(abs(q[j])*p1[j] for j in range(5))*D('.00135');q=[D(0)]*5
                    r=nav/before-1;dd=max(D(0),-r);u=(1+r).ln()-D('.5')*dd
                    values=dict(net_return=r,utility=u,price_return=price/before,signed_funding_return=-fund/before,cost_return=cost/before,daily_endpoint_drawdown=dd)
                    assert nav>0
                    for k,v in values.items():maxerr[k]=max(maxerr[k],abs(float(v)-float(proxy[label+k][i,e])))
    assert max(maxerr.values())<1e-12,maxerr
    report=read(packet/'TRAINING_COMPLEMENTARITY.json');u=proxy['fresh_paid_daily_utility'];r=proxy['fresh_paid_daily_net_return'];bad=(r[:,1]<0)&(r[:,2]<0);best=np.maximum(0,np.maximum(u[:,1],u[:,2]))
    scores={}
    for e in (3,4):
        name=proxy['expert_order'][e];scores[name]=float(np.maximum(0,u[bad,e]-best[bad]).mean())
        v=report['primary_fresh_paid_one_day']['candidates'][name]['conditional']['EXPOST_BOTH_VOL_CS_NET_NEGATIVE']
        assert v['days']==int(bad.sum()) and abs(v['mean_positive_incremental_daily_utility']-scores[name])<1e-15
    assert report['recommendation']['first_candidate']==max(scores,key=scores.get)
    return dict(status='PASS_PUBLIC_PACKET_IDENTITIES_EXACT778_CLOCK_MASKS_AND_SCALAR_DECIMAL_PAIRED_PROXIES',training_dates=778,
                verified_expert_days_per_proxy_panel=3890,proxy_panels=2,maximum_scalar_errors=maxerr,recommendation=report['recommendation']['first_candidate'],
                original_pack_sha256=sha(here/'temporal-economics/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz'),models_fit=0,wallets_run=0,native_execution_equivalence_claim=False)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--output',type=Path);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    r=verify(a.repo)
    if a.output:
        with a.output.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
    print(json.dumps(r),flush=True)
