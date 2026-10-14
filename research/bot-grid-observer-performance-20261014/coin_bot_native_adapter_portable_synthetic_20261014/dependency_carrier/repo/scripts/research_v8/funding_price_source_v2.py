"""Fixed 24 official carry-input archives: upstream download_file, source QA only."""
from __future__ import annotations
import argparse,ast,contextlib,csv,hashlib,importlib.util,io,json,math,os,resource,signal,socket,subprocess,sys,threading,time,zipfile
from collections import Counter
from datetime import UTC,date,datetime,timedelta
from pathlib import Path
import pyarrow as pa
import pyarrow.parquet as pq
from quant import disk,resources
from quant.paths import ROOT,STATE

sys.path.insert(0,str(ROOT))
from scripts.research_v8.registry import FIELDS,append_event,canonical

META_SHA='7d1fdfb19b406c41ed6d3634dedb37081ffd00f2306160d23183f3701e474217'
LIMIT=1_000_000_000
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
def require(condition,message):
    if not condition:raise ValueError(message)
def write_new(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,ensure_ascii=False,allow_nan=False);stream.write('\n')
def month_range(month):
    first=date.fromisoformat(month+'-01')
    last=(first.replace(day=28)+timedelta(days=4)).replace(day=1)
    return int(datetime.combine(first,datetime.min.time(),UTC).timestamp()*1000),int(datetime.combine(last,datetime.min.time(),UTC).timestamp()*1000)
def owned_bytes(run):return sum(p.stat().st_size for p in run.rglob('*') if p.is_file())

def progress_writer(total):
    source=ROOT/'scripts/research_v7/oracle_flow_ceiling.py'
    node=next(n for n in ast.parse(source.read_bytes()).body if isinstance(n,ast.ClassDef) and n.name=='Progress')
    namespace={'os':os,'Path':Path,'STATE':STATE,'threading':threading,'time':time,'json':json}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(source),'exec'),namespace)
    progress=namespace['Progress'].__new__(namespace['Progress'])
    progress.pid=os.getpid();progress.ticks=int(Path(f'/proc/{progress.pid}/stat').read_text().split(') ',1)[1].split()[19])
    progress.value={'pid':progress.pid,'start_ticks':progress.ticks,'task_id':os.environ.get('COIN_TASK_ID'),
        'phase':'冻结来源与容量核对','completed':0,'total':total,'unit':'文件','metrics':{},'detail':'官方资金费/价格代理来源QA；不是收益或执行资格'}
    progress.stop=threading.Event();progress.thread=threading.Thread(target=progress.heartbeat,daemon=True);progress.thread.start()
    return progress

