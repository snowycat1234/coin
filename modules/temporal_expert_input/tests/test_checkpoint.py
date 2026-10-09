"""Synthetic mechanics for two newborn readouts; no historical optimizer fitting."""

import copy
import json
import math
import random
import subprocess
from pathlib import Path

import numpy as np
import pytest
import torch
from torch import nn

from modules.temporal_expert_input import checkpoint as cp
from modules.temporal_short_expansion.stage import sources as frozen_sources
from modules.temporal_short_expansion.tests.test_checkpoint import (
    SyntheticExpansion,
    assert_optimizer_equal,
    clone_optimizer,
    rewrite_snapshot,
)
from modules.temporal_short_expansion.tests.test_checkpoint import (
    warm_case as warm_short_case,
)
from modules.temporal_two_expert.checkpoint import make_optimizer, run_binding
from modules.temporal_two_expert.exact import sha


@pytest.fixture(scope="module", autouse=True)
def deterministic_cpu():
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


class SyntheticExpertInput(SyntheticExpansion):
    def __init__(self, base=None, *, input_enabled):
        super().__init__(base, short_enabled=True)
        self.expert_projection = nn.Linear(18, 32, bias=False, dtype=torch.float64)
        nn.init.zeros_(self.expert_projection.weight)
        nn.init.zeros_(self.r_head.weight)
        nn.init.constant_(self.r_head.bias, math.log(0.01 / 0.99))
        self.input_enabled = input_enabled
        self.contract = dict(
            schema="SYNTHETIC_CURRENT_EXPERT_INPUT",
            input_enabled=input_enabled,
            expert_projection_shape=[32, 18],
            short_enabled=True,
        )

    def forward(self, values, expert_input):
        hidden = self.base[2](self.base[1](self.base[0](values)))
        projection = self.expert_projection(expert_input)
        if not self.input_enabled:
            projection = projection * 0.0
        hidden = hidden + projection
        return self.base[3](hidden) + torch.sigmoid(self.r_head(hidden))


def sources():
    root = Path(cp.__file__).resolve().parents[2]
    return {
        **frozen_sources(),
        **{str(p.relative_to(root)): sha(p) for p in Path(cp.__file__).parent.glob("*.py")},
    }


def warm_case(*, parent_step=3, input_enabled=True):
    previous, previous_optimizer, _ = warm_short_case(parent_step=parent_step)
    model = SyntheticExpertInput(previous.base, input_enabled=input_enabled)
    optimizer = make_optimizer(model)
    for parameter in model.base.parameters():
        optimizer.state[parameter] = copy.deepcopy(previous_optimizer.state[parameter])
    binding = run_binding(
        model,
        data_split_identity=dict(role="TRAIN", target_clock="available<=decision"),
        feature_batch_size=2,
        max_steps=parent_step + 4,
        algorithm=dict(
            parent=dict(step=parent_step),
            versioned_sources=sources(),
            parameter_birth_steps={
                n: 0 if n.startswith("base.") else parent_step for n, _ in model.named_parameters()
            },
        ),
    )
    return model, optimizer, binding


def update(model, optimizer):
    model.train()
    optimizer.zero_grad(set_to_none=True)
    output = model(torch.randn(3, 4, dtype=torch.float64), torch.randn(3, 18, dtype=torch.float64))
    (output - random.random() - float(np.random.random())).square().mean().backward()
    assert all(p.grad is not None for p in model.parameters())
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0, error_if_nonfinite=True)
    optimizer.step()
    optimizer.zero_grad(set_to_none=True)


