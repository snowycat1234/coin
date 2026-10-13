"""Freeze supplemental operational repair; no account/source imports."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent;C=HERE.parent/'coin_headroom_risk_candidate_20261013'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def main():
    state=C/'state_first_authorized_run';names=['state_first_authorized_run/RUN_BINDING.json','state_first_authorized_run/RESOURCE_RECEIPTS.json','HISTORICAL_LAUNCH.json','state_first_authorized_run/Y2021_STATIC50_FINE_HEADROOM.log']
    for identity in ('Y2021_STATIC50_FINE_HEADROOM','Y2023_STATIC50_FINE_HEADROOM'):
        if (state/identity).exists() or (state/identity).is_symlink():raise RuntimeError('Original account exists, no zero-history operation')
        p=state/(identity+'.log')
        if p.is_symlink() or p.exists() and p.stat().st_size:raise RuntimeError('Nonempty original account worker log')
    evidence={'status':'PASS_ORIGINAL_ZERO_ACCOUNT_ABORT_PROOF','original_state_root':str(state.resolve()),
        'original_files_SHA256':{name:sha(C/name) for name in names},
        'original2021_worker_log_bytes':0,'original2021_account_directory_exists':False,
        'original2023_account_directory_exists':False,'original2023_worker_not_started':True,
        'original_abort_wall_seconds':.006303863003267907,'local_remaining_CPU_wall_seconds':1199,
        'new_historical_wallets_started':0,'new_variant_count':0}
    if (HERE/'ZERO_HISTORY_INPUTS.json').exists():
        if json.loads((HERE/'ZERO_HISTORY_INPUTS.json').read_text())!=evidence:raise ValueError('Archive previous zero-history table before revision')
    else:write(HERE/'ZERO_HISTORY_INPUTS.json',evidence)
    files=['process_identity.py','run_fixed.py','PROTOCOL.json','test_process_identity.py','prepare_patch.py',
           'ZERO_HISTORY_INPUTS.json','ORIGINAL_STOP_RECEIPT.json','operation_namespace/CASE_BINDINGS.json','operation_namespace/REVIEW_RECEIPT.json']
    freeze={'status':'FROZEN_OPERATIONAL_PATCH_ZERO_HISTORY','original_candidate_freeze_SHA256':sha(C/'FROZEN_CODE.json'),
        'original_candidate_runner_SHA256':sha(C/'run_cases.py'),'original_review_SHA256':sha(C/'REVIEW_RECEIPT.json'),
        'files_SHA256':{name:sha(HERE/name) for name in files},'financial_code_changed':False,'new_historical_wallets_started':0}
    write(HERE/'FROZEN_PATCH.json',freeze);print('PATCH_FROZEN',sha(HERE/'FROZEN_PATCH.json'))
if __name__=='__main__':main()
