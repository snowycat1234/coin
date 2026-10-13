"""Read-only exact patch/original identity audit; no controller or wallet call."""
from pathlib import Path
import ast,hashlib,importlib.util,json,sys
H=Path(__file__).resolve().parent;W=H.parent;M=W/'coin_headroom_process_recovery_20261013';C=W/'coin_headroom_risk_candidate_20261013';sys.path.insert(0,str(M))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
EXPECTED='d511d426f79a5add7b3bd98598b6f9a68f8d25ee5249385c62b922b19d5cf8b8'
assert sha(M/'FROZEN_PATCH.json')==EXPECTED
spec=importlib.util.spec_from_file_location('independent_patch_identity_shim',M/'run_fixed.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
p=r.verify_patch(C)
assert p['original_candidate_freeze_SHA256']=='c1c50dd484400a175bf28b16ae16a500a5c195f0f88403e5d5dc4d08f275d5e6'
assert len(p['files_SHA256'])==9
zero=r.require_original_zero_history(C,C/'state_first_authorized_run')
run=r.load_original(C,W)
original=run.verify_reviewed_freeze(W,require_review=True)
assert len(original['files_SHA256'])==20 and len(original['dependencies_SHA256'])==45
assert Path(run.__file__).resolve()==C/'run_cases.py'
assert run.HERE==M/'operation_namespace'
for name in ('worker','controller'):
 fn=getattr(run,name);assert Path(fn.__code__.co_filename).resolve()==C/'run_cases.py'
assert sha(C/'run_cases.py')==p['original_candidate_runner_SHA256']
assert sha(C/'REVIEW_RECEIPT.json')==p['original_review_SHA256']
assert sha(C/'state_first_authorized_run/RESOURCE_RECEIPTS.json')==sha(M/'ORIGINAL_STOP_RECEIPT.json')
assert not list((C/'state_first_authorized_run').glob('*/BINDING.json'))
assert not list((C/'state_first_authorized_run').glob('*/recovery/POINTER.json'))
for k,v in {'WORKER_RSS_LIMIT':2_000_000_000,'WORKER_AS_LIMIT':4_000_000_000,'HOST_USED_LIMIT':8_000_000_000,'CPU_LIMIT':1200,'WALL_LIMIT':1200,'CASE_LIMIT':250_000_000,'DISK_RESERVE':16_106_127_360}.items():assert getattr(run.guard,k)==v
source=ast.parse((M/'run_fixed.py').read_text())
assert not any(isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name in ('worker','controller') for n in ast.walk(source))
assignments={ast.unparse(n.targets[0]):ast.unparse(n.value) for n in ast.walk(source) if isinstance(n,ast.Assign) and len(n.targets)==1}
assert assignments['run.guard.CPU_LIMIT']=='1199' and assignments['run.guard.WALL_LIMIT']=='1199'
e=json.loads((M/'ZERO_HISTORY_INPUTS.json').read_text());stop=json.loads((C/'state_first_authorized_run/RESOURCE_RECEIPTS.json').read_text())
assert e['original_abort_wall_seconds']==stop['per_case']['Y2021_STATIC50_FINE_HEADROOM']['elapsed_seconds']
assert 1199+e['original_abort_wall_seconds']<1200
assert list(stop['per_case'])==['Y2021_STATIC50_FINE_HEADROOM'] and stop['per_case']['Y2021_STATIC50_FINE_HEADROOM']['stop_reason']=='EXTERNAL_HISTORY'
assert (C/'state_first_authorized_run/Y2021_STATIC50_FINE_HEADROOM.log').stat().st_size==0
out={'status':'PASS_EXACT_PROCESS_PATCH_AND_ORIGINAL_ZERO_ACCOUNT_IDENTITIES','patch_freeze_SHA256':EXPECTED,'patch_files_verified':9,'original_freeze_SHA256':original['freeze_manifest_SHA256'],'original_candidate_files_verified':20,'original_old_dependencies_verified':45,'original_controller_worker_file_and_function_code_locations_unchanged':True,'original_STOP_launch_RUN_and_empty_log_SHA256':e['original_files_SHA256'],'actual_zero_history_gate':zero,'namespace_only_original_CASE_review_byte_copies':True,'local_CPU_wall_cap_seconds':1199,'original_aborted_wall_seconds_charged':e['original_abort_wall_seconds'],'cloud_fresh_CPU_wall_cap_seconds':1200,'per_worker_RSS_bytes':run.guard.WORKER_RSS_LIMIT,'address_bytes':run.guard.WORKER_AS_LIMIT,'host_bytes':run.guard.HOST_USED_LIMIT,'historical_financial_advances':0,'new_historical_wallets_executed':0}
with (H/'PATCH_IDENTITY_RECEIPT.json').open('x') as f:json.dump(out,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps(out,indent=2,sort_keys=True))
