"""Fixed USD-M trade klines; official downloader and accepted parsers reused.

Metadata mode reads only HEAD and small CHECKSUM bodies. Source mode requires a
separate frozen protocol and that exact completed metadata receipt. Neither
mode reads locked history, old market arrays, account endpoints or funding.
"""
from __future__ import annotations
import argparse, ast, contextlib, csv, gc, hashlib, io, json, os, resource
import shlex, signal, subprocess, sys, time, zipfile
from datetime import UTC, datetime
from pathlib import Path
import httpx
import polars as pl
from quant import data, disk, resources
from quant.paths import ROOT, STATE, utc_now_us
from scripts.research_v8 import funding_price_source_v2 as original
from scripts.research_v8.registry import FIELDS, append_event
from scripts.investment import public_daily_official_source_v3 as daily
from scripts.investment.official_carry_chronology_source import metadata_inspector

COMPONENT='reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json'
UPSTREAM='f446ce3812bd4e5521f21faecd4ae3c6460e49fc'
SYMBOLS=['BTCUSDT','ETHUSDT']
DAY=86_400_000_000
MINUTE=60_000_000
BOUNDS=dict(new_owned_bytes=2_000_000_000,max_archive_bytes=16_000_000,
    file_write_limit_bytes=32_000_000,max_csv_bytes=128_000_000,
    peak_RSS_bytes=1_000_000_000,file_seconds=30,wall_seconds=1800)
META_STATUS='PASS_USDM_TRADE_KLINE_HEAD_CHECKSUM_METADATA_NOT_SOURCE_ACCEPTANCE'
SOURCE_STATUS='PASS_USDM_TRADE_KLINE_FORMAT_CALENDAR_PENDING_INDEPENDENT_ACCEPTANCE'
HEADER=['open_time','open','high','low','close','volume','close_time',
    'quote_volume','count','taker_buy_volume','taker_buy_quote_volume','ignore']
PINS={**daily.PINS,
    'scripts/investment/public_daily_official_source.py':'2d6a06f1e935ff3c39d39c725c9acfc7304a35eda3023810398972a795b6d650',
    'scripts/investment/public_daily_official_source_v2.py':'079bc2ec5cf635afdc9b277aa3dbbc8f2cdaad520537a04b8275d16e49bfa83d',
    'scripts/investment/public_daily_official_source_v3.py':'dd058c092a4cee20b25e31650a1429dda78fdbf76e298cab3f45fba22ef81099'}
require=original.require
write=original.write_new
sha=lambda value:data.sha256_file(Path(value))


