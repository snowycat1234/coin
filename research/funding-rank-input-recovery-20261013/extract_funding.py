"""Existing source bytes only. No financial code, cadence filling or strategy."""
import argparse,csv,datetime,gzip,hashlib,io,json,os,resource,time,zipfile,collections,math
from pathlib import Path
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');START=1702166400000000;JAN=1704067200000000;JUL=1719792000000000;END=1735689600000000
def sha(b):return hashlib.sha256(b).hexdigest()
def file_sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,sort_keys=True,allow_nan=False)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-2024',type=Path,required=True);p.add_argument('--source-2023',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists();a.output.mkdir(parents=True,exist_ok=False);begun=time.monotonic();print('SOURCE_WORKER_STARTED',datetime.datetime.now(datetime.UTC).isoformat(),os.getpid(),flush=True)
 os.sched_setaffinity(0,{min(os.sched_getaffinity(0))});resource.setrlimit(resource.RLIMIT_AS,(4_000_000_000,4_000_000_000));resource.setrlimit(resource.RLIMIT_CPU,(600,600))
 import polars as pl
 idxraw=(a.source_2024/'prepared_2024/SOURCE_INDEX.json').read_bytes();assert sha(idxraw)=='0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69';index=json.loads(idxraw);expected_wrappers=index['public_wrappers_SHA256'];archives={}
 for n,h in expected_wrappers.items():assert file_sha(a.source_2024/'source'/n)==h,n;archives[n]=zipfile.ZipFile(a.source_2024/'source'/n)
 reference={};refident=[]
 for year,folder in ((2024,a.source_2024/'prepared_2024'),(2023,a.source_2023)):
  ir=(folder/'SOURCE_INDEX.json').read_bytes();ix=json.loads(ir);assert sha(ir)==('0b319baf450c8a0f2f89c2a15fdabf2741471bd0ae75aef6f5be1f76cb439c69' if year==2024 else '5c88d0022fe185f966266b54c9962b1e632048817d369e00112f72b2071c7251');body=(folder/'EVENTS.json').read_bytes();assert sha(body)==ix['files']['EVENTS.json']['SHA256'];assert len(body)==ix['files']['EVENTS.json']['bytes']
  events=json.loads(body);assert len(events)==ix['funding_events']
  for e in events:
   if START<=e['event_us']<END:assert (e['symbol'],e['event_us']) not in reference;reference[e['symbol'],e['event_us']]=e
  refident.append(dict(year=year,index_sha256=sha(ir),events_sha256=sha(body),events_bytes=len(body),declared_calendar=ix['calendar'],declared_funding_events=ix['funding_events'],authority=ix.get('authority','Original frozen 2024 source index calendar/count; not an independent provider completeness guarantee.')))
 h1=archives['H1.zip'];manifest_raw=h1.read('h1_market/reports/DATASET_MANIFEST.json');manifest=json.loads(manifest_raw);artifacts={r['relative_path']:r for r in manifest['artifacts']};sources={};rows=[];coverage_authority=dict(h1_score_windows=manifest['score_windows'],funding_rate_unit=manifest['funding_rate_unit'],funding_time_semantics=manifest['funding_time_semantics'],reference_indices=refident)
 def add(s,t,rate,raw_text,hours,existing_hours,sid,row,raw_hex):
  assert START<=t<END and (s,t) in reference,(s,t);e=reference[s,t];assert rate==e['raw_rate'];assert existing_hours==e['reported_interval_hours'];assert math.isfinite(rate)
  rows.append(dict(symbol=s,event_us=t,raw_rate_text=raw_text,source_numeric_float64_hex=raw_hex,existing_normalized_rate=e['raw_rate'],normalized_float64_hex=float(e['raw_rate']).hex(),source_reported_interval_hours=hours,existing_normalized_interval_hours=existing_hours,source_id=sid,source_row=row))
 for s in SYMBOLS:
  name=f'h1_market/data/normalized/{s}_funding_events.parquet';body=h1.read(name);r=artifacts[f'data/normalized/{s}_funding_events.parquet'];assert sha(body)==r['sha256'] and len(body)==r['bytes'];sid='normalized_'+s;sources[sid]=dict(wrapper='H1.zip',wrapper_sha256=expected_wrappers['H1.zip'],member=name,member_sha256=sha(body),member_bytes=len(body),manifest_member='h1_market/reports/DATASET_MANIFEST.json',manifest_sha256=sha(manifest_raw),locator='zero-based original parquet row',raw_rate_authority='Existing Float64 last_funding_rate field; original numeric text not retained',reported_interval_authority='Provider-original interval cannot be established from normalized parquet alone; null, normalized field separately preserved')
  table=pl.read_parquet(io.BytesIO(body)).with_row_index('_row');table=table.filter((pl.col('calc_time_ms')*1000>=START)&(pl.col('calc_time_ms')*1000<JUL))
  for r in table.iter_rows(named=True):add(s,int(r['calc_time_ms'])*1000,float(r['last_funding_rate']),None,None,float(r['funding_interval_hours']),sid,int(r['_row']),float(r['last_funding_rate']).hex())
  elapsed=time.monotonic()-begun;done=len(sources);print('SOURCE_PROGRESS',done,35,'elapsed',elapsed,'ETA_seconds',elapsed/done*(35-done),flush=True)
 lookup={n:z for z in archives.values() for n in z.namelist() if n.startswith('tail_data/data/raw/fundingRate/')}
 for s in SYMBOLS:
  for month in range(7,13):
   name=f'tail_data/data/raw/fundingRate/{s}/{s}-fundingRate-2024-{month:02d}.zip';z=lookup[name];raw=z.read(name);checksum=z.read(name+'.CHECKSUM');assert sha(raw)==checksum.decode().split()[0]
   with zipfile.ZipFile(io.BytesIO(raw)) as inner:
    assert len(inner.namelist())==1 and inner.testzip() is None;csvname=inner.namelist()[0];body=inner.read(csvname)
   sid=f'raw_{s}_2024_{month:02d}';wrapper=Path(z.filename).name;sources[sid]=dict(wrapper=wrapper,wrapper_sha256=expected_wrappers[wrapper],member=name,member_sha256=sha(raw),member_bytes=len(raw),checksum_member_sha256=sha(checksum),csv_member=csvname,csv_sha256=sha(body),locator='zero-based data row after actual CSV header',coverage_authority='Original checksum-verified monthly fundingRate archive, matched original frozen year EVENTS reference; no event-spacing inferred completeness')
   data=list(csv.DictReader(io.StringIO(body.decode())));assert data
   for i,r in enumerate(data):
    t=int(r['calc_time'])*1000
    if START<=t<END:
     text=r['last_funding_rate'];v=float(text);hours=float(r['funding_interval_hours']) if r.get('funding_interval_hours') not in (None,'') else None
     add(s,t,v,text,hours,reference[s,t]['reported_interval_hours'],sid,i,v.hex())
 rows.sort(key=lambda r:(r['event_us'],r['symbol']));keys=[(r['symbol'],r['event_us']) for r in rows];assert len(keys)==len(set(keys)) and set(keys)==set(reference);assert sum(JAN<=r['event_us']<END for r in rows)==5490
 body=b''.join((json.dumps(r,sort_keys=True,separators=(',',':'),allow_nan=False)+'\n').encode() for r in rows);encoded=gzip.compress(body,mtime=0);(a.output/'EVENTS.jsonl.gz').write_bytes(encoded)
 groups=[]
 for s in SYMBOLS:
  for month in ['2023-12']+[f'2024-{m:02d}' for m in range(1,13)]:
   group=[r for r in rows if r['symbol']==s and datetime.datetime.fromtimestamp(r['event_us']/1e6,datetime.UTC).strftime('%Y-%m')==month];ref=[e for (sym,t),e in reference.items() if sym==s and datetime.datetime.fromtimestamp(t/1e6,datetime.UTC).strftime('%Y-%m')==month];gb=b''.join((json.dumps(r,sort_keys=True,separators=(',',':'))+'\n').encode() for r in group)
   groups.append(dict(symbol=s,month=month,event_count=len(group),first_event_us=group[0]['event_us'] if group else None,last_event_us=group[-1]['event_us'] if group else None,missing_from_hash_bound_existing_reference=len({e['event_us'] for e in ref}-{e['event_us'] for e in group}),duplicates=0,provider_missing_count=None,provider_missing_count_reason='No cadence-derived expected count; completeness authority limited to original archives and hash-bound project reference.',group_sha256=sha(gb),reported_interval_null_count=sum(r['source_reported_interval_hours'] is None for r in group)))
 save(a.output/'SOURCE_IDENTITY.json',dict(archive_commit='d69e9ac94478c5be54cb46c622afec7aaf3c61f7',h1_index_git_path='research_artifacts/e5_h1_tail_coverage_pair_20261008/INDEX.json',tail_index_git_path='research_artifacts/native_20261008/INDEX.json',wrappers=expected_wrappers,sources=sources,coverage_authority=coverage_authority))
 save(a.output/'COVERAGE.json',dict(status='LIMITED_SOURCE_REPORTED_INTERVAL_AND_PROVIDER_COMPLETENESS_AUTHORITY',start_inclusive_us=START,end_exclusive_us=END,total_events=len(rows),year2024_events=5490,warmup_events=sum(r['event_us']<JAN for r in rows),all_requested_reference_events_recovered=True,year2024_reference_missing=0,warmup_reference_missing=0,source_reported_interval_null_count=sum(r['source_reported_interval_hours'] is None for r in rows),provider_complete_set_certified=False,original_rate_units_unchanged=True,settlement_time_limitation=manifest['funding_time_semantics'],groups=groups))
 save(a.output/'SCHEMA.json',dict(schema='existing_funding_input_observations_v1',event_us='Exact calc_time_ms*1000; preserve observed millisecond offsets, not arrival/charge certification',raw_rate_text='Exact original CSV token where present; null for existing Float64 parquet source',source_numeric_float64_hex='Exact Float64 original field representation, no unit scaling',existing_normalized_rate='Original hash-bound EVENTS raw_rate, preserved unchanged',source_reported_interval_hours='Original CSV reported field only; null when only normalized parquet exists',existing_normalized_interval_hours='Preserved original normalized field, NEVER used to fill source_reported interval',source_id='Key in SOURCE_IDENTITY.sources binding wrapper/member/hash',source_row='Actual zero-based parquet/data-row locator',scope='Sources only, no wallet/backtest/model/fit; no rebuilding missing common200bytes'))
 save(a.output/'EXTRACTION_RECEIPT.json',dict(status='PASS_REAL_EXISTING_SOURCE_EXPORT_LIMITED_AUTHORITY',event_count=len(rows),gzip_bytes=len(encoded),gzip_sha256=sha(encoded),uncompressed_jsonl_bytes=len(body),uncompressed_jsonl_sha256=sha(body),elapsed_seconds=time.monotonic()-begun,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,workers=1,cpu_count=1,new_wallets=0,fits=0,provider_requests=0,intervals_inferred=0));print('SOURCE_EXPORT_COMPLETE',len(rows),len(encoded),time.monotonic()-begun,flush=True)
if __name__=='__main__':main()
