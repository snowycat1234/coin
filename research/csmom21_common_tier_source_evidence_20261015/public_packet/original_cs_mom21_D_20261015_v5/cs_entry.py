"""Fresh portable pure-CS source and financial authority, never old-D aliases.

Metadata validators mint no authority. Actual source scopes require a fresh
externally digest-bound review and root GO under the whole source-only guard.
Financial scopes have a separate later review/GO and exact saved-target chain.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

import cs_common as c
import cs_config as config

MANIFEST_NAME = 'FROZEN_FIFTEEN_CELL_MANIFEST.json'
CONTRACT_NAME = 'SOURCE_CONTRACT_MAP.json'
SOURCE_SCHEMA = 'ROOT_SOURCE_TARGET_CSMOM21_COMMON_TIER_V2'
SOURCE_REVIEW_SCHEMA = 'INDEPENDENT_CSMOM21_SOURCE_GENERATED_REVIEW_V2'
FINANCIAL_SCHEMA = 'ROOT_FINANCIAL_CSMOM21_COMMON_TIER_V2'
FINANCIAL_REVIEW_SCHEMA = 'INDEPENDENT_CSMOM21_PREPARED_TARGET_REVIEW_V2'
FIRST6 = 'FIRST6_2022_2023_ALL_THREE_TIERS'
REMAINING9 = 'REMAINING9_2021_2024_2025_ALL_THREE_TIERS'
_SOURCE_SEAL = object()
_FINANCIAL_SEAL = object()
_RECORD_SEAL = object()
_ACTIVE_SOURCE = {}
_ACTIVE_FINANCIAL = {}
_ACTIVE_RECORDING = set()


def manifest():
    value = c.exact_object((c.HERE / MANIFEST_NAME).read_bytes())
    expected = list(config.cells())
    if (value.get('schema') != 'PORTABLE_CSMOM21_COMMON_TIER_FIFTEEN_DEV_V2'
            or c.canonical(value.get('cells')) != c.canonical(expected)
            or value.get('candidate') != config.STRATEGY or value.get('cell_count') != 15
            or value.get('source_tranche_order') != [FIRST6, REMAINING9]
            or value.get('financial_policy_changes_allowed') is not False):
        raise ValueError('EXACT_PREDECLARED_FIFTEEN_CELL_SCOPE_REQUIRED')
    return value


def manifest_sha():
    manifest()
    return c.sha((c.HERE / MANIFEST_NAME).read_bytes())


def tranche_cells(tranche):
    years = {FIRST6: (2022, 2023), REMAINING9: (2021, 2024, 2025)}
    if tranche not in years:
        raise ValueError('EXACT_PREDECLARED_TRANCHE_REQUIRED')
    return tuple(row['cell_id'] for year in years[tranche] for row in config.cells() if row['year'] == year)


def tranche_years(tranche):
    return tuple(dict.fromkeys(config.cell_named(cell)['year'] for cell in tranche_cells(tranche)))


def contracts():
    raw = (c.HERE / CONTRACT_NAME).read_bytes()
    value = c.exact_object(raw)
    if c.sha(raw) != manifest()['source_contract_map_SHA256'] or set(value['years']) != {'2021', '2022', '2023', '2024', '2025'}:
        raise ValueError('EXACT_FROZEN_FIVE_YEAR_SOURCE_CONTRACT_REQUIRED')
    return value


def contract_sha():
    contracts()
    return manifest()['source_contract_map_SHA256']


def code_identity():
    raw = (c.HERE / 'CODE_MANIFEST.json').read_bytes()
    record = c.exact_object(raw)
    for name, pin in record['files'].items():
        c.exact(c.HERE / c.relative(name), pin['SHA256'], pin['bytes'])
    for name, pin in record['dependencies'].items():
        path = c.ROOT / c.relative(name)
        if path.suffix not in ('.py', '.json', '.md'):
            raise ValueError('CODE_METADATA_DEPENDENCY_ONLY')
        c.exact(path, pin['SHA256'], pin['bytes'])
    return c.sha(raw)


def _review(raw, expected, schema, *, tranche, preparation_sha=None):
    value = c.checked_external(raw, expected)
    fixed = dict(schema=schema, status='PASS', code_manifest_SHA256=code_identity(),
                 scope_manifest_SHA256=manifest_sha(), source_contract_map_SHA256=contract_sha(),
                 tranche=tranche, ordered_cells=list(tranche_cells(tranche)), years=list(tranche_years(tranche)))
    if preparation_sha is not None:
        fixed['preparation_SHA256'] = preparation_sha
    if any(c.canonical(value.get(key)) != c.canonical(wanted) for key, wanted in fixed.items()):
        raise ValueError('EXACT_NEW_PURE_CS_INDEPENDENT_REVIEW_REQUIRED')
    if value.get('old_D_GO_reused_as_authority') is not False:
        raise ValueError('OLD_D_AUTHORITY_FORBIDDEN')
    return value


def source_policy(tranche, review_sha):
    if tranche != FIRST6:
        raise ValueError('ONLY_PREDECLARED_FIRST6_SOURCE_ENTRY_ENABLED_AT_THIS_CHECKPOINT')
    years = tranche_years(tranche)
    return dict(schema=SOURCE_SCHEMA, action='PREPARE_EXACT_' + tranche + '_CS_SOURCE_TARGETS_ONLY',
        status='APPROVED_SOURCE_TARGET_ONLY', candidate=config.STRATEGY, tranche=tranche,
        ordered_cells=list(tranche_cells(tranche)), years=list(years),
        code_manifest_SHA256=code_identity(), scope_manifest_SHA256=manifest_sha(),
        source_contract_map_SHA256=contract_sha(), independent_review_SHA256=c.digest(review_sha),
        source_identities={str(year): contracts()['years'][str(year)]['source_identity'] for year in years},
        canonical_source_capture_authorized=True, target_generation_authorized=True,
        source_only_2022_memory_normalization_authorized=2022 in years,
        source_only_2022_cache_creation_authorized=False,
        historical_execution_authorized=False, financial_execution_authorized=False,
        account_construction_authorized=False, provider_iteration_authorized=False,
        process_launch_authorized=False, canonical_claims_authorized=False,
        financial_GO_authorized=False, publication_authorized=False, old_D_GO_reused_as_authority=False,
        source_limits=dict(CPU_seconds=900, wall_seconds=1800, AS_bytes=3000000000,
                           output_bytes=1073741824, process_count=1, numerical_pools=1))


def validate_source_authority_metadata(go_raw, expected_go_sha256, review_raw, expected_review_sha256):
    """Pure exact wire validator. This return value is not an actual scope."""
    value = c.checked_external(go_raw, expected_go_sha256)
    if value.get('tranche') != FIRST6:
        raise ValueError('ONLY_FIRST6_HAS_A_SOURCE_ENTRY_CHECKPOINT')
    review = _review(review_raw, expected_review_sha256, SOURCE_REVIEW_SCHEMA, tranche=value['tranche'])
    expected = source_policy(value.get('tranche'), expected_review_sha256)
    if c.canonical(value) != c.canonical(expected):
        raise ValueError('EXACT_SOURCE_TARGET_ONLY_CS_ROOT_AUTHORITY_REQUIRED')
    return c.immutable(dict(policy=value, root_go_SHA256=expected_go_sha256,
                            review_SHA256=expected_review_sha256))


@dataclass(frozen=True, slots=True)
class SourceQualification:
    year: int
    source_identity: str
    source_contract_SHA256: str


@dataclass(frozen=True, slots=True)
class SourcePreparationScope:
    tranche: str
    source_go_sha256: str
    review_sha256: str
    raw_go: bytes = field(repr=False)
    raw_review: bytes = field(repr=False)
    _code: str = field(repr=False)
    _token: object = field(repr=False)
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _SOURCE_SEAL:
            raise ValueError('FRESH_CS_SOURCE_SCOPE_SEAL_REQUIRED')

    def validate_current(self, *, year=None):
        if _ACTIVE_SOURCE.get(self._token) is not self or self._code != code_identity():
            raise ValueError('LIVE_CURRENT_CS_SOURCE_STAGE_SCOPE_REQUIRED')
        validate_source_authority_metadata(self.raw_go, self.source_go_sha256, self.raw_review, self.review_sha256)
        if year is not None and (type(year) is not int or year not in tranche_years(self.tranche)):
            raise ValueError('EXACT_SOURCE_TRANCHE_YEAR_REQUIRED')
        from cs_source_guard import current_guard
        guard = current_guard()
        if guard is None or not guard.active:
            raise ValueError('WHOLE_INVOCATION_CS_SOURCE_ONLY_GUARD_REQUIRED')
        guard.checkpoint('SOURCE_SCOPE_CHECK')
        return True

    def qualification_for(self, year):
        self.validate_current(year=year)
        record = contracts()['years'][str(year)]
        return SourceQualification(year, record['source_identity'], c.jsha(record))

    def source_root(self, year):
        self.validate_current(year=year)
        return c.ROOT / c.relative(contracts()['years'][str(year)]['source_root'])

    def read_source(self, year, workspace_relative_name, expected_sha256, expected_bytes=None):
        self.validate_current(year=year)
        name = c.relative(workspace_relative_name)
        files = contracts()['years'][str(year)]['read_files']
        pin = files.get(name)
        if (pin is None or pin['SHA256'] != expected_sha256
                or expected_bytes is not None and (type(expected_bytes) is not int or expected_bytes != pin['bytes'])):
            raise ValueError('EXACT_QUALIFIED_YEAR_SOURCE_READ_ALLOWLIST_REQUIRED')
        return c.exact(c.ROOT / name, expected_sha256, pin['bytes'])


@contextmanager
def admit_source_stage(go_raw, expected_go_sha256, review_raw, expected_review_sha256):
    value = validate_source_authority_metadata(go_raw, expected_go_sha256, review_raw, expected_review_sha256)
    from cs_source_guard import current_guard
    guard = current_guard()
    if guard is None or not guard.active:
        raise ValueError('WHOLE_INVOCATION_CS_SOURCE_ONLY_GUARD_REQUIRED')
    token = object()
    scope = SourcePreparationScope(value['policy']['tranche'], expected_go_sha256, expected_review_sha256,
        go_raw, review_raw, code_identity(), token, _SOURCE_SEAL)
    _ACTIVE_SOURCE[token] = scope
    try:
        scope.validate_current()
        yield scope
    finally:
        _ACTIVE_SOURCE.pop(token, None)


@dataclass(frozen=True, slots=True)
class RecordingScope:
    cell_id: str
    binding_SHA256: str
    _token: object = field(repr=False)
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _RECORD_SEAL:
            raise ValueError('ENTRY_OWNED_RECORDING_SCOPE_ONLY')

    def validate_current(self):
        if self._token not in _ACTIVE_RECORDING:
            raise ValueError('RECORDING_SCOPE_REVOKED')
        return True


def record_metadata_bindings(preparation, callback):
    """All finite metadata callbacks; never a source/provider/account scope."""
    preparation = validate_preparation_metadata(c.canonical(preparation))
    cells = preparation.get('cells', {})
    ordered = tranche_cells(preparation.get('tranche'))
    if set(cells) != set(ordered):
        raise ValueError('EXACT_TRANCHE_METADATA_CELLS_REQUIRED')
    returned = []
    for cell_id in ordered:
        token = object(); _ACTIVE_RECORDING.add(token)
        scope = RecordingScope(cell_id, c.digest(cells[cell_id]['input_binding_SHA256']), token, _RECORD_SEAL)
        try:
            scope.validate_current(); callback(scope); returned.append(cell_id)
        finally:
            _ACTIVE_RECORDING.discard(token)
    return dict(ordered_cells=returned, metadata_scopes_revoked=not _ACTIVE_RECORDING,
                historical_scopes_created=0, actual_provider_iterations=0, accounts_created=0)


def validate_preparation_metadata(raw):
    value = c.exact_object(raw)
    ordered = tranche_cells(value.get('tranche'))
    fixed = dict(schema='PREPARED_CSMOM21_SOURCE_TARGET_ONLY_V2', candidate=config.STRATEGY,
        code_manifest_SHA256=code_identity(), scope_manifest_SHA256=manifest_sha(),
        source_contract_map_SHA256=contract_sha(), ordered_cells=list(ordered),
        historical_admission=False, financial_runs=0, accounts_created=0, accounts_advanced=0,
        provider_iterations=0, process_launches=0, canonical_claims_created=0,
        real_financial_GO_written=0, publication_actions=0)
    if any(c.canonical(value.get(key)) != c.canonical(wanted) for key, wanted in fixed.items()):
        raise ValueError('EXACT_SEPARATE_CS_SOURCE_TARGET_PREPARATION_REQUIRED')
    if (set(value.get('cells', {})) != set(ordered)
            or set(value.get('years', {})) != {str(y) for y in tranche_years(value['tranche'])}):
        raise ValueError('EXACT_PREDECLARED_TRANCHE_YEAR_CELL_BINDINGS_REQUIRED')
    c.digest(value.get('source_stage_GO_SHA256')); c.digest(value.get('source_review_SHA256'))
    artifacts = value.get('artifacts')
    if type(artifacts) is not dict:
        raise ValueError('EXACT_SAVED_CS_SOURCE_TARGET_ARTIFACT_PINS_REQUIRED')
    for name, pin in artifacts.items():
        c.relative(name)
        if type(pin) is not dict or set(pin) != {'SHA256', 'bytes'} or type(pin['bytes']) is not int or pin['bytes'] < 0:
            raise ValueError('EXACT_ARTIFACT_BYTE_PIN_REQUIRED')
        c.digest(pin['SHA256'])
    for name, digest in (('SOURCE_STAGE_AUTHORIZATION.json', value['source_stage_GO_SHA256']),
                         ('SOURCE_INDEPENDENT_REVIEW.json', value['source_review_SHA256'])):
        if artifacts.get(name, {}).get('SHA256') != digest:
            raise ValueError('EXACT_DIRECT_NEW_SOURCE_GO_REVIEW_LINEAGE_REQUIRED')
    for year in tranche_years(value['tranche']):
        info = value['years'][str(year)]; period = config.period_named(year)
        contract = contracts()['years'][str(year)]
        required = dict(source_identity=contract['source_identity'], source_contract_SHA256=c.jsha(contract),
                        days=period['days'], calendar=[period['start'], period['end']],
                        provider_months_source='MEMORY_ONLY_EXACT_OLD_NATIVE_CAPTURE' if year == 2022 else 'EXISTING_PINNED_CANONICAL_MONTHS',
                        quality_cells_SHA256=contract.get('normalized_quality_cells_SHA256', c.jsha([])),
                        all_CS_position_and_event_impacts_pending=True)
        if any(c.canonical(info.get(key)) != c.canonical(wanted) for key, wanted in required.items()):
            raise ValueError('EXACT_QUALIFIED_YEAR_SOURCE_QUALITY_LINEAGE_REQUIRED')
        for key in ('source_quality_sidecar_SHA256', 'source_rows_SHA256', 'funding_events_SHA256'):
            c.digest(info.get(key))
        expected_array_keys = {'decision_us', 'annual_covariance', 'weekly_raw_CS', 'original_sized_CS'} | {
            config.STRATEGY + '_' + tier for tier in config.TIERS}
        if set(info.get('array_raw_SHA256', {})) != expected_array_keys:
            raise ValueError('EXACT_RAW_ORIGINAL_COMMON_TIER_TARGET_STAGE_PINS_REQUIRED')
        for digest in info['array_raw_SHA256'].values():
            c.digest(digest)
        needed = {'TARGETS.npz', 'SOURCE_INPUTS.npz', 'RAW_EVENTS.json', 'MINUTE_MARK_PROVENANCE.json', 'TARGET_PROOFS.json'}
        if year == 2022:
            needed.add('NORMALIZATION_EQUIVALENCE.json')
        if any(str(year) + '/' + name not in artifacts for name in needed):
            raise ValueError('EXACT_YEAR_SOURCE_TARGET_QUALITY_ARTIFACTS_REQUIRED')
        if artifacts[str(year) + '/MINUTE_MARK_PROVENANCE.json']['SHA256'] != info['source_quality_sidecar_SHA256']:
            raise ValueError('EXACT_CS_SOURCE_QUALITY_SIDECAR_PIN_REQUIRED')
    for cell_id in ordered:
        cell = value['cells'][cell_id]
        if c.canonical(cell.get('descriptor')) != c.canonical(config.cell_named(cell_id)):
            raise ValueError('EXACT_CS_CELL_DESCRIPTOR_REQUIRED')
        binding = cell.get('input_binding')
        if (type(binding) is not dict or c.jsha(binding) != cell.get('input_binding_SHA256')
                or binding.get('cell_id') != cell_id or binding.get('strategy') != config.STRATEGY):
            raise ValueError('EXACT_CS_CELL_SOURCE_TARGET_BINDING_REQUIRED')
        descriptor = config.cell_named(cell_id); year = descriptor['year']; tier = descriptor['tier']
        contract = contracts()['years'][str(year)]; info = value['years'][str(year)]; hashes = info['array_raw_SHA256']
        expected_binding = dict(schema='EXACT_NEW_CS_CELL_SOURCE_TARGET_BINDING_V2', cell_id=cell_id,
            strategy=config.STRATEGY, year=year, tier=tier,
            calendar=[descriptor['start_us'], descriptor['end_exclusive_us']],
            source_identity=contract['source_identity'], source_contract_SHA256=c.jsha(contract),
            source_rows_SHA256=info['source_rows_SHA256'], funding_events_SHA256=info['funding_events_SHA256'],
            source_quality_sidecar_SHA256=info['source_quality_sidecar_SHA256'], quality_cells_SHA256=info['quality_cells_SHA256'],
            provider_months=[[rec['path'], rec['start'], rec['count'], rec['hash'], rec['size'], rec['lo'], rec['hi']]
                             for rec in contract['months']],
            decision_raw_SHA256=hashes['decision_us'], covariance_raw_SHA256=hashes['annual_covariance'],
            weekly_raw_CS_SHA256=hashes['weekly_raw_CS'], original_sized_CS_SHA256=hashes['original_sized_CS'],
            selected_target_raw_SHA256=hashes[config.STRATEGY + '_' + tier], cost='BASE27', policy_variant='GUARD50_EXIT_ONLY',
            quantity_profile_SHA256='94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf')
        if c.canonical(binding) != c.canonical(expected_binding):
            raise ValueError('EXACT_YEAR_TIER_CALENDAR_SOURCE_RAW_SIZED_TARGET_QUALITY_NATIVE_BINDING_REQUIRED')
    return value


def financial_policy(preparation_raw, tranche, review_sha):
    preparation = validate_preparation_metadata(preparation_raw)
    if preparation['tranche'] != tranche:
        raise ValueError('EXACT_PREPARED_TRANCHE_REQUIRED')
    return dict(schema=FINANCIAL_SCHEMA, status='APPROVED_FRESH_FINANCIAL_ONLY',
        action='RUN_FRESH_EXACT_' + tranche + '_CS_ORIGINAL_D_ONLY', candidate=config.STRATEGY,
        tranche=tranche, ordered_cells=list(tranche_cells(tranche)),
        preparation_SHA256=c.sha(preparation_raw), code_manifest_SHA256=code_identity(),
        scope_manifest_SHA256=manifest_sha(), source_contract_map_SHA256=contract_sha(),
        source_stage_GO_SHA256=preparation['source_stage_GO_SHA256'],
        independent_review_SHA256=c.digest(review_sha),
        per_cell_input_binding_SHA256={cell: preparation['cells'][cell]['input_binding_SHA256'] for cell in tranche_cells(tranche)},
        policy_variant='GUARD50_EXIT_ONLY', cost='BASE27', initial_cash_USDT='10000',
        free_cash_floor_USDT='1000', isolated_margin_ceiling_USDT='8500', automatic_topup=False,
        internal_margin_transfers=False, new_capital=False, debt_forgiveness=False,
        fresh_genesis_only=True, automatic_retry_authorized=False, halted_snapshot_resume_authorized=False,
        historical_execution_authorized=True, account_construction_authorized=True,
        provider_iteration_authorized=True, financial_execution_authorized=True,
        other_cells_or_holdouts_authorized=False, old_D_GO_reused_as_authority=False,
        publication_authorized=False)


def validate_financial_authority_metadata(preparation_raw, go_raw, expected_go_sha256, review_raw, expected_review_sha256):
    preparation = validate_preparation_metadata(preparation_raw)
    _review(review_raw, expected_review_sha256, FINANCIAL_REVIEW_SCHEMA, tranche=preparation['tranche'],
            preparation_sha=c.sha(preparation_raw))
    value = c.checked_external(go_raw, expected_go_sha256)
    if c.canonical(value) != c.canonical(financial_policy(preparation_raw, preparation['tranche'], expected_review_sha256)):
        raise ValueError('EXACT_FRESH_CS_FINANCIAL_AUTHORITY_REQUIRED')
    return c.immutable(value)
