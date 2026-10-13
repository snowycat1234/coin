"""Explicit-path transport of unchanged monthly and funding inputs."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import numpy as np

MINUTE=60_000_000;DAY=86_400_000_000
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_port(workspace):
    workspace=Path(workspace);repo=workspace/'coin_native_half_mix_20261013/repo'
    sys.path[:0]=[str(repo),str(repo/'src'),str(workspace/'coin_margin_protective_policy_20261013'),str(workspace/'coin_quantity_resolution_20261013')]
    os.environ['QUANT_ROOT']=str(repo);os.environ['QUANT_STATE']=str(workspace);os.environ['CONFIG_FILE']='/dev/null'
    path=repo/'research/static50-sma-20261013/local_native_apis.py'
    spec=importlib.util.spec_from_file_location('headroom_frozen_native_port',path)
    port=importlib.util.module_from_spec(spec);spec.loader.exec_module(port);port.verify()
    return port

def source_window(case,source_root,port,workspace):
    source_root=Path(source_root);workspace=Path(workspace)
    if sha(source_root/'SOURCE_INDEX.json')!=case['source_index_SHA256']:
        raise ValueError('Exact original source-index SHA required, independent of path')
    index=json.loads((source_root/'SOURCE_INDEX.json').read_text())
    symbols=tuple(case['symbols']);calendar=index.get('calendar',index.get('calendar_us'))
    if calendar!=case['calendar'] or tuple(index.get('symbol_order',index.get('symbols')))!=symbols:
        raise ValueError('Source calendar/symbol order differs')
    for name,rec in index['files'].items():
        p=source_root/name
        if sha(p)!=rec['SHA256'] or p.stat().st_size!=rec['bytes']:
            raise ValueError('Original source metadata bytes changed: '+name)
    if case['year']==2021:
        cube=workspace/'coin_cs_sma_recovery_20261013/inputs/Y2023.npz'
        if sha(cube)!='1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f':
            raise ValueError('Original2021 first completed sizing close changed')
        with np.load(cube,allow_pickle=False) as z:
            k=int(np.searchsorted(z['close_available_us'],calendar[0]))
            if z['close_available_us'][k]!=calendar[0]:raise ValueError('Original sizing close missing')
            first=z['close'][k].copy()
        with np.load(source_root/'DAILY_OHLC.npz',allow_pickle=False) as z:
            clocks=np.r_[calendar[0],z['available_us']];prices=np.vstack([first,z['close']])
        np.testing.assert_array_equal(clocks,np.arange(calendar[0],calendar[1]+DAY,DAY,dtype=np.int64))
        daily=port.native.pl.DataFrame([dict(symbol=s,close_us=int(t),close=float(prices[i,j])) for i,t in enumerate(clocks) for j,s in enumerate(symbols)])
    else:
        daily=port.native.pl.DataFrame(json.loads((source_root/'DAILY.json').read_text()))
    events=json.loads((source_root/'EVENTS.json').read_text())
    if len(events)!=index['funding_events']:raise ValueError('Original funding count changed')
    def blocks():
        expected=calendar[0]
        for rec in index['months']:
            p=source_root/'months'/(rec['month']+'.npz')
            if sha(p)!=rec['source_NPZ_SHA256'] or p.stat().st_size!=rec['source_NPZ_bytes']:
                raise ValueError('Original monthly source changed')
            with np.load(p,allow_pickle=False) as z:
                times=z['times'].copy()
                market={s:{k:z[s+'_'+k].copy() for k in ('open','close','quote_volume','mark')} for s in symbols}
            np.testing.assert_array_equal(times,np.arange(expected,expected+len(times)*MINUTE,MINUTE,dtype=np.int64));expected+=len(times)*MINUTE
            for offset in range(0,len(times),1440):
                yield {'times':times[offset:offset+1440],'market':{s:{k:v[offset:offset+1440] for k,v in row.items()} for s,row in market.items()}}
        if expected!=calendar[1]:raise ValueError('Original source full calendar ends differently')
    return dict(start=calendar[0],end=calendar[1],symbols=symbols,daily=daily,events=events,minute_blocks=blocks)

def rebuild_features(case,source_root,output,derived_csv=None):
    """Cloud-safe source-only rebuild; archive and all arrays must match freeze."""
    import csv
    from headroom_buffer import features
    from feature_tape import REASONS,FeatureTape
    source_root=Path(source_root);output=Path(output)
    manifest=json.loads((Path(__file__).parent/'features'/f"Y{case['year']}.json").read_text())
    if sha(source_root/'SOURCE_INDEX.json')!=case['source_index_SHA256']:raise ValueError('Source-index SHA changed')
    pieces=[]
    for rec in manifest['source_months']:
        p=source_root/'months'/(rec['month']+'.npz')
        if sha(p)!=rec['source_NPZ_SHA256'] or p.stat().st_size!=rec['source_NPZ_bytes']:raise ValueError('Source month SHA changed')
        with np.load(p,allow_pickle=False) as z:
            pieces.append({k:z[k].copy() for k in ['times',*[s+'_'+f for s in case['symbols'] for f in ('mark','open')]]})
    source={k:np.concatenate([p[k] for p in pieces]) for k in pieces[0]}
    np.testing.assert_array_equal(source['times'],np.arange(*case['calendar'],MINUTE,dtype=np.int64))
    mask={s:np.zeros(len(source['times']),bool) for s in case['symbols']}
    if case['year']==2024:
        if derived_csv is None or sha(derived_csv)!=case['derived_csv_SHA256']:raise ValueError('Original derived-cell provenance required')
        with Path(derived_csv).open() as f:rows=list(csv.DictReader(f))
        if len(rows)!=10:raise ValueError('Exactly ten original conditional cells')
        for row in rows:
            t=int(row['open_time_ms'])*1000;i=int(np.searchsorted(source['times'],t))
            if source['times'][i]!=t or row['source_missing']!='True':raise ValueError('Original derived cell coordinates differ')
            mask[row['symbol']][i]=True
    arrays={'close_us':source['times']+MINUTE}
    for s in case['symbols']:
        f=features(source['times'],source[s+'_mark'],source[s+'_open'],mask[s]);arrays[s+'_mark']=source[s+'_mark']
        for k in ('ready','a_down','a_up','g_down','g_up'):arrays[s+'_'+k]=f[k]
        codes=np.zeros(len(source['times']),np.uint8)
        for i,reason in enumerate(REASONS):codes[f['reason']==reason]=i
        arrays[s+'_reason_code']=codes
    if output.exists():raise FileExistsError('Source-only feature output must be fresh')
    output.parent.mkdir(parents=True,exist_ok=True);np.savez_compressed(output,**arrays)
    return FeatureTape.load(output,manifest).binding
