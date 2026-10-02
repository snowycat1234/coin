"""UNRUN D036 small-metadata close; no Parquet/price/old financial execution.
--binding: helper_sha256, protocol{path,sha256}, roles DIAGNOSTIC/INDEPENDENT
{report,report_sha256,required_status,expected_task_id,run_binding,
run_binding_sha256,source{path,sha256}}, exact two owned_STATE_directories,
project_files[{path,sha256}], preserved_failures STARTUP_V1 small proof/task only (no failed RUN_BINDING/STATE). Freeze only after both true completed0.
"""
import argparse,hashlib,importlib.util,json,math,os,sys
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
REUSE='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
REUSE_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
ARCHIVE='docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_ROOT_CLOSE_SOURCE_20261003_V1.py'
META='docs/archive/PUBLIC_PAIR_COMPLEMENTARITY_USED_ACTUAL_METADATA_20261003_V1'
OUT='reports/fast_research/PUBLIC_PAIR_COMPLEMENTARITY_ROOT_ACCEPTANCE_20261003_V1.json'
GIT='reports/GITHUB_PUBLIC_PAIR_COMPLEMENTARITY_SOURCE_BINDING_20261003_V1.json'
STATUS=dict(DIAGNOSTIC='COMPLETE_D036_SAVED_PUBLIC_PAIR_COMPLEMENTARITY_DIAGNOSTIC_NOT_ENSEMBLE_OR_LONG_TERM_APR',INDEPENDENT='PASS_D036_SAVED_PUBLIC_PAIR_STATISTICS_AND_SOURCE_BINDINGS_NOT_ENSEMBLE_OR_APR')
PERIODS=(('CONT547',547,787680),('CONT122',122,175680),('CONT90',90,129600))
PRIOR_STATUS={
 'PUBLIC_LONG_547D_ACTUAL_20261003_V1.json':'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING',
 'BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json':'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING',
 'BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json':'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING',
 'PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_ACTUAL_20261002_V1.json':'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING',
 'PUBLIC_DONCHIAN_HYBRID_BYBIT_90D_ACTUAL_20261002_V1.json':'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING',
 'PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json':'PASS_D033_THREE_NATIVE_SPOT_LEDGER_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR',
 'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json':'PASS_COMPOSITE_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_NOT_SINGLE_FRESH_SIX_SUITE',
 'PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json':'PASS_HYBRID_NATIVE_RECEIVED_ASSET_FEE_PROXY_LEDGER_ACCOUNTING_AND_CAUSAL_SCOPE',
 'PUBLIC_LONG_547D_ROOT_ACCEPTANCE_20261003_V1.json':'PASS_ROOT_D033_547D_THREE_ACCOUNT_SAVED_SUMMARY_METADATA_NOT_NATIVE_OR_LONG_TERM_APR',
 'BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json':'ACCEPT_BYBIT_SPOT_FEE_ACCOUNTING_ONLY_NO_PROFITABLE_CANDIDATE',
 'PUBLIC_DONCHIAN_HYBRID_NATIVE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json':'SCREENING_MIXED_EXIT_MECHANISM_NO_WINNER'}

