"""Saved-only FIRST6 terminal audit; no source recapture or account creation."""
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import zipfile
import stat
from dataclasses import fields

import numpy as np

import cs_common as c
import cs_codec as codec
import cs_config as config
import cs_finance_gate as gate
import cs_process_runtime as r


def saved_account_contract(audit, result, tier):
    import cs_native as native
    engine = native.V2.ENGINE
    cfg = engine.PerpetualConfig(initial_cash='10000', max_gross_weight=str(config.TIER_GROSS_CAPS[tier]),
        max_asset_weight='.30', leverage='1', half_spread_bps='4', slippage_bps='4')
    expected_config = {f.name: str(getattr(cfg, f.name)) for f in fields(cfg)}
    profile_path = c.ROOT / 'bounded_account_continuation_20261015/QUANTITY_PROFILE.json'
    profile = c.exact_object(c.exact(profile_path, '94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf'))
    profiles = {s: engine.InstrumentProfile(quantity_step=profile['rows'][s]['quantity_step'], min_notional='10').metadata()
                for s in native.S}
    if (audit['symbols'] != list(native.S) or set(audit['positions']) != set(native.S)
            or set(audit['marks']) != set(native.S) or c.canonical(audit['config']) != c.canonical(expected_config)
            or c.canonical(audit['instrument_profiles']) != c.canonical(profiles)
            or audit['closing_min_notional_exempt'] is not True or audit['cost_context'] is not None
            or audit['bound_nominal_tier'] != tier or audit['historical_execution_admitted'] is not True):
        raise ValueError('EXACT_SAVED_CORE5_TIER_BASE27_COARSE_ACCOUNT_REQUIRED')
    contract = audit['contract']; common = result['common_execution_policy']
    fixed_contract = dict(symbols=list(native.S), bound_nominal_tier=tier, free_cash_floor='1000',
        total_isolated_ceiling='8500', leverage=1, nominal_roundtrip_bps=27., taker_fee_bps_per_side=5.5,
        topup_enabled=False, policy_variant='GUARD50_EXIT_ONLY', quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE',
        historical_execution_admitted=True, generated_only=False, closing_min_notional_exempt=True)
    if (any(c.canonical(contract.get(k)) != c.canonical(v) for k, v in fixed_contract.items())
            or c.canonical(contract['instrument_profiles']) != c.canonical(profiles)
            or c.canonical(contract['scope_binding']) != c.canonical(audit['historical_execution_scope'])):
        raise ValueError('EXACT_SAVED_CS_NATIVE_CONTRACT_REQUIRED')
    fixed_common = dict(tier=tier, gross_ceiling=config.TIER_GROSS_CAPS[tier], asset_ceiling=.30,
        annual_covariance_volatility_ceiling=config.TIER_BUDGETS[tier], initial_cash='10000',
        free_cash_increase_floor='1000', actual_isolated_margin_ceiling='8500', automatic_topup=False,
        policy_variant='GUARD50_EXIT_ONLY', historical_execution_admitted=True)
    if any(c.canonical(common.get(k)) != c.canonical(v) for k, v in fixed_common.items()):
        raise ValueError('EXACT_SAVED_CS_TIER_CAPS_AND_COMMON_WALLET_REQUIRED')


