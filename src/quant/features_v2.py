"""Forty fixed causal hourly features, shared by batch and incremental callers."""

from __future__ import annotations

import copy
import hashlib
import json
import math
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

HOUR_US = 3_600_000_000
SYMBOLS = ("BTCUSDT", "ETHUSDT")
EPS = 1e-12
VERSION = "hourly_causal_features_v2.0"
FEATURE_NAMES_V2 = (
    "log_return_1", "log_return_4", "log_return_16", "volatility_24", "volatility_96",
    "volume_z96", "range_fraction", "body_fraction", "ema_gap", "taker_fraction",
    "log_return_2", "log_return_8", "log_return_24", "ema_gap_8_32",
    "high_distance_24", "high_distance_96", "low_distance_24", "low_distance_96",
    "volatility_6", "atr_fraction_14", "atr_fraction_48", "close_location",
    "volume_z24", "quote_volume_z24", "quote_volume_z96", "taker_imbalance",
    "taker_imbalance_mean_4", "taker_imbalance_mean_16", "other_asset_return_1",
    "other_asset_return_4", "other_asset_return_16", "relative_return_1",
    "relative_return_4", "rolling_corr_24", "is_BTC", "is_ETH", "hour_sin", "hour_cos",
    "weekday_sin", "weekday_cos",
)

DEFINITIONS = {
    **{f"log_return_{k}": f"log(close[t]/close[t-{k}]); {k}+1 consecutive complete hours"
       for k in (1, 2, 4, 8, 16, 24)},
    **{f"volatility_{k}": f"sample std(ddof=1) of last {k} hourly log_return_1 including t"
       for k in (6, 24, 96)},
    **{f"volume_z{k}": f"(volume[t]-mean(volume,{k}))/(std(volume,{k},ddof=1)+1e-12)"
       for k in (24, 96)},
    **{f"quote_volume_z{k}":
       f"(quote_volume[t]-mean(quote_volume,{k}))/(std(quote_volume,{k},ddof=1)+1e-12)"
       for k in (24, 96)},
    "range_fraction": "(high[t]-low[t])/close[t]",
    "body_fraction": "(close[t]-open[t])/open[t]; unchanged legacy definition",
    "ema_gap": "EMA20(close,adjust=False)/EMA100(close,adjust=False)-1; min_samples=100",
    "ema_gap_8_32": "EMA8(close,adjust=False)/EMA32(close,adjust=False)-1; min_samples=32",
    "taker_fraction": "taker_buy_base[t]/volume[t]; zero volume -> 0.5",
    **{f"{side}_distance_{k}":
       f"close[t]/{'max' if side == 'high' else 'min'}({side},last {k} bars including t)-1"
       for side in ("high", "low") for k in (24, 96)},
    **{f"atr_fraction_{k}":
       f"mean(TR,last {k} including t)/close[t]; TR=max(high-low,abs(high-prevclose),"
       "abs(low-prevclose)); first bar of segment uses high-low; not Wilder smoothing"
       for k in (14, 48)},
    "close_location": "(close-low)/(high-low); zero range -> 0.5",
    "taker_imbalance": "2*taker_fraction-1",
    **{f"taker_imbalance_mean_{k}": f"mean(2*taker_fraction-1,last {k} including t)"
       for k in (4, 16)},
    **{f"other_asset_return_{k}":
       f"other asset log_return_{k} at the SAME closed hour, only after both are available"
       for k in (1, 4, 16)},
    **{f"relative_return_{k}": f"own log_return_{k}-other_asset_return_{k}"
       for k in (1, 4)},
    "rolling_corr_24": "Pearson correlation of 24 synchronized hourly log returns; population "
                       "std<=1e-12 in either series -> 0 (uninformative); "
                       "never stale asof matching",
    "is_BTC": "1 for BTCUSDT else 0; numeric categorical indicator",
    "is_ETH": "1 for ETHUSDT else 0; numeric categorical indicator",
    "hour_sin": "sin(2*pi*UTC_hour(logical paired availability)/24)",
    "hour_cos": "cos(2*pi*UTC_hour(logical paired availability)/24)",
    "weekday_sin": "sin(2*pi*UTC_weekday(logical paired availability)/7); Monday=0",
    "weekday_cos": "cos(2*pi*UTC_weekday(logical paired availability)/7); Monday=0",
}
POLICY = {
    "interval": "1h", "warmup_consecutive_bars": 100, "history_max_bars": 100,
    "pending_max_closed_hours": 4, "gap_policy": "reset all local windows and EMAs",
    "cross_policy": "exact same close_us; never interpolate, forward fill, or use future asset",
    "availability_policy": "max of paired logical available_us, distinct from "
                           "max actual received_us",
    "ema_policy": "adjust=False; initialize first price of continuous segment; alpha=2/(span+1)",
    "rolling_policy": "trailing/current complete bar inclusive, full window, ddof=1, epsilon=1e-12",
    "normalization": "fixed trailing formula only; no fitted or global scaler",
}
INPUT_FIELDS = (
    "symbol", "interval", "open_us", "close_us", "available_us", "open", "high", "low",
    "close", "volume", "quote_volume", "taker_buy_base", "taker_buy_quote",
)
FEATURE_SCHEMA = {
    "symbol": pl.String, "interval": pl.String, "open_us": pl.Int64, "close_us": pl.Int64,
    "available_us": pl.Int64, "received_us": pl.Int64, "emitted_asof_us": pl.Int64,
    "local_available_us": pl.Int64, "other_available_us": pl.Int64,
    "local_received_us": pl.Int64, "other_received_us": pl.Int64, "feature_ready": pl.Boolean,
    **{key: pl.Float64 for key in INPUT_FIELDS[5:]},
    **dict.fromkeys(FEATURE_NAMES_V2, pl.Float64),
}


