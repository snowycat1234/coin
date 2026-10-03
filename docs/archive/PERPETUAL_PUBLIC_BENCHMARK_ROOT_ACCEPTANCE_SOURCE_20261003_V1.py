"""D041 small-metadata closure and saved-summary comparison; no market payload IO.

Binding: ready_to_execute/helper_sha256/protocol{path,sha256}; five roles
SOURCE/SOURCE_INDEPENDENT/NEW_TESTS/MARKET/INDEPENDENT, each
{path,sha256,required_status,task_id}; prior contains the six fixed proof refs
below. Only root-frozen ready=true binding after all real tasks closed0 runs.
"""
import argparse, hashlib, importlib.util, json, os, resource, sys, time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
ARCHIVE='docs/archive/PERPETUAL_PUBLIC_BENCHMARK_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py'
OUT='reports/fast_research/PERPETUAL_PUBLIC_BENCHMARK_ROOT_ACCEPTANCE_20261003_V1.json'
GIT='reports/GITHUB_PERPETUAL_PUBLIC_BENCHMARK_SOURCE_BINDING_20261003_V1.json'
LOCK='state/dataset_lock.json'
BUDGET=dict(new_owned_bytes=5000000,peak_RSS_bytes=1000000000,wall_seconds=120)
STATUSES=dict(SOURCE='PASS_D041_OFFICIAL_PERPETUAL_2H_JULY_FORMAT_CALENDAR_PENDING_INDEPENDENT_QA',
 SOURCE_INDEPENDENT='PASS_D041_JULY_2H_RAW_NORMALIZED_CALENDAR_AND_VOLUME_ONLY',
 NEW_TESTS='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT',
 MARKET='COMPLETE_D041_CONDITIONAL_PUBLIC_DONCHIAN_PERPETUAL_BENCHMARK_NOT_NATIVE_OR_LONG_TERM_APR',
 INDEPENDENT='PASS_D041_EIGHT_PUBLIC_DONCHIAN_LONG_ONLY_PERPETUAL_ACCOUNTS_AND_2H_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR')
PRIOR={
 'old_actual':dict(path='reports/fast_research/PERPETUAL_DIRECTIONAL_ACTUAL_20261003_V1.json',sha256='c643c6ae5542dc049595a8c2e21b7281ef5ce46ac7f026a3c845126f05bfb445'),
 'old_audit':dict(path='reports/fast_research/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDIT_20261003_V1.json',sha256='876fce2558757f797e1d0f9d5b923c5858427ecfd721926afe4926355ffef53d'),
 'fixed_actual':dict(path='reports/fast_research/PERPETUAL_SETTLEMENT_REPLAY_ACTUAL_20261003_V1.json',sha256='4a9dbcef25381d4909d640ea582e69b58342f137f538dbd2840e49e0a2bf89ff'),
 'fixed_audit':dict(path='reports/fast_research/PERPETUAL_SETTLEMENT_TWO_CASE_INDEPENDENT_AUDIT_20261003_V1.json',sha256='0132514ae4cd8b9a1f65318ba4c7b06c47b1fb257fc5caa001a59f1f5445e3f1'),
 'original_root':dict(path='reports/fast_research/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_20261003_V1.json',sha256='5b6fa633f14e976e75babb1405bedb97dfb91af9ed7cc25ae0363fa62ca5e89c'),
 'old_portable':dict(path='reports/GITHUB_PERPETUAL_DIRECTIONAL_SOURCE_BINDING_20261003_V1.json',sha256='962647497be3c526b261e41c16b870a02d259875db61248b5c12d37b1d29f7cb')}
