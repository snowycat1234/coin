"""Exact small public packets, original raw December trade once and pinned prior sources."""
import argparse,io,json,zipfile
from pathlib import Path
from util import HERE,sha,save
def persist(kind,state,raw22=None):
 target=HERE/'public'/kind;assert not target.exists();target.mkdir(parents=True);members={}
 if kind=='INPUTS':
  for name in ('TRAIN.npz','Y2023.npz','Y2025.npz','PREPARATION.json'):members[name]=(state/name).read_bytes()
  members['DECEMBER2022_TRADE_SOURCES.json']=(raw22/'SOURCES.json').read_bytes()
  for r in json.loads(members['DECEMBER2022_TRADE_SOURCES.json'])['records']:
   for suffix in ('','.CHECKSUM'):members[r['raw_path']+suffix]=(raw22/(r['raw_path']+suffix)).read_bytes()
 elif kind=='MODEL':members['MODEL.json']=(state/'MODEL.json').read_bytes()
 else:
  for name in ('Y2023.npz','Y2025.npz','RESULTS.json'):members[name]=(state/name).read_bytes()
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for name,b in sorted(members.items()):info=zipfile.ZipInfo(name,(2026,10,12,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
 raw=stream.getvalue();assert len(raw)<25000000;(target/'PACKET.zip').write_bytes(raw);save(target/'INDEX.json',dict(SHA256=sha(raw),bytes=len(raw),members={k:dict(SHA256=sha(v),bytes=len(v)) for k,v in members.items()}));print('ACTUAL_JUMP_PUBLIC_PACKET',kind,len(raw),len(members),sha(raw),flush=True)
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('kind',choices=['INPUTS','MODEL','SCORES']);q.add_argument('--state',type=Path,required=True);q.add_argument('--raw22',type=Path);a=q.parse_args();persist(a.kind,a.state,a.raw22)
