"""Pinned normal-Git byte recovery into this study's own external directory."""
from pathlib import Path
import hashlib,json,subprocess
REPO=Path(__file__).resolve().parents[2]
STATE=Path('/workspace/coin-cloud/csh-execution-stress-20261013')
CACHE=STATE/'git-bytes'
CODE='accda281f1da8bdcbf10d23a1e569acda58deb62'
FINE='a5471d18a58315b9eac17aa1e69c4c5f2657849a'
FULL2021='3f3a5db3b5f1f276bc642890c57c39772f11c0f3'
STRATEGY2021='c8a9de4c21ac4d77980d09b4e7d98ec58ec556da'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def write(path,raw):
 path.parent.mkdir(parents=True,exist_ok=True)
 if path.exists():assert path.read_bytes()==raw,path
 else:path.write_bytes(raw)
 return path

def get(commit,path,expected=None):
 assert len(commit)==40 and not any(x in path.lower().split('/') for x in ('holdout','locked'))
 CACHE.mkdir(parents=True,exist_ok=True)
 cache=CACHE/(sha((commit+':'+path).encode())+'.blob')
 if cache.exists():raw=cache.read_bytes()
 else:
  check=subprocess.run(['git','cat-file','-e',commit+'^{commit}'],cwd=REPO,capture_output=True)
  if check.returncode:
   subprocess.run(['git','fetch','--depth=1','--filter=blob:none','--no-tags','origin',commit],cwd=REPO,check=True)
  p=subprocess.run(['git','show',commit+':'+path],cwd=REPO,capture_output=True)
  if p.returncode:
   write(STATE/'failures'/(sha((commit+path).encode())+'.json'),json.dumps(dict(commit=commit,path=path,stderr=p.stderr.decode(),status='FAILED_GIT_READ')).encode())
   raise RuntimeError(p.stderr.decode())
  raw=p.stdout;write(cache,raw)
 if expected is not None:assert sha(raw)==expected,(commit,path,sha(raw),expected)
 return raw

def jsonget(c,p):return json.loads(get(c,p))
def materialize_code():
 root=STATE/'pinned-repo';manifest=jsonget(CODE,'research/static50-sma-20261013/LOCAL_CODE_MANIFEST_2025.json');records=[]
 files=set(manifest['sha256'])|{'research/static50-sma-20261013/LOCAL_CODE_MANIFEST.json','research/static50-sma-20261013/LOCAL_CODE_MANIFEST_2025.json','src/quant/__init__.py','src/quant/backtest.py','src/quant/data.py','src/quant/research.py'}
 tree=subprocess.check_output(['git','ls-tree','-r','--name-only',CODE,'modules/collector_research/pipeline'],cwd=REPO,text=True)
 files.update(p for p in tree.splitlines() if p.endswith('.py'));files.add('modules/collector_research/config.env')
 for path in sorted(files):
  raw=get(CODE,path,manifest['sha256'].get(path));write(root/path,raw)
  records.append(dict(commit=CODE,path=path,relative_destination=str((root/path).relative_to(STATE)),sha256=sha(raw),bytes=len(raw)))
 for name in ('fine_account.py','freeze_bootstrap.py','FROZEN_CODE.json','REVIEW_RECEIPT.json','FINE_PROFILE.json','CASE_BINDINGS.json','PROTOCOL.md','test_pure.py','run_cases.py','preflight.py'):
  path='research/quantity-resolution-sensitivity-20261013/'+name;raw=get(FINE,path);write(STATE/'fine-code'/name,raw)
  records.append(dict(commit=FINE,path=path,relative_destination='fine-code/'+name,sha256=sha(raw),bytes=len(raw)))
 for y,c,path in ((2021,STRATEGY2021,'research/core5-2021-strategy-20261013/targets/Y2021.npz'),(2023,CODE,'research/static50-sma-20261013/input/Y2023.npz'),(2025,CODE,'research/static50-sma-20261013/input/Y2025.npz')):
  raw=get(c,path);write(STATE/'targets'/f'Y{y}.npz',raw);records.append(dict(commit=c,path=path,relative_destination=f'targets/Y{y}.npz',sha256=sha(raw),bytes=len(raw)))
 write(REPO/'research/csh-execution-stress-20261013/PINNED_CODE_AND_TARGETS.json',json.dumps(records,indent=2).encode()+b'\n')
 print('PINNED_CODE_TARGETS_READY',len(records),flush=True)
if __name__=='__main__':materialize_code()
