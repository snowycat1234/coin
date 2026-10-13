"""Read-only known-project Git object recovery; no financial imports or advances."""
import argparse,datetime,hashlib,json,os,subprocess,time
from pathlib import Path
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--index',type=int,required=True);a=p.parse_args()
expected=json.loads((P/'REMOTE_BINARY_EXPECTED.json').read_text());f=expected['files'][a.index]
if not 0<=a.index<6 or not f['path'].startswith('research/causal-headroom-risk-20261013/postrun/local-fixed-21-23/finance/'):
 raise ValueError('Only six reviewed project binary paths')
out=P/'remote_binary_downloads'/f"{a.index}_{f['git_blob_sha']}"
event={'index':a.index,'path':f['path'],'git_blob_sha':f['git_blob_sha'],'source_commit':expected['commit']}
def log(stage,**extra):
 r={**event,**extra,'stage':stage,'time_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 with (P/'PUBLICATION_STAGE_EVENTS.jsonl').open('a') as s:s.write(json.dumps(r)+'\n')
 return r
log('PLAN_ONE_KNOWN_REMOTE_GIT_OBJECT_READ');begin=time.monotonic()
with out.open('xb') as dest:
 subprocess.run(['git','-C',str(P/'remote_finance_git'),'show',expected['commit']+':'+f['path']],stdout=dest,
  env={**os.environ,'GIT_TERMINAL_PROMPT':'0'},check=True,timeout=60)
b=out.read_bytes();h=hashlib.sha256(b).hexdigest()
if len(b)!=f['size'] or h!=f['SHA256']:raise ValueError('Actual remote bytes do not equal reviewed package')
print(json.dumps(log('REMOTE_GIT_BINARY_ACTUAL_BYTES_EXACT',size=len(b),SHA256=h,elapsed_seconds=time.monotonic()-begin,financial_advances=0)))
