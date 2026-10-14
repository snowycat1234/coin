"""Frozen, generated-only finite prefix parity; never dispatches a source case."""
import sys
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and sys.flags.optimize==0):
 raise RuntimeError('ISOLATED_NO_SITE_NO_BYTECODE_ASSERTIONS_ENABLED_REQUIRED')
from pathlib import Path
import ast,cProfile,dataclasses,gzip,hashlib,importlib.machinery,json,math,os,pstats,resource,tempfile,time,traceback,types
from copy import deepcopy
from decimal import Decimal as D,localcontext
BASE=Path(__file__).resolve().parent;ROOT=BASE.parent;OUT=BASE/'generated_finite_prefix_attempt001'
PIN=sys.argv[1];STARTED=time.monotonic();NPZ_OPENS=[];RESULTS=[];WITNESSES=[]
KNOWN_NPZ={(ROOT/'coin_h090_finite_native_20261014/dependencies/repo/research/static50-sma-20261013/input'/n).resolve() for n in ('Y2023.npz','Y2025.npz')}
def sha(raw):return hashlib.sha256(raw).hexdigest()
def normal(x):
 if dataclasses.is_dataclass(x):return normal(dataclasses.asdict(x))
 if isinstance(x,D):return str(x)
 if isinstance(x,dict):return {str(k):normal(v) for k,v in x.items()}
 if isinstance(x,(list,tuple)):return [normal(v) for v in x]
 if isinstance(x,set):return sorted(normal(v) for v in x)
 return x
def canonical(x):return json.dumps(normal(x),sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def save(name,x,compressed=False):
 raw=canonical(x)+b'\n';raw=gzip.compress(raw,mtime=0) if compressed else raw
 with (OUT/name).open('xb') as f:f.write(raw)
 return {'file':name,'SHA256':sha(raw),'bytes':len(raw)}
def exact(a,b,label):
 if normal(a)!=normal(b) or canonical(a)!=canonical(b):
  save('MISMATCH_'+label+'.json.gz',{'baseline':a,'prefix':b},True)
  raise AssertionError('EXACT_PARITY_MISMATCH:'+label)
def audit(event,args):
 if event in ('socket.connect','subprocess.Popen','os.system'):raise RuntimeError('NO_NETWORK_OR_CHILDREN_IN_GENERATED_WORKER')
 if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
 p=Path(os.fsdecode(args[0])).resolve()
 if p.suffix.lower() in ('.npz','.npy','.parquet','.csv') and not p.is_relative_to(OUT):
  if p not in KNOWN_NPZ:raise RuntimeError('EXTERNAL_ARRAY_READ_REFUSED:'+str(p))
  f=sys._getframe(1);chain=[]
  while f is not None and len(chain)<16:chain.append(f.f_code.co_name);f=f.f_back
  if not any(n in ('sha','file_sha','bytes','check') for n in chain):raise RuntimeError('NPZ_CHECKSUM_ONLY_REQUIRED')
  NPZ_OPENS.append({'path':str(p.relative_to(ROOT)),'callers':chain})
sys.addaudithook(audit)
def bootstrap():
 raw=(BASE/'PREPARATION_MANIFEST.json').read_bytes();assert sha(raw)==PIN
 for n,w in json.loads(raw)['files'].items():
  b=(BASE/n).read_bytes();assert sha(b)==w['SHA256'] and len(b)==w['bytes'],n
 p=BASE/'verified_source.py';m=types.ModuleType('verified_source');m.__file__=str(p)
 m.__spec__=importlib.machinery.ModuleSpec('verified_source',loader=None,origin=str(p));sys.modules['verified_source']=m
 exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__);rt=m.install(PIN,'generated')
 import bridge_runtime_locator
 rt.runtime_packages=bridge_runtime_locator.configure_runtime()
 global O,A,P,K,N,F,T,B,BTC,BASE_OWNER,FINITE,Z
 import original_bridge as O
 import accepted_original_bridge as A
 import preview_prefix as P
 import preview_callers as K
 import native_control as N
 import generated_fixtures as F
 import test_bridge as T
 import bridge_bindings as B
 from owner_ledger import BTC,BASE as BASE_OWNER,FINITE,Z
 import numpy as np
 return rt,np

