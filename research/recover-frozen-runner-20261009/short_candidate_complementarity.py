"""Training-only action, target and explicitly conditional daily-proxy evidence."""
import argparse, hashlib, json, os
from pathlib import Path
import resource, socket, sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
import native61 as frozen

EXPERTS=('CASH','VOL_MANAGED_HOLD','CSMOM21','DONCHIAN20_EXIT10_SHORT_ONLY','MOMENTUM30_SHORT_ONLY')
ORIGINAL_SHA='66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676'


def correlation(a,b):
    import numpy as np
    return float(np.corrcoef(a,b)[0,1]) if np.std(a)>0 and np.std(b)>0 else None


def proxy_panel(targets,p0,p1,funding,episodes,continuous):
    """Same original quantity proxy; no native-account or switch-oracle claim."""
    import numpy as np
    from modules.collector_research.pipeline.economics import proxy_step
    shape=targets.shape[:2]; out={k:np.zeros(shape) for k in ('net_return','utility','price_return','signed_funding_return','cost_return','daily_endpoint_drawdown')}
    for e in range(shape[1]):
        nav=10000.; q=np.zeros(5)
        for i in range(shape[0]):
            if not continuous or i==0 or episodes[i]!=episodes[i-1]:nav=10000.;q=np.zeros(5)
            before=nav
            nav,q,cost,fund,notional,price=proxy_step(nav,q,targets[i,e],p0[i],p1[i],funding[i],np.ones(5,bool),.00135)
            terminal=not continuous or i==shape[0]-1 or episodes[i+1]!=episodes[i]
            if terminal:
                fee=float((abs(q)*p1[i]).sum())*.00135;nav-=fee;cost+=fee;q=np.zeros(5)
            r=nav/before-1;dd=max(0.,-r)
            frozen.require(nav>0 and abs(r-(price-cost-fund)/before)<1e-12,'Proxy price/cost/funding bridge differs')
            for k,v in dict(net_return=r,utility=float(np.log1p(r)-.5*dd),price_return=price/before,signed_funding_return=-fund/before,cost_return=cost/before,daily_endpoint_drawdown=dd).items():out[k][i,e]=v
    return out


