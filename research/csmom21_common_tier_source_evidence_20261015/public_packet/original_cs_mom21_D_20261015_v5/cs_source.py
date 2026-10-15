"""Portable canonical source capture and separate pure-CS target preparation.

No finance, simulator, native constructor, provider iteration or process is
imported or called by preparation. Existing sources are captured once per year;
the 2022 exact normalized months stay in memory, as in original D.
"""
from dataclasses import asdict
from io import BytesIO
from pathlib import Path
import re
from types import MappingProxyType

import numpy as np

import cs_common as c
import cs_codec as codec
import cs_config as config
import cs_entry as entry
import cs_quality as quality
import cs_signal as signal


def _pin_read(scope, year, path):
    pin = entry.contracts()['years'][str(year)]['read_files'][path]
    return scope.read_source(year, path, pin['SHA256'], pin['bytes'])


def funding_events(year, raw, contract, *, normalized_2022=False):
    period = config.period_named(year)
    values = c.object_json(raw)
    if type(values) is not list:
        raise ValueError('EXACT_FUNDING_ARRAY_REQUIRED')
    if year == 2021:
        if len(values) != contract['events']['stored_events']:
            raise ValueError('EXACT_STORED_2021_FUNDING_COUNT_REQUIRED')
        values = [row for row in values if period['start'] <= row['event_us'] < period['end']]
        for row in values:
            witness = row.get('strict_prior_mark')
            if (type(witness) is not dict or witness['mark_available_us'] >= row['event_us']
                    or not 0 < witness['strict_prior_age_us'] <= codec.MINUTE):
                raise ValueError('ORIGINAL_STRICT_PRIOR_FUNDING_SOURCE_WITNESS_REQUIRED')
        values = [{key: row[key] for key in ('symbol', 'event_us', 'raw_rate', 'reported_interval_hours', 'raw_rate_unit')}
                  for row in values]
    expected_fields = {'symbol', 'event_us', 'raw_rate', 'reported_interval_hours'}
    if year in (2021, 2022):
        expected_fields.add('raw_rate_unit')
    if (len(values) != contract['events']['selected_events']
            or len({(row.get('symbol'), row.get('event_us')) for row in values}) != len(values)):
        raise ValueError('EXACT_ORIGINAL_FUNDING_IDENTITIES_REQUIRED')
    for row in values:
        if (type(row) is not dict or set(row) != expected_fields or row['symbol'] not in signal.SYMBOLS
                or type(row['event_us']) is not int or not period['start'] <= row['event_us'] < period['end']
                or type(row['raw_rate']) not in (int, float) or not np.isfinite(row['raw_rate'])
                or type(row['reported_interval_hours']) not in (int, float)
                or (not np.isfinite(row['reported_interval_hours']) or row['reported_interval_hours'] <= 0
                    if year == 2022 else row['reported_interval_hours'] != 8)
                or year in (2021, 2022) and row['raw_rate_unit'] != 'UNCONFIRMED'):
            raise ValueError('PRESERVED_RAW_UNCERTIFIED_FUNDING_SCHEMA_REQUIRED')
    # Preserve each original namespace's established same-clock ordering.
    if year == 2022:
        order = lambda row: (row['event_us'], signal.SYMBOLS.index(row['symbol']))
    else:
        order = lambda row: (row['event_us'], row['symbol'])
    if values != sorted(values, key=order):
        raise ValueError('ORIGINAL_SAMECLOCK_FUNDING_ORDER_REQUIRED')
    return c.immutable(values)


