"""Read-only reconciliation of actual synthetic V1 failure and V2 targeted recovery."""
import argparse, hashlib, json, os, resource, shlex, subprocess, sys, time
from datetime import UTC, datetime
from pathlib import Path
import xml.etree.ElementTree as ET
from quant import resources
ROOT=Path('/mnt/d/codex/coin'); STATE=Path('/home/xflops/coin-state')
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path): return json.loads(Path(path).read_text())
def write(path,value):
    with Path(path).open('x') as stream: json.dump(value,stream,indent=2,allow_nan=False)
p=argparse.ArgumentParser();p.add_argument('--run-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args();work=a.run_dir.resolve();out=a.output.resolve()
if not work.is_relative_to(STATE) or work.exists() or out.exists() or not out.is_relative_to(ROOT/'reports/fast_research'): raise ValueError('Exclusive STATE/report required')
if sys.prefix!=str(STATE/'v8-clean-env-20261002-v2'): raise ValueError('Accepted clean environment required')
paths=[ROOT/'reports/fast_research'/f'BYBIT_SPOT_FEE_ASSET_TINY_20261002_V{i}.json' for i in (1,2)]
expected=['494994ec5a5ad52216936b0ce4388b7dc0d30ca943a96214c548be98a2941607','933236cc26141df1f4b6cc9b763114baa45ce7cce4e474e12b7b49d909abd04c']
work.mkdir();binding=dict(git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),helper_source_sha256=sha(__file__),helper_source=str(Path(__file__).resolve()),
    parent_reports=[dict(path=str(path),sha256=sha(path),required_sha256=required) for path,required in zip(paths,expected)],
    environment_lock_sha256=sha(ROOT/'environments/v8/uv.lock'),sys_prefix=sys.prefix,exact_command=shlex.join([sys.executable,str(Path(__file__).resolve()),*sys.argv[1:]]),
    task_id=os.environ['COIN_TASK_ID'],data_scope='EXISTING_RECEIPTS_JUNIT_AND_SOURCE_ONLY_NO_MARKET_NO_TEST_RERUN',models_fit=0,GPU=0,seed='NOT_APPLICABLE')
write(work/'RUN_BINDING.json',binding);write(work/'START.json',dict(binding,status='PREBOUND_START',created_utc=datetime.now(UTC).isoformat()))
report=dict(status='FAIL_SYNTHETIC_RECEIPT_RECONCILIATION',binding=binding,run_dir=str(work),candidate_status='NO_QUALIFIED_CANDIDATE',market_inputs_read=False,new_tests_run=0,models_fit=0)
started=time.monotonic()
try:
    assert all(sha(path)==required for path,required in zip(paths,expected))
    old,new=[read(path) for path in paths]
    assert old['test_exit_code']==1 and new['test_exit_code']==0
    for key in ('original_function_ast_sha256','derived_AST_SHA256','derived_source_file_sha256','allowed_ast_changes','dependency_source_sha256','adapter_protocol_sha256'):
        assert old['derivation'][key]==new['derivation'][key], key
    assert len(new['derivation']['allowed_ast_changes'])==16 and all(x['matches']==1 for x in new['derivation']['allowed_ast_changes'])
    native_path='scripts/investment/bybit_spot_adapter.py'; test_path='tests/test_bybit_spot_adapter.py'
    before=(Path(old['run_dir'])/'source-snapshot'/native_path).read_text();after=(ROOT/native_path).read_text()
    assert before.split('def _smoke_main():')[0]==after.split('def _smoke_main():')[0]
    original_test=(Path(old['run_dir'])/'source-snapshot'/test_path).read_text();current_test=(ROOT/test_path).read_text()
    initial_line="    assert result.summary['gross_pnl_before_costs']==pytest.approx(shadowcash+sum(positions[s]*prices[s] for s in prices)-result.config.initial_cash)"
    new_line="    # Independent equivalent sums can cancel near zero at initial-cash precision.\n    assert result.summary['gross_pnl_before_costs']==pytest.approx(shadowcash+sum(positions[s]*prices[s] for s in prices)-result.config.initial_cash,\n        abs=16*np.spacing(result.config.initial_cash))"
    assert original_test.count(initial_line)==1 and original_test.replace(initial_line,new_line)==current_test
    assert all(sha(ROOT/path)==value for path,value in new['binding']['source_hashes'].items())
    cases=[];actual=[]
    for receipt in (old,new):
        junit=Path(receipt['run_dir'])/'junit.xml';assert sha(junit)==receipt['junit_sha256']
        parsed=ET.parse(junit).getroot();cases.append({case.attrib['name']:not any(item.tag in ('failure','error','skipped') for item in case) for case in parsed.iter('testcase')})
        taskpath=STATE/'task-progress'/('task-'+receipt['binding']['task_id']+'.json');task=read(taskpath)
        assert task['exit_code']==receipt['test_exit_code'] and task['status'] in ('failed','completed')
        actual.append(dict(task_id=task['id'],task_path=str(taskpath),task_sha256=sha(taskpath),status=task['status'],actual_exit_code=task['exit_code']))
    reused={name:dict(parent_report=str(paths[0]),passed=True) for name,passed in cases[0].items() if passed}
    failures={name for name,passed in cases[0].items() if not passed}
    assert len(cases[0])==5 and len(reused)==3 and len(cases[1])==2 and set(cases[1])==failures and all(cases[1].values())
    coverage={**reused,**{name:dict(parent_report=str(paths[1]),passed=True) for name in cases[1]}}
    assert len(coverage)==5
    report.update(status='PASS_FIVE_SYNTHETIC_CASES_COMPOSITE_NOT_SINGLE_FRESH_SUITE',coverage=coverage,actual_exits=actual,
        original_failure_retained=True,v1_passed_cases_reused=3,v2_failed_cases_recovered=2,fee_implementation_prefix_exact_unchanged=True,
        all_16_AST_change_records_exact_unchanged=True,derived_AST_SHA256=new['derivation']['derived_AST_SHA256'],derived_source_sha256=new['derivation']['derived_source_file_sha256'],
        only_test_change='SUMMARY_ZERO_NEAR_CANCELLATION_ABS_16_ULP_INITIAL_10000_USDT_2.9103830456733704e-11',
        quantity_fee_cash_nav_cap_and_dust_assertions_unchanged=True,current_source_hashes=new['binding']['source_hashes'])
except Exception as error:
    report.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    report.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources=resources.status())
    write(out,report);print(json.dumps(dict(status=report['status'],output=str(out),sha256=sha(out))))
