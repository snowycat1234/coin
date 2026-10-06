"""One explicitly released archive range; reuse original parsing and causal features.

This adapter never calls or modifies the original collector's locked bounds guard.
It has its own mandatory committed-evidence gate. No labels are built for fitting.
"""
import argparse,concurrent.futures,json,os,sys,threading,time
from pathlib import Path
import numpy as np
import pandas as pd
from .train import atomic,sha
from .locked_gate import require_release

START=pd.Timestamp('2026-03-01',tz='UTC');END=pd.Timestamp('2026-09-01',tz='UTC')
FAMILIES=('klines','markPriceKlines','premiumIndexKlines','fundingRate')

def actual_funding_coverage(events,start=START,end=END):
    """Check actual charge calendar, not the future-label execution proxy interval."""
    if events.empty:return False
    times=events.calc_time_ms.to_numpy(np.int64)*1000;hours=events.funding_interval_hours.to_numpy(float)
    left=start.value//1000;right=end.value//1000
    before=int(np.searchsorted(times,left,side='right')-1);last=int(np.searchsorted(times,right,side='left')-1)
    if before<0 or last<before:return False
    gaps=np.diff(times[before:last+1]);nominal=hours[before:last+1]*3_600_000_000
    good=(np.abs(gaps-nominal[:-1])<=1_000_000)|(np.abs(gaps-nominal[1:])<=1_000_000)
    return bool(good.all() and right-times[last]<=nominal[-1]+1_000_000)

