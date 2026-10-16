#!/usr/bin/env python3
"""Reassemble exact ZIP byte slices; trusted hash must arrive independently."""
import argparse,hashlib,json,re
from pathlib import Path
def require(c,m):
 if not c:raise ValueError(m)
def unique(pairs):
 result={}
 for k,v in pairs:
  require(k not in result,'DUPLICATE_JSON_KEY');result[k]=v
 return result
def pinshape(v):require(type(v) is dict and set(v)=={'SHA256','bytes'} and type(v['bytes']) is int and v['bytes']>=0 and type(v['SHA256']) is str and re.fullmatch('[0-9a-f]{64}',v['SHA256']) is not None,'EXACT_PIN_TYPES_REQUIRED')
p=argparse.ArgumentParser();p.add_argument('--trusted-zip-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args();root=Path(__file__).resolve().parent
require(re.fullmatch('[0-9a-f]{64}',a.trusted_zip_sha256) is not None,'EXTERNAL_TRUSTED_SHA256_REQUIRED')
m=json.loads((root/'REASSEMBLY_MANIFEST.json').read_bytes(),object_pairs_hook=unique,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')));pinshape(m['ZIP_pin']);require(m['ZIP_pin']['SHA256']==a.trusted_zip_sha256,'EXTERNAL_TRUSTED_HASH_REQUIRED')
require(type(m['parts']) is list and 0<len(m['parts'])<=32,'BOUNDED_PARTS_REQUIRED');output=Path(a.output);require(not output.exists(),'NEVER_OVERWRITE_OUTPUT');h=hashlib.sha256();size=0;success=False;created=False
try:
 with output.open('xb') as f:
  created=True;seen=set()
  for rec in m['parts']:
   name=rec['part'];require(type(name) is str and Path(name).name==name and name not in ('.','..') and '\\' not in name and name not in seen,'SAFE_UNIQUE_PART_NAME_REQUIRED');seen.add(name);part=root/name;require(part.is_file() and not part.is_symlink(),'REGULAR_PART_REQUIRED');pinshape(rec['pin'])
   require(type(rec['offset']) is int and rec['offset']==size and 0<rec['pin']['bytes']<=8*1024*1024 and part.stat().st_size==rec['pin']['bytes'],'EXACT_PART_OFFSET_SIZE_REQUIRED');data=part.read_bytes();require(hashlib.sha256(data).hexdigest()==rec['pin']['SHA256'],'EXACT_PART_HASH_REQUIRED');f.write(data);h.update(data);size+=len(data)
 require(size==m['ZIP_pin']['bytes'] and h.hexdigest()==a.trusted_zip_sha256,'REASSEMBLED_ZIP_MISMATCH');success=True
finally:
 if created and not success:output.unlink()
print(json.dumps(dict(status='PASS',bytes=size,SHA256=h.hexdigest()),sort_keys=True))
