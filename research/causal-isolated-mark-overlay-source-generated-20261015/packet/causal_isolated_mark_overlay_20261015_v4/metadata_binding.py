"""Pure metadata-only exact binding. No actual observations or overlay are loaded."""
from dataclasses import dataclass
from hashlib import sha256
import json
from overlay import MINUTE, OverlayRejected

EVIDENCE_IDENTITIES = (('ORIGINAL_MARK_Q3_RECOVERY.json', 129617, '3483c98ff56eb3759b6d86ae1461f4d7f84876735c93a199228705f8a69df797'), ('EXACT_JULY_MARK_GAP_ALLOWLIST.json', 15051, '55e87de1c4b238ab907d57c950de2eedc1a2ec245e8b6e0fe57cd2efe07c0f71'), ('FULL2022_GAP_TAXONOMY.json', 25346, 'bfc9f4bb0b91a2bfc2da25561fbe093c66fab996806087c0e25a394570c7157c'))
ACTUAL27_ORIGINAL_OPEN_POINTS = (('DOGEUSDT', 1657631820000), ('DOGEUSDT', 1657631880000), ('DOGEUSDT', 1657631940000), ('DOGEUSDT', 1657632000000), ('DOGEUSDT', 1657632060000), ('ETHUSDT', 1657630620000), ('ETHUSDT', 1657631220000), ('ETHUSDT', 1657631700000), ('ETHUSDT', 1657631760000), ('ETHUSDT', 1657631820000), ('ETHUSDT', 1657631880000), ('ETHUSDT', 1657631940000), ('ETHUSDT', 1657632000000), ('ETHUSDT', 1657632060000), ('ETHUSDT', 1657633920000), ('ETHUSDT', 1657695540000), ('SOLUSDT', 1657631760000), ('SOLUSDT', 1657631820000), ('SOLUSDT', 1657631880000), ('SOLUSDT', 1657631940000), ('SOLUSDT', 1657632000000), ('SOLUSDT', 1657632060000), ('XRPUSDT', 1657631820000), ('XRPUSDT', 1657631880000), ('XRPUSDT', 1657631940000), ('XRPUSDT', 1657632000000), ('XRPUSDT', 1657632060000))


@dataclass(frozen=True)
class ActualMetadataBindingReport:
    status: str = "EXACT27_METADATA_LINKAGE_ONLY_NOT_SOURCE_OR_SENSITIVITY_ADMISSION"
    asset_minutes: int = 27
    unique_open_clocks: int = 11
    asset_specific_runs: int = 8
    isolated_single_minute_runs: int = 4
    longest_run_minutes: int = 7
    prior_official_daily_attempts: int = 5
    prior_daily_added_rows: int = 0
    original_timestamp_semantics: str = "MINUTE_BAR_OPEN"
    nominal_completion_offset_ms: int = MINUTE
    nominal_completion_certifies_historical_arrival: bool = False
    actual_price_values_loaded: int = 0
    actual_overlay_records_created: int = 0
    raw_revalidation_pending: bool = True
    actual_application_enabled: bool = False
    quantity_cashflow_sensitivity: str = "PENDING_ACTUAL_SAVED_EVIDENCE"
    certifies_liquidation: bool = False
    certifies_no_liquidation: bool = False


def validate_actual27_metadata_bytes(original_receipt_bytes, exact_allowlist_bytes, taxonomy_bytes):
    """Verify only exact frozen metadata bytes; return no historical estimates.

    There is deliberately no flag to run real observations through the synthetic
    overlay. Every price application remains a separate future source-gate step.
    """
    parsed = []
    for identity, blob in zip(EVIDENCE_IDENTITIES,
                              (original_receipt_bytes, exact_allowlist_bytes, taxonomy_bytes)):
        _, size, digest = identity
        if type(blob) is not bytes or len(blob) != size or sha256(blob).hexdigest() != digest:
            raise OverlayRejected("Frozen original-attempt metadata identity mismatch")
        parsed.append(json.loads(blob))
    original, allowlist, taxonomy = parsed
    actual = tuple(sorted((p['symbol'], p['missing_original_open_ms']) for p in allowlist['points']))
    gaps = tuple(sorted((g['symbol'], t) for g in taxonomy['genuine_July_gaps'] for t in g['missing_open_ms']))
    source = tuple(sorted((r['source']['symbol'], t) for r in original['sources']
                          for t in r.get('remaining_missing_open_ms', [])))
    if not (actual == gaps == source == ACTUAL27_ORIGINAL_OPEN_POINTS):
        raise OverlayRejected("Original source OPEN identities differ from exact metadata binding")
    if len(set(actual)) != 27 or len({t for _, t in actual}) != 11:
        raise OverlayRejected("Exact 27 asset-minutes/11 OPEN clocks required")
    daily_attempts = [repair for r in original['sources'] if r.get('remaining_missing_open_ms')
                      for repair in r['repairs']]
    if len(daily_attempts) != 5 or any(r['added_actual_rows'] != 0 for r in daily_attempts):
        raise OverlayRejected("Original genuine official daily attempts must remain zero-added evidence")
    if not allowlist['current_raw_revalidation_pending'] or any(p['imputation_applied'] for p in allowlist['points']):
        raise OverlayRejected("Metadata cannot promote pending originals or apply estimates")
    if any(p['nominal_completed_available_ms'] != p['missing_original_open_ms'] + MINUTE
           for p in allowlist['points']):
        raise OverlayRejected("Nominal completion mapping differs from original OPEN identities")
    return ActualMetadataBindingReport()
