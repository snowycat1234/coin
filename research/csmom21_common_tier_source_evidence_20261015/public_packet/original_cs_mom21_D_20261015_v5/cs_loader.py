"""Additive saved-target loader. Load before any finance imports, under guard.

2022 retains original-D bounded per-process raw recapture cost. There is no IPC,
fork-sharing, persisted month cache, or target/covariance rebuild per case.
"""
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

import numpy as np

import cs_common as c
import cs_codec as codec
import cs_config as config
import cs_entry as entry
import cs_source as source
import cs_finance_gate as gate
import cs_verified_wires as verified

_SEAL = object()
_LIVE = {}


@dataclass(frozen=True, slots=True)
class LoadedInputs:
    year: int
    preparation_raw: bytes = field(repr=False)
    source: object = field(repr=False)
    arrays: object = field(repr=False)
    captured_artifacts: object = field(repr=False)
    financial_GO_SHA256: str
    verified_cell_id: str
    _token: object = field(repr=False)
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _SEAL:
            raise ValueError('ENTRY_OWNED_SAVED_CS_INPUTS_REQUIRED')

    def validate(self):
        if _LIVE.get(self._token) is not self:
            raise ValueError('LIVE_LOADED_CS_INPUTS_REQUIRED')
        prep = entry.validate_preparation_metadata(self.preparation_raw)
        info = prep['years'][str(self.year)]
        if any(value.flags.writeable or c.sha(value.tobytes()) != info['array_raw_SHA256'][key]
               for key, value in self.arrays.items()):
            raise ValueError('EXACT_IMMUTABLE_SAVED_CS_TARGET_COVARIANCE_BITS_REQUIRED')
        for name, raw in self.captured_artifacts.items():
            pin = prep['artifacts'][name]
            if c.sha(raw) != pin['SHA256'] or len(raw) != pin['bytes']:
                raise ValueError('EXACT_CURRENT_CAPTURED_PREPARATION_ARTIFACTS_REQUIRED')
        for cell_id in entry.tranche_cells(prep['tranche']):
            cell = config.cell_named(cell_id)
            if cell['year'] == self.year:
                binding = source.input_binding(cell, self.source, self.arrays)
                if c.jsha(binding) != prep['cells'][cell_id]['input_binding_SHA256']:
                    raise ValueError('EXACT_CURRENT_LOADED_SOURCE_TARGET_CELL_BINDING_REQUIRED')
        return True


