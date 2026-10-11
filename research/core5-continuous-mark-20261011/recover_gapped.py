"""Preserve real official mark holes; finish unaffected source acquisition."""
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import shutil
import time
import numpy as np
from mark_source import (HERE,ROOT,PREFIX,PHASES,SYMBOLS,SourceReader,bind_current,configure,inventories,
    identity,decode,union,grid_gaps,measure,git,digest,save)

KEEP=('RV_1m','RSplus_1m','RSminus_1m','RV_5m','RSplus_5m','RSminus_5m','open','close','high','low','max_log_up','max_log_down','observed_minutes')


def observed_month(reader,row,left,right,daily_get=None,gaps=None):
    identity(row);frame,dups=decode(reader,row,left,right);original=len(frame);repairs=[]
    initial,initial_days=grid_gaps(frame,left,right)
    companions=[r for r in reader.inventory['reusable_price_archives'] if r['family']=='markPriceKlines'
        and r['frequency']=='daily' and r['symbol']==row['symbol'] and r['month']==row['month']]
    companions+=row.get('new_daily_repairs',[])
    for d in companions:
        day=int(d['source_period'][-2:]);l=left+(day-1)*86400000
        f,dd=decode(reader,d,l,l+86400000);frame,e=union(frame,f,left,right)
        repairs.append(dict(source=d,observed_daily_minutes=len(f),identical_daily_duplicates=dd,**e))
    missing,days=grid_gaps(frame,left,right)
    if len(missing) and daily_get is not None:
        if gaps is not None:
            gaps.append(dict(stage='BEFORE_OFFICIAL_DAILY',symbol=row['symbol'],month=row['month'],missing_open_ms=missing.tolist()))
            (reader.state/'GAPS.json').write_text(json.dumps(gaps,indent=2)+'\n')
        for stamp in days:
            d=daily_get(row['symbol'],stamp);day=int(stamp[-2:]);l=left+(day-1)*86400000
            f,dd=decode(reader,d,l,l+86400000);frame,e=union(frame,f,left,right)
            repairs.append(dict(source=d,observed_daily_minutes=len(f),identical_daily_duplicates=dd,**e))
            row.setdefault('new_daily_repairs',[]).append(d)
        missing,days=grid_gaps(frame,left,right)
    if gaps is not None and len(missing):
        gaps.append(dict(stage='AFTER_MONTH_AND_OFFICIAL_DAYS',symbol=row['symbol'],month=row['month'],missing_open_ms=missing.tolist(),missing_days=days))
        (reader.state/'GAPS.json').write_text(json.dumps(gaps,indent=2)+'\n')
    return frame,dict(source=row,original_month_rows=original,observed_minutes=len(frame),original_missing_minutes=len(initial),
        identical_month_duplicates=dups,repairs=repairs,remaining_missing_open_ms=missing.tolist(),CRC=True,exact_complete_grid=not len(missing))


def observed_primitives(frame,past,left,right):
    n=(right-left)//86400000;result={k:np.full(n,np.nan) for k in KEEP};previous=past
    for i in range(n):
        l=left+i*86400000;r=l+86400000;d=frame[(frame.timestamp_ms>=l)&(frame.timestamp_ms<r)].reset_index(drop=True)
        result['observed_minutes'][i]=len(d)
        if len(d)==1440 and np.array_equal(d.timestamp_ms.to_numpy(),np.arange(l,r,60000)):
            v,_,_=measure(d,previous)
            for k in KEEP:result[k][i]=v[k][0]
        else:
            # Partialday extremes andvariation cannotcertify missingminute prices.
            if len(d) and d.timestamp_ms.iloc[0]==l:result['open'][i]=d.open.iloc[0]
            if len(d) and d.timestamp_ms.iloc[-1]==r-60000:result['close'][i]=d.close.iloc[-1]
        previous=float(d.close.iloc[-1]) if len(d) and d.timestamp_ms.iloc[-1]==r-60000 else None
    five_times=np.arange(left+4*60000,right,300000,dtype=np.int64)
    five=frame.set_index('timestamp_ms').close.reindex(five_times).to_numpy(dtype=float)
    return result,np.arange(left+86400000,right+86400000,86400000,dtype=np.int64)*1000,five


