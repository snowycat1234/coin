"""Cold-rebuild exact native 2023 scheduler checkpoint from public Git files.

Needs Python, NumPy. This script assembles and verifies parts and invokes only
the lossless decoder; it does not run or advance a wallet.
"""
import hashlib,json,sys
from pathlib import Path
from pack import restore

def sha(raw):return hashlib.sha256(raw).hexdigest()
def assemble(public,work):
 public=Path(public);work=Path(work);work.mkdir(parents=True,exist_ok=False)
 idx=json.loads((public/'PUBLIC_INDEX.json').read_text())
 assert idx['schema']=='NATIVE_2023_EXACT_RECOVERY_PUBLIC_PARTS_V1' and idx['wallet_advances']==0
 for row in idx['files']:
  name=row['reconstructed_path'];dest=work/name;h=hashlib.sha256();n=0
  with dest.open('xb') as out:
   for part in row['parts']:
    raw=(public/part['path']).read_bytes();assert len(raw)==part['bytes'] and sha(raw)==part['SHA256']
    out.write(raw);h.update(raw);n+=len(raw)
  assert n==row['bytes'] and h.hexdigest()==row['SHA256']
 print('PUBLIC_PARTS_ASSEMBLED_VERIFIED',len(idx['files']),flush=True)
 return idx
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: python restore_public.py PUBLICATION_DIR NEW_WORK_DIR NEW_RESTORED_CHECKPOINT_DIR')
 idx=assemble(sys.argv[1],sys.argv[2]);restore(sys.argv[2],sys.argv[3]);print('PUBLIC_COLD_RESTORE_PASS_ZERO_WALLET_ADVANCES',idx['checkpoint_state_hash'])