def owners(s):
 return {'ledger':s.owners.snapshot(),'program':deepcopy(vars(s.program)),'budget':deepcopy(vars(s.program_budget)),
  'pending':deepcopy(s.program_pending),'activated':s.program_activated,'activation_signal':s.program_activation_signal,
  'reservations':deepcopy(vars(s.reservations)),'events':deepcopy(s.owner_events),
  'authorizations':deepcopy(s._program_order_authorizations),'signal_marks':deepcopy(s._program_signal_mark_evidence),
  'bindings':deepcopy(s._fill_owner),'trade_cursor':s._trade_cursor,'funding_cursor':s._funding_cursor,
  'processed_native_receipts':deepcopy(s.processed_native_receipts)}
def full(s):
 snapshot=s.snapshot()
 return {'scheduler':snapshot,'account':s.account.snapshot(),'owners':owners(s)}
def compare(pair,label,retain=False):
 a,b=map(full,pair);exact(a,b,label)
 for s in pair:
  assert type(s.account).__name__=='OwnerRoutedAccount'
  assert all(type(v) is dict for v in s._program_order_authorizations.values())
  assert type(s.owners.fill_allocations) is list and all(type(v) is dict for v in s.owners.fill_allocations)
 if retain:WITNESSES.append(save(label+'_full_pair.json.gz',{'baseline':a,'prefix':b},True))
 return a

def unused_tool(label):
 for i in (4,3,0,1,5,2):
  if sys.monitoring.get_tool(i) is None:sys.monitoring.use_tool_id(i,label);return i
 raise RuntimeError('NO_FREE_MONITORING_SLOT')
def pair(bundle,recipe=False):
 data=T.admitted(bundle,recipe=recipe);a=A.make_sim(data,'FINITE',generated=True)
 timeline=[];tool=unused_tool('finite_constructor_order')
 codes={O.OriginalPrefixFiniteCandidate.__init__.__code__:'prefix',N.NATIVE.__init__.__code__:'native',P.install_preview_histories.__code__:'install'}
 def enter(code,offset):timeline.append(['start',codes[code]])
 def leave(code,offset,result):timeline.append(['return',codes[code]])
 sys.monitoring.register_callback(tool,sys.monitoring.events.PY_START,enter)
 sys.monitoring.register_callback(tool,sys.monitoring.events.PY_RETURN,leave)
 for c in codes:sys.monitoring.set_local_events(tool,c,sys.monitoring.events.PY_START|sys.monitoring.events.PY_RETURN)
 try:b=O.make_sim(data,'FINITE',generated=True)
 finally:
  for c in codes:sys.monitoring.set_local_events(tool,c,0)
  sys.monitoring.free_tool_id(tool)
 assert timeline==[['start','prefix'],['start','native'],['return','native'],['start','install'],['return','install'],['return','prefix']],timeline
 P.validate_engine(b.account.engine)
 assert b.account.engine.clock_us==0 and b.rows_written==0 and not any(getattr(b.account.engine,n) for n in P.HISTORY_FIELDS)
 assert b.account.owner_admission.__func__ is b._atomic_owner_route_admission.__func__
 assert b.account.risk_admission.__func__ is b._atomic_owner_admission.__func__
 assert type(b.account.capital_guard) is K.PrefixCapitalGuard
 assert O.OriginalPrefixFiniteCandidate._prepare is O.OriginalH090Control._prepare
 compare((a,b),'fresh_pair_'+str(len(RESULTS))+str(len(WITNESSES)))
 return a,b

def mark(s,n,price):
 stamp=F.START+n*F.MINUTE
 s.account.update_marks(stamp,{sym:{'price':D(str(price)) if sym==BTC else D('100'),'close_us':stamp,'available_us':stamp} for sym in F.S})
 return stamp
