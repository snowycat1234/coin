"""Exact common-code admission; paths are transport, bytes define identity."""
import hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(workspace=None,require_review=False):
    workspace=HERE.parent if workspace is None else Path(workspace)
    manifest=json.loads((HERE/'FROZEN_CODE.json').read_text())
    if manifest['bootstrap_SHA256']!=sha(HERE/'freeze_candidate.py'):
        raise ValueError('Candidate bootstrap bytes changed')
    for name,h in manifest['files_SHA256'].items():
        p=HERE/name
        if p.is_symlink() or sha(p)!=h:raise ValueError('Candidate frozen bytes changed: '+name)
    for name,h in manifest['dependencies_SHA256'].items():
        p=workspace/name
        if p.is_symlink() or sha(p)!=h:raise ValueError('Candidate frozen dependency changed: '+name)
    if require_review:
        r=json.loads((HERE/'REVIEW_RECEIPT.json').read_text())
        if r.get('status')!='PASS_INDEPENDENT_PRE_GO_REVIEW' or r.get('new_historical_wallets_executed')!=0 or r.get('freeze_manifest_SHA256')!=sha(HERE/'FROZEN_CODE.json'):
            raise RuntimeError('Independent exact-freeze review required before GO')
    return dict(freeze_manifest_SHA256=sha(HERE/'FROZEN_CODE.json'),**manifest)
