"""Read-only coverage counts from existing audited training proxy arrays.

No wallet, model inference, training, resampling or proxy rollout is performed.
Outcome labels are descriptive and must never become causal model features.
"""
import argparse,csv,hashlib,json
from datetime import datetime,UTC
from pathlib import Path
import numpy as np

HERE=Path(__file__).resolve().parent
DAY=86400000000
FILES={
 'short-candidate-contexts/TRAIN778_SHORT_COMPLEMENTARITY_PROXIES.npz':'e7fe203625c15ace4f875b91f7602fe8aab3ff6fa8351f98ed8fe312707b5883',
 'short-candidate-contexts/TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz':'64accfc82f78034af0da48561ef7e2fabfc8712760066860194e3d2bce9e382d',
 'temporal-economics/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz':'66c5fdb2317689ed1d084c3f8eeb6e1781fa04ccc15e6243784a03a3555e7676',
}


def date(t):return datetime.fromtimestamp(int(t)/1e6,UTC).date().isoformat()


def load(name,keys):
    p=HERE/name
    assert hashlib.sha256(p.read_bytes()).hexdigest()==FILES[name]
    # Unneeded object-valued metadata is deliberately never deserialized.
    with np.load(p,allow_pickle=False) as z:return {k:z[k].copy() for k in keys}


def contiguous_runs(mask,decisions,episodes):
    result=[];start=None
    for i in range(len(mask)):
        if mask[i]:
            if start is None:start=i
            if i+1<len(mask) and mask[i+1] and episodes[i+1]==episodes[i] and decisions[i+1]-decisions[i]==DAY:continue
            result.append(dict(episode_id=int(episodes[i]),first_date=date(decisions[start]),last_date=date(decisions[i]),days=i-start+1));start=None
    return result


