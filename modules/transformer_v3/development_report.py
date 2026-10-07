"""Compare complete reset wallets, retain every N/E, freeze before locked economics."""
import argparse,json,time
from pathlib import Path
import numpy as np
from modules.transformer_v2.train import atomic,sha
from modules.transformer_v2.report import compact_case,compare
from .train_policy import FAMILIES,SEEDS
from .funding_bridge import SCENARIOS

CANDIDATES=('PATCH_CROSS_ASSET_MULTITASK',*FAMILIES)

def compact(case,profile):
    for name in ('summary','independent_audit'):
        if sha(case[name+'_path'])!=case[name+'_sha256']:raise ValueError('Saved financial proof changed')
    row=compact_case(case);s=case['summary']
    row.update(profile=profile,task_id=case['task']['id'],liquidation_count=s['liquidation_count'],
               liquidation_loss_USDT=s['liquidation_loss_USDT'],liquidation_counts_by_symbol=s['liquidation_counts_by_symbol'],
               reentry_after_liquidation=s['reentry_after_liquidation'],execution_cost_USDT=s['execution_cost_USDT'],
               stopped_prefix_NAV_USDT=s['NAV'] if not row['full_calendar_and_paid_cash'] else None)
    return row

def profile_comparison(rows,models):
    summaries,paired,chosen=compare(rows,dict(models=list(models),seeds=list(SEEDS)))
    return summaries,paired,chosen

def half_linearity(rows):
    index={(r['family'],str(r['seed']),r['mapping'],r['funding_scale'],r['window'],r['profile']):r for r in rows}
    pairs=[]
    for key,full in index.items():
        if key[-1]!='FULL' or key[:-1]+('HALF',) not in index:continue
        half=index[key[:-1]+('HALF',)];complete=full['full_calendar_and_paid_cash'] and half['full_calendar_and_paid_cash']
        pairs.append(dict(family=key[0],seed=key[1],mapping=key[2],funding_scale=key[3],window=key[4],both_complete=complete,
            full_net_USDT=full['net_USDT'],half_net_USDT=half['net_USDT'],
            half_minus_half_full_USDT=half['net_USDT']-.5*full['net_USDT'] if complete else None,
            full_liquidation_count=full['liquidation_count'],half_liquidation_count=half['liquidation_count'],
            full_liquidation_loss_USDT=full['liquidation_loss_USDT'],half_liquidation_loss_USDT=half['liquidation_loss_USDT'],
            full_mean_gross=full['mean_gross'],half_mean_gross=half['mean_gross']))
    return pairs

def regret_comparison(old,new):
    index={(r['family'],str(r['seed']),r['fold'],r['funding_scale']):r for r in old};pairs=[]
    for row in new:
        family=dict(zip(FAMILIES,('CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK')))[row['family']]
        baseline=index[family,str(row['seed']),row['fold'],row['funding_scale']]
        for metric in ('mean_soft_policy_oracle_regret','mean_argmax_action_oracle_regret','expert_action_hit_rate_non_tie','rank_IC_mean','Spearman_mean'):
            a,b=baseline[metric],row[metric]
            pairs.append(dict(family=row['family'],baseline=family,seed=row['seed'],fold=row['fold'],funding_scale=row['funding_scale'],
                metric=metric,old=a,new=b,new_minus_old=b-a if a is not None and b is not None else None,
                scope='SAME_MATURE_DIAGNOSTIC_LABELS; REGRET_IS_DAILY_EXPERT_PROXY_NOT_WALLET_NET'))
    return pairs

def read_complete(path,count):
    value=json.loads(Path(path).read_text())
    if value['status']!='COMPLETE' or value['errors'] or len(value['cases'])!=count:raise ValueError('Every registered execution must finish: '+str(path))
    return value['cases']

