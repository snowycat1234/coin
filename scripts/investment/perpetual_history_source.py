"""D042 fixed historical USD-M inputs; reuse official transport and parsers.

Metadata reads HEAD/CHECKSUM only. A separate frozen source task consumes the
completed metadata receipt. This producer checks new formats, not economics or
funding units; independent source acceptance is a separate task.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, importlib.util, json, os, resource, shlex
import subprocess, sys, time, types
from datetime import UTC, datetime
from pathlib import Path
import httpx
import polars as pl
from quant import data, disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_trade_source as trade
from scripts.investment import perpetual_2h_warmup_source as twohour
from scripts.research_v8 import funding_price_source_v2 as original
from scripts.research_v8.registry import FIELDS, append_event

CONTRACT='D042_OFFICIAL_PERPETUAL_HISTORY_SOURCE_V1'
META_STATUS='PASS_D042_148_OFFICIAL_HISTORY_METADATA_ONLY'
SOURCE_STATUS='PASS_D042_148_HISTORY_FORMAT_PENDING_INDEPENDENT_QA'
SYMBOLS=['BTCUSDT','ETHUSDT']
BOUNDS=dict(new_owned_bytes=1_000_000_000,max_archive_bytes=16_000_000,
    file_write_limit_bytes=32_000_000,max_csv_bytes=128_000_000,
    peak_RSS_bytes=1_000_000_000,file_seconds=30,wall_seconds=1800)
FORMAT='protocols/FUNDING_MARK_INDEX_SOURCE_V8_V1.json'
GUARD='docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
PINS={**twohour.PINS,
    'scripts/investment/perpetual_2h_warmup_source.py':'a41accdebc6ce84186d32a5f6c84e51bcb727b844706a63b1ebe37b664ac3b4c',
    FORMAT:'2b3ef722ba3276c95d4a658d63ecdae12d92ae7a4f95a88de2918a4fd775d38a',
    GUARD:'278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'}
require,write,sha=original.require,original.write_new,trade.sha


def entries():
    objects=[]
    plans=[('klines','1m','2024-01','2025-06'),
        ('klines','1d','2023-06','2024-12'),('klines','2h','2023-12','2023-12'),
        ('markPriceKlines','1m','2024-01','2025-06'),('fundingRate',None,'2024-01','2025-06')]
    for kind,interval,first,last in plans:
        for symbol in SYMBOLS:
            for month in data.month_range(first,last):
                suffix=f'{symbol}-fundingRate-{month}.zip' if kind=='fundingRate' else f'{interval}/{symbol}-{interval}-{month}.zip'
                url=f'https://data.binance.vision/data/futures/um/monthly/{kind}/{symbol}/{suffix}'
                entry=dict(market='futures/um',partition='monthly',kind=kind,
                    symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM')
                if interval is not None:entry['interval']=interval
                objects.append(entry)
    require(len(objects)==148 and len({e['url'] for e in objects})==148,'Exactly148 authorized archives')
    return objects


def adapted_functions():
    """Only resource compatibility; original downloader body and URL guard kept."""
    patch=trade.daily.private['exact_patch']();changes=[]
    nodes=[n for n in ast.parse((ROOT/'scripts/research_v8/funding_price_source_v2.py').read_bytes()).body
        if isinstance(n,ast.FunctionDef) and n.name=='download_archive']
    require(len(nodes)==1,'One pinned original downloader')
    tree=ast.Module(nodes,type_ignores=[])
    for label,old,new in [
        ('D042 bounded historical ZIP compatibility',
         "require(entry['metadata_object_available'] and 0<entry['announced_zip_bytes']<=2_000_000,'Required small archive metadata unavailable')",
         "require(entry['metadata_object_available'] and 0<entry['announced_zip_bytes']<=16_000_000,'Required bounded history archive metadata unavailable')"),
        ('D042 bounded file compatibility','resource.setrlimit(resource.RLIMIT_FSIZE,(4_000_000,prior_limit[1]))',
         'resource.setrlimit(resource.RLIMIT_FSIZE,(32_000_000,prior_limit[1]))')]:
        tree=patch(tree,changes,label,old,new)
    namespace=dict(vars(original),LIMIT=BOUNDS['max_csv_bytes'])
    exec(compile(ast.fix_missing_locations(tree),'<D042-private-original-download>','exec'),namespace)
    _,parsers,trade_changes=trade.adapted_functions()
    _,parsers2h,convert2h,hour_changes=twohour.adapted_functions()
    # The original D041 converter has a small-file guard; only its private
    # resource namespace changes. Its calendar, volume and timestamp code stays.
    convert2h=types.FunctionType(convert2h.__code__,dict(convert2h.__globals__,BOUNDS=BOUNDS),
        convert2h.__name__,convert2h.__defaults__,convert2h.__closure__)
    changes+=trade_changes+hour_changes+[{'label':'D042 private2h CSV resource namespace','max_csv_bytes':BOUNDS['max_csv_bytes']}]
    require(original.LIMIT==1_000_000_000 and twohour.BOUNDS['max_csv_bytes']==2_000_000
        and trade.BOUNDS['max_csv_bytes']==128_000_000,'Frozen component globals unchanged')
    return namespace['download_archive'],parsers,parsers2h,convert2h,changes


def small(path,digest=None):
    path=Path(path).resolve()
    require(path.is_relative_to(ROOT) and path.is_file() and not path.is_symlink()
        and path.stat().st_size<=2_000_000,'Small ROOT protocol/receipt only')
    require(digest is None or sha(path)==digest,'Small frozen proof changed')
    return json.loads(path.read_bytes())


def validate(spec,mode,own):
    require(spec['ready_for_execution'] is True and spec['contract_id']==CONTRACT
        and spec['mode']==mode and spec['entries']==entries() and spec['budgets']==BOUNDS,
        'Fixed148 source scope, phase and budgets')
    require(spec['environment']['sys_prefix']==str(STATE/'v8-clean-env-20261002-v2'), 'Accepted CPU environment')
    require(spec['combined_capacity_reservation_bytes']==2_000_000_000,'New source1GB plus1GB working capacity')
    previous=small(ROOT/FORMAT,PINS[FORMAT])
    for key in ('funding_header','price_header','funding_nominal_interval_tolerance_ms'):
        require(spec[key]==previous[key],'Unchanged accepted format guard: '+key)
    hashes=spec['frozen_sources']
    require(hashes.get(own)==sha(__file__) and all(hashes.get(p)==h for p,h in PINS.items()),'Own/reused exact source binding')
    for path,value in hashes.items():
        candidate=(ROOT/path).resolve()
        require(not Path(path).is_absolute() and candidate.is_relative_to(ROOT)
            and not (ROOT/path).is_symlink() and sha(candidate)==value,'Frozen source changed: '+path)
    return hashes


def metadata_receipt(spec,hashes):
    receipt=small(ROOT/spec['metadata_path'],spec['metadata_sha256'])
    require(receipt['status']==META_STATUS and receipt['completed_files']==receipt['required_files']==148
        and receipt['archive_bodies_downloaded']==0 and receipt['binding']['mode']=='metadata'
        and receipt['binding']['source_sha256']==hashes[Path(__file__).resolve().relative_to(ROOT).as_posix()],
        'Actual same-source metadata phase, no archive bodies')
    expected=entries()
    require(len(receipt['objects'])==len(expected)
        and [{k:e[k] for k in template} for e,template in zip(receipt['objects'],expected)]==expected,
        'Metadata exact authorized URLs')
    guard_spec=importlib.util.spec_from_file_location('_d042_closed_metadata_guard',ROOT/GUARD)
    guard=importlib.util.module_from_spec(guard_spec);guard_spec.loader.exec_module(guard)
    closed=guard.closed(receipt['binding']['task_id'])
    require(closed['task']['ended_at']<=time.time(),'Metadata really completed before source')
    return receipt,closed


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['metadata','source'],required=True)
    for key in ('protocol','run-dir','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--experiment-id',required=True);args=parser.parse_args()
    run,out,protocol=args.run_dir.resolve(),args.output.resolve(),args.protocol.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists() and out.is_relative_to(ROOT/'reports/fast_research')
        and not out.exists() and protocol.is_relative_to(ROOT/'protocols') and os.environ.get('COIN_TASK_ID'),
        'Exclusive bounded/progress STATE and ROOT receipt')
    require(Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Accepted clean CPU runtime')
    spec=small(protocol);own=Path(__file__).resolve().relative_to(ROOT).as_posix();hashes=validate(spec,args.mode,own)
    require(run==Path(spec['run_dir']).resolve() and out==(ROOT/spec['output_path']).resolve(),'Frozen phase output paths')
    metadata=closed=None
    if args.mode=='source':metadata,closed=metadata_receipt(spec,hashes)
    objects=metadata['objects'] if metadata else entries()
    download,parsers,parsers2h,convert2h,changes=adapted_functions()
    before=resources.status();run.mkdir();started=time.monotonic()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(Path(__file__).resolve()),source_sha256=sha(__file__),
        source_hashes=dict(hashes),protocol_path=str(protocol),protocol_sha256=sha(protocol),mode=args.mode,spec=spec,
        exact_command=shlex.join([sys.executable,*sys.argv]),sys_prefix=sys.prefix,AST_changes=changes,
        metadata_actual_task=closed,git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',
        event_type='OPERATIONAL_SOURCE_START',git_commit=binding['git_commit'],
        data_manifest_hash=hashlib.sha256(json.dumps(entries(),sort_keys=True).encode()).hexdigest(),
        protocol_hash=binding['protocol_sha256'],feature_set='D042_OFFICIAL_HISTORY_'+args.mode.upper(),labels='NONE',model_family='NONE',
        hyperparameters={'mode':args.mode,'entries':entries()},seed=None,thresholds=BOUNDS,cost_assumptions='NOT_EVALUATED',
        all_folds='JAN2024_JUN2025_FIXED_SOURCE_ONLY',success_failure='START_BEFORE_NEW_NETWORK_OR_ROWS',
        reason_for_next_experiment='Fixed547day same-product public directional comparison; no profit-based date selection',
        result_influenced_later_choice=False,source_hashes=dict(hashes),exact_command=binding['exact_command'],run_binding_sha256=sha(run/'RUN_BINDING.json'))
    result=dict(status='FAIL_D042_HISTORY_'+args.mode.upper(),binding=binding,run_binding_sha256=sha(run/'RUN_BINDING.json'),
        registration_start=append_event(ROOT/'reports/experiment_registry.jsonl',event),objects=[],sources=[],completed_files=0,
        actual_files=0,required_files=148,archive_bodies_downloaded=0,actual_source_rows=0,source_only=True,
        source_acceptance_granted=False,old_source_QA_repeated=False,market_arrays_read=False,
        funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,publication_time_certified=False,
        native_market_certified=False,economic_scope='NOT_EVALUATED',models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources_before=before)
    progress=original.progress_writer(148);progress.value['detail']='D042 固定148档；新来源格式阶段，尚待独立验收'
    def guard(reserve=0):
        require(original.owned_bytes(run)+(metadata['owned_bytes'] if metadata else 0)+reserve<=BOUNDS['new_owned_bytes'],'Combined source/metadata1GB hard budget')
        require(time.monotonic()-started<=BOUNDS['wall_seconds'],'1800s source wall budget')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=BOUNDS['peak_RSS_bytes'],'Source RSS1GB budget')
    try:
        progress.update('真实磁盘扫描，总量未知',None,None,'扫描');scan=datetime.now(UTC).isoformat()
        result['disk']=dict(**disk.check(spec['combined_capacity_reservation_bytes']),scan_started_utc=scan,scan_finished_utc=datetime.now(UTC).isoformat())
        require(result['disk']['total_bytes']+spec['combined_capacity_reservation_bytes']<=32_000_000_000,'Expected32GB capacity with working reservation')
        component=small(ROOT/trade.COMPONENT,PINS[trade.COMPONENT]);require(component['commit']==trade.UPSTREAM,'Official software provenance')
        if args.mode=='metadata':
            with httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False,headers={'User-Agent':'coin-fixed-history-source/1.0'}) as client:
                inspect=trade.metadata_inspector(client)
                for entry in objects:
                    progress.update('官方HEAD/CHECKSUM；没有ZIP内容',result['completed_files'],148,'文件',kind=entry['kind'],month=entry['month'],symbol=entry['symbol'])
                    with trade.file_deadline():value=inspect(entry)
                    result['objects'].append(value);result['completed_files']=result['actual_files']=len(result['objects'])
                    require(value['metadata_object_available'] and isinstance(value['announced_zip_bytes'],int)
                        and 0<value['announced_zip_bytes']<=BOUNDS['max_archive_bytes'],'Unavailable/restricted/oversize metadata; no retry')
                    guard()
            announced=sum(e['announced_zip_bytes'] for e in result['objects'])
            guard(announced+BOUNDS['file_write_limit_bytes'])
            result.update(status=META_STATUS,announced_compressed_total_bytes=announced,
                maximum_announced_zip_bytes=max(e['announced_zip_bytes'] for e in result['objects']),
                uncompressed_bytes='UNKNOWN_BEFORE_ZIP',actual_source_rows='UNKNOWN_METADATA_ONLY')
        else:
            upstream=original.official_module(component);declared=0
            for entry in objects:
                guard(entry['announced_zip_bytes']+BOUNDS['file_write_limit_bytes'])
                label=f"{entry['symbol']}-{entry['interval']}-{entry['month']}" if entry['kind']=='klines' else f"{entry['kind']}-{entry['symbol']}-{entry['month']}"
                job=run/label;job.mkdir()
                receipt=dict(status='FAIL_D042_ARCHIVE',entry=entry,component_sha256=PINS[trade.COMPONENT])
                try:
                    progress.update('官方下载/CRC/原格式转换',result['completed_files'],148,'文件',kind=entry['kind'],month=entry['month'],symbol=entry['symbol'])
                    with trade.file_deadline():
                        archive,check,csv_bytes=download(entry,job,upstream);result['archive_bodies_downloaded']+=1
                        target=job/'source.parquet';declared+=csv_bytes
                        if entry['kind']=='klines':
                            frame,quality=(convert2h(archive,entry,parsers2h) if entry['interval']=='2h' else trade.convert(archive,entry,parsers))
                            frame.write_parquet(target,compression='zstd')
                            receipt.update(status='PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY',normalized_path=str(target),normalized_sha256=sha(target),
                                normalized_bytes=target.stat().st_size,rows=frame.height,quality=quality,normalized_schema={k:str(v) for k,v in frame.schema.items()})
                            del frame
                        else:
                            stats=original.convert_source(archive,entry,spec,target)
                            receipt.update(status='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA',stats=stats,
                                parquet_path=str(target),parquet_sha256=sha(target),parquet_bytes=target.stat().st_size)
                        require(target.stat().st_size<=BOUNDS['file_write_limit_bytes'],'Per-file32MB normalized limit')
                        receipt.update(zip_path=str(archive),zip_sha256=sha(archive),checksum_path=str(check),checksum_sha256=sha(check),zip_crc='PASS_FULL_READ',uncompressed_csv_bytes=csv_bytes)
                    gc.collect();guard();receipt['owned_bytes']=original.owned_bytes(job)
                except Exception as error:receipt.update(error_type=type(error).__name__,reason=str(error));raise
                finally:write(job/'receipt.json',receipt)
                item=dict(kind=entry['kind'],symbol=entry['symbol'],interval=entry.get('interval'),month=entry['month'],entry=entry,
                    receipt_path=str(job/'receipt.json'),receipt_sha256=sha(job/'receipt.json'),
                    format_evidence_role='NEW_PRODUCER_FORMAT_ONLY_PENDING_INDEPENDENT_QA')
                if entry['kind']=='klines':item.update({k:receipt[k] for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema')})
                else:item.update(normalized_path=receipt['parquet_path'],normalized_sha256=receipt['parquet_sha256'],normalized_bytes=receipt['parquet_bytes'],
                    rows=receipt['stats']['rows'],stats=receipt['stats'],normalized_schema=receipt['stats']['schema'])
                result['sources'].append(item);result['completed_files']=result['actual_files']=len(result['sources'])
                result['actual_source_rows']=sum(r['rows'] for r in result['sources']);result['market_arrays_read']=True
                progress.update('完整新档已写入',result['completed_files'],148,'文件')
            require(result['completed_files']==148,'All fixed archives complete')
            result.update(status=SOURCE_STATUS,declared_uncompressed_csv_bytes=declared,
                cumulative_declared_CSV_not_extracted=True,funding_events=sum(r['rows'] for r in result['sources'] if r['kind']=='fundingRate'))
        require(all(sha(ROOT/p)==h for p,h in hashes.items()),'Frozen source bytes unchanged after run')
        guard();progress.update('来源阶段实际完成',148,148,'文件')
    except Exception as error:result.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        result.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,owned_bytes=original.owned_bytes(run),resources_after=resources.status())
        write(out,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=args.experiment_id+':RESULT',event_type='OPERATIONAL_SOURCE_RESULT',
            success_failure=result['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],completed_files=result['completed_files'],output=str(out),sha256=sha(out))))


if __name__=='__main__':main()
