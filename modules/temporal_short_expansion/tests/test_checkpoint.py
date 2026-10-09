"""Synthetic optimizer mechanics only; no historical economic fitting or data writes."""

import copy
import json
import random
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from modules.temporal_short_expansion import checkpoint as cp
from modules.temporal_two_expert.checkpoint import make_optimizer, run_binding
from modules.temporal_two_expert.exact import sha


@pytest.fixture(scope="module", autouse=True)
def deterministic_cpu():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


class SyntheticExpansion(nn.Module):
    """The same 33 new parameters in control and expanded toy heads."""

    def __init__(self, base=None, *, short_enabled=True):
        super().__init__()
        self.base = (
            base
            if base is not None
            else nn.Sequential(
                nn.Linear(4, 32, dtype=torch.float64),
                nn.Tanh(),
                nn.Dropout(0.25),
                nn.Linear(32, 1, dtype=torch.float64),
            )
        )
        self.r_head = nn.Linear(32, 1, dtype=torch.float64)
        self.short_enabled = short_enabled
        self.contract = dict(schema="SYNTHETIC_ADAM_BIRTH_TEST", short_enabled=short_enabled)

    def forward(self, values):
        hidden = self.base[2](self.base[1](self.base[0](values)))
        r = torch.sigmoid(self.r_head(hidden))
        if not self.short_enabled:
            r = r * 0.0  # Real zero gradients still advance the matched Adam ages.
        return self.base[3](hidden) + r


def versioned_sources():
    root = Path(cp.__file__).resolve().parents[2]
    paths = list(Path(cp.__file__).parent.glob("*.py"))
    paths += list((root / "modules/temporal_surrogate_resume_v2").glob("*.py"))
    paths += list((root / "modules/temporal_risk_proxy_v2").glob("*.py"))
    return {str(p.relative_to(root)): sha(p) for p in sorted(paths)}


def warm_case(*, parent_step=3, short_enabled=True):
    base = nn.Sequential(
        nn.Linear(4, 32, dtype=torch.float64),
        nn.Tanh(),
        nn.Dropout(0.25),
        nn.Linear(32, 1, dtype=torch.float64),
    )
    parent_opt = torch.optim.Adam(
        base.parameters(), lr=0.001, betas=(0.9, 0.999), eps=1e-8, foreach=False
    )
    for _ in range(parent_step):
        parent_opt.zero_grad(set_to_none=True)
        base(torch.ones(2, 4, dtype=torch.float64)).square().mean().backward()
        parent_opt.step()
    parent_opt.zero_grad(set_to_none=True)
    model = SyntheticExpansion(base, short_enabled=short_enabled)
    optimizer = make_optimizer(model)
    for parameter in base.parameters():
        optimizer.state[parameter] = copy.deepcopy(parent_opt.state[parameter])
    binding = run_binding(
        model,
        data_split_identity="SYNTHETIC_TRAIN_ONLY",
        feature_batch_size=2,
        max_steps=parent_step + 4,
        max_seconds=120,
        algorithm=dict(
            parent=dict(step=parent_step),
            versioned_sources=versioned_sources(),
            parameter_birth_steps={
                n: 0 if n.startswith("base.") else parent_step for n, _ in model.named_parameters()
            },
        ),
    )
    return model, optimizer, binding


def update(model, optimizer):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    values = torch.randn(3, 4, dtype=torch.float64)
    loss = (model(values) - random.random() - float(np.random.random())).square().mean()
    loss.backward()
    assert all(p.grad is not None for p in model.parameters())
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)


def clone_optimizer(optimizer):
    return copy.deepcopy(optimizer.state_dict())


def assert_optimizer_equal(first, second):
    assert first["param_groups"] == second["param_groups"]
    assert first["state"].keys() == second["state"].keys()
    for key, state in first["state"].items():
        assert state.keys() == second["state"][key].keys()
        for name, value in state.items():
            assert torch.equal(value, second["state"][key][name])


