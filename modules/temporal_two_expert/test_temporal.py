"""Focused synthetic contract tests; zero economic optimizer updates or native wallets."""

import json
import random
from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from . import checkpoint as cp
from .exact import (
    Episode,
    exact_path_loss,
    load_prototype,
    prepare_recovery,
    request_loss_and_gradient,
    sha,
    training_loss,
)
from .inputs import (
    CORE5,
    DAY_US,
    FEATURE_NAMES,
    FeatureTimeline,
    Standardizer,
    fit_standardizer,
    load_feature_npz,
)
from .model import Selector, predict_windows


@pytest.fixture(scope="session", autouse=True)
def deterministic_cpu():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


@pytest.fixture(scope="session")
def recovery(tmp_path_factory):
    return prepare_recovery(tmp_path_factory.mktemp("recovery") / "exact")


@pytest.fixture(scope="session")
def prototype(recovery):
    return load_prototype(recovery / "source/modules/direct_path/prototype.py")


def timeline(count=76):
    rng = np.random.default_rng(61)
    x = rng.normal(0.0, 0.1, (count, 5, 24))
    completed = np.arange(19700, 19700 + count, dtype=np.int64) * DAY_US
    return FeatureTimeline(
        x,
        np.ones_like(x, dtype=bool),
        np.ones(x.shape[:2], bool),
        completed,
        np.broadcast_to(completed[:, None, None], x.shape),
        "a" * 64,
    )


def samples(count=8):
    source = timeline(64 + count)
    windows = source.windows(source.completed_us[63 : 63 + count])
    scaler = fit_standardizer(
        [windows], training_cutoff_us=int(windows.decision_us[-1]) + 2 * DAY_US
    )
    return windows, scaler


def episode(prototype, count=8, release=True):
    windows, scaler = samples(count)
    contexts = []
    for i, decision in enumerate(windows.decision_us):
        targets = np.array(
            [
                [0.0] * 5,
                [0.08, 0.025, 0.012, -0.01, 0.003],
                [-0.035, 0.011, 0.0, 0.0, 0.0],
                [0.0, -0.04, 0.0, 0.0, 0.0],
                [-0.03, 0.018, -0.016, 0.008, -0.002],
            ]
        )
        eligible = np.ones(5, bool)
        if release and i in (2, 5):
            eligible[1 if i == 2 else 4] = False
        past = np.zeros((30, 5))
        past[:, 0] = np.tile([-0.001, 0.001], 15)
        contexts.append(
            prototype.Context(
                int(decision),
                int(decision),
                targets,
                eligible,
                past,
                np.linspace(-0.03, 0.04, 13),
                np.full(5, decision, dtype=np.int64),
            )
        )
    t = np.arange(count + 1)[:, None]
    prices = 100.0 * np.exp(0.002 * np.sin(t * 0.81 + np.arange(5)[None, :]))
    funding = np.tile([0.008, -0.002, 0.001, 0.0, -0.001], (count, 1))
    result = Episode(
        "synthetic-full-wallet",
        windows,
        tuple(contexts),
        prices,
        funding,
        windows.decision_us + DAY_US,
        int(windows.decision_us[0]),
        int(windows.decision_us[-1]) + DAY_US,
        int(windows.decision_us[-1]) + 2 * DAY_US,
        "TRAIN",
        "b" * 64,
    )
    return result, scaler


def tensors(windows):
    return [torch.tensor(a.copy()) for a in (windows.values, windows.valid, windows.step_valid)]


@pytest.mark.parametrize(
    "family,no_cash,with_cash",
    [
        ("GRU64", 13057, 13090),
        ("LATEST_MLP", 12993, 13026),
    ],
)
def test_exact_counts_output_mask_and_paired_initialization(family, no_cash, with_cash):
    windows, scaler = samples(3)
    rng = torch.get_rng_state().clone()
    models = [Selector(scaler, family=family, cash_enabled=c) for c in (False, True)]
    assert torch.equal(torch.get_rng_state(), rng)
    assert [m.parameter_count for m in models] == [no_cash, with_cash]
    for a, b in zip(models[0].encoder.parameters(), models[1].encoder.parameters(), strict=True):
        assert torch.equal(a, b)
    for m in models:
        m.eval()
        out = predict_windows(m, windows)
        assert out.shape == (3, 5) and out.dtype == torch.float64
        assert torch.all(out >= 0) and torch.all(out <= 1)
        torch.testing.assert_close(
            out.sum(-1), torch.ones(3, dtype=torch.float64), rtol=0, atol=1e-15
        )
        assert torch.count_nonzero(out[:, 2:4]) == 0
        if not m.cash_enabled:
            assert torch.count_nonzero(out[:, 0]) == 0
        else:
            assert torch.all((out[:, 0] > 0) & (out[:, 0] < 1))


