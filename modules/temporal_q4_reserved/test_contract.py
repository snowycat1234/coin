from dataclasses import replace

import numpy as np
import pandas as pd
import pytest
import torch

from modules.temporal_expert_input.inputs import expose_episode
from modules.temporal_july_transfer.data import build_features
from modules.temporal_risk_proxy_v2.proxy import BoundaryPlan
from modules.temporal_short_expansion.adapter import append_episode, compress
from modules.temporal_two_expert.inputs import DAY_US, MARKET_CONTEXT, FeatureTimeline
from modules.temporal_two_expert.training_packet import named_context

from .data import END, EXECUTION_DELAY_US, START, TerminalEpisode
from .reconcile import reconcile
from .terminal import charged_terminal_path


def test_original_builder_future_suffix_missing_step_and_real64():
    dt = pd.date_range("2022-01-01", periods=400, tz="UTC")
    frames = {}
    for i, s in enumerate(MARKET_CONTEXT):
        close = 100 + i + np.arange(400) * 0.1 + np.sin(np.arange(400))
        frames[s] = pd.DataFrame(
            dict(
                dt=dt,
                symbol=s,
                close=close,
                high=close + 1,
                low=close - 1,
                quote_volume=1000 + np.arange(400),
                premium=0.001,
                funding=0.0001,
                complete_kline=True,
                complete_premium=True,
                complete_funding=True,
            )
        )
    cut = int(dt[300].value // 1000)
    expected = build_features(frames, end_us=cut)
    changed = {s: f.copy() for s, f in frames.items()}
    for f in changed.values():
        future = pd.DatetimeIndex(f.dt).as_unit("us").asi8 + DAY_US > cut
        for name in ("close", "high", "low", "quote_volume", "premium", "funding"):
            f.loc[future, name] = 1e8
    for a, b in zip(expected, build_features(changed, end_us=cut), strict=True):
        np.testing.assert_array_equal(a, b)
    changed[MARKET_CONTEXT[0]].loc[299, "complete_kline"] = False
    clocks, x, valid, steps, _ = build_features(changed, end_us=cut)
    assert not steps[-1, 0] and not valid[-1, 0].any()
    timeline = FeatureTimeline(
        x[-64:],
        valid[-64:],
        steps[-64:],
        clocks[-64:],
        np.broadcast_to(clocks[-64:, None, None], x[-64:].shape),
        "a" * 64,
    )
    windows = timeline.windows(np.array([cut], dtype=np.int64))
    assert windows.values.shape == (1, 64, 5, 24) and not windows.step_valid[0, -1, 0]
    with pytest.raises(ValueError, match="64 real"):
        replace(
            timeline,
            values=timeline.values[-63:],
            valid=timeline.valid[-63:],
            step_valid=timeline.step_valid[-63:],
            completed_us=timeline.completed_us[-63:],
            available_us=timeline.available_us[-63:],
        ).windows(np.array([cut], dtype=np.int64))


def test_complete_real_terminal_context_mapper_and_independent_accounting(prototype):
    decisions = np.arange(START, END, DAY_US, dtype=np.int64)
    clocks = np.arange(START - 63 * DAY_US, END, DAY_US, dtype=np.int64)
    x = np.zeros((155, 5, 24))
    valid = np.ones(x.shape, bool)
    steps = np.ones((155, 5), bool)
    timeline = FeatureTimeline(
        x, valid, steps, clocks, np.broadcast_to(clocks[:, None, None], x.shape), "b" * 64
    )
    rng = np.random.default_rng(19)
    past = rng.normal(0, 0.005, (30, 5))
    target = np.array([[0, 0, 0, 0, 0], [0.15, 0.15, 0, 0, 0], [-0.1, 0, 0.1, 0, 0]])
    contexts = tuple(
        named_context(
            prototype,
            int(t),
            target,
            np.ones(3, bool),
            past,
            np.zeros(13),
            np.full(3, t, dtype=np.int64),
        )
        for t in decisions
    )
    prices = 100 * np.exp(np.arange(92)[:, None] * np.array([[0.001, 0.002, -0.001, 0.001, 0]]))
    coeff = np.full((91, 5), 0.001)
    labels = np.r_[decisions[1:] + EXECUTION_DELAY_US, decisions[-1] + EXECUTION_DELAY_US]
    episode = TerminalEpisode(
        "synthetic_test_only",
        timeline.windows(decisions),
        contexts,
        prices,
        coeff,
        labels,
        START,
        END,
        END + DAY_US,
        "SEEN_VALIDATION",
        "c" * 64,
    )
    expanded = append_episode(
        episode,
        np.zeros((92, 1, 5)),
        np.ones((92, 1), bool),
        decisions[:, None],
        prototype,
        "d" * 64,
    )
    exposed = expose_episode(expanded)
    request = np.tile([0, 0.5, 0, 0, 0.5, 0], (92, 1))
    targets, mapped = prototype.mapped_path(compress(request), expanded.internal.contexts)
    report = charged_terminal_path(
        torch.tensor(targets), prices, coeff, plan=BoundaryPlan.full_fill_diagnostic(92)
    )
    metrics, rows = reconcile(request, exposed, targets, mapped, report)
    assert metrics["decisions"] == 92 and metrics["active_intervals"] == 91
    assert metrics["paid_terminal_cash"] and metrics["terminal_paid_cost"] > 0
    assert len(rows) == 92 and rows[-1]["terminal_paid_flat"]
    assert rows[-1]["price_PnL"] == rows[-1]["funding_PnL"] == 0
    assert exposed.expert_state.shape == (92, 18)
    altered = expanded.expert_targets.copy()
    mask = expanded.eligible.copy()
    mask[:, 1] = False
    altered[:, 1] = np.nan
    masked = expose_episode(replace(expanded, expert_targets=altered, eligible=mask))
    assert np.isfinite(masked.expert_state).all() and not masked.expert_state[:, :5].any()
    with pytest.raises(ValueError, match="no padding"):
        replace(episode, prices=np.vstack((prices, prices[-1:])))
