"""Stdlib-only identity and terminal-controller verification for exactly 3 cases."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE = ROOT / 'coin_daily_reentry_ablation_20261013'
STATE = MODULE / 'state_20261013T1156Z'
CASE_IDS = ('Y2024_STATIC50_FINE_REENTRY50', 'Y2025_STATIC50_FINE_REENTRY50',
            'Y2025_COMBINED_FINE_REENTRY50')
BASE_IDS = ('Y2024_STATIC50', 'Y2025_STATIC50', 'Y2025_COMBINED')
PREEXECUTION_COMMIT = 'e1f42b8ed4fbdfcd2870799bd4b375a3873743cb'
PINS = {
    'FROZEN_CODE.json': 'bd68e8cf8019507e24f30780bb7c6f97724de7bca64cdfae721b501759628a71',
    'reentry_freeze.py': '58eb413de253b1ad026ce9a5a3362218ab58d68c52298714c4c7ea8e2b4b8b2a',
    'REVIEW_RECEIPT.json': '0d383cbeba76da51f8ce1edc715ca7f689c30bd4c10a617c93298bfa76dbf296',
    'CASE_BINDINGS.json': '02ab7afdb5a51cf1f2d47617f64b7d84d73fa960e011b4a061bac70bff9f3998',
    'run_cases.py': '53d26592a6b42224373c1ef0fd60bd22fc21ddfc55eb97a391122bc293ebdebe',
    'resource_gate.py': 'eafdfa5102f051995627d2d65f099d5062acd4ea4e67c287cecf3fb7fee127df',
}


def sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path: Path):
    return json.loads(Path(path).read_text())


def pinned(path: Path, expected: str, label: str) -> None:
    if Path(path).is_symlink() or sha(path) != expected:
        raise ValueError('Pinned bytes changed: ' + label)


def verify_plan(plan: dict) -> list[str]:
    cases = plan.get('cases', [])
    if (tuple(c.get('case_id') for c in cases) != BASE_IDS or len(cases) != 3
            or plan.get('new_wallets') != 3 or plan.get('comparator_wallets_to_rerun') != 0
            or plan.get('mode') != 'FRESH_DAILY_REENTRY'):
        raise ValueError('Expected only the explicit fixed three-case reentry plan')
    for c in cases:
        if (c['case_id'] != f"Y{c['year']}_{c['arm']}" or len(c['symbols']) != 5
                or c['calendar'][0] >= c['calendar'][1]
                or set(c['fine_comparators']) != {'ORIGINAL', 'GUARD50'}):
            raise ValueError('Case identity/calendar/comparator population differs')
        for mode, ref in c['fine_comparators'].items():
            if ref['case_id'] != c['case_id'] + '_FINE_' + mode:
                raise ValueError('Comparator dispatcher differs')
    return list(CASE_IDS)


def verify_frozen_inputs(module: Path = MODULE, plan: dict | None = None) -> dict:
    module = Path(module)
    for name, digest in PINS.items():
        pinned(module / name, digest, name)
    spec = importlib.util.spec_from_file_location('verified_reentry_observer_freeze',
                                                  module / 'reentry_freeze.py')
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    freeze.verify(module, require_review=True)
    actual = read(module / 'CASE_BINDINGS.json')
    if plan is not None and plan != actual:
        raise ValueError('Supplied observer plan differs from pinned bytes')
    verify_plan(actual)
    for case in actual['cases']:
        for field in ('source_index', 'target_archive'):
            pinned(module.parent / case[field + '_local_locator'], case[field + '_SHA256'], field)
        for ref in case['fine_comparators'].values():
            for name, row in ref['files'].items():
                pinned(module.parent / row['locator'], row['SHA256'], ref['case_id'] + ':' + name)
    return actual


def verify_controller_population(controller: dict, ids: list[str]) -> None:
    status = controller.get('status')
    unstarted = controller.get('unstarted_case_ids')
    per_case = controller.get('per_case')
    if (status not in ('ALL_CASES_FINISHED', 'STOP_PARTIAL') or not isinstance(unstarted, list)
            or len(unstarted) != len(set(unstarted)) or not set(unstarted) <= set(ids)
            or not isinstance(per_case, dict) or set(per_case) != set(ids) - set(unstarted)):
        raise ValueError('Terminal controller receipt lacks the entire fixed population')
    for identity, row in per_case.items():
        if (type(row.get('exit_code')) is not int or type(row.get('peak_RSS')) is not int
                or row['peak_RSS'] < 0):
            raise ValueError('Malformed terminal worker receipt: ' + identity)
        if status == 'ALL_CASES_FINISHED' and (row['exit_code'] != 0
                or row.get('stop_reason') is not None or row['peak_RSS'] > 2_000_000_000):
            raise ValueError('Finished controller lacks clean bounded workers')
    if status == 'ALL_CASES_FINISHED' and unstarted:
        raise ValueError('Finished controller still has unstarted cases')
    if status == 'STOP_PARTIAL' and not unstarted and all(
            row['exit_code'] == 0 and row.get('stop_reason') is None for row in per_case.values()):
        raise ValueError('Partial controller has no failed/unstarted case')


def verify_terminal_run(state: Path = STATE, module: Path = MODULE,
                        plan: dict | None = None) -> list[str]:
    plan = verify_frozen_inputs(module, plan)
    ids = verify_plan(plan)
    binding = read(Path(state) / 'RUN_BINDING.json')
    if binding.get('parent_GO') is not True:
        raise ValueError('Historical parent GO must be explicit true')
    expected = {'parent_GO': True, 'new_case_ids': ids,
                'runner_SHA256': PINS['run_cases.py'],
                'bindings_SHA256': PINS['CASE_BINDINGS.json'],
                'fine_account_SHA256': sha(Path(module).parent / 'coin_quantity_resolution_20261013/fine_account.py'),
                'freeze_manifest_SHA256': PINS['FROZEN_CODE.json'],
                'fine_profile_SHA256': plan['fine_profile_SHA256'],
                'coarse_profile_SHA256': plan['coarse_profile_SHA256'],
                'review_receipt_SHA256': PINS['REVIEW_RECEIPT.json'],
                'resource_gate_SHA256': PINS['resource_gate.py'],
                'controller_wall_limit_seconds': 1200}
    for key, value in expected.items():
        if binding.get(key) != value:
            raise ValueError('Reentry RUN_BINDING differs: ' + key)
    nonce = binding.get('nonce')
    if not isinstance(nonce, str) or len(nonce) != 32 or any(c not in '0123456789abcdef' for c in nonce):
        raise ValueError('Reentry run nonce absent')
    controller = read(Path(state) / 'RESOURCE_RECEIPTS.json')
    verify_controller_population(controller, ids)
    for identity, row in controller['per_case'].items():
        if row['exit_code'] == 0 and row.get('stop_reason') is None:
            for name in ('RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'PREFIX_ACCEPTANCE.json',
                         'BINDING.json', 'recovery/POINTER.json'):
                if not (Path(state) / identity / name).is_file():
                    raise ValueError('Clean worker lacks accepted output: ' + identity + ':' + name)
    return ids


def dispatch_case(identity: str, plan: dict) -> dict:
    verify_plan(plan)
    if identity not in CASE_IDS:
        raise ValueError('Case outside explicit three-case dispatcher')
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


def verify_case_binding(binding: dict, identity: str, case: dict, state: Path = STATE) -> None:
    expected = {'case_id': identity, 'year': case['year'], 'arm': case['arm'],
        'mode': 'FRESH_DAILY_REENTRY', 'calendar': case['calendar'], 'capital_USDT': 10000,
        'source_index_SHA256': case['source_index_SHA256'],
        'target_archive_SHA256': case['target_archive_SHA256'],
        'target_array_SHA256': case['target_array_SHA256'],
        'fine_profile_SHA256': read(MODULE / 'CASE_BINDINGS.json')['fine_profile_SHA256'],
        'fine_account_class': 'conditional_shared_default_fine_grid_sensitivity_v1',
        'fine_account_SHA256': sha(ROOT / 'coin_quantity_resolution_20261013/fine_account.py'),
        'freeze_manifest_SHA256': PINS['FROZEN_CODE.json'],
        'coarse_profile_SHA256': read(MODULE / 'CASE_BINDINGS.json')['coarse_profile_SHA256'],
        'guard_policy_SHA256': sha(ROOT / 'coin_margin_protective_policy_20261013/protective_policy.py'),
        'scheduler_SHA256': sha(ROOT / 'coin_native_half_mix_20261013/repo/scripts/investment/resumable_perpetual.py'),
        'account_SHA256': sha(ROOT / 'coin_native_half_mix_20261013/repo/src/quant/perpetual_account.py'),
        'run_binding_SHA256': sha(Path(state) / 'RUN_BINDING.json'),
        'reentry_policy_SHA256': sha(MODULE / 'daily_reentry_policy.py'),
        'guard_comparator_pointer_SHA256': case['fine_comparators']['GUARD50']['files']['pointer']['SHA256'],
        'persist_cash_close': False, 'final_day_target_zero': False}
    for key, value in expected.items():
        if binding.get(key) != value:
            raise ValueError('Reentry case binding differs: ' + key)
    if set(binding) != set(expected):
        raise ValueError('Reentry case binding key population differs')


def input_file_hashes(state: Path, identity: str, pointer: dict) -> dict:
    base = Path(state) / identity
    names = ['BINDING.json', 'recovery/POINTER.json', 'recovery/' + pointer['snapshot_path'],
             'RESULT.json', 'ACCOUNT.json', 'MINUTE_NUMERIC.json', 'PREFIX_ACCEPTANCE.json']
    paths = [base / name for name in names if (base / name).is_file()]
    paths += [base / 'recovery' / row['path'] for row in pointer['chunks']]
    paths += [Path(state) / 'RUN_BINDING.json', Path(state) / 'RESOURCE_RECEIPTS.json']
    return {str(p.relative_to(ROOT)): sha(p) for p in paths}
