"""Offline code/evidence restore. No network, account imports or wallet advances."""
import sys
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and sys.flags.optimize==0):
    raise RuntimeError('ISOLATED_NO_SITE_NO_BYTECODE_ASSERTIONS_ENABLED_LAUNCH_REQUIRED')
from pathlib import Path,PurePosixPath
import argparse,gzip,hashlib,io,json,re
HERE=Path(__file__).resolve().parent
FORBIDDEN=('.npz','.npy','.parquet','.arrow','.csv','.whl','.so')
PREPARATION_SHA='a9b6cbf65b42003b77a9508b6c857ab1c8eee5bb9951cd0f089de56b06ea18b9'
REVIEW_SHA='d2538894cd8c8d0925cb770e51806e9bb49409c84ceb13132bac9964089812d3'
WITNESS_SHA='99b934cdbf99679512cf484cb145a654d131207d5d94cb92433a2aa6a4b2ce97'
PACKAGE='coin_paired_headroom_native_generated_20261014'

def digest(data):return hashlib.sha256(data).hexdigest()
def relative(name):
    p=PurePosixPath(name)
    if not isinstance(name,str) or '\\' in name or p.is_absolute() or '..' in p.parts or str(p)!=name or not p.parts:
        raise ValueError('SAFE_CANONICAL_RELATIVE_PATH_REQUIRED')
    if name.lower().endswith(FORBIDDEN):raise ValueError('CODE_ONLY_ARRAY_AND_BINARY_PATH_REFUSED')
    return Path(*p.parts)
def nonsymlink(path,stop):
    for p in [path,*path.parents]:
        if p==stop.parent:break
        if p.is_symlink():raise ValueError('SYMLINK_REFUSED')
def checked(path,record):
    if path.suffix.lower() in FORBIDDEN:raise ValueError('CACHE_ARRAY_OR_BINARY_PATH_REFUSED')
    if not path.is_file() or path.is_symlink():raise ValueError('REGULAR_CODE_FILE_REQUIRED')
    if path.stat().st_size!=record['bytes']:raise ValueError('EXACT_BLOB_SIZE_REQUIRED')
    data=path.read_bytes()
    if digest(data)!=record['SHA256']:raise ValueError('EXACT_BLOB_SHA256_REQUIRED')
    return data
def verify_payload(expected):
    if not re.fullmatch('[0-9a-f]{64}',expected):raise ValueError('EXTERNAL_MANIFEST_SHA_REQUIRED')
    manifest_path=HERE/'PUBLIC_PAYLOAD_MANIFEST.json';nonsymlink(manifest_path,HERE)
    raw=manifest_path.read_bytes()
    if digest(raw)!=expected:raise ValueError('PUBLIC_MANIFEST_PIN')
    manifest=json.loads(raw)
    if manifest['schema']!='PAIRED_NATIVE_MINIMAL_PUBLIC_TRANSPORT_V1':raise ValueError('MANIFEST_SCHEMA')
    wanted_files=set(manifest['files'])|{'PUBLIC_PAYLOAD_MANIFEST.json'}
    wanted_dirs={str(parent) for name in wanted_files for parent in relative(name).parents if str(parent)!='.'}
    actual_files=set();actual_dirs=set()
    for path in HERE.rglob('*'):
        nonsymlink(path,HERE);name=path.relative_to(HERE).as_posix()
        if path.is_file():actual_files.add(name)
        elif path.is_dir():actual_dirs.add(name)
        else:raise ValueError('REGULAR_PAYLOAD_ENTRY_REQUIRED')
    if actual_files!=wanted_files or actual_dirs!=wanted_dirs:raise ValueError('EXACT_PUBLIC_PAYLOAD_FILE_AND_DIRECTORY_SET_REQUIRED')
    values={}
    for name,record in manifest['files'].items():
        path=HERE/relative(name);nonsymlink(path,HERE)
        values[name]=checked(path,record)
    if 'restore_transport.py' not in values:raise ValueError('RESTORE_WRAPPER_NOT_BOUND')
    if digest(values[PACKAGE+'/PREPARATION_MANIFEST.json'])!=PREPARATION_SHA:raise ValueError('ACCEPTED_PREPARATION_PIN')
    if digest(values['review_paired_headroom_native_20261014/INDEPENDENT_REVIEW_PASS_a9b6.json'])!=REVIEW_SHA:raise ValueError('ACCEPTED_REVIEW_PIN')
    return manifest,values
def decompress(data,sha,size):
    with gzip.GzipFile(fileobj=io.BytesIO(data),mode='rb') as f:raw=f.read(size+1)
    if len(raw)!=size or digest(raw)!=sha:raise ValueError('LOSSLESS_GZIP_BODY_PIN')
    return raw
