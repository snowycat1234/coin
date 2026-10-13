"""Bit-exact, hardlink-aware archive of genuine 2024 native-wallet outputs.

No scheduler/simulator calls. Encoding is reversible byte-lane shuffling with
exact duplicate-column removal, then standard-library XZ compression.
"""
import argparse,hashlib,io,json,lzma,os,shutil,stat,sys
from collections import defaultdict
from pathlib import Path
import numpy as np
from codec_2023 import encode,decode,sha_file

def sha(b):return hashlib.sha256(b).hexdigest()
def get_files(root):
 paths=sorted(p for p in root.rglob('*') if p.is_file())
 assert len(paths)>2500
 return paths

def scan(root):
 groups=defaultdict(list); info=[]
 for p in get_files(root):
  s=p.lstat();assert stat.S_ISREG(s.st_mode) and not p.is_symlink()
  rel=p.relative_to(root).as_posix();inode=f'{s.st_dev}:{s.st_ino}'
  groups[inode].append(rel)
  info.append(dict(path=rel,bytes=s.st_size,mode=stat.S_IMODE(s.st_mode),mtime_ns=s.st_mtime_ns,link_group=inode))
 hashes={}
 for inode,paths in groups.items():hashes[inode]=sha_file(root/paths[0])
 for x in info:x['SHA256']=hashes[x['link_group']]
 return info

def pack(root,out):
 root=Path(root).resolve();out=Path(out).resolve();assert not out.exists();out.mkdir(parents=True)
 files=scan(root);by_hash={}
 for r in files:by_hash.setdefault(r['SHA256'],r['path'])
 objects=[];npz_uncompressed=other_uncompressed=0;npz_orig=0
 with lzma.open(out/'MINUTE_BITS.xz','wb',preset=6) as bits, lzma.open(out/'OTHER_BYTES.xz','wb',preset=6) as other:
  for i,(digest,path) in enumerate(sorted(by_hash.items())):
   p=root/path;s=p.stat();raw=p.read_bytes();assert sha(raw)==digest and p.stat().st_size==s.st_size and p.stat().st_mtime_ns==s.st_mtime_ns
   if path.endswith('.npz'):
    with np.load(io.BytesIO(raw),allow_pickle=False) as z:
     assert z.files==['minute_chunk'];a=z['minute_chunk']
    assert a.dtype==np.float64 and a.ndim==2 and a.shape[1]==36 and np.isfinite(a).all()
    keep,mapping,trans=encode(a)
    assert np.array_equal(decode(trans,*a.shape,keep,mapping).view(np.uint64),a.view(np.uint64))
    bio=io.BytesIO();np.savez_compressed(bio,minute_chunk=a)
    assert sha(bio.getvalue())==digest,'Original NPZ bytes not reproducible: '+path
    bits.write(trans);npz_uncompressed+=len(trans);npz_orig+=len(raw)
    objects.append(dict(SHA256=digest,original_bytes=len(raw),stream='MINUTE_BITS.xz',stream_bytes=len(trans),rows=len(a),columns=a.shape[1],keep=keep,mapping=mapping))
   else:
    other.write(raw);other_uncompressed+=len(raw)
    objects.append(dict(SHA256=digest,original_bytes=len(raw),stream='OTHER_BYTES.xz',stream_bytes=len(raw)))
   if (i+1)%200==0:print('packed unique objects',i+1,'/',len(by_hash),flush=True)
 streams={name:dict(bytes=(out/name).stat().st_size,SHA256=sha_file(out/name)) for name in ('MINUTE_BITS.xz','OTHER_BYTES.xz')}
 states={}
 for arm in ['EXACTHALF','SMA200_10PCT','VOL_MATCHED','STATIC50','CS_MATCHED']:
  states[arm]={}
  for stage in ('aug12_start','recovery'):
   pointer=json.loads((root/arm/stage/'POINTER.json').read_text());states[arm][stage]=dict(completed_minutes=pointer['completed_minutes'],state_hash=pointer['state_hash'],chunks=len(pointer['chunks']),snapshot_path=pointer['snapshot_path'])
 manifest=dict(schema='NATIVE_2024_FIVE_GENUINE_WALLETS_ALL_FILES_BIT_EXACT_V1',source_root_name='wallets',files=files,objects=objects,streams=streams,states=states,original_logical_bytes=sum(r['bytes'] for r in files),unique_object_bytes=sum(r['original_bytes'] for r in objects),transformed_minute_bytes=npz_uncompressed,other_raw_bytes=other_uncompressed,original_unique_npz_bytes=npz_orig,wallet_advances=0)
 (out/'MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n')
 print('PACK_PASS',len(files),'files',len(objects),'unique SHA objects',manifest['unique_object_bytes'],'unique object bytes',streams,flush=True)

def restore(pack,dest):
 pack=Path(pack);dest=Path(dest);assert not dest.exists();dest.mkdir(parents=True)
 m=json.loads((pack/'MANIFEST.json').read_text());assert m['schema']=='NATIVE_2024_FIVE_GENUINE_WALLETS_ALL_FILES_BIT_EXACT_V1' and m['wallet_advances']==0
 for n,r in m['streams'].items():assert (pack/n).stat().st_size==r['bytes'] and sha_file(pack/n)==r['SHA256']
 paths=defaultdict(list)
 for r in m['files']:
  p=Path(r['path']);assert not p.is_absolute() and '..' not in p.parts
  paths[r['SHA256']].append(r)
 with lzma.open(pack/'MINUTE_BITS.xz','rb') as bits,lzma.open(pack/'OTHER_BYTES.xz','rb') as other:
  for i,obj in enumerate(m['objects']):
   stream=bits if obj['stream']=='MINUTE_BITS.xz' else other
   raw=stream.read(obj['stream_bytes']);assert len(raw)==obj['stream_bytes']
   if obj['stream']=='MINUTE_BITS.xz':
    a=decode(raw,obj['rows'],obj['columns'],obj['keep'],obj['mapping'])
    bio=io.BytesIO();np.savez_compressed(bio,minute_chunk=a);raw=bio.getvalue()
   assert len(raw)==obj['original_bytes'] and sha(raw)==obj['SHA256']
   groups=defaultdict(list)
   for r in paths[obj['SHA256']]:groups[r['link_group']].append(r)
   for g,items in groups.items():
    first=items[0];q=dest/first['path'];q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw);os.chmod(q,first['mode']);os.utime(q,ns=(first['mtime_ns'],first['mtime_ns']))
    for r in items[1:]:
     assert r['mode']==first['mode'] and r['mtime_ns']==first['mtime_ns'];t=dest/r['path'];t.parent.mkdir(parents=True,exist_ok=True);os.link(q,t)
   if (i+1)%200==0:print('restored unique objects',i+1,'/',len(m['objects']),flush=True)
  assert bits.read(1)==b'' and other.read(1)==b''
 assert len(get_files(dest))==len(m['files'])
 for arm,stages in m['states'].items():
  for stage,expected in stages.items():
   p=json.loads((dest/arm/stage/'POINTER.json').read_text());assert p['state_hash']==expected['state_hash'] and p['completed_minutes']==expected['completed_minutes'] and len(p['chunks'])==expected['chunks']
 print('RESTORE_PASS_ALL_FILES_2024_FIVE_NATIVE_WALLETS_ZERO_ADVANCES',len(m['files']),flush=True)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('command',choices=('pack','restore'));a.add_argument('source');a.add_argument('destination');x=a.parse_args()
 globals()[x.command](x.source,x.destination)