def rewrite_snapshot(directory, change):
    pointer = json.loads((directory / "latest.json").read_text())
    path = directory / pointer["file"]
    state = torch.load(path, weights_only=True, map_location="cpu")
    change(state)
    torch.save(state, path)
    pointer["SHA256"] = sha(path)
    (directory / "latest.json").write_text(json.dumps(pointer))


@pytest.mark.parametrize("short_enabled", [False, True])
def test_warm_780_exact_next_update_and_all_rng_resume(tmp_path, short_enabled):
    model, optimizer, binding = warm_case(parent_step=780, short_enabled=short_enabled)
    births = binding["specification"]["algorithm"]["parameter_birth_steps"]
    cp.validate_moments(model, optimizer, 780, births)
    assert sum(p.numel() for p in model.r_head.parameters()) == 33
    assert all(not optimizer.state.get(p) for p in model.r_head.parameters())
    torch.manual_seed(79)
    random.seed(83)
    np.random.seed(89)
    with cp.run_guard(tmp_path / "run", binding) as directory:
        initial = cp.save_checkpoint(
            directory, model, optimizer, binding, step=780, sources=versioned_sources
        )
        initial_bytes = (directory / initial["file"]).read_bytes()
        update(model, optimizer)
        pointer = cp.save_checkpoint(
            directory,
            model,
            optimizer,
            binding,
            step=781,
            elapsed_seconds=0.5,
            trainer_state=dict(status="RUNNING", history=[dict(step=1)]),
        )
        assert (directory / initial["file"]).read_bytes() == initial_bytes
        for name, parameter in model.named_parameters():
            assert float(optimizer.state[parameter]["step"]) == (
                781 if name.startswith("base.") else 1
            )
            if not short_enabled and name.startswith("r_head."):
                assert torch.count_nonzero(optimizer.state[parameter]["exp_avg"]) == 0
                assert torch.count_nonzero(optimizer.state[parameter]["exp_avg_sq"]) == 0
        (directory / "step-orphan.pt").write_bytes(b"incomplete uncommitted generation")
        rng_next = (random.random(), np.random.random(), torch.rand(3))
        update(model, optimizer)
        expected = copy.deepcopy(model.state_dict())
        expected_opt = clone_optimizer(optimizer)
        resumed = SyntheticExpansion(short_enabled=short_enabled)
        resumed_opt = make_optimizer(resumed)
        loaded = cp.load_checkpoint(
            directory, resumed, resumed_opt, binding, sources=versioned_sources
        )
        assert loaded == dict(
            step=781,
            elapsed_seconds=0.5,
            model_identity=pointer["model_identity"],
            checkpoint_SHA256=pointer["SHA256"],
            trainer_state=dict(status="RUNNING", history=[dict(step=1)]),
        )
        assert resumed.training
        assert random.random() == rng_next[0] and np.random.random() == rng_next[1]
        assert torch.equal(torch.rand(3), rng_next[2])
        update(resumed, resumed_opt)
        assert all(torch.equal(resumed.state_dict()[k], v) for k, v in expected.items())
        assert_optimizer_equal(expected_opt, resumed_opt.state_dict())
        resumed.eval()
        sample = torch.ones(2, 4, dtype=torch.float64)
        expected_eval = resumed(sample).detach()
        cp.save_checkpoint(directory, resumed, resumed_opt, binding, step=782, elapsed_seconds=0.7)
        cp.load_checkpoint(directory, model, optimizer, binding)
        assert not model.training and torch.equal(model(sample), expected_eval)


def test_corrupt_bytes_rejected_before_deserialization(tmp_path, monkeypatch):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        pointer = cp.save_checkpoint(directory, model, optimizer, binding, step=3)
        file = directory / pointer["file"]
        file.write_bytes(file.read_bytes() + b"corrupt")
        monkeypatch.setattr(
            cp.torch, "load", lambda *a, **k: pytest.fail("unsafe byte mismatch deserialized")
        )
        with pytest.raises(ValueError, match="bytes"):
            cp.load_checkpoint(directory, model, optimizer, binding)


