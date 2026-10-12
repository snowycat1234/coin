"""Saved-model training-internal short attribution, with no model fits."""
import argparse,importlib.util,io,json,time
from pathlib import Path
import numpy as np
import pandas as pd
from core import partition,runs,reliability
from modules.collector_research.pipeline.economics import replay
from scripts.research.conditional_selector_core import budget_path,RankProvenance
from scripts.investment.public_sma_perpetual import signed_risk_weights

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('old',ROOT/'research/minute-conditional-selector-20261011/experiment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
FULL=ROOT/'research/selector-support-pair-20261012';OLD=ROOT/'research/minute-conditional-selector-20261011'

def load():
    roles=pd.read_csv(FULL/'result/ACTUAL_LOSS_DATES.csv');roles=roles[roles.arm=='OWNED_FULL'].reset_index(drop=True)
    maximum=m.utc('2022-09-15');require= m.require
    require(len(roles)==607 and roles.decision_us.is_unique and (roles.reward_complete_maturity_us<maximum).all(),'True607 training role')
    source,frames,holes,_=m.load_inputs(OLD/'input')
    d=source['decision_us'];ix=np.flatnonzero(d<=roles.decision_us.max());d=d[ix]
    # No external 59-day forecast/result packet is opened or scored.
    for k in ('baseline','targets','expert_eligible','asset_eligible','baseline_ready'):source[k]=source[k][ix]
    source['decision_us']=d
    source['close']=source['close'][source['close_available_us']<=maximum]
    source['close_available_us']=source['close_available_us'][source['close_available_us']<=maximum]
    frames={s:f[f.available_us<=maximum].copy().reset_index(drop=True) for s,f in frames.items()}
    with np.load(OLD/'result/VECTORS.npz',allow_pickle=False) as z:
        labels={k:z[k][ix] for k in ('utility','label_net_return','label_fees_USDT','label_funding_USDT','label_complete','common_feature_known','A_prediction')}
        routed_d=z['eval_decision_us'];route_ix=np.flatnonzero(routed_d<=d[-1]);saved=dict(d=routed_d[route_ix],budgets=z['A_budgets'][route_ix],targets=z['A_targets'][route_ix])
    with np.load(OLD/'result/MODELS.npz',allow_pickle=False) as z:old={k:z[k].copy() for k in z.files if k.startswith('A_') or k=='training_indices'}
    with np.load(FULL/'result/MODELS.npz',allow_pickle=False) as z:full={k:z[k].copy() for k in z.files if k.startswith('OWNED_FULL_')}
    return roles,source,frames,holes,labels,saved,old,full

def sleeve_metrics(frames,index,w):
    metrics,trace=replay(frames,np.array([index]),w[None,:],1.,m.COST,m.CAPITAL)
    return dict(utility=m.reference_utility(metrics),net_USDT=metrics['net'],price_USDT=float(trace.price_pnl.sum()),
                fees_USDT=metrics['fees'],funding_cash_USDT=-metrics['funding'])

def run(state,source_commit,expected=None):
    m.require(not state.exists() and state.resolve().is_relative_to(Path('/workspace')),'Fresh STATE')
    m.require(not m.git('status','--porcelain'),'Clean published source')
    if not expected:m.require(m.git('rev-parse','HEAD').decode().strip()==source_commit,'Published source')
    m.verify_manifest(HERE/'ACTIVE_SOURCE_SHA256.txt');state.mkdir();start=time.monotonic()
    roles,source,frames,holes,v,saved,old,full=load();d=source['decision_us'];symbols=tuple(source['symbol_order'])
    train=np.isin(d,roles.decision_us);known=v['common_feature_known'];complete=v['label_complete'].all(1)
    x=np.column_stack([source['baseline'],source['targets'].reshape(len(d),-1),source['expert_eligible'],source['asset_eligible'].reshape(len(d),-1)]).astype(float)
    np.testing.assert_array_equal(np.flatnonzero(train),full['OWNED_FULL_training_indices'])
    fitted=((x[train]-full['OWNED_FULL_mean'])/full['OWNED_FULL_scale'])@full['OWNED_FULL_coef'].T+full['OWNED_FULL_intercept']
    oldtrain=old['training_indices'];clocks=roles.set_index('decision_us').reward_complete_maturity_us
    oldmax=int(clocks.loc[d[oldtrain]].max());fit=m.utc('2022-01-01');cutoff=m.utc('2021-12-31')
    calendar=np.flatnonzero(d>=m.utc('2022-01-02'));ed=d[calendar]
    RankProvenance(np.full(len(ed),fit,np.int64),np.full(len(ed),cutoff,np.int64),np.full(len(ed),oldmax,np.int64),
        np.full(len(ed),int(d[oldtrain].max()),np.int64),tuple([m.digest((OLD/'result/MODELS.npz').read_bytes())]*len(ed)),
        tuple([m.digest(old['A_mean'].tobytes()+old['A_scale'].tobytes())]*len(ed))).validate(ed)
    score=v['A_prediction'][calendar];good=known[calendar]
    restored=((x[calendar[good]]-old['A_mean'])/old['A_scale'])@old['A_coef'].T+old['A_intercept']
    np.testing.assert_allclose(restored,score[good],rtol=1e-13,atol=1e-16)
    p=np.where(np.isfinite(score),score,0.);eligible=source['expert_eligible'][calendar].copy();eligible[~good,1:]=False
    scale=float(old['A_utility_scale']);ideal,_=budget_path(p,scale,cash_index=0,eligible=eligible,max_l1=2.)
    path,_=budget_path(p,scale,cash_index=0,eligible=eligible,max_l1=.1)
    np.testing.assert_array_equal(ed,saved['d']);np.testing.assert_array_equal(path,saved['budgets'])
    w=source['targets'][calendar];ideal_net=np.einsum('ne,nek->nk',ideal,w);path_net=np.einsum('ne,nek->nk',path,w);risk_net=path_net.copy()
    for j,t in enumerate(ed):
        active=np.flatnonzero(risk_net[j]!=0)
        if not len(active):continue
        pos=int(np.searchsorted(source['close_available_us'],t));past=source['close'][pos-30:pos+1][:,active]
        m.require(past.shape==(31,len(active)) and np.isfinite(past).all(),'Past-only risk context')
        risk_net[j,active],_=signed_risk_weights(risk_net[j,active],np.diff(past,axis=0)/past[:-1],annual_vol_target=.10)
    np.testing.assert_allclose(risk_net,saved['targets'],rtol=1e-13,atol=1e-16)
    available=frames[symbols[0]].available_us.to_numpy(np.int64);fi=np.searchsorted(available,d)
    sleeve=[];short_y=np.full(len(d),np.nan);short_price=short_y.copy();short_fees=short_y.copy();short_funds=short_y.copy()
    for i in np.flatnonzero(train):
        cs=source['targets'][i,2];sh=sleeve_metrics(frames,fi[i],np.minimum(cs,0));lo=sleeve_metrics(frames,fi[i],np.maximum(cs,0))
        np.testing.assert_allclose(sh['net_USDT']+lo['net_USDT'],v['label_net_return'][i,2]*m.CAPITAL,rtol=1e-10,atol=1e-8)
        np.testing.assert_allclose(sh['fees_USDT']+lo['fees_USDT'],v['label_fees_USDT'][i,2],rtol=1e-12,atol=1e-10)
        np.testing.assert_allclose(sh['funding_cash_USDT']+lo['funding_cash_USDT'],-v['label_funding_USDT'][i,2],rtol=1e-12,atol=1e-10)
        short_y[i]=sh['utility'];short_price[i]=sh['price_USDT'];short_fees[i]=sh['fees_USDT'];short_funds[i]=sh['funding_cash_USDT']
        sleeve.append(dict(decision_us=int(d[i]),UTC_date=pd.Timestamp(int(d[i]),unit='us',tz='UTC').date().isoformat(),
            reward_maturity_us=int(clocks.loc[d[i]]),short_active=bool(np.any(cs<0)),**{'short_'+k:val for k,val in sh.items()},
            **{'long_'+k:val for k,val in lo.items()},CS_utility=float(v['utility'][i,2]),best_nonshort_utility=float(max(v['utility'][i,0:2]))))
    mask=train[calendar]&good&complete[calendar];active=(w[:,2]<0).any(1);positive=mask&active&(short_y[calendar]>0)
    fullbest=v['utility'][calendar,2]>np.max(v['utility'][calendar,:2],axis=1)
    rankbest=p[:,2]>np.max(p[:,:2],axis=1)
    negative=lambda a:(a<-1e-12).any(1)
    stage=partition(positive,fullbest,rankbest,negative(ideal_net),negative(path_net),negative(risk_net))
    stage[~mask]='UNKNOWN_TRAINING_LABEL_OR_FEATURE'
    records=[]
    for j,i in enumerate(calendar):records.append(dict(decision_us=int(d[i]),UTC_date=pd.Timestamp(int(d[i]),unit='us',tz='UTC').date().isoformat(),
        feature_known=bool(good[j]),complete_train_label=bool(mask[j]),short_expert_intent=bool(active[j]),positive_short_reference=bool(positive[j]),
        full_CS_best=bool(fullbest[j]) if mask[j] else None,predicted_CS_best=bool(rankbest[j]),attribution=str(stage[j]),
        predicted_CS_advantage=float(p[j,2]-max(p[j,:2])),actual_CS_advantage=float(v['utility'][i,2]-max(v['utility'][i,:2])) if mask[j] else None,
        desired_CS_allocation=float(ideal[j,2]),path_CS_allocation=float(path[j,2]),desired_net_short=bool(negative(ideal_net)[j]),
        path_net_short=bool(negative(path_net)[j]),risk_net_short=bool(negative(risk_net)[j]),
        below_fixed10USDT_short_target_assets=int(((risk_net[j]<-1e-12)&(-risk_net[j]*10000<10)).sum()),native_fill='UNKNOWN_NOT_RUN'))
    blocks={}
    for name,left,right in [('JAN_MAR','2022-01-02','2022-04-01'),('APR_JUN','2022-04-01','2022-07-01'),('JUL_SEP13','2022-07-01','2022-09-14')]:
        b=(ed>=m.utc(left))&(ed<m.utc(right));q=mask&b
        blocks[name]=dict(calendar_dates=int(b.sum()),complete_dates=int(q.sum()),short_intent_dates=int((q&active).sum()),
            positive_short_dates=int((positive&b).sum()),full_CS_winning_short_dates=int((q&active&fullbest).sum()),
            attribution={str(k):int(((stage==k)&b).sum()) for k in np.unique(stage)},
            mean_short_sleeve_utility=float(short_y[calendar[q]].mean()) if q.any() else None)
    opportunity_runs=runs(ed,positive);full_runs=runs(ed,mask&active&fullbest)
    rng=np.random.default_rng(811236);bootstart=rng.integers(0,len(ed),(1000,int(np.ceil(len(ed)/14))))
    draws=((bootstart[:,:,None]+np.arange(14))%len(ed)).reshape(1000,-1)[:,:len(ed)]
    outcomes=np.where(mask&active,short_y[calendar],np.nan);ci=np.quantile(np.nanmean(outcomes[draws],axis=1),[.025,.975])
    diagnostic=dict(status='COMPLETE_TRAINING_INTERNAL_SHORT_ATTRIBUTION',source_commit=source_commit,new_fits=0,new_wallets=0,provider_downloads=0,
        causal_model='ORIGINAL181_A_FIT2022JAN1',full607_model_role='IN_SAMPLE_DESCRIPTION_ONLY',causal_prediction_max_error=float(np.max(np.abs(restored-score[good]))),
        actual607_support=dict(dates=607,short_intent_dates=sum(r['short_active'] for r in sleeve),
            positive_short_sleeve_dates=sum(r['short_utility']>0 and r['short_active'] for r in sleeve),
            positive_short_CS_winner_dates=sum(r['short_utility']>0 and r['CS_utility']>r['best_nonshort_utility'] for r in sleeve),
            in_sample_CS_best_prediction_dates=int((fitted[:,2]>fitted[:,:2].max(1)).sum())),
        internal_validation=dict(calendar_dates=len(ed),common_mature_train_dates=int(mask.sum()),blocks=blocks,
            positive_short_dates=int(positive.sum()),positive_short_run_events=len(opportunity_runs),full_CS_winner_run_events=len(full_runs),
            conditional_short_mean_utility=float(np.nanmean(outcomes)),conditional_short_mean_95CI=ci.tolist(),bootstrap_seed=811236,bootstrap_calendar_days=14,
            attribution={str(k):int((stage==k).sum()) for k in np.unique(stage)},
            allocation_success_Brier=float(np.mean((ideal[mask&active,2]-fullbest[mask&active])**2)),
            allocation_reliability=reliability(ideal[:,2],fullbest,mask&active)),
        native_execution='UNKNOWN_NO_NEW_WALLET',conditional_funding='RAW_AS_FRACTION_PAST_MARK_NOT_CERTIFIED',
        short_cost_bridge='PASS_NET_FEES_FUNDING_FULL_CS_FROM_UNRESCALED_SLEEVES',events_are_not_iid=True,
        external59_validation_outcomes_used=False,forced_short_fraction=False,model_or_gate_tuned=False)
    pd.DataFrame(sleeve).to_csv(state/'TRAIN607_SLEEVE_COSTS.csv',index=False);pd.DataFrame(records).to_csv(state/'CAUSAL_INTERNAL_DATES.csv',index=False)
    m.save(state/'OPPORTUNITY_RUNS.json',dict(positive_short=opportunity_runs,full_CS_winner=full_runs))
    np.savez_compressed(state/'INTERNAL_PACKET.npz',decision_us=ed,complete_mask=mask,short_active=active,positive_short=positive,
        full_CS_best=fullbest,old_prediction=p,actual_CS_advantage=v['utility'][calendar,2]-np.max(v['utility'][calendar,:2],axis=1),
        desired_budget=ideal,path_budget=path,raw_targets=w,desired_net=ideal_net,path_net=path_net,risk_net=risk_net,
        train607_decision_us=d[train],full607_fitted_prediction=fitted)
    m.save(state/'RESULT.json',diagnostic);m.save(state/'TIMING.json',dict(seconds=time.monotonic()-start))
    if expected:
        for name in ('RESULT.json','OPPORTUNITY_RUNS.json','TRAIN607_SLEEVE_COSTS.csv','CAUSAL_INTERNAL_DATES.csv','INTERNAL_PACKET.npz'):
            m.require(m.git('show',expected+':research/short-selection-attribution-20261012/result/'+name)==(state/name).read_bytes(),'Exact public '+name)
        m.save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_SAVED_MODEL_INTERNAL_ATTRIBUTION',new_fits=0,new_wallets=0,artifact_commit=expected))
    m.require(time.monotonic()-start<120,'120s finite budget');print(json.dumps(diagnostic,indent=2),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);p.add_argument('--expected-commit');a=p.parse_args();run(a.state,a.source_commit,a.expected_commit)
