"""Accept completed conditional ledgers using proofs; never replay market math."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
import sys
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
ARCHIVE='docs/archive/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py'
OUT=ROOT/'reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
assert not OUT.exists() and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
hashes={ARCHIVE:sha(ROOT/ARCHIVE)};receipts=[]
names=[
 ('reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_TINY_20261003_V1.json','dcfe7aafa049e1f8f366ce2873b133fb7ea7882fc9c0894d63442cb60b92a0a4','chunk:4eff5d'),
 ('reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json','d036745c61ce30203d6c941af863979591425604b7cea879277a2e22f0a57bbf','session:10927 / chunk:1714f6'),
 ('reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json',sys.argv[1],sys.argv[2])]
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
assert tiny['status']=='PASS_CONDITIONAL_CARRY_SYNTHETIC_ACCOUNTING_NOT_MARKET_RESULT'
assert tiny['junit_counts']==dict(tests=1,errors=0,failures=0,skipped=0) and not tiny['price_arrays_read'] and not tiny['funding_arrays_read']
assert actual['status']=='COMPLETE_CONDITIONAL_CARRY_PROXY_ACCOUNT_UNIT_UNCERTIFIED_NOT_NATIVE_OR_LONG_TERM_APR'
assert audit['status']=='PASS_CONDITIONAL_CARRY_DECIMAL_PROXY_ACCOUNTING_NOT_NATIVE_OR_LONG_TERM_APR'
assert audit['actual_report_sha256']==names[1][1] and actual['accepted_smoke_sha256']==names[0][1]
assert tiny['binding']['source_hashes']==actual['binding']['source_hashes']==audit['verified_source_hashes']
assert audit['completed_source_files_verified']==32 and audit['completed_fills_verified']==8 and audit['completed_minutes_verified']==175680
assert audit['completed_original_funding_events_verified']==732 and audit['completed_days_verified']==122 and audit['completed_months_verified']==4
assert audit['maximum_cash_error_USDT']<=1e-7 and audit['maximum_ratio_error']<=1e-10
assert len(actual['input_bindings'])==32 and len(actual['output_bindings'])==4
assert actual['summary']['rows']==175680 and actual['summary']['owned_funding_events']==68
assert actual['summary']['excluded_funding_events']==664 and actual['summary']['net_PnL_USDT']<0
assert actual['summary']['exit_reason']=='SELF_DEFINED_RISK_STOP' and audit['permanent_cash_after_exit']
for name,digest in actual['binding']['source_hashes'].items():add(name,digest)
for v in (tiny,actual):
    assert v['source_bytes_unchanged'] and not v['locked_consumed'] and not v['old_QA_or_green_tests_repeated']
    assert not v['funding_unit_certified'] and not v['native_Bybit_prices_or_filters'] and not v['real_liquidation_MMR_or_ADL_modeled']
    assert v['capital_net_APR']=='NOT_EVALUABLE' and v['candidate_status']=='NO_QUALIFIED_CANDIDATE'
    assert v['resources']['ram_limit_bytes']<=5000000000 and v['resources']['swap_bytes']==0 and not v['resources']['gpu_used']
    assert v['disk']['status']=='OK'
outputs=[]
for row in actual['output_bindings']:
    p=Path(row['path']);assert p.is_file() and not p.is_symlink() and p.resolve().is_relative_to(STATE.resolve())
    assert sha(p)==row['sha256'];outputs.append(row)
used=STATE/'test-conditional-carry-independent-audit-20261003-v1'
archive_dir=ROOT/'docs/archive/CONDITIONAL_CARRY_USED_INDEPENDENT_SOURCES_20261003_V1';archive_dir.mkdir()
archives=[]
failed_metadata=load(used/'BINDING_PREPARATION_INVOKE_FAILURE_20261003_V1.json')
assert failed_metadata['actual_exit_code']==1 and failed_metadata['host_chunk']=='20071b'
assert not failed_metadata['python_executed'] and not failed_metadata['arrays_read']
used_sources=[('audit.py',audit['independent_source_sha256']),('ACTUAL_BINDING.json',audit['binding']['ACTUAL_BINDING_sha256'])]
used_sources.extend((name,sha(used/name)) for name in ('prepare_actual_binding.ps1','BINDING_PREPARATION_INVOKE_FAILURE_20261003_V1.json'))
for source,expected in used_sources:
    p=used/source;assert p.is_file() and not p.is_symlink() and sha(p)==expected
    target=archive_dir/source
    with target.open('xb') as w:w.write(p.read_bytes())
    relative=str(target.relative_to(ROOT));add(relative,expected);archives.append(dict(original_path=str(p),archive_path=relative,sha256=expected))
event=dict.fromkeys(FIELDS)
event.update(experiment_id='CONDITIONAL-CARRY-INDEPENDENT-AUDIT-20261003-V1',event_id='CONDITIONAL-CARRY-INDEPENDENT-AUDIT-20261003-V1:RESULT',
    event_type='IMPORTED_OPERATIONAL_RESULT',git_commit=actual['binding']['git_commit'],data_manifest_hash=hashes['reports/fast_research/BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json'],
    protocol_hash=actual['binding']['protocol_sha256'],feature_set='FULL_CONDITIONAL_ACCOUNT_LEDGER',labels='NONE',model_family='NONE',
    hyperparameters='FIXED_D029_NO_SEARCH',seed='NONE',thresholds='SAME_PREREGISTERED_RISK_AND_TOLERANCE',cost_assumptions=actual['binding']['rules'],
    all_folds='ONE_CONTINUOUS_FULL122D',success_failure=audit['status'],reason_for_next_experiment='SAME_CAPS_MATCHED_PAIR_TRIM_MECHANISM',
    result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
    artifact_path=names[2][0],artifact_sha256=sha(ROOT/names[2][0]),actual_exit=0,actual_task=receipts[2])
append_event(ROOT/'reports/experiment_registry.jsonl',event)
value=dict(status='PASS_ROOT_CONDITIONAL_CARRY_NEGATIVE_ACCOUNT_MATH_NOT_NATIVE_OR_LONG_TERM_APR',created_utc=datetime.now(UTC).isoformat(),
    root_task_id=os.environ['COIN_TASK_ID'],source_hashes=hashes,original_receipts=receipts,exact_used_source_archives=archives,
    output_bindings=outputs,output_data_retained_in_STATE_not_Git=True,source_arrays_QA_math_or_tests_replayed_by_root=False,
    metadata_failure_preserved=failed_metadata,failed_metadata_financial_execution=False,
    financial_summary=actual['summary'],capital_net_APR='NOT_EVALUABLE',candidate_status='NO_QUALIFIED_CANDIDATE',
    decision='PAUSE_FIXED_ALL_FLAT_RECIPE_PRESERVE_CONTROL_AND_CARRY_CAPABILITY',
    next_experiment='PREDECLARE_SAME_CAP_COST_MATCHED_PAIR_TRIM_CONTROL',ROOT_host_exit_requires_actual_closure_after_report_written=True)
with OUT.open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps(dict(status=value['status'],sha256=sha(OUT),source_files=len(hashes),root_task_id=value['root_task_id'])))
