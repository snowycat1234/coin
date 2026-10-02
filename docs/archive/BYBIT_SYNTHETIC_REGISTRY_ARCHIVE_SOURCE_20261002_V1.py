import hashlib, json, shutil, sys
from pathlib import Path
root = Path('/mnt/d/codex/coin'); sys.path.insert(0, str(root))
from scripts.research_v8.registry import FIELDS, append_event
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
prefix = 'reports/fast_research/'
for version in (1, 2):
    name = prefix + f'BYBIT_SPOT_FEE_ASSET_TINY_20261002_V{version}.json'
    report = json.loads((root / name).read_text()); binding = report['binding']
    task = Path('/home/xflops/coin-state/task-progress') / ('task-' + binding['task_id'] + '.json')
    actual = json.loads(task.read_text())
    assert actual['exit_code'] == (1 if version == 1 else 0)
    event = dict.fromkeys(FIELDS)
    identifier = f'BYBIT-FEE-ASSET-UNIT-20261002-V{version}'
    event.update(experiment_id=identifier, git_commit=binding['git_commit'],
        data_manifest_hash=binding['source_hashes']['tests/test_bybit_spot_adapter.py'],
        protocol_hash=binding['source_hashes']['protocols/BYBIT_SPOT_RECEIVED_ASSET_ADAPTER_V1.json'],
        feature_set='SYNTHETIC_FEE_ASSET_BALANCES_NO_MARKET_PRICE_IO', labels='NONE', model_family='NONE',
        hyperparameters={'fit': 0, 'test_selection': binding['exact_test_command']}, seed='NOT_APPLICABLE',
        thresholds={'no_change_to_cash_qty_fee_cap_guard': True}, cost_assumptions='Bybit ordinary Spot10bp received asset',
        all_folds='SYNTHETIC_ONLY', success_failure='UNKNOWN',
        reason_for_next_experiment='Native received-asset compatibility before unchanged2h economics',
        result_influenced_later_choice=True, source_hashes=binding['source_hashes'],
        exact_command=binding['exact_command'], actual_task_path=str(task), actual_task_sha256=sha(task),
        actual_outer_exit=actual['exit_code'], market_inputs_read=False, models_fit=0,
        registration_timing='POST_RECORDED_FROM_PRESERVED_PREBOUND_START_NOT_BACKDATED')
    append_event(root / 'reports/experiment_registry.jsonl', {**event, 'event_id':identifier + ':START',
        'event_type':'OPERATIONAL_START_POST_RECORDED', 'success_failure':'PREBOUND_START_SAVED_BEFORE_ACTUAL_CHILD'})
    append_event(root / 'reports/experiment_registry.jsonl', {**event, 'event_id':identifier + ':RESULT',
        'event_type':'OPERATIONAL_RESULT', 'success_failure':report['status'], 'artifact_path':name, 'artifact_sha256':sha(root / name)})
    if version == 1:
        for source, target in [('scripts/investment/bybit_spot_adapter.py', 'BYBIT_SPOT_ADAPTER_FAILED_TINY_SOURCE_20261002_V1.py'),
            ('tests/test_bybit_spot_adapter.py', 'BYBIT_SPOT_ADAPTER_FAILED_TINY_TEST_SOURCE_20261002_V1.py')]:
            old = Path(report['run_dir']) / 'source-snapshot' / source
            assert sha(old) == binding['source_hashes'][source]
            with (root / 'docs/archive' / target).open('xb') as f:f.write(old.read_bytes())
for source, target in [('bybit_replay_protocol_env_repair_20261002_v2.py', 'BYBIT_FEE_REPLAY_PROTOCOL_ENV_REPAIR_SOURCE_20261002_V2.py')]:
    with (root / 'docs/archive' / target).open('xb') as f:f.write((root / '.cache' / source).read_bytes())
print('Actual failure and selective recovery recorded; source archives kept; zero new tests or market reads')
