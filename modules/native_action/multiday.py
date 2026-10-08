"""Fixed seven-day request values at one continuous native wallet state.

No fitting, historical label CLI, greedy-wallet advancement or financial engine.
Only first-decision state/proposal fields enter X. Later causal contexts and
market observations are used solely to evaluate Y and its maturity clock.
"""

from __future__ import annotations

import time
from copy import deepcopy
from dataclasses import dataclass
from typing import Callable

import numpy as np

from scripts.investment.perpetual_directional import DAY, MINUTE, need

from .availability_contract import scheduled_identity
from .teacher import E6, DayContext, Mapper, causal_features, identity_digest, simplex

SCHEMA = "NATIVE_FIXED_REQUEST_7D_ACTION_VALUES_V1"
HORIZON_DAYS = 7
CONTINUATION_RULE = "HOLD_INITIAL_REQUEST_7D_DAILY_CAUSAL_REMAP"


@dataclass(frozen=True)
class SevenDayEvaluation:
    row: dict
    # Diagnostic endpoints at d+7d, never the next day's live wallet.
    diagnostic_end_states: tuple


def _actions(order):
    order = tuple(order)
    need(order in (E6[:5], E6), "Ordered five or six native requests")
    return order


def _continuation_identity(context):
    identity = scheduled_identity(context.binding)
    identity["market_binding_sha256"] = context.binding["market_binding_sha256"]
    # Without a declared schedule the exact checkpoint is frozen throughout.
    if context.checkpoint_schedule is None:
        identity["rank_checkpoint_sha256"] = context.binding.get("rank_checkpoint_sha256")
    identity["market_feature_names"] = list(context.market_feature_names)
    identity["explicit_action_mask"] = context.action_available is not None
    return identity


def _proposal(mapper, branch, request, context):
    prior = simplex(branch.budget).copy()
    mask = context.action_mask()
    need(np.all(prior[~mask] == 0), "Unavailable expert has residual budget")
    proposal = mapper(prior.copy(), request.copy(), deepcopy(context))
    proposal.validate(prior, len(branch.symbols))
    need(np.array_equal(proposal.request, request), "Mapper preserves fixed request identity")
    need(
        np.all(np.asarray(proposal.budget)[~mask] == 0),
        "Mapper cannot allocate unavailable expert budget",
    )
    return proposal


def _action_features(sim, names, features, proposal):
    """Pre-branch geometry, matching the useful archived action-conditioning idea."""
    prior = simplex(sim.budget)
    positions = np.asarray(
        [features[names.index("wallet." + s + ".signed_weight")] for s in sim.symbols]
    )
    suffix = (
        ["candidate.request." + name for name in E6]
        + ["candidate.delta_budget." + name for name in E6]
        + ["candidate.target." + s for s in sim.symbols]
        + ["candidate.delta_position." + s for s in sim.symbols]
    )
    x = [
        *features,
        *proposal.request,
        *(np.asarray(proposal.budget) - prior),
        *proposal.targets,
        *(np.asarray(proposal.targets) - positions),
    ]
    need(np.isfinite(x).all(), "Finite causal action-conditioned features")
    return names + suffix, [float(v) for v in x]


