"""Read-only matched short attribution; no new accounts or recipe selection."""
import json,hashlib,os
from datetime import UTC,datetime
from collections import defaultdict
import polars as pl
from quant.paths import ROOT

def sha(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
paths=['reports/fast_research/CTA_TWO_SPEED_BASE27_20261005_V1.json','reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json']
rows=[]
for path in paths:
 r=json.loads((ROOT/path).read_bytes());c=next(v for v in r['cases'] if v['mode']=='LONG_SHORT' and v['unit']=='RAW_AS_PERCENT');s=c['summary'];assert s['completed_minutes']==s['required_minutes']
 for name in ('trades.parquet','funding.parquet','minute_nav_inventory.parquet'):assert sha(c['artifacts'][name]['path'])==c['artifacts'][name]['sha256']
 trades=pl.read_parquet(c['artifacts']['trades.parquet']['path']);fund=pl.read_parquet(c['artifacts']['funding.parquet']['path']);assets={x:dict(gross=0.,fees=0.,execution=0.,funding=0.,short_fills=0,short_open_or_add_legs=0,short_turnover_notional=0.) for x in s['symbols']}
 for v in trades.iter_rows(named=True):
  before,after=v['quantity_before'],v['quantity_after'];assert before*after>=0
  if before>=0 and after>=0:continue
  z=assets[v['symbol']];z['gross']-=v['position_delta']*v['mid_price'];z['fees']+=v['fee_USDT_mid'];z['execution']+=v['execution_cost'];z['short_fills']+=1;z['short_open_or_add_legs']+=after<before;z['short_turnover_notional']+=abs(v['position_delta']*v['mid_price'])
 for v in fund.iter_rows(named=True):
  if v['quantity']<0:assets[v['symbol']]['funding']+=v['signed_funding_USDT']
 terminal=pl.scan_parquet(c['artifacts']['minute_nav_inventory.parquet']['path']).tail(1).collect().to_dicts()[0]
 for x,z in assets.items():
  z['terminal_signed_marked_notional']=min(0.,terminal[x+'_signed_marked_notional']);z['gross']+=z['terminal_signed_marked_notional'];z['net']=z['gross']+z['funding']-z['fees']-z['execution']
 assert abs(sum(v['net'] for v in assets.values())-s['long_short_marked_contribution']['SHORT']['net_contribution'])<1e-7
 days=c['independent']['daily_direction_contributions'];states=r['descriptive_past_states'];day=86400000000
 losses=sorted((dict(date=datetime.fromtimestamp((v['day_end_us']-day)/1e6,UTC).date().isoformat(),past_BTC_state=states[str(v['day_end_us']-day)],SHORT=v['SHORT'],LONG=v['LONG']) for v in days),key=lambda v:v['SHORT'])
 bear=[v for v in losses if v['past_BTC_state']=='BEAR'];tot=sum(v['SHORT'] for v in bear);assert abs(tot-c['independent']['by_past_regime']['BEAR']['SHORT'])<1e-7
 rows.append(dict(source=path,source_sha256=sha(ROOT/path),strategy=c['strategy'],short_by_asset=assets,SHORT_total=sum(v['net'] for v in assets.values()),top5_short_losses=losses[:5],BEAR_short_days=len(bear),BEAR_short_sum=tot,BEAR_worst5_days=bear[:5],concentration=s['daily_net_gain_concentration'],actual_short_open_or_add_legs=c['independent']['actual_short_open_legs']))
delta={x:{k:rows[1]['short_by_asset'][x][k]-rows[0]['short_by_asset'][x][k] for k in ('net','gross','fees','execution','funding','short_turnover_notional')} for x in rows[0]['short_by_asset']}
assert abs(sum(v['net'] for v in delta.values())-(rows[1]['SHORT_total']-rows[0]['SHORT_total']))<1e-7
out=ROOT/'reports/SHORT_SELECTION_ATTRIBUTION_20261006_V1.json';assert not out.exists()
result=dict(status='PASS_SAVED_JOURNAL_SHORT_ASSET_AND_PAST_STATE_BRIDGES',created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID'],cases=rows,asset_delta=delta,new_accounts=0,fits=0,scope='WHOLE_WALLET_SHORT_CONTRIBUTIONS; INCLUDES_FEES_EXECUTION_FUNDING_AND_MARKED_RESIDUAL; NOT_SHORT_ONLY_ACCOUNT; PAST_BTC_REGIME_NOT_EACH_ASSET_REGIME; POST_RESULT_DESCRIPTIVE_DIAGNOSTIC_NOT_NEW_GATE')
out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
print(json.dumps(dict(asset_delta=delta,new_short=rows[1]['SHORT_total'],bear_worst5=rows[1]['BEAR_worst5_days']),ensure_ascii=False))