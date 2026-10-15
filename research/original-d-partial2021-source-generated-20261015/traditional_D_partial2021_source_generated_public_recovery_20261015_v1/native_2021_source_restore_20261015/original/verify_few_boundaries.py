"""Few independent raw-CSV boundary checks after completion; no redownload."""
import os,resource
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[k]='1'
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import csv,hashlib,io,json,math,zipfile
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parent;P=Path(os.environ.get('COIN_2021_SOURCE_OUT',str(ROOT/'prepared_2021')));S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');MIN=60000000;START=1609459200000000
def raw_rows(body):
    with zipfile.ZipFile(io.BytesIO(body)) as z:raw=z.read(z.namelist()[0])
    for row in csv.reader(io.StringIO(raw.decode('utf-8-sig'))):
        if row[0].strip().lower() in ('open_time','open_timestamp'):continue
        yield row
def main():
    index=json.loads((P/'SOURCE_INDEX.json').read_text());assert index['status']=='PASS_FULL2021_REAL_TRADE_MARK_SOURCE_ONLY';events=json.loads((P/'EVENTS.json').read_text());proofs=[]
    with np.load(P/'months/2021-01.npz') as jan, np.load(P/'months/2021-07.npz') as july, np.load(P/'months/2021-11.npz') as nov, np.load(P/'months/2021-12.npz') as dec, zipfile.ZipFile(ROOT/'source/Y2021.zip') as outer:
        for s in S:
            first=next(raw_rows(outer.read(f'raw/klines/{s}/{s}-1m-2021-01.zip')));assert int(first[0])*1000==START and int(first[6])*1000+1000==START+MIN;assert math.isclose(float(first[4]),float(jan[s+'_close'][0]),rel_tol=1e-12);proofs.append(dict(symbol=s,check='FIRST_REAL_EXECUTION_QUOTE',open_us=START,available_us=START+MIN,source_close=float(first[4])))
            row=next(r for r in index['months'][11]['sources'] if r['symbol']==s and r['family']=='markPriceKlines');boundary=row['past_boundary'];assert boundary['close']==float(nov[s+'_mark'][-1]);assert int(nov['available_us'][-1])==int(dec['times'][0])==boundary['available_us'];proofs.append(dict(symbol=s,check='NOV_DEC_REAL_MARK_BOUNDARY',available_us=int(boundary['available_us']),prior_close=boundary['close']))
            event=next(r for r in events if r['symbol']==s and r['event_us']==1640966400000000);quote=event['strict_prior_mark'];wanted=event['event_us']-2*MIN;assert quote['mark_open_us']==wanted and quote['mark_available_us']==event['event_us']-MIN and quote['strict_prior_age_us']==MIN
            source_body=(ROOT/'source/DEC2021'/s/(s+'-1m-2021-12.zip')).read_bytes();raw=next(r for r in raw_rows(source_body) if int(r[0])*1000==wanted);assert math.isclose(float(raw[4]),quote['mark_close'],rel_tol=1e-12);pos=int(np.searchsorted(dec['times'],wanted));assert dec['times'][pos]==wanted and float(dec[s+'_mark'][pos])==quote['mark_close'];proofs.append(dict(symbol=s,check='RESTORED_DEC31_16H_REAL_STRICT_PRIOR',event_us=event['event_us'],raw_mark_open_us=wanted,raw_mark_available_us=int(raw[6])*1000+1000,raw_mark_close=float(raw[4]),strict_prior_mark_close=quote['mark_close'],independent_CSV_float_bits_equal=bool(float(raw[4])==quote['mark_close'])))
        for s in ('BTCUSDT','SOLUSDT','XRPUSDT'):
            original=set(int(r[0])*1000 for r in raw_rows(outer.read(f'raw/markPriceKlines/{s}/{s}-1m-2021-07.zip')))
            row=next(r for r in index['months'][6]['sources'] if r['symbol']==s and r['family']=='markPriceKlines');assert len(row['repair_sources'])==5
            for repair in row['repair_sources']:
                r=next(raw_rows(outer.read(repair['member'])));open_us=int(r[0])*1000;assert open_us not in original;pos=int(np.searchsorted(july['times'],open_us));assert july['times'][pos]==open_us and math.isclose(float(r[4]),float(july[s+'_mark'][pos]),rel_tol=1e-12);proofs.append(dict(symbol=s,check='REAL_DAILY_REPAIR_MISSING_MONTHLY_MINUTE',original_daily_member=repair['member'],open_us=open_us,raw_daily_close=float(r[4]),prepared_mark_close=float(july[s+'_mark'][pos])))
    assert len(proofs)==30
    result=dict(status='PASS_30_INDEPENDENT_RAW_CSV_SOURCE_BOUNDARY_CHECKS',checks=proofs,source_index_SHA256=hashlib.sha256((P/'SOURCE_INDEX.json').read_bytes()).hexdigest(),scope='Five first execution quotes, five Nov-Dec boundaries, five final restored funding events, fifteen original-daily repair examples. No full rerun or repeated download.',provider_downloads=0,targets=0,wallets=0,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    (ROOT/'POSTSOURCE_QA.json').write_text(json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n');print(result['status'],result['peak_RSS_bytes'])
if __name__=='__main__':main()
