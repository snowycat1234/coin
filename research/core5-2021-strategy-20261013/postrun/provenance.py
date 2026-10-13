"""Stdlib-only four-case full2021 source, freeze and terminal identity checks."""
from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE = ROOT / 'coin_2021_strategy_comparison_20261013'
STATE = MODULE / 'state_first_authorized_run'
ARMS = ('STATIC50', 'SMA200_10PCT', 'EXACTHALF', 'VOL_MATCHED')
BASE_IDS = tuple('Y2021_' + arm for arm in ARMS)
CASE_IDS = tuple(base + '_FINE_ORIGINAL' for base in BASE_IDS)
CALENDAR = [1609459200000000, 1640995200000000]
SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT']
SOURCE_SHA = '13a0d6551deef1e5cc6865ff4487ebf3fed5dd518364e909fb25ab228838eb33'
TARGET_SHA = '48fbcdd8881700341dfd8d07c00cf0e6a6ead851658dd8b93f15d00044084494'
PINS = {
    'FROZEN_CODE.json': 'fcb32ce4b0585f68674967099cd17365e094abc64b37b0d9432d716501239e15',
    'freeze_2021.py': '7160786f3caf2a4bddac0d95bf7d9cc12414004077ac30dbd4533fad20fe480e',
    'CASE_BINDINGS.json': '45d09560e7a6a908a7e1bced3a699ec6ab7a403218a26ef832bf4ce14d2a2824',
    'run_cases.py': 'e39a2001fb8e43a537c8dce072229edef66884ae438e929e42040741a922b6b0',
    'resource_gate.py': '44157d5deac1316a960211e8e217526dbab1f0d29f4967191729ec7d875fbd20',
    'window_2021.py': '092243fbb8b9570e616062926c9edfc912ff40e797dccfef0926e2e5f1f0b1e9',
    'REVIEW_RECEIPT.json': '57af00916ad073c81818dc6e90602d7176b2adfb80264e2fad407c5806931ffb',
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def safe_path(root: Path, locator: str) -> Path:
    relative = Path(locator)
    if relative.is_absolute() or '..' in relative.parts or not relative.parts:
        raise ValueError('Absolute/traversing observer locator')
    path = Path(root) / relative
    if path.is_symlink() or not path.resolve().is_relative_to(Path(root).resolve()):
        raise ValueError('Observer locator escapes root or is a symlink')
    return path


def pinned(path, expected, label):
    if Path(path).is_symlink() or sha(path) != expected:
        raise ValueError('Pinned bytes changed: ' + label)


def verify_plan(plan):
    cases = plan.get('cases', [])
    if (tuple(c.get('case_id') for c in cases) != BASE_IDS or plan.get('case_count') != 4
            or plan.get('modes') != ['ORIGINAL'] or plan.get('new_historical_wallets_executed') != 0
            or plan.get('status') != 'FROZEN_FOUR_FULL2021_FINE_ORIGINAL_CASES_ZERO_HISTORY'):
        raise ValueError('Expected only explicit fixed four-case full2021 plan')
    for c, arm in zip(cases, ARMS):
        if (c.get('year') != 2021 or c.get('arm') != arm or c.get('symbols') != SYMBOLS
                or c.get('calendar') != CALENDAR or c.get('protective_enabled') is not False
                or c.get('source_index_SHA256') != SOURCE_SHA or c.get('target_archive_SHA256') != TARGET_SHA
                or c.get('source_index_local_locator') != 'coin_2021_source_closure_20261013/prepared_2021/SOURCE_INDEX.json'
                or c.get('target_archive_local_locator') != 'coin_2021_strategy_comparison_20261013/targets/Y2021.npz'
                or c.get('target_dtype') != '<f8' or c.get('target_shape') != [365, 5]):
            raise ValueError('Fixed case identity/calendar/source/targets differ')
    return list(CASE_IDS)


def verify_source_files(case):
    index_path = safe_path(ROOT, case['source_index_local_locator'])
    pinned(index_path, SOURCE_SHA, 'source index')
    index = read(index_path)
    if index.get('calendar_us') != CALENDAR or index.get('days') != 365 or index.get('funding_events') != 5475:
        raise ValueError('Source calendar/event closure differs')
    source = index_path.parent
    for row in index['months']:
        path = safe_path(source, 'months/' + row['month'] + '.npz')
        pinned(path, row['source_NPZ_SHA256'], 'monthly source:' + row['month'])
        if path.stat().st_size != row['source_NPZ_bytes']:
            raise ValueError('Monthly source byte count differs')
    for name, row in index['files'].items():
        path = safe_path(source, name)
        pinned(path, row['SHA256'], 'prepared source:' + name)
        if path.stat().st_size != row['bytes']:
            raise ValueError('Prepared source byte count differs')


def verify_frozen_inputs(module=MODULE, plan=None):
    module = Path(module)
    for name, digest in PINS.items():
        pinned(module / name, digest, name)
    spec = importlib.util.spec_from_file_location('full2021_observer_verified_freeze', module / 'freeze_2021.py')
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    freeze.verify(module, require_review=True)
    actual = read(module / 'CASE_BINDINGS.json')
    if plan is not None and plan != actual:
        raise ValueError('Supplied plan differs')
    verify_plan(actual)
    verify_source_files(actual['cases'][0])
    pinned(safe_path(ROOT, actual['cases'][0]['target_archive_local_locator']), TARGET_SHA, 'target archive')
    return actual


def verify_controller_population(controller: dict, ids: list[str]) -> None:
    status, unstarted, per_case = controller.get('status'), controller.get('unstarted_case_ids'), controller.get('per_case')
    if (status not in ('ALL_CASES_FINISHED', 'STOP_PARTIAL') or not isinstance(unstarted, list)
            or len(unstarted) != len(set(unstarted)) or not set(unstarted) <= set(ids)
            or not isinstance(per_case, dict) or set(per_case) != set(ids) - set(unstarted)):
        raise ValueError('Terminal controller receipt lacks the entire fixed population')
    for identity, row in per_case.items():
        if type(row.get('exit_code')) is not int or type(row.get('peak_RSS')) is not int or row['peak_RSS'] < 0:
            raise ValueError('Malformed terminal worker receipt: ' + identity)
        if status == 'ALL_CASES_FINISHED' and (row['exit_code'] != 0 or row.get('stop_reason') is not None or row['peak_RSS'] > 2_000_000_000):
            raise ValueError('Finished controller lacks clean bounded workers')
    if status == 'STOP_PARTIAL' and not unstarted and all(row['exit_code'] == 0 and row.get('stop_reason') is None for row in per_case.values()):
        raise ValueError('Partial controller has no failed/unstarted case')


def dispatch_case(identity, plan):
    verify_plan(plan)
    if identity not in CASE_IDS:
        raise ValueError('Case outside fixed four-case dispatcher')
    return plan['cases'][CASE_IDS.index(identity)]


def case_availability(state: Path, identity: str, controller: dict) -> str:
    if identity not in CASE_IDS:
        raise ValueError('Unknown case')
    path = Path(state) / identity
    if identity in controller['unstarted_case_ids']:
        if path.exists():
            raise ValueError('Unstarted case unexpectedly has wallet state')
        return 'UNSTARTED_NO_WALLET'
    if not (path / 'BINDING.json').is_file() or not (path / 'recovery/POINTER.json').is_file():
        return 'STARTED_NO_RECOVERABLE_CHECKPOINT'
    return 'ACCEPTED_RESULT' if (path / 'RESULT.json').is_file() else 'RECOVERABLE_PARTIAL_CHECKPOINT'


def verify_case_binding(binding, identity, case, state=STATE):
    plan = read(MODULE / 'CASE_BINDINGS.json')
    expected = {'case_id': identity, 'year': 2021, 'arm': case['arm'], 'mode': 'ORIGINAL',
        'calendar': CALENDAR, 'capital_USDT': 10000, 'source_index_SHA256': SOURCE_SHA,
        'target_archive_SHA256': TARGET_SHA, 'target_array_SHA256': case['target_array_SHA256'],
        'fine_profile_SHA256': plan['fine_profile_SHA256'],
        'fine_account_class': 'conditional_shared_default_fine_grid_sensitivity_v1',
        'fine_account_SHA256': sha(ROOT / 'coin_quantity_resolution_20261013/fine_account.py'),
        'freeze_manifest_SHA256': PINS['FROZEN_CODE.json'],
        'scheduler_SHA256': sha(ROOT / 'coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py'),
        'account_SHA256': sha(ROOT / 'coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py'),
        'run_binding_SHA256': sha(Path(state) / 'RUN_BINDING.json'),
        'terminal_quote_gate_SHA256': plan['terminal_quote_gate_SHA256'], 'protective_enabled': False,
        'original_dynamic_masks_preserved': True, 'source_commit': plan['source_commit'],
        'persist_cash_close': False, 'final_day_target_zero': False}
    if binding != expected:
        raise ValueError('Full2021 exact case binding differs')


def _verify_terminal_requirements(state=STATE, module=MODULE, plan=None):
    if Path(state).resolve() != STATE.resolve() or Path(state).is_symlink():
        raise ValueError('Only the single genuine authorized state root is admitted')
    plan = verify_frozen_inputs(module, plan)
    ids = verify_plan(plan)
    binding = read(Path(state) / 'RUN_BINDING.json')
    publication_path = Path(module) / 'PUBLICATION_RECEIPT.json'
    publication = read(publication_path)
    if (publication.get('status') != 'PASS_EXACT_PRE_GO_REMOTE_PUBLICATION' or publication.get('remote_verified') is not True
            or publication.get('freeze_manifest_SHA256') != PINS['FROZEN_CODE.json']
            or publication.get('case_bindings_SHA256') != PINS['CASE_BINDINGS.json']
            or publication.get('source_commit') != plan['source_commit']):
        raise ValueError('Historical pre-GO publication identity differs')
    expected = {'parent_GO': True, 'fine_case_ids': ids, 'runner_SHA256': PINS['run_cases.py'],
        'bindings_SHA256': PINS['CASE_BINDINGS.json'],
        'fine_account_SHA256': sha(ROOT / 'coin_quantity_resolution_20261013/fine_account.py'),
        'freeze_manifest_SHA256': PINS['FROZEN_CODE.json'], 'fine_profile_SHA256': plan['fine_profile_SHA256'],
        'review_receipt_SHA256': sha(Path(module) / 'REVIEW_RECEIPT.json'),
        'publication_receipt_SHA256': sha(publication_path)}
    for key, value in expected.items():
        if binding.get(key) != value:
            raise ValueError('Full2021 RUN_BINDING differs: ' + key)
    nonce = binding.get('nonce')
    if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
        raise ValueError('Historical run nonce missing')
    controller = read(Path(state) / 'RESOURCE_RECEIPTS.json')
    verify_controller_population(controller, ids)
    for identity in ids:
        availability = case_availability(Path(state), identity, controller)
        if controller['status'] == 'ALL_CASES_FINISHED' and availability != 'ACCEPTED_RESULT':
            raise ValueError('Clean worker lacks accepted result: ' + identity)
        if availability == 'ACCEPTED_RESULT':
            for name in ('ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv'):
                if not (Path(state) / identity / name).is_file():
                    raise ValueError('Accepted worker lacks output: ' + identity + ':' + name)
    return ids, controller


def input_file_hashes(state: Path, identity: str, pointer: dict) -> dict:
    base = Path(state) / identity
    names = ['BINDING.json', 'recovery/POINTER.json', 'recovery/' + pointer['snapshot_path'],
             'RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv']
    paths = [safe_path(base, name) for name in names if (base / name).is_file()]
    paths += [safe_path(base / 'recovery', row['path']) for row in pointer['chunks']]
    paths += [Path(state) / 'RUN_BINDING.json', Path(state) / 'RESOURCE_RECEIPTS.json']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}


