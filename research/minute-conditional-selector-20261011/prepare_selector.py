"""Reuse source features/pools/economic frames; new risk features are causal."""
import argparse
from datetime import datetime,timezone
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import time
import zipfile
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
OLD='research/core5-continuous-risk600-20261011/'
sys.path.insert(0,str(ROOT/OLD))
from prepare import SourceReader,digest,git,save,SYMBOLS
from join import assemble
from scripts.research.conditional_selector_inputs import bar_frame,existing_targets

DAY=86400000000
FEATURES=('mom1','mom5','mom20','mom60','mom200','vol30','vol200','dist50','dist200','funding','breadth20','dispersion20','market_vol20')


def utc(s):return int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp())*1000000


def prefix_array(z,name,rows):
    """Read only a C-ordered first-axis prefix, never future feature/outcome rows."""
    with z.open(name+'.npy') as f:
        version=np.lib.format.read_magic(f)
        assert version in ((1,0),(2,0)),'Explicit supported NPY source header required'
        reader=np.lib.format.read_array_header_1_0 if version==(1,0) else np.lib.format.read_array_header_2_0
        shape,fortran,dtype=reader(f)
        assert not fortran and not dtype.hasobject and 0<rows<=shape[0]
        count=rows*int(np.prod(shape[1:]));raw=f.read(count*dtype.itemsize)
        assert len(raw)==count*dtype.itemsize
        return np.frombuffer(raw,dtype=dtype).reshape((rows,*shape[1:])).copy()


def projected_source(raw,name,members,columns,left,right):
    with zipfile.ZipFile(io.BytesIO(raw)) as z:b=z.read(name)
    assert len(b)==members[name]['bytes'] and digest(b)==members[name]['SHA256']
    dtype=pq.read_schema(io.BytesIO(b)).field('dt').type;tz=timezone.utc if dtype.tz else None
    return pq.read_table(io.BytesIO(b),columns=columns,filters=[
        ('dt','>=',pa.scalar(datetime.fromisoformat(left).replace(tzinfo=tz),type=dtype)),
        ('dt','<',pa.scalar(datetime.fromisoformat(right).replace(tzinfo=tz),type=dtype))]).to_pandas()


