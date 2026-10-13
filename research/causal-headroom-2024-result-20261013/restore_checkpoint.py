"""Restore original day360/final checkpoint bytes WITH explicit verified prefix."""
import argparse,gzip,hashlib,json,os,io,zipfile
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def minimal_members(folder):
 index=json.loads((folder/'INDEX.json').read_text());pieces=[]
 for row in index['parts']:
  b=(folder/row['name']).read_bytes();assert sha(b)==row['sha256'] and len(b)==row['bytes'];pieces.append(b)
 b=b''.join(pieces);assert sha(b)==index['packet_sha256'] and len(b)==index['packet_bytes']
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  assert z.testzip() is None;members={n:z.read(n) for n in z.namelist()}
 for n,b in members.items():assert sha(b)==index['members'][n]['sha256'] and len(b)==index['members'][n]['bytes']
 return members

def restore(package,prefix,anchor,output):
 assert not output.exists();a=package/anchor;pointer=json.loads((a/'POINTER.json').read_text());raw=(a/pointer['snapshot_path']).read_bytes();assert sha(raw)==pointer['snapshot_SHA256'];inputs=[]
 for row in pointer['chunks']:
  src=prefix/row['path'] if int(row['path'][4:8])<360 else package/'tail'/row['path']
  assert src.is_file(),f'Exact original prefix/tail dependency missing: {row["path"]}'
  assert sha(src.read_bytes())==row['SHA256'],row['path'];inputs.append((src,row['path']))
 output.mkdir(parents=True,exist_ok=False);recover=output/'recovery';recover.mkdir()
 for src,name in inputs:os.link(src,recover/name)
 (recover/pointer['snapshot_path']).write_bytes(raw);(recover/'POINTER.json').write_bytes((a/'POINTER.json').read_bytes());(output/'BINDING.json').write_text(json.dumps(pointer['binding'],indent=2,sort_keys=True)+'\n')
 if anchor=='final':
  members=minimal_members(package/'result');assert members['FINAL_STATE.json.gz']==raw and members['POINTER.json']==(a/'POINTER.json').read_bytes()
  for name in ('BINDING.json','RESULT.json','ACCOUNT.json','MINUTE_NUMERIC.json','DAILY.csv','TIMING.json'):(output/name).write_bytes(members[name])
 receipt=dict(status='PASS_SNAPSHOT_TAIL_BYTES_WITH_VERIFIED_EXTERNAL_PREFIX',anchor=anchor,remote_tail_chunks=max(0,len(inputs)-360),external_prefix_chunks=min(360,len(inputs)),state_hash=pointer['state_hash'],snapshot_sha256=pointer['snapshot_SHA256'],all_minute_remote_cold_claim=False,financial_imports=0,new_wallets=0,advances=0)
 print(json.dumps(receipt));return receipt
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--package',type=Path,required=True);p.add_argument('--prefix-recovery',type=Path,required=True);p.add_argument('--anchor',choices=('day360','final'),default='final');p.add_argument('--output',type=Path,required=True);a=p.parse_args();restore(a.package,a.prefix_recovery,a.anchor,a.output)
