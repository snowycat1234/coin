"""Accept exact failure evidence and export used code; no market/test replay."""
from datetime import UTC, datetime
import hashlib
import json
import os
from pathlib import Path
from scripts.research_v8.registry import FIELDS, append_event

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
WORK=STATE/'test-bybit-funding-pilot-independent-audit-20261003-v1'
OUT=ROOT/'reports/fast_research/BYBIT_FUNDING_PILOT_ROOT_ACCEPTANCE_20261003_V1.json'
ARCHIVE='docs/archive/BYBIT_FUNDING_PILOT_ROOT_ACCEPTANCE_SOURCE_20261003_V1.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_bytes())
assert not OUT.exists() and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
hashes={ARCHIVE:sha(ROOT/ARCHIVE)}
names=[
 ('reports/fast_research/BYBIT_FUNDING_HISTORY_PILOT_ACTUAL_20261003_V1.json','eac907e172ac401dd05546645bf67c7dc724e3968afd62ad661cd885eb9d2765',1,'session:76274 / chunk:f1a912'),
 ('reports/fast_research/BYBIT_FUNDING_PILOT_INDEPENDENT_SYNTHETIC_20261003_V1.json','e76b7bb7955641822de892a2f458a39f224dbe04fef8f7131ed6c5f3d47c4f59',0,'chunk:0b765c'),
 ('reports/fast_research/BYBIT_FUNDING_PILOT_INDEPENDENT_FAILED_RESPONSE_AUDIT_20261003_V1.json','cb8c43f555d04196a1e713482c4fb0af953dbd8d3ffee885bd49272d39abf83f',0,'chunk:e09a3c')]
receipts=[]
def add(name,digest):
    assert not Path(name).is_absolute() and '..' not in Path(name).parts
    p=ROOT/name
    assert p.is_file() and not p.is_symlink() and p.stat().st_size<2000000 and sha(p)==digest,name
    assert name not in hashes or hashes[name]==digest
    hashes[name]=digest
for name,digest,exit_code,host in names:
    add(name,digest);v=load(ROOT/name)
    identity=v['binding']['task_id'];p=STATE/'task-progress'/('task-'+identity+'.json');task=load(p)
    assert task['id']==identity and task['exit_code']==exit_code and task['status']==('failed' if exit_code else 'completed')
    receipts.append(dict(path=name,sha256=digest,status=v['status'],actual_exit=exit_code,actual_host_result=host,
        actual_task_path=str(p),actual_task_sha256=sha(p),task=task))
pilot,synthetic,audit=[load(ROOT/name) for name,_,_,_ in names]
assert pilot['status']=='FAIL_BYBIT_NATIVE_FUNDING_HISTORY_PILOT_UNCONFIRMED' and pilot['actual_operation_exit_code']==1
assert audit['status']=='PASS_BYBIT_PILOT_FAILURE_EVIDENCE_STOP_AND_NO_ECONOMICS_SCOPE'
assert audit['pilot_report_sha256']==names[0][1] and audit['native_data_or_unit_gate']=='NOT_PASSED'
assert audit['observed_requests']==1 and not audit['ETH_requested'] and audit['samples_accepted']==0
assert audit['raw_response']['http_status']==403 and audit['raw_response']['bytes']==96
assert not audit['raw_response']['valid_JSON'] and audit['raw_response']['canonical_business_retCode'] is None
assert not pilot['funding_income_calculated'] and not pilot['locked_consumed'] and pilot['samples']==[]
protocol=pilot['binding']['protocol_path'];add(protocol,pilot['binding']['protocol_sha256']);spec=load(ROOT/protocol)
assert spec['frozen_sources']==pilot['binding']['source_hashes']==audit['verified_source_hashes']
for name,digest in spec['frozen_sources'].items():add(name,digest)
archives=[]
for source,target,digest in (
 ('audit.py','audit.py','d059687d102fc6c95bde5e89f728cd1d1775a703ee76fedc031a240946d6eb40'),
 ('synthetic.py','synthetic.py','61fda7b5275c8cc977f38df4722a715980193042176369382ee0dc089c3602df'),
 ('actual_failure_audit.py','actual_failure_audit.py','77c88c7c40977e1edfab41c25343703b69732cf93bb14f6682dfe7458d42ed90'),
 ('fixtures/valid_no_8h_assumption.json','fixtures/valid_no_8h_assumption.json','67c5e4185bb931d381120d488fb78e6354bbfe97eb1f07d79e1da7eeb5ce7cf0'),
 ('fixtures/bad_boolean_retcode.json','fixtures/bad_boolean_retcode.json','b396e95c8712991637fd7985467550f4be34fcddf2a24f5655285d801721d248'),
 ('fixtures/bad_duplicate_key.json','fixtures/bad_duplicate_key.json','8512f96b2a63ab2ef91c9aba846373dccae1737c8f43db4cacdb6c84690377c4'),
 ('fixtures/bad_wrongdate.json','fixtures/bad_wrongdate.json','28ce1ac992e101f675343646a5f730aa145ae8861747b7a1394da8d3c6b1ac85')):
    src=WORK/source;relative='docs/archive/BYBIT_FUNDING_PILOT_USED_SOURCES_20261003_V1/'+target;dst=ROOT/relative
    assert sha(src)==digest and not src.is_symlink()
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open('xb') as w:w.write(src.read_bytes())
    add(relative,digest);archives.append(dict(original=str(src),archive=relative,sha256=digest))
