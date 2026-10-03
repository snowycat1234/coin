"""Only two new July2h files: reuse accepted independent raw/source audit_one.

The two private AST substitutions are the exact2h duration and new conversion
receipt status. No old42 QA, network, trading account or parser is executed.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, importlib.util, json, os, resource, shlex, subprocess, sys, time
from pathlib import Path
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
BASE='docs/archive/PERPETUAL_TRADE_SOURCE_INDEPENDENT_AUDITOR_20261003_V1.py'
BASE_SHA='7770342534d216b121d42da3c541874bb7c175fcd3b10c9939337417760e8e92'
ACTUAL_STATUS='PASS_D041_OFFICIAL_PERPETUAL_2H_JULY_FORMAT_CALENDAR_PENDING_INDEPENDENT_QA'
STATUS='PASS_D041_JULY_2H_RAW_NORMALIZED_CALENDAR_AND_VOLUME_ONLY'
FAIL='FAIL_D041_JULY_2H_INDEPENDENT_SOURCE_QA'
BAR=7_200_000_000
BUDGET=dict(wall_seconds=300,peak_RSS_bytes=512000000,new_owned_bytes=5000000)

def need(ok,message):
    if not bool(ok):raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def base():
    p=ROOT/BASE;need(not p.is_symlink() and sha(p)==BASE_SHA,'Frozen accepted independent raw/source audit')
    spec=importlib.util.spec_from_file_location('d041_july_raw_independent',p);m=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def adapted_audit(b):
    tree=ast.parse((ROOT/BASE).read_bytes());nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='audit_one']
    need(len(nodes)==1,'Unique accepted audit_one');node=nodes[0];text=ast.unparse(node)
    replacements=[("'PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY'","'PASS_D041_2H_ARCHIVE_FORMAT_CALENDAR_ONLY'"),
        ("DAY if entry['interval'] == '1d' else MINUTE",'7200000000')]
    for before,after in replacements:
        need(text.count(before)==1,'Exact single new2h source adaptation '+before);text=text.replace(before,after,1)
    namespace=dict(vars(b));exec(compile(ast.parse(text),'<D041-independent-2h-audit-one>','exec'),namespace)
    return namespace['audit_one'],dict(base_sha256=BASE_SHA,only_substitutions=replacements,
        derived_function_AST_sha256=hashlib.sha256(ast.dump(ast.parse(text),include_attributes=False).encode()).hexdigest())

def entries():
    result=[]
    for symbol in ('BTCUSDT','ETHUSDT'):
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/2h/{symbol}-2h-2025-07.zip'
        result.append(dict(market='futures/um',partition='monthly',kind='klines',interval='2h',symbol=symbol,
            month='2025-07',url=url,checksum_url=url+'.CHECKSUM'))
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    for key in ('protocol','actual','run_dir','output'):setattr(a,key,getattr(a,key).resolve())
    b=base();g=b.guards();audit,derivation=adapted_audit(b)
    need(os.getenv('COIN_TASK_ID') and sys.prefix==str(STATE/'v8-clean-env-20261002-v2') and pl.thread_pool_size()<=2,'Bounded clean CPU2 source audit')
    need(a.run_dir.parent==STATE and a.run_dir.is_dir() and not a.run_dir.is_symlink()
        and {x.name for x in a.run_dir.iterdir()}=={'ACTUAL_BINDING.json'}
        and a.output.parent==ROOT/'reports/fast_research' and not a.output.exists(),'Fresh manifest-only newsource audit')
    plan,plan_sha=g.small(a.run_dir/'ACTUAL_BINDING.json');own=sha(__file__)
    need(plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['protocol_path']==str(a.protocol.relative_to(ROOT))
        and plan['actual_report']==str(a.actual.relative_to(ROOT)) and plan['budgets']==BUDGET,'Exact newsource invocation/budget')
    need(plan['source_hashes'].get(Path(__file__).resolve().relative_to(ROOT).as_posix())==own,'Own independent source explicitly pinned')
    binding=dict(task_id=os.environ['COIN_TASK_ID'],checker_sha256=own,ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(a.actual):plan['actual_report_sha256']},source_hashes=plan['source_hashes'],
        protocol_sha256=plan['protocol_sha256'],exact_command=shlex.join([sys.executable,*sys.argv]),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    g.write(a.run_dir/'RUN_BINDING.json',binding);began=time.monotonic();before=resources.status();rows=[];progress=None;error=None
    report=dict(status=FAIL,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=sha(a.run_dir/'RUN_BINDING.json'),
        independent_source_sha256=own,sources=rows,audit_one_derivation=derivation,source_only=True,
        old42_QA_repeated=False,funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,publication_time_certified=False,
        native_market_or_execution_certified=False,economics='NOT_EVALUATED',candidate_status='NO_QUALIFIED_CANDIDATE',
        models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D041-JULY-2H-INDEPENDENT-20261003-V1',
        event_id=binding['task_id']+':START',event_type='INDEPENDENT_SOURCE_START',git_commit=binding['git_commit'],
        data_manifest_hash=plan['actual_report_sha256'],protocol_hash=plan['protocol_sha256'],
        feature_set='TWO_JULY_2025_USDM_2H_RAW_NORMALIZED',labels='NONE',model_family='NONE',
        hyperparameters={'entries':entries()},seed=None,thresholds=BUDGET,cost_assumptions='NOT_EVALUATED',
        all_folds=['JULY2025_WARMUP_SOURCE_ONLY'],success_failure='START_BEFORE_RAW_OR_PARQUET',
        reason_for_next_experiment='Only two new official2h signal warmup files require independent raw checks',
        result_influenced_later_choice=False,source_hashes=plan['source_hashes'],exact_command=binding['exact_command'])
    report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    try:
        g.bounded(before);spec,proto_sha=g.small(a.protocol,plan['protocol_sha256']);actual,actual_sha=g.small(a.actual,plan['actual_report_sha256'])
        need(spec['contract_id']=='D041_OFFICIAL_PERPETUAL_2H_JULY_SOURCE_V1' and spec['entries']==entries()
            and actual['status']==ACTUAL_STATUS and actual['actual_files']==actual['required_files']==2
            and actual['actual_source_rows']==744 and len(actual['sources'])==2
            and actual['binding']['task_id']==plan['actual_task_id'] and actual['binding']['protocol_sha256']==proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'],'Only two completed fixed July2h archives')
        report['actual_task']=g.closed(plan['actual_task_id']);source_root=Path(spec['run_dir'])
        need(source_root.parent==STATE and source_root.name=='d041-official-perpetual-2h-july-20261003-v1','Exact dedicated source directory')
        rb,rb_sha=g.small(source_root/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Actual producer RUN_BINDING')
        need(plan['source_hashes'].get(BASE)==BASE_SHA and plan['source_hashes'].get(b.GUARD)==b.GUARD_SHA,'Independent original math/guards explicitly bound')
        verified={str(a.protocol.relative_to(ROOT)):proto_sha,str(a.actual.relative_to(ROOT)):actual_sha}
        for path,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
            need(path not in verified or verified[path]==digest,'No conflicting source pin');g.small(g.project(path),digest,False);verified[path]=digest
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(2)
        for item,entry in zip(actual['sources'],entries(),strict=True):
            need({k:item[k] for k in ('symbol','interval','month')}=={k:entry[k] for k in ('symbol','interval','month')},'Exact two archive identities')
            progress.update('仅July新增2h · 原CSV/UTC/量独立核对',len(rows),2,'文件',symbol=entry['symbol'])
            rows.append(audit(g,item,entry,source_root,spec));gc.collect()
            need(rows[-1]['rows']==372 and time.monotonic()-began<=300
                and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=512000000,'Complete fixed372 and processbudget')
        for path,digest in verified.items():g.small(g.project(path),digest,False)
        report.update(status=STATUS,verified_source_hashes=verified,actual_report_sha256=actual_sha,
            actual_run_binding_sha256=rb_sha,completed_files_verified=2,completed_rows_verified=744,
            rows_per_symbol=372,all_raw_normalized_values_equal=True,full_CSV_EOF_and_CRC_read=True)
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        report.update(completed_files_verified=len(rows),elapsed_seconds=time.monotonic()-began,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            resources_before=before,resources_after=resources.status(),own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
        try:g.bounded(report['resources_after'])
        except Exception as caught:error=error or caught;report['budget_error']=str(caught)
        if report['elapsed_seconds']>300 or report['peak_RSS_bytes']>512000000:error=error or RuntimeError('Fixed newsource audit budget')
        if error:report['status']=FAIL
        digest,size=g.write(a.output,report);need(sum(p.stat().st_size for p in a.run_dir.iterdir() if p.is_file())+size<=5000000,'Small source-audit metadata only')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=binding['task_id']+':RESULT',
            event_type='INDEPENDENT_SOURCE_RESULT',success_failure=report['status'],
            artifact_path=str(a.output.relative_to(ROOT)),artifact_sha256=digest))
        print(json.dumps(dict(status=report['status'],sha256=digest,completed_files=len(rows))),flush=True)
    if error:raise error

if __name__=='__main__':main()
