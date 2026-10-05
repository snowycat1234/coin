"""Independent scalar daily HOLD / Donchian target reference, no producer calls."""
import argparse, hashlib, json, time
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT, STATE
DAY=86_400_000_000
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def frame(r):
    assert sha(r['path'])==r['sha256'];v=pl.read_parquet(r['path']);assert v.height==r['rows'];return v
def calculate(bars,saved,symbols,recipe):
    times=saved['available_us'].unique(maintain_order=True).to_numpy();assert np.all(np.diff(times)==DAY)
    assert list(zip(saved['available_us'],saved['symbol']))==[(int(t),s) for t in times for s in symbols]
    states=dict.fromkeys(symbols,False);expected=[];raws=[];entries=dict.fromkeys(symbols,0);exits=dict.fromkeys(symbols,0)
    for t in times:
        returns=[]
        for s in symbols:
            p=bars.filter((pl.col('symbol')==s)&(pl.col('close_us')<=t)&(pl.col('available_us')<=t)).sort('close_us').tail(200)
            assert p.height==200 and p['close_us'][-1]==t and np.all(np.diff(p['close_us'])==DAY)
            close=p['close'][-1]
            if states[s]:
                if close<min(p['low'][-11:-1]):states[s]=False;exits[s]+=1
            elif close>max(p['high'][-21:-1]) and close>p['close'].mean():states[s]=True;entries[s]+=1
            prices=p['close'][-31:].to_numpy();returns.append(np.diff(prices)/prices[:-1])
        matrix=np.column_stack(returns);centered=matrix-matrix.mean(axis=0);cov=centered.T@centered/29*365
        hraw=np.full(len(symbols),min(.3,.6/len(symbols)))
        active=sum(states.values());draw=np.array([min(.3,.6/active) if states[s] else 0. for s in symbols]) if active else np.zeros(len(symbols))
        def scale(raw,limit):
            vol=float(np.sqrt(max(0.,raw@cov@raw)));return raw*min(1.,limit/vol) if vol else raw
        if recipe=='HOLD8':expected.extend(scale(hraw,.08));raws.extend(hraw)
        else:
            assert recipe=='HALF_HOLD10_EXIT10'
            expected.extend(.5*scale(hraw,.1)+.5*scale(draw,.1));raws.extend(.5*hraw+.5*draw)
    return np.array(expected),np.array(raws),entries,exits
ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);a=ap.parse_args();began=time.monotonic()
v=json.loads(Path(a.input).read_bytes());bars=frame(v['daily_bars']);saved=frame(v['target_artifact']);symbols=v['cases'][0]['symbols']
target,raw,entries,exits=calculate(bars,saved,symbols,v['recipe'])
gap=float(np.max(abs(target-saved['target_weight'].to_numpy())));raw_gap=float(np.max(abs(raw-saved['raw_signed_target'].to_numpy())))
assert max(gap,raw_gap)<=1e-12
cutoff=int(saved['available_us'][saved.height//2]);early=saved.filter(pl.col('available_us')<=cutoff)
altered=bars.with_columns([pl.when(pl.col('available_us')>cutoff).then(pl.col(n)*1.17).otherwise(pl.col(n)).alias(n) for n in ('open','high','low','close')])
perturbed,_,_,_=calculate(altered,saved,symbols,v['recipe']);early_gap=float(np.max(abs(perturbed[:early.height]-target[:early.height])));assert early_gap<=1e-12
times=saved['available_us'].unique(maintain_order=True).to_numpy()
if v['recipe']=='HOLD8':
    from scripts.investment.vol_managed_perpetual_target import fixed_targets
    altered_targets,_=fixed_targets(altered,times,'LONG_ONLY',symbols=symbols,allocation='EQUAL',annual_vol_target=.08)
else:
    from scripts.investment.hold_donchian_blend_target import fixed_targets
    altered_targets,_=fixed_targets(altered,times,'LONG_ONLY',symbols=symbols)
producer_early_gap=float(np.max(abs(altered_targets['target_weight'][:early.height].to_numpy()-saved['target_weight'][:early.height].to_numpy())))
assert producer_early_gap<=1e-12
out=Path(a.output).resolve();assert out.is_relative_to(STATE);out.parent.mkdir(parents=True,exist_ok=True)
with out.open('x') as f:json.dump(dict(status='PASS_INDEPENDENT_DAILY_SCALAR_TARGETS_AND_FUTURE_PERTURBATION',input_sha256=sha(a.input),
    target_rows=saved.height,target_max_error=gap,raw_max_error=raw_gap,early_future_perturbation_max_error=early_gap,
    entries=entries,exits=exits,producer_future_perturbation_early_error=producer_early_gap,
    current_source_sha256=sha(ROOT/'scripts/investment/public_sma_perpetual.py'),source_sha256=sha(__file__),elapsed_seconds=time.monotonic()-began,scope='Independent scalar expected signals, centered Gram covariance, allocation and blend; separate producer future perturbation. Not market QA, native execution or alpha qualification.'),f,indent=2)
print(json.dumps(dict(status='PASS_INDEPENDENT_DAILY_SCALAR_TARGETS_AND_FUTURE_PERTURBATION',error=gap)))
