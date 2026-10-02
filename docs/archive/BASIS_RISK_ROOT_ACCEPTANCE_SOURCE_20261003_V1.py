"""Accept closed fixed-period risk diagnostics without redoing price math or QA."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/BASIS_RISK_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py'
OUT=ROOT/'reports/fast_research/BASIS_RISK_ROOT_ACCEPTANCE_20261003_V1.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
assert not OUT.exists() and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
hashes={ARCHIVE:sha(ROOT/ARCHIVE)};receipts=[]
names=[
 ('reports/fast_research/BASIS_RISK_DIAGNOSTIC_TINY_20261003_V1.json','3bfdf7067ce90136b8ae7a80574ea5a8995492cff117e3e07bd004d1f1502387','chunk:528ef1; closed task independently observed0'),
 ('reports/fast_research/BASIS_RISK_DIAGNOSTIC_122D_ACTUAL_20261003_V1.json','5bb427dc3b5d2a79033176d56f56442f4190a6a65e9ea723c50b2cda35c55be1','session:21964 / chunk:16b8cd'),
 ('reports/fast_research/BASIS_RISK_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json','63b4b228bd1b6722c3537110739de2ce7a6193bf1eb4637c896bf19a71c9c740','session:13576 / chunk:7d224d; independent agent actual0')]
def add(name,digest):
    p=ROOT/name
    assert not Path(name).is_absolute() and '..' not in Path(name).parts and p.is_file() and not p.is_symlink()
    assert p.stat().st_size<2000000 and sha(p)==digest,name
    assert name not in hashes or hashes[name]==digest
    hashes[name]=digest
for name,digest,host in names:
    add(name,digest);v=load(ROOT/name);identity=v['binding']['task_id']
    path=STATE/'task-progress'/('task-'+identity+'.json');task=load(path)
    assert task['id']==identity and task['status']=='completed' and task['exit_code']==0
    receipts.append(dict(path=name,sha256=digest,status=v['status'],actual_host_result=host,actual_exit=0,
                         actual_task_path=str(path),actual_task_sha256=sha(path),task=task))
tiny,actual,audit=[load(ROOT/name) for name,_,_ in names]
assert tiny['status']=='PASS_BASIS_RISK_SYNTHETIC_MATH_ALIGNMENT_NOT_MARKET_RESULT'
assert tiny['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0) and not tiny['price_arrays_read']
assert actual['status']=='COMPLETE_FIXED_QUANTITY_BASIS_CLOSE_PROXY_RISK_NOT_CASH_NAV_OR_APR'
assert audit['status']=='PASS_FIXED_QUANTITY_BASIS_DECIMAL_PROXY_RISK_NOT_PNL_NAV_APR'
assert actual['completed_files']==24 and audit['completed_files_verified']==24 and audit['completed_windows_verified']==10
assert audit['completed_joined_minutes']==351360 and audit['maximum_absolute_error_bp']<1e-7
assert len(actual['input_bindings'])==24 and [v['full_period']['rows'] for v in actual['per_symbol']]==[175680,175680]
assert actual['binding']['source_hashes']==tiny['binding']['source_hashes']==audit['verified_source_hashes']
assert actual['accepted_smoke_sha256']==names[0][1] and audit['actual_report_sha256']==names[1][1]
for name,digest in actual['binding']['source_hashes'].items():add(name,digest)
for value in (tiny,actual):
    assert value['source_bytes_unchanged'] and not value['locked_consumed'] and not value['funding_arrays_read']
    assert not value['fees_fills_NAV_cash_PnL_or_realized_funding_computed'] and not value['coupon_added_to_basis']
    assert value['candidate_status']=='NO_QUALIFIED_CANDIDATE' and value['capital_net_APR']=='NOT_EVALUABLE'
    assert value['resources']['ram_limit_bytes']<=5000000000 and value['resources']['swap_bytes']==0
    assert not value['resources']['gpu_used'] and value['disk']['status']=='OK'
used=STATE/'test-basis-risk-independent-audit-20261003-v1'
bound=load(used/'ACTUAL_BINDING.json')
archive_dir=ROOT/'docs/archive/BASIS_RISK_USED_INDEPENDENT_SOURCES_20261003_V1';archive_dir.mkdir()
archives=[]
for source,expected in [('audit.py',audit['independent_source_sha256']),
                        ('ACTUAL_BINDING.json',audit['binding']['ACTUAL_BINDING_sha256']),
                        ('METADATA_BINDING_PREPARATION_FAILURE_V1.json',bound['prior_metadata_preparation_failure_sha256'])]:
    p=used/source;assert p.is_file() and not p.is_symlink() and sha(p)==expected
    target=archive_dir/source
    with target.open('xb') as w:w.write(p.read_bytes())
    relative=str(target.relative_to(ROOT));add(relative,expected)
    archives.append(dict(original_path=str(p),archive_path=relative,sha256=expected))
for name in ('docs/archive/BASIS_RISK_PROTOCOL_FREEZER_20261003_V1.py','docs/archive/BASIS_RISK_PROTOCOL_FREEZER_20261003_V2.py',
             'reports/fast_research/BASIS_RISK_PROTOCOL_FREEZER_FAILURE_20261003_V1.json','reports/fast_research/BASIS_RISK_PROTOCOL_FREEZER_FAILURE_20261003_V2.json'):
    add(name,sha(ROOT/name))
for label,name,exit_code in [('FREEZER-V1', 'reports/fast_research/BASIS_RISK_PROTOCOL_FREEZER_FAILURE_20261003_V1.json',1),
                            ('FREEZER-V2', 'reports/fast_research/BASIS_RISK_PROTOCOL_FREEZER_FAILURE_20261003_V2.json',1),
                            ('INDEPENDENT-AUDIT',names[2][0],0)]:
    event=dict.fromkeys(FIELDS)
    event.update(experiment_id='BASIS-RISK-'+label+'-20261003-V1',event_id='BASIS-RISK-'+label+'-20261003-V1:RESULT',
        event_type='IMPORTED_OPERATIONAL_RESULT',git_commit=actual['binding']['git_commit'],
        data_manifest_hash=hashes['reports/fast_research/BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json'],
        protocol_hash=actual['binding']['protocol_sha256'] if exit_code==0 else None,
        feature_set='NONE_METADATA_FAILURE' if exit_code else 'FIXED_COIN_QUANTITY_CLOSE_RISK_ONLY',
        labels='NONE',model_family='NONE',hyperparameters='NO_SEARCH',seed='NONE_DETERMINISTIC',
        thresholds='NO_INVESTMENT_THRESHOLD',cost_assumptions='NO_ACCOUNT_COSTS_OR_COUPON_ADDING',
        all_folds='ALL122D_AND_FOUR_LOCAL_MONTHS' if exit_code==0 else 'NO_ARRAY_IO',
        success_failure=load(ROOT/name)['status'],reason_for_next_experiment='D029_FIXED_CONTINUOUS_CONDITIONAL_ACCOUNT',
        result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
        artifact_path=name,artifact_sha256=sha(ROOT/name),actual_exit=exit_code)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
value=dict(status='PASS_ROOT_FIXED_PERIOD_BASIS_RISK_NOT_CASH_NAV_APR',created_utc=datetime.now(UTC).isoformat(),
    root_task_id=os.environ['COIN_TASK_ID'],source_hashes=hashes,original_receipts=receipts,exact_used_source_archives=archives,
    selected_price_source_count=24,joined_minutes=351360,full_plus_monthly_windows=10,
    maximum_absolute_independent_error_bp=audit['maximum_absolute_error_bp'],
    source_arrays_QA_math_or_tests_replayed_by_root=False,metadata_failures_retained=2,
    marked_risk_not_capital_net_return=True,capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE',
    next_experiment='ONE_FIXED_CONDITIONAL_CONTINUOUS_CARRY_ACCOUNT_D029',
    ROOT_host_exit_requires_actual_closure_after_report_written=True)
with OUT.open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(OUT),source_files=len(hashes),root_task_id=value['root_task_id'])))
