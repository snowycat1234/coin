"""Exact source-only 17-cell preparation and fresh, independently admitted entry.

Preparation does not construct an account, run a financial clock, read outcomes,
select a candidate, download, or use an old GO as authority. A new immutable scope
is minted only after new exact review and external root-GO byte bindings pass.
"""
from __future__ import annotations
from collections.abc import Mapping
from dataclasses import dataclass, field
from io import BytesIO
import hashlib
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from types import MappingProxyType

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT / 'traditional_three_tier_freeze_20261015'
D_ROOT = ROOT / 'bounded_native_continuation_guard50_exit_20261015'
for directory in (FROZEN, D_ROOT):
    if str(directory) not in sys.path:
        sys.path.insert(0, str(directory))
import annual_entry_2023 as a23
import annual_entry_2024 as a24
import guard50_exit_entry as old

POLICY_VARIANT = 'GUARD50_EXIT_ONLY'
MODES = (POLICY_VARIANT,)
COST = 'BASE27'
SETTLEMENT_MODE = 'CONDITIONAL_COLLATERAL_FORFEITURE'
LABEL = a24.LABEL
POLICY_VERSION = 'GUARD50_EXIT_ONLY_DEV_2023_2024_SEVENTEEN_CELL_EXPANSION_V1'
SOURCE_SCOPE = 'ROOT_ADMITTED_FRESH_EXACT_CELL_GUARD50_EXIT_ONLY_DEV2023_2024_V1'
PREPARATION_SCHEMA = 'SOURCE_TARGET_ONLY_GUARD50_EXIT_EXPANSION_17_DEV_CELLS_V1'
REVIEW_SCHEMA = 'INDEPENDENT_GUARD50_EXIT_EXPANSION_SOURCE_GENERATED_REVIEW_V1'
GO_SCHEMA = 'ROOT_GO_GUARD50_EXIT_EXPANSION_EXACT_ORDERED_TRANCHE_V1'
MANIFEST_NAME = 'FROZEN_SEVENTEEN_CELL_MANIFEST.json'
MANIFEST_SHA256 = '0c08a0c362c8222d2dc16735f7ebf11a26f4892999bc57b3b062d189ff050638'
ASSESSMENT_SHA256 = 'e05050b82bd25b4902aa97bfbde8ed12f959e70f4c95c1497f79913ab6d092a2'
FIRST_TRANCHE = 'FIRST_FIVE_STATIC50'
REMAINING_TRANCHE = 'REMAINING_TWELVE_H090_AND_HOLD'
YEARS = (2023, 2024)
ANNUAL_PREPARATIONS = {
    2023: FROZEN / 'annual_2023_source_preparation_attempt003',
    2024: FROZEN / 'annual_2024_source_preparation_attempt002',
}
ANNUAL_PREPARATION_PINS = {
    2023: '43c715123c2be9a1398bd5242bc86da27efaf1cd30927117d9d835a3bcaebb43',
    2024: '657317bb8c025d8ab926e66a57078bfcf2a8d684be6dcc40a0ac8e7502b29b46',
}
SOURCE_ROOTS = {year: ROOT / f'native_{year}_source_restore_20261015' for year in YEARS}
FROZEN_D_CODE_PINS = {
    'guard50_exit.py': '5fb0b20494269da55ea705c9f3f8aaa7270d132eb3d566eb81a29cb0466b1fc8',
    'guard50_exit_entry.py': 'cf50f5c1cde1e12d8f70fb081acc49a3505252cedc3e10dd46c9463c962d0dc3',
    'run_guard50_exit.py': '8c41a6e6d93ee085530dbb5d482cc02fa6cbd34e1c2989098c3bcc9088d968f2',
}
# Explicit immutable minute-mark and original200 evidence, independently of
# daily completeness. Raw archive/checksum/index pins are derived only from
# these exact pinned normalization receipts, never from untrusted new metadata.
PROVENANCE_2023_PINS = {'prepared_2023/SOURCE_INDEX.json': '5c88d0022fe185f966266b54c9962b1e632048817d369e00112f72b2071c7251', 'SOURCE_WARMUP_CLOSE_ONLY.npz': '45a3d6dd8c788a5a721a560736c611073d41fe65648f7b5e408cb07a71e0a75f', 'INDEPENDENT_ORIGINAL_TRANSPORT_CHECK.json': '2b198f3d547a5f99c58a7b9ed9c2e45b74f0a9e8c892d9875382d197c6e31f6c', 'original200_proof/original200_quality.py': '657b96aeba85c769be63b5bf3184953244eba6fdd83d6fc95065761f8aa1b01a', 'original200_proof/ORIGINAL200_SOURCE_QUALITY_PROOF.json.gz': 'ffb99d83840828c3bc6547562b530d9c584938acd9e23f1391a71079fdf091d7', 'original200_proof/ORIGINAL200_SOURCE_QUALITY_REVIEW.json': '3ce7f58d42423379453c9015ce386f0074627380cf71cc64ef7e1f6ff1c21cfe', 'normalization/normalize_sources.py': '3f5b632de27455e6218f0f64d1eb929ad30ab030d1f73f76dd740bb1d8edb4d1', 'normalization/pinned/normalize.py': 'ee394086066c96bc23e83b45bf0bc2777264ab4eb57128886394fee47fecd4ff', 'normalization/pinned/download.py': '2ffb1694c613be8350d2979c918d3b03a9345d8b2769bfb89b3e230375bdb707', 'normalization/NORMALIZATION_RECEIPT.json': '77ade85aa3d2e3bbbd1149c3e6c69d8b728ded9901709ffbc51ff6b92b576d24', 'normalization/EXACT_TRANSPORT_GATE.json': 'c185f0b79d2e8aa64570174ac6973ab4332337774dcff7778b75d0cfe02a158e', 'normalization/receipts/2023-01.json': '33c051840cbcfb0ca3645bfa280917be57bcebe9efc1ca14663d30a9d858d798', 'normalization/receipts/2023-02.json': '456aba613e716f44ec572a2f0da424ebb9ad07d6b7ca7284bfb064250fb95835', 'normalization/receipts/2023-03.json': 'd76add83cbd472d36e6e16948dbebde825adfe46706d5f6fa1b5e2c3cf7d7aef', 'normalization/receipts/2023-04.json': '7a72031f27165fb45e43b8755010f8fe6577e68af9e657e41d5dbad910e9c4e7', 'normalization/receipts/2023-05.json': '38fdcd4b3a7fae2768ddf617ed352f01787d725cc8d4766431a8b6d60198ed95', 'normalization/receipts/2023-06.json': '22e4fab2611b0d71352798489506025f018e42d5bec70597fe5d25fbaaceb654', 'normalization/receipts/2023-07.json': 'a8f7119e816a80ae0ff94551b2628c59915ba24edfb721f4894ceb3fcebd2f5e', 'normalization/receipts/2023-08.json': '16f8ca07788012821f69a8353e492fad8bfa1589de01cc9b7dfeb123e7632510', 'normalization/receipts/2023-09.json': '71d6eeea210b5c8c89b80c9dddfcdaa6f1c5ba6f27463ddbf8c85f590d869e2e', 'normalization/receipts/2023-10.json': '08d61db62c26c8a2b604180bdf64c55bfdf311b58d6ae67a9cdad436a407c6ce', 'normalization/receipts/2023-11.json': 'd331b145c7ca71cf9f0a1d416b6b2d80d14d77164a01749c025df285e80378c9', 'normalization/receipts/2023-12.json': 'ed73a8686ee37718295fd8ccb8b38f3906126058a9035629b1d1cb21eb595c85', 'normalization/pinned/original_source.py': '923db96473f5b4a79d313073bdaaed121ee24d631e7a79a298972aa613f2d156', 'normalization/pinned/native_run.py': '3661152766ca801a7050d26d377d6fdcddf4ec9b1fcc7eb4475ad256e18127e1', 'normalization/pinned/source_prepare.py': 'c0a284133b536d3496ce2002bbd8f8dfe4accf7f458a7691ba9adab3cdb4d28e'}
_SCOPE_SEAL = object()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(_plain(value), sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _json_sha(value):
    return _sha(_canonical(value))


def _same(a, b):
    return _canonical(a) == _canonical(b)


_object = old._object
_exact = old._exact
_ordinary = old._ordinary


def _immutable(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: _immutable(item) for key, item in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(_immutable(item) for item in value)
    return value


def _plain(value):
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    return value


def frozen_manifest():
    raw = a24.h._read_exact(HERE / MANIFEST_NAME, MANIFEST_SHA256)
    manifest = _object(raw, 'EXACT_FROZEN_SEVENTEEN_CELL_MANIFEST_REQUIRED')
    if (manifest['years'] != [2023, 2024] or len(manifest['cells']) != 17
            or manifest['policy_variant'] != POLICY_VARIANT
            or manifest['new_cell_count'] != 17
            or manifest['financial_policy_changes_allowed'] is not False):
        raise ValueError('EXACT_FROZEN_MANIFEST_SCOPE_REQUIRED')
    return manifest


def cell_descriptor(cell_id):
    if type(cell_id) is not str:
        raise ValueError('EXACT_MANIFEST_CELL_REQUIRED')
    for cell in frozen_manifest()['cells']:
        if cell['cell_id'] == cell_id:
            return cell
    raise ValueError('EXACT_MANIFEST_CELL_REQUIRED_REUSED_OR_OTHER_YEAR_REFUSED')


def tranche_cells(tranche=FIRST_TRANCHE):
    if tranche not in (FIRST_TRANCHE, REMAINING_TRANCHE):
        raise ValueError('ONLY_EXACT_ORDERED_FIRST_FIVE_OR_REMAINING_TWELVE_REQUIRED')
    return tuple(cell['cell_id'] for cell in frozen_manifest()['cells'] if cell['tranche'] == tranche)


RESOURCE_LIMITS = frozen_manifest()['resource_design']
RESOURCE_EXECUTION_CONTRACT = dict(
    interpretation='ONE_ASSIGNED_CPU_AND_MAX_ONE_THREAD_PER_NUMERICAL_COMPUTE_POOL',
    assigned_CPUs_per_worker=1, numerical_compute_pool_threads_max=1,
    OS_watchdog_IO_and_runtime_helper_threads_allowed=True,
    actual_OS_task_count_and_affinities_must_be_reported=True,
    every_OS_task_affinity_must_equal_worker_single_assigned_CPU=True,
    affinity_is_applied_before_numerical_imports=True,
    two_affinity_CPUs_do_not_certify_two_full_CPU_quotas=True,
    quota_visibility='UNVERIFIED_HOST_OBSERVATIONS_ONLY',
    serial_fallback_before_new_launch=True)
LAUNCH_CLAIM_CONTRACT = dict(
    launch_claim_schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1',
    launch_claim_registry_relative='bounded_native_continuation_guard50_exit_expansion_20261015/EXECUTION_CLAIMS',
    launch_claim_key='manifest_SHA256/cell_id.json',
    launch_claim_atomic_exclusive_create=True, launch_claim_never_automatically_cleared=True,
    existing_controller_output_refused=True, scheduling_resume_supported=False,
    cross_output_duplicate_launch_forbidden=True,
    claim_created_only_after_exact_GO_review_source_code_and_resource_validation=True,
    claim_binds='MANIFEST_CELL_YEAR_CONFIG_SOURCE_TARGET_PREPARATION_CODE_GO_REVIEW_CONTROLLER_PID_OUTPUT',
    process_ownership_recorded_after_Popen_in_exclusive_case_artifact=True)
GLOBAL_CONTROLLER_LEASE_CONTRACT = dict(
    schema='CANONICAL_MANIFEST_GLOBAL_CONTROLLER_FLOCK_V1',
    registry_relative='bounded_native_continuation_guard50_exit_expansion_20261015/EXECUTION_CLAIMS',
    key='manifest_SHA256/CONTROLLER_LEASE.lock',
    exclusive_nonblocking_flock=True, one_controller_across_both_tranches=True,
    lease_held_until_all_child_processes_exit=True, lease_FD_inherited_by_workers=True,
    existing_lease_refuses_new_controller=True,
    real_lease_created_only_after_external_GO_review_source_code_and_resource_validation=True)


def _annual(year):
    if type(year) is not int or year not in YEARS:
        raise ValueError('ONLY_SEEN_DEV_2023_2024_ALLOWED')
    module = a23 if year == 2023 else a24
    raw = a24.h._read_exact(ANNUAL_PREPARATIONS[year] / 'PREPARATION.json', ANNUAL_PREPARATION_PINS[year])
    annual = _object(raw, 'EXACT_FROZEN_ANNUAL_PREPARATION_REQUIRED')
    expected_calendar = [module.START, module.END]
    if (annual['code_identity'] != module.code_identity() or annual['calendar'] != expected_calendar
            or annual['cost'] != COST or annual['accounts_created'] != 0
            or annual['annual_returns_computed'] is not False
            or len(annual['configs']) != 9 or annual['unique_execution_jobs'] != 9):
        raise ValueError('FROZEN_ANNUAL_SOURCE_TARGET_CODE_OR_QUALITY_CHANGED')
    return module, raw, annual


def preserved_evidence_identity():
    pins = dict(old.PRESERVED_EVIDENCE_PINS)
    pins.update({
        'traditional_three_tier_freeze_20261015/annual_go/ROOT_GO_2023_PILOT001.json': '6930d9450279f652db8f6b644ec00043a6cedb166410191859c2f666d62f37ef',
        'traditional_three_tier_freeze_20261015/annual_go/ROOT_GO_2023_REMAINING001.json': 'c46cc26b8039c372ec973557a9b6a2fd8b4b0f80f354612795b1da9eb60489e0',
        'traditional_three_tier_independent_review_20261015/ANNUAL_FINAL_INDEPENDENT_REVIEW_RECEIPT.json': 'e25a233996aa8ac41750eba4cfe414b6524f8dce1888bdaba60bcc2d9de3bdd3',
    })
    reused = frozen_manifest()['reused_excluded_completed_cell']
    pins[reused['case_receipt']] = reused['case_receipt_SHA256']
    pins[reused['independent_paired_review']] = reused['independent_paired_review_SHA256']
    for name, digest in pins.items():
        a24.h._read_exact(ROOT / name, digest)
    return pins


def code_identity():
    result = {}
    for year in YEARS:
        _, _, annual = _annual(year)
        for name, digest in annual['code_identity'].items():
            key = 'traditional_three_tier_freeze_20261015/' + name
            if key in result and result[key] != digest:
                raise ValueError('OLD_ANNUAL_CODE_UNION_CONFLICT')
            a24.h._read_exact(FROZEN / name, digest)
            result[key] = digest
    reporting_digest = '3ffee703c1fabd4e18d9673220a850fff5e5663aed697e2dead7627017ff8636'
    a24.h._read_exact(FROZEN / 'annual_reporting.py', reporting_digest)
    result['traditional_three_tier_freeze_20261015/annual_reporting.py'] = reporting_digest
    for name, digest in old.PRIMITIVE_CODE_PINS.items():
        a24.h._read_exact(old.PRIMITIVE / name, digest)
        result['bounded_account_continuation_20261015/' + name] = digest
    for name, digest in old.FROZEN_V2_CODE_PINS.items():
        a24.h._read_exact(old.FROZEN_V2 / name, digest)
        result['bounded_native_continuation_v2_20261015/' + name] = digest
    for name, digest in FROZEN_D_CODE_PINS.items():
        a24.h._read_exact(D_ROOT / name, digest)
        result[D_ROOT.name + '/' + name] = digest
    for name in ('expansion.py', 'expansion_entry.py', 'run_expansion.py', 'saved_native_reconciliation.py'):
        result[HERE.name + '/' + name] = _sha(_ordinary(HERE / name))
    result[HERE.name + '/' + MANIFEST_NAME] = _sha(a24.h._read_exact(HERE / MANIFEST_NAME, MANIFEST_SHA256))
    result[HERE.name + '/EXPANSION_INPUT_ASSESSMENT.md'] = _sha(a24.h._read_exact(HERE / 'EXPANSION_INPUT_ASSESSMENT.md', ASSESSMENT_SHA256))
    return result


def _policy(code):
    return dict(version=POLICY_VERSION, source_scope=SOURCE_SCOPE,
        policy_variant=POLICY_VARIANT, cost=COST, settlement_mode=SETTLEMENT_MODE,
        manifest_SHA256=MANIFEST_SHA256, code_identity=code,
        ordered_cells=[cell['cell_id'] for cell in frozen_manifest()['cells']],
        first_tranche=list(tranche_cells()), remaining_tranche=list(tranche_cells(REMAINING_TRANCHE)),
        resource_limits=RESOURCE_LIMITS, resource_execution_contract=RESOURCE_EXECUTION_CONTRACT, launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,
        all_years_seen_development=True,
        candidate_threshold_or_performance_selection_allowed=False,
        initial_shared_wallet_USDT='10000', leverage=1,
        common_free_cash_floor_USDT='1000', common_isolated_margin_ceiling_USDT='8500',
        D_has_no_topup_or_internal_margin_transfer=True,
        D_warning_action='NATIVE_PAID_FULL_ACTUAL_POSITION_EXIT_NO_TOPUP',
        D_warning_threshold='KNOWN_FRESH_ISOLATED_EQUITY_LE_HALF_ISOLATED_BALANCE',
        mark_quality_exit_policy_version='UNKNOWN_MARK_NO_NEW_EXIT_V2',
        unknown_or_stale_quality_itself_creates_new_warning_exit=False,
        ordinary_new_strategy_reductions_and_native_exits_preserved=True,
        legitimate_preexisting_pending_exit_preserved=True,
        quantity_profile_SHA256=old.PRIMITIVE_CODE_PINS['QUANTITY_PROFILE.json'],
        frozen_D_code_SHA256=FROZEN_D_CODE_PINS['guard50_exit.py'],
        actual_held_exposure_and_forecast_overshoots_required=True,
        nominal_tier_equality_is_realized_risk_matching=False,
        fresh_genesis_only=True, automatic_retry_authorized=False,
        halted_snapshot_resume_authorized=False, old_GO_is_new_authority=False,
        other_years_or_2025_authorized=False, locked_or_holdout_consumed=False,
        publication_authorized=False)


def _coldstart_policy(year):
    if year == 2024:
        return a24._protocol()['coldstart_policy']
    return dict(version='UNCHANGED_V3_FRESH_FLAT_UNKNOWN_PRIOR',
        available_prior_source_used=False, initial_signal_us=a23.START,
        first_real_completed_quote_us=a23.START + a24.n.MINUTE,
        earliest_initial_increase_admission_us=a23.START + a24.n.MINUTE + 1)


def _safe_relative(name):
    p = Path(name)
    if not isinstance(name, str) or p.is_absolute() or '..' in p.parts:
        raise ValueError('EXACT_RELATIVE_PROVENANCE_PATH_REQUIRED')
    return p


def _provenance_2023(source_root, captured, *, reconstruct):
    root = Path(source_root)
    pins = {}
    for name, digest in PROVENANCE_2023_PINS.items():
        body = a24.h._read_exact(root / name, digest)
        pins[name] = dict(SHA256=digest, bytes=len(body))
    raw_records = []
    for month in range(1, 13):
        name = f'normalization/receipts/2023-{month:02d}.json'
        receipt = _object(a24.h._read_exact(root / name, pins[name]['SHA256']), 'EXACT_NORMALIZATION_RECEIPT_REQUIRED')
        container = captured[f'prepared_2023/months/2023-{month:02d}.npz']
        if (_sha(container) != receipt['actual_NPZ_SHA256']
                or len(container) != receipt['actual_NPZ_bytes']
                or receipt['original_container_identity'] is not True
                or receipt['financial_runs'] != 0):
            raise ValueError('EXACT_2023_MARK_PROVENANCE_CONTAINER_REQUIRED')
        with np.load(BytesIO(container), allow_pickle=False) as arrays:
            for symbol in a24.g.SYMBOLS:
                mark = arrays[symbol + '_mark']
                expected = receipt['arrays'][symbol + '_mark']
                if (mark.dtype.str != expected['dtype'] or list(mark.shape) != expected['shape']
                        or _sha(mark.tobytes(order='C')) != expected['C_order_byte_SHA256']):
                    raise ValueError('EXACT_2023_MARK_C_ORDER_PROVENANCE_REQUIRED')
        for row in receipt['source_records']:
            if row['family'] != 'markPriceKlines':
                continue
            if (row['complete_minute_grid'] is not True or row['CRC'] is not True
                    or row['original_manifest_hashes_match'] is not True
                    or row['official_checksum_matches_ZIP'] is not True):
                raise ValueError('GENUINE_ORIGINAL_MINUTE_MARK_PROVENANCE_REQUIRED')
            rows = [row] + [repair['source'] for repair in row['exact_daily_unions']]
            for record in rows:
                relative = str(_safe_relative(record['path']))
                for name, digest, size in ((relative, record['ZIP_SHA256'], record['ZIP_bytes']),
                        (relative + '.CHECKSUM', record['CHECKSUM_SHA256'], None)):
                    body = a24.h._read_exact(root / name, digest, size)
                    pin = dict(SHA256=digest, bytes=len(body))
                    if name in pins and pins[name] != pin:
                        raise ValueError('CONFLICTING_RAW_MINUTE_MARK_PROVENANCE')
                    pins[name] = pin
                raw_records.append(dict(month=receipt['month'], symbol=row['symbol'],
                    path=relative, ZIP_SHA256=record['ZIP_SHA256'], CHECKSUM_SHA256=record['CHECKSUM_SHA256']))
            if 'phase' in row:
                name = 'source-phases/' + row['phase'] + '/SOURCE_INDEX.json'
                digest = row['SOURCE_INDEX_SHA256']
            else:
                name = 'H2/' + row['fold'] + '/INDEX.json'
                digest = row['INDEX_SHA256']
            body = a24.h._read_exact(root / name, digest)
            pins[name] = dict(SHA256=digest, bytes=len(body))
    if len(raw_records) != 65 or len({r['path'] for r in raw_records}) != 65:
        raise ValueError('EXACT_SIXTY_MONTHLY_PLUS_FIVE_GENUINE_DAILY_MARK_STREAMS_REQUIRED')
    if reconstruct:
        path = root / 'normalization/normalize_sources.py'
        spec = importlib.util.spec_from_file_location('_expansion_pinned_pure_mark_normalizer', path)
        normalizer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(normalizer)
        for month in range(1, 13):
            with np.load(BytesIO(captured[f'prepared_2023/months/2023-{month:02d}.npz']), allow_pickle=False) as arrays:
                for symbol in a24.g.SYMBOLS:
                    frame, proof = normalizer.source_frame(month, symbol, 'markPriceKlines')
                    mark = frame.close.to_numpy()
                    if (mark.dtype != np.dtype('float64')
                            or mark.tobytes() != arrays[symbol + '_mark'].tobytes()
                            or proof['complete_minute_grid'] is not True):
                        raise ValueError('RAW_TO_PREPARED_GENUINE_MINUTE_MARK_BITS_REQUIRED')
    for name, pin in pins.items():
        a24.h._read_exact(root / name, pin['SHA256'], pin['bytes'])
    sidecar = dict(schema='EXACT_2023_ORIGINAL_GENUINE_MINUTE_MARK_PROVENANCE_V1',
        calendar=[a23.START, a23.END], symbol_order=list(a24.g.SYMBOLS),
        mark_cells=2628000, derived_mark_cells=0, original_mark_execution_admitted=True,
        source_kind='DIRECT_REVIEWED_SOURCE_OBSERVATION', missing_intervals=[],
        monthly_streams=60, actual_daily_repair_streams=5, raw_mark_streams=raw_records,
        source_and_proof_pins=pins, source_reconstruction='EXACT_PINNED_NORMALIZER_CLOSE_ASSIGNMENT',
        provider_arrival_certified=False, venue_methodology_certified=False,
        initial_prior_mark='UNKNOWN', initial_prior_quote='UNKNOWN',
        first_genuine_minute_available_us=a23.START + a24.n.MINUTE,
        unknown_or_stale_quality_itself_creates_new_warning_exit=False,
        accounts_constructed=0, financial_runs=0)
    return sidecar, pins


@dataclass(frozen=True, slots=True)
class _CapturedMinuteProvider:
    year: int
    months: tuple = field(repr=False)

    @property
    def identity(self):
        return [[name, start, count, _sha(body), len(body)] for name, start, count, body in self.months]

    def __call__(self):
        module = a23 if self.year == 2023 else a24
        expected = module.START
        for name, start, count, body in self.months:
            if start != expected:
                raise ValueError('EXACT_CAPTURED_EXPANSION_MONTH_ORDER_REQUIRED')
            arrays = a24._month_arrays(body, start, count)
            if self.year == 2024:
                arrays, _ = a24.m.project_month(arrays)
            for offset in range(0, count, 1440):
                yield dict(times=arrays['times'][offset:offset + 1440], market={symbol: {
                    key: arrays[symbol + '_' + key][offset:offset + 1440]
                    for key in ('open', 'close', 'quote_volume', 'mark')} for symbol in a24.g.SYMBOLS})
            expected += count * a24.n.MINUTE
        if expected != module.END:
            raise ValueError('EXACT_CAPTURED_YEAR_END_REQUIRED')


def _make_window(year, index, captured, sidecar):
    module = a23 if year == 2023 else a24
    months, start = [], module.START
    for record in index['months']:
        name = f'prepared_{year}/months/' + record['month'] + '.npz'
        months.append((name, start, record['minutes'], captured[name]))
        start += record['minutes'] * a24.n.MINUTE
    return MappingProxyType(dict(start=module.START, end=module.END, symbols=a24.g.SYMBOLS,
        daily=pl.DataFrame(json.loads(captured[f'prepared_{year}/DAILY.json'])),
        events=_immutable(json.loads(captured[f'prepared_{year}/EVENTS.json'])),
        minute_blocks=_CapturedMinuteProvider(year, tuple(months)),
        derived_mark_cells=0 if year == 2023 else 10,
        original_missing_mark_open_ms=() if year == 2023 else a24.MISSING_OPEN_MS,
        original_overlay_future_looking=year == 2024,
        original_overlay_execution_admitted=False,
        causal_mark_adapter=_immutable(sidecar)))


def _input_binding(cell, window, source_rows, decisions, targets, covariance):
    days = cell['days']
    year = cell['year']
    if (not isinstance(window, MappingProxyType)
            or type(window.get('minute_blocks')) is not _CapturedMinuteProvider
            or window['minute_blocks'].year != year or type(window.get('events')) is not tuple
            or type(source_rows) is not tuple or any(not isinstance(r, MappingProxyType) for r in source_rows)
            or not isinstance(window.get('daily'), pl.DataFrame)
            or not isinstance(decisions, np.ndarray) or decisions.dtype != np.dtype('int64')
            or decisions.shape != (days,) or decisions.flags.writeable
            or not isinstance(targets, np.ndarray) or targets.dtype != np.dtype('float64')
            or targets.shape != (days, 5) or targets.flags.writeable or not np.isfinite(targets).all()
            or not isinstance(covariance, np.ndarray) or covariance.dtype != np.dtype('float64')
            or covariance.shape != (days, 5, 5) or covariance.flags.writeable):
        raise ValueError('EXACT_IMMUTABLE_ENTRY_OWNED_CELL_INPUTS_REQUIRED')
    if (set(window) != {'start', 'end', 'symbols', 'daily', 'events', 'minute_blocks',
            'derived_mark_cells', 'original_missing_mark_open_ms', 'original_overlay_future_looking',
            'original_overlay_execution_admitted', 'causal_mark_adapter'}
            or [window['start'], window['end']] != cell['calendar']
            or tuple(window['symbols']) != a24.g.SYMBOLS
            or _sha(targets.tobytes()) != cell['selected_target_raw_SHA256']):
        raise ValueError('EXACT_CELL_CALENDAR_TARGET_WINDOW_REQUIRED')
    return dict(schema='ENTRY_OWNED_EXACT_EXPANSION_CELL_INPUT_BINDING_V1',
        cell_id=cell['cell_id'], year=year, config=cell['config'], tier=cell['tier'],
        calendar=[window['start'], window['end']], symbols=list(window['symbols']),
        decision_raw_SHA256=_sha(decisions.tobytes()), selected_target_raw_SHA256=_sha(targets.tobytes()),
        covariance_raw_SHA256=_sha(covariance.tobytes()),
        daily_rows_SHA256=_json_sha(window['daily'].to_dicts()),
        daily_schema=[[name, str(dtype)] for name, dtype in window['daily'].schema.items()],
        source_rows_SHA256=_json_sha(source_rows), funding_events_SHA256=_json_sha(window['events']),
        provider_month_identity=window['minute_blocks'].identity,
        causal_mark_adapter_SHA256=_json_sha(window['causal_mark_adapter']),
        derived_mark_cells=window['derived_mark_cells'],
        original_missing_mark_open_ms=list(window['original_missing_mark_open_ms']),
        original_overlay_future_looking=window['original_overlay_future_looking'],
        original_overlay_execution_admitted=window['original_overlay_execution_admitted'])


def _year_projection(year, source_root, artifacts, *, reconstruct=False):
    module, annual_raw, annual = _annual(year)
    if year == 2023:
        index, files, times, closes, rows, quality, payloads, months = a23._source(source_root)
        captured = {f'prepared_2023/months/{month}.npz': body for month, body in months.items()}
        captured.update({'prepared_2023/' + name: body for name, body in payloads.items()})
        rows = _immutable(rows)
        sidecar, auxiliary = _provenance_2023(source_root, captured, reconstruct=reconstruct)
        sidecar_raw = _canonical(sidecar) + b'\n'
    else:
        index, files, times, closes, rows, quality, captured = a24._source(source_root)
        sidecar_raw = artifacts['CAUSAL_MARK_ADAPTER.json']
        sidecar = _object(sidecar_raw, 'EXACT_2024_CAUSAL_ADAPTER_REQUIRED')
        if sidecar != a24._mark_adapter_receipt(captured):
            raise ValueError('EXACT_2024_CAUSAL_ADAPTER_BYTES_REQUIRED')
        auxiliary = {}
    if files != annual['source_files'] or quality != annual['original200_quality'] or module._source_identity(files, quality) != annual['source_identity']:
        raise ValueError('EXACT_FROZEN_YEAR_SOURCE_QUALITY_IDENTITY_REQUIRED')
    with np.load(BytesIO(artifacts['TARGETS.npz']), allow_pickle=False) as archive:
        if set(archive.files) != set(annual['configs']) | {'decision_us', 'annual_covariance'}:
            raise ValueError('ALL_NINE_ORIGINAL_TARGET_BYTE_PATHS_REQUIRED')
        decisions, covariance = archive['decision_us'].copy(), archive['annual_covariance'].copy()
        targets = {key: archive[key].copy() for key in annual['configs']}
    expected = np.arange(module.START, module.END, a24.g.DAY, dtype=np.int64)
    d, rebuilt, c, proofs = a24.g.build_target_grid(closes, times, times.copy(), expected)
    days = len(expected)
    if (decisions.dtype != np.dtype('int64') or decisions.shape != (days,) or decisions.tobytes() != expected.tobytes()
            or d.tobytes() != decisions.tobytes() or covariance.dtype != np.dtype('float64')
            or covariance.shape != (days, 5, 5) or c.tobytes() != covariance.tobytes()
            or any(targets[key].dtype != np.dtype('float64') or targets[key].shape != (days, 5)
                or targets[key].tobytes() != rebuilt[key].tobytes() for key in targets)):
        raise ValueError('EXACT_NINE_FROZEN_TARGET_AND_COVARIANCE_BITS_REQUIRED')
    equality = module.target_equality_receipt(decisions, targets, covariance,
        source_identity=annual['source_identity'], code=annual['code_identity'])
    if (json.loads(artifacts['TARGET_PROOFS.json']) != proofs
            or json.loads(artifacts['EXACT_EXECUTION_EQUALITY.json']) != equality
            or equality['target_identity'] != annual['target_identity']
            or equality['execution_identity'] != annual['execution_identity']):
        raise ValueError('EXACT_OLD_TARGET_PROOFS_AND_IDENTITY_REQUIRED')
    if year == 2024 and json.loads(artifacts['SOURCE_QUALIFICATION.json']) != quality:
        raise ValueError('EXACT_2024_ORIGINAL200_QUALIFICATION_REQUIRED')
    for array in (decisions, covariance, *targets.values()):
        array.setflags(write=False)
    window = _make_window(year, index, captured, sidecar)
    return dict(module=module, annual_raw=annual_raw, annual=annual, source_files=files,
        original200_quality=quality, auxiliary_source_pins=auxiliary,
        sidecar=sidecar, sidecar_raw=sidecar_raw, window=window, source_rows=rows,
        decisions=decisions, targets=targets, covariance=covariance, captured=captured)


def _load_annual_artifacts(year):
    _, raw, annual = _annual(year)
    artifacts = {name: a24.h._read_exact(ANNUAL_PREPARATIONS[year] / name, pin['SHA256'], pin['bytes'])
        for name, pin in annual['artifacts'].items()}
    artifacts['ANNUAL_SOURCE_PREPARATION.json'] = raw
    return artifacts


def _source_roots(source_roots):
    if not isinstance(source_roots, Mapping) or set(source_roots) != set(YEARS) or any(type(k) is not int for k in source_roots):
        raise ValueError('EXACT_TWO_YEAR_SOURCE_ROOT_MAPPING_REQUIRED')
    return {year: Path(source_roots[year]).resolve() for year in YEARS}


def prepare_source_only(source_roots, output_directory):
    """Capture both annual inputs, all old target paths and fixed 17 bindings.

    The caller must freeze all four new code files first. Use temporary
    directories for generated/source gates; no historical authority is produced.
    """
    roots = _source_roots(source_roots)
    output = Path(output_directory)
    if output.exists():
        raise ValueError('EXCLUSIVE_NEW_EXPANSION_PREPARATION_DIRECTORY_REQUIRED')
    code = code_identity()
    evidence = preserved_evidence_identity()
    artifacts, years, cells = {}, {}, {}
    for year in YEARS:
        original_artifacts = _load_annual_artifacts(year)
        projected = _year_projection(year, roots[year], original_artifacts, reconstruct=True)
        annual = projected['annual']
        if year == 2023:
            original_artifacts['MINUTE_MARK_PROVENANCE.json'] = projected['sidecar_raw']
        sidecar_name = f'{year}/' + ('MINUTE_MARK_PROVENANCE.json' if year == 2023 else 'CAUSAL_MARK_ADAPTER.json')
        artifacts.update({f'{year}/' + name: body for name, body in original_artifacts.items()})
        years[str(year)] = dict(year=year, calendar=annual['calendar'], days=365 if year == 2023 else 366,
            required_minutes=525600 if year == 2023 else 527040, coldstart_policy=_coldstart_policy(year),
            source_identity=annual['source_identity'], source_files=projected['source_files'],
            original200_quality=projected['original200_quality'],
            auxiliary_source_pins=projected['auxiliary_source_pins'],
            frozen_annual_preparation_SHA256=_sha(projected['annual_raw']),
            frozen_annual_code_identity=annual['code_identity'],
            frozen_annual_execution_identity=annual['execution_identity'],
            frozen_annual_target_identity=annual['target_identity'],
            original_artifact_pins=annual['artifacts'], quality_sidecar=sidecar_name,
            quality_sidecar_sha256=_sha(projected['sidecar_raw']),
            quality_intervals=[] if year == 2023 else [[a24.m.FIRST_MISSING_KNOWN, a24.m.RESUME_AVAILABLE, list(a24.g.SYMBOLS)]],
            original_genuine_observation_us=None if year == 2023 else 1723456920000000,
            decision_raw_SHA256=_sha(projected['decisions'].tobytes()),
            covariance_raw_SHA256=_sha(projected['covariance'].tobytes()))
        for cell in frozen_manifest()['cells']:
            if cell['year'] != year:
                continue
            target = projected['targets'][cell['config']]
            binding = _input_binding(cell, projected['window'], projected['source_rows'], projected['decisions'], target, projected['covariance'])
            cells[cell['cell_id']] = dict(descriptor=cell, input_binding=binding,
                input_binding_SHA256=_json_sha(binding),
                selected_target_identity=annual['target_identity']['SHA256_by_config'][cell['config']],
                selected_target_raw_SHA256=_sha(target.tobytes()),
                decision_raw_SHA256=_sha(projected['decisions'].tobytes()),
                covariance_raw_SHA256=_sha(projected['covariance'].tobytes()),
                quality_sidecar_sha256=years[str(year)]['quality_sidecar_sha256'])
    pins = {name: dict(SHA256=_sha(body), bytes=len(body)) for name, body in artifacts.items()}
    policy = _policy(code)
    prep = dict(schema=PREPARATION_SCHEMA, policy_version=POLICY_VERSION, source_scope=SOURCE_SCOPE,
        status='PREPARED_SOURCE_TARGET_ONLY_NO_HISTORICAL_ACCOUNT_OR_GO',
        manifest_SHA256=MANIFEST_SHA256, manifest=frozen_manifest(), years=years, cells=cells,
        ordered_cells=[cell['cell_id'] for cell in frozen_manifest()['cells']],
        cost=COST, modes=list(MODES), settlement_mode=SETTLEMENT_MODE,
        resource_limits=RESOURCE_LIMITS, resource_execution_contract=RESOURCE_EXECUTION_CONTRACT, launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,
        code_identity=code, policy=policy, policy_identity=_json_sha(policy),
        artifacts=pins, preserved_evidence_pins=evidence, preserved_old_root_GO_is_new_authority=False,
        all_inputs_seen_development=True, performance_selection_allowed=False,
        original_interpolated_mark_execution_admitted=False,
        accounts_created=0, accounts_advanced=0, historical_market_minutes_advanced=0,
        annual_returns_computed=False, financial_runs=0, outcomes_inspected=False,
        locked_or_holdout_consumed=False, other_years_or_2025_authorized=False,
        publication_actions=0, historical_admission=False,
        annual_execution_requires_new_exact_external_root_GO=True, execution_label=LABEL)
    if code_identity() != code or preserved_evidence_identity() != evidence:
        raise ValueError('CODE_OR_EVIDENCE_CHANGED_DURING_SOURCE_PREPARATION')
    _validate_preparation(_canonical(prep))
    output.mkdir(parents=True)
    for name, body in artifacts.items():
        destination = output / name
        destination.parent.mkdir(exist_ok=True)
        with destination.open('xb') as stream:
            stream.write(body)
    with (output / 'PREPARATION.json').open('xb') as stream:
        stream.write(json.dumps(prep, indent=2, allow_nan=False).encode() + b'\n')
    return prep


def _validate_preparation(raw):
    prep = _object(raw, 'EXACT_EXPANSION_PREPARATION_BYTES_REQUIRED')
    required = dict(schema=PREPARATION_SCHEMA, policy_version=POLICY_VERSION, source_scope=SOURCE_SCOPE,
        status='PREPARED_SOURCE_TARGET_ONLY_NO_HISTORICAL_ACCOUNT_OR_GO',
        manifest_SHA256=MANIFEST_SHA256, manifest=frozen_manifest(),
        ordered_cells=[cell['cell_id'] for cell in frozen_manifest()['cells']],
        cost=COST, modes=list(MODES), settlement_mode=SETTLEMENT_MODE, resource_limits=RESOURCE_LIMITS,
        resource_execution_contract=RESOURCE_EXECUTION_CONTRACT, launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,
        preserved_evidence_pins=preserved_evidence_identity(), preserved_old_root_GO_is_new_authority=False,
        all_inputs_seen_development=True, performance_selection_allowed=False,
        original_interpolated_mark_execution_admitted=False,
        accounts_created=0, accounts_advanced=0, historical_market_minutes_advanced=0,
        annual_returns_computed=False, financial_runs=0, outcomes_inspected=False,
        locked_or_holdout_consumed=False, other_years_or_2025_authorized=False,
        publication_actions=0, historical_admission=False,
        annual_execution_requires_new_exact_external_root_GO=True, execution_label=LABEL)
    if (any(not _same(prep.get(key), value) for key, value in required.items())
            or not isinstance(prep.get('code_identity'), dict)
            or not _same(prep.get('policy'), _policy(prep['code_identity']))
            or prep.get('policy_identity') != _json_sha(prep['policy'])
            or set(prep.get('years', {})) != {'2023', '2024'}
            or set(prep.get('cells', {})) != set(required['ordered_cells'])):
        raise ValueError('EXACT_FROZEN_EXPANSION_PREPARATION_SCOPE_REQUIRED')
    expected_artifacts = {}
    for year in YEARS:
        module, annual_raw, annual = _annual(year)
        info = prep['years'][str(year)]
        equality_pin = annual['artifacts']['EXACT_EXECUTION_EQUALITY.json']
        equality = _object(a24.h._read_exact(ANNUAL_PREPARATIONS[year] / 'EXACT_EXECUTION_EQUALITY.json',
            equality_pin['SHA256'], equality_pin['bytes']), 'EXACT_FROZEN_EXECUTION_EQUALITY_REQUIRED')
        static = dict(year=year, calendar=annual['calendar'], days=365 if year == 2023 else 366,
            required_minutes=525600 if year == 2023 else 527040, coldstart_policy=_coldstart_policy(year),
            decision_raw_SHA256=equality['decision_raw_SHA256'],
            covariance_raw_SHA256=equality['annual_covariance_raw_SHA256'],
            source_identity=annual['source_identity'], source_files=annual['source_files'],
            original200_quality=annual['original200_quality'],
            frozen_annual_preparation_SHA256=_sha(annual_raw), frozen_annual_code_identity=annual['code_identity'],
            frozen_annual_execution_identity=annual['execution_identity'], frozen_annual_target_identity=annual['target_identity'],
            original_artifact_pins=annual['artifacts'],
            quality_sidecar=f'{year}/' + ('MINUTE_MARK_PROVENANCE.json' if year == 2023 else 'CAUSAL_MARK_ADAPTER.json'),
            quality_intervals=[] if year == 2023 else [[a24.m.FIRST_MISSING_KNOWN, a24.m.RESUME_AVAILABLE, list(a24.g.SYMBOLS)]],
            original_genuine_observation_us=None if year == 2023 else 1723456920000000)
        if any(not _same(info.get(key), value) for key, value in static.items()):
            raise ValueError('EXACT_YEAR_SOURCE_TARGET_QUALITY_PREPARATION_REQUIRED')
        expected_artifacts.update({f'{year}/' + name: pin for name, pin in annual['artifacts'].items()})
        expected_artifacts[f'{year}/ANNUAL_SOURCE_PREPARATION.json'] = dict(SHA256=_sha(annual_raw), bytes=len(annual_raw))
        if year == 2024:
            if (info.get('quality_sidecar_sha256') != annual['artifacts']['CAUSAL_MARK_ADAPTER.json']['SHA256']
                    or info.get('auxiliary_source_pins') != {}):
                raise ValueError('EXACT_2024_QUALITY_INTERVAL_SIDECAR_REQUIRED')
        else:
            auxiliary = info.get('auxiliary_source_pins')
            if not isinstance(auxiliary, dict) or any(auxiliary.get(name, {}).get('SHA256') != digest for name, digest in PROVENANCE_2023_PINS.items()):
                raise ValueError('EXPLICIT_2023_RAW_MARK_PROVENANCE_REQUIRED')
            expected_artifacts['2023/MINUTE_MARK_PROVENANCE.json'] = prep['artifacts'].get('2023/MINUTE_MARK_PROVENANCE.json')
            if info.get('quality_sidecar_sha256') != expected_artifacts['2023/MINUTE_MARK_PROVENANCE.json']['SHA256']:
                raise ValueError('EXACT_2023_EMPTY_INTERVAL_PROVENANCE_SIDECAR_REQUIRED')
    if not _same(prep.get('artifacts'), expected_artifacts):
        raise ValueError('EXACT_UNCHANGED_ORIGINAL_ARTIFACT_BYTE_PINS_REQUIRED')
    for cell in frozen_manifest()['cells']:
        value = prep['cells'][cell['cell_id']]
        year = prep['years'][str(cell['year'])]
        binding = value.get('input_binding')
        if (not _same(value.get('descriptor'), cell) or not isinstance(binding, dict)
                or value.get('input_binding_SHA256') != _json_sha(binding)
                or value.get('selected_target_raw_SHA256') != cell['selected_target_raw_SHA256']
                or value.get('selected_target_identity') != year['frozen_annual_target_identity']['SHA256_by_config'][cell['config']]
                or value.get('decision_raw_SHA256') != year['decision_raw_SHA256']
                or value.get('covariance_raw_SHA256') != year['covariance_raw_SHA256']
                or value.get('quality_sidecar_sha256') != year['quality_sidecar_sha256']
                or any(not _same(binding.get(key), expected) for key, expected in dict(
                    cell_id=cell['cell_id'], year=cell['year'], config=cell['config'], tier=cell['tier'], calendar=cell['calendar'],
                    selected_target_raw_SHA256=cell['selected_target_raw_SHA256'], decision_raw_SHA256=year['decision_raw_SHA256'],
                    covariance_raw_SHA256=year['covariance_raw_SHA256']).items())):
            raise ValueError('EXACT_FIXED_CELL_TARGET_INPUT_BINDING_REQUIRED')
    return prep


def _authorization_common(preparation_raw, prep):
    return dict(policy_version=POLICY_VERSION, source_scope=SOURCE_SCOPE,
        preparation_SHA256=_sha(preparation_raw), manifest_SHA256=MANIFEST_SHA256,
        ordered_manifest_cells=prep['ordered_cells'], cost=COST, modes=list(MODES),
        settlement_mode=SETTLEMENT_MODE, code_identity=prep['code_identity'], policy_identity=prep['policy_identity'],
        artifacts=prep['artifacts'], years=prep['years'], cells=prep['cells'], resource_limits=RESOURCE_LIMITS,
        resource_execution_contract=RESOURCE_EXECUTION_CONTRACT, launch_claim_contract=LAUNCH_CLAIM_CONTRACT,
        global_controller_lease_contract=GLOBAL_CONTROLLER_LEASE_CONTRACT,
        preserved_evidence_pins=prep['preserved_evidence_pins'], preserved_old_root_GO_is_new_authority=False,
        all_inputs_seen_development=True, performance_selection_allowed=False,
        reused_2024_STATIC50_MID_rerun_authorized=False,
        original_interpolated_mark_execution_admitted=False,
        other_years_or_2025_authorized=False, locked_or_holdout_consumed=False,
        publication_authorized=False, fresh_genesis_only=True,
        automatic_retry_authorized=False, halted_snapshot_resume_authorized=False)


def validate_root_go(preparation_raw, go_raw, expected_go_sha256, *, cell_id, policy_variant=POLICY_VARIANT):
    cell_descriptor(cell_id)
    _exact(go_raw, expected_go_sha256, 'EXACT_NEW_EXTERNAL_EXPANSION_ROOT_GO_REQUIRED')
    prep = _validate_preparation(preparation_raw)
    go = _object(go_raw, 'EXACT_EXPANSION_ROOT_GO_OBJECT_REQUIRED')
    required = dict(schema=GO_SCHEMA, action='RUN_FRESH_EXACT_ORDERED_EXPANSION_TRANCHE_ONLY', **_authorization_common(preparation_raw, prep))
    tranche = go.get('tranche', FIRST_TRANCHE)
    permitted = go.get('permitted_cells')
    expected = list(tranche_cells(tranche))
    workers = go.get('requested_worker_count')
    cpus = go.get('worker_CPUs')
    review_sha = go.get('independent_review_SHA256')
    if (policy_variant != POLICY_VARIANT
            or any(not _same(go.get(key), value) for key, value in required.items())
            or not _same(permitted, expected) or cell_id not in expected
            or type(workers) is not int or workers not in (1, 2)
            or not isinstance(cpus, list) or len(cpus) != workers
            or any(type(cpu) is not int or cpu < 0 for cpu in cpus) or len(set(cpus)) != workers
            or not isinstance(review_sha, str) or len(review_sha) != 64
            or any(c not in '0123456789abcdef' for c in review_sha)
            or expected_go_sha256 in prep['preserved_evidence_pins'].values()):
        raise ValueError('EXACT_NEW_ROOT_GO_ORDERED_TRANCHE_CELL_RESOURCE_SCOPE_REQUIRED')
    return prep


def _validate_independent_review(preparation_raw, prep, review_raw, expected_review_sha256, go_raw):
    _exact(review_raw, expected_review_sha256, 'EXACT_NEW_EXTERNAL_EXPANSION_REVIEW_REQUIRED')
    review = _object(review_raw, 'EXACT_EXPANSION_REVIEW_OBJECT_REQUIRED')
    go = _object(go_raw, 'EXACT_EXPANSION_ROOT_GO_OBJECT_REQUIRED')
    required = dict(schema=REVIEW_SCHEMA, status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        **_authorization_common(preparation_raw, prep),
        generated_native_scheduler_phase_order_passed=True, generated_shared_pending_32_corner_passed=True,
        generated_preview_isolation_passed=True, generated_causal_quality_passed=True,
        generated_terminal_taxonomy_passed=True, generated_unknown_quality_no_new_exit_passed=True,
        generated_guard50_paid_exit_no_topup_passed=True,
        generated_exact_cell_year_tier_target_quality_gates_passed=True,
        generated_frozen_manifest_and_ordered_tranche_gates_passed=True,
        generated_pool_resource_and_aggregate_pressure_gates_passed=True,
        generated_canonical_launch_claim_duplicate_and_existing_output_gates_passed=True,
        generated_global_controller_lease_inherited_worker_FD_gates_passed=True,
        generated_helper_thread_affinity_and_compute_pool_contract_passed=True,
        generated_actual_held_exposure_forecast_overshoot_reporting_passed=True,
        actual_2023_2024_accounts_constructed=0, actual_2023_2024_financial_runs=0,
        historical_market_minutes_advanced=0, publication_actions=0, locked_source_reads=0)
    if (go.get('independent_review_SHA256') != expected_review_sha256
            or expected_review_sha256 in prep['preserved_evidence_pins'].values()
            or any(not _same(review.get(key), value) for key, value in required.items())):
        raise ValueError('EXACT_NEW_EXPANSION_INDEPENDENT_REVIEW_SCOPE_REQUIRED')
    return review


def validate_case_inputs(source_roots, preparation_directory, go_raw, expected_go_sha256, *, cell_id, policy_variant=POLICY_VARIANT):
    roots = _source_roots(source_roots)
    directory = Path(preparation_directory)
    raw = _ordinary(directory / 'PREPARATION.json')
    prep = validate_root_go(raw, go_raw, expected_go_sha256, cell_id=cell_id, policy_variant=policy_variant)
    if prep['code_identity'] != code_identity():
        raise ValueError('EXPANSION_CODE_CHANGED_SINCE_PREPARATION')
    artifacts = {name: a24.h._read_exact(directory / name, pin['SHA256'], pin['bytes']) for name, pin in prep['artifacts'].items()}
    cell = cell_descriptor(cell_id)
    year = cell['year']
    annual_artifacts = {name[len(str(year)) + 1:]: body for name, body in artifacts.items() if name.startswith(f'{year}/')}
    projected = _year_projection(year, roots[year], annual_artifacts)
    info = prep['years'][str(year)]
    if (projected['source_files'] != info['source_files']
            or projected['auxiliary_source_pins'] != info['auxiliary_source_pins']
            or _sha(projected['sidecar_raw']) != info['quality_sidecar_sha256']):
        raise ValueError('EXACT_YEAR_SOURCE_OR_AUXILIARY_MARK_PROVENANCE_CHANGED')
    target = projected['targets'][cell['config']]
    binding = _input_binding(cell, projected['window'], projected['source_rows'], projected['decisions'], target, projected['covariance'])
    if not _same(binding, prep['cells'][cell_id]['input_binding']):
        raise ValueError('EXACT_SELECTED_CELL_INPUT_PROVIDER_QUALITY_BINDING_REQUIRED')
    return prep, projected['window'], projected['source_rows'], projected['decisions'], target, projected['captured']


@dataclass(frozen=True, slots=True)
class CaseExecutionScope:
    cell_id: str
    year: int
    strategy: str
    tier_name: str
    config: str
    preparation_SHA256: str
    source_identity: str
    code_identity_SHA256: str
    policy_identity: str
    independent_review_SHA256: str
    root_GO_SHA256: str
    quality_intervals: tuple
    quality_sidecar_sha256: str
    original_genuine_observation_us: object
    policy_variant: str
    _source_root: Path = field(repr=False)
    _preparation_directory: Path = field(repr=False)
    _preparation_raw: bytes = field(repr=False)
    _review_raw: bytes = field(repr=False)
    _go_raw: bytes = field(repr=False)
    _source_pins: tuple = field(repr=False)
    _bound_window: object = field(repr=False, compare=False)
    _bound_source_rows: tuple = field(repr=False, compare=False)
    _bound_decisions: object = field(repr=False, compare=False)
    _bound_targets: object = field(repr=False, compare=False)
    _bound_covariance: object = field(repr=False, compare=False)
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _SCOPE_SEAL:
            raise ValueError('SCOPE_ONLY_FROM_EXACT_NEW_EXPANSION_ADMISSION')

    def __deepcopy__(self, memo):
        memo[id(self)] = self
        return self

    @property
    def source_scope(self):
        return SOURCE_SCOPE

    @property
    def mode(self):
        return self.policy_variant

    @property
    def metadata(self):
        # Return ordinary clone-safe plaintext containers. Mutating a returned
        # metadata object does not change the sealed scope or its authority.
        cell = cell_descriptor(self.cell_id)
        return dict(source_scope=SOURCE_SCOPE, policy_version=POLICY_VERSION, cell_id=self.cell_id,
            year=self.year, strategy=self.strategy, tier_name=self.tier_name, config=self.config,
            preparation_SHA256=self.preparation_SHA256, source_identity=self.source_identity,
            code_identity_SHA256=self.code_identity_SHA256, policy_identity=self.policy_identity,
            independent_review_SHA256=self.independent_review_SHA256, root_GO_SHA256=self.root_GO_SHA256,
            policy_variant=self.policy_variant, manifest_SHA256=MANIFEST_SHA256,
            calendar=list(cell['calendar']), days=cell['days'], required_minutes=cell['required_minutes'],
            cost=COST, settlement_mode=SETTLEMENT_MODE, fresh_genesis_only=True, generated_fixture_scope_used=False,
            coldstart_policy=_coldstart_policy(self.year),
            quality_intervals=_plain(self.quality_intervals), quality_sidecar_sha256=self.quality_sidecar_sha256,
            original_genuine_observation_us=self.original_genuine_observation_us,
            input_binding_SHA256=_json_sha(_input_binding(cell, self._bound_window, self._bound_source_rows,
                self._bound_decisions, self._bound_targets, self._bound_covariance)))

    def validate_inputs(self, window, source_rows, decisions, targets):
        if (self._seal is not _SCOPE_SEAL or window is not self._bound_window
                or source_rows is not self._bound_source_rows or decisions is not self._bound_decisions
                or targets is not self._bound_targets):
            raise ValueError('EXACT_ENTRY_OWNED_CELL_INPUT_REFERENCES_REQUIRED')
        prep = _object(self._preparation_raw, 'EXACT_SCOPE_PREPARATION_REQUIRED')
        cell = cell_descriptor(self.cell_id)
        binding = _input_binding(cell, window, source_rows, decisions, targets, self._bound_covariance)
        if (not _same(binding, prep['cells'][self.cell_id]['input_binding'])
                or _json_sha(binding) != prep['cells'][self.cell_id]['input_binding_SHA256']):
            raise ValueError('BOUND_CELL_SOURCE_TARGET_PROVIDER_OR_QUALITY_CHANGED')
        return True

    def validate_current(self):
        if self._seal is not _SCOPE_SEAL:
            raise ValueError('UNSEALED_EXPANSION_CASE_SCOPE')
        raw = _ordinary(self._preparation_directory / 'PREPARATION.json')
        if raw != self._preparation_raw or _sha(raw) != self.preparation_SHA256:
            raise ValueError('BOUND_EXPANSION_PREPARATION_CHANGED')
        prep = validate_root_go(raw, self._go_raw, self.root_GO_SHA256,
            cell_id=self.cell_id, policy_variant=self.policy_variant)
        _validate_independent_review(raw, prep, self._review_raw, self.independent_review_SHA256, self._go_raw)
        cell = cell_descriptor(self.cell_id)
        info = prep['years'][str(cell['year'])]
        pins = {**info['source_files'], **info['auxiliary_source_pins']}
        if (self.year != cell['year'] or self.config != cell['config'] or self.strategy != cell['strategy']
                or self.tier_name != cell['tier'] or self.source_identity != info['source_identity']
                or self.quality_intervals != _immutable(info['quality_intervals'])
                or self.quality_sidecar_sha256 != info['quality_sidecar_sha256']
                or self.original_genuine_observation_us != info['original_genuine_observation_us']
                or self._source_pins != tuple((name, pin['SHA256'], pin['bytes']) for name, pin in sorted(pins.items()))
                or self.policy_identity != prep['policy_identity']
                or self.code_identity_SHA256 != _json_sha(prep['code_identity'])
                or prep['code_identity'] != code_identity()):
            raise ValueError('BOUND_EXPANSION_CELL_YEAR_TIER_SOURCE_QUALITY_OR_CODE_CHANGED')
        for name, digest, size in self._source_pins:
            a24.h._read_exact(self._source_root / name, digest, size)
        for name, pin in prep['artifacts'].items():
            a24.h._read_exact(self._preparation_directory / name, pin['SHA256'], pin['bytes'])
        self.validate_inputs(self._bound_window, self._bound_source_rows, self._bound_decisions, self._bound_targets)
        return True


def _default_constructor_callback(*, scope, preparation, window, source_rows, decisions, targets, captured):
    integration = importlib.import_module('expansion')
    if Path(integration.__file__).resolve() != HERE / 'expansion.py':
        raise ValueError('EXACT_LOCAL_EXPANSION_CALLBACK_MODULE_REQUIRED')
    return integration.construct_case(window, source_rows, decisions, targets,
        policy_variant=POLICY_VARIANT, historical_scope=scope, quality_intervals=scope.quality_intervals)


def make_case(source_roots, preparation_directory, go_raw, expected_go_sha256, *, cell_id,
        policy_variant=POLICY_VARIANT, review_raw=None, expected_review_sha256=None, constructor_callback=None):
    roots = _source_roots(source_roots)
    raw = _ordinary(Path(preparation_directory) / 'PREPARATION.json')
    prep = validate_root_go(raw, go_raw, expected_go_sha256, cell_id=cell_id, policy_variant=policy_variant)
    _validate_independent_review(raw, prep, review_raw, expected_review_sha256, go_raw)
    prep, window, rows, decisions, targets, captured = validate_case_inputs(roots,
        preparation_directory, go_raw, expected_go_sha256, cell_id=cell_id, policy_variant=policy_variant)
    cell = cell_descriptor(cell_id)
    info = prep['years'][str(cell['year'])]
    with np.load(BytesIO(_ordinary(Path(preparation_directory) / f"{cell['year']}/TARGETS.npz")), allow_pickle=False) as z:
        covariance = z['annual_covariance'].copy()
    covariance.setflags(write=False)
    pins = {**info['source_files'], **info['auxiliary_source_pins']}
    scope = CaseExecutionScope(cell_id=cell_id, year=cell['year'], strategy=cell['strategy'], tier_name=cell['tier'],
        config=cell['config'], preparation_SHA256=_sha(raw), source_identity=info['source_identity'],
        code_identity_SHA256=_json_sha(prep['code_identity']), policy_identity=prep['policy_identity'],
        independent_review_SHA256=expected_review_sha256, root_GO_SHA256=expected_go_sha256,
        policy_variant=policy_variant, quality_intervals=_immutable(info['quality_intervals']),
        quality_sidecar_sha256=info['quality_sidecar_sha256'], original_genuine_observation_us=info['original_genuine_observation_us'],
        _source_root=roots[cell['year']], _preparation_directory=Path(preparation_directory).resolve(),
        _preparation_raw=raw, _review_raw=review_raw, _go_raw=go_raw,
        _source_pins=tuple((name, pin['SHA256'], pin['bytes']) for name, pin in sorted(pins.items())),
        _bound_window=window, _bound_source_rows=rows, _bound_decisions=decisions,
        _bound_targets=targets, _bound_covariance=covariance, _seal=_SCOPE_SEAL)
    scope.validate_current()
    callback = constructor_callback or _default_constructor_callback
    return callback(scope=scope, preparation=prep, window=window, source_rows=rows,
        decisions=decisions, targets=targets, captured=captured)
