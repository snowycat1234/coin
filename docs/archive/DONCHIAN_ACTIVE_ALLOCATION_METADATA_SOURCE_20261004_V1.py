"""Finite D065 metadata and saved-result contrast, reusing normal runners."""
import argparse, hashlib, importlib.util, json, os, subprocess, sys
from pathlib import Path
from datetime import UTC, datetime
from quant.paths import ROOT, STATE

STEM = 'DONCHIAN_ACTIVE_ALLOCATION_20261004_V1'
OWN = 'docs/archive/DONCHIAN_ACTIVE_ALLOCATION_METADATA_SOURCE_20261004_V1.py'
CHECKER = 'scripts/investment/multi_asset_financial_audit.py'
CONTROL = 'CONTINUOUS_DAILY_TREND_DONCHIAN_TEN_20261004_V1'
PARENT = '55798a1795b75c64b63c291a70fa5a84b357ce7f'

def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def read(p):
    p = Path(p)
    assert p.is_file() and not p.is_symlink()
    return json.loads(p.read_bytes())

def write(p, value):
    with Path(p).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')

def closed(actual):
    task = read(STATE/'task-progress'/('task-'+actual['binding']['task_id']+'.json'))
    assert task['status'] == 'completed' and task['exit_code'] == 0 and task['ended_at']
    return task

parser = argparse.ArgumentParser(); parser.add_argument('phase', choices=['test', 'market', 'finance', 'result'])
args = parser.parse_args()
assert os.environ['COIN_TASK_ID']
now = datetime.now(UTC).isoformat()
if args.phase == 'test':
    names = ['tests/test_donchian_active_allocation.py', 'scripts/investment/donchian_daily_pool_target.py',
        'scripts/investment/public_sma_perpetual.py', CHECKER, 'scripts/investment/public_sma_daily.py',
        'scripts/investment/research_tests.py', 'scripts/investment/public_pair_diagnostics.py',
        'docs/archive/BOUNDED_RESEARCH_TEST_RUNNER_SOURCE_20261003_V1.py', 'environments/v8/uv.lock', OWN]
    names += ['third_party/jesse_example_donchian/'+n for n in
        ['donchian_original.py', 'donchian_indicator_original.py', 'LICENSE', 'JESSE_LICENSE']]
    p = dict(ready_to_execute=True, tests=[names[0]], frozen_sources={n:sha(ROOT/n) for n in names},
        calculation_rules=dict(independent='Direct active count, signal state and past covariance; EQUAL control',
            tolerance=1e-13, future_perturbation=True, market_accounts=0, models_fit=0),
        fee_profile=dict(source='NONE_SYNTHETIC_TARGETS_ONLY', market='NONE', risk='abs.3/gross.6/vol.10'))
    write(ROOT/'protocols'/(STEM+'_SYNTHETIC.json'), p)
elif args.phase == 'market':
    from scripts.investment import donchian_daily_pool_target as dc
    from scripts.investment import compare_multi_asset_portfolios as reuse
    pp = ROOT/'protocols'/(CONTROL+'.json'); p = read(pp)
    ap = ROOT/'reports/fast_research'/(CONTROL+'.json'); actual = read(ap)
    fp = ROOT/'reports/fast_research'/(CONTROL.replace('_20261004_V1','_FINANCIAL_20261004_V1')+'.json')
    financial = read(fp); closed(actual); closed(financial)
    assert actual['completed_cases'] == actual['complete_calendar_cases'] == financial['financial_case_calls'] == 4
    test = ROOT/'reports/fast_research'/(STEM+'_SYNTHETIC.json'); t = read(test); closed(t)
    assert t['test_exit_code'] == 0 and t['status'].startswith('PASS_')
    pins = {n:sha(ROOT/n) for n in p['source_hashes']}
    for n in [OWN, 'tests/test_donchian_active_allocation.py', test.relative_to(ROOT).as_posix()]:
        pins[n] = sha(ROOT/n)
    control = dict(protocol_path=pp.relative_to(ROOT).as_posix(), protocol_sha256=sha(pp),
        actual_path=ap.relative_to(ROOT).as_posix(), actual_sha256=sha(ap),
        financial_path=fp.relative_to(ROOT).as_posix(), financial_sha256=sha(fp),
        accepted_source_commit=PARENT, original_producer_binding_commit=actual['binding']['git_commit'],
        artifacts={c['id']:c['artifacts'] for c in actual['cases']},
        note='D064 uncommitted producer sources were subsequently committed exactly in 55798a1; source pins and artifacts preserved')
    rules = dict(dc.RULES); rules.update(raw_allocation='MIN_0.3_0.6_DIVIDED_BY_ACTIVE_ELIGIBLE_SIGNALS',
        inactive_signal_budget_redistributed=True, allocation='ACTIVE_EQUAL', active_signal_zero_is_cash=True,
        clipped_budget_not_redistributed=True)
    p.update(allocation='ACTIVE_EQUAL', source_hashes=pins, strategy_rules=rules,
        experiment_id='D065-ACTIVE-EQUAL-SEPJUN303-20261004',
        question='Does allocating only to active unchanged daily signals improve net participation after past covariance scaling?',
        success_rule='Complete or honestly halt; correct independent targets/money; compare net and actual risk without promotion from seen history',
        budget=dict(owned_bytes=600000000, wall_seconds=1800, peak_RSS_bytes=3000000000),
        research_budget=dict(total_new_STATE_bytes=800000000, new_actual_accounts=4, new_independent_accounts=4,
            saved_control_accounts=4, HPO=0, models_fit=0, new_recipes=1), saved_control=control,
        independent_reference_pre_market_sha256=pins[CHECKER], economic_comparer_pre_market_sha256=pins['scripts/investment/compare_multi_asset_portfolios.py'],
        stopping_rule='No cost/date/pool/signal/risk/exit-attempt changes; keep any failure, missingness and noncash exit',
        created_utc=now)
    write(ROOT/'protocols'/(STEM+'.json'), p)
    write(ROOT/'reports/fast_research'/(STEM+'_METADATA.json'), dict(status='READY_FOUR_NEW_ACCOUNTS_NOT_RUN',
        task_id=os.environ['COIN_TASK_ID'], protocol_sha256=sha(ROOT/'protocols'/(STEM+'.json')),
        new_downloads=0, new_QA=0, new_accounts=0, control=control, created_utc=now))
