import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads((ROOT / p).read_text())
prefix = 'reports/fast_research/'
strategy = 'COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER'
unit = prefix + 'BYBIT_SPOT_FEE_ASSET_COMPOSITE_ACCEPTANCE_20261002_V1.json'
assert (ROOT / unit).is_file(), 'Need combined actual synthetic acceptance first'
extra = [
    'src/quant/execution.py', 'scripts/investment/bybit_spot_adapter.py',
    'scripts/investment/compare_simple_strategies.py', 'tests/test_bybit_spot_adapter.py',
    'tests/test_investment_bybit_pipeline.py', 'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
    'protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json', unit,
    prefix + 'BYBIT_SPOT_FEE_ASSET_TINY_20261002_V1.json',
    prefix + 'BYBIT_SPOT_FEE_ASSET_TINY_20261002_V2.json',
]
for period, old_protocol, old_report, old_audit in [
    ('122D', 'PUBLIC_DONCHIAN_2H_122D_V1.json', 'PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json',
        'PUBLIC_DONCHIAN_2H_122D_INDEPENDENT_ACTUAL_AUDIT_20261002_V1.json'),
    ('90D', 'PUBLIC_STRATEGY_CONTINUOUS_90D_V2.json', 'PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json',
        'PUBLIC_STRATEGY_CONTINUOUS_90D_INDEPENDENT_ACTUAL_AUDIT_20261002_V2_R2.json')]:
    spec = read('protocols/' + old_protocol)
    parent = read(prefix + old_report)
    audit = read(prefix + old_audit)
    assert parent['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
    assert parent['source_bytes_unchanged'] and parent['all_planned_ledgers_complete']
    fold = spec['folds'][0]['id']
    targets = Path(parent['run_dir']) / (fold + '-' + strategy)
    prior = [r for r in audit['ledgers'] if r['fold'] == fold and r['strategy'] == strategy]
    assert len(prior) == 3
    reference = {name: dict(path=str(targets / name), sha256=sha(targets / name))
        for name in ('targets.parquet', 'intent_calendar.parquet', 'target_receipt.json')}
    reference['accepted_audit'] = dict(path=prefix + old_audit, sha256=sha(ROOT / (prefix + old_audit)))
    expected = {key: reference[name]['sha256'] for key, name in
        (('target_sha256', 'targets.parquet'), ('intent_sha256', 'intent_calendar.parquet'), ('receipt_sha256', 'target_receipt.json'))}
    assert all(r['target_bindings'] == expected for r in prior)
    for key in list(spec):
        if key.startswith('reused_reference') or key in ('resource_adapter', 'preceding_failed_receipt',
            'failure_compatibility_repair', 'smoke_pytest_expression', 'reuse_invariants'):
            del spec[key]
    spec.update(contract_id='BYBIT_SPOT_2H_' + period + '_V1',
        classification='PREVIOUSLY_SEEN_BINANCE_PRICE_BYBIT_CURRENT_FEE_RULE_COUNTERFACTUAL_SCREENING',
        created_before_new_economics_utc=datetime.now(UTC).isoformat(),
        fee_settlement='BYBIT_SPOT_RECEIVED_ASSET_V1',
        market_type='CRYPTO_SPOT_NO_BORROW_OR_LEVERAGE',
        fee_profile_path='protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json',
        fee_profile_sha256=sha(ROOT / 'protocols/BYBIT_NONVIP_FEE_REFERENCE_20261002.json'),
        primary_selection_reason='Fixed native received-asset compatibility before strategy changes; original2h signal bytes reused',
        strategy_ids=[strategy], planned_ledgers=3, maximum_new_owned_bytes=512000000,
        smoke_test_path='tests/test_investment_bybit_pipeline.py',
        required_smoke_receipt=prefix + 'BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V1.json',
        reused_minute_input=dict(report_path=prefix + old_report, report_sha256=sha(ROOT / (prefix + old_report)),
            **{k: parent['minute_source'][k] for k in ('path', 'sha256')}),
        reused_target_inputs={fold + ':' + strategy: reference},
        research_question='How much does fixed ordinary Bybit Spot received-asset settlement change existing fixed2h economics? No new signals, periods, HPO or risk relaxation',
        return_reporting='Separate continuous122day/90day accounts; no stitching or long-term APR qualification',
    )
    spec['costs']['cost_booking'] = 'Once per fill; buy base fee net receipt at fillmid, sell quote fee; gross order spread/slippage; no fee discount'
    spec['strategy_rules'] = {'PUBLIC': 'Byte-identical accepted2h MIT hooks/targets; settlement only. No new parameter or period selection'}
    spec['continuity_invariants']['fees'] = 'Current Bybit global Non-VIP Spot10bp/side received asset; counterfactual rule on Binance minute proxy, not actual historical Bybit fees'
    spec['continuity_invariants']['source'] = 'Exact accepted derivative Parquet and2h target artifacts, no raw price QA or signals regeneration'
    spec['limitations'].extend(['Data venue remains Binance; Bybit native prices, filters and regional/account fees unverified',
        '2026 public Bybit fees used as fixed counterfactual, not proven historical account fee',
        'Native inventory contains positive sublot dust; marked terminal residuals never deleted',
        'Gross diagnostic uses same NET_RECEIVED position deltas; not fee-free gross order inventory'])
    for name in [*extra, prefix + old_report, prefix + old_audit]:
        spec['frozen_sources'][name] = sha(ROOT / name)
    for name, digest in spec['frozen_sources'].items():
        assert sha(ROOT / name) == digest, name
    destination = ROOT / ('protocols/BYBIT_SPOT_2H_' + period + '_V1.json')
    with destination.open('x') as stream:
        json.dump(spec, stream, indent=2, ensure_ascii=False, allow_nan=False); stream.write('\n')
    print(json.dumps(dict(protocol=str(destination), sha256=sha(destination), planned_accounts=3)))
