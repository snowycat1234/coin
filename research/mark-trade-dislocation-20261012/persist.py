"""Publish small exact packets, reuse already published monthly originals by immutable Git refs."""
import argparse,json,io,zipfile
from pathlib import Path
from util import HERE,sha,save
def persist(kind,state,boundary=None):
 target=HERE/'public'/kind;assert not target.exists();target.mkdir(parents=True);members={}
 if kind=='INPUTS':
  for name in ('TRAIN.npz','Y2023.npz','Y2025.npz','PREPARATION.json'):members[name]=(state/name).read_bytes()
  members['BOUNDARY.json']=(boundary/'BOUNDARY.json').read_bytes();B=json.loads(members['BOUNDARY.json'])
  for r in B['records']:
   if r['transport_status']=='REUSED_GIT_ORIGINAL':continue
   for suffix in ('','.CHECKSUM'):members[r['raw_path']+suffix]=(boundary/(r['raw_path']+suffix)).read_bytes()
 elif kind=='MODEL':members['MODEL.json']=(state/'MODEL.json').read_bytes()
 else:
  for name in ('Y2023.npz','Y2025.npz','RESULTS.json'):members[name]=(state/name).read_bytes()
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,b in sorted(members.items()):info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 raw=stream.getvalue();assert len(raw)<12000000;(target/'PACKET.zip').write_bytes(raw);save(target/'INDEX.json',dict(SHA256=sha(raw),bytes=len(raw),members={k:dict(SHA256=sha(v),bytes=len(v)) for k,v in members.items()}));print('ACTUAL_PUBLISHED_PACKET',kind,len(raw),len(members),sha(raw),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('kind',choices=['INPUTS','MODEL','SCORES']);p.add_argument('--state',type=Path,required=True);p.add_argument('--boundary',type=Path);a=p.parse_args();persist(a.kind,a.state,a.boundary)
