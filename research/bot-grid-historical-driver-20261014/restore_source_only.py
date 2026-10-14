"""Exact code/metadata restoration only. Never fetches or opens market data."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest-sha',required=True);p.add_argument('--base',required=True)
 p.add_argument('--metadata-only',action='store_true');a=p.parse_args()
 raw=(HERE/'SOURCE_TRANSPORT_MANIFEST.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=a.manifest_sha:raise ValueError('EXACT_TRANSPORT_MANIFEST_REQUIRED')
 manifest=json.loads(raw);base=Path(a.base).resolve()
 selected={n:r for n,r in manifest['files'].items() if n.startswith('coin_bot_historical_driver_preparation_revision_20261014/') or n in manifest['source_only_dependencies'] or n=='INDEPENDENT_PREPARATION_REVIEW.json'}
 for name,r in manifest['files'].items():
  relative=Path(name)
  if relative.is_absolute() or '..' in relative.parts or (HERE/relative).is_symlink():raise ValueError('SAFE_PUBLIC_RELATIVE_PATH_REQUIRED')
  path=HERE/relative;data=path.read_bytes()
  if len(data)!=r['bytes'] or hashlib.sha256(data).hexdigest()!=r['SHA256']:raise ValueError('TRANSPORT_BYTES_CHANGED:'+name)
 for name in selected:
  target=base/name
  if target.exists():
   if target.is_symlink() or hashlib.sha256(target.read_bytes()).hexdigest()!=selected[name]['SHA256']:raise ValueError('EXISTING_CONSUMER_FILE_DIFFERS:'+name)
   continue
  target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(HERE/name,target)
 print(json.dumps(dict(status='PASS_CODE_ONLY_SOURCE_RESTORE',files=len(selected),historical_arrays=0,wallets=0)))
 if a.metadata_only:
  command=[sys.executable,'-B',str(base/'coin_bot_historical_driver_preparation_revision_20261014/run_verified.py'),'--preparation-manifest-sha',manifest['preparation_manifest_SHA256'],'metadata']
  result=subprocess.run(command,check=True,capture_output=True,text=True)
  value=json.loads(result.stdout)
  if value.get('status')!='METADATA_ONLY_NO_ARRAY_OR_WALLET':raise ValueError('METADATA_ONLY_STATUS_REQUIRED')
  print(json.dumps(dict(status='PASS_RESTORED_METADATA_ONLY',historical_arrays=0,wallets=0)))
 return 0

if __name__=='__main__':raise SystemExit(main())
