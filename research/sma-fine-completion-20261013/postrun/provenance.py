"""Stdlib-only identity checks for three new SMA terminals and six old controls."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE = ROOT / 'coin_sma_fine_completion_20261013'
STATE = MODULE / 'state_first_authorized_run'
OLD_STATE = ROOT / 'coin_quantity_resolution_20261013/state_20261013'
YEARS = (2023, 2024, 2025)
BASE_IDS = tuple(f'Y{year}_SMA200_10PCT' for year in YEARS)
CASE_IDS = tuple(identity + '_FINE_ORIGINAL' for identity in BASE_IDS)
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT']
CALENDARS = {2023: [1672531200000000, 1704067200000000],
    2024: [1704067200000000, 1735689600000000], 2025: [1735689600000000, 1767225600000000]}
CONTROL_IDS = {year: {'STATIC50': f'Y{year}_STATIC50_FINE_ORIGINAL',
    'EXACTHALF': f'Y{year}_{"EXACTHALF" if year == 2024 else "COMBINED"}_FINE_ORIGINAL'} for year in YEARS}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def safe_path(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Absolute/traversing observer locator')
    path = root / relative
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError('Observer locator escapes root or is a symlink')
    return path


def pinned(path, digest, label):
    if Path(path).is_symlink() or sha(path) != digest:
        raise ValueError('Pinned bytes changed: ' + label)


def verify_plan(plan):
    cases = plan.get('cases', [])
    if (tuple(c.get('case_id') for c in cases) != BASE_IDS or plan.get('case_count') != 3
            or plan.get('modes') != ['ORIGINAL']):
        raise ValueError('Expected exactly the fixed three SMA original cases')
    for case, year in zip(cases, YEARS):
        if (case.get('year') != year or case.get('arm') != 'SMA200_10PCT'
                or case.get('symbols') != SYMBOLS or case.get('target_dtype') != '<f8'
                or case.get('target_shape') != [366 if year == 2024 else 365, 5]
                or case.get('calendar') != CALENDARS[year] or case.get('protective_enabled') is not False):
            raise ValueError('Fixed SMA identity/target geometry differs')
        controls = case.get('existing_fine_controls', {})
        if set(controls) != {'STATIC50', 'EXACTHALF'}:
            raise ValueError('Exact two fine controls must be bound by CASE_BINDINGS')
        for arm, ref in controls.items():
            expected = str((OLD_STATE / CONTROL_IDS[year][arm]).relative_to(ROOT))
            if ref.get('case_id') != CONTROL_IDS[year][arm] or ref.get('state_local_locator') != expected:
                raise ValueError('Read-only control outside exact existing fine bindings')
    return list(CASE_IDS)


def dispatch_case(identity, plan):
    verify_plan(plan)
    if identity not in CASE_IDS:
        raise ValueError('Case outside fixed three-case dispatcher')
    return plan['cases'][CASE_IDS.index(identity)]


def verify_source_files(case):
    """Hash only the exact bound month/daily/event cache; never discover inputs."""
    index_path = safe_path(ROOT, case['source_index_local_locator'])
    pinned(index_path, case['source_index_SHA256'], 'bound source index')
    index = read(index_path)
    if index.get('calendar') != case['calendar'] or index.get('symbol_order') != case['symbols']:
        raise ValueError('Bound source calendar/symbol order differs')
    if [row['month'] for row in index['months']] != [f'{case["year"]}-{month:02d}' for month in range(1, 13)]:
        raise ValueError('Bound source month population differs')
    for row in index['months']:
        path = safe_path(index_path.parent, 'months/' + row['month'] + '.npz')
        pinned(path, row['source_NPZ_SHA256'], 'bound source month')
        if path.stat().st_size != row['source_NPZ_bytes']:
            raise ValueError('Bound source month byte count differs')
    expected_metadata = {'DAILY.json', 'EVENTS.json'}
    if case['year'] == 2025:
        expected_metadata |= {'Y2025.npz', 'Y2025_RISK.json'}
    if set(index['files']) != expected_metadata:
        raise ValueError('Bound source metadata population differs')
    for name in ('DAILY.json', 'EVENTS.json'):
        row = index['files'][name]
        path = safe_path(index_path.parent, name)
        pinned(path, row['SHA256'], 'bound source metadata')
        if path.stat().st_size != row['bytes']:
            raise ValueError('Bound source metadata byte count differs')


def verify_frozen_inputs(module=MODULE, plan=None):
    manifest = read(HERE / 'REVIEWED_POSTRUN_CODE.json')
    for locator, digest in manifest['dependencies_SHA256'].items():
        pinned(safe_path(ROOT, locator), digest, locator)
    spec = importlib.util.spec_from_file_location('sma_postrun_verified_execution_freeze', module / 'freeze_sma.py')
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    freeze.verify(module, require_review=True)
    actual = read(module / 'CASE_BINDINGS.json')
    if plan is not None and actual != plan:
        raise ValueError('Supplied execution plan differs')
    verify_plan(actual)
    for case in actual['cases']:
        verify_source_files(case)
        pinned(safe_path(ROOT, case['target_archive_local_locator']), case['target_archive_SHA256'], 'bound frozen target archive')
    return actual


def verify_controller_population(controller, ids):
    status = controller.get('status')
    unstarted, per_case = controller.get('unstarted_case_ids'), controller.get('per_case')
    if (status not in ('ALL_CASES_FINISHED', 'STOP_PARTIAL') or not isinstance(unstarted, list)
            or len(unstarted) != len(set(unstarted)) or not set(unstarted) <= set(ids)
            or not isinstance(per_case, dict) or set(per_case) != set(ids) - set(unstarted)):
        raise ValueError('Terminal controller lacks entire fixed population')
    for identity, row in per_case.items():
        if type(row.get('exit_code')) is not int or type(row.get('peak_RSS')) is not int or row['peak_RSS'] < 0:
            raise ValueError('Malformed terminal worker receipt: ' + identity)
        if status == 'ALL_CASES_FINISHED' and (row['exit_code'] or row.get('stop_reason') is not None or row['peak_RSS'] > 2_000_000_000):
            raise ValueError('Finished controller lacks clean bounded workers')
    if status == 'STOP_PARTIAL' and not unstarted and all(not r['exit_code'] and r.get('stop_reason') is None for r in per_case.values()):
        raise ValueError('Partial controller has no failed/unstarted case')


def case_availability(state, identity, controller):
    if identity not in CASE_IDS:
        raise ValueError('Unknown SMA identity')
    base = state / identity
    if identity in controller['unstarted_case_ids']:
        if base.exists():
            raise ValueError('Unstarted case unexpectedly has state')
        return 'UNSTARTED_NO_WALLET'
    if not (base / 'BINDING.json').is_file() or not (base / 'recovery/POINTER.json').is_file():
        return 'STARTED_NO_RECOVERABLE_CHECKPOINT'
    return 'ACCEPTED_RESULT' if (base / 'RESULT.json').is_file() else 'RECOVERABLE_PARTIAL_CHECKPOINT'


def verify_case_binding(binding, identity, case, state=STATE):
    plan = read(MODULE / 'CASE_BINDINGS.json')
    expected = {'case_id': identity, 'year': case['year'], 'arm': 'SMA200_10PCT', 'mode': 'ORIGINAL',
        'calendar': case['calendar'], 'capital_USDT': 10000,
        'source_index_SHA256': case['source_index_SHA256'],
        'target_archive_SHA256': case['target_archive_SHA256'], 'target_array_SHA256': case['target_array_SHA256'],
        'fine_profile_SHA256': plan['fine_profile_SHA256'],
        'fine_account_SHA256': sha(ROOT / 'coin_quantity_resolution_20261013/fine_account.py'),
        'freeze_manifest_SHA256': sha(MODULE / 'FROZEN_CODE.json'),
        'run_binding_SHA256': sha(state / 'RUN_BINDING.json'),
        'persist_cash_close': False, 'final_day_target_zero': False,
        'fine_account_class': 'conditional_shared_default_fine_grid_sensitivity_v1',
        'scheduler_SHA256': sha(ROOT / 'coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py'),
        'account_SHA256': sha(ROOT / 'coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py'),
        'terminal_quote_gate_SHA256': plan['terminal_quote_gate_SHA256'], 'protective_enabled': False,
        'original_dynamic_masks_preserved': True, 'publication_base_commit': plan['publication_base_commit']}
    if binding != expected:
        raise ValueError('Exact SMA case binding differs')
    if binding.get('protective_enabled', False) is not False:
        raise ValueError('Protective policy forbidden')


def input_file_hashes(state, identity, pointer):
    base = state / identity
    names = ['BINDING.json', 'recovery/POINTER.json', 'recovery/' + pointer['snapshot_path'],
        'RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv']
    paths = [safe_path(base, name) for name in names if (base / name).is_file()]
    paths += [safe_path(base / 'recovery', row['path']) for row in pointer['chunks']]
    paths += [state / 'RUN_BINDING.json', state / 'RESOURCE_RECEIPTS.json']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def capture_terminal_inputs(state=STATE, module=MODULE, plan=None):
    """Read-only capture after parent release; never restore or advance a wallet."""
    if state.resolve() != STATE.resolve() or state.is_symlink():
        raise ValueError('Only single genuine execution state admitted')
    plan = verify_frozen_inputs(module, plan)
    ids = verify_plan(plan)
    publication = read(module / 'PUBLICATION_RECEIPT.json')
    if (publication.get('status') != 'PASS_EXACT_PRE_GO_REMOTE_PUBLICATION' or publication.get('remote_verified') is not True
            or publication.get('freeze_manifest_SHA256') != sha(module / 'FROZEN_CODE.json')
            or publication.get('case_bindings_SHA256') != sha(module / 'CASE_BINDINGS.json')
            or publication.get('publication_base_commit') != plan['publication_base_commit']
            or publication.get('review_receipt_SHA256') != sha(module / 'REVIEW_RECEIPT.json')):
        raise ValueError('Exact historical pre-GO publication identity differs')
    run = read(state / 'RUN_BINDING.json')
    expected = {'parent_GO': True, 'fine_case_ids': ids, 'runner_SHA256': sha(module / 'run_cases.py'),
        'bindings_SHA256': sha(module / 'CASE_BINDINGS.json'), 'freeze_manifest_SHA256': sha(module / 'FROZEN_CODE.json'),
        'fine_account_SHA256': sha(ROOT / 'coin_quantity_resolution_20261013/fine_account.py'),
        'fine_profile_SHA256': plan['fine_profile_SHA256'],
        'review_receipt_SHA256': sha(module / 'REVIEW_RECEIPT.json'),
        'publication_receipt_SHA256': sha(module / 'PUBLICATION_RECEIPT.json')}
    for key, value in expected.items():
        if run.get(key) != value:
            raise ValueError('SMA RUN_BINDING differs: ' + key)
    nonce = run.get('nonce')
    if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
        raise ValueError('Genuine run nonce missing')
    controller = read(state / 'RESOURCE_RECEIPTS.json')
    verify_controller_population(controller, ids)
    availability, pins = {}, {str((state / n).relative_to(ROOT)): sha(state / n) for n in ('RUN_BINDING.json', 'RESOURCE_RECEIPTS.json')}
    pins.update({str((module / n).relative_to(ROOT)): sha(module / n) for n in ('PUBLICATION_RECEIPT.json', 'REVIEW_RECEIPT.json')})
    for identity in ids:
        availability[identity] = case_availability(state, identity, controller)
        base = state / identity
        if controller['status'] == 'ALL_CASES_FINISHED' and availability[identity] != 'ACCEPTED_RESULT':
            raise ValueError('Clean worker lacks accepted result')
        if availability[identity] in ('ACCEPTED_RESULT', 'RECOVERABLE_PARTIAL_CHECKPOINT'):
            pointer = read(base / 'recovery/POINTER.json')
            pins.update(input_file_hashes(state, identity, pointer))
            pinned(safe_path(base / 'recovery', pointer['snapshot_path']), pointer['snapshot_SHA256'], 'terminal snapshot')
            for row in pointer['chunks']:
                pinned(safe_path(base / 'recovery', row['path']), row['SHA256'], 'terminal chunk')
            if availability[identity] == 'ACCEPTED_RESULT' and any(not (base / n).is_file() for n in ('ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv')):
                raise ValueError('Accepted terminal lacks numeric/daily/account outputs')
        elif base.exists():
            for name in ('BINDING.json', 'RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv'):
                if (base / name).is_file():
                    pins[str((base / name).relative_to(ROOT))] = sha(base / name)
    pinned(OLD_STATE / 'RUN_BINDING.json', plan['old_fine_run_binding_SHA256'], 'old fine run binding')
    old_controller = read(OLD_STATE / 'RESOURCE_RECEIPTS.json')
    if old_controller.get('status') != 'ALL_CASES_FINISHED' or old_controller.get('unstarted_case_ids') != []:
        raise ValueError('Existing fine controls lack terminal historical controller')
    for case in plan['cases']:
        for ref in case['existing_fine_controls'].values():
            old_worker = old_controller.get('per_case', {}).get(ref['case_id'], {})
            if (old_worker.get('exit_code') != 0 or old_worker.get('stop_reason') is not None
                    or type(old_worker.get('peak_RSS')) is not int or not 0 <= old_worker['peak_RSS'] <= 2_000_000_000):
                raise ValueError('Existing control lacks bounded completed historical worker')
            base = safe_path(ROOT, ref['state_local_locator'])
            pointer = read(base / 'recovery/POINTER.json')
            current = input_file_hashes(OLD_STATE, ref['case_id'], pointer)
            if set(ref['files_SHA256']) != {'BINDING.json', 'ACCOUNT.json', 'RESULT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv', 'recovery/POINTER.json'}:
                raise ValueError('Existing control pinned output population differs')
            for key, digest in ref['files_SHA256'].items():
                pinned(safe_path(base, key), digest, 'existing fine control')
            pinned(safe_path(base / 'recovery', pointer['snapshot_path']), pointer['snapshot_SHA256'], 'existing snapshot')
            for row in pointer['chunks']:
                pinned(safe_path(base / 'recovery', row['path']), row['SHA256'], 'existing chunk')
            pins.update(current)
    return {'kind': 'THREE_SMA_TERMINAL_AND_SIX_EXISTING_FINE_READ_ONLY_INPUT_PINS',
        'case_ids': ids, 'state_locator': str(state.relative_to(ROOT)), 'case_availability': availability,
        'controller_terminal_status': controller['status'], 'files_SHA256': pins,
        'financial_advances': 0, 'historical_wallets_opened': 0, 'controls_rerun': 0}


def verify_terminal_run(state=STATE, module=MODULE, plan=None):
    actual = capture_terminal_inputs(state, module, plan)
    if actual != read(HERE / 'TERMINAL_INPUTS.json'):
        raise ValueError('Frozen terminal input population/hash changed')
    return actual['case_ids']
