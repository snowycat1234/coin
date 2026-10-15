"""Run only the two inspected standalone saved-JSON validation entrypoints."""
from pathlib import Path
import contextlib, hashlib, importlib, io, json, os, resource, runpy, sys, time, unittest

OUT=Path(__file__).resolve().parent
NAME='traditional_D_partial2021_nine_compact_saved_results_public_recovery_20261015_v1'
ROOT=OUT/'fresh_extraction'/NAME
TMP=OUT/'temporary_test_files';TMP.mkdir(exist_ok=False)
os.environ['TMPDIR']=str(TMP)
os.environ['PYTHONDONTWRITEBYTECODE']='1'
sys.dont_write_bytecode=True
assert os.sched_getaffinity(0)=={7}
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    assert os.environ.get(name)=='1'
sys.path.insert(0,str(ROOT))
start=time.monotonic();cpu=time.process_time()
with (OUT/'STANDALONE_VERIFY.log').open('w') as f,contextlib.redirect_stdout(f),contextlib.redirect_stderr(f):
    old=sys.argv;sys.argv=['verify_packet.py','--root',str(ROOT)]
    try:runpy.run_path(str(ROOT/'verify_packet.py'),run_name='__main__')
    finally:sys.argv=old
module=importlib.import_module('test_packet')
with (OUT/'SUPPLIED_23_TESTS.log').open('w') as f:
    result=unittest.TextTestRunner(stream=f,verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(module))
assert result.testsRun==23 and not result.errors and not result.failures and not result.skipped
assert os.sched_getaffinity(0)=={7}
for prefix in ('partial_entry','partial_d','run_partial','perpetual_account','native_runtime','frozen_grid','forecast_monitor'):
    assert not any(prefix in m for m in sys.modules)
receipt=dict(status='PASS',entrypoints=['verify_packet.py','test_packet.py'],tests_run=result.testsRun,tests_passed=result.testsRun,failures=0,errors=0,skipped=0,
    CPU_affinity=sorted(os.sched_getaffinity(0)),numerical_threads=1,wall_seconds=time.monotonic()-start,CPU_seconds=time.process_time()-cpu,maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    accounts_constructed=0,financial_clocks_advanced=0,financial_children_launched=0,provider_iterations=0,source_downloads=0,raw_market_target_MINUTE_arrays_loaded=0,publication_performed=False,
    original_review_scripts_or_builder_executed=False,
    logs={p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in (OUT/'STANDALONE_VERIFY.log',OUT/'SUPPLIED_23_TESTS.log')})
(OUT/'FRESH_SUPPLIED_VALIDATION_RECEIPT.json').write_text(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
print(json.dumps(receipt,sort_keys=True))
