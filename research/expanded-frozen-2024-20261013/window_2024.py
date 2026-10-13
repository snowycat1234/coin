"""Source-only adapter for the frozen NativeDailySimulator minute-block contract."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import polars as pl

S = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
DAY = 86400000000


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def window(path):
    root = Path(path)
    index = json.loads((root / "SOURCE_INDEX.json").read_text())
    assert index["calendar"] == [1704067200000000, 1735689600000000]
    assert index["days"] == 366 and index["symbol_order"] == list(S)
    assert index["minutes_per_asset"] == 527040 and index["funding_events"] == 5490
    for name in ("DAILY.json", "EVENTS.json"):
        f = root / name
        assert sha(f) == index["files"][name]["SHA256"] and f.stat().st_size == index["files"][name]["bytes"]
    events = json.loads((root / "EVENTS.json").read_text())
    daily = pl.DataFrame(json.loads((root / "DAILY.json").read_text()))
    assert len(events) == 5490 and daily.height == 1830

    def blocks():
        for record in index["months"]:
            f = root / "months" / (record["month"] + ".npz")
            assert sha(f) == record["source_NPZ_SHA256"] and f.stat().st_size == record["source_NPZ_bytes"]
            with np.load(f, allow_pickle=False) as a:
                times = a["times"]
                market = {s: {field: a[s + "_" + field] for field in ("open", "close", "quote_volume", "mark")}
                          for s in S}
            for i in range(0, len(times), 1440):
                yield {"times": times[i:i+1440],
                       "market": {s: {field: values[i:i+1440] for field, values in fields.items()}
                                  for s, fields in market.items()}}

    return {"start": index["calendar"][0], "end": index["calendar"][1],
            "symbols": S, "daily": daily, "events": events, "minute_blocks": blocks}
