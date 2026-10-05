import hashlib,json
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=ROOT/'reports/fast_research/SPOT_LATER_BLEND_20261005_V1.json';v=json.loads(p.read_bytes())
def frame(r):assert sha(r['path'])==r['sha256'];return pl.read_parquet(r['path'])
bars=frame(v['daily_bars']);target=frame(v['target_artifact']);symbols=v['cases'][0]['symbols']
assert all(not any(r['component_EXIT10_raw']) and not any(r['component_EXIT10_target']) for r in v['target_meta']['risk'])
expected=[];sigma=[]
for t in target['available_us'].unique(maintain_order=True):
    returns=[]
    for s in symbols:
        closes=bars.filter((pl.col('symbol')==s)&(pl.col('available_us')<=t)).sort('close_us').tail(31)['close'].to_numpy()
        returns.append(np.diff(closes)/closes[:-1])
    matrix=np.column_stack(returns);centered=matrix-matrix.mean(axis=0);cov=centered.T@centered/29*365
    raw=np.full(len(symbols),min(.3,.6/len(symbols)));vol=float(np.sqrt(raw@cov@raw));sigma.append(vol)
    expected.extend(raw*min(1.,.05/vol))
gap=float(np.max(abs(np.array(expected)-target['target_weight'].to_numpy())))
out=STATE/'d082-later-spot-20261005-v1/MECHANISM.json'
with out.open('x') as f:json.dump(dict(status='SAVED_TARGET_MECHANISM_DIAGNOSTIC',input_sha256=sha(p),
    zero_EXIT10_raw_and_scaled_days=len(sigma),target_rows=target.height,
    diagnostic_budget=.05,budget_derivation='.5 times existing HOLD10; no fitted risk level or grid',
    independent_lower_budget_target_max_gap=gap,past_unscaled_vol_min=min(sigma),past_unscaled_vol_max=max(sigma),
    claim='No Donchian exposure in this fresh-flat 90day account; saved blend equals half HOLD10. Lower-budget target comparison is descriptive, not an executed HOLD5 PnL.',
    lower_budget_wallets='NOT_RUN',CASH_reference=dict(initial_capital_USDT=10000,net_USDT=0,model='USDT denomination, no interest, no trades'),
    new_market_replays=0,source_sha256=sha(__file__)),f,indent=2)
print(json.dumps(dict(zero_signal_days=len(sigma),lower_budget_target_gap=gap)))
