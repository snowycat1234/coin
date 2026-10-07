import json
from pathlib import Path
import numpy as np
import polars as pl

state=Path('/home/ubuntu/coin/execution-state/bear-support-observed-20261008-v1')
r=json.loads((state/'RESULTS.json').read_text())
old=json.loads(Path('/home/ubuntu/coin/execution-state/joint-information-20261008-v1/RESULTS.json').read_text())
cols=['close','sma_signal','mom20','mom60','mom200','dist50','dist200','vol30','range','vol_z']
out=[]
for a,b in zip(old['input_refs'],r['derived_refs']):
    frames=[]
    for ref in (a,b):
        f=pl.read_parquet(ref['past_path'],columns=['decision_available_at',*cols])
        f=f.filter((pl.col('decision_available_at').dt.epoch('us')>=old['protocol']['windows'][0]['start'])&(pl.col('decision_available_at').dt.epoch('us')<=max(x['end'] for x in old['protocol']['windows'])))
        frames.append(f)
    assert frames[0].height==frames[1].height
    delta=[]
    for c in cols:
        x=frames[0][c].to_numpy();y=frames[1][c].to_numpy();k=int(np.nanargmax(np.abs(x-y)))
        delta.append(dict(feature=c,max_abs_delta=float(abs(x[k]-y[k])),old=float(x[k]),new=float(y[k]),old_dtype=str(frames[0][c].dtype),new_dtype=str(frames[1][c].dtype),decision_us=int(frames[0]['decision_available_at'].dt.epoch('us')[k])))
    out.append(dict(symbol=a['symbol'],delta=delta))
with (state/'FEATURE_DELTA.json').open('x') as f:json.dump(out,f,indent=2)
print(json.dumps(out))