def plan_restore(manifest,values,index):
    materialized={name:body for name,body in values.items() if name.startswith((PACKAGE+'/',
        'coin_bot_historical_driver_preparation_20261014/','review_paired_headroom_native_20261014/'))}
    catalog=json.loads(values['IMMUTABLE_CODE_RESTORE.json'])
    if catalog['schema']!='PAIRED_NATIVE_CODE_ONLY_RESTORE_CATALOG_V1':raise ValueError('CODE_RESTORE_SCHEMA')
    for destination,record in catalog['files'].items():
        relative(destination)
        if not re.fullmatch('[0-9a-f]{40}',record['commit']) or not re.fullmatch('[0-9a-f]{40}',record['GitBlobSHA1']):raise ValueError('IMMUTABLE_PUBLIC_OBJECT_REQUIRED')
        cache=Path(index[record['SHA256']]).resolve()
        nonsymlink(Path(index[record['SHA256']]),Path(index[record['SHA256']]).parent)
        body=checked(cache,record)
        if hashlib.sha1(f'blob {len(body)}\0'.encode()+body).hexdigest()!=record['GitBlobSHA1']:raise ValueError('EXACT_GIT_BLOB_REQUIRED')
        materialized[destination]=body
    c=json.loads(values['GENERATED_EVIDENCE_CATALOG.json'])
    if digest(values['GENERATED_PRIORITY_WITNESS.json.gz'])!=c['gzip_SHA256']:raise ValueError('WITNESS_GZIP_PIN')
    raw=decompress(values['GENERATED_PRIORITY_WITNESS.json.gz'],c['restored_SHA256'],c['restored_bytes'])
    if digest(raw)!=WITNESS_SHA or len(json.loads(raw)['runs'])!=19:raise ValueError('COMPLETE_ACCEPTED_NINETEEN_RUNS_REQUIRED')
    for alias in c['aliases']:relative(alias);materialized[alias]=raw
    c=json.loads(values['ATTEMPT_ARCHIVE_CATALOG.json'])
    if digest(values['GENERATED_ATTEMPTS_AND_REVIEW.json.gz'])!=c['gzip_SHA256']:raise ValueError('ATTEMPT_GZIP_PIN')
    archive=json.loads(decompress(values['GENERATED_ATTEMPTS_AND_REVIEW.json.gz'],c['restored_archive_SHA256'],c['restored_archive_bytes']))
    records={r['alias']:r for r in c['members']}
    if len(records)!=len(c['members']) or len(archive['members'])!=len(records):raise ValueError('EXACT_ATTEMPT_ALIAS_SET_REQUIRED')
    for member in archive['members']:
        alias=member['alias'];relative(alias);body=member['body_utf8'].encode();r=records.pop(alias)
        if digest(body)!=r['SHA256'] or len(body)!=r['bytes']:raise ValueError('PROJECTED_ATTEMPT_BODY_PIN')
        if alias in materialized and materialized[alias]!=body:raise ValueError('CONFLICTING_ALIAS')
        materialized[alias]=body
    if records:raise ValueError('MISSING_ATTEMPT_ALIAS')
    preparation=json.loads(materialized[PACKAGE+'/PREPARATION_MANIFEST.json'])
    for name,r in preparation['files'].items():
        body=materialized[PACKAGE+'/'+name]
        if len(body)!=r['bytes'] or digest(body)!=r['SHA256']:raise ValueError('RESTORED_ACCEPTED_SCIENTIFIC_BODY_PIN')
    pins=json.loads(materialized[PACKAGE+'/DEPENDENCY_PINS.json'])
    for name,want in pins['files_SHA256'].items():
        if digest(materialized[name])!=want:raise ValueError('RESTORED_DEPENDENCY_PIN')
    return materialized
def main():
    p=argparse.ArgumentParser();p.add_argument('--manifest-sha',required=True);p.add_argument('--cache-index',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--receipt',type=Path,required=True);a=p.parse_args()
    manifest,values=verify_payload(a.manifest_sha)
    if a.cache_index.suffix.lower()!='.json':raise ValueError('LOCAL_JSON_CODE_CACHE_INDEX_REQUIRED')
    index=json.loads(a.cache_index.read_text());materialized=plan_restore(manifest,values,index)
    output=a.output.resolve();receipt=a.receipt.resolve()
    if output.exists() or receipt.exists() or output.is_relative_to(HERE) or receipt.is_relative_to(HERE) or receipt.is_relative_to(output):
        raise ValueError('FRESH_EXTERNAL_RESTORE_AND_RECEIPT_REQUIRED')
    # Complete source/cache/archive verification precedes every output write.
    output.mkdir(parents=True,exist_ok=False)
    for name,body in materialized.items():
        target=output/relative(name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(body)
    checked_science=len(json.loads(materialized[PACKAGE+'/PREPARATION_MANIFEST.json'])['files'])
    report=dict(schema='PAIRED_NATIVE_OFFLINE_PUBLIC_RESTORE_RECEIPT_V1',status='PASS_EXACT_CODE_AND_SAVED_EVIDENCE_RESTORE',
        public_manifest_SHA256=a.manifest_sha,accepted_preparation_SHA256=PREPARATION_SHA,accepted_review_SHA256=REVIEW_SHA,
        immutable_reused_blobs=len(json.loads(values['IMMUTABLE_CODE_RESTORE.json'])['files']),
        restored_scientific_files=checked_science,restored_files=len(materialized),complete_generated_runs=19,
        generated_witness_SHA256=WITNESS_SHA,original_preparation_bytes_unchanged=True,
        projected_attempt_evidence='HOST_PREFIX_ONLY_WITH_PUBLIC_ORDERED_PROJECTION_PROOF',
        historical_GO=False,array_files_opened=0,network_calls=0,project_imports=0,CONTROL_retests=0,
        wallet_advances=0,restored_files_SHA256={name:digest(body) for name,body in sorted(materialized.items())})
    receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='restored_files_SHA256'},sort_keys=True))
if __name__=='__main__':raise SystemExit(main())
