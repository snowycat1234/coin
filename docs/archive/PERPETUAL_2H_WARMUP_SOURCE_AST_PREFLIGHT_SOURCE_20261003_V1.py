"""D041 compiler/AST selectors only. No HTTP, CSV, Parquet or source acceptance."""
import ast, json, os, resource, shlex, sys, time
from datetime import UTC, datetime
from pathlib import Path
from quant import resources
from quant.paths import ROOT, STATE
from scripts.investment import perpetual_2h_warmup_source as module

run=STATE/'d041-2h-source-ast-preflight-20261003-v1'
out=ROOT/'reports/fast_research/PERPETUAL_2H_WARMUP_SOURCE_AST_PREFLIGHT_20261003_V1.json'
module.require(not run.exists() and not out.exists() and os.environ.get('COIN_TASK_ID'),'Exclusive real bounded AST task')
run.mkdir();started=time.monotonic();before=resources.status()
binding={'task_id':os.environ['COIN_TASK_ID'],'source_sha256':module.sha(module.__file__),
    'source_path':str(Path(module.__file__).resolve()),'helper_path':str(Path(__file__).resolve()),
    'helper_sha256':module.sha(__file__),'exact_command':shlex.join([sys.executable,*sys.argv]),'sys_prefix':sys.prefix}
module.write(run/'RUN_BINDING.json',binding)
result={'status':'FAIL_D041_SOURCE_AST_COMPILE_ONLY','binding':binding,'run_dir':str(run),
    'run_binding_sha256':module.sha(run/'RUN_BINDING.json'),'resources_before':before,
    'network_requests':0,'archive_bodies_downloaded':0,'market_rows_read':0,'source_function_calls':0,
    'source_acceptance_granted':False,'models_fit':0,'orders_sent':0,'GPU':0}
try:
    compile(ast.parse(Path(module.__file__).read_bytes()),str(module.__file__),'exec')
    for path,value in module.PINS.items():module.require(module.sha(ROOT/path)==value,'Frozen pin changed: '+path)
    download,parsers,conversion,changes=module.adapted_functions()
    module.require(callable(download) and callable(conversion) and set(parsers)=={'2h'} and len(changes)==4,
        'Exactly four private parser/calendar anchors and callable compiled definitions')
    module.require(module.sha(str(Path(module.__file__)))==module.sha(Path(module.__file__)), 'Path/string source SHA parity')
    result.update(status='PASS_D041_SOURCE_AST_COMPILE_ONLY_NO_NETWORK_OR_ROWS',AST_changes=changes,
        compiled_reused_functions=['download_archive','parse_csv','convert'],expected_source_archives=2,
        expected_source_rows_per_symbol=372,frozen_source_hashes=module.PINS)
except Exception as error:
    result.update(error_type=type(error).__name__,reason=str(error));raise
finally:
    result.update(created_utc=datetime.now(UTC).isoformat(),elapsed_seconds=time.monotonic()-started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,resources_after=resources.status())
    module.write(out,result)
print(json.dumps({'status':result['status'],'output':str(out),'sha256':module.sha(out)}))
