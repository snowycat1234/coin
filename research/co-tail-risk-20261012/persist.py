"""Small derived-source packets; reuse large previously public original price objects."""
import argparse,io,zipfile
from pathlib import Path
from util import HERE,sha,save
def persist(kind,state):
 target=HERE/'public'/kind;assert not target.exists();target.mkdir(parents=True);members={};names={'INPUTS':('TRAIN.npz','Y2023.npz','Y2025.npz','PREPARATION.json'),'MODEL':('MODEL.json',),'SCORES':('Y2023.npz','Y2025.npz','RESULTS.json')}[kind]
 for name in names:members[name]=(state/name).read_bytes()
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,b in sorted(members.items()):info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 b=stream.getvalue();assert len(b)<3000000;(target/'PACKET.zip').write_bytes(b);save(target/'INDEX.json',dict(SHA256=sha(b),bytes=len(b),members={k:dict(SHA256=sha(v),bytes=len(v)) for k,v in members.items()}));print('ACTUAL_CO_TAIL_SMALL_PUBLIC_PACKET',kind,len(b),len(members),sha(b),flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('kind',choices=['INPUTS','MODEL','SCORES']);q.add_argument('--state',type=Path,required=True);a=q.parse_args();persist(a.kind,a.state)
