"""Read-only short loss timing, matched to recorded fills and actual source prices."""
import json,hashlib,os
from pathlib import Path
from datetime import UTC,datetime
import polars as pl
from quant.paths import ROOT,STATE
from scripts.research_v7.oracle_flow_ceiling import Progress
DAY=86400000000;MINUTE=60000000

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def ts(s):return int(datetime.fromisoformat(s).replace(tzinfo=UTC).timestamp())*1000000
p=ROOT/'reports/fast_research/SHORT_CONFIRMATION_BASE27_20261006_V1.json';raw=json.loads(p.read_bytes());case=next(c for c in raw['cases'] if c['unit']=='RAW_AS_PERCENT');symbols=raw['protocol']['symbols']
mp=Path(raw['protocol']['data_manifest']['path']);assert sha(mp)==raw['protocol']['data_manifest']['sha256'];manifest=json.loads(mp.read_bytes())
diagnostic=ROOT/'reports/SHORT_SELECTION_ATTRIBUTION_20261006_V1.json';diagnostic_v=json.loads(diagnostic.read_bytes());days=diagnostic_v['cases'][1]['BEAR_worst5_days'];assert len(days)==5
for k in ('minute_nav_inventory.parquet','trades.parquet','funding.parquet'):assert sha(case['artifacts'][k]['path'])==case['artifacts'][k]['sha256']
nav=pl.scan_parquet(case['artifacts']['minute_nav_inventory.parquet']['path']);trades=pl.read_parquet(case['artifacts']['trades.parquet']['path']);fund=pl.read_parquet(case['artifacts']['funding.parquet']['path'])
source={};inputs={};progress=Progress();out=ROOT/'reports/SHORT_REBOUND_TIMING_20261006_V1.json';assert not out.exists()
result=dict(status='PASS_SAVED_SHORT_DAILY_PNL_AND_EXIT_TIMING_DIAGNOSTIC',task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),source_sha256=sha(__file__),producer_sha256=sha(p),manifest_sha256=sha(mp),diagnostic_sha256=sha(diagnostic),hypothesis_before_read='CHECK_WHETHER_PRIOR10_DAY_SHORT_EXIT_WAS_CROSSED_INTRADAY_BEFORE_DAILY_CONFIRMATION; DO_NOT_ASSUMe_FASTER_SAME_CHANNEL_EXITS_HELP_IF_LINE_NEVER_CROSSED',account_replays=0,fits=0,days=[],limitations=['POST_RESULT_WORST5_DATE_DIAGNOSTIC_NOT_A_FILTERED_RETURN_OR_NEW_SUCCESS_GATE','PAST_BTC_STATE_NOT_ASSET_REGIME','SIGNAL_AND_MARK_CLOCK_SEPARATED_FROM_ACTUAL_TRADE_CLOSE','MID_CASHFLOW_ONLY_A_PNL_IDENTITY_NOT_SHORT_SALE_INVESTABLE_CASH'])
for di,day in enumerate(days):
 begin=ts(day['date']);end=begin+DAY;snaps=nav.filter(pl.col('close_us').is_in([begin,end])).collect().to_dicts();assert len(snaps)==2;snaps=sorted(snaps,key=lambda x:x['close_us']);values=[]
 for s in symbols:
  fills=trades.filter((pl.col('symbol')==s)&(pl.col('event_us')>begin)&(pl.col('event_us')<=end)&((pl.col('quantity_before')<0)|(pl.col('quantity_after')<0)))
  funding=fund.filter((pl.col('symbol')==s)&(pl.col('event_us')>begin)&(pl.col('event_us')<=end)&(pl.col('quantity')<0))
  before=min(0.,snaps[0][s+'_signed_marked_notional']);after=min(0.,snaps[1][s+'_signed_marked_notional']);gross=-(fills['position_delta']*fills['mid_price']).sum()+after-before;fee=fills['fee_USDT_mid'].sum();execution=fills['execution_cost'].sum();signed_funding=funding['signed_funding_USDT'].sum();net=gross+signed_funding-fee-execution
  if before==after==0 and fills.is_empty():continue
  month=day['date'][:7]
  for record in manifest['market_records']:
   if record['symbol']==s and record['kind']=='klines' and record['month'] in ('2025-03','2025-04'):
    key=record['normalized_path']
    if key not in inputs:assert sha(key)==record['normalized_sha256'];inputs[key]=record['normalized_sha256']
    if (s,record['month']) not in source:source[(s,record['month'])]=pl.read_parquet(key).select('open_us','close_us','available_us','open','close','high','low')
  bars=pl.concat([source[(s,m)] for m in ('2025-03','2025-04')]).sort('open_us');past=bars.filter((pl.col('close_us')<=begin)&(pl.col('available_us')<=begin)&(pl.col('open_us')>=begin-10*DAY));assert past.height==14400
  prior10high=past['high'].max();today=bars.filter((pl.col('open_us')>=begin)&(pl.col('close_us')<=end));assert today.height==1440
  crossed=today.filter(pl.col('close')>prior10high);cross=int(crossed['close_us'][0]) if crossed.height else None
  post=trades.filter((pl.col('symbol')==s)&(pl.col('event_us')>begin)&(pl.col('quantity_before')<0)&(pl.col('quantity_after')==0)).sort('event_us');flat=post.to_dicts()[0] if post.height else None
  q0=snaps[0][s+'_quantity'];q1=snaps[1][s+'_quantity'];values.append(dict(symbol=s,gross=gross,fees=fee,execution=execution,funding=signed_funding,net=net,start_short_quantity=min(0.,q0),end_short_quantity=min(0.,q1),trade_close_return=today['close'][-1]/today['open'][0]-1,prior10_day_high=prior10high,first_closed_minute_above_existing_short_exit_us=cross,actual_next_flat=flat,trade_price_max=today['high'].max(),short_fill_count=fills.height,scope='EXISTING_DAILY_PRIOR10_LINE_DIAGNOSTIC; NOT_A_NEW_EXIT_REPLAY'))
 assert abs(sum(v['net'] for v in values)-day['SHORT'])<1e-7
 result['days'].append(dict(date=day['date'],actual_SHORT=day['SHORT'],reconciled_SHORT=sum(v['net'] for v in values),assets=values));progress.update('空头亏损日退出时点核对',di+1,5,'日期')
result['actual_source_hashes']=inputs;out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n');progress.stop.set();progress.thread.join(timeout=3)
print(json.dumps([dict(date=d['date'],SHORT=d['actual_SHORT'],assets=[{k:v[k] for k in ('symbol','net','trade_close_return','first_closed_minute_above_existing_short_exit_us','start_short_quantity','end_short_quantity')} for v in d['assets']]) for d in result['days']]))