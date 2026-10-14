"""Exact full generated snapshots/evidence and mutation-refusal validation."""
from pathlib import Path
import argparse,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parent.parent
from profile_generated import bootstrap,dense

def main():
 p=argparse.ArgumentParser();p.add_argument('--candidate-sha');p.add_argument('--output',required=True);args=p.parse_args();out=Path(args.output);out.mkdir(parents=True,exist_ok=False);runtime=bootstrap()
 if args.candidate_sha:
  candidate=ROOT/'coin_bot_native_adapter_observer_performance_20261014/native_adapter.py';runtime.add_path(candidate,args.candidate_sha);runtime.modules['native_adapter']=candidate.resolve();runtime.protected_roots.append(candidate.parent.resolve());candidate_evidence=ROOT/'coin_bot_historical_driver_observer_performance_20261014/evidence.py';runtime.add_path(candidate_evidence,'682c40d797e29e758bafaed316967a15765c1a2dfc610bf3370db8d068b0705e');runtime.modules['evidence']=candidate_evidence.resolve()
 import numpy as np
 np.load=lambda *a,**k:(_ for _ in ()).throw(ValueError('NO_ARRAY_LOAD_IN_GENERATED_PARITY'))
 from evidence import safe,json_file,export_final
 results=[];began=time.monotonic()
 for scenario in ('PARTIAL','REVERSE','TERMINAL_RESIDUAL'):
  for arm in ('CONTROL','CASH','GRID'):
   sim=dense(3,arm,scenario);daily=[];nav=[float(sim.account.nav())]
   while sim.cursor<sim.end and sim.stop is None:daily.append(sim.advance_day());nav.append(float(sim.account.nav()))
   target=out/(scenario+'_'+arm);result=export_final(sim,target/'evidence',dict(fixture='DENSE_FIXED_GENERATED_PARITY',scenario=scenario,arm=arm),daily,nav,origin='GENERATED_ONLY_NO_MARKET_PERFORMANCE')
   json_file(target/'FULL_SIMULATOR_SNAPSHOT.json.gz',sim.snapshot(),True)
   results.append(dict(scenario=scenario,arm=arm,completed_minutes=sim.rows_written,native_fills=len(sim.account.trades),native_funding=len(sim.account.funding),owner_fills=len(sim.allocations),owner_funding=len(sim.funding_allocations),result=result))
 mutations=[]
 if args.candidate_sha:
  sim=dense(1,'CONTROL');sim.advance_day()
  def rejects(name,action,pattern):
   try:action()
   except (ValueError,AssertionError,TypeError,AttributeError,ArithmeticError) as error:
    if pattern and pattern not in str(error):raise
    mutations.append(dict(name=name,status='REFUSED',reason=str(error)));return
   raise AssertionError('MUTATION_ACCEPTED:'+name)
  for name,action in [('row_fee_assignment',lambda:sim.allocations[0].__setitem__('fee','0')),('native_leg_nested_assignment',lambda:sim.allocations[0]['native_leg'].__setitem__(0,'MUTATED')),('ledger_append',lambda:sim.allocations.append({})),('ledger_clear',lambda:sim.allocations.clear()),('ledger_slice_truncate',lambda:sim.allocations.__delitem__(slice(None))),('funding_row_assignment',lambda:sim.funding_allocations[0].__setitem__('cash','0'))]:rejects(name,action,None)
  original=sim.allocations;sim.allocations=list(original);rejects('ledger_copy_replace',sim._reconcile,'IDENTITY_OR_LENGTH_CHANGED');sim.allocations=original
  rejects('baseclass_ledger_assignment',lambda:list.__setitem__(sim.allocations,0,{}),None)
  rejects('baseclass_row_assignment',lambda:dict.__setitem__(sim.allocations[0],'fee','999'),None)
  rejects('baseclass_nested_assignment',lambda:list.__setitem__(sim.allocations[0]['native_leg'],0,'MUTATED'),None)
  # An explicitly private append bypass is not a supported public operation;
  # the O(1) count guard still refuses it before the next reconciliation.
  sim._owner_allocation_ledger._append({});rejects('private_append_count_guard',sim._reconcile,'IDENTITY_OR_LENGTH_CHANGED')
  sim.allocations._OwnerAuditLedger__rows.pop()
  before=(len(sim.allocations),sim._owner_allocation_count,sim._owner_fee_total,sim._owner_cost_total)
  rejects('invalid_fill_cost_atomic',lambda:sim._record_owner_fill(dict(fee='1',execution_cost='bad')),None)
  if before!=(len(sim.allocations),sim._owner_allocation_count,sim._owner_fee_total,sim._owner_cost_total):raise AssertionError('FILL_TRANSACTION_PARTIALLY_COMMITTED')
  before=(len(sim.funding_allocations),sim._owner_funding_count,sim._owner_funding_total)
  rejects('invalid_second_funding_atomic',lambda:sim._record_owner_funding([dict(cash='1'),dict(cash='bad')]),None)
  if before!=(len(sim.funding_allocations),sim._owner_funding_count,sim._owner_funding_total):raise AssertionError('FUNDING_TRANSACTION_PARTIALLY_COMMITTED')
  rejects('fork',sim.fork,'FORK_NOT_IMPLEMENTED');rejects('resume',lambda:sim.from_snapshot({},{}),'RESTORE_NOT_IMPLEMENTED');sim.audit_owner_totals()
 runtime.audit();report=dict(status='PASS_GENERATED_PARITY_VALIDATION',candidate_adapter_SHA256=args.candidate_sha,scenarios=results,mutation_refusals=mutations,wall_seconds=time.monotonic()-began,historical_arrays_read=0,historical_wallets=0);(out/'VALIDATION_RECEIPT.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