def helpers():
    p=ROOT/REUSE;data=p.read_bytes()
    if p.is_symlink() or len(data)>2_000_000 or hashlib.sha256(data).hexdigest()!=REUSE_SHA:raise ValueError('Exact accepted metadata guards')
    spec=importlib.util.spec_from_file_location('d036_small_metadata_guards',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def owned(paths,expected,r):
    r.check(len(paths)==len(set(paths))==2 and {Path(p) for p in paths}==expected,'Exact two new D036 task directories only')
    rows=[]
    for name in paths:
        p=Path(name);r.check(p.parent==STATE and p.is_dir() and not p.is_symlink() and p.name.startswith('d036-public-pair-'),'Dedicated D036 only, never old inputs/all STATE')
        total=count=0
        for current,dirs,files in os.walk(p,followlinks=False):
            r.check(not any((Path(current)/n).is_symlink() for n in dirs+files),'No ownership symlink')
            for n in files:total+=(Path(current)/n).stat().st_size;count+=1
        rows.append(dict(path=str(p),bytes=total,files=count))
    total=sum(x['bytes'] for x in rows);r.check(total<=5_000_000,'D036 combined new STATE5MB')
    return dict(directories=rows,total_owned_bytes=total,maximum_owned_bytes=5_000_000,scope='EXACT_TWO_NEW_D036_FILE_STAT_ONLY')

def same(left,right,tolerance,r):
    if left is None or right is None:r.check(left is right,'Undefined statistic remains explicitly undefined');return
    r.check(type(left) in (int,float) and type(right) in (int,float),'Finite numeric statistical receipt only');r.near(left,right,tolerance)

def points(case,eligibility=None):
    overlap=case['actual_marked_exposure_overlap'];tails=case['worst_10_percent_days']
    ratios=dict(pearson=case['daily_PnL_correlation']['pearson'],spearman=case['daily_PnL_correlation']['spearman'],tail_overlap=case['worst_tail_intersection_fraction'],exposure_overlap=overlap['matched_asset_weight_overlap'])
    cash={s:tails[s]['other_signed_PnL_USDT'] for s in ('P','H')}
    exact=dict(period=case['period'],days=case['days'],minutes=case['minutes'],all_negative={s:(tails[s]['all_k_negative'] if eligibility is None else eligibility[s]) for s in ('P','H')})
    return ratios,cash,exact

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binding',type=Path,required=True);a=parser.parse_args();r=helpers();check,small=r.check,r.small
    check(a.binding.parent==ROOT/'protocols' and os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2','Bounded/progress clean metadata task only')
    plan,plan_sha=small(a.binding);check(plan['ready_to_execute'] is True and set(plan['roles'])==set(STATUS),'Exactly two actual ready roles')
    _,own_sha=small(__file__,plan['helper_sha256'],False);small(ROOT/ARCHIVE,own_sha,False);check(not any((ROOT/p).exists() for p in (OUT,GIT,META)),'Exclusive new output/archive')
    proto=plan['protocol'];check(proto['path'].startswith('protocols/PUBLIC_PAIR_COMPLEMENTARITY_') and proto['path'].endswith('.json'),'Exact D036 protocol namespace');spec,proto_sha=small(r.project(proto['path']),proto['sha256'])
    check(spec['classification']=='SCREENING_SAVED_LEDGER_COMPLEMENTARITY_NOT_ENSEMBLE' and spec['budgets']['module_combined_STATE_bytes']==spec['budgets']['new_owned_bytes']==5_000_000 and spec['budgets']['peak_RSS_bytes']==1_000_000_000 and spec['budgets']['wall_seconds']==300,'Frozen D036 scope/budget')
    check(spec['calculation_rules']['cash_tolerance']==1e-7 and spec['calculation_rules']['ratio_tolerance']==1e-12 and spec['calculation_rules']['no_ensemble_NAV'] is True,'Fixed arithmetic tolerances, no new return/account')
    hashes={str(a.binding.relative_to(ROOT)):plan_sha,ARCHIVE:own_sha,REUSE:REUSE_SHA,proto['path']:proto_sha};private={};reports={};tasks={};copies=[];dirs=set()
    for name,digest in spec['frozen_sources'].items():
        check(name!='reports/experiment_registry.jsonl','Mutable append-only registry cannot be a frozen file');small(r.project(name),digest,False)
        if name==r.LOCK:check(digest==r.LOCK_SHA,'Strong original local lock');private[name]=digest
        else:hashes[name]=digest
    for name,status in PRIOR_STATUS.items():
        p='reports/fast_research/'+name;check(p in spec['frozen_sources'],'All eleven original proof identities frozen');old,_=small(r.project(p),spec['frozen_sources'][p]);check(old['status']==status,'Exact original accepted scope, no startswith PASS/task retrofit')
    before=r.resources.status();r.bounded(before)
    for role,status in STATUS.items():
        item=plan['roles'][role];value,digest=small(r.project(item['report']),item['report_sha256']);check(value['status']==item['required_status']==status and value['binding']['task_id']==item['expected_task_id'],'Exact actual report/status/task');tasks[role]=r.closed(item['expected_task_id']);reports[role]=value;hashes[item['report']]=digest
        b,bsha=small(item['run_binding'],item['run_binding_sha256']);check(b==value['binding'] and b['task_id']==item['expected_task_id'] and value['run_binding_sha256']==bsha and b['protocol_sha256']==proto_sha,'Actual RUN_BINDING and selected protocol');dirs.add(Path(item['run_binding']).parent)
        code=item['source'];small(r.project(code['path']),code['sha256'],False);hashes[code['path']]=code['sha256'];check((b['source_hashes'][code['path']] if role=='DIAGNOSTIC' else b['checker_sha256'])==code['sha256'],'Actually used entry source byte SHA')
        copies.extend(((tasks[role]['path'],role+'_TASK_ACTUAL.json',tasks[role]['sha256']),(item['run_binding'],role+'_RUN_BINDING.json',bsha)))
        check(value['candidate_status']=='NO_QUALIFIED_CANDIDATE' and value['long_term_APR']=='NOT_EVALUABLE' and value['native_account_certified'] is False and value['ensemble_NAV_generated'] is False,'No investment/native/ensemble/APR qualification')
        check(value['peak_RSS_bytes']<=1_000_000_000 and value['elapsed_seconds']<=300,'Recorded oneGB/300s resource limits')
    d,i=reports['DIAGNOSTIC'],reports['INDEPENDENT'];check(tasks['DIAGNOSTIC']['task']['id']!=tasks['INDEPENDENT']['task']['id'] and tasks['INDEPENDENT']['task']['started_at']>=tasks['DIAGNOSTIC']['task']['ended_at'],'Independent starts after actual diagnostic closed0')
    check(d['completed_periods']==i['completed_periods_verified']==3 and d['completed_files']==i['completed_files_verified']==12 and len(d['cases'])==len(i['cases'])==3,'Three whole windows and twelve accepted files')
    check(d['binding']['source_hashes']==spec['frozen_sources']==i['verified_source_hashes'] and i['binding']['actual_report_sha256']==plan['roles']['DIAGNOSTIC']['report_sha256'],'Exact accepted scientific input/code binding; no new sourceQA')
    check(d['calculation_rules']==spec['calculation_rules'] and d['decision_rule']==spec['decision_rule'] and type(i['budget_screen_pass']) is bool and isinstance(i['decision_details'],dict),'Predeclared decision metadata; statisticsPASS and budgetchoice distinct')
    check(d['source_bytes_unchanged'] and d['saved_ledger_arrays_read'] and not d['market_arrays_read'] and not d['original_source_QA_repeated'] and not d['old_accounts_replayed'] and len(d['input_bindings'])==12,'Only projected accepted ledgers, no old accounts/market/QA')
    check(d['models_fit']==d['orders_sent']==d['GPU']==0 and d['locked_consumed'] is False and i['old_account_finance_or_source_QA_replayed'] is False,'No models/real orders/locked or old finance/source QA')
    check(r.canonical_reports(i['binding']['actual_reports'])==r.canonical_reports({plan['roles']['DIAGNOSTIC']['report']:plan['roles']['DIAGNOSTIC']['report_sha256']}),'Unique actual diagnostic report canonical provenance')
    check(i['statistic_tolerances']==dict(cash_USDT=1e-7,ratio=1e-12) and i['maximum_independent_RSS_bytes']==1_000_000_000 and i['maximum_wall_seconds']==300,'Exact independent declared statistical/resource bounds')
    for name,limit in (('cash_USDT',1e-7),('ratio',1e-12)):check(type(i['maximum_statistic_errors'][name]) in (int,float) and math.isfinite(i['maximum_statistic_errors'][name]) and 0<=i['maximum_statistic_errors'][name]<=limit,'Independent full-case errors within fixed tolerances')
    details=i['decision_details'];later={'CONT122','CONT90'};all_periods={x[0] for x in PERIODS}
    for name,keys in (('later_daily_PnL_Pearson',later),('later_worst10pct_overlap',later),('tail_other_signed_net_PnL_nonnegative',all_periods),('every_period_weighted_min_max_exposure_overlap',all_periods)):
        check(set(details[name])==keys and all(type(v) is bool for v in details[name].values()),'Whole fixed-period Boolean decision metadata')
    check(type(details['two_periods_including_a_later_offset']) is bool and details['numeric_band_did_not_change_signed_predicate'] is True and details['scope']=='BUDGET_SCREEN_ONLY_FIXED50_50_NEW_SHARED_ACCOUNT_NOT_QUALIFICATION','Point predicate not altered by numeric tolerance')
    check(i['budget_screen_pass']==(all(details['later_daily_PnL_Pearson'].values()) and all(details['later_worst10pct_overlap'].values()) and details['two_periods_including_a_later_offset'] and all(details['every_period_weighted_min_max_exposure_overlap'].values())),'Independent four-condition AND budgetscreen, not an investment PASS')
    expected=[]
    for p,(name,days,minutes) in zip(spec['periods'],PERIODS,strict=True):
        check((p['id'],p['days'],p['minutes'])==(name,days,minutes),'Exact separate whole period')
        for side in ('P','H'):
            for filename,artifact in p['legs'][side]['artifacts'].items():expected.append(dict(period=name,side=side,filename=filename,**artifact))
    check(sorted(d['input_bindings'],key=lambda x:(x['period'],x['side'],x['filename']))==sorted(expected,key=lambda x:(x['period'],x['side'],x['filename'])),'All twelve paths/SHA/rows metadata match frozen input universe, no payload reread')
    for actual,audit,(name,days,minutes) in zip(d['cases'],i['cases'],PERIODS,strict=True):
        ratios,cash,exact=points(actual);ar,ac,ae=points(audit,i['case_verification'][name]['tail_eligible']);check(exact==ae and (exact['period'],exact['days'],exact['minutes'])==(name,days,minutes),'Independent same selected complete window')
        for key,value in ratios.items():same(value,ar[key],1e-12,r)
        for key,value in cash.items():same(value,ac[key],1e-7,r)
        check(actual['no_ensemble_NAV_or_return_generated'] is True,'Descriptive case only, no synthetic common portfolio')
    for value in (d,i):r.bounded(value['resources_before']);r.bounded(value['resources_after'])
    ownership_before=owned(plan['owned_STATE_directories'],dirs,r)
    for item in plan.get('project_files',[]):
        check(item['path'] not in (r.LOCK,'reports/experiment_registry.jsonl'),'Local lock/mutable registry not portable');small(r.project(item['path']),item['sha256'],False);check(item['path'] not in hashes or hashes[item['path']]==item['sha256'],'Consistent public proof union');hashes[item['path']]=item['sha256']
    failed=plan['preserved_failures']['STARTUP_V1'];failure,failure_sha=small(r.project(failed['report']),failed['report_sha256']);check(failed['report']=='docs/archive/PUBLIC_PAIR_DIAGNOSTICS_ACTUAL_STARTUP_FAILURE_20261003_V1.json' and failure_sha=='38fe40c06b096c6df44d578b3c35ddba4ebfb202fc714c093b217994610ff1ee' and failure['status']==failed['required_status']=='ACTUAL_PROGRESS_STARTUP_FAILURE_BEFORE_SCIENCE_OR_STATE_CREATION','Preserved actual first scientific startup failure')
    failed_task=r.closed(failed['expected_task_id'],1);check(failed['required_exit_code']==failure['exit_code']==1 and failure['task_id']==failed['expected_task_id']=='18ecbb86586546348663cf660ab43e3e' and failed_task['task']['ended_at']<=tasks['DIAGNOSTIC']['task']['started_at'],'Actual failed task separately closed1 before restored diagnostic')
    check(failure['registry_started'] is False and failure['STATE_created'] is False and failure['saved_ledger_arrays_read'] is False and failure['raw_market_arrays_read'] is False and failure['completed_scientific_windows']==0,'Startup failed before RUN_BINDING/STATE/registry/arrays; no fake third directory')
    check('run_binding' not in failed and 'run_binding_sha256' not in failed,'Failed startup has no manufactured RUN_BINDING');hashes[failed['report']]=failure_sha;copies.append((failed_task['path'],'STARTUP_V1_FAILED_TASK_ACTUAL.json',failed_task['sha256']))
    for path_key,sha_key in (('source_path','source_sha256'),('protocol_path','protocol_sha256')):small(r.project(failure[path_key]),failure[sha_key],False);hashes[failure[path_key]]=failure[sha_key]
    freezer='docs/archive/PUBLIC_PAIR_DIAGNOSTICS_FREEZER_FAILURE_20261003_V1.json';f,fsha=small(r.project(freezer),'4c4924cbd71f35a4ee97c02564d4f4e0e22d858d03b4d254a6970ca029cce423');check(f['classification']=='ACTUAL_NATIVE_METADATA_FREEZER_FAILURE_BEFORE_PROTOCOL_OR_ARRAY_IO' and f['protocol_written'] is False and f['Python_executed'] is False and f['arrays_read'] is False,'Prior actual native alias failure preserves host proof, no fake task')
    small(r.project(f['failed_factory_path']),f['failed_factory_sha256'],False);hashes[freezer]=fsha;hashes[f['failed_factory_path']]=f['failed_factory_sha256']
    failures=dict(STARTUP_V1=dict(report=failed['report'],report_sha256=failure_sha,task=failed_task,exit_code=1,STATE_created=False,RUN_BINDING_created=False,arrays_read=False),FREEZER_V1=dict(report=freezer,report_sha256=fsha,host_result=f['host_result'],task_id='UNKNOWN_NOT_RETROFITTED',protocol_written=False,arrays_read=False))
    check(sum(r.ordinary(origin).stat().st_size for origin,_,_ in copies)<=r.LIMIT,'Small exact two-success-task plus failed-task metadata archive');(ROOT/META).mkdir()
    for origin,name,digest in copies:
        data=r.ordinary(origin).read_bytes();check(hashlib.sha256(data).hexdigest()==digest,'Closed metadata unchanged');target=ROOT/META/name
        with target.open('xb') as stream:stream.write(data)
        hashes[str(target.relative_to(ROOT))]=digest
    ownership_after=owned(plan['owned_STATE_directories'],dirs,r);after=r.resources.status();r.bounded(after)
    for name,digest in hashes.items():small(r.project(name),digest,False)
    common=dict(created_utc=datetime.now(UTC).isoformat(),binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=own_sha,closure_binding_sha256=plan_sha,root_own_completion='NOT_YET_CERTIFIED_LIVE_CALLER'),source_hashes=hashes,local_non_git_source_hashes=private,actual_task_bindings=tasks,preserved_failures=failures,ownership_before=ownership_before,ownership_after=ownership_after,resources_before=before,resources_after=after,root_RUN_BINDING_created=False,metadata_only=True,ledger_or_market_arrays_read=False,old_QA_or_account_or_green_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,candidate_status='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',native_account_certified=False,ensemble_NAV_generated=False)
    root=dict(common,status='PASS_ROOT_D036_SAVED_PUBLIC_PAIR_METADATA_AND_INDEPENDENT_STATISTICS_NOT_ENSEMBLE_OR_APR',completed_periods=3,completed_files=12,statistical_tolerances=dict(cash_USDT=1e-7,ratio=1e-12),budget_screen_pass=i['budget_screen_pass'],decision_details=i['decision_details'],independent_maximum_statistic_errors=i['maximum_statistic_errors'],decision_rule=spec['decision_rule'],cases=d['cases'])
    root_sha,root_bytes=r.write(ROOT/OUT,root);portable=dict(common,status='PASS_CLOSED_D036_PUBLIC_PAIR_PORTABLE_SOURCE_BINDING_SCREENING_NOT_ENSEMBLE_OR_APR',source_hashes={**hashes,OUT:root_sha},root_report_sha256=root_sha,private_lock_body_archived=False,exclusions_from_portable_source_hashes=list(private),own_root_task_completed0_must_be_verified_by_later_push_helper=True)
    git_sha,git_bytes=r.write(ROOT/GIT,portable);check(root_bytes+git_bytes+sum(r.ordinary(origin).stat().st_size for origin,_,_ in copies)<=r.LIMIT,'Combined small archive/report2MB')
    print(json.dumps(dict(root_report=OUT,root_sha256=root_sha,portable_report=GIT,portable_sha256=git_sha,closed_scientific_roles=2,root_caller_still_live=True)))
if __name__=='__main__':main()
