#!/usr/bin/env python3
"""Reassemble exact bounded slices; externally trusted ZIP hash is mandatory."""
import argparse,hashlib,json
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--trusted-zip-sha256',required=True);p.add_argument('--output',required=True);a=p.parse_args();root=Path(__file__).resolve().parent;m=json.loads((root/'REASSEMBLY_MANIFEST.json').read_bytes());assert m['ZIP_pin']['SHA256']==a.trusted_zip_sha256,'EXTERNAL_TRUSTED_HASH_REQUIRED';output=Path(a.output);assert not output.exists(),'NEVER_OVERWRITE_OUTPUT';h=hashlib.sha256();size=0
with output.open('xb') as f:
 for rec in m['parts']:
  name=rec['part'];assert Path(name).name==name;data=(root/name).read_bytes();assert len(data)==rec['pin']['bytes']<=8*1024*1024 and hashlib.sha256(data).hexdigest()==rec['pin']['SHA256'];assert size==rec['offset'];f.write(data);h.update(data);size+=len(data)
assert size==m['ZIP_pin']['bytes'] and h.hexdigest()==a.trusted_zip_sha256,'REASSEMBLED_ZIP_MISMATCH';print(json.dumps(dict(status='PASS',bytes=size,SHA256=h.hexdigest()),sort_keys=True))
