"""Stdlib-only freeze; independent review required only for historical launch."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
PORT_ROOT='coin_native_half_mix_20261013/repo/'
PORT_MANIFEST_COUNTS={
    PORT_ROOT+'research/static50-sma-20261013/LOCAL_CODE_MANIFEST.json':26,
    PORT_ROOT+'research/static50-sma-20261013/LOCAL_CODE_MANIFEST_2025.json':28,
}

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify(root=HERE,require_review=False):
    root=Path(root).resolve();p=root/'FROZEN_CODE.json';m=json.loads(p.read_text())
    if (m['status']!='PREPARED_ONLY_ZERO_HISTORY_PENDING_REVIEW_AND_GO'
            or m['bootstrap_SHA256']!=sha(root/'samegross_freeze.py')):
        raise ValueError('Same-gross freeze bootstrap changed')
    for name,expected in m['files_SHA256'].items():
        q=root/name
        if q.is_symlink() or sha(q)!=expected: raise ValueError('Prepared bytes changed: '+name)
    for name,expected in m['dependencies_SHA256'].items():
        q=root.parent/name
        if q.is_symlink() or sha(q)!=expected: raise ValueError('Frozen dependency changed: '+name)
    # Verify the entire original port-declared dependency closure BEFORE the
    # runner execs either port, whose module-level imports include finance.
    required={'coin_expanded_coverage_20261013/window_2024.py'}
    union={}
    for locator,count in PORT_MANIFEST_COUNTS.items():
        if locator not in m['dependencies_SHA256']:
            raise ValueError('Import-before-freeze port manifest is missing: '+locator)
        port=json.loads((root.parent/locator).read_text())
        if len(port['sha256'])!=count:
            raise ValueError('Original port dependency count changed')
        required.add(locator)
        for relative,expected in port['sha256'].items():
            name=PORT_ROOT+relative
            if name in union and union[name]!=expected:
                raise ValueError('Conflicting frozen port dependency')
            union[name]=expected
            if m['dependencies_SHA256'].get(name)!=expected:
                raise ValueError('Import-before-freeze dependency omitted: '+name)
    if len(union)!=28 or not required.issubset(m['dependencies_SHA256']):
        raise ValueError('Original port/window dependency closure is incomplete')
    if m['dependency_closure']!={'port_manifest_counts':PORT_MANIFEST_COUNTS,
                                'unique_port_entries':28,
                                'dependencies_total':len(m['dependencies_SHA256'])}:
        raise ValueError('Frozen dependency closure inventory mismatch')
    if require_review:
        rp=root/'REVIEW_RECEIPT.json'
        if not rp.exists(): raise RuntimeError('Independent exact-byte review required before parent GO')
        r=json.loads(rp.read_text())
        if (r['status']!='PASS_INDEPENDENT_PRE_GO_REVIEW' or r['new_historical_wallets_executed']!=0
                or r['freeze_manifest_SHA256']!=sha(p) or r['bootstrap_SHA256']!=sha(root/'samegross_freeze.py')):
            raise RuntimeError('Independent review is not bound to these exact prepared bytes')
    return {'freeze_manifest_SHA256':sha(p),'files_SHA256':m['files_SHA256'],
            'dependencies_SHA256':m['dependencies_SHA256']}
