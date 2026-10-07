"""Fill fixed source holes from official daily archives; no fitting or wallets.

Reuse the existing downloader, parser, normalizer and reference-utility kernel.
Original manifest/data/results remain immutable. No interpolation or clock change.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

import numpy as np
import pandas as pd
import polars as pl

from modules.collector_research.pipeline.download import Job, fetch, session
from modules.collector_research.pipeline.normalize import (numeric_csv, validate_price,
    canonical, aggregate_price, mark_funding, funding_windows)
from modules.collector_research.pipeline.make_labels import feature_frame
from modules.collector_research.pipeline.economics import interval_arrays
from scripts.research.joint_expert_information import (FEATURES, signed_intents,
    reference_labels, feedback_panel, reference_available_at, train_mask)

DAY_US=86400000000
WORK=Path('/home/ubuntu/coin/coin_collector_v3_fixed/work')
PRIOR=Path('/home/ubuntu/coin/execution-state/joint-information-20261008-v1')


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')


def merge_observed(old,new):
    """Only add missing timestamps. Conflicts never replace frozen observations."""
    if set(old.columns)!=set(new.columns):raise ValueError('Canonical columns differ')
    new=new[old.columns].drop_duplicates()
    if old.timestamp_ms.duplicated().any() or new.timestamp_ms.duplicated().any():
        raise ValueError('Duplicate timestamps in source')
    a=old.set_index('timestamp_ms');b=new.set_index('timestamp_ms');both=a.index.intersection(b.index)
    same=a.loc[both].eq(b.loc[both]) | (a.loc[both].isna() & b.loc[both].isna())
    if not same.all().all():
        # No tolerance or choice of a more favourable archive on conflicts.
        raise ValueError('Official daily/monthly overlap differs; preserve and investigate')
    return pd.concat([old,new[~new.timestamp_ms.isin(old.timestamp_ms)]],ignore_index=True).sort_values('timestamp_ms').reset_index(drop=True)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--protocol',type=Path,required=True);ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    began=time.monotonic();p=json.loads(a.protocol.read_text());state=a.state.resolve()
    assert os.uname().sysname=='Linux' and state.parent==Path('/home/ubuntu/coin/execution-state')
    assert os.environ['WORK_DIR']==str(state) and os.environ['RAW_CACHE_DIR']==str(state/'raw')
    assert not state.exists(),'Never replace a started or frozen source view'
    assert len(p['entries'])==26 and p['new_fits']==p['new_wallets']==0
    assert shutil.disk_usage(state.parent).free>=p['budget']['reserve_bytes']
    group=Path('/sys/fs/cgroup'+Path('/proc/self/cgroup').read_text().split('::',1)[1].strip())
    assert (group/'memory.max').read_text().strip()!='max' and int((group/'memory.max').read_text())<=8000000000 and (group/'memory.swap.max').read_text().strip()=='0'
    source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    assert sha(__file__)==hashlib.sha256(subprocess.check_output(['git','show','HEAD:scripts/research/repair_bear_support.py'])).hexdigest()
    for path,digest in p['source_hashes'].items():assert sha(path)==digest
    old=json.loads((PRIOR/'RESULTS.json').read_text());assert old['protocol_sha256']==p['parent_protocol_sha256']
    assert [ref['symbol'] for ref in old['input_refs']]==p['symbols']
    with np.load(PRIOR/'PAST_INTENTS.npz',allow_pickle=False) as panel:
        old_decisions=panel['decision_us'].copy()
    cutoff=pd.Timestamp(int(old_decisions[-1])-DAY_US,unit='us',tz='UTC')
    manifest=WORK/'reports/DATASET_MANIFEST.json';assert sha(manifest)==p['parent_dataset_sha256']
    m=json.loads(manifest.read_text());admitted={str(WORK/v['relative_path']):v['sha256'] for v in m['artifacts']}
    state.mkdir();save(state/'STARTED.json',dict(source_commit=source_commit,protocol_sha256=sha(a.protocol),started_at=time.time()))
    total=len(p['entries'])+5+2+1;done=0
    def progress(stage,detail):
        v=dict(status='running',stage=stage,phase=stage,completed=done,total=total,unit='任务',detail=detail,elapsed_seconds=time.monotonic()-began,updated_at=time.time(),pid=os.getpid())
        (state/'progress.json').write_text(json.dumps(v)+'\n');print(f'[{stage}] {done}/{total} {detail}',flush=True)
    def guard():
        assert time.monotonic()-began<p['budget']['wall_seconds']
        assert shutil.disk_usage(state).free>=p['budget']['reserve_bytes']
        assert sum(f.stat().st_size for f in state.rglob('*') if f.is_file())<=p['budget']['owned_bytes']
    def read(path,cols=None):
        path=Path(path);assert str(path) in admitted and sha(path)==admitted[str(path)]
        return pl.read_parquet(path,columns=cols).to_pandas()
    progress('DATA','fixed26 daily supplements; frozen source hashes')
    patches={};receipts=[];source_rows=0
    with session() as client:
        for entry in p['entries']:
            guard();day=pd.Timestamp(entry['day'],tz='UTC');job=Job(entry['symbol'],entry['family'],day.year,day.month,day.day)
            assert job.url==entry['url'] and entry['family'] in ['klines','markPriceKlines'] and '2022-01-01'<=entry['day']<='2023-12-31'
            receipt=fetch(job,client);receipts.append(receipt);save(state/f'SOURCE-{done:02d}.json',receipt)
            assert receipt['status'] in ['DOWNLOADED_VERIFIED','VERIFIED_CACHE','ADOPTED_VERIFIED_CACHE'],receipt
            raw=numeric_csv(job.path);lo=day.value//1000000;raw,_=validate_price(raw,entry['family'],lo,lo+86400000)
            assert np.array_equal(raw.timestamp_ms.to_numpy(),np.arange(lo,lo+86400000,60000)),'Daily archive itself incomplete'
            new=canonical(raw,entry['family'],entry['symbol']);key=(entry['symbol'],entry['family'],entry['day'][:7])
            if key not in patches:
                path=WORK/f'data/normalized/minute/{key[0]}/{key[1]}/{key[2]}.parquet';patches[key]=read(path)
            before=len(patches[key]);patches[key]=merge_observed(patches[key],new);source_rows+=len(patches[key])-before
            done+=1;progress('SOURCE',f'{entry["symbol"]} {entry["family"]} {entry["day"]}: verified1440 rows')
    (state/'minute').mkdir();patch_refs=[]
    for (s,f,month),v in patches.items():
        dest=state/'minute'/f'{s}_{f}_{month}.parquet';pl.from_pandas(v).write_parquet(dest,compression='zstd')
        patch_refs.append(dict(symbol=s,family=f,month=month,path=str(dest),sha256=sha(dest),rows=len(v)))
    daily={};frames=[];changes=[];derived_refs=[]
    for ref in old['input_refs']:
        guard();s=ref['symbol'];original=read(ref['daily_path'])
        assert original.dt.max().value//1000<p['locked_start_us']
        original=original.loc[original.dt<=cutoff].reset_index(drop=True)
        d=original.set_index('dt').copy();events=read(WORK/f'data/normalized/{s}_funding_events.parquet')
        for (ps,f,month),v in patches.items():
            if ps!=s:continue
            agg=aggregate_price(v,f)
            # Update the same source days only, preserving all untouched fields.
            days=[pd.Timestamp(e['day'],tz='UTC') for e in p['entries'] if e['symbol']==s and e['family']==f and e['day'].startswith(month)]
            if f=='klines':
                cols=['open','high','low','close','volume','quote_volume','trades','rows','unique_minutes','exec_price']
                d.loc[days,cols]=agg.loc[days,cols];d.loc[days,'complete_kline']=agg.loc[days,'complete']
                d.loc[days,'source_state']='OBSERVED_COMPLETE_OFFICIAL_DAILY_SUPPLEMENT'
            else:
                d.loc[days,'mark']=agg.loc[days,'close'];d.loc[days,'complete_mark']=agg.loc[days,'complete']
                affected=np.zeros(len(events),bool)
                for day in days:
                    affected|=(events.calc_time_ms>=day.value//1000000)&(events.calc_time_ms<=day.value//1000000+86400000+60000)
                fixed=mark_funding(events.loc[affected].reset_index(drop=True),v)
                events.loc[affected,['past_mark_price','past_mark_available_us']]=fixed[['past_mark_price','past_mark_available_us']].to_numpy()
        updated_funding=funding_windows(events,d.index)
        funding_cols=list(updated_funding.columns);d.loc[:,funding_cols]=updated_funding
        # Every changed cell is recorded; no global masked fill or zero funding.
        previous=original.set_index('dt')
        changed_dates=(~((d.eq(previous))|(d.isna()&previous.isna())).all(axis=1))
        permitted={pd.Timestamp(e['day'],tz='UTC') for e in p['entries'] if e['symbol']==s}
        # Funding at a restored source boundary may also affect the prior day.
        permitted|={day-pd.Timedelta(days=1) for day in list(permitted)}
        assert set(d.index[changed_dates])<=permitted,'Unexpected change outside declared source days/boundaries'
        changes.append(dict(symbol=s,changed_daily_dates=[str(v.date()) for v in d.index[changed_dates]],funding_incomplete_before=int((~previous.funding_interval_complete).sum()),funding_incomplete_after=int((~d.funding_interval_complete).sum())))
        dest=state/f'{s}_daily.parquet';pl.from_pandas(d.reset_index()).write_parquet(dest,compression='zstd');daily[s]=d.reset_index()
        f=feature_frame(daily[s],256);cols=['dt','symbol','close','decision_available_at','sma_signal',*FEATURES]
        path=state/f'{s}_past.parquet';pl.from_pandas(f[cols]).write_parquet(path,compression='zstd');frames.append(f)
        derived_refs.append(dict(symbol=s,daily_path=str(dest),daily_sha256=sha(dest),past_path=str(path),past_sha256=sha(path)))
        done+=1;progress('FEATURES',f'{s}: independent derived view, old files untouched')
    available=pd.DatetimeIndex(frames[0].decision_available_at).as_unit('us').asi8
    assert np.array_equal(available,old_decisions) and available[-1]<p['locked_start_us']
    assert all(np.array_equal(available,pd.DatetimeIndex(f.decision_available_at).as_unit('us').asi8) for f in frames)
    close=np.column_stack([f.close for f in frames]);sma=np.column_stack([f.sma_signal for f in frames]);weights=signed_intents(close,sma,available,p['symbols'])
    cube=np.stack([f[list(FEATURES)].to_numpy() for f in frames],axis=1);market_good=np.isfinite(cube).all((1,2))
    maturity=np.array([reference_available_at(v) for v in available]);coverage=[];panel_refs=[]
    for scale in [1,.01]:
        arrays=[interval_arrays(v,np.arange(len(v)-2),scale) for v in daily.values()]
        labels,reasons=reference_labels(weights,tuple(np.stack([x[k] for x in arrays],axis=1) for k in range(4)),.00135,10000,7)
        feedback,last=feedback_panel(available,maturity,labels,old['protocol']['anchor_us']);common=market_good&np.isfinite(feedback).all(1)&np.isfinite(labels).all(1)
        with np.load(PRIOR/f'REFERENCE_PANEL_{scale}.npz',allow_pickle=False) as original:
            before=original['common']&np.isfinite(original['labels']).all(1)
            assert np.array_equal(available,original['decision_us'])
            late=available>=old['protocol']['windows'][0]['start']
            assert np.allclose(labels[late],original['labels'][late],atol=1e-12,rtol=0,equal_nan=True),'Repair changed previously scored2024/25 utilities'
        np.savez_compressed(state/f'PANEL_{scale}.npz',decision_us=available,label_available_us=maturity,labels=labels,feedback=feedback,common=common,weights=weights)
        panel_refs.append(dict(funding_scale=scale,path=str(state/f'PANEL_{scale}.npz'),sha256=sha(state/f'PANEL_{scale}.npz')))
        counts=[]
        for window in old['protocol']['windows']:
            train=train_mask(available,maturity,common,window['start'],7);oldtrain=train_mask(available,maturity,before,window['start'],7)
            counts.append(dict(window=window['id'],before=int(oldtrain.sum()),after=int(train.sum())))
        bear=(available>=pd.Timestamp('2022-01-01',tz='UTC').value//1000)&(maturity<pd.Timestamp('2023-01-01',tz='UTC').value//1000)
        slots=(available-old['protocol']['anchor_us'])%(7*DAY_US)==0
        ids=np.flatnonzero(common)
        coverage.append(dict(scale=scale,first_complete_decision_us=int(available[ids[0]]) if len(ids) else None,train_counts=counts,bear_daily_rows_before=int((bear&before).sum()),bear_daily_rows_after=int((bear&common).sum()),bear_nonoverlap_week_blocks_before=int((bear&before&slots).sum()),bear_nonoverlap_week_blocks_after=int((bear&common&slots).sum()),invalid_label_reasons=reasons))
        done+=1;progress('LABELS',f'funding={scale}: source-support counts only, no fit')
    for ref in old['input_refs']:assert sha(ref['daily_path'])==ref['daily_sha256'] and sha(ref['past_path'])==ref['past_sha256']
    assert sha(manifest)==p['parent_dataset_sha256'];guard()
    result=dict(status='COMPLETE_OFFICIAL_SUPPLEMENT_DERIVED_VIEW_NOT_INVESTMENT',source_commit=source_commit,protocol_sha256=sha(a.protocol),parent_dataset_sha256=sha(manifest),receipts=receipts,minute_patch_refs=patch_refs,derived_refs=derived_refs,panel_refs=panel_refs,source_rows_added=source_rows,daily_changes=changes,coverage=coverage,new_fits=0,new_wallets=0,locked_consumed=False,old_inputs_unchanged=True,previously_scored_utilities_unchanged=True,elapsed_seconds=time.monotonic()-began,qualification='NONE_CASH',RAM_peak_bytes=None,RAM_limit_bytes=8000000000,swap=0,GPU=0)
    save(state/'RESULTS.json',result);done+=1;progress('REPORT','coverage restored; no re-training or old evidence replacement')
    value=json.loads((state/'progress.json').read_text());value['status']='completed';(state/'progress.json').write_text(json.dumps(value)+'\n')
    print(json.dumps(dict(status=result['status'],coverage=coverage,source_rows_added=source_rows,elapsed=result['elapsed_seconds'])))


if __name__=='__main__':
    try:main()
    except Exception as exc:
        # Preserve a failed run and its real progress; never display it as active.
        import sys
        if '--state' in sys.argv:
            path=Path(sys.argv[sys.argv.index('--state')+1])/'progress.json'
            if path.exists():
                value=json.loads(path.read_text());value.update(status='failed',error=repr(exc),updated_at=time.time());path.write_text(json.dumps(value)+'\n')
        raise
