"""Focused fresh-fold causality, paid-close, exact gradient and resume tests."""

import copy
from dataclasses import replace

import numpy as np
import pytest
import torch

from modules.temporal_episode_weighting_v2.gradient import memory_bounded_gradients
from modules.temporal_expert_input.checkpoint import load_checkpoint, save_checkpoint
from modules.temporal_expert_input.gradient import predict_episode, request_gradient
from modules.temporal_short_expansion.adapter import append_episode
from modules.temporal_short_expansion.tests.test_checkpoint import assert_optimizer_equal
from modules.temporal_two_expert.checkpoint import _rng_state, model_identity, run_guard
from modules.temporal_two_expert.inputs import DAY_US, fit_standardizer
from modules.temporal_two_expert.test_temporal import episode

from .data import EXECUTION_DELAY_US, close_slice, fold_inputs, load_source
from .model import initialize, parameter_identity
from .protocol import FOLDS, sources
from .stage import SUCCESS, binding_for, validate_terminal


def synthetic(prototype):
    original, _ = episode(prototype, 71, release=False)
    original = replace(
        original, label_available_us=original.label_available_us + EXECUTION_DELAY_US
    )
    expanded = append_episode(
        original,
        np.tile([-0.02, -0.01, -0.01, -0.005, -0.005], (71, 1, 1)),
        np.ones((71, 1), bool),
        original.windows.decision_us[:, None],
        prototype,
        "c" * 64,
    )
    clocks = {int(d): int(d) + EXECUTION_DELAY_US for d in original.windows.decision_us}
    cutoff = int(original.windows.decision_us[8])
    return expanded, clocks, cutoff


def prefix(expanded, clocks, cutoff):
    return close_slice(
        expanded,
        0,
        8,
        cutoff_us=cutoff,
        role="TRAIN",
        wallet_id="fresh-prefix",
        execution_clocks=clocks,
    )[0]


def step(model, optimizer, episodes, prototype):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    loss, _ = memory_bounded_gradients(model, episodes, prototype, feature_batch_size=32)
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)
    return loss


def test_terminal_maturity_rejects_future_active_interval(prototype):
    e, clocks, cutoff = synthetic(prototype)
    closed = prefix(e, clocks, cutoff)
    assert closed.label_available_us[-1] == cutoff - DAY_US + EXECUTION_DELAY_US < cutoff
    assert np.all(closed.label_available_us < cutoff)
    assert len(closed.internal.contexts) == len(closed.contexts) == len(closed.windows.values) == 8
    np.testing.assert_array_equal(closed.prices[-1], closed.prices[-2])
    np.testing.assert_array_equal(closed.funding_coeff[-1], 0)
    with pytest.raises(ValueError, match="precede cutoff"):
        close_slice(
            e, 0, 9, cutoff_us=cutoff, role="TRAIN", wallet_id="invalid", execution_clocks=clocks
        )
    futureclose = dict(clocks)
    futureclose[int(e.windows.decision_us[7])] = cutoff
    with pytest.raises(ValueError, match="precede cutoff"):
        prefix(e, futureclose, cutoff)


def test_future_suffix_cannot_change_prefix_scaler_loss_gradient_or_rng(prototype):
    e, clocks, cutoff = synthetic(prototype)
    a = prefix(e, clocks, cutoff)
    p, f = e.original.prices.copy(), e.original.funding_coeff.copy()
    p[8:] *= 1e6
    f[7:] *= 1e7
    values = e.windows.values.copy()
    values[8:] += 1e6
    windows = replace(e.windows, values=values)
    original = replace(e.original, prices=p, funding_coeff=f, windows=windows)
    targets = e.expert_targets.copy()
    targets[8:] *= -1
    altered = replace(e, original=original, expert_targets=targets)
    b = prefix(altered, clocks, cutoff)
    assert a.identity == b.identity
    scaler_a = fit_standardizer([a.windows], training_cutoff_us=cutoff)
    scaler_b = fit_standardizer([b.windows], training_cutoff_us=cutoff)
    assert scaler_a.identity == scaler_b.identity
    ma, oa = initialize(scaler_a)
    rng = torch.get_rng_state().clone()
    la, _ = memory_bounded_gradients(ma, [a], prototype)
    expected = [v.grad.clone() for v in ma.parameters()]
    mb, ob = initialize(scaler_b)
    assert torch.equal(torch.get_rng_state(), rng)
    lb, _ = memory_bounded_gradients(mb, [b], prototype)
    assert la == lb and not oa.state and not ob.state
    assert all(torch.equal(p.grad, g) for p, g in zip(mb.parameters(), expected, strict=True))


def test_same_seed_fresh_parameters_different_prefix_scalers(prototype):
    e, clocks, cutoff = synthetic(prototype)
    a = prefix(e, clocks, cutoff)
    b = close_slice(
        e, 0, 7, cutoff_us=cutoff, role="TRAIN", wallet_id="earlier", execution_clocks=clocks
    )[0]
    sa, sb = (fit_standardizer([x.windows], training_cutoff_us=cutoff) for x in (a, b))
    ma, oa = initialize(sa)
    rng = torch.get_rng_state().clone()
    mb, ob = initialize(sb)
    assert sa.identity != sb.identity and parameter_identity(ma) == parameter_identity(mb)
    assert ma.parameter_count == mb.parameter_count == 13699 and not oa.state and not ob.state
    assert torch.equal(rng, torch.get_rng_state()) and "no_parent" in ma.contract["initialization"]
    ma.eval()
    out = predict_episode(ma, a)
    np.testing.assert_array_equal(out.detach().numpy()[:, 2:4], 0)
    torch.testing.assert_close(out.sum(1), torch.ones(8, dtype=torch.float64), rtol=0, atol=1e-15)
    torch.testing.assert_close(
        out[:, 0], torch.full((8,), 0.5, dtype=torch.float64), rtol=0, atol=1e-15
    )


