import hashlib,json,subprocess,io,zipfile
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(raw):return hashlib.sha256(raw).hexdigest()
def file_sha(p):return sha(Path(p).read_bytes())
def save(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,sort_keys=True,indent=2,allow_nan=False)+'\n')
def git(spec):return subprocess.check_output(['git','show',spec],cwd=ROOT)
def clean(commit):assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT) and subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip()==commit
def verify():
 for line in (HERE/'SOURCE_SHA256.txt').read_text().splitlines():s,p=line.split(maxsplit=1);assert file_sha(ROOT/p)==s,p
def public_packet(commit,prefix):
 ix=json.loads(git(commit+':'+prefix+'INDEX.json'));raw=git(commit+':'+prefix+'PACKET.zip');assert sha(raw)==ix['SHA256'] and len(raw)==ix['bytes'];out={}
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  assert z.testzip() is None and set(z.namelist())==set(ix['members']) and len(z.namelist())==len(ix['members'])
  for name,r in ix['members'].items():b=z.read(name);assert sha(b)==r['SHA256'] and len(b)==r['bytes'];out[name]=b
 return out,ix