def test_bound_sources_births_and_source_set_reject(tmp_path, monkeypatch):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        cp.save_checkpoint(directory, model, optimizer, binding, step=3)
        changed = versioned_sources()
        changed[next(iter(changed))] = "0" * 64
        with pytest.raises(ValueError, match="source"):
            cp.load_checkpoint(directory, model, optimizer, binding, sources=lambda: changed)
        with monkeypatch.context() as patch:
            patch.setattr(cp, "source_identity", lambda: {})
            with pytest.raises(ValueError, match="source"):
                cp.load_checkpoint(directory, model, optimizer, binding)
    algorithm = copy.deepcopy(binding["specification"]["algorithm"])
    algorithm["parameter_birth_steps"]["r_head.bias"] = 0
    wrong_birth = run_binding(
        model,
        data_split_identity="SYNTHETIC_TRAIN_ONLY",
        feature_batch_size=2,
        max_steps=7,
        algorithm=algorithm,
    )
    with cp.run_guard(tmp_path / "wrong-birth", wrong_birth) as directory:
        with pytest.raises(ValueError, match="birth"):
            cp.save_checkpoint(directory, model, optimizer, wrong_birth, step=3)
    del algorithm["parameter_birth_steps"]["base.0.weight"]
    missing = run_binding(
        model,
        data_split_identity="SYNTHETIC_TRAIN_ONLY",
        feature_batch_size=2,
        max_steps=7,
        algorithm=algorithm,
    )
    with cp.run_guard(tmp_path / "missing-birth", missing) as directory:
        with pytest.raises(ValueError, match="Every parameter"):
            cp.save_checkpoint(directory, model, optimizer, missing, step=3)


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("global_step", "step/model"),
        ("old_age", "Adam age"),
        ("new_age", "Adam age"),
        ("negative_second_moment", "moments"),
        ("nan_moment", "moments"),
        ("moment_shape", "moments"),
        ("moment_dtype", "moments"),
        ("extra_parameter", "Unexpected Adam"),
        ("optimizer_lr", "configuration"),
        ("optimizer_order", "configuration"),
        ("model_dtype", "model snapshot"),
        ("rng_missing", "RNG"),
        ("training_flag", "trainer identity"),
    ],
)
def test_rehashed_invalid_snapshot_rejected_before_state_mutation(tmp_path, mutation, match):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        update(model, optimizer)
        cp.save_checkpoint(directory, model, optimizer, binding, step=4)
        before_model, before_optimizer = (
            copy.deepcopy(model.state_dict()),
            clone_optimizer(optimizer),
        )
        before_rng = torch.get_rng_state().clone()

        def corrupt(state):
            states = state["optimizer"]["state"]
            old, new = min(states), max(states)
            if mutation == "global_step":
                state["step"] += 1
            elif mutation == "old_age":
                states[old]["step"] += 1
            elif mutation == "new_age":
                states[new]["step"] = torch.tensor(4.0)
            elif mutation == "negative_second_moment":
                states[old]["exp_avg_sq"].flatten()[0] = -1
            elif mutation == "nan_moment":
                states[old]["exp_avg"].flatten()[0] = float("nan")
            elif mutation == "moment_shape":
                states[old]["exp_avg"] = torch.zeros(1)
            elif mutation == "moment_dtype":
                states[old]["exp_avg"] = states[old]["exp_avg"].float()
            elif mutation == "extra_parameter":
                states[999] = copy.deepcopy(states[old])
            elif mutation == "optimizer_lr":
                state["optimizer"]["param_groups"][0]["lr"] *= 2
            elif mutation == "optimizer_order":
                state["optimizer"]["param_groups"][0]["params"].reverse()
            elif mutation == "model_dtype":
                state["model"]["r_head.weight"] = state["model"]["r_head.weight"].float()
            elif mutation == "rng_missing":
                del state["rng"]["numpy"]
            elif mutation == "training_flag":
                state["training"] = 1

        rewrite_snapshot(directory, corrupt)
        with pytest.raises(ValueError, match=match):
            cp.load_checkpoint(directory, model, optimizer, binding)
        assert all(torch.equal(model.state_dict()[k], v) for k, v in before_model.items())
        assert_optimizer_equal(before_optimizer, optimizer.state_dict())
        assert torch.equal(torch.get_rng_state(), before_rng)


