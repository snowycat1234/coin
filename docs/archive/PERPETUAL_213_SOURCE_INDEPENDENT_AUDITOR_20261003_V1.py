"""UNRUN D043 only72 mixed-owner source QA entry; no financial execution.

CLI --protocol ROOT-independent-binding --actual producer-report --run-dir --output.
Root binding is copied byte-for-byte to run-dir/ACTUAL_BINDING.json. Fields:
ready_to_execute, checker_sha256, helper{path,sha256}, source_spec{path,sha256,
required_contract}, actual_source{path,sha256,task_id,required_status},
owner_bindings[2]{run_dir,report_path,report_sha256,task_id,exit_code,required_status},
frozen_sources, budgets{peak_RSS_bytes,wall_seconds,new_owned_bytes}.

The source/producer schema bridge still needs root's static final review.
This file and helpers have not been compiled or run; no payload was read.
"""
from __future__ import annotations
import argparse, gc, hashlib, importlib.util, json, os, resource, shlex, subprocess, sys, time
from pathlib import Path
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA='278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
STATUS='PASS_D043_72_MIXED_OWNER_213D_USDM_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS'
FAIL='FAIL_D043_72_MIXED_OWNER_SOURCE_INDEPENDENT_QA'
FORMAT='scripts/investment/audit_perpetual_history_source.py'
FORMAT_SHA='7e333eb672978409bcd6a469ea14998e209edeefb3ced4562dc43cccfc87ee6b'
BUDGET=dict(peak_RSS_bytes=1_000_000_000,wall_seconds=1200,new_owned_bytes=5_000_000)
RUN=STATE/'d043-perpetual-213-independent-20261003-v1'
OUT=ROOT/'reports/fast_research/PERPETUAL_213_SOURCE_INDEPENDENT_20261003_V1.json'

