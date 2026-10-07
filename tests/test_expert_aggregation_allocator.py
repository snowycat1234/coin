"""Counterexamples for the new causal allocator; no wallet/model reruns."""
import numpy as np
import pytest

from modules.expert_aggregation.allocator import (
    DAY_US, EVALUATION_START_US, NAMES, TRAIN_START_US,
    canonicalize_aliases, expand_alias_weights, family_prior,
    fixed_share_step, hedge_step, paths,
)


def sample():
    decisions = TRAIN_START_US + np.arange(730, dtype=np.int64) * DAY_US
    available = decisions + DAY_US + 1
    day = np.arange(730, dtype=np.float64)
    feedback = np.column_stack([np.zeros(730)] + [
        0.002 * np.sin(day / (8 + k)) + (k - 3) * 0.0001 for k in range(1, 8)
    ])
    return feedback, available, decisions


def test_future_feedback_cannot_change_evaluation_prefix_or_static_weights():
    feedback, available, decisions = sample()
    baseline, meta = paths(feedback, available, decisions, "RAW_AS_FRACTION")
    cut = 510
    changed = feedback.copy()
    changed[available > decisions[cut], 1:] = 0.75
    after, changed_meta = paths(changed, available, decisions, "RAW_AS_FRACTION")
    for name in baseline:
        np.testing.assert_array_equal(baseline[name][:cut + 1], after[name][:cut + 1])
    assert meta["static_train_frozen_expert"] == changed_meta["static_train_frozen_expert"]
    assert meta["utility_scale"] == changed_meta["utility_scale"]
    np.testing.assert_array_equal(baseline["STATIC_TRAIN_FROZEN"], after["STATIC_TRAIN_FROZEN"])


def test_same_interval_feedback_is_not_available_at_its_end_decision():
    feedback, available, decisions = sample()
    baseline, _ = paths(feedback, available, decisions, "RAW_AS_PERCENT")
    interval = 400
    changed = feedback.copy()
    changed[interval, 2] = 0.5
    after, _ = paths(changed, available, decisions, "RAW_AS_PERCENT")
    for name in ("HEDGE", "FIXED_SHARE", "EWMA"):
        np.testing.assert_array_equal(baseline[name][:interval + 2], after[name][:interval + 2])
        assert not np.array_equal(baseline[name][interval + 2], after[name][interval + 2])


def test_training_placeholders_and_boundary_exclusion_match_364_feedbacks():
    feedback, available, decisions = sample()
    output, meta = paths(feedback, available, decisions, "RAW_AS_FRACTION")
    prior = family_prior()
    first = int(np.searchsorted(decisions, EVALUATION_START_US))
    assert first == 365
    for name in ("HEDGE", "FIXED_SHARE", "EWMA", "FAMILY_EW", "STATIC_TRAIN_FROZEN"):
        np.testing.assert_array_equal(output[name][:first], np.tile(prior, (first, 1)))
    assert meta["training_feedback_count"] == meta["first_evaluation_matured_feedback_count"] == 364
    assert meta["feedback_consumed_count_by_decision"][first + 1] == 365
    assert meta["latest_consumed_available_at_us_by_decision"][first] < decisions[first]
    mutated = feedback.copy()
    mutated[364, 1:] = 0.9
    _, mutated_meta = paths(mutated, available, decisions, "RAW_AS_FRACTION")
    assert meta["utility_scale"] == mutated_meta["utility_scale"]
    assert meta["static_train_frozen_expert"] == mutated_meta["static_train_frozen_expert"]


