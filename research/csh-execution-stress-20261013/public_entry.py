"""Explicit public metadata gate; archived financial launcher remains byte-identical."""
import argparse,hashlib,json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(inputs,year):
 m=json.loads((HERE/'PUBLIC_REPRODUCIBILITY.json').read_text())
 assert sha(HERE/'FREEZE.json')==m['freeze_sha256']
 f=json.loads((HERE/'FREEZE.json').read_text())
 assert m['redacted_non_economic']=={'DEDUP.json':f['code_sha256']['DEDUP.json']}
 for name,h in f['code_sha256'].items():
  if name!='DEDUP.json':assert sha(HERE/name)==h,name
 for name,h in m['public_entry_and_restore_sha256'].items():assert sha(HERE/name)==h,name
 for row in json.loads((HERE/'PINNED_CODE_AND_TARGETS.json').read_text()):
  assert sha(inputs/row['relative_destination'])==row['sha256'],row['relative_destination']
 b=json.loads((HERE/'SOURCE_BINDINGS.json').read_text())[str(year)]['source_index']
 actual=json.loads((inputs/f'prepared_{year}/SOURCE_INDEX.json').read_text())
 for a,r in zip(actual['months'],b['months'],strict=True):
  assert a['month']==r['month'] and a['source_NPZ_SHA256']==r['source_NPZ_SHA256']
  p=inputs/f'prepared_{year}'/'months'/f"{r['month']}.npz"
  assert sha(p)==r['source_NPZ_SHA256'] and p.stat().st_size==r['source_NPZ_bytes']
 for name,row in b['files'].items():
  if name in ('Y2025.npz','Y2025_RISK.json'):continue # Unused derived native risk outputs; frozen strategy archive is checked above.
  assert sha(inputs/f'prepared_{year}'/name)==row['SHA256'] and (inputs/f'prepared_{year}'/name).stat().st_size==row['bytes'],name
 return f

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--year',type=int,choices=(2021,2023,2025),required=True);p.add_argument('--shock',choices=('FRICTION_DOUBLE','CAPACITY_HALF'));p.add_argument('--output',type=Path);p.add_argument('--authorize-new-historical-wallet',action='store_true');a=p.parse_args()
 if a.output or a.shock or a.authorize_new_historical_wallet:
  assert a.output and a.shock and a.authorize_new_historical_wallet,'Explicit authorization, shock and NEW output required'
  assert not a.output.exists(),'Output must not exist'
 f=verify(a.inputs.resolve(),a.year)
 if not a.authorize_new_historical_wallet:
  print(json.dumps(dict(status='PASS_PUBLIC_HASH_GATE_ONLY',year=a.year,historical_wallets=0)));return
 # Only an explicitly authorized future invocation imports the financial launcher.
 import run as archived, runtime, recover
 out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 for name in ('pinned-repo','fine-code','targets','inputs',f'prepared_{a.year}'):
  (out/name).symlink_to((a.inputs/name).resolve(),target_is_directory=True)
 (out/'PUBLIC_RUN_AUTHORIZATION.json').write_text(json.dumps(dict(explicit_authorization=True,public_manifest_sha256=sha(HERE/'PUBLIC_REPRODUCIBILITY.json'),original_freeze_sha256=sha(HERE/'FREEZE.json'),year=a.year,shock=a.shock),indent=2)+'\n')
 archived.STATE=runtime.STATE=recover.STATE=out
 # Replace only the obsolete private metadata gate, with all financial hashes checked above.
 archived.verify_freeze=lambda:verify(a.inputs.resolve(),a.year)
 archived.run(a.year,a.shock)
if __name__=='__main__':main()
