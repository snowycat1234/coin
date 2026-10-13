"""Verify serial recovery sidecars, then reuse frozen zero-advance cold observer."""
from pathlib import Path
import sys,json,hashlib,importlib.util
H=Path(__file__).resolve().parent;R=H.parent;O=R/'coin_earlier_terminal_exit_20261013'
from freeze_resume import verify,require_publication
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def verify_recovery_aggregate():
 verify(require_review=True);publication=require_publication();plan=read(H/'RESUME_PLAN.json');state=R/plan['destination_state_locator'];run=read(state/'RECOVERY_RUN_BINDING.json');receipts=read(state/'RESOURCE_RECEIPTS.json')
 if sha(R/plan['original_state_locator']/'RESOURCE_RECEIPTS.json')!=plan['original_STOP_receipt_SHA256']:raise ValueError('Original STOP was changed')
 if (receipts['status']!='ALL_CASES_FINISHED' or receipts['completion_scope']!='RECOVERY_OF_TWO_ORIGINAL_INTERRUPTED_CASES_NOT_NEW_BATCH'
  or receipts['original_STOP_preserved'] is not True or receipts['original_STOP_receipt_SHA256']!=plan['original_STOP_receipt_SHA256']
  or receipts['max_parallel']!=1 or receipts['unstarted_case_ids'] or set(receipts['per_case'])!={c['identity'] for c in plan['cases']}):raise ValueError('Not exact serial recovery aggregate')
 if (run['recovery_manifest_SHA256']!=sha(H/'FROZEN_RECOVERY.json') or run['review_receipt_SHA256']!=sha(H/'REVIEW_RECEIPT.json')
  or run['recovery_publication_receipt_SHA256']!=publication['receipt_SHA256']
  or run['new_wallets']!=0 or run['new_variants']!=0 or not run['parent_GO']):raise ValueError('Exact resource continuation authorization changed')
 if sha(state/'RUN_BINDING.json')!=plan['original_RUN_BINDING_SHA256']:raise ValueError('Original financial RUN identity changed')
 for c in plan['cases']:
  p=state/c['identity'];b=read(p/'RECOVERY_BINDING.json');receipt=receipts['per_case'][c['identity']]
  if (sha(p/'BINDING.json')!=c['source_binding_SHA256'] or b['original_pointer_SHA256']!=c['source_pointer_SHA256']
   or b['original_snapshot_SHA256']!=c['source_snapshot_SHA256'] or b['original_state_hash']!=c['source_state_hash']
   or b['original_durable_cursor']!=c['source_cursor_us'] or b['recovery_run_binding_SHA256']!=sha(state/'RECOVERY_RUN_BINDING.json')):raise ValueError('Recovery anchor identity changed')
  if (receipt['exit_code'] or receipt['stop_reason'] or receipt['original_elapsed_seconds']!=c['original_elapsed_seconds']
   or receipt['cumulative_case_elapsed_seconds']>1200 or receipt['remaining_CPU_limit']!=c['resume_CPU_seconds']):raise ValueError('Cumulative resource budget exceeded')
 return plan,state

def main(identity):
 plan,state=verify_recovery_aggregate()
 if identity not in {c['identity'] for c in plan['cases']}:raise ValueError('Foreign cold case')
 sys.path.insert(0,str(O));spec=importlib.util.spec_from_file_location('frozen_terminal_original_cold',O/'cold_audit.py');cold=importlib.util.module_from_spec(spec);spec.loader.exec_module(cold)
 cold.main(identity,state)
 original=read(O/'receipts'/f'{identity}.json')
 out=dict(status='PASS_RESUMED_AGGREGATE_AND_FROZEN_ZERO_ADVANCE_COLD',case_id=identity,financial_advances=0,new_wallets=0,
  original_STOP_receipt_SHA256=plan['original_STOP_receipt_SHA256'],recovery_run_binding_SHA256=sha(state/'RECOVERY_RUN_BINDING.json'),
  recovery_resource_receipt_SHA256=sha(state/'RESOURCE_RECEIPTS.json'),frozen_cold_receipt_SHA256=sha(O/'receipts'/f'{identity}.json'),
  new_ACCOUNT_SHA256=sha(state/identity/'ACCOUNT.json'),new_RESULT_SHA256=sha(state/identity/'RESULT.json'),
  original_financial_state_hash=original['genuine_state_hash'],pre_intervention_numeric_minutes_checked=original['pre_intervention_numeric_minutes_checked'])
 folder=H/'receipts';folder.mkdir(exist_ok=True)
 with (folder/f'{identity}.json').open('x') as file:json.dump(out,file,indent=2,sort_keys=True);file.write('\n')
 print(json.dumps(out,indent=2))
if __name__=='__main__':main(sys.argv[1])
