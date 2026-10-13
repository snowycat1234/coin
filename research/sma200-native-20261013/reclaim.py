"""Only verified public-restored duplicates; all genuine observed states retained."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git(spec):return subprocess.check_output(['git','show',spec],cwd=ROOT)
source=Path('/workspace/follow-native-2023-public-cold/source_rebuilt');proof=json.loads((source.parent/'PUBLIC_RESTORE.json').read_text());assert proof['status']=='PASS_EXACT_PUBLIC_FOLLOW_ZERO_ADVANCE' and proof['observed_STATE_open_attempts']==proof['account_advances']==0
index=json.loads((source/'SOURCE_INDEX.json').read_text());assert (source/'SOURCE_INDEX.json').read_bytes()==git('f38617c5a0917490c8b90fba355ecf0d5f1b87f4:research/cs-2023-continuous-economics-20261012/source-result/SOURCE_INDEX.json');remove=[];links=[]
for phase,commit in index['quarter_artifacts'].items():
 ix=json.loads(git(commit+':research/cs-2023-continuous-economics-20261012/source-phases/'+phase+'/SOURCE_INDEX.json'))
 for r in ix['all_archives']:
  p=source/phase/r['raw_path'];c=Path(str(p)+'.CHECKSUM');assert p.is_file() and sha(p)==r['ZIP_SHA256'] and p.stat().st_size==r['ZIP_bytes'] and sha(c)==r['CHECKSUM_SHA256'];remove.extend([(p,commit,r['ZIP_SHA256']),(c,commit,r['CHECKSUM_SHA256'])])
for r in index['source_certificates']:
 if 'fold' in r:
  p=source/(r['fold']+'.zip');assert sha(p)==r['package_SHA256'];remove.append((p,r['commit'],r['package_SHA256']))
for cached,canonical,receipt in (
 (source/'months',Path('/workspace/cs-2023-state/SOURCE_OBSERVED/months'),source.parent/'PUBLIC_RESTORE.json'),
 (Path('/workspace/follow-native-2025-public-cold/source_rebuilt/source/months'),Path('/workspace/portfolio-risk-2025-state/PUBLIC_SOURCE_RECOVERED/source/months'),Path('/workspace/follow-native-2025-public-cold/PUBLIC_RESTORE.json')),
 (source.parent/'account',Path('/workspace/rejected-break-follow-native-state/OBSERVED_Y2023'),source.parent/'PUBLIC_RESTORE.json'),
 (Path('/workspace/follow-native-2025-public-cold/account'),Path('/workspace/rejected-break-follow-native-state/OBSERVED_Y2025'),Path('/workspace/follow-native-2025-public-cold/PUBLIC_RESTORE.json')),
 (Path('/workspace/follow-cash-quota-public-restored'),Path('/workspace/follow-cash-compatibility-state/OBSERVED_Y2023'),ROOT/'research/follow-cash-compatibility-20261012/report/Y2023/NATIVE_COLD.json')):
  certificate=json.loads(receipt.read_text());assert certificate['status'].startswith('PASS')
  for p in cached.rglob('*'):
   if p.is_file():
    c=canonical/p.relative_to(cached)
    if c.is_file():assert sha(p)==sha(c) and p.stat().st_size==c.stat().st_size;links.append((p,c,sha(p)))
before=shutil.disk_usage('/workspace').free;records=[]
for p,c,digest in links:
 same=os.path.samefile(p,c);records.append(dict(path=str(p),canonical=str(c),SHA256=digest,bytes=p.stat().st_size,operation='ALREADY_SHARED' if same else 'BYTE_IDENTICAL_HARDLINK'))
 if not same:temporary=p.with_name(p.name+'.verified-link');assert not temporary.exists();os.link(c,temporary);temporary.replace(p);assert sha(p)==digest
for p,commit,digest in remove:records.append(dict(path=str(p),public_commit=commit,SHA256=digest,bytes=p.stat().st_size,operation='REMOVE_PUBLIC_DUPLICATE_RAW_ONLY'));p.unlink()
after=shutil.disk_usage('/workspace').free;assert after>=16106127360
out=dict(status='PASS_VERIFIED_PUBLIC_DUPLICATE_STORAGE_REUSE',before_free_bytes=before,after_free_bytes=after,freed_actual_bytes=after-before,records=records,original_financial_states_written_or_removed=0,source_month_bytes_changed=0,failures_removed=0,public_proofs_retained=True,public_source_cache_qualification='PREVIOUS_INDEPENDENT_COLD_PROOF_REUSED_BYTES_NOW_MAY_SHARE_CANONICAL_INODE_NOT_NEW_INDEPENDENT_RESTORE');(HERE/'evidence/RESOURCE_REUSE.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n');print('ACTUAL_VERIFIED_DUPLICATE_REUSE',len(remove),len(links),after-before,after,flush=True)
