"""Source-bound continuous completed-day trade features, with no fits or labels."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime, timezone
import zipfile
import numpy as np
import pandas as pd
from primitives import SYMBOLS, measure

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PHASES={'Y2021':[(2021,m) for m in range(1,13)],'Q12022':[(2022,m) for m in range(1,4)],
        'Q22022':[(2022,m) for m in range(4,7)],'Q32022':[(2022,m) for m in range(7,10)],
        'OCTNOV2022_REUSE':[(2022,10),(2022,11)]}
OLD5='b4756ec8fb59457cfd8db74a79ca6a859f07f331'
OLD5PATH='research/har-rv-risk-20261011/RESULT_BUNDLE.zip'
OLD5SHA='534cea64e8aa6b27b51bba1b4ffa0ff2305e42843c6022d75a68cc301ec27b17'
digest=lambda b:hashlib.sha256(b).hexdigest()


def git(*args):
    return subprocess.check_output(['git',*args],cwd=ROOT)


def save(p,x):
    with p.open('x') as f:
        f.write(json.dumps(x,indent=2,sort_keys=True,allow_nan=False)+'\n')


def file_sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):
            h.update(b)
    return h.hexdigest()


def configure(state,phase):
    a,b=PHASES[phase][0],PHASES[phase][-1]
    import calendar
    os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),SYMBOLS=','.join(SYMBOLS),
        WARMUP_START=f'{a[0]}-{a[1]:02d}-01',START_DATE=f'{a[0]}-{a[1]:02d}-01',
        END_DATE=f'{b[0]}-{b[1]:02d}-{calendar.monthrange(*b)[1]:02d}',
        FAMILIES='klines,markPriceKlines,fundingRate',HTTP_RETRIES='0',HTTP_CONNECT_TIMEOUT='10',HTTP_READ_TIMEOUT='20',
        MAX_ARCHIVE_MIB='8',MAX_UNCOMPRESSED_MIB='64',MAX_WORK_GIB='16',MIN_FREE_GIB='15',REFRESH_CHECKSUMS='0')


class SourceReader:
    """Read only named authorized source members; public Git objects on cold runs."""
    def __init__(self,inventory,state,local=False):
        self.inventory=inventory;self.state=state;self.local=local;self.wrappers={}

    def wrapper(self,name):
        if name in self.wrappers:
            return self.wrappers[name]
        r=self.inventory['source_wrappers'][name]
        local={'Y2021':'/workspace/btc-beta-residual-state/minute-source/originals.zip',
               'BEAR2022NOV':'/workspace/core5-2022-rv-state/originals.zip'}.get(name)
        if self.local and local:
            p=Path(local)
        else:
            p=self.state/(name+'.zip')
            with p.open('xb') as f:
                if r.get('parts'):
                    for part in r['parts']:
                        b=git('cat-file','blob',part['oid'])
                        assert len(b)==part['size'] and digest(b)==part['SHA256']
                        f.write(b)
                else:
                    f.write(git('show',r['commit']+':'+r['path']))
        assert p.stat().st_size==r['bytes'] and file_sha(p)==r['SHA256']
        z=zipfile.ZipFile(p);self.wrappers[name]=z
        return z

    def read(self,row):
        if row.get('kind')=='NEW_PUBLIC_PARTS':
            b=b''.join(self.part(row['artifact_commit'],p) for p in row['parts'])
            check=git('show',row['artifact_commit']+':'+row['checksum_path'])
            assert digest(b)==row['ZIP_SHA256'] and digest(check)==row['CHECKSUM_member_SHA256']
            return b,check
        if row['wrapper_id']=='OCT2022_PUBLISHED':
            index=self.inventory['source_wrappers']['OCT2022_PUBLISHED']
            raw=git('show',index['commit']+':'+index['index_path'])
            assert digest(raw)==index['index_SHA256']
            record=next(r for r in json.loads(raw)['monthly_sources'] if r['family']=='klines' and r['symbol']==row['symbol'])
            prefix=str(Path(index['index_path']).parent)+'/'
            b=b''.join(self.part(index['commit'],dict(**p,path=prefix+p['path'])) for p in record['parts'])
            check=git('show',index['commit']+':'+prefix+record['checksum_path'])
        else:
            z=self.wrapper(row['wrapper_id']);b=z.read(row['member'])
            if row['CHECKSUM_member']:
                check=z.read(row['CHECKSUM_member'])
            else:
                receipt=z.read(row['source_receipt_member'])
                assert digest(receipt)==row['source_receipt_SHA256']
                record=json.loads(receipt)
                assert record['SHA256']==digest(b)
                check=record['checksum_text'].encode()
        assert len(b)==row['ZIP_bytes'] and digest(b)==row['ZIP_SHA256']
        if row['CHECKSUM_member_SHA256']:
            assert digest(check)==row['CHECKSUM_member_SHA256']
        assert check.decode()==row['official_checksum_text']
        return b,check

    @staticmethod
    def part(commit,row):
        b=git('show',commit+':'+row['path'])
        assert len(b)==row['bytes'] and digest(b)==row['SHA256']
        return b

    def close(self):
        for z in self.wrappers.values():z.close()


def decode(raw,check,stem,state,left,right):
    from modules.collector_research.pipeline.download import parse_checksum,check_zip
    from modules.collector_research.pipeline.normalize import numeric_csv,validate_price
    assert digest(raw)==parse_checksum(check.decode(),stem)
    p=state/stem
    with p.open('xb') as f:f.write(raw)
    try:
        check_zip(p)
        return validate_price(numeric_csv(p),'klines',left,right)
    finally:
        p.unlink()


def decoded_month(reader,row,left,right):
    raw,check=reader.read(row)
    stem=row['official_URL'].split('/')[-1]
    frame,duplicates=decode(raw,check,stem,reader.state,left,right)
    original=len(frame);repairs=[]
    for old in reader.inventory['reusable_price_archives']:
        if old['family']=='klines' and old['frequency']=='daily' and old['symbol']==row['symbol'] and old['month']==row['month']:
            r,c=reader.read(old)
            day=int(old['source_period'][-2:]);l=left+(day-1)*86400000
            previous,d=decode(r,c,old['official_URL'].split('/')[-1],reader.state,l,l+86400000)
            assert len(previous)==1440 and d==0
            common=frame[frame.timestamp_ms.isin(previous.timestamp_ms)].reset_index(drop=True)
            matched=previous[previous.timestamp_ms.isin(common.timestamp_ms)].reset_index(drop=True)
            assert np.array_equal(common.to_numpy(),matched.to_numpy())
            from modules.collector_research.pipeline.normalize import validate_price
            frame,union=validate_price(pd.concat([frame,previous],ignore_index=True),'klines',left,right)
            assert union==len(common)
            repairs.append(dict(source=old,common_rows=len(common),added_actual_rows=1440-len(common),all_common_fields_exact=True))
    grid=np.arange(left,right,60000,dtype=np.int64)
    missing=np.setdiff1d(grid,frame.timestamp_ms.to_numpy())
    if len(missing):
        raise ValueError(json.dumps(dict(symbol=row['symbol'],month=row['month'],missing_minutes=len(missing),
            missing_open_ms=missing.tolist(),no_imputation=True)))
    assert np.array_equal(frame.timestamp_ms.to_numpy(),grid)
    return frame,dict(source=row,original_month_rows=original,observed_minutes=len(frame),
        identical_month_duplicates=duplicates,repairs=repairs,CRC=True,exact_complete_grid=True)


def old_five():
    b=git('show',OLD5+':'+OLD5PATH)
    assert digest(b)==OLD5SHA
    with zipfile.ZipFile(io.BytesIO(b)) as z:
        raw=z.read('prepared/FIVE_MIN_CLOSES.npz')
        with np.load(io.BytesIO(raw),allow_pickle=False) as a:
            assert tuple(a['symbol_order'])==SYMBOLS
            return a['available_us'].copy(),np.column_stack([a[s] for s in SYMBOLS]),digest(raw)


def bind_current(value,commit):
    if isinstance(value,list):return [bind_current(x,commit) for x in value]
    if isinstance(value,dict):
        result={k:bind_current(v,commit) for k,v in value.items()}
        if result.get('kind')=='NEW_PUBLIC_PARTS' and result.get('artifact_commit')=='CURRENT_ARTIFACT':
            result['artifact_commit']=commit
        return result
    return value


def run(phase,state,source,previous=None,previous_commit=None):
    assert git('rev-parse','HEAD').decode().strip()==source and not git('status','--porcelain')
    assert state.resolve().is_relative_to(Path('/workspace')) and not state.exists()
    state.mkdir();configure(state,phase)
    from modules.collector_research.pipeline.download import Job,fetch,session
    from modules.collector_research.pipeline.normalize import month_limits
    from modules.collector_research.pipeline.common import bounds
    bounds()
    invraw=(HERE/'SOURCE_COVERAGE.json').read_bytes();inv=json.loads(invraw)
    oldhash=json.loads((HERE/'HASH_ONLY_PRIOR_RECEIPTS.json').read_bytes())['price_source_receipts']
    save(state/'STARTED.json',dict(phase=phase,source_commit=source,inventory_SHA256=digest(invraw),fits=0,wallets=0))
    start=time.monotonic();newbytes=0;records=[];all_daily=[];all_five=[];all_times=[];boundaries={};downloaded=0
    prior={s:None for s in SYMBOLS}
    if previous is not None:
        prevraw=previous.read_bytes();prev=json.loads(prevraw)
        assert previous_commit and git('show',previous_commit+':'+str(previous.relative_to(ROOT)))==prevraw
        prev=bind_current(prev,previous_commit)
        assert prev['phase']==list(PHASES)[list(PHASES).index(phase)-1]
        prior=prev['end_boundaries']
    else:
        assert phase=='Y2021'
    reader=SourceReader(inv,state,local=True)
    with session() as connection:
        for year,month in PHASES[phase]:
            left,right=month_limits(year,month);daily={};five=[];times=None
            for s in SYMBOLS:
                old=next((r for r in inv['reusable_price_archives'] if r['family']=='klines' and r['frequency']=='monthly'
                          and r['symbol']==s and r['month']==f'{year}-{month:02d}'),None)
                if old is None:
                    assert year==2022 and 1<=month<=9
                    job=Job(s,'klines',year,month)
                    try:
                        received=fetch(job,connection)
                        assert received['status']!='ARCHIVE_UNAVAILABLE_UNCLASSIFIED','Official404 remains unknown'
                    except Exception as exc:
                        save(state/'BLOCKED.json',dict(phase=phase,month=month,symbol=s,error=str(exc),
                            HTTP_status=getattr(getattr(exc,'response',None),'status_code',None),completed_sources=len(records),
                            no_refusal_retry_or_bypass=True,fits=0,wallets=0))
                        raise
                    newbytes+=received['bytes'];downloaded+=int(received['status']=='DOWNLOADED_VERIFIED')
                    assert newbytes<=35000000
                    check=Path(str(job.path)+'.CHECKSUM').read_bytes()
                    old=dict(kind='NEW_OFFICIAL_RAW',wrapper_id='NEW',symbol=s,family='klines',month=f'{year}-{month:02d}',
                        frequency='monthly',ZIP_bytes=received['bytes'],ZIP_SHA256=received['sha256'],
                        CHECKSUM_member_SHA256=digest(check),official_checksum_text=check.decode(),official_URL=job.url,
                        raw_path=str(job.path.relative_to(state)),cache_status=received['status'],
                        verified_UTC=datetime.now(timezone.utc).isoformat())
                    raw=job.path.read_bytes()
                    frame,dups=decode(raw,check,job.stem,state,left,right)
                    # Use the same source union path as cold replay, with cache bytes supplied once.
                    original_read=reader.read
                    reader.read=lambda row: (raw,check) if row is old else original_read(row)
                    try:frame,evidence=decoded_month(reader,old,left,right)
                    finally:reader.read=original_read
                    receipt=next(r for r in oldhash if r['family']=='klines' and r['symbol']==s and r['month']==old['month'])
                    old['prior_HASH_ONLY_receipt_SHA256']=receipt['sha256']
                    old['matches_prior_HASH_ONLY_receipt']=old['ZIP_SHA256']==receipt['sha256'] and old['ZIP_bytes']==receipt['bytes']
                    assert old['matches_prior_HASH_ONLY_receipt'],'Changed old source identity requires review'
                else:
                    frame,evidence=decoded_month(reader,old,left,right)
                past=prior[s]
                if past is not None:
                    assert past['open_ms']==left-60000 and past['available_us']==left*1000
                result,t,close5=measure(frame,None if past is None else past['close'])
                if times is None:times=t
                np.testing.assert_array_equal(times,t)
                for k,v in result.items():daily.setdefault(k,[]).append(v)
                five.append(close5)
                evidence['past_boundary']=past
                end=dict(close=float(frame.close.iloc[-1]),open_ms=right-60000,available_us=right*1000,source=old)
                evidence['end_boundary']=end;prior[s]=end;records.append(evidence)
                print('COMPLETE',phase,s,old['month'],len(frame),'actual minutes',flush=True)
                assert time.monotonic()-start<600 and shutil.disk_usage(state).free>=15*1024**3
                assert sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<=1000000000
            all_daily.append({k:np.column_stack(v) for k,v in daily.items()})
            all_five.append(np.column_stack(five));all_times.append(times)
    reader.close()
    available=np.concatenate(all_times);measured={k:np.concatenate([d[k] for d in all_daily]) for k in all_daily[0]}
    closes=np.concatenate(all_five)
    five_available=np.arange(available[0]-86400000000+300000000,available[-1]+300000000,300000000,dtype=np.int64)
    assert len(five_available)==len(closes) and np.all(np.diff(available)==86400000000)
    np.savez_compressed(state/'DAILY.npz',symbol_order=np.asarray(SYMBOLS),available_us=available,**measured)
    oldref=None
    if phase=='Y2021':
        t,c,sha=old_five();np.testing.assert_array_equal(t,five_available);np.testing.assert_array_equal(c,closes)
        oldref=dict(commit=OLD5,path=OLD5PATH,wrapper_SHA256=OLD5SHA,member='prepared/FIVE_MIN_CLOSES.npz',member_SHA256=sha,
                    all_actual_source_end5min_closes_exact=True)
    else:
        np.savez_compressed(state/'FIVE_MIN.npz',symbol_order=np.asarray(SYMBOLS),available_us=five_available,close=closes)
    valid=np.isfinite(measured['RV_1m']).all(1)
    save(state/'RECOVERY.json',dict(status='PASS_REAL_CONTINUOUS_COMPLETED_DAY_TRADE_PHASE',phase=phase,source_commit=source,
        protocol_SHA256=digest((HERE/'PROTOCOL.json').read_bytes()),source_inventory_SHA256=digest(invraw),
        code_SHA256={p.name:digest(p.read_bytes()) for p in (HERE/'primitives.py',HERE/'prepare.py')},
        calendar_days=len(available),valid_joint_RV_days=int(valid.sum()),actual_minutes=sum(r['observed_minutes'] for r in records),
        sources=records,end_boundaries=prior,previous_proof_SHA256=None if previous is None else digest(previous.read_bytes()),
        new_original_bytes=newbytes,provider_downloaded_ZIPs=downloaded,official_daily_repairs_added=sum(x['added_actual_rows'] for r in records for x in r['repairs']),
        official_daily_common_rows_verified=sum(x['common_rows'] for r in records for x in r['repairs']),
        artifacts={p.name:file_sha(p) for p in state.glob('*.npz')},reused_public_five_min=oldref,
        first_unknown_boundary_preserved=phase=='Y2021',fits=0,wallets=0,labels_created=0,
        elapsed_seconds=time.monotonic()-start,scope='Seen development history; trade is not mark. Conservative day-end clocks, not actual historical arrival certification.'))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--phase',choices=PHASES,required=True)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True)
    p.add_argument('--previous',type=Path);p.add_argument('--previous-commit')
    a=p.parse_args();run(a.phase,a.state,a.source_commit,a.previous,a.previous_commit)
