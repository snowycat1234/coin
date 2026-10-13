"""Same-process operational shim; original frozen controller/worker are reused."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
OPERATION=HERE/'operation_namespace'
DEFAULT_CANDIDATE=HERE.parent/'coin_headroom_risk_candidate_20261013'
from process_identity import fixed_external_observation

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())

def verify_patch(candidate,require_review=False):
    freeze=read(HERE/'FROZEN_PATCH.json')
    if freeze['original_candidate_freeze_SHA256']!=sha(candidate/'FROZEN_CODE.json'):
        raise ValueError('Exact original candidate freeze required')
    for name,h in freeze['files_SHA256'].items():
        if sha(HERE/name)!=h:raise ValueError('Operational patch bytes changed: '+name)
    if require_review:
        r=read(HERE/'PATCH_REVIEW_RECEIPT.json');p=read(HERE/'PATCH_PUBLICATION_RECEIPT.json')
        if r.get('status')!='PASS_INDEPENDENT_PROCESS_IDENTITY_PATCH' or r.get('patch_freeze_SHA256')!=sha(HERE/'FROZEN_PATCH.json') or r.get('new_historical_wallets_executed')!=0:
            raise RuntimeError('Independent exact process patch review required')
        if p.get('status')!='PASS_EXACT_OPERATIONAL_PATCH_REMOTE_PUBLICATION' or p.get('remote_verified') is not True or p.get('patch_freeze_SHA256')!=sha(HERE/'FROZEN_PATCH.json') or p.get('review_receipt_SHA256')!=sha(HERE/'PATCH_REVIEW_RECEIPT.json'):
            raise RuntimeError('Exact operational patch remote publication required')
    return freeze

def require_original_zero_history(candidate,state):
    evidence=read(HERE/'ZERO_HISTORY_INPUTS.json')
    if str(state.resolve())!=evidence['original_state_root']:
        raise ValueError('Exact original aborted state required')
    for name,h in evidence['original_files_SHA256'].items():
        p=candidate/name
        if p.is_symlink() or sha(p)!=h:raise ValueError('Original STOP/reservation bytes changed: '+name)
    old=read(state/'RUN_BINDING.json');stop=read(state/'RESOURCE_RECEIPTS.json')
    expected=['Y2021_STATIC50_FINE_HEADROOM','Y2023_STATIC50_FINE_HEADROOM']
    if old['fine_case_ids']!=expected or stop['status']!='STOP_PARTIAL' or stop['unstarted_case_ids']!=expected[1:]:
        raise ValueError('Only original reserved2021/2023 cases may continue')
    for identity in expected:
        if (state/identity).exists() or (state/identity).is_symlink():
            raise RuntimeError('Any original account directory blocks zero-history recovery')
        log=state/(identity+'.log')
        if log.is_symlink() or log.exists() and log.stat().st_size!=0:
            raise RuntimeError('Nonempty original worker log blocks zero-history recovery')
    return {'status':'PASS_ORIGINAL_ACCOUNT_DIRECTORIES_AND_CHECKPOINTS_ABSENT',
            'original_aborted_state_unchanged':True,'historical_wallets_started':0}

def load_original(candidate,workspace):
    sys.path.insert(0,str(candidate))
    spec=importlib.util.spec_from_file_location('exact_original_headroom_runner',candidate/'run_cases.py')
    run=importlib.util.module_from_spec(spec);spec.loader.exec_module(run)
    run.verify_reviewed_freeze(workspace,require_review=True);run.preflight.require_publication()
    gspec=importlib.util.spec_from_file_location('exact_original_guard_resource',workspace/'coin_margin_protective_runner_20261013/run_guard_cases.py')
    run.guard=importlib.util.module_from_spec(gspec);gspec.loader.exec_module(run.guard)
    run.guard.require_assertions_enabled()
    gate=run.resource_gate
    gate.external_observation=lambda proc_root=Path('/proc'):fixed_external_observation(gate,proc_root)
    # Only the one-shot operational namespace changes. Identical CASE_BINDINGS
    # and original review bytes keep the original worker's exact checks intact.
    # Module __file__, worker subprocess path and all financial methods stay
    # the original frozen candidate. The failed original marker stays intact.
    if sha(OPERATION/'CASE_BINDINGS.json')!=sha(candidate/'CASE_BINDINGS.json') or sha(OPERATION/'REVIEW_RECEIPT.json')!=sha(candidate/'REVIEW_RECEIPT.json'):
        raise ValueError('Original binding/review transport copies changed')
    run.HERE=OPERATION
    return run

def require_cloud_unstarted(candidate):
    if (candidate/'HISTORICAL_LAUNCH.json').exists() or (candidate/'HISTORICAL_LAUNCH.json').is_symlink():
        raise RuntimeError('Original cloud candidate already reserved or started')
    for p in candidate.glob('state*'):
        if p.is_symlink():raise RuntimeError('Unknown original cloud state symlink')
        if p.is_dir() and ((p/'RUN_BINDING.json').exists() or any(p.glob('*/BINDING.json')) or any(p.glob('*/recovery/POINTER.json'))):
            raise RuntimeError('Original cloud account/state evidence blocks duplicate2024')
    if any(candidate.glob('Y2024*_FINE_HEADROOM')):
        raise RuntimeError('Original cloud2024 account directory exists')
    return {'status':'PASS_ORIGINAL_CLOUD_CANDIDATE_UNSTARTED','historical_wallets_started':0}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--candidate-root',type=Path,default=DEFAULT_CANDIDATE)
    parser.add_argument('--workspace-root',type=Path,default=HERE.parent)
    parser.add_argument('--executor',choices=['local','cloud'],required=True)
    parser.add_argument('--original-zero-state',type=Path)
    parser.add_argument('--check-only',action='store_true');parser.add_argument('--parent-go',action='store_true')
    parser.add_argument('--source-root',type=Path);parser.add_argument('--target-archive',type=Path)
    parser.add_argument('--feature-archive',type=Path);parser.add_argument('--state-root',type=Path)
    args=parser.parse_args();candidate=args.candidate_root.resolve();workspace=args.workspace_root.resolve()
    args.years=[2021,2023] if args.executor=='local' else [2024]
    args.workspace_root=workspace;os.environ['COIN_HEADROOM_WORKSPACE']=str(workspace)
    verify_patch(candidate,require_review=not args.check_only)
    if args.executor=='local':
        if args.original_zero_state is None:parser.error('Local recovery requires exact original zero-account state')
        zero=require_original_zero_history(candidate,args.original_zero_state.resolve())
    else:
        if args.original_zero_state is not None:parser.error('Cloud is only one original fresh2024 case')
        zero=require_cloud_unstarted(candidate)
    run=load_original(candidate,workspace)
    if args.executor=='local':
        # The aborted launch consumed0.006303863 wall seconds. Charge a full
        # second conservatively to every local remaining case rather than
        # granting a fresh1200-second original-case budget.
        run.guard.CPU_LIMIT=1199
        run.guard.WALL_LIMIT=1199
    if args.check_only:
        if args.parent_go or args.state_root:parser.error('Check-only cannot start or create a wallet')
        report=run.preflight.check(workspace,args.years,args.source_root,args.target_archive,args.feature_archive)
        report.update(operation='PROCESS_IDENTITY_PATCH_ONLY',zero_history=zero,
            external_processes=run.resource_gate.external_observation()['prior_historical_processes'])
        print(json.dumps(report,indent=2));return
    if not args.parent_go or args.state_root is None:parser.error('Separate conditional parent GO and fresh state required')
    if args.executor=='local' and any(v is not None for v in (args.source_root,args.target_archive,args.feature_archive)):
        parser.error('Local exact21/23 continuation uses original bound inputs')
    with run.resource_gate.controller_lock():run.controller(args,run.preflight.bindings())

if __name__=='__main__':main()
