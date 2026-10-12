import subprocess,hashlib,io,json,zipfile
from pathlib import Path
root=Path('/workspace/coin-tail-risk');state=Path('/workspace/mark-trade-dislocation-state');commit='d69e9ac94478c5be54cb46c622afec7aaf3c61f7'
def git(p):return subprocess.check_output(['git','show',commit+':'+p],cwd=root)
ix=json.loads(git('research_artifacts/native_20261008/INDEX.json'));rows=[];wrappers=[]
for r in [r for r in ix['files'] if r['file_name'].startswith('coin_public_tail_archives_')]:
 pieces=[]
 for part in sorted([q for q in ix['published_files'] if q['file_name'].startswith(r['file_name']+'.bytepart')],key=lambda q:q['index']):
  raw=git(part['path']);assert len(raw)==part['bytes'] and hashlib.sha256(raw).hexdigest()==part['sha256'];pieces.append(raw)
 raw=b''.join(pieces);assert len(raw)==r['bytes'] and hashlib.sha256(raw).hexdigest()==r['sha256']
 with zipfile.ZipFile(io.BytesIO(raw)) as z:
  names=[n for n in z.namelist() if ('/klines/' in n or '/markPriceKlines/' in n) and ('2022-12' in n or '2024-12' in n)];rows.extend([dict(wrapper_file=r['file_name'],member=n,bytes=z.getinfo(n).file_size) for n in names])
 wrappers.append(dict(path=r['path'],file_name=r['file_name'],SHA256=r['sha256'],bytes=r['bytes']))
out=dict(commit=commit,wrappers=wrappers,matching_members=rows,scope='CENTRAL_DIRECTORY_ONLY_NO_CSV_VALUES_OR_ARRAYS_FITS_ACCOUNTS')
(state/'WARM_BOUNDARY_INVENTORY.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out))
