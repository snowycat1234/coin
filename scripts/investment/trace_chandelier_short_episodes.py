"""Whole recorded short-episode first-trigger trace; no altered wallet/PnL."""
import json,hashlib,os,time,resource
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
import numpy as np
from quant.paths import ROOT
from scripts.investment.chandelier_short_levels import levels,RULES
from scripts.investment.multi_asset_data import load_portfolio_window
from scripts.investment.run_cta_leaderboard import stamp
from scripts.research_v7.oracle_flow_ceiling import Progress
DAY=86400000000;MINUTE=60000000

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
p=ROOT/'reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json';raw=json.loads(p.read_bytes());s=raw['protocol'];c=next(c for c in raw['cases'] if c['unit']=='RAW_AS_PERCENT');assert sha(c['artifacts']['trades.json']['path'])==c['artifacts']['trades.json']['sha256'];trades=json.loads(Path(c['artifacts']['trades.json']['path']).read_bytes());episodes=[];active={}
for v in trades:
 if v['quantity_before']==0 and v['quantity_after']<0:
  assert v['symbol'] not in active;z=dict(symbol=v['symbol'],first_fill_us=v['event_us'],entry_mid=v['mid_price'],first_signal_us=v['signal_us']);episodes.append(z);active[v['symbol']]=z
 if v['quantity_before']<0 and v['quantity_after']==0:active.pop(v['symbol'])['actual_flat_us']=v['event_us']
assert not active and len(episodes)==24
begin=stamp(s['economics_start']);end=stamp(s['economics_end_exclusive']);whole=load_portfolio_window(s['data_manifest']['path'],tuple(s['symbols']),begin,end);lines=levels(whole['daily'],tuple(s['symbols']));lookup={(v['available_us'],v['symbol']):v['short_exit_line'] for v in lines.iter_rows(named=True)};manifest=json.loads(Path(s['data_manifest']['path']).read_bytes());records={(v['symbol'],v['month']):v for v in manifest['market_records'] if v['kind']=='klines'};progress=Progress();started=time.monotonic()
for i,z in enumerate(episodes):
 first=z['first_fill_us'];last=z['actual_flat_us'];symbol=z['symbol'];trail=None;trigger=None
 for day in range(first//DAY*DAY,last//DAY*DAY+1,DAY):
  line=lookup[(day,symbol)];assert line is not None and line>0;trail=min(trail,line) if trail is not None else line
  month=datetime.fromtimestamp(day/1e6,UTC).strftime('%Y-%m');r=records[(symbol,month)];a=max(day,(first//MINUTE+1)*MINUTE);b=min(day+DAY,last//MINUTE*MINUTE)
  if b<=a:continue
  prices=pl.scan_parquet(r['normalized_path']).filter((pl.col('open_us')>=a)&(pl.col('close_us')<=b)).select('open_us','close_us','available_us','close').sort('open_us').collect()
  assert prices.height==(b-a)//MINUTE and prices['available_us'].equals(prices['close_us'])
  cross=prices.filter(pl.col('close')>trail)
  if cross.height:
   trigger=int(cross['close_us'][0]);z.update(first_public_trailing_trigger_us=trigger,known_stop_line=trail,trigger_trade_close=float(cross['close'][0]),earliest_eligible_open_us=trigger+MINUTE,days_before_actual_flat=(last-trigger)/DAY);break
 z.setdefault('first_public_trailing_trigger_us',None);progress.update('完整空头episode最早保护退出时点',i+1,len(episodes),'持仓');assert time.monotonic()-started<180 and resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024<800000000
worst=[stamp(v['date']) for v in json.loads((ROOT/'reports/SHORT_REBOUND_TIMING_20261006_V1.json').read_bytes())['days']];covered=[]
for day in worst:
 held=[z for z in episodes if z['first_fill_us']<day and z['actual_flat_us']>day]
 covered.append(dict(date=datetime.fromtimestamp(day/1e6,UTC).date().isoformat(),actual_episode_symbols=[z['symbol'] for z in held],earlier_CE_trigger_symbols=[z['symbol'] for z in held if z['first_public_trailing_trigger_us'] is not None and z['first_public_trailing_trigger_us']<day],scope='ORIGINAL_POSITION_TRAJECTORY_SHADOW_TRIGGER; NEW_CE_WALLET_OR_REENTRY_NOT_EVALUATED'))
out=ROOT/'reports/SHORT_CHANDELIER_EPISODE_TRACE_20261006_V1.json';assert not out.exists();out.write_text(json.dumps(dict(status='PASS_FULL_RECORDED_EPISODE_CAUSAL_CE_TRACE_NOT_ECONOMIC_REPLAY',task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(__file__),producer_sha256=sha(p),public_rule=RULES,adapter='SHORT_STOP_RATCHETS_MIN_OF_CLOSED_DAILY_CE_DURING_RECORDED_EPISODE; FIRST_FULL_MINUTE_AFTER_FILL; TRADE_CLOSE_OBSERVATION_NEXT_DELAYED_OPEN_REQUIRED',episodes=episodes,worst_day_earlier_triggers=covered,new_accounts=0,new_net_return='NOT_RUN',fits=0,limitation='EARLIER_TRIGGER_NOT_A_NEW_ECONOMIC_ACCOUNT; CANNOT_KEEP_OLD_GROSS_PNL_AFTER_REMOVING_TRADES; FIVE_DAY_RAW_LINE_PROBE_DOES_NOT_TEST_FULL_CHANDELIER_STRATEGY'),indent=2,ensure_ascii=False,allow_nan=False)+'\n');progress.stop.set();progress.thread.join(timeout=3);print(json.dumps(dict(episodes=len(episodes),triggered=sum(z['first_public_trailing_trigger_us'] is not None for z in episodes),worst_day_earlier_triggers=covered)))