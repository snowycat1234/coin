"""Causal append rejection tests; no economic fitting."""

import json

import numpy as np
import pytest

from .development_inputs import load_development_inputs
from .exact import sha
from .feature_windows import TRAINING_CUTOFF_US, load_feature_inputs
from .inputs import CORE5, DAY_US, FEATURE_NAMES, MARKET_CONTEXT
from .test_feature_windows import feature_fixture


def fixture(tmp_path, change=None):
    def shift(a, m):
        delta = TRAINING_CUTOFF_US - a["completed_day_available_us"][-1] - DAY_US
        a["raw_observation_us"] += delta
        a["completed_day_available_us"] += delta

    path, metadata, arguments = feature_fixture(tmp_path, mutation=shift)
    arguments["training_cutoff_us"] = TRAINING_CUTOFF_US
    base = load_feature_inputs(path, metadata, **arguments)
    clocks = TRAINING_CUTOFF_US + np.arange(3, dtype=np.int64) * DAY_US
    x = np.ones((3, 5, 24), np.float32)
    a = dict(
        raw_observation_us=clocks - DAY_US,
        completed_day_available_us=clocks,
        x=x,
        feature_observed_mask=np.ones_like(x, bool),
        close=np.ones((3, 5)),
        close_observed_mask=np.ones((3, 5), bool),
        original_price_ready256=np.zeros((3, 5), bool),
        symbol_order=np.array(CORE5),
        feature_order=np.array(FEATURE_NAMES),
        aggregate_context_asset_order=np.array(MARKET_CONTEXT),
    )
    m = dict(
        schema="CAUSAL_CORE5_DAILY_SEQUENCE_DEVELOPMENT_APPEND_V1",
        classification="ALREADY_SEEN_DEVELOPMENT_ONLY_NOT_TRAINING_EXPANSION_NOT_UNTOUCHED_OOS",
        feature_orders=dict(CORE5=list(CORE5), feature_order=list(FEATURE_NAMES)),
        feature_roles=dict(
            contains_future_labels=False, contains_label_conditioned_eligibility=False
        ),
        warmup_reference=dict(
            contains_duplicate_warmup=False, member_SHA256=base.binding["feature_npz_SHA256"]
        ),
        aggregates=dict(asset_order=list(MARKET_CONTEXT), recomputed_as_CORE5_only=False),
        rows=3,
    )
    if change == "gap":
        a["raw_observation_us"] += DAY_US
        a["completed_day_available_us"] += DAY_US
    if change == "wrong_role":
        m["classification"] = "TRAIN"
    if change == "mask_future":
        a["feature_observed_mask"][0] = False
    if change == "aggregate":
        a["aggregate_context_asset_order"] = a["aggregate_context_asset_order"][::-1]
    npz, manifest = tmp_path / "append.npz", tmp_path / "append.json"
    np.savez(npz, **a)
    manifest.write_text(json.dumps(m))
    return (
        base,
        npz,
        manifest,
        dict(expected_npz_sha256=sha(npz), expected_manifest_sha256=sha(manifest)),
    )


def test_append_uses_real_preMay_warmup_and_never_expands_train_dates(tmp_path):
    base, npz, manifest, arguments = fixture(tmp_path)
    dev = load_development_inputs(base, npz, manifest, **arguments)
    windows = dev.windows(dev.decision_us)
    assert len(dev.decision_us) == 3 and np.all(dev.decision_us >= TRAINING_CUTOFF_US)
    np.testing.assert_array_equal(windows.values[0, :-1], base.timeline.values[-63:])
    np.testing.assert_array_equal(windows.valid[0, :-1], base.timeline.valid[-63:])
    assert windows.completed_us[0, -1] == TRAINING_CUTOFF_US
    assert np.all(base.decision_us < TRAINING_CUTOFF_US)


@pytest.mark.parametrize("change", ["gap", "wrong_role", "mask_future", "aggregate"])
def test_append_cannot_change_chronology_roles_or_masks(tmp_path, change):
    base, npz, manifest, arguments = fixture(tmp_path, change)
    with pytest.raises(ValueError):
        load_development_inputs(base, npz, manifest, **arguments)