def row(price=100):return {sym:{'open':float(price) if sym==BTC else 100.,'quote_volume':10000000.} for sym in F.S}
def prepared(weights=None):
 q=pair(F.make_generated(weights=weights or [.05,.05,0,0,0]))
 for s in q:
  s._admit_decision(F.START,None,None,None,None);mark(s,0,100);s.previous_quote=dict.fromkeys(F.S,10000000.)
  s.schedule({sym:D('10') if sym==BTC else Z for sym in F.S},F.START,'DAILY_TARGET')
  s.attempt(F.START+F.MINUTE,row())
 compare(q,'prepared_'+str(len(WITNESSES)))
 return q

def calendar_cases(np):
 from finite_fixtures import demo_bundle
 cases=[]
 gap=demo_bundle()
 for field in ('open','mark','close'):gap[0]['market'][BTC][field][120:]=55.
 cases.append(('four_adds_stop_gap',gap,False,'stop'))
 weights=[[.05,0,0,0,0],[-.05,0,0,0,0]]
 cases.append(('positive_negative_paid',F.make_generated(days=2,weights=weights),False,'short'))
 quote=np.full(2880,10000000.);quote[1439:]=0.
 cases.append(('positive_negative_unpaid',F.make_generated(days=2,weights=weights,quote=quote),False,'unpaid'))
 quote=np.full(1440,10000000.);quote[1379:]=0.;quote[1379:1382]=20000.
 cases.append(('terminal_paid_partial',F.make_generated(weights=[.05,.05,0,0,0],quote=quote),False,'terminal'))
 prices={sym:np.full(1440,100.) for sym in F.S};prices[BTC][20:]=110.
 cases.append(('positive_pnl_no_new_TP',F.make_generated(weights=[.05,.05,0,0,0],minute_prices=prices),False,'profit'))
 for name,bundle,recipe,expect in cases:
  q=pair(bundle,recipe);begin=time.monotonic();daily=[[],[]]
  for i,s in enumerate(q):
   while s.stop is None and s.cursor<s.end:daily[i].append(s.advance_day())
  exact(daily[0],daily[1],name+'_daily');compare(q,name,True);output=[]
  for mode,s in zip(('baseline','prefix'),q):
   r=s.result();matrix=r['minute'].to_numpy();assert matrix.shape[1]==37
   minute_schema={'columns':r['minute'].columns,'schema':[(n,str(dtype)) for n,dtype in r['minute'].schema.items()]}
   np.save(OUT/(name+'_'+mode+'_minute.npy'),matrix,allow_pickle=False)
   journal={k:r[k] for k in ('owner_fill_allocations','owner_funding_allocations','owner_events')}
   journal.update(native_trades=list(s.account.trades),native_funding=list(s.account.funding),scheduler_funding=s.funding_journal,rejections=s.rejections,policy=s.policy_events,target_rows=s.target_rows,targets=r['targets'].to_dicts(),summary=r['summary'])
   save(name+'_'+mode+'_outputs.json.gz',journal,True);output.append((matrix,journal,minute_schema))
  am,aj,asc=output[0];bm,bj,bsc=output[1];exact(asc,bsc,name+'_minute_column_schema');assert am.shape==bm.shape and am.dtype==bm.dtype and am.tobytes()==bm.tobytes();exact(aj,bj,name+'_all_outputs')
  s=q[1]
  if expect=='stop':assert s.program.completed_opening_orders==4 and s.program.terminal and s.owners.quantity[FINITE][BTC]==0 and s.owners.pnl(FINITE,s.account.engine)<D('-200')
  if expect=='short':
   fills=[r for r in s.account.trades if r['event_us']>=F.START+F.DAY and r['event_us']<s.terminal_signal_us]
   close=next(r for r in fills if r['leg']=='CLOSE' and s._fill_owner[r['fill_id']][0]==FINITE)
   short=next(r for r in fills if r['leg']=='OPEN' and r['side']=='SELL');assert close['event_us']<=short['event_us']
  if expect=='unpaid':assert s.owners.quantity[FINITE][BTC]>0 and not any(r['leg']=='OPEN' and r['side']=='SELL' for r in s.account.trades) and FINITE in s.reservations.reservations
  if expect=='terminal':
   assert s.program.terminal and s.owners.quantity[FINITE][BTC]>0 and not s.result()['summary']['terminal_cash_realized']
   terminal_closes=[r for r in s.account.trades if r['leg']=='CLOSE' and r['event_us']>=s.terminal_signal_us and s._fill_owner[r['fill_id']][0]==FINITE]
   assert terminal_closes and all(D(r['decimal_strings']['quantity'])>0 for r in terminal_closes)
  if expect=='profit':
   assert not any('TAKE_PROFIT' in str(r) for r in s.owner_events)
   assert sum(r['kind']=='FIRST_ORIGINAL_CAUSALLY_ELIGIBLE_BTC_POSITIVE_PROGRAM_ACTIVATION' for r in s.owner_events)==1
  RESULTS.append({'case':name,'days':len(daily[0]),'minutes':len(am),'minute_bytes_SHA256':sha(am.tobytes()),'original_minute_columns_schema':asc,'full37_minute_bytes_equal':True,'full_owner_account_scheduler_outputs_equal':True,'wall_seconds':time.monotonic()-begin})

