"""Fixed-year source-only recovery, using existing official transport and normalizer."""
import argparse,calendar,hashlib,io,json,os,subprocess,sys,time,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT');DAY=86400000000
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def digest(raw):return hashlib.sha256(raw).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,allow_nan=False)+'\n')
def proto():return json.loads((HERE/'PROTOCOL.json').read_text())
def configure(state):
    os.environ.update(WORK_DIR=str(state/'work'),RAW_CACHE_DIR=str(state/'raw'),SYMBOLS=','.join(SYMBOLS),WARMUP_START='2023-01-01',START_DATE='2023-01-01',END_DATE='2023-12-31',FAMILIES='klines,markPriceKlines,fundingRate',HTTP_RETRIES='0',HTTP_CONNECT_TIMEOUT='10',HTTP_READ_TIMEOUT='20',MAX_ARCHIVE_MIB='8',MAX_UNCOMPRESSED_MIB='64',MAX_WORK_GIB='16',MIN_FREE_GIB='15',REFRESH_CHECKSUMS='0')
def verify():
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert sha(ROOT/p)==s,p
def checked_frame(p,family,stamp):
    from modules.collector_research.pipeline.download import check_zip,parse_checksum
    from modules.collector_research.pipeline.normalize import numeric_csv,validate_price,month_limits
    check=Path(str(p)+'.CHECKSUM').read_bytes();assert sha(p)==parse_checksum(check.decode(),p.name);check_zip(p)
    y,m=map(int,stamp[:7].split('-'));left,right=month_limits(y,m)
    if len(stamp)==10:left+=(int(stamp[-2:])-1)*86400000;right=left+86400000
    return validate_price(numeric_csv(p),family,left,right)[0]
def union_exact(month,daily,family,left,right):
    from modules.collector_research.pipeline.normalize import validate_price
    common=month[month.timestamp_ms.isin(daily.timestamp_ms)].reset_index(drop=True);other=daily[daily.timestamp_ms.isin(common.timestamp_ms)].reset_index(drop=True)
    if not np.array_equal(common.to_numpy(),other.to_numpy()):raise ValueError('Conflicting official monthly/daily numeric overlap')
    merged,dups=validate_price(pd.concat([month,daily],ignore_index=True),family,left,right);assert dups==len(common)
    return merged,dict(common_rows=len(common),added_actual_rows=len(daily)-len(common),all_common_numeric_fields_exact=True)
