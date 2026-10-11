"""Thin domain-bound adapter over public collector and source recovery APIs."""
import argparse
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
BASE_SOURCE='306b58c4a52035ac9f374de7c25d40dff22fb658'
OLD_PREFIX='research/core5-continuous-risk600-20261011/'
PREFIX='research/core5-continuous-mark-20261011/'
sys.path.insert(0,str(ROOT/OLD_PREFIX))
from prepare import bind_current,digest,git,save
from mark_reader import MarkSourceReader as SourceReader
from primitives import SYMBOLS,measure

PHASES={'REUSE_2021_JAN_NOV':[(2021,m) for m in range(1,12)],'DEC2021':[(2021,12)],
        'Q12022':[(2022,m) for m in range(1,4)],'Q22022':[(2022,m) for m in range(4,7)],
        'Q32022':[(2022,m) for m in range(7,10)],'REUSE_OCTNOV2022':[(2022,10),(2022,11)]}


def inventories():
    raw=git('show',BASE_SOURCE+':'+OLD_PREFIX+'SOURCE_COVERAGE.json')
    inv=json.loads(raw)
    hraw=git('show',BASE_SOURCE+':'+OLD_PREFIX+'HASH_ONLY_PRIOR_RECEIPTS.json')
    return inv,json.loads(hraw),digest(raw),digest(hraw)


def configure(state,phase):
    first,last=PHASES[phase][0],PHASES[phase][-1]
    import calendar
    os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),SYMBOLS=','.join(SYMBOLS),
        WARMUP_START=f'{first[0]}-{first[1]:02d}-01',START_DATE=f'{first[0]}-{first[1]:02d}-01',
        END_DATE=f'{last[0]}-{last[1]:02d}-{calendar.monthrange(*last)[1]:02d}',
        FAMILIES='klines,markPriceKlines,fundingRate',HTTP_RETRIES='0',HTTP_CONNECT_TIMEOUT='10',HTTP_READ_TIMEOUT='20',
        MAX_ARCHIVE_MIB='8',MAX_UNCOMPRESSED_MIB='64',MAX_WORK_GIB='16',MIN_FREE_GIB='15',REFRESH_CHECKSUMS='0')


def identity(row):
    if row.get('kind')=='DAILY_UNION':
        assert row['family']=='markPriceKlines'
        for r in row['daily_sources']:
            if r['symbol']!=row['symbol'] or r['month']!=row['month']:
                raise ValueError('Daily union symbol/month identity mismatch')
            identity(r)
        return
    if row['family']!='markPriceKlines' or row['symbol'] not in SYMBOLS:
        raise ValueError('Independent markPriceKlines identity required')
    period=row.get('source_period',row['month'])
    frequency='daily' if len(period)==10 else 'monthly'
    stem=f"{row['symbol']}-1m-{period}.zip"
    wanted=f"https://data.binance.vision/data/futures/um/{frequency}/markPriceKlines/{row['symbol']}/1m/{stem}"
    if row['official_URL']!=wanted or row['frequency']!=frequency or period[:7]!=row['month']:
        raise ValueError('Wrong source domain/clock/period/symbol identity')


def decode(reader,row,left,right):
    from modules.collector_research.pipeline.download import parse_checksum,check_zip
    from modules.collector_research.pipeline.normalize import numeric_csv,validate_price
    identity(row)
    if row.get('kind')=='NEW_OFFICIAL_RAW':
        p=reader.state/row['raw_path'];raw=p.read_bytes();check=Path(str(p)+'.CHECKSUM').read_bytes()
    else:raw,check=reader.read(row)
    assert digest(raw)==row['ZIP_SHA256']==parse_checksum(check.decode(),row['official_URL'].split('/')[-1])
    assert len(raw)==row['ZIP_bytes']
    p=reader.state/row['official_URL'].split('/')[-1]
    with p.open('xb') as f:f.write(raw)
    try:
        check_zip(p)
        return validate_price(numeric_csv(p),'markPriceKlines',left,right)
    finally:p.unlink()


def union(frame,daily,left,right):
    from modules.collector_research.pipeline.normalize import validate_price
    common=frame[frame.timestamp_ms.isin(daily.timestamp_ms)].reset_index(drop=True)
    other=daily[daily.timestamp_ms.isin(common.timestamp_ms)].reset_index(drop=True)
    if not np.array_equal(common.to_numpy(),other.to_numpy()):
        raise ValueError('Conflicting monthly/daily numeric source overlap')
    merged,duplicates=validate_price(pd.concat([frame,daily],ignore_index=True),'markPriceKlines',left,right)
    assert duplicates==len(common)
    return merged,dict(common_rows=len(common),added_actual_rows=len(daily)-len(common),all_common_numeric_fields_exact=True)