OLD_REGISTRY='b9965d36cd017e7c0df9d3550ffa1a5903e7551af2d14e209a766c3f8f9d8293'
REGISTRY_ARCHIVE='docs/archive/OPEN_SOURCE_REGISTRY_PRE_DONCHIAN_PERPETUAL_20261003_V1.md'
FIXED=['90D_SHORT_ONLY_BASE27_RAW_AS_PERCENT','90D_LONG_SHORT_BASE27_RAW_AS_PERCENT']


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--binding',type=Path,required=True);p.add_argument('--run-dir',type=Path,required=True)
    a=p.parse_args();started=time.monotonic()
    if digest(ROOT/GUARD)!=GUARD_SHA:raise ValueError('Frozen metadata guards changed')
    loader=importlib.util.spec_from_file_location('d041_metadata_guards',ROOT/GUARD);g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    g.check(os.getenv('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2','Real bounded clean CPU task')
    g.check(a.binding.parent==ROOT/'protocols' and a.run_dir.parent==STATE and not a.run_dir.exists()
        and not (ROOT/OUT).exists() and not (ROOT/GIT).exists(),'Exclusive metadata closure')
    plan,plan_sha=g.small(a.binding);g.check(plan['ready_to_execute'] is True and plan['budgets']==BUDGET
        and set(plan['roles'])==set(STATUSES) and plan['prior']==PRIOR,'Exact ready five-role closure and accepted prior pointers')
    _,own=g.small(__file__,plan['helper_sha256'],False);g.small(ROOT/ARCHIVE,own,False)
    before=g.resources.status();g.bounded(before);hashes={};local={};aliases=[];reports={};tasks={}
    def add(name,h):
        if (name,h)==('docs/OPEN_SOURCE_REGISTRY.md',OLD_REGISTRY):
            item=dict(original_path=name,original_sha256=h,archive_path=REGISTRY_ARCHIVE)
            if item not in aliases:aliases.append(item)
            name=REGISTRY_ARCHIVE
        g.small(g.ordinary(ROOT/name) if name=='docs/OPEN_SOURCE_REGISTRY.md' else g.project(name),h,False);target=local if name==LOCK else hashes
        g.check(name not in target or target[name]==h,'No conflicting current scientific identity');target[name]=h
    def read(ref):
        value,h=g.small(g.project(ref['path']),ref['sha256']);add(ref['path'],h);return value
    add(GUARD,GUARD_SHA);add(ARCHIVE,own);add(Path(__file__).relative_to(ROOT).as_posix(),own);add(a.binding.relative_to(ROOT).as_posix(),plan_sha)
    for role,status in STATUSES.items():
        ref=plan['roles'][role];r=read(ref);identity=r['binding']['task_id']
        g.check(r['status']==ref['required_status']==status and identity==ref['task_id'],'Exact executed role '+role)
        reports[role]=r;tasks[role]=g.closed(identity)
        for name,h in {**r['binding'].get('source_hashes',{}),**r.get('verified_source_hashes',{})}.items():add(name,h)
        proto=r['binding'].get('protocol_path')
        if proto:add(Path(proto).resolve().relative_to(ROOT).as_posix(),r['binding']['protocol_sha256'])
        run=r.get('run_dir',r['binding'].get('spec',{}).get('run_dir'))
        if run and r.get('run_binding_sha256'):
            rb,_=g.small(Path(run)/'RUN_BINDING.json',r['run_binding_sha256']);g.check(rb['task_id']==identity,'Real role RUN_BINDING')
    g.check(len({x['task']['id'] for x in tasks.values()})==5,'Five distinct closed0 roles')
    prior={k:read(v) for k,v in PRIOR.items()};root=prior['original_root'];root_task=g.closed(root['binding']['task_id'])
    g.check(root['status']=='PASS_ROOT_PERPETUAL_DIRECTIONAL_CONDITIONAL_METADATA_NOT_NATIVE_OR_LONG_TERM_APR'
        and root['original_full_calendar_cases']==30 and root['original_numeric_error_prefixes']==2
        and root['corrected_new_full_calendar_cases']==2 and root['full_calendar_scenario_evidence_count']==32,'Already accepted original30 plus corrected2')
    for role in ('SOURCE_ROOT','SIGNAL','ACCOUNT','CHAIN','CONTROLLER','SETTLEMENT_TEST'):
        identity=root['roles'][role]['task_id'];old_task=g.closed(identity)
        g.check(old_task['task']['ended_at']<=root_task['task']['started_at'],'Accepted six prerequisites before old root')
    for role in ('SOURCE','SOURCE_INDEPENDENT','NEW_TESTS'):
        g.check(tasks['MARKET']['task']['started_at']>=tasks[role]['task']['ended_at'],'Market after real prerequisites')
    g.check(tasks['SOURCE_INDEPENDENT']['task']['started_at']>=tasks['SOURCE']['task']['ended_at']
        and tasks['MARKET']['task']['started_at']>=root_task['task']['ended_at']
        and tasks['INDEPENDENT']['task']['started_at']>=tasks['MARKET']['task']['ended_at'],'True source and financial dependency clocks')
    source,qa,test,actual,audit=[reports[k] for k in STATUSES]
    g.check(source['actual_files']==2 and source['actual_source_rows']==744 and qa['completed_files_verified']==2
        and qa['completed_rows_verified']==744 and qa['actual_report_sha256']==plan['roles']['SOURCE']['sha256']
        and source['funding_rate_unit']==qa['funding_rate_unit']=='UNCONFIRMED'
        and not source['funding_unit_certified'] and not qa['funding_unit_certified'],'Only new source format accepted, no unit promotion')
    g.check(test['test_exit_code']==0 and test['source_bytes_unchanged'] and test['junit_counts']==dict(tests=2,errors=0,failures=0,skipped=0),'Actual two new cases only')
    junit=Path(test['run_dir'])/'junit.xml';g.small(junit,test['junit_sha256'],False)
    g.check({k:sum(int(s.get(k,0)) for s in ET.parse(junit).getroot().iter('testsuite')) for k in test['junit_counts']}==test['junit_counts'],'Saved JUnit identity')
    spec=read(plan['protocol']);proto_sha=plan['protocol']['sha256'];old_spec,_=g.small(Path(prior['old_actual']['binding']['protocol_path']),prior['old_actual']['binding']['protocol_sha256'])
    add(Path(prior['old_actual']['binding']['protocol_path']).relative_to(ROOT).as_posix(),prior['old_actual']['binding']['protocol_sha256'])
    g.check(spec['contract_id']=='D041_PUBLIC_DONCHIAN_TWO_HOUR_PERPETUAL_BENCHMARK_20261003_V1'
        and spec['period_ids']==old_spec['period_ids']==['122D','90D'] and spec['cost_scenarios']==old_spec['cost_scenarios']
        and spec['unit_scenarios']==old_spec['unit_scenarios'] and spec['input_manifest']==old_spec['input_manifest'],'Same two complete financial input windows and scenarios')
    for key,value in old_spec['rules'].items():
        if key not in ('modes','signal','sizing'):g.check(spec['rules'][key]==value,'Shared financial rule '+key)
    g.check(spec['rules']['modes']==['LONG_ONLY'] and spec['rules']['signal_interval_us']==7200000000,'Fixed original public2h long-only route')
    for key,role in [('july_signal_source_receipt','SOURCE'),('july_signal_independent_receipt','SOURCE_INDEPENDENT'),('required_new_tests','NEW_TESTS')]:
        g.check(all(spec[key][k]==plan['roles'][role][k] for k in ('path','sha256','required_status')),'Frozen prerequisite '+key)
    g.check(spec['original_root']==dict(PRIOR['original_root'],required_status=root['status']),'Exact accepted old comparison capability')
    g.check(actual['binding']['source_hashes']==spec['frozen_sources'] and actual['binding']['protocol_sha256']==proto_sha
        and audit['actual_report_sha256']==plan['roles']['MARKET']['sha256'] and g.canonical_reports(audit['binding']['actual_reports'])=={
            str(g.project(plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Exact new science and unique independently audited market')
    rb,rb_sha=g.small(Path(spec['run_dir'])/'RUN_BINDING.json',actual['run_binding_sha256']);g.check(rb==actual['binding'] and rb_sha==audit['actual_run_binding_sha256'],'Exact complete financial RUN_BINDING')
    g.check(actual['required_cases']==actual['completed_cases']==actual['completed_full_calendar_cases']==audit['required_cases']==audit['completed_cases_verified']==audit['completed_full_calendar_cases_verified']==8
        and actual['incomplete_or_halted_cases']==audit['incomplete_or_halted_cases_verified']==0,'Eight full accounts, no halt promoted')
    g.check(audit['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10) and audit['maximum_errors']['cash']<=1e-7 and audit['maximum_errors']['ratio']<=1e-10,'Saved independent numerical scope')
    for r in (actual,audit):
        g.check(r['funding_rate_unit']=='UNCONFIRMED' and not r['unit_certified'] and not r['native_market_certified']
            and r['candidate']=='NO_QUALIFIED_CANDIDATE' and r['long_term_APR']=='NOT_EVALUABLE'
            and r['models_fit']==r['orders_sent']==r['GPU']==0 and not r['locked_consumed'],'No investment/unit/native/locked promotion')
        g.bounded(r['resources_before']);g.bounded(r['resources_after'])
    for r,budget in [(source,source['binding']['spec']['budgets']),(actual,spec['budgets']),(qa,dict(wall_seconds=300,peak_RSS_bytes=512000000)),(audit,dict(wall_seconds=1200,peak_RSS_bytes=1500000000))]:
        g.check(r['elapsed_seconds']<=budget['wall_seconds'] and r['peak_RSS_bytes']<=budget['peak_RSS_bytes'],'Actual role process budget')
        if 'owned_bytes' in r:g.check(r['owned_bytes']<=budget['new_owned_bytes'],'Actual role owned budget')
    g.check([{k:x[k] for k in ('id','score_start_us','score_end_exclusive_us','original_funding_events','input_proofs')} for x in actual['input_windows']]==[
        {k:x[k] for k in ('id','score_start_us','score_end_exclusive_us','original_funding_events','input_proofs')} for x in prior['old_actual']['input_windows']],'Identical financial inputs, signal feature inputs may differ')
    old={c['id']:c for c in prior['old_actual']['cases']};old_proof={c['id']:c for c in prior['old_audit']['cases']}
    g.check(len(old)==32 and [k for k,v in old.items() if v['summary']['completion']!='COMPLETE_CONDITIONAL_ACCOUNT']==FIXED,'Original false-halt prefixes preserved')
    for c in root['original32_cases']:g.check(c['summary']==old[c['id']]['summary'],'Saved old root summary identity')
    for c,proof in zip(prior['fixed_actual']['cases'],prior['fixed_audit']['cases'],strict=True):
        g.check(c['id']==proof['id'] and c['id'] in FIXED and proof['complete_calendar_verified'],'Exactly two accepted corrected references');old[c['id']]=c;old_proof[c['id']]=proof
    g.check(len(old)==32 and all(c['summary']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' for c in old.values()),'Canonical32 uses30 plus2, not a new32 replay')
    for c in root['corrected_new_cases']:g.check(c['summary']==old[c['id']]['summary'],'Accepted corrected root summary identity')
    comparisons=[];selectors=[f'{p}_LONG_ONLY_{c}_{u}' for p in ('122D','90D') for c in ('BASE27','STRESS43') for u in ('RAW_AS_FRACTION','RAW_AS_PERCENT')]
    g.check([c['id'] for c in actual['cases']]==[c['id'] for c in audit['cases']]==selectors,'Eight fixed selectors without selection')
    for new,proof in zip(actual['cases'],audit['cases'],strict=True):
        s=new['summary'];days=122 if new['period']=='122D' else 90
        g.check(proof['complete_calendar_verified'] and s['required_minutes']==s['completed_minutes']==proof['completed_minutes_verified']==days*1440
            and proof['completed_days_verified']==days and proof['completed_months_verified']==(4 if days==122 else 3),'Complete agreed window')
        for key,value in proof['summary'].items():g.near(s[key],value,1e-7)
        g.near(s['all_observation_max_drawdown'],proof['all_observation_max_drawdown'],1e-10)
        g.check({k:v['sha256'] for k,v in new['artifacts'].items()}==proof['ledger_artifact_hashes'],'Saved independently accepted artifact identities only; no payload IO')
        refs=[]
        for mode in ('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH'):
            identity=f"{new['period']}_{mode}_{new['cost_id']}_{new['unit_id']}";control=old[identity]['summary'];v=old_proof[identity]
            g.check(v['complete_calendar_verified'] and control['cost_scenario']==s['cost_scenario'] and control['unit_scenario']==s['unit_scenario'],'Same complete cost/unit/control window')
            refs.append(dict(id=identity,evidence='CORRECTED_NEW_REFERENCE' if identity in FIXED else 'ORIGINAL_COMPLETE_REFERENCE',summary=control,
                delta_Donchian_minus_SMA_USDT={k:s[k]-control[k] for k in ('net_PnL','gross_PnL_same_quantities','fees_USDT','execution_cost_USDT','funding_USDT')}))
        comparisons.append(dict(id=new['id'],Donchian_summary=s,SMA_controls=refs,months=proof['months']))
    for name,h in plan.get('additional_project_files',{}).items():add(name,h)
    g.check(LOCK in local and LOCK not in hashes,'Private dataset lock is local-only exact guard')
    a.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=own,closure_binding_sha256=plan_sha,
        source_hashes=dict(hashes),local_non_git_hash_guard=dict(local),own_completion='LIVE_CALLER_NOT_YET_CLOSED')
    rb_sha,_=g.write(a.run_dir/'RUN_BINDING.json',binding);after=g.resources.status();g.bounded(after)
    elapsed=time.monotonic()-started;peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    g.check(elapsed<=120 and peak<=1000000000 and (a.run_dir/'RUN_BINDING.json').stat().st_size<=5000000,'Small metadata-only root budget')
    shared=dict(created_utc=datetime.now(UTC).isoformat(),binding=binding,source_hashes=hashes,local_non_git_hash_guard=local,
        roles=plan['roles'],prior=PRIOR,actual_closed_tasks=tasks,prior_root_closed_task=root_task,run_dir=str(a.run_dir),run_binding_sha256=rb_sha,
        historical_source_aliases=aliases,resources_before=before,resources_after=after,elapsed_seconds=elapsed,peak_RSS_bytes=peak,
        owned_bytes=(a.run_dir/'RUN_BINDING.json').stat().st_size,funding_rate_unit='UNCONFIRMED',unit_certified=False,native_market_certified=False,
        candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',unseen_qualification=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        no_market_or_ledger_payload_IO=True,no_market_artifact_rehash=True,no_financial_recalculation=True,old_accounts_replayed=False)
    root_result=dict(shared,status='PASS_ROOT_D041_PUBLIC_PERPETUAL_BENCHMARK_AND_SAVED_SUMMARY_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR',
        completed_new_full_calendar_accounts=8,saved_SMA_scenario_references=32,comparisons=comparisons,
        preserved_numeric_error_prefix_refs=[dict(id=c,report=PRIOR['old_actual'],summary=next(x['summary'] for x in prior['old_actual']['cases'] if x['id']==c)) for c in FIXED],
        comparison_scope='SEPARATE_FULL_ACCOUNTS_SAVED_SUMMARIES_NOT_JOINED_NAV_OR_CAUSAL_SHORT_EFFECT',realized_risk_matched_claimed=False,
        common_capital_USDT=10000,common_caps_do_not_equalize_realized_risk=True,economic_action='ACCEPT_COMPARISON_CAPABILITY_NO_INVESTMENT_ADOPTION')
    root_sha,_=g.write(ROOT/OUT,root_result)
    portable=dict(shared,status='PASS_D041_CLOSED_PORTABLE_BENCHMARK_SOURCE_BINDING_NOT_NATIVE_OR_LONG_TERM_APR',
        source_hashes={**hashes,OUT:root_sha},root_report_path=OUT,root_report_sha256=root_sha,real_data_and_runtime_not_Git=True,
        exclusions_from_portable_source_hashes=[LOCK],verified_prior_files={v['path']:v['sha256'] for v in PRIOR.values()})
    git_sha,_=g.write(ROOT/GIT,portable);print(json.dumps(dict(root_sha256=root_sha,portable_sha256=git_sha,root_task_id=binding['task_id'],root_own_task_not_yet_closed=True)))


if __name__=='__main__':main()
