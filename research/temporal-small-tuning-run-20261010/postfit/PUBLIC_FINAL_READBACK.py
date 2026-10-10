"""Read back already-published research bytes; no data acquisition or economics."""
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path


if __name__ == '__main__':
    repo = Path('/workspace/coin-temporal')
    output = Path('/workspace/coin-state/work/temporal-two-expert-20261009/small-tuning-run')
    prefix = 'research/temporal-small-tuning-run-20261010/'
    commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()
    manifest = json.loads((repo/prefix/'PUBLIC_MANIFEST.json').read_text())
    names = list(manifest['files'])+['PUBLIC_MANIFEST.json']
    receipt = repo/prefix/'FINAL_PUBLIC_READBACK.json'
    if receipt.exists():
        names.append(receipt.name)

    def verify(name):
        url = f'https://raw.githubusercontent.com/snowycat1234/coin/{commit}/{prefix}{name}'
        with urllib.request.urlopen(url,timeout=15) as response:
            body = response.read()
        expected = (repo/prefix/name).read_bytes()
        digest = hashlib.sha256(body).hexdigest()
        if body != expected:
            raise ValueError('Public bytes differ:'+name)
        if name in manifest['files'] and manifest['files'][name] != dict(bytes=len(body),SHA256=digest):
            raise ValueError('Manifest differs:'+name)
        return dict(file=prefix+name,bytes=len(body),SHA256=digest)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(verify,names))
    refs = subprocess.check_output(['git','ls-remote','origin','refs/heads/main','refs/heads/research/temporal-two-expert-20261009'],cwd=repo,text=True).splitlines()
    if not any(x.startswith(commit+'\t') and x.endswith('research/temporal-two-expert-20261009') for x in refs):
        raise ValueError('Remote research head differs')
    if not any(x.startswith('ef67d636a51fd3fa9e804f651aab5775f6bae5f8\t') and x.endswith('/main') for x in refs):
        raise ValueError('Remote main changed')
    result = dict(status='ALL_PUBLIC_BYTES_AND_REMOTE_HEAD_VERIFIED',commit=commit,files=results,public_files=len(results),bytes=sum(r['bytes'] for r in results),main_unchanged=True,optimizer_updates=0,model_inferences=0,wallet_rollouts=0,reserve_read=False)
    with (output/f'FINAL_PUBLIC_READBACK_{commit[:7]}.json').open('x') as stream:
        stream.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
