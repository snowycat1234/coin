"""Focused fixed-calendar inputs, prefix causality and empty-Adam serialization."""

import copy
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_expert_input.checkpoint import load_checkpoint, save_checkpoint
from modules.temporal_prequential_transfer.data import load_source
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_two_expert.checkpoint import _rng_state, model_identity, run_guard
from modules.temporal_two_expert.inputs import DAY_US

from .data import END, FOLD, START, load_fold, prefixes
from .protocol import PROTOCOL, sources
from .stage import SUCCESS, binding_for, validate_terminal

STATE = Path("/workspace/coin-state/work/temporal-two-expert-20261009")


def test_future_suffix_cannot_change_prefix_or_normalization():
    if not (STATE / "FROZEN_PACKET.json").exists():
        pytest.skip("Restore existing pinned public packets for actual prefix test")
    source, _, clocks = load_source(STATE)
    train, scaler, _ = prefixes(source, clocks)
    final = source[-1]
    base = final.original
    n = int((final.windows.decision_us < START).sum())
    prices, funding = base.prices.copy(), base.funding_coeff.copy()
    prices[n:] *= 1e6
    funding[n - 1 :] *= 1e6
    values = base.windows.values.copy()
    values[n:] += 1e6
    altered = replace(
        final,
        original=replace(
            base,
            prices=prices,
            funding_coeff=funding,
            windows=replace(base.windows, values=values),
        ),
    )
    other, other_scaler, _ = prefixes([*source[:-1], altered], clocks)
    assert [e.identity for e in train] == [e.identity for e in other]
    assert (
        scaler.identity
        == other_scaler.identity
        == "2a15ff63febdc6feb065f0ef01da909a77b4661d13fbcf7f438b39c0c9e21102"
    )


@pytest.fixture(scope="module")
def actual():
    if not (STATE / "FROZEN_PACKET.json").exists():
        pytest.skip("Restore existing pinned public packets for actual April coverage test")
    return load_fold(STATE)


def test_fixed_calendar_prefix_counts_real_warmup_and_paid_closure(actual):
    train, forward, _, scaler, _, receipt = actual
    assert [len(e.contexts) for e in train] == [54, 88, 62, 144, 401]
    assert sum(len(e.contexts) for e in train) == 749
    assert scaler.provenance["real_row_count"] == 878
    assert all(np.all(e.label_available_us < START) for e in train)
    assert max(int(e.label_available_us.max()) for e in train) == START - DAY_US + 60000001
    np.testing.assert_array_equal(
        forward.windows.decision_us, np.arange(START, END, DAY_US, dtype=np.int64)
    )
    assert forward.windows.values.shape == (63, 64, 5, 24)
    assert forward.windows.step_valid.all()
    assert np.all(np.diff(forward.windows.completed_us, axis=1) == DAY_US)
    assert forward.windows.completed_us[0, 0] == START - 63 * DAY_US
    assert forward.label_available_us[-1] == END - DAY_US + 60000001
    np.testing.assert_array_equal(forward.prices[-1], forward.prices[-2])
    np.testing.assert_array_equal(forward.funding_coeff[-1], 0)
    assert receipt["boundary_prices_funding_29_overlap"].startswith("BIT_IDENTICAL")
    assert len(forward.contexts) == 63 and forward.wallet_id == "FORWARD63_" + FOLD


def test_forward_inputs_are_causal_and_no_training_window_reaches_April(actual):
    train, forward, _, _, _, _ = actual
    assert all(np.max(e.windows.completed_us) < START for e in train)
    assert all(np.max(e.expert_input_available_us) < START for e in train)
    assert np.all(forward.expert_input_available_us <= forward.windows.decision_us[:, None])
    assert np.all(forward.target_available_us <= forward.windows.decision_us[:, None])
    assert np.all(forward.windows.available_us <= forward.windows.decision_us[:, None, None, None])
    assert not forward.eligible[:, 2:4].any()
    np.testing.assert_array_equal(forward.expert_targets[:, 2:4], 0)


def test_same_fresh_parameters_full_rng_and_empty_adam(actual):
    model, optimizer = initialize(actual[3])
    raw, rng = parameter_identity(model), copy.deepcopy(_rng_state())
    other, other_optimizer = initialize(actual[3])
    assert model.parameter_count == 13699 and not optimizer.state and not other_optimizer.state
    assert (
        raw
        == parameter_identity(other)
        == "0994f7810bad367ba112800f2e3aeea503813094d62bb734c7e489de7bf995f2"
    )
    assert tree_identity(_rng_state()) == tree_identity(rng)
    assert tree_identity(rng) == "30a903bc36cf857b72cba9f97a6809c6945bf4cf8c5227adf4263e1bcd715a77"


def test_step_zero_checkpoint_and_changed_prefix_rejection(tmp_path, actual):
    model, optimizer = initialize(actual[3])
    binding = binding_for(model, actual[4])
    assert set(binding["specification"]["algorithm"]["parameter_birth_steps"].values()) == {0}
    with run_guard(tmp_path / "snapshot", binding) as folder:
        save_checkpoint(folder, model, optimizer, binding, step=0, sources=sources)
        other, opt = initialize(actual[3])
        saved = load_checkpoint(folder, other, opt, binding, sources=sources)
        assert (
            saved["step"] == 0 and not opt.state and model_identity(other) == model_identity(model)
        )
        wrong = binding_for(other, dict(changed_prefix=True))
        with pytest.raises(ValueError, match="binding"):
            load_checkpoint(folder, other, opt, wrong, sources=sources)


@pytest.mark.parametrize(
    "field,value", [("step", 511), ("model_identity", "wrong"), ("checkpoint_SHA256", "wrong")]
)
def test_actual512_required_before_any_forward_export(field, value):
    terminal = dict(
        status=SUCCESS,
        completed_updates=512,
        fixed_target=512,
        model_identity="m",
        checkpoint_SHA256="c",
    )
    saved = dict(step=512, model_identity="m", checkpoint_SHA256="c")
    validate_terminal(terminal, saved)
    saved[field] = value
    with pytest.raises(ValueError, match="actual checkpoint"):
        validate_terminal(terminal, saved)


def test_no_period_choice_recipe_change_or_erasure_of_prior_failure():
    assert PROTOCOL["planned_fits"] == 1 and PROTOCOL["fixed_updates"] == 512
    assert PROTOCOL["folds"] == {FOLD: START}
    assert PROTOCOL["controls"]["VOL50_CS50"] == [0, 0.5, 0, 0, 0.5, 0]
    assert PROTOCOL["controls"]["CASH50_VOL25_CS25"] == [0.5, 0.25, 0, 0, 0.25, 0]
    assert PROTOCOL["no_choice_of_alternative_period"] and PROTOCOL["no_continuation_beyond512"]
    for name in [
        "modules/temporal_april_transfer/upstream/momentum_short_pool_target.py",
        "modules/collector_research/pipeline/normalize.py",
        "modules/temporal_episode_weighting_v2/gradient.py",
    ]:
        assert name in sources()
