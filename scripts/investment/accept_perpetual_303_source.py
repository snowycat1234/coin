"""UNRUN D045 metadata-only ROOT closure; no payload open/hash or source QA.
CLI --binding ROOT frozen ready plan --run-dir fresh STATE.
Plan: ready_to_execute/checker_sha256/source_hashes/source_protocol{path,sha256,
required_contract}/roles SOURCE,INDEPENDENT{path,sha256,status,task_id}/run_dir/budgets.
Root owns freeze/start; no PASS output until two true distinct closed0 roles.
"""
from __future__ import annotations
import argparse,hashlib,importlib.util,json,os,resource,shlex,subprocess,sys,time
from datetime import UTC,datetime
from pathlib import Path
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
LOCK='state/dataset_lock.json';LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
STATUS='PASS_ROOT_D045_COMPLETE_303_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS'
QA_STATUS='PASS_D045_94_SOURCE_COVERAGE_70_FIRST_QA_24_ACCEPTED_REUSE_NOT_UNIT_OR_ECONOMICS'
SOURCE_STATUS='PASS_D045_94_HISTORY_FORMAT_54_REUSED_40_NEW_PENDING_INDEPENDENT_QA'
SOURCE_CONTRACT='D045_FIXED_303D_MIXED_OWNER_OFFICIAL_SOURCE_V1'
INPUT='reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json'
INPUT_STATUS='PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'
OUT='reports/fast_research/PERPETUAL_303_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json'
BUDGET=dict(new_owned_bytes=5_000_000,peak_RSS_bytes=1_000_000_000,wall_seconds=120)
PRIOR={
 'reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json':('82cae26a2313417c59e6a63af8458d775851e7c1e341d51bc9e7fa9a2cf6c427','FAIL_D042_HISTORY_SOURCE'),
 'reports/fast_research/PERPETUAL_HISTORY_METADATA_ACTUAL_20261003_V1.json':('cbfde5a12c27613666ef5d45a71963000a6b0b0e5e6f3fcef6cf0227e70101bf','PASS_D042_148_OFFICIAL_HISTORY_METADATA_ONLY'),
 'reports/fast_research/PERPETUAL_213_SOURCE_ACTUAL_20261003_V1.json':('3e03d1eaad434a32219d1e2a03c3dcbacdafc923419740f5f8f20bedfbb06ca9','PASS_D043_72_HISTORY_FORMAT_PENDING_FULL_INDEPENDENT_QA'),
 'reports/fast_research/PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json':('dc193b2df35dda8dc011895bc9d973946321931f304ad112266b5ccf1f8090ef','PASS_D043_72_MIXED_OWNER_213D_USDM_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS'),
 'reports/fast_research/PERPETUAL_213_SOURCE_ROOT_ACCEPTANCE_20261003_V1.json':('795667026b7eb50ab08f1c5b07254eb2002591549b792aa4685439a2d82cc823','PASS_ROOT_D043_COMPLETE_213_USDM_SOURCE_NOT_UNIT_OR_ECONOMICS'),
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_ACTUAL_20261003_V1.json':('2e067443a79cebcb7b304e451130fc7c14cc62903a335f9a5742c5de859f0615','PASS_USDM_TRADE_KLINE_FORMAT_CALENDAR_PENDING_INDEPENDENT_ACCEPTANCE'),
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_INDEPENDENT_QA_20261003_V2.json':('99d918102e825324d678037d39648081e6aa16fd2c1a1f89cf8a4c11660492fb','PASS_NEW_USDM_TRADE_SOURCE_RAW_NORMALIZED_CALENDAR_VOLUME_ONLY'),
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_ROOT_ACCEPTANCE_20261003_V4.json':('f8f6d2e49c320ecc5f61506ffd291ac1c94af0b80803baa6b8e4210741a1f95d','PASS_NEW_PERPETUAL_TRADE_SOURCE_ROOT_METADATA_CLOSURE'),
 'reports/fast_research/PERPETUAL_TRADE_SOURCE_METADATA_20261003_V1.json':('b03187a50bafe29df7e285a372547d44bf440f0be13b44a03a5f4ed0a2b4b400',None)}
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def key(r):return r.get('kind','klines'),r['symbol'],r.get('interval'),r['month']
def months(first,last):
    y,m=map(int,first.split('-'));end=tuple(map(int,last.split('-')));out=[]
    while (y,m)<=end:
        out.append(f'{y:04d}-{m:02d}');m+=1
        if m==13:y+=1;m=1
    return out