def saved_source_guard(guard):
    from cs_source_guard import SourceOnlyGuard
    def zeros(value):
        return (type(value) is dict and set(value) == set(SourceOnlyGuard.CATEGORIES)
                and all(type(v) is int and v == 0 for v in value.values()))
    if (guard.get('schema') != 'OBSERVED_PORTABLE_CS_SOURCE_GUARD_V2'
            or guard.get('status') != 'PASS_FINANCIAL_WORKER_SOURCE_ONLY_RECAPTURE'
            or not zeros(guard.get('forbidden_attempts')) or guard.get('error') is not None
            or guard.get('attempted_targets') != [] or guard.get('guard_active') is not False
            or guard.get('historical_execution_authorized') is not False
            or guard.get('financial_execution_authorized') is not False
            or guard.get('source_scopes_revoked') is not True
            or guard.get('saved_targets_and_covariance_rebuilt') is not False):
        raise ValueError('EXACT_OBSERVED_CLEAN_CS_SOURCE_RECAPTURE_GUARD_REQUIRED')
    points = guard.get('checkpoints')
    if (type(points) is not list or [p.get('label') for p in points] != [
            'FRESH_WORKER_CS_SOURCE_RECAPTURE_BEFORE_FINANCE_IMPORT',
            'EXACT_SAVED_CS_TARGETS_LOADED_WITHOUT_REGENERATION']
            or any(not zeros(p.get('attempts')) for p in points)):
        raise ValueError('EXACT_TWO_OBSERVED_CS_RECAPTURE_CHECKPOINTS_REQUIRED')
    reads = guard.get('observed_workspace_read_paths')
    if (type(reads) is not dict or not reads
            or any(type(k) is not str or type(v) is not int or v <= 0 for k, v in reads.items())):
        raise ValueError('OBSERVED_CS_SOURCE_READ_PATHS_REQUIRED')


def quality_identity(sidecar, year_info, version):
    if (c.jsha(sidecar['cells']) != year_info['quality_cells_SHA256']
            or sidecar['qualified_source_identity'] != year_info['source_identity']
            or sidecar['arrival_status'] != 'UNKNOWN_NOT_CERTIFIED'
            or sidecar['original_source_age_and_arrival_flags_preserved'] is not True
            or sidecar['actual_CS_event_impacts'] != 'PENDING_CS_SAVED_EXECUTION'
            or sidecar['actual_CS_position_interval_impacts'] != 'PENDING_CS_SAVED_EXECUTION_NOT_INHERITED_FROM_D'):
        raise ValueError('EXACT_SAVED_CS_QUALITY_SOURCE_IDENTITY_REQUIRED')
    identity = dict(version=version, source_sidecar_sha256=year_info['source_quality_sidecar_SHA256'],
        intervals=[], known_fill_identity_precedes_quality=True, actual_installed_mark_recovery_required=True,
        reduce_only_finance_and_native_retry_unchanged=True, estimated_valuation_is_genuine_mark=False,
        native_venue_or_current_mark_certified=False)
    if sidecar['cells']:
        identity.update(source_clock_cells=sidecar['cells'], per_asset_genuine_recovery_required=True)
    return identity


def saved_resources(receipt, bootstrap, owner, claim, *, lease_inode, directory):
    cpu = receipt['requested_CPU']; pid = receipt['PID']
    expected_limits = {name: [value, value] for name, value in
        (('AS', r.LIMITS['per_case_AS_bytes']), ('CPU', r.LIMITS['per_case_CPU_seconds']),
         ('RSS', r.LIMITS['per_case_RSS_stop_bytes']))}
    fixed_bootstrap = dict(schema='STDLIB_PRE_NUMERICAL_IMPORT_RESOURCE_BOOTSTRAP_V1', PID=pid,
        requested_CPU=cpu, actual_affinity=[cpu], limits=expected_limits,
        thread_environment={key: '1' for key in r.THREAD_ENV})
    if any(c.canonical(bootstrap.get(k)) != c.canonical(v) for k, v in fixed_bootstrap.items()):
        raise ValueError('EXACT_SAVED_CS_PRE_NUMERICAL_BOOTSTRAP_REQUIRED')
    if (type(pid) is not int or pid <= 0 or type(receipt['controller_PID']) is not int
            or receipt['controller_PID'] <= 0 or receipt['controller_PID'] == pid
            or type(receipt['process_start_ticks']) is not str or not receipt['process_start_ticks'].isdigit()
            or owner.get('cell_id') != receipt['cell_id'] or owner.get('PID') != pid or owner.get('CPU') != cpu
            or owner.get('controller_PID') != receipt['controller_PID']
            or owner.get('process_start_ticks') != receipt['process_start_ticks']
            or claim.get('controller_PID') != receipt['controller_PID']
            or claim.get('controller_output') != str(Path(directory).parent)
            or receipt['controller_lease_inode'] != lease_inode):
        raise ValueError('EXACT_SAVED_CS_PID_START_CONTROLLER_AND_LEASE_BINDINGS_REQUIRED')