def test_duplicate_and_renamed_aliases_do_not_change_any_canonical_update_or_intent():
    feedback, available, decisions = sample()
    original, _ = paths(feedback, available, decisions, "RAW_AS_FRACTION")
    aliases = (*NAMES, "RENAMED_SMA", "COPY_SMA")
    identities = (*NAMES, "SMA200_SIGNED", "SMA200_SIGNED")
    expanded_feedback = np.column_stack([feedback, feedback[:, 2], feedback[:, 2]])
    canonical, layout = canonicalize_aliases(expanded_feedback, aliases, identities)
    np.testing.assert_array_equal(canonical, feedback)
    duplicate_output, _ = paths(canonical, available, decisions, "RAW_AS_FRACTION")
    targets = np.arange(730 * 8, dtype=np.float64).reshape(730, 8, 1) / 100000
    aliases_targets = np.concatenate([targets, targets[:, 2:3], targets[:, 2:3]], axis=1)
    canonicalize_aliases(expanded_feedback, aliases, identities, targets=aliases_targets)
    for name, weights in original.items():
        np.testing.assert_array_equal(duplicate_output[name], weights)
        displayed = expand_alias_weights(weights, layout)
        reconstructed = np.column_stack([displayed[:, list(group)].sum(axis=1) for group in layout.member_indices])
        np.testing.assert_allclose(reconstructed, weights, atol=1e-15, rtol=0)
        np.testing.assert_allclose(np.einsum("tk,tki->ti", displayed, aliases_targets),
                                   np.einsum("tk,tki->ti", weights, targets), atol=1e-15, rtol=0)
    bad = expanded_feedback.copy()
    bad[20, -1] += 1e-8
    with pytest.raises(ValueError, match="duplicate feedback"):
        canonicalize_aliases(bad, aliases, identities)
    bad_targets = aliases_targets.copy()
    bad_targets[20, -1, 0] += 1e-8
    with pytest.raises(ValueError, match="duplicate intent"):
        canonicalize_aliases(expanded_feedback, aliases, identities, targets=bad_targets)


def test_cash_is_kept_and_wins_static_when_every_noncash_expert_loses():
    feedback, available, decisions = sample()
    feedback[:, 1:] = -0.001
    output, meta = paths(feedback, available, decisions, "RAW_AS_PERCENT")
    assert meta["static_train_frozen_expert"] == "CASH"
    assert np.all(output["CASH"][:, 0] == 1)
    assert np.all(output["CASH"][:, 1:] == 0)
    assert np.all(output["FIXED_SHARE"][:, 0] > 0)
    assert np.all(output["STATIC_TRAIN_FROZEN"][365:, 0] == 1)
    invalid = feedback.copy()
    invalid[0, 0] = 1e-5
    with pytest.raises(ValueError, match="CASH"):
        paths(invalid, available, decisions, "RAW_AS_PERCENT")


def test_hedge_and_fixed_share_definitions_and_share_endpoints():
    prior = family_prior()
    utility = np.asarray([0, 1, -2, 3, -1, 0.5, -0.1, 0.2])
    expected = prior * np.exp(0.05 * utility)
    expected /= expected.sum()
    np.testing.assert_allclose(hedge_step(prior, utility), expected, atol=1e-15, rtol=0)
    np.testing.assert_allclose(fixed_share_step(prior, utility, prior, alpha=0), expected, atol=1e-15, rtol=0)
    np.testing.assert_allclose(fixed_share_step(prior, utility, prior, alpha=1), prior, atol=1e-15, rtol=0)
    np.testing.assert_allclose(fixed_share_step(prior, utility, prior), 0.99 * expected + 0.01 * prior, atol=1e-15, rtol=0)
    np.testing.assert_allclose(hedge_step(prior, np.zeros(8)), prior, atol=1e-15, rtol=0)


def test_numerical_extremes_and_all_zero_feedback_remain_finite():
    feedback, available, decisions = sample()
    feedback[:, 1:] = 1e100
    output, meta = paths(feedback, available, decisions, "RAW_AS_FRACTION")
    assert np.isfinite(meta["utility_scale"])
    for weights in output.values():
        assert np.isfinite(weights).all() and np.all(weights >= 0)
        np.testing.assert_allclose(weights.sum(axis=1), 1, atol=1e-14, rtol=0)
    for weights in paths(np.zeros((730, 8)), available, decisions, "RAW_AS_FRACTION")[0].values():
        assert np.isfinite(weights).all()
    extreme = hedge_step(family_prior(), np.asarray([0, 1e6, -1e6, 0, 0, 0, 0, 0]))
    assert np.isfinite(extreme).all() and np.isclose(extreme.sum(), 1)


@pytest.mark.parametrize("fault", ["nan", "bankrupt", "availability", "gap", "unit"])
def test_invalid_source_or_clock_is_rejected(fault):
    feedback, available, decisions = sample()
    unit = "RAW_AS_FRACTION"
    if fault == "nan":
        feedback[0, 1] = np.nan
    elif fault == "bankrupt":
        feedback[0, 1] = -1
    elif fault == "availability":
        available = available - 1
    elif fault == "gap":
        decisions = decisions.copy()
        decisions[10] += DAY_US
    else:
        unit = "BEST_PROFITABLE_UNIT"
    with pytest.raises(ValueError):
        paths(feedback, available, decisions, unit)
