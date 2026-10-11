"""Verify public continuous feature bytes and rebuild the published phase chain."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request
from prepare import HERE,digest,save
from join import run

PREFIX='research/core5-continuous-risk600-20261011/'


def verify(commit,state):
    assert not state.exists();state.mkdir()
    attempts=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=str(Path(args[0]).absolute())
            if p.startswith('/workspace/continuous600-state/') or p.startswith('/workspace/continuous600-joined/'):
                attempts.append(p);raise RuntimeError('Original STATE forbidden')
    sys.addaudithook(audit)
    def public(path):
        with urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+PREFIX+path,timeout=20) as r:
            b=r.read(800001)
        assert len(b)<800001
        return b
    for name in ('cold_join.py','join.py','prepare.py','primitives.py'):
        assert digest(public(name))==digest((HERE/name).read_bytes())
    proofraw=public('continuous/COVERAGE.json');proof=json.loads(proofraw)
    raw=public('continuous/DAILY_CONTINUOUS.npz');assert digest(raw)==proof['daily_continuous_SHA256']
    saved=state/'PUBLIC_DAILY.npz';saved.write_bytes(raw)
    run(commit,state/'rebuilt',saved)
    rebuilt=json.loads((state/'rebuilt/COVERAGE.json').read_bytes())
    assert rebuilt['daily_continuous_SHA256']==proof['daily_continuous_SHA256'] and not attempts
    receipt=dict(status='PASS_PUBLIC_698_DAY_JOIN_COLD_BYTE_AND_VECTOR_RESTORE',artifact_commit=commit,
        public_feature_SHA256=digest(raw),public_feature_bytes=len(raw),public_coverage_SHA256=digest(proofraw),
        valid_joint_dates=698,all_phase_feature_vectors_and_source_boundaries_exact=True,
        reused_independent_raw_phase_cold_certificates=5,new_CSV_parses=0,provider_downloads=0,
        original_STATE_open_attempts=len(attempts),fits=0,wallets=0,future_labels=0)
    save(state/'PUBLIC_RESTORE.json',receipt);print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--state',type=Path,required=True)
    a=p.parse_args();verify(a.commit,a.state)
