"""Pure, generated-fixture-only causal MARK overlay. No actual application route."""
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from types import MappingProxyType
import json
import re

MINUTE = 60_000
METHOD = "ESTIMATED_CAUSAL_PREVIOUS_GENUINE_MARK"
QUALITY = "UNKNOWN_OR_DERIVED"
POLICY_ID = "CAUSAL_PREVIOUS_GENUINE_MARK_27_SOURCE_ONLY_V1"
POLICY_SHA256 = "d873e9802cc3205907ce2e2d53fde2b10785570a641e96265dcfb6c808f39e58"
# An exact synthetic allowlist, deliberately disjoint from every real symbol/year.
# It mirrors the shape (11/6/5/5; longest run 7), not real prices or observations.
FIXTURE_BASE_MS = 978_307_200_000  # 2001-01-01T00:00:00Z, minute OPEN
_FIXTURE_OFFSETS = (
    ("FIXTURE_ETH", (2, 12, 20, 21, 22, 23, 24, 25, 26, 57, 1084)),
    ("FIXTURE_SOL", (21, 22, 23, 24, 25, 26)),
    ("FIXTURE_XRP", (22, 23, 24, 25, 26)),
    ("FIXTURE_DOGE", (22, 23, 24, 25, 26)),
)
_ID = re.compile(r"[A-Za-z0-9_.:-]{1,160}\Z")
_SHA = re.compile(r"[0-9a-f]{64}\Z")


class OverlayRejected(ValueError):
    """An exact bounded policy or causal contract was not satisfied."""


def _require(condition, message):
    if not condition:
        raise OverlayRejected(message)


def _digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                             allow_nan=False).encode()).hexdigest()


def _clock(value):
    _require(type(value) is int and value >= 0, "Clock must be nonnegative integer milliseconds")


@dataclass(frozen=True)
class MissingCell:
    symbol: str
    minute_open_ms: int
    proof_id: str
    proof_sha256: str
    domain: str = "MARK"
    selected_field: str = "selected_mark_price"
    original_cell_missing: bool = True


FIXTURE_HOLES = tuple(
    MissingCell(symbol, FIXTURE_BASE_MS + offset * MINUTE,
                f"fixture-absence-{symbol}-{offset}",
                _digest(["GENERATED_ABSENCE_PROOF", symbol, offset]))
    for symbol, offsets in _FIXTURE_OFFSETS for offset in offsets
)
_FIXTURE_BY_ID = MappingProxyType({(x.symbol, x.minute_open_ms): x for x in FIXTURE_HOLES})
_FIXTURE_SYMBOLS = frozenset(x.symbol for x in FIXTURE_HOLES)
FIXTURE_ALLOWLIST_SHA256 = _digest([asdict(x) for x in FIXTURE_HOLES])


@dataclass(frozen=True)
class GenuineObservation:
    observation_id: str
    symbol: str
    minute_open_ms: int
    source_close_inclusive_ms: int
    completed_at_ms: int
    available_at_ms: int
    installed_at_ms: int
    price_text: str
    source_sha256: str
    source_record_id: str
    domain: str = "MARK"
    selected_field: str = "selected_mark_price"
    source_quality: str = "GENUINE_MARK_SOURCE"


@dataclass(frozen=True)
class OverlayRecord:
    symbol: str
    minute_open_ms: int
    source_close_inclusive_ms: int
    completed_at_ms: int
    evaluation_clock_ms: int
    price_text: str
    estimate_method: str
    quality: str
    original_cell_missing: bool
    is_genuine: bool
    missing_proof_id: str
    missing_proof_sha256: str
    anchor_observation_id: str
    anchor_source_record_id: str
    anchor_source_sha256: str
    anchor_minute_open_ms: int
    anchor_completed_at_ms: int
    anchor_available_at_ms: int
    anchor_installed_at_ms: int
    anchor_age_ms: int
    # This is the old source clock, not the missing minute completion.
    source_freshness_clock_ms: int


