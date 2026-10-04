"""D072 finite bindings for one configured-pool contrast using existing runners."""
import argparse,hashlib,json,os,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.investment import donchian_daily_pool_target as dc
STEM='DONCHIAN_TWO_20261005_V1'
OWN='docs/archive/DONCHIAN_TWO_METADATA_SOURCE_20261005_V1.py'
CHECKER='scripts/investment/multi_asset_financial_audit.py'
PARENT='e9608b808478d8f433d6b0b7230396abf7449b21'
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
    names=['tests/test_donchian_two_asset_reference.py',CHECKER,'scripts/investment/donchian_daily_pool_target.py',
        'scripts/investment/public_sma_perpetual.py','scripts/investment/public_sma_daily.py',
        'scripts/investment/research_tests.py','scripts/investment/public_pair_diagnostics.py',
        'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py','environments/v8/uv.lock',OWN]
    names+=['third_party/jesse_example_donchian/'+n for n in dc.PINNED_HASHES]
    write(ROOT/'protocols'/(STEM+'_SYNTHETIC.json'),dict(ready_to_execute=True,tests=[names[0]],frozen_sources={n:sha(ROOT/n) for n in names},
        calculation_rules=dict(fixed_periods=[10,20],ordered_two_asset_targets_and_direct_reference=True,past_only=True,tolerance=1e-12),
        fee_profile=dict(source='NONE_SYNTHETIC_TARGETS_ONLY',market='NONE',risk='abs.3/gross.6/vol.10')))
elif args.phase=='market':
    p=read(ROOT/'protocols/DONCHIAN_EXIT10_20261004_V1.json');p.pop('saved_control',None)
    tr=ROOT/'reports/fast_research'/(STEM+'_SYNTHETIC.json');t=read(tr);closed(t);assert t['test_exit_code']==0
    refs={}
    for role,proto,actual,finance,commit in (
        ('HOLD10_TWO','CONTINUOUS_DAILY_TREND_HOLD_TWO_20261004_V1','CONTINUOUS_DAILY_TREND_HOLD_TWO_20261004_V1','CONTINUOUS_DAILY_TREND_HOLD_TWO_FINANCIAL_20261004_V1','55798a1'),
        ('HOLD8_TWO','HOLD_RISK8_20261005_V1','HOLD_RISK8_20261005_V1','HOLD_RISK8_20261005_V1_FINANCIAL',PARENT),
        ('EXIT10_TEN','DONCHIAN_EXIT10_20261004_V1','DONCHIAN_EXIT10_20261004_V1','DONCHIAN_EXIT10_20261004_V1_FINANCIAL','33fa0de74cc9fb9d86420d2f1ad0d6d48b49d998')):
        pp=ROOT/'protocols'/(proto+'.json');ap=ROOT/'reports/fast_research'/(actual+'.json');fp=ROOT/'reports/fast_research'/(finance+'.json')
        a=read(ap);f=read(fp);closed(a);closed(f);assert a['complete_calendar_cases']==f['financial_case_calls']==4
        refs[role]=dict(protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),actual_path=ap.relative_to(ROOT).as_posix(),actual_sha256=sha(ap),
            financial_path=fp.relative_to(ROOT).as_posix(),financial_sha256=sha(fp),accepted_source_commit=commit)
    pins={n:sha(ROOT/n) for n in p['source_hashes']}
    for n in (OWN,'tests/test_donchian_two_asset_reference.py',tr.relative_to(ROOT).as_posix(),
              'docs/archive/DONCHIAN_TWO_DIAGNOSTIC_SOURCE_20261005_V1.py'):pins[n]=sha(ROOT/n)
    p.update(source_hashes=pins,saved_comparisons=refs,experiment_id='D072-EXIT10-TWO-SEPJUN303-20261005',
        question='Does the fixed EXIT10 timing rule add net/risk value against HOLD on the same two assets, and what changes when only the configured pool is expanded?',
        stopping_rule='One unchanged EXIT10 recipe/explicitTWO_ASSET only; no cost/date/risk/capital/terminal changes or search, retain failures',
        success_rule='Complete accurate paired economics; no profit/alpha promotion gate; risk is reported rather than assumed matched',
        budget=dict(owned_bytes=400000000,wall_seconds=1800,peak_RSS_bytes=3000000000),
        research_budget=dict(total_new_STATE_bytes=400000000,new_actual_accounts=4,new_independent_accounts=4,saved_reference_accounts=12,HPO=0,models_fit=0,new_recipes=0),
        independent_reference_pre_market_sha256=pins[CHECKER],economic_comparer_pre_market_sha256=pins['scripts/investment/compare_multi_asset_portfolios.py'],created_utc=now)
    assert p['strategy']==dc.strategy_id(10,20) and p['strategy_rules']==dc.strategy_rules('ACTIVE_EQUAL',10,20)
    write(ROOT/'protocols'/(STEM+'.json'),p)
else:
    pp=ROOT/'protocols'/(STEM+'.json');p=read(pp);ap=ROOT/'reports/fast_research'/(STEM+'.json');a=read(ap);task=closed(a)
    assert a['completed_cases']==a['complete_calendar_cases']==4 and all(c['symbols']==['BTCUSDT','ETHUSDT'] for c in a['cases'])
    assert a['binding']['protocol_sha256']==sha(pp)
    for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
    plan=read(ROOT/'protocols/HOLD_RISK8_20261005_V1_FINANCIAL_BINDING.json')
    for n,h in plan['source_hashes'].items():assert n==CHECKER or sha(ROOT/n)==h,n
    bp=ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING.json')
    plan.update(checker_sha256=sha(ROOT/CHECKER),source_hashes={n:sha(ROOT/n) for n in plan['source_hashes']},
        protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),actual_report=ap.relative_to(ROOT).as_posix(),actual_report_sha256=sha(ap),
        actual_task_id=a['binding']['task_id'],strategy=p['strategy'],allocation=p['allocation'],independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL.json',
        independent_binding_protocol=bp.relative_to(ROOT).as_posix(),metadata_helper=dict(path=OWN,sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID']),
        producer_actual_closed_task=task,created_utc=now)
    write(bp,plan);run=STATE/'d072-donchian-two-financial-20261005-v1';run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(phase=args.phase,task_id=os.environ['COIN_TASK_ID'],created_utc=now)))
