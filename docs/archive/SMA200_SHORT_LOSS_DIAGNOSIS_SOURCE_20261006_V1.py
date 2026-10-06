import json,os
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha
path=ROOT/'reports/fast_research/SMA200_FIXED_CYCLE_LONG_SHORT_20261006_V1.json'
r=json.loads(path.read_bytes());case=next(c for c in r['cases'] if c['unit']=='RAW_AS_PERCENT')
monthly={};daily=[]
for d in case['independent']['daily_direction_contributions']:
    day=datetime.fromtimestamp((d['day_end_us']-1)//1000000,UTC)
    key=day.strftime('%Y-%m');monthly[key]=monthly.get(key,0.)+d['SHORT']
    if day.year==2023:daily.append(dict(day=day.strftime('%Y-%m-%d'),SHORT=d['SHORT']))
expected=case['summary']['long_short_marked_contribution']['SHORT']['net_contribution']
assert abs(sum(monthly.values())-expected)<1e-7
years={y:sum(v for k,v in monthly.items() if k.startswith(y)) for y in ('2022','2023')}
out=dict(status='PASS_SAVED_SMA200_SHORT_MONTHLY_PNL_BRIDGE_NOT_NEW_RECIPE',task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),
    producer_sha256=sha(path),monthly_SHORT=monthly,yearly_SHORT=years,worst2023days=sorted(daily,key=lambda d:d['SHORT'])[:10],
    actual_SHORT=expected,bridge_error=abs(sum(monthly.values())-expected),new_accounts=0,fits=0,
    created_utc=datetime.now(UTC).isoformat(),scope='SAME_WALLET_DAILY_SHORT_CONTRIBUTION; NOT_ORDER_REASON_CAUSALITY_OR_REMOVED_COST_COUNTERFACTUAL')
with (ROOT/'reports/SMA200_SHORT_LOSS_DIAGNOSIS_20261006_V1.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'],years=years,months2023={k:v for k,v in monthly.items() if k.startswith('2023')})))
