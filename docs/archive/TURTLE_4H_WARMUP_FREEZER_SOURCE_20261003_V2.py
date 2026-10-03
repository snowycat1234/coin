"""Freeze the four small official4h warmup files; compile without reading rows."""
import hashlib,json,os
from datetime import UTC,datetime
from pathlib import Path
from scripts.investment import perpetual_4h_warmup_source as source
ROOT,STATE=source.ROOT,source.STATE
ARCHIVE='docs/archive/TURTLE_4H_WARMUP_FREEZER_SOURCE_20261003_V2.py'
PROTOCOL='protocols/TURTLE_4H_WARMUP_SOURCE_20261003_V1.json'
OUT='reports/fast_research/TURTLE_4H_WARMUP_SOURCE_COMPILE_20261003_V1.json'
def sha(p):
    with Path(p).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2,allow_nan=False);f.write('\n')
assert os.environ.get('COIN_TASK_ID') and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
assert sha(ROOT/'state/dataset_lock.json')==source.LOCAL_GUARD['state/dataset_lock.json']
parent=json.loads((ROOT/'protocols/PERPETUAL_2H_WARMUP_SOURCE_20261003_V1.json').read_bytes())
names=set(source.PINS)|{'scripts/investment/perpetual_4h_warmup_source.py',
    'docs/archive/TURTLE_4H_WARMUP_SOURCE_20261003_V1.py',ARCHIVE}
hashes={name:sha(ROOT/name) for name in sorted(names)}
assert not ('state/dataset_lock.json' in hashes)
for p,h in source.PINS.items():assert hashes[p]==h
spec=dict(parent,contract_id=source.CONTRACT,source_start='2024-07-01',source_end_exclusive='2024-09-01',
    symbols=source.SYMBOLS,interval='4h',expected_archives=4,expected_rows_per_archive=186,
    expected_rows_per_symbol=372,expected_total_rows=744,budgets=source.BOUNDS,entries=source.entries(),
    frozen_sources=hashes,local_non_git_hash_guard=source.LOCAL_GUARD,
    run_dir=str(STATE/'d047-turtle-4h-warmup-source-20261003-v1'),
    output_path='reports/fast_research/TURTLE_4H_WARMUP_SOURCE_ACTUAL_20261003_V1.json',
    planned_status=source.STATUS,combined_capacity_reservation_bytes=20_000_000,
    created_utc=datetime.now(UTC).isoformat(),freezer_task_id=os.environ['COIN_TASK_ID'])
spec.pop('pre_execution_syntax_receipt',None)
source.validate(spec,'scripts/investment/perpetual_4h_warmup_source.py')
env=source.context();download,parser,convert,changes=env['adapted_functions']()
assert callable(download) and isinstance(parser,dict) and set(parser)=={'4h'} and callable(parser['4h']) and callable(convert)
write(ROOT/OUT,dict(status='COMPILED_D047_FOUR_4H_WARMUP_SOURCE_ANCHORS_NO_ROWS_OR_NETWORK',
    binding=dict(task_id=os.environ['COIN_TASK_ID'],source_sha256=sha(__file__)),
    market_arrays_read=False,network_requests=0,changes=changes))
spec['pre_execution_syntax_receipt']=dict(path=OUT,sha256=sha(ROOT/OUT))
write(ROOT/PROTOCOL,spec)
print(json.dumps(dict(status='FROZEN_D047_FOUR_4H_WARMUP_NO_ROWS_OR_NETWORK',protocol=PROTOCOL,sha256=sha(ROOT/PROTOCOL))))
