"""Feature-only dataset consumer and compact causal window index; never fits.

Only the named NPZ and its feature manifest are opened. Source/economic Parquets,
outcome audits and label-derived eligibility are deliberately outside this API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .inputs import (
    CORE5,
    DAY_US,
    FEATURE_NAMES,
    LOOKBACK,
    MARKET_CONTEXT,
    FeatureTimeline,
    array_digest,
    digest,
    require_sha,
)

SOURCE_COMMIT = "d901f130993b6f00ad6479dcc6a04b77627192b8"
FEATURE_NPZ_SHA256 = "f164dc8986727e12446f4a807aed72382e8fd665ad7eda9ba14590811ebc680c"
FEATURE_MANIFEST_SHA256 = "9ecbc55c21a5eab2b400604bbd7347a6e9b1261f31b4e749364ee292031da464"
TRAINING_CUTOFF_US = 1714521600000000  # 2024-05-01T00:00:00Z, exclusive
PAYLOAD_FIELDS = {
    "raw_observation_us",
    "completed_day_available_us",
    "x",
    "feature_observed_mask",
    "close",
    "close_observed_mask",
    "original_price_ready256",
    "symbol_order",
    "feature_order",
    "aggregate_context_asset_order",
}


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _date(clock):
    return str(np.datetime64(int(clock), "us").astype("datetime64[D]"))


@dataclass(frozen=True)
class FeatureInputs:
    timeline: FeatureTimeline
    binding: dict
    decision_us: np.ndarray
    end_row: np.ndarray  # inclusive completed-day row; start=end-63

    def windows(self, decisions):
        """Materialize only requested feature windows, without economic resets."""
        decisions = np.asarray(decisions)
        if decisions.ndim != 1 or decisions.dtype.kind not in "iu" or not len(decisions):
            raise ValueError("Explicit integer decision clocks required")
        indices = np.searchsorted(self.decision_us, decisions)
        if np.any(indices >= len(self.decision_us)) or not np.array_equal(
            self.decision_us[indices], decisions
        ):
            raise ValueError("Only enumerated pre-cutoff input decisions are available")
        return self.timeline.windows(decisions)

    @property
    def identity(self):
        return digest(
            dict(
                binding=self.binding,
                decisions=array_digest(self.decision_us),
                end_rows=array_digest(self.end_row),
                lookback=LOOKBACK,
            )
        )

    def receipt(self):
        timeline = self.timeline
        rows = self.end_row
        observed = timeline.step_valid.astype(np.int64)
        prefix = np.concatenate((np.zeros((1, 5), np.int64), observed.cumsum(0)), axis=0)
        observed_per_window = prefix[rows + 1] - prefix[rows - LOOKBACK + 1]
        years = np.array([_date(d)[:4] for d in self.decision_us])
        year_counts = {year: int(np.sum(years == year)) for year in np.unique(years)}
        mask = timeline.valid
        return dict(
            schema="TEMPORAL_FEATURE_WINDOW_INDEX_V1",
            status="INPUT_READY_ECONOMIC_EPISODES_PENDING",
            input_identity=self.identity,
            binding=self.binding,
            source_feature_rows=len(timeline.values),
            calendar_64day_windows=len(rows),
            usable_input_decisions=len(rows),
            first_decision=_date(self.decision_us[0]),
            last_decision=_date(self.decision_us[-1]),
            decision_days_by_year=year_counts,
            latest_day_all_CORE5_observed=int(timeline.step_valid[rows].all(1).sum()),
            all64_steps_all_CORE5_observed=int((observed_per_window == LOOKBACK).all(1).sum()),
            latest_day_has_observed_asset_and_feature=int(
                (timeline.step_valid[rows].any(1) & mask[rows].any((1, 2))).sum()
            ),
            feature_valid_observations={
                name: int(mask[:, :, i].sum()) for i, name in enumerate(FEATURE_NAMES)
            },
            validity_rule="finite_feature_AND_causal_current_asset_close_observed",
            date_rule=(
                "64_actual_consecutive_completed_calendar_steps; at_least_one_latest_observation"
            ),
            missing_CORE5_history="retained_with_feature_and_time_masks; no_ready256_gate",
            normalization="NOT_FIT_WAIT_FOR_FROZEN_TRAIN_EPISODES",
            training_episodes="NOT_FROZEN; input_dates_are_not_economic_wallet_intersections",
            economic_outcomes_or_funding_completeness_used_for_masks=False,
            economic_Parquets_opened=False,
            economic_models_fit=0,
            native_wallets=0,
            provider_downloads=0,
            available_at_semantics=(
                "producer_completed_day_boundary_proxy; actual_historical_publication_unknown"
            ),
            classification=(
                "previously_seen_development_inputs; no_native_or_unseen_OOS_certification"
            ),
        )


def load_feature_inputs(
    npz_path,
    manifest_path,
    *,
    expected_npz_sha256=FEATURE_NPZ_SHA256,
    expected_manifest_sha256=FEATURE_MANIFEST_SHA256,
    source_commit=SOURCE_COMMIT,
    training_cutoff_us=TRAINING_CUTOFF_US,
):
    """Verify a feature-only payload and construct masks from observations alone."""
    require_sha(expected_npz_sha256)
    require_sha(expected_manifest_sha256)
    if _sha(npz_path) != expected_npz_sha256 or _sha(manifest_path) != expected_manifest_sha256:
        raise ValueError("Exact feature NPZ and manifest bytes required")
    manifest = json.loads(Path(manifest_path).read_text())
    schema = manifest.get("feature_schema", {})
    aggregates = manifest.get("aggregates", {})
    roles = manifest.get("feature_roles", {})
    if (
        manifest.get("schema") != "CAUSAL_CORE5_DAILY_SEQUENCE_DATA_V1"
        or schema.get("symbol_order") != list(CORE5)
        or schema.get("feature_order") != list(FEATURE_NAMES)
        or aggregates.get("asset_order") != list(MARKET_CONTEXT)
        or aggregates.get("recomputed_as_CORE5_only") is not False
        or roles.get("contains_future_labels") is not False
        or roles.get("contains_label_conditioned_eligibility") is not False
    ):
        raise ValueError(
            "Causal named24 CORE5 features and retained original10 aggregates required"
        )
    with np.load(npz_path, allow_pickle=False) as archive:
        if set(archive.files) != PAYLOAD_FIELDS:
            raise ValueError(
                "Only named feature payload fields allowed; no future labels or outcomes"
            )
        # The legacy ready256 field is allowed in the producer payload but is
        # never read or used to make features, masks, calendar dates or actions.
        arrays = {k: archive[k].copy() for k in PAYLOAD_FIELDS - {"original_price_ready256"}}
    x, close = arrays["x"], arrays["close"]
    observed = arrays["close_observed_mask"]
    raw, available = arrays["raw_observation_us"], arrays["completed_day_available_us"]
    if (
        tuple(arrays["symbol_order"]) != CORE5
        or tuple(arrays["feature_order"]) != FEATURE_NAMES
        or tuple(arrays["aggregate_context_asset_order"]) != MARKET_CONTEXT
        or x.dtype != np.dtype(schema.get("dtype"))
        or list(x.shape) != schema.get("shape")
        or len(x) != manifest.get("rows")
        or close.shape != x.shape[:2]
        or observed.shape != close.shape
        or observed.dtype != bool
        or raw.shape != (len(x),)
        or available.shape != raw.shape
        or raw.dtype.kind not in "iu"
        or available.dtype.kind not in "iu"
        or np.any(raw < 0)
        or np.any(raw > np.iinfo(np.int64).max - DAY_US)
        or not np.array_equal(available, raw + DAY_US)
        or type(training_cutoff_us) is not int
        or training_cutoff_us % DAY_US
        or np.any(available >= training_cutoff_us)
    ):
        raise ValueError(
            "Original schema, bar-start+1day availability and pre-training cutoff required"
        )
    if not np.array_equal(observed, np.isfinite(close) & (close > 0)):
        raise ValueError("Truthful current completed-close observation mask required")
    mask = np.isfinite(x) & observed[..., None]
    if arrays["feature_observed_mask"].dtype != bool or not np.array_equal(
        mask, arrays["feature_observed_mask"]
    ):
        raise ValueError("Feature masks must equal finite values AND causal close observation")
    if not np.array_equal(
        x[:, :, 18:], np.broadcast_to(x[:, :1, 18:], x[:, :, 18:].shape), equal_nan=True
    ):
        raise ValueError("Six unchanged shared original10 aggregate columns required")
    binding = dict(
        source_commit=source_commit,
        feature_npz_SHA256=expected_npz_sha256,
        feature_manifest_SHA256=expected_manifest_sha256,
        feature_schema=schema,
        aggregate_context=list(MARKET_CONTEXT),
        training_cutoff_us=training_cutoff_us,
        raw_observation_clock="daily_bar_start",
        available_clock="raw_observation_us+1day",
        input_mask_uses=["finite x", "causal close_observed_mask"],
        excluded_from_inputs=[
            "original_price_ready256",
            "relative",
            "regime",
            "eligible_ranker_indices",
            "future_economic_completeness",
        ],
        publication_time="completed_day_proxy; actual_historical_time_UNKNOWN",
    )
    timeline = FeatureTimeline(
        x,
        mask,
        observed,
        available,
        np.broadcast_to(available[:, None, None], x.shape),
        digest(binding),
    )
    rows = np.arange(LOOKBACK - 1, len(x), dtype=np.int64)
    # This is an observable input-information criterion only. Missing assets or
    # individual features survive; no wallet/outcome completeness gate is used.
    rows = rows[observed[rows].any(1) & mask[rows].any((1, 2))]
    if not len(rows):
        raise ValueError("No actual64-day input windows with current observed information")
    decisions = available[rows].copy()
    rows.flags.writeable = False
    decisions.flags.writeable = False
    return FeatureInputs(timeline, binding, decisions, rows)


def publish_window_index(inputs, output):
    """Write a compact index and identity, without scalers or expanded data copies."""
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "WINDOW_INDEX.npz"
    with archive.open("xb") as stream:
        np.savez_compressed(
            stream,
            decision_us=inputs.decision_us,
            start_row=inputs.end_row - LOOKBACK + 1,
            end_row=inputs.end_row,
            symbol_order=np.array(CORE5),
            feature_names=np.array(FEATURE_NAMES),
            aggregate_context_asset_order=np.array(MARKET_CONTEXT),
            input_identity=np.array(inputs.identity),
            lookback=np.array(LOOKBACK),
        )
    receipt = inputs.receipt()
    receipt["window_index_SHA256"] = _sha(archive)
    with (output / "INPUT_READY.json").open("x") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feature-npz", required=True)
    parser.add_argument("--feature-manifest", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inputs = load_feature_inputs(args.feature_npz, args.feature_manifest)
    receipt = publish_window_index(inputs, args.output)
    print(
        json.dumps(
            {
                k: receipt[k]
                for k in (
                    "status",
                    "input_identity",
                    "usable_input_decisions",
                    "first_decision",
                    "last_decision",
                    "normalization",
                )
            }
        )
    )


if __name__ == "__main__":
    main()