@dataclass(frozen=True)
class QualitySidecar:
    symbol: str
    minute_open_ms: int
    quality: str = QUALITY
    new_increase_source_eligible: bool = False
    topup_source_eligible: bool = False
    native_intent_lifecycle: str = "UNCHANGED_NOT_IMPLEMENTED_HERE"
    funding_mark_valuation_quality: str = QUALITY
    trigger_mark_valuation_quality: str = QUALITY
    execution_mark_valuation_quality: str = QUALITY
    certifies_liquidation: bool = False
    certifies_no_liquidation: bool = False
    actual_historical_arrival_status: str = "UNKNOWN_NOT_CERTIFIED_BY_THIS_POLICY"


@dataclass(frozen=True)
class OverlayBatch:
    policy_id: str
    policy_sha256: str
    scope: str
    fixture_allowlist_sha256: str
    records: tuple
    quality_sidecar: tuple
    record_sha256: tuple
    overlay_sha256: str


def _validate_observations(observations):
    by_cell, ids, source_ids = {}, set(), set()
    for o in observations:
        _require(type(o) is GenuineObservation, "Only explicit genuine observation records accepted")
        _require(type(o.symbol) is str and o.symbol in _FIXTURE_SYMBOLS,
                 "Actual/unknown symbol rejected: generated API only")
        _require(all(type(value) is str for value in (o.domain, o.selected_field, o.source_quality)),
                 "Explicit string source domain/field/quality required")
        _require(o.domain == "MARK" and o.selected_field == "selected_mark_price", "MARK selected price only")
        _require(o.source_quality == "GENUINE_MARK_SOURCE", "Derived observations cannot become genuine anchors")
        for identifier in (o.observation_id, o.source_record_id):
            _require(type(identifier) is str and _ID.fullmatch(identifier), "Invalid/nonportable source identifier")
        _require(type(o.source_sha256) is str and _SHA.fullmatch(o.source_sha256), "Invalid source hash")
        for clock in (o.minute_open_ms, o.source_close_inclusive_ms, o.completed_at_ms,
                      o.available_at_ms, o.installed_at_ms):
            _clock(clock)
        _require(o.minute_open_ms % MINUTE == 0, "Minute OPEN must be aligned")
        _require(o.source_close_inclusive_ms == o.minute_open_ms + MINUTE - 1,
                 "Raw inclusive CLOSE must not be confused with OPEN or completion")
        _require(o.completed_at_ms == o.minute_open_ms + MINUTE, "Explicit completed CLOSE mapping mismatch")
        _require(o.completed_at_ms <= o.available_at_ms <= o.installed_at_ms,
                 "A genuine row cannot be available before completion or installed before availability")
        _require(type(o.price_text) is str and 0 < len(o.price_text) <= 200,
                 "Exact raw decimal string required")
        try:
            price = Decimal(o.price_text)
        except (InvalidOperation, ValueError):
            raise OverlayRejected("Invalid genuine anchor price") from None
        _require(price.is_finite() and price > 0, "Missing/nonpositive/nonfinite genuine price")
        key = (o.symbol, o.minute_open_ms)
        _require(key not in _FIXTURE_BY_ID,
                 "Frozen original missing cell cannot be declared genuine or reset anchor provenance")
        _require(o.observation_id not in ids, "Duplicate/conflicting observation ID")
        _require(key not in by_cell, "Duplicate/conflicting source cell")
        source_key = (o.source_sha256, o.source_record_id)
        _require(source_key not in source_ids, "Duplicate/conflicting source record identity")
        ids.add(o.observation_id)
        source_ids.add(source_key)
        by_cell[key] = o
    return by_cell


