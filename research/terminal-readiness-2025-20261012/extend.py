"""Finite exit scheduling only; all finance uses the original validated account."""
import argparse,gzip,json,time
from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import numpy as np
from common import HERE,ROOT,START,END,MINUTE,ARMS,SYMBOLS,parent,account_api,git,sha,digest,save
from quant.execution_contract import ExecutionContractV2
from quant.perpetual_account import HALTS

def extend(account,rows,events,previous_quote,namespace):
 assert account.clock_us==START and namespace.startswith('TERMINAL60_2026JAN1_')
 assert all(START<=r['event_us']<=END for r in events) and events==sorted(events,key=lambda r:(r['event_us'],r['symbol']))
 assert len({(r['symbol'],r['event_us']) for r in events})==len(events)
 before=account.summary();historical=deepcopy(account.snapshot());oldtrades=len(account.trades);oldfund=len(account.funding);requests=[];observations=[];trace=[];cursor=0;previous=deepcopy(previous_quote);owned=[s for s in account.symbols if account.positions[s].quantity]
 status='STOP_60MIN_DEADLINE_RESIDUAL';stop=START;peak=before['NAV'];mdd=0.;risk=[]
 def observe(at,cause):
  nonlocal peak,mdd
  r=account.summary();peak=max(peak,r['NAV']);mdd=max(mdd,1-r['NAV']/peak)
  observations.append(dict(event_us=int(at),cause=cause,NAV=r['NAV'],gross=r['gross_notional'],status=account.status))
  if account.status!='ACTIVE':risk.append(dict(event_us=int(at),cause=cause,status=account.status,halt=deepcopy(account.halt_witness),gross=r['gross_notional']))
 def fund(limit,inclusive):
  nonlocal cursor
  while cursor<len(events):
   row=events[cursor];at=row['event_us']
   if at>limit or not inclusive and at==limit:break
   assert f"{row['symbol']}:{at}" not in account.funding_events,'Boundary funding must not replay'
   observe(at,'BEFORE_ACTUAL_FUNDING');account.apply_funding(row['symbol'],f"{row['symbol']}:{at}",at,D(str(row['raw_rate'])),at);observe(at,'AFTER_ACTUAL_FUNDING');cursor+=1
   if account.status in HALTS:break
 for i,(at,row) in enumerate(rows):
  assert i<60 and at==START+i*MINUTE and set(row)==set(account.symbols)
  assert all(np.isfinite([r['open'],r['mark'],r['quote_volume']]).all() and r['open']>0 and r['mark']>0 and r['quote_volume']>=0 for r in row.values()),'Actual complete hour values required'
  fund(at+1,True)
  if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop=account.clock_us;break
  if at+1>=ExecutionContractV2().earliest_execution_us(START)+1:
   for s in owned:
    q=account.positions[s].quantity
    if not q:continue
    cap=D(str(previous[s]))*D('.001')/D(str(row[s]['open']));key=f'{namespace}:{s}:{at}';assert key not in account.fill_requests
    receipt=account.execute_fill(s,'SELL' if q>0 else 'BUY',abs(q),at+1,START,key,execution_mid_price=D(str(row[s]['open'])),quote_available_us=at,available_quantity=cap,reduce_only=True)
    requests.append(dict(fill_id=key,symbol=s,event_us=at+1,signal_us=START,previous_quote_volume=str(D(str(previous[s]))),previous_quote_available_us=at,current_open=str(D(str(row[s]['open']))),capacity_quantity=str(cap),quantity_before=str(q),quantity_after=str(account.positions[s].quantity),receipt=receipt));observe(at+1,'AFTER_PAID_REDUCE_ONLY')
    assert account.positions[s].quantity*q>=0 and abs(account.positions[s].quantity)<=abs(q),'No flip or increase'
    if account.status in HALTS:break
  if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop=account.clock_us;break
  fund(at+MINUTE,False)
  if account.status in HALTS:status='STOP_ACCOUNT_HALT';stop=account.clock_us;break
  account.update_marks(at+MINUTE,{s:dict(price=D(str(r['mark'])),close_us=at+MINUTE,available_us=at+MINUTE) for s,r in row.items()});observe(at+MINUTE,'CAUSALLY_COMPLETED_MARK');fund(at+MINUTE,True)
  current=account.summary();trace.append(dict(close_us=at+MINUTE,summary=current));previous={s:r['quote_volume'] for s,r in row.items()};stop=at+MINUTE
  if account.status in HALTS:status='STOP_ACCOUNT_HALT';break
  if all(p.quantity==0 for p in account.positions.values()):status='PASS_PAID_FLAT_WITHIN_60MIN';break
 after=account.summary();now=account.snapshot()
 assert all(now['fill_requests'][k]==v for k,v in historical['fill_requests'].items()) and all(now['funding_events'][k]==v for k,v in historical['funding_events'].items())
 assert account.trades[:oldtrades]==historical['trades'] and account.funding[:oldfund]==historical['funding']
 assert all(r['leg']=='CLOSE' and not r.get('liquidation_takeover') for r in account.trades[oldtrades:])
 assert all(sum(r['symbol']==s for r in requests)<=59 for s in owned)
 exact=lambda k:float(D(after['decimal_strings'][k])-D(before['decimal_strings'][k]));paid=all(p.quantity==0 for p in account.positions.values())
 return dict(status=status,start_us=START,maximum_end_us=END,actual_end_us=stop,minutes=len(trace),paid_flat=paid,before=before,after=after,short_tail_marked_increment_USDT=exact('NAV'),short_tail_paid_increment_USDT=exact('NAV') if paid else None,extended_paid_total_net_USDT=after['NAV']-10000 if paid else None,old_annual_result_unchanged=True,fees_paid_USDT=exact('fees_USDT'),execution_paid_USDT=exact('execution_cost_USDT'),funding_cash_USDT=exact('funding_USDT'),new_trades=account.trades[oldtrades:],new_funding=account.funding[oldfund:],requests=requests,observations=observations,minute_trace=trace,risk_observations=risk,available_event_tail_drawdown=mdd,actual_funding_events_applied=cursor,historical_fill_request_maps_preserved=True,new_request_namespace=namespace,financial_scope='EXIT_READINESS_ALREADYSEEN_NOT_NEW_MODEL_OOS_OR_ANNUAL_RETURN')

