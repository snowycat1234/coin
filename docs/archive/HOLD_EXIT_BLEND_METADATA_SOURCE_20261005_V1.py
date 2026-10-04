"""Bind one finite shared-wallet blend experiment to existing accepted data."""
import argparse,hashlib,json,os,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.investment import hold_donchian_blend_target as blend
STEM='HOLD_EXIT_BLEND_20261005_V1'
OWN='docs/archive/HOLD_EXIT_BLEND_METADATA_SOURCE_20261005_V1.py'
CHECKER='scripts/investment/multi_asset_financial_audit.py'
PARENT='f1d19a6ca9b071b375b3bfa943a47213facf0062'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,allow_nan=False);f.write('\n')
def closed(a):
    ident=a.get('binding',{}).get('task_id') or a['task_id']
    t=read(STATE/'task-progress'/('task-'+ident+'.json'))
    assert t['status']=='completed' and t['exit_code']==0 and t['ended_at'];return t
parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('test','market','finance'));args=parser.parse_args()
assert os.environ['COIN_TASK_ID']
assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
now=datetime.now(UTC).isoformat()
if args.phase=='test':
    names=['tests/test_hold_donchian_blend.py',CHECKER,'scripts/investment/hold_donchian_blend_target.py',
        'scripts/investment/donchian_daily_pool_target.py','scripts/investment/vol_managed_perpetual_target.py',
        'scripts/investment/public_sma_perpetual.py','scripts/investment/public_sma_daily.py',
        'scripts/investment/research_tests.py','scripts/investment/public_pair_diagnostics.py',
        'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py','environments/v8/uv.lock',OWN]
    names+=['third_party/jesse_example_donchian/'+n for n in ('donchian_original.py','donchian_indicator_original.py','LICENSE','JESSE_LICENSE')]
    write(ROOT/'protocols'/(STEM+'_SYNTHETIC.json'),dict(ready_to_execute=True,tests=[names[0]],frozen_sources={n:sha(ROOT/n) for n in names},
        calculation_rules=dict(fixed_component_weights=[.5,.5],ordered_targets_after_component_risk=True,
            shared_capital_not_NAV_blend=True,past_only=True,tolerance=1e-12),
        fee_profile=dict(source='NONE_SYNTHETIC_TARGETS_ONLY',market='NONE',risk='abs.3/gross.6/component vol.10')))
elif args.phase=='market':
    p=read(ROOT/'protocols/DONCHIAN_TWO_20261005_V1.json')
    tr=ROOT/'reports/fast_research'/(STEM+'_SYNTHETIC.json');t=read(tr);closed(t);assert t['test_exit_code']==0
    refs={k:v for k,v in p['saved_comparisons'].items() if k in ('HOLD10_TWO','HOLD8_TWO')}
    for role,stem,financial in (('EXIT10_TWO','DONCHIAN_TWO_20261005_V1','DONCHIAN_TWO_20261005_V1_FINANCIAL'),):
        pp=ROOT/'protocols'/(stem+'.json');ap=ROOT/'reports/fast_research'/(stem+'.json');fp=ROOT/'reports/fast_research'/(financial+'.json')
        refs[role]=dict(protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),
            actual_path=ap.relative_to(ROOT).as_posix(),actual_sha256=sha(ap),
            financial_path=fp.relative_to(ROOT).as_posix(),financial_sha256=sha(fp),accepted_source_commit=PARENT)
    for ref in refs.values():
        a=read(ROOT/ref['actual_path']);f=read(ROOT/ref['financial_path']);closed(a);closed(f)
        assert a['complete_calendar_cases']==f['financial_case_calls']==4
    pins={n:sha(ROOT/n) for n in p['source_hashes']}
    for n in (OWN,'scripts/investment/hold_donchian_blend_target.py','tests/test_hold_donchian_blend.py',
        tr.relative_to(ROOT).as_posix(),'docs/archive/HOLD_EXIT_BLEND_DIAGNOSTIC_SOURCE_20261005_V1.py'):pins[n]=sha(ROOT/n)
    p.update(source_hashes=pins,saved_comparisons=refs,experiment_id='D073-HALF-HOLD-EXIT10-TWO-SEPJUN303-20261005',
        strategy=blend.STRATEGY_ID,allocation=blend.ALLOCATION,strategy_rules=blend.RULES,
        question='Does one fixed 50/50 mix of past-available HOLD10 and EXIT10 targets in one wallet offer a better net-return/risk tradeoff than the existing same-pool controls?',
        stopping_rule='Exactly one half/half recipe and explicit TWO_ASSET, four complete accounts; finite wall/output/RSS bounds; no cost/date/caps/terminal changes, no weight search',
        success_rule='Accurate account economics; retain challenger only if not dominated by existing same-pool controls in net return and both volatility/MDD across all declared cost/unit scenarios; no alpha/APR promotion',
        budget=dict(owned_bytes=400000000,wall_seconds=1800,peak_RSS_bytes=3000000000),
        research_budget=dict(total_new_STATE_bytes=400000000,new_actual_accounts=4,new_independent_accounts=4,saved_reference_accounts=12,HPO=0,models_fit=0,new_recipes=1),
        independent_reference_pre_market_sha256=pins[CHECKER],created_utc=now)
    write(ROOT/'protocols'/(STEM+'.json'),p)
else:
    pp=ROOT/'protocols'/(STEM+'.json');p=read(pp);ap=ROOT/'reports/fast_research'/(STEM+'.json');a=read(ap);task=closed(a)
    assert a['completed_cases']==a['complete_calendar_cases']==4 and all(c['symbols']==['BTCUSDT','ETHUSDT'] for c in a['cases'])
    assert a['binding']['protocol_sha256']==sha(pp)
    for n,h in p['source_hashes'].items():assert sha(ROOT/n)==h,n
    plan=read(ROOT/'protocols/DONCHIAN_TWO_20261005_V1_FINANCIAL_BINDING.json')
    for n,h in plan['source_hashes'].items():assert n==CHECKER or sha(ROOT/n)==h,n
    bp=ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING.json')
    plan.update(checker_sha256=sha(ROOT/CHECKER),source_hashes={n:sha(ROOT/n) for n in plan['source_hashes']},
        protocol_path=pp.relative_to(ROOT).as_posix(),protocol_sha256=sha(pp),actual_report=ap.relative_to(ROOT).as_posix(),actual_report_sha256=sha(ap),
        actual_task_id=a['binding']['task_id'],strategy=p['strategy'],allocation=p['allocation'],independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL.json',
        independent_binding_protocol=bp.relative_to(ROOT).as_posix(),metadata_helper=dict(path=OWN,sha256=sha(__file__),task_id=os.environ['COIN_TASK_ID']),
        producer_actual_closed_task=task,created_utc=now)
    write(bp,plan);run=STATE/'d073-hold-exit-blend-financial-20261005-v1';run.mkdir();(run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
print(json.dumps(dict(phase=args.phase,task_id=os.environ['COIN_TASK_ID'],created_utc=now)))