def universe():
    return {(kind,symbol,interval,month) for kind,interval,first in [('klines','1m','2024-09'),('klines','1d','2024-02'),('markPriceKlines','1m','2024-09'),('fundingRate',None,'2024-09')] for symbol in ('BTCUSDT','ETHUSDT') for month in months(first,'2025-06')}
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('binding','run-dir'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();args.binding=args.binding.absolute();run=args.run_dir.absolute()
    if sha(ROOT/GUARD)!=GUARD_SHA:raise ValueError('Exact existing metadata guard')
    loader=importlib.util.spec_from_file_location('_d045_root_guard',ROOT/GUARD);g=importlib.util.module_from_spec(loader);loader.loader.exec_module(g)
    plan,ph=g.small(args.binding);own=sha(__file__);task=os.environ.get('COIN_TASK_ID')
    g.check(args.binding.parent==ROOT/'protocols' and plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['budgets']==BUDGET,'Ready frozen root plan')
    g.check(task and run==Path(plan['run_dir']) and run.parent==STATE and run.name.startswith('d045-') and not run.exists() and sys.prefix==str(STATE/'v8-clean-env-20261002-v2'),'Fresh bounded root task')
    g.check(not (ROOT/OUT).exists() and not (ROOT/INPUT).exists(),'Exclusive new root/input receipts')
    hashes=dict(plan['source_hashes']);g.check(hashes.get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own and hashes.get(GUARD)==GUARD_SHA and hashes.get(LOCK)==LOCK_SHA,'Own/guard/private lock pinned')
    for name,digest in hashes.items():
        if name==LOCK:g.check(sha(g.project(name))==digest,'Private lock streamed SHA only')
        else:g.small(g.ordinary(ROOT/name) if name=='docs/OPEN_SOURCE_REGISTRY.md' else g.project(name),digest,False)
    run.mkdir();started=time.monotonic();before=resources.status();g.bounded(before)
    rb=dict(task_id=task,source_sha256=own,source_hashes=dict(hashes),binding_path=str(args.binding),binding_sha256=ph,exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    rh,_=g.write(run/'RUN_BINDING.json',rb);error=None;input_sha=None
    result=dict(status='FAIL_ROOT_D045_303_SOURCE',binding=rb,run_dir=str(run),run_binding_sha256=rh,source_only=True,market_arrays_read=False,market_payload_hashing=False,source_QA_repeated=False,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,native_Bybit_certified=False,publication_or_exact_charge_certified=False,economics='NOT_EVALUATED',candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE',models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,local_non_git_hash_guard={LOCK:LOCK_SHA})
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D045-303-SOURCE-ROOT-20261003-V1',event_id=task+':START',event_type='OPERATIONAL_SOURCE_ACCEPTANCE_START',git_commit=rb['git_commit'],protocol_hash=ph,data_manifest_hash=plan['roles']['SOURCE']['sha256'],feature_set='94_SOURCE_70_FIRST_QA_24_REUSED_CAPABILITIES',labels='NONE',model_family='NONE',seed=None,success_failure='START_BEFORE_ROOT_METADATA',source_hashes=dict(hashes),exact_command=rb['exact_command'],thresholds=BUDGET)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    try:
        g.check(set(plan['roles'])=={'SOURCE','INDEPENDENT'},'Two real source/independent roles');records={};tasks={};proofs={};priors={}
        for role,item in plan['roles'].items():
            r,h=g.small(g.project(item['path']),item['sha256']);g.check(r['status']==item['status'] and r['binding']['task_id']==item['task_id'],'Exact role status/task '+role)
            records[role]=r;proofs[item['path']]=h;tasks[role]=g.closed(item['task_id'])
        source,qa=records['SOURCE'],records['INDEPENDENT'];g.check(tasks['SOURCE']['task']['id']!=tasks['INDEPENDENT']['task']['id'] and tasks['INDEPENDENT']['task']['started_at']>=tasks['SOURCE']['task']['ended_at'],'Actually distinct sequential QA')
        sr=plan['source_protocol'];spec,sph=g.small(g.project(sr['path']),sr['sha256']);proofs[sr['path']]=sph
        g.check(spec['contract_id']==sr['required_contract']==SOURCE_CONTRACT and spec['score_period_start']=='2024-09-01' and spec['score_period_end_exclusive']=='2025-07-01','Fixed complete303 source-only dates')
        g.check(len(spec['entries'])==94 and {key(e) for e in spec['entries']}==universe() and spec['required_files']==94 and spec['expected_reused_files']==54 and spec['expected_new_files']==40,'Exact94 selectors54/40 no2h/index/Aug score')
        g.check(source['status']==SOURCE_STATUS and source['completed_files']==source['required_files']==len(source['sources'])==94 and source['reused_completed_files']==54 and source['new_completed_files']==40 and source['archive_bodies_downloaded']==40 and source['binding']['protocol_sha256']==sph and source['binding']['source_hashes']==spec['frozen_sources'],'Complete94 actual producer binding')
        g.check(qa['status']==QA_STATUS and qa['completed_files_verified']==qa['actual_archives']==94 and qa['first_independent_QA_files']==70 and qa['reused_accepted_QA_files']==24 and qa['actual_report_sha256']==plan['roles']['SOURCE']['sha256'] and qa['protocol_sha256']==sph and qa['actual_run_binding_sha256']==source['run_binding_sha256'],'Exact first70/reused24 independent coverage')
        g.check(qa['actual_task']['task']['id']==tasks['SOURCE']['task']['id'] and len(qa['accepted_capability_proofs'])==2 and len(qa['owner_proofs'])==3,'QA real producer/capability/owner proofs')
        expected_owners={str(STATE/'d042-perpetual-history-source-20261003-v1'),str(STATE/'perpetual-trade-source-actual-20261003-v1'),spec['run_dir']}
        g.check({p['run_dir'] for p in qa['owner_proofs']}==expected_owners,'Only three physical owners; D043 is capability only')
        for p in qa['owner_proofs']:
            closed=g.closed(p['task_id'],1 if p['run_dir'].endswith('d042-perpetual-history-source-20261003-v1') else 0)
            g.check(closed==p['actual_task'],'Exact current closed owner task, failed owner not upgraded')
        for report in (source,qa):g.check(report['funding_rate_unit']=='UNCONFIRMED' and report['funding_unit_certified'] is False and report['locked_consumed'] is False,'No unit/locked promotion')
        g.check(source['models_fit']==source['orders_sent']==source['GPU']==0 and source['source_only'] is True,'No financial run')
        actual_rb,_=g.small(Path(spec['run_dir'])/'RUN_BINDING.json',source['run_binding_sha256']);g.check(actual_rb==source['binding'],'Exact source RUN_BINDING')
        qa_rb,_=g.small(Path(qa['run_dir'])/'RUN_BINDING.json',qa['run_binding_sha256']);g.check(qa_rb==qa['binding'],'Exact independent RUN_BINDING')
        for name,(digest,status) in PRIOR.items():
            prior,_=g.small(g.project(name),digest);g.check(status is None or prior['status']==status,'Preserved prior status '+name);priors[name]=prior;proofs[name]=digest
        failed=priors['reports/fast_research/PERPETUAL_HISTORY_SOURCE_ACTUAL_20261003_V1.json'];g.check(failed['completed_files']==83 and failed['required_files']==148 and failed['source_acceptance_granted'] is False,'Failed547 remains failed')
        qrows={key(r):r for r in qa['sources']};g.check(len(qrows)==94 and set(qrows)==universe(),'94 distinct independently covered files');files={};owner_counts={};new_count=0
        for item in source['sources']:
            k=key(item);v=qrows[k];g.check(k in universe() and v['receipt_path']==item['receipt_path'] and v['receipt_sha256']==item['receipt_sha256'] and v['normalized_path']==item['normalized_path'] and v['normalized_sha256']==item['normalized_sha256'] and v['rows']==item['rows'] and v['owner_run_dir']==item['source_owner_path'],'Exact source/QA aliases, never reread payload')
            owner=item['source_owner_path'];g.check(Path(item['receipt_path']).parent.parent==Path(owner) and Path(item['normalized_path']).parent.parent==Path(owner),'Original mixed source owner');owner_counts[owner]=owner_counts.get(owner,0)+1;new_count+=owner==spec['run_dir']
            name=f"trade:{k[2]}:{k[1]}:{k[3]}" if k[0]=='klines' else f"{k[0]}:{k[1]}:{k[3]}";g.check(name not in files,'Unique source ID')
            files[name]=dict(item,format_evidence_role=v['QA_scope'],independent_QA_report_path=plan['roles']['INDEPENDENT']['path'],independent_QA_report_sha256=plan['roles']['INDEPENDENT']['sha256'],prior_QA=v.get('prior_QA'),product='USD_M_PERPETUAL_TRADE_KLINES' if k[0]=='klines' else 'USD_M_PERPETUAL_'+k[0])
        g.check(new_count==40 and len(files)-new_count==54 and owner_counts=={str(STATE/'d042-perpetual-history-source-20261003-v1'):42,str(STATE/'perpetual-trade-source-actual-20261003-v1'):12,spec['run_dir']:40},'Real54 reuse/40new ownership')
        g.check(sum(v['rows'] for v in files.values())==qa['completed_rows_verified']==source['actual_source_rows'] and all(c['passed'] is True for c in qa['crossmonth']) and len(qa['crossmonth'])==8,'Saved rows and all eight crossmonth scopes complete')
        ids={}
        for symbol in ('BTCUSDT','ETHUSDT'):
            def selected(kind,interval,first,last):return sorted(n for n,v in files.items() if v['symbol']==symbol and v['kind']==kind and v.get('interval')==interval and first<=v['month']<=last)
            roles=dict(trade_1m=selected('klines','1m','2024-09','2025-06'),mark_1m=selected('markPriceKlines','1m','2024-09','2025-06'),funding=selected('fundingRate',None,'2024-09','2025-06'),trade_1d_warmup=selected('klines','1d','2024-02','2024-08'),trade_1d_score=selected('klines','1d','2024-09','2025-06'))
            g.check({k:len(v) for k,v in roles.items()}==dict(trade_1m=10,mark_1m=10,funding=10,trade_1d_warmup=7,trade_1d_score=10),'Five complete roles, no2h')
            counts={k:sum(files[n]['rows'] for n in ns) for k,ns in roles.items()};g.check(counts['trade_1m']==counts['mark_1m']==436320 and counts['trade_1d_warmup']==213 and counts['trade_1d_score']==303,'Full303 and213dailywarmup source counts');ids[symbol]=roles
        window=dict(id='303D',start='2024-09-01T00:00:00+00:00',end_exclusive='2025-07-01T00:00:00+00:00',days=303,minutes_per_symbol=436320,daily_warmup_start='2024-02-01T00:00:00+00:00',initial_completed_daily_warmup_days=213,source_ids=ids,symbols={s:dict(source_ids=v,rows_inherited_from_receipts={'funding':sum(files[n]['rows'] for n in v['funding'])}) for s,v in ids.items()},research_role='SEEN_DEVELOPMENT_SCREENING_NOT_UNSEEN')
        manifest=dict(status=INPUT_STATUS,binding=rb,source_files=files,windows=[window],accepted_source_roles=proofs,source_only=True,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,publication_or_exact_charge_certified=False,native_Bybit_certified=False,locked_consumed=False,economic_scope='NOT_EVALUATED',preceding_547_failure_preserved=True,source_rows_repaired=False,period_chosen_on_source_completeness_before_new_PnL=True,independent_accounts_no_NAV_stitch=True,first_QA_files=70,reused_accepted_QA_files=24)
        for name,digest in hashes.items():
            if name==LOCK:g.check(sha(g.project(name))==digest,'Private lock streamed SHA only')
            else:g.small(g.ordinary(ROOT/name) if name=='docs/OPEN_SOURCE_REGISTRY.md' else g.project(name),digest,False)
        after=resources.status();g.bounded(after);g.check(time.monotonic()-started<=120 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1_000_000_000,'Root metadata resources')
        input_sha,input_bytes=g.write(ROOT/INPUT,manifest);result.update(status=STATUS,roles=tasks,verified_prior_files=proofs,actual_archives=94,reused_original_producer_files=54,new_files=40,first_QA_files=70,reused_accepted_QA_files=24,owner_file_counts=owner_counts,input_binding_path=INPUT,input_binding_sha256=input_sha,input_binding_bytes=input_bytes,source_hashes=dict(hashes),independent_source_rows=qa['completed_rows_verified'],actual_funding_events=qa['funding_event_count'])
    except Exception as caught:error=caught;result['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        result.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_before=before,resources_after=resources.status(),created_utc=datetime.now(UTC).isoformat())
        out_sha,out_bytes=g.write(ROOT/OUT,result);append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='OPERATIONAL_SOURCE_ACCEPTANCE_RESULT',success_failure=result['status'],artifact_path=OUT,artifact_sha256=out_sha))
        g.check(sum(p.stat().st_size for p in run.iterdir() if p.is_file())+out_bytes+(result.get('input_binding_bytes') or 0)<=5_000_000,'Owned metadata5MB')
    if error:raise error
    print(json.dumps(dict(status=result['status'],input_sha256=input_sha,root_report_sha256=out_sha)))
if __name__=='__main__':main()
