"""Exact code/metadata restoration. No source projection or wallet admission."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent

def safe(base,name):
 relative=Path(name)
 if relative.is_absolute() or '..' in relative.parts:raise ValueError('SAFE_RELATIVE_CODE_PATH_REQUIRED')
 path=base/relative
 if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('SYMLINKED_CODE_DESTINATION_REFUSED')
 if not path.resolve().is_relative_to(base.resolve()):raise ValueError('CODE_PATH_ESCAPE')
 return path

def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest-sha',required=True);p.add_argument('--base',required=True);p.add_argument('--metadata-only',action='store_true');args=p.parse_args()
 raw=(HERE/'WALLET_TRANSPORT_MANIFEST.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=args.manifest_sha:raise ValueError('EXACT_TRANSPORT_MANIFEST_REQUIRED')
 manifest=json.loads(raw);base=Path(args.base)
 if not base.is_absolute() or any(p.is_symlink() for p in (base,*base.parents)):raise ValueError('ABSOLUTE_NONSYMLINK_CONSUMER_BASE_REQUIRED')
 for name,record in manifest['files'].items():
  path=safe(HERE,name)
  if path.suffix.lower() in ('.npz','.npy','.zip','.parquet','.arrow','.pyc'):raise ValueError('ARRAY_OR_BYTECODE_BODY_REFUSED')
  data=path.read_bytes()
  if len(data)!=record['bytes'] or hashlib.sha256(data).hexdigest()!=record['SHA256']:raise ValueError('EXACT_PUBLIC_CODE_BYTES_REQUIRED:'+name)
 for name in manifest['restore_files']:
  source=safe(HERE,name);target=safe(base,name);record=manifest['files'][name]
  if target.exists():
   if not target.is_file() or target.stat().st_size!=record['bytes'] or hashlib.sha256(target.read_bytes()).hexdigest()!=record['SHA256']:raise ValueError('EXISTING_CONSUMER_CODE_DIFFERS:'+name)
  else:
   target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 print(json.dumps(dict(status='PASS_WALLET_CODE_ONLY_RESTORE',files=len(manifest['restore_files']),historical_arrays=0,wallets=0)))
 if args.metadata_only:
  path=base/'coin_bot_historical_driver_wallet_locator_20261014/run_verified.py'
  result=subprocess.run([sys.executable,'-B',str(path),'--preparation-manifest-sha',manifest['wallet_preparation_SHA256'],'metadata'],check=True,capture_output=True,text=True)
  value=json.loads(result.stdout)
  if value.get('status')!='METADATA_ONLY_NO_ARRAY_OR_WALLET':raise ValueError('EXACT_METADATA_ONLY_STATUS_REQUIRED')
  print(json.dumps(dict(status='PASS_RESTORED_WALLET_METADATA_ONLY',historical_arrays=0,wallets=0)))
 return 0

if __name__=='__main__':raise SystemExit(main())
