"""Export four exact public original NPZ byte streams to small UTF-8 Base64."""
import base64,hashlib,io,json,subprocess,textwrap,time,zipfile
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def sha(b):return hashlib.sha256(b).hexdigest()
def git(spec):return subprocess.check_output(['git','show',spec],cwd=ROOT)
def save(p,x):p.write_text(json.dumps(x,indent=2,sort_keys=True)+'\n')
def run():
 assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT)
 P=json.loads((HERE/'PROTOCOL.json').read_text());dest=HERE/'public/ORIGINAL_TARGETS';assert not dest.exists();dest.mkdir(parents=True);records={};payloads={};begin=time.monotonic()
 for name,r in P['original_sources'].items():
  raw=git(r['commit']+':'+r['path']);assert len(raw)==r['bytes'];encoded=('\n'.join(textwrap.wrap(base64.b64encode(raw).decode('ascii'),76))+'\n').encode('ascii');assert base64.b64decode(encoded)==raw
  (dest/(name+'.b64')).write_bytes(encoded);records[name]={**r,'SHA256':sha(raw),'UTF8_Base64_file':name+'.b64','UTF8_Base64_bytes':len(encoded),'UTF8_Base64_SHA256':sha(encoded)};payloads[name]=raw
  if r.get('risk_path'):records[name]['risk_SHA256']=sha(git(r['commit']+':'+r['risk_path']))
  print('ACTUAL_EXACT_TARGET_EXPORT',name,len(raw),sha(raw),flush=True)
 stream=io.BytesIO()
 with zipfile.ZipFile(stream,'w',zipfile.ZIP_STORED) as z:
  for name,raw in sorted(payloads.items()):z.writestr(zipfile.ZipInfo(name,(1980,1,1,0,0,0)),raw)
 raw=stream.getvalue();encoded=('\n'.join(textwrap.wrap(base64.b64encode(raw).decode('ascii'),76))+'\n').encode('ascii');assert base64.b64decode(encoded)==raw
 with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as z:
  assert z.testzip() is None and set(z.namelist())==set(records)
  for name,r in records.items():assert z.read(name)==payloads[name] and sha(z.read(name))==r['SHA256']
 (dest/'TARGETS.zip.b64').write_bytes(encoded);assert sum(p.stat().st_size for p in dest.iterdir())<P['budget_this_stage']['published_bytes']
 save(dest/'INDEX.json',dict(status='PASS_FOUR_ORIGINAL_PUBLIC_GIT_NPZ_BYTES_UNCHANGED_UTF8_BASE64',export_code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),protocol_SHA256=sha((HERE/'PROTOCOL.json').read_bytes()),files=records,package=dict(file='TARGETS.zip.b64',ZIP_bytes=len(raw),ZIP_SHA256=sha(raw),UTF8_Base64_bytes=len(encoded),UTF8_Base64_SHA256=sha(encoded),compression='STORED_ALREADY_COMPRESSED_ORIGINAL_NPZ'),downloads=0,array_recalculations=0,fits=0,new_wallets=0,seconds=time.monotonic()-begin))
if __name__=='__main__':run()