def build_generated_overlay(observations, requested_holes, *, as_of_ms):
    """Return immutable estimates for an exact subset of synthetic approved holes.

    Each estimate is fixed at its own completion clock. as_of_ms only selects
    already completed target cells; it cannot move an anchor evaluation clock.
    No I/O, financial constructor, source adapter, or real-symbol execution exists.
    """
    _clock(as_of_ms)
    observations, holes = tuple(observations), tuple(requested_holes)
    _require(len(holes) <= 27, "At most 27 exact approved holes; no wide or monthly gaps")
    seen = set()
    for h in holes:
        _require(type(h) is MissingCell, "Explicit approved missing-cell record required")
        _clock(h.minute_open_ms)
        _require(all(type(value) is str for value in
                     (h.symbol, h.proof_id, h.proof_sha256, h.domain, h.selected_field)),
                 "Exact string missing-cell identity/proof/domain/field required")
        key = (h.symbol, h.minute_open_ms)
        _require(key not in seen, "Duplicate/conflicting requested missing-cell identity")
        seen.add(key)
        _require(type(h.original_cell_missing) is bool, "Missingness must be explicit boolean")
        _require(_FIXTURE_BY_ID.get(key) == h, "Unlisted, altered, TRADE, volume, or nonmissing cell rejected")
        _require(h.minute_open_ms + MINUTE <= as_of_ms, "Target completion is after snapshot clock")
    by_cell = _validate_observations(observations)
    records = []
    for h in sorted(holes, key=lambda x: (x.minute_open_ms, x.symbol)):
        _require((h.symbol, h.minute_open_ms) not in by_cell,
                 "Present genuine target may not be overwritten, even if delivered later")
        clock = h.minute_open_ms + MINUTE
        candidates = [o for o in observations
                      if o.symbol == h.symbol and o.minute_open_ms < h.minute_open_ms
                      and o.completed_at_ms < clock
                      and o.available_at_ms <= clock and o.installed_at_ms <= clock]
        _require(candidates, "No prior genuine MARK anchor causally available and installed")
        anchor = max(candidates, key=lambda o: o.completed_at_ms)
        # A long absent run cannot hide behind this bounded API. If an intervening
        # minute is missing, it must itself be one of the exact approved holes.
        intervening = range(anchor.minute_open_ms + MINUTE, h.minute_open_ms + MINUTE, MINUTE)
        _require((h.minute_open_ms - anchor.minute_open_ms) // MINUTE <= 7,
                 "Anchor too old for approved isolated/clustered gap (maximum seven missing minutes)")
        _require(all((h.symbol, t) in _FIXTURE_BY_ID for t in intervening),
                 "Unlisted intervening missing minute or unavailable genuine row")
        records.append(OverlayRecord(
            h.symbol, h.minute_open_ms, h.minute_open_ms + MINUTE - 1, clock, clock,
            anchor.price_text, METHOD, QUALITY, True, False, h.proof_id, h.proof_sha256,
            anchor.observation_id, anchor.source_record_id, anchor.source_sha256,
            anchor.minute_open_ms, anchor.completed_at_ms, anchor.available_at_ms,
            anchor.installed_at_ms, clock - anchor.completed_at_ms, anchor.available_at_ms))
    records = tuple(records)
    sidecar = tuple(QualitySidecar(x.symbol, x.minute_open_ms) for x in records)
    hashes = tuple(_digest(asdict(x)) for x in records)
    commitment = _digest({"policy_id": POLICY_ID, "policy_sha256": POLICY_SHA256,
                          "fixture_allowlist_sha256": FIXTURE_ALLOWLIST_SHA256,
                          "record_sha256": hashes,
                          "quality_sidecar": [asdict(x) for x in sidecar]})
    return OverlayBatch(POLICY_ID, POLICY_SHA256, "GENERATED_FIXTURES_ONLY_NO_ACTUAL_ADMISSION",
                        FIXTURE_ALLOWLIST_SHA256, records, sidecar, hashes, commitment)


