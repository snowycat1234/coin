"""D037: thin official monthly Spot1d source adapter; no old database writes.

Reuse pinned Binance utility.download_file and accepted archive orchestration,
and private quant.data.parse_csv with explicit daily interval/calendar anchors.
No price acquisition or source acceptance occurs merely by importing this file.
"""
from __future__ import annotations
import argparse, ast, io, json, os, resource, shlex, subprocess, sys, time, zipfile
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
import httpx
import polars as pl
from quant import data as original_data, disk, resources
from quant.paths import ROOT, STATE, utc_now_us
from scripts.research_v8 import funding_price_source_v2 as original_source
from scripts.research_v8.registry import FIELDS, append_event
from scripts.investment.official_carry_chronology_source import metadata_inspector

DAY_US=86_400_000_000
SYMBOLS=['BTCUSDT','ETHUSDT']
MONTHS=original_data.month_range('2023-06','2026-02')
START,END='2023-06-01','2026-03-01'
STATUS='PASS_D037_OFFICIAL_SPOT_DAILY_SOURCE_FORMAT_AND_CALENDAR_ONLY'
COMPONENT='reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json'
PINS={
 'src/quant/data.py':'d6574aa1964b03f9d9a2a110365d47f8210eccfadb1ac11c391b4c8fb3f7862e',
 'scripts/research_v8/funding_price_source_v2.py':'2f39c9803051373654094ee990474b3ebe9b241ef85fa9eb586b9bde92bb4cdb',
 'scripts/investment/official_carry_chronology_source.py':'889954bb2a6b12d480742cfdde2b01bbdaaf26e28250c8f4eac506acf8380e64',
 'scripts/investment/bybit_spot_adapter.py':'8c8852bf70813ada5720c210f50c9038a5ecaadee1b4f38b77a71aa9e8b038ca',
 'docs/archive/V8_OFFICIAL_INPUT_METADATA_SOURCE_20261002_V1.py':'d2e419dcbc05c3a1f71ee147a2ec5307ee49918106a206bc72cb3d19ea15aa5c',
 COMPONENT:'8a2ae22bd5bbf60763df352abb50d380763ba1fe19ac6545cc398f8d45d3ce96'}
BOUNDS=dict(new_owned_bytes=10_000_000,max_archive_bytes=32_768,
 max_csv_bytes=65_536,max_parquet_bytes=32_768)
SCHEMA=['open','high','low','close','volume','quote_volume','trade_count','taker_buy_base',
 'taker_buy_quote','open_us','close_us','available_us','symbol','interval','ingested_us','source_close_us']
sha=original_data.sha256_file
require=original_source.require
write=original_source.write_new


def stamp(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp())*1_000_000