class FeatureInputError(ValueError):
    """Invalid, future, changed, or out-of-order source evidence."""


def _hash(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                    allow_nan=False).encode()).hexdigest()


def feature_schema_v2() -> dict:
    return {
        "version": VERSION, "missing_policy": "reject",
        "features": [{"name": name, "dtype": "float64", "definition": DEFINITIONS[name]}
                     for name in FEATURE_NAMES_V2],
    }


def feature_contract_v2() -> dict:
    return {
        "version": VERSION, "schema_sha256": _hash(feature_schema_v2()),
        "definition_sha256": _hash({"schema": feature_schema_v2(), "policy": POLICY}),
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def _new_symbol() -> dict:
    return {"count": 0, "last_open_us": None, "last_available_us": None,
            "ema": {}, "rows": []}


def _normalize(bar: dict, asof_us: int | None) -> tuple[dict, int]:
    if any(name not in bar for name in INPUT_FIELDS):
        raise FeatureInputError("Complete hourly OHLC/volume/taker/availability fields required")
    row = {key: bar[key] for key in INPUT_FIELDS}
    for key in ("open_us", "close_us", "available_us"):
        if not isinstance(row[key], (int, np.integer)) or isinstance(row[key], bool):
            raise FeatureInputError("UTC microseconds must be integers")
        row[key] = int(row[key])
    receipt = bar.get("received_us")
    if receipt is not None and (
        not isinstance(receipt, (int, np.integer)) or isinstance(receipt, bool)
    ):
        raise FeatureInputError("received_us must be integer UTC microseconds")
    row["received_us"] = int(receipt if receipt is not None else (
        asof_us if asof_us is not None else row["available_us"]
    ))
    now = row["received_us"] if asof_us is None else asof_us
    if not isinstance(now, (int, np.integer)) or isinstance(now, bool):
        raise FeatureInputError("asof_us must be integer UTC microseconds")
    now = int(now)
    if (
        row["symbol"] not in SYMBOLS or row["interval"] != "1h"
        or row["open_us"] % HOUR_US or row["close_us"] - row["open_us"] != HOUR_US
        or row["available_us"] < row["close_us"]
        or row["received_us"] < row["available_us"]
        or now < max(row["received_us"], row["available_us"])
    ):
        raise FeatureInputError("Incomplete, unaligned, or future hourly evidence")
    for key in INPUT_FIELDS[5:]:
        row[key] = float(row[key])
        if not math.isfinite(row[key]) or row[key] < 0:
            raise FeatureInputError("Market fields must be finite nonnegative numbers")
    if not (
        0 < row["low"] <= min(row["open"], row["close"])
        <= max(row["open"], row["close"]) <= row["high"]
        and row["taker_buy_base"] <= row["volume"]
        and row["taker_buy_quote"] <= row["quote_volume"]
    ):
        raise FeatureInputError("OHLC or taker volumes violate the input contract")
    return row, now


def _transition(state: dict, bar: dict) -> dict:
    if state["last_open_us"] is not None and bar["open_us"] != state["last_open_us"] + HOUR_US:
        state.update(_new_symbol())
    price = bar["close"]
    for span in (8, 20, 32, 100):
        previous = state["ema"].get(str(span))
        state["ema"][str(span)] = (
            price if previous is None else previous + (price - previous) * 2 / (span + 1)
        )
    state["count"] += 1
    state["last_open_us"], state["last_available_us"] = bar["open_us"], bar["available_us"]
    state["rows"] = (state["rows"] + [bar])[-100:]
    rows = state["rows"]
    closes = np.asarray([row["close"] for row in rows], dtype=float)
    returns = np.diff(np.log(closes))
    values = dict.fromkeys(FEATURE_NAMES_V2)
    for window in (1, 2, 4, 8, 16, 24):
        if len(closes) > window:
            values[f"log_return_{window}"] = (
                float(returns[-1]) if window == 1 else math.log(price / closes[-window - 1])
            )
    for window in (6, 24, 96):
        if len(returns) >= window:
            values[f"volatility_{window}"] = float(np.std(returns[-window:], ddof=1))
    for column, prefix in (("volume", "volume_z"), ("quote_volume", "quote_volume_z")):
        data = np.asarray([row[column] for row in rows], dtype=float)
        for window in (24, 96):
            if len(data) >= window:
                trailing = data[-window:]
                values[f"{prefix}{window}"] = float(
                    (data[-1] - np.mean(trailing)) / (np.std(trailing, ddof=1) + EPS)
                )
    for window in (24, 96):
        if len(rows) >= window:
            values[f"high_distance_{window}"] = price / max(r["high"] for r in rows[-window:]) - 1
            values[f"low_distance_{window}"] = price / min(r["low"] for r in rows[-window:]) - 1
    ranges = np.asarray([row["high"] - row["low"] for row in rows], dtype=float)
    true_ranges = ranges.copy()
    if len(rows) > 1:
        true_ranges[1:] = np.maximum.reduce([
            ranges[1:], np.abs([row["high"] for row in rows[1:]] - closes[:-1]),
            np.abs([row["low"] for row in rows[1:]] - closes[:-1]),
        ])
    for window in (14, 48):
        if len(rows) >= window:
            values[f"atr_fraction_{window}"] = float(np.mean(true_ranges[-window:]) / price)
    fractions = np.asarray([row["taker_buy_base"] / row["volume"] if row["volume"] > 0
                            else 0.5 for row in rows])
    imbalance = 2 * fractions - 1
    for window in (4, 16):
        if len(rows) >= window:
            values[f"taker_imbalance_mean_{window}"] = float(np.mean(imbalance[-window:]))
    values.update(
        range_fraction=ranges[-1] / price,
        body_fraction=(price - bar["open"]) / bar["open"],
        taker_fraction=float(fractions[-1]), taker_imbalance=float(imbalance[-1]),
        close_location=(price - bar["low"]) / ranges[-1] if ranges[-1] > 0 else 0.5,
        is_BTC=float(bar["symbol"] == "BTCUSDT"), is_ETH=float(bar["symbol"] == "ETHUSDT"),
    )
    if state["count"] >= 32:
        values["ema_gap_8_32"] = state["ema"]["8"] / state["ema"]["32"] - 1
    if state["count"] >= 100:
        values["ema_gap"] = state["ema"]["20"] / state["ema"]["100"] - 1
    return {"bar": bar, "values": values, "ready": state["count"] >= 100,
            "returns24": returns[-24:].tolist()}


class HourlyFeatureState:
    """Bounded state. Caller input time is verified; no network, fitting, or trading."""

    def __init__(self):
        self.contract = feature_contract_v2()
        self.state = {"symbols": {symbol: _new_symbol() for symbol in SYMBOLS},
                      "pending": {}, "last_asof_us": None, "last_emitted_end_us": None,
                      "unpaired_hours_discarded": 0}

    def ingest(self, bar: dict, *, asof_us: int | None = None) -> list[dict]:
        row, now = _normalize(bar, asof_us)
        local = self.state["symbols"][row["symbol"]]
        for old in local["rows"]:
            if old["open_us"] == row["open_us"]:
                if any(old[key] != row[key] for key in INPUT_FIELDS):
                    raise FeatureInputError("Previously observed market evidence changed")
                return []
        if local["last_open_us"] is not None and row["open_us"] <= local["last_open_us"]:
            raise FeatureInputError("Out-of-order/backfilled hourly evidence")
        if (local["last_available_us"] is not None
                and row["available_us"] <= local["last_available_us"]):
            raise FeatureInputError("Local logical availability must strictly increase")
        if self.state["last_asof_us"] is not None and now < self.state["last_asof_us"]:
            raise FeatureInputError("Observation asof cannot regress")
        snapshot = _transition(local, row)
        self.state["last_asof_us"] = now
        end = str(row["close_us"])
        pending = self.state["pending"]
        pending.setdefault(end, {})[row["symbol"]] = snapshot
        if len(pending) > 4:
            del pending[min(pending, key=int)]
            self.state["unpaired_hours_discarded"] += 1
        if end not in pending or set(pending[end]) != set(SYMBOLS):
            return []
        pair = pending.pop(end)
        if (self.state["last_emitted_end_us"] is not None
                and int(end) <= self.state["last_emitted_end_us"]):
            self.state["unpaired_hours_discarded"] += 1
            return []
        available = max(item["bar"]["available_us"] for item in pair.values())
        receipt = max(item["bar"]["received_us"] for item in pair.values())
        date = datetime.fromtimestamp(available / 1e6, UTC)
        ready = all(item["ready"] for item in pair.values())
        corr = None
        if ready:
            first, second = (np.asarray(pair[symbol]["returns24"]) for symbol in SYMBOLS)
            corr = (0.0 if np.std(first) <= EPS or np.std(second) <= EPS
                    else float(np.corrcoef(first, second)[0, 1]))
        output = []
        for symbol in SYMBOLS:
            own = pair[symbol]
            other = pair[SYMBOLS[1] if symbol == SYMBOLS[0] else SYMBOLS[0]]
            values = own["values"].copy()
            values.update(hour_sin=math.sin(2 * math.pi * date.hour / 24),
                          hour_cos=math.cos(2 * math.pi * date.hour / 24),
                          weekday_sin=math.sin(2 * math.pi * date.weekday() / 7),
                          weekday_cos=math.cos(2 * math.pi * date.weekday() / 7),
                          rolling_corr_24=corr)
            for window in (1, 4, 16):
                other_return = other["values"][f"log_return_{window}"]
                values[f"other_asset_return_{window}"] = other_return
                if window in (1, 4) and other_return is not None:
                    own_return = values[f"log_return_{window}"]
                    values[f"relative_return_{window}"] = (
                        own_return - other_return if own_return is not None else None
                    )
            if ready and any(
                value is None or not math.isfinite(value) for value in values.values()
            ):
                raise FeatureInputError("Warmed feature vector must be complete and finite")
            output.append({
                **own["bar"], **values, "available_us": available, "received_us": receipt,
                "emitted_asof_us": now, "local_available_us": own["bar"]["available_us"],
                "other_available_us": other["bar"]["available_us"],
                "local_received_us": own["bar"]["received_us"],
                "other_received_us": other["bar"]["received_us"], "feature_ready": ready,
            })
        self.state["last_emitted_end_us"] = int(end)
        return output

    def export_state(self) -> dict:
        body = {"contract": self.contract, "state": self.state}
        return copy.deepcopy({**body, "state_sha256": _hash(body)})

    @classmethod
    def from_snapshot(cls, snapshot: dict) -> HourlyFeatureState:
        body = {key: snapshot[key] for key in ("contract", "state")}
        if snapshot.get("state_sha256") != _hash(body):
            raise FeatureInputError("Feature state content digest changed")
        result = cls()
        if body["contract"] != result.contract:
            raise FeatureInputError("Feature schema/definition/implementation changed")
        state = body["state"]
        if set(state["symbols"]) != set(SYMBOLS) or len(state["pending"]) > 4:
            raise FeatureInputError("Feature state shape is invalid")
        for symbol in SYMBOLS:
            local = state["symbols"][symbol]
            if len(local["rows"]) > 100 or local["count"] < len(local["rows"]):
                raise FeatureInputError("Unbounded or inconsistent feature history")
            if local["rows"] and local["last_open_us"] != local["rows"][-1]["open_us"]:
                raise FeatureInputError("Feature history boundary mismatch")
        result.state = copy.deepcopy(state)
        return result


def build_features_v2(bars: pl.DataFrame, *, include_warmup: bool = False) -> pl.DataFrame:
    """Batch = the same transition in availability/receipt order, without learned scaling."""
    if not set(INPUT_FIELDS).issubset(bars.columns):
        raise FeatureInputError("Hourly feature input schema is incomplete")
    order = "received_us" if "received_us" in bars.columns else "available_us"
    state, outputs = HourlyFeatureState(), []
    for row in bars.sort([order, "available_us", "symbol"]).iter_rows(named=True):
        for feature in state.ingest(row):
            if include_warmup or feature["feature_ready"]:
                outputs.append(feature)
    return pl.DataFrame(outputs, schema=FEATURE_SCHEMA).sort(["available_us", "symbol"])