for relative,expected in (
 ('SYNTHETIC_BINDING.json','7080d587427dd82f14c1977b687b049ba2e160f75ae8e4f866bab03848a01a4b'),
 ('ACTUAL_BINDING.json','9f6de62255e313beab8a2f022ebfb4a7fb2bf32070072749660f3bacad1df238')):
    src=WORK/relative;assert sha(src)==expected
    target='docs/archive/BYBIT_FUNDING_PILOT_USED_SOURCES_20261003_V1/'+relative
    with (ROOT/target).open('xb') as w:w.write(src.read_bytes())
    add(target,expected)
for name in ('docs/archive/BYBIT_FUNDING_PUSH_VERIFICATION_SOURCE_20261003_V1.py',
             'reports/GITHUB_FUNDING_INCOME_SYNC_VERIFIED_20261003_V1.json'):add(name,sha(ROOT/name))
for receipt in receipts[1:]:
    event=dict.fromkeys(FIELDS)
    event.update(experiment_id='BYBIT-PILOT-'+receipt['path'].split('/')[-1].removesuffix('.json'),
        event_id='BYBIT-PILOT-'+receipt['path'].split('/')[-1]+':RESULT',event_type='IMPORTED_OPERATIONAL_RESULT',
        git_commit=pilot['binding']['git_commit'],data_manifest_hash=None,protocol_hash=sha(ROOT/protocol),
        feature_set='NONE_SOURCE_GUARDS_ONLY',labels='NONE',model_family='NONE',hyperparameters='NO_MODEL_NO_MARKET_REPLAY',
        seed='NOT_APPLICABLE',thresholds='FIXED_ONE_DAY_AND_FAILURE_STOP',cost_assumptions='NOT_EVALUATED',
        all_folds='BTC_ETH_FIXED_2025_08_01_ONLY',success_failure=receipt['status'],reason_for_next_experiment='D027_EXISTING_BASIS_RISK_SCALE',
        result_influenced_later_choice=True,post_completion_registration=True,preregistered_start_record_created=False,
        artifact_path=receipt['path'],artifact_sha256=receipt['sha256'],actual_exit=receipt['actual_exit'],
        actual_task_path=receipt['actual_task_path'],actual_task_sha256=receipt['actual_task_sha256'],actual_host_result=receipt['actual_host_result'])
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
value=dict(status='PASS_ROOT_ACCEPTED_TRUE_BYBIT_PILOT_FAILURE_EVIDENCE_NOT_NATIVE_DATA_OR_ECONOMICS',
    created_utc=datetime.now(UTC).isoformat(),root_task_id=os.environ['COIN_TASK_ID'],source_hashes=hashes,
    original_receipts=receipts,exact_used_source_archives=archives,pilot_actual_exit=1,
    native_input_or_unit_gate='NOT_PASSED',funding_income_calculated=False,NAV_or_APR_computed=False,
    candidate_status='NO_QUALIFIED_CANDIDATE',old_QA_green_tests_or_economics_repeated=False,
    raw_body_not_exported_to_Git=True,source_hashes_contain_STATE_paths=False,
    ROOT_host_exit_requires_actual_closure_after_report_written=True)
with OUT.open('x') as w:json.dump(value,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps({'status':value['status'],'sha256':sha(OUT),'frozen_files':len(hashes),'root_task_id':value['root_task_id']}))
