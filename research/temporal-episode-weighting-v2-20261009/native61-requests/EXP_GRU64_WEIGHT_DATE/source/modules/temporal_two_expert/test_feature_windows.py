"""Feature-only tests: no economic Parquets, real-data scalers or training."""

import json
from pathlib import Path

import numpy as np
import pytest
import torch

from .exact import sha
from .feature_windows import load_feature_inputs, publish_window_index
from .inputs import CORE5, DAY_US, FEATURE_NAMES, MARKET_CONTEXT, Standardizer
from .model import Selector


def feature_fixture(tmp_path, *, mutation=None):
    count = 80
    rng = np.random.default_rng(66)
    raw = np.arange(19500, 19500 + count, dtype=np.int64) * DAY_US
    x = rng.normal(0.0, 0.02, (count, 5, 24)).astype(np.float32)
    x[:, :, 18:] = x[:, :1, 18:]
    x[:, :, 4:6] = np.nan
    x[:, :, 17] = np.nan  # Missing funding feature is not an economic availability gate.
    close = np.ones((count, 5)) * 100.0
    close[:10, 2] = np.nan
    observed = np.isfinite(close) & (close > 0)
    arrays = dict(
        raw_observation_us=raw,
        completed_day_available_us=raw + DAY_US,
        x=x,
        feature_observed_mask=np.isfinite(x) & observed[..., None],
        close=close,
        close_observed_mask=observed,
        original_price_ready256=np.zeros_like(observed),
        symbol_order=np.array(CORE5),
        feature_order=np.array(FEATURE_NAMES),
        aggregate_context_asset_order=np.array(MARKET_CONTEXT),
    )
    manifest = dict(
        schema="CAUSAL_CORE5_DAILY_SEQUENCE_DATA_V1",
        rows=count,
        feature_schema=dict(
            dtype="float32",
            shape=[count, 5, 24],
            symbol_order=list(CORE5),
            feature_order=list(FEATURE_NAMES),
        ),
        aggregates=dict(asset_order=list(MARKET_CONTEXT), recomputed_as_CORE5_only=False),
        feature_roles=dict(
            contains_future_labels=False, contains_label_conditioned_eligibility=False
        ),
    )
    if mutation:
        mutation(arrays, manifest)
    path, metadata = tmp_path / "features.npz", tmp_path / "manifest.json"
    np.savez_compressed(path, **arrays)
    metadata.write_text(json.dumps(manifest))
    arguments = dict(
        expected_npz_sha256=sha(path),
        expected_manifest_sha256=sha(metadata),
        source_commit="synthetic_test_fixture",
        training_cutoff_us=int(raw[-1]) + 2 * DAY_US,
    )
    return path, metadata, arguments


def test_observation_clocks_real64_dates_and_ignored_ready256(tmp_path):
    path, metadata, arguments = feature_fixture(tmp_path)
    inputs = load_feature_inputs(path, metadata, **arguments)
    assert len(inputs.decision_us) == 17
    first = inputs.windows(inputs.decision_us[:1])
    assert first.values.shape == (1, 64, 5, 24)
    assert first.completed_us[0, -1] == first.decision_us[0]
    assert not first.valid[..., 4:6].any() and not first.valid[..., 17].any()
    assert first.valid[..., 0].any()  # Missing long history/funding does not erase momentum1.
    assert not first.step_valid[0, :10, 2].any()
    assert np.all(np.isfinite(first.values[first.valid]))
    assert inputs.receipt()["economic_outcomes_or_funding_completeness_used_for_masks"] is False
    # Legacy256 readiness cannot alter any input/window enumeration.
    with np.load(path, allow_pickle=False) as archive:
        arrays = {name: archive[name].copy() for name in archive.files}
    arrays["original_price_ready256"][:] = True
    np.savez_compressed(path, **arrays)
    other = load_feature_inputs(path, metadata, **{**arguments, "expected_npz_sha256": sha(path)})
    np.testing.assert_array_equal(inputs.decision_us, other.decision_us)
    np.testing.assert_array_equal(inputs.timeline.valid, other.timeline.valid)
    np.testing.assert_array_equal(inputs.timeline.values, other.timeline.values)


