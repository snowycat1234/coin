"""Frozen low-complexity allocation of the existing eight BTC intent streams.

Shadow feedback is not invested capital.  The 2022 output rows are explicitly
training placeholders: a scale fitted on all available 2022 feedback must not
be used to claim causal 2022 predictions.  Economic evaluation starts in 2023.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Sequence

import numpy as np


DAY_US = 86_400_000_000
TRAIN_START_US = int(datetime(2022, 1, 1, tzinfo=UTC).timestamp()) * 1_000_000
EVALUATION_START_US = int(datetime(2023, 1, 1, tzinfo=UTC).timestamp()) * 1_000_000
EVALUATION_END_US = int(datetime(2024, 1, 1, tzinfo=UTC).timestamp()) * 1_000_000
NAMES = (
    "CASH", "HOLD", "SMA200_SIGNED", "DONCHIAN20_10", "DC_TWO_SPEED",
    "DC_CONFIRMED_SHORT", "PUBLIC_SMA50_200", "SMA200_SHORT50",
)
FAMILY_BY_STREAM = {
    name: "CASH" if name == "CASH" else "LONG_BETA" if name == "HOLD" else "TREND"
    for name in NAMES
}
ETA = 0.05
SHARE_ALPHA = 0.01
EWMA_HALF_LIFE_DAYS = 30.0
UTILITY_CLIP = 5.0
UNIT_IDS = ("RAW_AS_FRACTION", "RAW_AS_PERCENT")


@dataclass(frozen=True)
class CanonicalLayout:
    """Alias display mapping; all allocation updates occur at canonical level."""

    alias_names: tuple[str, ...]
    stream_ids: tuple[str, ...]
    member_indices: tuple[tuple[int, ...], ...]


def family_prior() -> np.ndarray:
    """Three fixed family budgets; six trend streams share the trend third."""
    return np.asarray([1 / 3 if n in ("CASH", "HOLD") else 1 / 18 for n in NAMES], dtype=np.float64)


def canonicalize_aliases(
    returns: np.ndarray,
    alias_names: Sequence[str],
    stream_ids: Sequence[str],
    *,
    targets: np.ndarray | None = None,
) -> tuple[np.ndarray, CanonicalLayout]:
    """Collapse declared aliases, checking exact equality rather than correlation.

    ``stream_ids`` are registered semantic identities, not identities learned
    by clustering future returns.  Optional targets have shape [T, aliases, I]
    and must also agree for aliases of the same stream.  This prevents two
    different intents with accidentally equal feedback from being merged.
    """
    values = np.asarray(returns, dtype=np.float64)
    aliases, ids = tuple(alias_names), tuple(stream_ids)
    if (values.ndim != 2 or values.shape[1] != len(aliases) or len(aliases) != len(ids)
            or len(set(aliases)) != len(aliases) or set(ids) != set(NAMES)
            or not np.isfinite(values).all() or np.any(values <= -1)):
        raise ValueError("Complete finite canonical eight-stream feedback and unique aliases required")
    intent = None if targets is None else np.asarray(targets, dtype=np.float64)
    if intent is not None and (intent.ndim != 3 or intent.shape[:2] != values.shape
                               or not np.isfinite(intent).all()):
        raise ValueError("Alias targets require finite [time, alias, instrument] values")
    members = tuple(tuple(i for i, identity in enumerate(ids) if identity == name) for name in NAMES)
    selected = []
    for name, group in zip(NAMES, members):
        first = group[0]
        for other in group[1:]:
            if not np.array_equal(values[:, first], values[:, other]):
                raise ValueError("Declared duplicate feedback differs: " + name)
            if intent is not None and not np.array_equal(intent[:, first], intent[:, other]):
                raise ValueError("Declared duplicate intent differs: " + name)
        selected.append(values[:, first])
    return np.column_stack(selected), CanonicalLayout(aliases, ids, members)


def expand_alias_weights(weights: np.ndarray, layout: CanonicalLayout) -> np.ndarray:
    """Split each canonical weight among aliases without increasing its budget."""
    values = np.asarray(weights, dtype=np.float64)
    if values.ndim not in (1, 2) or values.shape[-1] != len(NAMES):
        raise ValueError("Canonical weights must have eight columns")
    if not np.isfinite(values).all() or np.any(values < 0) or not np.allclose(values.sum(axis=-1), 1, atol=1e-14, rtol=0):
        raise ValueError("Finite nonnegative unit-sum canonical weights required")
    result = np.zeros((*values.shape[:-1], len(layout.alias_names)), dtype=np.float64)
    for k, group in enumerate(layout.member_indices):
        result[..., list(group)] = values[..., k, None] / len(group)
    return result


def _probability_vector(values: np.ndarray) -> np.ndarray:
    result = np.asarray(values, dtype=np.float64)
    if (result.ndim != 1 or not len(result) or not np.isfinite(result).all()
            or np.any(result < 0) or not np.isclose(result.sum(), 1, atol=1e-14, rtol=0)):
        raise ValueError("Finite nonnegative unit-sum probability vector required")
    return result


def _softmax(log_values: np.ndarray) -> np.ndarray:
    values = np.asarray(log_values, dtype=np.float64)
    if values.ndim != 1 or np.isnan(values).any() or np.isposinf(values).any() or not np.isfinite(values).any():
        raise ValueError("Finite log scores with at least one supported stream required")
    weights = np.exp(values - np.max(values))
    return weights / weights.sum()


def hedge_step(weights: np.ndarray, utility: np.ndarray, *, eta: float = ETA) -> np.ndarray:
    """One log-space Hedge update, exposed for independent definition tests."""
    weights = _probability_vector(weights)
    utility = np.asarray(utility, dtype=np.float64)
    if utility.shape != weights.shape or not np.isfinite(utility).all() or not np.isfinite(eta) or eta < 0:
        raise ValueError("Finite matching utility and nonnegative eta required")
    log_weights = np.full(weights.shape, -np.inf)
    np.log(weights, out=log_weights, where=weights > 0)
    return _softmax(log_weights + eta * utility)


def fixed_share_step(
    weights: np.ndarray, utility: np.ndarray, prior: np.ndarray,
    *, eta: float = ETA, alpha: float = SHARE_ALPHA,
) -> np.ndarray:
    """Hedge followed by restoration toward the registered family prior."""
    prior = _probability_vector(prior)
    if np.asarray(weights).shape != prior.shape or not np.isfinite(alpha) or not 0 <= alpha <= 1:
        raise ValueError("Matching prior and share alpha in [0,1] required")
    updated = hedge_step(weights, utility, eta=eta)
    result = (1 - alpha) * updated + alpha * prior
    return result / result.sum()


def _clock(values: np.ndarray, name: str) -> np.ndarray:
    array = np.asarray(values)
    if array.ndim != 1 or array.dtype.kind not in "iu" or not len(array):
        raise ValueError(name + " must be a nonempty integer microsecond clock")
    array = array.astype(np.int64, copy=False)
    if np.any(array < 0) or np.any(np.diff(array) != DAY_US):
        raise ValueError(name + " must retain the full consecutive daily calendar")
    return array


def paths(
    returns: np.ndarray, available_at_us: np.ndarray,
    decisions_us: np.ndarray, unit_id: str,
) -> tuple[dict[str, np.ndarray], dict]:
    """Produce registered full-length paths and their frozen causal metadata.

    Columns always follow ``NAMES``.  Feedback is the already-costed continuous
    shadow expert net return; its availability is interval end + 1 microsecond.
    The first 2023 decision consumes 364 mature 2022 intervals, never the return
    ending at that same decision time.  No 2022 output is an economic prediction.
    """
    if unit_id not in UNIT_IDS:
        raise ValueError("Both original unconfirmed funding unit interpretations must be retained")
    feedback, _ = canonicalize_aliases(returns, NAMES, NAMES)
    available = _clock(available_at_us, "Feedback availability")
    decisions = _clock(decisions_us, "Decision timestamps")
    if len(feedback) != len(available) or len(decisions) != len(feedback):
        raise ValueError("The same full 730-day expert feedback/intent calendar is required")
    if (len(decisions) != 730 or decisions[0] != TRAIN_START_US
            or decisions[-1] + DAY_US != EVALUATION_END_US
            or not np.array_equal(available, decisions + DAY_US + 1)):
        raise ValueError("Frozen 2022-2023 daily calendar and end+1us feedback availability required")
    cash_index = NAMES.index("CASH")
    if np.any(feedback[:, cash_index] != 0):
        raise ValueError("The frozen no-position CASH expert has zero shadow net return")
    train = available <= EVALUATION_START_US
    train_count = int(train.sum())
    if train_count != 364:
        raise ValueError("Only the 364 intervals matured by 2023-01-01 may fit scale or static weights")
    noncash = np.arange(len(NAMES)) != cash_index
    training_values = feedback[train][:, noncash]
    rms_normalizer = np.max(np.abs(training_values), axis=0)
    normalized_training = np.zeros_like(training_values)
    np.divide(training_values, rms_normalizer, out=normalized_training, where=rms_normalizer > 0)
    normalized_rms = np.minimum(1.0, np.sqrt(np.mean(np.square(normalized_training), axis=0)))
    train_rms = rms_normalizer * normalized_rms
    scale = max(0.001, float(np.median(train_rms)))
    if not np.isfinite(scale):
        raise ValueError("Finite frozen training-only utility scale required")
    train_log_growth = np.log1p(feedback[train]).sum(axis=0)
    # np.argmax deterministically chooses the first registered identity on ties.
    static_index = int(np.argmax(train_log_growth))
    prior = family_prior()
    names = ("HEDGE", "FIXED_SHARE", "EWMA", "FAMILY_EW", "STATIC_TRAIN_FROZEN", "SMA200_SIGNED", "CASH")
    output = {name: np.tile(prior, (len(decisions), 1)) for name in names}
    output["SMA200_SIGNED"][:] = 0
    output["SMA200_SIGNED"][:, NAMES.index("SMA200_SIGNED")] = 1
    output["CASH"][:] = 0
    output["CASH"][:, cash_index] = 1
    hedge_log_weights = np.log(prior)
    share_weights = prior.copy()
    ewma_score = np.zeros(len(NAMES), dtype=np.float64)
    decay = float(2 ** (-1 / EWMA_HALF_LIFE_DAYS))
    cursor = 0
    consumed_counts = np.zeros(len(decisions), dtype=np.int64)
    max_consumed_available = np.full(len(decisions), -1, dtype=np.int64)
    for i, timestamp in enumerate(decisions):
        if timestamp < EVALUATION_START_US:
            continue
        while cursor < len(available) and available[cursor] <= timestamp:
            # Overflow of the ratio has an unambiguous bounded utility.  This
            # affects allocator feedback only, never an account journal/NAV.
            with np.errstate(over="ignore"):
                utility = np.clip(feedback[cursor] / scale, -UTILITY_CLIP, UTILITY_CLIP)
            hedge_log_weights += ETA * utility
            # A common shift preserves the exact softmax path and finite scores.
            hedge_log_weights -= np.max(hedge_log_weights)
            share_weights = fixed_share_step(share_weights, utility, prior)
            ewma_score = decay * ewma_score + (1 - decay) * utility
            cursor += 1
        output["HEDGE"][i] = _softmax(hedge_log_weights)
        output["FIXED_SHARE"][i] = share_weights
        output["EWMA"][i] = _softmax(np.log(prior) + ewma_score)
        output["STATIC_TRAIN_FROZEN"][i] = 0
        output["STATIC_TRAIN_FROZEN"][i, static_index] = 1
        consumed_counts[i] = cursor
        if cursor:
            max_consumed_available[i] = available[cursor - 1]
    for name, values in output.items():
        if (not np.isfinite(values).all() or np.any(values < 0)
                or not np.allclose(values.sum(axis=1), 1, atol=1e-14, rtol=0)):
            raise ValueError("Invalid registered allocation path: " + name)
    first_evaluation = int(np.searchsorted(decisions, EVALUATION_START_US))
    metadata = {
        "status": "FROZEN_CAUSAL_HISTORICAL_EXPERT_ALLOCATION_NOT_FRESH_OOS",
        "unit_id": unit_id,
        "canonical_names": list(NAMES),
        "family_by_stream": FAMILY_BY_STREAM.copy(),
        "family_prior": {"TREND": 1 / 3, "LONG_BETA": 1 / 3, "CASH": 1 / 3},
        "canonical_prior": prior.tolist(),
        "training_cutoff_available_at_us_inclusive": EVALUATION_START_US,
        "training_feedback_count": train_count,
        "training_noncash_stream_rms": train_rms.tolist(),
        "utility_scale": scale,
        "utility_definition": "CLIP_ALREADY_COSTED_SHADOW_NET_RETURN_DIVIDED_BY_TRAIN_SCALE_TO_MINUS5_PLUS5",
        "financial_losses_and_costs_clipped": False,
        "extra_turnover_cost_debited_from_feedback": False,
        "hedge_eta": ETA,
        "fixed_share_alpha": SHARE_ALPHA,
        "ewma_half_life_days": EWMA_HALF_LIFE_DAYS,
        "ewma_score_initialization": "ZERO; EACH_MATURE_INTERVAL_UPDATES_DECAY_TIMES_SCORE_PLUS_ONE_MINUS_DECAY_TIMES_UTILITY",
        "static_train_frozen_expert": NAMES[static_index],
        "static_action_domain": "REGISTERED_EIGHT_ONE_HOT_CHOICES_INCLUDING_CASH_NOT_CONVEX_OPTIMUM",
        "static_training_log_growth_by_expert": dict(zip(NAMES, train_log_growth.tolist())),
        "static_tie_break": "FIRST_CANONICAL_NAME_IN_FIXED_REGISTERED_ORDER",
        "training_output_role": "2022_PRIOR_PLACEHOLDERS_NOT_ECONOMIC_PREDICTIONS; CONTROL_ONEHOTS_REMAIN_DECLARED_CONTROLS",
        "evaluation_start_us": EVALUATION_START_US,
        "evaluation_end_exclusive_us": EVALUATION_END_US,
        "evaluation_wallet_initial_capital_USDT": 10000,
        "shadow_training_PnL_enters_actual_wallet_capital": False,
        "feedback_available_at": "INTERVAL_END_PLUS_1_MICROSECOND",
        "first_evaluation_matured_feedback_count": int(consumed_counts[first_evaluation]),
        "feedback_consumed_count_by_decision": consumed_counts.tolist(),
        "latest_consumed_available_at_us_by_decision": max_consumed_available.tolist(),
        "complete_minute_dynamic_candidates": ["HEDGE", "FIXED_SHARE"],
        "screen_only_dynamic_controls": ["EWMA"],
        "allocation_update_level": "CANONICAL_STREAM; ALIASES_ONLY_SPLIT_DISPLAY_WEIGHTS",
    }
    return output, metadata
