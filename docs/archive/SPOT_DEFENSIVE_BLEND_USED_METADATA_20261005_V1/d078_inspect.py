import json
from pathlib import Path
import polars as pl
R=Path('/mnt/d/codex/coin');S=Path('/home/xflops/coin-state')
v=json.loads((R/'reports/fast_research/SPOT_DEFENSIVE_BLEND_20261005_V1.json').read_bytes())
d=json.loads((S/'d078-spot-saved-diagnostics-20261005-v1/RESULT.json').read_bytes())
print(json.dumps(d['cases']['BLEND'][0],indent=2))
for name in ['SPOT_DEFENSIVE_BLEND_20261005_V1','SPOT_PERPETUAL_PRODUCT_20261005_V1']:
    p=json.loads((R/'reports/fast_research'/f'{name}.json').read_bytes())
    for c in p['cases']:
        t=pl.read_parquet(c['artifacts']['trades']['path'])
        print(json.dumps(dict(recipe=name,cost=c['id'],median_notional=t['notional'].median(),
            bands=[dict(under_USDT=x,count=t.filter(pl.col('notional')<x).height,
                cost_USDT=float(t.filter(pl.col('notional')<x).select((pl.col('fee')+pl.col('execution_cost')).sum()).item()))
                for x in [25,50,100]])))
