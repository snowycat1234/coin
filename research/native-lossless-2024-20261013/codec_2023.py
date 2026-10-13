"""Bit-exact preservation of genuine native-wallet checkpoint, no simulator execution.

Encode each immutable float64 minute chunk by exact column de-duplication and
reversible byte-lane shuffle, then compress one XZ stream. Original checkpoint
SHA-256 checks ensure numpy's deterministic NPZ regeneration is truly exact.
"""
import argparse, hashlib, json, lzma, shutil, io, os
from pathlib import Path
import numpy as np

def sha_bytes(x): return hashlib.sha256(x).hexdigest()
def sha_file(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1<<20),b''):h.update(chunk)
 return h.hexdigest()
def encode(a):
 assert a.dtype==np.float64 and a.ndim==2
 u=a.view(np.uint64);keep=[];mapping=[]
 for j in range(u.shape[1]):
  prior=next((k for k in keep if np.array_equal(u[:,j],u[:,k])),None)
  if prior is None:keep.append(j);mapping.append(j)
  else:mapping.append(prior)
 v=u[:,keep].T.copy().view(np.uint8).reshape(len(keep),a.shape[0],8)
 shuffled=v.transpose(0,2,1).copy().tobytes()
 return keep,mapping,shuffled

def decode(raw,rows,cols,keep,mapping):
 k=len(keep)
 assert len(raw)==k*rows*8 and len(mapping)==cols
 reshuffled=np.frombuffer(raw,dtype=np.uint8).reshape(k,8,rows).transpose(0,2,1).copy()
 v=reshuffled.view('<u8').reshape(k,rows).T
 bits=np.empty((rows,cols),dtype='<u8')
 positions={j:i for i,j in enumerate(keep)}
 for j,parent in enumerate(mapping):bits[:,j]=v[:,positions[parent]]
 return bits.view('<f8')

def pack(src,out):
 src=Path(src);out=Path(out);out.mkdir(parents=True,exist_ok=False)
 p=src/'POINTER.json';pointer=json.loads(p.read_text());days=pointer['chunks'];assert len(days)==365
 assert pointer['completed_minutes']==525600
 final=src/pointer['snapshot_path'];assert sha_file(final)==pointer['snapshot_SHA256']
 shutil.copyfile(p,out/'POINTER.json');shutil.copyfile(final,out/final.name)
 meta=[];raw_total=0
 with lzma.open(out/'MINUTE_BITS.xz','wb',preset=6) as stream:
  for i,item in enumerate(days):
   file=src/item['path'];assert sha_file(file)==item['SHA256']
   with np.load(file,allow_pickle=False) as z:
    assert list(z.files)==['minute_chunk'];a=z['minute_chunk']
   assert a.dtype==np.float64 and a.shape==(item['rows'],item['columns']) and np.isfinite(a).all()
   keep,mapping,raw=encode(a);assert np.array_equal(decode(raw,*a.shape,keep,mapping).view(np.uint64),a.view(np.uint64))
   tmp=io.BytesIO();np.savez_compressed(tmp,minute_chunk=a)
   assert sha_bytes(tmp.getvalue())==item['SHA256'],f'Non-reproducible original NPZ byte at {i}'
   stream.write(raw);raw_total+=len(raw)
   meta.append(dict(path=item['path'],rows=item['rows'],columns=item['columns'],keep=keep,mapping=mapping,npz_SHA256=item['SHA256']))
   if (i+1)%50==0:print('encoded',i+1,'/',len(days),flush=True)
 manifest=dict(schema='NATIVE_FLOAT64_BIT_EXACT_SHUFFLED_XZ_V1',source_pointer_SHA256=sha_file(p),snapshot_path=final.name,snapshot_SHA256=sha_file(final),completed_minutes=pointer['completed_minutes'],state_hash=pointer['state_hash'],days=meta,raw_transformed_bytes=raw_total,original_npz_bytes=sum((src/x['path']).stat().st_size for x in days))
 manifest['xz_SHA256']=sha_file(out/'MINUTE_BITS.xz');manifest['xz_bytes']=(out/'MINUTE_BITS.xz').stat().st_size
 (out/'MANIFEST.json').write_text(json.dumps(manifest,sort_keys=True,separators=(',',':'))+'\n')
 print('PACK_DONE',manifest['original_npz_bytes'],manifest['xz_bytes'],manifest['xz_SHA256'],flush=True)

def restore(pack,dest):
 pack=Path(pack);dest=Path(dest);dest.mkdir(parents=True,exist_ok=False)
 m=json.loads((pack/'MANIFEST.json').read_text());assert m['schema']=='NATIVE_FLOAT64_BIT_EXACT_SHUFFLED_XZ_V1'
 assert sha_file(pack/'POINTER.json')==m['source_pointer_SHA256'];pointer=json.loads((pack/'POINTER.json').read_text())
 assert pointer['state_hash']==m['state_hash'] and pointer['completed_minutes']==m['completed_minutes']
 assert len(pointer['chunks'])==len(m['days'])
 assert sha_file(pack/m['snapshot_path'])==m['snapshot_SHA256']==pointer['snapshot_SHA256']
 assert sha_file(pack/'MINUTE_BITS.xz')==m['xz_SHA256']
 shutil.copyfile(pack/'POINTER.json',dest/'POINTER.json');shutil.copyfile(pack/m['snapshot_path'],dest/m['snapshot_path'])
 raw_bytes=0
 with lzma.open(pack/'MINUTE_BITS.xz','rb') as stream:
  for i,(item,original) in enumerate(zip(m['days'],pointer['chunks'])):
   assert item['path']==original['path'] and item['rows']==original['rows'] and item['columns']==original['columns'] and item['npz_SHA256']==original['SHA256']
   n=len(item['keep'])*item['rows']*8;raw=stream.read(n);assert len(raw)==n;raw_bytes+=n
   a=decode(raw,item['rows'],item['columns'],item['keep'],item['mapping']);assert a.dtype==np.float64 and a.shape==(item['rows'],item['columns']) and np.isfinite(a).all()
   f=dest/item['path'];np.savez_compressed(f,minute_chunk=a);assert sha_file(f)==item['npz_SHA256'],item['path']
   if (i+1)%50==0:print('verified',i+1,'/',len(m['days']),flush=True)
  assert stream.read(1)==b''
 assert raw_bytes==m['raw_transformed_bytes']
 print('RESTORE_PASS_ALL_365_NPZ_BYTES_AND_NATIVE_CHECKPOINT',m['state_hash'],flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='cmd',required=True)
 for name in ('pack','restore'):
  s=sub.add_parser(name);s.add_argument('source');s.add_argument('destination')
 a=parser.parse_args();globals()[a.cmd](a.source,a.destination)