def test_exact_named24_matches_existing_sources():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    source = ast.parse((root / "modules/collector_research/pipeline/make_labels.py").read_text())
    base = next(
        ast.literal_eval(n.value)
        for n in source.body
        if isinstance(n, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "BASE_FEATURES" for t in n.targets)
    )
    assert tuple(base) == FEATURE_NAMES[:18]
    assert FEATURE_NAMES[18:] == (
        "breadth1",
        "breadth5",
        "breadth20",
        "breadth60",
        "dispersion20",
        "market_vol20",
    )
    assert CORE5 == ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")


def test_future_rows_cannot_change_past_windows_or_train_normalization():
    source = timeline()
    decisions = source.completed_us[63:67]
    windows = source.windows(decisions)
    changed = source.values.copy()
    changed[67:] = 1e9
    future = replace(source, values=changed)
    other = future.windows(decisions)
    assert windows.identity == other.identity
    left = fit_standardizer([windows], training_cutoff_us=int(decisions[-1]) + DAY_US)
    right = fit_standardizer([other], training_cutoff_us=int(decisions[-1]) + DAY_US)
    assert left.identity == right.identity
    # Count shared warmup once; do not weight a row 64 times through overlapping windows.
    assert np.all(left.count == 67 * 5)
    np.testing.assert_allclose(left.mean, source.values[:67].mean((0, 1)), rtol=0, atol=1e-16)
    with pytest.raises(ValueError, match="Validation"):
        fit_standardizer(
            [future.windows(source.completed_us[67:69])],
            training_cutoff_us=int(decisions[-1]) + DAY_US,
        )


def test_insufficient_history_missing_calendar_future_clock_and_orders_reject():
    source = timeline()
    with pytest.raises(ValueError, match="64 real"):
        source.windows(source.completed_us[62:63])
    clocks = source.completed_us.copy()
    clocks[20:] += DAY_US
    with pytest.raises(ValueError, match="consecutive"):
        replace(source, completed_us=clocks)
    available = source.available_us.copy()
    available[4, 0, 0] += 1
    with pytest.raises(ValueError, match="causally"):
        replace(source, available_us=available)
    with pytest.raises(ValueError, match="order"):
        replace(source, symbol_order=tuple(reversed(CORE5)))
    with pytest.raises(ValueError, match="order"):
        replace(source, feature_names=tuple(reversed(FEATURE_NAMES)))


@pytest.mark.parametrize("family", ["GRU64", "LATEST_MLP"])
def test_missing_features_time_masks_and_finite_gradients(family):
    windows, scaler = samples(3)
    m = Selector(scaler, family=family).eval()
    x, mask, step = tensors(windows)
    mask[:, 8, 1] = False
    step[:, 8, 1] = False
    mask[:, -1, 3] = False
    step[:, -1, 3] = False
    mask[:, 14, 2, 4] = False
    x[~mask] = float("nan")
    output = m(x, mask, step)
    other = x.clone()
    other[~mask] = float("inf")
    torch.testing.assert_close(output, m(other, mask, step), rtol=0, atol=0)
    output[:, 4].sum().backward()
    assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in m.parameters())
    with pytest.raises(ValueError, match="finite"):
        m(x, torch.ones_like(mask), step)
    changed = x.clone()
    changed[0, -1, 0, 0] = float("inf")
    with pytest.raises(ValueError, match="finite"):
        m(changed, mask, step)


def test_temporal_uses_history_latest_baseline_only_uses_latest_completed_day():
    windows, scaler = samples(2)
    x, mask, step = tensors(windows)
    changed = x.clone()
    changed[:, -12, 0, 0] += 3.0
    gru = Selector(scaler, family="GRU64").eval()
    mlp = Selector(scaler, family="LATEST_MLP").eval()
    assert not torch.equal(gru(x, mask, step), gru(changed, mask, step))
    assert torch.equal(mlp(x, mask, step), mlp(changed, mask, step))
    with torch.no_grad():
        torch.testing.assert_close(
            predict_windows(gru, windows, feature_batch_size=1),
            predict_windows(gru, windows, feature_batch_size=2),
            rtol=0,
            atol=1e-15,
        )


