"""UNRUN independent QA of the 42 new USD-M trade archives only.

Raw CSV -> typed Parquet comparison follows the accepted audit_one method;
the old 24-file main, old mark/index/funding payloads and parsers are not called.
Root must freeze ACTUAL_BINDING.json after the producer actually exits zero.
CLI: --protocol --actual --run-dir --output. No network or account calculation.
"""
from __future__ import annotations
import argparse, csv, gc, hashlib, importlib.util, io, json, math, os, resource, sys, time, zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
import polars as pl
from quant import resources

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
GUARD = 'docs/archive/VOL_MANAGED_HOLD_547D_ROOT_CLOSE_SOURCE_20261003_V2.py'
GUARD_SHA = '278c9117283b88eb73b50276f37a4cd86449ffd87e747556db301dc146ce905a'
STATUS = 'PASS_NEW_USDM_TRADE_SOURCE_RAW_NORMALIZED_CALENDAR_VOLUME_ONLY'
DAY, MINUTE = 86_400_000_000, 60_000_000
HEADER = ['open_time','open','high','low','close','volume','close_time',
          'quote_volume','count','taker_buy_volume','taker_buy_quote_volume','ignore']
SCHEMA = ['open','high','low','close','volume','quote_volume','trade_count','taker_buy_base',
          'taker_buy_quote','open_us','close_us','available_us','symbol','interval','ingested_us','source_close_us']
FLOATS = ['open','high','low','close','volume','quote_volume','taker_buy_base','taker_buy_quote']
INTS = ['trade_count','open_us','close_us','available_us','ingested_us','source_close_us']
RAW_FLOATS = {1:'open',2:'high',3:'low',4:'close',5:'volume',7:'quote_volume',9:'taker_buy_base',10:'taker_buy_quote'}

def require(ok, message):
    if not ok: raise ValueError(message)

def sha(path):
    with Path(path).open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()

def guards():
    path = ROOT/GUARD
    require(sha(path)==GUARD_SHA and not path.is_symlink(),'Exact accepted small/task/path guards')
    spec = importlib.util.spec_from_file_location('trade_source_accepted_guards',path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module

def stamp(day): return int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp())*1_000_000

def months(first):
    year,month = map(int,first.split('-')); result=[]
    while (year,month)<(2026,3):
        result.append(f'{year:04d}-{month:02d}'); month+=1
        if month==13: year+=1;month=1
    return result

def entries():
    result=[]
    for interval,first in [('1d','2025-01'),('1m','2025-08')]:
        for symbol in ('BTCUSDT','ETHUSDT'):
            for month in months(first):
                url=f'https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/{interval}/{symbol}-{interval}-{month}.zip'
                result.append(dict(market='futures/um',partition='monthly',kind='klines',interval=interval,
                    symbol=symbol,month=month,url=url,checksum_url=url+'.CHECKSUM'))
    return result

def payload(path, root, expected_sha, maximum, expected_bytes=None):
    p=Path(path)
    require(p.is_absolute() and '..' not in p.parts and p.is_relative_to(root) and p.is_file(), 'Exact new source path')
    for ancestor in (p,*p.parents):
        require(not ancestor.is_symlink(),'No source symlink')
        if ancestor==STATE: break
    require(0<p.stat().st_size<=maximum and (expected_bytes is None or p.stat().st_size==expected_bytes)
            and sha(p)==expected_sha,'Actual new source bytes/SHA/bound')
    return p

def finite(raw):
    value=Decimal(raw)
    require(value.is_finite(),'Finite raw numeric trade field')
    result=float(value); require(math.isfinite(result),'Raw field fits normalized Float64')
    return result

