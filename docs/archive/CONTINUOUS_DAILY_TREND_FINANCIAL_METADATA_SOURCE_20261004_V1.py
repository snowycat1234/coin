"""Bind only true closed continuous303 producers to the existing independent account."""
import argparse,hashlib,importlib.util,json,os,sys
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
CHECKER='scripts/investment/multi_asset_financial_audit.py'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p):
    p=Path(p);assert p.is_file() and not p.is_symlink() and p.stat().st_size<4_000_000
    return json.loads(p.read_bytes())
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
parser=argparse.ArgumentParser();parser.add_argument('--recipe',required=True,choices=['HOLD_TWO','HOLD_TEN','DONCHIAN_TEN']);args=parser.parse_args()
assert os.environ['COIN_TASK_ID']
stem='CONTINUOUS_DAILY_TREND_'+args.recipe+'_20261004_V1'
pp=ROOT/'protocols'/(stem+'.json');ap=ROOT/'reports/fast_research'/(stem+'.json');p=small(pp);a=small(ap)
task=small(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
assert task['status']=='completed' and task['exit_code']==0 and task['ended_at']
assert a['completed_cases']==a['complete_calendar_cases']==4 and a['actual_calendar_days']==303
rb=small(Path(a['run_dir'])/'RUN_BINDING.json');assert rb==a['binding'] and rb['protocol_sha256']==sha(pp)
assert rb['source_hashes']==p['source_hashes']
for n,h in rb['source_hashes'].items():assert sha(ROOT/n)==h,n
prior_path=STATE/'d054-november-ten-equal-financial-20261004-v1/ACTUAL_BINDING.json'
assert sha(prior_path)=='e402f2d22ec174da1f9ab11da52917d1223c6d5320c9381f746609f6631aa0fc'
prior=small(prior_path);pins=dict(prior['source_hashes']);assert len(pins)==14 and prior['source_archives']=={}
pins[CHECKER]=sha(ROOT/CHECKER)
for n,h in pins.items():assert sha(ROOT/n)==h,n
assert p['independent_reference_pre_market_sha256']==pins[CHECKER]
spec=importlib.util.spec_from_file_location('continuous303_account_metadata_checker',ROOT/CHECKER)
checker=importlib.util.module_from_spec(spec);sys.modules[spec.name]=checker;spec.loader.exec_module(checker)
scope=checker.calendar_scope(p);assert scope['period_days']==303 and scope['required_minutes']==436320 and scope['calendar_months']==10
run=STATE/('d064-continuous303-'+args.recipe.lower().replace('_','-')+'-financial-20261004-v1')
out='reports/fast_research/CONTINUOUS_DAILY_TREND_'+args.recipe+'_FINANCIAL_20261004_V1.json'
bp=ROOT/'protocols'/('CONTINUOUS_DAILY_TREND_'+args.recipe+'_FINANCIAL_BINDING_20261004_V1.json')
plan=dict(ready_to_execute=True,checker_sha256=pins[CHECKER],source_hashes=pins,source_archives={},
    tolerances=prior['tolerances'],protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),
    actual_report=ap.relative_to(ROOT).as_posix(),actual_report_sha256=sha(ap),actual_task_id=a['binding']['task_id'],
    required_scope=scope,strategy=p['strategy'],allocation='EQUAL',required_financial_case_calls=4,
    independent_output_path=out,independent_binding_protocol=bp.relative_to(ROOT).as_posix(),
    terminal_cash_required=False,full_market_intent_sizing_independently_rebuilt=False,
    budgets=dict(new_owned_bytes=100000,wall_seconds=1800,peak_RSS_bytes=1500000000),
    prior_independent_helper_map=dict(path=str(prior_path),sha256=sha(prior_path)),
    metadata_helper=dict(path='docs/archive/CONTINUOUS_DAILY_TREND_FINANCIAL_METADATA_SOURCE_20261004_V1.py',sha256=sha(Path(__file__)),task_id=os.environ['COIN_TASK_ID']),
    producer_actual_closed_task=task,created_utc=datetime.now(UTC).isoformat())
assert plan['tolerances']==dict(cash_USDT=1e-7,ratio=1e-10)
write(bp,plan);run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(recipe=args.recipe,plan=str(run/'ACTUAL_BINDING.json'),sha256=sha(bp),source_payloads_read=0,financial_calls=0)),flush=True)