@pytest.mark.parametrize("family", ["GRU64", "LATEST_MLP"])
def test_eval_determinism_and_training_dropout(family):
    windows, scaler = samples(5)
    m = Selector(scaler, family=family, cash_enabled=True)
    m.eval()
    assert torch.equal(predict_windows(m, windows), predict_windows(m, windows))
    m.train()
    torch.manual_seed(710)
    first = predict_windows(m, windows)
    torch.manual_seed(710)
    assert torch.equal(first, predict_windows(m, windows))
    assert not torch.equal(first, predict_windows(m, windows))


class RequestsHead:
    """Exogenous request identity adapter for the original prototype API."""

    def __init__(self, requests):
        self.parameters = dict(requests=requests)

    def forward(self, features):
        assert len(features) == len(self.parameters["requests"])
        return self.parameters["requests"], None

    def backward(self, gradient, cache):
        return dict(requests=gradient)


@pytest.mark.parametrize("cash_enabled", [False, True])
def test_original_mapped_objective_exact_request_vjp_and_paid_terminal(prototype, cash_enabled):
    e, scaler = episode(prototype)
    m = Selector(scaler, cash_enabled=cash_enabled).eval()
    request = predict_windows(m, e.windows)
    fragment = dict(contexts=e.contexts, prices=e.prices, funding_coeff=e.funding_coeff)
    loss, gradients, reports = prototype.loss_and_gradient(
        RequestsHead(request.detach().numpy()), [fragment], "DIRECT_PATH_UTILITY"
    )
    actual = exact_path_loss(request, e, prototype)
    grad = torch.autograd.grad(actual, request, retain_graph=True)[0]
    assert float(actual.detach()) == loss
    np.testing.assert_array_equal(grad.numpy(), gradients["requests"])
    _, _, report = request_loss_and_gradient(request.detach().numpy(), e, prototype)
    assert report["utility_sum"] == reports[0]["utility_sum"]
    assert report["terminal_cash_realized"] and report["fees"] > 0
    assert np.all(report["quantity"][-1] == 0)
    targets, records = prototype.mapped_path(request.detach().numpy(), e.contexts)
    assert np.all(targets[-1] == 0) and np.all(grad.numpy()[-1] == 0)
    assert report["net_PnL"] == pytest.approx(
        report["gross"] + report["funding"] - report["fees"] - report["spread"] - report["slippage"]
    )
    for record in records:
        assert np.abs(record["budget"] - record["released_prior"]).sum() <= 0.1 + 1e-12
        assert record["allocated_leg_gross"] <= 0.6 + 1e-12
        assert np.all(record["allocated_underlier_gross"] <= 0.3 + 1e-12)
        assert record["annual_vol"] <= 0.1 + 1e-12
    # Exogenous requests stay two-expert; availability release may mechanically produce CASH.
    assert records[2]["budget"][1] == 0 and records[5]["budget"][4] == 0


@pytest.mark.parametrize(
    "family,cash_enabled", [(f, c) for f in ("GRU64", "LATEST_MLP") for c in (False, True)]
)
def test_neural_exact_path_gradients_match_finite_difference(prototype, family, cash_enabled):
    e, scaler = episode(prototype)
    m = Selector(scaler, family=family, cash_enabled=cash_enabled, dropout=0.0).eval()
    loss = training_loss(m, [e], prototype, feature_batch_size=3)
    loss.backward()
    selected = [(m.w_head.weight, (0, 2))]
    if cash_enabled:
        selected.append((m.s_head.weight, (0, 2)))
    encoder = m.encoder.weight_ih_l0 if family == "GRU64" else m.encoder[0].weight
    # Select a material gradient, rather than falsely validating a zero derivative.
    index = np.unravel_index(int(torch.argmax(encoder.grad.abs())), tuple(encoder.shape))
    selected.append((encoder, index))
    for p, index in selected:
        analytic = float(p.grad[index])
        assert abs(analytic) > 1e-13
        original = float(p.detach()[index])
        eps = 1e-5
        with torch.no_grad():
            p[index] = original + eps
            plus = float(training_loss(m, [e], prototype, feature_batch_size=3))
            p[index] = original - eps
            minus = float(training_loss(m, [e], prototype, feature_batch_size=3))
            p[index] = original
        assert analytic == pytest.approx((plus - minus) / (2 * eps), rel=3e-4, abs=2e-11)