def acquire(state,phase,source,destination):
    assert phase in ('Q1','Q2') and not state.exists() and not destination.exists() and not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==source
    verify();configure(state)
    from modules.collector_research.pipeline.download import Job,fetch,session
    from modules.collector_research.pipeline.normalize import month_limits
    state.mkdir();started=time.monotonic();connection=session();rows=[];newbytes=0;daily_count=0;P=proto()
    previous_bytes=0;previous_daily=0
    if phase=='Q2':
        prev=json.loads((HERE/'source-phases/Q1/SOURCE_INDEX.json').read_text());previous_bytes=prev['original_bytes'];previous_daily=prev['daily_archives']
    def bounded():
        import shutil
        assert time.monotonic()-started<P['budget']['source_phase_seconds'] and shutil.disk_usage(state).free>=P['budget']['reserve_bytes']
        assert newbytes+8*2**20<=P['source']['new_original_bytes_phase_max'] and previous_bytes+newbytes+8*2**20<=P['source']['new_original_bytes_max']
    def get(s,family,stamp):
        nonlocal newbytes,daily_count
        y,m=map(int,stamp[:7].split('-'));day=int(stamp[-2:]) if len(stamp)==10 else None
        if day is not None:daily_count+=1;assert daily_count+previous_daily<=P['source']['new_daily_archives_max']
        bounded();job=Job(s,family,y,m,day);r=fetch(job,connection)
        if r['status']=='ARCHIVE_UNAVAILABLE_UNCLASSIFIED':raise ValueError('Official404 remainsUNKNOWN: '+job.url)
        newbytes+=r['bytes'];check=Path(str(job.path)+'.CHECKSUM').read_bytes();frame=checked_frame(job.path,family,stamp);bounded()
        row=dict(symbol=s,family=family,month=stamp[:7],source_period=stamp,frequency='daily' if day else 'monthly',official_URL=job.url,ZIP_SHA256=r['sha256'],ZIP_bytes=r['bytes'],CHECKSUM_SHA256=digest(check),official_checksum_text=check.decode(),raw_path=str(job.path.relative_to(state)),transport_status=r['status'],CRC=True,numeric_rows=len(frame))
        rows.append(row);save(state/'PROGRESS.json',dict(phase=phase,verified_archives=len(rows),original_bytes=newbytes,daily_archives=daily_count,latest=row,seconds=time.monotonic()-started));print('ACTUAL_2023_SOURCE_ARCHIVE',phase,len(rows),s,family,stamp,len(frame),newbytes,flush=True)
        return frame,row
    records=[]
    try:
        for m in range(1 if phase=='Q1' else 4,4 if phase=='Q1' else 7):
            stamp=f'2023-{m:02d}';left,right=month_limits(2023,m)
            for s in SYMBOLS:
                for family in ('klines','markPriceKlines'):
                    frame,row=get(s,family,stamp);grid=np.arange(left,right,60000,dtype=np.int64);missing=np.setdiff1d(grid,frame.timestamp_ms.to_numpy());repairs=[]
                    if len(missing):
                        days=sorted({pd.Timestamp(int(t),unit='ms',tz='UTC').strftime('%Y-%m-%d') for t in missing});save(state/f'GAPS-{s}-{family}-{stamp}.json',dict(missing_open_ms=missing.tolist(),missing_days=days,no_imputation=True))
                        for day in days:
                            d,dr=get(s,family,day);assert len(d)==1440;frame,e=union_exact(frame,d,family,left,right);repairs.append(dict(source=dr,**e))
                    np.testing.assert_array_equal(frame.timestamp_ms.to_numpy(),grid);records.append(dict(source=row,repairs=repairs,exact_complete_grid=True,actual_minutes=len(frame)))
        bounded();destination.mkdir(parents=True);parts=[]
        for i,row in enumerate(rows):
            raw=(state/row['raw_path']).read_bytes();sub=destination/f'archive-{i:03d}';sub.mkdir();rp=[]
            for j,off in enumerate(range(0,len(raw),786432)):
                name=f'original.zip.part{j:04d}';p=sub/name;b=raw[off:off+786432];p.write_bytes(b);part=dict(path=str(p.relative_to(ROOT)),bytes=len(b),SHA256=digest(b));rp.append(part);parts.append(part)
            cp=sub/'original.CHECKSUM';cp.write_bytes(Path(str(state/row['raw_path'])+'.CHECKSUM').read_bytes());row['parts']=rp;row['checksum_path']=str(cp.relative_to(ROOT))
        report=dict(status='PASS_EXACT_OFFICIAL_2023_SOURCE_QUARTER',phase=phase,source_commit=source,original_bytes=newbytes,monthly_archives=30,daily_archives=daily_count,records=records,all_archives=rows,parts=parts,provider_downloads=sum(r['transport_status']=='DOWNLOADED_VERIFIED' for r in rows),seconds=time.monotonic()-started,new_wallets=0,new_fits=0)
        save(destination/'SOURCE_INDEX.json',report);save(state/'SOURCE_INDEX.json',report);print('ACTUAL_2023_SOURCE_QUARTER_PASS',phase,newbytes,time.monotonic()-started,flush=True)
    except Exception as exc:
        response=getattr(exc,'response',None);save(state/'FAILED.json',dict(status='STOP_SOURCE_PHASE',phase=phase,error=str(exc),HTTP_status=getattr(response,'status_code',None),verified_archives=len(rows),original_bytes=newbytes,provider_denial_stops=True,seconds=time.monotonic()-started,new_wallets=0,new_fits=0));raise
    finally:connection.close()