def evaluate_candidates_7d(
    sim,
    context_at: Callable[[int], DayContext],
    mapper: Mapper,
    *,
    action_order=E6,
    state_role="ACTUAL_PREDECLARED_WALLET_STATE",
    time_limit_seconds=900,
):
    """Fork each available request from the SAME native wallet and hold it 7 days.

    Every UTC decision remaps that request with the branch's ramped budget and
    that day's causally available context. Global terminal policies remain in
    advance_day; an intermediate label end does not liquidate. E5 output uses
    the first five requests of the existing E6 state contract, without padding
    missing labels or modifying any frozen model.

    The source financial/scheduling state is unchanged. Its shared tape retains
    at most seven days so the source can advance ONE day under its independently
    declared policy. Returned endpoint states are diagnostic, not a teacher
    rollout. Do not concatenate best seven-day endpoints as daily decisions.
    """
    order = _actions(action_order)
    need(
        np.isfinite(time_limit_seconds) and 0 < time_limit_seconds <= 900,
        "Bounded seven-day candidate evaluation",
    )
    need(sim.stop is None and sim.cursor < sim.end, "Active native source wallet")
    started = time.monotonic()

    def check_time():
        need(
            time.monotonic() - started < time_limit_seconds,
            "Seven-day candidate wall-clock budget exceeded",
        )

    context = deepcopy(context_at(sim.cursor))
    names, features = causal_features(sim, context)
    prior = simplex(sim.budget).copy()
    source_available = context.action_mask()
    need(
        np.all(prior[~source_available] == 0),
        "Unavailable expert has residual budget; explicit exit adapter required",
    )
    base_hash = sim.state_hash()
    before = float(sim.account.nav())
    end = sim.cursor + HORIZON_DAYS * DAY
    identity = _continuation_identity(context)
    binding = dict(
        continuation_rule=CONTINUATION_RULE,
        horizon_days=HORIZON_DAYS,
        native_state_contract=list(E6),
        action_order=list(order),
        symbol_order=list(sim.symbols),
        context_identity=identity,
        simulator_version=sim.VERSION,
        mode=sim.mode,
        cost=deepcopy(sim.cost),
        funding_unit=deepcopy(sim.unit),
        account_class=type(sim.account).__module__ + "." + type(sim.account).__qualname__,
        persist_cash_close=sim.persist_cash_close,
        final_day_target_zero=sim.final_day_target_zero,
    )
    binding["sha256"] = identity_digest(binding)
    candidates = [
        dict(
            name=name,
            available=bool(source_available[k]),
            valid=False,
            net_increment_USDT=None,
            label_available_us=None,
            features=None,
            days_completed=0,
            daily_trace=[],
            completion="UNAVAILABLE_AT_DECISION_NOT_SIMULATED",
        )
        for k, name in enumerate(order)
    ]
    row = dict(
        schema=SCHEMA,
        decision_us=sim.cursor,
        interval_end_us=end,
        evaluation_end_us=None,
        label_available_us=None,
        horizon_days=HORIZON_DAYS,
        continuation_rule=CONTINUATION_RULE,
        label_binding=binding,
        binding=deepcopy(context.binding),
        feature_available_us=context.available_us,
        feature_names=list(names),
        features=list(features),
        candidate_feature_names=None,
        action_order=list(order),
        symbol_order=list(sim.symbols),
        budget_before=prior.tolist(),
        wallet_before=deepcopy(sim.account.summary()),
        state_hash=base_hash,
        state_role=state_role,
        candidates=candidates,
        action_available=source_available[: len(order)].tolist(),
        valid_mask=[False] * len(order),
        rewards_USDT=[None] * len(order),
        best_evaluable_action=None,
        optimization_allowed=False,
        global_native_upper_bound=False,
        evaluation_scope="FIXED_7D_REQUEST_CONDITIONAL_ON_ONE_SOURCE_WALLET",
        terminal_convention=(
            "FINAL_DAY_ZERO_PLUS_CHARGED_GLOBAL_TERMINAL"
            if sim.final_day_target_zero
            else "CHARGED_GLOBAL_END_MINUS_6_MINUTES"
        ),
        includes_global_terminal=end == sim.end,
    )
    if end > sim.end:
        for c in candidates:
            if c["available"]:
                c["completion"] = "INSUFFICIENT_7D_HORIZON_NOT_SIMULATED"
        row["completion"] = "INSUFFICIENT_7D_HORIZON_NOT_SIMULATED"
        row["elapsed_seconds"] = time.monotonic() - started
        return SevenDayEvaluation(row, (None,) * len(order))

    # Capture ALL initial X before any future context or market reader is touched.
    proposals = {}
    for k, c in enumerate(candidates):
        if not c["available"]:
            continue
        check_time()
        p = _proposal(mapper, sim, np.eye(6)[k], context)
        feature_names, x = _action_features(sim, names, features, p)
        row["candidate_feature_names"] = feature_names
        c.update(
            features=x,
            request=list(p.request),
            budget=list(p.budget),
            targets=list(p.targets),
            origin=p.origin,
            completion="EVALUATING",
        )
        proposals[k] = p

    sim.tape.retain_days(sim.cursor, HORIZON_DAYS)
    branches = [None] * len(order)
    active = set(proposals)
    for k in sorted(active):
        check_time()
        clock = time.monotonic()
        branches[k] = sim.fork()
        candidates[k]["clone_seconds"] = time.monotonic() - clock
    # Day-major order shares each immutable day's stream across all candidates.
    for day in range(HORIZON_DAYS):
        if not active:
            break
        check_time()
        stamp = sim.cursor + day * DAY
        current = context if day == 0 else deepcopy(context_at(stamp))
        for k in sorted(active):
            check_time()
            branch, c = branches[k], candidates[k]
            current.validate(branch)
            need(
                _continuation_identity(current) == identity,
                "Continuation context/mapper/market/checkpoint schedule identity changed",
            )
            mask = current.action_mask()
            if not mask[k] or np.any(simplex(branch.budget)[~mask] != 0):
                c["completion"] = (
                    "REQUEST_UNAVAILABLE_DURING_CONTINUATION"
                    if not mask[k]
                    else "RESIDUAL_UNAVAILABLE_BUDGET_NO_EXIT_DEFINED"
                )
                c["invalid_at_us"] = stamp
                active.remove(k)
                continue
            p = proposals[k] if day == 0 else _proposal(mapper, branch, np.eye(6)[k], current)
            branch.budget = list(p.budget)
            clock = time.monotonic()
            result = branch.advance_day(dict(zip(sim.symbols, p.targets, strict=True)))
            check_time()
            c["replay_seconds"] = c.get("replay_seconds", 0.0) + time.monotonic() - clock
            c["daily_trace"].append(
                dict(
                    decision_us=stamp,
                    context_binding=deepcopy(current.binding),
                    feature_available_us=current.available_us,
                    action_available=mask.tolist(),
                    request=list(p.request),
                    budget=list(p.budget),
                    targets=list(p.targets),
                    applied_targets=[branch.weights[stamp][s] for s in sim.symbols],
                )
            )
            complete = (
                result["completed"]
                and branch.cursor == stamp + DAY
                and branch.rows_written - sim.rows_written == (day + 1) * DAY // MINUTE
            )
            if not complete:
                c["completion"] = branch.completion
                c["invalid_at_us"] = branch.cursor
                active.remove(k)
                continue
            c["days_completed"] += 1

    for k, branch in enumerate(branches):
        if branch is None:
            continue
        c = candidates[k]
        c.update(
            state_after_hash=branch.state_hash(),
            evaluation_end_us=branch.cursor,
            terminal_cash_realized=all(p.quantity == 0 for p in branch.account.positions.values()),
        )
        complete = k in active and branch.cursor == end and c["days_completed"] == HORIZON_DAYS
        if end == sim.end and not c["terminal_cash_realized"]:
            complete = False
            c["completion"] = "GLOBAL_TERMINAL_NOT_REALIZED"
        if complete:
            maturity = max(end, int(branch.account.clock_us))
            for raw in branch.funding_journal[sim.event_cursor :]:
                maturity = max(maturity, int(raw.get("available_us", raw["event_us"])))
            c.update(
                valid=True,
                completion="COMPLETE_7D_FIXED_REQUEST",
                net_increment_USDT=float(branch.account.nav()) - before,
                label_available_us=maturity,
                fees_increment_USDT=float(branch.account.fees - sim.account.fees),
                execution_cost_increment_USDT=float(
                    branch.account.execution_cost - sim.account.execution_cost
                ),
                funding_increment_USDT=float(
                    branch.account.funding_cash - sim.account.funding_cash
                ),
            )
    need(sim.state_hash() == base_hash, "Seven-day replay contaminated source wallet")
    row["valid_mask"] = [c["valid"] for c in candidates]
    row["rewards_USDT"] = [c["net_increment_USDT"] for c in candidates]
    valid = [k for k, c in enumerate(candidates) if c["valid"]]
    if valid:
        row.update(
            evaluation_end_us=end,
            label_available_us=max(candidates[k]["label_available_us"] for k in valid),
            best_evaluable_action=max(valid, key=lambda k: row["rewards_USDT"][k]),
            # Missing later outcomes must not manufacture a hindsight
            # training/action mask. Keep diagnostics, exclude the state.
            optimization_allowed=all(c["valid"] for c in candidates if c["available"]),
        )
    row["completion"] = (
        "COMPLETE_7D_AVAILABLE_CANDIDATES"
        if row["optimization_allowed"]
        else "PARTIAL_OR_UNEVALUABLE_7D_DIAGNOSTIC_ONLY"
    )
    row["elapsed_seconds"] = time.monotonic() - started
    return SevenDayEvaluation(row, tuple(branches))


