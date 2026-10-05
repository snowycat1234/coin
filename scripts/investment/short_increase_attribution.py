"""Read-only marginal attribution of initial orders vs later short increases.

Pro rata lot accounting is descriptive, not a remove-adds counterfactual.
"""
import json,hashlib,os
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
from quant.paths import ROOT

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
p=ROOT/'reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json';raw=json.loads(p.read_bytes());c=next(v for v in raw['cases'] if v['unit']=='RAW_AS_PERCENT');assert c['summary']['terminal_cash_realized']
for k in ('trades.json','funding.parquet'):assert sha(c['artifacts'][k]['path'])==c['artifacts'][k]['sha256']
trades=json.loads(Path(c['artifacts']['trades.json']['path']).read_bytes());fund=pl.read_parquet(c['artifacts']['funding.parquet']['path']).to_dicts();stream=sorted([(v['event_us'],1,'TRADE',v) for v in trades]+[(v['event_us'],0,'FUNDING',v) for v in fund],key=lambda v:v[:2]);pool={s:[] for s in raw['protocol']['symbols']};orders={};lots=[]
for t,_,kind,v in stream:
 s=v['symbol'];active=pool[s];held=sum(z['remaining'] for z in active)
 if kind=='FUNDING':
  if v['quantity']>=0:continue
  assert abs(held+v['quantity'])<1e-7
  for z in active:z['funding']+=v['signed_funding_USDT']*z['remaining']/held
  continue
 before,after=v['quantity_before'],v['quantity_after'];assert before*after>=0
 if before>=0 and after>=0:continue
 assert abs(held+before)<1e-7
 if after<before:
  order=v['fill_id'].rsplit(':',2)[0]
  if before==0:orders[s]=order
  group='INITIAL_LOGICAL_ORDER' if order==orders[s] else 'SUBSEQUENT_INCREASE_ORDER'
  z=dict(symbol=s,group=group,order_id=order,event_us=t,entry_mid=v['mid_price'],remaining=-v['position_delta'],gross=0.,fees=v['fee_USDT_mid'],execution=v['execution_cost'],funding=0.,entry_quantity=-v['position_delta']);active.append(z);lots.append(z)
 else:
  closed=v['position_delta'];assert 0<closed<=held+1e-7
  fraction=min(1.,closed/held)
  for z in active:
   share=z['remaining']/held;quantity=z['remaining']*fraction;z['gross']+=quantity*(z['entry_mid']-v['mid_price']);z['fees']+=v['fee_USDT_mid']*share;z['execution']+=v['execution_cost']*share;z['remaining']-=quantity
  if after==0:
   assert sum(z['remaining'] for z in active)<1e-7;pool[s]=[];orders.pop(s)
assert not any(pool.values())
groups={}
for z in lots:
 z['net']=z['gross']+z['funding']-z['fees']-z['execution'];v=groups.setdefault(z['group'],dict(open_fill_fragments=0,logical_orders=set(),gross=0.,fees=0.,execution=0.,funding=0.,net=0.));v['open_fill_fragments']+=1;v['logical_orders'].add((z['symbol'],z['order_id']))
 for k in ('gross','fees','execution','funding','net'):v[k]+=z[k]
for v in groups.values():v['logical_orders']=len(v['logical_orders'])
expected=c['summary']['long_short_marked_contribution']['SHORT']['net_contribution'];error=abs(sum(v['net'] for v in groups.values())-expected);assert error<1e-7
out=ROOT/'reports/SHORT_INCREASE_ATTRIBUTION_20261006_V1.json';assert not out.exists();out.write_text(json.dumps(dict(status='PASS_ALL303D_SHORT_PRO_RATA_LOT_PNL_BRIDGE_NOT_NO_ADD_BACKTEST',created_utc=datetime.now(UTC).isoformat(),task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),producer_sha256=sha(p),actual_SHORT=expected,bridge_error=error,groups=groups,lots=lots,new_accounts=0,fits=0,scope='FIRST_LOGICAL_ORDER_FRAGMENTS_VS_LATER_SHORT_INCREASE_ORDERS; PRO_RATA_EXITS_AND_ACTUAL_FUNDING; NOT_CAUSAL_OR_UNSEEN; REMOVING_ADDS_REQUIRES_FULL_ACCOUNT_REPLAY'),indent=2,ensure_ascii=False,allow_nan=False)+'\n');print(json.dumps(dict(groups=groups,SHORT=expected,bridge_error=error)))