def new_source(state,quarter,expected=None):
    assert not state.exists();state.mkdir();index=json.loads(git('show',quarter+':'+str((HERE/'source-phases').relative_to(ROOT))+'/'+expected+'/SOURCE_INDEX.json'));assert index['status']=='PASS_EXACT_OFFICIAL_2023_SOURCE_QUARTER'
    for row in index['all_archives']:
        pieces=[]
        for p in row['parts']:
            b=git('show',quarter+':'+p['path']);assert len(b)==p['bytes'] and digest(b)==p['SHA256'];pieces.append(b)
        raw=b''.join(pieces)
        assert len(raw)==row['ZIP_bytes'] and digest(raw)==row['ZIP_SHA256'];check=git('show',quarter+':'+row['checksum_path']);assert digest(check)==row['CHECKSUM_SHA256']
        p=state/row['raw_path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);Path(str(p)+'.CHECKSUM').write_bytes(check);frame=checked_frame(p,row['family'],row['source_period']);assert len(frame)==row['numeric_rows']
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_EXACT_PUBLIC_OFFICIAL_2023_QUARTER_SOURCE',artifact_commit=quarter,phase=expected,all_original_checksums_CRC_numeric_rows=True,new_provider_downloads=0,new_wallets=0,new_fits=0))
    return index
def h2_wrapper(state,fold):
    P=proto();base=P['source']['reused_H2_base']+fold+'/';commit=P['source']['reused_H2_commit'];index=json.loads(git('show',commit+':'+base+'INDEX.json'));p=state/(fold+'.zip')
    with p.open('xb') as f:
        for part in index['parts']:
            raw=git('show',commit+':'+base+part['name']);assert len(raw)==part['bytes'] and digest(raw)==part['SHA256'];f.write(raw)
    assert p.stat().st_size==index['package_bytes'] and sha(p)==index['package_SHA256'];z=zipfile.ZipFile(p);assert z.testzip() is None;return z,{r['name']:r for r in index['members']},dict(commit=commit,index_SHA256=digest(git('show',commit+':'+base+'INDEX.json')),package_SHA256=index['package_SHA256'])
def build(state,source,q1,q2,expected=None):
    assert not state.exists() and not git('status','--porcelain');verify();configure(state);state.mkdir();(state/'months').mkdir();started=time.monotonic();P=proto()
    if not expected:assert git('rev-parse','HEAD').decode().strip()==source
    sys.path.insert(0,str(ROOT/'research/cs-continuous-economics-20261012'));from source_prepare import native
    start,end=map(native.utc,P['calendar']);d=np.arange(start,end,DAY);assert len(d)==365
    assert sha(ROOT/P['daily_cube'])==P['daily_cube_SHA256']
    with np.load(ROOT/P['daily_cube'],allow_pickle=False) as a:clocks=a['close_available_us'];prices=a['close']
    indices={};cert=[]
    for phase,commit in [('Q1',q1),('Q2',q2)]:indices[phase]=new_source(state/phase,commit,phase);cert.append(dict(phase=phase,commit=commit,index_SHA256=digest(git('show',commit+':'+str((HERE/'source-phases').relative_to(ROOT))+'/'+phase+'/SOURCE_INDEX.json'))))
    wrappers={};members={}
    for fold in P['source']['reused_H2_folds']:wrappers[fold],members[fold],c=h2_wrapper(state,fold);cert.append(dict(fold=fold,**c))
    daily=[];records=[];previous={}
    from modules.collector_research.pipeline.normalize import month_limits
    for m in range(1,13):
        stamp=f'2023-{m:02d}';left,right=month_limits(2023,m);times=np.arange(left*1000,right*1000,60000000,dtype=np.int64);arrays=dict(times=times);sources=[]
        for asset,s in enumerate(SYMBOLS):
            for family in ('klines','markPriceKlines'):
                if m<=6:
                    phase='Q1' if m<=3 else 'Q2';rec=next(r for r in indices[phase]['records'] if r['source']['symbol']==s and r['source']['family']==family and r['source']['month']==stamp);row=rec['source'];f=checked_frame(state/phase/row['raw_path'],family,stamp)
                    for repair in rec['repairs']:dr=repair['source'];df=checked_frame(state/phase/dr['raw_path'],family,dr['source_period']);f,e=union_exact(f,df,family,left,right);assert e=={k:v for k,v in repair.items() if k!='source'}
                    descriptor=dict(source=row,repairs=rec['repairs'],artifact_commit=q1 if phase=='Q1' else q2)
                else:
                    fold='JULY2023' if m<=9 else 'OCTOBER2023';name=f'raw/{family}/{s}/{s}-1m-{stamp}.zip';raw=wrappers[fold].read(name);check=wrappers[fold].read(name+'.CHECKSUM')
                    for n,b in [(name,raw),(name+'.CHECKSUM',check)]:assert len(b)==members[fold][n]['bytes'] and digest(b)==members[fold][n]['SHA256']
                    p=state/f'{s}-1m-{stamp}.zip';p.write_bytes(raw);Path(str(p)+'.CHECKSUM').write_bytes(check)
                    f=checked_frame(p,family,stamp);p.unlink();Path(str(p)+'.CHECKSUM').unlink();descriptor=dict(source_commit=P['source']['reused_H2_commit'],member=name,ZIP_SHA256=digest(raw),ZIP_bytes=len(raw),CHECKSUM_SHA256=digest(check),official_URL=f'https://data.binance.vision/data/futures/um/monthly/{family}/{s}/1m/{s}-1m-{stamp}.zip')
                np.testing.assert_array_equal(f.timestamp_ms.to_numpy()*1000,times)
                prior=previous.get((s,family));last=float(f.close.iloc[-1]);sources.append(dict(symbol=s,family=family,source=descriptor,actual_minutes=len(f),prior_completed_close=prior,end_completed_close=last,exact_grid=True));previous[s,family]=last
                if family=='klines':
                    arrays[s+'_open']=f.open.to_numpy();arrays[s+'_close']=f.close.to_numpy();arrays[s+'_quote_volume']=f.quote_volume.to_numpy()
                    for i,at in enumerate(range(left*1000,right*1000,DAY)):
                        k=int(np.searchsorted(clocks,at));assert clocks[k]==at
                        before=prices[k,asset] if at==start else (prior if i==0 else float(f.close.iloc[i*1440-1]));assert abs(before-prices[k,asset])<=1e-12*abs(before),'Pastdailycube vsactualpriorclose'
                        daily.append(dict(symbol=s,close_us=at,close=float(before)))
                        k2=int(np.searchsorted(clocks,at+DAY));assert clocks[k2]==at+DAY;actual=float(f.close.iloc[(i+1)*1440-1]);assert abs(actual-prices[k2,asset])<=1e-12*abs(actual),'Completedfull2023dailycloseparity'
                else:arrays[s+'_mark']=f.close.to_numpy()
        p=state/'months'/(stamp+'.npz');np.savez_compressed(p,**arrays);records.append(dict(month=stamp,minutes=len(times),source_NPZ_SHA256=sha(p),source_NPZ_bytes=p.stat().st_size,sources=sources));del arrays;print('ACTUAL_2023_SOURCE_MONTH_VERIFIED',m,12,flush=True)
    for z in wrappers.values():z.close()
    events,fund=native.fund_events(state,start,end)
    for s in SYMBOLS:
        e=[r for r in events if r['symbol']==s];ts=np.array([r['event_us'] for r in e],np.int64);assert len(e)==365*3 and np.all(np.abs(np.diff(ts)-8*3600000000)<=1000000),'FullactualCORE5fundingcoverage'
    save(state/'EVENTS.json',events);save(state/'DAILY.json',daily)
    report=dict(status='PASS_EXACT_FULL_2023_TRADE_MARK_FUND_SOURCE',source_commit=source,quarter_artifacts=dict(Q1=q1,Q2=q2),calendar=[start,end],days=365,minutes_per_asset=365*1440,symbol_order=list(SYMBOLS),months=records,source_certificates=cert,funding=fund,funding_events=len(events),daily_price_parity=True,provider_downloads=0,new_wallets=0,new_fits=0,initial_mark_boundary='UNOWNED_FRESHFLAT_PRIORUNKNOWN_NO_FABRICATED2022MINUTE',authority='CONDITIONAL_UNCHANGED_FUNDUNIT_CHARGE_MARK_MMR_ARRIVAL')
    report['files']={name:dict(SHA256=sha(state/name),bytes=(state/name).stat().st_size) for name in ('EVENTS.json','DAILY.json')};save(state/'SOURCE_INDEX.json',report);save(state/'TIMING.json',dict(seconds=time.monotonic()-started));assert time.monotonic()-started<P['budget']['source_prepare_seconds']
    if expected:assert report==json.loads(git('show',expected+':'+str(HERE.relative_to(ROOT))+'/source-result/SOURCE_INDEX.json'));save(state/'PUBLIC_SOURCE_RESTORE.json',dict(status='PASS_EXACT_FULL2023_PUBLIC_SOURCE',artifact_commit=expected,provider_downloads=0,new_wallets=0,new_fits=0))
    print('ACTUAL_2023_COMPLETE_SOURCE_READY',365,365*1440,len(events),time.monotonic()-started,flush=True)
def funding_check(state):
    assert not state.exists();state.mkdir();configure(state);verify();started=time.monotonic()
    sys.path.insert(0,str(ROOT/'research/cs-continuous-economics-20261012'));from source_prepare import native
    start,end=map(native.utc,proto()['calendar']);events,proof=native.fund_events(state,start,end);coverage=[]
    for s in SYMBOLS:
        e=[r for r in events if r['symbol']==s];ts=np.array([r['event_us'] for r in e],np.int64);good=len(e)==365*3 and bool(np.all(np.abs(np.diff(ts)-8*3600000000)<=1000000))
        coverage.append(dict(symbol=s,events=len(e),first_event_us=int(ts[0]) if len(ts) else None,last_event_us=int(ts[-1]) if len(ts) else None,complete_three_actual_events_per_day=good))
    report=dict(status='PASS_FULL2023_ACTUAL_FUNDING' if all(r['complete_three_actual_events_per_day'] for r in coverage) else 'STOP_FULL2023_FUNDING_GAP',coverage=coverage,source=proof,new_wallets=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-started);save(state/'FUNDING_CHECK.json',report);print(json.dumps(report,indent=2),flush=True);assert report['status']=='PASS_FULL2023_ACTUAL_FUNDING'
if __name__=='__main__':
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='command',required=True)
    a=s.add_parser('acquire');a.add_argument('--state',type=Path,required=True);a.add_argument('--phase',choices=['Q1','Q2'],required=True);a.add_argument('--source-commit',required=True);a.add_argument('--destination',type=Path,required=True)
    a=s.add_parser('restore-quarter');a.add_argument('--state',type=Path,required=True);a.add_argument('--artifact-commit',required=True);a.add_argument('--phase',choices=['Q1','Q2'],required=True)
    a=s.add_parser('build');a.add_argument('--state',type=Path,required=True);a.add_argument('--source-commit',required=True);a.add_argument('--q1-commit',required=True);a.add_argument('--q2-commit',required=True);a.add_argument('--expected-commit')
    a=s.add_parser('funding-check');a.add_argument('--state',type=Path,required=True)
    a=p.parse_args()
    if a.command=='acquire':acquire(a.state,a.phase,a.source_commit,a.destination)
    elif a.command=='restore-quarter':configure(a.state);new_source(a.state,a.artifact_commit,a.phase);print('PUBLIC_2023_QUARTER_ZERO_DOWNLOAD_RESTORED',a.phase,flush=True)
    elif a.command=='funding-check':funding_check(a.state)
    else:build(a.state,a.source_commit,a.q1_commit,a.q2_commit,a.expected_commit)