def assemble_inputs(year, warm_raw, daily_raw, events_raw, sidecar_raw, months, contract):
    """Pure shared source validation over bytes; this mints no actual scope."""
    period = config.period_named(year)
    clocks, close, decisions = codec.daily_inputs(year, warm_raw, daily_raw)
    sidecar = c.exact_object(sidecar_raw)
    recoveries = []
    if year == 2022:
        cells = quality.quality_cells_2022(sidecar, contract['exact_mark_absent_open_points_us'],
                                         contract['normalized_quality_cells_SHA256'])
        intervals = quality.intervals(cells)
        if c.canonical(intervals) != c.canonical(contract['quality_intervals']):
            raise ValueError('EXACT27_CAUSAL_UNKNOWN_INTERVALS_REQUIRED')
    else:
        cells = ()
        intervals = tuple((a, b, tuple(symbols)) for a, b, symbols in contract['quality_intervals'])
    events = funding_events(year, events_raw, contract, normalized_2022=year == 2022)
    cursor = period['start']; seen = []; final = None; decoded = []
    if len(months) != len(contract['months']):
        raise ValueError('EXACT_CANONICAL_MONTH_COUNT_REQUIRED')
    for rec, (name, raw) in zip(contract['months'], months, strict=True):
        if (name != rec['path'] or c.sha(raw) != rec['hash'] or len(raw) != rec['size']
                or rec['start'] + rec['lo'] * codec.MINUTE != cursor
                or not 0 <= rec['lo'] < rec['hi'] <= rec['count']):
            raise ValueError('EXACT_SHARED_CANONICAL_MONTH_IDENTITY_REQUIRED')
        arrays, missing = codec.month_arrays(year, raw, rec['start'], rec['count'], cells)
        seen.extend(missing); final = arrays
        for at in range(rec['start'] + config.DAY, rec['start'] + rec['count'] * codec.MINUTE + 1, config.DAY):
            if not period['start'] <= at < period['end']:
                continue
            k = int(np.searchsorted(clocks, at)); off = (at - rec['start']) // codec.MINUTE - 1
            for j, symbol in enumerate(signal.SYMBOLS):
                if arrays[symbol + '_close'][off].tobytes() != close[k, j].tobytes():
                    raise ValueError('EXACT_NATIVE_DAILY_CLOSE_BIT_PARITY_REQUIRED')
        if year == 2024 and rec['start'] <= 1723456920000000 < rec['start'] + rec['count'] * codec.MINUTE:
            for symbol in signal.SYMBOLS:
                if c.sha(arrays[symbol + '_mark'].tobytes()) != sidecar['causal_estimate_mark_array_SHA256'][symbol]:
                    raise ValueError('EXACT_2024_PINNED_CAUSAL_MARK_ARRAY_BITS_REQUIRED')
        decoded.append((rec, arrays)); cursor = rec['start'] + rec['hi'] * codec.MINUTE
    if cursor != period['end'] or final is None:
        raise ValueError('EXACT_NATIVE_EXECUTION_AND_CLOSING_CALENDAR_REQUIRED')
    if year == 2022:
        if sorted(seen) != sorted(tuple(row) for row in contract['exact_mark_absent_open_points_us']):
            raise ValueError('EXACT27_ONLY_CARRY_APPLICATION_REQUIRED')
        for cell in cells:
            rec, arrays = next((rec, arrays) for rec, arrays in decoded
                if rec['start'] <= cell.anchor_open_us < rec['start'] + rec['count'] * codec.MINUTE)
            offset = (cell.anchor_open_us - rec['start']) // codec.MINUTE
            if arrays[cell.symbol + '_mark'][offset].tobytes() != np.float64(float(cell.price_text)).tobytes():
                raise ValueError('EXACT_PRIOR_GENUINE_MARK_ANCHOR_BITS_REQUIRED')
        missing = {(cell.symbol, cell.minute_open_us) for cell in cells}
        recovery_points = set()
        for cell in cells:
            opened = cell.minute_open_us + codec.MINUTE
            while (cell.symbol, opened) in missing:
                opened += codec.MINUTE
            recovery_points.add((cell.symbol, opened))
        if len(recovery_points) != 8:
            raise ValueError('EXACT_EIGHT_PER_ASSET_GENUINE_RECOVERY_ROWS_REQUIRED')
        for symbol, opened in sorted(recovery_points):
            rec, arrays = next((rec, arrays) for rec, arrays in decoded
                if rec['start'] <= opened < rec['start'] + rec['count'] * codec.MINUTE)
            value = arrays[symbol + '_mark'][(opened - rec['start']) // codec.MINUTE]
            if (symbol, opened) in missing or not np.isfinite(value) or value <= 0:
                raise ValueError('GENUINE_POST_GAP_RECOVERY_SOURCE_ROW_REQUIRED')
            recoveries.append(dict(symbol=symbol, minute_open_us=opened, completed_us=opened + codec.MINUTE,
                modeled_available_us=opened + codec.MINUTE, source_file_SHA256=rec['hash'],
                native_mark_float64_SHA256=c.sha(value.tobytes()), is_genuine=True,
                actual_publication_arrival_installation='UNKNOWN_NOT_CERTIFIED'))
    endpoint = {symbol: float(final[symbol + '_close'][-1]) for symbol in signal.SYMBOLS}
    if year in (2021, 2022, 2025) and sidecar.get('final_endpoint_close') != endpoint:
        raise ValueError('EXACT_GENUINE_FINAL_NATIVE_CLOSE_WITNESS_REQUIRED')
    rows = tuple(MappingProxyType(dict(symbol=symbol, close_us=int(at), available_us=int(at), close=float(close[i, j])))
                 for i, at in enumerate(clocks) for j, symbol in enumerate(signal.SYMBOLS))
    cs_sidecar = dict(schema='CSMOM21_REUSED_QUALIFIED_SOURCE_QUALITY_V2', year=year,
        calendar=[period['start'], period['end']], qualified_source_identity=contract['source_identity'],
        original_quality_sidecar_SHA256=c.sha(sidecar_raw), original_quality_sidecar=c.plain(sidecar),
        cells=[asdict(cell) for cell in cells], quality_intervals=c.plain(intervals),
        derived_mark_cells=contract['quality_summary'].get('derived_mark_cells', contract.get('derived_mark_cells', 0)),
        source_completion_is_not_arrival_certification=True, arrival_status='UNKNOWN_NOT_CERTIFIED',
        original_source_age_and_arrival_flags_preserved=True, actual_CS_event_impacts='PENDING_CS_SAVED_EXECUTION',
        genuine_recovery_witnesses=recoveries,
        actual_CS_position_interval_impacts='PENDING_CS_SAVED_EXECUTION_NOT_INHERITED_FROM_D',
        certifies_liquidation=False, certifies_no_liquidation=False, final_endpoint_close=endpoint,
        funding_ownership='CURRENT_NATIVE_ACTUAL_QUANTITY_ONLY_AFTER_PAID_FILLS')
    return dict(year=year, period=period, clocks=clocks, close=close, decisions=decisions,
        source_rows=rows, events=events, months=tuple(months), quality_cells=cells,
        quality_intervals=intervals, sidecar=cs_sidecar, sidecar_raw=c.canonical(cs_sidecar) + b'\n',
        source_identity=contract['source_identity'], contract=c.immutable(contract))


def capture_year(year, source_scope):
    if type(source_scope) is not entry.SourcePreparationScope:
        raise ValueError('EXACT_NEW_CS_SOURCE_SCOPE_REQUIRED')
    source_scope.validate_current(year=year)
    contract = entry.contracts()['years'][str(year)]
    sidecar_raw = _pin_read(source_scope, year, contract['quality_sidecar_path'])
    if year == 2022:
        from cs_source_bridge import capture_2022
        transport, captured = capture_2022(source_scope.source_root(year), source_scope=source_scope)
        warm_raw, events_raw = captured['DAILY_PROJECTION.npz'], captured['RAW_EVENTS.json']
        months = tuple((rec['path'], captured[rec['path']]) for rec in contract['months'])
        daily_raw = None
    else:
        warm_raw = _pin_read(source_scope, year, contract['warmup_path'])
        daily_raw = _pin_read(source_scope, year, contract['daily_path']) if contract['daily_path'] is not None else None
        events_raw = _pin_read(source_scope, year, contract['events_path'])
        months = tuple((rec['path'], _pin_read(source_scope, year, rec['path'])) for rec in contract['months'])
        transport = None
    result = assemble_inputs(year, warm_raw, daily_raw, events_raw, sidecar_raw, months, contract)
    if transport is not None:
        result['normalization_equivalence'] = transport['normalization_equivalence']
    source_scope.validate_current(year=year)
    return result


def project_targets(source):
    raw, original, targets, covariance, diagnostic, proofs = signal.project_arrays(
        source['close'], source['clocks'], source['clocks'], source['decisions'])
    arrays = dict(decision_us=source['decisions'], annual_covariance=covariance,
                  weekly_raw_CS=raw, original_sized_CS=original)
    arrays.update({config.STRATEGY + '_' + tier: targets[tier] for tier in config.TIERS})
    return {key: codec.frozen_array(value) for key, value in arrays.items()}, dict(
        original_signal_diagnostics=diagnostic, tier_proofs=proofs,
        sizing_difference={tier: dict(rows_reexpanded=sum(p['tiers'][tier]['factor'] > 1 for p in proofs),
            rows_shrunk=sum(p['tiers'][tier]['factor'] < 1 for p in proofs),
            original_sized_CS_SHA256=c.sha(original.tobytes()), common_tier_CS_SHA256=c.sha(targets[tier].tobytes()))
            for tier in config.TIERS})


def target_blob(arrays):
    stream = BytesIO(); np.savez_compressed(stream, **arrays); return stream.getvalue()


def input_binding(cell, source, targets):
    key = config.STRATEGY + '_' + cell['tier']
    return dict(schema='EXACT_NEW_CS_CELL_SOURCE_TARGET_BINDING_V2', cell_id=cell['cell_id'],
        strategy=config.STRATEGY, year=cell['year'], tier=cell['tier'],
        calendar=[cell['start_us'], cell['end_exclusive_us']], source_identity=source['source_identity'],
        source_contract_SHA256=c.jsha(source['contract']), source_rows_SHA256=c.jsha(source['source_rows']),
        funding_events_SHA256=c.jsha(source['events']), source_quality_sidecar_SHA256=c.sha(source['sidecar_raw']),
        quality_cells_SHA256=c.jsha([asdict(row) for row in source['quality_cells']]),
        provider_months=[[rec['path'], rec['start'], rec['count'], rec['hash'], rec['size'], rec['lo'], rec['hi']]
                         for rec in source['contract']['months']],
        decision_raw_SHA256=c.sha(targets['decision_us'].tobytes()),
        covariance_raw_SHA256=c.sha(targets['annual_covariance'].tobytes()),
        weekly_raw_CS_SHA256=c.sha(targets['weekly_raw_CS'].tobytes()),
        original_sized_CS_SHA256=c.sha(targets['original_sized_CS'].tobytes()),
        selected_target_raw_SHA256=c.sha(targets[key].tobytes()),
        cost='BASE27', policy_variant='GUARD50_EXIT_ONLY', quantity_profile_SHA256=
        '94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf')


def prepare_source_only(output_directory, *, source_go_raw, expected_source_go_sha256,
                        review_raw, expected_review_sha256):
    """Exclusive finite actual stage, gated before any source read or write."""
    authority = entry.validate_source_authority_metadata(source_go_raw, expected_source_go_sha256,
                                                         review_raw, expected_review_sha256)
    from cs_source_guard import current_guard
    guard = current_guard()
    if guard is None or not guard.active:
        raise ValueError('WHOLE_INVOCATION_CS_SOURCE_ONLY_GUARD_REQUIRED')
    output = Path(output_directory).absolute()
    base = c.HERE / 'source_attempts'
    if (output.parent != base or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,100}', output.name)
            or output.is_symlink() or any(parent.is_symlink() for parent in output.parents)):
        raise ValueError('EXACT_NEW_CS_SOURCE_ATTEMPT_OUTPUT_NO_SYMLINK_ANCESTORS_REQUIRED')
    if output.exists():
        raise ValueError('EXCLUSIVE_NEW_CS_SOURCE_PREPARATION_REQUIRED')
    artifacts = {}; years = {}; cells = {}
    tranche = authority['policy']['tranche']
    with entry.admit_source_stage(source_go_raw, expected_source_go_sha256, review_raw, expected_review_sha256) as scope:
        for year in entry.tranche_years(tranche):
            source = capture_year(year, scope); targets, proofs = project_targets(source)
            prefix = str(year) + '/'
            artifacts[prefix + 'TARGETS.npz'] = target_blob(targets)
            artifacts[prefix + 'SOURCE_INPUTS.npz'] = target_blob(dict(close_available_us=source['clocks'], close=source['close']))
            artifacts[prefix + 'RAW_EVENTS.json'] = c.canonical(source['events']) + b'\n'
            artifacts[prefix + 'MINUTE_MARK_PROVENANCE.json'] = source['sidecar_raw']
            artifacts[prefix + 'TARGET_PROOFS.json'] = c.canonical(proofs) + b'\n'
            if year == 2022:
                artifacts[prefix + 'NORMALIZATION_EQUIVALENCE.json'] = c.canonical(source['normalization_equivalence']) + b'\n'
            years[str(year)] = dict(source_identity=source['source_identity'],
                source_contract_SHA256=c.jsha(source['contract']), days=source['period']['days'],
                calendar=[source['period']['start'], source['period']['end']],
                provider_months_source='MEMORY_ONLY_EXACT_OLD_NATIVE_CAPTURE' if year == 2022 else 'EXISTING_PINNED_CANONICAL_MONTHS',
                source_quality_sidecar_SHA256=c.sha(source['sidecar_raw']),
                quality_cells_SHA256=c.jsha([asdict(row) for row in source['quality_cells']]),
                source_rows_SHA256=c.jsha(source['source_rows']), funding_events_SHA256=c.jsha(source['events']),
                array_raw_SHA256={key: c.sha(value.tobytes()) for key, value in targets.items()},
                all_CS_position_and_event_impacts_pending=True)
            for cell_id in entry.tranche_cells(tranche):
                cell = config.cell_named(cell_id)
                if cell['year'] == year:
                    binding = input_binding(cell, source, targets)
                    cells[cell_id] = dict(descriptor=cell, input_binding=binding, input_binding_SHA256=c.jsha(binding))
            guard.checkpoint('PREPARED_' + str(year) + '_CS_TARGETS_NO_ACCOUNT')
    if entry._ACTIVE_SOURCE:
        raise ValueError('CS_SOURCE_SCOPES_NOT_REVOKED')
    artifacts['SOURCE_STAGE_AUTHORIZATION.json'] = source_go_raw
    artifacts['SOURCE_INDEPENDENT_REVIEW.json'] = review_raw
    preparation = dict(schema='PREPARED_CSMOM21_SOURCE_TARGET_ONLY_V2', candidate=config.STRATEGY,
        tranche=tranche, ordered_cells=list(entry.tranche_cells(tranche)), years=years, cells=cells,
        code_manifest_SHA256=entry.code_identity(), scope_manifest_SHA256=entry.manifest_sha(),
        source_contract_map_SHA256=entry.contract_sha(), source_stage_GO_SHA256=expected_source_go_sha256,
        source_review_SHA256=expected_review_sha256,
        artifacts={name: dict(SHA256=c.sha(raw), bytes=len(raw)) for name, raw in artifacts.items()},
        historical_admission=False, financial_runs=0, accounts_created=0, accounts_advanced=0,
        provider_iterations=0, process_launches=0, canonical_claims_created=0,
        real_financial_GO_written=0, publication_actions=0)
    raw = c.canonical(preparation) + b'\n'; entry.validate_preparation_metadata(raw)
    output.mkdir(parents=True)
    for name, value in artifacts.items():
        path = output / c.relative(name); path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(value)
    with (output / 'PREPARATION.json').open('xb') as stream:
        stream.write(raw)
    return preparation
