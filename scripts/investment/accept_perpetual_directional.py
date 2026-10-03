"""Metadata-only root closure, after the original seven and three repair roles close0.

--binding: ready_to_execute/helper_sha256/protocol{path,sha256}, roles with
SOURCE_ROOT,SIGNAL,ACCOUNT,CHAIN,CONTROLLER,MARKET,INDEPENDENT,
SETTLEMENT_TEST,FIXED_MARKET,FIXED_INDEPENDENT, each
{path,sha256,required_status,task_id}; old_portable/capability{path,sha256};
settlement_protocol{path,sha256}; preserved_controller_failure{path,sha256,task_id};
additional_project_files. Original32 evidence is retained, not rewritten.
No saved market/ledger payload is opened, hashed or financially recomputed.
"""
import argparse, hashlib, importlib.util, json, os, resource, sys, time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
ARCHIVE='docs/archive/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py'
OUT='reports/fast_research/PERPETUAL_DIRECTIONAL_ROOT_ACCEPTANCE_20261003_V1.json'
GIT='reports/GITHUB_PERPETUAL_DIRECTIONAL_SOURCE_BINDING_20261003_V1.json'
LOCK='state/dataset_lock.json'
TEST_STATUS='PASS_BOUNDED_RESEARCH_TESTS_SYNTHETIC_NOT_MARKET_RESULT'
STATUSES={'SOURCE_ROOT':'PASS_NEW_PERPETUAL_TRADE_SOURCE_ROOT_METADATA_CLOSURE',
 'SIGNAL':TEST_STATUS,'ACCOUNT':TEST_STATUS,'CHAIN':TEST_STATUS,'CONTROLLER':TEST_STATUS,
 'MARKET':'COMPLETE_CONDITIONAL_USDM_FOUR_DIRECTION_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR',
 'INDEPENDENT':'PASS_CONDITIONAL_PERPETUAL_DIRECTIONAL_JOURNAL_NAV_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR',
 'SETTLEMENT_TEST':TEST_STATUS,
 'FIXED_MARKET':'COMPLETE_TWO_EXACT_SETTLEMENT_CORRECTNESS_REPLAYS_NOT_NATIVE_OR_LONG_TERM_APR',
 'FIXED_INDEPENDENT':'PASS_TWO_EXACT_SETTLEMENT_REPLAYS_INDEPENDENT_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR'}
FIXED_SELECTORS=['90D_SHORT_ONLY_BASE27_RAW_AS_PERCENT','90D_LONG_SHORT_BASE27_RAW_AS_PERCENT']
ALIASES=[('docs/OPEN_SOURCE_REGISTRY.md','8da5b04187f618759de190260bb7b277bf402c6f31b0480c37a85c8788e06f0e',
          'docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_20261003_V1.md'),
 ('scripts/investment/perpetual_directional.py','71bc62a72a55d2085a9a393ed134d6edc9e971d635701bcfff2a912e6f717a37',
  'docs/archive/PERPETUAL_DIRECTIONAL_FAILED_COLLECTION_SOURCE_20261003_V1.py'),
 ('src/quant/perpetual_account.py','2bae17b6351dec5c632e3af42fed2a6a5cf91293dba0a08c06a7aa81f4df58fb',
  'docs/archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py')]
# The failed source is an archive alias, never a demand that current code be71bc.

