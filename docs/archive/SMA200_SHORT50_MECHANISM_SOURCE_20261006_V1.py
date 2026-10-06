import json,os
from datetime import UTC,datetime
from quant.paths import ROOT
from scripts.investment.reuse_cycle_controls import sha

def read(p):return json.loads((ROOT/p).read_bytes())
new=read('reports/fast_research/SMA200_SHORT50_LONG_SHORT_20261006_V1.json')
old=read('reports/fast_research/SMA200_FIXED_CYCLE_LONG_SHORT_20261006_V1.json')
rows=[]
for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
    old_case=next(c for c in old['cases'] if c['unit']==unit)
    new_case=next(c for c in new['cases'] if c['unit']==unit)
    values=[]
    for case in (old_case,new_case):
        months={}
        for day in case['independent']['daily_direction_contributions']:
            m=datetime.fromtimestamp((day['day_end_us']-1)//1000000,UTC).strftime('%Y-%m')
            months[m]=months.get(m,0.)+day['SHORT']
        error=abs(sum(months.values())-case['summary']['long_short_marked_contribution']['SHORT']['net_contribution'])
        assert error<1e-7
        values.append(dict(id=case['id'],monthly_SHORT=months,bridge_error=error))
    a,b=old_case['summary'],new_case['summary']
    contribution=lambda s,k:s['long_short_marked_contribution'][k]['net_contribution']
    delta_short=contribution(b,'SHORT')-contribution(a,'SHORT');delta_long=contribution(b,'LONG')-contribution(a,'LONG')
    assert abs(delta_short+delta_long-(b['net_PnL']-a['net_PnL']))<1e-7
    rows.append(dict(unit=unit,old=values[0],new=values[1],
        delta_net=b['net_PnL']-a['net_PnL'],delta_SHORT=delta_short,
        delta_LONG_from_same_wallet_path_not_signal_change=delta_long,
        fees_and_execution_old=a['fees_USDT']+a['execution_cost_USDT'],
        fees_and_execution_new=b['fees_USDT']+b['execution_cost_USDT']))
out=dict(status='PASS_SHORT50_MONTHLY_AND_DIRECTION_PNL_BRIDGE',task_id=os.environ['COIN_TASK_ID'],
    source_sha256=sha(__file__),rows=rows,new_accounts=0,fits=0,created_utc=datetime.now(UTC).isoformat(),
    scope='SAME_WALLET_DAILY_MARKED_PNL; NOT_ORDER_REASON_CAUSALITY; LONG_SIGNAL_UNCHANGED_BUT_CAPITAL_PATH_CAN_CHANGE_LONG_PNL')
with (ROOT/'reports/SMA200_SHORT50_MECHANISM_20261006_V1.json').open('x') as f:
    json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'],rows=rows)))