def capture_terminal_inputs(state=STATE, module=MODULE, plan=None):
    """Return read-only pins for parent exclusive-create after terminal release.

    Does not import a financial module, restore state, or write any receipt.
    Parent must separately hash-bind these bytes in its postrun GO.
    """
    ids, controller = _verify_terminal_requirements(state, module, plan)
    paths = [Path(state) / 'RUN_BINDING.json', Path(state) / 'RESOURCE_RECEIPTS.json',
             Path(module) / 'PUBLICATION_RECEIPT.json', Path(module) / 'REVIEW_RECEIPT.json']
    pins = {str(path.relative_to(ROOT)): sha(path) for path in paths}
    availability = {}
    for identity in ids:
        status = case_availability(Path(state), identity, controller)
        availability[identity] = status
        base = Path(state) / identity
        if status in ('ACCEPTED_RESULT', 'RECOVERABLE_PARTIAL_CHECKPOINT'):
            pointer = read(base / 'recovery/POINTER.json')
            pins.update(input_file_hashes(Path(state), identity, pointer))
            pinned(safe_path(base / 'recovery', pointer['snapshot_path']), pointer['snapshot_SHA256'], identity + ':snapshot')
            for row in pointer['chunks']:
                pinned(safe_path(base / 'recovery', row['path']), row['SHA256'], identity + ':chunk')
        elif base.exists():
            for name in ('BINDING.json', 'RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'DAILY.csv'):
                path = base / name
                if path.is_file():
                    pins[str(path.relative_to(ROOT))] = sha(path)
    return {'kind': 'FOUR_FULL2021_TERMINAL_READ_ONLY_INPUT_PINS', 'case_ids': ids,
        'state_locator': str(Path(state).relative_to(ROOT)), 'controller_terminal_status': controller['status'],
        'case_availability': availability, 'files_SHA256': pins, 'financial_advances': 0,
        'historical_wallets_opened': 0, 'controls_rerun': 0}


def verify_terminal_run(state=STATE, module=MODULE, plan=None):
    actual = capture_terminal_inputs(state, module, plan)
    saved = read(HERE / 'TERMINAL_INPUTS.json')
    if saved != actual:
        raise ValueError('Frozen terminal input population/hash changed')
    return actual['case_ids']
