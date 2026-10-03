"""Close only the new complete213 source; failed547 parent remains failed.

Metadata-only closure after producer and first72 independent archive checks.
No market arrays, price interpolation, new economic or native unit claims.
"""
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
STATUS='PASS_ROOT_D043_COMPLETE_213_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS'
INPUT='reports/fast_research/PERPETUAL_213D_INPUT_BINDING_20261003_V1.json'
OUT='reports/fast_research/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--binding',type=Path,required=True);a=p.parse_args()
    assert sha(ROOT/GUARD)==GUARD_SHA
    loader=importlib.util.spec_from_file_location('_d043_213_guard',ROOT/GUARD)
    g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    plan,plan_sha=g.small(a.binding)
    g.check(plan['ready_to_execute'] is True and plan['source_hashes'][Path(__file__).resolve().relative_to(ROOT).as_posix()]==sha(__file__), 'Frozen root source')
    run=Path(plan['run_dir']);g.check(run.parent==STATE and not run.exists() and os.getenv('COIN_TASK_ID'),'Exclusive root task')
    g.check(sha(ROOT/LOCK)==LOCK_SHA,'Private lock SHA only');run.mkdir();start=time.monotonic()
    rb=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),source_hashes=plan['source_hashes'],
        binding_path=str(a.binding),binding_sha256=plan_sha,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        exact_command=shlex.join([sys.executable,*sys.argv]))
    rb_sha,_=g.write(run/'RUN_BINDING.json',rb)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D043-213-SOURCE-ROOT-20261003-V1',event_id=rb['task_id']+':START',
        event_type='OPERATIONAL_SOURCE_ACCEPTANCE_START',git_commit=rb['git_commit'],protocol_hash=plan_sha,
        data_manifest_hash=plan['roles']['SOURCE']['sha256'],feature_set='ONLY_72_OFFICIAL_USDM_213_SOURCE_FILES',labels='NONE',model_family='NONE',
        hyperparameters={'archives':72,'reused_failed_parent_complete_files':51,'new_files':21},seed=None,
        thresholds={'days':213,'wall_seconds':120,'peak_RSS_bytes':1_000_000_000},cost_assumptions='NOT_EVALUATED',
        all_folds='SEEN_JAN_JUL2024_INPUT_ONLY',success_failure='START_BEFORE_ROOT_METADATA',
        reason_for_next_experiment='Complete paired213 input; preserve original547 source rejection',result_influenced_later_choice=False,
        source_hashes=rb['source_hashes'],exact_command=rb['exact_command'])
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    report=dict(status='FAIL_ROOT_D043_213_SOURCE',binding=rb,run_binding_sha256=rb_sha,source_only=True,
        funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,native_Bybit_certified=False,publication_or_exact_charge_certified=False,
        market_arrays_read=False,economics='NOT_EVALUATED',candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,local_non_git_hash_guard={LOCK:LOCK_SHA})
    error=None
    try:
        records={};tasks={};proofs={}
        g.check(set(plan['roles'])=={'METADATA','PRECEDING_FAILURE','SOURCE','INDEPENDENT'},'Four explicit actual roles')
        for role,item in plan['roles'].items():
            r,h=g.small(g.project(item['path']),item['sha256'])
            g.check(r['status']==item['status'] and r['binding']['task_id']==item['task_id'],'Exact actual role '+role)
            tasks[role]=g.closed(item['task_id'],1 if role=='PRECEDING_FAILURE' else 0);records[role]=r;proofs[item['path']]=h
        source,qa,failed=records['SOURCE'],records['INDEPENDENT'],records['PRECEDING_FAILURE']
        g.check(failed['status']=='FAIL_D042_HISTORY_SOURCE' and failed['completed_files']==83 and failed['required_files']==148
            and failed['source_acceptance_granted'] is False,'Parent still rejected547 source')
        g.check(source['completed_files']==source['required_files']==len(source['sources'])==72
            and source['archive_bodies_downloaded']==21 and qa['actual_archives']==qa['completed_files_verified']==72
            and qa['actual_report_sha256']==proofs[plan['roles']['SOURCE']['path']]
            and qa['protocol_sha256']==source['binding']['protocol_sha256'],'All72 source/independent bindings')
        independent={(r['kind'],r['symbol'],r.get('interval'),r['month']):r for r in qa['sources']};files={}
        g.check(len(independent)==72,'72 distinct independent sources')
        for r in source['sources']:
            key=(r['kind'],r['symbol'],r.get('interval'),r['month']);v=independent[key]
            g.check(v['receipt_path']==r['receipt_path'] and v['receipt_sha256']==r['receipt_sha256']
                and v['normalized_sha256']==r['normalized_sha256'],'Same exact independent payload receipt')
            name=f"trade:{r['interval']}:{r['symbol']}:{r['month']}" if r['kind']=='klines' else f"{r['kind']}:{r['symbol']}:{r['month']}"
            g.check(name not in files,'Unique product source ID')
            files[name]=dict(r,format_evidence_role='D043_213_FIRST_INDEPENDENT_FORMAT_CALENDAR_QA',
                product='USD_M_PERPETUAL_TRADE_KLINES' if r['kind']=='klines' else 'USD_M_PERPETUAL_'+r['kind'])
        ids={}
        for symbol in ('BTCUSDT','ETHUSDT'):
            def chosen(kind,interval,first,last):
                return sorted(k for k,v in files.items() if v['symbol']==symbol and v['kind']==kind and v.get('interval')==interval and first<=v['month']<=last)
            roles=dict(trade_1m=chosen('klines','1m','2024-01','2024-07'),mark_1m=chosen('markPriceKlines','1m','2024-01','2024-07'),
                funding=chosen('fundingRate',None,'2024-01','2024-07'),trade_1d_warmup=chosen('klines','1d','2023-06','2023-12'),
                trade_1d_score=chosen('klines','1d','2024-01','2024-07'),signal_warmup_2h=chosen('klines','2h','2023-12','2023-12'))
            g.check({k:len(v) for k,v in roles.items()}==dict(trade_1m=7,mark_1m=7,funding=7,trade_1d_warmup=7,trade_1d_score=7,signal_warmup_2h=1),'Six complete product/period roles')
            counts={k:sum(files[n]['rows'] for n in names) for k,names in roles.items()}
            g.check(counts['trade_1m']==counts['mark_1m']==306720 and counts['trade_1d_warmup']==214
                and counts['trade_1d_score']==213 and counts['signal_warmup_2h']==372,'Complete new213/warmup calendars')
            ids[symbol]=roles
        window=dict(id='213D',start='2024-01-01T00:00:00+00:00',end_exclusive='2024-08-01T00:00:00+00:00',days=213,
            minutes_per_symbol=306720,daily_warmup_start='2023-06-01T00:00:00+00:00',source_ids=ids,
            symbols={s:dict(source_ids=v,rows_inherited_from_receipts={'funding':sum(files[k]['rows'] for k in v['funding'])}) for s,v in ids.items()},
            initial_completed_daily_warmup_days=214,research_role='SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN')
        manifest=dict(status='PASS_D043_FIXED_213D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS',source_files=files,windows=[window],
            accepted_source_roles=proofs,source_only=True,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,publication_or_exact_charge_certified=False,
            native_Bybit_certified=False,locked_consumed=False,economic_scope='NOT_EVALUATED',
            preceding_547_failure_preserved=True,period_chosen_on_source_completeness_before_new_PnL=True,independent_accounts_no_NAV_stitch=True)
        for name,digest in plan['source_hashes'].items():
            g.check(sha(ROOT/name)==digest,'Frozen source changed '+name)
        g.check(time.monotonic()-start<=120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1_000_000_000,'Root metadata bound')
        input_sha,_=g.write(ROOT/INPUT,manifest)
        report.update(status=STATUS,roles=tasks,verified_prior_files=proofs,actual_archives=72,reused_failed_parent_complete_files=51,new_files=21,
            input_binding_path=INPUT,input_binding_sha256=input_sha,source_hashes=plan['source_hashes'],run_dir=str(run))
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        report.update(elapsed_seconds=time.monotonic()-start,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,created_utc=datetime.now(UTC).isoformat())
        out_sha,_=g.write(ROOT/OUT,report)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=rb['task_id']+':RESULT',event_type='OPERATIONAL_SOURCE_ACCEPTANCE_RESULT',success_failure=report['status'],artifact_path=OUT,artifact_sha256=out_sha))
    if error:raise error
    print(json.dumps(dict(status=report['status'],input_sha256=report['input_binding_sha256'],root_report_sha256=out_sha)))

if __name__=='__main__':main()