def grid_gaps(frame,left,right):
    grid=np.arange(left,right,60000,dtype=np.int64)
    missing=np.setdiff1d(grid,frame.timestamp_ms.to_numpy())
    return missing,sorted({datetime.fromtimestamp(int(t)/1000,timezone.utc).date().isoformat() for t in missing})


def complete_month(reader,row,left,right,acquire_daily=None,gap_records=None):
    from modules.collector_research.pipeline.normalize import validate_price
    identity(row)
    duplicates=0;repairs=[]
    if row.get('kind')=='DAILY_UNION':
        blocks=[]
        for d in row['daily_sources']:
            day=int(d['source_period'][-2:]);l=left+(day-1)*86400000
            f,dups=decode(reader,d,l,l+86400000);blocks.append(f);duplicates+=dups
        frame,_=validate_price(pd.concat(blocks,ignore_index=True),'markPriceKlines',left,right)
    else:frame,duplicates=decode(reader,row,left,right)
    original=len(frame)
    initial_missing,initial_days=grid_gaps(frame,left,right)
    if len(initial_missing) and gap_records is not None:
        gap_records.append(dict(stage='ORIGINAL_MONTH_BEFORE_DAILY_REPAIR',symbol=row['symbol'],month=row['month'],
            missing_minutes=len(initial_missing),missing_open_ms=initial_missing.tolist(),missing_days=initial_days,no_imputation=True))
        (reader.state/'GAPS.json').write_text(json.dumps(gap_records,indent=2)+'\n')
    # Always verify alreadyarchived daily companions, including complete-month overlap.
    companions=[d for d in reader.inventory['reusable_price_archives'] if d['family']=='markPriceKlines'
                and d['frequency']=='daily' and d['symbol']==row['symbol'] and d['month']==row['month']]
    companions+=row.get('new_daily_repairs',[])
    for d in companions:
        day=int(d['source_period'][-2:]);l=left+(day-1)*86400000
        daily,dups=decode(reader,d,l,l+86400000)
        assert dups==0 and len(daily)==1440
        frame,e=union(frame,daily,left,right);repairs.append(dict(source=d,**e))
    missing,days=grid_gaps(frame,left,right)
    if len(missing):
        gap=dict(symbol=row['symbol'],month=row['month'],missing_minutes=len(missing),
                 missing_open_ms=missing.tolist(),missing_days=days,no_imputation=True)
        if gap_records is not None:
            gap_records.append(dict(stage='REMAINING_BEFORE_NEW_DAILY_FETCH',**gap))
            (reader.state/'GAPS.json').write_text(json.dumps(gap_records,indent=2)+'\n')
        if acquire_daily is not None:
            for stamp in days:
                d=acquire_daily(row['symbol'],stamp)
                day=int(stamp[-2:]);l=left+(day-1)*86400000
                daily,dups=decode(reader,d,l,l+86400000)
                assert dups==0 and len(daily)==1440
                frame,e=union(frame,daily,left,right);repairs.append(dict(source=d,**e))
                row.setdefault('new_daily_repairs',[]).append(d)
            missing,days=grid_gaps(frame,left,right)
        if len(missing):raise ValueError(json.dumps(dict(gap,remaining_missing_minutes=len(missing))))
    assert np.array_equal(frame.timestamp_ms.to_numpy(),np.arange(left,right,60000,dtype=np.int64))
    return frame,dict(source=row,original_month_rows=original,observed_minutes=len(frame),
                     original_missing_minutes=len(initial_missing),identical_month_duplicates=duplicates,
                     repairs=repairs,CRC=True,exact_complete_grid=True)


def bindings(manifest):
    assert manifest in ('SOURCE_SHA256.txt','SOURCE_CURRENT_SHA256.txt')
    for line in (HERE/manifest).read_text().splitlines():
        sha,p=line.split(maxsplit=1);assert digest((ROOT/p).read_bytes())==sha,p


