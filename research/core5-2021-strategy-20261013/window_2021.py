"""Transport-only full2021 source view for the byte-identical native scheduler."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
REPO=ROOT/'coin_native_half_mix_20261013/repo'
SOURCE=ROOT/'coin_2021_source_closure_20261013/prepared_2021'
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
DAY=86_400_000_000

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def source_window(pl):
    import numpy as np
    from prepare_targets import source_gate,CUBE_SHA
    source_gate()
    index=json.loads((SOURCE/'SOURCE_INDEX.json').read_text())
    start,end=index['calendar_us']
    cube=ROOT/'coin_cs_sma_recovery_20261013/inputs/Y2023.npz'
    if sha(cube)!=CUBE_SHA[2023]:raise ValueError('SOURCE_STOP: initial completed daily signal close changed')
    with np.load(cube,allow_pickle=False) as a:
        k=int(np.searchsorted(a['close_available_us'],start))
        if a['close_available_us'][k]!=start:raise ValueError('SOURCE_STOP: initial completed daily signal close absent')
        first=a['close'][k].copy()
    with np.load(SOURCE/'DAILY_OHLC.npz',allow_pickle=False) as a:
        clocks=np.r_[start,a['available_us']]
        values=np.vstack([first,a['close']])
    np.testing.assert_array_equal(clocks,np.arange(start,end+DAY,DAY,dtype=np.int64))
    if not np.isfinite(values).all() or (values<=0).any():raise ValueError('SOURCE_STOP: actual daily sizing prices')
    daily=pl.DataFrame([dict(symbol=s,close_us=int(at),close=float(values[i,j]))
        for i,at in enumerate(clocks) for j,s in enumerate(SYMBOLS)])
    events=json.loads((SOURCE/'EVENTS.json').read_text())
    if len(events)!=5475:raise ValueError('SOURCE_STOP: funding event count')
    def blocks():
        for rec in index['months']:
            path=SOURCE/'months'/(rec['month']+'.npz')
            if sha(path)!=rec['source_NPZ_SHA256'] or path.stat().st_size!=rec['source_NPZ_bytes']:
                raise ValueError('SOURCE_STOP: actual monthly tape changed')
            with np.load(path,allow_pickle=False) as z:
                times=z['times'].copy()
                market={s:{k:z[s+'_'+k].copy() for k in ('open','close','quote_volume','mark')} for s in SYMBOLS}
            for offset in range(0,len(times),1440):
                yield dict(times=times[offset:offset+1440],
                    market={s:{k:v[offset:offset+1440] for k,v in row.items()} for s,row in market.items()})
    return dict(start=start,end=end,symbols=SYMBOLS,daily=daily,events=events,minute_blocks=blocks)

def load_port_and_source():
    from freeze_2021 import verify
    verify(require_review=True)
    path=REPO/'research/static50-sma-20261013/local_native_apis.py'
    if sha(path)!='c290175e490ac982b37f60e5b45793068169629fbeb70dc1625d49f7cfb4cb22':
        raise ValueError('Frozen native transport changed')
    sys.path[:0]=[str(REPO),str(REPO/'src')]
    os.environ['QUANT_ROOT']=str(REPO)
    os.environ['QUANT_STATE']=str(HERE)
    os.environ['CONFIG_FILE']='/dev/null'
    spec=importlib.util.spec_from_file_location('exact_original_2021_native_port',path)
    port=importlib.util.module_from_spec(spec);spec.loader.exec_module(port);port.verify()
    return port,source_window(port.native.pl)