def purged_chronological_split(
    rows, *, training_start_us, validation_start_us, validation_end_us, asof_us
):
    """Split whole wallet-state rows, including all actions, without any fitting.

    Purge the full seven-day outcome interval AND publication delays. The
    end==validation_start boundary is also purged because it shares a mark with
    validation's decision state. This is a conservative chronological split;
    it does not implement shuffled/CV folds or reuse overlapping future folds.
    """
    need(
        training_start_us < validation_start_us < validation_end_us,
        "Ordered chronological split boundaries",
    )
    train, validation, excluded = [], [], []
    for r in rows:
        need(
            r["schema"] == SCHEMA and r["continuation_rule"] == CONTINUATION_RULE,
            "Exact fixed-seven-day label semantics",
        )
        binding = r["label_binding"]
        need(
            binding["sha256"]
            == identity_digest({k: v for k, v in binding.items() if k != "sha256"})
            and binding["continuation_rule"] == CONTINUATION_RULE
            and binding["horizon_days"] == r["horizon_days"] == HORIZON_DAYS
            and binding["action_order"] == r["action_order"],
            "Exact label continuation/horizon/action binding",
        )
        n = len(_actions(r["action_order"]))
        available, valid = np.asarray(r["action_available"]), np.asarray(r["valid_mask"])
        need(
            available.shape == valid.shape == (n,)
            and np.all((available == 0) | (available == 1))
            and np.all((valid == 0) | (valid == 1))
            and np.all(valid <= available),
            "Explicit distinct decision and evaluation masks",
        )
        rewards = r["rewards_USDT"]
        need(
            len(rewards) == n
            and all(np.isfinite(rewards[k]) if valid[k] else rewards[k] is None for k in range(n)),
            "Valid rewards finite; unavailable or incomplete rewards null, never zero",
        )
        start, end, mature = r["decision_us"], r["interval_end_us"], r["label_available_us"]
        need(r["feature_available_us"] <= start, "First-decision inputs must be causal")
        need(end == start + HORIZON_DAYS * DAY, "Fixed full seven-day outcome interval")
        if not r["optimization_allowed"]:
            excluded.append((r, "UNEVALUABLE_STATE"))
            continue
        need(
            available.any() and np.array_equal(available, valid),
            "Optimize only states with every decision-available candidate evaluated",
        )
        need(
            r["evaluation_end_us"] == end and mature is not None and mature >= end,
            "Label must mature at or after actual seven-day evaluation end",
        )
        if mature > asof_us:
            excluded.append((r, "NOT_MATURE_ASOF"))
        elif training_start_us <= start < validation_start_us:
            if end < validation_start_us and mature < validation_start_us:
                train.append(r)
            else:
                excluded.append((r, "PURGED_7D_INTERVAL_OR_PUBLICATION_OVERLAP"))
        elif validation_start_us <= start < validation_end_us and end <= validation_end_us:
            validation.append(r)
        else:
            excluded.append((r, "OUTSIDE_COMPLETE_SPLIT_INTERVAL"))
    return dict(training=train, validation=validation, excluded=excluded)
