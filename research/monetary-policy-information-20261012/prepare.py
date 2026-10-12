"""Build one new external-policy benchmark dataset from immutable public Git."""
import argparse,gzip,hashlib,importlib.util,io,json,sys,time,zipfile
from pathlib import Path
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from core import DAY,policy_features
from scripts.research.conditional_selector_inputs import bar_frame,existing_targets,reference_utility
from modules.collector_research.pipeline.economics import interval_arrays,replay
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
spec=importlib.util.spec_from_file_location('original',ROOT/'research/minute-conditional-selector-20261011/experiment.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
EXEC=60_000_001;FIT=m.utc('2023-01-01')

def run(state,source_commit):
    m.require(not state.exists() and not m.git('status','--porcelain'),'Fresh STATE/clean frozen source')
    m.require(m.git('rev-parse','HEAD').decode().strip()==source_commit,'Published preparation source')
    m.verify_manifest(HERE/'SOURCE_SHA256.txt');state.mkdir();started=time.monotonic()
    spec=importlib.util.spec_from_file_location('rawsource',ROOT/'research/short-funding-residual-20261011/experiment.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);raw=mod.source_archive(ROOT,state)
    clocks=np.arange(m.utc('2020-01-02'),m.utc('2024-01-04'),DAY,dtype=np.int64);d=np.arange(m.utc('2021-01-01'),m.utc('2024-01-01'),DAY,dtype=np.int64)
    close=np.full((len(clocks),5),np.nan);frames={};events={};records=[];(state/'daily_features').mkdir()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        m.require(z.testzip() is None,'Source CRC');members=json.loads(z.read('MEMBERS.json'))['files']
        def member(name):
            b=z.read(name);r=members[name];m.require(m.digest(b)==r['SHA256'] and len(b)==r['bytes'],'Original member '+name);return b
        def projected(b):
            dtype=pq.read_schema(io.BytesIO(b)).field('dt').type;tz='UTC' if dtype.tz else None
            return pq.read_table(io.BytesIO(b),filters=[('dt','>=',pa.scalar(pd.Timestamp('2020-01-01',tz=tz).to_pydatetime(),type=dtype)),('dt','<',pa.scalar(pd.Timestamp('2024-01-03',tz=tz).to_pydatetime(),type=dtype))]).to_pandas()
        for j,s in enumerate(SYMBOLS):
            name='source_tables_not_model_inputs/daily_features/'+s+'.parquet';b=member(name);f=projected(b);f['dt']=pd.to_datetime(f.dt,utc=True);f=f.sort_values('dt')
            a=f.dt.to_numpy(dtype='datetime64[us]').astype(np.int64)+DAY;m.require(not f.dt.duplicated().any() and set(f.symbol)=={s},'Exact daily source identity')
            ix=np.searchsorted(clocks,a);m.require(np.array_equal(clocks[ix],a),'Daily source exact clock')
            close[ix,j]=np.where(f.complete_kline.to_numpy(bool),f.close.to_numpy(float),np.nan)
            f.to_parquet(state/'daily_features'/(s+'.parquet'),index=False)
            name='source_tables_not_model_inputs/economics/'+s+'_daily.parquet';b=member(name);e=projected(b);e['dt']=pd.to_datetime(e.dt,utc=True);a=e.dt.to_numpy(dtype='datetime64[us]').astype(np.int64)+DAY
            m.require(not e.dt.duplicated().any() and np.array_equal(a,e.available_us.to_numpy(np.int64)),'Original economics available clock')
            e=e.set_index('available_us').reindex(clocks).reset_index();e['dt']=pd.to_datetime(clocks-DAY,unit='us',utc=True);e['symbol']=s
            for flag in ('complete_kline','complete_mark','funding_interval_complete'):e[flag]=e[flag].fillna(False).astype(bool)
            frames[s]=e
            name='source_tables_not_model_inputs/economics/'+s+'_funding_events.parquet';b=member(name)
            table=pq.read_table(io.BytesIO(b),columns=['calc_time_ms'],filters=[('calc_time_ms','<',m.utc('2024-01-03')//1000)]);ev=np.sort(table.column(0).to_numpy().astype(np.int64)*1000)
            m.require(np.all(np.diff(ev)>0),'Actual unique funding coverage clock');events[s]=ev
            records.append(dict(symbol=s,daily_rows=len(f),economic_rows=int(np.isfinite(e.exec_price).sum()),funding_events=len(ev)))
    bars=bar_frame(state,SYMBOLS);w,_,eligible,asset=existing_targets(dict(recipe='VOL_MANAGED_HOLD',mechanism='VOL'),bars,d,close,clocks,SYMBOLS)
    di=np.searchsorted(clocks,d);x=np.full((len(d),8),np.nan)
    for j,k in enumerate(di):
        past=close[k-63:k+1]
        if past.shape!=(64,5) or not np.isfinite(past).all() or np.any(past<=0):continue
        returns={h:past[-1]/past[-1-h]-1 for h in (1,7,21,63)}
        r=np.diff(past[-31:],axis=0)/past[-31:-1]
        x[j]=[returns[h][0] for h in (1,7,21)]+[returns[h].mean() for h in (1,7,21,63)]+[r.std(0,ddof=1).mean()]
    policy=json.loads((HERE/'source/POLICY_RELEASES.json').read_text());mac,pc=policy_features(d,np.array([r['published_us'] for r in policy],np.int64),np.array([r['target_upper_percent'] for r in policy]),x[:,5])
    known=np.isfinite(x).all(1)&np.isfinite(mac).all(1)&eligible;m.require((pc<=d).all(),'Policy announcement as-of')
    arrays=[interval_arrays(frames[s],di,1.) for s in SYMBOLS];p0,p1,fp,good=[np.stack([a[k] for a in arrays],axis=1) for k in range(4)]
    # Existing quantity proxy plus explicit held full-mark and coverage maturity guard.
    complete=np.ones(len(d),bool);maturity=d+2*DAY;y=np.full(len(d),np.nan);net=y.copy();fees=y.copy();fund=y.copy();labels=[]
    for j,i in enumerate(di):
        own=w[j]!=0;valid=good[j]&np.isfinite(p0[j])&np.isfinite(p1[j])&np.isfinite(fp[j])&(p0[j]>0)&(p1[j]>0)
        valid &= np.array([frames[s].complete_mark.iloc[i+1] for s in SYMBOLS],bool)
        complete[j]=eligible[j] and own.any() and valid[own].all()
        for k in np.flatnonzero(own):
            pos=int(np.searchsorted(events[SYMBOLS[k]],d[j]+DAY+EXEC,side='right'))
            if pos>=len(events[SYMBOLS[k]]):complete[j]=False
            else:maturity[j]=max(maturity[j],int(events[SYMBOLS[k]][pos]))
        if not complete[j]:continue
        metrics,trace=replay(frames,np.array([i]),w[j][None,:],1.,.00135,10000.)
        y[j]=reference_utility(metrics);net[j]=metrics['net'];fees[j]=metrics['fees'];fund[j]=-metrics['funding']
        labels.append(dict(decision_us=int(d[j]),true_reward_maturity_us=int(maturity[j]),utility=y[j],net_USDT=net[j],fees_USDT=fees[j],funding_cash_USDT=fund[j]))
    train=known&complete&(d<FIT)&(maturity<FIT);chosen=np.flatnonzero(train)
    m.require(len(chosen)>=600 and len(np.unique(d[chosen]))==len(chosen),'At least600 actual mature known training dates before any fit')
    ownstart=d[chosen]+EXEC;ownend=ownstart+DAY;m.require(np.all(ownstart[1:]>=ownend[:-1]),'Nonoverlapping owned intervals despite conservative later maturity')
    np.savez_compressed(state/'INPUTS.npz',decision_us=d,close_available_us=clocks,close=close,price_features=x,policy_features=mac,policy_available_us=pc,benchmark_targets=w,known=known,eligible=eligible,asset_eligible=asset,label_complete=complete,true_reward_maturity_us=maturity,utility=y,net_USDT=net,fees_USDT=fees,funding_cash_USDT=fund,p0=p0,p1=p1,funding_per_unit=fp,owned_interval_valid=good,training_indices=chosen)
    pd.DataFrame(labels).to_csv(state/'TEACHER_LABELS.csv',index=False)
    report=dict(status='PASS_PREPARED_ACTUAL600_PLUS_EXTERNAL_POLICY',source_commit=source_commit,actual_training_dates=len(chosen),natural_train_calendar=int((d<FIT).sum()),natural_validation_calendar=int((d>=FIT).sum()),maximum_train_true_reward_maturity_us=int(maturity[chosen].max()),fit_available_us=FIT,original_public_archive_commit=mod.SOURCE_COMMIT,archive_SHA256=mod.ARCHIVE_SHA,symbol_order=list(SYMBOLS),sources=records,official_policy_releases=len(policy),new_model_fits=0,new_wallets=0,policy_vintage='PUBLIC_TIMESTAMPED_ANNOUNCEMENTS_NOT_FINAL_REVISED_EFFR',scope='SEEN_2021_2022_TRAIN_2023_DEV_CONDITIONAL_DAILY_TEACHER',seconds=time.monotonic()-started)
    m.save(state/'PREPARATION.json',report);m.require(report['seconds']<120,'Preparation120sbudget');print(json.dumps(report,indent=2),flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.source_commit)
