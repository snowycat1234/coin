"""One metadata-only AST selector smoke: no network, archive or data rows."""
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
run.mkdir();started=time.monotonic();source=ROOT/'scripts/investment/public_daily_official_source_v2.py'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
report=dict(status='FAIL_D037_DAILY_SOURCE_AST_SELECTORS_NO_NETWORK_NO_ROWS',
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_path=str(source),source_sha256=sha(source),
        helper_path=str(Path(__file__).resolve()),helper_sha256=sha(__file__)),
    resources_before=resources.status(),network_requests=0,archives_downloaded=0,data_rows_read=0,
    old_DB_writes=0,models_fit=0,orders_sent=0,GPU=0,locked_consumed=False)
try:
    expected='079bc2ec5cf635afdc9b277aa3dbbc8f2cdaad520537a04b8275d16e49bfa83d'
    if sha(source)!=expected:raise ValueError('Exact prepared daily source changed')
    spec=importlib.util.spec_from_file_location('d037_daily_source_selector',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    for path,digest in module.PINS.items():
        if sha(ROOT/path)!=digest:raise ValueError('Original reused selector source changed')
    download,parse,changes=module.adapted_functions()
    if len(changes)!=6 or any(c['matches']!=1 for c in changes):raise ValueError('Six unique exact adapted AST anchors')
    if download.__globals__['LIMIT']!=65_536 or parse.__globals__['MINUTE_US']!=86_400_000_000:
        raise ValueError('Private daily globals')
    if module.original_data.MINUTE_US!=60_000_000 or module.original_source.LIMIT!=1_000_000_000:
        raise ValueError('Shared original globals must stay unchanged')
    report.update(status='PASS_D037_PRIVATE_DAILY_DOWNLOAD_PARSE_AST_SELECTORS_NO_NETWORK_NO_ROWS',
        anchors=changes,private_function_names=[download.__name__,parse.__name__],
        original_minute_globals_unchanged=True,selected_source_files=module.PINS,source_bytes_unchanged=sha(source)==expected)
except Exception as error:
    report.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    report.update(elapsed_seconds=time.monotonic()-started,peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        resources_after=resources.status())
    with out.open('x') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
    print(json.dumps(dict(status=report['status'],path=str(out),sha256=sha(out))))
