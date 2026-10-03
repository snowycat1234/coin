"""UNRUN D045 saved-summary comparison; no arrays, prices, QA or account replay.
--binding --run-dir --output. Plan: ready_to_execute/helper_sha256/frozen_sources,
budgets/run_dir/output_path/market_protocol{path,sha256}/roles MARKET,FINANCE.
Refs: path,sha256,required_status,task_id. finance required_status comes from
its frozen final contract, not a guessed success field. source_aliases optional.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,resource,shlex,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
VIEW='scripts/investment/compare_perpetual_213_results.py';VIEW_SHA='c7af4ac72b0332e27b41312f58362e255cacd94614de3173a64725e67b361792'
CONTRACT='D045_FIXED_303D_SAVED_SUMMARY_COMPARISON_V1'
MARKET_CONTRACT='D045_FIXED_303D_SMA_DIRECTIONS_AND_CONSTANT_LONG_CONDITIONAL_V1'
MARKET_STATUS='COMPLETE_D045_FIXED303D_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
STATUS='COMPLETE_D045_303D_SAVED_SUMMARY_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
AUDIT_STATUS='PASS_D045_TWENTY_FIXED303D_SMA_HOLD_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
BUDGET=dict(new_owned_bytes=5_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)
HOLD='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
SMA='COIN_JESSE_SMA50_200_1D_USDT_PERPETUAL_ADAPTER'
SELECTORS=('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH','HOLD_LONG_ONLY')
COSTS=('BASE27','STRESS43');UNITS=('RAW_AS_FRACTION','RAW_AS_PERCENT')
MONTHS=[f'2024-{m:02d}' for m in range(9,13)]+[f'2025-{m:02d}' for m in range(1,7)]
PAIRS=(('LS_MINUS_LO','LONG_SHORT','LONG_ONLY'),('SO_MINUS_CASH','SHORT_ONLY','CASH'),
 ('LS_MINUS_SO','LONG_SHORT','SHORT_ONLY'),('LS_MINUS_HOLD','LONG_SHORT','HOLD_LONG_ONLY'),('HOLD_MINUS_CASH','HOLD_LONG_ONLY','CASH'))
PRIOR_COMPARISON=('reports/fast_research/PERPETUAL_HOLD_ECONOMIC_COMPARISON_20261003_V1.json','7bacf7a20203ccb176c1f9e35a79c60bd24d661738454421591ef30f890a976d')
PRIOR_ROOT=('reports/fast_research/PERPETUAL_HOLD_ROOT_ACCEPTANCE_20261003_V2.json','efc44e8a8bbbb77bfb60fce016d51c65739cef581ac3c43724cfcc340df9e87c')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(name,digest,label):
    p=ROOT/name
    if p.is_symlink() or sha(p)!=digest:raise ValueError('Exact reused metadata code '+name)
    s=importlib.util.spec_from_file_location(label,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def guard():return load(GUARD,GUARD_SHA,'d045_summary_guards')
def pin(g,name,digest,aliases=()):
    if name=='state/dataset_lock.json':g.check(sha(g.project(name))==digest,'Private lock streamed hash only');return name
    selected=[r for r in aliases if r['original_path']==name and r['original_sha256']==digest]
    g.check(len(selected)<=1,'Unique explicit source alias')
    if selected:
        r=selected[0];allowed={'docs/OPEN_SOURCE_REGISTRY.md':'docs/archive/OPEN_SOURCE_REGISTRY_',
         'third_party/ts2vec/UPSTREAM.md':'third_party/ts2vec/UPSTREAM_FR68_CORE_20261001.md'}
        g.check(name in allowed and r['archive_path'].startswith(allowed[name]),'Only accepted narrow provenance alias');name=r['archive_path']
    g.small(g.project(name),digest,False);return name
def role(g,r):
    v,h=g.small(g.project(r['path']),r['sha256']);g.check(v['status']==r['required_status'] and v['binding']['task_id']==r['task_id'],'Exact frozen actual role')
    t=g.closed(r['task_id'])
    if v.get('run_dir') and v.get('run_binding_sha256'):
        rb,_=g.small(Path(v['run_dir'])/'RUN_BINDING.json',v['run_binding_sha256']);g.check(rb==v['binding'],'Exact actual RUN_BINDING')
    return v,h,t
def comparisons(cases,proofs,v,g):
    index={};expected={(c,u,s) for c in COSTS for u in UNITS for s in SELECTORS}
    for c in cases:
        selector=c['selector_mode'];key=c['cost_id'],c['unit_id'],selector;proof=proofs[c['id']];s=c['summary']
        g.check(key in expected and key not in index and c['period']=='303D' and s['required_minutes']==436320,'Exact303 selector/calendar')
        g.check(c['strategy_id']==s['strategy_id']==(HOLD if selector=='HOLD_LONG_ONLY' else SMA),'Strategy identity, not direction alias')
        if proof['complete_calendar_verified']:g.check(s['completed_minutes']==436320 and [r['month'] for r in s['months']]==MONTHS,'All ten whole months')
        row=v.view(c,proof);row['selector']=selector;row['period']='303D';index[key]=row
    g.check(set(index)==expected,'All20 saved selectors, no subset')
    groups=[]
    for cost in COSTS:
        for unit in UNITS:
            rows={s:index[cost,unit,s] for s in SELECTORS};pairs=[]
            for label,left,right in PAIRS:
                a,b=rows[left],rows[right];full=a['complete_calendar'] and b['complete_calendar'];risk=(a['realized_annual_volatility'],b['realized_annual_volatility'],a['summary']['all_observation_max_drawdown'],b['summary']['all_observation_max_drawdown'])
                evaluable=full and all(x is not None for x in risk);delta={k:a['summary'][k]-b['summary'][k] for k in v.MONEY} if evaluable else None
                months=[]
                if evaluable:
                    for x,y in zip(a['saved_months'],b['saved_months'],strict=True):
                        g.check(x['month']==y['month'],'Identical continuous month pair');months.append(dict(month=x['month'],delta_net_USDT=x['net_PnL']-y['net_PnL'],delta_gross_USDT=x['gross_PnL']-y['gross_PnL'],delta_funding_USDT=x['funding_USDT']-y['funding_USDT']))
                attribution=None
                if label=='LS_MINUS_LO' and evaluable:
                    legs=a['summary']['long_short_marked_contribution'];attribution=dict(LS_short_net=legs['SHORT']['net_contribution'],LS_long_minus_LO_net=legs['LONG']['net_contribution']-b['summary']['net_PnL'])
                    g.near(sum(attribution.values()),delta['net_PnL'],1e-7)
                pairs.append(dict(comparison=label,left=a['id'],right=b['id'],scope='FULL_SEPARATE_ACCOUNTS' if evaluable else 'NOT_EVALUABLE_FULL_PERIOD_OR_MISSING_RISK',delta_USDT=delta,delta_full_capital_return_percentage_points=delta['net_PnL']/100 if evaluable else None,delta_realized_volatility=risk[0]-risk[1] if evaluable else None,delta_all_observation_MDD=risk[2]-risk[3] if evaluable else None,monthly_deltas=months,LS_minus_LO_decomposition=attribution,risk_equalized=False,pure_short_causal_effect_identified=False))
            groups.append(dict(period='303D',cost_id=cost,unit_id=unit,selectors=rows,paired_deltas=pairs))
    return groups
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('binding','run-dir','output'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();g=guard();plan,ph=g.small(a.binding);started=time.monotonic();before=resources.status();g.bounded(before)
    g.check(os.getenv('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2' and plan['ready_to_execute'] is True and plan['helper_sha256']==sha(__file__) and plan['contract_id']==CONTRACT and plan['budgets']==BUDGET,'Actual root-frozen clean metadata comparison')
    g.check(a.binding.parent==ROOT/'protocols' and a.run_dir.parent==STATE and a.run_dir==Path(plan['run_dir']) and not a.run_dir.exists() and a.output==ROOT/plan['output_path'] and a.output.parent==ROOT/'reports/fast_research' and not a.output.exists(),'Fresh STATE/output')
    hashes=dict(plan['frozen_sources']);aliases=plan.get('source_aliases',[])
    for name,digest in hashes.items():pin(g,name,digest,aliases)
    g.check(hashes.get(VIEW)==VIEW_SHA,'Original saved-view helper pinned');v=load(VIEW,VIEW_SHA,'d045_saved_views')
    declared=[(plan['market_protocol']['path'],plan['market_protocol']['sha256']),PRIOR_COMPARISON,PRIOR_ROOT]+[(r['path'],r['sha256']) for r in plan['roles'].values()]
    for name,digest in declared:g.check(name not in hashes or hashes[name]==digest,'No conflicting declared source hash');hashes[name]=digest
    a.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=sha(__file__),plan_sha256=ph,source_hashes=dict(hashes),command=[sys.executable,*sys.argv],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip());rbs,_=g.write(a.run_dir/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D045-303-SAVED-COMPARISON-V1',event_id=binding['task_id']+':START',event_type='SAVED_SUMMARY_COMPARISON_START',git_commit=binding['git_commit'],protocol_hash=ph,data_manifest_hash=plan['roles']['MARKET']['sha256'],feature_set='FIVE_FIXED303_SELECTORS_AND_THREE_SEPARATE_ACCEPTED_WINDOWS',labels='NONE',model_family='NONE',hyperparameters={'saved_postprocessing_not_new_market_trial':True},thresholds=BUDGET,success_failure='START_BEFORE_SAVED_COMPARISON_SELECTION',source_hashes=dict(hashes),exact_command=shlex.join([sys.executable,*sys.argv]),result_influenced_later_choice=False)
    start_event=append_event(ROOT/'reports/experiment_registry.jsonl',event);error=None
    result=dict(status='FAIL_D045_303D_SAVED_SUMMARY_COMPARISON',binding=binding,run_dir=str(a.run_dir),run_binding_sha256=rbs,registration_start=start_event,candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',market_or_Parquet_IO=False,old_accounts_replayed=False,saved_postprocessing_not_new_market_trial=True)
    try:
        g.check(set(plan['roles'])=={'MARKET','FINANCE'},'Two new completed scientific roles');records={};tasks={}
        for key,r in plan['roles'].items():records[key],h,t=role(g,r);tasks[key]=t;hashes[r['path']]=h
        g.check(tasks['FINANCE']['task']['started_at']>=tasks['MARKET']['task']['ended_at'] and tasks['FINANCE']['task']['id']!=tasks['MARKET']['task']['id'],'Finance follows actual market0')
        actual,audit=records['MARKET'],records['FINANCE'];spec,sph=g.small(g.project(plan['market_protocol']['path']),plan['market_protocol']['sha256'])
        g.check(actual['status']==MARKET_STATUS and audit['status']==AUDIT_STATUS and spec['contract_id']==MARKET_CONTRACT and spec['period_ids']==['303D'] and spec['rules']['initial_capital_USDT']==10000,'Fixed seen303 full capital')
        g.check(actual['binding']['protocol_sha256']==sph and actual['binding']['source_hashes']==spec['frozen_sources'] and audit['actual_report_sha256']==plan['roles']['MARKET']['sha256'] and g.canonical_reports(audit['binding']['actual_reports'])=={str((ROOT/plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Exact new finance/market/spec identity')
        g.check(actual['required_cases']==actual['completed_cases']==audit['completed_cases_verified']==len(actual['cases'])==len(audit['cases'])==20 and {c['id'] for c in actual['cases']}=={c['id'] for c in audit['cases']},'Twenty whole selector records')
        for r in (actual,audit):g.check(r['funding_rate_unit']=='UNCONFIRMED' and not r['unit_certified'] and not r['native_market_certified'] and r['candidate']=='NO_QUALIFIED_CANDIDATE' and r['long_term_APR']=='NOT_EVALUABLE','Conditional math, no native/unit/APR gate')
        proofs={c['id']:c for c in audit['cases']}
        for c in actual['cases']:
            s=c['summary'];q=proofs[c['id']]
            g.check(s['cost_scenario']==next(x for x in spec['cost_scenarios'] if x['id']==c['cost_id']) and s['unit_scenario']==next(x for x in spec['unit_scenarios'] if x['id']==c['unit_id']),'Same declared cost/unit')
            for k in v.MONEY[:3]+('execution_cost_USDT','funding_USDT'):g.near(s[k],q['summary'][k],1e-7)
            g.near(s['all_observation_max_drawdown'],q['all_observation_max_drawdown'],1e-10)
        groups=comparisons(actual['cases'],proofs,v,g)
        old,oh=g.small(g.project(PRIOR_COMPARISON[0]),PRIOR_COMPARISON[1]);prior,rh=g.small(g.project(PRIOR_ROOT[0]),PRIOR_ROOT[1])
        g.check(old['status']=='COMPLETE_D044_ALWAYS_LONG_SAVED_SUMMARY_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR' and prior['status']=='PASS_ROOT_D044_TWELVE_CONSTANT_LONG_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR' and prior['comparison_sha256']==oh,'Exact three accepted independent old windows')
        old_tasks={k:g.closed(r['binding']['task_id']) for k,r in [('COMPARISON',old),('ROOT',prior)]};old_groups=[]
        map_old={'LONG_ONLY':'SMA_LO','SHORT_ONLY':'SMA_SO','LONG_SHORT':'SMA_LS','CASH':'CASH','HOLD_LONG_ONLY':'HOLD'}
        g.check(len(old['groups'])==12 and {(x['period'],x['cost_id'],x['unit_id']) for x in old['groups']}=={(p,c,u) for p in ('213D','122D','90D') for c in COSTS for u in UNITS},'All old windows/cost/unit groups')
        for x in old['groups']:
            selected={name:x['selectors'][prior_name] for name,prior_name in map_old.items()};g.check(all(r['common_initial_capital_USDT']==10000 for r in selected.values()),'Separate same10k references, no NAV stitch')
            old_groups.append(dict(period=x['period'],cost_id=x['cost_id'],unit_id=x['unit_id'],selectors=selected,evidence=dict(path=PRIOR_COMPARISON[0],sha256=oh,accepted_root_path=PRIOR_ROOT[0],accepted_root_sha256=rh),scope='SAVED_WHOLE_WINDOW_REFERENCE_ONLY_NOT_SAME_DATE_CAUSAL_DELTA'))
        hashes.update({plan['market_protocol']['path']:sph,PRIOR_COMPARISON[0]:oh,PRIOR_ROOT[0]:rh});g.check(binding['source_hashes']==hashes,'Actual references match immutable START binding')
        result=dict(status=STATUS,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=rbs,closed_prerequisite_tasks=tasks,prior_closed_tasks=old_tasks,groups=groups,prior_window_groups=old_groups,compared_selectors=20,cost_unit_groups=4,paired_comparisons=20,saved_reference_rows=60,summary_rows=80,market_or_Parquet_IO=False,old_accounts_replayed=False,financial_metrics_recalculated=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',funding_unit_certified=False,native_market_certified=False,seen_screening=True,common_caps_do_not_equalize_realized_risk=True,risk_rescaled_after_results=False,pooling_or_selected_months_or_joined_NAV=False,economic_action='ACCEPT_SAVED_COMPARISON_CAPABILITY_NO_INVESTMENT_ADOPTION',resources_before=before,resources_after=resources.status(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,created_utc=datetime.now(UTC).isoformat())
        result.update(registration_start=start_event,saved_postprocessing_not_new_market_trial=True)
    except Exception as e:error=e;result['failure']=dict(type=type(e).__name__,reason=str(e));result['status']='FAIL_D045_303D_SAVED_SUMMARY_COMPARISON'
    finally:
        result.update(resources_before=before,resources_after=resources.status(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        try:
            g.bounded(result['resources_after']);g.check(result['elapsed_seconds']<=120 and result['peak_RSS_bytes']<=1_000_000_000 and len(json.dumps(result,ensure_ascii=False,allow_nan=False).encode())+(a.run_dir/'RUN_BINDING.json').stat().st_size<=5_000_000,'Saved comparison resource/output bound')
        except Exception as e:error=error or e;result['budget_error']=str(e);result['status']='FAIL_D045_303D_SAVED_SUMMARY_COMPARISON'
        h,_=g.write(a.output,result);append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=binding['task_id']+':RESULT',event_type='SAVED_SUMMARY_COMPARISON_RESULT',success_failure=result['status'],artifact_path=a.output.relative_to(ROOT).as_posix(),artifact_sha256=h));print(h)
    if error:raise error
if __name__=='__main__':main()