def audit_one(g, item, entry, source_root, spec):
    job=source_root/f"{entry['symbol']}-{entry['interval']}-{entry['month']}"
    require(Path(item['receipt_path'])==job/'receipt.json','Exact new archive receipt selector')
    receipt,_=g.small(job/'receipt.json',item['receipt_sha256'])
    require(receipt['status']=='PASS_USDM_TRADE_ARCHIVE_FORMAT_CALENDAR_ONLY'
        and {key:receipt['entry'][key] for key in entry}==entry,'Actual completed selected trade conversion')
    for key in ('normalized_path','normalized_sha256','normalized_bytes','rows','quality','normalized_schema'):
        require(receipt[key]==item[key],'Top receipt/per-file binding: '+key)
    require(Path(item['normalized_path'])==job/'source.parquet','Exact normalized new file')
    parquet=payload(item['normalized_path'],job,item['normalized_sha256'],spec['budgets']['file_write_limit_bytes'],item['normalized_bytes'])
    archive=payload(receipt['zip_path'],job,receipt['zip_sha256'],spec['budgets']['max_archive_bytes'],receipt['entry']['announced_zip_bytes'])
    checksum=payload(receipt['checksum_path'],job,receipt['checksum_sha256'],65_536)
    name=f"{entry['symbol']}-{entry['interval']}-{entry['month']}.zip"
    fields=checksum.read_text().split()
    require(archive.name==name and checksum.name==name+'.CHECKSUM' and len(fields)==2
        and fields[0].lower()==receipt['zip_sha256']==receipt['entry']['checksum']['announced_zip_sha256']
        and fields[1].lstrip('*')==name,'Actual saved official CHECKSUM/archive identity')
    frame=pl.read_parquet(parquet)
    require(frame.columns==SCHEMA and {k:str(v) for k,v in frame.schema.items()}==item['normalized_schema']
        and all(frame.schema[n]==pl.Float64 for n in FLOATS) and all(frame.schema[n]==pl.Int64 for n in INTS)
        and all(frame.schema[n]==pl.String for n in ('symbol','interval')) and sum(frame.null_count().row(0))==0,
        'Original complete typed trade schema, no null/imputation')
    first=entry['month']+'-01'; year,month=map(int,entry['month'].split('-'))
    end=f'{year+1:04d}-01-01' if month==12 else f'{year:04d}-{month+1:02d}-01'
    start,stop=stamp(first),stamp(end); duration=DAY if entry['interval']=='1d' else MINUTE
    expected=range(start,stop,duration)
    require(frame.height==len(expected)==item['rows'] and frame['open_us'].to_list()==list(expected)
        and frame['close_us'].to_list()==[t+duration for t in expected]
        and frame['available_us'].to_list()==frame['close_us'].to_list()
        and frame['source_close_us'].to_list()==[t+duration-1000 for t in expected],
        'All exclusive UTC closes/availability proxy and raw inclusive millisecond clock')
    require(frame['symbol'].unique().to_list()==[entry['symbol']]
        and frame['interval'].unique().to_list()==[entry['interval']]
        and frame['ingested_us'].n_unique()==1 and frame['ingested_us'][0]>0,
        'Exact product/interval and declared ingestion clock; ingestion is not publication')
    require(frame.select(pl.all_horizontal(pl.col(FLOATS).is_finite()).all()).item()
        and frame.filter((pl.col('low')<=0)|(pl.col('high')<pl.max_horizontal('open','close','low'))
            |(pl.col('low')>pl.min_horizontal('open','close','high'))
            |pl.any_horizontal(pl.col(['volume','quote_volume','trade_count','taker_buy_base','taker_buy_quote'])<0)
            |(pl.col('taker_buy_base')>pl.col('volume')*(1+1e-8))).height==0,
        'Finite OHLC envelope and retained nonnegative volume/count; original tolerance unchanged')
    observed=None; count=0; rows=frame.iter_rows(named=True)
    with zipfile.ZipFile(archive) as zipped:
        members=zipped.infolist()
        require(len(members)==1 and members[0].filename==name[:-4]+'.csv'
            and not members[0].is_dir() and 0<members[0].file_size==receipt['uncompressed_csv_bytes']<=spec['budgets']['max_csv_bytes'],
            'One bounded original CSV member; no extraction')
        with zipped.open(members[0]) as stream, io.TextIOWrapper(stream,encoding='utf-8-sig',newline='') as text:
            for raw in csv.reader(text):
                if count==0 and observed is None and raw and raw[0]=='open_time':
                    require(raw==HEADER,'Exact optional official trade header'); observed=raw; continue
                require(len(raw)==12 and count<frame.height,'Raw CSV width/count, no ignored extra rows')
                row=next(rows)
                opened,closed,trades=int(raw[0]),int(raw[6]),int(raw[8])
                require(opened*1000==row['open_us'] and closed*1000==row['source_close_us']
                    and trades==row['trade_count'],'Every raw integer millisecond/count value retained')
                require(all(finite(raw[index])==row[column] for index,column in RAW_FLOATS.items()),
                    'Every original OHLCV/quote/taker value equals normalized Float64')
                finite(raw[11]); count+=1
        require(count==frame.height,'Full new CSV EOF/CRC reached without row drop')
    quality=item['quality']
    require(quality['rows']==count and quality['timestamp_unit']=='milliseconds'
        and all(quality[k]==0 for k in ('duplicate_rows','bad_timestamps','bad_values','gaps'))
        and quality['incomplete_days']==quality['nonstandard_closes']==[] and quality['observed_header']==observed
        and quality['first_open_us']==start and quality['last_open_us']==stop-duration and quality['last_close_us']==stop,
        'Independent actual calendar/values agree with published quality')
    require(sha(parquet)==item['normalized_sha256'] and sha(archive)==receipt['zip_sha256']
        and sha(checksum)==receipt['checksum_sha256'],'Selected new input bytes unchanged during full read')
    return dict(symbol=entry['symbol'],interval=entry['interval'],month=entry['month'],rows=count,
        first_open_us=start,last_open_us=stop-duration,last_close_us=stop,header=observed,
        normalized_path=str(parquet),normalized_sha256=item['normalized_sha256'],receipt_sha256=item['receipt_sha256'],
        zip_sha256=receipt['zip_sha256'],checksum_sha256=receipt['checksum_sha256'],
        all_raw_normalized_values_equal=True,full_CSV_EOF_and_CRC_read=True,raw_timestamp_unit='EPOCH_MILLISECONDS')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('protocol','actual','run-dir','output'): parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();g=guards();own_sha=sha(__file__);task=os.environ.get('COIN_TASK_ID')
    require(task and Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2' and pl.thread_pool_size()<=2,'Actual bounded clean CPU2/progress runtime')
    require(args.run_dir.parent==STATE and args.run_dir.is_dir() and not args.run_dir.is_symlink()
        and {p.name for p in args.run_dir.iterdir()}=={'ACTUAL_BINDING.json'}
        and args.output.parent==ROOT/'reports/fast_research' and not args.output.exists(),'New independent manifest-only STATE/output')
    plan,plan_sha=g.small(args.run_dir/'ACTUAL_BINDING.json')
    require(plan['ready_to_execute'] is True and plan['checker_sha256']==own_sha
        and plan['protocol_path']==str(args.protocol.relative_to(ROOT))
        and plan['actual_report']==str(args.actual.relative_to(ROOT)),'Frozen exact independent invocation')
    require(all(type(plan['budgets'][k]) is int and 0<plan['budgets'][k]<=v for k,v in
        {'peak_RSS_bytes':1_000_000_000,'wall_seconds':600,'new_owned_bytes':5_000_000}.items()),
        'Independent preregistered RSS1GB/wall600s/small5MB maximum')
    binding=dict(task_id=task,checker_sha256=own_sha,ACTUAL_BINDING_sha256=plan_sha,
        actual_reports={str(args.actual):plan['actual_report_sha256']},source_hashes=plan['source_hashes'])
    g.write(args.run_dir/'RUN_BINDING.json',binding);started=time.monotonic();before=resources.status()
    report=dict(status='FAIL_NEW_USDM_TRADE_INDEPENDENT_SOURCE_QA',binding=binding,run_dir=str(args.run_dir),
        run_binding_sha256=sha(args.run_dir/'RUN_BINDING.json'),independent_source_sha256=own_sha,sources=[],
        funding_rate_unit='UNCONFIRMED',funding_unit_certified=False,publication_time_certified=False,
        native_market_or_execution_certified=False,economics='NOT_EVALUATED',
        old_mark_index_funding_QA_repeated=False,source_only=True,models_fit=0,orders_sent=0,GPU=0,
        locked_consumed=False,candidate_status='NO_QUALIFIED_CANDIDATE',own_completion='LIVE_CALLER_NOT_SELF_CERTIFIED')
    error=None;progress=None
    try:
        g.bounded(before);spec,proto_sha=g.small(args.protocol,plan['protocol_sha256'])
        actual,actual_sha=g.small(args.actual,plan['actual_report_sha256'])
        require(spec['contract_id']=='USD_M_TRADE_KLINE_SOURCE_20261003_V1' and spec['entries']==entries()
            and spec['funding_rate_unit']=='UNCONFIRMED' and not spec['funding_read_or_zero_filled'],'Fixed42 new trade scope only')
        require(actual['status']=='PASS_USDM_TRADE_KLINE_FORMAT_CALENDAR_PENDING_INDEPENDENT_ACCEPTANCE'
            and actual['actual_files']==actual['required_files']==actual['archive_bodies_downloaded']==42
            and len(actual['sources'])==42 and actual['binding']['task_id']==plan['actual_task_id']
            and actual['binding']['protocol_sha256']==proto_sha and actual['binding']['source_hashes']==spec['frozen_sources']
            and not actual['old_source_QA_repeated'] and not actual['locked_consumed']
            and not actual['funding_unit_certified'] and actual['funding_rate_unit']=='UNCONFIRMED'
            and actual['models_fit']==actual['orders_sent']==actual['GPU']==0,'Actual complete new source, no economic or unit promotion')
        report['actual_task']=g.closed(plan['actual_task_id']);source_root=Path(spec['run_dir'])
        require(source_root.parent==STATE and source_root.name=='perpetual-trade-source-actual-20261003-v1','Exact dedicated new source ROOT')
        rb,rb_sha=g.small(source_root/'RUN_BINDING.json',actual['run_binding_sha256'])
        require(rb==actual['binding'],'Producer actual RUN_BINDING identity')
        verified={str(args.protocol.relative_to(ROOT)):proto_sha,str(args.actual.relative_to(ROOT)):actual_sha}
        require(all(name not in spec['frozen_sources'] or spec['frozen_sources'][name]==digest
            for name,digest in plan['source_hashes'].items()),'Independent dependencies cannot override producer pins')
        for name,digest in {**spec['frozen_sources'],**plan['source_hashes']}.items():
            require(name not in verified or verified[name]==digest,'No conflicting source hash map')
            g.small(g.project(name),digest,False);verified[name]=digest
        require(plan['source_hashes'].get(GUARD)==GUARD_SHA,'Accepted guards pinned')
        from scripts.research_v8.funding_price_source_v2 import progress_writer
        progress=progress_writer(42);progress.value['detail']='仅新USD-M成交K线：原CSV/UTC/真实量；非单位、收益或发单资格'
        for item,entry in zip(actual['sources'],entries(),strict=True):
            require({k:item[k] for k in ('symbol','interval','month')}=={k:entry[k] for k in ('symbol','interval','month')},'No missing/duplicate/substituted source selector')
            progress.update('新成交来源独立原值核对',len(report['sources']),42,'文件',symbol=entry['symbol'],interval=entry['interval'],month=entry['month'])
            report['sources'].append(audit_one(g,item,entry,source_root,spec));gc.collect()
            require(time.monotonic()-started<=plan['budgets']['wall_seconds']
                and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<=plan['budgets']['peak_RSS_bytes'],'Independent process frozen resource bound')
        totals={};cross=[]
        for symbol in ('BTCUSDT','ETHUSDT'):
            for interval,expected_rows in [('1d',424),('1m',305280)]:
                rows=[r for r in report['sources'] if r['symbol']==symbol and r['interval']==interval]
                require(all(a['last_close_us']==b['first_open_us'] for a,b in zip(rows,rows[1:])), 'All month joins continuous, no gap/overlap')
                require(sum(r['rows'] for r in rows)==expected_rows,'Complete fixed interval calendar row count')
                totals[symbol+'_'+interval]=expected_rows;cross.append(dict(symbol=symbol,interval=interval,passed=True,month_joins=len(rows)-1))
        for name,digest in verified.items():g.small(g.project(name),digest,False)
        report.update(status=STATUS,verified_source_hashes=verified,actual_report_sha256=actual_sha,
            actual_run_binding_sha256=rb_sha,row_totals=totals,crossmonth=cross,
            completed_files_verified=42,completed_daily_rows_verified=848,completed_minute_rows_verified=610560,
            completed_rows_verified=611408,source_fingerprint_portability='EXACT_SAVED_FILE_BYTES_NOT_RE_SERIALIZED_FRAME')
    except Exception as caught:
        error=caught;report['failure']=dict(type=type(caught).__name__,reason=str(caught))
    finally:
        report.update(completed_files_verified=len(report['sources']),elapsed_seconds=time.monotonic()-started,
            peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_before=before,resources_after=resources.status())
        try:g.bounded(report['resources_after'])
        except Exception as caught:
            error=error or caught;report.update(status='FAIL_NEW_USDM_TRADE_INDEPENDENT_SOURCE_QA',budget_error=str(caught))
        if progress:progress.stop.set();progress.thread.join(timeout=3)
        if report['peak_RSS_bytes']>plan['budgets']['peak_RSS_bytes'] or report['elapsed_seconds']>plan['budgets']['wall_seconds']:
            error=error or RuntimeError('Frozen independent process bound exceeded');report.update(status='FAIL_NEW_USDM_TRADE_INDEPENDENT_SOURCE_QA',budget_error=str(error))
        digest,output_bytes=g.write(args.output,report)
        require(sum(p.stat().st_size for p in args.run_dir.iterdir() if p.is_file())+output_bytes<=plan['budgets']['new_owned_bytes'],'Small independent metadata budget')
        print(json.dumps(dict(status=report['status'],report=str(args.output),sha256=digest,completed_files=report['completed_files_verified'])),flush=True)
    if error:raise error

if __name__=='__main__':main()
