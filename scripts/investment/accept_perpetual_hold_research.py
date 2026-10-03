"""UNRUN D044 close: saved small receipts only, no financial/source payload replay.

--binding: ready_to_execute/run_dir/source_hashes/market_protocol; roles
SOURCE_REUSE,SMOKE,CONTEXT,MARKET,FINANCIAL,COMPARISON,FULL547_FAILURE each
{path,sha256,status,task_id,exit_code}; prior_portables [{path,sha256}]; optional
historical_source_aliases {original_path,original_sha256,archive_path}; optional
metadata_failed_tasks is a role->task_id dict or a list of actual task IDs.
CONTEXT has no retrofitted report task_id: the separately bound real task is
verified against its frozen protocol/unchanged AST/count output instead.
"""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
LOCK='state/dataset_lock.json';LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
STATUS='PASS_ROOT_D044_TWELVE_CONSTANT_LONG_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
OUT='reports/fast_research/PERPETUAL_HOLD_ROOT_ACCEPTANCE_20261003_V1.json'
PORTABLE='reports/GITHUB_PERPETUAL_HOLD_SOURCE_BINDING_20261003_V1.json'
PRIOR={'reports/GITHUB_PERPETUAL_213_RESEARCH_SOURCE_BINDING_20261003_V1.json',
    'reports/GITHUB_PERPETUAL_213_USED_RECEIPTS_BINDING_20261003_V1.json'}
CURRENT_ALIAS=dict(original_path='docs/OPEN_SOURCE_REGISTRY.md',original_sha256='b43b246450136df6f1d1befd5ddfa4c08e6b62c8157df2e0a1b08e020a088e62',
    archive_path='docs/archive/OPEN_SOURCE_REGISTRY_PRE_PERPETUAL_HOLD_20261003_V1.md')
HOLD='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
PERIODS={'213D':(213,306720),'122D':(122,175680),'90D':(90,129600)}