def _validate_generated_batch(batch):
    _require(type(batch) is OverlayBatch and
             batch.scope == "GENERATED_FIXTURES_ONLY_NO_ACTUAL_ADMISSION"
             and batch.policy_id == POLICY_ID and batch.policy_sha256 == POLICY_SHA256
             and batch.fixture_allowlist_sha256 == FIXTURE_ALLOWLIST_SHA256,
             "Exact generated-only policy and allowlist required")
    _require(type(batch.records) is tuple and len(batch.records) <= 27, "Bounded immutable generated records required")
    keys = []
    anchors_by_cell, anchors_by_observation_id, anchors_by_source_record = {}, {}, {}
    for r in batch.records:
        _require(type(r) is OverlayRecord, "Explicit overlay record required")
        h = _FIXTURE_BY_ID.get((r.symbol, r.minute_open_ms))
        _require(h is not None and r.missing_proof_id == h.proof_id
                 and r.missing_proof_sha256 == h.proof_sha256
                 and r.estimate_method == METHOD and r.quality == QUALITY
                 and r.is_genuine is False and r.original_cell_missing is True,
                 "Unlisted, altered or promoted overlay record")
        for clock in (r.minute_open_ms, r.source_close_inclusive_ms, r.completed_at_ms,
                      r.evaluation_clock_ms, r.anchor_minute_open_ms, r.anchor_completed_at_ms,
                      r.anchor_available_at_ms, r.anchor_installed_at_ms, r.anchor_age_ms,
                      r.source_freshness_clock_ms):
            _clock(clock)
        _require(r.minute_open_ms % MINUTE == 0
                 and r.source_close_inclusive_ms == r.minute_open_ms + MINUTE - 1
                 and r.completed_at_ms == r.minute_open_ms + MINUTE
                 and r.evaluation_clock_ms == r.completed_at_ms,
                 "Overlay target OPEN/CLOSE/completion/evaluation clocks mismatch")
        _require((r.symbol, r.anchor_minute_open_ms) not in _FIXTURE_BY_ID,
                 "Frozen missing source cell cannot be a genuine anchor")
        _require(r.anchor_minute_open_ms % MINUTE == 0
                 and r.anchor_minute_open_ms < r.minute_open_ms
                 and r.anchor_completed_at_ms == r.anchor_minute_open_ms + MINUTE
                 and r.anchor_completed_at_ms <= r.anchor_available_at_ms
                 <= r.anchor_installed_at_ms <= r.evaluation_clock_ms,
                 "Genuine anchor clock/availability/installation ordering mismatch")
        _require(r.anchor_age_ms == r.evaluation_clock_ms - r.anchor_completed_at_ms
                 and MINUTE <= r.anchor_age_ms <= 7 * MINUTE
                 and r.source_freshness_clock_ms == r.anchor_available_at_ms,
                 "Anchor age/freshness is not the original bounded genuine provenance")
        _require(all((r.symbol, t) in _FIXTURE_BY_ID
                     for t in range(r.anchor_minute_open_ms + MINUTE,
                                    r.minute_open_ms + MINUTE, MINUTE)),
                 "Overlay anchor spans an unlisted missing minute")
        for identifier in (r.anchor_observation_id, r.anchor_source_record_id):
            _require(type(identifier) is str and _ID.fullmatch(identifier),
                     "Invalid/nonportable genuine anchor identity")
        _require(type(r.anchor_source_sha256) is str and _SHA.fullmatch(r.anchor_source_sha256),
                 "Invalid genuine anchor source hash")
        _require(type(r.price_text) is str and 0 < len(r.price_text) <= 200,
                 "Overlay requires exact raw decimal text")
        try:
            price = Decimal(r.price_text)
        except (InvalidOperation, ValueError):
            raise OverlayRejected("Invalid overlay anchor price") from None
        _require(price.is_finite() and price > 0, "Nonpositive/nonfinite overlay anchor price")
        provenance = (r.symbol, r.anchor_minute_open_ms, r.anchor_observation_id,
                      r.anchor_source_record_id, r.anchor_source_sha256, r.price_text,
                      r.anchor_completed_at_ms, r.anchor_available_at_ms,
                      r.anchor_installed_at_ms, r.source_freshness_clock_ms)
        for mapping, key in ((anchors_by_cell, (r.symbol, r.anchor_minute_open_ms)),
                             (anchors_by_observation_id, r.anchor_observation_id),
                             (anchors_by_source_record, (r.anchor_source_sha256, r.anchor_source_record_id))):
            _require(key not in mapping or mapping[key] == provenance,
                     "Conflicting duplicate genuine-anchor identity/provenance across overlay records")
            mapping[key] = provenance
        keys.append((r.minute_open_ms, r.symbol))
    _require(keys == sorted(set(keys)), "Duplicate/conflicting/unordered overlay identity")
    sidecar = tuple(QualitySidecar(r.symbol, r.minute_open_ms) for r in batch.records)
    hashes = tuple(_digest(asdict(r)) for r in batch.records)
    commitment = _digest({"policy_id": POLICY_ID, "policy_sha256": POLICY_SHA256,
                          "fixture_allowlist_sha256": FIXTURE_ALLOWLIST_SHA256,
                          "record_sha256": hashes,
                          "quality_sidecar": [asdict(x) for x in sidecar]})
    _require(batch.quality_sidecar == sidecar and batch.record_sha256 == hashes
             and batch.overlay_sha256 == commitment, "Overlay/quality commitments mismatch")