def summarize(output,bundle):
    a=load(next(iter(FILES)),['decision_us','episode_id','fresh_paid_daily_utility','fresh_paid_daily_price_return','continuous_episode_utility','continuous_episode_price_return'])
    b=load('short-candidate-contexts/TRAIN778_MOMENTUM_SHORT_CONTEXTS.npz',['decision_us','episode_id','expert_targets','expert_eligible','expert_asset_eligible'])
    c=load('temporal-economics/PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz',['decision_us','episode_id','start_price','end_price','start_execution_us','end_execution_us'])
    d=a['decision_us'];ep=a['episode_id'];n=len(d);assert n==778 and int(c['end_execution_us'].max())<1714521600000000
    for other in (b,c):assert np.array_equal(other['decision_us'],d) and np.array_equal(other['episode_id'],ep)
    assert np.all(np.diff(d)>0) and np.all(c['start_execution_us']<c['end_execution_us'])
    assert np.all(c['end_execution_us'][:-1]<=c['start_execution_us'][1:])
    active=abs(b['expert_targets']).sum((1,2))>0;eligible=b['expert_eligible'][:,0]
    assert (active<=eligible).all() and b['expert_asset_eligible'].shape==(778,1,5)
    market=(c['end_price']/c['start_price']-1).mean(1)
    terminal=np.r_[ep[:-1]!=ep[1:],True];assert int(terminal.sum())==5
    panels={};labels={};run_rows=[]
    for panel in ('fresh_paid_daily','continuous_episode'):
        u=a[panel+'_utility'];p=a[panel+'_price_return'];assert u.shape==(778,5) and np.isfinite(u).all() and (u[:,0]==0).all()
        masks=dict(short_positive=u[:,4]>0,short_negative=u[:,4]<0,short_zero=u[:,4]==0,
                   short_beats_VOL=u[:,4]>u[:,1],short_beats_CS=u[:,4]>u[:,2],
                   short_beats_both=(u[:,4]>u[:,1])&(u[:,4]>u[:,2]),
                   short_positive_beats_both=u[:,4]>np.maximum(0,np.maximum(u[:,1],u[:,2])),
                   short_loses_on_CORE5_rebound=(u[:,4]<0)&(market>0),
                   short_loses_on_held_basket_rise=(u[:,4]<0)&(p[:,4]<0),
                   VOL_CS_MOM_all_lose=(u[:,1]<0)&(u[:,2]<0)&(u[:,4]<0),
                   all_four_risky_lose=(u[:,1:]<0).all(1),
                   both_existing_lose=(u[:,1]<0)&(u[:,2]<0),
                   short_positive_when_both_existing_lose=(u[:,4]>0)&(u[:,1]<0)&(u[:,2]<0))
        labels[panel]=masks;counts={};episode_rows=[]
        for name,mask in masks.items():
            runs=contiguous_runs(mask,d,ep)
            counts[name]=dict(dates=int(mask.sum()),episodes_with_condition=len(np.unique(ep[mask])),
                              consecutive_runs=len(runs),longest_run_days=max((r['days'] for r in runs),default=0))
            if name in ('short_positive','short_positive_beats_both','short_loses_on_CORE5_rebound','VOL_CS_MOM_all_lose'):
                run_rows.extend(dict(panel=panel,condition=name,**r) for r in runs)
        for e in np.unique(ep):
            ix=ep==e
            episode_rows.append(dict(episode_id=int(e),days=int(ix.sum()),first_date=date(d[ix][0]),last_date=date(d[ix][-1]),
                                     short_active_dates=int((active&ix).sum()),short_utility_sum=float(u[ix,4].sum()),
                                     short_mean_utility=float(u[ix,4].mean()),counts={k:int((v&ix).sum()) for k,v in masks.items()}))
        panels[panel]=dict(counts=counts,episodes=episode_rows,
                          nonterminal_decision_counts={k:int((v&~terminal).sum()) for k,v in masks.items()})
    weights=[]
    for e in np.unique(ep):
        size=int((ep==e).sum());old=size/n;proposed=.5*old+.5/5
        weights.append(dict(episode_id=int(e),days=size,current_objective_weight=old,
                            proposed_half_date_half_episode_weight=proposed,proposed_per_day_multiplier=proposed/old))
    assert abs(sum(r['current_objective_weight'] for r in weights)-1)<1e-12 and abs(sum(r['proposed_half_date_half_episode_weight'] for r in weights)-1)<1e-12
    gradient=bundle/'GRADIENT_SOURCE.py';objective=bundle/'OBJECTIVE_SOURCE.py';inputs=bundle/'INPUT_SOURCE.py'
    bound={n:hashlib.sha256(p.read_bytes()).hexdigest() for n,p in [('GRADIENT_SOURCE.py',gradient),('OBJECTIVE_SOURCE.py',objective),('INPUT_SOURCE.py',inputs)]}
    assert bound=={'GRADIENT_SOURCE.py':'c93bb567d11d49de6b45c689e216070d9053ea5371a39983181fa56f69c7c228','OBJECTIVE_SOURCE.py':'c438a85a1853f7b8cef02dede194dd3c905d93f74bbb2882b5ae0fd8d50ad040','INPUT_SOURCE.py':'e9b175aadede32539eefc25cc64c4d98964e7e2b166278f972c41f1dedcffcf5'}
    assert 'weight = len(episode.contexts) / total' in gradient.read_text() and 'loss_sum += loss * weight' in gradient.read_text() and 'LOOKBACK = 64' in inputs.read_text()
    warmup_rows=set(int(t)-j*DAY for t in d for j in range(64))
    adjacent_window_overlap=np.maximum(0,64-np.diff(d)//DAY)
    result=dict(schema='CACHED_TRAIN778_SHORT_REGIME_COVERAGE_AND_LOSS_WEIGHT_V1',status='PASS_READ_ONLY_BOUND_AUDITED_CACHED_ARRAY_COUNTS_NO_ROLLOUT_OR_FIT',
                source_input_SHA256=FILES,training_dates=778,continuous_economic_wallet_episodes=5,
                availability=dict(expert_available_dates=int(eligible.sum()),expert_unavailable_dates=int((~eligible).sum()),
                                  eligible_asset_dates=int(b['expert_asset_eligible'].sum()),total_asset_dates=3890,
                                  excluded_asset_dates=int((~b['expert_asset_eligible']).sum()),active_dates=int(active.sum()),available_but_cash_dates=int((eligible&~active).sum())),
                terminal_decisions=dict(dates=[date(t) for t in d[terminal]],count=5,
                   caveat='Current mapped v2 path forces zero targets on each final decision. Cached standalone reference labels still include that interval, so exclude these five rows when interpreting possible new-action entry coverage; closure costs remain in the full-wallet loss.'),
                panels=panels,current_v2_loss=dict(source_SHA256=bound,episode_weights=weights,
                  formula='L_e=-sum(log(NAV_next/NAV_prev)-5*min(daily_return,0)^2)/n_e; L=sum((n_e/778)*L_e)=-sum(all_daily_path_utilities)/778',
                  model_pool='CURRENT_FIXED_VOL_CS_WITH_OPTIONAL_CASH; MOMENTUM_SHORT_NOT_YET_IN_CURRENT_TRAIN_LOSS',
                  actual_per_episode_loss_and_gradient_contributions='NOT_EXPORTED; aggregate terminal loss cannot recover them; no model or checkpoint loaded'),
                dependence=dict(outcome_intervals_overlap_pairs=0,adjacent_intervals_share_boundary_pairs=int((c['end_execution_us'][:-1]==c['start_execution_us'][1:]).sum()),
                  adjacent_consecutive_decision_pairs=int((np.diff(d)==DAY).sum()),lookback_days=64,
                  distinct_64_day_calendar_feature_completion_dates=len(warmup_rows),adjacent_window_pairs_with_overlap=int((adjacent_window_overlap>0).sum()),
                  consecutive_decisions_share_feature_days=63,
                  cross_episode_adjacent_feature_overlap_days=[int(x) for x in adjacent_window_overlap[ep[1:]!=ep[:-1]]],
                  interpretation='778 disjoint one-day outcome intervals; overlapping feature windows, wallet state and descriptive masks do not yield778 independent trials. Five separate wallets are not five statistically independent market draws. Consecutive outcome runs are not new independent episodes.'),
                definitions=dict(short_positive='cached net utility>0 including recorded costs and signed funding',
                  beats_both='strict utility excess over both VOL and CS, may merely be cash or a smaller loss',
                  positive_beats_both='strict excess over max(CASH=0,VOL,CS)',
                  CORE5_rebound='ex-post equally weighted mean(end_execution_price/start_execution_price-1)>0; never an available-at-decision gate',
                  held_basket_rise='cached short price_return<0; its held short basket rose',
                  all_experts='VOL/CS/MOM risky pool; CASH utility is always0 and never loses; Donchian counted separately as fourth risky comparator'),
                proxy_limitations='Cached old diagnostic utility log1p(r)-.5*max(0,-r), independently unramped expert targets, not the current v2 shared-wallet objective or native risk-order execution. Fresh panel pays entry/exit daily; continuous panel retains quantities per episode. No new proxy paths were run.',
                proposed_experiment=dict(status='RECOMMEND_ONE_MODERATE_CONTROLLED_WEIGHT_COMPARISON_AFTER_FIXED_POOL;NOT_RUN',
                  episode_weight='.5*(n_e/778)+.5*(1/5)',rationale='Measured length imbalance warrants checking sensitivity, not training only on ex-post profitable short labels.',
                  preserve='all dates; winner and rebound losses; whole chronological wallets; causal features; masks; same mapper/costs/paid terminal flattening; source-bound objective; fixed architecture/LR/step budget',
                  evaluate='Freeze after training-only budget; report each training episode including adverse rebound rows; then full predeclared seen development native comparison. No June selection or weighting search.',
                  uncertainty='Short mean cached utility is negative in every episode under both references. Length balancing is not regime balancing and may reduce performance.'),
                models_loaded=0,fits=0,wallets_run=0,new_proxy_rollouts=0,development_outcomes_read=0,provider_downloads=0)
    output.mkdir(exist_ok=False)
    (output/'COVERAGE.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    with (output/'TRAIN778_DESCRIPTIVE_LABELS.csv').open('x',newline='') as f:
        columns=['date','episode_id','short_available','short_active','current_v2_forced_terminal_cash']+[panel+'_'+k for panel,masks in labels.items() for k in masks]
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for i in range(n):
            row=dict(date=date(d[i]),episode_id=int(ep[i]),short_available=int(eligible[i]),short_active=int(active[i]),current_v2_forced_terminal_cash=int(terminal[i]))
            row.update({panel+'_'+k:int(v[i]) for panel,masks in labels.items() for k,v in masks.items()});writer.writerow(row)
    with (output/'CONTIGUOUS_OUTCOME_RUNS.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['panel','condition','episode_id','first_date','last_date','days']);writer.writeheader();writer.writerows(run_rows)
    print(json.dumps(dict(status=result['status'],availability=result['availability'],fresh_counts=panels['fresh_paid_daily']['counts'],continuous_counts=panels['continuous_episode']['counts'],loss_weights=weights,dependence=result['dependence'])),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();summarize(a.output,a.bundle)
