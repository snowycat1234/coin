"""One module checkpoint: reuse registry/disk guards; never fit or replay."""
import hashlib, json, subprocess, time
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from quant import disk, resources
from scripts.research_v8.registry import FIELDS, append_event

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
def save(name, value):
    with (ROOT/name).open('x') as f:
        json.dump(value,f,ensure_ascii=False,indent=2,allow_nan=False); f.write('\n')
def git(*args): return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()

head=git('rev-parse','HEAD'); assert head=='5346a5c7b01ac2fdf85572086e8a061c6b865203'
primary='reports/SHORT_ROUTING_DIAGNOSIS_20261008.json'
r=json.loads((ROOT/primary).read_bytes())
assert r['status']=='COMPLETE_READ_ONLY_SHORT_ROUTING_DIAGNOSIS' and r['new_models_fit']==r['new_accounts']==0
assert sha(ROOT/primary)=='842840d974e43d13ab9f871d0d6939c00583046dc12235b1ec0e7e58b18e01de'
assert sha(ROOT/'scripts/research/diagnose_short_routing.py')==r['source_sha256']
assert sha(ROOT/'protocols/SHORT_ROUTING_DIAGNOSIS_20261008.json')==r['protocol_sha256']
assert sha(ROOT/'tests/test_short_routing_diagnosis.py')=='24009d71fa080e0d900d21d10ab79c5b4c00c20fa9e4021ad977fd01ce65514c'
from xml.etree import ElementTree as ET
suite=ET.parse(ROOT/'reports/SHORT_ROUTING_DIAGNOSIS_TESTS_20261008.xml').find('testsuite')
assert suite.attrib['tests']=='3' and suite.attrib['failures']==suite.attrib['errors']=='0'
event=dict.fromkeys(FIELDS)
event.update(experiment_id='SHORT_ROUTING_DIAGNOSIS_20261008',event_id='SHORT_ROUTING_DIAGNOSIS_20261008:COMPLETE',
 event_type='OPERATIONAL_RESEARCH_DECISION',git_commit=head,model_family='NONE_READ_ONLY',models_fit=0,new_accounts=0,
 protocol_hash=r['protocol_sha256'],all_folds='BTC_2022_2023_SEEN_DEVELOPMENT',
 success_failure='SHORT_NOT_SOLVED; FIXED_EW_NONSHORT_BOUND; HEDGE_GROSS_SHORT_LOSS',
 reason_for_next_experiment='Past-only bear-continuation versus rebound information; approved multi-asset coverage first; no eta/model grid',
 result_influenced_later_choice=True,artifact_path=primary,artifact_sha256=sha(ROOT/primary),locked_consumed=False)
# Preserve the exact committed prefix, including historical mixed line endings.
for name in ('docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl'):
    prior=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
    assert (ROOT/name).read_bytes().startswith(prior), 'Append-only history bytes changed: '+name
append_event(ROOT/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(phase='关闭模块：实际D盘扫描，总量未知',completed=None,total=None)),flush=True)
began=time.monotonic(); scan=dict(disk.check(),measured_utc=datetime.now(UTC).isoformat())
closed='reports/SHORT_ROUTING_CLOSED_20261008.json'; binding='reports/GITHUB_SHORT_ROUTING_SOURCE_BINDING_20261008.json'
paths=['scripts/research/diagnose_short_routing.py','protocols/SHORT_ROUTING_DIAGNOSIS_20261008.json',
 'tests/test_short_routing_diagnosis.py',primary,'reports/SHORT_ROUTING_DIAGNOSIS_20261008.md',
 'reports/SHORT_ROUTING_DIAGNOSIS_TESTS_20261008.xml','docs/archive/SHORT_ROUTING_CLOSE_SOURCE_20261008.py',
 'docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md','reports/experiment_registry.jsonl',
 'reports/SELECTOR_TRANSFER_COLLECTOR_PRESERVED_20261008.json','reports/SELECTOR_TRANSFER_COLLECTORS_RESTORED_20261008.json',closed,binding]
untracked=set(git('ls-files','--others','--exclude-standard','-z').split('\0'))-{''}
prior=sorted(untracked-set(paths))
legacy=json.loads((ROOT/'reports/GITHUB_SELECTOR_ML_COMPLETED_SOURCE_BINDING_20261006_V1.json').read_bytes())['prior_WIP_preserved']
assert set(legacy).issubset(prior), 'Preserve all prior unrelated untracked work'
save(closed,dict(status='COMPLETE_READ_ONLY_SERVER_MODULE_CHECKPOINT',parent_commit=head,
 scientific_execution='SERVER_8GB_SWAP0_GPU0_SCOPE',scientific_elapsed_seconds=r['elapsed_seconds'],
 scientific_process_RSS_bytes=r['peak_process_RSS_bytes'],shared_server_group_peak='NOT_MEASURED',
 scientific_source_sha256=r['source_sha256'],tests_passed=3,tests_artifact_sha256=sha(ROOT/'reports/SHORT_ROUTING_DIAGNOSIS_TESTS_20261008.xml'),
 disk_scan=scan,disk_scan_elapsed_seconds=time.monotonic()-began,local_resources=resources.status(),
 server_free_bytes_observed=24864100352,server_free_observed_utc='UNKNOWN_NOT_CAPTURED_WITH_SHELL_OBSERVATION',
 original_server_WIP_preserved=['tests/test_expert_aggregation_report.py'],
 new_models_fit=0,new_accounts=0,new_strategy_net_return='NOT_RUN',qualification='NONE_CASH',
 selected_bytes_before_receipts=sum((ROOT/p).stat().st_size for p in paths if (ROOT/p).is_file()),
 locked_body_read=False,collector_processes_restored=True,collector_new_data_progress='NOT_CONFIRMED_SAMPLING_FAILED'))
save(binding,dict(status='ACCEPTED_MODULE_SOURCE_BINDING',parent_commit=head,selected_module_paths=paths,
 source_hashes={p:sha(ROOT/p) for p in paths if p!=binding},prior_WIP_preserved=prior,locked_body_read=False))
p=STATE/'task-progress/last-disk.json'; tmp=p.with_suffix('.short-routing.tmp')
tmp.write_text(json.dumps(dict(ledger=scan,measured_at=datetime.fromisoformat(scan['measured_utc']).timestamp(),source=closed)));tmp.replace(p)
print(json.dumps(dict(status='COMPLETE_READ_ONLY_SERVER_MODULE_CHECKPOINT',disk_bytes=scan['total_bytes'],preserved_WIP=len(prior))),flush=True)