@pytest.mark.parametrize("enabled", [False, True])
def test_warm_780_two_births_exact_next_update_rng_and_serialization(tmp_path, enabled):
    model, optimizer, binding = warm_case(parent_step=780, input_enabled=enabled)
    births = binding["specification"]["algorithm"]["parameter_birth_steps"]
    cp.validate_moments(model, optimizer, 780, births)
    assert sum(p.numel() for n, p in model.named_parameters() if not n.startswith("base.")) == 609
    assert all(
        not optimizer.state.get(p) for n, p in model.named_parameters() if not n.startswith("base.")
    )
    torch.manual_seed(193)
    random.seed(197)
    np.random.seed(199)
    with cp.run_guard(tmp_path / "run", binding) as directory:
        initial = cp.save_checkpoint(
            directory, model, optimizer, binding, step=780, sources=sources
        )
        initial_bytes = (directory / initial["file"]).read_bytes()
        cp.load_checkpoint(directory, model, optimizer, binding, sources=sources)
        assert all(
            not optimizer.state.get(p)
            for n, p in model.named_parameters()
            if not n.startswith("base.")
        )
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
            if name == "expert_projection.weight" and not enabled:
                assert torch.count_nonzero(optimizer.state[parameter]["exp_avg"]) == 0
                assert torch.count_nonzero(optimizer.state[parameter]["exp_avg_sq"]) == 0
        expected_rng_draw = (random.random(), np.random.random(), torch.rand(3))
        update(model, optimizer)
        expected, expected_opt = copy.deepcopy(model.state_dict()), clone_optimizer(optimizer)
        resumed = SyntheticExpertInput(input_enabled=enabled)
        resumed_optimizer = make_optimizer(resumed)
        saved = cp.load_checkpoint(directory, resumed, resumed_optimizer, binding, sources=sources)
        assert saved["step"] == 781 and saved["checkpoint_SHA256"] == pointer["SHA256"]
        assert saved["trainer_state"] == dict(status="RUNNING", history=[dict(step=1)])
        assert (
            random.random() == expected_rng_draw[0] and np.random.random() == expected_rng_draw[1]
        )
        assert torch.equal(torch.rand(3), expected_rng_draw[2])
        update(resumed, resumed_optimizer)
        assert all(torch.equal(resumed.state_dict()[k], v) for k, v in expected.items())
        assert_optimizer_equal(expected_opt, resumed_optimizer.state_dict())
        resumed.eval()
        x, ex = torch.ones(2, 4, dtype=torch.float64), torch.ones(2, 18, dtype=torch.float64)
        before = resumed(x, ex).detach()
        cp.save_checkpoint(
            directory, resumed, resumed_optimizer, binding, step=782, elapsed_seconds=0.6
        )
        model.expert_projection.weight.grad = torch.full_like(
            model.expert_projection.weight, float("nan")
        )
        cp.load_checkpoint(directory, model, optimizer, binding)
        assert not model.training and all(p.grad is None for p in model.parameters())
        assert torch.equal(model(x, ex), before)


@pytest.mark.parametrize(
    "mutation", ["projection_birth", "short_birth", "base_birth", "missing", "extra"]
)
def test_wrong_or_missing_parameter_births_rejected(tmp_path, mutation):
    model, optimizer, binding = warm_case()
    algorithm = copy.deepcopy(binding["specification"]["algorithm"])
    births = algorithm["parameter_birth_steps"]
    if mutation == "projection_birth":
        births["expert_projection.weight"] = 0
    elif mutation == "short_birth":
        births["r_head.bias"] = 0
    elif mutation == "base_birth":
        births["base.0.weight"] = 3
    elif mutation == "missing":
        del births["expert_projection.weight"]
    elif mutation == "extra":
        births["expert_projection.bias"] = 3
    changed = run_binding(
        model,
        data_split_identity="synthetic",
        feature_batch_size=2,
        max_steps=7,
        algorithm=algorithm,
    )
    with cp.run_guard(tmp_path / "run", changed) as directory:
        with pytest.raises(ValueError, match="birth"):
            cp.save_checkpoint(directory, model, optimizer, changed, step=3)


@pytest.mark.parametrize(
    "mutation,match",
    [
        ("projection_age", "Adam age"),
        ("short_age", "Adam age"),
        ("old_age", "Adam age"),
        ("projection_moment_shape", "moments"),
        ("projection_negative_square", "moments"),
        ("projection_nan", "model snapshot"),
        ("projection_dtype", "model snapshot"),
        ("projection_missing", "model snapshot"),
        ("global_step", "step/model"),
        ("optimizer_lr", "configuration"),
        ("rng_missing", "RNG"),
    ],
)
def test_rehashed_invalid_snapshots_rejected_without_mutation(tmp_path, mutation, match):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        update(model, optimizer)
        cp.save_checkpoint(directory, model, optimizer, binding, step=4)
        before, before_opt, rng = (
            copy.deepcopy(model.state_dict()),
            clone_optimizer(optimizer),
            torch.get_rng_state().clone(),
        )
        identifiers = dict(
            zip(
                dict(model.named_parameters()),
                optimizer.state_dict()["param_groups"][0]["params"],
                strict=True,
            )
        )

        def corrupt(state):
            states = state["optimizer"]["state"]
            projection = states[identifiers["expert_projection.weight"]]
            if mutation == "projection_age":
                projection["step"] = torch.tensor(4.0)
            elif mutation == "short_age":
                states[identifiers["r_head.bias"]]["step"] = torch.tensor(4.0)
            elif mutation == "old_age":
                states[identifiers["base.0.weight"]]["step"] = torch.tensor(1.0)
            elif mutation == "projection_moment_shape":
                projection["exp_avg"] = torch.zeros(1)
            elif mutation == "projection_negative_square":
                projection["exp_avg_sq"].flatten()[0] = -1
            elif mutation == "projection_nan":
                state["model"]["expert_projection.weight"].flatten()[0] = float("nan")
            elif mutation == "projection_dtype":
                state["model"]["expert_projection.weight"] = state["model"][
                    "expert_projection.weight"
                ].float()
            elif mutation == "projection_missing":
                del state["model"]["expert_projection.weight"]
            elif mutation == "global_step":
                state["step"] += 1
            elif mutation == "optimizer_lr":
                state["optimizer"]["param_groups"][0]["lr"] *= 2
            elif mutation == "rng_missing":
                del state["rng"]["torch"]

        rewrite_snapshot(directory, corrupt)
        with pytest.raises(ValueError, match=match):
            cp.load_checkpoint(directory, model, optimizer, binding)
        assert all(torch.equal(model.state_dict()[k], v) for k, v in before.items())
        assert_optimizer_equal(before_opt, optimizer.state_dict())
        assert torch.equal(rng, torch.get_rng_state())


