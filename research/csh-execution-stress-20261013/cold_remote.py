"""Fresh normal-Git read of a published exact SHA; no checkout or financial advance."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
PREFIX='research/csh-execution-stress-20261013/'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
 assert len(a.commit)==40 and not a.output.exists();a.output.mkdir(parents=True);begun=time.monotonic();gitdir=a.output/'fresh-git';gitdir.mkdir()
 subprocess.run(['git','init','--quiet',str(gitdir)],check=True)
 subprocess.run(['git','-C',str(gitdir),'remote','add','origin','https://github.com/snowycat1234/coin.git'],check=True)
 subprocess.run(['git','-C',str(gitdir),'fetch','--quiet','--depth=1','--filter=blob:none','--no-tags','origin',a.commit],check=True)
 head=subprocess.check_output(['git','-C',str(gitdir),'rev-parse','FETCH_HEAD'],text=True).strip();assert head==a.commit
 root=a.output/'restored';root.mkdir()
 def get(path):
  assert path.startswith(PREFIX)
  return subprocess.check_output(['git','-C',str(gitdir),'show',a.commit+':'+path])
 raw=get(PREFIX+'PUBLIC_MANIFEST.json');manifest=json.loads(raw);(root/'PUBLIC_MANIFEST.json').write_bytes(raw)
 # This is the independently reviewed local verifier's expected manifest identity;
 # the remote manifest additionally binds each individual remote file.
 rows=[]
 for n,r in manifest['files'].items():
  raw=get(PREFIX+n);assert len(raw)==r['bytes'] and sha(raw)==r['sha256'],n
  q=root/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw);rows.append(dict(path=n,bytes=len(raw),sha256=sha(raw)))
 verifier=root/'audit_packet.py';original=Path(__file__).with_name('audit_packet.py');assert sha(verifier.read_bytes())==sha(original.read_bytes())
 freeze=sha((root/'FREEZE.json').read_bytes());assert freeze==manifest['freeze_sha256']
 # Every case is audited in a fresh interpreter using the remotely-read verifier.
 # It only reads the restored packet/target; no original STATE path is supplied.
 cases=[]
 for identity in manifest['cases']:
  year=identity[1:5];result=a.output/(identity+'.json');env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',POLARS_MAX_THREADS='1')
  command=[sys.executable,str(verifier),str(root/'result'/identity),'--target',str(root/'targets'/('Y'+year+'.npz')),'--output',str(result)]
  subprocess.run(command,env=env,cwd=root,check=True,stdout=subprocess.DEVNULL)
  cases.append(json.loads(result.read_text()))
 receipt=dict(status='PASS_EXACT_REMOTE_SHA_READONLY_RECOVERY',remote_commit=a.commit,remote_manifest_sha256=sha((root/'PUBLIC_MANIFEST.json').read_bytes()),freeze_sha256=freeze,files_verified=len(rows),total_bytes_verified=sum(r['bytes'] for r in rows),files=rows,cases=cases,elapsed_seconds=time.monotonic()-begun,git_scope='Fresh object store; exact published SHA; no worktree/checkout',financial_imports=0,account_constructions=0,account_advances=0,old_or_new_historical_replays=0,fits=0,original_STATE_reads=0,provider_downloads=0)
 (a.output/'REMOTE_RECOVERY_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:receipt[k] for k in ('status','remote_commit','freeze_sha256','files_verified','total_bytes_verified','elapsed_seconds')}))
if __name__=='__main__':main()