def evidence(targets,raw,eligible,assets,panel,episodes,past):
    import numpy as np
    r=panel['net_return'];u=panel['utility'];net=targets.sum(2);gross=abs(targets).sum(2);active=gross>0
    tails=(r<=np.quantile(r,.05,axis=0))&(r<0)
    best=np.maximum(0,np.maximum(u[:,1],u[:,2]));conditions={
        'ALL_TRAINING':np.ones(len(r),bool),
        'PAST30_CORE5_MEAN_COMPOUND_RETURN_NEGATIVE':np.mean(np.prod(1+past,axis=1)-1,axis=1)<0,
        'PAST30_CORE5_MEAN_COMPOUND_RETURN_NONNEGATIVE':np.mean(np.prod(1+past,axis=1)-1,axis=1)>=0,
        'EXPOST_VOL_NET_NEGATIVE':r[:,1]<0,
        'EXPOST_CS_NET_NEGATIVE':r[:,2]<0,
        'EXPOST_BOTH_VOL_CS_NET_NEGATIVE':(r[:,1]<0)&(r[:,2]<0),
        'EXPOST_VOL_BOTTOM5_LOSS':tails[:,1],
        'EXPOST_CS_BOTTOM5_LOSS':tails[:,2]}
    pairs=[]
    for a in range(1,len(EXPERTS)):
        for b in range(a+1,len(EXPERTS)):
            ta=targets[:,a];tb=targets[:,b];den=float(np.maximum(abs(ta),abs(tb)).sum());shared=float((np.minimum(abs(ta),abs(tb))*(ta*tb>0)).sum());opposite=float((np.minimum(abs(ta),abs(tb))*(ta*tb<0)).sum())
            pairs.append(dict(a=EXPERTS[a],b=EXPERTS[b],net_target_correlation=correlation(net[:,a],net[:,b]),
                pooled_same_asset_target_correlation=correlation(ta.ravel(),tb.ravel()),daily_net_proxy_return_correlation=correlation(r[:,a],r[:,b]),
                same_sign_target_overlap=shared/den if den else None,opposite_sign_target_overlap=opposite/den if den else None,
                active_days_a=int(active[:,a].sum()),active_days_b=int(active[:,b].sum()),active_days_both=int((active[:,a]&active[:,b]).sum()),
                negative_days_a=int((r[:,a]<0).sum()),negative_days_b=int((r[:,b]<0).sum()),shared_negative_days=int(((r[:,a]<0)&(r[:,b]<0)).sum()),
                fraction_b_loses_on_a_loss=float(np.mean(r[r[:,a]<0,b]<0)) if (r[:,a]<0).any() else None,
                bottom5_loss_days_a=int(tails[:,a].sum()),bottom5_loss_days_b=int(tails[:,b].sum()),shared_bottom5_loss_days=int((tails[:,a]&tails[:,b]).sum())))
    candidates={}
    for e in (3,4):
        conditional={}
        for name,mask in conditions.items():
            own=u[mask,e];diff=own-best[mask]
            conditional[name]=dict(days=int(mask.sum()),active_candidate_days=int((active[:,e]&mask).sum()),
                mean_daily_net_return=float(r[mask,e].mean()) if mask.any() else None,mean_daily_utility=float(own.mean()) if mask.any() else None,
                mean_utility_minus_VOL=float((own-u[mask,1]).mean()) if mask.any() else None,
                mean_utility_minus_CS=float((own-u[mask,2]).mean()) if mask.any() else None,
                mean_utility_minus_CASH=float(own.mean()) if mask.any() else None,
                mean_utility_minus_best_existing_including_CASH=float(diff.mean()) if mask.any() else None,
                positive_incremental_utility_days=int((diff>0).sum()),mean_positive_incremental_daily_utility=float(np.maximum(0,diff).mean()) if mask.any() else None,
                nonnegative_candidate_on_condition_days=int((r[mask,e]>=0).sum()))
        by_episode=[]
        for ep in np.unique(episodes):
            mask=episodes==ep;adverse=mask&conditions['EXPOST_BOTH_VOL_CS_NET_NEGATIVE'];gain=np.maximum(0,u[:,e]-best)
            by_episode.append(dict(episode_id=int(ep),days=int(mask.sum()),active_days=int((mask&active[:,e]).sum()),mean_daily_net_return=float(r[mask,e].mean()),
                both_existing_adverse_days=int(adverse.sum()),mean_positive_incremental_utility_on_adverse=float(gain[adverse].mean()) if adverse.any() else None))
        candidates[EXPERTS[e]]=dict(expert_available_days=int(eligible[:,e].sum()),active_target_days=int(active[:,e].sum()),eligible_but_cash_days=int((eligible[:,e]&~active[:,e]).sum()),
            eligible_asset_dates=int(assets[:,e].sum()),active_asset_dates=int((raw[:,e]!=0).sum()),mean_target_gross=float(gross[:,e].mean()),peak_target_gross=float(gross[:,e].max()),
            mean_signed_target=float(net[:,e].mean()),conditional=conditional,by_episode=by_episode)
    return dict(pairs=pairs,candidates=candidates,
        positive_incremental_utility_role='EXPOST_POINTWISE_OPPORTUNITY_ASSOCIATION_ONLY; NOT_SWITCHING_ORACLE_OR_PORTFOLIO_PNL',
        conditional_future_outcomes='Training-only adverse and tail conditions are ex-post descriptive labels, never available-at-decision selection gates')