def saved_minute(raw, rows):
    if type(rows) is not int or not 0 <= rows <= 525600:
        raise ValueError('BOUNDED_SAVED_NATIVE_MINUTES_REQUIRED')
    with zipfile.ZipFile(BytesIO(raw)) as archive:
        info = archive.infolist()
        if (len(info) != 2 or {x.filename for x in info} != {'values.npy', 'columns.npy'}
                or any(x.flag_bits & 1 or x.is_dir() or stat.S_ISLNK(x.external_attr >> 16)
                       or x.file_size > r.LIMITS['per_case_output_bytes'] for x in info)
                or sum(x.file_size for x in info) > r.LIMITS['per_case_output_bytes']):
            raise ValueError('BOUNDED_EXACT_SAVED_MINUTE_ARCHIVE_REQUIRED')
        headers = {}
        for member in info:
            with archive.open(member) as stream:
                version = np.lib.format.read_magic(stream)
                if version not in ((1, 0), (2, 0)):
                    raise ValueError('SUPPORTED_SAVED_MINUTE_NPY_HEADER_REQUIRED')
                reader = np.lib.format.read_array_header_1_0 if version == (1, 0) else np.lib.format.read_array_header_2_0
                shape, fortran, dtype = reader(stream, max_header_size=4096)
                if fortran or dtype.hasobject:
                    raise ValueError('ORDINARY_NUMERIC_SAVED_MINUTE_HEADER_REQUIRED')
                if member.filename == 'values.npy':
                    if dtype != np.dtype('float64') or len(shape) != 2 or shape[0] != rows or not 1 <= shape[1] <= 128:
                        raise ValueError('EXACT_BOUNDED_SAVED_MINUTE_MATRIX_HEADER_REQUIRED')
                elif dtype.kind != 'U' or not 0 < dtype.itemsize <= 512 or len(shape) != 1 or not 1 <= shape[0] <= 128:
                    raise ValueError('EXACT_BOUNDED_SAVED_MINUTE_COLUMNS_HEADER_REQUIRED')
                if stream.tell() + int(np.prod(shape)) * dtype.itemsize != member.file_size:
                    raise ValueError('EXACT_SAVED_MINUTE_NPY_PAYLOAD_LENGTH_REQUIRED')
                headers[member.filename] = shape
        if headers['values.npy'][1] != headers['columns.npy'][0]:
            raise ValueError('EXACT_SAVED_MINUTE_COLUMN_COUNT_REQUIRED')
    with np.load(BytesIO(raw), allow_pickle=False) as arrays:
        values, columns = arrays['values'], arrays['columns']
    if (values.dtype != np.dtype('float64') or values.ndim != 2 or values.shape[0] != rows
            or not 1 <= values.shape[1] <= 128 or not np.isfinite(values).all()
            or columns.ndim != 1 or columns.dtype.kind != 'U' or len(columns) != values.shape[1]
            or len(set(columns.tolist())) != len(columns)):
        raise ValueError('FINITE_EXACT_COMPLETED_NATIVE_MINUTE_MATRIX_REQUIRED')
    return values, columns.tolist()


def saved_worker_phases(first, second, *, receipt, claim_raw, source_guard_raw):
    fixed=dict(schema='CS_WORKER_PREFINANCE_PHASE_V1', cell_id=receipt['cell_id'],
        root_GO_SHA256=receipt['root_GO_SHA256'], preparation_SHA256=receipt['preparation_SHA256'],
        PID=receipt['PID'], historical_scopes_constructed=0, providers_constructed=0, accounts_constructed=0)
    for value in (first,second):
        if any(type(value.get(k)) is not type(v) or value.get(k)!=v for k,v in fixed.items()):
            raise ValueError('EXACT_SAVED_PREACCOUNT_PHASE_REQUIRED')
        if type(value.get('UTC')) is not str:
            raise ValueError('EXACT_SAVED_PHASE_UTC_REQUIRED')
    if (first.get('phase')!='EXACT_EXECUTABLE_GO_VERIFIED_OUTSIDE_UNCHANGED_SOURCE_GUARD'
            or first.get('financial_code_manifest_SHA256')!=receipt['financial_code_manifest_SHA256']
            or first.get('claim_SHA256')!=c.sha(claim_raw) or first.get('source_capture_started') is not False
            or second.get('phase')!='SOURCE_RECAPTURE_AND_SAVED_TARGET_BINDING_ACCEPTED_GUARD_EXITED'
            or second.get('source_guard_receipt_SHA256')!=c.sha(source_guard_raw)
            or second.get('verified_wires_revoked') is not True or second['UTC']<first['UTC']):
        raise ValueError('EXACT_SAVED_AUTHORITY_SOURCE_BEFORE_ACCOUNT_PHASE_CHAIN_REQUIRED')
    return True


