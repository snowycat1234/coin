"""Count observed aggregates and audit original IDs; reuse the frozen bar engine.

The private engine instance receives ordinal count IDs only. Original archive IDs
are validated here and restored in the manifest. Prices, quantities, timestamps,
maker flags, ZIP bytes and the frozen engine's aggregation math are unchanged.
"""

from __future__ import annotations

import hashlib
import importlib.util

import pyarrow as pa

from quant.paths import ROOT
from quant.research_fast import trade_flow as original

VERSION = "trade_flow_5s_v2"
SCHEMA = pa.schema([field for field in original.SCHEMA if field.name != "raw_trade_count"])
CONTRACT = {
    **original.CONTRACT,
    "version": VERSION,
    "trade_count": "observed aggregate CSV rows; NOT inferred raw execution count",
    "buy_count": "observed buyer-aggressor aggregate rows",
    "sell_count": "observed seller-aggressor aggregate rows",
    "agg_count": "exact compatibility alias of trade_count",
    "raw_trade_count": "absent; first/last ID ranges do not prove exact perp executions",
    "quality": "0: official archive observation scope passed checksum/original ordering/ID "
    "policy; not all raw executions, realtime qualification or executable-price evidence",
    "id_policy_spot": "strict original raw-range adjacency; aggregate IDs strictly increasing",
    "id_policy_perp": "strict aggregate adjacency; original raw ranges increasing without "
    "overlap; raw range gaps counted, cause unconfirmed and scope not all raw executions",
    "scope_reference": "https://developers.binance.com/en/docs/catalog/"
    "core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data",
    "scope": "official observed aggregate market trades; perp excludes insurance fund/ADL",
}
FROZEN_CORE = {
    "src/quant/research_fast/trade_flow.py": (
        "be07e53ad9c2f1590c1ca8e7c6332f3953d53a79cd869bdc36052c0a24003439"
    ),
    "scripts/hf_fetch.py": "b515610fefcbf8ad18209c12da27b8c98fb38162a95137bc816a7a2bd80d23c3",
}
checksum, require, validate_request = original.checksum, original.require, original.validate_request


def source_hashes():
    for name, expected in FROZEN_CORE.items():
        require(checksum(ROOT / name) == expected, "Frozen FR62 V1 core changed")
    return {
        **FROZEN_CORE,
        **{
            name: checksum(ROOT / name)
            for name in ("src/quant/research_fast/trade_flow_v2.py", "scripts/hf_fetch_v2.py")
        },
    }


def private_module(name, path):
    """Isolated namespace: no mutation of an imported production module."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def convert_zip(
    zip_path,
    output_path,
    *,
    market,
    symbol,
    day,
    previous_day_last_raw_id=None,
    previous_day_last_agg_id=None,
    max_csv_bytes=4_000_000_000,
):
    validate_request(market, symbol, day)
    bindings = source_hashes()
    require(
        (previous_day_last_raw_id is None) == (previous_day_last_agg_id is None),
        "Both preceding original ID high waters required",
    )
    require(
        previous_day_last_raw_id is None
        or all(
            type(value) is int and value >= 0
            for value in (previous_day_last_raw_id, previous_day_last_agg_id)
        ),
        "Invalid original preceding ID boundary",
    )
    engine = private_module(
        "isolated_fr62_bar_engine", ROOT / "src/quant/research_fast/trade_flow.py"
    )
    parse_original = engine.parse_trade
    first, previous, aggregate_rows = None, None, 0
    gaps, gap_ids, examples = 0, 0, []
    boundary_gap = None

    def parse_observed(row, selected_market, opened, closed):
        nonlocal first, previous, aggregate_rows, gaps, gap_ids, boundary_gap
        actual = parse_original(row, selected_market, opened, closed)
        a, f, last, timestamp, price, quantity, maker = actual
        if previous is not None:
            prior_a, prior_l = previous[0], previous[2]
            require(a > prior_a and timestamp >= previous[3], "Duplicate/nonordered aggregate rows")
        else:
            prior_a, prior_l = previous_day_last_agg_id, previous_day_last_raw_id
        if prior_a is not None:
            raw_gap = f - prior_l - 1
            require(raw_gap >= 0, "ORIGINAL_RAW_RANGE_OVERLAP")
            if market == "spot":
                require(raw_gap == 0, "SPOT_ORIGINAL_RAW_ID_GAP")
            else:
                require(a == prior_a + 1, "PERP_UNRESOLVED_AGGREGATE_ID_GAP")
            if previous is None:
                boundary_gap = raw_gap
            elif raw_gap:
                gaps += 1
                gap_ids += raw_gap
                if len(examples) < 8:
                    examples.append(
                        {
                            "previous_a": prior_a,
                            "previous_l": prior_l,
                            "a": a,
                            "f": f,
                            "l": last,
                            "unrepresented_ids": raw_gap,
                        }
                    )
        first = actual if first is None else first
        previous = actual
        aggregate_rows += 1
        # The old engine sums l-f+1. One observed aggregate is one count unit.
        # These ordinal IDs never leave this isolated count adapter.
        return a, aggregate_rows, aggregate_rows, timestamp, price, quantity, maker

    engine.VERSION, engine.SCHEMA, engine.CONTRACT = VERSION, SCHEMA, CONTRACT
    engine.parse_trade = parse_observed
    converted = engine.convert_zip(
        zip_path, output_path, market=market, symbol=symbol, day=day, max_csv_bytes=max_csv_bytes
    )
    converted.pop("raw_trade_count")
    converted.update(
        first_a=first[0],
        first_f=first[1],
        first_l=first[2],
        last_a=previous[0],
        last_l=previous[2],
        observed_aggregate_count=aggregate_rows,
        cross_day_scope_boundary_verified=previous_day_last_agg_id is not None,
        cross_day_raw_boundary_verified=boundary_gap == 0 if boundary_gap is not None else False,
        cross_day_unrepresented_raw_ids=boundary_gap,
        original_raw_range_gap_events=gaps,
        original_unrepresented_raw_ids=gap_ids,
        original_raw_range_gap_examples=examples,
        raw_gap_cause="UNCONFIRMED",
        adapter_source_hashes=bindings,
        schema_sha256=hashlib.sha256(str(SCHEMA).encode()).hexdigest(),
    )
    return converted