def load_year(preparation_root, *, expected_preparation_sha256, year,
              source_go_raw, expected_source_go_sha256, source_review_raw, expected_source_review_sha256,
              financial_go_raw, expected_financial_go_sha256, financial_review_raw, expected_financial_review_sha256,
              prepared_review_raw, expected_prepared_review_sha256, native_review_raw, expected_native_review_sha256, verified_binding=None):
    """No financial scope or provider is constructed by this source-only call."""
    from cs_source_guard import current_guard
    guard = current_guard()
    if guard is None or not guard.active:
        raise ValueError('WHOLE_INVOCATION_NEW_CS_RECAPTURE_SOURCE_GUARD_REQUIRED')
    entry.validate_source_authority_metadata(source_go_raw, expected_source_go_sha256,
                                            source_review_raw, expected_source_review_sha256)
    root = Path(preparation_root).absolute()
    if root.is_symlink() or any(path.is_symlink() for path in root.parents):
        raise ValueError('ORDINARY_EXACT_CS_PREPARATION_DIRECTORY_REQUIRED')
    raw = c.exact(root / 'PREPARATION.json', expected_preparation_sha256)
    prep = entry.validate_preparation_metadata(raw)
    financial_sha = verified.consume(verified_binding, preparation_raw=raw, year=year, supplied={
        'go': financial_go_raw, 'review': financial_review_raw, 'prepared-review': prepared_review_raw,
        'native-review': native_review_raw, 'source-go': source_go_raw, 'source-review': source_review_raw})
    if (financial_sha != expected_financial_go_sha256
            or verified_binding.hashes['review'] != expected_financial_review_sha256
            or verified_binding.hashes['prepared-review'] != expected_prepared_review_sha256
            or verified_binding.hashes['native-review'] != expected_native_review_sha256
            or verified_binding.hashes['source-go'] != expected_source_go_sha256
            or verified_binding.hashes['source-review'] != expected_source_review_sha256):
        raise ValueError('EXACT_EXTERNAL_PREVERIFIED_WIRE_DIGESTS_REQUIRED')
    if type(year) is not int or year not in entry.tranche_years(prep['tranche']):
        raise ValueError('EXACT_PREPARED_FIRST6_YEAR_REQUIRED')
    if (prep['source_stage_GO_SHA256'] != expected_source_go_sha256
            or prep['source_review_SHA256'] != expected_source_review_sha256):
        raise ValueError('EXACT_EXTERNAL_NEW_CS_SOURCE_LINEAGE_REQUIRED')
    selected = {name: pin for name, pin in prep['artifacts'].items()
                if name.startswith(str(year) + '/') or name in ('SOURCE_STAGE_AUTHORIZATION.json', 'SOURCE_INDEPENDENT_REVIEW.json')}
    artifacts = {name: c.exact(root / c.relative(name), pin['SHA256'], pin['bytes']) for name, pin in selected.items()}
    if (artifacts['SOURCE_STAGE_AUTHORIZATION.json'] != source_go_raw
            or artifacts['SOURCE_INDEPENDENT_REVIEW.json'] != source_review_raw):
        raise ValueError('EXACT_NEW_SOURCE_GO_REVIEW_BODY_BINDING_REQUIRED')
    with entry.admit_source_stage(source_go_raw, expected_source_go_sha256,
                                  source_review_raw, expected_source_review_sha256) as scope:
        captured = source.capture_year(year, scope)  # Once for this worker/year.
    days = config.period_named(year)['days']
    keys = set(prep['years'][str(year)]['array_raw_SHA256'])
    specs = {key: ((days,) if key == 'decision_us' else (days, 5, 5) if key == 'annual_covariance' else (days, 5),
                   'int64' if key == 'decision_us' else 'float64') for key in keys}
    arrays = codec.npz(artifacts[str(year) + '/TARGETS.npz'], specs)
    if any(not np.isfinite(value).all() for value in arrays.values()):
        raise ValueError('FINITE_SAVED_TARGETS_REQUIRED')
    if (arrays['decision_us'].tobytes() != captured['decisions'].tobytes()
            or artifacts[str(year) + '/MINUTE_MARK_PROVENANCE.json'] != captured['sidecar_raw']
            or c.object_json(artifacts[str(year) + '/RAW_EVENTS.json']) != c.plain(captured['events'])):
        raise ValueError('EXACT_CURRENT_SOURCE_CALENDAR_FUNDING_QUALITY_REQUIRED')
    n = days + 199
    saved = codec.npz(artifacts[str(year) + '/SOURCE_INPUTS.npz'],
        {'close_available_us': ((n,), 'int64'), 'close': ((n, 5), 'float64')})
    if (saved['close_available_us'].tobytes() != captured['clocks'].tobytes()
            or saved['close'].tobytes() != captured['close'].tobytes()):
        raise ValueError('EXACT_CURRENT_SOURCE_DAILY_CLOSURE_BITS_REQUIRED')
    token = object()
    loaded = LoadedInputs(year, raw, c.immutable(captured), MappingProxyType(arrays),
                          MappingProxyType(artifacts), financial_sha, verified_binding.cell_id, token, _SEAL)
    _LIVE[token] = loaded
    try:
        loaded.validate()
        return loaded
    except BaseException:
        _LIVE.pop(token, None)
        raise


def revoke(loaded):
    if type(loaded) is not LoadedInputs or _LIVE.get(loaded._token) is not loaded:
        raise ValueError('LIVE_LOADED_CS_INPUTS_REQUIRED')
    _LIVE.pop(loaded._token)