def validate_saved_terminal(directory, *, args, cell_id):
    import run_cs
    import cs_native as native
    from saved_native_reconciliation import reconcile_saved_native, checker_sha256
    directory = run_cs.ordinary(directory)
    prep_raw, prep, blobs = run_cs.wires(args)
    cell = config.cell_named(cell_id); calendar = [cell['start_us'], cell['end_exclusive_us']]
    checkpoint = c.exact_object((directory / 'TERMINAL_CHECKPOINT.json').read_bytes())
    if (checkpoint.get('cell_id') != cell_id or checkpoint.get('all_evidence_fsynced') is not True
            or checkpoint.get('restart_financial_snapshot_permission') is not False
            or checkpoint.get('fresh_scope_revoked') is not True
            or set(checkpoint.get('files', {})) != set(run_cs.TERMINAL_FILES)
            or checkpoint.get('checker_SHA256') != checker_sha256()):
        raise ValueError('EXACT_ALL_SAVED_TERMINAL_SCOPE_BYTES_REQUIRED')
    saved = {name: c.exact(directory / name, digest) for name, digest in checkpoint['files'].items()}
    for name, key in (('ADMISSION_GO.json', 'go'), ('ADMISSION_REVIEW.json', 'review'),
                      ('PREPARED_TARGET_REVIEW.json', 'prepared-review'), ('NATIVE_GENERATED_REVIEW.json', 'native-review')):
        if saved[name] != blobs[key]: raise ValueError('EXACT_SAVED_NEW_CS_AUTHORITY_CHAIN_REQUIRED')
    claim = run_cs.ordinary(run_cs.supersession.claim_path(cell_id)).read_bytes()
    if saved['LAUNCH_CLAIM.json'] != claim: raise ValueError('EXACT_CANONICAL_CS_LAUNCH_CLAIM_REQUIRED')
    receipt = c.exact_object(saved['CASE_RECEIPT.json'])
    fixed = dict(schema='FINITE_CSMOM21_FIRST6_ORIGINAL_D_CASE_V2', cell_id=cell_id,
        year=cell['year'], strategy=config.STRATEGY, tier=cell['tier'], config=config.STRATEGY + '_' + cell['tier'],
        calendar=calendar, cost='BASE27', policy_variant=native.POLICY_VARIANT, adaptive_DEV_only=True,
        root_GO_SHA256=args.go_sha, independent_review_SHA256=args.review_sha,
        prepared_source_target_review_SHA256=args.prepared_review_sha, native_generated_review_SHA256=args.native_review_sha,
        preparation_SHA256=c.sha(prep_raw), scope_manifest_SHA256=run_cs.SCOPE_SHA,
        source_identity=prep['years'][str(cell['year'])]['source_identity'],
        source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256, financial_code_manifest_SHA256=gate.code_identity(),
        input_binding_SHA256=prep['cells'][cell_id]['input_binding_SHA256'], checker_SHA256=checker_sha256(),
        required_minutes=cell['calendar_days'] * 1440, limits=r.LIMITS, no_halt_reset=True,
        snapshot_restart_certified=False, automatic_retry=False,
        native_exchange_or_funding_publication_certified=False, locked_source_reads=0, publication_actions=0)
    if any(c.canonical(receipt.get(k)) != c.canonical(v) for k, v in fixed.items()):
        raise ValueError('EXACT_SAVED_CS_CASE_BINDINGS_REQUIRED')
    saved_worker_phases(c.exact_object(saved['WORKER_AUTHORITY_VERIFIED.json']),
        c.exact_object(saved['WORKER_SOURCE_ACCEPTED_BEFORE_ACCOUNT.json']), receipt=receipt,
        claim_raw=claim, source_guard_raw=saved['SOURCE_RECAPTURE_GUARD_RECEIPT.json'])
    claim_value = c.exact_object(claim)
    cloned_args = SimpleNamespace(**vars(args)); cloned_args.cell_id = cell_id
    cloned_args.case_output = str(directory); cloned_args.cpu = receipt['requested_CPU']
    if any(c.canonical(claim_value.get(k)) != c.canonical(v)
           for k, v in run_cs.expected_claim(cloned_args, prep_raw, prep).items()):
        raise ValueError('EXACT_SAVED_CS_CLAIM_BINDINGS_REQUIRED')
    audit = c.exact_object(saved['ACCOUNT_FINANCIAL_AUDIT.json'])
    result = c.exact_object(saved['NATIVE_RESULT.json'])
    saved_account_contract(audit, result, cell['tier'])
    proof = reconcile_saved_native(audit, result, expected_continuation_version=native.VERSION)
    if (r.body(proof) != saved['NATIVE40_RECONSTRUCTION_PROOF.json']
            or r.body(proof) != saved['PRIMARY_FINANCIAL_RECONCILIATION.json']
            or c.sha(r.body(proof)) != receipt['reconstruction_proof_SHA256']
            or checkpoint['reconstruction_proof_SHA256'] != receipt['reconstruction_proof_SHA256']
            or result['primary_financial_reconciliation'] != c.exact_object(saved['LEGACY_PRIMARY_FINANCIAL_RECONCILIATION.json'])):
        raise ValueError('EXACT_NATIVE40_AND_UNCHANGED_RAW100_RESIDUAL_BINDINGS_REQUIRED')
    classification = r.classify_terminal(audit, result, calendar=calendar,
        completed_minutes=receipt['completed_minutes'], stop_us=receipt['account_stop_us'])
    if receipt['status'] != classification: raise ValueError('EXACT_SAVED_CS_TERMINAL_TAXONOMY_REQUIRED')
    values, columns = saved_minute(saved['MINUTE.npz'], receipt['completed_minutes'])
    required = ['close_us', 'nav', 'free_cash', 'isolated_balance', 'gross_weight'] + [s + '_signed_weight' for s in native.S]
    if any(name not in columns for name in required): raise ValueError('EXACT_NATIVE_MINUTE_EXPOSURE_COLUMNS_REQUIRED')
    clocks = values[:, columns.index('close_us')]
    if not np.array_equal(clocks, calendar[0] + np.arange(1, len(values) + 1, dtype=np.int64) * codec.MINUTE):
        raise ValueError('EXACT_SAVED_CS_CONTIGUOUS_MINUTE_CALENDAR_REQUIRED')
    if len(values) and receipt['account_stop_us'] is None:
        for column, key in (('nav', 'NAV'), ('free_cash', 'free_cash'), ('isolated_balance', 'isolated_balance'), ('gross_weight', 'gross_weight')):
            if float(values[-1, columns.index(column)]) != result['summary'][key]:
                raise ValueError('EXACT_SAVED_NATIVE_FINAL_MINUTE_PROJECTION_REQUIRED')
    year_info = prep['years'][str(cell['year'])]; days = cell['calendar_days']
    name = str(cell['year']) + '/TARGETS.npz'; pin = prep['artifacts'][name]
    target_raw = c.exact(Path(args.preparation) / name, pin['SHA256'], pin['bytes'])
    specs = {key: ((days,) if key == 'decision_us' else (days, 5, 5) if key == 'annual_covariance' else (days, 5),
                   'int64' if key == 'decision_us' else 'float64') for key in year_info['array_raw_SHA256']}
    arrays = codec.npz(target_raw, specs)
    if any(c.sha(a.tobytes()) != year_info['array_raw_SHA256'][k] for k, a in arrays.items()):
        raise ValueError('EXACT_SAVED_CS_TARGET_COVARIANCE_RAW_BITS_REQUIRED')
    risk = run_cs.held_risk(values, columns, SimpleNamespace(arrays=arrays), cell['tier'], c.object_json(saved['GUARD_RECEIPTS.json']))
    if r.body(risk) != saved['ACTUAL_HELD_RISK_REPORT.json']:
        raise ValueError('EXACT_SAVED_ACTUAL_HELD_RISK_RECOMPUTATION_REQUIRED')
    binding = audit['historical_execution_scope']
    for key in ('cell_id', 'year', 'strategy', 'config', 'preparation_SHA256', 'source_identity',
                'root_GO_SHA256', 'independent_review_SHA256', 'policy_variant',
                'source_code_manifest_SHA256', 'financial_code_manifest_SHA256', 'input_binding_SHA256',
                'prepared_source_target_review_SHA256', 'native_generated_review_SHA256'):
        if binding.get(key) != receipt[key]: raise ValueError('EXACT_AUDIT_CS_EXECUTION_SCOPE_REQUIRED:' + key)
    quality_name = str(cell['year']) + '/MINUTE_MARK_PROVENANCE.json'; quality_pin = prep['artifacts'][quality_name]
    sidecar_raw = c.exact(Path(args.preparation) / quality_name, quality_pin['SHA256'], quality_pin['bytes'])
    sidecar = c.exact_object(sidecar_raw)
    if (c.sha(sidecar_raw) != year_info['source_quality_sidecar_SHA256']
            or binding.get('quality_sidecar_sha256') != c.sha(sidecar_raw)
            or c.canonical(binding.get('quality_intervals')) != c.canonical(sidecar['quality_intervals'])):
        raise ValueError('EXACT_SAVED_CS_SCOPE_QUALITY_SIDECAR_AND_INTERVALS_REQUIRED')
    expected_quality = quality_identity(sidecar, year_info, native.V2.quality_module.VERSION)
    quality = c.exact_object(saved['CAUSAL_MARK_QUALITY.json']); quality_sha = c.jsha(expected_quality)
    if (c.canonical(quality['identity']) != c.canonical(expected_quality) or quality['policy_SHA256'] != quality_sha
            or quality['original_interpolated_marks_execution_admitted'] is not False
            or quality['actual_CS_event_and_position_impacts'] != 'REQUIRE_SEPARATE_SAVED_AUDIT_NOT_INHERITED_FROM_D'
            or result['target_meta']['mark_quality_policy_identity'] != quality_sha
            or result['target_meta']['mark_quality_guard_version'] != native.V2.quality_module.VERSION):
        raise ValueError('EXACT_RECONSTRUCTED_CS_QUALITY_POLICY_REQUIRED')
    guard = c.exact_object(saved['SOURCE_RECAPTURE_GUARD_RECEIPT.json'])
    saved_source_guard(guard)
    saved_resources(receipt, c.exact_object(saved['BOOTSTRAP_READY.json']),
        c.exact_object(saved['PROCESS_OWNERSHIP.json']), claim_value,
        lease_inode=(run_cs.supersession.registry_root() / run_cs.SCOPE_SHA / 'CONTROLLER_LEASE.lock').stat().st_ino,
        directory=directory)
    if (receipt['actual_CPU_affinity'] != [receipt['requested_CPU']]
            or receipt['requested_CPU'] not in [4, 5]
            or any(row != [receipt['requested_CPU']] for row in receipt['all_TID_affinities'])
            or receipt['thread_environment'] != {key: '1' for key in r.THREAD_ENV}
            or receipt['total_wall_seconds'] > 600 or receipt['CPU_seconds'] > 600
            or receipt['max_RSS_bytes'] > r.LIMITS['per_case_RSS_stop_bytes']
            or r.own_bytes(directory) > r.LIMITS['per_case_output_bytes']):
        raise ValueError('EXACT_SAVED_CS_RESOURCE_BINDINGS_REQUIRED')
    return receipt
