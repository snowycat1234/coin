"""Prepare bounded Git blobs with sha256-verified ordered parts."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent;SRC=ROOT/'bundle';OUT=ROOT/'publication700';OUT.mkdir(exist_ok=True)
PART_SIZE=716800
rows=[]
for name in ['MINUTE_BITS.xz','OTHER_BYTES.xz','MANIFEST.json']:
 p=SRC/name;h=hashlib.sha256();parts=[]
 with p.open('rb') as f:
  i=0
  while raw:=f.read(PART_SIZE):
   h.update(raw);rel=f'{name}.part{i:04d}' if p.stat().st_size>PART_SIZE else name
   dest=OUT/rel
   if dest.exists():assert dest.read_bytes()==raw
   else:dest.write_bytes(raw)
   parts.append(dict(path=rel,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
   i+=1
 rows.append(dict(reconstructed_path=name,bytes=p.stat().st_size,SHA256=h.hexdigest(),parts=parts))
manifest=json.loads((SRC/'MANIFEST.json').read_text())
index=dict(schema='NATIVE_2024_FIVE_WALLETS_PUBLIC_PARTS_V1',part_size=PART_SIZE,files=rows,archive_schema=manifest['schema'],original_files=len(manifest['files']),unique_objects=len(manifest['objects']),original_logical_bytes=manifest['original_logical_bytes'],wallet_advances=0,states=manifest['states'])
(OUT/'PUBLIC_INDEX.json').write_text(json.dumps(index,indent=2,sort_keys=True)+'\n')
print('parts',sum(len(x['parts']) for x in rows),'total bytes',sum((OUT/y['path']).stat().st_size for x in rows for y in x['parts']))
