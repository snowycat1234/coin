"""Thin adapter of accepted official download/checksum/publication orchestration."""

from __future__ import annotations

import argparse
import json
from datetime import date
from functools import partial
from pathlib import Path

from quant.paths import ROOT
from quant.research_fast.trade_flow_v2 import (
    convert_zip,
    private_module,
    require,
    source_hashes,
)

STORE = ROOT / "data/research_fast/trade_flow_5s_v2"


def fetch_day(
    market,
    symbol,
    day,
    *,
    store=STORE,
    client=None,
    previous_day_last_raw_id=None,
    previous_day_last_agg_id=None,
    max_zip_bytes=512_000_000,
):
    source_hashes()
    # Reuse every httpx URL/HEAD/CHECKSUM/size/fsync/manifest/raw-cleanup step.
    # A separate module namespace keeps frozen V1 application globals untouched.
    wrapper = private_module("isolated_official_hf_orchestrator", ROOT / "scripts/hf_fetch.py")
    wrapper.convert_zip = partial(convert_zip, previous_day_last_agg_id=previous_day_last_agg_id)
    return wrapper.fetch_day(
        market,
        symbol,
        day,
        store=store,
        client=client,
        previous_day_last_raw_id=previous_day_last_raw_id,
        max_zip_bytes=max_zip_bytes,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=("spot", "perp"), required=True)
    parser.add_argument("--symbol", choices=("BTCUSDT", "ETHUSDT"), required=True)
    parser.add_argument("--day", type=date.fromisoformat, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "reports") and not output.exists(), "New D report")
    result = fetch_day(args.market, args.symbol, args.day)
    with output.open("x") as out:
        out.write(json.dumps(result, indent=2, allow_nan=False) + "\n")
    print(json.dumps({key: result[key] for key in ("status", "raw_deleted", "feature_path")}))


if __name__ == "__main__":
    main()
