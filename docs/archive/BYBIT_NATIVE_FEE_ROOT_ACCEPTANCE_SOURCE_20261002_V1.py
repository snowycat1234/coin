import hashlib, json, shutil, subprocess, sys
from datetime import UTC, datetime
from pathlib import Path

root = Path('/mnt/d/codex/coin'); sys.path.insert(0, str(root))
from scripts.research_v8.registry import FIELDS, append_event
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
prefix = 'reports/fast_research/'
proofs = {
    'BYBIT_SPOT_FEE_ASSET_TINY_20261002_V1.json': '494994ec5a5ad52216936b0ce4388b7dc0d30ca943a96214c548be98a2941607',
    'BYBIT_SPOT_FEE_ASSET_TINY_20261002_V2.json': '933236cc26141df1f4b6cc9b763114baa45ce7cce4e474e12b7b49d909abd04c',
    'BYBIT_SPOT_FEE_ASSET_COMPOSITE_ACCEPTANCE_20261002_V1.json': '850b8a2e984bd00d33c396dca43af6b6a2f0d55c327eff3c29fc2f238f63d2b0',
    'BYBIT_SPOT_2H_122D_ACTUAL_20261002_V2.json': '53447ac3722829cb5c4db12f5b469b100edb20c05bbb6e9c83f29bce5138bee3',
    'BYBIT_SPOT_2H_90D_ACTUAL_20261002_V2.json': '329f9f923ed4fd8223e2e267a200c2e67036c8ce4f82a7fef0027efdd3b7960a',
    'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json': 'bcba15e8df42270870c49a4f1aefa902fc69b037400a87dbe1e957b47643bb4f',
    'BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json': '70fc1568e51019d2c13abb42eb7fd844a58f9c39e77f0ff27278f1b5f7d94c6f',
}
for name in ('BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V1.json', 'BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V2.json'):
    proofs[name] = sha(root / (prefix + name))