def rolled_partial_replay():
 q=prepared();ids=[];original=[]
 for s in q:
  stamp=mark(s,2,90);s._evaluate_program(stamp);ids.append(s.program_pending['order_id']);original.append(deepcopy(s._program_order_authorizations[ids[-1]]));s.previous_quote=dict.fromkeys(F.S,40500.)
 for n in range(3,8):
  for s in q:mark(s,n,90);s.attempt(F.START+n*F.MINUTE,row(90))
  compare(q,'rolled_step_'+str(n))
 for s,oid,w in zip(q,ids,original):
  assert s.program.completed_opening_orders==2 and s._program_order_authorizations[oid]==w
  assert w['mark_close_us'] not in [m['close_us'] for m in s.account.marks[BTC]]
  assert len([r for r in s.account.trades if r['fill_id'].startswith(oid+':')])==5
 compare(q,'rolled_partial',True)
 receipts=[]
 for s in q:
  leg=next(r for r in s.account.trades if s._fill_owner[r['fill_id']][0]==FINITE)
  before=full(s);request=deepcopy(s.account.fill_requests[leg['fill_id']]['identity'])
  s.risk_contexts[s.cursor]['ready']=False;before=full(s)
  receipt=s.account.execute_fill(**request,fill_id=leg['fill_id']);assert type(receipt) is dict and type(receipt['fills']) is list
  receipt['fills'][0]['decimal_strings']['quantity']='caller_mutated';exact(before,full(s),'replay_no_progress_'+str(len(receipts)));receipts.append(receipt)
 exact(receipts[0],receipts[1],'replay_plain_receipt');compare(q,'replay_full',True)


def funding_profit_selective():
 q=prepared();rates=(D('.000000123456789012345678901234567890123456789'),D('-.0000000987654321098765432109876543210987654321'))
 for i in range(8):
  for s in q:
   s.account.apply_funding(BTC,'FRACTIONAL-FUNDING-'+str(i),F.START+(i+2)*F.MINUTE+1,rates[i%2],F.START);s._flush_account()
  compare(q,'fractional_'+str(i))
 for s in q:
  used=s.program_budget.consumed_fee_funding_reserve;count=s.program.completed_opening_orders
  mark(s,10,110);s._evaluate_program(F.START+10*F.MINUTE)
  assert s.owners.pnl(FINITE,s.account.engine)>0 and not s.program.terminal and s.program_budget.consumed_fee_funding_reserve==used and s.program.completed_opening_orders==count
  s.account.apply_funding(BTC,'PROFIT-CREDIT-NO-REFILL',F.START+11*F.MINUTE+1,D('-.003'),F.START);s._flush_account();assert s.program_budget.consumed_fee_funding_reserve==used
  mark(s,12,90);s._evaluate_program(F.START+12*F.MINUTE);s.attempt(F.START+13*F.MINUTE,row(90))
  base=s.owners.quantity[BASE_OWNER][BTC];held=s.owners.quantity[FINITE][BTC]
  s._retire_program('GENERATED_SELECTIVE_EXIT_TEST',F.START+14*F.MINUTE,exit_inventory=True);s.previous_quote=dict.fromkeys(F.S,50000.);s.attempt(F.START+15*F.MINUTE,row(97))
  assert s.owners.quantity[BASE_OWNER][BTC]==base and Z<s.owners.quantity[FINITE][BTC]<held
 compare(q,'funding_profit_selective',True)


