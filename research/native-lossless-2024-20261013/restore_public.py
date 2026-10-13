"""Rebuild every exact 2024 native wallet file from the public Git branch.

Requires Python and NumPy. This never calls or advances a wallet simulator.
"""
import hashlib,json,sys
from pathlib import Path
from pack_all import restore

def sha(raw):return hashlib.sha256(raw).hexdigest()
def assemble(public,work):
 public=Path(public);work=Path(work);assert not work.exists();work.mkdir(parents=True)
 idx=json.loads((public/'PUBLIC_INDEX.json').read_text())
 assert idx['schema']=='NATIVE_2024_FIVE_WALLETS_PUBLIC_PARTS_V1' and idx['wallet_advances']==0
 for row in idx['files']:
  name=row['reconstructed_path'];dest=work/name;h=hashlib.sha256();n=0
  with dest.open('xb') as out:
   for part in row['parts']:
    raw=(public/part['path']).read_bytes();assert len(raw)==part['bytes'] and sha(raw)==part['SHA256']
    out.write(raw);h.update(raw);n+=len(raw)
  assert n==row['bytes'] and h.hexdigest()==row['SHA256']
 print('PUBLIC_PARTS_ASSEMBLED_VERIFIED',sum(len(x['parts']) for x in idx['files']),flush=True)
 return idx
if __name__=='__main__':
 if len(sys.argv)!=4:raise SystemExit('Usage: python restore_public.py PUBLICATION_DIR NEW_WORK_DIR NEW_RESTORED_WALLETS_DIR')
 idx=assemble(sys.argv[1],sys.argv[2]);restore(sys.argv[2],sys.argv[3]);print('PUBLIC_COLD_RESTORE_PASS_ZERO_WALLET_ADVANCES',idx['original_files'])
