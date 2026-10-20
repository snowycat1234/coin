"""Generated threshold/capacity joint cases; no price history."""
from pathlib import Path
from decimal import Decimal as D, ROUND_CEILING, ROUND_DOWN, localcontext
import sys,json
sys.path[:0]=[str(Path(__file__).parent/'src'),str(Path(__file__).parent)]
from quant.perpetual_account import PerpetualConfig,InstrumentProfile
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Account

def need(v,m):
 if not v:raise RuntimeError(m)
rows=[]
with localcontext() as ctx:
 ctx.prec=40
 for side,direction in [('BUY',D(1)),('SELL',D(-1))]:
  for bps in [D(4),D(8),D(16)]:
   for step in [D('.00000001'),D('.01')]:
    fill=D(100)*(1+direction*2*bps/10000)
    threshold=(D(10)/fill/step).to_integral_value(rounding=ROUND_CEILING)*step
    for qshift in [-1,0,1]:
     for cshift in [-1,0,1]:
      q=threshold+qshift*step;capacity=threshold+cshift*step
      a=Account(PerpetualConfig(half_spread_bps=bps,slippage_bps=bps),symbols=('BTCUSDT',),instrument_profiles={'BTCUSDT':InstrumentProfile(quantity_step=step)})
      a.update_marks(0,{'BTCUSDT':dict(price=100,close_us=0,available_us=0)})
      request=dict(symbol='BTCUSDT',side=side,quantity=q,event_us=60000001,signal_us=0,fill_id='boundary',execution_mid_price=100,quote_available_us=0,available_quantity=capacity)
      r=a.execute_fill(**request)
      possible=(min(q,capacity)/step).to_integral_value(rounding=ROUND_DOWN)*step
      expected=possible if possible*fill>=10 else D(0)
      need(a.positions['BTCUSDT'].quantity==direction*expected,'JOINT_THRESHOLD_CAPACITY')
      need(a.fees==expected*fill*D('.00055'),'FEE_BASE')
      need(a.execution_cost==expected*D(100)*2*bps/10000,'EXECUTION_COST')
      need(a.nav()==D(10000)-a.fees-a.execution_cost,'NAV')
      snap=a.snapshot();restored=Account.from_snapshot(snap)
      need(restored.execute_fill(**request)==r and restored.snapshot()==snap,'CACHED_RECEIPT_RESTORE')
      changed=dict(request,available_quantity=capacity+step)
      try:restored.execute_fill(**changed)
      except ValueError:pass
      else:raise RuntimeError('CONFLICTING_CAPACITY_ACCEPTED')
      need(restored.snapshot()==snap,'CONFLICT_MUTATED_STATE')
      rows.append(dict(side=side,bps=str(bps),step=str(step),qshift=qshift,cshift=cshift,executed=str(expected),status=r['status']))
result={'status':'PASS','generated_cases':len(rows),'scope':'Joint fill-price minimum, lot-floor, capacity and restored cached rejection/partial/full receipt; existing account only.','cases':rows}
p=Path(__file__).parent/('BOUNDARY_OPTIMIZED.json' if sys.flags.optimize else 'BOUNDARY_RESULT.json');p.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k!='cases'}))
