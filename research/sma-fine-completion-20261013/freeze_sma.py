"""Stdlib-only exact input/code admission before financial imports."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def verify(root=HERE,require_review=False):
    root=Path(root).resolve();path=root/'FROZEN_CODE.json'
    m=json.loads(path.read_text())
    if m['status']!='PREPARED_ONLY_ZERO_HISTORY_PENDING_REVIEW_AND_GO' or m['bootstrap_SHA256']!=sha(root/'freeze_sma.py'):
        raise ValueError('SMA fine freeze bootstrap changed')
    for name,expected in m['files_SHA256'].items():
        p=root/name
        if p.is_symlink() or sha(p)!=expected:raise ValueError('Prepared bytes changed: '+name)
    for name,expected in m['dependencies_SHA256'].items():
        p=root.parent/name
        if p.is_symlink() or sha(p)!=expected:raise ValueError('Frozen dependency changed: '+name)
    port_name='coin_native_half_mix_20261013/repo/research/static50-sma-20261013/LOCAL_CODE_MANIFEST.json'
    if port_name not in m['dependencies_SHA256']:raise ValueError('Port manifest missing before financial import')
    port=json.loads((root.parent/port_name).read_text())
    if len(port['sha256'])!=26:raise ValueError('Exact original port closure count')
    for relative,expected in port['sha256'].items():
        name='coin_native_half_mix_20261013/repo/'+relative
        if m['dependencies_SHA256'].get(name)!=expected:raise ValueError('Port closure omitted: '+name)
    if require_review:
        if not (root/'REVIEW_RECEIPT.json').is_file():
            raise RuntimeError('Exact-byte independent SMA fine review required before GO')
        r=json.loads((root/'REVIEW_RECEIPT.json').read_text())
        if (r.get('status')!='PASS_INDEPENDENT_PRE_GO_REVIEW' or r.get('new_historical_wallets_executed')!=0
                or r.get('freeze_manifest_SHA256')!=sha(path) or r.get('bootstrap_SHA256')!=sha(root/'freeze_sma.py')):
            raise RuntimeError('Exact-byte independent SMA fine review required before GO')
    return dict(freeze_manifest_SHA256=sha(path),files_SHA256=m['files_SHA256'],dependencies_SHA256=m['dependencies_SHA256'])
