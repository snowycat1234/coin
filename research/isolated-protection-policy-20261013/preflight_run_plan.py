"""Read-only binding/resource preflight for the 11 preregistered cases.

No simulator is instantiated and no wallet or output state is written. A separate
reviewed runner and fresh state directories are required after parent GO.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil

import numpy as np

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / 'RUN_MANIFEST.json'
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
DAY = 86_400_000_000
EXPECTED_CASES = {
    (2023, 'STATIC50'), (2023, 'SMA200_10PCT'), (2023, 'COMBINED'),
    (2024, 'CS_MATCHED'), (2024, 'VOL_MATCHED'), (2024, 'STATIC50'),
    (2024, 'SMA200_10PCT'), (2024, 'EXACTHALF'),
    (2025, 'STATIC50'), (2025, 'SMA200_10PCT'), (2025, 'COMBINED')}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(manifest_path: Path, workspace_root: Path) -> dict:
    freeze = json.loads((HERE / 'FREEZE.json').read_text())
    for key, path in [('protocol', HERE / 'PROTOCOL.json'),
                      ('adapter', HERE / 'protective_policy.py'),
                      ('synthetic_tests', HERE / 'test_policy_synthetic.py'),
                      ('run_manifest', manifest_path),
                      ('read_only_preflight', HERE / 'preflight_run_plan.py')]:
        if sha(path) != freeze['SHA256'][key]:
            raise ValueError(f'Frozen {key} bytes differ')
    protocol = json.loads((HERE / 'PROTOCOL.json').read_text())
    manifest = json.loads(manifest_path.read_text())
    if (manifest['policy_id'] != 'isolated_half_equity_full_exit_v1'
            or protocol['policy_id'] != manifest['policy_id']
            or {(row['year'], row['arm']) for row in manifest['cases']} != EXPECTED_CASES
            or len(manifest['cases']) != len(EXPECTED_CASES)
            or any(row['case_id'] != f"Y{row['year']}_{row['arm']}"
                   for row in manifest['cases'])
            or manifest['resource_plan']['historical_run_gate'] != 'PARENT_REVIEW_AND_GO_REQUIRED'):
        raise ValueError('Unexpected registered case set or missing GO gate')
    verified_sources = set()
    verified_targets = set()
    cases = []
    for case in manifest['cases']:
        year = case['year']
        if year not in (2023, 2024, 2025):
            raise ValueError('Out-of-scope year')
        if (case['source_index_SHA256'] != protocol['comparison_plan']['source_index_SHA256'][str(year)]
                or case['target_archive_SHA256'] != protocol['comparison_plan']['target_archive_SHA256'][str(year)]):
            raise ValueError(f"Protocol source/target identity differs: {case['case_id']}")
        source = workspace_root / case['source_index_local_locator']
        target = workspace_root / case['target_archive_local_locator']
        if sha(source) != case['source_index_SHA256'] or sha(target) != case['target_archive_SHA256']:
            raise ValueError(f"Bound source or target differs: {case['case_id']}")
        index = json.loads(source.read_text())
        if (index['calendar'] != case['calendar'] or index['symbol_order'] != list(SYMBOLS)
                or index.get('minutes_per_asset', sum(row['minutes'] for row in index['months']))
                != (case['calendar'][1] - case['calendar'][0]) // 60_000_000
                or index['days'] != (366 if year == 2024 else 365)):
            raise ValueError(f"Source calendar differs: {case['case_id']}")
        if source not in verified_sources:
            for row in index['months']:
                month = source.parent / 'months' / f"{row['month']}.npz"
                if month.stat().st_size != row['source_NPZ_bytes'] or sha(month) != row['source_NPZ_SHA256']:
                    raise ValueError(f"Source month differs: {month}")
            for name in ('DAILY.json', 'EVENTS.json'):
                path = source.parent / name
                if path.stat().st_size != index['files'][name]['bytes'] or sha(path) != index['files'][name]['SHA256']:
                    raise ValueError(f"Source metadata differs: {path}")
            verified_sources.add(source)
        if target not in verified_targets:
            verified_targets.add(target)
        with np.load(target, allow_pickle=False) as archive:
            if (tuple(archive['symbol_order']) != SYMBOLS
                    or not np.array_equal(archive['decision_us'], np.arange(
                        case['calendar'][0], case['calendar'][1], DAY, dtype=np.int64))):
                raise ValueError(f"Target calendar differs: {case['case_id']}")
            array = archive[case['arm']]
            if (array.dtype.str != case['target_dtype'] or list(array.shape) != case['target_shape']
                    or not np.isfinite(array).all()
                    or hashlib.sha256(array.tobytes(order='C')).hexdigest()
                    != case['target_array_SHA256']):
                raise ValueError(f"Target array differs: {case['case_id']}")
            if np.max(np.abs(array)) > .3 + 1e-12 or np.max(np.abs(array).sum(axis=1)) > .6 + 1e-12:
                raise ValueError(f"Original target cap violation: {case['case_id']}")
            if case['arm'] in ('COMBINED', 'EXACTHALF') and not np.array_equal(
                    array, .5 * archive['STATIC50'] + .5 * archive['SMA200_10PCT']):
                raise ValueError(f"Frozen half-sum differs: {case['case_id']}")
            if year in (2023, 2025) and case['arm'] != 'COMBINED':
                original = workspace_root / case['standalone_original_target_local_locator']
                expected = protocol['comparison_plan']['standalone_original_archive_SHA256'][str(year)][case['arm']]
                if (case['standalone_original_target_SHA256'] != expected
                        or sha(original) != expected
                        or case['standalone_original_array_key'] != case['arm']):
                    raise ValueError(f"Standalone original differs: {case['case_id']}")
                with np.load(original, allow_pickle=False) as standalone:
                    if (tuple(standalone['symbol_order']) != SYMBOLS
                            or not np.array_equal(standalone['decision_us'], archive['decision_us'])
                            or not np.array_equal(standalone[case['arm']], array)):
                        raise ValueError(f"Standalone target array differs: {case['case_id']}")
        cases.append(case['case_id'])
    resource = manifest['resource_plan']
    free = shutil.disk_usage(workspace_root).free
    required = (resource['disk_reserve_bytes']
                + resource['initial_parallel_wallet_limit'] * resource['per_case_state_max_bytes']
                + resource['per_case_state_max_bytes'])
    # The extra case budget leaves room for concurrent packaging/checkpoint
    # overhead. RAM/cgroup limits must be separately verified by the launcher.
    return {'status': 'INPUTS_BOUND_RESOURCE_RECHECK_REQUIRED_BEFORE_GO',
            'policy_id': manifest['policy_id'], 'case_ids': cases,
            'source_indexes_verified': len(verified_sources),
            'target_archives_verified': len(verified_targets),
            'disk_free_bytes_at_check': free,
            'disk_required_bytes_at_check': required,
            'disk_preflight_pass': free >= required,
            'host_RAM_limit_verified': False,
            'wallets_started': 0, 'new_fits': 0}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--workspace-root', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(check(MANIFEST, args.workspace_root.resolve()), indent=2))
