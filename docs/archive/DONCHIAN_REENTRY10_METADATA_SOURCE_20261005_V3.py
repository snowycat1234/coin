"""Small D070 bindings for existing test, portfolio and independent runners."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
from datetime import UTC, datetime
from quant.paths import ROOT, STATE
from scripts.investment import donchian_daily_pool_target as dc

STEM='DONCHIAN_REENTRY10_20261005_V3'
CONTROL='DONCHIAN_EXIT10_20261004_V1'
OWN='docs/archive/DONCHIAN_REENTRY10_METADATA_SOURCE_20261005_V3.py'
CHECKER='scripts/investment/multi_asset_financial_audit.py'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(Path(p).read_bytes())
def write(p,v):
    with Path(p).open('x') as f: json.dump(v,f,indent=2,allow_nan=False); f.write('\n')
def closed(a):
    ident=a['binding']['task_id']
    t=read(STATE/'task-progress'/('task-'+ident+'.json'))
    assert t['status']=='completed' and t['exit_code']==0 and t['ended_at']
    return t
parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('test','market','finance'));args=parser.parse_args()
assert os.environ['COIN_TASK_ID']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()=='1b3987e77854940a043b35b52e928d615ef739bc'
now=datetime.now(UTC).isoformat()
if args.phase=='test':
    names=['tests/test_donchian_reentry_period.py', 'scripts/investment/donchian_daily_pool_target.py',
        'scripts/investment/public_sma_perpetual.py', 'scripts/investment/public_sma_daily.py', CHECKER,
        'scripts/investment/research_tests.py','scripts/investment/public_pair_diagnostics.py',
        'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py','environments/v8/uv.lock',OWN]
    names += ['third_party/jesse_example_donchian/'+n for n in dc.PINNED_HASHES]
    write(ROOT/'protocols'/(STEM+'_SYNTHETIC.json'),dict(ready_to_execute=True, tests=[names[0]],frozen_sources={n:sha(ROOT/n) for n in names},
        calculation_rules=dict(exit_periods=[10],reentry_periods=[20,10],prior20_initial_entry_unchanged=True,independent_direct_state_and_covariance=True,tolerance=1e-13),
        fee_profile=dict(source='NONE_SYNTHETIC_TARGETS_ONLY',market='NONE',risk='abs.3/gross.6/vol.10')))
elif args.phase=='market':
    pp=ROOT/'protocols'/(CONTROL+'.json'); ap=ROOT/'reports/fast_research'/(CONTROL+'.json'); fp=ROOT/'reports/fast_research'/(CONTROL+'_FINANCIAL.json')
    p=read(pp);a=read(ap);f=read(fp);closed(a);closed(f)
    assert a['complete_calendar_cases']==f['financial_case_calls']==4
    tpath=ROOT/'reports/fast_research/DONCHIAN_REENTRY10_20261005_V2_SYNTHETIC.json';t=read(tpath);closed(t);assert t['test_exit_code']==0
    pins={n:sha(ROOT/n) for n in p['source_hashes']}
    for n in [OWN,'tests/test_donchian_reentry_period.py',tpath.relative_to(ROOT).as_posix(),'docs/archive/DONCHIAN_REENTRY10_DIAGNOSTIC_SOURCE_20261005_V3.py']:pins[n]=sha(ROOT/n)
    control=dict(protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),actual_path=ap.relative_to(ROOT).as_posix(),actual_sha256=sha(ap),
        financial_path=fp.relative_to(ROOT).as_posix(),financial_sha256=sha(fp),accepted_source_commit='33fa0de74cc9fb9d86420d2f1ad0d6d48b49d998',
        artifacts={c['id']:c['artifacts'] for c in a['cases']},note='Saved D067 full exit10/reentry20 ACTIVE_EQUAL accounts; no old replay')
    p.update(execution_pool_id='LIQUIDITY_TEN',required_invocation_pool_id='LIQUIDITY_TEN',prior_mislaunch_report='reports/fast_research/DONCHIAN_REENTRY10_20261005_V2.json',prior_mislaunch_report_sha256=sha(ROOT/'reports/fast_research/DONCHIAN_REENTRY10_20261005_V2.json'),strategy=dc.strategy_id(10,reentry_period=10),strategy_rules=dc.strategy_rules('ACTIVE_EQUAL',10,reentry_period=10),source_hashes=pins,saved_control=control,
        experiment_id='D070-REENTRY10-SEPJUN303-20261005-V3',question='Does only faster armed prior10 recovery reentry improve actual net/risk after unchanged initial20 entry, exit10 and costs?',
        stopping_rule='One armed-reentry20-to10 change; first20 entry and exit10 retained; no search, pool/date/cost/risk/capital/terminal-attempt changes',
        success_rule='Correct full replay and independent targets/ledger; retain challenger only if economically useful across all fixed interpretations, not APR promotion',
        research_budget=dict(total_new_STATE_bytes=800000000,new_actual_accounts=4,new_independent_accounts=4,saved_control_accounts=4,HPO=0,models_fit=0,new_recipes=1),
        independent_reference_pre_market_sha256=pins[CHECKER],economic_comparer_pre_market_sha256=pins['scripts/investment/compare_multi_asset_portfolios.py'],
        created_utc=now)
    write(ROOT/'protocols'/(STEM+'.json'),p)
else:
    pp=ROOT/'protocols'/(STEM+'.json');p=read(pp);ap=ROOT/'reports/fast_research'/(STEM+'.json');a=read(ap);task=closed(a)
    assert a['completed_cases']==a['complete_calendar_cases']==4
    assert a['binding']['protocol_sha256']==sha(pp)
    for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
    prior=read(ROOT/'protocols'/(CONTROL+'_FINANCIAL_BINDING.json'))
    for n,h in prior['source_hashes'].items():assert n==CHECKER or sha(ROOT/n)==h,n
    bp=ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING.json')
    prior.update(checker_sha256=sha(ROOT/CHECKER),source_hashes={n:sha(ROOT/n) for n in prior['source_hashes']},
        protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),actual_report=ap.relative_to(ROOT).as_posix(),actual_report_sha256=sha(ap),
        actual_task_id=a['binding']['task_id'],strategy=p['strategy'],independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL.json',
        independent_binding_protocol=bp.relative_to(ROOT).as_posix(),metadata_helper=dict(path=OWN,sha256=sha(Path(__file__)),task_id=os.environ['COIN_TASK_ID']),
        producer_actual_closed_task=task,created_utc=now)
    write(bp,prior); run=STATE/'d070-reentry10-financial-20261005-v3';run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(phase=args.phase,task_id=os.environ['COIN_TASK_ID'],created_utc=now)))
