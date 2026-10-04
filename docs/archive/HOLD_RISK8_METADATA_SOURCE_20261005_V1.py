"""Finite D071 orchestration of existing bounded tests and shared account runners."""
import argparse, hashlib, json, os, subprocess
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from scripts.investment import vol_managed_perpetual_target as hold

STEM='HOLD_RISK8_20261005_V1'
CONTROL='CONTINUOUS_DAILY_TREND_HOLD_TWO_20261004_V1'
OWN='docs/archive/HOLD_RISK8_METADATA_SOURCE_20261005_V1.py'
CHECKER='scripts/investment/multi_asset_financial_audit.py'
PARENT='d82ac37415d099cd8d408424a81505bc85c0ca66'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def closed(a):
    t=read(STATE/'task-progress'/('task-'+a['binding']['task_id']+'.json'))
    assert t['status']=='completed' and t['exit_code']==0 and t['ended_at'];return t
parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('test','market','finance'));args=parser.parse_args()
assert os.environ['COIN_TASK_ID']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
now=datetime.now(UTC).isoformat()
if args.phase=='test':
    names=['tests/test_hold_risk_budget.py','scripts/investment/public_sma_perpetual.py',
        'scripts/investment/vol_managed_perpetual_target.py','scripts/investment/multi_asset_portfolio.py',CHECKER,
        'scripts/investment/public_sma_daily.py','scripts/investment/research_tests.py',
        'scripts/investment/public_pair_diagnostics.py','docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py',
        'environments/v8/uv.lock',OWN]
    write(ROOT/'protocols'/(STEM+'_SYNTHETIC.json'),dict(ready_to_execute=True,tests=[names[0]],frozen_sources={n:sha(ROOT/n) for n in names},
        calculation_rules=dict(risk_budgets=[.10,.08],default_equivalence=True,past_covariance_only=True,ordered_assets=True,tolerance=1e-13),
        fee_profile=dict(source='NONE_SYNTHETIC_TARGETS_ONLY',market='NONE',risk='abs.3/gross.6/vol<=.10')))
elif args.phase=='market':
    pp=ROOT/'protocols'/(CONTROL+'.json');ap=ROOT/'reports/fast_research'/(CONTROL+'.json')
    fp=ROOT/'reports/fast_research/CONTINUOUS_DAILY_TREND_HOLD_TWO_FINANCIAL_20261004_V1.json'
    p=read(pp);a=read(ap);f=read(fp);closed(a);closed(f)
    assert a['complete_calendar_cases']==f['financial_case_calls']==4
    tr=ROOT/'reports/fast_research'/(STEM+'_SYNTHETIC.json');test=read(tr);closed(test);assert test['test_exit_code']==0
    pins={n:sha(ROOT/n) for n in p['source_hashes']}
    for n in (OWN,'tests/test_hold_risk_budget.py',tr.relative_to(ROOT).as_posix(),
              'docs/archive/HOLD_RISK8_DIAGNOSTIC_SOURCE_20261005_V1.py'):pins[n]=sha(ROOT/n)
    control=dict(protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),actual_path=ap.relative_to(ROOT).as_posix(),actual_sha256=sha(ap),
        financial_path=fp.relative_to(ROOT).as_posix(),financial_sha256=sha(fp),accepted_source_commit='55798a1',
        note='Saved D064 HOLD_TWO 10 percent full account; historical source resolved by Git, never replayed')
    rules=dict(hold.RULES,annual_volatility_target=.08)
    p.update(strategy_rules=rules,source_hashes=pins,saved_control=control,
        experiment_id='D071-HOLD8-TWO-SEPJUN303-20261005',question='Does lower past-only HOLD risk budget retain net return while approaching the timing strategy actual risk?',
        stopping_rule='Exactly one predeclared8percent setting; explicit TWO_ASSET only; no posthoc NAV scaling or budget grid, no change to costs/capital/caps/exit attempts',
        success_rule='Complete full accounts and independent ledger; judge net/risk jointly, no APR certification',
        research_budget=dict(total_new_STATE_bytes=400000000,new_actual_accounts=4,new_independent_accounts=4,saved_control_accounts=4,HPO=0,models_fit=0,new_recipes=1),
        independent_reference_pre_market_sha256=pins[CHECKER],economic_comparer_pre_market_sha256=pins['scripts/investment/compare_multi_asset_portfolios.py'],created_utc=now)
    write(ROOT/'protocols'/(STEM+'.json'),p)
else:
    pp=ROOT/'protocols'/(STEM+'.json');p=read(pp);ap=ROOT/'reports/fast_research'/(STEM+'.json');a=read(ap);task=closed(a)
    assert a['completed_cases']==a['complete_calendar_cases']==4 and all(c['symbols']==['BTCUSDT','ETHUSDT'] for c in a['cases'])
    assert a['binding']['protocol_sha256']==sha(pp)
    for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
    plan=read(ROOT/'protocols/CONTINUOUS_DAILY_TREND_HOLD_TWO_FINANCIAL_BINDING_20261004_V1.json')
    for n,h in plan['source_hashes'].items():assert n==CHECKER or sha(ROOT/n)==h,n
    bp=ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING.json')
    plan.pop('source_archives',None)
    plan.update(checker_sha256=sha(ROOT/CHECKER),source_hashes={n:sha(ROOT/n) for n in plan['source_hashes']},
        protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),actual_report=ap.relative_to(ROOT).as_posix(),actual_report_sha256=sha(ap),
        actual_task_id=a['binding']['task_id'],strategy=p['strategy'],allocation=p['allocation'],independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL.json',
        independent_binding_protocol=bp.relative_to(ROOT).as_posix(),metadata_helper=dict(path=OWN,sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID']),
        producer_actual_closed_task=task,created_utc=now)
    write(bp,plan);run=STATE/'d071-hold-risk8-financial-20261005-v1';run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(phase=args.phase,task_id=os.environ['COIN_TASK_ID'],created_utc=now)))