def run(phase,state,source,previous_commit=None,source_manifest='SOURCE_SHA256.txt'):
    assert git('rev-parse','HEAD').decode().strip()==source and not git('status','--porcelain')
    assert state.resolve().is_relative_to(Path('/workspace')) and not state.exists()
    bindings(source_manifest);state.mkdir();configure(state,phase)
    from modules.collector_research.pipeline.download import Job,fetch,session
    from modules.collector_research.pipeline.normalize import month_limits
    from modules.collector_research.pipeline.common import bounds
    bounds();inv,oldhash,invsha,hashsha=inventories()
    plan=json.loads((HERE/'INVENTORY.json').read_text())
    assert plan['coverage_SHA256']==invsha and plan['hash_only_SHA256']==hashsha
    start=time.monotonic();newbytes=0;downloads=0;gaps=[];unavailable=[];records=[];prior={s:None for s in SYMBOLS}
    previous_sha=None;prior_newbytes=0
    preceding=list(PHASES)[:list(PHASES).index(phase)]
    for oldphase in preceding:
        b=git('show',source+':'+PREFIX+'phases/'+oldphase+'/RECOVERY.json')
        p=json.loads(b);prior_newbytes+=p['new_original_bytes']
    if preceding:
        assert previous_commit
        b=git('show',previous_commit+':'+PREFIX+'phases/'+preceding[-1]+'/RECOVERY.json')
        p=bind_current(json.loads(b),previous_commit);prior=p['end_boundaries'];previous_sha=digest(b)
        assert git('show',source+':'+PREFIX+'phases/'+preceding[-1]+'/RECOVERY.json')==b
    def bounded():
        assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=16106127360
        assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<=1000000000
    save(state/'STARTED.json',dict(phase=phase,source_commit=source,source_inventory_SHA256=invsha,
        domain='BinanceUSD-MmarkPriceKlines',prior_public_newbytes=prior_newbytes,fits=0,wallets=0))
    reader=SourceReader(inv,state,local=False)
    days=[];fives=[];times=[]
    with session() as connection:
        def acquire(symbol,stamp):
            nonlocal newbytes,downloads
            y,m=map(int,stamp[:7].split('-'));d=int(stamp[-2:]) if len(stamp)==10 else None
            assert prior_newbytes+newbytes+8*2**20<=100000000 and newbytes+8*2**20<=35000000
            bounded();job=Job(symbol,'markPriceKlines',y,m,d)
            result=fetch(job,connection)
            if result['status']=='ARCHIVE_UNAVAILABLE_UNCLASSIFIED':
                unavailable.append(dict(official_URL=job.url,HTTP_status=404,status='UNKNOWN_ARCHIVE_UNAVAILABLE'))
                save(state/f'UNAVAILABLE-{job.stem}.json',unavailable[-1]);return None
            newbytes+=result['bytes'];downloads+=int(result['status']=='DOWNLOADED_VERIFIED');bounded()
            check=Path(str(job.path)+'.CHECKSUM').read_bytes()
            row=dict(kind='NEW_OFFICIAL_RAW',wrapper_id='NEW',symbol=symbol,family='markPriceKlines',
                month=stamp[:7],source_period=stamp,frequency='daily' if d else 'monthly',ZIP_bytes=result['bytes'],
                ZIP_SHA256=result['sha256'],CHECKSUM_member_SHA256=digest(check),official_checksum_text=check.decode(),
                official_URL=job.url,raw_path=str(job.path.relative_to(state)),verified_UTC=datetime.now(timezone.utc).isoformat())
            if d is None:
                old=next(r for r in oldhash['price_source_receipts'] if r['family']=='markPriceKlines'
                         and r['symbol']==symbol and r['month']==stamp)
                row.update(prior_HASH_ONLY_receipt_SHA256=old['sha256'],matches_prior_HASH_ONLY_receipt=
                           row['ZIP_SHA256']==old['sha256'] and row['ZIP_bytes']==old['bytes'])
                assert row['matches_prior_HASH_ONLY_receipt'],'Changed old source identity requires review'
            return row
        def daily(symbol,stamp):
            row=acquire(symbol,stamp)
            if row is None:raise ValueError('Official daily404 remainsUNKNOWN, incompletephase')
            return row
        try:
            for y,m in PHASES[phase]:
                left,right=month_limits(y,m);measured={};five=[];clock=None
                for symbol in SYMBOLS:
                    stamp=f'{y}-{m:02d}'
                    row=next((r.copy() for r in inv['reusable_price_archives'] if r['family']=='markPriceKlines'
                        and r['frequency']=='monthly' and r['symbol']==symbol and r['month']==stamp),None)
                    if row is None:
                        assert stamp=='2021-12' or (y==2022 and 1<=m<=9)
                        row=acquire(symbol,stamp)
                        if row is None:
                            count=(right-left)//86400000
                            ds=[daily(symbol,f'{stamp}-{d:02d}') for d in range(1,count+1)]
                            row=dict(kind='DAILY_UNION',symbol=symbol,family='markPriceKlines',month=stamp,daily_sources=ds)
                    frame,e=complete_month(reader,row,left,right,daily,gaps)
                    # Persist gaps immediately rather than silently filling monthly omissions.
                    if gaps and not (state/'GAPS.json').exists():save(state/'GAPS.json',gaps)
                    elif gaps:(state/'GAPS.json').write_text(json.dumps(gaps,indent=2)+'\n')
                    past=prior[symbol]
                    if past is not None:
                        assert past['open_ms']==left-60000 and past['available_us']==left*1000
                        identity(past['source'])
                    result,t,c=measure(frame,None if past is None else past['close'])
                    for name,v in result.items():
                        if name not in ('volume','quote_volume','trades','zero_quote_minutes','zero_trade_minutes'):
                            measured.setdefault(name,[]).append(v)
                    if clock is None:clock=t
                    np.testing.assert_array_equal(clock,t)
                    e['past_boundary']=past
                    e['end_boundary']=dict(close=float(frame.close.iloc[-1]),open_ms=right-60000,
                        available_us=right*1000,source=row)
                    prior[symbol]=e['end_boundary'];records.append(e);five.append(c)
                    print('MARK_MONTH_COMPLETE',phase,symbol,stamp,len(frame),'actual independentmark minutes',flush=True)
                    bounded()
                days.append({k:np.column_stack(v) for k,v in measured.items()});fives.append(np.column_stack(five));times.append(clock)
        except Exception as exc:
            save(state/'BLOCKED.json',dict(phase=phase,error=str(exc),HTTP_status=getattr(getattr(exc,'response',None),'status_code',None),
                completed_sources=len(records),new_original_bytes=newbytes,gaps=gaps,unavailable=unavailable,
                no_access_denial_retry_or_bypass=True,fits=0,wallets=0));raise
        finally:reader.close()
    available=np.concatenate(times);full={k:np.concatenate([d[k] for d in days]) for k in days[0]}
    np.savez_compressed(state/'DAILY.npz',symbol_order=np.asarray(SYMBOLS),available_us=available,**full)
    five=np.concatenate(fives);ft=np.arange(available[0]-86400000000+300000000,available[-1]+300000000,300000000,dtype=np.int64)
    np.savez_compressed(state/'FIVE_MIN.npz',symbol_order=np.asarray(SYMBOLS),available_us=ft,close=five)
    assert len(ft)==len(five) and np.all(np.diff(available)==86400000000)
    valid=np.isfinite(full['RV_1m']).all(1)
    proof=dict(status='PASS_REAL_CONTINUOUS_INDEPENDENT_MARK_PHASE',phase=phase,source_commit=source,
        source_binding_manifest=source_manifest,
        protocol_SHA256=digest((HERE/'PROTOCOL.json').read_bytes()),source_inventory_SHA256=invsha,
        plan_SHA256=digest((HERE/'INVENTORY.json').read_bytes()),hash_only_SHA256=hashsha,
        code_SHA256={name:digest((HERE/name).read_bytes()) for name in ('mark_source.py','publish_mark.py','cold_mark.py')},
        calendar_days=len(available),valid_joint_RV_days=int(valid.sum()),actual_minutes=sum(r['observed_minutes'] for r in records),
        sources=records,end_boundaries=prior,previous_proof_SHA256=previous_sha,new_original_bytes=newbytes,
        provider_downloaded_ZIPs=downloads,cumulative_new_original_bytes=prior_newbytes+newbytes,
        gaps=gaps,unavailable=unavailable,official_daily_repairs_added=sum(x['added_actual_rows'] for r in records for x in r['repairs']),
        official_daily_common_rows_verified=sum(x['common_rows'] for r in records for x in r['repairs']),
        artifacts={p.name:digest(p.read_bytes()) for p in state.glob('*.npz')},first_unknown_boundary_preserved=not preceding,
        fits=0,wallets=0,labels_created=0,elapsed_seconds=time.monotonic()-start,
        domain='IndependentofficialBinanceUSD-MmarkPriceKlines; no trade substitute or precisefundingcharge mark claim',
        clock='Followingminute/day closure, not actualhistoricalpublication/arrivalcertificate')
    bounded();save(state/'RECOVERY.json',proof)
    print(json.dumps({k:v for k,v in proof.items() if k in ('status','phase','calendar_days','valid_joint_RV_days','actual_minutes','new_original_bytes','elapsed_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=PHASES,required=True);p.add_argument('--state',type=Path,required=True)
    p.add_argument('--source-commit',required=True);p.add_argument('--previous-commit')
    p.add_argument('--source-manifest',choices=('SOURCE_SHA256.txt','SOURCE_CURRENT_SHA256.txt'),default='SOURCE_SHA256.txt')
    a=p.parse_args();run(a.phase,a.state,a.source_commit,a.previous_commit,a.source_manifest)
