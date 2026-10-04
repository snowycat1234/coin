"""Preserve actual failed source, freeze strict parser and bounded byte reuse."""
import ast,hashlib,json,os,subprocess
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
assert os.environ['COIN_TASK_ID']
pp=ROOT/'protocols/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V1.json';old=read(pp)
ap=ROOT/'reports/fast_research/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V1.json';a=read(ap)
assert a['status']=='FAIL_D062_SOURCE_STAGE' and a['actual_exit_code']==1 and a['source_bytes_unchanged']
task=read(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
assert task['status']=='failed' and task['exit_code']==1 and task['ended_at']
assert a['completed_source_files']==48 and len(a['completed_sources'])==48
assert a['binding']['protocol_sha256']==sha(pp)
changes={'src/quant/data.py','scripts/investment/multi_asset_data.py'}
pins={}
for n,h in old['source_hashes'].items():
    current=sha(ROOT/n);assert n in changes or current==h,n;pins[n]=current
archive='docs/archive/MULTI_ASSET_SPRING_RECOVERY_METADATA_SOURCE_20261004_V1.py'
assert sha(ROOT/archive)==sha(Path(__file__))
pins[archive]=sha(ROOT/archive);pins[ap.relative_to(ROOT).as_posix()]=sha(ap)
pins[pp.relative_to(ROOT).as_posix()]=sha(pp)
for name in ('src/quant/data.py','scripts/investment/multi_asset_data.py',
             'scripts/investment/multi_asset_source_acceptance.py','tests/test_trade_parser_decimal_tail.py'):
    ast.parse((ROOT/name).read_bytes())
job=Path(a['run_dir'])/'klines-SOLUSDT-1m-2025-04'
zip_path=job/'SOLUSDT-1m-2025-04.zip';check=job/'SOLUSDT-1m-2025-04.zip.CHECKSUM'
assert not (job/'receipt.json').exists() and not (job/'source.parquet').exists()
assert zip_path.is_file() and check.is_file() and check.read_text().split()[0]==sha(zip_path)
new=dict(old);new.update(experiment_id='D062-FIXED-POOL-SPRING-SOURCE-20261004-V2',
    run_dir=str(STATE/'d062-multiasset-spring-source-20261004-v2'),
    output_path='reports/fast_research/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V2.json',
    source_hashes=pins,partial_source_reuse=dict(path=ap.relative_to(ROOT).as_posix(),sha256=sha(ap),required_status=a['status']),
    partial_source_reuse_source_sha256=a['binding']['source_sha256'],
    partial_source_reuse_protocol_sha256=sha(pp),
    saved_archive_reuse={"https://data.binance.vision/data/futures/um/monthly/klines/SOLUSDT/1m/SOLUSDT-1m-2025-04.zip":
        dict(zip_path=str(zip_path),zip_sha256=sha(zip_path),checksum_path=str(check),checksum_sha256=sha(check))},
    recovery_scope='36 completed pending-first-QA rows reused;12 accepted controls;1 retained official ZIP reparse;59 remaining downloads;no old acceptance promoted',
    created_utc=datetime.now(UTC).isoformat())
write(ROOT/'protocols/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V2.json',new)
test=read(ROOT/'protocols/MULTI_ASSET_SPRING_CALENDAR_SYNTHETIC_20261004_V1.json')
test['frozen_sources']={n:sha(ROOT/n) for n in test['frozen_sources'] if not n.startswith('tests/')}
n='tests/test_trade_parser_decimal_tail.py';test['frozen_sources'][n]=sha(ROOT/n)
test['frozen_sources'][archive]=sha(ROOT/archive)
test.update(tests=[n],test_scope='ONE_NEW_OFFICIAL_NUMERIC_PREFIX_INFERENCE_COUNTEREXAMPLE',
    calculation_rules=dict(all_price_volume_fields='Float64 at CSV read',timestamps_trade_count='strict Int64',
        no_ignore_errors=True,no_null_fill=True,independent_reference='csv.reader + Decimal all1440volume'),
    freeze_task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat())
write(ROOT/'protocols/MULTI_ASSET_DECIMAL_TAIL_SYNTHETIC_20261004_V1.json',test)
write(ROOT/'reports/fast_research/MULTI_ASSET_SPRING_RECOVERY_METADATA_20261004_V1.json',dict(
    status='READY_TRUE_FAILED_STAGE_BYTE_REUSE_AND_STRICT_NUMERIC_FIX_NOT_QA_OR_ECONOMICS',
    task_id=os.environ['COIN_TASK_ID'],failure_report_sha256=sha(ap),failure_task=task,
    source_hashes=pins,old_QA_repeated=False,accounts=0,models=0,
    protocol_sha256=sha(ROOT/'protocols/MULTI_ASSET_SPRING_MARKET_SOURCE_20261004_V2.json')))
print(json.dumps(dict(status='READY_RECOVERY_AND_ONE_NEW_COUNTEREXAMPLE',prior_completed=48,new_downloads=59)),flush=True)
