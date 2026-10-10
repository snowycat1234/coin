"""Causal suffix, missing observations, source identity and accounting tests."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import torch

from modules.temporal_expert_input.gradient import predict_episode
from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_two_expert.checkpoint import model_identity
from modules.temporal_two_expert.inputs import DAY_US, MARKET_CONTEXT, FeatureTimeline

from .data import START, build_features, economics, load
from .evaluate import cost, frozen_model

STATE = Path("/workspace/coin-state/work/temporal-two-expert-20261009")
ECONOMICS = STATE / "july-frozen-transfer/economics"


@pytest.fixture(scope="module")
def actual():
    pa.set_cpu_count(1)
    pa.set_io_thread_count(1)
    if not ECONOMICS.exists():
        pytest.skip("Restore pinned small economics packet first")
    return load(STATE, ECONOMICS)


def test_future_suffix_and_missing_observations_do_not_leak(actual):
    frames = {
        s: pq.read_table(
            STATE
            / f"feature-input/verified/source_tables_not_model_inputs/daily_features/{s}.parquet"
        ).to_pandas()
        for s in MARKET_CONTEXT
    }
    expected = build_features(frames, end_us=START)
    changed = {s: f.copy(deep=True) for s, f in frames.items()}
    for frame in changed.values():
        future = pd.DatetimeIndex(frame.dt).as_unit("us").asi8 + DAY_US > START
        for name in ("open", "high", "low", "close", "quote_volume", "premium", "funding"):
            frame.loc[future, name] = 1e8
    other = build_features(changed, end_us=START)
    for a, b in zip(expected, other, strict=True):
        np.testing.assert_array_equal(a, b)
    frame = changed["BTCUSDT"]
    row = np.flatnonzero(pd.DatetimeIndex(frame.dt).as_unit("us").asi8 + DAY_US == START)[0]
    frame.loc[row, "complete_kline"] = False
    clocks, values, valid, steps, _ = build_features(changed, end_us=START)
    assert clocks[-1] == START and not steps[-1, 0] and not valid[-1, 0].any()
    timeline = FeatureTimeline(
        values[-63:],
        valid[-63:],
        steps[-63:],
        clocks[-63:],
        np.broadcast_to(clocks[-63:, None, None], values[-63:].shape),
        "a" * 64,
    )
    with pytest.raises(ValueError, match="64 real"):
        timeline.windows(np.array([START], dtype=np.int64))


def test_unavailable_targets_are_masked_before_arithmetic(actual):
    episode, _, _, _ = actual
    expanded = episode.original
    targets, eligible = expanded.expert_targets.copy(), expanded.eligible.copy()
    eligible[:, 1] = False
    targets[:, 1] = np.nan
    exposed = expose_episode(replace(expanded, expert_targets=targets, eligible=eligible))
    assert np.isfinite(exposed.expert_state).all()
    assert not exposed.expert_state[:, :5].any()
    assert not exposed.expert_state[:, 15].any()
    np.testing.assert_array_equal(exposed.expert_state[:, 5:15], episode.expert_state[:, 5:15])


def test_exact_frozen_inference_and_serialization_without_optimizer_updates(actual, tmp_path):
    episode, _, scaler, receipt = actual
    model = frozen_model(scaler)
    identity, rng = model_identity(model), torch.get_rng_state().clone()
    with torch.no_grad():
        request = predict_episode(model, episode).numpy()
    assert request.shape == (63, 6) and np.isfinite(request).all()
    assert not request[:, 2:4].any() and not request[~episode.eligible].any()
    np.testing.assert_allclose(request.sum(1), 1, atol=1e-12, rtol=0)
    assert torch.equal(rng, torch.get_rng_state()) and model_identity(model) == identity
    checkpoint = tmp_path / "inference-only.pt"
    torch.save(model.state_dict(), checkpoint)
    other = frozen_model(scaler)
    other.load_state_dict(
        torch.load(checkpoint, map_location="cpu", weights_only=True), strict=True
    )
    with torch.no_grad():
        repeated = predict_episode(other, episode).numpy()
    np.testing.assert_array_equal(request, repeated)
    assert model_identity(other) == identity
    assert receipt["all64_steps_observed"] and receipt["source_feature_parity_rows"] == 1642


def test_economic_clock_and_source_mutation_rejected(actual, tmp_path):
    episode, _, _, _ = actual
    prices, funding, _ = economics(ECONOMICS, episode.windows.decision_us)
    np.testing.assert_array_equal(prices, episode.prices)
    np.testing.assert_array_equal(funding, episode.funding_coeff)
    assert not funding[-1].any() and np.array_equal(prices[-1], prices[-2])
    with pytest.raises(AssertionError):
        economics(ECONOMICS, episode.windows.decision_us + DAY_US)
    (tmp_path / "CONSUMER_INDEX.json").write_bytes(b"altered")
    with pytest.raises(ValueError, match="Exact supplied"):
        economics(tmp_path, episode.windows.decision_us)


def test_signed_costs_charge_paid_exit_and_funding_has_base_units():
    price = np.array([10.0, 20.0])
    quantity = np.array([2.0, -1.0])
    entry = cost(quantity, price)
    exit_cost = cost(-quantity, price)
    assert sum(entry) > 0 and sum(exit_cost) > 0
    np.testing.assert_allclose(np.array(entry) + exit_cost, [0.044, 0.032, 0.032], atol=1e-15)
    # Coefficient is USDT per base unit; opposite held units reverse funding.
    coefficient = np.array([0.01, 0.02])
    assert float(np.array([2.0, 0.0]) @ coefficient) == 0.02
    assert float(np.array([-2.0, 0.0]) @ coefficient) == -0.02


def test_saved_four_wallet_accounting_and_complete_controls(actual):
    from .verify import verify

    receipt = verify(STATE, ECONOMICS, STATE / "july-frozen-transfer/results")
    assert receipt["status"] == "PASS" and receipt["verified_daily_rows"] == 252
    assert receipt["economic_wallets_rerun"] == 0
