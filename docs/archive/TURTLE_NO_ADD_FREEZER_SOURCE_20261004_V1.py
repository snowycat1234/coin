"""Finite metadata freeze of one necessary case or the fixed noADD contrast."""
import argparse
import ast
from datetime import UTC,datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
PARENT='8288569c4ff673ebab3161ba17782ccec69c3411'


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def write(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2,allow_nan=False);stream.write('\n')


args=argparse.ArgumentParser();args.add_argument('--stage',choices=('test','research'),required=True);stage=args.parse_args().stage
assert os.environ.get('COIN_TASK_ID') and subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()==PARENT
archive=ROOT/'docs/archive/TURTLE_NO_ADD_FREEZER_SOURCE_20261004_V1.py'
if not archive.exists():archive.write_bytes(Path(__file__).read_bytes())
assert sha(archive)==sha(__file__)
old=json.loads((ROOT/'protocols/RSI2_SELECTIVE_SHORT_TARGET_SYNTHETIC_20261004_V1.json').read_bytes())
paths={p for p in old['frozen_sources'] if not p.startswith(('tests/','reports/','protocols/','docs/archive/RSI2_'))}
paths|={'scripts/investment/turtle_perpetual_bridge.py','scripts/investment/turtle_direction_mask.py',
 'scripts/investment/turtle_perpetual_research.py','scripts/investment/turtle_direction_research.py',
 'scripts/investment/turtle_direction_saved_comparison.py','scripts/investment/turtle_turnover_diagnostic.py',
 'scripts/investment/perpetual_risk_reduction_research_v2.py','scripts/investment/perpetual_303_research.py',
 'scripts/investment/perpetual_213_research.py','scripts/investment/perpetual_directional.py',
 'scripts/investment/perpetual_closing_exempt_account.py','src/quant/perpetual_account.py',
 'third_party/jesse_example_turtle_rules/turtle_rules_original.py',
 'third_party/jesse_example_turtle_rules/atr_indicator_original.py','third_party/jesse_example_turtle_rules/LICENSE',
 'third_party/jesse_example_donchian/donchian_indicator_original.py',
 'docs/archive/PERPETUAL_INDEPENDENT_REFERENCE_20261003_V1.py',
 'docs/archive/TURTLE_NO_ADD_FREEZER_SOURCE_20261004_V1.py','tests/test_turtle_no_add_direct.py'}
for name in paths:
    if name.endswith('.py'):ast.parse((ROOT/name).read_text())
source_hashes={p:sha(ROOT/p) for p in sorted(paths)}
if stage=='test':
    spec=dict(old)
    for key in ('rsi_parameters','strategy_rules','direction_mode','pre_change_daily_adapter'):spec.pop(key,None)
    name='TURTLE_NO_ADD_SYNTHETIC_20261004_V1'
    spec.update(contract_id='D060_NORMAL_TURTLE_NO_ADD_SYNTHETIC_V1',git_commit=PARENT,
        created_utc=datetime.now(UTC).isoformat(),freeze_task_id=os.environ['COIN_TASK_ID'],
        frozen_sources=source_hashes,tests=['tests/test_turtle_no_add_direct.py'],
        calculation_rules=dict(default=True,no_add_changes_only_proactive_increase=True,
            retains_entry_fragments_exit_stop_risk=True,cash_tolerance_USDT=1e-7,ratio_tolerance=1e-10,
            ordered_N_covariance_and_shared_wallet=True,snapshot_policy_order_identity=True),
        run_dir=str(STATE/'d060-turtle-no-add-synthetic-20261004-v1'),
        output_path='reports/fast_research/'+name+'.json',
        test_scope='ONE_NEW_NORMAL_EVENT_CASE_NO_MARKET_OLD_TESTS_OR_QA',models_fit=0,
        old_tests_replayed=False)
    out=ROOT/'protocols'/f'{name}.json'
else:
    name='TURTLE_NO_ADD_RESEARCH_20261004_V1'
    testpath=ROOT/'reports/fast_research/TURTLE_NO_ADD_SYNTHETIC_20261004_V1.json'
    actual=json.loads(testpath.read_bytes());assert actual['test_exit_code']==0 and actual['source_bytes_unchanged']
    task=json.loads((STATE/'task-progress'/('task-'+actual['binding']['task_id']+'.json')).read_bytes())
    assert task['status']=='completed' and task['exit_code']==0
    paths.add('scripts/investment/audit_turtle_direction_research.py')
    # Current independent finance reuses these already accepted helpers; no producer-loop extraction.
    paths|=set(json.loads((ROOT/'reports/fast_research/RSI2_SELECTIVE_SHORT_SEPNOV91_INDEPENDENT_20261004_V1.json').read_bytes())['binding']['source_hashes'])
    source_hashes={p:sha(ROOT/p) for p in sorted(paths)}
    def proof(path,status):return dict(path=path,sha256=sha(ROOT/path),required_status=status)
    spec=dict(contract_id='D060_FIXED303D_TURTLE_NO_ADD_CONDITIONAL_V1',parent_commit=PARENT,
        experiment_id='D060_TURTLE_SINGLE_LAYER_FIXED303D',strategy_id='COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER',
        direction_mode='LONG_ONLY',variants=dict(PYRAMID4=True,SINGLE_LAYER=False),initial_capital_USDT=10000,
        source_hashes=source_hashes,
        input_manifest=proof('reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json',
            'PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'),
        warmup_acceptance=proof('reports/fast_research/TURTLE_4H_WARMUP_SOURCE_INDEPENDENT_20261003_V1.json',
            'PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY'),
        saved_original=proof('reports/fast_research/TURTLE_DIRECTION_ABLATION_ACTUAL_20261003_V1.json',
            'COMPLETE_D049_EIGHT_TURTLE_DIRECTION_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'),
        required_test=proof(testpath.relative_to(ROOT).as_posix(),actual['status']),
        cost_scenarios=[dict(id='BASE27',half_spread_bps=4,slippage_bps=4,roundtrip_bps=27),
            dict(id='STRESS43',half_spread_bps=8,slippage_bps=8,roundtrip_bps=43)],
        unit_scenarios=[dict(id='RAW_AS_FRACTION',scale=1.0),dict(id='RAW_AS_PERCENT',scale=.01)],
        budget=dict(owned_bytes=250000000,wall_seconds=1800,peak_RSS_bytes=3000000000),
        total_budget=dict(new_accounts=8,financial_calls=8,model_fits=0,HPO=0,new_downloads=0,
            new_source_QA_calls=0,total_STATE_bytes=700000000,shared_RAM_bytes=5000000000),
        question='Does suppressing proactive Turtle ADD improve full-capital net economics while mandatory exits/risk remain?',
        data_role='SEEN_DEVELOPMENT_COMPLETE303D_NOT_INDEPENDENT',
        default_migration_gate='ALL4_SAVED_TARGET_TRADE_FUND_MINUTE_NAV_POSITION_SEMANTICS_AT_ORIGINAL_TOLERANCES',
        created_utc=datetime.now(UTC).isoformat(),freeze_task_id=os.environ['COIN_TASK_ID'])
    out=ROOT/'protocols'/f'{name}.json'
write(out,spec)
print(json.dumps(dict(stage=stage,protocol=str(out),sha256=sha(out),source_count=len(source_hashes),
    market_arrays_read=False,tests_executed=0,model_fits=0)),flush=True)