def run(state,source,previous_commit,cache):
    phase='Q32022';assert git('rev-parse','HEAD').decode().strip()==source and not git('status','--porcelain')
    assert state.resolve().is_relative_to(Path('/workspace')) and not state.exists();state.mkdir();configure(state,phase)
    for line in (HERE/'GAPPED_SOURCE_SHA256.txt').read_text().splitlines():
        sha,p=line.split(maxsplit=1);assert digest((ROOT/p).read_bytes())==sha
    inv,oldhash,invsha,hashsha=inventories();gaps=[];records=[];newbytes=0;downloads=0;cached=0;start=time.monotonic()
    previous_raw=git('show',previous_commit+':'+PREFIX+'phases/Q22022/RECOVERY.json')
    previous=bind_current(json.loads(previous_raw),previous_commit);prior=previous['end_boundaries']
    priorbytes=previous['cumulative_new_original_bytes']
    # Cache is our failed unpublishedattempt, not vanished2026ledgers or aprivatecold dependency.
    assert cache==Path('/workspace/mark-continuous-state/Q32022')
    shutil.copytree(cache/'raw',state/'raw')
    from modules.collector_research.pipeline.download import Job,fetch,session
    from modules.collector_research.pipeline.normalize import month_limits
    reader=SourceReader(inv,state,local=False);days=[];fives=[];times=[]
    def bounded():
        assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=16106127360
        assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<1000000000
    save(state/'STARTED.json',dict(phase=phase,source_commit=source,ownfailed_cache=str(cache),prior_public_newbytes=priorbytes,fits=0,wallets=0))
    with session() as connection:
        def acquire(symbol,stamp):
            nonlocal newbytes,downloads,cached
            assert priorbytes+newbytes+8*2**20<=100000000 and newbytes+8*2**20<=35000000
            bounded();y,m=map(int,stamp[:7].split('-'));d=int(stamp[-2:]) if len(stamp)==10 else None
            job=Job(symbol,'markPriceKlines',y,m,d);r=fetch(job,connection)
            assert r['status']!='ARCHIVE_UNAVAILABLE_UNCLASSIFIED','Official404 unknown, cannotcomplete sourcephase'
            newbytes+=r['bytes'];downloads+=int(r['status']=='DOWNLOADED_VERIFIED');cached+=int(r['status']=='VERIFIED_CACHE')
            check=Path(str(job.path)+'.CHECKSUM').read_bytes()
            row=dict(kind='NEW_OFFICIAL_RAW',wrapper_id='NEW',symbol=symbol,family='markPriceKlines',month=stamp[:7],
                source_period=stamp,frequency='daily' if d else 'monthly',ZIP_bytes=r['bytes'],ZIP_SHA256=r['sha256'],
                CHECKSUM_member_SHA256=digest(check),official_checksum_text=check.decode(),official_URL=job.url,
                raw_path=str(job.path.relative_to(state)),cache_status=r['status'],verified_UTC=datetime.now(timezone.utc).isoformat())
            if d is None:
                h=next(x for x in oldhash['price_source_receipts'] if x['family']=='markPriceKlines' and x['symbol']==symbol and x['month']==stamp)
                assert h['sha256']==row['ZIP_SHA256'] and h['bytes']==row['ZIP_bytes']
                row.update(prior_HASH_ONLY_receipt_SHA256=h['sha256'],matches_prior_HASH_ONLY_receipt=True)
            return row
        try:
            for y,m in PHASES[phase]:
                left,right=month_limits(y,m);daily={};five=[];clock=None
                for s in SYMBOLS:
                    row=acquire(s,f'{y}-{m:02d}');f,e=observed_month(reader,row,left,right,acquire,gaps)
                    past=prior[s];assert past['open_ms']==left-60000 and past['available_us']==left*1000
                    v,t,c=observed_primitives(f,past['close'],left,right)
                    for k,a in v.items():daily.setdefault(k,[]).append(a)
                    if clock is None:clock=t
                    np.testing.assert_array_equal(clock,t)
                    assert f.timestamp_ms.iloc[-1]==right-60000,'Unknownmonthend cannot become inventedboundary'
                    e['past_boundary']=past;e['end_boundary']=dict(close=float(f.close.iloc[-1]),open_ms=right-60000,available_us=right*1000,source=row)
                    prior[s]=e['end_boundary'];records.append(e);five.append(c)
                    print('OBSERVED_MARK_MONTH',s,row['month'],len(f),'rows, missing',len(e['remaining_missing_open_ms']),flush=True);bounded()
                days.append({k:np.column_stack(v) for k,v in daily.items()});fives.append(np.column_stack(five));times.append(clock)
        except Exception as exc:
            save(state/'BLOCKED.json',dict(error=str(exc),HTTP_status=getattr(getattr(exc,'response',None),'status_code',None),
                sources_completed=len(records),gaps=gaps,new_original_bytes=newbytes,no_denial_retry_or_bypass=True));raise
        finally:reader.close()
    full={k:np.concatenate([d[k] for d in days]) for k in KEEP};at=np.concatenate(times);five=np.concatenate(fives)
    np.savez_compressed(state/'DAILY.npz',symbol_order=np.asarray(SYMBOLS),available_us=at,**full)
    ft=np.arange(at[0]-86400000000+300000000,at[-1]+300000000,300000000,dtype=np.int64)
    np.savez_compressed(state/'FIVE_MIN.npz',symbol_order=np.asarray(SYMBOLS),available_us=ft,close=five)
    missing=sum(len(r['remaining_missing_open_ms']) for r in records)
    proof=dict(status='PARTIAL_REAL_MARK_PHASE_WITH_OFFICIAL_GAPS',phase=phase,source_commit=source,
        protocol_SHA256=digest((HERE/'GAPPED_SOURCE_PROTOCOL.json').read_bytes()),source_inventory_SHA256=invsha,
        source_binding_manifest='GAPPED_SOURCE_SHA256.txt',hash_only_SHA256=hashsha,
        calendar_days=len(at),valid_joint_RV_days=int(np.isfinite(full['RV_1m']).all(1).sum()),actual_minutes=sum(r['observed_minutes'] for r in records),
        remaining_missing_minutes=missing,sources=records,end_boundaries=prior,previous_proof_SHA256=digest(previous_raw),
        new_original_bytes=newbytes,cumulative_new_original_bytes=priorbytes+newbytes,provider_downloaded_ZIPs=downloads,
        verified_ownfailed_cache_ZIPs=cached,gaps=gaps,
        official_daily_repairs_added=sum(x['added_actual_rows'] for r in records for x in r['repairs']),
        official_daily_common_rows_verified=sum(x['common_rows'] for r in records for x in r['repairs']),
        artifacts={p.name:digest(p.read_bytes()) for p in state.glob('*.npz')},fits=0,wallets=0,labels_created=0,
        elapsed_seconds=time.monotonic()-start,full_minute_continuity=False,no_imputation=True,
        domain='IndependentofficialmarkPriceKlines, actualholes remainUNKNOWN; not full698daynativecertification')
    save(state/'RECOVERY.json',proof);print(json.dumps({k:v for k,v in proof.items() if k in ('status','actual_minutes','remaining_missing_minutes','calendar_days','valid_joint_RV_days','new_original_bytes','provider_downloaded_ZIPs','verified_ownfailed_cache_ZIPs','elapsed_seconds')}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--previous-commit',required=True);p.add_argument('--cache',type=Path,required=True)
    a=p.parse_args();run(a.state,a.source_commit,a.previous_commit,a.cache)
