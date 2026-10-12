import datetime,hashlib,json,os,shutil
from pathlib import Path
base=Path('/workspace/cs-2023-state');records=[]
for phase in ('Q1','Q2'):
 old=base/(phase+'_OBSERVED')/'raw';canonical=base/'SOURCE_OBSERVED'/phase/'raw'
 assert old.is_dir() and not old.is_symlink() and canonical.is_dir() and not canonical.is_symlink()
 left={str(p.relative_to(old)):p for p in old.rglob('*') if p.is_file()};right={str(p.relative_to(canonical)):p for p in canonical.rglob('*') if p.is_file()};assert set(left)==set(right)
 rows=[]
 for name,p in sorted(left.items()):
  raw=p.read_bytes();q=right[name];assert raw==q.read_bytes();rows.append(dict(path=name,bytes=len(raw),SHA256=hashlib.sha256(raw).hexdigest()))
 records.append(dict(phase=phase,old_path=str(old),canonical_path=str(canonical),files=rows,exact_bytes=sum(r['bytes'] for r in rows)))
for r in records:
 old=Path(r['old_path']);canonical=Path(r['canonical_path']);temporary=old.with_name('raw.DUPLICATE_PROVEN');link=old.with_name('raw.CANONICAL_LINK');assert not temporary.exists() and not link.exists()
 os.symlink(canonical,link,target_is_directory=True);old.rename(temporary);link.rename(old)
 for row in r['files']:
  p=old/row['path'];assert p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['SHA256']
 shutil.rmtree(temporary)
report=dict(check_UTC=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='EXACT_RAW_BYTE_DUPLICATES_DEDUPLICATED_ORIGINAL_PATHS_PRESERVED_VIA_CANONICAL_LINKS',records=records,reclaimed_exact_file_bytes=sum(r['exact_bytes'] for r in records),source_prices_retained=True,quarter_metadata_retained=True,financial_accounts_touched=0,financial_advances=0,provider_downloads=0,guard_budget_changed=False)
Path('/workspace/portfolio-risk-budget-state/RAW_DUPLICATE_REUSE.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='records'},indent=2))
