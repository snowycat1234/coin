"""D041: two July USD-M 2h archives, using pinned official source functions.

Format/calendar producer only; independent acceptance remains a separate task.
No old data QA, funding interpretation, synthetic resampling or account run.
"""
from __future__ import annotations
import argparse, ast, gc, hashlib, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
import httpx
import polars as pl
from quant import data, disk, resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_trade_source as trade
from scripts.research_v8 import funding_price_source_v2 as original
from scripts.research_v8.registry import FIELDS, append_event

SYMBOLS=['BTCUSDT','ETHUSDT']
TWO_HOUR_US=7_200_000_000
DAY_US=86_400_000_000
STATUS='PASS_D041_OFFICIAL_PERPETUAL_2H_JULY_FORMAT_CALENDAR_PENDING_INDEPENDENT_QA'
CONTRACT='D041_OFFICIAL_PERPETUAL_2H_JULY_SOURCE_V1'
BOUNDS=dict(new_owned_bytes=20_000_000,max_archive_bytes=2_000_000,
    max_csv_bytes=2_000_000,file_write_limit_bytes=4_000_000,
    peak_RSS_bytes=512_000_000,file_seconds=30,wall_seconds=300)
PINS={**trade.PINS,
    'scripts/investment/perpetual_trade_source.py':'8c569bb1add310c230230cc9e2cd923adba7f4ac37776e48c1fdfc1ed0e9240c',
    'src/quant/disk.py':'4b4c80b309fcff83cc740e8c59ed0a8fcdd56121063a94d854126aa7518277b9',
    'src/quant/resources.py':'e8028c40240bfb0df05228247ad6fee734831a14b9c6ac40acbd0c291b1969a3',
    'src/quant/paths.py':'3c3e43ddd9ef1f2a52f902869d29e9a0ac5f29f1b5e64362b873290d07f72282',
    'scripts/research_v8/registry.py':'081f881f2cb1cdc84b8c098606e9f3235c92fcdd04c0120527bee0d8493068ab',
    'scripts/research_v7/oracle_flow_ceiling.py':'959f63f40c3294b6b2b75267b9138202df79223a7e7723397cf06b8d45a1477e',
    'environments/v8/uv.lock':'97335dc3dbb04d7dbc67425f91d4e941a0cfd2c84e5f2adcd852514ec4600de6',
    'state/dataset_lock.json':'29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'}
require,write,sha=original.require,original.write_new,trade.sha


def entries():
    result=[]
    for symbol in SYMBOLS:
        url=f'https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/2h/{symbol}-2h-2025-07.zip'
        result.append(dict(market='futures/um',partition='monthly',kind='klines',
            interval='2h',symbol=symbol,month='2025-07',url=url,checksum_url=url+'.CHECKSUM'))
    return result


