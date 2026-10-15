"""One-use immutable metadata admission, verified before the unchanged guard.

This is a finite reviewed worker-graph capability, not a Python sandbox or a
historical/source scope. No generated flag, callback, or public seal is accepted.
"""
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import MappingProxyType

import cs_common as c
import cs_config as config
import cs_entry as entry
import cs_finance_gate as gate

_SEAL = object()
_LIVE = {}


@dataclass(frozen=True, slots=True)
class VerifiedWires:
    cell_id: str
    preparation_raw: bytes = field(repr=False)
    raw: object = field(repr=False)
    hashes: object = field(repr=False)
    code_sha: str
    claim_raw: bytes = field(repr=False)
    claim_sha: str
    _token: object = field(repr=False)
    _seal: object = field(repr=False)

    def __post_init__(self):
        if self._seal is not _SEAL:
            raise ValueError('INTERNALLY_VERIFIED_IMMUTABLE_WIRES_REQUIRED')

    def consume(self, *, preparation_raw, year, supplied):
        record = _LIVE.get(self._token)
        if record is None or record[0] is not self or record[1] != 'OPEN' or self._seal is not _SEAL:
            if record is not None and record[0] is self:
                _LIVE.pop(self._token, None)
            raise ValueError('LIVE_UNUSED_VERIFIED_WIRES_REQUIRED')
        try:
            if (type(year) is not int or config.cell_named(self.cell_id)['year'] != year
                    or type(preparation_raw) is not bytes or preparation_raw != self.preparation_raw
                    or gate.code_identity() != self.code_sha or type(supplied) is not dict
                    or set(supplied) != set(self.raw)
                    or any(type(supplied[k]) is not bytes or supplied[k] != self.raw[k]
                           or c.sha(supplied[k]) != self.hashes[k] for k in supplied)):
                _LIVE.pop(self._token, None)
                raise ValueError('EXACT_PREVERIFIED_YEAR_CODE_PREPARATION_AND_WIRE_BYTES_REQUIRED')
            if c.sha(self.claim_raw) != self.claim_sha:
                raise ValueError('EXACT_VERIFIED_WORKER_CLAIM_BYTES_REQUIRED')
        except BaseException:
            _LIVE.pop(self._token, None)
            raise
        _LIVE[self._token] = (self, 'CONSUMED')
        return self.hashes['go']


def exact_preparation_shape(preparation_raw):
    prep = entry.validate_preparation_metadata(preparation_raw)
    top = {'accounts_advanced','accounts_created','artifacts','candidate','canonical_claims_created','cells',
        'code_manifest_SHA256','financial_runs','historical_admission','ordered_cells','process_launches',
        'provider_iterations','publication_actions','real_financial_GO_written','schema','scope_manifest_SHA256',
        'source_contract_map_SHA256','source_review_SHA256','source_stage_GO_SHA256','tranche','years'}
    yearly = {'all_CS_position_and_event_impacts_pending','array_raw_SHA256','calendar','days','funding_events_SHA256',
        'provider_months_source','quality_cells_SHA256','source_contract_SHA256','source_identity',
        'source_quality_sidecar_SHA256','source_rows_SHA256'}
    artifacts = {'SOURCE_INDEPENDENT_REVIEW.json','SOURCE_STAGE_AUTHORIZATION.json','2022/NORMALIZATION_EQUIVALENCE.json'}
    artifacts.update(str(y)+'/'+n for y in (2022,2023) for n in ('MINUTE_MARK_PROVENANCE.json','RAW_EVENTS.json',
        'SOURCE_INPUTS.npz','TARGETS.npz','TARGET_PROOFS.json'))
    if (set(prep)!=top or set(prep['years'])!={'2022','2023'}
            or set(prep['cells'])!=set(entry.tranche_cells(entry.FIRST6)) or set(prep['artifacts'])!=artifacts
            or any(set(v)!=yearly for v in prep['years'].values())
            or any(set(v)!={'descriptor','input_binding','input_binding_SHA256'} for v in prep['cells'].values())
            or any(set(v)!={'SHA256','bytes'} for v in prep['artifacts'].values())):
        raise ValueError('EXACT_FROZEN_FIRST6_PREPARATION_WRAPPER_KEYSETS_REQUIRED')
    return prep


@contextmanager
def verify(*, preparation_raw, cell_id, raw, hashes, claim_raw):
    from cs_source_guard import current_guard
    if current_guard() is not None:
        raise ValueError('FINANCIAL_WIRE_VALIDATION_MUST_PRECEDE_SOURCE_GUARD')
    if (type(preparation_raw) is not bytes or type(raw) is not dict or type(hashes) is not dict
            or set(raw) != {'go', 'review', 'prepared-review', 'native-review', 'source-go', 'source-review'}
            or set(raw) != set(hashes) or any(type(v) is not bytes for v in raw.values())
            or any(c.sha(raw[k]) != c.digest(hashes[k]) for k in raw)):
        raise ValueError('EXACT_EXTERNALLY_HASHED_IMMUTABLE_WIRES_REQUIRED')
    prep = exact_preparation_shape(preparation_raw)
    if (tuple(prep['ordered_cells']) != entry.tranche_cells(entry.FIRST6)
            or set(prep['years']) != {'2022','2023'} or cell_id not in prep['ordered_cells']):
        raise ValueError('EXACT_PREPARED_CELL_REQUIRED')
    entry.validate_source_authority_metadata(raw['source-go'], hashes['source-go'], raw['source-review'], hashes['source-review'])
    gate.validate(preparation_raw, raw['go'], hashes['go'], raw['review'], hashes['review'],
                  raw['prepared-review'], hashes['prepared-review'], raw['native-review'], hashes['native-review'])
    if (prep['source_stage_GO_SHA256'] != hashes['source-go'] or prep['source_review_SHA256'] != hashes['source-review']):
        raise ValueError('EXACT_VERIFIED_SOURCE_LINEAGE_REQUIRED')
    code_sha = gate.code_identity()
    claim = c.exact_object(claim_raw)
    if (claim.get('cell_id') != cell_id or claim.get('root_GO_SHA256') != hashes['go']
            or claim.get('preparation_SHA256') != c.sha(preparation_raw) or claim.get('code_identity') != code_sha):
        raise ValueError('EXACT_VERIFIED_WORKER_CLAIM_CELL_GO_PREPARATION_CODE_REQUIRED')
    if any(v[0].cell_id == cell_id or v[0].claim_sha == c.sha(claim_raw) for v in _LIVE.values()):
        raise ValueError('CONFLICTING_LIVE_VERIFIED_CELL_OR_CLAIM_BINDING')
    token = object()
    value = VerifiedWires(cell_id, preparation_raw, MappingProxyType(dict(raw)), MappingProxyType(dict(hashes)),
                          code_sha, claim_raw, c.sha(claim_raw), token, _SEAL)
    _LIVE[token] = (value, 'OPEN')
    try:
        yield value
    finally:
        _LIVE.pop(token, None)


def consume(value, **kwargs):
    if type(value) is not VerifiedWires:
        raise ValueError('EXACT_SEALED_PREVERIFIED_FINANCIAL_WIRES_REQUIRED')
    return value.consume(**kwargs)