def test_newborn_head_state_and_pending_gradient_rejected(tmp_path):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        parameter = model.r_head.weight
        optimizer.state[parameter] = dict(
            step=torch.tensor(0.0),
            exp_avg=torch.zeros_like(parameter),
            exp_avg_sq=torch.zeros_like(parameter),
        )
        with pytest.raises(ValueError, match="Newborn"):
            cp.save_checkpoint(directory, model, optimizer, binding, step=3)
        del optimizer.state[parameter]
        parameter.grad = torch.zeros_like(parameter)
        with pytest.raises(ValueError, match="pending gradients"):
            cp.save_checkpoint(directory, model, optimizer, binding, step=3)


def test_failed_partial_gradient_can_roll_back_but_adam_flags_cannot_change(tmp_path):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        cp.save_checkpoint(directory, model, optimizer, binding, step=3)
        model.r_head.bias.grad = torch.full_like(model.r_head.bias, float("nan"))
        cp.load_checkpoint(directory, model, optimizer, binding)
        assert all(p.grad is None for p in model.parameters())
        for flag, value in [("fused", True), ("capturable", True), ("differentiable", True)]:
            optimizer.param_groups[0][flag] = value
            with pytest.raises(ValueError, match="configuration"):
                cp.load_checkpoint(directory, model, optimizer, binding)
            optimizer.param_groups[0][flag] = None if flag == "fused" else False


def test_progress_bounds_elapsed_and_pointer_interruption(tmp_path, monkeypatch):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        initial = cp.save_checkpoint(
            directory, model, optimizer, binding, step=3, elapsed_seconds=0.5
        )
        for step, elapsed in [(2, 0.5), (8, 0.5), (True, 0.5), (3, float("nan")), (3, -1)]:
            with pytest.raises(ValueError, match="global step"):
                cp.save_checkpoint(
                    directory, model, optimizer, binding, step=step, elapsed_seconds=elapsed
                )
        with pytest.raises(ValueError, match="backwards"):
            cp.save_checkpoint(directory, model, optimizer, binding, step=3, elapsed_seconds=0.4)
        update(model, optimizer)
        with monkeypatch.context() as patch:

            def interrupt(path, record):
                raise InterruptedError("before pointer swap")

            patch.setattr(cp, "_atomic_json", interrupt)
            with pytest.raises(InterruptedError):
                cp.save_checkpoint(
                    directory, model, optimizer, binding, step=4, elapsed_seconds=0.6
                )
        assert json.loads((directory / "latest.json").read_text()) == initial
        assert cp.load_checkpoint(directory, model, optimizer, binding)["step"] == 3


def test_exact_old_sources_remain_frozen():
    root = Path(cp.__file__).resolve().parents[2]
    import subprocess

    prefixes = [
        "modules/temporal_two_expert",
        "modules/temporal_risk_proxy_v2",
        "modules/temporal_surrogate_resume_v2",
    ]
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", *prefixes], cwd=root, text=True
    ).splitlines()
    assert "modules/temporal_two_expert/checkpoint.py" in names
    for name in [n for n in names if n.endswith(".py")]:
        assert (root / name).read_bytes() == subprocess.check_output(
            ["git", "show", f"HEAD:{name}"], cwd=root
        )