def test_wallet_gap_split_maturity_duplicate_and_validation_role_reject(prototype):
    e, scaler = episode(prototype)
    m = Selector(scaler).eval()
    with pytest.raises(ValueError, match="chronological"):
        replace(e, contexts=e.contexts[:3] + e.contexts[4:])
    with pytest.raises(ValueError, match="chronological"):
        replace(e, start_us=e.start_us + DAY_US)
    with pytest.raises(ValueError, match="mature"):
        replace(e, label_available_us=e.windows.decision_us)
    with pytest.raises(ValueError, match="mature"):
        replace(e, label_available_us=np.full(len(e.contexts), e.split_cutoff_us, np.int64))
    with pytest.raises(ValueError, match="TRAIN"):
        training_loss(m, [replace(e, role="SEEN_VALIDATION")], prototype)
    with pytest.raises(ValueError, match="Distinct"):
        training_loss(m, [e, e], prototype)


def test_training_loss_never_resets_at_feature_chunks(prototype):
    e, scaler = episode(prototype)
    m = Selector(scaler).eval()
    a = training_loss(m, [e], prototype, feature_batch_size=1)
    b = training_loss(m, [e], prototype, feature_batch_size=3)
    torch.testing.assert_close(a, b, rtol=0, atol=1e-16)
    ga = torch.autograd.grad(a, tuple(m.parameters()))
    gb = torch.autograd.grad(b, tuple(m.parameters()))
    for left, right in zip(ga, gb, strict=True):
        torch.testing.assert_close(left, right, rtol=1e-10, atol=1e-16)


def test_terminal_label_clock_uses_original_forced_cash_maturity_rule(prototype):
    e, scaler = episode(prototype)
    labels = e.label_available_us.copy()
    labels[-1] = e.split_cutoff_us + 40 * DAY_US
    terminal = replace(e, label_available_us=labels)
    model = Selector(scaler).eval()
    assert torch.equal(
        training_loss(model, [e], prototype), training_loss(model, [terminal], prototype)
    )
    assert not terminal.contexts[0].expert_targets.flags.writeable


def test_recovered_real_fragment_unchanged_objective_no_fitting(recovery, prototype):
    index = json.loads((recovery / "direct_path_fragments/INDEX.json").read_text())
    entry = index["fragments"][0]
    path = recovery / "direct_path_fragments" / entry["file"]
    assert sha(path) == entry["sha256"]
    with np.load(path, allow_pickle=False) as z:
        a = {k: z[k].copy() for k in z.files}
    contexts = tuple(
        prototype.Context(
            int(d),
            int(a["market_state13_available_us"][i]),
            a["expert_targets"][i],
            a["expert_eligible"][i],
            a["past_returns30"][i],
            a["market_state13"][i],
            a["target_available_us"][i],
        )
        for i, d in enumerate(a["decision_us"])
    )
    original = recovery / "two_expert_direct_fit/NO_CASH.npz"
    assert sha(original) == "25730ad657e7de45dc3740df0c88f116bc80391e61dbb50844f1698b9a0c7ec6"
    with np.load(original, allow_pickle=False) as head:
        features = (a["market_state13"][:, [2, 5]] - head["mean"]) / head["scale"]
        logits = np.c_[np.ones(len(features)), features] @ head["w"]
        w = 1.0 / (1.0 + np.exp(-logits))
    requests = np.zeros((len(w), 5))
    requests[:, 1], requests[:, 4] = 1.0 - w, w
    e = SimpleNamespace(contexts=contexts, prices=a["prices"], funding_coeff=a["funding_coeff"])
    actual, gradient, _ = request_loss_and_gradient(requests, e, prototype)
    reference, gradients, _ = prototype.loss_and_gradient(
        RequestsHead(requests),
        [dict(contexts=contexts, prices=e.prices, funding_coeff=e.funding_coeff)],
        "DIRECT_PATH_UTILITY",
    )
    assert actual == reference
    np.testing.assert_array_equal(gradient, gradients["requests"])
    assert sha(original) == "25730ad657e7de45dc3740df0c88f116bc80391e61dbb50844f1698b9a0c7ec6"


def test_corrupt_recovery_source_rejects(tmp_path, prototype):
    path = tmp_path / "prototype.py"
    path.write_bytes(open(prototype.__file__, "rb").read() + b"\n# changed\n")
    with pytest.raises(ValueError, match="Exact recovered"):
        load_prototype(path)


def synthetic_update(model, optimizer, windows):
    """Optimizer mechanics only, deliberately no path economic loss."""
    model.train()
    optimizer.zero_grad(set_to_none=True)
    requests = predict_windows(model, windows, feature_batch_size=2)
    coefficients = requests.new_tensor([0.31, -0.7, 0.0, 0.0, 0.91])
    loss = ((requests * coefficients).sum(-1) - 0.1).square().mean()
    loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)