@pytest.mark.parametrize(
    "change,match",
    [
        ("current_bar_available_early", "bar-start"),
        ("mask_using_label_eligibility", "masks"),
        ("asset_mask_using_ready", "observation"),
        ("recomputed_CORE5_aggregate", "original10"),
        ("future_relative", "future labels"),
        ("eligible_ranker_indices", "future labels"),
        ("aggregate_value_changed", "aggregate columns"),
    ],
)
def test_mistiming_future_fields_or_future_conditioned_masks_reject(tmp_path, change, match):
    def mutate(a, m):
        if change == "current_bar_available_early":
            a["completed_day_available_us"] -= DAY_US
        elif change == "mask_using_label_eligibility":
            a["feature_observed_mask"][70] = False
        elif change == "asset_mask_using_ready":
            a["close_observed_mask"][:] = False
        elif change == "recomputed_CORE5_aggregate":
            m["aggregates"]["recomputed_as_CORE5_only"] = True
        elif change == "future_relative":
            a["relative"] = np.zeros((80, 5, 3), np.float32)
        elif change == "eligible_ranker_indices":
            a["eligible_ranker_indices"] = np.arange(80)
        elif change == "aggregate_value_changed":
            a["x"][10, 2, 18] += 1.0

    path, metadata, arguments = feature_fixture(tmp_path, mutation=mutate)
    with pytest.raises(ValueError, match=match):
        load_feature_inputs(path, metadata, **arguments)


def test_index_roundtrip_exact_identity_no_scaler_and_future_date_reject(tmp_path):
    path, metadata, arguments = feature_fixture(tmp_path)
    inputs = load_feature_inputs(path, metadata, **arguments)
    out = tmp_path / "index"
    receipt = publish_window_index(inputs, out)
    assert receipt["normalization"] == "NOT_FIT_WAIT_FOR_FROZEN_TRAIN_EPISODES"
    assert receipt["window_index_SHA256"] == sha(out / "WINDOW_INDEX.npz")
    with np.load(out / "WINDOW_INDEX.npz", allow_pickle=False) as index:
        np.testing.assert_array_equal(index["decision_us"], inputs.decision_us)
        assert np.all(index["end_row"] - index["start_row"] == 63)
        assert index["input_identity"].item() == inputs.identity
    assert json.loads((out / "INPUT_READY.json").read_text())["input_identity"] == inputs.identity
    with pytest.raises(ValueError, match="pre-cutoff"):
        inputs.windows(np.array([arguments["training_cutoff_us"]], dtype=np.int64))
    with pytest.raises(FileExistsError):
        publish_window_index(inputs, out)


def test_payload_identity_change_rejects_and_never_opens_economic_files(tmp_path, monkeypatch):
    path, metadata, arguments = feature_fixture(tmp_path)
    original = Path.read_bytes
    opened = []

    def only_features(self):
        opened.append(self.name)
        assert "parquet" not in self.name.lower() and "economic" not in self.name.lower()
        return original(self)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", only_features)
        load_feature_inputs(path, metadata, **arguments)
    assert opened == [path.name, metadata.name]
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="Exact feature"):
        load_feature_inputs(path, metadata, **arguments)


def test_named_output_set_is_bound_current_pair_only():
    # An inspection scaler only; no scaler fitting or economic optimizer updates.
    scaler = Standardizer(
        np.zeros(24),
        np.ones(24),
        np.ones(24, dtype=np.int64),
        dict(role="architecture_inspection_only"),
    )
    normal = Selector(scaler, cash_enabled=True).eval()
    reversed_pool = Selector(
        scaler, cash_enabled=True, fixed_expert_set=("CSMOM21", "VOL_MANAGED_HOLD")
    ).eval()
    assert normal.parameter_count == reversed_pool.parameter_count == 13090
    assert normal.contract["fixed_expert_set"] == ["VOL_MANAGED_HOLD", "CSMOM21"]
    # Same named mixture under the inverse reference logit, without new actions.
    with torch.no_grad():
        reversed_pool.w_head.weight.neg_()
        reversed_pool.w_head.bias.neg_()
    x = torch.zeros((2, 64, 5, 24), dtype=torch.float64)
    mask = torch.ones_like(x, dtype=torch.bool)
    step = torch.ones((2, 64, 5), dtype=torch.bool)
    torch.testing.assert_close(
        normal(x, mask, step), reversed_pool(x, mask, step), rtol=0, atol=1e-15
    )
    for pool in (("VOL_MANAGED_HOLD", "DONCHIAN_EXIT10"), ("CSMOM21", "UNVERIFIED")):
        with pytest.raises(ValueError, match="verified frozen"):
            Selector(scaler, fixed_expert_set=pool)