def exact_patch():
    """Reuse only the existing AST patch utility, without importing finance code."""
    path=ROOT/'scripts/investment/bybit_spot_adapter.py'
    names={'_digest','_one_statement','_ExactPatch','_replace'}
    nodes=[n for n in ast.parse(path.read_bytes()).body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    require({n.name for n in nodes}==names and len(nodes)==4,'Four exact accepted AST utility definitions')
    namespace=dict(ast=ast,deepcopy=deepcopy)
    exec(compile(ast.Module(nodes,type_ignores=[]),str(path)+'<AST_UTILITIES_ONLY>','exec'),namespace)
    return namespace['_replace']


def adapted_functions():
    patch=exact_patch();changes=[]
    def tree(path,name):
        nodes=[n for n in ast.parse((ROOT/path).read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name==name]
        require(len(nodes)==1,'One pinned reusable function: '+name)
        return ast.Module(nodes,type_ignores=[])
    download=tree('scripts/research_v8/funding_price_source_v2.py','download_archive')
    download=patch(download,changes,'Spot1d exact URL guard',
        "url=entry['url'];require(url.startswith('https://data.binance.vision/data/futures/um/monthly/'),'Unexpected upstream URL')".split(';')[1],
        "require(url.startswith('https://data.binance.vision/data/spot/monthly/klines/'),'Unexpected upstream URL')")
    download=patch(download,changes,'Small1d archive bound',
        "require(entry['metadata_object_available'] and 0<entry['announced_zip_bytes']<=2_000_000,'Required small archive metadata unavailable')",
        "require(entry['metadata_object_available'] and 0<entry['announced_zip_bytes']<=32_768,'Required small archive metadata unavailable')")
    download=patch(download,changes,'Small1d OS write bound',
        'resource.setrlimit(resource.RLIMIT_FSIZE,(4_000_000,prior_limit[1]))',
        'resource.setrlimit(resource.RLIMIT_FSIZE,(32_768,prior_limit[1]))')
    namespace=dict(original_source.__dict__);namespace['LIMIT']=BOUNDS['max_csv_bytes']
    exec(compile(ast.fix_missing_locations(download),'<private-Spot1d-official-download>','exec'),namespace)
    parser=tree('src/quant/data.py','parse_csv')
    parser=patch(parser,changes,'One complete UTC day per daily source row',
        'dates=(frame.with_columns((pl.col("open_us") // (MINUTE_US * 1440)).alias("day")).group_by("day").len().sort("day"))',
        'dates=(frame.with_columns((pl.col("open_us") // MINUTE_US).alias("day")).group_by("day").len().sort("day"))')
    parser=patch(parser,changes,'Daily one-row calendar check',
        'bad_days=[{"date":datetime.fromtimestamp(row[0] * 86400,UTC).date().isoformat(),"rows":row[1]} for row in dates.iter_rows() if row[1] != 1440]',
        'bad_days=[{"date":datetime.fromtimestamp(row[0] * 86400,UTC).date().isoformat(),"rows":row[1]} for row in dates.iter_rows() if row[1] != 1]')
    parser=patch(parser,changes,'Daily interval label only',
        '''frame=frame.sort("open_us").with_columns(
            (pl.col("open_us") + MINUTE_US).alias("close_us"),
            (pl.col("open_us") + MINUTE_US).alias("available_us"),
            pl.lit(symbol).alias("symbol"), pl.lit("1m").alias("interval"),
            pl.lit(ingested_us).alias("ingested_us"),
            (pl.col("raw_close") * scale).alias("source_close_us"))''',
        '''frame=frame.sort("open_us").with_columns(
            (pl.col("open_us") + MINUTE_US).alias("close_us"),
            (pl.col("open_us") + MINUTE_US).alias("available_us"),
            pl.lit(symbol).alias("symbol"), pl.lit("1d").alias("interval"),
            pl.lit(ingested_us).alias("ingested_us"),
            (pl.col("raw_close") * scale).alias("source_close_us"))''')
    parsed_namespace=dict(original_data.__dict__);parsed_namespace['MINUTE_US']=DAY_US
    exec(compile(ast.fix_missing_locations(parser),'<private-original-parse_csv-daily>','exec'),parsed_namespace)
    return namespace['download_archive'],parsed_namespace['parse_csv'],changes


def source_frame(archive,entry,parse):
    opened_ms,closed_ms=original_source.month_range(entry['month'])
    with zipfile.ZipFile(archive) as zipped:
        member=zipped.infolist()[0]
        require(member.file_size<=BOUNDS['max_csv_bytes'],'Small CSV hard bound before reading')
        content=zipped.read(member)
    frame,quality=parse(content,entry['symbol'],utc_now_us())
    expected_unit='milliseconds' if entry['month']<'2025-01' else 'microseconds'
    scale=1000 if expected_unit=='milliseconds' else 1
    expected=list(range(opened_ms*1000,closed_ms*1000,DAY_US))
    require(frame.columns==SCHEMA and quality['timestamp_unit']==expected_unit,'Original normalized daily schema/raw unit regime')
    require(all(quality[k]==0 for k in ('duplicate_rows','bad_timestamps','bad_values','gaps'))
        and not quality['incomplete_days'] and not quality['nonstandard_closes'],'Complete daily format; no row repair or timestamp anomalies')
    require(frame['open_us'].to_list()==expected and frame.height==len(expected),'Exact whole monthly UTC daily calendar')
    require(frame.null_count().row(0)==(0,)*len(SCHEMA),'No null normalized field or availability')
    require(frame['close_us'].to_list()==[t+DAY_US for t in expected]
        and frame['available_us'].to_list()==frame['close_us'].to_list()
        and frame['source_close_us'].to_list()==[t+DAY_US-scale for t in expected], 'Exclusive day close / source-inclusive close / closure proxy availability')
    require(frame['symbol'].unique().to_list()==[entry['symbol']] and frame['interval'].unique().to_list()==['1d'],'Fixed symbol/interval')
    types=dict(frame.schema)
    require(all(types[n]==pl.Float64 for n in ('open','high','low','close','volume','quote_volume','taker_buy_base','taker_buy_quote'))
        and all(types[n]==pl.Int64 for n in ('trade_count','open_us','close_us','available_us','ingested_us','source_close_us'))
        and all(types[n]==pl.String for n in ('symbol','interval')),'Fixed normalized physical types')
    quality.update(exact_month_daily_calendar=True,first_open_us=expected[0],last_open_us=expected[-1],
        last_close_us=expected[-1]+DAY_US,availability='UTC_EXCLUSIVE_CLOSED_DAY_PROXY_NOT_PUBLICATION_CERTIFIED',
        price_semantics='OFFICIAL_SPOT_KLINE_CLOSE_LAST_TRADE_PRICE_NOT_BBO_OR_EXECUTABLE_FILL',header=None)
    return frame,quality


def validate(spec):
    require(spec['contract_id']=='D037_OFFICIAL_SPOT_DAILY_SOURCE_V1'
        and spec['source_start']==START and spec['source_end_exclusive']==END
        and spec['source_calendar']==MONTHS and spec['symbols']==SYMBOLS and spec['expected_archives']==66
        and spec['expected_days_per_symbol']==1004 and spec['expected_total_rows']==2008,'Fixed minimum daily source universe')
    require(all(spec['budgets'][k]==v for k,v in BOUNDS.items())
        and 0<spec['budgets']['wall_seconds']<=1800 and 0<spec['budgets']['peak_RSS_bytes']<=1_000_000_000,
        'Source10MB/RAM/wall hard budget')
    require(spec['compressed_bytes_expected'] is None and spec['source_acceptance_before_actual'] is False
        and spec['publication_time_certified'] is False and spec['economic_scope']=='NOT_EVALUATED','Unknown sizes and no fictitious source/economic certification')
    entries=spec['entries']
    require(len(entries)==66 and {(e['symbol'],e['month']) for e in entries}=={(s,m) for s in SYMBOLS for m in MONTHS},'Exactly66 unique authorized month/symbol sources')
    for entry in entries:
        url=f"https://data.binance.vision/data/spot/monthly/klines/{entry['symbol']}/1d/{entry['symbol']}-1d-{entry['month']}.zip"
        require(entry['market']=='spot' and entry['kind']=='klines' and entry['partition']=='monthly'
            and entry['interval']=='1d' and entry['url']==url and entry['checksum_url']==url+'.CHECKSUM'
            and all(entry[k] is None for k in ('metadata_object_available','announced_zip_bytes','announced_zip_sha256','actual_source_rows')),
            'Frozen official URL and genuinely unknown metadata')
    return entries


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for arg in ('protocol','run-dir','output'):parser.add_argument('--'+arg,type=Path,required=True)
    parser.add_argument('--experiment-id',required=True);args=parser.parse_args()
    run,out,protocol=args.run_dir.resolve(),args.output.resolve(),args.protocol.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists() and out.is_relative_to(ROOT/'reports/fast_research')
        and not out.exists() and protocol.is_relative_to(ROOT/'protocols') and os.environ.get('COIN_TASK_ID'),'New exclusive bounded/progress source task')
    spec=json.loads(protocol.read_bytes());entries=validate(spec);before=resources.status()
    require(run==Path(spec['run_dir']).resolve() and out==(ROOT/spec['output_path']).resolve()
        and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Frozen source output and clean CPU environment')
    hashes=spec['frozen_sources'];own=Path(__file__).resolve().relative_to(ROOT).as_posix()
    require(own in hashes and all(hashes.get(p)==h for p,h in PINS.items()),'New entry and exact reused components explicitly pinned')
    for p,h in hashes.items():require((ROOT/p).resolve().is_relative_to(ROOT) and sha(ROOT/p)==h,'Frozen source bytes changed: '+p)
    component=json.loads((ROOT/COMPONENT).read_bytes())
    require(component['status']=='PINNED_OFFICIAL_DOWNLOAD_COMPONENT_STAGED_NO_MARKET_DATA'
        and component['commit']==spec['upstream_commit']=='f446ce3812bd4e5521f21faecd4ae3c6460e49fc', 'Already staged official unchanged download software')
    download,parse,changes=adapted_functions();run.mkdir()
    binding=dict(task_id=os.environ['COIN_TASK_ID'],protocol_path=str(protocol),protocol_sha256=sha(protocol),source_hashes=hashes,
        source_path=str(Path(__file__).resolve()),source_sha256=sha(__file__),exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),sys_prefix=sys.prefix,
        spec=dict(source_calendar=MONTHS,source_scope='JUN2023_FEB2026',source_start=START,source_end_exclusive=END,
            symbols=SYMBOLS,days_per_symbol=1004),official_files=component['files'],AST_changes=changes,
        scalar_namespace_change=dict(parse_csv_MINUTE_US=DAY_US,download_LIMIT=BOUNDS['max_csv_bytes']))
    write(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);event.update(experiment_id=args.experiment_id,event_id=args.experiment_id+':START',event_type='OPERATIONAL_SOURCE_START',
        git_commit=binding['git_commit'],data_manifest_hash=original_source.hashlib.sha256(json.dumps(entries,sort_keys=True).encode()).hexdigest(),
        protocol_hash=binding['protocol_sha256'],feature_set='OFFICIAL_SPOT_1D_SOURCE_ONLY',labels='NONE',model_family='NONE',
        hyperparameters={'months':MONTHS,'symbols':SYMBOLS,'AST_changes':changes},seed=None,thresholds=spec['budgets'],cost_assumptions='NOT_EVALUATED',
        all_folds='JUN2023_FEB2026_SOURCE_ONLY',success_failure='START_BEFORE_NETWORK_AND_ROWS',reason_for_next_experiment='Provide200completeUTCdailywarmup without expanding1m downloads',
        source_hashes=hashes,exact_command=binding['exact_command'],run_binding_sha256=sha(run/'RUN_BINDING.json'),result_influenced_later_choice=False)
    result=dict(status='FAIL_D037_OFFICIAL_SPOT_DAILY_SOURCE_UNACCEPTED',binding=binding,run_binding_sha256=sha(run/'RUN_BINDING.json'),
        registration_start=append_event(ROOT/'reports/experiment_registry.jsonl',event),sources=[],metadata=[],required_archives=66,
        metadata_completed_files=0,completed_files=0,actual_total_rows=0,rows_per_symbol={s:0 for s in SYMBOLS},resources_before=before,
        source_only=True,source_acceptance_granted=False,publication_time_certified=False,economic_scope='NOT_EVALUATED',
        old_1m_QA_repeated=False,old_database_written=False,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
    progress=original_source.progress_writer(66);progress.value['detail']='官方Spot日线新来源格式与完整UTC日；不是APR或执行资格'
    started=time.monotonic();client=None;clocks={s:[] for s in SYMBOLS}
    def budget():
        require(original_source.owned_bytes(run)<=BOUNDS['new_owned_bytes'], 'Hard10MB new source budget; preserve partial failure')
        require(time.monotonic()-started<=spec['budgets']['wall_seconds'], 'Source wall budget exceeded')
        require(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=spec['budgets']['peak_RSS_bytes'],'Source peak RAM budget exceeded')
    try:
        progress.update('真实容量扫描，总量未知',0,None,'扫描');scan=datetime.now(UTC).isoformat()
        result['disk']=dict(**disk.check(BOUNDS['new_owned_bytes']),scan_started_utc=scan,scan_finished_utc=datetime.now(UTC).isoformat())
        require(result['disk']['total_bytes']+BOUNDS['new_owned_bytes']<=32_000_000_000,'Expected32GB source capacity guard')
        upstream=original_source.official_module(component)
        client=httpx.Client(timeout=httpx.Timeout(12,connect=10),follow_redirects=False)
        inspect=metadata_inspector(client);resolved=[]
        for entry in entries:
            progress.update('官方1d HEAD/CHECKSUM，实际大小待核',len(resolved),66,'文件')
            value=inspect(entry);write(run/('metadata-'+entry['symbol']+'-'+entry['month']+'.json'),value)
            result['metadata'].append(value);result['metadata_completed_files']=len(result['metadata'])
            require(value['metadata_object_available'] and isinstance(value['announced_zip_bytes'],int)
                and 0<value['announced_zip_bytes']<=BOUNDS['max_archive_bytes'], 'Missing/restricted/oversized archive; stop without alternate source or retry')
            resolved.append(value);budget()
        result['announced_compressed_zip_bytes']=sum(e['announced_zip_bytes'] for e in resolved)
        for entry in resolved:
            job=run/(entry['symbol']+'-'+entry['month']);job.mkdir();receipt=dict(status='FAIL_NEW_DAILY_SOURCE',entry=entry)
            try:
                progress.update('官方1d下载/格式/UTC完整性',result['completed_files'],66,'文件',月份=entry['month'],币种=entry['symbol'])
                archive,checksum,csv_bytes=download(entry,job,upstream);budget()
                frame,quality=source_frame(archive,entry,parse)
                normalized=job/'source.parquet';frame.write_parquet(normalized,compression='zstd')
                require(normalized.stat().st_size<=BOUNDS['max_parquet_bytes'],'Normalized daily file hard bound')
                receipt.update(status='PASS_NEW_OFFICIAL_DAILY_ARCHIVE_FORMAT_CALENDAR',zip_path=str(archive),zip_sha256=sha(archive),
                    checksum_path=str(checksum),checksum_sha256=sha(checksum),zip_crc='PASS_FULL_READ',uncompressed_csv_bytes=csv_bytes,
                    normalized_path=str(normalized),normalized_sha256=sha(normalized),normalized_bytes=normalized.stat().st_size,
                    rows=frame.height,quality=quality,normalized_schema={k:str(v) for k,v in frame.schema.items()})
                clocks[entry['symbol']].extend(frame['open_us'].to_list())
            except Exception as error:receipt.update(error_type=type(error).__name__,reason=str(error));raise
            finally:write(job/'receipt.json',receipt)
            result['sources'].append({k:receipt[k] for k in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema')}|
                dict(symbol=entry['symbol'],month=entry['month'],receipt_path=str(job/'receipt.json'),receipt_sha256=sha(job/'receipt.json')))
            result['completed_files']=len(result['sources']);result['rows_per_symbol'][entry['symbol']]+=receipt['rows']
            result['actual_total_rows']+=receipt['rows'];budget()
        expected=list(range(stamp(START),stamp(END),DAY_US))
        require(all(sorted(clocks[s])==expected and len(clocks[s])==1004 for s in SYMBOLS)
            and result['completed_files']==66 and result['actual_total_rows']==2008,'Full1004day per-symbol common calendar, no overlaps or gaps')
        require(all(sha(ROOT/p)==h for p,h in hashes.items()),'Frozen source bytes unchanged')
        result.update(status=STATUS,days_per_symbol=1004,source_files=66,actual_daily_rows=2008,full_common_calendar=True,
            initial_2024_score_completed_warmup_days=214,source_bytes_unchanged=True,availability_definition='exclusive_closed_UTC_day_proxy_not_actual_publication')
        progress.update('新官方日线格式与完整日历完成',66,66,'文件')
    except Exception as error:result.update(error_type=type(error).__name__,reason=str(error));raise
    finally:
        if client is not None:client.close()
        result.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,owned_bytes=original_source.owned_bytes(run),resources_after=resources.status())
        if result['owned_bytes']+len(json.dumps(result,ensure_ascii=False).encode())>BOUNDS['new_owned_bytes']:
            result.update(status='FAIL_D037_OFFICIAL_SPOT_DAILY_SOURCE_UNACCEPTED',reason='Final10MB source/report budget exceeded')
        write(out,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=args.experiment_id+':RESULT',event_type='OPERATIONAL_SOURCE_RESULT',
            success_failure=result['status'],artifact_path=str(out.relative_to(ROOT)),artifact_sha256=sha(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    require(result['status']==STATUS,'Preserved source failure, not accepted')
    print(json.dumps(dict(status=result['status'],source_files=result['source_files'],output=str(out),sha256=sha(out))))


if __name__=='__main__':main()