def run(state,contexts,output,plan):
    import numpy as np
    frozen.modules(state); output.mkdir(parents=True,exist_ok=False)
    protocol=frozen.read(plan)
    for n,d in protocol['source_sha256'].items():frozen.require(frozen.sha(frozen.REPO/n)==d,'Bound diagnostic source differs: '+n)
    original=HERE/'temporal-economics/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz';frozen.require(frozen.sha(original)==ORIGINAL_SHA,'Original three-slot pack changed')
    with np.load(original,allow_pickle=False) as z:base={k:z[k].copy() for k in z.files}
    train=base['decision_us'];episodes=base['episode_id'];targets=[base['expert_targets']];raw=[base['expert_raw_targets']];eligible=[base['expert_eligible']];assets=[base['expert_asset_eligible']]
    bindings=[]
    for p,name,expected in [(HERE/'short-contexts/TRAIN778_SHORT_CONTEXTS.npz',EXPERTS[3],'5e80d2703bfc669cf03fb889b8bc9666fde671aaa31f6c22012bcc7396ee2943'),
                            (contexts/'TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz',EXPERTS[4],frozen.read(contexts/'MOMENTUM_CONTEXT_READY.json')['contexts'][0]['sha256'])]:
        frozen.require(frozen.sha(p)==expected,'Frozen short target packet differs')
        with np.load(p,allow_pickle=False) as z:
            frozen.require(np.array_equal(z['decision_us'],train) and np.array_equal(z['episode_id'],episodes) and z['symbol_order'].tolist()==list(frozen.SYMBOLS) and z['expert_order'].tolist()==[name],'Aligned training-only context identity required')
            targets.append(z['expert_targets'].copy());raw.append(z['expert_raw_targets'].copy());eligible.append(z['expert_eligible'].copy());assets.append(z['expert_asset_eligible'].copy())
        bindings.append(dict(expert=name,sha256=expected))
    targets=np.concatenate(targets,axis=1);raw=np.concatenate(raw,axis=1);eligible=np.concatenate(eligible,axis=1);assets=np.concatenate(assets,axis=1)
    frozen.require(len(train)==778 and (train<frozen.START).all() and (base['end_execution_us']<frozen.START).all() and np.isfinite(targets).all(),'Exact mature pre-May778 training-only dates required')
    fresh=proxy_panel(targets,base['start_price'],base['end_price'],base['funding_per_unit'],episodes,False)
    continuous=proxy_panel(targets,base['start_price'],base['end_price'],base['funding_per_unit'],episodes,True)
    primary=evidence(targets,raw,eligible,assets,fresh,episodes,base['past_returns30'])
    secondary=evidence(targets,raw,eligible,assets,continuous,episodes,base['past_returns30'])
    criterion='EXPOST_BOTH_VOL_CS_NET_NEGATIVE'
    ranking=sorted((dict(expert=n,score=v['conditional'][criterion]['mean_positive_incremental_daily_utility']) for n,v in primary['candidates'].items()),key=lambda x:(-x['score'],x['expert']))
    filename=output/'TRAIN778_SHORT_COMPLEMENTARITY_PROXIES.npz'
    np.savez_compressed(filename,decision_us=train,episode_id=episodes,expert_order=np.array(EXPERTS),
        **{'fresh_paid_daily_'+k:v for k,v in fresh.items()},**{'continuous_episode_'+k:v for k,v in continuous.items()})
    report=dict(schema='TRAINING_ONLY_TWO_FROZEN_SHORT_CANDIDATE_COMPLEMENTARITY_V1',status='PASS_BOUND_TARGETS_AND_PAIRED_CONDITIONAL_DAILY_PROXY_DIAGNOSTICS_NO_FITS',
        training_dates=778,training_episodes=len(np.unique(episodes)),training_last_outcome_us=int(base['end_execution_us'].max()),original_three_slot_payload_sha256=ORIGINAL_SHA,
        original_pack_unchanged=True,source_sha256=protocol['source_sha256'],plan_sha256=frozen.sha(plan),short_context_bindings=bindings,
        expert_order=EXPERTS,proxy_conventions=protocol['proxy_conventions'],primary_fresh_paid_one_day=primary,secondary_continuous_single_expert_episode=secondary,
        recommendation=dict(first_candidate=ranking[0]['expert'],training_only_predeclared_ranking=ranking,
            criterion=protocol['recommendation_criterion'],not_based_on_unconditional_positive_return=True,requires_corrected_proxy_risk_order_and_separate_controlled_pool_expansion_protocol=True,
            uncertainty='Training association and retrospective candidate comparison, not evidence of learnable timing, achievable shared-wallet gain or OOS alpha'),
        feasible_shared_wallet_constrained_oracle=dict(status='NOT_IMPLEMENTED_IN_INSPECTED_REUSABLE_CODE; NOT_RUN',incremental_bound=None,
            inspected=protocol['oracle_inspection'],reason='Existing optimal_path is rebased independent expert growth with boundary surcharge; no shared quantities, cash-to-expertL1<=.1 constraint or native schedule/cost state. Existing oracle targets/replay are feasible comparators, not an optimizing incremental bound. No new optimizer built.'),
        proxy_payload=dict(path=filename.name,bytes=filename.stat().st_size,sha256=frozen.sha(filename),role='TRAINING_OUTCOME_DIAGNOSTICS_ONLY_NOT_CAUSAL_FEATURES_OR_EXPANDED_MODEL_PACK'),
        development_outcomes_used_for_selection=False,development_payload_read_by_diagnostics=False,models_fit=0,scalers_fit=0,new_wallets=0,provider_downloads=0,recipe_changes=0,pool_promotion=False)
    frozen.require(frozen.sha(original)==ORIGINAL_SHA,'Original pack modified')
    (output/'TRAINING_COMPLEMENTARITY.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps(dict(status=report['status'],recommendation=report['recommendation'],candidates={n:{k:v[k] for k in ('expert_available_days','active_target_days','eligible_asset_dates','mean_target_gross','peak_target_gross')}|dict(adverse=v['conditional'][criterion]) for n,v in primary['candidates'].items()})),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',type=Path,required=True);p.add_argument('--contexts',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);a=p.parse_args()
    for k in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','POLARS_MAX_THREADS','NUMEXPR_NUM_THREADS'):os.environ[k]='1'
    os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(6000000000,6000000000));resource.setrlimit(resource.RLIMIT_CPU,(120,120))
    def blocked(*a,**kw):raise RuntimeError('Offline complementarity diagnostics forbid network')
    socket.create_connection=blocked;socket.socket.connect=blocked
    run(a.state,a.contexts,a.output,a.plan)
