"""UNRUN D046 saved-summary comparison + ROOT metadata acceptance, no arrays.
CLI --binding ready ROOT plan. Keys: ready_to_execute/helper_sha256/frozen_sources,
market_protocol{path,sha256}/roles MARKET,FINANCE,SMOKE{path,sha256,required_status,
task_id}/budgets/run_dir/output_path/portable_path. New finance4; old16 saved views.
Own caller remains LIVE_CALLER; USED must subsequently seal its real completed0.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,resource,shlex,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
from types import SimpleNamespace
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state');LOCK='state/dataset_lock.json'
LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
CMP='scripts/investment/compare_perpetual_303_results.py';CMP_SHA='cdb85b8b385282f9f98a6861836401bd8d3c2adbde1a6200bd3d589c67a25bc5'
VIEW='scripts/investment/compare_perpetual_213_results.py';VIEW_SHA='c7af4ac72b0332e27b41312f58362e255cacd94614de3173a64725e67b361792'
STATUS='PASS_ROOT_D046_FOUR_CORRECTNESS_CONTROLS_AND_TWENTY_SAVED_SELECTORS_NOT_NATIVE_OR_LONG_TERM_APR'
FAIL='FAIL_ROOT_D046_SAVED_CORRECTNESS_CONTROL_COMPARISON'
CONTRACT='D046_FIXED303D_CORRECTNESS_CONTROL_SAVED_COMPARISON_ROOT_BINDING_V1'
MARKET_CONTRACT='D046_FIXED303D_LONG_SHORT_PRODUCT_LEGAL_RISK_REDUCTION_V1'
MARKET_STATUS='COMPLETE_D046_FOUR_FIXED303D_LONG_SHORT_RISK_REDUCTION_CONTROLS_NOT_NATIVE_OR_LONG_TERM_APR'
FINANCE_STATUS='PASS_D046_FOUR_FIXED303D_LONG_SHORT_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
SMOKE_STATUS='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'
BUDGET=dict(new_owned_bytes=5_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)
PRIOR={
 'ACTUAL':('reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json','de350689cdfa86a40ee1d083795578d215c657e627d6d18b2885b2e59c1dfca3'),
 'COMPARISON':('reports/fast_research/PERPETUAL_303_ECONOMIC_COMPARISON_20261003_V1.json','77b1872abcc1b049ca5e04c85db2ce186830cbf81f96d56d5708642d382e097f'),
 'ROOT':('reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json','841a525d41162bbcbaedb14b0be0c3696bcf3356cfdb76542a864662797c4f58'),
 'PORTABLE':('reports/GITHUB_PERPETUAL_303_RESEARCH_SOURCE_BINDING_20261003_V1.json','e353a69e1c93fa68633f78cdc0c8408b2ffcb327225f2652c1b6652dac919753')}
def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def load(name,digest,label):
    path=ROOT/name
    if path.is_symlink() or sha(path)!=digest:raise ValueError('Exact saved metadata code '+name)
    spec=importlib.util.spec_from_file_location(label,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binding',type=Path,required=True);a=parser.parse_args();a.binding=a.binding.absolute()
    cmp=load(CMP,CMP_SHA,'d046_saved_pair_math');g=cmp.guard();v=load(VIEW,VIEW_SHA,'d046_saved_views');plan,ph=g.small(a.binding);own=sha(__file__);task=os.getenv('COIN_TASK_ID')
    g.check(task and a.binding.parent==ROOT/'protocols' and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and plan['ready_to_execute'] is True and plan['helper_sha256']==own and plan['contract_id']==CONTRACT and plan['budgets']==BUDGET,'Ready bounded metadata binding')
    run=Path(plan['run_dir']);out=ROOT/plan['output_path'];portable=ROOT/plan['portable_path'];g.check(run.parent==STATE and run.name.startswith('d046-') and not run.exists() and out.parent==ROOT/'reports/fast_research' and portable.parent==ROOT/'reports' and not out.exists() and not portable.exists(),'Exclusive new metadata results')
    hashes=dict(plan['frozen_sources']);g.check(hashes.get(CMP)==CMP_SHA and hashes.get(VIEW)==VIEW_SHA and hashes.get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own,'Direct saved-view/pair/self pins')
    for name,digest in hashes.items():g.check(not name.startswith('docs/') or name.startswith('docs/archive/'),'No mutable ordinary docs scientific pins');cmp.pin(g,name,digest)
    g.check(sha(ROOT/LOCK)==LOCK_SHA,'Private lock streamed only');local={LOCK:LOCK_SHA}
    declared=[(a.binding.relative_to(ROOT).as_posix(),ph),(plan['market_protocol']['path'],plan['market_protocol']['sha256']),*PRIOR.values(),*((r['path'],r['sha256']) for r in plan['roles'].values())]
    for name,digest in declared:g.check(name not in hashes or hashes[name]==digest,'Exact compact proof pointer');hashes[name]=digest
    run.mkdir();started=time.monotonic();before=resources.status();g.bounded(before)
    rb=dict(task_id=task,helper_sha256=own,binding_path=str(a.binding),binding_sha256=ph,source_hashes=dict(hashes),command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip());rbs,_=g.write(run/'RUN_BINDING.json',rb)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D046-FOUR-CORRECTNESS-CONTROLS-ROOT-V1',event_id=task+':START',event_type='SAVED_CORRECTNESS_COMPARISON_ACCEPTANCE_START',git_commit=rb['git_commit'],protocol_hash=ph,data_manifest_hash=plan['roles']['MARKET']['sha256'],feature_set='4_NEW_LS_AND_16_ACCEPTED_SAVED_NON_LS',labels='NONE',model_family='NONE',seed=None,thresholds=BUDGET,source_hashes=dict(hashes),exact_command=rb['command'],success_failure='START_BEFORE_SAVED_SUMMARY_ACCEPTANCE');start_event=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    result=dict(status=FAIL,binding=rb,run_dir=str(run),run_binding_sha256=rbs,registration_start=start_event,root_own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED',candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',local_non_git_hash_guard=local);error=None
    try:
        g.check(set(plan['roles'])=={'MARKET','FINANCE','SMOKE'},'Only three new actual prerequisites');records={};tasks={}
        for label,ref in plan['roles'].items():records[label],_,tasks[label]=cmp.role(g,ref)
        actual,audit,smoke=records['MARKET'],records['FINANCE'],records['SMOKE'];g.check(len({x['task']['id'] for x in tasks.values()})==3 and tasks['MARKET']['task']['started_at']>=tasks['SMOKE']['task']['ended_at'] and tasks['FINANCE']['task']['started_at']>=tasks['MARKET']['task']['ended_at'],'New smoke then market then finance realclosed0')
        g.check(actual['status']==MARKET_STATUS and audit['status']==FINANCE_STATUS and smoke['status']==SMOKE_STATUS and smoke['test_exit_code']==0 and smoke['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0) and smoke['source_bytes_unchanged'] is True,'One new case and exact four-case financial contract')
        g.small(Path(smoke['run_dir'])/'junit.xml',smoke['junit_sha256'],False)
        spec,sph=g.small(g.project(plan['market_protocol']['path']),plan['market_protocol']['sha256']);g.check(spec['contract_id']==MARKET_CONTRACT and spec['period_ids']==['303D'] and spec['rules']['initial_capital_USDT']==10000 and spec['rules']['strategy_design']==[dict(strategy_id=cmp.SMA,mode='LONG_SHORT')],'Four fixed303 long-short samecapital')
        g.check(spec['required_smoke_receipt']=={k:plan['roles']['SMOKE'][k] for k in ('path','sha256','required_status')} and actual['binding']['protocol_sha256']==sph and actual['binding']['source_hashes']==spec['frozen_sources'] and audit['protocol_sha256']==sph and audit['actual_report_sha256']==plan['roles']['MARKET']['sha256'] and g.canonical_reports(audit['binding']['actual_reports'])=={str((ROOT/plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Same actual payload independently audited')
        saved,prior_tasks={},{}
        for label,(path,digest) in PRIOR.items():saved[label],_=g.small(g.project(path),digest)
        old,oldcmp,oldroot,oldportable=[saved[k] for k in ('ACTUAL','COMPARISON','ROOT','PORTABLE')]
        g.check(old['status']==cmp.MARKET_STATUS and oldcmp['status']==cmp.STATUS and oldroot['status']=='PASS_ROOT_D045_TWENTY_FIXED303D_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR' and oldroot['comparison_sha256']==PRIOR['COMPARISON'][1] and oldroot['portable_binding_sha256']==PRIOR['PORTABLE'][1] and oldportable['root_task_id']==oldroot['binding']['task_id'],'Exact accepted original capabilities, not inherited huge pin maps')
        for label in ('ACTUAL','COMPARISON','ROOT'):prior_tasks[label]=g.closed(saved[label]['binding']['task_id'])
        oldproto=Path(old['binding']['protocol_path']);g.check(oldproto.parent==ROOT/'protocols','Original protocol identity');oldspec,_=g.small(oldproto,old['binding']['protocol_sha256'])
        changing={'strategy_design','planned_selectors','planned_trading_account_simulations','planned_constant_cash_baselines','classification'}
        g.check(all(spec['rules'].get(k)==value for k,value in oldspec['rules'].items() if k not in changing) and spec['rules']['planned_selectors']==spec['rules']['planned_trading_account_simulations']==4 and spec['rules']['planned_constant_cash_baselines']==0 and spec['cost_scenarios']==oldspec['cost_scenarios'] and spec['unit_scenarios']==oldspec['unit_scenarios'] and spec['input_manifest']==oldspec['input_manifest'],'Unchanged complete source/cost/unit/risk; only legal reduction policy and newsubset')
        g.check(actual['required_cases']==actual['completed_cases']==audit['required_cases']==audit['completed_cases_verified']==audit['financial_case_calls']==len(actual['cases'])==len(audit['cases'])==4 and audit['shared_CASH_artifact_equivalences_verified']==0 and audit['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10),'Four real new financial calls exact tolerances')
        g.near(audit['maximum_errors']['cash'],0,1e-7);g.near(audit['maximum_errors']['ratio'],0,1e-10)
        for report in (actual,audit):g.check(report['funding_rate_unit']=='UNCONFIRMED' and report['unit_certified'] is False and report['native_market_certified'] is False and report['candidate']=='NO_QUALIFIED_CANDIDATE' and report['long_term_APR']=='NOT_EVALUABLE','No unit/native/investment/APR promotion')
        oldrows={(x['cost_id'],x['unit_id'],s):row for x in oldcmp['groups'] for s,row in x['selectors'].items()};g.check(len(oldrows)==20 and oldroot['completed_full_calendar_cases']==16 and oldroot['incomplete_or_halted_cases']==4,'Preserve original16full/4prefix scope')
        proofs={c['id']:c for c in audit['cases']};rows=dict(oldrows);cases=[];pairproofs={};preserved=[]
        for c in old['cases']:
            k=c['cost_id'],c['unit_id'],c['selector_mode'];row=oldrows[k];g.check(all(c['summary'].get(name)==value for name,value in row['summary'].items()),'Old saved summary exactly accepted, no financial replay')
            if c['selector_mode']=='LONG_SHORT':preserved.append(dict(case=c,saved_view=row,role='IMMUTABLE_ORIGINAL_LS_HALTED_PREFIX_NOT_FULL303_RESULT'));continue
            g.check(row['complete_calendar'] is True,'Only accepted16 complete non-LS controls');cases.append(c);pairproofs[c['id']]=dict(complete_calendar_verified=True,scope='COMPLETENESS_FROM_ACCEPTED_SAVED_VIEW_NOT_NEW_FINANCIAL_AUDIT')
        expected={(cost,unit,'LONG_SHORT') for cost in cmp.COSTS for unit in cmp.UNITS};g.check({(c['cost_id'],c['unit_id'],c['selector_mode']) for c in actual['cases']}==expected and len(proofs)==4,'All four fixed cost/unit LS scenarios')
        for c in actual['cases']:
            p=proofs[c['id']];s=c['summary'];g.check(c['period']=='303D' and c['mode']==c['selector_mode']=='LONG_SHORT' and c['strategy_id']==s['strategy_id']==cmp.SMA and s['required_minutes']==436320 and s['cost_scenario']==next(x for x in spec['cost_scenarios'] if x['id']==c['cost_id']) and s['unit_scenario']==next(x for x in spec['unit_scenarios'] if x['id']==c['unit_id']),'Same fixed303 LS/cost/unit design')
            for key in v.MONEY[:3]+('execution_cost_USDT','funding_USDT'):g.near(s[key],p['summary'][key],1e-7)
            g.near(s['all_observation_max_drawdown'],p['all_observation_max_drawdown'],1e-10);g.check({k:item['sha256'] for k,item in c['artifacts'].items()}==p['ledger_artifact_hashes'],'Exact independently verified new artifact hashes, no payload read')
            if p['complete_calendar_verified']:g.check(s['completed_minutes']==436320 and s['daily_metrics']['days']==303 and [m['month'] for m in s['months']]==cmp.MONTHS,'True complete303 only')
            rows[c['cost_id'],c['unit_id'],'LONG_SHORT']=v.view(c,p);cases.append(c);pairproofs[c['id']]=p
        # Original pair arithmetic is reused; old16 views are returned verbatim.
        reader=SimpleNamespace(MONEY=v.MONEY,view=lambda c,p:rows[c['cost_id'],c['unit_id'],c['selector_mode']]);groups=cmp.comparisons(cases,pairproofs,reader,g)
        full=sum(bool(p['complete_calendar_verified']) for p in proofs.values());g.check(full==audit['completed_full_calendar_cases_verified'] and 4-full==audit['incomplete_or_halted_cases_verified'],'Actual complete/prefix counts, no promotion')
        preserved_metadata={label:g.closed(identity,1) for label,identity in plan.get('preserved_metadata_failures',{}).items()}
        g.check(actual['peak_RSS_bytes']<=spec['budgets']['peak_RSS_bytes'] and actual['elapsed_seconds']<=spec['budgets']['wall_seconds'] and actual['owned_bytes']<=spec['budgets']['new_owned_bytes'],'Actual four-account resources inside prebound budget')
        result.update(status=STATUS,groups=groups,preserved_original_four_LS_prefixes=preserved,preserved_metadata_failures=preserved_metadata,new_LS_source=plan['roles']['MARKET'],original_sixteen_non_LS_source=dict(path=PRIOR['ACTUAL'][0],sha256=PRIOR['ACTUAL'][1]),closed_prerequisite_tasks=tasks,prior_closed_tasks=prior_tasks,completed_selector_references=20,new_financial_case_calls=4,old_financial_case_calls=0,new_complete_calendar_cases=full,new_prefix_cases=4-full,complete_selector_references=16+full,cost_unit_groups=4,paired_comparisons=20,reference_scope='16_ORIGINAL_COMPLETE_PLUS_4_NEW_SEPARATE_ACCOUNTS_NOT_SINGLE_FRESH20_RUN',financial_tolerances=audit['tolerances'],financial_maximum_errors=audit['maximum_errors'],funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,market_or_Parquet_IO=False,old_accounts_or_QA_replayed=False,financial_metrics_recalculated=False,seen_screening=True,risk_equalized=False,pure_short_causal_effect_identified=False,NAV_or_months_stitched=False,economic_action='ACCEPT_CORRECTNESS_CONTROL_AND_SAVED_COMPARISON_CAPABILITY_NO_INVESTMENT_ADOPTION',portable_binding_path=portable.relative_to(ROOT).as_posix(),source_hashes=dict(hashes))
    except Exception as caught:error=caught;result['failure']=dict(type=type(caught).__name__,reason=str(caught));result['status']=FAIL
    finally:
        result.update(resources_before=before,resources_after=resources.status(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,created_utc=datetime.now(UTC).isoformat())
        try:g.bounded(result['resources_after']);g.check(result['elapsed_seconds']<=120 and result['peak_RSS_bytes']<=1_000_000_000 and len(json.dumps(result,allow_nan=False).encode())*2+(run/'RUN_BINDING.json').stat().st_size<=5_000_000,'Small compare+close bound')
        except Exception as caught:error=error or caught;result['budget_error']=str(caught);result['status']=FAIL
        h,_=g.write(out,result);append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='SAVED_CORRECTNESS_COMPARISON_ACCEPTANCE_RESULT',success_failure=result['status'],artifact_path=out.relative_to(ROOT).as_posix(),artifact_sha256=h))
    if error:raise error
    github={name:digest for name,digest in hashes.items() if name!=LOCK};github[out.relative_to(ROOT).as_posix()]=h
    portable_result=dict(status='D046_SAVED_CORRECTNESS_CONTROL_COMPARISON_BOUND_NOT_INVESTMENT',source_hashes=github,verified_prior_files={path:digest for path,digest in PRIOR.values()},prior_portables=[dict(path=PRIOR['PORTABLE'][0],sha256=PRIOR['PORTABLE'][1],capability_referenced_without_recursive_hash_map=True)],root_task_id=task,root_own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED',local_non_git_hash_guard=local,result_path=out.relative_to(ROOT).as_posix(),result_sha256=h,market_payloads_exported=False,candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
    gh,_=g.write(portable,portable_result);print(json.dumps(dict(status=result['status'],result_sha256=h,portable_sha256=gh,task_id=task)))
if __name__=='__main__':main()
