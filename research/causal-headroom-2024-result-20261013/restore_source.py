"""Restore fixed 2024 public originals via normal Git only, never a wallet."""
import argparse,hashlib,importlib.util,io,json,os,subprocess,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ARCHIVE='d69e9ac94478c5be54cb46c622afec7aaf3c61f7';SOURCE='45052aacfa54fc62aba103e3e82c7c1c2d247efc';CUBE='53357f33f4e6ccb536af762fbff39b269c24d837'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);p.add_argument('--git-cache',type=Path);p.add_argument('--byte-cache',type=Path);p.add_argument('--check-existing',type=Path);a=p.parse_args()
 if a.check_existing:
  actual=a.check_existing;assert (actual/'SOURCE_INDEX.json').read_bytes()==(HERE/'SOURCE_INDEX.json').read_bytes();m=json.loads((HERE/'SOURCE_INDEX.json').read_text())
  for r in m['months']:
   b=(actual/'months'/(r['month']+'.npz')).read_bytes();assert sha(b)==r['source_NPZ_SHA256'] and len(b)==r['source_NPZ_bytes']
  for n,r in m['files'].items():
   b=(actual/n).read_bytes();assert sha(b)==r['SHA256'] and len(b)==r['bytes']
  print('PASS_EXISTING_SOURCE_HASHES_ONLY_ZERO_WALLETS');return
 assert a.output and a.git_cache and not a.output.exists();a.output.mkdir(parents=True,exist_ok=False);root=a.output;records=[]
 def get(c,path,h=None):
  assert not any(x in path.lower() for x in ('holdout','locked'))
  key=sha((c+':'+path).encode())+'.blob';cached=a.byte_cache/key if a.byte_cache else None
  if cached is not None and cached.exists():b=cached.read_bytes();mode='EXISTING_BYTE_CACHE'
  else:b=subprocess.check_output(['git','-c','http.version=HTTP/1.1','-C',str(a.git_cache),'show',c+':'+path]);mode='NORMAL_GIT'
  if h:assert sha(b)==h,path
  records.append(dict(commit=c,path=path,sha256=sha(b),bytes=len(b),mode=mode));return b
 def wrapper(c,prefix,index,path):
  with path.open('xb') as f:
   for r in index['parts']:
    b=get(c,prefix+r['file_name'],r['sha256']);assert len(b)==r['bytes'];f.write(b)
  assert sha(path.read_bytes())==index['original_sha256'] and path.stat().st_size==index['original_bytes']
 source=root/'source';source.mkdir();prefix='research_artifacts/e5_h1_tail_coverage_pair_20261008/';m=json.loads(get(ARCHIVE,prefix+'INDEX.json'));wrapper(ARCHIVE,prefix,m,source/'H1.zip')
 prefix='research_artifacts/native_20261008/';m=json.loads(get(ARCHIVE,prefix+'INDEX.json'))
 for r in m['market_archives_layout']['original_archives']:wrapper(ARCHIVE,prefix+'byteparts/',r,source/r['original_file_name'])
 for path in source.glob('*.zip'):
  with zipfile.ZipFile(path) as z:assert not any('2026-0'+str(i) in n for n in z.namelist() for i in range(3,10))
 prefix='research/settled-funding-direction-20261012/public/INPUTS_FINAL/';m=json.loads(get(CUBE,prefix+'INDEX.json'));raw=get(CUBE,prefix+'PACKET.zip',m['SHA256'])
 with zipfile.ZipFile(io.BytesIO(raw)) as z:b=z.read('Y2025.npz')
 assert sha(b)==m['members']['Y2025.npz']['SHA256'];cube=root/'completed_close_cube.npz';cube.write_bytes(b)
 raw=get(SOURCE,'research/expanded-frozen-2024-20261013/prepare_native_2024.py','24c034b22d36a63bffe70b57884aa50c771c68239c3f8eefddf3f3c9f4898bac');code=root/'original_prepare_native_2024.py';code.write_bytes(raw)
 b=(HERE/'2024_DERIVED_MARK_OHLC.csv').read_bytes();assert sha(b)=='0af6d1cc66bc81afd39582ae4de2b1aa25d9e0031765ce6bce74e917a5577d0c';(source/'DERIVED_MARK_OHLC.csv').write_bytes(b)
 spec=importlib.util.spec_from_file_location('original_source_prepare_2024',code);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.prepare(source,cube,root/'prepared_2024')
 expected=json.loads((HERE/'SOURCE_INDEX.json').read_text());actual=root/'prepared_2024/SOURCE_INDEX.json';assert actual.read_bytes()==(HERE/'SOURCE_INDEX.json').read_bytes()
 for r in expected['months']:b=(root/'prepared_2024/months'/(r['month']+'.npz')).read_bytes();assert sha(b)==r['source_NPZ_SHA256'] and len(b)==r['source_NPZ_bytes']
 for n,r in expected['files'].items():b=(root/'prepared_2024'/n).read_bytes();assert sha(b)==r['SHA256'] and len(b)==r['bytes']
 (root/'RESTORE_RECEIPT.json').write_text(json.dumps(dict(status='PASS_EXACT_2024_SOURCE_BYTES_WITH_ORIGINAL_10_DERIVED_CELLS',source_index_sha256=sha(actual.read_bytes()),records=records,wallets=0,targets_generated=0,provider_requests=0),indent=2)+'\n');print('PASS_SOURCE_ONLY')
if __name__=='__main__':main()
