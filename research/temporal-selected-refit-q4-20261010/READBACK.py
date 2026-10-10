"""Byte readback of existing published deliverables; no provider downloads."""
import argparse
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
repo = Path('/workspace/coin-temporal')
commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
names = subprocess.check_output(['git','ls-tree','-r','--name-only',commit,
    'modules/temporal_selected_refit','modules/temporal_q4_reserved',
    'research/temporal-selected-refit-q4-20261010','docs/RESEARCH_STATUS.md',
    'docs/OPEN_SOURCE_REGISTRY.md','docs/RESEARCH_DECISION_LOG.md'],cwd=repo,text=True).splitlines()
def verify(name):
    with urllib.request.urlopen(f'https://raw.githubusercontent.com/snowycat1234/coin/{commit}/{name}', timeout=15) as response:
        body=response.read()
    expected=subprocess.check_output(['git','show',f'{commit}:{name}'],cwd=repo)
    if body != expected:
        raise ValueError('Published bytes differ:'+name)
    return dict(file=name, bytes=len(body), SHA256=hashlib.sha256(body).hexdigest())
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    records=list(pool.map(verify,names))
refs=subprocess.check_output(['git','ls-remote','origin','refs/heads/main',
    'refs/heads/research/temporal-two-expert-20261009'],cwd=repo,text=True).splitlines()
assert any(r.startswith(commit+'\t') and r.endswith('/temporal-two-expert-20261009') for r in refs)
assert any(r.startswith('ef67d636a51fd3fa9e804f651aab5775f6bae5f8\t') and r.endswith('/main') for r in refs)
result=dict(status='ALL_PUBLIC_BYTES_AND_REMOTE_HEAD_VERIFIED',commit=commit,files=records,
    public_files=len(records),bytes=sum(r['bytes'] for r in records),main_unchanged=True,
    optimizer_updates=0,model_inferences=0,wallet_rollouts=0)
with args.output.open('x') as stream:
    stream.write(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='files'}))
