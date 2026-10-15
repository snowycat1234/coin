"""Source-only finite preparation and separately authorized historical boundary.

No account, runtime, clock, return or historical job is created by preparation.
The old annual entry's exact source/target functions are reused without its GO
or constructor. Historical construction is delegated only after an exact new
independent review and exact external root-GO byte binding have both passed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections.abc import Mapping
from io import BytesIO
import hashlib
import importlib
import json
from pathlib import Path
import sys
from types import MappingProxyType

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FROZEN = ROOT / 'traditional_three_tier_freeze_20261015'
PRIMITIVE = ROOT / 'bounded_account_continuation_20261015'
if str(FROZEN) not in sys.path:
    sys.path.insert(0, str(FROZEN))
import annual_entry_2024 as a

START, END, DAYS, MINUTES = a.START, a.END, a.DAYS, a.MINUTES
CONFIG, COST = 'STATIC50_MID', 'BASE27'
MODES = ('CONTINUE_ONLY', 'TOPUP_THEN_CONTINUE')
MODE_LABELS = {'B': MODES[0], 'C': MODES[1]}
SETTLEMENT_MODE = 'CONDITIONAL_COLLATERAL_FORFEITURE'
POLICY_VERSION = 'BOUNDED_NATIVE_CONTINUATION_FULL2024_STATIC50_MID_V1'
SOURCE_SCOPE = 'ROOT_ADMITTED_FRESH_FINITE_FULL2024_BOUNDED_NATIVE_CONTINUATION_CAUSAL_MARKS'
LABEL = a.LABEL
RESOURCE_LIMITS = dict(per_case_wall_seconds=600, CPU_threads=1,
    RSS_stop_bytes=2_000_000_000, AS_bytes=4_000_000_000,
    output_bytes=250_000_000, maximum_cases=2)
INTEGRATION_FILES = ('integration.py', 'run_finite.py')
ANNUAL_PREPARATION = FROZEN / 'annual_2024_source_preparation_attempt002'
ANNUAL_PREPARATION_PIN = (10673, '657317bb8c025d8ab926e66a57078bfcf2a8d684be6dcc40a0ac8e7502b29b46')
ARTIFACTS = tuple(a.ARTIFACTS) + ('ANNUAL_SOURCE_PREPARATION.json',)
PREPARATION_SCHEMA = 'SOURCE_TARGET_ONLY_BOUNDED_NATIVE_CONTINUATION_FULL2024_STATIC50_MID_V1'
REVIEW_SCHEMA = 'INDEPENDENT_BOUNDED_NATIVE_CONTINUATION_SOURCE_GENERATED_REVIEW_V1'
GO_SCHEMA = 'ROOT_GO_BOUNDED_NATIVE_CONTINUATION_FULL2024_STATIC50_MID_V1'

# These are preserved provenance, never authority to run a new account.
PRESERVED_EVIDENCE_PINS = {
 'traditional_three_tier_freeze_20261015/root_go_2024_pilot_attempt001.json': 'a6a3f4b36a7fe008d99a140b32bc41a86f14c8bae281f068aac3b684c8a43851',
 'traditional_three_tier_freeze_20261015/root_go_2024_remaining_attempt001.json': 'ab8f768beef74b0d45d8231a743fa5d25a919a6230cb166a71fd56d891e9a4b7',
 'traditional_three_tier_independent_review_20261015/SOURCE_2024_FINAL_INDEPENDENT_REVIEW_RECEIPT.json': '493683d02e060a1e0015df0963e66effa11eddb95582b17cd43b9e7463b942bd',
 'traditional_three_tier_independent_review_20261015/SOURCE_2024_COMBINED_SOURCE_DRIVER_REVIEW_RECEIPT.json': '6236c593b24d3086183a362e7c57dc74604185f8b703e0e6952636e2b92f81d1',
 'traditional_three_tier_independent_review_20261015/SOURCE_2024_ECONOMIC_TERMINAL_V2_COMBINED_REVIEW_RECEIPT.json': 'dcee8ff39a077a58bf85a21aaca937f678faef19f5d13aa8542a2863edbf3219',
 'traditional_three_tier_independent_review_20261015/SOURCE_2024_INDEPENDENT_INPUT_PROOF_REVIEW.json': '2b559e18b16be1a7389ce7fface0e6795aefa10d26c783a21c998b1d389e5c49',
 'bounded_account_continuation_independent_review_20261015/REVIEW.json': 'aa6e4ca724e3339eefc52070b30779b7d273e6f8f9b9c5faad6a47176779d3d5',
}
PRIMITIVE_CODE_PINS = {
 'continuation.py': 'bf8c3df52420af95ac1b2528e75c9ad7268ccdd2e56bbacf3baa2c39e7c562a8',
 'POLICY.json': 'f8a5313a0f538f13a38e738737bb489d66ee47f934bd61d84198c0a860e023b1',
 'PRIMITIVE_PINS.json': 'b715ed772ab61530a3195d559af2ea8fc8fce0e75b43ece82825c0839833951f',
 'headroom_buffer.py': '2ab4158bf610c0075bc901b4ba0a649eed5b993251090bf54bbaa5332f1dfb39',
 'QUANTITY_PROFILE.json': '94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf',
 'vendor_quant/perpetual_account.py': '14916598f3dab6a631b89317b38be9a3740549cb7882acf02b8a80658c64433c',
 'vendor_quant/execution_contract.py': 'b7fc110d84240233611e2f7e7360c1b7cc5c92308f842a796560964db33f97d1',
 'vendor_quant/bybit_isolated_account.py': '54c7d9ff823d8c2f95e6d0e96973c1fea95afd15148a1c196d61a2d342246c42',
}
_SCOPE_SEAL = object()


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _json_sha(value):
    return _sha(_canonical(value))


def _same(left, right):
    # JSON structural identity distinguishes bools from integers.
    return _canonical(left) == _canonical(right)


def _object(raw, error):
    if not isinstance(raw, bytes):
        raise ValueError(error)
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(error)
            result[key] = value
        return result
    try:
        value = json.loads(raw, object_pairs_hook=reject_duplicates,
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(error)))
    except (ValueError, TypeError, UnicodeDecodeError) as exc:
        raise ValueError(error) from exc
    if not isinstance(value, dict):
        raise ValueError(error)
    return value


def _exact(raw, expected, error):
    if (not isinstance(raw, bytes) or not isinstance(expected, str)
            or len(expected) != 64 or any(c not in '0123456789abcdef' for c in expected)
            or _sha(raw) != expected):
        raise ValueError(error)


def _ordinary(path):
    path = Path(path)
    if path.is_symlink() or any(p.is_symlink() for p in path.parents) or not path.is_file():
        raise ValueError('ORDINARY_PINNED_CONTINUATION_FILE_REQUIRED')
    return path.read_bytes()


def preserved_evidence_identity():
    for name, digest in PRESERVED_EVIDENCE_PINS.items():
        a.h._read_exact(ROOT / name, digest)
    return dict(PRESERVED_EVIDENCE_PINS)


def _frozen_preparation(directory=ANNUAL_PREPARATION):
    size, digest = ANNUAL_PREPARATION_PIN
    raw = a.h._read_exact(Path(directory) / 'PREPARATION.json', digest, size)
    prep = _object(raw, 'EXACT_FROZEN_SOURCE_PREPARATION_REQUIRED')
    if (prep['code_identity'] != a.code_identity()
            or prep['calendar'] != [START, END] or prep['cost'] != COST
            or prep['source_identity'] != '3794f1d1502740816bb1ac31096e60a4720d1b7a19d588150fd469ef1515966b'
            or prep['accounts_created'] != 0 or prep['annual_returns_computed'] is not False
            or prep['original_interpolated_mark_execution_admitted'] is not False
            or set(prep['artifacts']) != set(a.ARTIFACTS)):
        raise ValueError('FROZEN_SOURCE_TARGET_QUALITY_OR_CODE_PINS_CHANGED')
    return raw, prep


def code_identity():
    _, baseline = _frozen_preparation()
    result = {'traditional_three_tier_freeze_20261015/' + name: digest
        for name, digest in baseline['code_identity'].items()}
    for name, digest in PRIMITIVE_CODE_PINS.items():
        a.h._read_exact(PRIMITIVE / name, digest)
        result['bounded_account_continuation_20261015/' + name] = digest
    for name in ('continuation_entry.py',) + INTEGRATION_FILES:
        result['bounded_native_continuation_20261015/' + name] = _sha(_ordinary(HERE / name))
    return result


def _policy(code):
    return dict(version=POLICY_VERSION, config=CONFIG, cost=COST, calendar=[START, END],
        modes=list(MODES), mode_labels=MODE_LABELS, settlement_mode=SETTLEMENT_MODE,
        primitive_policy_SHA256=PRIMITIVE_CODE_PINS['POLICY.json'],
        primitive_continuation_SHA256=PRIMITIVE_CODE_PINS['continuation.py'],
        quantity_profile_SHA256=PRIMITIVE_CODE_PINS['QUANTITY_PROFILE.json'],
        code_identity=code, resource_limits=RESOURCE_LIMITS,
        initial_shared_wallet_USDT='10000', leverage=1,
        common_free_cash_floor_USDT='1000', common_isolated_margin_ceiling_USDT='8500',
        B_has_no_Guard50_warning_transfer_or_exit=True,
        C_minus_B_attribution='WHOLE_BOUNDED_MARGIN_MANAGEMENT_PACKAGE_NOT_PURE_TOPUP_TRANSFER',
        actual_native_liquidation_or_insurance_certified=False,
        unchanged_frozen_V3_risk_source_coarse_profile_and_causal_quality=True,
        coldstart_policy=a._protocol()['coldstart_policy'])


def _source_projection(source_root, annual_raw, annual, artifacts):
    """Use only old source-only functions, never annual GO or finance entry."""
    index, files, times, closes, rows, quality, captured = a._source(source_root)
    if (files != annual['source_files'] or quality != annual['original200_quality']
            or a._source_identity(files, quality) != annual['source_identity']):
        raise ValueError('UNCHANGED_EXACT_FULL2024_SOURCE_QUALITY_REQUIRED')
    with np.load(BytesIO(artifacts['TARGETS.npz']), allow_pickle=False) as archive:
        if set(archive.files) != set(annual['configs']) | {'decision_us', 'annual_covariance'}:
            raise ValueError('EXACT_FROZEN_NINE_TARGET_WITNESS_REQUIRED')
        decisions = archive['decision_us'].copy()
        covariance = archive['annual_covariance'].copy()
        targets = {key: archive[key].copy() for key in annual['configs']}
    expected_decisions = np.arange(START, END, a.g.DAY, dtype=np.int64)
    d, rebuilt, c, proofs = a.g.build_target_grid(closes, times, times.copy(), expected_decisions)
    if (decisions.dtype != np.dtype('int64') or decisions.shape != (DAYS,)
            or decisions.tobytes() != expected_decisions.tobytes()
            or d.tobytes() != decisions.tobytes()
            or covariance.dtype != np.dtype('float64') or covariance.shape != (DAYS, 5, 5)
            or covariance.tobytes() != c.tobytes()
            or any(targets[key].dtype != np.dtype('float64') or targets[key].shape != (DAYS, 5)
                or targets[key].tobytes() != rebuilt[key].tobytes() for key in targets)):
        raise ValueError('EXACT_FULL366_TARGET_AND_COVARIANCE_BITS_REQUIRED')
    equality = a.target_equality_receipt(decisions, targets, covariance,
        source_identity=annual['source_identity'], code=annual['code_identity'])
    if (json.loads(artifacts['TARGET_PROOFS.json']) != proofs
            or json.loads(artifacts['SOURCE_QUALIFICATION.json']) != quality
            or json.loads(artifacts['EXACT_EXECUTION_EQUALITY.json']) != equality
            or equality['target_identity'] != annual['target_identity']
            or equality['execution_identity'] != annual['execution_identity']
            or json.loads(artifacts['CAUSAL_MARK_ADAPTER.json']) != a._mark_adapter_receipt(captured)):
        raise ValueError('UNCHANGED_SOURCE_ONLY_TARGET_AND_CAUSAL_QUALITY_PROOF_REQUIRED')
    decisions.setflags(write=False)
    target = targets[CONFIG]
    target.setflags(write=False)
    covariance.setflags(write=False)
    return index, files, quality, rows, decisions, target, covariance, captured


def _load_annual_artifacts(directory, annual):
    return {name: a.h._read_exact(Path(directory) / name, pin['SHA256'], pin['bytes'])
        for name, pin in annual['artifacts'].items()}


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


@dataclass(frozen=True, slots=True)
class _CapturedMinuteProvider:
    """Immutable source bytes and fixed month clocks, with no late file reads."""
    months: tuple = field(repr=False)

    @property
    def identity(self):
        return [[name, start, count, _sha(body), len(body)]
            for name, start, count, body in self.months]

    def __call__(self):
        expected = START
        for name, start, count, body in self.months:
            if start != expected:
                raise ValueError('EXACT_CAPTURED_CONTINUATION_MONTH_ORDER_REQUIRED')
            arrays = a._month_arrays(body, start, count)
            arrays, _ = a.m.project_month(arrays)
            stamps = arrays['times']
            for offset in range(0, len(stamps), 1440):
                yield dict(times=stamps[offset:offset + 1440], market={symbol: {
                    key: arrays[symbol + '_' + key][offset:offset + 1440]
                    for key in ('open', 'close', 'quote_volume', 'mark')}
                    for symbol in a.g.SYMBOLS})
            expected += count * a.n.MINUTE
        if expected != END:
            raise ValueError('EXACT_FULL2024_CAPTURED_CONTINUATION_PROVIDER_END_REQUIRED')


def _make_window(index, captured, adapter):
    months = []
    start = START
    for record in index['months']:
        name = 'prepared_2024/months/' + record['month'] + '.npz'
        months.append((name, start, record['minutes'], captured[name]))
        start += record['minutes'] * a.n.MINUTE
    return MappingProxyType(dict(start=START, end=END, symbols=a.g.SYMBOLS,
        daily=pl.DataFrame(json.loads(captured['prepared_2024/DAILY.json'])),
        events=_immutable(json.loads(captured['prepared_2024/EVENTS.json'])),
        minute_blocks=_CapturedMinuteProvider(tuple(months)),
        derived_mark_cells=10, original_missing_mark_open_ms=a.MISSING_OPEN_MS,
        original_overlay_future_looking=True, original_overlay_execution_admitted=False,
        causal_mark_adapter=_immutable(adapter)))


def _input_binding(window, source_rows, decisions, targets):
    if (not isinstance(window, MappingProxyType)
            or type(window.get('minute_blocks')) is not _CapturedMinuteProvider
            or type(window.get('events')) is not tuple
            or type(source_rows) is not tuple
            or not isinstance(window.get('daily'), pl.DataFrame)
            or not isinstance(decisions, np.ndarray) or decisions.dtype != np.dtype('int64')
            or decisions.shape != (DAYS,) or decisions.flags.writeable
            or not isinstance(targets, np.ndarray) or targets.dtype != np.dtype('float64')
            or targets.shape != (DAYS, 5) or targets.flags.writeable
            or not np.isfinite(targets).all()):
        raise ValueError('EXACT_IMMUTABLE_ENTRY_OWNED_HISTORICAL_INPUTS_REQUIRED')
    if set(window) != {'start', 'end', 'symbols', 'daily', 'events', 'minute_blocks',
            'derived_mark_cells', 'original_missing_mark_open_ms',
            'original_overlay_future_looking', 'original_overlay_execution_admitted',
            'causal_mark_adapter'}:
        raise ValueError('EXACT_ENTRY_OWNED_HISTORICAL_WINDOW_FIELDS_REQUIRED')
    return dict(schema='ENTRY_OWNED_EXACT_FULL2024_CONTINUATION_INPUT_BINDING_V1',
        calendar=[window['start'], window['end']], symbols=list(window['symbols']),
        decision_raw_SHA256=_sha(decisions.tobytes()), selected_target_raw_SHA256=_sha(targets.tobytes()),
        daily_rows_SHA256=_json_sha(window['daily'].to_dicts()),
        daily_schema=[[name, str(dtype)] for name, dtype in window['daily'].schema.items()],
        source_rows_SHA256=_json_sha(_plain(source_rows)),
        funding_events_SHA256=_json_sha(_plain(window['events'])),
        provider_month_identity=window['minute_blocks'].identity,
        causal_mark_adapter_SHA256=_json_sha(_plain(window['causal_mark_adapter'])),
        derived_mark_cells=window['derived_mark_cells'],
        original_missing_mark_open_ms=list(window['original_missing_mark_open_ms']),
        original_overlay_future_looking=window['original_overlay_future_looking'],
        original_overlay_execution_admitted=window['original_overlay_execution_admitted'])


def prepare_source_only(source_root, output_directory, *, annual_preparation_directory=ANNUAL_PREPARATION):
    """Finite source/target preparation. No account, original fake scope, GO or run."""
    output = Path(output_directory)
    if output.exists():
        raise ValueError('EXCLUSIVE_NEW_CONTINUATION_PREPARATION_DIRECTORY_REQUIRED')
    code = code_identity()
    evidence = preserved_evidence_identity()
    annual_raw, annual = _frozen_preparation(annual_preparation_directory)
    artifacts = _load_annual_artifacts(annual_preparation_directory, annual)
    projection = _source_projection(source_root, annual_raw, annual, artifacts)
    index, files, quality, rows, decisions, target, covariance, captured = projection
    window = _make_window(index, captured, json.loads(artifacts['CAUSAL_MARK_ADAPTER.json']))
    input_binding = _input_binding(window, rows, decisions, target)
    policy = _policy(code)
    artifacts['ANNUAL_SOURCE_PREPARATION.json'] = annual_raw
    pins = {name: dict(SHA256=_sha(body), bytes=len(body)) for name, body in artifacts.items()}
    prep = dict(schema=PREPARATION_SCHEMA,
        status='PREPARED_SOURCE_TARGET_ONLY_NO_HISTORICAL_ACCOUNT_OR_GO',
        calendar=[START, END], days=DAYS, required_minutes=MINUTES,
        symbol_order=list(a.g.SYMBOLS), config=CONFIG, configs=[CONFIG], cost=COST,
        modes=list(MODES), mode_labels=MODE_LABELS, maximum_cases=2,
        settlement_mode=SETTLEMENT_MODE, resource_limits=RESOURCE_LIMITS,
        code_identity=code, policy=policy, policy_identity=_json_sha(policy),
        source_identity=annual['source_identity'], source_files=files,
        original200_quality=quality, artifacts=pins,
        frozen_annual_preparation_SHA256=_sha(annual_raw),
        frozen_annual_code_identity=annual['code_identity'],
        frozen_annual_execution_identity=annual['execution_identity'],
        frozen_annual_target_identity=annual['target_identity'],
        selected_target_raw_SHA256=_sha(target.tobytes()),
        decision_raw_SHA256=_sha(decisions.tobytes()),
        covariance_raw_SHA256=_sha(covariance.tobytes()),
        input_binding=input_binding, input_binding_SHA256=_json_sha(input_binding),
        preserved_evidence_pins=evidence, preserved_old_root_GO_is_new_authority=False,
        mark_feed_adapter_version=a.m.VERSION, mark_quality_guard_version=a.q.VERSION,
        original_interpolated_mark_execution_admitted=False,
        coldstart_policy=annual['coldstart_policy'], execution_label=LABEL,
        C_minus_B_attribution=policy['C_minus_B_attribution'],
        accounts_created=0, accounts_advanced=0, historical_market_minutes_advanced=0,
        annual_returns_computed=False, financial_runs=0, outcomes_inspected=False,
        locked_or_holdout_consumed=False, other_years_authorized=False,
        publication_actions=0, historical_admission=False,
        annual_execution_requires_new_exact_external_root_GO=True,
        source_counts=dict(months=12, decisions=len(decisions), source_rows=len(rows),
            daily_records=1830, funding_events=5490, required_minutes=MINUTES,
            actual_close_export_rows=566, actual_close_export_cells=2830,
            completed_actual_closes_per_decision=200, derived_mark_cells=10))
    if code_identity() != code or preserved_evidence_identity() != evidence:
        raise ValueError('CODE_OR_PRESERVED_PINS_CHANGED_DURING_PREPARATION')
    output.mkdir(parents=True)
    for name, body in artifacts.items():
        with (output / name).open('xb') as stream:
            stream.write(body)
    with (output / 'PREPARATION.json').open('xb') as stream:
        stream.write((json.dumps(prep, indent=2, allow_nan=False) + '\n').encode())
    return prep


def _validate_preparation(raw):
    prep = _object(raw, 'EXACT_CONTINUATION_PREPARATION_BYTES_REQUIRED')
    required = dict(schema=PREPARATION_SCHEMA,
        status='PREPARED_SOURCE_TARGET_ONLY_NO_HISTORICAL_ACCOUNT_OR_GO',
        calendar=[START, END], days=DAYS,
        required_minutes=MINUTES, symbol_order=list(a.g.SYMBOLS), config=CONFIG,
        configs=[CONFIG], cost=COST, modes=list(MODES), mode_labels=MODE_LABELS,
        maximum_cases=2, settlement_mode=SETTLEMENT_MODE, resource_limits=RESOURCE_LIMITS,
        preserved_evidence_pins=PRESERVED_EVIDENCE_PINS,
        preserved_old_root_GO_is_new_authority=False,
        mark_feed_adapter_version=a.m.VERSION, mark_quality_guard_version=a.q.VERSION,
        original_interpolated_mark_execution_admitted=False,
        coldstart_policy=a._protocol()['coldstart_policy'], execution_label=LABEL,
        accounts_created=0, accounts_advanced=0, historical_market_minutes_advanced=0,
        annual_returns_computed=False, financial_runs=0, outcomes_inspected=False,
        locked_or_holdout_consumed=False, other_years_authorized=False,
        publication_actions=0, historical_admission=False,
        annual_execution_requires_new_exact_external_root_GO=True,
        source_counts=dict(months=12, decisions=366, source_rows=2825,
            daily_records=1830, funding_events=5490, required_minutes=MINUTES,
            actual_close_export_rows=566, actual_close_export_cells=2830,
            completed_actual_closes_per_decision=200, derived_mark_cells=10))
    if (any(not _same(prep.get(key), value) for key, value in required.items())
            or not isinstance(prep.get('code_identity'), dict)
            or prep.get('policy') != _policy(prep['code_identity'])
            or prep.get('policy_identity') != _json_sha(prep['policy'])
            or not isinstance(prep.get('input_binding'), dict)
            or prep.get('input_binding_SHA256') != _json_sha(prep['input_binding'])
            or not isinstance(prep.get('artifacts'), dict)
            or set(prep['artifacts']) != set(ARTIFACTS)):
        raise ValueError('EXACT_BOUNDED_CONTINUATION_PREPARATION_SCOPE_REQUIRED')
    return prep


def validate_root_go(preparation_raw, go_raw, expected_go_sha256, *, policy_variant, config=CONFIG):
    _exact(go_raw, expected_go_sha256, 'EXACT_NEW_EXTERNAL_CONTINUATION_ROOT_GO_REQUIRED')
    prep = _validate_preparation(preparation_raw)
    go = _object(go_raw, 'EXACT_CONTINUATION_ROOT_GO_OBJECT_REQUIRED')
    required = dict(schema=GO_SCHEMA, action='RUN_FRESH_BOUNDED_NATIVE_CONTINUATION_CASES_ONLY',
        preparation_SHA256=_sha(preparation_raw), calendar=[START, END], config=CONFIG,
        cost=COST, settlement_mode=SETTLEMENT_MODE, modes=list(MODES),
        code_identity=prep['code_identity'], policy_identity=prep['policy_identity'],
        source_identity=prep['source_identity'], artifacts=prep['artifacts'],
        selected_target_raw_SHA256=prep['selected_target_raw_SHA256'],
        input_binding_SHA256=prep['input_binding_SHA256'],
        resource_limits=RESOURCE_LIMITS, preserved_evidence_pins=PRESERVED_EVIDENCE_PINS,
        preserved_old_root_GO_is_new_authority=False,
        mark_feed_adapter_version=a.m.VERSION, mark_quality_guard_version=a.q.VERSION,
        original_interpolated_mark_execution_admitted=False,
        coldstart_policy=prep['coldstart_policy'], serial_execution=True,
        automatic_retry_authorized=False, locked_or_holdout_consumed=False,
        other_years_authorized=False, publication_authorized=False,
        fresh_genesis_only=True, halted_snapshot_resume_authorized=False)
    permitted = go.get('permitted_modes')
    review_sha = go.get('independent_review_SHA256')
    if (config != CONFIG or policy_variant not in MODES
            or any(not _same(go.get(key), value) for key, value in required.items())
            or not isinstance(permitted, list) or not 1 <= len(permitted) <= 2
            or any(type(value) is not str or value not in MODES for value in permitted)
            or len(set(permitted)) != len(permitted) or policy_variant not in permitted
            or not isinstance(review_sha, str) or len(review_sha) != 64
            or any(c not in '0123456789abcdef' for c in review_sha)
            or expected_go_sha256 in PRESERVED_EVIDENCE_PINS.values()):
        raise ValueError('EXACT_NEW_ROOT_GO_FIXED_TWO_MODE_FINITE2024_SCOPE_REQUIRED')
    return prep


def _validate_independent_review(preparation_raw, prep, review_raw, expected_review_sha256, go_raw):
    _exact(review_raw, expected_review_sha256, 'EXACT_NEW_EXTERNAL_CONTINUATION_REVIEW_REQUIRED')
    review = _object(review_raw, 'EXACT_CONTINUATION_REVIEW_OBJECT_REQUIRED')
    go = _object(go_raw, 'EXACT_CONTINUATION_ROOT_GO_OBJECT_REQUIRED')
    required = dict(schema=REVIEW_SCHEMA, status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        preparation_SHA256=_sha(preparation_raw), calendar=[START, END], config=CONFIG,
        cost=COST, modes=list(MODES), settlement_mode=SETTLEMENT_MODE,
        code_identity=prep['code_identity'], source_identity=prep['source_identity'],
        policy_identity=prep['policy_identity'], artifacts=prep['artifacts'],
        selected_target_raw_SHA256=prep['selected_target_raw_SHA256'],
        input_binding_SHA256=prep['input_binding_SHA256'],
        resource_limits=RESOURCE_LIMITS, preserved_evidence_pins=PRESERVED_EVIDENCE_PINS,
        preserved_old_root_GO_is_new_authority=False,
        mark_feed_adapter_version=a.m.VERSION, mark_quality_guard_version=a.q.VERSION,
        original_interpolated_mark_execution_admitted=False,
        coldstart_policy=prep['coldstart_policy'],
        generated_native_scheduler_phase_order_passed=True,
        generated_shared_pending_32_corner_passed=True,
        generated_preview_isolation_passed=True, generated_causal_quality_passed=True,
        generated_terminal_taxonomy_passed=True,
        actual_2024_accounts_constructed=0, actual_2024_financial_runs=0,
        historical_market_minutes_advanced=0, publication_actions=0, locked_source_reads=0)
    if (go.get('independent_review_SHA256') != expected_review_sha256
            or expected_review_sha256 in PRESERVED_EVIDENCE_PINS.values()
            or any(not _same(review.get(key), value) for key, value in required.items())):
        raise ValueError('EXACT_NEW_CONTINUATION_INDEPENDENT_REVIEW_SCOPE_REQUIRED')
    return review


def validate_annual_inputs(source_root, preparation_directory, go_raw, expected_go_sha256,
        *, policy_variant, config=CONFIG):
    """Source-only positive admission; no account or provider iteration."""
    directory = Path(preparation_directory)
    raw = _ordinary(directory / 'PREPARATION.json')
    prep = validate_root_go(raw, go_raw, expected_go_sha256,
        policy_variant=policy_variant, config=config)
    if prep['code_identity'] != code_identity() or preserved_evidence_identity() != prep['preserved_evidence_pins']:
        raise ValueError('CONTINUATION_CODE_OR_PRESERVED_EVIDENCE_CHANGED')
    artifacts = {name: a.h._read_exact(directory / name, pin['SHA256'], pin['bytes'])
        for name, pin in prep['artifacts'].items()}
    annual_raw = artifacts['ANNUAL_SOURCE_PREPARATION.json']
    _exact(annual_raw, ANNUAL_PREPARATION_PIN[1], 'EXACT_OLD_SOURCE_PREPARATION_PIN_REQUIRED')
    annual = _object(annual_raw, 'EXACT_OLD_SOURCE_PREPARATION_REQUIRED')
    if (prep['frozen_annual_preparation_SHA256'] != _sha(annual_raw)
            or prep['frozen_annual_code_identity'] != annual['code_identity']
            or prep['frozen_annual_execution_identity'] != annual['execution_identity']
            or prep['frozen_annual_target_identity'] != annual['target_identity']):
        raise ValueError('PRESERVED_FROZEN_ANNUAL_SOURCE_TARGET_CODE_PINS_REQUIRED')
    for name in a.ARTIFACTS:
        if prep['artifacts'][name] != annual['artifacts'][name]:
            raise ValueError('ORIGINAL_TARGET_OR_QUALITY_ARTIFACT_PIN_CHANGED')
    index, files, quality, rows, decisions, target, covariance, captured = _source_projection(
        source_root, annual_raw, annual, artifacts)
    if (files != prep['source_files'] or quality != prep['original200_quality']
            or annual['source_identity'] != prep['source_identity']
            or _sha(target.tobytes()) != prep['selected_target_raw_SHA256']
            or _sha(decisions.tobytes()) != prep['decision_raw_SHA256']
            or _sha(covariance.tobytes()) != prep['covariance_raw_SHA256']):
        raise ValueError('EXACT_ADMITTED_SOURCE_TARGET_CALENDAR_OR_COVARIANCE_REQUIRED')
    window = _make_window(index, captured, json.loads(artifacts['CAUSAL_MARK_ADAPTER.json']))
    if not _same(_input_binding(window, rows, decisions, target), prep['input_binding']):
        raise ValueError('EXACT_ENTRY_OWNED_PROVIDER_DAILY_EVENTS_TARGET_QUALITY_BINDING_REQUIRED')
    return prep, window, rows, decisions, target, captured


@dataclass(frozen=True, slots=True)
class HistoricalExecutionScope:
    """Immutable exact finite authority; never a generated fixture flag.

    Creation is internal to the admitted entry. The source, code, policy,
    preparation, review and GO byte bindings can be checked before native
    construction. This is a process-local admission proof, not a secret token.
    """
    preparation_SHA256: str
    source_identity: str
    code_identity_SHA256: str
    policy_identity: str
    independent_review_SHA256: str
    root_GO_SHA256: str
    policy_variant: str
    config: str
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
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _SCOPE_SEAL:
            raise ValueError('SCOPE_CAN_ONLY_BE_MINTED_BY_EXACT_CONTINUATION_ADMISSION')

    def __deepcopy__(self, memo):
        # All members are immutable; preview forks retain the same authority
        # rather than producing a new token or recursively copying evidence.
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
        return MappingProxyType(dict(source_scope=self.source_scope,
            preparation_SHA256=self.preparation_SHA256, source_identity=self.source_identity,
            code_identity_SHA256=self.code_identity_SHA256, policy_identity=self.policy_identity,
            independent_review_SHA256=self.independent_review_SHA256,
            root_GO_SHA256=self.root_GO_SHA256, policy_variant=self.policy_variant,
            config=self.config, calendar=(START, END), cost=COST,
            settlement_mode=SETTLEMENT_MODE, fresh_genesis_only=True,
            generated_fixture_scope_used=False,
            input_binding_SHA256=_json_sha(_input_binding(self._bound_window,
                self._bound_source_rows, self._bound_decisions, self._bound_targets))))

    def validate_inputs(self, window, source_rows, decisions, targets):
        if (self._seal is not _SCOPE_SEAL or window is not self._bound_window
                or source_rows is not self._bound_source_rows
                or decisions is not self._bound_decisions or targets is not self._bound_targets):
            raise ValueError('EXACT_ENTRY_OWNED_HISTORICAL_INPUT_REFERENCES_REQUIRED')
        prep = _object(self._preparation_raw, 'EXACT_SCOPE_PREPARATION_REQUIRED')
        binding = _input_binding(window, source_rows, decisions, targets)
        if (not _same(binding, prep['input_binding'])
                or _json_sha(binding) != prep['input_binding_SHA256']
                or binding['calendar'] != [START, END]
                or binding['symbols'] != list(a.g.SYMBOLS)
                or binding['decision_raw_SHA256'] != prep['decision_raw_SHA256']
                or binding['selected_target_raw_SHA256'] != prep['selected_target_raw_SHA256']):
            raise ValueError('BOUND_HISTORICAL_PROVIDER_SOURCE_DAILY_TARGET_OR_QUALITY_CHANGED')
        return True

    def validate_current(self):
        if self._seal is not _SCOPE_SEAL:
            raise ValueError('UNSEALED_HISTORICAL_CONTINUATION_SCOPE')
        raw = _ordinary(self._preparation_directory / 'PREPARATION.json')
        if raw != self._preparation_raw or _sha(raw) != self.preparation_SHA256:
            raise ValueError('BOUND_CONTINUATION_PREPARATION_CHANGED')
        prep = validate_root_go(raw, self._go_raw, self.root_GO_SHA256,
            policy_variant=self.policy_variant, config=self.config)
        _validate_independent_review(raw, prep, self._review_raw,
            self.independent_review_SHA256, self._go_raw)
        if (self._source_pins != tuple((name, pin['SHA256'], pin['bytes'])
                    for name, pin in sorted(prep['source_files'].items()))
                or prep['source_identity'] != self.source_identity
                or prep['policy_identity'] != self.policy_identity
                or _json_sha(prep['code_identity']) != self.code_identity_SHA256
                or prep['code_identity'] != code_identity()
                or prep['policy'] != _policy(prep['code_identity'])
                or preserved_evidence_identity() != prep['preserved_evidence_pins']):
            raise ValueError('BOUND_CONTINUATION_SOURCE_CODE_OR_POLICY_CHANGED')
        for name, digest, size in self._source_pins:
            a.h._read_exact(self._source_root / name, digest, size)
        for name, pin in prep['artifacts'].items():
            a.h._read_exact(self._preparation_directory / name, pin['SHA256'], pin['bytes'])
        self.validate_inputs(self._bound_window, self._bound_source_rows,
            self._bound_decisions, self._bound_targets)
        return True


def _default_constructor_callback(*, scope, preparation, window, source_rows,
        decisions, targets, captured):
    integration = importlib.import_module('integration')
    if Path(integration.__file__).resolve() != HERE / 'integration.py':
        raise ValueError('EXACT_SEPARATE_INTEGRATION_CALLBACK_MODULE_REQUIRED')
    intervals = ((a.m.FIRST_MISSING_KNOWN, a.m.RESUME_AVAILABLE, a.g.SYMBOLS),)
    return integration.construct_case(window, source_rows, decisions, targets,
        policy_variant=scope.policy_variant, historical_scope=scope, quality_intervals=intervals)


def make_annual_case(source_root, preparation_directory, go_raw, expected_go_sha256,
        *, policy_variant, config=CONFIG, review_raw=None, expected_review_sha256=None,
        constructor_callback=None):
    """Validate once then delegate fresh construction; never advance a clock."""
    preparation_raw = _ordinary(Path(preparation_directory) / 'PREPARATION.json')
    prep = validate_root_go(preparation_raw, go_raw, expected_go_sha256,
        policy_variant=policy_variant, config=config)
    _validate_independent_review(preparation_raw, prep, review_raw,
        expected_review_sha256, go_raw)
    prep, window, rows, decisions, targets, captured = validate_annual_inputs(
        source_root, preparation_directory, go_raw, expected_go_sha256,
        policy_variant=policy_variant, config=config)
    scope = HistoricalExecutionScope(preparation_SHA256=_sha(preparation_raw),
        source_identity=prep['source_identity'], code_identity_SHA256=_json_sha(prep['code_identity']),
        policy_identity=prep['policy_identity'], independent_review_SHA256=expected_review_sha256,
        root_GO_SHA256=expected_go_sha256, policy_variant=policy_variant, config=config,
        _source_root=Path(source_root).resolve(), _preparation_directory=Path(preparation_directory).resolve(),
        _preparation_raw=preparation_raw, _review_raw=review_raw, _go_raw=go_raw,
        _source_pins=tuple((name, pin['SHA256'], pin['bytes'])
            for name, pin in sorted(prep['source_files'].items())),
        _bound_window=window, _bound_source_rows=rows, _bound_decisions=decisions,
        _bound_targets=targets, _seal=_SCOPE_SEAL)
    scope.validate_current()
    callback = constructor_callback or _default_constructor_callback
    return callback(scope=scope, preparation=prep, window=window, source_rows=rows,
        decisions=decisions, targets=targets, captured=captured)


make_continuation_case = make_annual_case