def reserve_and_stop():
 q=prepared()
 for s in q:
  with localcontext() as ctx:ctx.prec=40;rate=D('140')/(s.owners.quantity[FINITE][BTC]*D('100'))
  s.account.apply_funding(BTC,'GENERATED_COST_RESERVE_DRAIN',F.START+2*F.MINUTE+1,rate,F.START);s._flush_account();s._evaluate_program(F.START+2*F.MINUTE+1)
  used=s.program_budget.consumed_fee_funding_reserve;assert used>D('135.156250') and s.program.terminal
  s.account.apply_funding(BTC,'GENERATED_CREDIT_NO_REFILL',F.START+3*F.MINUTE+1,-rate,F.START);s._flush_account();assert s.program_budget.consumed_fee_funding_reserve==used
  s._start_margin_order(F.START+4*F.MINUTE);assert s.program_pending is None
 compare(q,'reserve_no_refill',True)
 signals=[]
 for epsilon in (D('1e-20'),Z,D('-1e-20')):
  q=prepared();rows=[]
  for s in q:
   with localcontext() as ctx:
    ctx.prec=40;target=D('-200')+epsilon;debit=s.owners.pnl(FINITE,s.account.engine)-target;rate=debit/(s.owners.quantity[FINITE][BTC]*D('100'))
   s.account.apply_funding(BTC,'NEAR-MINUS200-GENERATED',F.START+2*F.MINUTE+1,rate,F.START);s._flush_account();assert s.owners.pnl(FINITE,s.account.engine)==target
   s._evaluate_program(F.START+2*F.MINUTE+1);rows.append(any(r.get('reason')=='ACTUAL_FILL_ECONOMIC_NET_SLEEVE_PNL_LE_MINUS200' for r in s.owner_events))
  assert rows[0]==rows[1];signals.append(rows[0]);compare(q,'stop_boundary_'+str(epsilon),True)
 assert signals==[False,True,True]
 q=prepared()
 for s in q:
  mark(s,2,90);s._evaluate_program(F.START+2*F.MINUTE);s.attempt(F.START+3*F.MINUTE,row(90));basis=s.owners.basis[FINITE][BTC]
  with localcontext() as ctx:ctx.prec=28;old=s.program.plan.trigger_price(basis)
  with localcontext() as ctx:ctx.prec=40;trigger=s.program.plan.trigger_price(basis)
  assert trigger>old;mark(s,4,trigger);s._evaluate_program(F.START+4*F.MINUTE);assert s.program_pending['program_order_index']==2
 compare(q,'trigger_Decimal40',True)


