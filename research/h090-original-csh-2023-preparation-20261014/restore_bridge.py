"""Immutable code/evidence assembly only. No account, source job or trading."""
import sys
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and sys.flags.optimize==0):
 raise RuntimeError('ISOLATED_NO_SITE_NO_BYTECODE_ASSERTIONS_ENABLED_REQUIRED')
from pathlib import Path,PurePosixPath
import argparse,gzip,hashlib,io,json,re
HERE=Path(__file__).resolve().parent
SCIENCE='coin_h090_original2023_bridge_20261014'
SCIENCE_SHA='c209bab0cc76cfc265be8fb61d45fbc1246c139c4b10470e4bfbc25a00b3b5ed'
FORBIDDEN=('.npy','.parquet','.arrow','.zip','.whl','.so','.pyc')
def digest(b):return hashlib.sha256(b).hexdigest()
def safe_name(name,npz=False):
 p=PurePosixPath(name)
 if not isinstance(name,str) or p.is_absolute() or '..' in p.parts or '\\' in name or str(p)!=name or not p.parts or name.lower().endswith(FORBIDDEN) or name.lower().endswith('.npz') and not npz:raise ValueError('SAFE_CODE_OR_DECLARED_HASH_ONLY_PATH_REQUIRED')
 return Path(*p.parts)
def no_links(p):
 if any(x.is_symlink() for x in (p,*p.parents)):raise ValueError('SYMLINK_REFUSED')
def checked(p,r,allow_npz=False):
 no_links(p)
 if p.suffix.lower() in FORBIDDEN or p.suffix.lower()=='.npz' and not allow_npz or not p.is_file() or p.stat().st_size!=r['bytes']:raise ValueError('EXACT_REGULAR_BODY_REQUIRED')
 b=p.read_bytes()
 if digest(b)!=r['SHA256']:raise ValueError('BODY_SHA256_REQUIRED')
 return b
def payload(expected):
 if not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('EXTERNAL_MANIFEST_SHA_REQUIRED')
 path=HERE/'PUBLIC_PAYLOAD_MANIFEST.json';no_links(path);raw=path.read_bytes()
 if digest(raw)!=expected:raise ValueError('EXTERNAL_MANIFEST_PIN_REQUIRED')
 m=json.loads(raw)
 if m['schema']!='FINITE_ORIGINAL2023_MINIMAL_PUBLIC_TRANSPORT_V1' or m['science_manifest_SHA256']!=SCIENCE_SHA:raise ValueError('EXACT_TRANSPORT_SCIENCE_REQUIRED')
 wanted=set(m['files'])|{'PUBLIC_PAYLOAD_MANIFEST.json'};dirs={str(p) for name in wanted for p in safe_name(name).parents if str(p)!='.'};actual=set();actual_dirs=set()
 for p in HERE.rglob('*'):
  no_links(p);name=p.relative_to(HERE).as_posix()
  if p.is_file():actual.add(name)
  elif p.is_dir():actual_dirs.add(name)
  else:raise ValueError('REGULAR_PAYLOAD_ENTRIES_REQUIRED')
 if actual!=wanted or actual_dirs!=dirs:raise ValueError('EXACT_PAYLOAD_SET_REQUIRED')
 values={n:checked(HERE/safe_name(n),r) for n,r in m['files'].items()}
 if digest(values[SCIENCE+'/PREPARATION_MANIFEST.json'])!=SCIENCE_SHA:raise ValueError('EXACT_SCIENCE_PIN_REQUIRED')
 return values
def read_cache(index,r,allow_npz=False):
 if r['repository']!='snowycat1234/coin' or not re.fullmatch('[0-9a-f]{40}',r['commit']) or not re.fullmatch('[0-9a-f]{40}',r['GitBlobSHA1']):raise ValueError('IMMUTABLE_PUBLIC_CODE_REFERENCE_REQUIRED')
 b=checked(Path(index[r['SHA256']]),r,allow_npz)
 if hashlib.sha1(f'blob {len(b)}\0'.encode()+b).hexdigest()!=r['GitBlobSHA1']:raise ValueError('PUBLIC_GIT_BLOB_REQUIRED')
 return b