def collect_and_normalize(state,collector_root,development_work,source_run,workers=16):
    state,root,old=Path(state),Path(collector_root),Path(development_work)
    repo=Path(__file__).resolve().parents[2];protocol_path=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json'
    protocol=json.loads(protocol_path.read_text());release=require_release(state,sha(protocol_path))
    result_path=state/'LOCKED_DATA_MANIFEST.json'
    if result_path.exists():
        saved=json.loads(result_path.read_text());assert saved['protocol_sha256']==sha(protocol_path)
        for entry in saved['artifacts']:assert sha(entry['path'])==entry['sha256']
        return saved
    work=state/'locked-work';work.mkdir(exist_ok=True)
    binding=json.loads(Path(source_run,'BINDING.json').read_text());os.environ.update(binding['config'])
    os.environ.update(CONFIG_FILE=str(root/'config.env'),WORK_DIR=str(work),RAW_CACHE_DIR=str(work/'data/raw'),
                      MIN_FREE_GIB='15',MAX_WORK_GIB='150',HTTP_RETRIES='1',REFRESH_CHECKSUMS='0')
    sys.path.insert(0,str(root))
    from pipeline import common,download,normalize as norm
    from pipeline.storage import write_table
    assert common.WORK==work.resolve(),'Locked adapter requires a fresh isolated process'
    common.init_dirs();symbols=protocol['data']['symbols'];jobs=[download.Job(s,f,2026,m) for s in symbols for m in range(3,9) for f in FAMILIES]
    reservations=download.DownloadReservations();local=threading.local();sessions=[];session_lock=threading.Lock()
    def fetch(job):
        reservations.acquire()
        try:
            if not hasattr(local,'session'):
                local.session=download.session()
                with session_lock:sessions.append(local.session)
            # Adopt a verified existing archive through links, without altering old evidence.
            prior=old/'data/raw'/job.family/job.symbol/job.stem
            if prior.exists() and not job.path.exists():
                download.verify_local(prior);job.path.parent.mkdir(parents=True,exist_ok=True)
                job.path.symlink_to(prior);Path(str(job.path)+'.CHECKSUM').symlink_to(Path(str(prior)+'.CHECKSUM'))
            return download.fetch(job,local.session,reserved=True)
        finally:reservations.release()
    records=[]
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
            futures={pool.submit(fetch,j):j for j in jobs}
            for future in concurrent.futures.as_completed(futures):
                records.append(future.result())
                atomic(state/'locked-data-progress.json',dict(stage='LOCKED_ARCHIVE_CHECKSUM_DOWNLOAD',current=len(records),total=len(jobs),pid=os.getpid(),updated_at=time.time()))
                atomic(state/'LOCKED_DOWNLOAD_MANIFEST.json',dict(archives=records,protocol_sha256=sha(protocol_path)))
    finally:
        for session in sessions:session.close()
    artifacts=[];audits=[];days=pd.date_range(START,END-pd.Timedelta(days=1),freq='D');base=work/'data/normalized'
    def record(path,role):artifacts.append(dict(path=str(path),sha256=sha(path),role=role,bytes=path.stat().st_size))
    for sid,symbol in enumerate(symbols):
        aggregates={f:[] for f in FAMILIES if f!='fundingRate'};funding_parts=[]
        previous_marks=pd.read_parquet(old/'data/normalized/minute'/symbol/'markPriceKlines/2026-02.parquet').tail(2)
        old_events=pd.read_parquet(old/'data/normalized'/f'{symbol}_funding_events.parquet')
        for month in range(3,9):
            current={}
            for family in FAMILIES:
                job=download.Job(symbol,family,2026,month);left,right=norm.month_limits(2026,month)
                if not job.path.exists():current[family]=pd.DataFrame();continue
                proof=download.verify_local(job.path);frame=norm.numeric_csv(job.path,family=='fundingRate')
                frame,duplicates=norm.validate_funding(frame,left,right) if family=='fundingRate' else norm.validate_price(frame,family,left,right)
                frame=norm.canonical(frame,family,symbol);current[family]=frame
                path=write_table(frame,base/'minute'/symbol/family/f'2026-{month:02d}');record(path,family+'_minute')
                atomic(path.with_suffix('.receipt.json'),dict(source=proof,output_sha256=sha(path),duplicates=duplicates,locked_authorization=release['candidate_freeze_sha256']))
                if family!='fundingRate':aggregates[family].append(norm.aggregate_price(frame,family))
            marks=pd.concat([previous_marks,current.get('markPriceKlines',pd.DataFrame())],ignore_index=True).sort_values('available_us')
            events=current.get('fundingRate',pd.DataFrame())
            if not events.empty:funding_parts.append(norm.mark_funding(events,marks))
            previous_marks=marks.tail(2)
            atomic(state/'locked-data-progress.json',dict(stage='LOCKED_NORMALIZE',current=sid*6+month-2,total=60,symbol=symbol,month=month,pid=os.getpid(),updated_at=time.time()))
        daily=pd.DataFrame(index=days)
        for family in ('klines','markPriceKlines','premiumIndexKlines'):
            q=pd.concat(aggregates[family]).sort_index().reindex(days) if aggregates[family] else pd.DataFrame(index=days)
            flag=dict(klines='complete_kline',markPriceKlines='complete_mark',premiumIndexKlines='complete_premium')[family]
            daily[flag]=q.get('complete',pd.Series(False,index=days)).fillna(False).astype(bool)
            if family=='klines':
                for col in ('open','high','low','close','volume','quote_volume','trades','rows','unique_minutes','exec_price'):daily[col]=q.get(col,pd.Series(np.nan,index=days))
            else:daily['mark' if family=='markPriceKlines' else 'premium']=q.get('close',pd.Series(np.nan,index=days))
        locked_events=pd.concat(funding_parts,ignore_index=True) if funding_parts else old_events.iloc[:0].copy()
        events,_=norm.deduplicate(pd.concat([old_events,locked_events],ignore_index=True),'calc_time_ms')
        daily=daily.join(norm.funding_windows(events,days));daily['source_state']=np.where(daily.complete_kline,'OBSERVED_COMPLETE','MISSING_OR_INCOMPLETE_UNCLASSIFIED')
        daily['symbol']=symbol;daily['open_us']=days.as_unit('us').asi8;daily['close_us']=daily.open_us+86_400_000_000;daily['available_us']=daily.close_us;daily.index.name='dt'
        prior_daily=pd.read_parquet(old/'data/normalized'/f'{symbol}_daily.parquet')
        context=pd.concat([prior_daily,daily.reset_index()],ignore_index=True)
        assert pd.DatetimeIndex(context.dt).is_unique and pd.DatetimeIndex(context.dt).is_monotonic_increasing
        path=write_table(context,base/f'{symbol}_daily');record(path,'causal_daily_context')
        path=write_table(events,base/f'{symbol}_funding_events');record(path,'funding_events')
        complete=daily[['complete_kline','complete_mark','complete_premium','complete_funding']].all(axis=1)
        funding_ok=actual_funding_coverage(events)
        audits.append(dict(symbol=symbol,complete_days=int(complete.sum()),required_days=184,incomplete_dates=[str(d.date()) for d in daily.index[~complete]],actual_funding_calendar_complete=funding_ok))
    full=all(r['complete_days']==184 and r['actual_funding_calendar_complete'] for r in audits)
    result=dict(status='COMPLETE184DAY_ACTUAL_INPUTS' if full else 'NOT_EVALUABLE_INCOMPLETE_LOCKED_CALENDAR',work=str(work),
                protocol_sha256=sha(protocol_path),adapter_source_sha256=sha(__file__),authorization_sha256=sha(state/'LOCKED_READ_AUTHORIZATION.json'),
                archive_manifest_sha256=sha(state/'LOCKED_DOWNLOAD_MANIFEST.json'),artifacts=artifacts,audit=audits,
                range=['2026-03-01','2026-08-31'],days=184,labels_for_training_built=False,
                boundary_rule='Actual funding charge clock through Sep1 exclusive checked against reported interval; future-label execution flag is not an actual-account completeness flag. No September archive read.')
    atomic(result_path,result);return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True)
    p.add_argument('--source-run',required=True);p.add_argument('--workers',type=int,default=16);a=p.parse_args()
    print(json.dumps(collect_and_normalize(a.state,a.collector_root,a.work,a.source_run,a.workers),indent=2))

if __name__=='__main__':main()
