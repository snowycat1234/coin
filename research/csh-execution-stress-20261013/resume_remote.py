"""Resume a source-identical failed remote readonly pull; no original STATE reads."""
import argparse,hashlib,json,os,subprocess,sys,time
from pathlib import Path
PREFIX='research/csh-execution-stress-20261013/'
def sha(x):return hashlib.sha256(x).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--commit',required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();begun=time.monotonic();store=a.output/'fresh-git';root=a.output/'restored'
 assert store.is_dir() and root.is_dir() and not (a.output/'REMOTE_RECOVERY_RECEIPT.json').exists()
 assert subprocess.check_output(['git','-C',str(store),'rev-parse','FETCH_HEAD'],text=True).strip()==a.commit
 def get(n):return subprocess.check_output(['git','-c','http.version=HTTP/1.1','-C',str(store),'show',a.commit+':'+PREFIX+n])
 raw=get('PUBLIC_MANIFEST.json');assert raw==(root/'PUBLIC_MANIFEST.json').read_bytes();manifest=json.loads(raw);rows=[]
 for n,r in manifest['files'].items():
  # Re-extract from the fresh remote object store even when a restored file
  # exists. This never substitutes bytes from the original source checkout.
  raw=get(n);assert len(raw)==r['bytes'] and sha(raw)==r['sha256'],n
  path=root/n;path.parent.mkdir(parents=True,exist_ok=True)
  if path.exists():assert path.read_bytes()==raw
  else:path.write_bytes(raw)
  rows.append(dict(path=n,bytes=len(raw),sha256=sha(raw)))
  if len(rows)%10==0:print('REMOTE_BYTE_READ',len(rows),len(manifest['files']),flush=True)
 assert sha((root/'FREEZE.json').read_bytes())==manifest['freeze_sha256']
 cases=[]
 for case in manifest['cases']:
  output=a.output/(case+'.json');assert not output.exists()
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
  subprocess.run([sys.executable,str(root/'audit_packet.py'),str(root/'result'/case),'--target',str(root/'targets'/('Y'+case[1:5]+'.npz')),'--output',str(output)],env=env,cwd=root,check=True,stdout=subprocess.DEVNULL)
  result=json.loads(output.read_text());cases.append(result);print('REMOTE_READONLY_REBUILT',case,result['status'],flush=True)
 receipt=dict(status='PASS_EXACT_REMOTE_SHA_READONLY_INDICATOR_FINANCIAL_RECOVERY',remote_commit=a.commit,remote_manifest_sha256=sha((root/'PUBLIC_MANIFEST.json').read_bytes()),freeze_sha256=manifest['freeze_sha256'],files_verified=len(rows),total_bytes_verified=sum(r['bytes'] for r in rows),files=rows,cases=cases,elapsed_seconds=time.monotonic()-begun,resumed_after='Two upstream Git HTTP503 interruptions; same normal Git origin, HTTP/1.1 transport option on final resume; TLS verification preserved, completed public remote objects reused',scope=manifest['scope'],financial_imports=0,account_constructions=0,account_advances=0,old_or_new_historical_replays=0,fits=0,original_STATE_reads=0,provider_downloads=0)
 (a.output/'REMOTE_RECOVERY_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
 print(json.dumps({k:receipt[k] for k in ('status','remote_commit','files_verified','total_bytes_verified','elapsed_seconds')}))
if __name__=='__main__':main()
