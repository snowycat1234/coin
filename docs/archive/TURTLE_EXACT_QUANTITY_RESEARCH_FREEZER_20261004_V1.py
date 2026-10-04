"""Freeze same two fixed policies after an independently checked correctness repair."""
import ast,hashlib,json,os,subprocess
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert os.environ['COIN_TASK_ID'] and parent=='bbb2d8dd943c4830579f79e5aa01bc8799b7a904'
test='reports/fast_research/TURTLE_EXACT_QUANTITY_SYNTHETIC_20261004_V1.json'
r=json.loads((ROOT/test).read_bytes());assert r['test_exit_code']==0 and r['source_bytes_unchanged']
t=json.loads((STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')).read_bytes())
assert t['status']=='completed' and t['exit_code']==0
archive=ROOT/'docs/archive/TURTLE_EXACT_QUANTITY_RESEARCH_FREEZER_20261004_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
old=json.loads((ROOT/'protocols/TURTLE_NO_ADD_RESEARCH_20261004_V1.json').read_bytes())
paths=set(old['source_hashes'])-{'tests/test_turtle_no_add_direct.py','docs/archive/TURTLE_NO_ADD_FREEZER_SOURCE_20261004_V1.py'}
paths|={'tests/test_turtle_exact_candidate_quantity.py',str(archive.relative_to(ROOT)),
 'docs/archive/TURTLE_EXACT_QUANTITY_SYNTHETIC_FREEZER_20261004_V1.py',
 'docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py',
 'docs/archive/PERPETUAL_213_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'}
for p in paths:
    if p.endswith('.py'):ast.parse((ROOT/p).read_bytes())
spec=dict(old,parent_commit=parent,experiment_id='D061_TURTLE_CORRECTED_EXACT_QUANTITY_FIXED303D',
 source_hashes={p:sha(ROOT/p) for p in sorted(paths)},
 required_test=dict(path=test,sha256=sha(ROOT/test),required_status=r['status']),
 correctness_change='UNSCALED_CANDIDATE_DECIMAL_IDENTITY_NO_EPSILON',
 prior_default=dict(path='reports/fast_research/TURTLE_NO_ADD_PYRAMID4_303D_20261004_V1.json',
    sha256=sha(ROOT/'reports/fast_research/TURTLE_NO_ADD_PYRAMID4_303D_20261004_V1.json')),
 default_migration_gate='D060_TRACE_EQUIVALENCE_ALREADY_PASSED;KNOWN_SPURIOUS_REDUCTION_NOT_REPRODUCED',
 question='After correcting same-weight spurious reductions, does no proactive ADD improve fixed303D net economics?',
 created_utc=datetime.now(UTC).isoformat(),freeze_task_id=os.environ['COIN_TASK_ID'])
out=ROOT/'protocols/TURTLE_EXACT_QUANTITY_RESEARCH_20261004_V1.json'
with out.open('x') as f:json.dump(spec,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(protocol=str(out),sha256=sha(out),source_count=len(paths),market_arrays_read=False)),flush=True)
