"""Freeze necessary settlement case and two-case replay; metadata only."""
import argparse, hashlib, json, os
from datetime import UTC, datetime
from pathlib import Path
from scripts.investment import perpetual_settlement_replay as replay
R=Path('/mnt/d/codex/coin');S=Path('/home/xflops/coin-state')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def reference(name):
    v=read(R/name);return dict(path=name,sha256=sha(R/name),required_status=v['status'])
def closed(report):
    t=read(S/'task-progress'/('task-'+report['binding']['task_id']+'.json'))
    assert t['status']=='completed' and t['exit_code']==0
p=argparse.ArgumentParser();p.add_argument('--phase',choices=['test','replay'],required=True);a=p.parse_args()
old=read(R/'protocols/PERPETUAL_CONTROLLER_TEST_20261003_V2.json')
names=set(old['frozen_sources']);names.update(['docs/archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py',
    'tests/test_perpetual_settlement.py','scripts/bounded.sh','scripts/with_task_progress.sh','scripts/task_progress_run.py'])
assert sha(R/'docs/archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py')=='2bae17b6351dec5c632e3af42fed2a6a5cf91293dba0a08c06a7aa81f4df58fb'
assert sha(R/'scripts/investment/perpetual_directional.py')=='547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3'
pins={n:sha(R/n) for n in sorted(names)}
archive=R/'docs/archive/PERPETUAL_SETTLEMENT_PROTOCOL_FREEZER_20261003_V1.py'
if not archive.exists():
    with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
assert sha(archive)==sha(__file__)
if a.phase=='test':
    value=dict(classification='D040_NEW_EXACT_SETTLEMENT_FALSE_BANKRUPTCY_SYNTHETIC_ONLY',created_utc=datetime.now(UTC).isoformat(),
        frozen_sources=pins,tests=['tests/test_perpetual_settlement.py'],
        calculation_rules=dict(full_close='RELEASE_ORIGINAL_BALANCE_EXACT_IDENTITY_NOT_EPSILON',
            debit='NEGATIVE_INPUT_INVARIANT_REJECTED_REAL_INSUFFICIENCY_STILL_DEBT',
            preserved_old_source_sha256=pins['docs/archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py'],
            required_old_actual_false_halt_reproduction=True,old_green_tests_replayed=False,orders=False,locked=False,market_inputs=False),
        fee_profile=old['fee_profile'])
    path=R/'protocols/PERPETUAL_SETTLEMENT_TEST_20261003_V1.json'
else:
    actual_ref=reference('reports/fast_research/PERPETUAL_DIRECTIONAL_ACTUAL_20261003_V1.json')
    independent_ref=reference('reports/fast_research/PERPETUAL_DIRECTIONAL_INDEPENDENT_AUDIT_20261003_V1.json')
    test_ref=reference('reports/fast_research/PERPETUAL_SETTLEMENT_TEST_ACTUAL_20261003_V1.json')
    for v in (actual_ref,independent_ref,test_ref):closed(read(R/v['path']))
    test=read(R/test_ref['path']);assert test['test_exit_code']==0 and test['source_bytes_unchanged']
    original=read(R/'protocols/PERPETUAL_DIRECTIONAL_20261003_V1.json')
    names.update(original['frozen_sources']);names.update([actual_ref['path'],independent_ref['path'],test_ref['path'],
        'scripts/investment/perpetual_settlement_replay.py','protocols/PERPETUAL_SETTLEMENT_TEST_20261003_V1.json',
        'protocols/PERPETUAL_DIRECTIONAL_20261003_V1.json'])
    pins={n:sha(R/n) for n in sorted(names)}
    value=dict(contract_id=replay.CONTRACT,created_utc=datetime.now(UTC).isoformat(),
        classification='CORRECTNESS_ONLY_TWO_PRIOR_FALSE_HALTS_SEEN_DEVELOPMENT',selectors=replay.SELECTORS,
        rules=replay.reuse.RULES,cost=replay.reuse.COSTS[0],unit=replay.reuse.UNITS[1],frozen_sources=pins,
        original_actual=actual_ref,original_independent=independent_ref,original_report=actual_ref,original_audit=independent_ref,
        required_settlement_test=test_ref,required_smoke_receipt=test_ref,input_manifest=original['input_manifest'],
        trade_source_acceptance=original['trade_source_acceptance'],
        preserved_original_account=dict(path='docs/archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py',
            sha256=pins['docs/archive/PERPETUAL_ACCOUNT_PRE_SETTLEMENT_FIX_SOURCE_20261003_V1.py']),
        run_dir=str(S/'d040-perpetual-settlement-replay-20261003-v1'),
        output_path='reports/fast_research/PERPETUAL_SETTLEMENT_REPLAY_ACTUAL_20261003_V1.json',
        budgets=dict(new_owned_bytes=60_000_000,peak_RSS_bytes=1_500_000_000,wall_seconds=1200),
        environment=original['environment'],original_other_thirty_cases_replayed=False,
        no_signal_cost_risk_unit_or_date_change=True,locked_consumed=False,orders_sent=0)
    path=R/'protocols/PERPETUAL_SETTLEMENT_REPLAY_20261003_V1.json'
write(path,value)
print(json.dumps(dict(protocol=str(path),sha256=sha(path),source_pins=len(pins),market_arrays_read=False,task_id=os.environ['COIN_TASK_ID'])))