def run(state,source):
    assert not state.exists() and state.resolve().is_relative_to(Path('/workspace'))
    assert git('rev-parse','HEAD').decode().strip()==source and not git('status','--porcelain')
    for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():
        sha,p=line.split(maxsplit=1);assert digest((ROOT/p).read_bytes())==sha,p
    state.mkdir();began=time.monotonic()
    spec=importlib.util.spec_from_file_location('old_funding_source',ROOT/'research/short-funding-residual-20261011/experiment.py')
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);raw=mod.source_archive(ROOT,state)
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members=json.loads(z.read('MEMBERS.json'))['files']
        name='features/CORE5_PRE_MAY2024.npz';packed=z.read(name)
        assert digest(packed)==members[name]['SHA256']
    with zipfile.ZipFile(io.BytesIO(packed)) as z:
        with np.load(io.BytesIO(packed),allow_pickle=False) as a:
            t=a['completed_day_available_us'];order=tuple(a['symbol_order']);feature_order=tuple(a['feature_order'])
        rows=int(np.searchsorted(t,utc('2022-12-01'),side='right'))
        assert rows and np.all(t[:rows]<=utc('2022-12-01'))
        x=prefix_array(z,'x',rows);observed=prefix_array(z,'feature_observed_mask',rows)
        base=x[:,order.index('BTCUSDT')][:,[feature_order.index(k) for k in FEATURES]].astype(float)
        base_mask=observed[:,order.index('BTCUSDT')][:,[feature_order.index(k) for k in FEATURES]].all(1)
    full,coverage=assemble('306b58c4a52035ac9f374de7c25d40dff22fb658')
    decisions=np.arange(utc('2021-01-02'),utc('2022-12-01'),DAY,dtype=np.int64)
    ix=np.searchsorted(full['available_us'],decisions);assert np.array_equal(full['available_us'][ix],decisions)
    bx=np.searchsorted(t[:rows],decisions);assert np.array_equal(t[bx],decisions)
    baseline=base[bx];ready=base_mask[bx]&np.isfinite(baseline).all(1)
    # Keep real2020 warmup and true original observed gaps. No future rows parsed.
    daily_path=state/'daily_features';daily_path.mkdir();frames={};source_records=[]
    for j,s in enumerate(SYMBOLS):
        name=f'source_tables_not_model_inputs/daily_features/{s}.parquet'
        f=projected_source(raw,name,members,['dt','symbol','complete_kline','open','high','low','close','volume'],'2020-01-01','2021-01-01')
        # Append actual recovered2021/2022 completed trade bars, not stale cachedholes.
        observed_full=pd.DataFrame(dict(dt=pd.to_datetime(full['available_us']-DAY,unit='us',utc=True),symbol=s,complete_kline=True,
            **{k:full[k][:,j] for k in ('open','high','low','close','volume')}))
        combined=pd.concat([f,observed_full],ignore_index=True).sort_values('dt')
        assert not combined.dt.duplicated().any();combined.to_parquet(daily_path/(s+'.parquet'),index=False)
        frames[s]=combined
        source_records.append(dict(symbol=s,warmup_member_SHA256=members[name]['SHA256'],warmup_rows=len(f),actual_source_rows=len(observed_full)))
    bars=bar_frame(state,SYMBOLS)
    available=np.arange(utc('2020-01-02'),utc('2022-12-02'),DAY,dtype=np.int64);close=np.full((len(available),5),np.nan)
    for j,s in enumerate(SYMBOLS):
        f=frames[s];cl=f.dt.to_numpy().astype('datetime64[us]').astype(np.int64)+DAY
        ci=np.searchsorted(available,cl);known=f.complete_kline.to_numpy(bool)
        close[ci,j]=np.where(known,f.close.to_numpy(float),np.nan)
    cube=[];eligibility=[];assets=[]
    for recipe,mechanism in [('CASH','CASH'),('VOL_MANAGED_HOLD','VOL'),('CSMOM21','CS')]:
        weights,_,eligible,asset=existing_targets(dict(recipe=recipe,mechanism=mechanism),bars,decisions,close,available,SYMBOLS)
        cube.append(weights);eligibility.append(eligible);assets.append(asset)
    targets=np.stack(cube,axis=1);eligible=np.stack(eligibility,axis=1);asset=np.stack(assets,axis=1)
    assert np.abs(targets).max()<=.3+1e-12 and np.abs(targets).sum(2).max()<=.6+1e-12
    # Native historical November source is the exact independent producer check.
    inv=json.loads(git('show','306b58c4a52035ac9f374de7c25d40dff22fb658:'+OLD+'SOURCE_COVERAGE.json'))
    reader=SourceReader(inv,state,local=False);z=reader.wrapper('BEAR2022NOV')
    saved=z.read('bear_recovery_data/inputs/BEAR2022NOV_INPUTS.npz')
    assert digest(saved)=='c00557727efe5213621958f5bd59cb62268c5f98f9117ea1f4a35f18a9d0ae45'
    with np.load(io.BytesIO(saved),allow_pickle=False) as a:
        saved_keys=list(a.files);saved_shapes={k:list(a[k].shape) for k in a.files}
        # Keys are checked by the original producer metadata before choosing a projection.
        print('BEAR_CONTEXT_SCHEMA',json.dumps(saved_shapes),flush=True)
    reader.close()
    np.savez_compressed(state/'SOURCE_PREPARED.npz',symbol_order=np.asarray(SYMBOLS),decision_us=decisions,baseline=baseline,baseline_ready=ready,
        targets=targets,expert_eligible=eligible,asset_eligible=asset,**{k:full[k][ix] for k in ('RV_1m','RV_5m','RSplus_1m','RSminus_1m')})
    save(state/'PREPARATION.json',dict(status='SOURCE_PREPARED_PARITY_PENDING_SCHEMA',source_commit=source,source_records=source_records,
        original_market13_features=list(FEATURES),no_2023_24_feature_or_outcome_values_parsed=True,prefix_rows_read=rows,
        prepared_dates=len(decisions),old_2020_warmup_retained=True,core_price_source=coverage['source_chain_commit'],
        actual_pool_schema=saved_shapes,market13_and_pool_parity='PENDING_SCHEMA_CHECK_BEFORE_FIT',
        scientific_fits=0,labels_created=0,wallets=0,provider_downloads=0,elapsed_seconds=time.monotonic()-began))
    assert time.monotonic()-began<600 and shutil.disk_usage(state).free>=16106127360
    print((state/'PREPARATION.json').read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True)
    a=p.parse_args();run(a.state,a.source_commit)