def csh_budget():
 from owner_ledger import exact as number
 for excess in (Z,D('.00000001')):
  q=pair(F.make_generated(weights=[0,0,0,0,0]));requests=[]
  for s in q:
   s._admit_decision(F.START,None,None,None,None);mark(s,0,100)
   def req(sym,side,qty,fid,event):
    s._fill_owner[fid]=(BASE_OWNER,None)
    return dict(symbol=sym,side=side,quantity=D(qty),fill_id=fid,event_us=event,signal_us=F.START,execution_mid_price=D('100'),quote_available_us=event-1,reduce_only=False)
   for i,(sym,side) in enumerate(zip(F.S[:3],('BUY','SELL','BUY'))):
    receipt=s.account.execute_fill(**req(sym,side,'20','CSH-PREFIX-'+str(i),F.START+F.MINUTE+1+i));assert receipt['status']=='FILLED';s._flush_account()
   request=req(F.S[3],'SELL','19.9','CSH-8000-BOUNDARY',F.START+F.MINUTE+10)
   raw=s.account.engine;probe=deepcopy(raw,{id(raw.instrument_profiles):raw.instrument_profiles});before=len(probe.trades);assert probe.execute_fill(**request)['status']=='FILLED'
   ledger=deepcopy(s.owners)
   for r in probe.trades[before:]:ledger.trade(r,BASE_OWNER)
   with localcontext() as ctx:ctx.prec=40;needed=D('8000')-s._owner_committed(BASE_OWNER,ledger,probe)+excess;rate=needed/D('2000')
   funded=s.account.apply_funding(BTC,'CSH-BUDGET-DEBIT',F.START+F.MINUTE+5,rate,F.START);assert number(funded,'signed_funding_USDT')==-needed;s._flush_account()
   before=full(s);receipt=s.account.execute_fill(**request)
   if excess:
    assert receipt=={'status':'POLICY_REJECTED','reason':'CSH_FIXED8000_MARGIN_COST_LOSS_BUDGET'};exact(before,full(s),'budget_atomic_'+str(len(requests)))
    committed=s._owner_committed(BASE_OWNER,s.owners,raw);s.account.apply_funding(BTC,'CSH-CREDIT-NO-REFILL',F.START+F.MINUTE+6,D('-.0005'),F.START);s._flush_account();assert s._owner_committed(BASE_OWNER,s.owners,raw)==committed
    assert s.account.execute_fill(**request)['reason']=='CSH_FIXED8000_MARGIN_COST_LOSS_BUDGET'
   else:s._flush_account();assert receipt['status']=='FILLED' and s._owner_committed(BASE_OWNER,s.owners,raw)==D('8000')
   requests.append(receipt)
  exact(requests[0],requests[1],'budget_receipt_'+str(excess));compare(q,'budget_'+str(excess),True)


def ordinary_refusal():
 for case in ('overowned','direction','witness_type','source_freshness','conflicting_identity'):
  q=prepared();receipts=[]
  for s in q:
   fid='ORDINARY-INVALID-REDUCTION';s._fill_owner[fid]=(FINITE,None)
   request=dict(symbol=BTC,side='SELL',quantity=s.owners.quantity[FINITE][BTC]+D('.00000001'),event_us=F.START+2*F.MINUTE+1,signal_us=F.START,fill_id=fid,execution_mid_price=D('100'),quote_available_us=F.START+2*F.MINUTE,reduce_only=True)
   if case=='direction':request.update(side='BUY',quantity=D('.1'))
   if case in ('witness_type','source_freshness'):
    stamp=mark(s,2,94);s._evaluate_program(stamp);order=s.program_pending;fid=order['order_id']+':0:INCREASE';s._fill_owner[fid]=(FINITE,1)
    if case=='witness_type':s._program_order_authorizations[order['order_id']]['source_decision_us']=float(F.START)
    else:s.risk_contexts[s.cursor]['ready']=False
    request.update(side='BUY',quantity=D('.1'),event_us=F.START+3*F.MINUTE+1,signal_us=stamp,fill_id=fid,quote_available_us=F.START+3*F.MINUTE,reduce_only=False)
   if case=='conflicting_identity':
    leg=s.account.trades[0];request=deepcopy(s.account.fill_requests[leg['fill_id']]['identity']);request.update(fill_id=leg['fill_id'],quantity=D(request['quantity'])+D('.00000001'))
   before=full(s)
   if case=='conflicting_identity':
    try:s.account.execute_fill(**request)
    except ValueError as error:receipt={'exception_type':'ValueError','message':str(error)}
    else:raise AssertionError('CONFLICTING_IDENTITY_MUST_REFUSE')
    assert receipt['message']=='conflicting fill identity'
   else:
    receipt=s.account.execute_fill(**request);assert receipt['status']=='POLICY_REJECTED'
    if case=='source_freshness':assert receipt['reason']=='SOURCE_FRESHNESS_REQUIRED_FOR_OWNER_INCREASE'
   exact(before,full(s),'ordinary_atomic_'+case+str(len(receipts)));receipts.append(receipt)
  exact(receipts[0],receipts[1],'ordinary_reasons_'+case);compare(q,'ordinary_'+case,True)