def analyze(state,repo):
    state=Path(state);repo=Path(repo);protocol=repo/'reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json'
    proto=json.loads(protocol.read_text());rows=[]
    full=read_complete(state/'V2_BYBIT_LIQUIDATION_REPLAY.json',864)
    # All original FULL rows remain evidence, including noncausal oracle rows;
    # they never enter candidate ranking or get summed into a portfolio return.
    rows.extend(compact(c,'FULL') for c in full)
    rows.extend(compact(c,'HALF') for c in read_complete(state/'half-controls/HALF_CONTROL_RESULTS.json',348))
    rows.extend(compact(c,c['task']['profile']) for c in read_complete(state/'policy-development/POLICY_DEVELOPMENT_RESULTS.json',576))
    if max(r['contribution_sum_error'] for r in rows)>1e-6:raise ValueError('Long/short accounting bridge failed')
    summaries=[];paired=[];eligible=[]
    for profile in proto['development_selection']['profile_order']:
        own=[r for r in rows if r['profile']==profile and not r['noncausal'] and not r['task_id'].startswith(('development-exposure/','corrected-oracles/'))]
        s,p,_=profile_comparison(own,CANDIDATES)
        for row in s:row['profile']=profile
        for row in p:row['profile']=profile
        summaries.extend(s);paired.extend(p)
        eligible.extend(s0 for family in CANDIDATES for s0 in s if s0['family']==family and s0['rank_worst_scale_median_net'] is not None)
    if not eligible:raise ValueError('No fully comparable registered development candidate')
    chosen=sorted(eligible,key=lambda r:(r['rank_worst_scale_median_net'],r['rank_worst_scale_median_delta']),reverse=True)[0]
    comparator_summaries=[]
    for profile in ('FULL','HALF'):
        own=[r for r in rows if r['profile']==profile and not r['noncausal'] and not r['task_id'].startswith(('development-exposure/','corrected-oracles/'))]
        s,_,_=profile_comparison(own,(*CANDIDATES,'CROSS_ASSET_MULTITASK'))
        comparator_summaries.extend(dict(r,profile=profile) for r in s if r['family']=='CROSS_ASSET_MULTITASK')
    old_metrics=json.loads((state/'FROZEN_V2_PREDICTION_DIAGNOSTICS.json').read_text())['rows']
    new_metrics=json.loads((state/'POLICY_PREDICTION_METRICS.json').read_text())['rows']
    result=dict(status='DEVELOPMENT_COMPLETE_LOCKED_ECONOMICS_NOT_READ',protocol_sha256=sha(protocol),rows=rows,summaries=summaries,
        comparator_summaries=comparator_summaries,paired_deltas=paired,half_linearity=half_linearity(rows),
        prediction_metrics=old_metrics+new_metrics,regret_comparison=regret_comparison(old_metrics,new_metrics),
        chosen={k:chosen[k] for k in ('family','mapping','profile')},development_gate_pass=chosen['development_gate_pass'],
        complete_rows=sum(r['full_calendar_and_paid_cash'] for r in rows),total_rows=len(rows),locked_economics_read=False,
        no_partial_return_imputation=True,no_reset_wallet_return_splicing=True,no_winner_seed=True,
        certification='CONDITIONAL_MINUTE_MARK_BYBIT_STYLE; NATIVE_RISK_SNAPSHOT_UNAVAILABLE',
        sources={str(p.relative_to(state)):sha(p) for p in (state/'V2_BYBIT_LIQUIDATION_REPLAY.json',state/'half-controls/HALF_CONTROL_RESULTS.json',
            state/'policy-development/POLICY_DEVELOPMENT_RESULTS.json',state/'FROZEN_V2_PREDICTION_DIAGNOSTICS.json',state/'POLICY_PREDICTION_METRICS.json')})
    path=state/'TRANSFORMER_V3_DEV_RESULTS.json'
    if path.exists():
        if json.loads(path.read_text())!=result:raise ValueError('Existing development comparison changed')
    else:atomic(path,result)
    lines=['# Oracle-policy development comparison','',result['certification'],'',
        f"Complete calendar and paid terminal cash: {result['complete_rows']}/{len(rows)} rows. Stopped accounts remain N/E in the full row table.",
        'Independent reset wallets and overlapping windows are never added into one return. Fixed three-seed prediction ensembles are used.',
        '', '|Model|Profile|Mapping|Worst funding median net %|Paired delta strongest static pct|Gate|', '|---|---|---|---:|---:|---|']
    for r in summaries+comparator_summaries:
        values=['N/E' if r[k] is None else f'{r[k]:.4f}' for k in ('rank_worst_scale_median_net','rank_worst_scale_median_delta')]
        lines.append(f"|{r['family']}|{r['profile']}|{r['mapping']}|{values[0]}|{values[1]}|{r['development_gate_pass']}|")
    lines+=['', 'Frozen candidate: '+json.dumps(result['chosen']),f"Development gate: {result['development_gate_pass']}; a failed gate carries into the final decision.",
        'FULL/HALF matched differences, every seed/window/cost/liquidation/reentry, long/short net, MDD/vol/Sharpe and actual gross are in DEV_RESULTS.json.',
        'Prediction IC/rank/hit/spread and mature daily-proxy regret are separate from actual wallet net. No causal inference consumes future labels.',
        'Locked economics has not yet been read. Investment state: NONE/CASH.']
    (state/'TRANSFORMER_V3_DEV_REPORT.md').write_text('\n'.join(lines)+'\n')
    return result

