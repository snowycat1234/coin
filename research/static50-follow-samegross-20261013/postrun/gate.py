"""Separate parent-reviewed postrun GO, never inherited from historical GO."""
from __future__ import annotations
import json
import os
import resource
import sys
from pathlib import Path
from provenance import HERE, MODULE, STATE, CASE_IDS, PINS, TERMINAL_PINS, sha, verify_terminal_run

FILES = frozenset({'provenance.py', 'gate.py', 'cold_audit.py', 'audit_all.py',
                   'build_report.py', 'test_observer.py', 'test_report.py', 'PROTOCOL.md'})


def verify_code_manifest(here: Path = HERE) -> dict:
    manifest = json.loads((here / 'REVIEWED_POSTRUN_CODE.json').read_text())
    if (manifest.get('kind') != 'PREPARED_SIX_CASE_ZERO_ADVANCE_SAMEGROSS_OBSERVER'
            or set(manifest.get('files_SHA256', {})) != FILES
            or manifest.get('case_ids') != list(CASE_IDS)
            or manifest.get('frozen_samegross_manifest_SHA256') != PINS['FROZEN_CODE.json']
            or manifest.get('independent_pre_GO_receipt_SHA256') != PINS['REVIEW_RECEIPT.json']
            or manifest.get('terminal_inputs_SHA256') != TERMINAL_PINS
            or manifest.get('historical_observer_executions_during_preparation') != 0):
        raise ValueError('Postrun code manifest identity differs')
    for name, digest in manifest['files_SHA256'].items():
        if (here / name).is_symlink() or sha(here / name) != digest:
            raise ValueError('Reviewed postrun bytes changed: ' + name)
    for locator,digest in manifest['terminal_inputs_SHA256'].items():
        path=HERE.parent/locator
        if path.is_symlink() or sha(path)!=digest:
            raise ValueError('Frozen terminal input changed: '+locator)
    return manifest


def verify_observer_go(stage: str, here: Path = HERE, state: Path = STATE) -> dict:
    if stage not in ('AUDIT', 'REPORT'):
        raise ValueError('Unknown postrun action')
    verify_code_manifest(here)
    receipt_path = here / 'POSTRUN_REVIEW_RECEIPT.json'
    go_path = here / 'POSTRUN_GO.json'
    receipt = json.loads(receipt_path.read_text())
    manifest_sha = sha(here / 'REVIEWED_POSTRUN_CODE.json')
    if (receipt.get('status') != 'PASS_INDEPENDENT_POSTRUN_PRE_EXECUTION_REVIEW'
            or receipt.get('manifest_SHA256') != manifest_sha
            or receipt.get('historical_observer_executions') != 0):
        raise RuntimeError('Separate independent review of exact observer code required')
    go = json.loads(go_path.read_text())
    if (go.get('parent_GO') is not True or stage not in go.get('approved_stages', [])
            or not set(go.get('approved_stages', [])) <= {'AUDIT', 'REPORT'}
            or go.get('manifest_SHA256') != manifest_sha
            or go.get('review_receipt_SHA256') != sha(receipt_path)
            or go.get('state_locator') != str(state.relative_to(HERE.parent))
            or go.get('run_binding_SHA256') != sha(state / 'RUN_BINDING.json')
            or go.get('controller_receipt_SHA256') != sha(state / 'RESOURCE_RECEIPTS.json')):
        raise RuntimeError('Separate parent GO for this terminal run and action required')
    verify_terminal_run(state=state, module=MODULE)
    return go


def require_bounded_worker(stage: str) -> None:
    go = verify_observer_go(stage)
    if (os.environ.get('FOLLOW_SAMEGROSS_POSTRUN_BOUNDED') != '1'
            or os.environ.get('FOLLOW_SAMEGROSS_POSTRUN_GO_SHA256') != sha(HERE / 'POSTRUN_GO.json')):
        raise RuntimeError('Observer must run through the bounded postrun orchestrator')
    if sys.flags.optimize:
        raise RuntimeError('Observer requires enabled frozen source assertions')
    address_limits = resource.getrlimit(resource.RLIMIT_AS)
    cpu_limits = resource.getrlimit(resource.RLIMIT_CPU)
    if (len(os.sched_getaffinity(0)) != 1
            or any(not 0 < limit <= 4_000_000_000 for limit in address_limits)
            or any(not 0 < limit <= 300 for limit in cpu_limits)):
        raise RuntimeError('Actual one-CPU/4GB-AS/300-second CPU observer bounds missing')
