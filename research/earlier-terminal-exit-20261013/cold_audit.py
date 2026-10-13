"""One bounded, zero-financial-advance observer per fixed terminal60 wallet."""
from __future__ import annotations
import sys,json,hashlib,os,resource
from pathlib import Path
from decimal import Decimal as D
H=Path(__file__).resolve().parent;R=H.parent
from freeze_terminal import verify
from preflight_terminal import bindings,require_publication

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def same(a,b,label):
 if a!=b:raise ValueError('Cold terminal60 mismatch: '+label)

def main(case_id,state_root):
 verify(require_review=True);require_publication()
 if sys.flags.optimize or len(os.sched_getaffinity(0))!=1 or any(not 0<n<=4_000_000_000 for n in resource.getrlimit(resource.RLIMIT_AS)) or any(not 0<n<=300 for n in resource.getrlimit(resource.RLIMIT_CPU)):
  raise RuntimeError('One CPU, finite4GB-AS/300sec-CPU observer required')
 import numpy as np
 from run_cases import guard
 plan=bindings();case=next((c for c in plan['cases'] if c['case_id']+'_FINE_ORIGINAL'==case_id),None)
 if case is None:raise ValueError('Case outside exact two-arm plan')
 state=Path(state_root).resolve()
 if state.parent!=H or not state.name.startswith('state') or state.is_symlink():raise ValueError('Foreign state root')
 receipts=read(state/'RESOURCE_RECEIPTS.json');same(receipts['status'],'ALL_CASES_FINISHED','controller')
 expected={c['case_id']+'_FINE_ORIGINAL' for c in plan['cases']}
 same(set(receipts['per_case']),expected,'two-arm population');same(receipts['unstarted_case_ids'],[],'unstarted')
 if any(r['exit_code'] or r['stop_reason'] for r in receipts['per_case'].values()):raise ValueError('Unclean controller')
 run=read(state/'RUN_BINDING.json');same(run['runner_SHA256'],sha(H/'run_cases.py'),'run code');same(run['freeze_manifest_SHA256'],sha(H/'FROZEN_CODE.json'),'freeze')
 port,source,_=guard.load_port(2025)
 sys.path.insert(0,str(R/'coin_quantity_resolution_20261013'))
 from fine_account import FineGridAccount
 from terminal_adapter import EarlierTerminalSimulator
 p=state/case_id;binding=read(p/'BINDING.json');saved=read(p/'ACCOUNT.json');result=read(p/'RESULT.json')
 same(binding['run_binding_SHA256'],sha(state/'RUN_BINDING.json'),'controller binding')
 same(binding['terminal_adapter_SHA256'],sha(H/'terminal_adapter.py'),'adapter')
 same(binding['target_array_SHA256'],case['target_array_SHA256'],'target')
 same(binding['terminal_signal_us'],source['end']-61*60_000_000,'signal')
 snapshot,pointer=port.restore_snapshot(p/'recovery',binding)
 original=EarlierTerminalSimulator.advance_day
 def forbidden(*args,**kwargs):raise RuntimeError('Cold observer cannot advance finance')
 EarlierTerminalSimulator.advance_day=forbidden
 try:
  sim=EarlierTerminalSimulator.from_snapshot(snapshot,source,account_class=FineGridAccount)
  same(sim.state_hash(),pointer['state_hash'],'state hash');same(sim.state_hash(),result['genuine_state_hash'],'result state')
  output=sim.result()
 finally:EarlierTerminalSimulator.advance_day=original
 same(output['summary'],saved['summary'],'summary')
 for key in ('trades','funding','rejections','breaches','extrema','target_meta'):same(output[key],saved[key],key)
 same(output['targets'].to_dicts(),saved['targets'],'targets');same(port.fingerprint(output['minute']),read(p/'MINUTE_NUMERIC.json')['columns'],'numeric bits')
 same(sim.rows_written,result['completed_minutes'],'minutes')
 _,inventory=port.native.episodes(output['trades'],tuple(source['symbols']))
 for symbol in source['symbols']:same(inventory[symbol],sim.account.positions[symbol].quantity,'signed inventory '+symbol)
 bridge=port.native.nav_bridge(output['trades'],output['funding'],inventory,output['summary']['terminal_mark_prices'],sim.account.nav())
 same(bridge,result['independent_decimal_NAV_bridge'],'Decimal NAV')
 full=sim.rows_written==525600;paid=full and sim.completion=='COMPLETE_CONDITIONAL_ACCOUNT' and all(q==0 for q in inventory.values())
 same(result['full_calendar'],full,'full');same(result['paid_flat'],paid,'paid-flat');same(result['paid_cash_PnL_USDT'],output['summary']['net_PnL'] if paid else None,'paid cash')
 # Compare all observed numeric rows before first changed execution. Source cache
 # decoding during native restoration is not a financial replay.
 old=R/case['baseline_state_local_locator'];oldptr=read(old/'recovery/POINTER.json');same(len(oldptr['chunks']),365,'old calendar')
 prefix=525600-60;checked=0
 for row,new in zip(oldptr['chunks'],sim.minute_chunks):
  take=min(len(new),prefix-checked)
  if take<=0:break
  op=old/'recovery'/row['path'];same(sha(op),row['SHA256'],'old lossless chunk')
  with np.load(op,allow_pickle=False) as a:np.testing.assert_array_equal(a['minute_chunk'][:take],new[:take])
  checked+=take
 same(checked,prefix,'complete pre-intervention prefix')
 oldaccount=read(old/'ACCOUNT.json');first=source['end']-60*60_000_000+1
 for key in ('trades','funding'):
  same([x for x in output[key] if x['event_us']<first],[x for x in oldaccount[key] if x['event_us']<first],'unchanged '+key+' prefix')
 gate=read(H/'TERMINAL_QUOTE_GATE.json');signal=source['end']-61*60_000_000;term=[t for t in output['trades'] if t['signal_us']==signal]
 for f in term:
  n=(f['event_us']-1-(source['end']-60*60_000_000))//60_000_000
  if not 0<=n<60 or f['leg']!='CLOSE':raise ValueError('Terminal clock/reduce-only violation')
  g=gate['symbols'][f['symbol']];cap=D(str(g['quote_volume'][n]))*D('.001')/D(str(g['open_prices'][n+1]))
  d=f['decimal_strings']
  if D(d['quantity'])>cap or abs(D(d['quantity_after']))>abs(D(d['quantity_before'])) or D(d['quantity_after'])*D(d['quantity_before'])<0:raise ValueError('Terminal capacity/inventory violation')
 # Every terminal fill request, including rejected attempts, carries the same
 # true previous-minute capacity and distinct event clocks. No same-minute loop.
 req={s:[] for s in source['symbols']}
 for val in sim.account.snapshot()['fill_requests'].values():
  x=val['identity']
  if x['signal_us']!=signal:continue
  n=(x['event_us']-1-(source['end']-60*60_000_000))//60_000_000
  if not 0<=n<60 or x['reduce_only'] is not True:raise ValueError('Terminal request clock/reduce-only')
  g=gate['symbols'][x['symbol']];cap=D(str(g['quote_volume'][n]))*D('.001')/D(str(g['open_prices'][n+1]))
  same(D(x['available_quantity']),cap,'prior quote capacity');req[x['symbol']].append(x['event_us'])
 for s,times in req.items():
  if len(times)>60 or len(times)!=len(set(times)):raise ValueError('Duplicate/excess terminal attempts')
 receipt=dict(status='PASS_ZERO_ADVANCE_COLD_RESTORE_AND_IDENTICAL_PRE_EXIT_PREFIX',case_id=case_id,financial_advances=0,new_historical_wallets=0,
  pre_intervention_numeric_minutes_checked=checked,entire_observed_numeric_fingerprint=read(p/'MINUTE_NUMERIC.json')['columns'],
  terminal_fill_count=len(term),terminal_request_count_by_symbol={s:len(t) for s,t in req.items()},terminal_real_clock_max=60,
  baseline_result_SHA256=sha(old/'RESULT.json'),new_result_SHA256=sha(p/'RESULT.json'),genuine_state_hash=sim.state_hash(),independent_decimal_NAV_bridge=bridge)
 out=H/'receipts';out.mkdir(exist_ok=True)
 with (out/(case_id+'.json')).open('x') as f:json.dump(receipt,f,indent=2,sort_keys=True);f.write('\n')
 print(json.dumps(receipt,indent=2))
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
