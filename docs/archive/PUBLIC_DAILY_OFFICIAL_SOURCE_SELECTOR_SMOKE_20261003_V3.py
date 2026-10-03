"""D037 metadata-only V3 namespace/Path bridge and AST selectors; no rows."""
import argparse, hashlib, importlib.util, json, os, resource, time
from pathlib import Path
from quant import resources
from quant.paths import ROOT, STATE
parser=argparse.ArgumentParser()
parser.add_argument('--run-dir',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();run=args.run_dir.resolve();out=args.output.resolve()
if not run.is_relative_to(STATE) or run.exists() or not out.is_relative_to(ROOT/'reports/fast_research') or out.exists():
    raise ValueError('Exclusive metadata-only STATE/report')
run.mkdir();started=time.monotonic();source=ROOT/'scripts/investment/public_daily_official_source_v3.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=dict(status='FAIL_D037_V3_DAILY_SOURCE_AST_AND_PATH_BRIDGE_NO_NETWORK_NO_ROWS',
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(source),source_sha256=sha(source),
        helper_path=str(Path(__file__).resolve()),helper_sha256=sha(__file__)),resources_before=resources.status(),
    network_requests=0,archives_downloaded=0,data_rows_read=0,old_DB_writes=0,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
try:
    expected='dd058c092a4cee20b25e31650a1429dda78fdbf76e298cab3f45fba22ef81099'
    if sha(source)!=expected:raise ValueError('Exact V3 daily source changed')
    spec=importlib.util.spec_from_file_location('d037_daily_source_v3_selector',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for path,digest in module.PINS.items():
        if sha(ROOT/path)!=digest:raise ValueError('Original reusable selector source changed')
    download,parse,changes=module.private['adapted_functions']()
    if len(changes)!=6 or any(c['matches']!=1 for c in changes):raise ValueError('Six exact daily AST anchors')
    bridge=module.private['sha'];actual_file=module.private['__file__']
    if not isinstance(actual_file,str) or bridge(actual_file)!=bridge(Path(actual_file)) or bridge(actual_file)!=expected:
        raise ValueError('Actual __file__ string and Path equivalent SHA bridge')
    if module.main.__globals__ is not module.private or module.main.__globals__['sha'] is not bridge:
        raise ValueError('Unchanged main binds the corrected private Path bridge')
    binding=dict(source_path=str(Path(actual_file).resolve()),source_sha256=bridge(actual_file))
    if binding!=dict(source_path=str(source.resolve()),source_sha256=expected):raise ValueError('Main source binding field interface')
    if download.__globals__['LIMIT']!=65536 or parse.__globals__['MINUTE_US']!=86400000000:
        raise ValueError('Daily private scalar namespace')
    if module.original.original_data.MINUTE_US!=60000000 or module.original.original_source.LIMIT!=1000000000:
        raise ValueError('Original source and minute parser globals unchanged')
    report.update(status='PASS_D037_V3_DAILY_SOURCE_AST_AND_PATH_BRIDGE_NO_NETWORK_NO_ROWS',
        anchors=changes,str_Path_sha_equal=True,main_binding_types_checked=True,
        source_binding_fixture=binding,formal_main_executed=False,original_globals_unchanged=True,source_bytes_unchanged=sha(source)==expected)
except Exception as error:report.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_after=resources.status())
    with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=report['status'],path=str(out),sha256=sha(out))))