def official_module(component):
    for item in component['files']:require(sha(item['path'])==item['sha256'],'Pinned official source changed')
    folder=Path(component['files'][0]['path']).parent
    require(folder.is_relative_to(STATE),'Official source outside D-hosted STATE')
    sys.path.insert(0,str(folder))
    spec=importlib.util.spec_from_file_location('v8_official_binance_utility',folder/'utility.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    require(module.BASE_URL=='https://data.binance.vision/','Official BASE_URL differs')
    return module

def download_archive(entry,run,upstream):
    require(entry['metadata_object_available'] and 0<entry['announced_zip_bytes']<=2_000_000,'Required small archive metadata unavailable')
    url=entry['url'];require(url.startswith('https://data.binance.vision/data/futures/um/monthly/'),'Unexpected upstream URL')
    relative=url.removeprefix('https://data.binance.vision/');base,name=relative.rsplit('/',1);base+='/'
    require(not any(p.is_symlink() for p in run.rglob('*')),'Owned STATE symlink forbidden')
    raw_root=run/'raw';raw_root.mkdir()
    socket.setdefaulttimeout(30)
    prior_limit=resource.getrlimit(resource.RLIMIT_FSIZE)
    def bound_error(_signum,_frame):raise RuntimeError('Official download exceeds soft file bound; partial source preserved')
    prior_handler=signal.signal(signal.SIGXFSZ,bound_error)
    try:
        resource.setrlimit(resource.RLIMIT_FSIZE,(4_000_000,prior_limit[1]))
        with (run/'official-download.stdout.log').open('x') as log,contextlib.redirect_stdout(log):
            upstream.download_file(base,name+'.CHECKSUM',folder=str(raw_root))
            upstream.download_file(base,name,folder=str(raw_root))
    finally:
        resource.setrlimit(resource.RLIMIT_FSIZE,prior_limit);signal.signal(signal.SIGXFSZ,prior_handler)
    zip_path=raw_root/relative;check=zip_path.with_name(name+'.CHECKSUM')
    require(zip_path.is_file() and check.is_file(),'Official function did not deliver both archive and CHECKSUM; inspect preserved log')
    require(check.stat().st_size<=4096,'Official checksum response bound')
    fields=check.read_text().strip().split()
    require(len(fields)==2 and fields[1].lstrip('*')==name and fields[0].lower()==entry['checksum']['announced_zip_sha256'],'Official CHECKSUM changed from metadata')
    require(zip_path.stat().st_size==entry['announced_zip_bytes'] and sha(zip_path)==fields[0].lower(),'ZIP actual size or checksum mismatch')
    with zipfile.ZipFile(zip_path) as archive:
        members=archive.infolist()
        require(len(members)==1 and members[0].filename==name.removesuffix('.zip')+'.csv' and not members[0].flag_bits&1,'ZIP member/name/encryption mismatch')
        require(0<members[0].file_size<=LIMIT,'Declared uncompressed source exceeds 1GB')
        require(archive.testzip() is None,'ZIP CRC failure')
        member_bytes=members[0].file_size
    require(owned_bytes(run)<=LIMIT,'Owned source footprint exceeds 1GB')
    return zip_path,check,member_bytes

def funding_row(row,opened,closed):
    require(len(row)==3,'Funding column count')
    require(row[0].isascii() and row[0].isdecimal(),'Funding timestamp integer')
    timestamp=int(row[0]);hours=float(row[1]);rate=float(row[2])
    require(opened<=timestamp<closed,'Funding timestamp must be epoch milliseconds in stated month; no automatic rescale')
    require(math.isfinite(hours) and hours>0 and math.isfinite(rate),'Funding finite/interval unit')
    return {'calc_time_ms':timestamp,'funding_interval_hours':hours,'last_funding_rate':rate}

def price_row(row,opened,closed):
    require(len(row)==12,'Price proxy column count')
    require(row[0].isascii() and row[0].isdecimal() and row[6].isascii() and row[6].isdecimal(),'Price times integer')
    timestamp,close_time=int(row[0]),int(row[6]);values=[float(i) for i in row[1:5]]
    require(opened<=timestamp<closed and timestamp%60000==0 and close_time==timestamp+59999,'Price epoch-ms/1m open-close clock')
    require(all(math.isfinite(v) and v>0 for v in values),'Price finite/positive')
    o,h,l,c=values;require(l<=min(o,c)<=max(o,c)<=h,'OHLC price envelope')
    require(all(math.isfinite(float(row[i])) for i in (5,7,8,9,10,11)),'Ignored numeric fields finite; never treat them as volume evidence')
    return dict(timestamp_ms=timestamp,close_time_ms=close_time,open=o,high=h,low=l,close=c,
        **{f'ignore_{i}':row[i] for i in (5,7,8,9,10,11)})

def synthetic_checks(run):
    opened,closed=month_range('2025-08');passed=[]
    funding_row([str(opened),'4','0.0001'],opened,closed);passed.append('valid_funding_raw_ms_4h')
    row=[str(opened),'100','101','99','100','0',str(opened+59999),'0','0','0','0','0']
    price_row(row,opened,closed);passed.append('valid_1m_ohlc_proxy')
    bad=[('funding_microsecond_not_silently_rescaled',lambda:funding_row([str(opened*1000),'8','0'],opened,closed)),
         ('funding_interval_nonfinite',lambda:funding_row([str(opened),'nan','0'],opened,closed)),
         ('funding_rate_nonfinite',lambda:funding_row([str(opened),'8','inf'],opened,closed)),
         ('price_envelope_inconsistent',lambda:price_row([row[0],'100','98',*row[3:]],opened,closed))]
    for name,probe in bad:
        try:probe()
        except ValueError:passed.append(name)
        else:raise AssertionError('Invalid synthetic row accepted: '+name)
    fixture_dir=run/'synthetic-fixtures';fixture_dir.mkdir()
    fixture_protocol={'funding_header':['calc_time','funding_interval_hours','last_funding_rate'],
                      'funding_nominal_interval_tolerance_ms':1000}
    raw_rows=[[str(t+(i%3)+1),'4','0.0001'] for i,t in enumerate(range(opened,closed,4*3600000))]
    def fixture(name,rows):
        path=fixture_dir/(name+'.zip');text=io.StringIO();writer=csv.writer(text)
        writer.writerow(fixture_protocol['funding_header']);writer.writerows(rows)
        with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED) as archive:archive.writestr('synthetic.csv',text.getvalue())
        return path
    good=fixture('funding-4h-calc-jitter',raw_rows)
    stats=convert_source(good,{'kind':'fundingRate','month':'2025-08'},fixture_protocol,fixture_dir/'good.parquet')
    require(stats['rows']==186,'Synthetic non-eight-hour complete calendar');passed.append('4h_month_with_actual_calc_ms_jitter_accepted')
    missing=fixture('funding-missing-event',raw_rows[:4]+raw_rows[5:])
    try:convert_source(missing,{'kind':'fundingRate','month':'2025-08'},fixture_protocol,fixture_dir/'missing-unaccepted.parquet')
    except ValueError:passed.append('whole_missing_event_rejected_despite_calc_jitter_tolerance')
    else:raise AssertionError('Whole missing funding event accepted')
    write_new(run/'synthetic.json',{'status':'PASS_FORMAT_GUARDS_ONLY','cases':passed,'market_rows_used':False})

