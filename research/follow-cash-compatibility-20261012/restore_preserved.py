"""Byte-exact public account preservation restore, zero financial imports/advances."""
import argparse,hashlib,io,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];PREFIX='research/follow-cash-compatibility-20261012/preserved/Y2023/'
def sha(b):return hashlib.sha256(b).hexdigest()
q=argparse.ArgumentParser();q.add_argument('--artifact-commit',required=True);q.add_argument('--state',type=Path,required=True);a=q.parse_args();assert not a.state.exists()
def git(name):return subprocess.check_output(['git','show',a.artifact_commit+':'+PREFIX+name],cwd=ROOT)
ix=json.loads(git('INDEX.json'));pieces=[]
for r in ix['parts']:b=git(r['file']);assert sha(b)==r['SHA256'] and len(b)==r['bytes'];pieces.append(b)
raw=b''.join(pieces);assert sha(raw)==ix['packet_SHA256'] and len(raw)==ix['packet_bytes'];a.state.mkdir(parents=True)
with zipfile.ZipFile(io.BytesIO(raw)) as z:
 assert z.testzip() is None and len(z.namelist())==len(ix['members']) and set(z.namelist())==set(ix['members'])
 for name,r in ix['members'].items():b=z.read(name);assert sha(b)==r['SHA256'] and len(b)==r['bytes'];p=a.state/name;assert p.resolve().is_relative_to(a.state.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
pointer=json.loads((a.state/'recovery/POINTER.json').read_text());assert pointer['snapshot_SHA256']==ix['genuine_snapshot_SHA256'] and pointer['state_hash']==ix['genuine_state_hash'];(a.state/'BYTE_RESTORE.json').write_text(json.dumps(dict(status='PASS_BYTE_EXACT_PUBLIC_RESTORE_NATIVE_ARITHMETIC_NOT_RUN',artifact_commit=a.artifact_commit,members=len(ix['members']),rows=pointer['completed_minutes'],state_hash=pointer['state_hash'],account_advances=0,new_fits=0,provider_downloads=0),indent=2)+'\n');print('ACTUAL_PUBLIC_PRESERVED_ACCOUNT_BYTE_RESTORE',pointer['completed_minutes'],len(ix['members']),flush=True)