def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binding',type=Path,required=True);parser.add_argument('--run-dir',type=Path,required=True)
    args=parser.parse_args();started=time.monotonic()
    assert digest(ROOT/GUARD)==GUARD_SHA
    loader=importlib.util.spec_from_file_location('perpetual_root_metadata_guards',ROOT/GUARD)
    g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    g.check(os.getenv('COIN_TASK_ID') and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2','Bounded clean CPU environment')
    g.check(args.binding.parent==ROOT/'protocols' and args.run_dir.parent==STATE and not args.run_dir.exists()
        and not (ROOT/OUT).exists() and not (ROOT/GIT).exists(),'Exclusive metadata closure')
    plan,plan_sha=g.small(args.binding);g.check(plan['ready_to_execute'] is True and set(plan['roles'])==set(STATUSES),'Ten actual completed roles')
    _,own=g.small(__file__,plan['helper_sha256'],False);g.small(ROOT/ARCHIVE,own,False)
    before=g.resources.status();g.bounded(before);hashes={};local={};aliases=[];reports={};tasks={}
    def add(name,value):
        canonical=name
        for original,old_sha,archive in ALIASES:
            if (name,value)==(original,old_sha):
                canonical=archive;item=dict(original_path=name,original_sha256=value,archive_path=archive)
                if item not in aliases:aliases.append(item)
        g.small(g.project(canonical),value,False)
        destination=local if canonical==LOCK else hashes
        g.check(canonical not in destination or destination[canonical]==value,'No conflicting source identity')
        destination[canonical]=value
    add(GUARD,GUARD_SHA);add(ARCHIVE,own);add(Path(__file__).relative_to(ROOT).as_posix(),own)
    add(str(args.binding.relative_to(ROOT)),plan_sha)
    for role,expected in STATUSES.items():
        item=plan['roles'][role];report,h=g.small(g.project(item['path']),item['sha256'])
        identity=report['binding']['task_id']
        g.check(report['status']==item['required_status']==expected and identity==item['task_id'],'Exact actual role '+role)
        reports[role]=report;tasks[role]=g.closed(identity);add(item['path'],h)
        for name,source_sha in report['binding']['source_hashes'].items():add(name,source_sha)
        role_protocol_sha=report['binding'].get('protocol_sha256')
        if role_protocol_sha:
            if report['binding'].get('protocol_path'):
                p=Path(report['binding']['protocol_path'])
                p=(p if p.is_absolute() else ROOT/p).resolve()
                g.check(p.is_relative_to(ROOT/'protocols'),'Exact executed ROOT protocol path')
                add(p.relative_to(ROOT).as_posix(),role_protocol_sha)
            else:
                matches=[name for name,value in report['binding']['source_hashes'].items()
                    if name.startswith('protocols/') and value==role_protocol_sha]
                g.check(len(matches)==1,'Unique actual protocol SHA in executed test source map')
        if report.get('run_dir') and report.get('run_binding_sha256'):
            rb,_=g.small(Path(report['run_dir'])/'RUN_BINDING.json',report['run_binding_sha256'])
            g.check(rb['task_id']==identity,'Actual run binding '+role)
    g.check(len({t['task']['id'] for t in tasks.values()})==10,'Separate true completed0 tasks')
    for role in ('SOURCE_ROOT','SIGNAL','ACCOUNT','CHAIN','CONTROLLER'):
        g.check(tasks['MARKET']['task']['started_at']>=tasks[role]['task']['ended_at'],'Market after actual accepted prerequisites')
    g.check(tasks['INDEPENDENT']['task']['started_at']>=tasks['MARKET']['task']['ended_at'],'Independent after actual closed market')
    for left,right in (('INDEPENDENT','SETTLEMENT_TEST'),('SETTLEMENT_TEST','FIXED_MARKET'),('FIXED_MARKET','FIXED_INDEPENDENT')):
        g.check(tasks[right]['task']['started_at']>=tasks[left]['task']['ended_at'],'Actual correctness replay order')
    source=reports['SOURCE_ROOT'];g.check(source['source_acceptance_granted'] and not source['funding_unit_certified'],
         'Only new source format acceptance, not funding certification')
    for role,count in [('SIGNAL',1),('ACCOUNT',10),('CHAIN',1),('CONTROLLER',1),('SETTLEMENT_TEST',1)]:
        r=reports[role];g.check(r['test_exit_code']==0 and r['source_bytes_unchanged']
            and r['junit_counts']==dict(tests=count,errors=0,failures=0,skipped=0),'Actual accepted synthetic counts')
        junit=Path(r['run_dir'])/'junit.xml';g.small(junit,r['junit_sha256'],False)
        suites=ET.parse(junit).getroot().iter('testsuite')
        totals=dict.fromkeys(('tests','errors','failures','skipped'),0)
        for suite in suites:
            for key in totals:totals[key]+=int(suite.get(key,0))
        g.check(totals==r['junit_counts'],'Saved actual JUnit metadata')
    proto=plan['protocol'];spec,proto_sha=g.small(g.project(proto['path']),proto['sha256']);add(proto['path'],proto_sha)
    g.check(spec['contract_id']=='USDM_DIRECTIONAL_TWO_PERIOD_CONDITIONAL_20261003_V1'
        and spec['period_ids']==['122D','90D'] and spec['budgets']==dict(new_owned_bytes=400000000,peak_RSS_bytes=1500000000,wall_seconds=3600),
        'Fixed full two-window source/risk/resource contract')
    actual,audit=reports['MARKET'],reports['INDEPENDENT']
    g.check(actual['binding']['source_hashes']==spec['frozen_sources'] and actual['binding']['protocol_sha256']==proto_sha,
        'Actual complete scientific source map')
    for name,h in spec['frozen_sources'].items():add(name,h)
    for name,h in source['binding']['source_hashes'].items():add(name,h)
    g.check(spec['trade_source_acceptance']['path']==plan['roles']['SOURCE_ROOT']['path']
        and spec['trade_source_acceptance']['sha256']==plan['roles']['SOURCE_ROOT']['sha256']
        and spec['required_smoke_receipt']['path']==plan['roles']['CONTROLLER']['path']
        and spec['required_smoke_receipt']['sha256']==plan['roles']['CONTROLLER']['sha256'],'Required real source/controller binding')
    g.check(audit['actual_report_sha256']==plan['roles']['MARKET']['sha256'] and audit['required_cases']==audit['completed_cases_verified']==32,
        'Independent exact actual32 selectors')
    canonical=g.canonical_reports(audit['binding']['actual_reports'])
    g.check(canonical=={str(g.project(plan['roles']['MARKET']['path']).resolve()):plan['roles']['MARKET']['sha256']},'Unique independent actual report')
    for name,h in audit['verified_source_hashes'].items():add(name,h)
    g.check(audit['independent_source_sha256']==audit['binding']['checker_sha256'],'Executed independent checker source')
    run=Path(spec['run_dir']);rb,rb_sha=g.small(run/'RUN_BINDING.json',actual['run_binding_sha256'])
    g.check(rb==actual['binding'] and audit['actual_run_binding_sha256']==rb_sha,'Exact actual RUN_BINDING')
    g.check(actual['required_cases']==actual['completed_cases']==32 and actual['completed_trading_account_simulations']==24
        and actual['completed_constant_cash_baselines']==2,'32 selectors,24 trading simulations,2 physical cash baselines')
    g.check(actual['elapsed_seconds']<=3600 and actual['peak_RSS_bytes']<=1500000000 and actual['owned_bytes']<=400000000,
         'Actual research wall/RSS/STATE budget')
    for r in (actual,audit,reports['FIXED_MARKET'],reports['FIXED_INDEPENDENT']):
        g.check(r['funding_rate_unit']=='UNCONFIRMED' and not r['unit_certified'] and not r['native_market_certified']
            and r['candidate']=='NO_QUALIFIED_CANDIDATE' and r['long_term_APR']=='NOT_EVALUABLE'
            and r['models_fit']==r['orders_sent']==r['GPU']==0 and not r['locked_consumed'],'Conditional scope never promoted')
        g.bounded(r['resources_before']);g.bounded(r['resources_after'])
    selectors=[f'{p}_{m}_{c}_{u}' for p in ('122D','90D') for m in ('LONG_ONLY','SHORT_ONLY','LONG_SHORT','CASH')
        for c in ('BASE27','STRESS43') for u in ('RAW_AS_FRACTION','RAW_AS_PERCENT')]
    g.check([c['id'] for c in actual['cases']]==[c['id'] for c in audit['cases']]==selectors,'Fixed selectors, no economic selection')
    def accepted_case_summaries(produced_cases,verified_cases,owned_run):
        rows=[]
        for produced,proof in zip(produced_cases,verified_cases,strict=True):
            s=produced['summary'];count=175680 if produced['period']=='122D' else 129600
            g.check(produced['id']==proof['id'] and s['required_minutes']==count
                and s['completed_minutes']==proof['completed_minutes_verified']<=count
                and proof['complete_calendar_verified']==(s['completed_minutes']==count)
                and proof['complete_calendar_verified']==(s['completion']=='COMPLETE_CONDITIONAL_ACCOUNT'),'Honest completed/prefix calendar')
            g.check({k:v['sha256'] for k,v in produced['artifacts'].items()}==proof['ledger_artifact_hashes'],'Already independently accepted artifact hashes')
            for item in produced['artifacts'].values():
                path=Path(item['path']);g.check(path.is_relative_to(owned_run) and path.is_file() and not path.is_symlink()
                    and path.stat().st_size==item['bytes'],'Artifact file stat only, no data rehash')
            for key,value in proof['summary'].items():g.near(s[key],value,1e-7)
            g.near(s['all_observation_max_drawdown'],proof['all_observation_max_drawdown'],1e-10)
            g.near(s['terminal_marked_notional'],proof['actual_terminal_marked_notional'],1e-7)
            if proof['complete_calendar_verified']:
                g.check(proof['completed_days_verified']==(122 if produced['period']=='122D' else 90)
                    and proof['completed_months_verified']==(4 if produced['period']=='122D' else 3),'Authorized complete day/month scope')
            else:g.check(s['daily_metrics'] is None,'Prefix is not a full-window return')
            rows.append(dict(id=produced['id'],summary=s,independent_scope={k:proof[k] for k in
                ('complete_calendar_verified','completed_minutes_verified','completed_days_verified','completed_months_verified')},
                ledger_artifact_hashes=proof['ledger_artifact_hashes']))
        return rows
    cases=accepted_case_summaries(actual['cases'],audit['cases'],run)
    g.check(actual['completed_full_calendar_cases']==audit['completed_full_calendar_cases_verified']
        and actual['incomplete_or_halted_cases']==audit['incomplete_or_halted_cases_verified'],'Whole-window completion is not assumed')
    g.check(audit['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10),'Original independent tolerances')
    g.check(audit['maximum_errors']['cash']<=1e-7 and audit['maximum_errors']['ratio']<=1e-10,'Saved independent numerical bounds')
    g.check(actual['completed_full_calendar_cases']==30 and actual['incomplete_or_halted_cases']==2
        and [c['id'] for c in actual['cases'] if c['summary']['completion']!='COMPLETE_CONDITIONAL_ACCOUNT']==FIXED_SELECTORS,
        'Original32 retains thirty full and two numeric-error prefixes')
    for case in (c for c in actual['cases'] if c['id'] in FIXED_SELECTORS):
        g.check(case['summary']['halt_witness']['decimal_strings']['unpaid_liability']=='1.000E-37'
            and case['summary']['NAV']>10000 and case['summary']['free_cash']>9000,'Original false-bankruptcy witness preserved')
    fixed_spec_ref=plan['settlement_protocol'];fixed_spec,fixed_spec_sha=g.small(g.project(fixed_spec_ref['path']),fixed_spec_ref['sha256'])
    add(fixed_spec_ref['path'],fixed_spec_sha);fixed,fixed_audit=reports['FIXED_MARKET'],reports['FIXED_INDEPENDENT']
    g.check(fixed_spec['contract_id']=='USDM_EXACT_SETTLEMENT_TWO_FALSE_HALTS_20261003_V1'
        and fixed_spec['selectors']==FIXED_SELECTORS and fixed_spec['rules']==spec['rules']
        and fixed_spec['cost']==spec['cost_scenarios'][0] and fixed_spec['unit']==spec['unit_scenarios'][1],'Only exact correctness replay selectors, unchanged science')
    for key,role in (('original_actual','MARKET'),('original_independent','INDEPENDENT'),('required_settlement_test','SETTLEMENT_TEST')):
        g.check(fixed_spec[key]['path']==plan['roles'][role]['path'] and fixed_spec[key]['sha256']==plan['roles'][role]['sha256'],'Replay required actual proofs')
    g.check(fixed['binding']['source_hashes']==fixed_spec['frozen_sources']
        and fixed['binding']['protocol_sha256']==fixed_spec_sha and fixed['original_report_sha256']==plan['roles']['MARKET']['sha256']
        and fixed['original_independent_sha256']==plan['roles']['INDEPENDENT']['sha256'],'New repair binding, original reports not overwritten')
    for name,h in fixed_spec['frozen_sources'].items():add(name,h)
    for name,h in fixed_audit['verified_source_hashes'].items():add(name,h)
    fixed_run=Path(fixed_spec['run_dir']);fixed_rb,fixed_rb_sha=g.small(fixed_run/'RUN_BINDING.json',fixed['run_binding_sha256'])
    g.check(fixed_rb==fixed['binding'] and fixed_audit['actual_run_binding_sha256']==fixed_rb_sha
        and fixed_audit['actual_report_sha256']==plan['roles']['FIXED_MARKET']['sha256'],'New independent exact replay RUN_BINDING')
    g.check(g.canonical_reports(fixed_audit['binding']['actual_reports'])=={
        str(g.project(plan['roles']['FIXED_MARKET']['path']).resolve()):plan['roles']['FIXED_MARKET']['sha256']},'Unique independently audited new replay')
    g.check(fixed_audit['independent_source_sha256']==fixed_audit['binding']['checker_sha256']
        and fixed_audit['required_cases']==fixed_audit['completed_cases_verified']==fixed['required_cases']==fixed['completed_cases']==2
        and fixed['completed_full_calendar_cases']==fixed_audit['completed_full_calendar_cases_verified']==2
        and fixed['incomplete_or_halted_cases']==0
        and fixed['completed_trading_account_simulations']==2 and fixed['completed_constant_cash_baselines']==0
        and not fixed['original_other_thirty_financial_cases_replayed'],'Two complete new cases only; no thirty-case replay')
    g.check([c['id'] for c in fixed['cases']]==[c['id'] for c in fixed_audit['cases']]==FIXED_SELECTORS,'No new unit/cost/economic subset selection')
    g.check(fixed_audit['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10)
        and fixed_audit['maximum_errors']['cash']<=1e-7 and fixed_audit['maximum_errors']['ratio']<=1e-10,'Repair independent numerical bounds unchanged')
    g.check(fixed_audit['original_report_sha256']==plan['roles']['MARKET']['sha256']
        and fixed_audit['original_independent_sha256']==plan['roles']['INDEPENDENT']['sha256']
        and fixed_audit['original_other_thirty_verified_scope_referenced']==30
        and fixed_audit['NOT_SINGLE_FRESH_32_SUITE'] is True,'Separate original and corrected evidence, no fictional fresh32 suite')
    g.check(fixed['elapsed_seconds']<=fixed_spec['budgets']['wall_seconds']
        and fixed['peak_RSS_bytes']<=fixed_spec['budgets']['peak_RSS_bytes'] and fixed['owned_bytes']<=fixed_spec['budgets']['new_owned_bytes'],'Actual correctness replay resource budget')
    fixed_cases=accepted_case_summaries(fixed['cases'],fixed_audit['cases'],fixed_run)
    for case in fixed_cases:
        s=case['summary'];g.check(s['unpaid_liability']==s['terminal_marked_notional']==0 and not s.get('halt_witness'),'Exact repaired settlement, not artificial zero after halt')
    g.check(spec['frozen_sources']['src/quant/perpetual_account.py']==ALIASES[2][1]
        and fixed_spec['frozen_sources']['src/quant/perpetual_account.py']!=ALIASES[2][1],'Old archived account and new normal source are separately bound')
    cap_ref=plan['capability'];cap,cap_sha=g.small(g.project(cap_ref['path']),cap_ref['sha256']);add(cap_ref['path'],cap_sha)
    capability_task=g.closed(cap['task_id'])
    for name,h in cap['archived_metadata'].items():add(name,h)
    for identity,item in cap['preserved_root_initialization_failures'].items():
        failed=g.closed(identity,1);g.check(failed['sha256']==item['sha256'],'Preserved source-root failure remains failed1')
    failure=plan['preserved_controller_failure'];f,h=g.small(g.project(failure['path']),failure['sha256']);add(failure['path'],h)
    failed_task=g.closed(failure['task_id'],1)
    g.check(f['binding']['task_id']==failure['task_id'] and f['status']=='FAIL_BOUNDED_RESEARCH_TESTS_SYNTHETIC'
        and f['test_exit_code']==2 and f['junit_counts']==dict(tests=1,errors=1,failures=0,skipped=0),
        'True failed collection, no executed finance case')
    for name,h in f['binding']['source_hashes'].items():add(name,h)
    old_ref=plan['old_portable'];old,h=g.small(g.project(old_ref['path']),old_ref['sha256']);add(old_ref['path'],h)
    g.check(old['status']=='PASS_D038_PORTABLE_SOURCE_BINDING_PRIVATE_LOCK_EXCLUDED','Accepted previous portable proof')
    g.closed(old['binding']['task_id'])
    for name,h in old['source_hashes'].items():add(name,h)
    for name,h in plan.get('additional_project_files',{}).items():add(name,h)
    g.check(LOCK in local and LOCK not in hashes,'Private lock exact locally, excluded from Git source map')
    args.run_dir.mkdir();binding=dict(task_id=os.environ['COIN_TASK_ID'],helper_sha256=own,closure_binding_sha256=plan_sha,
        root_own_completion='LIVE_CALLER_NOT_YET_SELF_CERTIFIED',source_hashes=dict(hashes),local_non_git_hash_guard=dict(local))
    root_run_binding_sha,_=g.write(args.run_dir/'RUN_BINDING.json',binding)
    archive_dir=ROOT/'docs/archive/PERPETUAL_DIRECTIONAL_USED_ACTUAL_METADATA_20261003_V1';g.check(not archive_dir.exists(),'New task archive')
    archive_dir.mkdir()
    for role,task in {**tasks,'CAPABILITY':capability_task,'FAILED_CONTROLLER':failed_task}.items():
        payload=g.ordinary(task['path']).read_bytes();target=archive_dir/(role+'_TASK.json')
        with target.open('xb') as stream:stream.write(payload)
        add(str(target.relative_to(ROOT)),task['sha256'])
    after=g.resources.status();g.bounded(after)
    elapsed=time.monotonic()-started;peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    owned_bytes=sum(p.stat().st_size for p in args.run_dir.iterdir() if p.is_file())
    g.check(elapsed<=120 and peak<=1000000000 and owned_bytes<=5000000,'Metadata-only root budget120s/RSS1GB/STATE5MB')
    shared=dict(created_utc=datetime.now(UTC).isoformat(),binding=binding,source_hashes=hashes,local_non_git_hash_guard=local,
        run_dir=str(args.run_dir),run_binding_sha256=root_run_binding_sha,
        historical_source_aliases=[a for a in aliases if a['original_path']=='docs/OPEN_SOURCE_REGISTRY.md'],
        preserved_executed_source_aliases=[a for a in aliases if a['original_path']!='docs/OPEN_SOURCE_REGISTRY.md'],
        roles=plan['roles'],actual_closed_tasks=tasks,source_only_qualification_not_promoted=True,
        no_market_or_ledger_payload_reopened=True,no_financial_recalculation=True,old_QA_or_green_replayed=False,
        funding_rate_unit='UNCONFIRMED',unit_certified=False,native_execution_certified=False,MMR_native_certified=False,
        candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',unseen_qualification=False,
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources_before=before,resources_after=after,
        preserved_failed_controller_task=failed_task,capability_proof=cap_ref,own_completion='LIVE_CALLER_REQUIRES_LATER_CLOSED0',
        elapsed_seconds=elapsed,peak_RSS_bytes=peak,owned_bytes=owned_bytes)
    root=dict(shared,status='PASS_ROOT_PERPETUAL_DIRECTIONAL_CONDITIONAL_METADATA_NOT_NATIVE_OR_LONG_TERM_APR',
        completed_scenario_selectors=32,original_physical_trading_simulations=24,
        correctness_replay_physical_trading_simulations=2,constant_cash_baselines=2,
        original_full_calendar_cases=30,original_numeric_error_prefixes=2,corrected_new_full_calendar_cases=2,
        original32_cases=cases,corrected_new_cases=fixed_cases,
        full_calendar_scenario_evidence_count=32,
        scenario_coverage_evidence=[dict(id=c['id'],actual_role='FIXED_MARKET' if c['id'] in FIXED_SELECTORS else 'MARKET',
            independent_role='FIXED_INDEPENDENT' if c['id'] in FIXED_SELECTORS else 'INDEPENDENT') for c in cases],
        evidence_scope='THIRTY_ORIGINAL_COMPLETE_PLUS_TWO_NEW_COMPLETE_REFERENCES_NOT_SINGLE_FRESH32_OR_JOINED_NAV',
        original_reports_or_NAV_overwritten=False,independent_maximum_errors=audit['maximum_errors'],
        corrected_independent_maximum_errors=fixed_audit['maximum_errors'],independent_tolerances=audit['tolerances'],
        economic_action='ACCEPT_CONDITIONAL_COMPARISON_CAPABILITY_NO_INVESTMENT_ADOPTION',
        saved_actual_resources={role:{k:reports[role][k] for k in ('elapsed_seconds','peak_RSS_bytes','owned_bytes','disk')}
            for role in ('MARKET','FIXED_MARKET')})
    root_sha,_=g.write(ROOT/OUT,root)
    portable=dict(shared,status='PASS_CLOSED_PERPETUAL_DIRECTIONAL_PORTABLE_SOURCE_BINDING_UNIT_UNCERTIFIED_NOT_APR',
        source_hashes={**hashes,OUT:root_sha},root_report_path=OUT,root_report_sha256=root_sha,
        exclusions_from_portable_source_hashes=[LOCK],real_data_and_runtime_not_Git=True)
    git_sha,_=g.write(ROOT/GIT,portable)
    print(json.dumps(dict(root_report=OUT,root_sha256=root_sha,portable_report=GIT,portable_sha256=git_sha,
        completed_prior_roles=10,root_task_id=binding['task_id'],own_root_task_not_yet_closed=True)))

if __name__=='__main__':main()
