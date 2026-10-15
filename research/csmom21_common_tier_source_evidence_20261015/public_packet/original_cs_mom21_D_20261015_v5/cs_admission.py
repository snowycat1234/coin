"""Additive actual CS scope/provider, admitted only after saved-input loading.

Import after the clean source-only loader exits. There is no generated flag or
callback in this actual constructor. No old-D scope or GO body is consumed.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import MappingProxyType

import polars as pl

import cs_common as c
import cs_codec as codec
import cs_config as config
import cs_entry as entry
import cs_finance_gate as gate
import cs_loader as loader
from cs_signal import SYMBOLS

_SEAL = object()
_LIVE = {}
SOURCE_SCOPE = 'EXACT_NEW_CSMOM21_FIRST6_SAVED_INPUTS_ORIGINAL_D_V2'


@dataclass(frozen=True, slots=True)
class CapturedMinuteProvider:
    year: int
    _loaded: object = field(repr=False)
    _scope: object = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        if type(self._loaded) is not loader.LoadedInputs or self.year != self._loaded.year:
            raise ValueError('EXACT_NEW_CS_SAVED_INPUT_PROVIDER_REQUIRED')
        self._loaded.validate()

    def _bind(self, scope):
        if (type(scope) is not FreshHistoricalExecutionScope or self._scope is not None
                or scope._window['minute_blocks'] is not self):
            raise ValueError('EXACT_LIVE_CS_PROVIDER_SCOPE_REQUIRED')
        scope.validate_current()
        object.__setattr__(self, '_scope', scope)

    @property
    def identity(self):
        source = self._loaded.source
        return dict(year=self.year, source_identity=source['source_identity'],
            months=[[rec['path'], rec['start'], rec['count'], rec['hash'], rec['size'], rec['lo'], rec['hi']]
                    for rec in source['contract']['months']],
            quality_SHA256=c.jsha(source['sidecar']['cells']))

    def __call__(self):
        if type(self._scope) is not FreshHistoricalExecutionScope:
            raise ValueError('NEW_CS_PROVIDER_REQUIRES_FRESH_FINANCIAL_AUTHORITY')
        self._scope.validate_current()
        source = self._loaded.source
        cursor = source['period']['start']
        for rec, (name, raw) in zip(source['contract']['months'], source['months'], strict=True):
            if (name != rec['path'] or c.sha(raw) != rec['hash'] or len(raw) != rec['size']
                    or rec['start'] + rec['lo'] * codec.MINUTE != cursor):
                raise ValueError('EXACT_NEW_CS_PINNED_CHRONOLOGICAL_NATIVE_MONTHS_REQUIRED')
            arrays, _ = codec.month_arrays(self.year, raw, rec['start'], rec['count'], source['quality_cells'])
            for off in range(rec['lo'], rec['hi'], 1440):
                if _LIVE.get(self._scope._token) is not self._scope:
                    raise ValueError('REVOKED_CS_PROVIDER_SCOPE')
                stop = min(off + 1440, rec['hi'])
                yield dict(times=arrays['times'][off:stop], market={symbol:
                    {key: arrays[symbol + '_' + key][off:stop]
                     for key in ('open', 'close', 'quote_volume', 'mark')}
                    for symbol in SYMBOLS})
            cursor = rec['start'] + rec['hi'] * codec.MINUTE
        if cursor != source['period']['end']:
            raise ValueError('EXACT_NEW_CS_NATIVE_END_AND_CLOSING_CALENDAR_REQUIRED')


@dataclass(frozen=True, slots=True)
class FreshHistoricalExecutionScope:
    cell_id: str
    _loaded: object = field(repr=False)
    _go_raw: bytes = field(repr=False)
    _go_sha: str = field(repr=False)
    _review_raw: bytes = field(repr=False)
    _review_sha: str = field(repr=False)
    _prepared_review_raw: bytes = field(repr=False)
    _prepared_review_sha: str = field(repr=False)
    _native_review_raw: bytes = field(repr=False)
    _native_review_sha: str = field(repr=False)
    _window: object = field(repr=False)
    _targets: object = field(repr=False)
    _token: object = field(repr=False)
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _SEAL:
            raise ValueError('EXACT_NEW_CS_FINANCIAL_ADMISSION_ONLY')

    def __deepcopy__(self, memo):
        memo[id(self)] = self
        return self

    @property
    def year(self): return config.cell_named(self.cell_id)['year']
    @property
    def tier_name(self): return config.cell_named(self.cell_id)['tier']
    @property
    def strategy(self): return config.STRATEGY
    @property
    def config(self): return config.STRATEGY + '_' + self.tier_name
    @property
    def policy_variant(self): return 'GUARD50_EXIT_ONLY'
    @property
    def source_scope(self): return SOURCE_SCOPE
    @property
    def quality_cells(self): return self._loaded.source['quality_cells']
    @property
    def quality_intervals(self): return self._loaded.source['quality_intervals']
    @property
    def original_genuine_observation_us(self): return None
    @property
    def quality_sidecar_sha256(self): return c.sha(self._loaded.source['sidecar_raw'])
    @property
    def metadata(self):
        prep = entry.validate_preparation_metadata(self._loaded.preparation_raw)
        return dict(source_scope=SOURCE_SCOPE, cell_id=self.cell_id, year=self.year,
            strategy=self.strategy, tier_name=self.tier_name, config=self.config,
            source_identity=self._loaded.source['source_identity'],
            source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
            financial_code_manifest_SHA256=gate.code_identity(),
            preparation_SHA256=c.sha(self._loaded.preparation_raw),
            input_binding_SHA256=prep['cells'][self.cell_id]['input_binding_SHA256'],
            root_GO_SHA256=self._go_sha, independent_review_SHA256=self._review_sha,
            prepared_source_target_review_SHA256=self._prepared_review_sha,
            native_generated_review_SHA256=self._native_review_sha,
            policy_variant=self.policy_variant, generated_fixture_scope_used=False,
            fresh_genesis_only=True, old_D_GO_reused_as_authority=False,
            quality_sidecar_sha256=self.quality_sidecar_sha256,
            quality_intervals=c.plain(self.quality_intervals),
            actual_CS_gap_impacts='PENDING_CURRENT_SAVED_EXECUTION')

    def validate_inputs(self, window, source_rows, decisions, targets):
        if (window is not self._window or source_rows is not self._loaded.source['source_rows']
                or decisions is not self._loaded.arrays['decision_us'] or targets is not self._targets):
            raise ValueError('EXACT_ENTRY_OWNED_CS_INPUT_REFERENCES_REQUIRED')
        if c.jsha(window['daily'].to_dicts()) != c.jsha(source_rows):
            raise ValueError('EXACT_CS_DAILY_SOURCE_ROWS_REQUIRED')
        return True

    def validate_current(self):
        if _LIVE.get(self._token) is not self or self._seal is not _SEAL:
            raise ValueError('LIVE_NEW_CS_FINANCIAL_SCOPE_REQUIRED')
        if (type(self._loaded) is not loader.LoadedInputs or self.year != self._loaded.year
                or self._loaded.financial_GO_SHA256 != self._go_sha or self._loaded.verified_cell_id != self.cell_id
                or self.cell_id not in entry.tranche_cells(entry.FIRST6)):
            raise ValueError('EXACT_LOADED_FIRST6_YEAR_CELL_REQUIRED')
        self._loaded.validate()
        gate.validate(self._loaded.preparation_raw, self._go_raw, self._go_sha,
            self._review_raw, self._review_sha, self._prepared_review_raw, self._prepared_review_sha,
            self._native_review_raw, self._native_review_sha)
        self.validate_inputs(self._window, self._loaded.source['source_rows'],
                             self._loaded.arrays['decision_us'], self._targets)
        return True


@contextmanager
def admit_case(loaded, *, cell_id, go_raw, expected_go_sha256, review_raw, expected_review_sha256,
               prepared_review_raw, expected_prepared_review_sha256,
               native_review_raw, expected_native_review_sha256):
    if type(loaded) is not loader.LoadedInputs:
        raise ValueError('EXACT_SEALED_SAVED_CS_INPUTS_REQUIRED')
    loaded.validate()
    cell = config.cell_named(cell_id)
    if (cell_id not in entry.tranche_cells(entry.FIRST6) or cell['year'] != loaded.year
            or loaded.financial_GO_SHA256 != expected_go_sha256 or loaded.verified_cell_id != cell_id):
        raise ValueError('EXACT_PREPARED_CS_YEAR_CELL_REQUIRED')
    gate.validate(loaded.preparation_raw, go_raw, expected_go_sha256, review_raw, expected_review_sha256,
                  prepared_review_raw, expected_prepared_review_sha256, native_review_raw, expected_native_review_sha256)
    source = loaded.source
    provider = CapturedMinuteProvider(loaded.year, loaded)
    window = MappingProxyType(dict(start=source['period']['start'], end=source['period']['end'],
        symbols=tuple(SYMBOLS), daily=pl.DataFrame(c.plain(source['source_rows'])),
        events=source['events'], minute_blocks=provider,
        derived_mark_cells=source['sidecar']['derived_mark_cells'],
        original_missing_mark_open_ms=tuple(sorted({cell.minute_open_us // 1000 for cell in source['quality_cells']})),
        original_overlay_future_looking=False, original_overlay_execution_admitted=False,
        causal_mark_adapter=source['sidecar']))
    targets = loaded.arrays[config.STRATEGY + '_' + cell['tier']]
    token = object()
    scope = FreshHistoricalExecutionScope(cell_id, loaded, go_raw, expected_go_sha256,
        review_raw, expected_review_sha256, prepared_review_raw, expected_prepared_review_sha256,
        native_review_raw, expected_native_review_sha256, window, targets, token, _SEAL)
    _LIVE[token] = scope
    try:
        scope.validate_current(); provider._bind(scope)
        import cs_native
        sim, guard = cs_native.construct_case(window, source['source_rows'], loaded.arrays['decision_us'],
                                              targets, historical_scope=scope)
        yield sim, guard, scope
    finally:
        _LIVE.pop(token, None)
