import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads((ROOT / p).read_text())
prefix = 'reports/fast_research/'
strategy = 'COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER'
extra = [
    'scripts/investment/public_donchian_hybrid.py', 'tests/test_public_donchian_hybrid.py',
    'tests/test_hybrid_native_fee_integration.py',
    prefix + 'PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_20261002_V1.json',
    prefix + 'BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V2.json',
    prefix + 'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json',
    prefix + 'BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json',
]
rules = {
    'PUBLIC': 'Fixed MIT prior20 Donchian + SMA200 closed2h entry, prior20 closed1h exit, long0.3; no new threshold/HPO',
    'priority': 'Held exit first at same stamp; next new closed2h may reenter; no same-stamp reentry',
    'causality': 'Only complete causal1h/2h candles with200 contiguous bars; any unavailable source makes paired fold NOT_EVALUABLE',
    'terminal': 'Common costed zero target; actual lots/capacity may leave marked dust',
    'interpretation': 'Joint exit lookback40h to20h and checking frequency change, not pure latency causal isolation',
}
for period in ('122D', '90D'):
    control_protocol = 'protocols/BYBIT_SPOT_2H_' + period + '_V2.json'
    control_report = prefix + 'BYBIT_SPOT_2H_' + period + '_ACTUAL_20261002_V2.json'
    spec = read(control_protocol)
    control = read(control_report)
    assert control['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
    assert control['source_bytes_unchanged'] and control['all_planned_ledgers_complete']
    assert control['completed_ledgers'] == 3 and len(control['folds'][0]['results']) == 3
    assert control['registration_start']['cost_assumptions'] == spec['costs']
    spec.pop('reused_target_inputs')
    spec.pop('preceding_failure', None)
    spec['contract_id'] = 'PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_V1'
    spec['created_before_new_economics_utc'] = datetime.now(UTC).isoformat()
    spec['primary_reference'] = strategy
    spec['primary_selection_reason'] = 'One fixed exit mechanism experiment against already accepted native-fee2h control; no search'
    spec['strategy_ids'] = [strategy]
    spec['strategy_rules'] = rules
    spec['smoke_test_path'] = 'tests/test_hybrid_native_fee_integration.py'
    spec['required_smoke_receipt'] = prefix + 'PUBLIC_DONCHIAN_HYBRID_NATIVE_PIPELINE_TINY_20261002_V1.json'
    spec['research_question'] = 'Can the fixed2h entry/1h exit preserve trend gains and reduce loss months after unchanged Bybit Non-VIP Spot costs?'
    spec['continuity_invariants']['source'] = 'Exact same accepted minute Parquet as native2h control; fresh fixedhybrid causal targets; own immutable physical Arrow read before engine'
    spec['limitations'].extend([
        'Hybrid2h entry/1h exit jointly changes prior20 physical exit lookback and evaluation frequency',
        'Faster exits can change subsequent entry opportunity set; entry rule equality does not imply identical entry timestamps',
        'Native strictflat round_trip_count may be0 because real positive dust persists; compare fills/notional/net positions and MTM',
        'Both complete windows are already seen development SCREENING; no independently unseen or longterm APR evidence',
    ])
    spec['paired_control_reference'] = dict(
        protocol_path=control_protocol, protocol_sha256=sha(ROOT / control_protocol),
        report_path=control_report, report_sha256=sha(ROOT / control_report),
        role='Saved accepted summary control only; no old market ledger rerun',
        strategy_id='COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER',
        same_fields=['common_config', 'costs', 'folds', 'warmup_days', 'reused_minute_input', 'fee_settlement', 'fee_profile_sha256'],
    )
    for name in [*extra, control_protocol, control_report]:
        spec['frozen_sources'][name] = sha(ROOT / name)
    for name, digest in spec['frozen_sources'].items():
        assert sha(ROOT / name) == digest, name
    destination = ROOT / ('protocols/PUBLIC_DONCHIAN_HYBRID_BYBIT_' + period + '_V1.json')
    with destination.open('x') as stream:
        json.dump(spec, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps(dict(protocol=str(destination), sha256=sha(destination), planned_new_accounts=3)))