def freeze_weights(state,v2,source_run,repo,result):
    state=Path(state);v2=Path(v2);weights=[];active_sets=[]
    for directory,name,count in ((state,'POLICY_FINAL_FITS.json',12),(v2,'FINAL_FITS.json',24)):
        fits=json.loads((directory/name).read_text())
        if fits['status']!='COMPLETE' or fits['completed']!=count:raise ValueError('All registered final past-only fits required')
        for fit in fits['results']:
            for file,field in (('weights.pt','weights_sha256'),('scaler.npz','scaler_sha256')):
                p=Path(fit['folder'])/file
                if sha(p)!=fit['result'][field]:raise ValueError('Protected final fit changed')
                weights.append(dict(path=str(p),sha256=sha(p),family=fit['task']['family'],seed=fit['task']['seed'],tag=fit['task']['tag']))
            active_sets.append(fit['task']['active'])
    if not all(a==active_sets[0] for a in active_sets):raise ValueError('Final active universe differs; no implicit common-universe selection')
    for tag in ('raw_fraction','raw_percent'):
        study=Path(json.loads(Path(source_run,tag,'RESEARCH.json').read_text())['study_dir']);folder=study/'models/fold5/TRANSFORMER_SHARED'
        checkpoint=json.loads((folder/'CHECKPOINT.json').read_text())
        for e in checkpoint['models']:
            p=folder/e['name']
            if sha(p)!=e['sha256']:raise ValueError('Protected legacy control changed')
            weights.append(dict(path=str(p),sha256=sha(p),family='OLD_FROZEN_TRANSFORMER_SHARED',tag=tag))
    old=json.loads((Path(repo)/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json').read_text())
    release=dict(status='FROZEN_DEVELOPMENT_WEIGHTS_AND_RISK_BEFORE_LOCKED_ECONOMICS',protocol_sha256=result['protocol_sha256'],
        development_results_sha256=sha(state/'TRANSFORMER_V3_DEV_RESULTS.json'),development_report_sha256=sha(state/'TRANSFORMER_V3_DEV_REPORT.md'),
        chosen=result['chosen'],development_gate_pass=result['development_gate_pass'],funding_bridges=list(SCENARIOS),
        funding_bridges_sha256=sha(state/'LOCKED_BRIDGE_PREREGISTRATION.json'),frozen_weights_and_scalers=weights,
        active_symbols=[s for s,a in zip(old['data']['symbols'],active_sets[0]) if a],
        risk_profiles=['FULL','HALF'],risk_assumption='MMR0.005_MMD0_NATIVE_LIMITS_UNKNOWN',locked_economics_read=False)
    path=state/'LOCKED_DEVELOPMENT_FREEZE.json'
    if path.exists():
        prior=json.loads(path.read_text())
        if {k:v for k,v in prior.items() if k!='frozen_at'}!=release:raise ValueError('Development release already frozen')
    else:atomic(path,dict(release,frozen_at=time.time()))
    return release

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--v2-state',required=True);p.add_argument('--source-run',required=True);a=p.parse_args()
    repo=Path(__file__).resolve().parents[2];result=analyze(a.state,repo);freeze_weights(a.state,a.v2_state,a.source_run,repo,result)
    print('DEVELOPMENT FROZEN',json.dumps(result['chosen']),result['development_gate_pass'],flush=True)

if __name__=='__main__':main()
