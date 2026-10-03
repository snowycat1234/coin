"""UNRUN D045 seven-role metadata closure, no price/ledger/QA payload IO.
--binding plan: ready_to_execute/helper_sha256/source_hashes/budgets/run_dir,
market_protocol{path,sha256}; roles SOURCE/QA/ROOT/SMOKE/MARKET/FINANCE/COMPARISON
{path,sha256,required_status,task_id}; source_aliases optional explicit pins.
Prior failure metadata stays failed; no completed financial output is presumed.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,resource,shlex,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
COMPARE='scripts/investment/compare_perpetual_303_results.py'
OUT='reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json'
PORTABLE='reports/GITHUB_PERPETUAL_303_RESEARCH_SOURCE_BINDING_20261003_V1.json'
CONTRACT='D045_FIXED_303D_RESEARCH_METADATA_CLOSE_V1'
STATUS='PASS_ROOT_D045_TWENTY_FIXED303D_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
BUDGET=dict(new_owned_bytes=5_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)
PRIOR_PORTABLES={
 'reports/GITHUB_PERPETUAL_HOLD_SOURCE_BINDING_20261003_V2.json':'b39a24c9fdf25fd86b49e68c51dc1cbc88d3fc75806920693e35606f22d0fae7',
 'reports/GITHUB_PERPETUAL_HOLD_USED_RECEIPTS_BINDING_20261003_V1.json':'f70b00400bc6b92137bfcc870af0483f72b4624b6a77e22e0f703a76e11bb99a'}
EXPECTED_STATUS={
 'SOURCE':'PASS_D045_94_HISTORY_FORMAT_54_REUSED_40_NEW_PENDING_INDEPENDENT_QA',
 'QA':'PASS_D045_94_SOURCE_COVERAGE_70_FIRST_QA_24_ACCEPTED_REUSE_NOT_UNIT_OR_ECONOMICS',
 'ROOT':'PASS_ROOT_D045_COMPLETE_303_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS',
 'MARKET':'COMPLETE_D045_FIXED303D_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR',
 'FINANCE':'PASS_D045_TWENTY_FIXED303D_SMA_HOLD_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR',
 'COMPARISON':'COMPLETE_D045_303D_SAVED_SUMMARY_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'}
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binding',type=Path,required=True);a=p.parse_args()
    # One new comparison module supplies only the already accepted small guards.
    raw=json.loads(a.binding.read_bytes());digest=raw['source_hashes'][COMPARE]
    if (ROOT/COMPARE).is_symlink() or sha(ROOT/COMPARE)!=digest:raise ValueError('Exact new saved-summary adapter')
    loader=importlib.util.spec_from_file_location('d045_close_metadata',ROOT/COMPARE);c=importlib.util.module_from_spec(loader);loader.loader.exec_module(c);g=c.guard()
    plan,ph=g.small(a.binding);run=Path(plan['run_dir']);task=os.getenv('COIN_TASK_ID');own=Path(__file__).absolute().relative_to(ROOT).as_posix()
    g.check(a.binding.parent==ROOT/'protocols' and plan['ready_to_execute'] is True and plan['contract_id']==CONTRACT and plan['helper_sha256']==sha(__file__) and plan['source_hashes'].get(own)==sha(__file__) and plan['budgets']==BUDGET,'Exact frozen ready closure')
    g.check(task and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2' and run.parent==STATE and run.name.startswith('d045-') and not run.exists() and not (ROOT/OUT).exists() and not (ROOT/PORTABLE).exists(),'Fresh bounded root receipt/STATE')
    before=resources.status();g.bounded(before);started=time.monotonic();run.mkdir();error=None
    rb=dict(task_id=task,source_sha256=sha(__file__),source_hashes=plan['source_hashes'],binding_path=str(a.binding),binding_sha256=ph,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),exact_command=shlex.join([sys.executable,*sys.argv]));rh,_=g.write(run/'RUN_BINDING.json',rb)
    report=dict(status='FAIL_ROOT_D045_303_RESEARCH',binding=rb,run_dir=str(run),run_binding_sha256=rh,candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,local_non_git_hash_guard={'state/dataset_lock.json':'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'},market_arrays_read=False,old_accounts_or_QA_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources_before=before,root_own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D045-303-RESEARCH-ROOT-V1',event_id=task+':START',event_type='RESEARCH_ACCEPTANCE_START',git_commit=rb['git_commit'],protocol_hash=ph,data_manifest_hash=plan['roles']['MARKET']['sha256'],feature_set='FIXED303_SMA4_AND_HOLD_SAVED_COMPARISON',labels='NONE',model_family='NONE',success_failure='START_BEFORE_ROLE_METADATA',source_hashes=plan['source_hashes'],exact_command=rb['exact_command']);append_event(ROOT/'reports/experiment_registry.jsonl',event)
    try:
        g.check(set(plan['roles'])=={'SOURCE','QA','ROOT','SMOKE','MARKET','FINANCE','COMPARISON'},'Seven genuinely completed roles')
        records={};closed={};verified={};portable_sources={};aliases=plan.get('source_aliases',[]);prior_refs=[]
        for name,digest in PRIOR_PORTABLES.items():
            prior,h=g.small(g.project(name),digest);g.check(prior['root_task_id']==g.closed(prior['root_task_id'])['task']['id'],'Previously accepted portable root true0')
            verified[name]=h;prior_refs.append(dict(path=name,sha256=h,scope='EXACT_PRIOR_ACCEPTED_CAPABILITY_REFERENCE_NO_OLD_FILE_OR_DOC_REREAD'))
        for name,digest in plan['source_hashes'].items():
            resolved=c.pin(g,name,digest,aliases)
            if name!='state/dataset_lock.json':portable_sources[resolved]=digest
        for key,ref in plan['roles'].items():
            row,d,t=c.role(g,ref);g.check(key not in EXPECTED_STATUS or row['status']==EXPECTED_STATUS[key],'Exact scientific role '+key)
            records[key]=row;closed[key]=t;verified[ref['path']]=d
        g.check(len({x['task']['id'] for x in closed.values()})==7,'Seven distinct true0 tasks')
        for left,right in [('SOURCE','QA'),('QA','ROOT'),('ROOT','SMOKE'),('SMOKE','MARKET'),('MARKET','FINANCE'),('FINANCE','COMPARISON')]:g.check(closed[right]['task']['started_at']>=closed[left]['task']['ended_at'],'Actual causal prerequisite order '+left+' '+right)
        source,qa,sroot,tiny,m,f,comp=[records[k] for k in ('SOURCE','QA','ROOT','SMOKE','MARKET','FINANCE','COMPARISON')]
        g.check(source['completed_files']==source['required_files']==qa['completed_files_verified']==qa['actual_archives']==sroot['actual_archives']==94 and qa['first_independent_QA_files']==sroot['first_QA_files']==70 and qa['reused_accepted_QA_files']==sroot['reused_accepted_QA_files']==24,'Accepted94 source coverage, not repeated QA')
        g.check(qa['actual_report_sha256']==plan['roles']['SOURCE']['sha256'] and source['reused_completed_files']==54 and source['new_completed_files']==40,'Actual54 existing/40 new, QA70/24 identities')
        g.check(sroot['source_only'] is True and source['funding_unit_certified'] is qa['funding_unit_certified'] is sroot['funding_unit_certified'] is False,'Format-only qualification remains conditional')
        spec,sph=g.small(g.project(plan['market_protocol']['path']),plan['market_protocol']['sha256']);verified[plan['market_protocol']['path']]=sph
        g.check(spec['contract_id']==c.MARKET_CONTRACT and spec['period_ids']==['303D'] and spec['rules']['initial_capital_USDT']==10000 and spec['rules']['planned_selectors']==20,'One complete303 same10k fixed recipe')
        source_ref=spec['trade_source_acceptance'];g.check(source_ref['path']==plan['roles']['ROOT']['path'] and source_ref['sha256']==plan['roles']['ROOT']['sha256'],'Producer uses this accepted source root')
        ir=spec['input_manifest'];g.check(ir['path']==sroot['input_binding_path'] and ir['sha256']==sroot['input_binding_sha256'],'Exact accepted94 input binding')
        manifest,_=g.small(g.project(ir['path']),ir['sha256']);verified[ir['path']]=ir['sha256']
        g.check(len(manifest['source_files'])==94 and len(manifest['windows'])==1 and manifest['windows'][0]['id']=='303D' and manifest['windows'][0]['days']==303 and manifest['windows'][0]['minutes_per_symbol']==436320,'Unbroken window calendar from accepted source metadata')
        smoke_ref=spec['required_smoke_receipt'];g.check(smoke_ref['path']==plan['roles']['SMOKE']['path'] and smoke_ref['sha256']==plan['roles']['SMOKE']['sha256'],'Exact new route case acceptance')
        g.check(tiny['test_exit_code']==0 and tiny['source_bytes_unchanged'] is True and tiny['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0),'Exactly one new true integration case')
        g.check(m['binding']['protocol_sha256']==sph and m['binding']['source_hashes']==spec['frozen_sources'] and f['actual_report_sha256']==plan['roles']['MARKET']['sha256'] and g.canonical_reports(f['binding']['actual_reports'])=={str((ROOT/plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Immutable new financial/market binding')
        expected={f'303D_{mode}_{cost}_{unit}' for mode in c.SELECTORS for cost in c.COSTS for unit in c.UNITS}
        g.check(m['required_cases']==m['completed_cases']==f['completed_cases_verified']==len(m['cases'])==len(f['cases'])==20 and {q['id'] for q in m['cases']}=={q['id'] for q in f['cases']}==expected,'All20 predeclared selectors, no winner filtering')
        g.check(m['planned_trading_account_simulations']==m['completed_trading_account_simulations']==16 and m['planned_constant_cash_baselines']==m['completed_constant_cash_baselines']==1 and f['financial_case_calls']==17 and f['shared_CASH_artifact_equivalences_verified']==3,'16 traded accounts and one CASH proof; three metadata aliases, not20 finance replays')
        g.check(m['completed_full_calendar_cases']==f['completed_full_calendar_cases_verified'] and m['incomplete_or_halted_cases']==f['incomplete_or_halted_cases_verified'] and m['completed_full_calendar_cases']+m['incomplete_or_halted_cases']==20,'Full/prefix counts remain honest')
        g.check(f['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10) and f['maximum_errors']['cash']<=1e-7 and f['maximum_errors']['ratio']<=1e-10,'Original accepted independent tolerances, not loosened')
        for r in (m,f):g.check(r['funding_rate_unit']=='UNCONFIRMED' and not r['unit_certified'] and not r['native_market_certified'] and r['candidate']=='NO_QUALIFIED_CANDIDATE' and r['long_term_APR']=='NOT_EVALUABLE','No unit/native/APR qualification')
        for name,digest in spec['frozen_sources'].items():g.check(plan['source_hashes'].get(name)==digest,'All frozen market code refs included');c.pin(g,name,digest,aliases)
        g.check(comp['compared_selectors']==20 and comp['cost_unit_groups']==len(comp['groups'])==4 and comp['paired_comparisons']==20 and comp['saved_reference_rows']==60 and comp['summary_rows']==80 and len(comp['prior_window_groups'])==12,'Four new groups plus three separate saved windows')
        g.check(comp['closed_prerequisite_tasks']['MARKET']==closed['MARKET'] and comp['closed_prerequisite_tasks']['FINANCE']==closed['FINANCE'] and comp['market_or_Parquet_IO'] is comp['old_accounts_replayed'] is comp['pooling_or_selected_months_or_joined_NAV'] is False,'No hidden replay/stitching')
        g.check({(x['period'],x['cost_id'],x['unit_id']) for x in comp['groups']}=={('303D',cost,unit) for cost in c.COSTS for unit in c.UNITS},'All costs/units preserved')
        proof={x['id']:x for x in f['cases']}
        for group in comp['groups']:
            for selector,row in group['selectors'].items():
                actual=next(x for x in m['cases'] if x['id']==row['id']);q=proof[row['id']]
                g.check(selector==actual['selector_mode'] and row['complete_calendar']==q['complete_calendar_verified'],'Saved selector/completion unchanged')
                for key in ('net_PnL','gross_PnL_same_quantities','fees_USDT','funding_USDT'):g.near(row['summary'][key],actual['summary'][key],1e-7)
                g.check(row['saved_months']==actual['summary']['months'],'Whole saved monthly table, no recomputation')
        g.check(m['peak_RSS_bytes']<=spec['budgets']['peak_RSS_bytes'] and m['elapsed_seconds']<=spec['budgets']['wall_seconds'] and m['owned_bytes']<=spec['budgets']['new_owned_bytes'],'Actual producer resources')
        report['preserved_failed_tasks']={str(k):g.closed(t,1) for k,t in plan.get('preserved_failed_tasks',{}).items()}
        after=resources.status();g.bounded(after);report.update(resources_after=after)
        g.check(time.monotonic()-started<=120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1_000_000_000,'Bounded small root metadata')
        portable=dict(status='ROOT_D045_FIXED303_SAVED_RESEARCH_BOUND_NOT_INVESTMENT',source_hashes=portable_sources,verified_actual_reports=verified,prior_portables=prior_refs,historical_source_aliases=aliases,root_task_id=task,private_scientific_lock_access='HASH_ONLY_NOT_EXPORTED',root_own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        h,_=g.write(ROOT/PORTABLE,portable)
        report.update(status=STATUS,roles=closed,source_hashes=portable_sources,scientific_source_hashes=plan['source_hashes'],verified_actual_reports=verified,comparison_sha256=plan['roles']['COMPARISON']['sha256'],portable_binding_sha256=h,prior_portables=prior_refs,comparisons=comp['groups'],prior_window_groups=comp['prior_window_groups'],completed_cases=20,financial_case_calls=17,cash_aliases_verified=3,completed_full_calendar_cases=m['completed_full_calendar_cases'],incomplete_or_halted_cases=m['incomplete_or_halted_cases'],physical_trading_accounts=16,constant_cash_baselines=1,required_days_by_independent_window={'303D':303},funding_unit_conditions_not_selected=True,seen_development_screening=True,realized_risk_equalized=False,adoption='RESEARCH_COMPARISON_CAPABILITY_ONLY; INVESTMENT_NONE_CASH')
    except Exception as e:error=e;report['failure']=dict(type=type(e).__name__,reason=str(e))
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024);h,size=g.write(ROOT/OUT,report)
        g.check(size+(run/'RUN_BINDING.json').stat().st_size+((ROOT/PORTABLE).stat().st_size if (ROOT/PORTABLE).exists() else 0)<=5_000_000,'Metadata total output5MB')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='RESEARCH_ACCEPTANCE_RESULT',success_failure=report['status'],artifact_path=OUT,artifact_sha256=h))
    if error:raise error
    print(json.dumps(dict(status=report['status'],sha256=h)))
if __name__=='__main__':main()
