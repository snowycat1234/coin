"""A10 fixed, causal per-symbol view of complete microstructure_l1_v2 5s rows.

Pure numerical transition: no collector, market IO, database, network, fitting or labels.
Current z-scores use strictly earlier state; only then is that state updated.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from collections.abc import Iterable, Iterator, Mapping
from numbers import Integral, Real
from pathlib import Path

SOURCE_VERSION = "microstructure_l1_v2"
VERSION = "microstructure_causal_features_v2.0"
STATE_VERSION = "microstructure_causal_ewm_state_v2.0"
SYMBOLS = ("BTCUSDT", "ETHUSDT")
SECOND_US = 1_000_000
INTERVAL_US = 5 * SECOND_US
HALF_LIFE_SECONDS = 3_600
WARMUP_PAST_SAMPLES = 720
EPS = 1e-12
INVALID_QUALITY_MASK = 507
KNOWN_QUALITY_MASK = 2047

INPUT_FIELDS = (
    "version", "symbol", "mode", "session", "interval_s", "open_us", "close_us",
    "available_us", "quality", "known_seconds", "valid_seconds", "mid_last",
    "spread_bps_mean", "spread_bps_last", "l1_total_depth_last", "bid_qty_mean_mean",
    "ask_qty_mean_mean", "L1_imbalance_mean_mean", "L1_imbalance_last",
    "microprice_offset_bps_mean_mean", "OFI_L1", "aggressive_buy_notional",
    "aggressive_sell_notional", "trade_vwap", "quote_update_count", "agg_trade_count",
    "realized_return",
)
DERIVED_FEATURES = (
    "ofi_depth_norm", "log_l1_depth", "log_trade_notional", "trade_flow_imbalance",
    "vwap_offset_bps", "log_quote_updates", "log_trade_count", "quote_trade_ratio",
)
RETAINED_FEATURES = (
    "spread_bps", "L1_imbalance_mean", "L1_imbalance_last",
    "microprice_offset_bps_mean", "realized_return_5s",
)
SCALE_HEAVY_FEATURES = tuple(name for name in DERIVED_FEATURES
                             if name != "trade_flow_imbalance")
RAW_FEATURES = DERIVED_FEATURES + RETAINED_FEATURES
FEATURE_NAMES_V2 = RAW_FEATURES + tuple(f"{name}_z1h" for name in SCALE_HEAVY_FEATURES)
# This whitelist is an interface for a later authorized study, not a model or qualification.
# Raw scale-heavy values remain visible for QA, but must never enter a pooled model by default.
MODEL_FEATURE_NAMES = tuple(f"{name}_z1h" for name in SCALE_HEAVY_FEATURES) + (
    "trade_flow_imbalance",
) + RETAINED_FEATURES
DEFINITIONS = {
    "ofi_depth_norm": "OFI_L1/(bid_qty_mean_mean+ask_qty_mean_mean+1e-12)",
    "log_l1_depth": "log1p(bid_qty_mean_mean+ask_qty_mean_mean); base-asset quantity",
    "log_trade_notional": "log1p(aggressive_buy_notional+aggressive_sell_notional); USDT",
    "trade_flow_imbalance": "(buy-sell)/(buy+sell+1e-12); no trades -> 0",
    "vwap_offset_bps": "(trade_vwap/mid_last-1)*10000; no trades -> null",
    "log_quote_updates": "log1p(quote_update_count); 5s sum count",
    "log_trade_count": "log1p(agg_trade_count); 5s sum count",
    "quote_trade_ratio": "log1p(quote_update_count)-log1p(agg_trade_count)",
    "spread_bps": "spread_bps_mean; unweighted mean of the five 1s bucket means",
    "L1_imbalance_mean": "L1_imbalance_mean_mean; unweighted mean of 1s means",
    "L1_imbalance_last": "actual final-second L1 imbalance; never last-non-null",
    "microprice_offset_bps_mean": "microprice_offset_bps_mean_mean; mean of 1s means",
    "realized_return_5s": "source realized_return; sum of backward 1s log returns; null kept",
}
POLICY = {
    "source_version": SOURCE_VERSION, "symbols": list(SYMBOLS), "interval_s": 5,
    "epsilon": EPS, "half_life_seconds": HALF_LIFE_SECONDS,
    "warmup_past_nonnull_samples_per_field": WARMUP_PAST_SAMPLES,
    "scale_heavy_features": list(SCALE_HEAVY_FEATURES),
    "ewm": "adjust=False population variance; alpha=1-exp(-ln(2)*elapsed_seconds/3600)",
    "order": "validate, derive, compute all z from past state, then update current values",
    "time": "per-symbol strictly increasing aligned close; nondecreasing available_us",
    "reset": "per-symbol gap!=5s, session change, INVALID, incomplete or required input null",
    "null": "no trade VWAP and unavailable backward return stay null; no imputation",
    "zero_variance": "prior variance<=epsilon**2: equal current/mean -> 0; else null",
    "unknown": "wrong version/symbol, unknown quality bits, nonfinite or malformed -> reject",
    "state": "separate fixed symbol states; schema/definition/implementation SHA and checksum",
    "provenance": "each symbol permanently binds live or engineering; mixed mode rejected",
    "future_model_input_whitelist": list(MODEL_FEATURE_NAMES),
    "purpose": "QA_ONLY; no qualification, future return, labels, global fit or model choice",
}
_NONNEGATIVE = {
    "spread_bps_mean", "spread_bps_last", "l1_total_depth_last", "bid_qty_mean_mean",
    "ask_qty_mean_mean", "aggressive_buy_notional", "aggressive_sell_notional",
    "quote_update_count", "agg_trade_count",
}
_CORE_REQUIRED = tuple(name for name in INPUT_FIELDS[11:]
                       if name not in {"trade_vwap", "realized_return"})


class MicroFeatureInputError(ValueError):
    """Source row or restart state violates the fixed v2 contract."""


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode()).hexdigest()


def micro_feature_schema_v2() -> dict:
    return {
        "version": VERSION, "inputs": list(INPUT_FIELDS),
        "future_model_input_fields": list(MODEL_FEATURE_NAMES),
        "qa_raw_only_fields": list(SCALE_HEAVY_FEATURES),
        "features": [{"name": name, "dtype": "nullable_float64", "definition":
                      DEFINITIONS[name] if name in DEFINITIONS else
                      f"past-only EWM z-score of {name.removesuffix('_z1h')}",
                      "role": "MODEL_INPUT" if name in MODEL_FEATURE_NAMES else "QA_RAW_ONLY"}
                     for name in FEATURE_NAMES_V2],
    }


def micro_feature_contract_v2() -> dict:
    schema = micro_feature_schema_v2()
    return {
        "version": VERSION, "source_version": SOURCE_VERSION,
        "schema_sha256": _hash(schema), "definition_sha256": _hash((schema, POLICY)),
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }


def _integer(value: object, name: str, *, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or value < minimum:
        raise MicroFeatureInputError(f"{name} must be an integer >= {minimum}")
    return int(value)


def _optional_number(value: object, name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise MicroFeatureInputError(f"{name} must be a numeric value or null")
    result = float(value)
    if not math.isfinite(result):
        raise MicroFeatureInputError(f"{name} must be finite")
    if name in _NONNEGATIVE and result < 0:
        raise MicroFeatureInputError(f"{name} must be nonnegative")
    if name in {"mid_last", "trade_vwap"} and result <= 0:
        raise MicroFeatureInputError(f"{name} must be positive")
    if name in {"L1_imbalance_mean_mean", "L1_imbalance_last"} and abs(result) > 1:
        raise MicroFeatureInputError(f"{name} must be in [-1,1]")
    if name in {"quote_update_count", "agg_trade_count"} and (
        not result.is_integer() or result > 2**53
    ):
        raise MicroFeatureInputError(f"{name} must be an exactly representable integer count")
    return result


def _normalize(row: Mapping, asof_us: int | None) -> tuple[dict, int]:
    if not isinstance(row, Mapping) or any(name not in row for name in INPUT_FIELDS):
        raise MicroFeatureInputError("Full microstructure_l1_v2 aggregate input fields required")
    result = {name: row[name] for name in INPUT_FIELDS}
    if result["version"] != SOURCE_VERSION or result["symbol"] not in SYMBOLS:
        raise MicroFeatureInputError("Only the registered v2 source version/symbols are allowed")
    if result["mode"] not in {"live", "engineering"} or not isinstance(
        result["session"], str
    ) or not 0 < len(result["session"]) <= 128:
        raise MicroFeatureInputError("Explicit provenance mode and nonempty session required")
    for name in INPUT_FIELDS[4:11]:
        result[name] = _integer(result[name], name)
    now = _integer(result["available_us"] if asof_us is None else asof_us, "asof_us")
    if (result["interval_s"] != 5 or result["open_us"] % INTERVAL_US
        or result["close_us"] != result["open_us"] + INTERVAL_US
        or result["available_us"] < result["close_us"] or now < result["available_us"]):
        raise MicroFeatureInputError("Require aligned closed 5s bucket available at asof_us")
    if result["quality"] & ~KNOWN_QUALITY_MASK:
        raise MicroFeatureInputError("Unknown quality bits are not admitted by this contract")
    if not 0 <= result["valid_seconds"] <= result["known_seconds"] <= 5:
        raise MicroFeatureInputError("Impossible 5s completeness counters")
    for name in INPUT_FIELDS[11:]:
        result[name] = _optional_number(result[name], name)
    return result, now


def _derive(row: dict) -> dict:
    depth = row["bid_qty_mean_mean"] + row["ask_qty_mean_mean"]
    buy, sell = row["aggressive_buy_notional"], row["aggressive_sell_notional"]
    notional = buy + sell
    if not all(math.isfinite(value) for value in (depth, notional)):
        raise MicroFeatureInputError("Derived depth/notional overflow")
    no_trades = row["agg_trade_count"] == 0
    if (no_trades and (notional != 0 or row["trade_vwap"] is not None)) or (
        not no_trades and (notional <= 0 or row["trade_vwap"] is None)
    ):
        raise MicroFeatureInputError("Trade count, notional and nullable VWAP disagree")
    quote_log, trade_log = math.log1p(row["quote_update_count"]), math.log1p(
        row["agg_trade_count"]
    )
    result = {
        "ofi_depth_norm": row["OFI_L1"] / (depth + EPS),
        "log_l1_depth": math.log1p(depth), "log_trade_notional": math.log1p(notional),
        "trade_flow_imbalance": (buy - sell) / (notional + EPS),
        "vwap_offset_bps": (row["trade_vwap"] / row["mid_last"] - 1) * 10_000
        if row["trade_vwap"] is not None else None,
        "log_quote_updates": quote_log, "log_trade_count": trade_log,
        "quote_trade_ratio": quote_log - trade_log,
        "spread_bps": row["spread_bps_mean"],
        "L1_imbalance_mean": row["L1_imbalance_mean_mean"],
        "L1_imbalance_last": row["L1_imbalance_last"],
        "microprice_offset_bps_mean": row["microprice_offset_bps_mean_mean"],
        "realized_return_5s": row["realized_return"],
    }
    if any(value is not None and not math.isfinite(value) for value in result.values()):
        raise MicroFeatureInputError("Derived feature overflow")
    return result


def _new_symbol() -> dict:
    return {"last_close_us": None, "last_available_us": None, "session": None,
            "mode": None, "consecutive_valid_buckets": 0, "ewm": {}}


def _score(value: float | None, past: dict | None) -> tuple[float | None, str]:
    if value is None:
        return None, "NULL_CURRENT"
    if past is None or past["count"] < WARMUP_PAST_SAMPLES:
        return None, "WARMUP"
    delta = value - past["mean"]
    if past["variance"] <= EPS**2:
        return (0.0, "ZERO_VARIANCE_CONSTANT") if delta == 0 else (None, "ZERO_VARIANCE_CHANGE")
    score = delta / math.sqrt(past["variance"])
    if not math.isfinite(score):
        raise MicroFeatureInputError("Past-only z-score overflow")
    return score, "READY"


def _updated(value: float, past: dict | None, close_us: int) -> dict:
    if past is None:
        return {"count": 1, "last_us": close_us, "mean": value, "variance": 0.0}
    elapsed_seconds = (close_us - past["last_us"]) / SECOND_US
    alpha = -math.expm1(-math.log(2) * elapsed_seconds / HALF_LIFE_SECONDS)
    delta = value - past["mean"]
    mean = past["mean"] + alpha * delta
    variance = (1 - alpha) * (past["variance"] + alpha * delta * delta)
    if not math.isfinite(mean) or not math.isfinite(variance):
        raise MicroFeatureInputError("EWM state overflow")
    return {"count": past["count"] + 1, "last_us": close_us, "mean": mean,
            "variance": variance}


class MicroFeatureState:
    """Bounded 2-symbol state. Every rejected transition is atomic and leaves state unchanged."""

    def __init__(self):
        self._symbols = {symbol: _new_symbol() for symbol in SYMBOLS}

    def ingest(self, source: Mapping, *, asof_us: int | None = None) -> dict:
        row, now = _normalize(source, asof_us)
        prior = self._symbols[row["symbol"]]
        if prior["mode"] is not None and row["mode"] != prior["mode"]:
            raise MicroFeatureInputError("Live and engineering provenance cannot share state")
        if prior["last_close_us"] is not None and (
            row["close_us"] <= prior["last_close_us"]
            or row["available_us"] < prior["last_available_us"]
        ):
            raise MicroFeatureInputError("Per-symbol duplicate or out-of-order source row")
        reset = None
        if prior["last_close_us"] is None:
            reset = "START"
        elif row["session"] != prior["session"]:
            reset = "SESSION_CHANGE"
        elif row["close_us"] - prior["last_close_us"] != INTERVAL_US:
            reset = "TIME_GAP"
        if row["quality"] & INVALID_QUALITY_MASK:
            source_status = reset = "INVALID_QUALITY"
        elif row["known_seconds"] != 5 or row["valid_seconds"] != 5:
            source_status = reset = "INCOMPLETE_BUCKET"
        elif any(row[name] is None for name in _CORE_REQUIRED):
            source_status = reset = "NULL_REQUIRED_INPUT"
        else:
            source_status = "VALID"
        # All changes are prepared locally. Derivation/overflow/rejection cannot partially commit.
        state = _new_symbol() if reset else copy.deepcopy(prior)
        output = {
            "version": VERSION, "source_version": SOURCE_VERSION, "symbol": row["symbol"],
            "mode": row["mode"], "session": row["session"], "open_us": row["open_us"],
            "close_us": row["close_us"], "available_us": row["available_us"],
            "emitted_asof_us": now, "interval_s": 5, "quality": row["quality"],
            "source_status": source_status, "reset_reason": reset, "feature_ready": False,
            "normalization_status": {}, "scaler_prior_samples": {},
            **dict.fromkeys(FEATURE_NAMES_V2),
        }
        if source_status == "VALID":
            output.update(_derive(row))
            for name in SCALE_HEAVY_FEATURES:
                past = state["ewm"].get(name)
                output[f"{name}_z1h"], status = _score(output[name], past)
                output["normalization_status"][name] = status
                output["scaler_prior_samples"][name] = past["count"] if past else 0
            for name in SCALE_HEAVY_FEATURES:
                if output[name] is not None:
                    state["ewm"][name] = _updated(output[name], state["ewm"].get(name),
                                                   row["close_us"])
            state["consecutive_valid_buckets"] += 1
            output["feature_ready"] = all(output[name] is not None for name in MODEL_FEATURE_NAMES)
        else:
            output["normalization_status"] = dict.fromkeys(SCALE_HEAVY_FEATURES, source_status)
            output["scaler_prior_samples"] = dict.fromkeys(SCALE_HEAVY_FEATURES, 0)
        state.update(last_close_us=row["close_us"], last_available_us=row["available_us"],
                     session=row["session"], mode=row["mode"])
        self._symbols[row["symbol"]] = state
        return output

    def export_state(self) -> dict:
        payload = {"state_version": STATE_VERSION, "contract": micro_feature_contract_v2(),
                   "symbols": copy.deepcopy(self._symbols)}
        return {**payload, "sha256": _hash(payload)}

    @classmethod
    def from_snapshot(cls, snapshot: Mapping) -> MicroFeatureState:
        if not isinstance(snapshot, Mapping) or set(snapshot) != {
            "state_version", "contract", "symbols", "sha256"
        }:
            raise MicroFeatureInputError("Invalid restart snapshot fields")
        payload = {key: copy.deepcopy(snapshot[key]) for key in snapshot if key != "sha256"}
        try:
            checksum = _hash(payload)
        except (TypeError, ValueError) as error:
            raise MicroFeatureInputError("Restart state must be finite canonical JSON") from error
        if (snapshot["sha256"] != checksum or snapshot["state_version"] != STATE_VERSION
            or snapshot["contract"] != micro_feature_contract_v2()):
            raise MicroFeatureInputError("Restart checksum/version/source contract mismatch")
        symbols = payload["symbols"]
        if not isinstance(symbols, dict) or set(symbols) != set(SYMBOLS):
            raise MicroFeatureInputError("Restart symbols cannot be shared or added")
        for state in symbols.values():
            cls._validate_symbol_state(state)
        instance = cls()
        instance._symbols = {symbol: copy.deepcopy(symbols[symbol]) for symbol in SYMBOLS}
        return instance

    @staticmethod
    def _validate_symbol_state(state: object):
        if not isinstance(state, dict) or set(state) != set(_new_symbol()):
            raise MicroFeatureInputError("Malformed symbol restart state")
        count = _integer(state["consecutive_valid_buckets"], "consecutive_valid_buckets")
        ewm = state["ewm"]
        if not isinstance(ewm, dict) or not set(ewm).issubset(SCALE_HEAVY_FEATURES):
            raise MicroFeatureInputError("Unregistered restart scaler field")
        close, available = state["last_close_us"], state["last_available_us"]
        if close is None:
            if state != _new_symbol():
                raise MicroFeatureInputError("Initial restart state must be empty")
            return
        close = _integer(close, "last_close_us")
        available = _integer(available, "last_available_us")
        if (close % INTERVAL_US or available < close or not isinstance(state["session"], str)
            or not 0 < len(state["session"]) <= 128 or (count == 0 and ewm)
            or state["mode"] not in {"live", "engineering"}):
            raise MicroFeatureInputError("Invalid restart timing/session/completeness")
        required_scalers = set(SCALE_HEAVY_FEATURES) - {"vwap_offset_bps"}
        if count and not required_scalers.issubset(ewm):
            raise MicroFeatureInputError("Missing nonnullable restart scaler")
        for past in ewm.values():
            if not isinstance(past, dict) or set(past) != {"count", "last_us", "mean", "variance"}:
                raise MicroFeatureInputError("Malformed EWM restart state")
            samples = _integer(past["count"], "count", minimum=1)
            last_us = _integer(past["last_us"], "last_us")
            mean = _optional_number(past["mean"], "mean")
            variance = _optional_number(past["variance"], "variance")
            if (samples > count or last_us % INTERVAL_US or not
                close - (count - 1) * INTERVAL_US <= last_us <= close
                or mean is None or variance is None or variance < 0):
                raise MicroFeatureInputError("Impossible EWM moments/count/time")


def iter_micro_features_v2(rows: Iterable[Mapping], *, asof_us: int | None = None
                           ) -> Iterator[dict]:
    """Stream rows in caller order through the exact same incremental transition."""
    state = MicroFeatureState()
    for row in rows:
        yield state.ingest(row, asof_us=asof_us)


def build_micro_features_v2(rows: Iterable[Mapping], *, asof_us: int | None = None) -> list[dict]:
    """Convenience batch wrapper, with no sort, fitted scaler, cross-symbol join or backfill."""
    return list(iter_micro_features_v2(rows, asof_us=asof_us))
