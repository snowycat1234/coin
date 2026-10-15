"""Independent byte-level review; never decode the five approved numeric bodies."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{1})
import base64, hashlib, json, re, stat, urllib.parse, zipfile
from pathlib import Path, PurePosixPath

R=Path.cwd()
O=Path(__file__).resolve().parent
P=R/'full2025_source_generated_packet_20261015_v1'
Z=R/(P.name+'.zip')
W=R/'full2025_source_generated_packaging_20261015_v1'
EXPECTED_Z={'bytes':1559883,'SHA256':'e2278f738d5f2a3aa2d2d71a1b81bf80f80ebe96eeeeaea27a69a39edb0beade'}
EXPECTED_M={'bytes':53364,'SHA256':'2939fdfe4cde068fa88a524a539ace784b9d090c3eb084e50321ba4f6b10b606'}
def pin(raw):return {'bytes':len(raw),'SHA256':hashlib.sha256(raw).hexdigest()}
def pairs(rows):
    v={}
    for k,x in rows:
        assert k not in v,'DUPLICATE_JSON_KEY'
        v[k]=x
    return v
def parse(raw):return json.loads(raw,object_pairs_hook=pairs,parse_constant=lambda x:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def j(n):return parse((P/n).read_bytes())
def save(n,v):
    with (O/n).open('x') as f:json.dump(v,f,indent=2,sort_keys=True,allow_nan=False);f.write('\n')
def safe(n):
    q=PurePosixPath(n)
    return bool(n) and not q.is_absolute() and '\\' not in n and ':' not in n and all(x not in ('','.','..') for x in n.split('/')) and '\0' not in n

assert pin(Z.read_bytes())==EXPECTED_Z
assert pin((P/'FILE_MANIFEST.json').read_bytes())==EXPECTED_M
manifest=j('FILE_MANIFEST.json')['files']
assert len(manifest)==269 and 'FILE_MANIFEST.json' not in manifest
assert all(safe(n) for n in manifest)
disk={f.relative_to(P).as_posix():pin(f.read_bytes()) for f in P.rglob('*') if f.is_file()}
assert set(disk)==set(manifest)|{'FILE_MANIFEST.json'} and len(disk)==270
assert not any(f.is_symlink() for f in P.rglob('*'))
assert all(disk[n]==v for n,v in manifest.items())
extract=O/'cold_extraction'
assert not extract.exists()
extract.mkdir()
rows=[]
with zipfile.ZipFile(Z) as a:
    infos=a.infolist();names=[x.filename for x in infos]
    assert len(infos)==270 and len(names)==len(set(names))
    assert set(names)=={P.name+'/'+n for n in disk}
    assert a.testzip() is None
    for i in infos:
        assert safe(i.filename) and not i.flag_bits&1
        assert stat.S_ISREG(i.external_attr>>16) and not stat.S_ISLNK(i.external_attr>>16)
        assert i.file_size<=8*1024**2
        n=PurePosixPath(i.filename).relative_to(P.name).as_posix()
        raw=a.read(i)
        assert pin(raw)==disk[n] and raw==(P/n).read_bytes()
        out=extract/i.filename;out.parent.mkdir(parents=True,exist_ok=True)
        with out.open('xb') as f:f.write(raw)
        rows.append({'path':n,**pin(raw),'ZIP_CRC32':format(i.CRC,'08x'),'ZIP_compressed_bytes':i.compress_size})

mapping=j('ORIGINAL_COPY_MAPPING.json')['files']
assert len(mapping)==235 and len({x['packet_path'] for x in mapping})==235
assert len({x['original_workspace_relative_path'] for x in mapping})==235
original_pins={}
for row in mapping:
    n=row['packet_path'];src=row['original_workspace_relative_path']
    assert safe(n) and safe(src) and n==src
    assert row['copy_method']=='EXACT_BYTES_UNMODIFIED'
    f=R/src;assert f.is_file() and not f.is_symlink()
    expected={k:row[k] for k in ('bytes','SHA256')}
    assert pin(f.read_bytes())==disk[n]==expected
    original_pins[src]=expected
assert sum(x['bytes'] for x in mapping)==8246702
code=j('traditional_D_full2025_20261015/CODE_MANIFEST.json')['code_identity']
assert len(code)==94
assert all(n in original_pins and original_pins[n]['SHA256']==sha for n,sha in code.items())

derivatives=j('PUBLIC_DERIVATIVE_MAPPING.json')['files']
assert len(derivatives)==11 and len({x['packet_path'] for x in derivatives})==11
assert set(x['packet_path'] for x in derivatives).isdisjoint(original_pins)
bad=(b'/'+b'workspace/',b'/'+b'Users/',b'/'+b'home/agent/')
def scrub(v):
    if isinstance(v,str):return '[OMITTED_PRIVATE_ABSOLUTE_PATH]' if any(x.decode() in v for x in bad) else v
    if isinstance(v,list):return [scrub(x) for x in v]
    if isinstance(v,dict):
        return {('[OMITTED_PRIVATE_PATH_KEY_'+hashlib.sha256(k.encode()).hexdigest()[:12]+']' if any(x in k.encode() for x in bad) else k):scrub(x) for k,x in v.items()}
    return v
for row in derivatives:
    n=row['packet_path'];src=row['original_workspace_relative_path']
    assert safe(n) and safe(src) and n in disk and src not in disk
    assert row['not_exact_original_bytes'] is True
    original=(R/src).read_bytes()
    assert pin(original)==row['original']
    original_pins[src]=pin(original)
    v=j(n)
    assert v['original']==row['original'] and v['public_body']==scrub(parse(original))
    if n.startswith('public_derivatives/'):
        assert v['not_exact_original_bytes'] is True
        assert 'not current authority' in v['derivation']
    else:
        assert v['not_original_pinned_receipt'] is True and v['original_body_omitted_for_private_absolute_denial_path'] is True

small=set(j('BUILD_COPY_RECEIPT.json')['small_numeric_bodies_copied'])
assert len(small)==5
assert {n for n in disk if n.endswith('.npz')}=={n for n in small if n.endswith('.npz')}
assert len([n for n in small if n.endswith('.npz')])==2
privacy_issues=[];known_defaults=[];valid_authority=[]
prefixes=[str(R).encode(),*bad]
variants=[]
for x in prefixes:
    variants.extend([x,x.replace(b'/',b'\\/'),urllib.parse.quote_from_bytes(x,safe='').encode(),urllib.parse.quote_from_bytes(x,safe='/').encode(),base64.b64encode(x),x.hex().encode()])
signatures=[rb'gh[pousr]_[A-Za-z0-9_]{20,}',rb'AKIA[A-Z0-9]{16}',rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',rb'Bearer\s+[A-Za-z0-9_\-]{20,}']
def walk(v,n):
    if isinstance(v,dict):
        schema=v.get('schema','');action=v.get('action','')
        if schema in ('ROOT_GO_ORIGINAL_D_FULL2025_EXACT_NINE_V1','ROOT_SOURCE_PREP_FULL2025_V1') and action!='INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION':valid_authority.append(n)
        if schema=='EXTERNAL_FULL2025_SOURCE_STAGE_AUTHORIZATION_V1' and v.get('status')=='APPROVED_SOURCE_ONLY':valid_authority.append(n)
        for x in v.values():walk(x,n)
    elif isinstance(v,list):
        for x in v:walk(x,n)
for n in disk:
    raw=(P/n).read_bytes()
    if any(x in raw for x in variants):privacy_issues.append({'path':n,'finding':'PRIVATE_PREFIX_LITERAL_OR_REVERSIBLE_ENCODING'})
    if any(re.search(p,raw) for p in signatures):privacy_issues.append({'path':n,'finding':'SECRET_SIGNATURE'})
    if b'/home/ubuntu/coin/execution-state' in raw:known_defaults.append(n)
    assert not any(t in PurePosixPath(n).parts for t in ('EXECUTION_CLAIMS','opaque_cache','months'))
    assert not n.endswith(('.zip','.npy','.parquet','.bin','.pkl','.pickle','.pt','.pth','.safetensors','.pyc'))
    assert 'financial_attempt' not in n
    if n.endswith('.json') and n not in small:walk(j(n),n)
assert not privacy_issues and not valid_authority
assert known_defaults==['traditional_three_tier_freeze_20261015/sources/reference/joint_expert_information.py']

omissions=j('OMISSIONS_AND_HASH_ONLY_EVIDENCE.json')['files']
assert len({x['original_workspace_relative_path'] for x in omissions})==len(omissions)
assert all(x['body_included'] is False and x['original_workspace_relative_path'] not in disk for x in omissions)
external=j('EXTERNAL_RAW_SOURCE_DEPENDENCIES.json')
assert len(external['canonical_months'])==12 and sum(x['bytes'] for x in external['canonical_months'])==45314380
assert external['opaque_cache_objects']==217 and external['raw_source_archives_selected_in_historical_run']==180
assert not external['fresh_source_GO_alone_restores_full_raw_qualification']
deps=external['omitted_exact_runtime_metadata_dependencies']
assert len(deps)==4 and all(x['required_by_exact_frozen_load_plan'] and x['not_merely_a_test_fixture'] and not x['body_included'] for x in deps)
for x in deps:
    assert x['original_workspace_relative_path'] not in disk
    # Omitted runtime metadata is verified by hash only; never substituted.
    raw=(R/x['original_workspace_relative_path']).read_bytes()
    assert pin(raw)=={k:x[k] for k in ('bytes','SHA256')}
    original_pins[x['original_workspace_relative_path']]=pin(raw)
    assert any(o['original_workspace_relative_path']==x['original_workspace_relative_path'] and o['original']==pin(raw) for o in omissions)

frozen_rows=[]
omitted_by_path={o['original_workspace_relative_path']:o['original'] for o in omissions}
for folder in ('traditional_D_full2025_20261015','full2025_selective_source_qualification_20261015_v2'):
    fm=j(folder+'/FROZEN_PACKAGE_MANIFEST.json')
    for r in fm['files']:
        n=folder+'/'+r['file'];expected={k:r[k] for k in ('bytes','SHA256')}
        assert disk.get(n,omitted_by_path.get(n))==expected
        frozen_rows.append({'path':n,**expected,'body_included':n in disk})

cold=j('COLD_TEST_RECEIPT.json')
assert (cold['tests_run'],cold['tests_passed'],cold['explicit_skips'],cold['failures'],cold['errors'])==(223,217,6,0,0)
assert (cold['exact_archived_tests_declared'],cold['exact_archived_tests_passed'],cold['additional_packet_integrity_tests_passed'])==(217,211,6)
assert cold['archived_counts']=={'qualifier_author':50,'qualifier_independent':60,'D_author':58,'D_independent_including_terminal_supplement':49}
for suite,counts in (('QUALIFIER',(113,109,4)),('FULL',(110,108,2))):
    r=j(suite+'_COLD_RECEIPT.json')
    assert (r['tests_run'],r['tests_passed'],len(r['skipped']))==counts
    assert r['status'].startswith('PASS') and r['failures']==r['errors']==0
    assert not any(r['observed'].values()) and not r['blocked_attempts'] and not r['exact_copied_Python_files_changed'] and not r['foreign_project_modules']
    assert r['CPU_affinity']==[2] and all(x==[2] for x in r['all_TID_affinities'].values())
    assert all(x=='1' for x in r['thread_environment'].values())
for n in ('cold_failed_attempt001/SUMMARY.json','cold_failed_attempt002/SUMMARY.json'):
    r=j(n);assert r['not_a_PASS'] and not r['original_code_and_tests_rewritten'] and r['actual_source_or_financial_actions']==0

for sidecar in ('SEALED_ARCHIVE_TRANSPORT.json','PUBLIC_TRANSPORT_FILE_LIST.json'):
    v=parse((W/sidecar).read_bytes())
    if sidecar.startswith('PUBLIC'):
        for x in v['files']:
            assert safe(x['path']) and pin((R/x['path']).read_bytes())=={k:x[k] for k in ('bytes','SHA256')}
    else:assert v['archive_pin']==EXPECTED_Z and v['manifest_pin']==EXPECTED_M
save('ARCHIVE_FULL_FILE_ALLOWLIST.json',{'schema':'INDEPENDENT_FULL2025_ARCHIVE_ALLOWLIST_V1','archive_pin':EXPECTED_Z,'manifest_pin':EXPECTED_M,'members':rows,'members_count':len(rows)})
save('BEFORE_ORIGINAL_INPUT_PINS.json',{'schema':'INDEPENDENT_FULL2025_BEFORE_ORIGINAL_INPUT_PINS_V1','files':original_pins})
save('STATIC_REVIEW_RECEIPT.json',{'schema':'INDEPENDENT_FULL2025_STATIC_PACKET_REVIEW_V1','status':'PASS_STATIC_BYTES_SCOPE_AND_DOCUMENTED_RECOVERY_LIMITS','archive_pin':EXPECTED_Z,'manifest_pin':EXPECTED_M,'members':270,'uncompressed_bytes':sum(x['bytes'] for x in disk.values()),'exact_original_copies':235,'exact_original_copy_bytes':8246702,'D_current_code_identity_files':94,'primary_builder_derivatives':10,'final_derivatives_including_failed_cold_receipt':11,'duplicate_archive_members':0,'unsafe_paths':0,'symlinks':0,'encrypted_members':0,'manifest_exact_file_set':True,'all_archive_and_disk_member_bytes_equal':True,'all_original_copies_exact':True,'all_derivative_original_pins_and_transformations_verified':True,'private_prefix_literal_or_reversible_encoding_matches':privacy_issues,'valid_actual_authority_bodies':valid_authority,'approved_numeric_bodies_byte_hashed_only':sorted(small),'approved_numeric_bodies_decoded':False,'actual_financial_results_in_archive':False,'raw_transport_parts_or_raw_archives_read':0,'canonical_month_bodies_read':0,'omitted_runtime_metadata_dependencies':deps,'cold_archived_counts_verified':True,'failed_cold_attempts_preserved':2,'known_public_upstream_default_paths':known_defaults,'static_secret_scan_is_not_universal_secret_absence_proof':True,'frozen_package_rows_verified':len(frozen_rows),'CPU_affinity':sorted(os.sched_getaffinity(0)),'publication_actions':0,'external_financial_run_reexecuted_or_inspected':False,'sealed_archive_modified':False})
print(json.dumps({'status':'PASS_STATIC','members':270,'copies':235,'D_code_identity':94,'derivatives_final':11,'extracted_for_cold':True}))