def test_exact_bytes_sources_clock_binding_and_input_arm_required(tmp_path, monkeypatch):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        pointer = cp.save_checkpoint(directory, model, optimizer, binding, step=3)
        changed_sources = sources()
        changed_sources[next(iter(changed_sources))] = "0" * 64
        with pytest.raises(ValueError, match="source"):
            cp.load_checkpoint(
                directory, model, optimizer, binding, sources=lambda: changed_sources
            )
        clock_binding = run_binding(
            model,
            data_split_identity=dict(role="TRAIN", target_clock="changed"),
            feature_batch_size=2,
            max_steps=7,
            algorithm=binding["specification"]["algorithm"],
        )
        with pytest.raises(ValueError, match="binding"):
            cp.load_checkpoint(directory, model, optimizer, clock_binding)
        other = SyntheticExpertInput(input_enabled=False)
        with pytest.raises(ValueError, match="binding"):
            cp.load_checkpoint(directory, other, make_optimizer(other), binding)
        file = directory / pointer["file"]
        file.write_bytes(file.read_bytes() + b"corrupt")
        monkeypatch.setattr(
            cp.torch, "load", lambda *a, **kw: pytest.fail("corrupt bytes deserialized")
        )
        with pytest.raises(ValueError, match="bytes"):
            cp.load_checkpoint(directory, model, optimizer, binding)


def test_atomic_interruption_keeps_warm_generation_and_progress_bounds(tmp_path, monkeypatch):
    model, optimizer, binding = warm_case()
    with cp.run_guard(tmp_path / "run", binding) as directory:
        initial = cp.save_checkpoint(
            directory, model, optimizer, binding, step=3, elapsed_seconds=0.5
        )
        for step, elapsed in ((2, 0.5), (8, 0.5), (3, float("nan")), (3, -1)):
            with pytest.raises(ValueError, match="global step"):
                cp.save_checkpoint(
                    directory, model, optimizer, binding, step=step, elapsed_seconds=elapsed
                )
        with pytest.raises(ValueError, match="backwards"):
            cp.save_checkpoint(directory, model, optimizer, binding, step=3, elapsed_seconds=0.4)
        update(model, optimizer)

        def disconnect(path, record):
            raise InterruptedError("before atomic pointer publication")

        with monkeypatch.context() as patch:
            patch.setattr(cp, "_atomic_json", disconnect)
            with pytest.raises(InterruptedError):
                cp.save_checkpoint(
                    directory, model, optimizer, binding, step=4, elapsed_seconds=0.6
                )
        assert json.loads((directory / "latest.json").read_text()) == initial
        restored = cp.load_checkpoint(directory, model, optimizer, binding)
        assert restored["step"] == 3 and all(
            not optimizer.state.get(p)
            for n, p in model.named_parameters()
            if not n.startswith("base.")
        )


def test_all_frozen_sources_unchanged():
    root = Path(cp.__file__).resolve().parents[2]
    prefixes = [
        "modules/temporal_two_expert",
        "modules/temporal_risk_proxy_v2",
        "modules/temporal_surrogate_resume_v2",
        "modules/temporal_short_expansion",
    ]
    names = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", "HEAD", "--", *prefixes], cwd=root, text=True
    ).splitlines()
    assert "modules/temporal_short_expansion/checkpoint.py" in names
    for name in (n for n in names if n.endswith(".py")):
        assert (root / name).read_bytes() == subprocess.check_output(
            ["git", "show", f"HEAD:{name}"], cwd=root
        )