@pytest.mark.parametrize("family", ["GRU64", "LATEST_MLP"])
def test_atomic_checkpoint_exact_optimizer_rng_resume_and_eval_serialization(tmp_path, family):
    windows, scaler = samples(5)
    m = Selector(scaler, family=family, cash_enabled=True)
    opt = cp.make_optimizer(m)
    binding = cp.run_binding(
        m,
        data_split_identity=dict(input=windows.identity, cutoff="TRAIN_ONLY"),
        feature_batch_size=2,
        max_steps=4,
    )
    torch.manual_seed(77)
    np.random.seed(83)
    random.seed(89)
    with cp.run_guard(tmp_path / "run", binding) as output:
        synthetic_update(m, opt, windows)
        pointer = cp.save_checkpoint(output, m, opt, binding, step=1, elapsed_seconds=0.5)
        # Ignore an interrupted generation whose pointer was never committed.
        (output / "step-orphan.pt").write_bytes(b"incomplete interrupted write")
        python_expected, numpy_expected = random.random(), np.random.random()
        synthetic_update(m, opt, windows)
        expected = {k: v.clone() for k, v in m.state_dict().items()}
        expected_optimizer = opt.state_dict()
        resumed = Selector(scaler, family=family, cash_enabled=True)
        resumed_opt = cp.make_optimizer(resumed)
        state = cp.load_checkpoint(output, resumed, resumed_opt, binding)
        assert state["step"] == 1 and state["elapsed_seconds"] == 0.5
        assert state["checkpoint_SHA256"] == pointer["SHA256"]
        assert random.random() == python_expected and np.random.random() == numpy_expected
        assert resumed.training
        synthetic_update(resumed, resumed_opt, windows)
        for key, value in expected.items():
            assert torch.equal(resumed.state_dict()[key], value)
        for key, value in expected_optimizer["state"].items():
            for name, tensor in value.items():
                assert torch.equal(resumed_opt.state_dict()["state"][key][name], tensor)
        resumed.eval()
        before = predict_windows(resumed, windows).detach()
        frozen = cp.save_checkpoint(output, resumed, resumed_opt, binding, step=2)
        cp.load_checkpoint(output, m, opt, binding)
        assert not m.training
        assert torch.equal(predict_windows(m, windows), before)
        assert cp.model_identity(m) == frozen["model_identity"]


def test_duplicate_run_and_changed_input_config_source_or_corrupt_snapshot_reject(tmp_path):
    windows, scaler = samples(2)
    model = Selector(scaler)
    optimizer = cp.make_optimizer(model)
    binding = cp.run_binding(
        model, data_split_identity=windows.identity, feature_batch_size=2, max_steps=2
    )
    with cp.run_guard(tmp_path / "run", binding) as output:
        with pytest.raises(RuntimeError, match="duplicate"):
            with cp.run_guard(output, binding):
                pass
        pointer = cp.save_checkpoint(output, model, optimizer, binding, step=0)
        different = cp.run_binding(
            model, data_split_identity="changed-split", feature_batch_size=2, max_steps=2
        )
        with pytest.raises(ValueError, match="binding"):
            cp.load_checkpoint(output, model, optimizer, different)
        file = output / pointer["file"]
        file.write_bytes(file.read_bytes() + b"corrupt")
        with pytest.raises(ValueError, match="bytes"):
            cp.load_checkpoint(output, model, optimizer, binding)
    with pytest.raises(ValueError, match="identity differs"):
        with cp.run_guard(tmp_path / "run", different):
            pass


def test_interruption_before_atomic_pointer_keeps_previous_snapshot(tmp_path, monkeypatch):
    windows, scaler = samples(2)
    model = Selector(scaler)
    optimizer = cp.make_optimizer(model)
    binding = cp.run_binding(
        model, data_split_identity=windows.identity, feature_batch_size=2, max_steps=2
    )
    with cp.run_guard(tmp_path / "run", binding) as output:
        original = cp.save_checkpoint(output, model, optimizer, binding, step=0)
        synthetic_update(model, optimizer, windows)

        def interrupted_pointer(path, record):
            raise InterruptedError("simulated connection/process interruption before pointer swap")

        with monkeypatch.context() as patch:
            patch.setattr(cp, "_atomic_json", interrupted_pointer)
            with pytest.raises(InterruptedError):
                cp.save_checkpoint(output, model, optimizer, binding, step=1)
        assert json.loads((output / "latest.json").read_text()) == original
        assert cp.load_checkpoint(output, model, optimizer, binding)["step"] == 0


