"""Close the 2021 source gates only. No target or wallet generation is possible."""
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[k]='1'
import resource
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
if hasattr(os,'sched_setaffinity'):os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
import hashlib,io,json,shutil,time,zipfile
from pathlib import Path
import numpy as np
from source_parser import S,MINUTE,DAY,START,END,sha,limits,utc,parse_zip,union_exact,complete_grid,aggregate_daily,strict_prior
ROOT=Path(__file__).resolve().parent;OUT=Path(os.environ.get('COIN_2021_SOURCE_OUT',str(ROOT/'prepared_2021')));SRC=ROOT/'source';CUBE=Path(os.environ.get('COIN_CUBE_PATH',str(ROOT.parent/'coin_cs_sma_recovery_20261013/inputs/Y2023.npz')))
def fsha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def save(path,data):path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n')
def main():
    started=time.monotonic();restore=json.loads((ROOT/'PUBLIC_GIT_RESTORE_RECEIPT.json').read_text());assert restore['status']=='PASS_ALL222_REAL2021_PUBLIC_PARTS_SHA_CRC_LOCAL'
    y=json.loads((ROOT/'evidence/Y2021_INDEX.json').read_text());mark=json.loads((ROOT/'evidence/DEC2021_RECOVERY.json').read_text());members={r['name']:r for r in y['members']};dec={r['source']['symbol']:r['source'] for r in mark['sources']}
    assert fsha(SRC/'Y2021.zip')==y['package_SHA256'];assert fsha(CUBE)=='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f'
    with np.load(CUBE,allow_pickle=False) as z:assert tuple(z['symbol_order'])==S;cube_t=z['close_available_us'].copy();cube_price=z['close'].copy()
    rawevents=json.loads((ROOT/'RAW_FUNDING_EVENTS.json').read_text());assert len(rawevents)==5475;events_by_symbol={s:[dict(r) for r in rawevents if r['symbol']==s] for s in S};matched=[]
    assert not OUT.exists(),'Never overwrite a prepared source run';OUT.mkdir();(OUT/'months').mkdir()
    daily_t=np.arange(START+DAY,END+DAY,DAY,dtype=np.int64);daily_arrays={k:np.full((365,5),np.nan) for k in ('open','high','low','close','volume','quote_volume')};ready=np.zeros((365,5),dtype=bool)
    previous={};previous_mark_two={};months=[];streams=[];repair_total=0;daily_parity=0;year_minute_totals={'klines':0,'markPriceKlines':0}
    with zipfile.ZipFile(SRC/'Y2021.zip') as outer:
        def member(name):
            body=outer.read(name);rec=members[name];assert len(body)==rec['bytes'] and sha(body)==rec['SHA256'],name;return body
        for m in range(1,13):
            assert shutil.disk_usage(ROOT).free>15*1024**3,'Maintain 15GiB disk reserve'
            left,right=limits(2021,m);stamp=f'2021-{m:02}';times=np.arange(left,right,MINUTE,dtype=np.int64);arrays=dict(times=times,available_us=times+MINUTE);source_rows=[]
            for j,s in enumerate(S):
                for family in ('klines','markPriceKlines'):
                    name=f'raw/{family}/{s}/{s}-1m-{stamp}.zip';repairs=[];owners=None
                    if family=='markPriceKlines' and m==12:
                        row=dec[s];path=SRC/'DEC2021'/s/(s+'-1m-2021-12.zip');body=path.read_bytes();check=Path(str(path)+'.CHECKSUM').read_bytes();assert len(body)==row['ZIP_bytes'] and sha(body)==row['ZIP_SHA256'] and sha(check)==row['CHECKSUM_member_SHA256'];origin=dict(public_commit=restore['December_mark_public_commit'],parts=row['parts'],checksum_path=row['checksum_path'])
                    else:
                        body=member(name);check=member(name+'.CHECKSUM');origin=dict(public_commit=restore['year_public_commit'],wrapper_member=name)
                    assert check.decode().split()[0]==sha(body),'Official CHECKSUM disagrees with original ZIP'
                    f,parsed=parse_zip(body,family,left,right);observed_monthly=len(f);owners=np.zeros(len(times),dtype=np.int16);pos=(f.timestamp_ms.to_numpy(np.int64)*1000-left)//MINUTE;owners[:]=-1;owners[pos]=0
                    daily_names=sorted(n for n in members if n.startswith(f'raw/{family}/{s}/{s}-1m-{stamp}-') and n.endswith('.zip'))
                    for repair_id,n in enumerate(daily_names,1):
                        db=member(n);dc=member(n+'.CHECKSUM');assert dc.decode().split()[0]==sha(db);df,dr=parse_zip(db,family,left,right);before=set(f.timestamp_ms.to_numpy().tolist());f,evidence=union_exact(f,df);new_ts=[int(v) for v in df.timestamp_ms.to_numpy() if int(v) not in before];owners[(np.asarray(new_ts,dtype=np.int64)*1000-left)//MINUTE]=repair_id;repairs.append(dict(member=n,ZIP_SHA256=sha(db),CHECKSUM_SHA256=sha(dc),CSV=dr,**evidence));repair_total+=evidence['actual_daily_new_rows_added']
                    t=complete_grid(f,left,right);assert np.array_equal(t,times) and (owners>=0).all()
                    prior=previous.get((s,family));first_boundary=dict(status='UNKNOWN_NOT_FILLED',available_us=left,open_us=None,close=None) if prior is None else dict(status='REAL_PREVIOUS_MONTH_LAST_MINUTE',available_us=left,open_us=left-MINUTE,close=prior)
                    previous[(s,family)]=float(f.close.iloc[-1]);year_minute_totals[family]+=len(f)
                    if family=='klines':
                        for k in ('open','high','low','close','volume','quote_volume'):arrays[s+'_'+k]=f[k].to_numpy(float)
                        daily=aggregate_daily(f,left,right);idx=np.searchsorted(daily_t,daily['available_us']);assert np.array_equal(daily_t[idx],daily['available_us']);cp=np.searchsorted(cube_t,daily['available_us']);assert np.array_equal(cube_t[cp],daily['available_us']);assert daily['close'].tobytes()==cube_price[cp,j].tobytes(),'Daily real-trade close differs from original saved cube';daily_parity+=len(idx)
                        for k in daily_arrays:daily_arrays[k][idx,j]=daily[k]
                        ready[idx,j]=True
                    else:
                        for k in ('open','high','low'):arrays[s+'_mark_'+k]=f[k].to_numpy(float)
                        arrays[s+'_mark']=f.close.to_numpy(float)
                        prior_t,prior_c=previous_mark_two.get(s,(np.asarray([],dtype=np.int64),np.asarray([],dtype=float)));mt=np.concatenate((prior_t,t));mc=np.concatenate((prior_c,arrays[s+'_mark']))
                        for event in events_by_symbol[s]:
                            if left<=event['event_us']<right:
                                quote=strict_prior(event['event_us'],mt,mc);event['strict_prior_mark']=quote;event['strict_prior_mark_status']='PASS_REAL_MINUTE' if quote is not None else 'UNKNOWN_PRE2021_BOUNDARY';event['not_owned_under_fresh_CASH_start']=event['event_us']<START+MINUTE+1;matched.append(event)
                                assert quote is not None or (m==1 and event['not_owned_under_fresh_CASH_start']),'Owned-eligible event has no actual recent strict-prior mark'
                        previous_mark_two[s]=(t[-2:].copy(),arrays[s+'_mark'][-2:].copy())
                    record=dict(symbol=s,family=family,month=stamp,ZIP_SHA256=sha(body),ZIP_bytes=len(body),CHECKSUM_SHA256=sha(check),source_origin=origin,parsed=parsed,monthly_observed_minutes=observed_monthly,actual_complete_minutes=len(f),exact_clock_verified=True,first_open_us=int(t[0]),last_open_us=int(t[-1]),first_available_us=int(t[0]+MINUTE),last_available_us=int(t[-1]+MINUTE),past_boundary=first_boundary,repair_sources=repairs,source_owner_index_SHA256=sha(owners.tobytes()),no_forward_fill=True,no_trade_mark_substitution=True);source_rows.append(record);streams.append(record)
                    del f,body
            path=OUT/'months'/(stamp+'.npz');np.savez_compressed(path,**arrays);months.append(dict(month=stamp,minutes=len(times),source_NPZ_SHA256=fsha(path),source_NPZ_bytes=path.stat().st_size,sources=source_rows));print('2021_REAL_SOURCE_MONTH_CLOSED',stamp,len(times),flush=True)
    assert ready.all() and daily_parity==1825 and year_minute_totals=={'klines':2628000,'markPriceKlines':2628000} and repair_total==21600
    assert len(matched)==5475 and sum(r['strict_prior_mark'] is not None for r in matched)==5470 and sum(r['not_owned_under_fresh_CASH_start'] for r in matched)==5
    matched.sort(key=lambda r:(r['event_us'],r['symbol']));save(OUT/'EVENTS.json',matched);np.savez_compressed(OUT/'DAILY_OHLC.npz',symbol_order=np.asarray(S),available_us=daily_t,ready=ready,**daily_arrays)
    warm=json.loads((ROOT/'WARMUP_DIAGNOSTIC.json').read_text());fund=json.loads((ROOT/'FUNDING_DIAGNOSTIC.json').read_text());prefix_expected=(START,START+MINUTE);source_files={p.name:dict(SHA256=fsha(p),bytes=p.stat().st_size) for p in (OUT/'EVENTS.json',OUT/'DAILY_OHLC.npz')}
    result=dict(status='PASS_FULL2021_REAL_TRADE_MARK_SOURCE_ONLY',calendar_us=[START,END],calendar_UTC=[utc(START),utc(END)],symbols=list(S),days=365,minutes_per_asset_per_domain=525600,actual_minutes_per_domain=year_minute_totals,total_actual_minute_rows=5256000,monthly_streams=120,true_official_daily_repair_streams=15,true_daily_repair_added_minutes=repair_total,missing_minute_rows=0,original_archives_SHA_CHECKSUM_CRC='PASS',every_original_open_ms_and_close_ms_plus_one_clock_verified=True,source_clock_authority='Following-minute/day closure semantics; historical publication/arrival time not certified.',daily_complete_OHLC_cells=1825,all_daily_close_bits_equal_existing_cube=True,first_daily_OHLC_available_us=int(daily_t[0]),last_daily_OHLC_available_us=int(daily_t[-1]),Jan1_risk_daily_close='Existing saved daily cube value from completed 2020-12-31; not a reconstructed pre2021 minute quote.',Jan1_trade_and_mark_prior_month_boundary='UNKNOWN preserved; no synthetic December2020 minute.',first_fresh_CASH_execution_contract_us=START+MINUTE+1,first_real_execution_quote_open_us=START,first_real_execution_quote_available_us=START+MINUTE,funding_events=5475,real_strict_prior_mark_recomputed_events=5470,unknown_first_nonowned_events=5,funding_unit_authority='UNCONFIRMED authoritative rate units; raw numeric rates preserved. Any raw-fraction economics remain conditional.',CORE5_21close_ready_decisions=warm['CORE5_21close_ready_decisions'],CORE5_31close_ready_decisions=warm['CORE5_31close_ready_decisions'],CORE5_200close_ready_decisions=warm['CORE5_200close_ready_decisions'],CORE5_200close_first_ready_UTC=warm['CORE5_200close_first_ready_UTC'],fixed_fullfive_200close_Jan1_admitted=False,fixed_target_validation='Source is sufficient for calendar-matched fixed targets with original dynamic masks and declared fresh-CASH/terminal quote semantics. Targets and wallets require their own separate admission. A fullfive-200close Jan1 assumption is not admitted.',warmup_proof_SHA256=fsha(ROOT/'WARMUP_DIAGNOSTIC.json'),funding_raw_union_proof_SHA256=fsha(ROOT/'FUNDING_DIAGNOSTIC.json'),public_restore_proof_SHA256=fsha(ROOT/'PUBLIC_GIT_RESTORE_RECEIPT.json'),months=months,files=source_files,provider_downloads=0,targets_generated=0,wallets_created=0,historical_runs=0,Library_calls=0,uploads=0,retained_2026_opened=0,elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,CPU_affinity=list(os.sched_getaffinity(0)),AS_limit_bytes=2*1024**3,free_disk_bytes=shutil.disk_usage(ROOT).free)
    save(OUT/'SOURCE_INDEX.json',result);print(json.dumps({k:result[k] for k in ('status','total_actual_minute_rows','real_strict_prior_mark_recomputed_events','daily_complete_OHLC_cells','elapsed_seconds','peak_RSS_bytes')}),flush=True)
if __name__=='__main__':
    try:main()
    except Exception as e:save(ROOT/'SOURCE_STOP.json',dict(status='SOURCE_GATE_STOP',error_type=type(e).__name__,error=str(e),targets=0,wallets=0,provider_downloads=0));raise
