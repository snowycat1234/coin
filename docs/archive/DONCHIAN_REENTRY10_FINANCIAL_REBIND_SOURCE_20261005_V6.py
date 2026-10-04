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
failed=read(STATE/'task-progress/task-057725d9898149e3a9c009fae76cc55d.json')
assert failed['status']=='failed' and failed['exit_code']==1 and failed['ended_at']
prior=ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING_V5.json');plan=read(prior)
assert plan['checker_sha256']==sha(ROOT/CHECKER)
save(ROOT/'reports/DONCHIAN_REENTRY10_FINANCIAL_SOURCE_BINDING_FAILURE_20261005_V5.json',dict(
    status='FAILED_OLD_CHECKER_SOURCE_BINDING_BEFORE_FINANCIAL_INPUT',actual_closed_task=failed,
    original_binding_sha256=sha(prior),checker_sha256=sha(ROOT/CHECKER),market_replays=0,financial_calls_started=0,
    reason='V5 archives mapping applied to both source maps; independent planned checker digest must be original while checker_sha256 binds actual current evaluator',
    correction='Use existing source_archives CHECKER to exact f8a753 archive in planned source_hashes; checker_sha256 separately pins current684 evaluator; no further production code change',
    created_utc=datetime.now(UTC).isoformat()))
plan['source_hashes'][CHECKER]=sha(ROOT/OLD)
plan.update(current_evaluator_source=dict(path=CHECKER,sha256=sha(ROOT/CHECKER)),source_archives={**plan.get('source_archives',{}),CHECKER:OLD},
    independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL_V6.json',
    independent_binding_protocol='protocols/'+STEM+'_FINANCIAL_BINDING_V6.json',
    source_binding_correction_only=True,prior_failed_binding_task=failed,
    metadata_helper=dict(path=Path(__file__).relative_to(ROOT).as_posix(),sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID']),
    created_utc=datetime.now(UTC).isoformat())
bp=ROOT/plan['independent_binding_protocol'];save(bp,plan)
run=STATE/'d070-reentry10-financial-20261005-v6';run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(path=str(bp),sha256=sha(bp),source_archives=plan['source_archives'])))
