"""Bind only the lossless report-output correction after the saved full market replay."""
import hashlib, json, os
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE

STEM = 'DONCHIAN_REENTRY10_20261005_V3'
CHECKER = 'scripts/investment/multi_asset_financial_audit.py'
OLD = 'docs/archive/DONCHIAN_REENTRY10_PRE_COMPACT_FINANCIAL_SOURCE_20261005_V1.py'
def read(p): return json.loads(Path(p).read_bytes())
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, v):
    with Path(p).open('x') as f: json.dump(v, f, indent=2, allow_nan=False); f.write('\n')
assert os.environ['COIN_TASK_ID']
p = read(ROOT/'protocols'/(STEM+'.json'))
a = read(ROOT/'reports/fast_research'/(STEM+'.json'))
market_task = read(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
assert market_task['status']=='completed' and market_task['exit_code']==0 and market_task['ended_at']
assert a['completed_cases']==a['complete_calendar_cases']==4 and all(c['pool']=='LIQUIDITY_TEN' for c in a['cases'])
for name, digest in p['source_hashes'].items():
    assert sha(ROOT/(OLD if name==CHECKER else name))==digest, name
failed = read(STATE/'task-progress/task-00d746b7f6044411a289545ad33a6ca7.json')
assert failed['status']=='failed' and failed['exit_code']==1 and failed['ended_at']
oldbinding = ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING.json')
plan = read(oldbinding)
assert plan['checker_sha256']==sha(ROOT/OLD) and not (ROOT/'reports/fast_research'/(STEM+'_FINANCIAL.json')).exists()
save(ROOT/'reports/DONCHIAN_REENTRY10_FINANCIAL_OUTPUT_FAILURE_20261005_V3.json',dict(
    status='FAILED_REPORT_2MB_LIMIT_NOT_FINANCIAL_ACCEPTANCE', actual_closed_task=failed,
    old_checker_path=OLD, old_checker_sha256=sha(ROOT/OLD), original_binding_sha256=sha(oldbinding),
    final_output_written=False, reason='finally guard.write rejected pretty-printed repeated witness fields above 2000000 bytes',
    accounts_visited_in_progress=4, completed_financial_acceptance=0, market_replays=0,
    correction='All witness fields/rows preserved as key schemas and ordered values with exact roundtrip assertion; financial math/target reference/tolerances unchanged',
    created_utc=datetime.now(UTC).isoformat()))
plan.update(checker_sha256=sha(ROOT/CHECKER),source_hashes={n:sha(ROOT/n) for n in plan['source_hashes']},
    independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL_V4.json',
    independent_binding_protocol='protocols/'+STEM+'_FINANCIAL_BINDING_V4.json',
    pre_market_checker_resolution=dict(path=OLD,sha256=sha(ROOT/OLD)),
    report_encoding_correction_only=True, original_failed_financial_task=failed,
    metadata_helper=dict(path=Path(__file__).relative_to(ROOT).as_posix(),sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID']),
    created_utc=datetime.now(UTC).isoformat())
bp=ROOT/plan['independent_binding_protocol'];save(bp,plan)
run=STATE/'d070-reentry10-financial-20261005-v4';run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(path=str(bp),sha256=sha(bp),checker_sha256=plan['checker_sha256'])))