@dataclass(frozen=True)
class SavedGeneratedEvent:
    event_id: str
    symbol: str
    event_clock_ms: int
    kind: str
    mark_reference_open_ms: int | None = None
    position_start_ms: int | None = None
    position_end_exclusive_ms: int | None = None


EVENT_KINDS = ("POSITION", "FILL", "ELIGIBLE_OPEN", "FUNDING", "GUARD50", "NATIVE_RISK", "TERMINAL")


def audit_saved_generated_events(batch, saved_events):
    """Classify supplied fake saved events only; no replay or financial arithmetic.

    Explicit saved mark references are authoritative for non-position overlap.
    An event timestamp alone never guesses strict-prior scheduler mapping.
    """
    _validate_generated_batch(batch)
    events = tuple(saved_events)
    seen = set()
    for e in events:
        _require(type(e) is SavedGeneratedEvent and type(e.symbol) is str and e.symbol in _FIXTURE_SYMBOLS,
                 "Only saved generated fixture events accepted")
        _require(type(e.event_id) is str and _ID.fullmatch(e.event_id) and e.event_id not in seen,
                 "Duplicate/conflicting/invalid saved event ID")
        seen.add(e.event_id)
        _clock(e.event_clock_ms)
        _require(type(e.kind) is str and e.kind in EVENT_KINDS, "Unknown event category")
        if e.mark_reference_open_ms is not None:
            _clock(e.mark_reference_open_ms)
            _require(e.mark_reference_open_ms % MINUTE == 0, "Saved mark OPEN must be aligned")
            _require(e.mark_reference_open_ms + MINUTE <= e.event_clock_ms,
                     "Saved event cannot reference an uncompleted mark")
        if e.kind == "POSITION":
            _clock(e.position_start_ms)
            _clock(e.position_end_exclusive_ms)
            _require(e.position_start_ms < e.position_end_exclusive_ms, "Invalid position interval")
        else:
            _require(e.position_start_ms is None and e.position_end_exclusive_ms is None,
                     "Only positions have exposure intervals")
    rows = []
    for r in batch.records:
        overlaps = {kind: [] for kind in EVENT_KINDS}
        unmapped = []
        for e in events:
            if e.symbol != r.symbol:
                continue
            if e.kind == "POSITION":
                if e.position_start_ms <= r.completed_at_ms < e.position_end_exclusive_ms:
                    overlaps[e.kind].append(e.event_id)
            elif e.mark_reference_open_ms == r.minute_open_ms:
                overlaps[e.kind].append(e.event_id)
            elif e.mark_reference_open_ms is None:
                unmapped.append(e.event_id)
        rows.append({"symbol": r.symbol, "minute_open_ms": r.minute_open_ms,
                     "saved_generated_overlap_ids": {k: sorted(v) for k, v in overlaps.items()},
                     "saved_generated_events_without_mark_mapping": sorted(unmapped),
                     "actual_positions_fills_funding_risk_terminal_overlap": "PENDING_ACTUAL_SAVED_EVIDENCE",
                     "quantity_sensitivity": "PENDING_ACTUAL_EVIDENCE",
                     "cashflow_sensitivity": "PENDING_ACTUAL_EVIDENCE",
                     "claim_of_negligible_impact": False})
    return {"scope": "SAVED_GENERATED_EVENTS_ONLY_NO_REPLAY", "rows": rows,
            "audit_sha256": _digest(rows), "actual_event_review": "PENDING"}


