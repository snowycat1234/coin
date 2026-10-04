"""Use the existing source_archives interface for the output-only checker correction."""
import hashlib, json, os
from pathlib import Path
from datetime import UTC, datetime
from quant.paths import ROOT, STATE
STEM='DONCHIAN_REENTRY10_20261005_V3'
CHECKER='scripts/investment/multi_asset_financial_audit.py'
OLD='docs/archive/DONCHIAN_REENTRY10_PRE_COMPACT_FINANCIAL_SOURCE_20261005_V1.py'
def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f: json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
assert os.environ['COIN_TASK_ID']
p=read(ROOT/'protocols'/(STEM+'.json'))
for name,digest in p['source_hashes'].items(): assert sha(ROOT/(OLD if name==CHECKER else name))==digest,name
failed=read(STATE/'task-progress/task-0d9095813e634f28bc9e31bc8a6ffa9c.json')
assert failed['status']=='failed' and failed['exit_code']==1 and failed['ended_at']
prior=ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING_V4.json');plan=read(prior)
assert plan['checker_sha256']==sha(ROOT/CHECKER)
save(ROOT/'reports/DONCHIAN_REENTRY10_FINANCIAL_SOURCE_BINDING_FAILURE_20261005_V4.json',dict(
    status='FAILED_OLD_CHECKER_SOURCE_BINDING_BEFORE_FINANCIAL_INPUT',actual_closed_task=failed,
    original_binding_sha256=sha(prior),checker_sha256=sha(ROOT/CHECKER),market_replays=0,financial_calls_started=0,
    reason='V4 binding omitted existing source_archives mapping for pre-market checker bytes',
    correction='Use existing source_archives CHECKER to exact original f8a753 archive; no further production code change',
    created_utc=datetime.now(UTC).isoformat()))
plan.update(source_archives={**plan.get('source_archives',{}),CHECKER:OLD},
    independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL_V5.json',
    independent_binding_protocol='protocols/'+STEM+'_FINANCIAL_BINDING_V5.json',
    source_binding_correction_only=True,prior_failed_binding_task=failed,
    metadata_helper=dict(path=Path(__file__).relative_to(ROOT).as_posix(),sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID']),
    created_utc=datetime.now(UTC).isoformat())
bp=ROOT/plan['independent_binding_protocol'];save(bp,plan)
run=STATE/'d070-reentry10-financial-20261005-v5';run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(path=str(bp),sha256=sha(bp),source_archives=plan['source_archives'])))
