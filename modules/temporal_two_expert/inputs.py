"""Named causal feature windows, with real calendar rows and train-only scaling.

The producer supplies the existing collector feature_frame + market_features
outputs. This module never loads labels, downloads data, or invents warmup.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

DAY_US = 86_400_000_000
CORE5 = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")
FEATURE_NAMES = (
    "mom1",
    "mom5",
    "mom20",
    "mom60",
    "mom120",
    "mom200",
    "vol10",
    "vol30",
    "vol60",
    "vol200",
    "dist20",
    "dist50",
    "dist100",
    "dist200",
    "range",
    "vol_z",
    "premium",
    "funding",
    "breadth1",
    "breadth5",
    "breadth20",
    "breadth60",
    "dispersion20",
    "market_vol20",
)
LOOKBACK = 64


def digest(record):
    return hashlib.sha256(
        json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def array_digest(value):
    a = np.ascontiguousarray(value)
    return digest(
        dict(
            dtype=a.dtype.str,
            shape=list(a.shape),
            bytes_SHA256=hashlib.sha256(a.tobytes()).hexdigest(),
        )
    )


def require_sha(value):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError("Explicit SHA256 identity required")
    return value


def _copy(value, dtype=None):
    result = np.array(value, dtype=dtype, copy=True)
    result.flags.writeable = False
    return result


def _clock(value, shape):
    a = np.asarray(value)
    if a.shape != shape or a.dtype.kind not in "iu" or np.any(a < 0):
        raise ValueError("Explicit integer microsecond clocks required")
    return a


@dataclass(frozen=True)
class FeatureTimeline:
    values: np.ndarray  # calendar day, CORE5, named24
    valid: np.ndarray  # per-feature validity; missing is not zero
    step_valid: np.ndarray  # completed asset observation on each real day
    completed_us: np.ndarray  # end of completed daily bar, not bar start
    available_us: np.ndarray  # per-feature causal availability clock
    source_sha256: str  # producer's verified source/input manifest
    symbol_order: tuple = CORE5
    feature_names: tuple = FEATURE_NAMES

    def __post_init__(self):
        x, mask, step = map(np.asarray, (self.values, self.valid, self.step_valid))
        if x.ndim != 3 or x.shape[1:] != (5, 24) or x.dtype.kind != "f":
            raise ValueError("Floating daily CORE5 x named24 features required")
        if (
            mask.shape != x.shape
            or mask.dtype != bool
            or step.shape != x.shape[:2]
            or step.dtype != bool
        ):
            raise ValueError("Explicit boolean feature and time masks required")
        if tuple(self.symbol_order) != CORE5 or tuple(self.feature_names) != FEATURE_NAMES:
            raise ValueError("Exact CORE5 and existing24 feature order required")
        clocks = _clock(self.completed_us, (len(x),))
        availability = _clock(self.available_us, x.shape)
        if not len(x) or np.any(clocks % DAY_US) or np.any(np.diff(clocks) != DAY_US):
            raise ValueError("Real consecutive daily rows required; represent gaps with masks")
        if (
            np.any(mask & ~step[..., None])
            or not np.isfinite(x[mask]).all()
            or np.any(availability[mask] > np.broadcast_to(clocks[:, None, None], x.shape)[mask])
        ):
            raise ValueError("Every valid feature must be finite, observed and causally available")
        require_sha(self.source_sha256)
        for name in ("values", "valid", "step_valid", "completed_us", "available_us"):
            object.__setattr__(self, name, _copy(getattr(self, name)))

    def windows(self, decision_us):
        decisions = np.asarray(decision_us)
        _clock(decisions, (len(decisions),))
        if not len(decisions) or np.any(decisions % DAY_US) or np.any(np.diff(decisions) <= 0):
            raise ValueError("Ordered unique daily decision clocks required")
        ends = np.searchsorted(self.completed_us, decisions)
        if (
            np.any(ends >= len(self.values))
            or not np.array_equal(self.completed_us[ends], decisions)
            or np.any(ends < LOOKBACK - 1)
        ):
            raise ValueError("Each decision requires 64 real completed daily steps; no padding")
        indices = ends[:, None] - np.arange(LOOKBACK - 1, -1, -1)[None, :]
        return WindowBatch(
            self.values[indices],
            self.valid[indices],
            self.step_valid[indices],
            self.completed_us[indices],
            self.available_us[indices],
            decisions,
            self.source_sha256,
        )


@dataclass(frozen=True)
class WindowBatch:
    values: np.ndarray
    valid: np.ndarray
    step_valid: np.ndarray
    completed_us: np.ndarray
    available_us: np.ndarray
    decision_us: np.ndarray
    source_sha256: str

    def __post_init__(self):
        x = np.asarray(self.values)
        mask, step = np.asarray(self.valid), np.asarray(self.step_valid)
        if x.ndim != 4 or x.shape[1:] != (LOOKBACK, 5, 24) or x.dtype.kind != "f":
            raise ValueError("Batch x real64 x CORE5 x named24 required")
        if (
            mask.shape != x.shape
            or mask.dtype != bool
            or step.shape != x.shape[:-1]
            or step.dtype != bool
        ):
            raise ValueError("Explicit boolean feature and time masks required")
        completed = _clock(self.completed_us, x.shape[:2])
        available = _clock(self.available_us, x.shape)
        decisions = _clock(self.decision_us, (len(x),))
        if (
            not len(x)
            or np.any(completed % DAY_US)
            or np.any(decisions % DAY_US)
            or np.any(np.diff(completed, axis=1) != DAY_US)
            or not np.array_equal(completed[:, -1], decisions)
            or np.any(np.diff(decisions) <= 0)
        ):
            raise ValueError("Causal 64-day calendar ending at each unique decision required")
        if (
            np.any(mask & ~step[..., None])
            or not np.isfinite(x[mask]).all()
            or np.any(available[mask] > np.broadcast_to(completed[..., None, None], x.shape)[mask])
        ):
            raise ValueError("Finite observed features available at completed step required")
        require_sha(self.source_sha256)
        for name in (
            "values",
            "valid",
            "step_valid",
            "completed_us",
            "available_us",
            "decision_us",
        ):
            object.__setattr__(self, name, _copy(getattr(self, name)))

    @property
    def identity(self):
        # Invalid numeric slots are placeholders, never observations or identity changes.
        return digest(
            dict(
                source=self.source_sha256,
                symbols=CORE5,
                features=FEATURE_NAMES,
                **{
                    k: array_digest(v)
                    for k, v in dict(
                        values=np.where(self.valid, self.values, 0.0),
                        valid=self.valid,
                        steps=self.step_valid,
                        completed=self.completed_us,
                        available=self.available_us,
                        decisions=self.decision_us,
                    ).items()
                },
            )
        )


@dataclass(frozen=True)
class Standardizer:
    mean: np.ndarray
    scale: np.ndarray
    count: np.ndarray
    provenance: dict

    def __post_init__(self):
        mean, scale, count = map(np.asarray, (self.mean, self.scale, self.count))
        if (
            mean.shape != (24,)
            or scale.shape != (24,)
            or count.shape != (24,)
            or not np.isfinite(mean).all()
            or not np.isfinite(scale).all()
            or np.any(scale <= 0)
            or count.dtype.kind not in "iu"
            or np.any(count <= 0)
        ):
            raise ValueError("Observed train-only named24 mean/scale/count required")
        # Reject unsupported metadata before it enters a checkpoint.
        digest(self.provenance)
        for name in ("mean", "scale", "count"):
            object.__setattr__(self, name, _copy(getattr(self, name)))

    @property
    def identity(self):
        return digest(
            dict(
                mean=array_digest(self.mean),
                scale=array_digest(self.scale),
                count=array_digest(self.count),
                provenance=self.provenance,
            )
        )


def load_feature_npz(path, *, expected_sha256):
    """Load producer-bound features only; no labels, source stores or downloads."""
    require_sha(expected_sha256)
    path = Path(path)
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256:
        raise ValueError("Exact producer-bound feature archive required")
    fields = {
        "values",
        "valid",
        "step_valid",
        "completed_us",
        "available_us",
        "source_sha256",
        "symbol_order",
        "feature_names",
    }
    with np.load(path, allow_pickle=False) as archive:
        if set(archive.files) != fields:
            raise ValueError("Only explicit named feature timeline fields required")
        arrays = {k: archive[k].copy() for k in fields}
    return FeatureTimeline(
        arrays["values"],
        arrays["valid"],
        arrays["step_valid"],
        arrays["completed_us"],
        arrays["available_us"],
        str(arrays["source_sha256"].item()),
        tuple(arrays["symbol_order"]),
        tuple(arrays["feature_names"]),
    )


def fit_standardizer(training_windows, *, training_cutoff_us):
    """Union of real rows used by training windows, counted once across overlaps.

    Warmup is allowed only before the training cutoff. Validation windows are
    never passed here. Both architectures and cash arms reuse this exact object.
    """
    batches = tuple(training_windows)
    if not batches or type(training_cutoff_us) is not int or training_cutoff_us % DAY_US:
        raise ValueError("Explicit training windows and daily split cutoff required")
    rows = {}
    for batch in batches:
        if np.any(batch.decision_us >= training_cutoff_us):
            raise ValueError("Validation or future rows cannot normalize training")
        for i in range(len(batch.values)):
            for t, clock in enumerate(batch.completed_us[i]):
                row = (
                    np.where(batch.valid[i, t], batch.values[i, t], 0.0),
                    batch.valid[i, t],
                    batch.step_valid[i, t],
                    batch.available_us[i, t],
                )
                key = int(clock)
                if key in rows and any(
                    not np.array_equal(a, b) for a, b in zip(rows[key], row, strict=True)
                ):
                    raise ValueError("Overlapping training histories disagree; no episode splicing")
                rows[key] = row
    values = np.stack([rows[k][0] for k in sorted(rows)])
    valid = np.stack([rows[k][1] for k in sorted(rows)])
    count = valid.sum(axis=(0, 1))
    if np.any(count == 0):
        raise ValueError("Every feature requires an actual training observation")
    mean = np.where(valid, values, 0.0).sum(axis=(0, 1)) / count
    variance = np.where(valid, (values - mean) ** 2, 0.0).sum(axis=(0, 1)) / count
    scale = np.sqrt(variance)
    scale = np.where(scale > 1e-8, scale, 1.0)
    return Standardizer(
        mean,
        scale,
        count,
        dict(
            rule="unique_training_window_rows_valid_only_shared_assets_ddof0_no_clip",
            training_cutoff_us=training_cutoff_us,
            real_row_count=len(rows),
            completed_us_SHA256=array_digest(np.array(sorted(rows), dtype=np.int64)),
            training_window_identities=[b.identity for b in batches],
        ),
    )
