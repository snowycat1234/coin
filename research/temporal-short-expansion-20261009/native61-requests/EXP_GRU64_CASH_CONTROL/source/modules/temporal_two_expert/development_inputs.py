"""Byte-bound seen-development append using the existing real pre-May warmup."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from .feature_windows import PAYLOAD_FIELDS, TRAINING_CUTOFF_US, FeatureInputs, _sha
from .inputs import CORE5, DAY_US, FEATURE_NAMES, MARKET_CONTEXT, FeatureTimeline, digest

DEVELOPMENT_COMMIT = "e0d3400b23842f11f167a63e7d80856d76501de8"
DEVELOPMENT_SHA = "800e39e53170fc87a279322b61f0f7f7b7a7812759267c58b1d4db948ab3aa8f"
DEVELOPMENT_MANIFEST_SHA = "5fef36b0ffefe28b617678ff8e77fa058163aaf7076eceea29bc94ee96efe879"


def load_development_inputs(
    base,
    npz_path,
    manifest_path,
    *,
    expected_npz_sha256=DEVELOPMENT_SHA,
    expected_manifest_sha256=DEVELOPMENT_MANIFEST_SHA,
):
    if _sha(npz_path) != expected_npz_sha256 or _sha(manifest_path) != expected_manifest_sha256:
        raise ValueError("Exact development feature append bytes required")
    manifest = json.loads(Path(manifest_path).read_text())
    order = manifest.get("feature_orders", {})
    roles = manifest.get("feature_roles", {})
    warmup = manifest.get("warmup_reference", {})
    aggregate = manifest.get("aggregates", {})
    if (
        manifest.get("schema") != "CAUSAL_CORE5_DAILY_SEQUENCE_DEVELOPMENT_APPEND_V1"
        or manifest.get("classification")
        != "ALREADY_SEEN_DEVELOPMENT_ONLY_NOT_TRAINING_EXPANSION_NOT_UNTOUCHED_OOS"
        or order.get("CORE5") != list(CORE5)
        or order.get("feature_order") != list(FEATURE_NAMES)
        or aggregate.get("asset_order") != list(MARKET_CONTEXT)
        or aggregate.get("recomputed_as_CORE5_only") is not False
        or roles.get("contains_future_labels") is not False
        or roles.get("contains_label_conditioned_eligibility") is not False
        or warmup.get("contains_duplicate_warmup") is not False
        or warmup.get("member_SHA256") != base.binding["feature_npz_SHA256"]
    ):
        raise ValueError(
            "Seen-development role and identical causal feature/warmup contract required"
        )
    with np.load(npz_path, allow_pickle=False) as z:
        if set(z.files) != PAYLOAD_FIELDS:
            raise ValueError("Named feature-only append required")
        a = {k: z[k].copy() for k in PAYLOAD_FIELDS - {"original_price_ready256"}}
    x, observed = a["x"], a["close_observed_mask"]
    clocks, raw = a["completed_day_available_us"], a["raw_observation_us"]
    if (
        tuple(a["symbol_order"]) != CORE5
        or tuple(a["feature_order"]) != FEATURE_NAMES
        or tuple(a["aggregate_context_asset_order"]) != MARKET_CONTEXT
        or len(x) != manifest["rows"]
        or x.dtype != np.float32
        or clocks.dtype != np.int64
        or clocks.shape != (len(x),)
        or not np.array_equal(clocks, raw + DAY_US)
        or clocks[0] != base.timeline.completed_us[-1] + DAY_US
        or np.any(clocks < TRAINING_CUTOFF_US)
        or observed.dtype != bool
        or observed.shape != x.shape[:2]
        or not np.array_equal(observed, np.isfinite(a["close"]) & (a["close"] > 0))
    ):
        raise ValueError("Append must be contiguous, causally clocked, and strictly development")
    mask = np.isfinite(x) & observed[..., None]
    if (
        a["feature_observed_mask"].dtype != bool
        or not np.array_equal(mask, a["feature_observed_mask"])
        or not np.array_equal(
            x[:, :, 18:], np.broadcast_to(x[:, :1, 18:], x[:, :, 18:].shape), equal_nan=True
        )
    ):
        raise ValueError(
            "Truthful causal masks and unchanged original ten-asset aggregates required"
        )
    binding = dict(
        base_input_identity=base.identity,
        append_SHA256=expected_npz_sha256,
        manifest_SHA256=expected_manifest_sha256,
        source_commit=DEVELOPMENT_COMMIT,
        role="SEEN_DEVELOPMENT_NOT_TRAINING_OR_UNTOUCHED_OOS",
        warmup="existing_preMay_real_rows_no_gap_overlap_or_padding",
        normalization="reuse_frozen_train_only_scaler",
    )
    combined = np.concatenate((base.timeline.values, x))
    completed = np.concatenate((base.timeline.completed_us, clocks))
    timeline = FeatureTimeline(
        combined,
        np.concatenate((base.timeline.valid, mask)),
        np.concatenate((base.timeline.step_valid, observed)),
        completed,
        np.broadcast_to(completed[:, None, None], combined.shape),
        digest(binding),
    )
    rows = np.arange(len(base.timeline.values), len(completed), dtype=np.int64)
    rows = rows[observed.any(1) & mask.any((1, 2))]
    decisions = completed[rows].copy()
    rows.flags.writeable = False
    decisions.flags.writeable = False
    return FeatureInputs(timeline, binding, decisions, rows)
