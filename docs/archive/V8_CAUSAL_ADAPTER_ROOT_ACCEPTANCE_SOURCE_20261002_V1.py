"""Bind existing actual adapter/audit outputs; no rerun, market read or fit."""
import hashlib, json, subprocess, sys, xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
sources={}; proofs={}; archives=[]; actual=[]

def bind(mapping):
    for rel,h in mapping.items():
        assert not rel.startswith('.cache/'),rel
        assert sha(ROOT/rel)==h,rel
        assert rel not in sources or sources[rel]==h,rel
        sources[rel]=h

def read(name):
    p=ROOT/'reports/fast_research'/name; o=json.loads(p.read_text())
    proofs[str(p.relative_to(ROOT))]=sha(p)
    return o

def copy_exact(original, rel, expected=None):
    original=Path(original); digest=sha(original)
    if expected is not None: assert digest==expected,str(original)
    dest=ROOT/rel; value=original.read_bytes(); assert len(value)<4_000_000
    if dest.exists(): assert dest.read_bytes()==value,rel
    else:
        with dest.open('xb') as f:f.write(value)
    proofs[rel]=digest
    archives.append(dict(original=str(original),archive=rel,sha256=digest,bytes=len(value)))
    return digest

def completed(task_id):
    p=STATE/'task-progress'/('task-'+task_id+'.json'); o=json.loads(p.read_text())
    assert o['id']==task_id and o['status']=='completed' and o['exit_code']==0,task_id
    actual.append(o)
    return o

def unit(name, accepted, tag, source_field):
    o=read(name); assert o['status']==accepted
    b=o['binding'];bind(b[source_field])
    assert o['actual_test_exit_code']==0 and o['source_bytes_unchanged']
    j=Path(o['junit_path']);assert sha(j)==o['junit_sha256']
    suite=ET.parse(j).getroot()
    assert sum(int(x.attrib.get('failures',0)) for x in suite.iter('testsuite'))==0
    assert sum(int(x.attrib.get('errors',0)) for x in suite.iter('testsuite'))==0
    rb=j.parent/'RUN_BINDING.json';assert sha(rb)==o['run_binding_sha256']
    copy_exact(j,'reports/fast_research/V8_ACCEPTED_'+tag+'_ACTUAL_JUNIT_20261002_V1.xml',o['junit_sha256'])
    copy_exact(rb,'reports/fast_research/V8_ACCEPTED_'+tag+'_RUN_BINDING_20261002_V1.json',o['run_binding_sha256'])
    completed(b['task_id'])
    return o

label=unit('V8_LABEL_V5_SYNTHETIC_ACCEPTANCE_20261002_V1.json',
           'PASS_SYNTHETIC_LABEL_V5_MISSING_POLICY','LABEL_V5','source_hashes')
bench=unit('V8_BENCHMARK_TARGETS_SYNTHETIC_20261002_V2.json',
           'PASS_SYNTHETIC_CAUSAL_BENCHMARK_TARGET_V2_ADAPTER','BENCHMARK_V2','dirty_source_hashes')
feature=read('V8_FIXED_FEATURE_CHECK_RECEIPT_20261002_V4.json')
assert feature['status']=='PASS_FIXED_FEATURE_SYNTHETIC_CHECKS_PENDING_INDEPENDENT_AUDIT'
assert feature['actual_unified_exit_code']==0
bind(feature['source_hashes']);completed(feature['actual_task']['id'])
assert sha(ROOT/feature['junit_path'])==feature['junit_sha256']
assert feature['junit_counts']==dict(tests=16,errors=0,failures=0,skipped=0)
proofs[feature['junit_path']]=feature['junit_sha256']

for name,status in (
 ('V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5_R2.json','PASS_CONTRACT_IMPLEMENTATION'),
 ('V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V3.json','PASS_FEATURE_CONTRACT_IMPLEMENTATION')):
    o=read(name);assert o['status']==status and o['execution']['exit_code']==0
    assert not o['acceptance_blocker_ids'];bind(o['verified_source_hashes'])

archiveproof=read('V8_BENCHMARK_TARGET_AUDIT_SOURCE_ARCHIVE_20261002_V1.json')
mapping={a['source']:a['archive'] for a in archiveproof['archives']}
for a in archiveproof['archives']:
    assert sha(ROOT/a['source'])==a['sha256'] and sha(ROOT/a['archive'])==a['sha256']
    sources[a['archive']]=a['sha256']
ba=read('V8_BENCHMARK_TARGET_INDEPENDENT_AUDIT_20261002_V2.json')
assert ba['status']=='PASS_INDEPENDENT_TARGET_ADAPTER_ONLY' and ba['actual_test_exit_code']==0
for rel,h in ba['binding']['source_hashes'].items():
    if rel.startswith('.cache/'):
        assert rel in mapping and sha(ROOT/mapping[rel])==h
    else:bind({rel:h})
completed(ba['binding']['task_id'])
j=Path(ba['junit_path']);assert sha(j)==ba['junit_sha256']
copy_exact(j,'reports/fast_research/V8_ACCEPTED_BENCHMARK_AUDIT_ACTUAL_JUNIT_20261002_V1.xml',ba['junit_sha256'])
copy_exact(j.parent/'RUN_BINDING.json','reports/fast_research/V8_ACCEPTED_BENCHMARK_AUDIT_RUN_BINDING_20261002_V1.json',ba['run_binding_sha256'])

# Preserve exact independent probes and their invented outputs, including failures.
audit_names=['V8_LABEL_ADVERSARIAL_AUDIT_20261002_V3.json',
 'V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5.json','V8_LABEL_ADVERSARIAL_AUDIT_20261002_V5_R2.json',
 'V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V1.json',
 'V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V2.json',
 'V8_FIXED_FEATURE_ADVERSARIAL_AUDIT_20261002_V3.json']