def need(ok,message):
    if not bool(ok):raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def load(path,digest,name):
    p=Path(path);need(p.is_file() and not p.is_symlink() and sha(p)==digest,'Exact pinned independent helper')
    spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec)
    sys.modules[name]=m;spec.loader.exec_module(m);return m

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    for key in ('protocol','actual','run_dir','output'):setattr(a,key,getattr(a,key).absolute())
    g=load(ROOT/GUARD,GUARD_SHA,'d043_source_metadata_guards');own=sha(__file__);task=os.getenv('COIN_TASK_ID')
    need(task and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Bounded clean CPU2 progress runtime')
    need(a.protocol.parent==ROOT/'protocols' and a.actual.parent==ROOT/'reports/fast_research'
        and a.run_dir==RUN and a.run_dir.is_dir() and not a.run_dir.is_symlink()
        and {f.name for f in a.run_dir.iterdir()}=={'ACTUAL_BINDING.json'} and a.output==OUT and not OUT.exists(),
        'Exclusive ROOT binding / manifest-only new independent STATE / report')
    root_plan,proto_sha=g.small(a.protocol);plan,manifest_sha=g.small(RUN/'ACTUAL_BINDING.json')
    need(plan==root_plan and manifest_sha==proto_sha and plan['ready_to_execute'] is True
        and plan['checker_sha256']==own and plan['budgets']==BUDGET,'Exact byte-copied ready root binding and audit budgets')
    binding=dict(task_id=task,checker_sha256=own,ACTUAL_BINDING_sha256=manifest_sha,protocol_sha256=proto_sha,
        source_hashes=plan['frozen_sources'],actual_reports={str(a.actual):plan['actual_source']['sha256']},
        exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    g.write(RUN/'RUN_BINDING.json',binding);started=time.monotonic();before=resources.status();rows=[];error=None;progress=None
    report=dict(status=FAIL,binding=binding,run_dir=str(RUN),run_binding_sha256=sha(RUN/'RUN_BINDING.json'),
        independent_source_sha256=own,sources=rows,source_only=True,source_rows_repaired=False,
        failed_full547_parent_remains_failed=True,unselected_old83_QA_repeated=False,
        price_financial_replay=False,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,
        publication_time_certified=False,native_market_or_execution_certified=False,economics='NOT_EVALUATED',
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,candidate_status='NO_QUALIFIED_CANDIDATE')
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D043-213D-MIXED-SOURCE-INDEPENDENT-20261003-V1',
        event_id=task+':START',event_type='INDEPENDENT_SOURCE_START',git_commit=binding['git_commit'],
        data_manifest_hash=plan['actual_source']['sha256'],protocol_hash=proto_sha,feature_set='ONLY_FIXED_72_SOURCE_ARCHIVES_213D',
        labels='NONE',model_family='NONE',seed=None,thresholds=BUDGET,cost_assumptions='NOT_EVALUATED',
        all_folds='2024JAN_JUL_SOURCE_ONLY_AND_REQUIRED_WARMUP',success_failure='START_BEFORE_RAW_OR_PARQUET',
        reason_for_next_experiment='First independent QA of explicit51 preserved-complete plus21 newly needed files',
        result_influenced_later_choice=False,source_hashes=plan['frozen_sources'],exact_command=binding['exact_command'])
    report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    def budget():
        need(time.monotonic()-started<=1200 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=1_000_000_000,'Frozen1200s/RSS1GB independent QA')
    try:
        g.bounded(before)
        need(plan['frozen_sources'].get(GUARD)==GUARD_SHA and plan['frozen_sources'].get(FORMAT)==FORMAT_SHA
            and plan['frozen_sources'].get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own,'Own/format/guard code explicitly frozen')
        for path,digest in plan['frozen_sources'].items():
            f=g.project(path)
            if path=='state/dataset_lock.json':need(sha(f)==digest,'Private scientific lock hash-only, no JSON/body')
            else:g.small(f,digest,False)
        helper_ref=plan['helper'];need(plan['frozen_sources'].get(helper_ref['path'])==helper_ref['sha256'],'Original mixed-owner helper pinned')
        h=load(g.project(helper_ref['path']),helper_ref['sha256'],'d043_213_mixed_owner_reuse')
        source_ref=plan['source_spec'];spec,source_proto_sha=g.small(g.project(source_ref['path']),source_ref['sha256'])
        need(spec['contract_id']==source_ref['required_contract'],'Exact new213 source contract')
        expected={h.identity(e):e for e in h.source_entries()}
        need(len(spec['entries'])==72 and len({h.identity(e) for e in spec['entries']})==72
            and {h.identity(e) for e in spec['entries']}==set(expected)
            and all(all(e.get(k)==v for k,v in expected[h.identity(e)].items()) for e in spec['entries']),
            'Fixed72 official selectors/URLs; cannot silently skip dates')
        actual_ref=plan['actual_source'];need(a.actual.relative_to(ROOT).as_posix()==actual_ref['path'],'Exact new actual source report')
        actual,actual_sha=g.small(a.actual,actual_ref['sha256'])
        need(actual['status']==actual_ref['required_status'] and actual['completed_files']==actual['required_files']==72
            and actual.get('actual_files',72)==72 and len(actual['sources'])==72
            and actual['binding']['task_id']==actual_ref['task_id'] and actual['binding']['protocol_sha256']==source_proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'],'True completed new72 source task and immutable dependencies')
        need(actual['funding_unit_certified'] is False and actual['funding_rate_unit']=='UNCONFIRMED'
            and actual['locked_consumed'] is False and actual['orders_sent']==actual['models_fit']==actual['GPU']==0,
            'No unit/native/economic/model/locked promotion')
        report['actual_task']=g.closed(actual_ref['task_id'])
        producer_run=Path(spec['run_dir']);need(producer_run.parent==STATE,'Explicit new producer directory')
        rb,rb_sha=g.small(producer_run/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Actual producer RUN_BINDING identity')
        for path,digest in spec['frozen_sources'].items():
            need(path in plan['frozen_sources'] and plan['frozen_sources'][path]==digest,'No unpinned or changed producer dependency')
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(72)
        computed=h.qa_72(actual['sources'],plan['owner_bindings'],spec,results=rows,progress=progress,check_budget=budget)
        need(sum(r['rows'] for r in rows)==actual['actual_source_rows'],'All original source rows match actual72 catalogue')
        for path,digest in plan['frozen_sources'].items():
            f=g.project(path)
            if path=='state/dataset_lock.json':need(sha(f)==digest,'Private lock hash unchanged')
            else:g.small(f,digest,False)
        report.update(computed);report.update(status=STATUS,actual_report_sha256=actual_sha,protocol_sha256=source_proto_sha,
            independent_protocol_sha256=proto_sha,actual_run_binding_sha256=rb_sha,
            verified_source_hashes=plan['frozen_sources'],completed_files_verified=72,actual_archives=72,
            price_rows=sum(r['rows'] for r in rows if r['kind']!='fundingRate'),
            source_fingerprint_portability='EXACT_SAVED_FILES_NOT_RESERIALIZED_FRAMES')
        budget()
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        gc.collect();report.update(completed_files_verified=len(rows),actual_archives=len(rows),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_before=before,resources_after=resources.status(),own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after']);budget()
        except Exception as caught:error=error or caught;report['budget_error']=str(caught)
        if error:report['status']=FAIL
        digest,size=g.write(OUT,report)
        need(sum(p.stat().st_size for p in RUN.iterdir() if p.is_file())+size<=5_000_000,'Metadata-only independent5MB budget')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='INDEPENDENT_SOURCE_RESULT',
            success_failure=report['status'],artifact_path=OUT.relative_to(ROOT).as_posix(),artifact_sha256=digest))
        print(json.dumps(dict(status=report['status'],sha256=digest,completed_files=len(rows),task_id=task)),flush=True)
    if error:raise error

if __name__=='__main__':main()