def lineage_checks():
 identity=B.require_control_baseline_lineage();p=BASE/'baseline_control_metadata/EVIDENCE_MANIFEST.json';record=json.loads(p.read_text());digest=sha(p.read_bytes())
 assert B.completed_control_preparation_matches(p,digest,record,PIN)
 for bad_sha,bad_record in (('0'*64,record),(digest,dict(record,preparation_manifest_SHA256='0'*64))):
  try:B.completed_control_preparation_matches(p,bad_sha,bad_record,PIN)
  except ValueError as error:assert str(error)=='EXACT_PINNED_CONTROL_BASELINE_LINEAGE_REQUIRED'
  else:raise AssertionError('WRONG_BASELINE_LINEAGE_MUST_REFUSE')
 with tempfile.TemporaryDirectory(dir=OUT) as td:
  folder=Path(td)
  for name in ('EVIDENCE_MANIFEST.json','BINDING.json','SUMMARY.json'):(folder/name).write_bytes((p.parent/name).read_bytes())
  (folder/'SUMMARY.json').write_text('{}\n')
  try:accepted=B.completed_control_preparation_matches(folder/p.name,digest,record,PIN)
  except (TypeError,ValueError):accepted=False
  assert not accepted
 return {'baseline_identity':identity,'exact_actual_b58_complete_metadata':True,'wrong_sha_wrong_prep_wrong_sibling_rejected':True,'actual_metadata_never_relabeled':True}

def main():
 rt,np=bootstrap();lineage=lineage_checks();profile=cProfile.Profile();profile.enable()
 try:
  calendar_cases(np);rolled_partial_replay();funding_profit_selective();reserve_and_stop();csh_budget();ordinary_refusal()
 finally:profile.disable();profile.dump_stats(str(OUT/'generated_finite_parity.pstats'))
 stats=pstats.Stats(profile);parsers=[]
 for (filename,line,function),(primitive,total,own,cum,callers) in stats.stats.items():
  if function in ('load','loadtxt','genfromtxt','read_parquet') and any(n in filename for n in ('/numpy/','/polars/','/pyarrow/')):parsers.append([filename,function,total])
 assert not parsers
 distinct=sorted({r['path'] for r in NPZ_OPENS});assert len(distinct)==2 and sum((ROOT/n).stat().st_size for n in distinct)==50586
 save('RESULT.json',{'schema':'GENERATED_ORIGINAL_FINITE_PREFIX_PARITY_V1','status':'PASS','preparation_manifest_SHA256':PIN,'cases':RESULTS,'direct_full_owner_state_witnesses':WITNESSES,'lineage':lineage,'source_audit':rt.audit(),'runtime_packages':rt.runtime_packages,'source_arrays_parsed':0,'historical_accounts_drivers':0,'public_checksum_only_NPZ_files':2,'public_checksum_only_NPZ_bytes':50586,'NPZ_open_log':NPZ_OPENS,'array_parsers':parsers,'OwnerLedger_copies_changed':False,'recipe_changed':False,'automatic_retries':0,'CPU_affinity':sorted(os.sched_getaffinity(0)),'wall_seconds':time.monotonic()-STARTED,'CPU_seconds':time.process_time(),'peak_RSS_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024})
try:main()
except BaseException as error:
 save('FAILURE.json',{'status':'FAILED_NO_RETRY','error':repr(error),'traceback':traceback.format_exc(),'completed_cases':RESULTS,'direct_witnesses':WITNESSES,'automatic_retries':0});raise
