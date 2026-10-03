"""D042 small-metadata close and fixed 547-day input manifest; no price arrays."""
from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, resource, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
LOCK='state/dataset_lock.json'
LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
STATUS='PASS_ROOT_D042_148_NEW_OFFICIAL_HISTORY_SOURCES_AND_547D_INPUT_BINDING_NOT_ECONOMICS'
OUT='reports/fast_research/PERPETUAL_HISTORY_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json'
INPUT='reports/fast_research/PERPETUAL_547D_INPUT_BINDING_20261003_V1.json'
PORTABLE='reports/GITHUB_PERPETUAL_HISTORY_SOURCE_BINDING_20261003_V1.json'

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binding',required=True,type=Path)
    a=p.parse_args(); started=time.monotonic()
    assert sha(ROOT/GUARD)==GUARD_SHA
    spec=importlib.util.spec_from_file_location('history_metadata_guard',ROOT/GUARD)
    g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
    g.check(os.environ.get('COIN_TASK_ID') and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2','Bounded CPU environment')
    plan,plan_sha=g.small(a.binding)
    g.check(a.binding.parent==ROOT/'protocols' and plan['ready_to_execute'] is True
        and plan['checker_sha256']==sha(__file__),'Root-frozen exact checker')
    g.bounded(resources.status())
    g.check(sha(ROOT/LOCK)==LOCK_SHA,'Locked manifest hash only')
    run=Path(plan['run_dir']);g.check(run.parent==STATE and not run.exists(),'Exclusive root STATE')
    g.check(not any((ROOT/name).exists() for name in (OUT,INPUT,PORTABLE)),'Exclusive small outputs')
    run.mkdir(); rb=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=sha(__file__),
        protocol_sha256=plan_sha,protocol_path=str(a.binding.relative_to(ROOT)),source_hashes=plan['source_hashes'],
        command=[sys.executable,*sys.argv],git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    rb_sha,_=g.write(run/'RUN_BINDING.json',rb)
    identity='D042-PERPETUAL-HISTORY-ROOT-20261003-V1'
    event=dict.fromkeys(FIELDS);event.update(experiment_id=identity,event_id=identity+':START',
        event_type='OPERATIONAL_SOURCE_ACCEPTANCE_START',git_commit=rb['git_commit'],protocol_hash=plan_sha,
        data_manifest_hash=plan['roles']['SOURCE']['sha256'],feature_set='NONE_SOURCE_ONLY',labels='NONE',
        model_family='NONE',hyperparameters={'new_archives':148,'reused_daily':12},seed=None,
        thresholds={'days':547,'new_owned_bytes':5_000_000,'wall_seconds':120},cost_assumptions='NOT_EVALUATED',
        all_folds='SEEN_2024JAN_2025JUN_INPUT_ONLY',success_failure='START_BEFORE_ROOT_METADATA_CLOSURE',
        reason_for_next_experiment='Complete fixed common perpetual input before cross-window direction comparison',
        result_influenced_later_choice=False,source_hashes=rb['source_hashes'],exact_command=' '.join(rb['command']),
        run_binding_sha256=rb_sha)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    proofs={}; records={}; tasks={}
    for role,item in plan['roles'].items():
        row,digest=g.small(ROOT/item['path'],item['sha256'])
        g.check(row['status']==item['status'] and row['binding']['task_id']==item['task_id'],'Actual source role identity: '+role)
        tasks[role]=g.closed(item['task_id']);proofs[item['path']]=digest;records[role]=row
    g.check(set(records)=={'METADATA','SOURCE','INDEPENDENT'},'Three actual source roles')
    source=records['SOURCE'];independent=records['INDEPENDENT'];meta=records['METADATA']
    g.check(source['completed_files']==source['required_files']==148 and len(source['sources'])==148
        and meta['completed_files']==meta['required_files']==148 and meta['archive_bodies_downloaded']==0
        and independent['actual_archives']==148
        and independent['actual_report_sha256']==proofs[plan['roles']['SOURCE']['path']]
        and independent['protocol_sha256']==source['binding']['protocol_sha256'],'Complete bound source and independent universe')
    old,old_sha=g.small(ROOT/plan['old_input']['path'],plan['old_input']['sha256'])
    old_root,old_root_sha=g.small(ROOT/plan['old_source_root']['path'],plan['old_source_root']['sha256'])
    g.check(old_root['status']==plan['old_source_root']['status'],'Existing source accepted')
    files={}
    for key,item in old['source_files'].items():
        if key.startswith('trade:1d:') and '2025-01'<=item['month']<='2025-06':
            files[key]=item
    g.check(len(files)==12 and sum(x['rows'] for x in files.values())==362,'Only 12 accepted old daily metadata records')
    audit_items={(r['kind'],r['symbol'],r['month'],r.get('interval')):r for r in independent['sources']}
    audit_keys=set(audit_items)
    for item in source['sources']:
        key=(item['kind'],item['symbol'],item['month'],item.get('interval'))
        g.check(key in audit_keys and audit_items[key]['receipt_sha256']==item['receipt_sha256']
            and audit_items[key]['receipt_path']==item['receipt_path'],'New source receipt independently verified')
        if item['kind']=='klines': name=f"trade:{item['interval']}:{item['symbol']}:{item['month']}"
        else:name=f"{item['kind']}:{item['symbol']}:{item['month']}"
        g.check(name not in files,'Unique product-bound source ID')
        files[name]=dict(item,format_evidence_role='D042_NEW_INDEPENDENT_FORMAT_ONLY',
            product='USD_M_PERPETUAL_TRADE_KLINES' if item['kind']=='klines' else 'USD_M_PERPETUAL_'+item['kind'])
    g.check(len(files)==160 and len(audit_keys)==148,'160 source bindings, old QA not rerun')
    def selected(symbol,kind,interval,first,last):
        prefix=f'trade:{interval}:{symbol}:' if kind=='klines' else f'{kind}:{symbol}:'
        names=sorted(k for k,v in files.items() if k.startswith(prefix) and first<=v['month']<=last)
        return names
    ids={}
    for symbol in ('BTCUSDT','ETHUSDT'):
        ids[symbol]=dict(trade_1m=selected(symbol,'klines','1m','2024-01','2025-06'),
            mark_1m=selected(symbol,'markPriceKlines',None,'2024-01','2025-06'),
            funding=selected(symbol,'fundingRate',None,'2024-01','2025-06'),
            trade_1d_warmup=selected(symbol,'klines','1d','2023-06','2023-12'),
            trade_1d_score=selected(symbol,'klines','1d','2024-01','2025-06'),
            signal_warmup_2h=selected(symbol,'klines','2h','2023-12','2023-12'))
        g.check({k:len(v) for k,v in ids[symbol].items()}==dict(trade_1m=18,mark_1m=18,funding=18,
            trade_1d_warmup=7,trade_1d_score=18,signal_warmup_2h=1),'Fixed complete period role counts')
        g.check(sum(files[k]['rows'] for k in ids[symbol]['trade_1m'])==787680
            and sum(files[k]['rows'] for k in ids[symbol]['mark_1m'])==787680
            and sum(files[k]['rows'] for k in ids[symbol]['trade_1d_warmup'])==214
            and sum(files[k]['rows'] for k in ids[symbol]['trade_1d_score'])==547
            and files[ids[symbol]['signal_warmup_2h'][0]]['rows']==372,'Full minutes and causal warmup counts')
    window=dict(id='547D',start='2024-01-01T00:00:00+00:00',end_exclusive='2025-07-01T00:00:00+00:00',
        days=547,minutes_per_symbol=787680,daily_warmup_start='2023-06-01T00:00:00+00:00',source_ids=ids,
        research_role='SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN',initial_completed_daily_warmup_days=214)
    manifest=dict(status='PASS_D042_FIXED_547D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS',
        source_files=files,windows=[window],accepted_source_roles=proofs,prior_daily_source_root_sha256=old_root_sha,
        prior_input_manifest_sha256=old_sha,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,
        publication_or_exact_charge_certified=False,native_Bybit_certified=False,locked_consumed=False,
        economic_scope='NOT_EVALUATED',same_dates_predeclared_before_new_prices_or_PnL=True)
    input_sha,_=g.write(ROOT/INPUT,manifest)
    verified={**proofs,plan['old_input']['path']:old_sha,plan['old_source_root']['path']:old_root_sha,
        INPUT:input_sha,str(a.binding.relative_to(ROOT)):plan_sha}
    hashes={}
    for name,digest in plan['source_hashes'].items():
        g.small(g.project(name),digest,False);hashes[name]=digest
    g.check(time.monotonic()-started<=120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1_000_000_000,'Root metadata budget')
    result=dict(status=STATUS,binding=rb,run_binding_sha256=rb_sha,roles=tasks,run_dir=str(run),
        actual_new_archives=148,reused_old_daily_files=12,input_binding_path=INPUT,input_binding_sha256=input_sha,
        source_hashes=hashes,verified_prior_files=verified,market_arrays_read=False,old_source_QA_repeated=False,
        investment_candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',orders_sent=0,models_fit=0,GPU=0,
        locked_consumed=False,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,
        local_non_git_hash_guard={LOCK:LOCK_SHA},elapsed_seconds=time.monotonic()-started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    out_sha,_=g.write(ROOT/OUT,result)
    g.write(ROOT/PORTABLE,dict(status='D042_ACTUAL_SOURCE_BYTES_PORTABLE_PENDING_ROOT_EXIT',source_hashes=hashes,
        verified_prior_files={**verified,OUT:out_sha},local_non_git_hash_guard={LOCK:LOCK_SHA},root_task_id=rb['task_id']))
    append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=identity+':RESULT',
        event_type='OPERATIONAL_SOURCE_ACCEPTANCE_RESULT',success_failure=STATUS,artifact_path=OUT,artifact_sha256=out_sha))
    print(json.dumps(dict(status=STATUS,input_sha256=input_sha,root_report_sha256=out_sha)))

if __name__=='__main__':main()