elif args.phase == 'finance':
    pp = ROOT/'protocols'/(STEM+'.json'); p = read(pp)
    ap = ROOT/'reports/fast_research'/(STEM+'.json'); a = read(ap); task = closed(a)
    assert a['completed_cases'] == a['complete_calendar_cases'] == 4
    rb = read(Path(a['run_dir'])/'RUN_BINDING.json')
    assert rb == a['binding'] and rb['protocol_sha256'] == sha(pp) and rb['source_hashes'] == p['source_hashes']
    for n,h in rb['source_hashes'].items(): assert sha(ROOT/n) == h, n
    prior_path = STATE/'d054-november-ten-equal-financial-20261004-v1/ACTUAL_BINDING.json'
    assert sha(prior_path) == 'e402f2d22ec174da1f9ab11da52917d1223c6d5320c9381f746609f6631aa0fc'
    prior = read(prior_path); pins = dict(prior['source_hashes']); pins[CHECKER] = sha(ROOT/CHECKER)
    for n,h in pins.items(): assert sha(ROOT/n) == h, n
    assert pins[CHECKER] == p['independent_reference_pre_market_sha256']
    spec = importlib.util.spec_from_file_location('d065_independent_metadata', ROOT/CHECKER)
    checker = importlib.util.module_from_spec(spec); sys.modules[spec.name] = checker; spec.loader.exec_module(checker)
    scope = checker.calendar_scope(p); assert scope['period_days'] == 303
    bp = ROOT/'protocols'/(STEM+'_FINANCIAL_BINDING.json')
    plan = dict(ready_to_execute=True, checker_sha256=pins[CHECKER], source_hashes=pins, source_archives={},
        tolerances=prior['tolerances'], protocol_path=pp.relative_to(ROOT).as_posix(), protocol_sha256=sha(pp),
        actual_report=ap.relative_to(ROOT).as_posix(), actual_report_sha256=sha(ap), actual_task_id=a['binding']['task_id'],
        required_scope=scope, strategy=p['strategy'], allocation='ACTIVE_EQUAL', required_financial_case_calls=4,
        independent_output_path='reports/fast_research/'+STEM+'_FINANCIAL.json', independent_binding_protocol=bp.relative_to(ROOT).as_posix(),
        terminal_cash_required=False, full_market_intent_sizing_independently_rebuilt=False,
        budgets=dict(new_owned_bytes=100000, wall_seconds=1800, peak_RSS_bytes=1500000000),
        prior_independent_helper_map=dict(path=str(prior_path), sha256=sha(prior_path)),
        metadata_helper=dict(path=OWN, sha256=sha(Path(__file__)), task_id=os.environ['COIN_TASK_ID']),
        producer_actual_closed_task=task, created_utc=now)
    assert plan['tolerances'] == dict(cash_USDT=1e-7, ratio=1e-10)
    write(bp, plan); run = STATE/'d065-active-allocation-financial-20261004-v1'; run.mkdir()
    (run/'ACTUAL_BINDING.json').write_bytes(bp.read_bytes())
else:
    # The actual economic comparison is implemented after market closure in a
    # separate small saved-ledger script; this helper never launches an account.
    raise ValueError('Use the saved-result diagnostic script after producer and independent closure')
print(json.dumps(dict(phase=args.phase, task_id=os.environ['COIN_TASK_ID'], created_utc=now)), flush=True)
