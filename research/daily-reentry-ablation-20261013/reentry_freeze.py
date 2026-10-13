"""Stdlib-only byte binding before financial or historical imports."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FILES = frozenset({'daily_reentry_policy.py', 'run_cases.py', 'reentry_preflight.py',
                   'prefix_acceptance.py', 'resource_gate.py', 'test_synthetic.py',
                   'PROTOCOL.md', 'CASE_BINDINGS.json', 'GUARD_PACK_RELEASE.json'})

def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def verify(root: Path = HERE, *, require_review: bool = False) -> dict:
    root = Path(root).resolve()
    manifest_path = root / 'FROZEN_CODE.json'
    manifest = json.loads(manifest_path.read_text())
    if (manifest.get('status') != 'PREPARED_CODE_INPUTS_ZERO_HISTORY_PENDING_INDEPENDENT_REVIEW'
            or set(manifest.get('files_SHA256', {})) != FILES
            or manifest.get('bootstrap_SHA256') != sha(root / 'reentry_freeze.py')):
        raise ValueError('Daily-reentry code manifest invalid')
    for name, expected in manifest['files_SHA256'].items():
        path = root / name
        if path.is_symlink() or sha(path) != expected:
            raise ValueError(f'Daily-reentry prepared bytes changed: {name}')
    for locator, expected in manifest['dependencies_SHA256'].items():
        path = root.parent / locator
        if path.is_symlink() or sha(path) != expected:
            raise ValueError(f'Frozen dependency changed: {locator}')
    if require_review:
        receipt = json.loads((root / 'REVIEW_RECEIPT.json').read_text())
        if (receipt.get('status') != 'PASS_INDEPENDENT_PRE_GO_REVIEW'
                or receipt.get('new_historical_wallets_executed') != 0
                or receipt.get('freeze_manifest_SHA256') != sha(manifest_path)
                or receipt.get('bootstrap_SHA256') != sha(root / 'reentry_freeze.py')):
            raise RuntimeError('Independent review of exact prepared bytes required before GO')
    return {'freeze_manifest_SHA256': sha(manifest_path),
            'files_SHA256': manifest['files_SHA256'],
            'dependencies_SHA256': manifest['dependencies_SHA256']}
