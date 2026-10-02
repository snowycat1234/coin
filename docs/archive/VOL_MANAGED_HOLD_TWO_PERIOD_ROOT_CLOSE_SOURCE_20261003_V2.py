"""UNRUN D035 close: only saved small proofs/code and six dedicated STATE file stats including one failed audit.
--binding: helper_sha256, ready_to_execute, protocols CONT122/CONT90 {path,sha256},
roles TINY/RESEARCH122/RESEARCH90/INDEPENDENT/COMPARISON each report/report_sha256,
required_status/expected_task_id/run_binding/run_binding_sha256; last two also source
{path,sha256}; failed_roles INDEPENDENT_V1 kept separately (exit1), project_files and exact six owned_STATE_directories. No arrays/replay.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys
from copy import deepcopy
from datetime import UTC,datetime
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state');VM='VOL_MANAGED_BUY_AND_HOLD'
REUSE='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
REUSE_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
ARCHIVE='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_ROOT_CLOSE_SOURCE_20261003_V2.py'
META='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_USED_ACTUAL_METADATA_20261003_V1'
OUT='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_ROOT_ACCEPTANCE_20261003_V1.json'
GIT='reports/GITHUB_VOL_MANAGED_HOLD_TWO_PERIOD_SOURCE_BINDING_20261003_V1.json'
ROLES=('TINY','RESEARCH122','RESEARCH90','INDEPENDENT','COMPARISON')
STATUSES=('PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING','PASS_D035_TWO_VM_NATIVE_SPOT_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_LONG_TERM_APR','COMPLETE_D035_TWO_PERIOD_SAVED_SUMMARY_RISK_COST_COMPARISON_NOT_LONG_TERM_APR')
FIXED={
 'CONT122':dict(role='RESEARCH122',days=122,minutes=175680,budget=75000000,source_days=153,rows=440640,months=['2025-08','2025-09','2025-10','2025-11'],source_status='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_153D_CALENDAR',parent='protocols/BYBIT_SPOT_2H_122D_V2.json',parent_sha='11a667b18ec6c3f779214c28fc0bcfe805319ee8b89e62097f6ee3aa52659192',native='reports/fast_research/BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json',native_sha='53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3',hybrid='reports/fast_research/PUBLIC_DONCHIAN_HYBRID_BYBIT_122D_ACTUAL_20261002_V1.json',hybrid_sha='9e7727b41b994db2ab1d3496094e22ef12de98ab841d050cd1c9c7fd31310313',cash='reports/fast_research/SIMPLE_STRATEGY_CONTINUOUS_122D_ACTUAL_20261002_V1.json',cash_sha='62cb5604580e3af8de3bcf7d1db5f76343581ef44f656ba89f927ba4bdb24e94'),
 'CONT90':dict(role='RESEARCH90',days=90,minutes=129600,budget=60000000,source_days=151,rows=348480,months=['2025-12','2026-01','2026-02'],source_status='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_151D_CALENDAR',parent='protocols/BYBIT_SPOT_2H_90D_V2.json',parent_sha='8505eec0f6406d7725962856455e3dfdbefda6139503f5e2d7856443383ca457',native='reports/fast_research/BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json',native_sha='329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a',hybrid='reports/fast_research/PUBLIC_DONCHIAN_HYBRID_BYBIT_90D_ACTUAL_20261002_V1.json',hybrid_sha='3b6e1f58c9f76411a5d8bcddde29fdfc3c7bdb955a9f04013269599199c3bfb6',cash='reports/fast_research/PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json',cash_sha='7e47d20fb71a8c6f87cc5b1adc26a2e031bb9bdbd8cf1a64d61ab6b4ac25642c')}

def load_helpers():
    path=ROOT/REUSE;data=path.read_bytes()
    if path.is_symlink() or len(data)>2_000_000 or hashlib.sha256(data).hexdigest()!=REUSE_SHA:raise ValueError('Exact accepted metadata helpers')
    spec=importlib.util.spec_from_file_location('d035_accepted_metadata_guards',path);r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r);return r

def owned(paths,expected,r):
    r.check(len(paths)==len(set(paths))==6 and {Path(p) for p in paths}==expected,'Exactly five success-task directories plus preserved failed audit, no old inputs/allSTATE')
    rows=[]
    for name in paths:
        p=Path(name);r.check(p.parent==STATE and p.is_dir() and not p.is_symlink() and p.name.startswith(('vol-managed-hold-122d-','vol-managed-hold-90d-','test-vol-managed-hold-two-period-','d035-')),'Dedicated D035 directory only')
        count=total=0
        for current,dirs,files in os.walk(p,followlinks=False):
            r.check(not any((Path(current)/n).is_symlink() for n in dirs+files),'No ownership symlinks')
            for n in files:total+=(Path(current)/n).stat().st_size;count+=1
        rows.append(dict(path=str(p),bytes=total,files=count))
    total=sum(x['bytes'] for x in rows);r.check(total<=150_000_000,'Combined D035150MB limit')
    return dict(directories=rows,total_owned_bytes=total,maximum_owned_bytes=150_000_000,scope='EXACT_SIX_NEW_D035_FILE_STAT_ONLY_INCLUDING_FAILED_AUDIT')

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--binding',type=Path,required=True);a=parser.parse_args();r=load_helpers();check,small=r.check,r.small
    check(a.binding.parent==ROOT/'protocols' and os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2','Root-frozen metadata binding and bounded/progress clean environment')
    plan,plan_sha=small(a.binding);check(plan['ready_to_execute'] is True and set(plan['roles'])==set(ROLES) and set(plan['protocols'])==set(FIXED) and set(plan['failed_roles'])=={'INDEPENDENT_V1'},'All five real completed0 roles, one preserved failed audit and two separate protocols')
    _,own_sha=small(__file__,plan['helper_sha256'],False);small(ROOT/ARCHIVE,own_sha,False);check(not any((ROOT/p).exists() for p in (OUT,GIT,META)),'Exclusive new report/archive')
    hashes={str(a.binding.relative_to(ROOT)):plan_sha,ARCHIVE:own_sha,REUSE:REUSE_SHA};copies=[];reports={};tasks={};bindings={};dirs=set()
    for role,status in zip(ROLES,STATUSES):
        item=plan['roles'][role];report,digest=small(r.project(item['report']),item['report_sha256']);check(report['status']==item['required_status']==status and report['binding']['task_id']==item['expected_task_id'],'Exact actual role/report/status')
        tasks[role]=r.closed(item['expected_task_id']);reports[role]=report;hashes[item['report']]=digest;copies.append((tasks[role]['path'],role+'_TASK_ACTUAL.json',tasks[role]['sha256']))
        b,bsha=small(item['run_binding'],item['run_binding_sha256']);check(b['task_id']==item['expected_task_id'],'Real task RUN_BINDING');bindings[role]=b;dirs.add(Path(item['run_binding']).parent);copies.append((item['run_binding'],role+'_RUN_BINDING.json',bsha))
        if 'run_binding_sha256' in report:check(report['run_binding_sha256']==bsha,'Actual binding receipt SHA')
    failed=plan['failed_roles']['INDEPENDENT_V1'];failed_report,failed_sha=small(r.project(failed['report']),failed['report_sha256']);failed_task=r.closed(failed['expected_task_id'],1)
    check(failed['report']=='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V1.json' and failed_sha=='fdc4cb0683cc224943ca4ec7bbe018f452f21bb77221c230cf86f38f359a1bcc' and failed['required_status']==failed_report['status']=='FAIL_D035_TWO_VM_INDEPENDENT_AUDIT' and failed['required_exit_code']==1 and failed_report['binding']['task_id']==failed['expected_task_id']=='9d00f027d29047afb026b2790e65151a','Preserve exact actual V1 audit failure, never relabel passed')
    failed_rb,failed_rb_sha=small(failed['run_binding'],failed['run_binding_sha256']);check(failed_rb==failed_report['binding'] and failed_rb_sha==failed_report['run_binding_sha256']=='c5fa56e4610229183cb20c8d27e826a24db9184528a751fa118465105c374327' and Path(failed['run_binding']).parent==STATE/'d035-independent-20261003-v1','Preserved failed actual RUN_BINDING')
    failed_code=failed['source'];small(r.project(failed_code['path']),failed_code['sha256'],False);check(failed_code==dict(path='docs/archive/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_SOURCE_20261003_V2.py',sha256='752c1015144bff614147ec445a4fcf62ff64f4d89b7a7074e93718c5ab9447d4') and failed_report['binding']['checker_sha256']==failed_code['sha256'] and Path(failed_report['independent_source'])==ROOT/failed_code['path'],'Failed checker exact used-source bytes retained')
    failed_manifest=failed_report['binding']['actual_manifest_path'];failed_manifest_sha=failed_report['binding']['actual_manifest_sha256'];small(failed_manifest,failed_manifest_sha);check(failed_manifest_sha=='af1150c97eab05bb2bb744a3ac6b791a6aa0a52ace3678df647363e862798c55' and Path(failed_manifest)==Path(failed['run_binding']).parent/'ACTUAL_BINDING.json','Actual failed invocation manifest preserved')
    check(failed_report['completed_ledgers_verified']==failed_report['completed_ledgers_before_failure']==0 and failed_report['ledgers']==failed_report['cases']==failed_report['runtime_inputs']==[] and failed_report['error_type']=='KeyError' and failed_report['error']=="'source_scope'",'Metadata/source-scope compatibility failure before account arrays, no financial PASS claimed')
    hashes[failed['report']]=failed_sha;hashes[failed_code['path']]=failed_code['sha256'];dirs.add(Path(failed['run_binding']).parent);copies.extend(((failed_task['path'],'INDEPENDENT_V1_FAILED_TASK_ACTUAL.json',failed_task['sha256']),(failed['run_binding'],'INDEPENDENT_V1_FAILED_RUN_BINDING.json',failed_rb_sha),(failed_manifest,'INDEPENDENT_V1_FAILED_ACTUAL_BINDING.json',failed_manifest_sha)))
    failures=dict(INDEPENDENT_V1=dict(report=failed['report'],report_sha256=failed_sha,required_exit_code=1,task=failed_task,run_binding_sha256=failed_rb_sha,source=failed_code,actual_manifest_sha256=failed_manifest_sha,completed_ledgers_verified=0,classification='METADATA_SCOPE_COMPATIBILITY_FAILURE_NOT_FINANCIAL_FAILURE_OR_PASS'))
    check(len({x['task']['id'] for x in tasks.values()})==5 and failed_task['task']['id'] not in {x['task']['id'] for x in tasks.values()},'Five distinct real completed0 tasks; failed audit separate');tiny,audit,comparison=reports['TINY'],reports['INDEPENDENT'],reports['COMPARISON']
    check(Path(plan['roles']['INDEPENDENT']['run_binding']).parent==STATE/'d035-independent-20261003-v2' and plan['roles']['INDEPENDENT']['report']=='reports/fast_research/VOL_MANAGED_HOLD_TWO_PERIOD_INDEPENDENT_AUDIT_20261003_V2.json','Only successful V2 audit fills success role')
    check(tasks['INDEPENDENT']['task']['started_at']>=failed_task['task']['ended_at'] and all(failed_task['task']['started_at']>=tasks[k]['task']['ended_at'] for k in ('RESEARCH122','RESEARCH90')),'Failed V1 and restored V2 exact causal order')
    for left,right in (('TINY','RESEARCH122'),('TINY','RESEARCH90'),('RESEARCH122','INDEPENDENT'),('RESEARCH90','INDEPENDENT'),('INDEPENDENT','COMPARISON')):check(tasks[right]['task']['started_at']>=tasks[left]['task']['ended_at'],'Causal completion order')
    before=r.resources.status();r.bounded(before);ownership_before=owned(plan['owned_STATE_directories'],dirs,r)
    check(tiny['junit_counts']==dict(tests=1,failures=0,errors=0,skipped=0) and tiny['test_exit_code']==0 and not tiny['market_inputs_read'],'One fresh joint metadata/integration case, not repeated greens')
    junit=Path(tiny['run_dir'])/'junit.xml';small(junit,tiny['junit_sha256'],False);tree=ET.parse(junit).getroot();check({k:sum(int(s.get(k,0)) for s in tree.iter('testsuite')) for k in ('tests','failures','errors','skipped')}==tiny['junit_counts'],'Real onecase JUnit');copies.append((str(junit),'TINY_JUNIT_ACTUAL.xml',tiny['junit_sha256']))
    check(audit['completed_ledgers_verified']==2 and len(audit['ledgers'])==2 and audit['completed_days_verified']==212 and audit['completed_minutes_verified']==305280 and audit['completed_months_verified']==7 and audit['peak_RSS_bytes']<=3_500_000_000,'Independent two whole accounts, seven months, bounded resource scope')
    r.bounded(tiny['resources']);check(tiny['market_models_fit']==tiny['orders_sent']==0 and not tiny['locked_consumed'],'No models/orders/locked in joint synthetic receipt')
    scientific={};specs={};sources={};summaries={};all_reports={};references={};private={r.LOCK:r.LOCK_SHA}
    for fold,config in FIXED.items():
        proto=plan['protocols'][fold];expected_prefix=f'protocols/VOL_MANAGED_HOLD_{config["days"]}D_BYBIT_20261003_V';check(proto['path'].startswith(expected_prefix) and proto['path'].endswith('.json'),'Exact child period protocol namespace')
        spec,psha=small(r.project(proto['path']),proto['sha256']);specs[fold]=spec;parent,_=small(r.project(config['parent']),config['parent_sha']);actual=reports[config['role']];item=plan['roles'][config['role']]
        check(item['report']==spec['research_output_path'] and actual['binding']['protocol_sha256']==psha and spec['namespace_parent_protocol']==dict(path=config['parent'],sha256=config['parent_sha']),'Selected exact protocol and historical parent')
        for key in ('folds','warmup_days','common_config','environment','fee_settlement','fee_profile_path','fee_profile_sha256','market_type','source_receipt','source_receipt_sha256'):check(spec[key]==parent[key],'Unchanged original period/capital/risk/fee/source/environment: '+key)
        costs=deepcopy(parent['costs']);costs.update(spread_bps=[8],nominal_roundtrip_bps=[36]);check(spec['costs']==costs and spec['strategy_ids']==[VM] and spec['planned_ledgers']==1 and spec['maximum_new_owned_bytes']==config['budget'] and spec['maximum_wall_seconds']==900 and spec['module_combined_STATE_budget_bytes']==150_000_000,'Only originalVM, conservative36bp and preregistered budget')
        expected={**spec['frozen_sources'],proto['path']:psha};scientific[fold]=expected;check(expected[r.LOCK]==r.LOCK_SHA and actual['binding']['source_hashes']==expected==audit['verified_source_hashes'][fold]==comparison['source_hashes_by_period'][fold],'Exact selected source bindings, never conflated across dates')
        for name,digest in expected.items():small(r.project(name),digest,False);check(name not in hashes or hashes[name]==digest,'Consistent portable union');hashes.update({name:digest} if name!=r.LOCK else {})
        source,ssha=small(r.project(spec['source_receipt']),spec['source_receipt_sha256']);check(source['status']==config['source_status'] and source['days_per_symbol']==config['source_days'] and source['source_files']==10,'Old source accepted metadata, no invented source task');sources[fold]=dict(path=spec['source_receipt'],sha256=ssha,status=source['status'],legacy_task_id='UNKNOWN_NOT_RETROFITTED',source_days_per_symbol=config['source_days'],actual_derivative_rows=config['rows'])
        scope,calendar=('JUL_NOV_2025',['2025-07','2025-08','2025-09','2025-10','2025-11']) if fold=='CONT122' else ('OCT2025_FEB2026',['2025-10','2025-11','2025-12','2026-01','2026-02'])
        check(spec['source_scope']==actual['source_scope']==scope and spec['source_calendar']==actual['source_calendar']==calendar and spec['source_days_per_symbol']==actual['source_days_per_symbol']==config['source_days'] and actual['source_receipt_sha256']==ssha,'Explicit same accepted per-period source scope, source153/151 distinct from actual153/121 derivative')
        prior,_=small(r.project(config['native']),config['native_sha']);r.closed(prior['binding']['task_id']);check(spec['reused_minute_input']==dict(report_path=config['native'],report_sha256=config['native_sha'],path=prior['minute_source']['path'],sha256=prior['minute_source']['sha256']) and actual['reused_minute_input']==spec['reused_minute_input'] and actual['raw_normalized_market_files_read'] is False and actual['minute_source']['rows']==config['rows'],'Original accepted native Parquet reuse, no prices reread')
        check(actual['status']=='COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING' and actual['all_planned_ledgers_complete'] and actual['completed_ledgers']==actual['planned_ledgers']==1 and actual['accepted_smoke_sha256']==plan['roles']['TINY']['report_sha256'] and actual['source_bytes_unchanged'] and actual['market_models_fit']==actual['orders_sent']==0 and not actual['locked_consumed'] and actual['candidate_status']=='NO_QUALIFIED_CANDIDATE','Complete new account only, no qualification')
        r.bounded(actual['resources']);check(actual['orchestrator_peak_RSS_bytes']<=3_500_000_000 and actual['owned_bytes']<=config['budget'] and actual['elapsed_seconds']<=900,'Actual per-period resource bounds')
        f=actual['folds'][0];check(len(actual['folds'])==1 and f['fold']==fold and f['days']==config['days'] and f['status']=='COMPLETE_PROXY_COMPARISON' and len(f['results'])==1,'Whole independent scoring period')
        row=f['results'][0];proof=[x for x in audit['ledgers'] if x['fold']==fold];check(len(proof)==1,'Unique independently verified period');proof=proof[0];summary=row['summary']
        check(row['strategy']==proof['strategy']==VM and row['spread_bps']==proof['spread_bps']==8 and row['nominal_roundtrip_bps']==36 and summary['initial_nav']==10000 and summary['period_days']==config['days'] and [m['month'] for m in proof['months']]==config['months'],'Same complete capital/cost/month scope')
        for key,target in r.METRICS.items():r.near(summary[key],proof[target],1e-10 if key in ('turnover','max_observed_minute_MDD','max_drawdown') else 1e-7)
        r.near(proof['sparse_Decimal_settlement']['maximum_Decimal_cash_error_USDT'],0,1e-7);check(summary['trade_count']==proof['trade_count'] and {name:v['sha256'] for name,v in row['artifacts'].items()}==proof['ledger_artifact_hashes'],'Saved independently verified settlement/artifact metadata, no payload read')
        check(summary['annualized_return_is_descriptive_only'] and not summary['net_long_term_CAGR_proven'] and not summary['candidate_qualification_allowed'] and not summary['native_Bybit_market_or_filters_proven'] and not summary['real_BBO'] and summary['fee_settlement_version']=='BYBIT_SPOT_RECEIVED_ASSET_V1','No futureAPR/native/BBO qualification')
        check(bindings[config['role']]==actual['binding'] and Path(actual['run_dir'])==Path(plan['roles'][config['role']]['run_binding']).parent,'Actual RUN_BINDING identity/source snapshot scope')
        for name,digest in expected.items():small(Path(actual['run_dir'])/'source-snapshot'/name,digest,False)
        summaries[fold]=summary;all_reports[item['report']]=item['report_sha256'];references[fold]={}
        for name in ('native','hybrid','cash'):small(r.project(config[name]),config[name+'_sha']);hashes[config[name]]=config[name+'_sha'];references[fold][name]=dict(path=config[name],sha256=config[name+'_sha'])
    check(tiny['binding']['source_hashes']==scientific['CONT122'] and tiny['binding']['protocol_sha256']==plan['protocols']['CONT122']['sha256'],'Only122 child executes the single shared case')
    for key in ('frozen_sources','common_config','costs','strategy_rules','environment','fee_settlement','fee_profile_sha256'):check(specs['CONT122'][key]==specs['CONT90'][key],'Same shared code and economic recipe, separate inputs')
    check(specs['CONT122']['required_smoke_receipt']==specs['CONT90']['required_smoke_receipt']==plan['roles']['TINY']['report'],'Exactly one common new acceptance receipt')
    check(r.canonical_reports(audit['binding']['actual_reports'])==r.canonical_reports(all_reports)==r.canonical_reports(comparison['binding']['actual_reports'])==r.canonical_reports(failed_report['binding']['actual_reports']),'Canonical exact two actual report provenance including failed metadata attempt')
    check(set(audit['verified_source_hashes'])==set(comparison['source_hashes_by_period'])==set(FIXED) and len(comparison['cases'])==8 and len(comparison['pairs'])==4 and comparison['economic_action']=='TWO_SEEN_PERIODS_NO_INVESTMENT_ADOPTION','Two whole periods, saved8cases/4pairs, no adoption')
    strategies={VM,'CASH','COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER','COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'}
    for fold,config in FIXED.items():
        cases=[x for x in comparison['cases'] if x['fold']==fold];pairs=[x for x in comparison['pairs'] if x['fold']==fold];check(len(cases)==4 and {x['strategy'] for x in cases}==strategies and len(pairs)==2 and {x['reference_strategy'] for x in pairs}==strategies-{VM,'CASH'},'No missing/extra or selected control')
        for case in cases:
            check(case['days']==config['days'],'Same saved reference full period')
            if case['strategy']==VM:check(case['report_path']==plan['roles'][config['role']]['report'] and case['report_sha256']==plan['roles'][config['role']]['report_sha256'],'Current actual comparison binding');r.near(case['summary']['net_cash_PnL'],summaries[fold]['net_cash_PnL'],1e-7)
            else:
                ref=references[fold]['cash' if case['strategy']=='CASH' else 'native' if case['strategy']=='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER' else 'hybrid'];check(case['report_path']==ref['path'] and case['report_sha256']==ref['sha256'],'Exact accepted saved reference, no old simulation')
    for role,key in (('INDEPENDENT','checker_sha256'),('COMPARISON','source_sha256')):
        code=plan['roles'][role]['source'];small(r.project(code['path']),code['sha256'],False);check(reports[role]['binding'][key]==code['sha256'],'Actually executed checker/comparator source');hashes[code['path']]=code['sha256']
    for item in plan['project_files']:small(r.project(item['path']),item['sha256'],False);check(item['path']!=r.LOCK and (item['path'] not in hashes or hashes[item['path']]==item['sha256']),'Consistent public source union');hashes[item['path']]=item['sha256']
    for name,digest in comparison['small_report_hashes'].items():small(r.project(name),digest);check(name not in hashes or hashes[name]==digest,'Compared small proof exact');hashes[name]=digest
    check(sum(r.ordinary(origin).stat().st_size for origin,_,_ in copies)<=r.LIMIT and len({n for _,n,_ in copies})==len(copies),'Small exact metadata archive')
    (ROOT/META).mkdir()
    for origin,name,digest in copies:
        data=r.ordinary(origin).read_bytes();check(hashlib.sha256(data).hexdigest()==digest,'Closed task/code proof unchanged');p=ROOT/META/name
        with p.open('xb') as stream:stream.write(data)
        hashes[str(p.relative_to(ROOT))]=digest
    ownership_after=owned(plan['owned_STATE_directories'],dirs,r);after=r.resources.status();r.bounded(after)
    for name,digest in hashes.items():small(r.project(name),digest,False)
    common=dict(created_utc=datetime.now(UTC).isoformat(),binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=own_sha,closure_binding_sha256=plan_sha,root_own_completion='NOT_YET_CERTIFIED_LIVE_CALLER'),source_hashes=hashes,local_non_git_source_hashes=private,actual_task_bindings=tasks,preserved_failed_task_bindings=failures,failed_audit_financial_ledgers_verified=0,ownership_before=ownership_before,ownership_after=ownership_after,resources_before=before,resources_after=after,metadata_only=True,price_or_ledger_arrays_or_QA_or_old_green_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,candidate_status='NO_QUALIFIED_CANDIDATE',sustainable_net_APR='NOT_ESTABLISHED',native_account_certified=False,unseen_qualification=False)
    result=dict(common,status='PASS_ROOT_D035_TWO_VM_SAVED_SUMMARY_METADATA_NOT_NATIVE_OR_LONG_TERM_APR',scientific_source_hashes_by_period=scientific,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),completed_accounts=2,independent_period_days=[122,90],accounts_stitched=False,financial_summaries=summaries,legacy_source_acceptance=sources,saved_reference_bindings=references,comparison_report=plan['roles']['COMPARISON'],root_RUN_BINDING_created=False,private_lock_body_archived=False)
    root_sha,root_bytes=r.write(ROOT/OUT,result);portable=dict(common,status='PASS_CLOSED_VOL_MANAGED_HOLD_TWO_PERIOD_PORTABLE_SOURCE_BINDING_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR',source_hashes={**hashes,OUT:root_sha},root_report_sha256=root_sha,exclusions_from_portable_source_hashes=[r.LOCK],private_scientific_hash_guard_preserved=True,own_root_task_completed0_must_be_verified_by_later_push_helper=True)
    git_sha,git_bytes=r.write(ROOT/GIT,portable);check(root_bytes+git_bytes+sum(r.ordinary(origin).stat().st_size for origin,_,_ in copies)<=r.LIMIT,'Combined small archive/output2MB budget')
    print(json.dumps(dict(root_report=OUT,root_sha256=root_sha,portable_report=GIT,portable_sha256=git_sha,closed_prior_roles=5,root_caller_still_live=True)))
if __name__=='__main__':main()