def test_training_interface_does_not_accept_inspection_scaler(prototype, tmp_path):
    from .runner import train_steps

    e, _ = episode(prototype)
    dummy = Standardizer(np.zeros(24), np.ones(24), np.ones(24, np.int64), dict(role="inspection"))
    with pytest.raises(ValueError, match="standardizer"):
        train_steps(Selector(dummy), [e], prototype, tmp_path / "never-started", max_steps=1)
    assert not (tmp_path / "never-started").exists()


def test_training_runner_interruption_resumes_without_duplicate_updates(
    prototype, tmp_path, monkeypatch
):
    # Replace economic loss with a synthetic scalar solely to test control flow.
    # No economic training is performed by this test.
    from . import runner

    e, scaler = episode(prototype, count=3)
    calls = []

    def synthetic_loss(model, episodes, ignored_prototype, *, feature_batch_size):
        calls.append(1)
        request = predict_windows(model, episodes[0].windows, feature_batch_size=feature_batch_size)
        return ((request[:, 4] - 0.71) ** 2).mean()

    def interrupted_loss(*args, **kwargs):
        if len(calls) == 1:
            raise InterruptedError("synthetic interruption after first committed update")
        return synthetic_loss(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(runner, "training_loss", interrupted_loss)
        interrupted = Selector(scaler, cash_enabled=True)
        with pytest.raises(InterruptedError):
            runner.train_steps(
                interrupted, [e], prototype, tmp_path / "resumed", max_steps=3, feature_batch_size=2
            )
    assert json.loads((tmp_path / "resumed/latest.json").read_text())["step"] == 1
    assert len(calls) == 1
    with monkeypatch.context() as patch:
        patch.setattr(runner, "training_loss", synthetic_loss)
        resumed = Selector(scaler, cash_enabled=True)
        result = runner.train_steps(
            resumed, [e], prototype, tmp_path / "resumed", max_steps=3, feature_batch_size=2
        )
        assert result["completed_steps"] == 3 and not result["validation_scored"]
        assert len(calls) == 3
        again = runner.train_steps(
            Selector(scaler, cash_enabled=True),
            [e],
            prototype,
            tmp_path / "resumed",
            max_steps=3,
            feature_batch_size=2,
        )
        assert again["completed_steps"] == 3 and len(calls) == 3
        reference = Selector(scaler, cash_enabled=True)
        runner.train_steps(
            reference, [e], prototype, tmp_path / "uninterrupted", max_steps=3, feature_batch_size=2
        )
    for key, value in reference.state_dict().items():
        assert torch.equal(resumed.state_dict()[key], value)


def test_safe_feature_archive_and_exact_hash(tmp_path):
    source = timeline()
    path = tmp_path / "features.npz"
    np.savez(
        path,
        values=source.values,
        valid=source.valid,
        step_valid=source.step_valid,
        completed_us=source.completed_us,
        available_us=source.available_us,
        source_sha256=np.array(source.source_sha256),
        symbol_order=np.array(CORE5),
        feature_names=np.array(FEATURE_NAMES),
    )
    loaded = load_feature_npz(path, expected_sha256=sha(path))
    assert (
        loaded.windows(loaded.completed_us[63:66]).identity
        == source.windows(source.completed_us[63:66]).identity
    )
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="producer-bound"):
        load_feature_npz(path, expected_sha256="c" * 64)


def test_changed_source_and_arm_identity_reject(tmp_path, monkeypatch):
    windows, scaler = samples(2)
    model = Selector(scaler)
    opt = cp.make_optimizer(model)
    binding = cp.run_binding(
        model, data_split_identity=windows.identity, feature_batch_size=2, max_steps=2
    )
    with cp.run_guard(tmp_path / "run", binding) as output:
        cp.save_checkpoint(output, model, opt, binding, step=0)
        other_arm = Selector(scaler, cash_enabled=True)
        with pytest.raises(ValueError, match="binding"):
            cp.load_checkpoint(output, other_arm, cp.make_optimizer(other_arm), binding)
        with monkeypatch.context() as patch:
            patch.setattr(cp, "source_identity", lambda: {"modified_source": "d" * 64})
            with pytest.raises(ValueError, match="binding"):
                cp.load_checkpoint(output, model, opt, binding)
