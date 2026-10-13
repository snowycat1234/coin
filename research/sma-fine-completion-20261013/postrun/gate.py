"""Separate exact-byte review and parent GO before any postrun observer."""
from __future__ import annotations
import os
import resource
import sys
from pathlib import Path
from provenance import HERE, ROOT, MODULE, STATE, CASE_IDS, sha, read, safe_path, verify_terminal_run

FILES = frozenset({'provenance.py', 'gate.py', 'cold_audit.py', 'audit_all.py',
    'report_helpers.py', 'build_report.py', 'test_observer.py', 'test_report.py', 'PROTOCOL.md'})


def verify_code_manifest(here=HERE):
    manifest = read(here / 'REVIEWED_POSTRUN_CODE.json')
    if (manifest.get('kind') != 'PREPARED_FIXED_THREE_SMA_ZERO_ADVANCE_OBSERVER'
            or set(manifest.get('files_SHA256', {})) != FILES or manifest.get('case_ids') != list(CASE_IDS)
            or manifest.get('state_locator') != str(STATE.relative_to(ROOT))
            or manifest.get('cold_observers') != 3 or manifest.get('report_observers') != 1
            or any(manifest.get(k) != 0 for k in ('new_historical_wallets_to_open', 'financial_advances',
                'controls_to_rerun', 'historical_observer_executions_during_preparation'))
            or manifest.get('terminal_inputs_binding') != 'EXCLUSIVE_CREATE_AFTER_TERMINAL_HASH_BOUND_BY_POSTRUN_GO'):
        raise ValueError('Fixed observer code manifest differs')
    for name, digest in manifest['files_SHA256'].items():
        if (here / name).is_symlink() or sha(here / name) != digest:
            raise ValueError('Reviewed observer bytes changed: ' + name)
    for locator, digest in manifest['dependencies_SHA256'].items():
        if sha(safe_path(ROOT, locator)) != digest:
            raise ValueError('Frozen observer dependency changed: ' + locator)
    return manifest


def verify_observer_go(stage, here=HERE, state=STATE):
    if stage not in ('AUDIT', 'REPORT'):
        raise ValueError('Unknown observer action')
    verify_code_manifest(here)
    review_path = here / 'POSTRUN_REVIEW_RECEIPT.json'
    review, go = read(review_path), read(here / 'POSTRUN_GO.json')
    manifest_sha = sha(here / 'REVIEWED_POSTRUN_CODE.json')
    if (review.get('status') != 'PASS_INDEPENDENT_POSTRUN_PRE_EXECUTION_REVIEW'
            or review.get('manifest_SHA256') != manifest_sha or review.get('historical_observer_executions') != 0):
        raise RuntimeError('Separate independent exact-byte observer review required')
    if (go.get('parent_GO') is not True or stage not in go.get('approved_stages', [])
            or not set(go.get('approved_stages', [])) <= {'AUDIT', 'REPORT'}
            or len(go['approved_stages']) != len(set(go['approved_stages']))
            or go.get('manifest_SHA256') != manifest_sha or go.get('review_receipt_SHA256') != sha(review_path)
            or go.get('state_locator') != str(state.relative_to(ROOT))
            or go.get('run_binding_SHA256') != sha(state / 'RUN_BINDING.json')
            or go.get('controller_receipt_SHA256') != sha(state / 'RESOURCE_RECEIPTS.json')
            or go.get('terminal_inputs_SHA256') != sha(here / 'TERMINAL_INPUTS.json')
            or go.get('historical_controller_released') is not True):
        raise RuntimeError('Separate parent GO for terminal run/action required')
    verify_terminal_run(state=state, module=MODULE)
    return go


def require_bounded_worker(stage):
    verify_observer_go(stage)
    if (os.environ.get('COIN_SMA_FINE_POSTRUN_BOUNDED') != '1'
            or os.environ.get('COIN_SMA_FINE_POSTRUN_GO_SHA256') != sha(HERE / 'POSTRUN_GO.json')):
        raise RuntimeError('Observer requires bounded postrun orchestrator')
    if sys.flags.optimize:
        raise RuntimeError('Assertions must remain enabled')
    if (len(os.sched_getaffinity(0)) != 1
            or any(not 0 < n <= 4_000_000_000 for n in resource.getrlimit(resource.RLIMIT_AS))
            or any(not 0 < n <= 300 for n in resource.getrlimit(resource.RLIMIT_CPU))):
        raise RuntimeError('Actual one-CPU/4GB-AS/300-second CPU bounds missing')
