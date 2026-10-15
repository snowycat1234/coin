"""Read-only hash preservation and decompressed public-scope review."""
from pathlib import Path
from copy import deepcopy
from decimal import Decimal, localcontext
import ast, gzip, hashlib, json, os, re, resource, sys, time

OUT=Path(__file__).resolve().parent;W=OUT.parent
NAME='traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1'
R=OUT/'fresh_extraction'/NAME
assert os.sched_getaffinity(0)=={7}
start=time.monotonic();cpu=time.process_time()
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()
def pin(p):return dict(sha256=sha(p),bytes=Path(p).stat().st_size)
def unique(pairs):
    d={}
    for k,v in pairs:
        assert k not in d,'DUPLICATE_JSON_KEY';d[k]=v
    return d
def load(p):
    p=Path(p);b=p.read_bytes()
    if p.suffix=='.gz':b=gzip.decompress(b)
    return json.loads(b,object_pairs_hook=unique,parse_constant=lambda s:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(',',':'),allow_nan=False)

preservation_path=W/'traditional_D_partial2021_saved_results_packaging_20261015/LOCAL_FULL_RECOVERY_MANIFEST.json'
assert sha(preservation_path)=='a4b39431210645114629954a83c5a75439e55e35dab5190875549616b4bb3feb'
pres=load(preservation_path);assert len(pres['files'])==268
for rel,expected in pres['files'].items():assert pin(W/rel)==expected,'ORIGINAL_HASH_OR_SIZE_CHANGED:'+rel
for rel,expected in pres['directory_file_sets'].items():
    actual=sorted(str(p.relative_to(W/rel)) for p in (W/rel).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    assert actual==sorted(expected),'ORIGINAL_FILESET_CHANGED:'+rel
assert len(pres['MINUTE_outputs'])==9 and sum(v['bytes'] for v in pres['MINUTE_outputs'].values())==409691086
pins=load(R/'FULL_SAVED_OUTPUT_HASH_PINS.json')['files']
assert len(pins)==275
for rel,expected in pins.items():assert pin(W/rel)==expected,'ORIGINAL_OR_PACKAGING_SUPPORT_PIN_CHANGED:'+rel
assert all(pins[rel]==ref for rel,ref in pres['files'].items())

source_receipt_path=W/'coin_recovery_state/partial2021_source_generated_publication_20261015/PUBLICATION_VERIFIED.json'
assert sha(source_receipt_path)=='fc30cd10b3106e2020878afaafa8a05076225eb1eeaf5a7f850a9b723da078e1'
sr=load(source_receipt_path);source=load(R/'SOURCE_PUBLICATION_REFERENCE.json')
assert sr['status']=='PASS' and sr['commit']==source['source_commit']=='f8239806dd68e833273c6684102ebefffc3033b1'
assert sr['parent_commit']==source['source_parent_commit']=='bf2b1d40df9958033e7d61c38c5b8f343127771b'
assert sr['parents_exact']==[sr['parent_commit']]
assert sr['remote_content_verification']['every_remote_byte_matches_expected_local'] is True
assert sr['archive']['SHA256']==source['source_archive_sha256']=='b0dcec82a6f8c28feba170aa080a131fb6c6494b3b06b2046a962e99f004c8f7'
assert sr['archive']['bytes']==source['source_archive_bytes']==696892
assert source['full_private_publication_receipt_sha256']==sha(source_receipt_path)

m=load(R/'MANIFEST.json')
markers=[b'/'+b'workspace/',b'/'+b'tmp/',b'/'+b'home/agent/',b'/'+b'Users/',b'-----BEGIN '+b'PRIVATE KEY',b'github_'+b'pat_',b'gh'+b'p_',b'Bearer'+b' ']
secret_patterns=[rb'(?i)(?:api[_-]?key|access[_-]?token|password|secret)\s*[=:]\s*["\x27][A-Za-z0-9_+./=-]{16,}',rb'AKIA[0-9A-Z]{16}',rb'xox[baprs]-[A-Za-z0-9-]{16,}']
denied_basenames={'ADMISSION_GO.json','LAUNCH_CLAIM.json','PROCESS_OWNERSHIP.json','BOOTSTRAP_READY.json','ADMISSION_REVIEW.json'}
json_count=0;gzip_count=0;scanned_bytes=0;static_modules=[]
for rel in sorted(set(m['files'])|{'MANIFEST.json'}):
    p=R/rel;b=p.read_bytes()
    assert p.suffix not in ('.npz','.npy','.log') and p.name not in denied_basenames
    if p.suffix=='.gz':b=gzip.decompress(b);gzip_count+=1
    scanned_bytes+=len(b)
    assert not any(mark in b for mark in markers),'PRIVATE_PREFIX_OR_CREDENTIAL_MARKER:'+rel
    assert not any(re.search(pattern,b) for pattern in secret_patterns),'SECRET_PATTERN:'+rel
    if p.suffix=='.json' or p.name.endswith('.json.gz'):load(p);json_count+=1
    if p.suffix=='.py':
        tree=ast.parse(b.decode(),filename=rel)
        imports=sorted({n.module or '' for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}|{a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names})
        static_modules.append(dict(path=rel,imports=imports,executed=rel in {'saved_native_reconciliation.py','saved_report.py','verify_packet.py','test_packet.py'}))

omitted=load(R/'OMITTED_ARRAYS_AND_RECOVERY_LIMITS.json')
assert omitted['raw_market_source_target_and_covariance_arrays_omitted'] is True
assert omitted['all_minute_risk_regeneration_self_contained'] is False and omitted['omitted_bytes_recoverable_from_hashes'] is False
assert {c:{k:v for k,v in ref.items() if k!='source'} for c,ref in omitted['MINUTE_outputs'].items()}==pres['MINUTE_outputs']
frozen=load(R/'traditional_D_partial2021_20261015/FROZEN_NINE_CELL_MANIFEST.json')
assert omitted['frozen_input_array_and_source_artifact_pins']==frozen['source_target_artifacts']
report=load(R/'summary/REPORT.json');scope=report['scope']
assert len(report['rows'])==9 and len(report['descriptive_period_rows'])==27
assert scope['partial_return_annualized'] is False and scope['annual_or_cross_cell_wallets_compounded'] is False and scope['continuous_CAGR'] is None
assert scope['OOS_or_live_performance_claim'] is False and scope['native_exchange_or_funding_publication_certified'] is False
assert scope['execution_alias_or_future_reuse_permission'] is False and scope['full_audit_byte_identity_claim'] is False
assert scope['all_minute_risk_regenerated'] is False
financial_rows=[]
for row in report['rows']:
    assert row['period_days']==274 and row['completed_minutes']==row['required_minutes']==394560 and row['initial_wallet_USDT']=='10000'
    assert row['observed_funding_events']==4110 and row['native_applied_funding_events']==4105 and row['fresh_flat_no_past_mark_events']==5
    assert row['actual_paid_market_flat'] is True and row['internal_transfer_count']==row['conditional_settlement_count']==0 and Decimal(row['unpaid_liability_USDT'])==0
    with localcontext() as c:
        c.prec=100;assert Decimal(row['period_return_fraction'])==(Decimal(row['terminal_NAV_USDT'])-Decimal('10000'))/Decimal('10000')
    financial_rows.append({k:row[k] for k in ('cell_id','terminal_NAV_USDT','period_return_fraction','fees_USDT','execution_cost_USDT','signed_funding_USDT','gross_paid_market_turnover_USDT','D_warning_signals','paid_full_warning_exits','forecast_budget_overshoot_minutes','minimum_free_cash_minute_close_USDT','maximum_isolated_margin_minute_close_USDT','gross_held_max_minute_close','raw100_stored_delta_residuals')})
eq=load(R/'traditional_D_partial2021_independent_review_20261015/actual_nine_saved_review/STATIC50_H090_POST_HOC_SAVED_EQUALITY.json')
assert len(eq['pairs'])==3
for pair in eq['pairs']:
    a,b=(pair[k] for k in ('STATIC50_cell','H090_cell'))
    assert pres['MINUTE_outputs'][a]==pres['MINUTE_outputs'][b]
    assert pair['both_separately_executed'] is True and pair['raw_target_paths_byte_exact'] is False
    assert pair['full_saved_financial_audit_exact_except_scope_metadata'] is False and pair['different_fill_request_records']>0

receipt=dict(schema='INDEPENDENT_STATIC_PRIVACY_ORIGINAL_PRESERVATION_V1',status='PASS',
    source_verified_commit=sr['commit'],source_sole_parent=sr['parent_commit'],source_private_receipt_sha256=sha(source_receipt_path),source_archive_sha256=sr['archive']['SHA256'],source_archive_bytes=sr['archive']['bytes'],
    source_receipt_read_locally_no_network=True,original_preservation_manifest_sha256=sha(preservation_path),original_files_rehashed=268,original_directory_sets_unchanged=True,full_saved_pin_files_rehashed=275,MINUTE_outputs_stream_hashed_without_loading=9,MINUTE_output_bytes=409691086,
    decompressed_packet_members_scanned=131,decompressed_bytes_scanned=scanned_bytes,strict_finite_unique_key_JSON_members=json_count,lossless_gzip_members=gzip_count,private_bodies_or_raw_array_members_found=False,private_prefix_or_secret_markers_found=False,
    static_Python_modules=static_modules,financial_rows_preserved=financial_rows,
    source_and_target_arrays_not_loaded=True,all_nine_executions_retained=True,realized_duplicate_pairs=3,full_audit_identity_or_alias_authority=False,deep_minute_risk_MDD_recovery_self_contained=False,
    CPU_affinity=sorted(os.sched_getaffinity(0)),numerical_threads=1,wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-cpu,maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    accounts_constructed=0,financial_clocks_advanced=0,financial_children_launched=0,provider_iterations=0,source_downloads=0,publication_performed=False)
(OUT/'STATIC_PRIVACY_PRESERVATION_RECEIPT.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in receipt.items() if k not in ('financial_rows_preserved','static_Python_modules')},sort_keys=True))
