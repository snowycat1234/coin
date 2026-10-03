"""D042 independent new148 archive QA; prepared without executing any payload.

Reuse the accepted trade audit_one (only a private 2h duration extension) and
the unchanged funding/mark audit_one. Never run their old main, a producer
parser, network request, old12 daily QA, strategy or financial account.
Root freezes ACTUAL_BINDING after the new producer really completes zero.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, importlib.util, json, os, resource, shlex, subprocess, sys, time, zipfile
from datetime import UTC, datetime
from pathlib import Path
import polars as pl
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
TRADE='docs/archive/PERPETUAL_TRADE_SOURCE_INDEPENDENT_AUDITOR_20261003_V1.py'
FUND='scripts/research_v8/audit_funding_price_source.py'
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
PINS={TRADE:'7770342534d216b121d42da3c541874bb7c175fcd3b10c9939337417760e8e92',
    FUND:'edf2b7e8f7f74e392c422a126ae11d3755f915d11984b50014aa44df54dcd79c',
    GUARD:'278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a',
    'scripts/research_v8/funding_price_source_v2.py':'2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb',
    'scripts/research_v7/oracle_flow_ceiling.py':'959f63f40c3294b6b2b75267b9138202df79223a7e7723397cf06b8d45a1477e',
    'scripts/research_v8/registry.py':'081f881f2cb1cdc84b8c098606e9f3235c92fcdd04c0120527bee0d8493068ab',
    'src/quant/resources.py':'e8028c40240bfb0df05228247ad6fee734831a14b9c6ac40acbd0c291b1969a3',
    'src/quant/paths.py':'3c3e43ddd9ef1f2a52f902869d29e9a0ac5f29f1b5e64362b873290d07f72282'}
CONTRACT='D042_OFFICIAL_PERPETUAL_HISTORY_SOURCE_V1'
ACTUAL_STATUS='PASS_D042_148_HISTORY_FORMAT_PENDING_INDEPENDENT_QA'
STATUS='PASS_D042_NEW_148_OFFICIAL_USDM_HISTORY_FORMAT_CALENDAR_ONLY_NOT_UNIT_OR_ECONOMICS'
FAIL='FAIL_D042_NEW_148_INDEPENDENT_SOURCE_QA'
BUDGET=dict(peak_RSS_bytes=1_000_000_000,wall_seconds=1200,new_owned_bytes=5_000_000)
SOURCE_BUDGET=dict(new_owned_bytes=1_000_000_000,max_archive_bytes=16_000_000,file_write_limit_bytes=32_000_000,
    max_csv_bytes=128_000_000,peak_RSS_bytes=1_000_000_000,file_seconds=30,wall_seconds=1800)
MINUTE,DAY,BAR=60_000_000,86_400_000_000,7_200_000_000

def need(ok,message):
    if not bool(ok):raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def load(name):
    path=ROOT/name;need(not path.is_symlink() and sha(path)==PINS[name],'Exact accepted helper: '+name)
    spec=importlib.util.spec_from_file_location('d042_'+Path(name).stem,path)
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    return module

def pin(g,name,digest):
    path=g.project(name)
    if name=='state/dataset_lock.json':
        need(sha(path)==digest,'Private scientific lock streamed SHA only; no JSON/body export')
    else:g.small(path,digest,False)

def trade_audit(module):
    nodes=[n for n in ast.parse((ROOT/TRADE).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='audit_one']
    need(len(nodes)==1,'Unique accepted trade audit_one');text=ast.unparse(nodes[0])
    before="DAY if entry['interval'] == '1d' else MINUTE"
    after="DAY if entry['interval'] == '1d' else 7200000000 if entry['interval'] == '2h' else MINUTE"
    need(text.count(before)==1,'Exact sole new2h duration anchor');text=text.replace(before,after,1)
    namespace=dict(vars(module));exec(compile(ast.parse(text),'<D042-private-trade-audit-one>','exec'),namespace)
    return namespace['audit_one'],dict(base_sha256=PINS[TRADE],only_substitution=[before,after],
        derived_function_AST_sha256=hashlib.sha256(ast.dump(ast.parse(text),include_attributes=False).encode()).hexdigest())

def months(first,last):
    year,month=map(int,first.split('-'));end=tuple(map(int,last.split('-')));out=[]
    while (year,month)<=end:
        out.append(f'{year:04d}-{month:02d}');month+=1
        if month==13:year+=1;month=1
    return out

def entries():
    result=[]
    for kind,interval,first,last in [('klines','1m','2024-01','2025-06'),('klines','1d','2023-06','2024-12'),
        ('klines','2h','2023-12','2023-12'),('markPriceKlines','1m','2024-01','2025-06'),('fundingRate',None,'2024-01','2025-06')]:
        for symbol in ('BTCUSDT','ETHUSDT'):
            for month in months(first,last):
                suffix=f'{symbol}-fundingRate-{month}.zip' if interval is None else f'{interval}/{symbol}-{interval}-{month}.zip'
                url=f'https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{suffix}'
                item=dict(market='futures/um',partition='monthly',kind=kind,symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM')
                if interval is not None:item['interval']=interval
                result.append(item)
    return result

def identity(item):return item['kind'],item['symbol'],item.get('interval'),item['month']

def exact_entries(actual):
    expected={identity(e):e for e in entries()}
    need(len(actual)==len(expected)==148 and len({identity(e) for e in actual})==148,'Exactly148 distinct new archive identities')
    for entry in actual:
        need(identity(entry) in expected and all(entry.get(k)==v for k,v in expected[identity(entry)].items()),'Fixed official URL/product/interval universe')
    return expected

def proxy_audit(g,b,f,item,entry,source_root,spec):
    # Extra path/bounds before unchanged funding/mark audit_one can read payloads.
    receipt_path=Path(item['receipt_path']);job=receipt_path.parent
    need(job==source_root/f"{entry['kind']}-{entry['symbol']}-{entry['month']}"
        and receipt_path.name=='receipt.json','One exact new proxy archive directory')
    receipt,_=g.small(receipt_path,item['receipt_sha256'])
    need(all(receipt['entry'].get(k)==v for k,v in entry.items()),'Exact new mark/funding receipt entry')
    need(receipt['status']=='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA','Completed new proxy conversion')
    aliases=dict(normalized_path=receipt['parquet_path'],normalized_sha256=receipt['parquet_sha256'],
        normalized_bytes=receipt['parquet_bytes'],rows=receipt['stats']['rows'],stats=receipt['stats'],normalized_schema=receipt['stats']['schema'])
    need(all(item[k]==v for k,v in aliases.items()) and item['entry']==receipt['entry'],
        'Published proxy normalized aliases/rows/stats/schema and original receipt agree before payload read')
    budget=spec['budgets'];parquet=Path(receipt['parquet_path'])
    need(parquet==job/'source.parquet','Exact new proxy normalized path')
    b.payload(parquet,job,receipt['parquet_sha256'],budget['file_write_limit_bytes'],receipt['parquet_bytes'])
    archive=b.payload(receipt['zip_path'],job,receipt['zip_sha256'],budget['max_archive_bytes'],receipt['entry']['announced_zip_bytes'])
    b.payload(receipt['checksum_path'],job,receipt['checksum_sha256'],65_536)
    name=entry['url'].rsplit('/',1)[1]
    need(archive.name==name and Path(receipt['checksum_path']).name==name+'.CHECKSUM','Exact official proxy filenames')
    with zipfile.ZipFile(archive) as z:
        members=z.infolist();need(len(members)==1 and members[0].filename==name[:-4]+'.csv'
            and not members[0].is_dir() and not members[0].flag_bits&1
            and 0<members[0].file_size==receipt['uncompressed_csv_bytes']<=budget['max_csv_bytes'],'One bounded new proxy CSV, no extraction')
    result=f.audit_one(receipt,spec)
    need(sha(parquet)==receipt['parquet_sha256'] and sha(archive)==receipt['zip_sha256']
        and sha(receipt['checksum_path'])==receipt['checksum_sha256'],'Proxy bytes unchanged during independent read')
    result.update(normalized_path=str(parquet),normalized_sha256=receipt['parquet_sha256'],
        zip_sha256=receipt['zip_sha256'],checksum_sha256=receipt['checksum_sha256'])
    return result

def crossmonth(rows,tolerance):
    checks=[];totals={}
    for symbol in ('BTCUSDT','ETHUSDT'):
        for kind,interval,count in [('klines','1m',787680),('klines','1d',580),('klines','2h',372),('markPriceKlines','1m',787680)]:
            selected=sorted([r for r in rows if r['symbol']==symbol and r['kind']==kind and r['interval']==interval],key=lambda r:r['month'])
            need(sum(r['rows'] for r in selected)==count,'Full fixed new price calendar count')
            if kind=='klines':joined=all(a['last_close_us']==b['first_open_us'] for a,b in zip(selected,selected[1:]))
            else:joined=all(a['last_timestamp_ms']+60_000==b['first_timestamp_ms'] for a,b in zip(selected,selected[1:]))
            need(joined,'Independent price cross-month no gap/overlap');totals[symbol+'_'+kind+'_'+interval]=count
            checks.append(dict(symbol=symbol,kind=kind,interval=interval,passed=True,month_joins=len(selected)-1,rows=count))
        funding=sorted([r for r in rows if r['symbol']==symbol and r['kind']=='fundingRate'],key=lambda r:r['month'])
        need(len(funding)==18,'All18 original funding months per symbol')
        for a,b in zip(funding,funding[1:]):
            gap=b['first_timestamp_ms']-a['last_timestamp_ms']
            need(any(abs(gap-h*3_600_000)<=tolerance for h in (a['last_interval_hours'],b['first_interval_hours'])),
                'Independent funding cross-month reported interval coverage')
        total=sum(r['rows'] for r in funding);totals[symbol+'_funding_events']=total
        checks.append(dict(symbol=symbol,kind='fundingRate',interval=None,passed=True,month_joins=17,
            rows=total,event_count_basis='ACTUAL_ORIGINAL_CSV_NOT_ASSUMED_8H'))
    return checks,totals

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('protocol','actual','run-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    for key in ('protocol','actual','run_dir','output'):setattr(a,key,getattr(a,key).absolute())
    b=load(TRADE);g=b.guards();f=load(FUND);audit,derivation=trade_audit(b)
    own=sha(__file__);task=os.environ.get('COIN_TASK_ID')
    need(task and Path(sys.prefix)==STATE/'v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Actual bounded clean CPU2 runtime')
    need(a.run_dir==STATE/'d042-perpetual-history-independent-20261003-v1' and a.run_dir.is_dir()
        and not a.run_dir.is_symlink() and {x.name for x in a.run_dir.iterdir()}=={'ACTUAL_BINDING.json'}
        and a.output==ROOT/'reports/fast_research/PERPETUAL_HISTORY_SOURCE_INDEPENDENT_20261003_V1.json'
        and not a.output.exists(),'Exclusive new manifest-only audit STATE/output')
    plan,plan_sha=g.small(a.run_dir/'ACTUAL_BINDING.json')
    need(plan['ready_to_execute'] is True and plan['checker_sha256']==own and plan['budgets']==BUDGET
        and plan['protocol_path']==a.protocol.relative_to(ROOT).as_posix()
        and plan['actual_report']==a.actual.relative_to(ROOT).as_posix(),'Exact root-frozen invocation and budget')
    binding=dict(task_id=task,checker_sha256=own,ACTUAL_BINDING_sha256=plan_sha,protocol_sha256=plan['protocol_sha256'],
        actual_reports={str(a.actual):plan['actual_report_sha256']},source_hashes=plan['source_hashes'],
        exact_command=shlex.join([sys.executable,*sys.argv]),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    g.write(a.run_dir/'RUN_BINDING.json',binding);began=time.monotonic();before=resources.status();rows=[];error=None;progress=None
    report=dict(status=FAIL,binding=binding,run_dir=str(a.run_dir),run_binding_sha256=sha(a.run_dir/'RUN_BINDING.json'),
        independent_source_sha256=own,sources=rows,audit_one_derivation=derivation,source_only=True,
        old_QA_repeated=False,reused_daily_archives=12,reused_daily_QA_repeated=False,
        funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,publication_time_certified=False,
        native_market_or_execution_certified=False,economics='NOT_EVALUATED',models_fit=0,orders_sent=0,GPU=0,
        locked_consumed=False,private_scientific_lock_access='STREAMED_SHA_ONLY_NO_JSON_READ_OR_BODY_EXPORT',
        candidate_status='NO_QUALIFIED_CANDIDATE',own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
    event=dict.fromkeys(FIELDS);event.update(experiment_id='D042-HISTORY-INDEPENDENT-20261003-V1',event_id=task+':START',
        event_type='INDEPENDENT_SOURCE_START',git_commit=binding['git_commit'],data_manifest_hash=plan['actual_report_sha256'],
        protocol_hash=plan['protocol_sha256'],feature_set='ONLY_148_NEW_USDM_RAW_NORMALIZED_HISTORY_ARCHIVES',
        labels='NONE',model_family='NONE',hyperparameters={'required_archives':148},seed=None,thresholds=BUDGET,
        cost_assumptions='NOT_EVALUATED',all_folds='FIXED_FULL_HISTORY_INPUT_SCOPE_ONLY',success_failure='START_BEFORE_RAW_OR_PARQUET',
        reason_for_next_experiment='Independent new148 format/calendar; old12 accepted daily metadata reused without QA',
        result_influenced_later_choice=False,source_hashes=plan['source_hashes'],exact_command=binding['exact_command'])
    report['registration_start']=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    try:
        g.bounded(before);spec,proto_sha=g.small(a.protocol,plan['protocol_sha256']);actual,actual_sha=g.small(a.actual,plan['actual_report_sha256'])
        need(spec['contract_id']==CONTRACT and spec['mode']=='source' and spec['score_period_start']=='2024-01-01'
            and spec['score_period_end_exclusive']=='2025-07-01' and spec['funding_rate_unit']=='UNCONFIRMED'
            and spec['funding_unit_certified'] is False and spec['economic_scope']=='NOT_EVALUATED'
            and spec['budgets']==SOURCE_BUDGET,'Fixed full547 input-only scope and per-file resource bounds')
        expected=exact_entries(spec['entries'])
        need(actual['status']==ACTUAL_STATUS and actual['actual_files']==actual['required_files']==148
            and actual.get('completed_files',148)==148 and len(actual['sources'])==148
            and actual['binding']['task_id']==plan['actual_task_id'] and actual['binding']['protocol_sha256']==proto_sha
            and actual['binding']['source_hashes']==spec['frozen_sources'],'Actual new148 fully completed and pinned')
        need(actual['funding_rate_unit']=='UNCONFIRMED' and actual['funding_unit_certified'] is False
            and actual['locked_consumed'] is False and actual['models_fit']==actual['orders_sent']==actual['GPU']==0,
            'No unit/economic/locked qualification promotion')
        need(actual['archive_bodies_downloaded']==148 and actual['source_acceptance_granted'] is False
            and actual['old_source_QA_repeated'] is False,'All new archive bodies, independent acceptance still pending, no oldQA')
        report['actual_task']=g.closed(plan['actual_task_id']);source_root=Path(spec['run_dir'])
        need(source_root==STATE/'d042-perpetual-history-source-20261003-v1','Exact dedicated newsource directory')
        rb,rb_sha=g.small(source_root/'RUN_BINDING.json',actual['run_binding_sha256']);need(rb==actual['binding'],'Actual producer RUN_BINDING bytes')
        need(all(plan['source_hashes'].get(k)==v for k,v in PINS.items())
            and plan['source_hashes'].get(Path(__file__).absolute().relative_to(ROOT).as_posix())==own,'All actual auditor imports explicitly frozen')
        verified={a.protocol.relative_to(ROOT).as_posix():proto_sha,a.actual.relative_to(ROOT).as_posix():actual_sha}
        for name,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
            need(name not in verified or verified[name]==digest,'No conflicting dependency hash');pin(g,name,digest);verified[name]=digest
        need(spec['funding_header']==['calc_time','funding_interval_hours','last_funding_rate']
            and spec['price_header']==b.HEADER and spec['funding_nominal_interval_tolerance_ms']==1000,'Accepted headers and original interval tolerance')
        need(len({identity(r) for r in actual['sources']})==148 and {identity(r) for r in actual['sources']}==set(expected),
            'Exact148 published selectors without missing/duplicate/substitution')
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(148)
        for item in actual['sources']:
            entry=expected[identity(item)];progress.update('新增148档 · 原CSV/UTC/实际资金费间隔',len(rows),148,'文件',symbol=entry['symbol'],kind=entry['kind'],month=entry['month'])
            result=audit(g,item,entry,source_root,spec) if entry['kind']=='klines' else proxy_audit(g,b,f,item,entry,source_root,spec)
            result.update(kind=entry['kind'],symbol=entry['symbol'],month=entry['month'],interval=entry.get('interval'),
                receipt_path=item['receipt_path'],receipt_sha256=item['receipt_sha256']);rows.append(result);gc.collect()
            need(time.monotonic()-began<=BUDGET['wall_seconds'] and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=BUDGET['peak_RSS_bytes'],
                'Frozen independent wall/RSS bounds')
        checks,totals=crossmonth(rows,spec['funding_nominal_interval_tolerance_ms'])
        need(sum(r['rows'] for r in rows)==actual['actual_source_rows']
            and sum(r['rows'] for r in rows if r['kind']=='fundingRate')==actual['funding_events'],'Actual source reported row/event counts equal independent raw checks')
        for name,digest in verified.items():pin(g,name,digest)
        report.update(status=STATUS,actual_archives=148,completed_files_verified=148,actual_report_sha256=actual_sha,
            protocol_sha256=proto_sha,actual_run_binding_sha256=rb_sha,verified_source_hashes=verified,crossmonth=checks,row_totals=totals,
            price_rows=sum(r['rows'] for r in rows if r['kind']!='fundingRate'),
            funding_event_count=sum(r['rows'] for r in rows if r['kind']=='fundingRate'),
            completed_rows_verified=sum(r['rows'] for r in rows),all_raw_normalized_values_equal=True,
            full_CSV_EOF_and_CRC_read=True,source_fingerprint_portability='EXACT_FILE_BYTES_NOT_FRAME_RE_SERIALIZATION')
    except Exception as caught:error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        report.update(completed_files_verified=len(rows),actual_archives=len(rows),elapsed_seconds=time.monotonic()-began,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_before=before,resources_after=resources.status())
        try:g.bounded(report['resources_after'])
        except Exception as caught:error=error or caught;report['budget_error']=str(caught)
        if report['peak_RSS_bytes']>BUDGET['peak_RSS_bytes'] or report['elapsed_seconds']>BUDGET['wall_seconds']:
            error=error or RuntimeError('Independent fixed resource bound')
        if error:report['status']=FAIL
        digest,size=g.write(a.output,report)
        need(sum(p.stat().st_size for p in a.run_dir.iterdir() if p.is_file())+size<=BUDGET['new_owned_bytes'],'Metadata-only own5MB budget')
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=task+':RESULT',event_type='INDEPENDENT_SOURCE_RESULT',
            success_failure=report['status'],artifact_path=a.output.relative_to(ROOT).as_posix(),artifact_sha256=digest))
        print(json.dumps(dict(status=report['status'],report=str(a.output),sha256=digest,completed_files=len(rows))),flush=True)
    if error:raise error

if __name__=='__main__':main()