for name, digest in proofs.items():assert sha(root / (prefix + name)) == digest, name
read = lambda n: json.loads((root / (prefix + n)).read_text())
unit = read('BYBIT_SPOT_FEE_ASSET_COMPOSITE_ACCEPTANCE_20261002_V1.json')
assert unit['status'] == 'PASS_FIVE_SYNTHETIC_CASES_COMPOSITE_NOT_SINGLE_FRESH_SUITE'
assert unit['v1_passed_cases_reused'] == 3 and unit['v2_failed_cases_recovered'] == 2
failure = read('BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V1.json')
assert failure['status'] == 'FAIL_SIMPLE_STRATEGY_COMPARISON' and failure['reason'] == 'At most2 Polars threads'
assert not failure['market_inputs_read'] and not failure['folds'] and 'test_exit_code' not in failure
tiny = read('BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V2.json')
assert tiny['status'] == 'PASS_SIMPLE_COMPARISON_SYNTHETIC_NOT_MARKET_RESULT'
assert tiny['test_exit_code'] == 0 and tiny['junit_counts'] == dict(tests=4, errors=0, failures=0, skipped=0)
audit = read('BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json')
assert audit['status'].startswith('PASS_') and audit['completed_ledgers_verified'] == 6
assert len(audit['ledgers']) == 6
accounts, source_hashes, task_receipts, scans, outputs = [], {}, [], [], []
for period, old in [('122D', 'PUBLIC_DONCHIAN_2H_122D_ACTUAL_20261002_V1.json'),
    ('90D', 'PUBLIC_STRATEGY_CONTINUOUS_90D_ACTUAL_20261002_V2.json')]:
    name = 'BYBIT_SPOT_2H_' + period + '_ACTUAL_20261002_V2.json'
    actual = read(name); prior = read(old)
    assert actual['status'] == 'COMPLETE_ACTUAL_PROXY_STRATEGY_SCREENING'
    assert actual['completed_ledgers'] == actual['planned_ledgers'] == 3 and actual['source_bytes_unchanged']
    assert actual['all_planned_ledgers_complete'] and actual['fee_settlement'] == 'BYBIT_SPOT_RECEIVED_ASSET_V1'
    assert actual['accepted_smoke_sha256'] == proofs['BYBIT_SPOT_COMMON_PIPELINE_TINY_20261002_V2.json']
    assert not actual['raw_normalized_market_files_read'] and not actual['locked_consumed'] and actual['orders_sent'] == actual['market_models_fit'] == 0
    task = Path('/home/xflops/coin-state/task-progress') / ('task-' + actual['binding']['task_id'] + '.json')
    tv = json.loads(task.read_text()); assert tv['status'] == 'completed' and tv['exit_code'] == 0
    task_receipts.append(dict(path=str(task), sha256=sha(task), actual_exit=0, task_id=actual['binding']['task_id'],
        actual_host_session=50234 if period == '122D' else 97035))
    fold = actual['folds'][0]
    assert fold['minute_input_format'] == 'IMMUTABLE_ARROW_IPC_FILE_READ_BEFORE_SIGNALS_AND_EXECUTION'
    assert sha(fold['minute_input_path']) == fold['minute_input_sha256']
    for name, digest in actual['binding']['source_hashes'].items():
        assert sha(root / name) == digest, name
        assert name not in source_hashes or source_hashes[name] == digest
        source_hashes[name] = digest
    scans.append(actual['disk']); outputs.append(dict(period=period, run_dir=actual['run_dir'], owned_bytes=actual['owned_bytes'],
        peak_RSS_bytes=actual['orchestrator_peak_RSS_bytes'], elapsed_seconds=actual['elapsed_seconds']))
    for row in fold['results']:
        oldrow = [r for f in prior['folds'] for r in f['results'] if r['strategy'] == row['strategy'] and r.get('spread_bps') == row['spread_bps']]
        assert len(oldrow) == 1
        new, oldsummary = row['summary'], oldrow[0]['summary']
        accounts.append(dict(period=period, nominal_roundtrip_bps=row['nominal_roundtrip_bps'],
            new_net_return=new['total_return'], old_quote_net_return=oldsummary['total_return'],
            delta_net_USDT=(new['total_return'] - oldsummary['total_return']) * 10000,
            delta_net_basis_points=(new['total_return'] - oldsummary['total_return']) * 10000,
            gross_shadow_USDT=new['gross_cash_PnL_same_quantities'], fees_USDT_mid=new['fees'],
            spread_USDT=new['spread_cost'], slippage_USDT=new['slippage_cost'],
            minute_MDD=new['max_observed_minute_MDD'], terminal_marked_notional=new['terminal_marked_notional'],
            trade_count=new['trade_count'], turnover=new['turnover'],
            strategy_and_targets_unchanged=True, old_quote_accounts_rerun=False))
latest = max(scans, key=lambda v: datetime.fromisoformat(v['scan_finished_utc']))
assert latest['total_bytes'] == latest['project_bytes'] + latest['wsl_vhd_bytes'] < 32000000000
resource = actual['resources']; assert resource['ram_limit_bytes'] <= 5000000000 and resource['swap_bytes'] == 0 and not resource['gpu_used']
assert resource['ram_peak_bytes'] <= resource['ram_limit_bytes']
for name, digest in unit['current_source_hashes'].items():
    assert sha(root / name) == digest
    assert name not in source_hashes or source_hashes[name] == digest
    source_hashes[name] = digest
for name in ('scripts/investment/public_donchian_hybrid.py', 'tests/test_public_donchian_hybrid.py',
    'reports/fast_research/PUBLIC_DONCHIAN_HYBRID_TARGET_TINY_20261002_V1.json'):
    source_hashes[name] = sha(root / name)