def assemble(values,index,include_npz):
 material={n:b for n,b in values.items() if n.startswith((SCIENCE+'/', 'independent_review/'))}
 reuse=json.loads(values['IMMUTABLE_CODE_REUSE.json'])
 if reuse['schema']!='FINITE_ORIGINAL2023_IMMUTABLE_CODE_REUSE_V1' or len(reuse['files'])!=183 or len(reuse['separately_authorized_public_checksum_only_archives'])!=2:raise ValueError('EXACT183_PLUS2_CLOSURE_REQUIRED')
 for alias,r in reuse['files'].items():safe_name(alias);material[alias]=read_cache(index,r)
 npz_records=reuse['separately_authorized_public_checksum_only_archives']
 if sum(r['bytes'] for r in npz_records.values())!=50586 or {Path(n).name for n in npz_records}!={'Y2023.npz','Y2025.npz'}:raise ValueError('EXACT_KNOWN_PUBLIC_CHECKSUM_ARTIFACTS_REQUIRED')
 if include_npz:
  for alias,r in npz_records.items():safe_name(alias,True);material[alias]=read_cache(index,r,True)
 catalog=json.loads(values['SAVED_EVIDENCE_CATALOG.json']);compressed=values['SAVED_SOURCE_AND_ATTEMPTS.json.gz']
 if len(compressed)!=catalog['archive_bytes'] or digest(compressed)!=catalog['archive_SHA256']:raise ValueError('EXACT_ARCHIVE_REQUIRED')
 with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as f:raw=f.read(catalog['decoded_bytes']+1)
 if len(raw)!=catalog['decoded_bytes'] or digest(raw)!=catalog['decoded_SHA256']:raise ValueError('BOUNDED_ARCHIVE_DECODE_REQUIRED')
 saved=json.loads(raw);members=saved['members'];expected={r['alias']:r for r in catalog['members']}
 if len(expected)!=len(members) or len(expected)!=len(catalog['members']):raise ValueError('SAVED_MEMBER_SET_REQUIRED')
 for r in members:
  alias=r['alias'];safe_name(alias)
  if r!=expected.pop(alias):raise ValueError('SAVED_MEMBER_RECORD_REQUIRED')
  b=saved['bodies_utf8_by_SHA256'][r['SHA256']].encode()
  if len(b)!=r['bytes'] or digest(b)!=r['SHA256'] or alias in material and material[alias]!=b:raise ValueError('EXACT_SAVED_BODY_REQUIRED')
  material[alias]=b
 if expected or saved['linked_binary_scientific_members']!=catalog['linked_binary_scientific_members']:raise ValueError('SAVED_LINK_SET_REQUIRED')
 for r in catalog['linked_binary_scientific_members']:
  safe_name(r['alias']);safe_name(r['restore_from_current_scientific_body']);b=values[r['restore_from_current_scientific_body']]
  if len(b)!=r['bytes'] or digest(b)!=r['SHA256']:raise ValueError('EXACT_SAVED_BINARY_LINK_REQUIRED')
  material[r['alias']]=b
 manifest=json.loads(material[SCIENCE+'/PREPARATION_MANIFEST.json'])
 for name,r in manifest['files'].items():
  b=material[SCIENCE+'/'+name]
  if len(b)!=r['bytes'] or digest(b)!=r['SHA256']:raise ValueError('RESTORED_SCIENTIFIC_BYTES_REQUIRED')
 closure=json.loads(material[SCIENCE+'/EXECUTED_SOURCE_CLOSURE.json']);all_refs={n:h for m in closure['modes'].values() for n,h in m['files_SHA256'].items()}
 if len(all_refs)!=185 or set(all_refs)!=set(reuse['files'])|set(npz_records):raise ValueError('EXACT_BOUND_CLOSURE_SET_REQUIRED')
 for alias,sha in all_refs.items():
  if alias in material:
   if digest(material[alias])!=sha:raise ValueError('EXACT_CLOSURE_BODY_REQUIRED')
  elif alias not in npz_records or npz_records[alias]['SHA256']!=sha:raise ValueError('MISSING_CLOSURE_IDENTITY')
 return material,reuse,catalog
def main():
 p=argparse.ArgumentParser();p.add_argument('--manifest-sha',required=True);p.add_argument('--cache-index',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--include-public-checksum-only',action='store_true');a=p.parse_args()
 values=payload(a.manifest_sha);no_links(a.cache_index);index=json.loads(a.cache_index.read_text());material,reuse,catalog=assemble(values,index,a.include_public_checksum_only)
 no_links(a.output);no_links(a.receipt);out=a.output.resolve();receipt=a.receipt.resolve()
 if out.exists() or receipt.exists() or out.is_relative_to(HERE) or receipt.is_relative_to(HERE) or receipt.is_relative_to(out):raise ValueError('FRESH_EXTERNAL_OUTPUT_AND_RECEIPT_REQUIRED')
 out.mkdir(parents=True)
 for alias,b in material.items():
  target=out/safe_name(alias,a.include_public_checksum_only);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b)
 report={'schema':'FINITE_ORIGINAL2023_OFFLINE_RESTORE_RECEIPT_V1','status':'PASS_EXACT_SCIENCE_CODE_AND_SAVED_EVIDENCE_RESTORE','transport_manifest_SHA256':a.manifest_sha,'science_manifest_SHA256':SCIENCE_SHA,'restored_files':len(material),'reused_code_metadata_aliases':183,'bound_closure_paths':185,'checksum_only_archives_restored':2 if a.include_public_checksum_only else 0,'checksum_only_archive_bytes':50586 if a.include_public_checksum_only else 0,'array_values_parsed':0,'saved_attempt_members':len(catalog['members']),'historical_GO':False,'original26_runtime_admission':False,'project_imports':0,'new_accounts':0,'new_audits':0,'finance_retests':0,'network_calls':0,'restored_files_SHA256':{n:digest(b) for n,b in sorted(material.items())}}
 receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='restored_files_SHA256'},sort_keys=True));return 0
if __name__=='__main__':raise SystemExit(main())