@dataclass(frozen=True)
class PastOnlySensitivity:
    symbol: str
    minute_open_ms: int
    status: str
    primary_carry_price_text: str
    lower_reference_price_text: str | None
    upper_reference_price_text: str | None
    genuine_observation_ids: tuple
    original_available_at_ms: tuple
    original_installed_at_ms: tuple
    definition: str = "MIN_MAX_OF_EXACT_LAST_TWO_PAST_GENUINE_SELECTED_MARKS"
    guaranteed_bound_on_missing_price: bool = False
    certifies_liquidation: bool = False
    certifies_no_liquidation: bool = False
    actual_sensitivity_admission: str = "BLOCKED_PENDING_SOURCE_AND_SAVED_EVENT_EVIDENCE"
    quantity_sensitivity: str = "PENDING_ACTUAL_EVIDENCE"
    cashflow_sensitivity: str = "PENDING_ACTUAL_EVIDENCE"


def build_generated_past_only_sensitivity(batch, observations):
    """Fixed two-genuine-observation reference range; never a future-price bound.

    No fitted lookback, threshold, market high/low, hindsight selection, or financial
    arithmetic. This reference range is exploratory uncertainty evidence only.
    Fewer than two eligible genuine observations leaves sensitivity pending.
    """
    _validate_generated_batch(batch)
    observations = tuple(observations)
    _validate_observations(observations)
    # Rebuild each primary estimate to prevent forged/mismatched provenance.
    expected_holes = tuple(_FIXTURE_BY_ID.get((r.symbol, r.minute_open_ms)) for r in batch.records)
    _require(all(expected_holes), "Unlisted overlay record")
    clock = max((r.completed_at_ms for r in batch.records), default=0)
    rebuilt = build_generated_overlay(observations, expected_holes, as_of_ms=clock)
    _require(rebuilt == batch, "Overlay and supplied genuine observations do not match")
    output = []
    for r in batch.records:
        eligible = sorted((o for o in observations if o.symbol == r.symbol
                           and o.minute_open_ms < r.minute_open_ms
                           and o.available_at_ms <= r.evaluation_clock_ms
                           and o.installed_at_ms <= r.evaluation_clock_ms),
                          key=lambda o: o.completed_at_ms)
        selected = tuple(eligible[-2:])
        if len(selected) < 2:
            output.append(PastOnlySensitivity(r.symbol, r.minute_open_ms,
                "PENDING_TWO_PAST_GENUINE_OBSERVATIONS", r.price_text, None, None,
                tuple(o.observation_id for o in selected),
                tuple(o.available_at_ms for o in selected), tuple(o.installed_at_ms for o in selected)))
            continue
        lower = min(selected, key=lambda o: Decimal(o.price_text))
        upper = max(selected, key=lambda o: Decimal(o.price_text))
        output.append(PastOnlySensitivity(r.symbol, r.minute_open_ms,
            "PAST_ONLY_REFERENCE_RANGE_NOT_A_GUARANTEED_PRICE_BOUND", r.price_text,
            lower.price_text, upper.price_text, tuple(o.observation_id for o in selected),
            tuple(o.available_at_ms for o in selected), tuple(o.installed_at_ms for o in selected)))
    return tuple(output)