def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binding',type=Path,required=True);args=parser.parse_args()
    assert sha(ROOT/GUARD)==GUARD_SHA
    loader=importlib.util.spec_from_file_location('_d044_root_guard',ROOT/GUARD)
    g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    plan,plan_sha=g.small(args.binding);run=Path(plan['run_dir']);task=os.getenv('COIN_TASK_ID')
    g.check(task and plan['ready_to_execute'] is True and run.parent==STATE and run.name.startswith('d044-') and not run.exists(),'Actual exclusive root task/STATE')
    g.check(Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2' and sha(ROOT/LOCK)==LOCK_SHA,'Frozen clean environment/private lock hash only')
    own=Path(__file__).resolve().relative_to(ROOT).as_posix();g.check(plan['source_hashes'][own]==sha(__file__),'Frozen root helper bytes')
    before=resources.status();g.bounded(before);started=time.monotonic();run.mkdir()
    rb=dict(task_id=task,source_hashes=plan['source_hashes'],source_sha256=sha(__file__),binding_path=str(args.binding),binding_sha256=plan_sha,
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),exact_command=shlex.join([sys.executable,*sys.argv]))
    rb_sha,_=g.write(run/'RUN_BINDING.json',rb)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D044-HOLD-ROOT-CLOSE-20261003-V1',event_id=task+':START',event_type='RESEARCH_ACCEPTANCE_START',
        git_commit=rb['git_commit'],protocol_hash=plan_sha,data_manifest_hash=plan['roles']['MARKET']['sha256'],feature_set='SAVED_THREE_WINDOW_CONSTANT_LONG_REFERENCE',
        labels='NONE',model_family='NONE',success_failure='START_BEFORE_SAVED_RECEIPTS',source_hashes=plan['source_hashes'],exact_command=rb['exact_command'])
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    report=dict(status='FAIL_ROOT_D044_HOLD',binding=rb,run_binding_sha256=rb_sha,run_dir=str(run),candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',
        funding_rate_unit='UNCONFIRMED',native_market_certified=False,unit_certified=False,market_arrays_read=False,old_accounts_or_QA_replayed=False,
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,local_non_git_hash_guard={LOCK:LOCK_SHA},resources_before=before,root_own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
    error=None
    try:
        g.check(set(plan['roles'])=={'SOURCE_REUSE','SMOKE','CONTEXT','MARKET','FINANCIAL','COMPARISON','FULL547_FAILURE'},'Exact six accepted roles and retained full547 failure')
        records={};closed={};verified={}
        for role,item in plan['roles'].items():
            row,digest=g.small(g.project(item['path']),item['sha256']);g.check(row['status']==item['status'],'Exact saved role '+role)
            expected_exit=1 if role=='FULL547_FAILURE' else 0;g.check(item['exit_code']==expected_exit,'No relabelled failure role')
            if role!='CONTEXT':g.check(row['binding']['task_id']==item['task_id'],'Same actual role task '+role)
            closed[role]=g.closed(item['task_id'],expected_exit);records[role]=row;verified[item['path']]=digest
            if 'run_dir' in row and 'run_binding_sha256' in row:
                saved,_=g.small(Path(row['run_dir'])/'RUN_BINDING.json',row['run_binding_sha256']);g.check(saved==row['binding'],'Exact saved RUN_BINDING '+role)
        failed=plan.get('metadata_failed_tasks',{});g.check(isinstance(failed,(dict,list)),'Explicit actual failure task identities')
        failed=failed.items() if isinstance(failed,dict) else enumerate(failed)
        report['metadata_failed_tasks']={str(name):g.closed(identity,1) for name,identity in failed}
        m,f,c=records['MARKET'],records['FINANCIAL'],records['COMPARISON'];spec,protocol_sha=g.small(g.project(plan['market_protocol']['path']),plan['market_protocol']['sha256'])
        g.check(spec['contract_id']=='D044_THREE_SEEN_USDM_PAST30_COVARIANCE_HOLD_REFERENCE_V1' and spec['period_ids']==list(PERIODS)
            and spec['rules']['initial_capital_USDT']==10000 and spec['rules']['strategy_id']==HOLD,'Fixed independent whole-capital recipe')
        g.check(m['binding']['protocol_sha256']==protocol_sha and m['binding']['source_hashes']==spec['frozen_sources']
            and f['actual_report_sha256']==plan['roles']['MARKET']['sha256'],'Same frozen market and independent identity')
        g.check(m['required_cases']==m['completed_cases']==f['completed_cases_verified']==f['financial_case_calls']==12
            and m['planned_trading_account_simulations']==m['completed_trading_account_simulations']==12
            and m['planned_constant_cash_baselines']==m['completed_constant_cash_baselines']==0,'Exactly12 new physical accounts, no CASH aliases')
        expected={f'{p}_LONG_ONLY_{cost}_{unit}' for p in PERIODS for cost in ('BASE27','STRESS43') for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT')}
        g.check({q['id'] for q in m['cases']}=={q['id'] for q in f['cases']}==expected,'No winner-case filtering')
        g.check([(w['id'],w['score_end_exclusive_us']-w['score_start_us']) for w in m['input_windows']]==[(p,v[0]*86400000000) for p,v in PERIODS.items()],'Three full input calendars, not stitched NAV')
        for q in m['cases']:g.check(q['mode']=='LONG_ONLY' and q['strategy_id']==q['summary']['strategy_id']==HOLD
            and q['summary']['required_minutes']==PERIODS[q['period']][1],'Correct recipe and whole required calendar')
        g.check(m['completed_full_calendar_cases']==f['completed_full_calendar_cases_verified']
            and m['incomplete_or_halted_cases']==f['incomplete_or_halted_cases_verified']
            and m['completed_full_calendar_cases']+m['incomplete_or_halted_cases']==12,'Actual completion/halt counts preserved')
        for role in ('MARKET','FINANCIAL'):g.check(records[role]['candidate']=='NO_QUALIFIED_CANDIDATE'
            and records[role]['long_term_APR']=='NOT_EVALUABLE' and not records[role]['unit_certified'] and not records[role]['native_market_certified'],'No unit/native/APR promotion')
        g.check(closed['FINANCIAL']['task']['started_at']>=closed['MARKET']['task']['ended_at']
            and closed['COMPARISON']['task']['started_at']>=closed['FINANCIAL']['task']['ended_at'],'Real post-market audit and comparison')
        g.check(records['SOURCE_REUSE']['source_files']==156 and records['SOURCE_REUSE']['source_only'] is True
            and records['SOURCE_REUSE']['new_source_QA_or_payload_IO'] is False and records['SOURCE_REUSE']['old_accounts_replayed'] is False,'Source-only accepted reuse, no invented new QA')
        smoke=records['SMOKE'];g.check(smoke['test_exit_code']==0 and smoke['source_bytes_unchanged'] is True
            and smoke['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0),'Only one actual new target/routing case')
        context=records['CONTEXT'];g.check(context['protocol_sha256']==protocol_sha and context['simulate_AST_unchanged'] is True
            and context['selected_periods']==list(PERIODS) and context['planned_physical_accounts']==12 and context['market_arrays_read'] is False,'Metadata-only frozen context, no retrofitted task in old JSON')
        g.check(records['FULL547_FAILURE']['completed_files']==83 and records['FULL547_FAILURE']['source_acceptance_granted'] is False,'Original rejected full547 remains rejected')
        g.check(c['compared_new_selectors']==c['cost_unit_period_groups']==len(c['groups'])==12 and c['saved_reference_rows']==60
            and c['summary_rows']==72 and c['paired_comparisons']==60 and c['old_accounts_replayed'] is False,'Saved12 groups, no old account replay')
        g.check({(r['period'],r['cost_id'],r['unit_id']) for r in c['groups']}=={(p,cost,unit) for p in PERIODS
            for cost in ('BASE27','STRESS43') for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT')},'All fixed cost/unit/window comparisons')
        g.check(m['peak_RSS_bytes']<=spec['budgets']['peak_RSS_bytes'] and m['elapsed_seconds']<=spec['budgets']['wall_seconds']
            and m['owned_bytes']<=spec['budgets']['new_owned_bytes'],'Frozen research resource budget')
        for name,digest in plan['source_hashes'].items():
            if name==LOCK:g.check(digest==LOCK_SHA,'Exact private lock digest')
            else:g.small(g.project(name),digest,False)
        g.check({r['path'] for r in plan['prior_portables']}==PRIOR,'Inherit both scientific source and actually used receipts bindings')
        priors=[];aliases={}
        for ref in plan['prior_portables']:
            prior,digest=g.small(g.project(ref['path']),ref['sha256']);priors.append(prior);verified[ref['path']]=digest
            for row in prior.get('historical_source_aliases',[]):aliases[row['original_path'],row['original_sha256']]=row
        for row in [*plan.get('historical_source_aliases',[]),CURRENT_ALIAS]:aliases[row['original_path'],row['original_sha256']]=row
        allowed={'docs/OPEN_SOURCE_REGISTRY.md':'docs/archive/OPEN_SOURCE_REGISTRY_','third_party/ts2vec/UPSTREAM.md':'third_party/ts2vec/UPSTREAM_FR68_CORE_20261001.md'}
        for (name,digest),row in aliases.items():g.check(name in allowed and row['archive_path'].startswith(allowed[name]),'Only existing narrow provenance aliases');g.small(g.project(row['archive_path']),digest,False)
        prior_files=dict(verified)
        for prior in priors:
            for field in ('verified_prior_files','source_hashes'):
                for name,digest in prior.get(field,{}).items():
                    if name==LOCK:g.check(digest==LOCK_SHA,'Prior private lock remains local');continue
                    resolved=aliases.get((name,digest),{}).get('archive_path',name);g.small(g.project(resolved),digest,False)
                    g.check(resolved not in prior_files or prior_files[resolved]==digest,'No conflicting portable byte pins');prior_files[resolved]=digest
        after=resources.status();g.bounded(after);report['resources_after']=after
        g.check(time.monotonic()-started<=120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1000000000,'Small root metadata resource limit')
        portable=dict(status='ROOT_D044_CONSTANT_LONG_SAVED_RESEARCH_BOUND_NOT_INVESTMENT',source_hashes={k:v for k,v in plan['source_hashes'].items() if k!=LOCK},
            verified_prior_files=prior_files,historical_source_aliases=list(aliases.values()),root_task_id=task,local_non_git_hash_guard={LOCK:LOCK_SHA},root_own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        g.check(sum(len(json.dumps(value,indent=2).encode()) for value in (rb,portable,report,c['groups']))<=5000000,'Small root outputs/RUN_BINDING budget')
        portable_sha,_=g.write(ROOT/PORTABLE,portable)
        report.update(status=STATUS,roles=closed,source_hashes=portable['source_hashes'],scientific_source_hashes=plan['source_hashes'],verified_actual_reports=verified,
            comparison_sha256=plan['roles']['COMPARISON']['sha256'],portable_binding_sha256=portable_sha,comparisons=c['groups'],completed_cases=12,
            completed_full_calendar_cases=m['completed_full_calendar_cases'],incomplete_or_halted_cases=m['incomplete_or_halted_cases'],physical_trading_accounts=12,
            planned_constant_cash_baselines=0,required_days_by_independent_window={p:v[0] for p,v in PERIODS.items()},funding_unit_conditions_not_selected=True,
            realized_risk_equalized=False,adoption='RESEARCH_BASELINE_AND_COMPARISON_CAPABILITY_ONLY; INVESTMENT_NONE_CASH')
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        digest,_=g.write(ROOT/OUT,report)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='RESEARCH_ACCEPTANCE_RESULT',success_failure=report['status'],artifact_path=OUT,artifact_sha256=digest))
    if error:raise error
    print(json.dumps(dict(status=report['status'],sha256=digest)))

if __name__=='__main__':main()