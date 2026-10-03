"""Accept saved D043 receipts only; never replay financial or source arrays."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from scripts.research_v8.registry import FIELDS, append_event

GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
LOCK='state/dataset_lock.json'
LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
STATUS='PASS_ROOT_D043_213D_CONDITIONAL_DIRECTION_COMPARISON_NOT_NATIVE_OR_LONG_TERM_APR'
OUT='reports/fast_research/PERPETUAL_213_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json'
PORTABLE='reports/GITHUB_PERPETUAL_213_RESEARCH_SOURCE_BINDING_20261003_V1.json'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True);a=p.parse_args()
    assert sha(ROOT/GUARD)==GUARD_SHA
    spec=importlib.util.spec_from_file_location('_d043_213_close_guard',ROOT/GUARD)
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    plan,plan_sha=g.small(a.binding);run=Path(plan['run_dir']);task=os.getenv('COIN_TASK_ID')
    g.check(task and plan['ready_to_execute'] is True and run.parent==STATE and not run.exists(),'New root task/STATE')
    g.check(sha(ROOT/LOCK)==LOCK_SHA,'Private lock hash only');start=time.monotonic();run.mkdir()
    own=Path(__file__).resolve().relative_to(ROOT).as_posix()
    g.check(plan['source_hashes'][own]==sha(__file__),'Exact root source')
    rb=dict(task_id=task,source_hashes=plan['source_hashes'],source_sha256=sha(__file__),binding_path=str(a.binding),
        binding_sha256=plan_sha,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        exact_command=shlex.join([sys.executable,*sys.argv]))
    rb_sha,_=g.write(run/'RUN_BINDING.json',rb)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D043-213D-ROOT-ACCEPTANCE-20261003-V1',event_id=task+':START',
        event_type='RESEARCH_ACCEPTANCE_START',git_commit=rb['git_commit'],protocol_hash=plan_sha,
        data_manifest_hash=plan['roles']['MARKET']['sha256'],feature_set='SAVED_213D_TWENTY_DIRECTIONS_AND_PUBLIC_REFERENCE',
        labels='NONE',model_family='NONE',seed=None,success_failure='START_BEFORE_SAVED_METADATA',
        reason_for_next_experiment='Accept independently checked actual direction contribution; no investment qualification',
        source_hashes=plan['source_hashes'],exact_command=rb['exact_command'])
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    report=dict(status='FAIL_ROOT_D043_213D_RESEARCH',binding=rb,run_binding_sha256=rb_sha,run_dir=str(run),
        candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',funding_rate_unit='UNCONFIRMED',
        native_market_certified=False,unit_certified=False,publication_or_exact_charge_certified=False,
        market_arrays_read=False,old_accounts_or_QA_replayed=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        local_non_git_hash_guard={LOCK:LOCK_SHA})
    error=None
    try:
        records={};closed={};verified={}
        g.check(set(plan['roles'])=={'SOURCE','SOURCE_QA','SOURCE_ROOT','SMOKE','MARKET','FINANCIAL','COMPARISON','FINANCIAL_V1_FAILURE','FULL547_FAILURE'},'Explicit actual roles')
        for role,item in plan['roles'].items():
            r,h=g.small(g.project(item['path']),item['sha256'])
            g.check(r['status']==item['status'] and r['binding']['task_id']==item['task_id'],'Exact role '+role)
            closed[role]=g.closed(item['task_id'],item['exit_code']);records[role]=r;verified[item['path']]=h
        report['separate_metadata_failures']={k:g.closed(v,1) for k,v in plan['separate_metadata_failures'].items()}
        m,f,c=records['MARKET'],records['FINANCIAL'],records['COMPARISON']
        g.check(m['completed_cases']==m['completed_full_calendar_cases']==20 and m['incomplete_or_halted_cases']==0
            and f['completed_cases_verified']==f['completed_full_calendar_cases_verified']==20
            and f['incomplete_or_halted_cases_verified']==0 and f['financial_case_calls']==17
            and f['shared_CASH_artifact_equivalences_verified']==3,'20 full selectors, truthful17 physical audit calls')
        g.check(f['actual_report_sha256']==plan['roles']['MARKET']['sha256']
            and m['completed_trading_account_simulations']==16 and m['completed_constant_cash_baselines']==1,'Same actual market bound')
        g.check(records['SOURCE_ROOT']['actual_archives']==72 and records['SOURCE_QA']['completed_files_verified']==72
            and records['SMOKE']['test_exit_code']==0,'First72 calendar checks and new route fixture')
        g.check(records['FULL547_FAILURE']['completed_files']==83 and records['FULL547_FAILURE']['source_acceptance_granted'] is False
            and records['FINANCIAL_V1_FAILURE']['financial_case_calls']==0,'Preserved rejected full547 and before-finance failure')
        # Claim no short increment only when saved actual executions and attribution agree.
        by={v['id']:v for v in m['cases']};pairs=[]
        for cost in ('BASE27','STRESS43'):
            for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
                get=lambda mode:by[f'213D_{mode}_{cost}_{unit}']['summary']
                lo,so,ls,cash=get('LONG_ONLY'),get('SHORT_ONLY'),get('LONG_SHORT'),get('CASH')
                g.check(so['trade_legs']==0 and so['net_PnL']==cash['net_PnL']==0
                    and ls['net_PnL']==lo['net_PnL'] and ls['long_short_marked_contribution']['SHORT']['net_contribution']==0,
                    'This fixed window has no short signal/execution, not a short-capability failure')
                pairs.append(dict(cost=cost,unit=unit,SMA_long_net_USDT=lo['net_PnL'],SMA_short_net_USDT=so['net_PnL'],
                    long_short_minus_long_USDT=ls['net_PnL']-lo['net_PnL'],SMA_vol=lo['daily_metrics']['annual_volatility'],
                    SMA_all_observation_MDD=lo['all_observation_max_drawdown'],
                    Donchian_long_net_USDT=get('DONCHIAN_LONG_ONLY')['net_PnL']))
        for name,digest in plan['source_hashes'].items():g.check(sha(ROOT/name)==digest,'Frozen source '+name)
        prior,prior_sha=g.small(g.project(plan['prior_portable']['path']),plan['prior_portable']['sha256'])
        prior_files=dict(prior['verified_prior_files']);prior_files.update(prior['source_hashes']);prior_files.update(verified)
        prior_files[plan['prior_portable']['path']]=prior_sha
        for name,digest in prior_files.items():
            resolved=next((v['archive_path'] for v in prior.get('historical_source_aliases',[]) if v['original_path']==name and v['original_sha256']==digest),name)
            g.check(sha(ROOT/resolved)==digest,'Prior unchanged bytes '+name)
        portable=dict(status='ROOT_D043_ACTUAL_CONDITIONAL_RESEARCH_BOUND_NOT_INVESTMENT',
            source_hashes={k:v for k,v in plan['source_hashes'].items() if k!=LOCK},verified_prior_files=prior_files,
            historical_source_aliases=prior.get('historical_source_aliases',[]),root_task_id=task,
            local_non_git_hash_guard={LOCK:LOCK_SHA})
        psha,_=g.write(ROOT/PORTABLE,portable)
        report.update(status=STATUS,roles=closed,source_hashes=plan['source_hashes'],verified_actual_reports=verified,
            comparison_sha256=plan['roles']['COMPARISON']['sha256'],portable_binding_sha256=psha,paired_summary=pairs,
            complete_score_days=213,short_trades_this_window=0,prior_D040_short_execution_preserved=True,
            funding_unit_conditions_not_selected=True,realized_risk_equalized=False,
            adoption='RESEARCH_CAPABILITY_AND_FIXED_SMA_REFERENCE_ONLY; INVESTMENT_NONE_CASH',
            next_question='Does same-product past-volatility-managed hold dominate fixed SMA across separate complete windows?')
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-start,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        digest,_=g.write(ROOT/OUT,report)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='RESEARCH_ACCEPTANCE_RESULT',
            success_failure=report['status'],artifact_path=OUT,artifact_sha256=digest))
    if error:raise error
    print(json.dumps(dict(status=report['status'],sha256=digest)))

if __name__=='__main__':main()
