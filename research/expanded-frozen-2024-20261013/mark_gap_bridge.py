"""Reproducible, mark-only sensitivity for the ten absent August 2024 minutes.

The five official monthly ZIP members are read but never edited. Output contains
only the ten derived OHLC rows and provenance. No trade, volume, funding, or
signal input is synthesized.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, ROUND_HALF_EVEN
import hashlib
import io
import json
from pathlib import Path
import zipfile

CORE5 = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
GAPS = (1723456920000, 1723456980000)
MINUTE_MS = 60000
MONTH_START = 1722470400000
MONTH_END = 1725148800000
WRAPPER_SHA256 = "d86a50dee14ea13df4a83fc8d5d90ec1ab0d42e352f430173d759b094c96013e"
MONTH_SHA256 = {
    "BTCUSDT": "e5be12f99523a72726e7235ad024465cc283b1ebbe1904e16674e130f373c362",
    "ETHUSDT": "ae8244cc4ad2033b815ef3f488aa060eab3ebec917e74f9500a01715f0e9a647",
    "SOLUSDT": "8d50fbc2a0a996563e27c97bc2ae4249647604645e51e94fa9e0aa8b125aa64d",
    "XRPUSDT": "f35ec1fda8eb6b363e21d55499f7be351c356cde75fd3455c42ffe8ba5278579",
    "DOGEUSDT": "5f99f0ca3a504e1f74a74a37be03e1579bfea04b643b83f03b5caa0e94469c28",
}
DAY_SHA256 = {
    "BTCUSDT": "139f800b758d844744b51a2d2fa1e0391447091faba2cccedb17028acb34d8cc",
    "ETHUSDT": "11a3640b1e90491a5491c8abe6182e4b4cb6f6ce5dde3c7ba34a0e5ccbda6552",
    "SOLUSDT": "6dd1cb8302a8b4f001f20faa13db417010ec41e073dd720c4ed19529e70a09fe",
    "XRPUSDT": "0e8749d7570ce6675a8b85fb83f5dac8c274d2236dc1d57b9654e7e94ab60959",
    "DOGEUSDT": "ca17a4f41390d14a3798a0ded7b3f880dce0f174b87bb3d60883097a115734f7",
}
Q8 = Decimal("0.00000001")


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def load_member(outer: zipfile.ZipFile, symbol: str, period: str, expected_sha: str):
    name = f"raw/markPriceKlines/{symbol}/{symbol}-1m-{period}.zip"
    blob = outer.read(name)
    if digest(blob) != expected_sha:
        raise ValueError(f"SHA mismatch: {name}")
    with zipfile.ZipFile(io.BytesIO(blob)) as inner:
        if inner.testzip() is not None:
            raise ValueError(f"bad inner CRC: {name}")
        members = inner.namelist()
        if members != [f"{symbol}-1m-{period}.csv"]:
            raise ValueError(f"unexpected CSV member: {name}")
        raw = inner.read(members[0]).decode("utf-8")
    rows = list(csv.DictReader(io.StringIO(raw)))
    if not rows or set(rows[0]) != {"open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"}:
        raise ValueError(f"unexpected CSV schema: {name}")
    keyed = {int(r["open_time"]): r for r in rows}
    if len(keyed) != len(rows):
        raise ValueError(f"duplicate minute: {name}")
    return keyed


def derive_pair(prior_close: Decimal, next_open: Decimal):
    """Time-linear bridge across exactly two missing, consecutive 1m bars."""
    if not prior_close.is_finite() or not next_open.is_finite() or min(prior_close, next_open) <= 0:
        raise ValueError("nonpositive or nonfinite boundary")
    mid = ((prior_close + next_open) / 2).quantize(Q8, rounding=ROUND_HALF_EVEN)
    endpoints = ((prior_close, mid), (mid, next_open))
    return [{"open": f"{a:.8f}", "high": f"{max(a,b):.8f}",
             "low": f"{min(a,b):.8f}", "close": f"{b:.8f}"}
            for a, b in endpoints]


def build(wrapper: Path, output: Path):
    if digest(wrapper.read_bytes()) != WRAPPER_SHA256:
        raise ValueError("public wrapper SHA mismatch")
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    derived = []
    provenance = []
    with zipfile.ZipFile(wrapper) as outer:
        if outer.testzip() is not None:
            raise ValueError("bad wrapper CRC")
        for symbol in CORE5:
            monthly = load_member(outer, symbol, "2024-08", MONTH_SHA256[symbol])
            daily = load_member(outer, symbol, "2024-08-12", DAY_SHA256[symbol])
            expected = set(range(MONTH_START, MONTH_END, MINUTE_MS)) - set(GAPS)
            if set(monthly) != expected or len(monthly) != 44638:
                raise ValueError(f"unallowlisted August minute issue: {symbol}")
            day_start = 1723420800000
            day_expected = set(range(day_start, day_start + 86400000, MINUTE_MS)) - set(GAPS)
            if set(daily) != day_expected or len(daily) != 1438:
                raise ValueError(f"unallowlisted August 12 issue: {symbol}")
            if any(daily[t] != monthly[t] for t in daily):
                raise ValueError(f"monthly/daily overlap conflict: {symbol}")
            left_t = GAPS[0] - MINUTE_MS
            right_t = GAPS[-1] + MINUTE_MS
            left = monthly[left_t]
            right = monthly[right_t]
            left_close, right_open = Decimal(left["close"]), Decimal(right["open"])
            made = derive_pair(left_close, right_open)
            for t, bars in zip(GAPS, made):
                derived.append({"symbol": symbol, "open_time_ms": t, **bars,
                                "source_missing": True, "method": "TIME_LINEAR_PRIOR_CLOSE_TO_NEXT_OPEN"})
            provenance.append({"symbol": symbol, "monthly_original_SHA256": MONTH_SHA256[symbol],
                               "daily_original_SHA256": DAY_SHA256[symbol],
                               "prior_actual_open_time_ms": left_t, "prior_actual_close": left["close"],
                               "next_actual_open_time_ms": right_t, "next_actual_open": right["open"],
                               "missing_open_time_ms": list(GAPS), "derived": made})
    assert len(derived) == 10
    csv_path = output / "DERIVED_MARK_OHLC.csv"
    with csv_path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["symbol", "open_time_ms", "open", "high", "low", "close", "source_missing", "method"])
        writer.writeheader()
        writer.writerows(derived)
    manifest = {"schema": "MARK_ONLY_2024_AUG12_GAP_SENSITIVITY_V1",
                "role": "derived evaluation marks only; original ZIPs and source missingness unchanged",
                "source_repository": "snowycat1234/coin",
                "source_commit": "001024ceb6f7a33be6b1f95b17f7c7d9777a3dde",
                "source_index_path": "research/core5-july2024-native-data/JULY2024/INDEX.json",
                "source_wrapper_SHA256": WRAPPER_SHA256,
                "method": "linearly bridge prior actual 10:01 close at 10:02:00 to next actual 10:04 open at 10:04:00; two piecewise-linear one-minute OHLC bars; midpoint rounded to eight decimal places half-even",
                "not_derived": ["trade prices", "trade volume", "mark volume", "funding", "signals", "original source rows"],
                "original_gap_open_time_ms": list(GAPS), "derived_rows": 10,
                "derived_csv_SHA256": digest(csv_path.read_bytes()), "per_symbol": provenance}
    (output / "PROVENANCE.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--wrapper", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = build(args.wrapper, args.output)
    print(json.dumps({"rows": result["derived_rows"], "CSV_SHA256": result["derived_csv_SHA256"]}))
