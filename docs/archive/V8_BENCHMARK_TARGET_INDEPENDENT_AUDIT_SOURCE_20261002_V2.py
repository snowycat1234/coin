"""Independent target audit with local binding only; no shared registry append."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import resource
import shlex
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from datetime import UTC, datetime

ROOT=Path('/mnt/d/codex/coin')
STATE=Path('/home/xflops/coin-state')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

p=argparse.ArgumentParser()
p.add_argument('--run-dir',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
args=p.parse_args()
run,output=args.run_dir.resolve(),args.output.resolve()
assert run.is_relative_to(STATE) and not run.exists()
assert output.is_relative_to(ROOT/'reports/fast_research') and not output.exists()
assert Path(sys.prefix).resolve()==STATE/'v8-clean-env-20261002-v2'
assert not any('research-env-v6' in name or '/coin/.venv/' in name for name in sys.path)
assert os.environ.get('COIN_TASK_ID')
probe=ROOT/'.cache/v8_benchmark_target_independent_probes_v1.py'
paths=[ROOT/'scripts/research_v8/benchmark_targets.py',ROOT/'scripts/research_v8/benchmark_targets_v2.py',
       ROOT/'tests/test_v8_benchmark_targets.py',ROOT/'tests/test_v8_benchmark_targets_v2.py',
       ROOT/'protocols/BENCHMARK_CONTRACT_V1.json',ROOT/'protocols/EXECUTION_COST_SCENARIOS_V8.json',
       ROOT/'environments/v8/uv.lock',Path(__file__),probe]
before={str(path.relative_to(ROOT)):sha(path) for path in paths}
assert before['scripts/research_v8/benchmark_targets.py']=='cb3158116494c41b6649f80dc4013b3c1ff9e495773b3ae298d9d5b6e9d46652'
assert before['scripts/research_v8/benchmark_targets_v2.py']=='72235137633847101af57e658f8a50ea50494e1a63de663784754d72fef81a82'
old=[]
registry_lines=(ROOT/'reports/experiment_registry.jsonl').read_bytes().splitlines()
for version in (1,2):
    receipt_path=ROOT/f'reports/fast_research/V8_BENCHMARK_TARGETS_SYNTHETIC_20261002_V{version}.json'
    receipt=json.loads(receipt_path.read_text())
    binding=receipt['binding']
    folder=STATE/f'v8-benchmark-targets-synthetic-20261002-v{version}'
    local_binding=folder/'RUN_BINDING.json'
    assert sha(local_binding)==receipt['run_binding_sha256']
    assert json.loads(local_binding.read_text())==binding
    assert sha(Path(receipt['junit_path']))==receipt['junit_sha256']
    assert receipt['actual_test_exit_code']==0 and receipt['source_bytes_unchanged']
    frozen=[]
    for name,digest in binding['dirty_source_hashes'].items():
        actual=sha(ROOT/name)
        snapshot=folder/'source-snapshot'/name
        assert actual==sha(snapshot)==digest
        frozen.append({'path':name,'sha256':digest,'frozen_snapshot_sha256':sha(snapshot)})
    identifier=binding['experiment_id']
    needle=('"experiment_id":"'+identifier+'"').encode()
    events=[json.loads(line) for line in registry_lines if needle in line]
    start=next(value for value in events if value['event_id']==identifier+':start')
    result=next(value for value in events if value['event_id']==identifier+':result')
    assert start['source_hashes']==binding['dirty_source_hashes']
    assert start['run_binding_sha256']==receipt['run_binding_sha256']
    assert result['result_sha256']==sha(receipt_path) and result['success_failure']==receipt['status']
    assert start['exact_command']==binding['exact_test_command']
    suites=ET.parse(receipt['junit_path']).getroot().findall('.//testsuite')
    assert suites and all(int(suite.get('failures','0'))==int(suite.get('errors','0'))==0 for suite in suites)
    props={node.get('name'):node.get('value') for node in ET.parse(receipt['junit_path']).getroot().findall('.//property')}
    if version==2:
        assert props['run_binding_sha256']==receipt['run_binding_sha256']
        assert props['environment_lock_sha256']==binding['environment_lock_sha256']
        assert props['pre_execution_adapter_sha256']==binding['dirty_source_hashes']['scripts/research_v8/benchmark_targets_v2.py']
        assert props['pre_execution_test_sha256']==binding['dirty_source_hashes']['tests/test_v8_benchmark_targets_v2.py']
    task_path=STATE/'task-progress'/f'task-{binding["task_id"]}.json'
    task=json.loads(task_path.read_text())
    assert task['status']=='completed' and task['exit_code']==0
    old.append({'version':version,'receipt_path':str(receipt_path.relative_to(ROOT)),
        'receipt_sha256':sha(receipt_path),'run_binding_sha256':sha(local_binding),
        'junit_sha256':receipt['junit_sha256'],'junit_tests':sum(int(suite.get('tests','0')) for suite in suites),
        'actual_command':binding['exact_test_command'],'frozen_sources':frozen,
        'registry_start_sha256':start['record_sha256'],'registry_result_sha256':result['record_sha256'],
        'actual_task_id':task['id'],'actual_task_exit_code':task['exit_code']})
run.mkdir()
test_copy=run/'test_independent_targets.py'
shutil.copyfile(probe,test_copy)
argv=[sys.executable,'-m','pytest',str(test_copy),'-q','-s',f'--basetemp={run/"pytest"}',
      '-o',f'cache_dir={run/"pytest-cache"}',f'--junitxml={run/"junit.xml"}']
binding={'created_utc':datetime.now(UTC).isoformat(),'task_id':os.environ['COIN_TASK_ID'],
         'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
         'python_executable':sys.executable,'sys_prefix':sys.prefix,'source_hashes':before,
         'environment_lock_sha256':before['environments/v8/uv.lock'],
         'exact_test_command':shlex.join(argv),'test_file_sha256':sha(test_copy),'prior_frozen_evidence':old,
         'data_scope':'INVENTED_MINUTE_PRICES_DAILY_RETURNS_AND_FROZEN_PREDICTIONS_ONLY',
         'previous_failed_audit':{'path':'reports/fast_research/V8_BENCHMARK_TARGET_INDEPENDENT_AUDIT_20261002_V1.json','sha256':'3514c1cc21f54caa391ffa35577d0b0066f5e87c5239b17645a6d6204867ba0a','failure_scope':'PYTEST_CAPTURE_BEFORE_TEST_EXECUTION'},'pytest_capture_disabled':True,'child_tmpdir':str(run/'tmp'),'shared_registry_append':False,'market_model_fits':0,'market_rows_read':False,'seed':'DETERMINISTIC_NO_RANDOMNESS'}
with (run/'RUN_BINDING.json').open('x') as stream:json.dump(binding,stream,indent=2,allow_nan=False)
started=time.monotonic()
(run/'tmp').mkdir()
child_env={**os.environ,'TMPDIR':str(run/'tmp')}
completed=subprocess.run(argv,cwd=ROOT,env=child_env)
unchanged=before=={str(path.relative_to(ROOT)):sha(path) for path in paths}
receipt={'status':'PASS_INDEPENDENT_TARGET_ADAPTER_ONLY' if completed.returncode==0 and unchanged else 'FAIL_INDEPENDENT_TARGET_ADAPTER',
         'created_utc':datetime.now(UTC).isoformat(),'binding':binding,'run_binding_sha256':sha(run/'RUN_BINDING.json'),
         'actual_test_exit_code':completed.returncode,'source_bytes_unchanged':unchanged,
         'junit_path':str(run/'junit.xml'),'junit_sha256':sha(run/'junit.xml') if (run/'junit.xml').exists() else None,
         'elapsed_seconds':time.monotonic()-started,
         'peak_child_rss_bytes':resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024,
         'target_adapter_scope_only':True,'economic_acceptance':'NOT_EVALUATED','costs_paid':False,
         'complete_benchmark_suite_evaluable':False,'P1_gate':'NOT_READY','qualification':'NO_QUALIFIED_CANDIDATE',
         'market_rows_read':False,'market_model_outcomes_read':False,'market_models_fit':0,
         'locked_consumed':False,'orders_sent':0,'shared_registry_appended':False,
         'limitations':['Synthetic provided forecast receipt exercises target conversion only; it is not a production FrozenPredictor qualification.',
                        'Intent weights and causal risk downscaling are checked; fills, fees, NAV, cash accounting and realized exposure are not evaluated.',
                        'Missing carry, unfrozen XGB and explicitly partial ensemble remain economically NOT_EVALUABLE.']}
with output.open('x') as stream:json.dump(receipt,stream,indent=2,allow_nan=False);stream.write('\n')
print(json.dumps({'status':receipt['status'],'actual_test_exit_code':completed.returncode,
                  'elapsed_seconds':receipt['elapsed_seconds'],'receipt_sha256':sha(output)}),flush=True)
raise SystemExit(0 if receipt['status'].startswith('PASS_') else 1)