def convert_source(zip_path,entry,protocol,parquet):
    opened,closed=month_range(entry['month']);fund=entry['kind']=='fundingRate'
    schema=pa.schema([('calc_time_ms',pa.int64()),('funding_interval_hours',pa.float64()),('last_funding_rate',pa.float64())]) if fund else pa.schema(
        [('timestamp_ms',pa.int64()),('close_time_ms',pa.int64()),('open',pa.float64()),('high',pa.float64()),('low',pa.float64()),('close',pa.float64())]+[(f'ignore_{i}',pa.string()) for i in (5,7,8,9,10,11)])
    times=[];intervals=[];batch=[];rows=0;header=None;last_time=None
    with zipfile.ZipFile(zip_path) as archive,archive.open(archive.infolist()[0]) as binary,io.TextIOWrapper(binary,encoding='utf-8-sig',newline='') as text,pq.ParquetWriter(parquet,schema,compression='zstd') as writer:
        reader=csv.reader(text)
        first=next(reader)
        if fund:
            require(first==protocol['funding_header'],'Actual funding header differs from frozen schema');header=first
        elif first[0]=='open_time':
            require(first==protocol['price_header'],'Actual price header differs from frozen schema');header=first
        else:batch.append(price_row(first,opened,closed))
        for raw in reader:
            require(raw,'Empty CSV row')
            value=funding_row(raw,opened,closed) if fund else price_row(raw,opened,closed)
            batch.append(value)
            if len(batch)>=4096:
                for value in batch:
                    timestamp=value['calc_time_ms' if fund else 'timestamp_ms'];require(last_time is None or timestamp>last_time,'Duplicate/backward source clock')
                    if not fund:require(timestamp==opened+rows*60000,'Missing/shifted minute')
                    times.append(timestamp) if fund else None
                    intervals.append(value['funding_interval_hours']) if fund else None
                    rows+=1;last_time=timestamp
                writer.write_table(pa.Table.from_pylist(batch,schema=schema));batch=[]
        for value in batch:
            timestamp=value['calc_time_ms' if fund else 'timestamp_ms'];require(last_time is None or timestamp>last_time,'Duplicate/backward source clock')
            if not fund:require(timestamp==opened+rows*60000,'Missing/shifted minute')
            times.append(timestamp) if fund else None
            intervals.append(value['funding_interval_hours']) if fund else None
            rows+=1;last_time=timestamp
        if batch:writer.write_table(pa.Table.from_pylist(batch,schema=schema))
    require(rows>0,'No source rows')
    stats={'rows':rows,'observed_header':header,'schema':str(schema),'first_timestamp_ms':times[0] if fund else opened,'last_timestamp_ms':last_time,
           'timestamp_unit':'EPOCH_MILLISECONDS_RANGE_AND_GRID_VERIFIED','zip_csv_consumed_to_eof':True}
    if fund:
        deltas=[(b-a)/3600000 for a,b in zip(times,times[1:])]
        tolerance=protocol['funding_nominal_interval_tolerance_ms']
        require(0<=tolerance<=1000,'Nominal interval jitter bound')
        require(times[0]-opened<intervals[0]*3600000+tolerance and closed-times[-1]<=intervals[-1]*3600000+tolerance,'Funding edge coverage inconsistent with reported interval')
        mismatch=[i for i,d in enumerate(deltas,1) if not any(abs(d*3600000-h*3600000)<=tolerance for h in (intervals[i-1],intervals[i]))]
        require(not mismatch,'Funding event gap does not match either adjacent reported actual interval')
        stats.update(observed_delta_hours=dict(Counter(map(str,deltas))),reported_interval_hours=dict(Counter(map(str,intervals))),
                     interval_transition_count=sum(a!=b for a,b in zip(intervals,intervals[1:])),all_adjacent_gaps_consistent=True,
                     first_reported_interval_hours=intervals[0],last_reported_interval_hours=intervals[-1],nominal_interval_tolerance_ms=tolerance,
                     interval_semantics='Reported nominal hours; actual calc_time milliseconds and deltas retained, not exact charge/publication time',
                     funding_charge_and_publication_time_semantics='NOT_CERTIFIED_BY_API_EVENT_MATCH; preserve calc_time raw field')
    else:require(rows==(closed-opened)//60000,'Complete fixed-1m calendar required')
    return stats

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,required=True);parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    run,out=args.run_dir.resolve(),args.output.resolve()
    require(run.is_relative_to(STATE.resolve()) and not run.exists(),'Exclusive D-hosted source STATE')
    require(out.is_relative_to(ROOT/'reports') and not out.exists(),'Exclusive receipt')
    run.mkdir();protocol=json.loads(args.protocol.read_bytes());mode=protocol['mode'];preflight=mode=='FORMAT_PREFLIGHT'
    require(mode in ('FORMAT_PREFLIGHT','FIXED_SOURCE_FORMAT_QA'),'Unknown source-only stage')
    clean=json.loads((ROOT/'reports/fast_research/V8_CLEAN_ENVIRONMENT_SMOKE_20261002_V2.json').read_bytes())
    require(Path(sys.prefix).resolve()==Path(clean['sys_prefix']).resolve() and not any('research-env-v6' in p or '/coin/.venv/' in p for p in sys.path),'Accepted clean V8 runtime required')
    metadata_path=ROOT/'reports/fast_research/V8_OFFICIAL_INPUT_METADATA_20261002_V1.json';require(sha(metadata_path)==META_SHA,'Original metadata changed')
    component_path=ROOT/'reports/fast_research/V8_OFFICIAL_DOWNLOAD_COMPONENT_20261002_V2.json';component=json.loads(component_path.read_bytes())
    require(component['status']=='PINNED_OFFICIAL_DOWNLOAD_COMPONENT_STAGED_NO_MARKET_DATA','Official source not staged')
    entries=[i for i in json.loads(metadata_path.read_bytes())['objects'] if i['market']=='futures/um' and i['partition']=='monthly' and i['kind'] in ('fundingRate','markPriceKlines','indexPriceKlines')]
    entries.sort(key=lambda i:(0 if i['kind']=='fundingRate' else 1,i['kind'],i['symbol'],i['month']))
    require(len(entries)==24 and sum(i['announced_zip_bytes'] for i in entries)==16_260_808,'Fixed source universe differs')
    if preflight:entries=[next(i for i in entries if i['kind']=='fundingRate' and i['symbol']=='BTCUSDT' and i['month']=='2025-08')]
    else:
        prior=json.loads(Path(protocol['preflight_report']).read_bytes())
        require(sha(protocol['preflight_report'])==protocol['preflight_sha256'] and prior['status']=='PASS_FORMAT_PREFLIGHT_ONLY_NOT_SOURCE_ACCEPTANCE','Real format preflight required')
        first_receipt=json.loads(Path(prior['sources'][0]['path']).read_bytes())
        require(first_receipt['observed_header']==protocol['funding_header'],'Final funding header not bound to actual preflight')
    require(protocol['source_sha256']==sha(Path(__file__)),'Source bytes changed after protocol freeze')
    binding={'command':[sys.executable,*sys.argv],'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'protocol_path':str(args.protocol.resolve()),'protocol_sha256':sha(args.protocol),'source_path':str(Path(__file__).resolve()),'source_sha256':sha(Path(__file__)),
        'component_receipt_sha256':sha(component_path),'metadata_sha256':META_SHA,'official_files':component['files'],
        'environment':{'executable':sys.executable,'prefix':sys.prefix,'lock_sha256':sha(ROOT/'environments/v8/uv.lock')},
        'entry_urls':[i['url'] for i in entries],'no_fits_locked_keys_paid_gpu':True}
    write_new(run/'RUN_BINDING.json',binding)
    event=dict.fromkeys(FIELDS);identity=protocol['experiment_id']
    event.update(event_id=identity+':start',event_type='OPERATIONAL_SOURCE_START',experiment_id=identity,git_commit=binding['git_commit'],
        data_manifest_hash=META_SHA,protocol_hash=sha(args.protocol),feature_set='NONE_SOURCE_FORMAT_ONLY',labels='NONE',model_family='NONE',
        hyperparameters=protocol,seed=None,thresholds={'owned_bytes':LIMIT,'expected_archives':len(entries)},cost_assumptions='UNCHANGED_NOT_EVALUATED',
        all_folds='2025_AUG_SEP_OCT_NOV_BTC_ETH_SOURCE_ONLY',success_failure='START_BEFORE_SOURCE_QA_AND_DOWNLOAD',
        reason_for_next_experiment='New funding/mark/index information for carry/slowportfolio source feasibility, no profit experiment',
        result_influenced_later_choice='OFFICIAL_SOURCE_METADATA_ONLY',fits=0,run_binding_sha256=sha(run/'RUN_BINDING.json'))
    start=append_event(ROOT/'reports/experiment_registry.jsonl',event)
    result={'status':'FAILED_NEW_OFFICIAL_INPUT_SOURCE_UNACCEPTED','registration_start':start,'run_binding':binding,
        'run_binding_sha256':sha(run/'RUN_BINDING.json'),'started_utc':datetime.now(UTC).isoformat(),'completed_files':0,'required_files':len(entries),
        'sources':[],'model_fits':0,'locked_consumed':False,'orders_sent':0,'economic_eligibility':False,'carry':'NOT_EVALUABLE','source_only':True}
    progress=progress_writer(len(entries));started=time.monotonic()
    try:
        progress.update('实际磁盘扫描，扫描总量未知',None,None,'扫描')
        result['initial_disk']=disk.check(LIMIT);result['initial_disk']['measured_utc']=datetime.now(UTC).isoformat()
        require(result['initial_disk']['total_bytes']+LIMIT<=32_000_000_000,'Expected32GB capacity would be exceeded')
        synthetic_checks(run);upstream=official_module(component)
        uncompressed=0
        for index,entry in enumerate(entries):
            job=run/f'{entry["kind"]}-{entry["symbol"]}-{entry["month"]}';job.mkdir()
            job_event=dict(event,event_id=identity+f':file-{index}:start',event_type='OPERATIONAL_SOURCE_FILE_START',
                           success_failure='BEFORE_OFFICIAL_FILE_DOWNLOAD',source_url=entry['url'])
            append_event(ROOT/'reports/experiment_registry.jsonl',job_event)
            receipt={'status':'FAILED_ARCHIVE_SOURCE_UNACCEPTED','entry':entry,'component_sha256':sha(component_path)}
            try:
                progress.update('官方档案下载/校验',index,len(entries),'文件',当前档案=f'{entry["kind"]}/{entry["symbol"]}/{entry["month"]}')
                archive,check,declared=download_archive(entry,job,upstream);uncompressed+=declared
                require(uncompressed<=LIMIT and owned_bytes(run)<=LIMIT,'New source/temp budget exceeds 1GB')
                receipt.update(zip_path=str(archive),zip_sha256=sha(archive),checksum_path=str(check),checksum_sha256=sha(check),zip_crc='PASS_FULL_READ',uncompressed_csv_bytes=declared)
                if preflight:
                    with zipfile.ZipFile(archive) as z,z.open(z.infolist()[0]) as f,io.TextIOWrapper(f,encoding='utf-8-sig',newline='') as text:
                        reader=csv.reader(text);receipt['observed_header']=next(reader);rows=list(reader)
                    opened,closed=month_range(entry['month']);receipt['observed_data_columns']=sorted({len(row) for row in rows})
                    require(all(len(row)==3 for row in rows),'Unknown funding row structure')
                    times=[int(row[0]) for row in rows];require(all(opened<=t<closed for t in times),'Preflight funding time not epoch-ms month')
                    receipt.update(rows=len(rows),first_timestamp_ms=times[0],last_timestamp_ms=times[-1],
                        observed_timestamp_unit='EPOCH_MILLISECONDS_RANGE_VERIFIED',reported_interval_hours=dict(Counter(row[1] for row in rows)),
                        observed_delta_hours=dict(Counter(str((b-a)/3600000) for a,b in zip(times,times[1:]))),status='PASS_FORMAT_PREFLIGHT_ONLY_NOT_SOURCE_ACCEPTANCE')
                else:
                    parquet=job/'source.parquet';stats=convert_source(archive,entry,protocol,parquet)
                    receipt.update(stats=stats,parquet_path=str(parquet),parquet_sha256=sha(parquet),parquet_bytes=parquet.stat().st_size,
                                   status='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA')
                receipt['owned_bytes']=owned_bytes(job)
            except Exception as error:
                receipt.update(error_type=type(error).__name__,reason=str(error)[:1024]);raise
            finally:
                write_new(job/'receipt.json',receipt)
                append_event(ROOT/'reports/experiment_registry.jsonl',dict(job_event,event_id=identity+f':file-{index}:result',
                    event_type='OPERATIONAL_SOURCE_FILE_RESULT',success_failure=receipt['status'],output_sha256=sha(job/'receipt.json'),output_path=str(job/'receipt.json')))
            result['sources'].append({'path':str(job/'receipt.json'),'sha256':sha(job/'receipt.json'),'status':receipt['status']})
            result['completed_files']=len(result['sources']);progress.update('真实格式校验完成',len(result['sources']),len(entries),'文件',新增实际字节=owned_bytes(run))
        result.update(status='PASS_FORMAT_PREFLIGHT_ONLY_NOT_SOURCE_ACCEPTANCE' if preflight else 'OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA',
                      declared_uncompressed_csv_bytes=uncompressed,owned_bytes=owned_bytes(run),resources=resources.status())
    except Exception as error:
        result.update(error_type=type(error).__name__,reason=str(error)[:1024]);raise
    finally:
        result.update(elapsed_seconds=time.monotonic()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write_new(out,result);append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=identity+':result',event_type='OPERATIONAL_SOURCE_RESULT',
           success_failure=result['status'],output_sha256=sha(out),output_path=str(out)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps({k:result[k] for k in ('status','completed_files','required_files','elapsed_seconds','peak_rss_bytes')}))

if __name__=='__main__':main()