out = root / (prefix + 'BYBIT_SPOT_NATIVE_FEE_ROOT_MODULE_ACCEPTANCE_20261002_V1.json')
receipt = dict(status='ACCEPT_BYBIT_SPOT_FEE_ACCOUNTING_ONLY_NO_PROFITABLE_CANDIDATE', created_utc=datetime.now(UTC).isoformat(),
    git_commit_before_module=subprocess.check_output(['git', 'rev-parse', 'HEAD'],cwd=root,text=True).strip(),
    source_hashes=source_hashes, verified_prior_files={prefix+n:v for n,v in proofs.items()},
    independent_audit_sha256=proofs['BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json'],
    actual_task_bindings=task_receipts, actual_outputs=outputs, accounts=accounts,
    source_reuse='Exact accepted derivative Parquet and2h signals; no raw source QA, downloads or old economic replay',
    acceptance='Native fee asset rule, synthetic cash/inventory checks and six actual proxy account ledgers accepted; economic findings only SCREENING',
    preserved_failures=['Two summary float cancellation failures with3PASS reused and2cases recovered',
        'Common invocation rejected missing thread env before tests/disk/market',
        'Independent122 financial checks complete; checker expected variable collision then failed source guard; metadata recovery plus only90 financial checks, not a single freshsix pass'],
    current_profitable_main='NONE', candidate_status='NO_QUALIFIED_CANDIDATE',
    decision='Adopt Bybit ordinary Spot received-asset settlement; cost-only explanation rejected, proceed one fixed hybrid at unchangedcosts/risk',
    native_Bybit_market_execution_proven=False, current_fee_counterfactual_on_Binance_history=True,
    locked_consumed=False, real_orders=0, models_fit=0, GPU=0, entire_D_disk_latest_completed_scan=latest, resources=resource,
    next_experiment='Only fixed2h entry/1h exit, same native fee account, two separate seen periods; no HPO or evidence stitching',
    next_hybrid_economic_status='NOT_STARTED_TARGET_SYNTHETIC_ONLY', helper_source_sha256=sha(__file__))
with out.open('x') as f:json.dump(receipt,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
gitproof = dict(receipt)
gitproof['source_hashes'] = {n:v for n,v in source_hashes.items() if n != 'state/dataset_lock.json'}
gitproof['runtime_excluded_from_git'] = dict(path='state/dataset_lock.json', sha256=source_hashes['state/dataset_lock.json'],
    verified_actual_runtime=True, reason='Market source lock remains runtime metadata; root acceptance retains complete binding')
gp = root / 'reports/GITHUB_BYBIT_NATIVE_FEE_SOURCE_BINDING_20261002_V1.json'
with gp.open('x') as f:json.dump(gitproof,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
for source, target in [('bybit_native_fee_root_acceptance_20261002_v1.py','BYBIT_NATIVE_FEE_ROOT_ACCEPTANCE_SOURCE_20261002_V1.py'),
    ('bybit_synthetic_registry_archive_20261002_v1.py','BYBIT_SYNTHETIC_REGISTRY_ARCHIVE_SOURCE_20261002_V1.py')]:
    with (root / 'docs/archive' / target).open('xb') as f:f.write((root / '.cache' / source).read_bytes())
event = dict.fromkeys(FIELDS); event.update(experiment_id='BYBIT-SPOT-NATIVE-FEE-MODULE-20261002-V1',
    event_id='BYBIT-SPOT-NATIVE-FEE-MODULE-20261002-V1:RESULT', event_type='OPERATIONAL_RESULT',
    git_commit=receipt['git_commit_before_module'], data_manifest_hash=source_hashes['state/dataset_lock.json'],
    protocol_hash=source_hashes['protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json'], feature_set='FIXED_PUBLIC2H_SAME_SIGNALS_NATIVE_FEE_ASSET',
    labels='NONE', model_family='NONE', hyperparameters='NO_FIT_OR_PARAMETER_CHANGE', seed='NOT_APPLICABLE',
    thresholds='UNCHANGED_FIXED_RULES', cost_assumptions='Bybit NonVIP Spot10bp+fixedspread2/4/8+slip4bpside',
    all_folds=['CONT122','CONT90'], success_failure=receipt['status'],
    reason_for_next_experiment=receipt['next_experiment'], result_influenced_later_choice=True,
    artifact_path=str(out.relative_to(root)), artifact_sha256=sha(out), source_hashes=source_hashes)
append_event(root/'reports/experiment_registry.jsonl',event)
print(json.dumps(dict(status=receipt['status'], output=str(out),sha256=sha(out),accounts=accounts),ensure_ascii=False))