def adapted_functions():
    """Compile four private definitions; no reused module globals are changed."""
    patch=trade.daily.private['exact_patch']();changes=[]
    def selected(path,name):
        nodes=[n for n in ast.parse((ROOT/path).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name]
        require(len(nodes)==1,'One exact pinned function: '+name)
        return ast.Module(nodes,type_ignores=[])
    download=selected('scripts/research_v8/funding_price_source_v2.py','download_archive')
    download_ns=dict(vars(original),LIMIT=BOUNDS['max_csv_bytes'])
    exec(compile(ast.fix_missing_locations(download),'<D041-private-original-download>','exec'),download_ns)
    parser=selected('src/quant/data.py','parse_csv')
    parser=patch(parser,changes,'2h UTC daily bucket',
        'dates=(frame.with_columns((pl.col("open_us") // (MINUTE_US * 1440)).alias("day")).group_by("day").len().sort("day"))',
        'dates=(frame.with_columns((pl.col("open_us") // DAY_US).alias("day")).group_by("day").len().sort("day"))')
    parser=patch(parser,changes,'2h twelve bars per complete UTC day',
        'bad_days=[{"date":datetime.fromtimestamp(row[0] * 86400,UTC).date().isoformat(),"rows":row[1]} for row in dates.iter_rows() if row[1] != 1440]',
        'bad_days=[{"date":datetime.fromtimestamp(row[0] * 86400,UTC).date().isoformat(),"rows":row[1]} for row in dates.iter_rows() if row[1] != 12]')
    old='''frame=frame.sort("open_us").with_columns(
        (pl.col("open_us") + MINUTE_US).alias("close_us"),
        (pl.col("open_us") + MINUTE_US).alias("available_us"),
        pl.lit(symbol).alias("symbol"), pl.lit("1m").alias("interval"),
        pl.lit(ingested_us).alias("ingested_us"),
        (pl.col("raw_close") * scale).alias("source_close_us"))'''
    parser=patch(parser,changes,'2h interval label',old,old.replace('pl.lit("1m")','pl.lit("2h")'))
    parser_ns=dict(vars(data),MINUTE_US=TWO_HOUR_US,DAY_US=DAY_US)
    exec(compile(ast.fix_missing_locations(parser),'<D041-private-original-2h-parser>','exec'),parser_ns)
    conversion=selected('scripts/investment/perpetual_trade_source.py','convert')
    conversion=patch(conversion,changes,'2h unchanged trade format calendar duration',
        "duration=MINUTE if entry['interval']=='1m' else DAY",'duration=TWO_HOUR_US')
    convert_ns=dict(vars(trade),TWO_HOUR_US=TWO_HOUR_US,BOUNDS=BOUNDS)
    exec(compile(ast.fix_missing_locations(conversion),'<D041-private-original-trade-convert>','exec'),convert_ns)
    require(data.MINUTE_US==60_000_000 and original.LIMIT==1_000_000_000
        and trade.BOUNDS['max_csv_bytes']==128_000_000,'Frozen module globals unchanged')
    return download_ns['download_archive'],{'2h':parser_ns['parse_csv']},convert_ns['convert'],changes


def validate(spec,own):
    require(spec['ready_for_execution'] is True and spec['contract_id']==CONTRACT and spec['entries']==entries()
        and spec['source_start']=='2025-07-01' and spec['source_end_exclusive']=='2025-08-01'
        and spec['symbols']==SYMBOLS and spec['interval']=='2h'
        and spec['expected_archives']==2 and spec['expected_rows_per_symbol']==372
        and spec['expected_total_rows']==744 and spec['budgets']==BOUNDS,'Exact two July source archives and hard budgets')
    require(spec['announced_zip_bytes_expected'] is None and spec['source_acceptance_before_actual'] is False
        and spec['publication_time_certified'] is False and spec['economic_scope']=='NOT_EVALUATED'
        and spec['environment']['sys_prefix']==str(STATE/'v8-clean-env-20261002-v2'), 'Unknown sizes and source-only scope')
    hashes=spec['frozen_sources']
    require(hashes.get(own)==sha(__file__) and all(hashes.get(p)==h for p,h in PINS.items()),'Full reused and own frozen source binding')
    for path,value in hashes.items():
        candidate=(ROOT/path).resolve()
        require(candidate.is_relative_to(ROOT) and not (ROOT/path).is_symlink() and sha(candidate)==value,'Frozen ordinary source changed: '+path)
    return hashes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','run-dir','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--experiment-id',required=True);args=parser.parse_args()
    run,out,protocol=args.run_dir.resolve(),args.output.resolve(),args.protocol.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists() and out.is_relative_to(ROOT/'reports/fast_research')
        and not out.exists() and protocol.is_relative_to(ROOT/'protocols') and os.environ.get('COIN_TASK_ID'),'Fresh bounded/progress STATE and small ROOT report')
    require(Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Accepted CPU-only clean runtime')
    spec=json.loads(protocol.read_bytes());own=Path(__file__).resolve().relative_to(ROOT).as_posix();hashes=validate(spec,own)
    require(run==Path(spec['run_dir']).resolve() and out==(ROOT/spec['output_path']).resolve(),'Exact frozen output paths')
    download,parsers,convert,changes=adapted_functions();before=resources.status();run.mkdir();started=time.monotonic()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(Path(__file__).resolve()),source_sha256=sha(__file__),
        source_hashes=dict(hashes),protocol_path=str(protocol),protocol_sha256=sha(protocol),spec=spec,
        exact_command=shlex.join([sys.executable,*sys.argv]),sys_prefix=sys.prefix,AST_changes=changes,
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',
        event_type='OPERATIONAL_SOURCE_START',git_commit=binding['git_commit'],data_manifest_hash=hashlib.sha256(json.dumps(entries(),sort_keys=True).encode()).hexdigest(),
        protocol_hash=binding['protocol_sha256'],feature_set='USD_M_TRADE_KLINE_2H_JULY_WARMUP_SOURCE',labels='NONE',model_family='NONE',
        hyperparameters={'entries':entries()},seed=None,thresholds=BOUNDS,cost_assumptions='NOT_EVALUATED',all_folds='JUL2025_SOURCE_ONLY',
        success_failure='START_BEFORE_NETWORK_OR_ROWS',reason_for_next_experiment='Original public2h benchmark needs400h warmup; source only',
        result_influenced_later_choice=False,source_hashes=dict(hashes),exact_command=binding['exact_command'],run_binding_sha256=sha(run/'RUN_BINDING.json'))
    result=dict(status='FAIL_D041_PERPETUAL_2H_JULY_SOURCE',binding=binding,run_binding_sha256=sha(run/'RUN_BINDING.json'),
        registration_start=append_event(ROOT/'reports/experiment_registry.jsonl',event),objects=[],sources=[],actual_files=0,required_files=2,
        metadata_files=0,archive_bodies_downloaded=0,actual_source_rows=0,source_only=True,source_acceptance_granted=False,
        old_source_QA_repeated=False,publication_time_certified=False,funding_unit_certified=False,funding_rate_unit='UNCONFIRMED',
        native_market_certified=False,economic_scope='NOT_EVALUATED',models_fit=0,orders_sent=0,GPU=0,locked_consumed=False,resources_before=before)
    progress=original.progress_writer(2);progress.value['detail']='D041 官方7月2小时成交预热；来源格式阶段，尚待独立验收'
    def guard():
        require(original.owned_bytes(run)<=BOUNDS['new_owned_bytes'],'New STATE20MB hard bound')
        require(time.monotonic()-started<=BOUNDS['wall_seconds'],'Source300s wall hard bound')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=BOUNDS['peak_RSS_bytes'],'Source RSS512MB hard bound')
    try:
        progress.update('真实磁盘扫描，总量未知',None,None,'扫描');scan=datetime.now(UTC).isoformat()
        result['disk']=dict(**disk.check(BOUNDS['new_owned_bytes']),scan_started_utc=scan,scan_finished_utc=datetime.now(UTC).isoformat())
        require(result['disk']['total_bytes']+BOUNDS['new_owned_bytes']<=32_000_000_000,'Expected32GB source capacity')
        component=json.loads((ROOT/trade.COMPONENT).read_bytes());require(component['commit']==trade.UPSTREAM,'Existing official software pin')
        with httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False,headers={'User-Agent':'coin-fixed-july-2h-source/1.0'}) as client:
            inspect=trade.metadata_inspector(client)
            for entry in entries():
                progress.update('官方HEAD/CHECKSUM；完整档尚未完成',0,2,'文件',symbol=entry['symbol'])
                with trade.file_deadline():value=inspect(entry)
                result['objects'].append(value);result['metadata_files']=len(result['objects'])
                require(value['metadata_object_available'] and isinstance(value['announced_zip_bytes'],int)
                    and 0<value['announced_zip_bytes']<=BOUNDS['max_archive_bytes'],'Unavailable/oversize metadata; no retries or alternate hosts')
                guard()
        upstream=original.official_module(component)
        for entry in result['objects']:
            require(original.owned_bytes(run)+entry['announced_zip_bytes']+BOUNDS['file_write_limit_bytes']<=BOUNDS['new_owned_bytes'],'Single ZIP and working reservation')
            job=run/f"{entry['symbol']}-2h-2025-07";job.mkdir();receipt=dict(status='FAIL_D041_2H_ARCHIVE',entry=entry)
            try:
                progress.update('官方两小时档下载/CRC/完整UTC格式',result['actual_files'],2,'文件',symbol=entry['symbol'])
                with trade.file_deadline():
                    archive,checksum,csv_bytes=download(entry,job,upstream);result['archive_bodies_downloaded']+=1
                    frame,quality=convert(archive,entry,parsers);target=job/'source.parquet';frame.write_parquet(target,compression='zstd')
                    require(frame.height==372 and target.stat().st_size<=BOUNDS['file_write_limit_bytes'],'372 exact July2h bars and bounded normalized file')
                receipt.update(status='PASS_D041_2H_ARCHIVE_FORMAT_CALENDAR_ONLY',normalized_path=str(target),normalized_sha256=sha(target),
                    normalized_bytes=target.stat().st_size,rows=frame.height,quality=quality,normalized_schema={k:str(v) for k,v in frame.schema.items()},
                    zip_path=str(archive),zip_sha256=sha(archive),checksum_path=str(checksum),checksum_sha256=sha(checksum),zip_crc='PASS_FULL_READ',uncompressed_csv_bytes=csv_bytes)
                del frame;gc.collect();guard()
            except Exception as error:receipt.update(error_type=type(error).__name__,reason=str(error));raise
            finally:write(job/'receipt.json',receipt)
            result['sources'].append({k:receipt[k] for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema')}|
                dict(symbol=entry['symbol'],interval='2h',month='2025-07',format_evidence_role='PRODUCER_FORMAT_CALENDAR_ONLY_PENDING_INDEPENDENT_QA',receipt_path=str(job/'receipt.json'),receipt_sha256=sha(job/'receipt.json')))
            result['actual_files']=len(result['sources']);result['actual_source_rows']=sum(e['rows'] for e in result['sources'])
            progress.update('完整来源档已写入',result['actual_files'],2,'文件')
        require(result['actual_files']==2 and result['actual_source_rows']==744 and all(sha(ROOT/p)==h for p,h in hashes.items()),'Both sources complete and frozen bytes preserved')
        result.update(status=STATUS,rows_per_symbol=372,normalized_interval='2h',warmup_scope='31_FULL_UTC_DAYS_372_BARS_PER_ASSET')
    except Exception as error:result.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        result.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,owned_bytes=original.owned_bytes(run),resources_after=resources.status())
        write(out,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=args.experiment_id+':RESULT',event_type='OPERATIONAL_SOURCE_RESULT',
            success_failure=result['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],actual_files=result['actual_files'],output=str(out),sha256=sha(out))))


if __name__=='__main__':main()
