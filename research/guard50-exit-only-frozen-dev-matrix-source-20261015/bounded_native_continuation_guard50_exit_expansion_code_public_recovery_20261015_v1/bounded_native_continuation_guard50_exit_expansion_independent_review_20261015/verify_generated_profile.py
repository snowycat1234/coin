"""Read-only generated evidence check. No account construction or execution."""
from pathlib import Path
from decimal import Decimal as Q
from hashlib import sha256
import json
import run_expansion as runner
from saved_native_reconciliation import reconcile_saved_native
ROOT=Path('bounded_native_continuation_guard50_exit_expansion_20261015')
OUT=Path('bounded_native_continuation_guard50_exit_expansion_independent_review_20261015')
def pin(p):return sha256(p.read_bytes()).hexdigest()
p=ROOT/'generated_pool_final_v2';r=json.loads((p/'GENERATED_POOL_PROFILE.json').read_bytes())
assert r['runner_SHA256']==pin(ROOT/'run_expansion.py')
assert r['checker_SHA256']==pin(ROOT/'saved_native_reconciliation.py')
assert r['generated_only'] is True and r['historical_account_objects_constructed']==0
assert len(r['cases'])==2 and all(not x['reused_saved_terminal'] for x in r['cases'])
assert any(len([w for w in x['workers'] if w['RSS_bytes']>0])==2 for x in r['observations'])
assigned={};startup_samples=[]
for sample in r['observations']:
 assert sample['aggregate_live_RSS_bytes']<runner.LIMITS['aggregate_live_worker_RSS_stop_bytes']
 assert len(sample['workers'])<=2
 cpus=[w['CPU_affinity'] for w in sample['workers']]
 single=[c[0] for c in cpus if len(c)==1];assert len(set(single))==len(single)
 for worker in sample['workers']:
  if len(worker['CPU_affinity'])==1:
   assert all(t['CPU_affinity']==worker['CPU_affinity'] for t in worker['tasks'])
   assigned[worker['PID']]=worker['CPU_affinity']
  else:
   assert worker['PID'] not in assigned and worker['CPU_affinity']==r['coordinator_CPU_affinity']
   startup_samples.append(dict(UTC=sample['UTC'],PID=worker['PID'],CPU_affinity=worker['CPU_affinity'],RSS_bytes=worker['RSS_bytes']))
rows=[]
for cell in r['cases']:
 d=p/cell['cell_id'];cp=json.loads((d/'TERMINAL_CHECKPOINT.json').read_bytes())
 assert all(pin(d/name)==digest for name,digest in cp['files'].items())
 a=json.loads((d/'GENERATED_AUDIT.json').read_bytes());result=json.loads((d/'GENERATED_RESULT.json').read_bytes())
 proof=reconcile_saved_native(a,result)
 assert runner.body(proof)==(d/'GENERATED_PROOF.json').read_bytes()
 assert a['transfer_journal']==[] and a['transfer_ids']=={} and a['settlement_journal']==[]
 rec=json.loads((d/'CASE_RECEIPT.json').read_bytes());assert rec['generated_minutes']==4320 and rec['paid_trade_rows']==14
 assert Q(a['totals']['fees'])>0
 warning=[]
 for m in a['monitor_journal']:
  for action in m['actions']:
   if action.get('reason')=='GUARD50_PAID_EXIT_NO_TOPUP':
    assert action['transferred']=='0' and action['full_actual_position_exit_required'] is True
    trade=next(t for t in a['trades'] if t['symbol']==action['symbol'] and t['leg']=='CLOSE' and t['signal_us']==m['event_us'])
    assert trade['event_us']==m['event_us']+60_000_001 and not trade.get('liquidation_takeover')
    assert Q(trade['decimal_strings']['quantity_after'])==0 and Q(trade['decimal_strings']['fee_amount'])>0
    warning.append(dict(symbol=action['symbol'],signal_us=m['event_us'],paid_fill_us=trade['event_us']))
 assert len(warning)==3
 bootstrap=json.loads((d/'BOOTSTRAP_READY.json').read_bytes())
 assert bootstrap['PID']==rec['PID'] and bootstrap['actual_affinity']==rec['actual_affinity']
 assert bootstrap['thread_environment']==rec['thread_environment'] and all(v=='1' for v in rec['thread_environment'].values())
 assert rec['wall_seconds']<600 and rec['max_RSS_bytes']<runner.LIMITS['per_case_RSS_stop_bytes']
 rows.append(dict(cell_id=cell['cell_id'],paid_trade_rows=rec['paid_trade_rows'],warning_exits=warning,
   financial_ledger_rows=proof['financial_ledger_rows_checked'],funding_rows=proof['funding_rows_checked'],
   resource_receipt=rec,proof_SHA256=pin(d/'GENERATED_PROOF.json'),bootstrap_SHA256=pin(d/'BOOTSTRAP_READY.json')))
receipt=dict(schema='INDEPENDENT_READONLY_ACTIVE_GENERATED_POOL_EVIDENCE_REVIEW_V1',status='PASS',
 profile_SHA256=pin(p/'GENERATED_POOL_PROFILE.json'),runner_SHA256=r['runner_SHA256'],checker_SHA256=r['checker_SHA256'],
 stdlib_pre_bootstrap_CPU_union_samples=startup_samples,
 post_bootstrap_assignment_proof='Exact stdlib bootstrap applies CPU affinity and limits before exec; all subsequent observed samples remain assigned; bootstrap/PID/receipt and independent startup probes checked',
 peak_observed_aggregate_worker_RSS_bytes=max(x['aggregate_live_RSS_bytes'] for x in r['observations']),cases=rows,
 actual_historical_accounts_constructed=0,historical_market_minutes_advanced=0,
 annual_feasibility_certified=False,host_quota_certified=False,publication_actions=0)
(OUT/'GENERATED_PROFILE_REVIEW.json').write_bytes(runner.body(receipt))
print(pin(OUT/'GENERATED_PROFILE_REVIEW.json'));print(json.dumps({k:v for k,v in receipt.items() if k!='cases'}))