def entries():
    result=[]
    for interval,first in [('1d','2025-01'),('1m','2025-08')]:
        for symbol in SYMBOLS:
            for month in data.month_range(first,'2026-02'):
                url=f'https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip'
                result.append(dict(market='futures/um',partition='monthly',kind='klines',
                    interval=interval,symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM'))
    require(len(result)==42,'Fixed 28 daily and 14 minute monthly files')
    return result


def adapted_functions():
    """Three exact resource guards only; original transport/checksum/CRC kept."""
    patch=daily.private['exact_patch']();changes=[]
    nodes=[n for n in ast.parse((ROOT/'scripts/research_v8/funding_price_source_v2.py').read_bytes()).body
        if isinstance(n,ast.FunctionDef) and n.name=='download_archive']
    require(len(nodes)==1,'One original archive orchestration')
    tree=ast.Module(nodes,type_ignores=[])
    for label,old,new in [
        ('Trade ZIP budget compatibility',
         "require(entry['metadata_object_available'] and 0<entry['announced_zip_bytes']<=2_000_000,'Required small archive metadata unavailable')",
         "require(entry['metadata_object_available'] and 0<entry['announced_zip_bytes']<=16_000_000,'Required bounded trade archive metadata unavailable')"),
        ('Trade file write budget compatibility','resource.setrlimit(resource.RLIMIT_FSIZE,(4_000_000,prior_limit[1]))',
         'resource.setrlimit(resource.RLIMIT_FSIZE,(32_000_000,prior_limit[1]))'),
        ('Exact trade product URL',
         "require(url.startswith('https://data.binance.vision/data/futures/um/monthly/'),'Unexpected upstream URL')",
         "require(url.startswith('https://data.binance.vision/data/futures/um/monthly/klines/'),'Unexpected upstream URL')")]:
        tree=patch(tree,changes,label,old,new)
    namespace=dict(vars(original),LIMIT=BOUNDS['max_csv_bytes'])
    exec(compile(ast.fix_missing_locations(tree),'<private-original-trade-archive>','exec'),namespace)
    _,day_parser,day_changes=daily.private['adapted_functions']()
    return namespace['download_archive'],{'1m':data.parse_csv,'1d':day_parser},changes+day_changes


@contextlib.contextmanager
def file_deadline():
    previous=signal.getsignal(signal.SIGALRM)
    def expired(_signum,_frame):raise TimeoutError('Fixed 30 second per-file deadline; no retry')
    signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,BOUNDS['file_seconds'])
    try:yield
    finally:signal.setitimer(signal.ITIMER_REAL,0);signal.signal(signal.SIGALRM,previous)


def convert(archive,entry,parsers):
    duration=MINUTE if entry['interval']=='1m' else DAY
    first,last=original.month_range(entry['month']);opened,closed=first*1000,last*1000
    with zipfile.ZipFile(archive) as zipped:
        member=zipped.infolist()[0]
        require(0<member.file_size<=BOUNDS['max_csv_bytes'],'CSV memory bound before full read')
        raw=zipped.read(member)
    first_line=raw.split(b'\n',1)[0].decode('utf-8-sig').rstrip('\r')
    observed_header=None
    if first_line.startswith('open_time,'):
        observed_header=next(csv.reader([first_line]));require(observed_header==HEADER,'Exact official 12-column trade header')
        raw=raw.split(b'\n',1)[1]
    frame,quality=parsers[entry['interval']](raw,entry['symbol'],utc_now_us());del raw
    expected=range(opened,closed,duration)
    require(frame.columns==daily.private['SCHEMA'] and quality['timestamp_unit']=='milliseconds',
        'USD-M millisecond raw clocks, original full-volume normalized schema')
    require(frame.height==len(expected) and frame['open_us'].to_list()==list(expected)
        and all(quality[k]==0 for k in ('duplicate_rows','bad_timestamps','bad_values','gaps'))
        and not quality['incomplete_days'] and not quality['nonstandard_closes'],'Exact complete monthly calendar; no repair/drop/fill')
    require(sum(frame.null_count().row(0))==0 and frame['close_us'].to_list()==[x+duration for x in expected]
        and frame['available_us'].to_list()==frame['close_us'].to_list()
        and frame['source_close_us'].to_list()==[x+duration-1000 for x in expected],
        'Closed-bar proxy availability and inclusive raw endpoint')
    require(frame['symbol'].unique().to_list()==[entry['symbol']]
        and frame['interval'].unique().to_list()==[entry['interval']], 'Exact product interval/symbol')
    require(all(frame.schema[n]==pl.Float64 for n in ('open','high','low','close','volume','quote_volume','taker_buy_base','taker_buy_quote'))
        and all(frame.schema[n]==pl.Int64 for n in ('trade_count','open_us','close_us','available_us','ingested_us','source_close_us')),
        'Original numeric types and real trade volume/count retained')
    quality.update(observed_header=observed_header,first_open_us=opened,last_open_us=closed-duration,last_close_us=closed,
        exact_full_month_calendar=True,market='USD_M_PERPETUAL_TRADE_KLINES',
        price_semantics='OFFICIAL_FAPI_KLINE_TRADE_CLOSE_NOT_MARK_INDEX_BBO_OR_EXECUTABLE_FILL',
        availability='EXCLUSIVE_CLOSED_BAR_PROXY_NOT_HISTORICAL_PUBLICATION_CERTIFIED')
    return frame,quality


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['metadata','source'],required=True)
    for name in ('run-dir','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--protocol',type=Path);parser.add_argument('--experiment-id',required=True)
    args=parser.parse_args();run,out=args.run_dir.resolve(),args.output.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists() and out.is_relative_to(ROOT/'reports/fast_research')
        and not out.exists() and os.environ.get('COIN_TASK_ID'),'Exclusive bounded/progress STATE and report')
    require(Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Accepted clean CPU runtime')
    own=Path(__file__).resolve().relative_to(ROOT).as_posix()
    hashes={**PINS,own:sha(__file__)}
    for path,value in hashes.items():require(sha(ROOT/path)==value,'Frozen reused source bytes changed: '+path)
    objects=entries();spec=None;metadata=None
    if args.mode=='source':
        require(args.protocol is not None and args.protocol.resolve().is_relative_to(ROOT/'protocols'),'Frozen source protocol required')
        spec=json.loads(args.protocol.read_bytes())
        require(spec['contract_id']=='USD_M_TRADE_KLINE_SOURCE_20261003_V1'
            and spec['entries']==objects and spec['budgets']==BOUNDS and spec['frozen_sources'].get(own)==hashes[own]
            and all(spec['frozen_sources'].get(p)==h for p,h in PINS.items())
            and run==Path(spec['run_dir']).resolve() and out==(ROOT/spec['output_path']).resolve(), 'Exact fixed source scope/budgets/paths')
        hashes=spec['frozen_sources']
        for p,h in hashes.items():require((ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,'Full frozen source map')
        meta_path=(ROOT/spec['metadata_path']).resolve()
        require(meta_path.is_relative_to(ROOT/'reports/fast_research') and meta_path.stat().st_size<=2_000_000
            and sha(meta_path)==spec['metadata_sha256'],'Exact source-free HEAD/CHECKSUM receipt')
        metadata=json.loads(meta_path.read_bytes())
        require(metadata['status']==META_STATUS and metadata['actual_files']==42
            and metadata['archive_bodies_downloaded']==0 and metadata['binding']['source_sha256']==hashes[own],
            'Actual completed metadata before separately authorized source run')
        objects=metadata['objects']
        require([{k:e[k] for k in entries()[0]} for e in objects]==entries(),'No substituted metadata URLs')
    before=resources.status();run.mkdir();started=time.monotonic()
    download,parsers,changes=adapted_functions()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(Path(__file__).resolve()),source_sha256=sha(__file__),
        source_hashes=hashes,exact_command=shlex.join([sys.executable,*sys.argv]),mode=args.mode,
        protocol_path=str(args.protocol.resolve()) if args.protocol else None,
        protocol_sha256=sha(args.protocol) if args.protocol else None,sys_prefix=sys.prefix,
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),AST_changes=changes,
        spec=dict(source_scope='USD_M_TRADE_JAN2025_FEB2026_DAILY_AUG2025_FEB2026_MINUTE',
            daily_calendar=data.month_range('2025-01','2026-02'),minute_calendar=data.month_range('2025-08','2026-02'),symbols=SYMBOLS))
    write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',
        event_type='OPERATIONAL_SOURCE_START',git_commit=binding['git_commit'],data_manifest_hash=hashlib.sha256(json.dumps(entries(),sort_keys=True).encode()).hexdigest(),
        protocol_hash=binding['protocol_sha256'],feature_set='USD_M_TRADE_KLINE_'+args.mode.upper(),labels='NONE',model_family='NONE',
        hyperparameters={'entries':entries(),'mode':args.mode},seed=None,thresholds=BOUNDS,cost_assumptions='NOT_EVALUATED',
        all_folds='2025AUG_2026FEB_SOURCE_ONLY',success_failure='START_BEFORE_NEW_NETWORK_OR_ROWS',
        reason_for_next_experiment='Fixed long-short research requires real perpetual trade prices; reuse existing funding/mark/index',
        result_influenced_later_choice=False,source_hashes=hashes,exact_command=binding['exact_command'],run_binding_sha256=sha(run/'RUN_BINDING.json'))
    result=dict(status='FAIL_USDM_TRADE_KLINE_'+args.mode.upper(),binding=binding,run_binding_sha256=sha(run/'RUN_BINDING.json'),
        registration_start=append_event(ROOT/'reports/experiment_registry.jsonl',event),objects=[],sources=[],actual_files=0,
        required_files=42,archive_bodies_downloaded=0,market_arrays_read=False,old_source_QA_repeated=False,
        source_only=True,source_acceptance_granted=False,funding_unit_certified=False,funding_rate_unit='UNCONFIRMED',
        publication_time_certified=False,native_market_certified=False,economic_scope='NOT_EVALUATED',models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,
        resources_before=before)
    progress=original.progress_writer(42);progress.value['detail']='官方USD-M成交K线；来源格式阶段，不是资金费单位或交易资格'
    client=None
    def guard():
        extra=metadata['owned_bytes'] if metadata else 0
        require(original.owned_bytes(run)+extra<=BOUNDS['new_owned_bytes'],'Combined2GB source/metadata hard bound')
        require(time.monotonic()-started<=BOUNDS['wall_seconds'],'Fixed source wall budget')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=BOUNDS['peak_RSS_bytes'],'Source RSS1GB hard budget')
    try:
        progress.update('真实磁盘容量扫描，总量未知',None,None,'扫描')
        scan=datetime.now(UTC).isoformat()
        result['disk']=dict(**disk.check(BOUNDS['new_owned_bytes']),scan_started_utc=scan,scan_finished_utc=datetime.now(UTC).isoformat())
        require(result['disk']['total_bytes']+BOUNDS['new_owned_bytes']<=32_000_000_000,'Expected32GB capacity')
        component=json.loads((ROOT/COMPONENT).read_bytes());require(component['commit']==UPSTREAM,'Existing official software pin')
        if args.mode=='metadata':
            client=httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False,headers={'User-Agent':'coin-fixed-usdm-trade-source/1.0'})
            inspect=metadata_inspector(client)
            for entry in objects:
                progress.update('官方HEAD与CHECKSUM，无ZIP内容',result['actual_files'],42,'文件',interval=entry['interval'],month=entry['month'],symbol=entry['symbol'])
                with file_deadline():value=inspect(entry)
                result['objects'].append(value);result['actual_files']=len(result['objects'])
                require(value['metadata_object_available'] and isinstance(value['announced_zip_bytes'],int)
                    and 0<value['announced_zip_bytes']<=BOUNDS['max_archive_bytes'],'Absent/restricted/oversize metadata: no retry or alternate host')
                guard()
            result.update(status=META_STATUS,announced_compressed_total_bytes=sum(e['announced_zip_bytes'] for e in result['objects']),
                maximum_announced_zip_bytes=max(e['announced_zip_bytes'] for e in result['objects']),uncompressed_bytes='UNKNOWN_BEFORE_ZIP',actual_source_rows='UNKNOWN_METADATA_ONLY')
            require(result['announced_compressed_total_bytes']<BOUNDS['new_owned_bytes'],'Announced ZIP total alone exceeds combined2GB budget')
        else:
            upstream=original.official_module(component)
            totals={(s,i):0 for s in SYMBOLS for i in ('1d','1m')}
            for entry in objects:
                require(original.owned_bytes(run)+metadata['owned_bytes']+entry['announced_zip_bytes']+BOUNDS['file_write_limit_bytes']<=BOUNDS['new_owned_bytes'],'Before-download ZIP+Parquet working reservation')
                job=run/f"{entry['symbol']}-{entry['interval']}-{entry['month']}";job.mkdir()
                receipt=dict(status='FAIL_USDM_TRADE_ARCHIVE',entry=entry)
                try:
                    progress.update('官方成交K线下载/完整UTC格式',result['actual_files'],42,'文件',interval=entry['interval'],month=entry['month'],symbol=entry['symbol'])
                    with file_deadline():
                        archive,checksum,csv_bytes=download(entry,job,upstream);result['archive_bodies_downloaded']+=1
                        frame,quality=convert(archive,entry,parsers);target=job/'source.parquet'
                        frame.write_parquet(target,compression='zstd');require(target.stat().st_size<=BOUNDS['file_write_limit_bytes'],'Per-file normalized Parquet bound')
                    receipt.update(status='PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY',normalized_path=str(target),normalized_sha256=sha(target),
                        normalized_bytes=target.stat().st_size,rows=frame.height,quality=quality,normalized_schema={k:str(v) for k,v in frame.schema.items()},
                        zip_path=str(archive),zip_sha256=sha(archive),checksum_path=str(checksum),checksum_sha256=sha(checksum),zip_crc='PASS_FULL_READ',uncompressed_csv_bytes=csv_bytes)
                    totals[(entry['symbol'],entry['interval'])]+=frame.height;del frame;gc.collect();guard()
                except Exception as error:receipt.update(error_type=type(error).__name__,reason=str(error));raise
                finally:write(job/'receipt.json',receipt)
                result['sources'].append({k:receipt[k] for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema')}|
                    dict(symbol=entry['symbol'],interval=entry['interval'],month=entry['month'],receipt_path=str(job/'receipt.json'),receipt_sha256=sha(job/'receipt.json')))
                result['actual_files']=len(result['sources']);result['market_arrays_read']=True
            require(all(totals[(s,'1d')]==424 and totals[(s,'1m')]==305280 for s in SYMBOLS),'Complete authorized424 daily/212 scoring days per asset')
            result.update(status=SOURCE_STATUS,daily_rows_per_symbol=424,minute_rows_per_symbol=305280,score_days=212,initial_completed_daily_warmup_days=212)
        require(all(sha(ROOT/p)==h for p,h in hashes.items()),'Source bytes unchanged after actual run')
        progress.update('新来源元数据或格式完成',42,42,'文件')
    except Exception as error:result.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        if client:client.close()
        result.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            owned_bytes=original.owned_bytes(run),resources_after=resources.status())
        write(out,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=args.experiment_id+':RESULT',event_type='OPERATIONAL_SOURCE_RESULT',
            success_failure=result['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],actual_files=result['actual_files'],output=str(out),sha256=sha(out))))


if __name__=='__main__':main()
