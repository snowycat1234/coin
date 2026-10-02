"""Independent fixed-input archive/Parquet QA; no trading or model evaluation."""
from __future__ import annotations
import argparse,csv,hashlib,io,json,math,resource,subprocess,sys,time,zipfile
from collections import Counter
from datetime import UTC,date,datetime,timedelta
from pathlib import Path
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from quant.paths import ROOT,STATE

sys.path.insert(0,str(ROOT))
from scripts.research_v8.registry import FIELDS,append_event
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
def check(ok,message):
    if not ok:raise ValueError(message)
def write(path,value):
    with Path(path).open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')

def audit_one(receipt,protocol):
    entry=receipt['entry'];zip_path=Path(receipt['zip_path']);parquet=Path(receipt['parquet_path'])
    check(receipt['status']=='SOURCE_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA','Producer not fully complete')
    check(zip_path.is_relative_to(STATE) and parquet.is_relative_to(STATE),'Source outside D-hosted STATE')
    check(sha(zip_path)==receipt['zip_sha256']==entry['checksum']['announced_zip_sha256'],'Actual official ZIP SHA changed')
    check(zip_path.stat().st_size==entry['announced_zip_bytes'],'Actual ZIP byte size differs from HEAD')
    fields=Path(receipt['checksum_path']).read_text().split()
    check(len(fields)==2 and fields[0].lower()==receipt['zip_sha256'] and fields[1].lstrip('*')==zip_path.name,'Saved official CHECKSUM identity')
    check(sha(receipt['checksum_path'])==receipt['checksum_sha256'] and sha(parquet)==receipt['parquet_sha256'],'Actual CHECKSUM/Parquet binding')
    first=date.fromisoformat(entry['month']+'-01');end=(first.replace(day=28)+timedelta(days=4)).replace(day=1)
    opened=int(datetime.combine(first,datetime.min.time(),UTC).timestamp()*1000);closed=int(datetime.combine(end,datetime.min.time(),UTC).timestamp()*1000)
    table=pq.read_table(parquet);fund=entry['kind']=='fundingRate'
    if fund:
        check(table.column_names==['calc_time_ms','funding_interval_hours','last_funding_rate'],'Funding Parquet names')
        check(table.schema.types==[pa.int64(),pa.float64(),pa.float64()],'Funding Parquet physical types')
        clock=table['calc_time_ms'].to_pylist();hours=table['funding_interval_hours'].to_pylist()
        check(all(math.isfinite(x) and x>0 for x in hours),'Funding interval finite/positive')
        check(pc.all(pc.is_finite(table['last_funding_rate'])).as_py(),'Funding rate finite; retained raw units')
        check(clock and opened<=clock[0] and clock[-1]<closed and all(a<b for a,b in zip(clock,clock[1:])),'Funding strict epoch-ms/month clock')
        gaps=[(b-a)/3600000 for a,b in zip(clock,clock[1:])]
        tolerance=protocol['funding_nominal_interval_tolerance_ms'];check(0<=tolerance<=1000,'Nominal interval jitter bound')
        check(all(any(abs(g*3600000-h*3600000)<=tolerance for h in (hours[i],hours[i+1])) for i,g in enumerate(gaps)),'Independent funding nominal interval/gap coverage')
        check(clock[0]-opened<hours[0]*3600000+tolerance and closed-clock[-1]<=hours[-1]*3600000+tolerance,'Funding month edge coverage')
        result={'rows':len(clock),'observed_interval_hours':dict(Counter(map(str,hours))),'actual_delta_hours':dict(Counter(map(str,gaps))),
                'first_timestamp_ms':clock[0],'last_timestamp_ms':clock[-1],'first_interval_hours':hours[0],'last_interval_hours':hours[-1]}
    else:
        expected=['timestamp_ms','close_time_ms','open','high','low','close']+[f'ignore_{i}' for i in (5,7,8,9,10,11)]
        check(table.column_names==expected and table.schema.types==[pa.int64(),pa.int64()]+[pa.float64()]*4+[pa.string()]*6,'Fixed proxy schema/types')
        clock=table['timestamp_ms'].to_pylist();closing=table['close_time_ms'].to_pylist()
        check(clock==list(range(opened,closed,60000)) and closing==[v+59999 for v in clock],'Full exact 1m common calendar/open-close times')
        for name in ('open','high','low','close'):
            check(pc.all(pc.and_(pc.is_finite(table[name]),pc.greater(table[name],0))).as_py(),'Finite positive price proxy')
        for o,h,l,c in zip(*(table[name].to_pylist() for name in ('open','high','low','close'))):check(l<=min(o,c)<=max(o,c)<=h,'OHLC envelope')
        for i in (5,7,8,9,10,11):check(pc.all(pc.is_finite(pc.cast(table[f'ignore_{i}'],pa.float64()))).as_py(),'Ignored numeric field finite')
        result={'rows':len(clock),'first_timestamp_ms':clock[0],'last_timestamp_ms':clock[-1],'exact_1m_calendar':True}
    check(table.num_rows==receipt['stats']['rows'] and parquet.stat().st_size==receipt['parquet_bytes'],'Actual published rows/bytes')
    # Independently compare every published row against the actual official CSV values.
    values=table.to_pylist();position=0;header=None
    with zipfile.ZipFile(zip_path) as z:
        members=z.infolist();check(len(members)==1 and members[0].file_size==receipt['uncompressed_csv_bytes'],'ZIP member/declared bytes')
        with z.open(members[0]) as f,io.TextIOWrapper(f,encoding='utf-8-sig',newline='') as text:
            for raw in csv.reader(text):
                if position==0 and header is None and (fund or raw[0]=='open_time'):
                    check(raw==protocol['funding_header' if fund else 'price_header'],'Actual frozen archive header');header=raw;continue
                check(position<len(values),'CSV longer than published source')
                row=values[position]
                if fund:check([int(raw[0]),float(raw[1]),float(raw[2])]==[row['calc_time_ms'],row['funding_interval_hours'],row['last_funding_rate']],'Raw funding bytes/Parquet value disagreement')
                else:
                    check([int(raw[0]),int(raw[6]),*[float(v) for v in raw[1:5]]]==[row['timestamp_ms'],row['close_time_ms'],row['open'],row['high'],row['low'],row['close']],'Raw price bytes/Parquet disagreement')
                    check(all(raw[i]==row[f'ignore_{i}'] for i in (5,7,8,9,10,11)),'Ignored raw values changed')
                position+=1
        check(position==table.num_rows and z.testzip() is None,'Actual CSV full EOF/row count/independent ZIP CRC')
    result.update(status='PASS_SOURCE_FORMAT_ONLY',kind=entry['kind'],symbol=entry['symbol'],month=entry['month'],
                  header=header,timestamp_unit='EPOCH_MILLISECONDS',zip_crc_full_read=True,all_published_values_equal_raw=True,
                  carry_economics='NOT_EVALUABLE',BBO=False,funding_charge_price=False,executable=False)
    return result

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--receipt',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--run-dir',type=Path,required=True);args=parser.parse_args();run=args.run_dir.resolve();out=args.output.resolve()
    check(run.is_relative_to(STATE) and not run.exists() and out.is_relative_to(ROOT/'reports') and not out.exists(),'Exclusive audit artifacts')
    run.mkdir();source=json.loads(args.receipt.read_bytes());binding=source['run_binding'];protocol=json.loads(Path(binding['protocol_path']).read_bytes())
    check(source['status']=='OFFICIAL_CARRY_INPUT_FORMAT_QA_COMPLETE_PENDING_INDEPENDENT_QA' and source['completed_files']==source['required_files']==24,'24 actual source conversions required')
    check(sha(binding['protocol_path'])==binding['protocol_sha256'] and Path(binding['source_path']).is_relative_to(ROOT/'scripts/research_v8') and sha(binding['source_path'])==binding['source_sha256'],'Frozen producer source/protocol differs')
    check(sha(Path(__file__))==protocol['auditor_sha256'],'Frozen independent auditor differs')
    event=dict.fromkeys(FIELDS);identity='V8-FUNDING-PRICE-INDEPENDENT-QA-20261002-V1'
    event.update(event_id=identity+':start',event_type='OPERATIONAL_SOURCE_AUDIT_START',experiment_id=identity,
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),data_manifest_hash=sha(args.receipt),protocol_hash=binding['protocol_sha256'],
        feature_set='NONE_SOURCE_ONLY',labels='NONE',model_family='NONE',hyperparameters={'auditor_sha256':sha(Path(__file__)),'producer_binding_sha256':source['run_binding_sha256']},seed=None,
        thresholds={'archives':24,'added_bytes':1_000_000_000},cost_assumptions='NOT_EVALUATED_UNCHANGED',all_folds='FIXED_2025_AUG_NOV_SOURCE_ONLY',
        success_failure='START_BEFORE_INDEPENDENT_ROWS_QA',reason_for_next_experiment='Independent actual raw/archive/Parquet equivalence',result_influenced_later_choice='NO_MODEL_RESULTS',fits=0)
    write(run/'RUN_BINDING.json',{'command':[sys.executable,*sys.argv],'source_sha256':sha(Path(__file__)),'producer_sha256':sha(args.receipt),'protocol_sha256':binding['protocol_sha256']})
    start=append_event(ROOT/'reports/experiment_registry.jsonl',event);started=time.monotonic()
    report={'status':'FAILED_OFFICIAL_CARRY_INPUT_INDEPENDENT_QA','registration_start':start,'sources':[],'source_receipt_sha256':sha(args.receipt),
            'auditor_sha256':sha(Path(__file__)),'no_economics_models_locked_keys_paid_gpu':True,'source_only':True,'carry':'NOT_EVALUABLE'}
    try:
        for item in source['sources']:
            check(sha(item['path'])==item['sha256'],'Actual per-file receipt changed')
            result=audit_one(json.loads(Path(item['path']).read_bytes()),protocol)
            result.update(receipt_path=item['path'],receipt_sha256=item['sha256']);report['sources'].append(result)
            print(json.dumps({'phase':'独立逐档来源QA','completed_files':len(report['sources']),'required_files':24,'unit':'文件'}),flush=True)
        for symbol in ('BTCUSDT','ETHUSDT'):
            funding=sorted([i for i in report['sources'] if i['symbol']==symbol and i['kind']=='fundingRate'],key=lambda i:i['month'])
            for a,b in zip(funding,funding[1:]):check(any(abs(b['first_timestamp_ms']-a['last_timestamp_ms']-h*3600000)<=protocol['funding_nominal_interval_tolerance_ms'] for h in (a['last_interval_hours'],b['first_interval_hours'])),'Independent cross-month funding gap')
        check(len({(i['kind'],i['symbol'],i['month']) for i in report['sources']})==24,'Duplicate/missing source universe')
        report.update(status='PASS_OFFICIAL_CARRY_INPUT_FORMAT_ONLY_INDEPENDENT_QA',actual_archives=24,actual_rows=sum(i['rows'] for i in report['sources']),
            exact_1m_price_proxy_months=16,funding_event_months=8,cross_month_funding_gaps='PASS_REPORTED_ACTUAL_INTERVALS',
            units_or_economics_qualified='Raw numeric values and timestamp-ms accepted; fee, capital, charge-event availability and execution remain NOT_EVALUABLE')
    except Exception as error:report.update(error_type=type(error).__name__,reason=str(error)[:1024]);raise
    finally:
        report.update(elapsed_seconds=time.monotonic()-started,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
        write(out,report);append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=identity+':result',event_type='OPERATIONAL_SOURCE_AUDIT_RESULT',
            success_failure=report['status'],output_path=str(out),output_sha256=sha(out)))
    print(json.dumps({k:report[k] for k in ('status','actual_archives','actual_rows','elapsed_seconds','peak_rss_bytes')}))

if __name__=='__main__':main()
