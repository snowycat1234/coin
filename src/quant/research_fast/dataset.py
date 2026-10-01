"""FR64 one Arrow/Polars-backed window, label, fold and train-only scaler API.

Only endpoints are persisted; no [samples,256,F] array is materialized. Torch is
imported only by the optional Dataset bridge, and dependency installation is external.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pyarrow.parquet as pq
from sklearn.preprocessing import StandardScaler

from quant.paths import ROOT, STATE

from .labels import BAR_US, LABEL_COLUMNS, LABEL_LAG_US, TARGET_STREAMS, TASKS, label_table
from .trade_flow_v2 import CONTRACT, FROZEN_CORE, source_hashes

SOURCE_VERSION = "trade_flow_5s_v2"
START = date(2025, 7, 1)
LOCKED = date(2026, 3, 1)
DAY_US = 86_400_000_000
PAST_BARS = 256
ENDPOINT_STEP_US = 60_000_000
EMBARGO_US = 300_000_000
STREAMS = ("spot_BTCUSDT", "spot_ETHUSDT", "perp_BTCUSDT", "perp_ETHUSDT")
FEATURES_PER_STREAM = (
    "return_5s",
    "flow_imbalance",
    "vwap_close_offset_bps",
    "log_hl_range",
    "large_trade_share",
    "signed_price_impact",
    "log_quote_notional",
    "log_base_volume",
    "log_trade_count",
    "log_agg_count",
    "log_mean_trade_size",
    "log_max_trade_size",
    "log_mean_interarrival",
    "log_std_interarrival",
    "has_trade",
    "has_return",
    "has_interarrival",
)
FEATURE_COLUMNS = tuple(f"{stream}__{name}" for stream in STREAMS for name in FEATURES_PER_STREAM)
SCALE_INDICES = tuple(
    index
    for index, name in enumerate(FEATURE_COLUMNS)
    if not name.rsplit("__", 1)[-1].startswith("has_")
)
SOURCE_COLUMNS = (
    "version",
    "market",
    "symbol",
    "timestamp",
    "close_us",
    "available_us",
    "quality",
    "open",
    "high",
    "low",
    "close",
    "vwap",
    "trade_count",
    "buy_count",
    "sell_count",
    "agg_count",
    "base_volume",
    "quote_notional",
    "aggressive_buy_notional",
    "aggressive_sell_notional",
    "flow_imbalance",
    "mean_trade_size",
    "max_trade_size",
    "large_trade_share",
    "mean_interarrival",
    "std_interarrival",
    "interarrival_count",
    "return_5s",
    "signed_price_impact",
    "first_trade_us",
    "last_trade_us",
    "empty_bin",
)


def _sha(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def file_sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1_048_576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def day_us(day: date) -> int:
    return int(datetime.combine(day, datetime.min.time(), UTC).timestamp()) * 1_000_000


def protocol() -> dict:
    return json.loads((ROOT / "protocols/fast_research_v6.json").read_text())


@dataclass(frozen=True)
class ShardSpec:
    path: Path
    market: str
    symbol: str
    day: date
    rows: int
    sha256: str
    checksum_verified: bool = False
    provenance: str = "engineering_synthetic"
    first_raw_id: int | None = None
    last_raw_id: int | None = None
    first_agg_id: int | None = None
    last_agg_id: int | None = None
    scope_boundary_verified: bool = False

    @property
    def stream(self) -> str:
        return f"{self.market}_{self.symbol}"

    @property
    def start_us(self) -> int:
        return day_us(self.day)

    @property
    def end_us(self) -> int:
        return self.start_us + self.rows * BAR_US

    @classmethod
    def from_conversion(cls, path: Path, summary: dict, *, checksum_verified: bool):
        """Thin adapter; the official fetch receipt must establish checksum_verified."""
        if summary.get("status") != "OFFICIAL_ARCHIVE_CONVERSION_COMPLETE" or (
            summary.get("version") != SOURCE_VERSION
        ):
            raise ValueError("Require the verified FR62 conversion receipt")
        return cls(
            Path(path),
            summary["market"],
            summary["symbol"],
            date.fromisoformat(summary["date"]),
            summary["rows"],
            summary["parquet_sha256"],
            checksum_verified,
            "official_binance_checksum",
            summary["first_f"],
            summary["last_l"],
            summary["first_a"],
            summary["last_a"],
            summary["cross_day_scope_boundary_verified"],
        )

    @classmethod
    def from_manifest(cls, path: Path):
        """Read only an explicitly named, in-range FR62 manifest, never glob history."""
        path = Path(path)
        declared_day = date.fromisoformat(path.name[:10])
        if not START <= declared_day < LOCKED or path.stat().st_size > 131_072:
            raise ValueError("Manifest date/size outside development contract")
        payload = json.loads(path.read_text())
        converted = payload["conversion"]
        if (
            payload.get("date") != declared_day.isoformat()
            or payload.get("status") != "OFFICIAL_HF_DAY_ACCEPTED"
            or payload.get("engineering_fixture_hook") is not False
            or payload.get("source_hashes") != FROZEN_CORE
            or payload.get("checksum_status") != "PASS"
            or payload.get("feature_sha256") != converted.get("parquet_sha256")
            or converted.get("adapter_source_hashes") != source_hashes()
            or converted.get("contract") != CONTRACT
            or Path(payload["owned_temporary_directory"]).exists()
        ):
            raise ValueError("Manifest checksum/feature/date binding mismatch")
        return cls.from_conversion(Path(payload["feature_path"]), converted, checksum_verified=True)


@dataclass(frozen=True)
class Fold:
    name: str
    train_start_us: int
    validation_start_us: int
    test_start_us: int
    test_end_us: int

    @property
    def fit_cutoff_us(self) -> int:
        return self.validation_start_us - EMBARGO_US - LABEL_LAG_US

    def interval(self, split: str) -> tuple[int, int, int]:
        if split == "train":
            return self.train_start_us, self.fit_cutoff_us, self.validation_start_us - EMBARGO_US
        if split == "validation":
            return (
                self.validation_start_us,
                self.test_start_us - EMBARGO_US - LABEL_LAG_US,
                self.test_start_us - EMBARGO_US,
            )
        if split == "test":
            return self.test_start_us, self.test_end_us - LABEL_LAG_US, self.test_end_us
        raise ValueError("Unknown common split")


def make_folds() -> tuple[Fold, ...]:
    """Six fixed full 14/7/7 folds, chosen before outcomes within the first 180d prefix."""
    result = []
    for index in (0, 4, 9, 13, 18, 22):
        start = START + timedelta(days=7 * index)
        result.append(
            Fold(
                f"rolling_{index:02d}",
                day_us(start),
                day_us(start + timedelta(days=12)),
                day_us(start + timedelta(days=14)),
                day_us(start + timedelta(days=21)),
            )
        )
    return tuple(result)


def feature_matrix(joint: pl.DataFrame) -> np.ndarray:
    """Current closed-bar features only; undefined observables have explicit masks."""
    expressions = []
    for stream in STREAMS:

        def col(name, stream=stream):
            return pl.col(f"{stream}__{name}")

        definitions = {
            "return_5s": col("return_5s"),
            "flow_imbalance": col("flow_imbalance"),
            "vwap_close_offset_bps": (col("vwap") / col("close") - 1) * 10_000,
            "log_hl_range": (col("high") / col("low")).log(),
            "large_trade_share": col("large_trade_share"),
            "signed_price_impact": col("signed_price_impact"),
            **{
                f"log_{name}": col(name).log1p()
                for name in (
                    "quote_notional",
                    "base_volume",
                    "trade_count",
                    "agg_count",
                    "mean_trade_size",
                    "max_trade_size",
                    "mean_interarrival",
                    "std_interarrival",
                )
            },
            "has_trade": (~col("empty_bin")).cast(pl.Float64),
            "has_return": col("return_5s").is_not_null().cast(pl.Float64),
            "has_interarrival": (col("interarrival_count") > 0).cast(pl.Float64),
        }
        expressions.extend(
            definitions[name].fill_null(0).alias(f"{stream}__{name}")
            for name in FEATURES_PER_STREAM
        )
    values = joint.select(expressions).to_numpy().astype(np.float32)
    if not np.isfinite(values).all():
        raise ValueError("Nonfinite common input feature")
    return values


def tabular_view(x: np.ndarray) -> np.ndarray:
    if x.shape[-2:] != (PAST_BARS, len(FEATURE_COLUMNS)):
        raise ValueError("Require the identical common [256,68] tensor")
    return np.concatenate((x[..., -1, :], x.mean(axis=-2), x.std(axis=-2)), axis=-1)


@dataclass(frozen=True)
class FoldNormalizer:
    scaler: StandardScaler
    dataset_sha256: str
    fold_name: str
    fit_first_us: int
    fit_last_us: int
    rows: int

    def transform(self, x: np.ndarray) -> np.ndarray:
        output = x.copy()
        output[..., SCALE_INDICES] = self.scaler.transform(x[..., SCALE_INDICES])
        if not np.isfinite(output).all():
            raise ValueError("Nonfinite train-only normalization")
        return output

    def receipt(self) -> dict:
        return {
            "implementation": "sklearn.preprocessing.StandardScaler",
            "dataset_sha256": self.dataset_sha256,
            "fold": self.fold_name,
            "fit_first_us": self.fit_first_us,
            "fit_last_us": self.fit_last_us,
            "rows": self.rows,
            "mean": self.scaler.mean_.tolist(),
            "scale": self.scaler.scale_.tolist(),
            "variance": self.scaler.var_.tolist(),
            "columns": list(SCALE_INDICES),
        }


@dataclass(frozen=True)
class TargetNormalizer:
    scaler: StandardScaler
    dataset_sha256: str
    fold_name: str
    fit_last_label_available_us: int
    rows: int

    def transform(self, y: np.ndarray) -> np.ndarray:
        return self.scaler.transform(y.reshape(-1, len(LABEL_COLUMNS))).reshape(y.shape)

    def inverse_transform(self, y: np.ndarray) -> np.ndarray:
        return self.scaler.inverse_transform(y.reshape(-1, len(LABEL_COLUMNS))).reshape(y.shape)

    def receipt(self) -> dict:
        return {
            "implementation": "sklearn.preprocessing.StandardScaler",
            "dataset_sha256": self.dataset_sha256,
            "fold": self.fold_name,
            "rows": self.rows,
            "fit_last_label_available_us": self.fit_last_label_available_us,
            "labels": list(LABEL_COLUMNS),
            "mean": self.scaler.mean_.tolist(),
            "scale": self.scaler.scale_.tolist(),
            "variance": self.scaler.var_.tolist(),
        }


class FastSequenceDataset:
    """Bounded Parquet row-group reads and a small memory-mapped endpoint index."""

    def __init__(self, shards: list[ShardSpec], *, mode: str = "smoke"):
        if mode not in {"smoke", "formal"} or not shards:
            raise ValueError("Explicit smoke/formal and nonempty declared shards required")
        # Validate every declared date BEFORE opening any file; never discover locked files.
        for spec in shards:
            path = spec.path.resolve()
            if (
                not isinstance(spec.day, date)
                or not START <= spec.day < LOCKED
                or spec.stream not in STREAMS
                or not 0 < spec.rows <= 17_280
                or not (path.is_relative_to(ROOT.resolve()) or path.is_relative_to(STATE.resolve()))
                or len(spec.sha256) != 64
            ):
                raise ValueError("Declared source/date/path outside the development contract")
        self.shards = sorted(shards, key=lambda item: (item.day, item.stream))
        keys = {(item.day, item.stream) for item in shards}
        if len(keys) != len(shards) or {item.stream for item in shards} != set(STREAMS):
            raise ValueError("Require exactly one source per stream-day and all four streams")
        self.mode = mode
        self._stats = {}
        self._metadata = {}
        for spec in self.shards:
            if file_sha(spec.path) != spec.sha256:
                raise ValueError("Published feature SHA mismatch")
            metadata = pq.ParquetFile(spec.path).metadata
            if metadata.num_rows != spec.rows or any(
                metadata.row_group(index).num_rows > 17_280
                for index in range(metadata.num_row_groups)
            ):
                raise ValueError("Declared bounded 5s rows differ from Parquet")
            self._stats[spec.path] = (spec.path.stat().st_size, spec.path.stat().st_mtime_ns)
            self._metadata[spec.path] = metadata
        self.days = sorted({item.day for item in self.shards})
        self.complete_days = tuple(
            day
            for day in self.days
            if all(
                any(
                    spec.day == day
                    and spec.stream == stream
                    and spec.rows == 17_280
                    and spec.checksum_verified
                    and spec.provenance == "official_binance_checksum"
                    for spec in self.shards
                )
                for stream in STREAMS
            )
        )
        if mode == "formal":
            expected = {START + timedelta(days=index) for index in range(180)}
            if not expected.issubset(self.complete_days):
                raise ValueError(
                    "INSUFFICIENT_EVIDENCE: first 180 complete common UTC days required"
                )
            for stream in STREAMS:
                run = sorted(
                    (s for s in self.shards if s.stream == stream and s.day in expected),
                    key=lambda s: s.day,
                )
                for previous, current in zip(run, run[1:], strict=False):
                    if (
                        previous.last_raw_id is None
                        or current.first_raw_id is None
                        or not current.scope_boundary_verified
                        or (
                            stream.startswith("spot_")
                            and current.first_raw_id != previous.last_raw_id + 1
                        )
                        or (
                            stream.startswith("perp_")
                            and (
                                current.first_raw_id <= previous.last_raw_id
                                or previous.last_agg_id is None
                                or current.first_agg_id != previous.last_agg_id + 1
                            )
                        )
                    ):
                        raise ValueError("Unverified/gapped cross-day observation scope boundary")
        self.contract_sha256 = _sha(
            {
                "protocol": protocol(),
                "shards": [
                    {
                        "day": s.day.isoformat(),
                        "stream": s.stream,
                        "rows": s.rows,
                        "sha256": s.sha256,
                        "checksum_verified": s.checksum_verified,
                        "provenance": s.provenance,
                        "first_raw_id": s.first_raw_id,
                        "last_raw_id": s.last_raw_id,
                        "first_agg_id": s.first_agg_id,
                        "last_agg_id": s.last_agg_id,
                        "scope_boundary_verified": s.scope_boundary_verified,
                    }
                    for s in self.shards
                ],
            }
        )
        self.index = None
        self.normalizer = None
        self.target_normalizer = None
        self.fold = None
        self.split = None

    def _read(self, spec: ShardSpec, start: int, end: int) -> pl.DataFrame:
        current_stat = (spec.path.stat().st_size, spec.path.stat().st_mtime_ns)
        if current_stat != self._stats[spec.path]:
            raise ValueError("Frozen feature source changed")
        lower = max(0, (start - spec.start_us) // BAR_US)
        upper = min(spec.rows, (end - spec.start_us + BAR_US - 1) // BAR_US)
        groups, offset = [], 0
        metadata = self._metadata[spec.path]
        for index in range(metadata.num_row_groups):
            count = metadata.row_group(index).num_rows
            if offset < upper and offset + count > lower:
                groups.append(index)
            offset += count
        table = pq.ParquetFile(spec.path).read_row_groups(
            groups, columns=list(SOURCE_COLUMNS), use_threads=False
        )
        frame = pl.from_arrow(table).filter(
            pl.col("timestamp").is_between(start, end, closed="left")
        )
        if frame.is_empty():
            return frame
        times = frame["timestamp"].to_numpy()
        if (
            frame["version"].unique().to_list() != [SOURCE_VERSION]
            or frame["market"].unique().to_list() != [spec.market]
            or frame["symbol"].unique().to_list() != [spec.symbol]
            or (np.diff(times) != BAR_US).any()
            or (times % BAR_US).any()
            or times.min() < spec.start_us
            or times.max() >= spec.end_us
            or not (frame["close_us"] == frame["timestamp"] + BAR_US).all()
            or not (frame["available_us"] == frame["close_us"]).all()
            or not (frame["quality"] == 0).all()
        ):
            raise ValueError("Unknown, invalid or nonconsecutive published 5s evidence")
        required = (
            "timestamp",
            "close_us",
            "available_us",
            "quality",
            "empty_bin",
            "trade_count",
            "buy_count",
            "sell_count",
            "agg_count",
            "interarrival_count",
            "base_volume",
            "quote_notional",
            "aggressive_buy_notional",
            "aggressive_sell_notional",
        )
        numbers = SOURCE_COLUMNS[7:30]
        if (
            frame.select(pl.any_horizontal([pl.col(name).is_null() for name in required]))
            .to_series()
            .any()
        ):
            raise ValueError("Unknown required source values")
        if (
            frame.select(
                pl.any_horizontal(
                    [pl.col(name).is_not_null() & ~pl.col(name).is_finite() for name in numbers]
                )
            )
            .to_series()
            .any()
        ):
            raise ValueError("Nonfinite source values cannot become zero/masks")
        source_valid = (
            (pl.col("trade_count") >= 0)
            & (pl.col("buy_count") >= 0)
            & (pl.col("sell_count") >= 0)
            & (pl.col("buy_count") + pl.col("sell_count") == pl.col("trade_count"))
            & (pl.col("agg_count") >= 0)
            & (pl.col("agg_count") == pl.col("trade_count"))
            & (pl.col("empty_bin") == (pl.col("trade_count") == 0))
        )
        traded = ~pl.col("empty_bin")
        for field in ("open", "high", "low", "close", "vwap"):
            source_valid &= (
                pl.when(traded).then(pl.col(field) > 0).otherwise(pl.col(field).is_null())
            )
        for field in ("first_trade_us", "last_trade_us"):
            source_valid &= (
                pl.when(traded)
                .then(
                    pl.col(field).is_between(pl.col("timestamp"), pl.col("close_us"), closed="left")
                )
                .otherwise(pl.col(field).is_null())
            )
        if not frame.select(source_valid.fill_null(False).all()).item():
            raise ValueError("Count/empty/price/trade-time source contract mismatch")
        if (spec.path.stat().st_size, spec.path.stat().st_mtime_ns) != current_stat:
            raise ValueError("Source changed during row-group decoding")
        return frame

    def joint_rows(self, start: int, end: int) -> pl.DataFrame:
        if start < day_us(START) or end > day_us(LOCKED) or start >= end:
            raise ValueError("Requested read would enter locked/nondevelopment dates")
        frames = []
        for stream in STREAMS:
            pieces = [
                self._read(spec, start, end)
                for spec in self.shards
                if spec.stream == stream and spec.start_us < end and spec.end_us > start
            ]
            if not pieces:
                raise ValueError("Missing required declared stream")
            frame = pl.concat(pieces).sort("timestamp")
            frames.append(
                frame.select(
                    "timestamp",
                    *[
                        pl.col(name).alias(f"{stream}__{name}")
                        for name in SOURCE_COLUMNS
                        if name != "timestamp"
                    ],
                )
            )
        joint = frames[0]
        for frame in frames[1:]:
            joint = joint.join(frame, on="timestamp", how="inner", validate="1:1")
        joint = joint.sort("timestamp")
        expected = np.arange(start, end, BAR_US, dtype=np.int64)
        if not np.array_equal(joint["timestamp"].to_numpy(), expected):
            raise ValueError("Missing synchronization interval: no interpolation/asof matching")
        return joint

    def prepare_index(self, path: Path) -> dict:
        """Persist only valid shared decision timestamps, at the fixed 60s stride."""
        path = Path(path)
        if not path.resolve().is_relative_to(STATE.resolve()) or path.exists():
            raise ValueError("Exclusive native STATE endpoint index required")
        chunks, exclusions = [], []
        first = max(
            min(s.start_us for s in self.shards if s.stream == stream) for stream in STREAMS
        )
        last = min(max(s.end_us for s in self.shards if s.stream == stream) for stream in STREAMS)
        for day in self.days:
            lower, upper = (
                max(first, day_us(day) - PAST_BARS * BAR_US),
                min(last, day_us(day) + DAY_US + LABEL_LAG_US),
            )
            if upper - lower <= (PAST_BARS + 62) * BAR_US:
                continue
            try:
                joint = self.joint_rows(lower, upper)
            except ValueError as error:
                if self.mode == "formal" or not str(error).startswith("Missing synchronization"):
                    raise
                exclusions.append({"day": day.isoformat(), "reason": str(error)})
                continue
            features = feature_matrix(joint)
            labels = label_table(joint)
            endpoints = labels.filter(
                pl.col("label_valid")
                & (pl.col("decision_us") % ENDPOINT_STEP_US == 0)
                & pl.col("decision_us").is_between(day_us(day), day_us(day) + DAY_US, closed="left")
                & (pl.col("decision_us") >= first + PAST_BARS * BAR_US)
            )["decision_us"].to_numpy()
            if not np.isfinite(features).all():
                raise ValueError("Common tensor must remain finite")
            chunks.append(endpoints)
        values = np.unique(np.concatenate(chunks)) if chunks else np.array([], dtype=np.int64)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as handle:
            handle.write(values.astype("<i8").tobytes())
        self.index = (
            np.memmap(path, dtype="<i8", mode="r", shape=(len(values),)) if len(values) else values
        )
        return {
            "status": "FORMAL_DATA_READY" if self.mode == "formal" else "SMOKE_ONLY",
            "path": str(path),
            "sha256": file_sha(path),
            "endpoints": len(values),
            "complete_common_days": len(self.complete_days),
            "dataset_sha256": self.contract_sha256,
            "excluded_smoke_intervals": exclusions,
        }

    def __len__(self):
        return 0 if self.index is None else len(self.index)

    def __getitem__(self, index: int) -> dict:
        if self.index is None or not 0 <= index < len(self.index):
            raise IndexError("No such prepared common endpoint")
        decision = int(self.index[index])
        if self.normalizer is not None:
            lower, upper, mature_by = self.fold.interval(self.split)
            if not lower <= decision < upper or decision + LABEL_LAG_US > mature_by:
                raise ValueError("Endpoint outside the bound fold/split or label maturity")
        joint = self.joint_rows(decision - PAST_BARS * BAR_US, decision + LABEL_LAG_US)
        source_available = [f"{stream}__available_us" for stream in STREAMS]
        past = joint.filter(pl.max_horizontal(source_available) <= decision)
        if past.height != PAST_BARS:
            raise ValueError("Current/future/partial bar cannot enter the past256 window")
        labels = label_table(joint).row(PAST_BARS - 1, named=True)
        if not labels["label_valid"]:
            raise ValueError("Prepared common label no longer valid")
        x = feature_matrix(past)
        if self.normalizer is not None:
            if self.split != "train" and self.normalizer.fit_last_us >= decision:
                raise ValueError("Scaler contains current/future inference information")
            x = self.normalizer.transform(x)
        y = np.array([labels[name] for name in LABEL_COLUMNS], dtype=np.float32).reshape(
            len(TARGET_STREAMS), len(TASKS)
        )
        transformed = (
            self.target_normalizer.transform(y).astype(np.float32)
            if (self.target_normalizer is not None)
            else y.copy()
        )
        return {
            "sample_id": _sha((self.contract_sha256, decision)),
            "decision_us": decision,
            "x": x,
            "y": transformed,
            "y_raw": y,
            "target_units": "standardized" if self.target_normalizer else "original",
            "label_available_us": labels["label_available_us"],
            "qa": {
                name: value
                for name, value in labels.items()
                if name not in LABEL_COLUMNS and name not in {"decision_us", "label_valid"}
            },
            "status": "FORMAL_DATA_READY" if self.mode == "formal" else "SMOKE_ONLY",
        }

    def split_indices(self, fold: Fold, split: str) -> np.ndarray:
        if self.index is None:
            raise ValueError("Prepare the common endpoint index first")
        start, end, mature_by = fold.interval(split)
        return np.flatnonzero(
            (self.index >= start) & (self.index < end) & (self.index + LABEL_LAG_US <= mature_by)
        )

    def fit_fold_scaler(self, fold: Fold) -> FoldNormalizer:
        """Reuse sklearn partial_fit on unique train rows, never repeated windows or labels."""
        scaler, count, first, last = StandardScaler(), 0, None, None
        for day in self.days:
            lower = max(day_us(day), fold.train_start_us)
            upper = min(day_us(day) + DAY_US, fold.fit_cutoff_us)
            # Only declared synchronized rows, and their availability, can fit the scaler.
            common_end = min(
                max(s.end_us for s in self.shards if s.stream == stream) for stream in STREAMS
            )
            upper = min(upper, common_end)
            if lower >= upper:
                continue
            joint = self.joint_rows(lower, upper)
            joint = joint.filter(
                pl.max_horizontal([f"{s}__available_us" for s in STREAMS]) <= fold.fit_cutoff_us
            )
            if joint.is_empty():
                continue
            values = feature_matrix(joint)
            scaler.partial_fit(values[:, SCALE_INDICES])
            count += len(values)
            first = int(joint["timestamp"][0] + BAR_US) if first is None else first
            last = int(joint["timestamp"][-1] + BAR_US)
        if count < 2 or last > fold.fit_cutoff_us:
            raise ValueError("Insufficient or future fitting source rows")
        return FoldNormalizer(scaler, self.contract_sha256, fold.name, first, last, count)

    def fit_target_scaler(self, fold: Fold) -> TargetNormalizer:
        if self.index is None:
            raise ValueError("Prepare common endpoints before fitting common target scaler")
        scaler, count, last = StandardScaler(), 0, None
        eligible = self.index[self.split_indices(fold, "train")]
        for day in self.days:
            lower = max(day_us(day), fold.train_start_us)
            common_end = min(
                max(s.end_us for s in self.shards if s.stream == stream) for stream in STREAMS
            )
            upper = min(day_us(day) + DAY_US + LABEL_LAG_US, fold.fit_cutoff_us, common_end)
            if upper - lower <= LABEL_LAG_US:
                continue
            labels = label_table(self.joint_rows(lower, upper)).filter(
                pl.col("label_valid")
                & pl.col("decision_us").is_in(eligible.tolist())
                & (pl.col("label_available_us") <= fold.fit_cutoff_us)
                & pl.col("decision_us").is_between(day_us(day), day_us(day) + DAY_US, closed="left")
            )
            if labels.is_empty():
                continue
            scaler.partial_fit(labels.select(LABEL_COLUMNS).to_numpy())
            count += labels.height
            last = int(labels["label_available_us"].max())
        if count < 2 or last > fold.fit_cutoff_us:
            raise ValueError("Insufficient/missing/future mature train targets")
        return TargetNormalizer(scaler, self.contract_sha256, fold.name, last, count)

    def normalized(
        self, normalizer: FoldNormalizer, fold: Fold, split: str, *, targets: TargetNormalizer
    ):
        if (
            normalizer.dataset_sha256 != self.contract_sha256
            or normalizer.fold_name != fold.name
            or normalizer.fit_last_us > fold.fit_cutoff_us
            or split not in {"train", "validation", "test"}
            or targets.dataset_sha256 != self.contract_sha256
            or targets.fold_name != fold.name
            or targets.fit_last_label_available_us > fold.fit_cutoff_us
        ):
            raise ValueError("Wrong/future/shared cross-fold normalization")
        result = copy.copy(self)
        result.normalizer, result.fold, result.split = normalizer, fold, split
        result.target_normalizer = targets
        return result

    def as_torch_dataset(self):
        """Thin use of the mature PyTorch Dataset/DataLoader interface; no custom loader."""
        from torch.utils.data import Dataset

        source = self

        class TorchView(Dataset):
            def __len__(self):
                return len(source)

            def __getitem__(self, index):
                return source[index]

        return TorchView()
