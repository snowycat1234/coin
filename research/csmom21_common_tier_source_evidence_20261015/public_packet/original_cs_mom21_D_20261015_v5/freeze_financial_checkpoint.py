"""Seal only code/metadata. No source, account, authority or claim creation."""
from hashlib import sha256
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent

def pin(path):
    raw=path.read_bytes();return dict(SHA256=sha256(raw).hexdigest(),bytes=len(raw))

def seal():
    old=json.loads((ROOT/'original_cs_mom21_D_20261015_v4/FINANCIAL_CODE_MANIFEST.json').read_bytes())
    names=set(old['files'])|{'cs_verified_wires.py','cs_supersession.py','FAILED_ATTEMPT_SUPERSESSION_PACKET.json',
        'test_worker_integration.py','test_cs_verified.py','freeze_financial_checkpoint.py'}
    deps=old['dependencies'].copy()
    packet=json.loads((HERE/'FAILED_ATTEMPT_SUPERSESSION_PACKET.json').read_bytes())
    for name,p in packet['evidence'].items():deps[name]=p
    for p in packet['failed_claims'].values():deps[p['path']]={k:p[k] for k in ('SHA256','bytes')}
    for name,expected in deps.items():
        if pin(ROOT/name)!=expected:raise ValueError('EXACT_FROZEN_DEPENDENCY_CHANGED:'+name)
    value=dict(old,files={n:pin(HERE/n) for n in sorted(names)},dependencies=deps,
        predecessor_financial_code_manifest_SHA256=sha256((ROOT/'original_cs_mom21_D_20261015_v4/FINANCIAL_CODE_MANIFEST.json').read_bytes()).hexdigest(),
        repair_scope='PREVERIFIED_IMMUTABLE_GO_BINDING_OUTSIDE_UNCHANGED_SOURCE_GUARD_AND_MANUAL_APPEND_ONLY_FAILED_CLAIM_SUPERSESSION')
    (HERE/'FINANCIAL_CODE_MANIFEST.json').write_text(json.dumps(value,sort_keys=True,indent=2)+'\n')
    print(pin(HERE/'FINANCIAL_CODE_MANIFEST.json'))
if __name__=='__main__':seal()
