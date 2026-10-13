"""Exact observer/source/pins only. No main/cold restore, result, or transition."""
from pathlib import Path
import ast,hashlib,importlib.util,json,sys
H=Path(__file__).resolve().parent;W=H.parent;M=W/'coin_headroom_risk_candidate_postrun_audit_20261013';C=W/'coin_headroom_risk_candidate_20261013';P=W/'coin_headroom_process_recovery_20261013'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
expected='ff3635f59948b421dd06194f0643633fdcf7a079f695b30ac78c7bad41743f5e'
assert sha(M/'PREPARED_OBSERVER.json')==expected
manifest=json.loads((M/'PREPARED_OBSERVER.json').read_text())
for name,h in manifest['files_SHA256'].items():assert sha(M/name)==h
sys.path.insert(0,str(C));from freeze_candidate import verify
original=verify(W,require_review=True);assert original['freeze_manifest_SHA256']==manifest['freeze_SHA256']
spec=importlib.util.spec_from_file_location('independent_observer_identity',M/'cold_audit.py');a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)
for name,h in a.PATCH_PINS.items():assert sha(P/name)==h
for name,h in a.TERMINAL_PINS.items():assert sha(P/name)==h
assert sha(C/'PUBLICATION_RECEIPT.json')==a.ORIGINAL_PUBLICATION
patch=json.loads((P/'FROZEN_PATCH.json').read_text())
for name,h in patch['files_SHA256'].items():assert sha(P/name)==h
assert len(patch['files_SHA256'])==9 and len(original['files_SHA256'])==20 and len(original['dependencies_SHA256'])==45
assert manifest['local_years']==[2021,2023] and manifest['historical_observer_executions_during_preparation']==0
for n in ['cold_audit.py','run_bounded_audit.py']:
 tree=ast.parse((M/n).read_text());calls=[ast.unparse(x.func) for x in ast.walk(tree) if isinstance(x,ast.Call)]
 for forbidden in ['advance_day','schedule','attempt','funding_through','risk_schedule','observe','execute_fill','apply_funding','update_marks']:
  assert not any(c.endswith('.'+forbidden) for c in calls),(n,forbidden)
assert 'HeadroomFullExitSimulator.from_snapshot' in [ast.unparse(x.func) for x in ast.walk(ast.parse((M/'cold_audit.py').read_text())) if isinstance(x,ast.Call)]
out={'status':'PASS_EXACT_OBSERVER_SOURCE_ORIGINAL_FINANCE_AND_OPERATIONAL_PINS','observer_manifest_SHA256':expected,'observer_code_SHA256':sha(M/'cold_audit.py'),'wrapper_SHA256':sha(M/'run_bounded_audit.py'),'original_candidate_freeze_SHA256':original['freeze_manifest_SHA256'],'original_candidate_files_verified':20,'original_unchanged_dependencies_verified':45,'patch_files_verified':9,'patch_pins':a.PATCH_PINS,'terminal_release_and_transport_pins':a.TERMINAL_PINS,'no_financial_transition_call_in_observer_or_wrapper_AST':True,'actual_cold_main_or_restore_executions':0,'historical_financial_advances':0,'new_historical_wallets_executed':0}
with (H/'OBSERVER_IDENTITY_RECEIPT.json').open('x') as f:json.dump(out,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(out,indent=2,sort_keys=True))
