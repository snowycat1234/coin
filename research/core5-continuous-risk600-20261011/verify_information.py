"""Cold recompute the published descriptive result, with no new scientific fit."""
import argparse
import json
from pathlib import Path
import sys
import urllib.request
from prepare import HERE,digest,save
from information import run

PREFIX='research/core5-continuous-risk600-20261011/'


def verify(commit,state):
    assert not state.exists();state.mkdir();attempts=[]
    def audit(event,args):
        if event=='open' and isinstance(args[0],(str,bytes)):
            p=str(Path(args[0]).absolute())
            if any(p.startswith('/workspace/'+x+'/') for x in ('continuous600-state','continuous600-information','continuous600-joined')):
                attempts.append(p);raise RuntimeError('Original STATE forbidden')
    sys.addaudithook(audit)
    def public(path):
        with urllib.request.urlopen('https://raw.githubusercontent.com/snowycat1234/coin/'+commit+'/'+PREFIX+path,timeout=20) as r:
            b=r.read(800001)
        assert len(b)<800001
        return b
    for name in ('information.py','INFORMATION_PROTOCOL.json','prepare.py','primitives.py','join.py'):
        assert digest(public(name))==digest((HERE/name).read_bytes())
    raw=public('information/INFORMATION.json');expected=json.loads(raw)
    panel=public('information/TRAINING_SOURCE_COVARIANCE.npz');assert digest(panel)==expected['artifact_SHA256']
    run(expected['dataset_commit'],state/'rebuilt')
    actual=json.loads((state/'rebuilt/INFORMATION.json').read_bytes())
    assert digest((state/'rebuilt/TRAINING_SOURCE_COVARIANCE.npz').read_bytes())==digest(panel)
    for name,value in expected.items():
        if name!='elapsed_seconds':assert actual[name]==value,name
    assert not attempts
    save(state/'PUBLIC_RESTORE.json',dict(status='PASS_PUBLIC_TRAINING_INFORMATION_COLD_RECOMPUTATION',artifact_commit=commit,
        published_result_SHA256=digest(raw),published_covariance_SHA256=digest(panel),training_dates=637,
        all_descriptive_statistics_and_covariance_bytes_exact=True,original_STATE_open_attempts=len(attempts),
        new_scientific_attempts=0,new_fits=0,wallets=0,provider_downloads=0,future_labels=0))
    print((state/'PUBLIC_RESTORE.json').read_text())


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--state',type=Path,required=True)
    a=p.parse_args();verify(a.commit,a.state)