def test_paid_close_exact_mapped_objective_and_suffix_independence(prototype):
    e, clocks, cutoff = synthetic(prototype)
    a = prefix(e, clocks, cutoff)
    scaler = fit_standardizer([a.windows], training_cutoff_us=cutoff)
    m, _ = initialize(scaler)
    m.eval()
    q = predict_episode(m, a).detach().numpy()
    loss, g, report = request_gradient(q, a, prototype)
    assert report["terminal_cash_realized"] and float(report["fees"]) > 0
    # Compare unchanged objective on the originally stored final interval:
    # its numerical values must be causally irrelevant after paid forced CASH.
    original = replace(
        a.original.original,
        prices=e.original.prices[:9],
        funding_coeff=e.original.funding_coeff[:8],
    )
    internal = replace(original, contexts=a.internal.contexts)
    altered = replace(a.original, original=original, internal=internal)
    from modules.temporal_expert_input.inputs import expose_episode

    raw = expose_episode(altered)
    other, other_g, other_report = request_gradient(q, raw, prototype)
    assert loss == other
    np.testing.assert_array_equal(g, other_g)
    torch.testing.assert_close(report["nav"], other_report["nav"], rtol=0, atol=0)
    direction = np.zeros_like(q)
    direction[:, 0] = -0.2
    direction[:, 1] = 0.2
    eps = 1e-5
    finite = (
        request_gradient(q + eps * direction, a, prototype)[0]
        - request_gradient(q - eps * direction, a, prototype)[0]
    ) / (2 * eps)
    assert abs(finite - float((g * direction).sum())) < 1e-9


def test_fresh_checkpoint_exact_next_update_and_crossfold_rejection(tmp_path, prototype):
    e, clocks, cutoff = synthetic(prototype)
    a = prefix(e, clocks, cutoff)
    scaler = fit_standardizer([a.windows], training_cutoff_us=cutoff)
    m, o = initialize(scaler)
    binding = binding_for(m, dict(fold="synthetic", train=[a.identity], scaler=scaler.identity))
    with run_guard(tmp_path / "run", binding) as folder:
        save_checkpoint(folder, m, o, binding, step=0, sources=sources)
        step(m, o, [a], prototype)
        save_checkpoint(folder, m, o, binding, step=1, sources=sources)
        rng = copy.deepcopy(_rng_state())
        step(m, o, [a], prototype)
        wanted = model_identity(m)
        wanted_opt = copy.deepcopy(o.state_dict())
        resumed, ro = initialize(scaler)
        saved = load_checkpoint(folder, resumed, ro, binding, sources=sources)
        assert saved["step"] == 1 and torch.equal(torch.get_rng_state(), rng["torch"])
        step(resumed, ro, [a], prototype)
        assert model_identity(resumed) == wanted
        assert_optimizer_equal(wanted_opt, ro.state_dict())
        assert all(float(ro.state[p]["step"]) == 2 for p in resumed.parameters())
        wrong = binding_for(
            initialize(scaler)[0],
            dict(fold="different", train=[a.identity], scaler=scaler.identity),
        )
        with pytest.raises(ValueError, match="binding"):
            load_checkpoint(folder, resumed, ro, wrong, sources=sources)


def test_real_fold_counts_close_clocks_and_no_full_scaler_reuse(prototype):
    from pathlib import Path

    state = Path("/workspace/coin-state/work/temporal-two-expert-20261009")
    if not (state / "FROZEN_PACKET.json").exists():
        pytest.skip("Existing public payload must be restored for historical input check")
    source, _, clocks = load_source(state, prototype=prototype)
    counts = []
    identities = []
    for fold, start in FOLDS.items():
        train, forward, scaler, _, receipt = fold_inputs(source, clocks, start, fold)
        counts.append(receipt["training_decisions"])
        identities.append(scaler.identity)
        assert len(forward.contexts) == 63 and forward.start_us == start
        assert len(train) == 5 and train[0].start_us == source[0].start_us
        assert train[-1].windows.decision_us[-1] == start - DAY_US
        assert all(np.all(e.label_available_us < start) for e in train)
        assert scaler.provenance["real_row_count"] < 907
    assert counts == [476, 567, 658]
    assert len(set(identities)) == 3


def test_source_binding_includes_actual_whole_wallet_gradient():
    assert "modules/temporal_episode_weighting_v2/gradient.py" in sources()


@pytest.mark.parametrize(
    "field,value", [("step", 511), ("model_identity", "wrong"), ("checkpoint_SHA256", "wrong")]
)
def test_terminal512_receipt_cannot_promote_wrong_checkpoint(field, value):
    terminal = dict(
        status=SUCCESS,
        completed_updates=512,
        fixed_target=512,
        model_identity="x",
        checkpoint_SHA256="y",
    )
    saved = dict(step=512, model_identity="x", checkpoint_SHA256="y")
    validate_terminal(terminal, saved)
    saved[field] = value
    with pytest.raises(ValueError, match="actual checkpoint"):
        validate_terminal(terminal, saved)


def test_incomplete_forward_result_cannot_enter_aggregate(tmp_path):
    import json

    from .export import aggregate

    path = tmp_path / "FOLD_incomplete"
    path.mkdir()
    (path / "RESULT.json").write_text(json.dumps(dict(primary_utility_excess=100)))
    result = aggregate(tmp_path)
    assert result["completed_folds"] == 0 and result["screen_pass"] is False
    assert "FOLD_incomplete" in result["rejected_incomplete_or_changed_bundles"]
