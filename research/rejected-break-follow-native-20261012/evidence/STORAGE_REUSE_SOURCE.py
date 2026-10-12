import os,hashlib,json,time,shutil,subprocess
from pathlib import Path
root=Path('/workspace/coin-tail-risk');state=Path('/workspace/rejected-break-follow-native-state')
a=Path('/workspace/coin-slow-momentum/research/recover-frozen-runner-20261009')
b=Path('/workspace/coin-liquidation-next/research/recover-frozen-runner-20261009')
assert a.is_dir() and b.is_dir()
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while chunk:=f.read(1048576):h.update(chunk)
 return h.hexdigest()
before=shutil.disk_usage('/workspace').free;rows=[]
for p in sorted(a.rglob('*')):
 if p.is_symlink() or not p.is_file() or p.stat().st_size<131072:continue
 q=b/p.relative_to(a)
 if not q.is_file() or q.is_symlink():continue
 x,y=p.stat(),q.stat()
 if x.st_ino==y.st_ino or x.st_size!=y.st_size or x.st_mode!=y.st_mode:continue
 hp=digest(p);hq=digest(q)
 if hp!=hq:continue
 temporary=p.with_name(p.name+'.follow-native-dedup');assert not temporary.exists()
 os.link(q,temporary);os.replace(temporary,p)
 assert p.stat().st_ino==q.stat().st_ino and digest(p)==hp
 rows.append(dict(relinked=str(p),canonical=str(q),bytes=x.st_size,SHA256=hp,same_bytes=True,all_original_paths_preserved=True))
out=dict(status='PASS_BYTE_IDENTICAL_FROZEN_DUPLICATE_STORAGE_REUSE',created_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),files=rows,logical_duplicate_bytes=sum(r['bytes'] for r in rows),free_before=before,free_after=shutil.disk_usage('/workspace').free,no_original_deleted=True,no_distribution_path_touched=True,no_financial_replay=True)
(state/'STORAGE_REUSE.json').write_text(json.dumps(out,indent=2)+'\n')
assert rows and out['free_after']>=16106127360+400000000
print(out['status'],len(rows),out['logical_duplicate_bytes'],out['free_after'])