def run(state,science):
 assert not state.exists() and not git('status','--porcelain') and git('rev-parse','HEAD').decode().strip()==science
 for line in (HERE/'FINANCIAL_SHA256.txt').read_text().splitlines():h,p=line.split(maxsplit=1);assert sha(ROOT/p)==h,p
 state.mkdir(parents=True);began=time.monotonic();Closing,_=account_api();source=json.loads((HERE/'source/SOURCE_INDEX.json').read_text())
 assert sha(HERE/'source/INPUTS.npz')==source['INPUTS_SHA256'] and sha(HERE/'source/EVENTS.json')==source['EVENTS_SHA256']
 with np.load(HERE/'source/INPUTS.npz',allow_pickle=False) as z:
  times=z['times'];assert tuple(z['symbol_order'])==SYMBOLS;np.testing.assert_array_equal(times,np.arange(START,END,MINUTE));market={s:{k:z[s+'_'+k] for k in ('open','close','quote_volume','mark')} for s in SYMBOLS}
 events=json.loads((HERE/'source/EVENTS.json').read_text());reports={}
 for arm in ARMS:
  case=state/arm;case.mkdir();snap,body,proof=parent(arm);account=Closing.from_snapshot(snap['account']);assert account.snapshot()==snap['account']
  for k,v in account.summary().items():assert body['summary'][k]==v,k
  def rows():
   for i,at in enumerate(times):yield int(at),{s:{k:float(v[i]) for k,v in fields.items()} for s,fields in market.items()}
  start=time.monotonic();r=extend(account,rows(),events,snap['state']['previous_quote'],'TERMINAL60_2026JAN1_'+arm);r.update(arm=arm,parent_proof=proof,science_source_commit=science,source_INDEX_SHA256=sha(HERE/'source/SOURCE_INDEX.json'),source_INPUTS_SHA256=sha(HERE/'source/INPUTS.npz'),protocol_SHA256=sha(HERE/'PROTOCOL.json'),seconds=time.monotonic()-start,new_short_tail_forks=1,old_annual_wallet_replays=0,new_model_fits=0,provider_downloads=0)
  raw=json.dumps(account.snapshot(),sort_keys=True,separators=(',',':'),allow_nan=False).encode();p=case/'FINAL_ACCOUNT.json.gz';p.write_bytes(gzip.compress(raw,mtime=0));r['final_snapshot_SHA256']=sha(p);r['final_account_state_SHA256']=digest(raw);save(case/'TAIL.json',r)
  audit=__import__('common').load('unchanged_tail_inventory_NAV_audit',ROOT/'research/short-native-activity-20261012/activity.py');_,q=audit.episodes(account.trades,SYMBOLS)
  for s in SYMBOLS:assert q[s]==account.positions[s].quantity
  prices={s:float(account.marks[s][-1]['price']) for s in SYMBOLS};r['independent_decimal_NAV_bridge']=audit.nav_bridge(account.trades,account.funding,q,prices,account.nav());r['inventory_NAV_audit']='PASS';save(case/'TAIL.json',r)
  reports[arm]={k:r[k] for k in ('status','paid_flat','minutes','before','after','short_tail_marked_increment_USDT','short_tail_paid_increment_USDT','extended_paid_total_net_USDT','fees_paid_USDT','execution_paid_USDT','funding_cash_USDT','final_snapshot_SHA256','final_account_state_SHA256','seconds')}
  assert time.monotonic()-start<120 and sum(p.stat().st_size for p in state.rglob('*') if p.is_file())<100000000
  print('ACTUAL_60MIN_EXIT_RESULT',arm,r['status'],r['minutes'],r['after']['gross_notional'],r['short_tail_marked_increment_USDT'],flush=True)
 save(state/'RESULT.json',dict(cases=reports,scientific_rule_attempts=1,new_short_tail_forks=3,annual_wallet_replays=0,new_fits=0,provider_downloads=0,seconds=time.monotonic()-began));print('ACTUAL_ALL_THREE_SHORT_TAILS_COMPLETE',time.monotonic()-began,flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--source-commit',required=True);a=p.parse_args();run(a.state,a.source_commit)
