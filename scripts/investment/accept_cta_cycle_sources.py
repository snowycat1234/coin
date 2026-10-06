"""Join the two completed source batches and verify funding boundary continuity."""
import argparse,csv,io,json,os,zipfile
from datetime import UTC,datetime
from pathlib import Path
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.cta_cycle_source import sha,save
from scripts.investment.cta_cycle_window import STATUS

def stamp(s):return int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())*1000000

ap=argparse.ArgumentParser()
ap.add_argument('--source',action='append',required=True)
ap.add_argument('--symbols',nargs='+',default=['BTCUSDT','ETHUSDT'])
ap.add_argument('--run-dir',type=Path,required=True)
ap.add_argument('--output',type=Path,required=True)
a=ap.parse_args();assert a.run_dir.parent==STATE and not a.run_dir.exists() and os.getenv('COIN_TASK_ID')
symbols=a.symbols;assert symbols in (['BTCUSDT'],['BTCUSDT','ETHUSDT'])
a.run_dir.mkdir();records=[];warm=[];refs=[];funding={s:[] for s in symbols};compound=[]
for path in a.source:
    p=ROOT/path;source=json.loads(p.read_bytes());assert source['status'] in ('PASS_CYCLE_OFFICIAL_RAW_REFERENCE_FORMAT_NOT_ECONOMICS','FAILED_CYCLE_SOURCE')
    task=json.loads((STATE/'task-progress'/('task-'+source['binding']['task_id']+'.json')).read_bytes())
    expected_exit=0 if source['status']=='PASS_CYCLE_OFFICIAL_RAW_REFERENCE_FORMAT_NOT_ECONOMICS' else 1
    assert task['status']==('completed' if expected_exit==0 else 'failed') and task['exit_code']==expected_exit
    refs.append(dict(path=path,sha256=sha(p),task_id=source['binding']['task_id'],producer_status=source['status'],expected_exit_code=expected_exit,
        acceptance_scope='ONLY_SELECTED_COMPLETED_INDEPENDENT_RAW_REFERENCE_ROWS_NOT_WHOLE_FAILED_TASK'))
    assert len(source['sources'])<=len(source['protocol']['entries'])
    for row in source['sources']:
        proof=row['independent_reference'];entry=row['entry']
        if entry['symbol'] not in symbols:continue
        p=Path(row['receipt_path'])
        assert sha(p)==row['receipt_sha256'];receipt=json.loads(p.read_bytes())
        assert json.loads((p.parent/'INDEPENDENT_RAW_REFERENCE.json').read_bytes())==proof
        parents=row.get('official_archive_parents') or row.get('source_composition',{}).get('parents')
        if parents:
            # Independent parent-to-derived check, beyond normalized-vs-derived QA.
            reference={}
            for parent in parents:
                zpath=Path(parent['path']);assert zpath.is_relative_to(STATE) and sha(zpath)==parent['sha256']
                with zipfile.ZipFile(zpath) as z:
                    assert len(z.infolist())==1
                    original=list(csv.reader(io.StringIO(z.read(z.infolist()[0]).decode('utf-8-sig'))))
                if original[0][0]=='open_time':original.pop(0)
                for raw in original:
                    key=int(raw[0])
                    if key in reference:
                        from decimal import Decimal
                        assert all(Decimal(a)==Decimal(b) for a,b in zip(reference[key],raw))
                    else:reference[key]=raw
            with zipfile.ZipFile(receipt['zip_path']) as z:
                derived=list(csv.reader(io.StringIO(z.read(z.infolist()[0]).decode('utf-8-sig'))))
            assert derived==[reference[k] for k in sorted(reference)]
            compound.append(dict(symbol=entry['symbol'],month=entry['month'],parents=parents,
                independent_exact_parent_union_rows=len(derived),not_official_monthly_zip=True))
        if entry['kind']=='klines':
            assert proof['all_raw_normalized_values_equal'] and proof['full_CSV_EOF_and_CRC_read']
            normalized=receipt['normalized_path'];h=receipt['normalized_sha256'];size=receipt['normalized_bytes']
        else:
            assert proof['status']=='PASS_SOURCE_FORMAT_ONLY' and proof['all_published_values_equal_raw'] and proof['zip_crc_full_read']
            normalized=receipt['parquet_path'];h=receipt['parquet_sha256'];size=receipt['parquet_bytes']
        file=Path(normalized);assert file.is_relative_to(STATE) and not file.is_symlink() and file.stat().st_size==size and sha(file)==h
        r=dict(kind=entry['kind'],symbol=entry['symbol'],month=entry['month'],interval=entry.get('interval'),
            normalized_path=normalized,normalized_sha256=h,normalized_bytes=size,rows=proof['rows'],
            receipt_path=str(p),receipt_sha256=row['receipt_sha256'])
        if entry.get('interval')=='1d':warm.append(r)
        else:records.append(r)
        if entry['kind']=='fundingRate':funding[entry['symbol']].append(pl.read_parquet(file))
months=[f'{y}-{m:02}' for y in (2022,2023) for m in range(1,13)]
keys={(r['symbol'],r['kind'],r['month']) for r in records}
assert len(records)==len(keys)==72*len(symbols) and keys=={(s,k,m) for s in symbols for k in ('klines','markPriceKlines','fundingRate') for m in months}
assert len(warm)==12*len(symbols) and {(r['symbol'],r['month']) for r in warm}=={(s,f'2021-{m:02}') for s in symbols for m in range(1,13)}
counts={}
for s in symbols:
    rates=pl.concat(funding[s]).sort('calc_time_ms');clock=rates['calc_time_ms'].to_list();hours=rates['funding_interval_hours'].to_list()
    assert len(clock)==len(set(clock))
    assert clock[0]-stamp('2022-01-01')//1000<=1000 and 0<stamp('2024-01-01')//1000-clock[-1]<=hours[-1]*3600000+1000
    assert all(min(abs(b-a-h*3600000) for h in (hours[i],hours[i+1]))<=1000 for i,(a,b) in enumerate(zip(clock,clock[1:])))
    counts[s]=len(clock)
manifest=dict(status=STATUS,symbols=symbols,start_us=stamp('2022-01-01'),end_us=stamp('2024-01-01'),warmup_start_us=stamp('2021-01-01'),
    source_reports=refs,market_records=records,daily_records=warm,funding_events=sum(counts.values()),
    source_only=True,native_Bybit=False,funding_unit='UNKNOWN_RETAIN_CONDITIONAL_SCALES',historical10coin_pool=False,data_role='OLDER_CYCLE_DEVELOPMENT_NOT_LOCKED_OR_UNSEEN_INVESTMENT')
manifest_path=a.run_dir/'INPUT_MANIFEST.json';save(manifest_path,manifest)
save(a.output,dict(status='PASS_FIXED_CYCLE_SOURCE_FORMAT_AND_CROSS_MONTH_FUNDING_NOT_ECONOMICS',task_id=os.environ['COIN_TASK_ID'],
    source_sha256=sha(__file__),source_reports=refs,source_only=True,new_accounts=0,models_fit=0,economics='NOT_RUN',
    symbols=symbols,canonical_source_objects=84*len(symbols),official_archives=84*len(symbols)+sum(len(v['parents'])-1 for v in compound),compound_mark_sources=compound,
    market_months=24,warmup_days=365,actual_evaluation_days=730,funding_events=counts,
    manifest=dict(path=str(manifest_path),sha256=sha(manifest_path)),created_utc=datetime.now(UTC).isoformat()))
print(json.dumps(dict(status='PASS_CYCLE_SOURCE_ONLY',canonical_source_objects=84*len(symbols),funding_events=counts)))
