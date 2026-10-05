"""Read-only short episode attribution from saved actual fills and funding.

Entry-state grouping is descriptive; never remove fills/costs or claim a new return.
"""
import json,hashlib,os
from pathlib import Path
from collections import defaultdict
from datetime import UTC,datetime
import polars as pl
from quant.paths import ROOT,STATE
from quant import resources
from scripts.research_v7.oracle_flow_ceiling import Progress

def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 out=ROOT/'reports/fast_research/SHORT_ENTRY_MECHANISM_20261006_V1.json';assert not out.exists()
 path=ROOT/'reports/fast_research/CTA_TWO_SPEED_BASE27_20261005_V1.json';r=json.loads(path.read_bytes());symbols=r['protocol']['symbols']
 signals=STATE/'d094-two-speed-base27-20261005-v1/frozen_signals.parquet';signal={(v['close_us'],v['symbol']):v for v in pl.read_parquet(signals).iter_rows(named=True)}
 states=r['descriptive_past_states'];progress=Progress();progress.value['detail']='实际旧空头成交episode归因；不是删除交易后的回测'
 result=dict(status='PASS_READ_ONLY_SHORT_EPISODE_RECONCILIATION',created_utc=datetime.now(UTC).isoformat(),task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__),producer_sha256=sha(path),signal_sha256=sha(signals),cases=[],fit=0,new_accounts=0,funding_interpretation='RAW_AS_PERCENT_UNKNOWN_DIAGNOSTIC_ONLY',hypothesis_before_read='SEPARATE_FAST_ONLY_SLOW_ONLY_BOTH_SHORT_ENTRY_AND_REBOUND_LOSSES; USE_PRIOR_SIGNALS_ONLY; NO_RECIPE_SEARCH',limitation='ENTRY_BUCKET_ASSOCIATION_NOT_CAUSAL; NOT_A_FILTERED_RETURN_OR_UNSEEN; OPEN_EPISODES_INCLUDE_TERMINAL_MARKED_NOTIONAL')
 for i,mode in enumerate(('LONG_SHORT','SHORT_ONLY')):
  c=next(v for v in r['cases'] if v['mode']==mode and v['unit']=='RAW_AS_PERCENT');episodes=[];active={}
  for k in ('trades.parquet','funding.parquet','minute_nav_inventory.parquet'):
   assert sha(c['artifacts'][k]['path'])==c['artifacts'][k]['sha256']
  trades=pl.read_parquet(c['artifacts']['trades.parquet']['path']).to_dicts();fund=pl.read_parquet(c['artifacts']['funding.parquet']['path']).to_dicts()
  events=sorted([(v['event_us'],1,'TRADE',v) for v in trades]+[(v['event_us'],0,'FUNDING',v) for v in fund],key=lambda x:x[:2])
  for t,_,kind,v in events:
   s=v['symbol']
   if kind=='FUNDING':
    if v['quantity']<0:
     assert s in active;active[s]['funding']+=v['signed_funding_USDT']
    continue
   before,after=v['quantity_before'],v['quantity_after'];assert before*after>=0,'Reversal must be split'
   if before>=0 and after>=0:continue
   if before==0 and after<0:
    key=(v['signal_us'],s);sig=signal[key];f20=sig['DONCHIAN20_10'];f55=sig['DONCHIAN55_20']
    bucket='BOTH_SHORT' if f20<0 and f55<0 else 'FAST_ONLY' if f20<0 else 'SLOW_ONLY' if f55<0 else 'UNKNOWN'
    assert s not in active
    ep=dict(symbol=s,start_us=t,signal_us=v['signal_us'],entry_bucket=bucket,entry_regime=states[str(v['signal_us'])],cashflow_mid=0.,fees=0.,execution=0.,funding=0.,fills=0,peak_abs_quantity=0.,closed=False)
    active[s]=ep;episodes.append(ep)
   ep=active[s];ep['cashflow_mid']-=v['position_delta']*v['mid_price'];ep['fees']+=v['fee_USDT_mid'];ep['execution']+=v['execution_cost'];ep['fills']+=1;ep['peak_abs_quantity']=max(ep['peak_abs_quantity'],abs(after))
   if after==0:ep.update(closed=True,end_us=t);del active[s]
  terminal=pl.scan_parquet(c['artifacts']['minute_nav_inventory.parquet']['path']).tail(1).collect().to_dicts()[0]
  for s,ep in active.items():ep.update(end_us=terminal['close_us'],terminal_signed_marked_notional=terminal[s+'_signed_marked_notional']);assert terminal[s+'_quantity']<0
  for ep in episodes:
   ep['gross']=ep['cashflow_mid']+ep.get('terminal_signed_marked_notional',0.);ep['net']=ep['gross']+ep['funding']-ep['fees']-ep['execution']
  expected=c['summary']['long_short_marked_contribution']['SHORT']['net_contribution'];assert abs(sum(v['net'] for v in episodes)-expected)<1e-7
  groups={}
  for label,keys in [('entry_confirmation',('entry_bucket',)),('entry_regime',('entry_regime',)),('confirmation_x_regime',('entry_bucket','entry_regime'))]:
   agg={}
   for ep in episodes:
    key='/'.join(ep[k] for k in keys);z=agg.setdefault(key,dict(episodes=0,closed=0,gross=0.,fees=0.,execution=0.,funding=0.,net=0.,winning=0,worst_net=0.))
    z['episodes']+=1;z['closed']+=ep['closed'];z['winning']+=ep['net']>0;z['worst_net']=min(z['worst_net'],ep['net'])
    for k in ('gross','fees','execution','funding','net'):z[k]+=ep[k]
   groups[label]=agg
  result['cases'].append(dict(mode=mode,actual_short_net=expected,reconciled_episode_net=sum(v['net'] for v in episodes),groups=groups,episodes=episodes,artifacts=c['artifacts']))
  progress.update('已保存空头成交与NAV归因核对',i+1,2,'账户')
 result['resources']=resources.status();out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n');progress.stop.set();progress.thread.join(timeout=3)
 print(json.dumps({v['mode']:v['groups'] for v in result['cases']},ensure_ascii=False))
if __name__=='__main__':main()
