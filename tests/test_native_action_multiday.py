"""Synthetic fixed seven-day labels only; no model fitting or historical data."""

import json
from copy import deepcopy
from dataclasses import replace

import numpy as np
import polars as pl
import pytest
from test_native_action_teacher import context
from test_resumable_perpetual import CORE5, START, synthetic

from modules.native_action.availability_contract import CheckpointSchedule
from modules.native_action.multiday import (
    CONTINUATION_RULE,
    SCHEMA,
    evaluate_candidates_7d,
    purged_chronological_split,
)
from modules.native_action.teacher import E6, identity_digest, linear_ramp_risk_mapper
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as old
from scripts.investment.resumable_perpetual import NativeDailySimulator


def make_sim(days=14, *, streamed=False, mask=None, terminal_zero=False):
    window = synthetic(days)
    consumed = []
    if streamed:
        original = window.pop("market")

        def blocks():
            for d in range(days):
                consumed.append(d)
                sl = slice(d * 1440, (d + 1) * 1440)
                yield dict(
                    times=window["times"][sl],
                    market={s: {k: v[sl] for k, v in data.items()} for s, data in original.items()},
                )

        window["minute_blocks"] = blocks
    sim = NativeDailySimulator(
        window,
        "LONG_SHORT",
        old.COSTS[0],
        old.UNITS[0],
        account_factory=BybitIsolatedAccount,
        persist_cash_close=True,
        final_day_target_zero=terminal_zero,
    )
    sim.budget = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    schedule = CheckpointSchedule(
        []
        if mask is not None and not mask[5]
        else [
            dict(
                start_us=START,
                end_us=START + 40 * old.DAY,
                available_us=START,
                training_label_end_us=START,
                checkpoint_sha256="1" * 64,
            )
        ]
    )

    def context_at(stamp):
        c = context(stamp)
        # Targets vary with each day's information: holding a request is not
        # freezing the day-zero portfolio or continuing a baseline policy.
        targets = c.expert_targets.copy()
        targets[1] *= 1 - 0.02 * ((stamp - START) // old.DAY)
        if mask is None:
            return replace(c, expert_targets=targets)
        targets[np.logical_not(mask)] = np.nan
        clocks = c.expert_available_us.copy()
        clocks[np.logical_not(mask)] += 50 * old.DAY
        return replace(
            c,
            expert_targets=targets,
            expert_available_us=clocks,
            action_available=np.asarray(mask),
            checkpoint_schedule=schedule,
            binding=dict(
                c.binding,
                rank_checkpoint_sha256=schedule.at(stamp) if mask[5] else None,
                rank_checkpoint_schedule_sha256=schedule.sha256,
            ),
        )

    return sim, context_at, consumed


def advance_request(sim, context_at, action):
    c = context_at(sim.cursor)
    c.validate(sim)
    p = linear_ramp_risk_mapper(np.asarray(sim.budget), np.eye(6)[action], c)
    sim.budget = list(p.budget)
    sim.advance_day(dict(zip(sim.symbols, p.targets, strict=True)))


@pytest.fixture(scope="module")
def full_evaluation():
    sim, context_at, consumed = make_sim(streamed=True)
    snapshot = sim.snapshot()
    result = evaluate_candidates_7d(sim, context_at, linear_ramp_risk_mapper)
    return sim, context_at, consumed, snapshot, result


def test_seven_day_labels_keep_same_wallet_and_causal_action_conditioning(full_evaluation):
    sim, _, consumed, snapshot, result = full_evaluation
    row = result.row
    assert sim.snapshot() == snapshot
    assert consumed == list(range(7))
    assert len(sim.tape.retained) == 7
    assert row["valid_mask"] == [True] * 6
    assert row["label_available_us"] == row["evaluation_end_us"] == START + 7 * old.DAY
    assert row["continuation_rule"] == CONTINUATION_RULE and not row["global_native_upper_bound"]
    assert row["optimization_allowed"] and not row["includes_global_terminal"]
    for k, c in enumerate(row["candidates"]):
        assert c["days_completed"] == 7 and len(c["daily_trace"]) == 7
        assert c["request"] == np.eye(6)[k].tolist()
        assert all(t["request"] == c["request"] for t in c["daily_trace"])
        assert all(t["feature_available_us"] <= t["decision_us"] for t in c["daily_trace"])
        assert len(c["features"]) == len(row["candidate_feature_names"])
        assert (
            c["net_increment_USDT"] == float(result.diagnostic_end_states[k].account.nav()) - 10000
        )
    holding = row["candidates"][1]
    assert holding["budget"][1] == pytest.approx(0.05)
    assert holding["daily_trace"][-1]["budget"][1] == pytest.approx(0.35)
    assert holding["targets"] != holding["daily_trace"][-1]["targets"]
    endpoint = result.diagnostic_end_states[1]
    assert endpoint.cursor == START + 7 * old.DAY and not endpoint.terminal
    assert any(p.quantity for p in endpoint.account.positions.values())
    assert endpoint.account.fees > 0 and endpoint.account.funding_cash != 0
    json.dumps(row, allow_nan=False)


def test_two_seven_day_segments_equal_original_continuous_fixed_path(full_evaluation):
    _, _, _, _, first = full_evaluation
    # Action 1 is predeclared here, never chosen from reward/winner information.
    sim, context_at, _ = make_sim()
    prior = np.asarray(sim.budget)
    targets = []
    for stamp in range(START, sim.end, old.DAY):
        p = linear_ramp_risk_mapper(prior, np.eye(6)[1], context_at(stamp))
        prior = np.asarray(p.budget)
        targets.extend(
            dict(available_us=stamp, symbol=s, target_weight=w)
            for s, w in zip(CORE5, p.targets, strict=True)
        )
    full = old.simulate(
        sim.window,
        "LONG_SHORT",
        old.COSTS[0],
        old.UNITS[0],
        target_factory=lambda *_: (pl.DataFrame(targets), {"source": "SYNTHETIC_FIXED_PATH"}),
        account_factory=BybitIsolatedAccount,
        persist_cash_close=True,
    )
    # Recovery supplies an independent tape for this separate fixed-path test;
    # the shared fixture's source must remain able to consume its first day.
    segment1 = NativeDailySimulator.from_snapshot(
        first.diagnostic_end_states[1].snapshot(), sim.window, account_class=BybitIsolatedAccount
    )
    second = evaluate_candidates_7d(
        segment1, context_at, linear_ramp_risk_mapper, action_order=E6[:5]
    )
    segmented = second.diagnostic_end_states[1]
    assert second.row["includes_global_terminal"] and second.row["valid_mask"] == [True] * 5
    assert second.row["label_available_us"] == START + 14 * old.DAY
    direct, direct_context, _ = make_sim()
    while direct.cursor < direct.end:
        advance_request(direct, direct_context, 1)
    assert segmented.snapshot() == direct.snapshot()
    assert segmented.result()["minute"].equals(full["minute"])
    for key in ("trades", "funding", "rejections", "breaches", "extrema", "liquidations"):
        assert segmented.result()[key] == full[key], key
    assert all(p.quantity == 0 for p in segmented.account.positions.values())
    assert segmented.terminal and segmented.account.fees > segment1.account.fees


def test_forks_isolate_endpoint_mutations_and_source_can_still_advance(full_evaluation):
    sim, context_at, consumed, snapshot, result = full_evaluation
    a = result.diagnostic_end_states[1].fork()
    b = result.diagnostic_end_states[2]
    b_snapshot = b.snapshot()
    a.account.trades[0]["side"] = "MUTATED_ONLY_A"
    a.budget[1] = 999
    a.pending.clear()
    assert sim.snapshot() == snapshot and b.snapshot() == b_snapshot
    source = sim.fork()
    advance_request(source, context_at, 1)
    assert source.cursor == START + old.DAY and consumed == list(range(7))
    assert source.minute_chunks[0] is not result.diagnostic_end_states[1].minute_chunks[0]
    assert np.array_equal(source.minute_chunks[0], result.diagnostic_end_states[1].minute_chunks[0])
    with pytest.raises(TypeError):
        source.tape.retained[START][0][1][CORE5[0]]["open"] = 0


def test_first_features_ignore_later_prices_targets_and_rewards():
    mask = [1, 1, 0, 0, 0, 0]
    a, ca, _ = make_sim(8, mask=mask)
    b, cb, _ = make_sim(8, mask=mask)
    for values in b.window["market"].values():
        for key in ("mark", "open", "close"):
            values[key][1440:] *= 1.05
    for raw in b.window["events"]:
        if raw["event_us"] >= START + old.DAY:
            raw["raw_rate"] *= 2

    def changed(stamp):
        c = cb(stamp)
        if stamp == START:
            return c
        targets = c.expert_targets.copy()
        targets[1] *= 0.25
        return replace(c, market_features=(0.9, 0.8), expert_targets=targets)

    ra = evaluate_candidates_7d(a, ca, linear_ramp_risk_mapper).row
    rb = evaluate_candidates_7d(b, changed, linear_ramp_risk_mapper).row
    assert ra["feature_names"] == rb["feature_names"] and ra["features"] == rb["features"]
    assert ra["candidates"][0]["features"] == rb["candidates"][0]["features"]
    assert ra["candidates"][1]["features"] == rb["candidates"][1]["features"]
    assert ra["rewards_USDT"][1] != rb["rewards_USDT"][1]
    assert (
        ra["candidates"][1]["daily_trace"][1]["targets"]
        != rb["candidates"][1]["daily_trace"][1]["targets"]
    )
    assert ra["rewards_USDT"][2:] == [None] * 4
    names = ra["candidate_feature_names"]
    assert not any("daily_trace" in n or "applied_target" in n or "reward" in n for n in names)


@pytest.mark.parametrize("days", [6, 7])
def test_short_horizon_and_charged_true_terminal(days, monkeypatch):
    sim, context_at, _ = make_sim(days, mask=[1, 1, 0, 0, 0, 0], terminal_zero=True)
    if days == 6:
        monkeypatch.setattr(sim, "fork", lambda: pytest.fail("Short horizon must not replay"))
    row = evaluate_candidates_7d(sim, context_at, linear_ramp_risk_mapper).row
    if days == 6:
        assert row["rewards_USDT"] == [None] * 6 and row["label_available_us"] is None
        assert row["completion"] == "INSUFFICIENT_7D_HORIZON_NOT_SIMULATED"
        assert not row["optimization_allowed"]
    else:
        assert row["valid_mask"] == [True, True, False, False, False, False]
        c = row["candidates"][1]
        assert c["daily_trace"][-1]["applied_targets"] == [0.0] * 5
        assert c["terminal_cash_realized"] and c["fees_increment_USDT"] > 0
        assert row["label_available_us"] == sim.end


def test_five_output_missing_rank_and_future_loss_of_availability():
    sim, context_at, _ = make_sim(8, mask=[1, 1, 0, 0, 0, 0])
    called = []

    def mapper(prior, request, c):
        called.append((c.decision_us, int(request.argmax())))
        return linear_ramp_risk_mapper(prior, request, c)

    def later_missing(stamp):
        c = context_at(stamp)
        if stamp == START:
            return c
        mask = [1, 0, 0, 0, 0, 0]
        targets = c.expert_targets.copy()
        targets[1] = np.nan
        return replace(c, action_available=np.asarray(mask), expert_targets=targets)

    row = evaluate_candidates_7d(sim, later_missing, mapper, action_order=E6[:5]).row
    assert row["action_order"] == list(E6[:5]) and len(row["rewards_USDT"]) == 5
    assert row["action_available"] == [True, True, False, False, False]
    assert row["valid_mask"] == [True, False, False, False, False]
    assert row["rewards_USDT"] == [0.0, None, None, None, None]
    assert row["candidates"][1]["completion"] == "REQUEST_UNAVAILABLE_DURING_CONTINUATION"
    assert row["candidates"][1]["days_completed"] == 1
    assert not row["optimization_allowed"]  # Future missingness cannot pick a training winner.
    assert all(k in (0, 1) for _, k in called)
    assert all(k == 0 for stamp, k in called if stamp > START)
    assert row["candidates"][2]["features"] is None


def test_pending_close_survives_intermediate_label_boundary():
    sim, context_at, _ = make_sim(9, mask=[1, 1, 0, 0, 0, 0])
    for values in sim.window["market"].values():
        values["quote_volume"][1439:] = 0.0
    advance_request(sim, context_at, 1)
    sim.budget = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    source_snapshot = sim.snapshot()
    evaluation = evaluate_candidates_7d(sim, context_at, linear_ramp_risk_mapper)
    branch = evaluation.diagnostic_end_states[0]
    assert sim.snapshot() == source_snapshot
    assert branch.cursor == START + 8 * old.DAY and not branch.terminal
    assert branch.pending and any(o["attempts"] > 5 for o in branch.pending.values())
    assert any(p.quantity for p in branch.account.positions.values())
    assert evaluation.row["valid_mask"][0]
    # Same cost, retry and funding semantics in the independent daily scheduler.
    direct, dc, _ = make_sim(9, mask=[1, 1, 0, 0, 0, 0])
    for values in direct.window["market"].values():
        values["quote_volume"][1439:] = 0.0
    advance_request(direct, dc, 1)
    direct.budget = [1.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    for _ in range(7):
        advance_request(direct, dc, 0)
    assert branch.snapshot() == direct.snapshot()


@pytest.mark.parametrize("change", ["future_clock", "mapper", "request"])
def test_daily_causality_continuation_identity_and_request_are_bound(change):
    sim, context_at, _ = make_sim(8, mask=[1, 0, 0, 0, 0, 0])
    snapshot = sim.snapshot()

    def bad_context(stamp):
        c = context_at(stamp)
        if stamp > START and change == "future_clock":
            return replace(c, available_us=stamp + 1)
        if stamp > START and change == "mapper":
            return replace(c, binding=dict(c.binding, mapper_sha256="a" * 64))
        return c

    def bad_mapper(prior, request, c):
        p = linear_ramp_risk_mapper(prior, request, c)
        return replace(p, request=tuple(np.eye(6)[1])) if change == "request" else p

    match = {
        "future_clock": "available",
        "mapper": "identity changed",
        "request": "fixed request identity",
    }[change]
    with pytest.raises(ValueError, match=match):
        evaluate_candidates_7d(sim, bad_context, bad_mapper)
    assert sim.snapshot() == snapshot


def test_label_maturity_includes_funding_publication_delay():
    sim, context_at, _ = make_sim(8, mask=[1, 0, 0, 0, 0, 0])
    sim.window["events"][0]["available_us"] = START + 7 * old.DAY + 123
    row = evaluate_candidates_7d(sim, context_at, linear_ramp_risk_mapper).row
    assert row["evaluation_end_us"] == START + 7 * old.DAY
    assert row["label_available_us"] == row["evaluation_end_us"] + 123


def test_purge_covers_full_seven_days_and_delayed_maturity():
    # Clock-only split fixtures: no reward computation or model fit.
    binding = dict(continuation_rule=CONTINUATION_RULE, horizon_days=7, action_order=list(E6))
    binding["sha256"] = identity_digest(binding)
    rows = [
        dict(
            schema=SCHEMA,
            continuation_rule=CONTINUATION_RULE,
            label_binding=deepcopy(binding),
            action_order=list(E6),
            horizon_days=7,
            action_available=[True] * 6,
            valid_mask=[True] * 6,
            rewards_USDT=[-1.0] * 6,
            feature_available_us=START + i * old.DAY,
            decision_us=START + i * old.DAY,
            interval_end_us=START + (i + 7) * old.DAY,
            evaluation_end_us=START + (i + 7) * old.DAY,
            label_available_us=START + (i + 7) * old.DAY,
            optimization_allowed=True,
        )
        for i in range(20)
    ]
    rows[0]["label_available_us"] = START + 11 * old.DAY
    split = purged_chronological_split(
        rows,
        training_start_us=START,
        validation_start_us=START + 10 * old.DAY,
        validation_end_us=START + 20 * old.DAY,
        asof_us=START + 20 * old.DAY,
    )
    assert [r["decision_us"] for r in split["training"]] == [START + old.DAY, START + 2 * old.DAY]
    assert len(split["validation"]) == 4  # Full 7d outcomes within validation end.
    purged = [r for r, reason in split["excluded"] if reason.startswith("PURGED")]
    assert [r["decision_us"] for r in purged] == [START] + [
        START + i * old.DAY for i in range(3, 10)
    ]
    bad = deepcopy(rows[1])
    bad["label_available_us"] -= old.DAY
    with pytest.raises(ValueError, match="actual seven-day evaluation"):
        purged_chronological_split(
            [bad],
            training_start_us=START,
            validation_start_us=START + 10 * old.DAY,
            validation_end_us=START + 20 * old.DAY,
            asof_us=START + 20 * old.DAY,
        )


def test_overlapping_label_windows_roll_bounded_stream_cache():
    sim, context_at, consumed = make_sim(9, streamed=True, mask=[1, 0, 0, 0, 0, 0])
    evaluate_candidates_7d(sim, context_at, linear_ramp_risk_mapper)
    advance_request(sim, context_at, 0)
    snapshot = sim.snapshot()
    row = evaluate_candidates_7d(sim, context_at, linear_ramp_risk_mapper).row
    assert sim.snapshot() == snapshot
    assert row["label_available_us"] == START + 8 * old.DAY
    assert consumed == list(range(8))  # No reread of any streaming market block.
    assert len(sim.tape.retained) == 7 and START not in sim.tape.retained
    advance_request(sim, context_at, 0)
    assert consumed == list(range(8))
    with pytest.raises(ValueError, match="rewind discarded"):
        sim.tape.retain_days(START, 7)


def test_residual_unavailable_budget_and_failed_global_exit_have_null_rewards():
    sim, context_at, _ = make_sim(8, mask=[1, 1, 0, 0, 0, 0])
    sim.budget = [0.0, 1.0, 0.0, 0.0, 0.0, 0.0]

    def lost(stamp):
        c = context_at(stamp)
        if stamp == START:
            return c
        targets = c.expert_targets.copy()
        targets[1] = np.nan
        return replace(c, expert_targets=targets, action_available=np.asarray([1, 0, 0, 0, 0, 0]))

    row = evaluate_candidates_7d(sim, lost, linear_ramp_risk_mapper).row
    assert row["candidates"][0]["completion"] == "RESIDUAL_UNAVAILABLE_BUDGET_NO_EXIT_DEFINED"
    assert row["rewards_USDT"] == [None] * 6 and not row["optimization_allowed"]

    sim, context_at, _ = make_sim(8, mask=[1, 0, 0, 0, 0, 0])
    # First create real holdings before the seven-day CASH label begins.
    c = context(sim.cursor)
    p = linear_ramp_risk_mapper(np.asarray(sim.budget), np.eye(6)[1], c)
    for values in sim.window["market"].values():
        values["quote_volume"][1439:] = 0.0
    sim.advance_day(dict(zip(sim.symbols, p.targets, strict=True)))
    row = evaluate_candidates_7d(sim, context_at, linear_ramp_risk_mapper).row
    assert row["includes_global_terminal"]
    assert row["candidates"][0]["completion"] == "GLOBAL_TERMINAL_NOT_REALIZED"
    assert row["rewards_USDT"][0] is None and not row["optimization_allowed"]


def test_purge_rejects_changed_continuation_binding(full_evaluation):
    row = deepcopy(full_evaluation[-1].row)
    row["label_binding"]["continuation_rule"] = "FIRST_DAY_THEN_BASELINE"
    with pytest.raises(ValueError, match="continuation/horizon/action binding"):
        purged_chronological_split(
            [row],
            training_start_us=START,
            validation_start_us=START + 10 * old.DAY,
            validation_end_us=START + 20 * old.DAY,
            asof_us=START + 20 * old.DAY,
        )