for name in audit_names:
    o=read(name); p=o['independent_probe'];tag=name.removesuffix('.json')
    copy_exact(p['script'],'docs/archive/'+tag+'_EXACT_PROBE.py',p['script_sha256'])
    copy_exact(p['output'],'reports/fast_research/'+tag+'_EXACT_PROBE_OUTPUT.json',p['output_sha256'])

prior_names=['V8_LABEL_V4_SYNTHETIC_ACCEPTANCE_20261002_V1.json',
 'V8_LABEL_V5_AUDIT_EXECUTION_RECONCILIATION_20261002_V1.json',
 'V8_BENCHMARK_TARGETS_SYNTHETIC_20261002_V1.json',
 'V8_BENCHMARK_TARGET_INDEPENDENT_AUDIT_20261002_V1.json',
 'V8_FIXED_FEATURE_RESULT_REGISTRATION_FAILURE_20261002_V1.json',
 'V8_FIXED_FEATURE_THROUGHPUT_20261002_V1.json',
 'V8_CLEAN_CI_EXECUTION_RECEIPT_20261002_V2.json','V8_CLEAN_CI_START_20261002_V2.json']
for name in prior_names:read(name)
for v in (1,2,3,4):
    for prefix in ('V8_FIXED_FEATURE_START','V8_FIXED_FEATURE_CHECK_RECEIPT'):
        read(f'{prefix}_20261002_V{v}.json')
    p=ROOT/'reports/fast_research'/f'V8_FIXED_FEATURE_TESTS_20261002_V{v}.xml'
    proofs[str(p.relative_to(ROOT))]=sha(p)
for original in (
 'v8_feature_test_start_20261002_v1.py','v8_feature_v2_start_20261002_v1.py',
 'v8_feature_v3_start_20261002_v1.py','v8_feature_v3_result_registration_recovery_20261002_v2.py',
 'v8_feature_v4_start_20261002_v1.py','v8_feature_v4_result_20261002_v1.py'):
    copy_exact(ROOT/'.cache'/original,'docs/archive/'+original.upper())
throughput=read('V8_FIXED_FEATURE_THROUGHPUT_20261002_V1.json')
p='docs/archive/V8_FIXED_FEATURE_THROUGHPUT_SOURCE_20261002_V1.py'
bind({p:throughput['source_archive_sha256']})
p=ROOT/'docs/archive/V8_FIXED_FEATURE_RESULT_FAILED_SOURCE_20261002_V1.py'
proofs[str(p.relative_to(ROOT))]=sha(p)
for name in ('V8_LABEL_V4_SYNTHETIC_ACCEPTANCE_20261002_V1.json',
             'V8_BENCHMARK_TARGETS_SYNTHETIC_20261002_V1.json'):
    o=read(name);tag=name.removesuffix('.json');j=Path(o['junit_path'])
    copy_exact(j,'reports/fast_research/'+tag+'_EXACT_JUNIT.xml',o['junit_sha256'])
    copy_exact(j.parent/'RUN_BINDING.json','reports/fast_research/'+tag+'_EXACT_RUN_BINDING.json',o['run_binding_sha256'])
archive=ROOT/'docs/archive/V8_CAUSAL_ADAPTER_ROOT_ACCEPTANCE_SOURCE_20261002_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
sources[str(archive.relative_to(ROOT))]=sha(archive)
receipt=dict(status='ROOT_PASS_CAUSAL_LABEL_V5_FIXED_478_FEATURE_V4_BENCHMARK_TARGET_V2_ONLY',
 created_utc=datetime.now(UTC).isoformat(),git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
 data_hash=label['binding']['synthetic_recipe_sha256'],data_scope='BOUND_SYNTHETIC_AND_INDEPENDENT_ADAPTER_OUTPUTS_ONLY',
 protocol_hash=label['binding']['protocol_sha256'],environment_hash=sha(ROOT/'environments/v8/uv.lock'),seed=20261002,
 exact_command='bash scripts/bounded.sh /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python .cache/v8_causal_adapter_root_acceptance_20261002_v1.py',
 source_hashes=sources,verified_prior_files=proofs,exact_archives=archives,verified_actual_tasks=actual,
 accepted_scopes=['Nonoverlap labels, timestamp/maturity/locked export/split, missing-row preservation',
 'Frozen478 past-only features with causal primitive/empty-bar guards',
 'Benchmark fixed long-flat target intent adapter only'],
 candidate='NONE',candidate_status='NO_QUALIFIED_CANDIDATE',P1_gate='NOT_READY',classification='CORRECTNESS_ONLY_NOT_ALPHA_QUALIFICATION',
 market_models_fit=0,locked_consumed=False,orders_sent=0,GPU_hours=0,
 limitations=['No full ten-model caller routing, shared market scaler/calendar or economic replay acceptance.',
 'No paid fees, executable ask/bid/size/latency fills, maker, carry or complete benchmark qualification.',
 'P7 fee/impossible-fill mutations and P1 economic/statistical gate remain incomplete.',
 'All prior failures remain preserved; synthetic acceptance is not predictive/economic evidence.'])
out=ROOT/'reports/fast_research/V8_CAUSAL_ADAPTER_ROOT_MODULE_ACCEPTANCE_20261002_V1.json'
with out.open('x') as f:json.dump(receipt,f,indent=2);f.write('\n')
print(json.dumps(dict(status=receipt['status'],source_files=len(sources),proof_files=len(proofs),actual_tasks=len(actual),receipt_sha256=sha(out))))
