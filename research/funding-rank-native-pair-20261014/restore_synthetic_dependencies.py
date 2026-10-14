"""Restore small exact public code/identity/old-target-reference bytes; no market data.
Uses an existing same-origin Git cache. Optional fetch is explicit; refusal stops.
"""
import argparse,json,subprocess,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
def restore(cache,output,fetch_missing=False):
 manifest=json.loads((HERE/'SYNTHETIC_DEPENDENCIES.json').read_text());root=Path(output)
 if root.exists():raise ValueError('Fresh output required')
 root.mkdir(parents=True)
 for name,rec in manifest['files'].items():
  command=['git','show',rec['commit']+':'+rec['path']];q=subprocess.run(command,cwd=cache,capture_output=True)
  if q.returncode and fetch_missing:
   f=subprocess.run(['git','fetch','--no-tags','--depth=1','--filter=blob:none','https://github.com/snowycat1234/coin.git',rec['commit']],cwd=cache,capture_output=True)
   if f.returncode:raise RuntimeError(f.stderr.decode())
   q=subprocess.run(command,cwd=cache,capture_output=True)
  if q.returncode:raise RuntimeError(q.stderr.decode())
  if hashlib.sha256(q.stdout).hexdigest()!=rec['SHA256']:raise ValueError('Exact dependency bytes differ:'+name)
  p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(q.stdout)
 roots={'common':str(root/'common'),'workspace':str(root/'common/runtime_dependencies'),'repo':str(root/'common/runtime_dependencies/coin_native_half_mix_20261013/repo')}
 (root/'SYNTHETIC_ROOTS.json').write_text(json.dumps(roots,indent=2)+'\n');return root/'SYNTHETIC_ROOTS.json'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--git-cache',required=True);p.add_argument('--output',required=True);p.add_argument('--fetch-missing',action='store_true');a=p.parse_args();print(restore(a.git_cache,a.output,a.fetch_missing))
