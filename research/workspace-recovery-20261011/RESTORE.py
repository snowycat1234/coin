"""Verify/recover only this public package from a pinned Git commit; no network.

Run under recovered bounded_cloud.py. Reads published Git objects only, never a
collector/reserved dataset. Existing differing destination bytes are rejected.
"""
import argparse, hashlib, io, json, subprocess, zipfile
from pathlib import Path, PurePosixPath
BASE='research/workspace-recovery-20261011/'

def sha(b): return hashlib.sha256(b).hexdigest()
def safe(name):
 p=PurePosixPath(name)
 assert not p.is_absolute() and '..' not in p.parts and p.parts[0]=='state',name
 return p

def main():
 parser=argparse.ArgumentParser(); parser.add_argument('--git-repo',type=Path,required=True); parser.add_argument('--commit',required=True); parser.add_argument('--workspace',type=Path); parser.add_argument('--verify-only',action='store_true'); args=parser.parse_args()
 assert args.verify_only or args.workspace is not None
 assert len(args.commit)==40 and all(c in '0123456789abcdef' for c in args.commit)
 def git(path): return subprocess.check_output(['git','-C',str(args.git_repo),'show',args.commit+':'+path],timeout=180)
 raw_index=git(BASE+'PUBLIC_RECOVERY_INDEX.json'); index=json.loads(raw_index); outputs={}; total=0
 def check(b,r): assert len(b)==r['bytes'] and sha(b)==r['sha256'],r['path'] if 'path' in r else r['destination']
 def add(name,b):
  safe(name)
  if name in outputs: assert outputs[name]==b,name
  outputs[name]=b
 for key in ['source_archive','derived_archive']:
  r=index[key]; b=git(r['path']); check(b,r); expected={m['path']:m for m in r['members']}
  assert len(expected)==len(r['members'])
  with zipfile.ZipFile(io.BytesIO(b)) as z:
   assert len(z.namelist())==len(set(z.namelist())) and set(z.namelist())==set(expected)
   assert z.testzip() is None
   for n in z.namelist():
    body=z.read(n); check(body,expected[n]); add(n,body)
 for source in index['raw_official_trade_archives']:
  blocks=[]
  for p in source['parts']:
   assert p['bytes']<=index['chunk_ceiling_bytes']<=1500000
   b=git(p['path']); check(b,p); assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==p['git_blob_sha1']; blocks.append(b)
  b=b''.join(blocks); check(b,source)
  with zipfile.ZipFile(io.BytesIO(b)) as z: assert z.testzip() is None
  add(source['destination'],b); total+=len(b)
 if not args.verify_only:
  for name,b in outputs.items():
   p=safe(name); out=args.workspace/'coin_single_state'/Path(*p.parts[1:])
   assert out.resolve().is_relative_to((args.workspace/'coin_single_state').resolve())
   if out.exists(): assert out.read_bytes()==b,f'Preserve existing differing bytes: {out}'
   else:
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as f: f.write(b)
 print(json.dumps(dict(status='PASS_PUBLISHED_GIT_BYTES_AND_SAFE_RESTORE',commit=args.commit,index_sha256=sha(raw_index),source_and_derived_members=len(outputs)-len(index['raw_official_trade_archives']),official_trade_archives=len(index['raw_official_trade_archives']),raw_archive_bytes=total,verify_only=args.verify_only,original_Q1_Q2_financial_ledger_checkpoint_bytes='MISSING',native_full_tape=False,Q3_consumed=False)))
if __name__=='__main__': main()
