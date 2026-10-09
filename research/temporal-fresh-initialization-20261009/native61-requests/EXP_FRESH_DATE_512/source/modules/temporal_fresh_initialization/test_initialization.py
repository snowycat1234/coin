"""No historical fit: fresh state, terminal barrier and native export API checks."""

import json
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from modules.temporal_expert_input.checkpoint import load_checkpoint, save_checkpoint
from modules.temporal_prequential_transfer.model import initialize, parameter_identity
from modules.temporal_two_expert.checkpoint import _rng_state, model_identity, run_guard
from modules.temporal_two_expert.exact import sha
from modules.temporal_two_expert.test_temporal import samples

from . import export, stage


def test_same_fresh_recipe_empty_adam_and_birth_zero():
    _, scaler = samples()
    first, optimizer = initialize(scaler)
    raw, rng = parameter_identity(first), stage.tree_identity(_rng_state())
    second, other = initialize(scaler)
    assert first.parameter_count == second.parameter_count == 13699
    assert raw == parameter_identity(second) and rng == stage.tree_identity(_rng_state())
    assert not optimizer.state and not other.state
    binding = stage.binding_for(first, dict(scaler=scaler.identity))
    algorithm = binding["specification"]["algorithm"]
    assert set(algorithm["parameter_birth_steps"].values()) == {0}
    assert algorithm["parent"] == dict(step=0, fresh=True)
    assert algorithm["mixing"] == 0 and algorithm["objective_version"] == 2
    assert stage.PROTOCOL["planned_fits"] == 1 and stage.PROTOCOL["fixed_updates"] == 512


def test_step_zero_checkpoint_roundtrip_and_changed_data_rejection(tmp_path):
    _, scaler = samples()
    model, optimizer = initialize(scaler)
    binding = stage.binding_for(model, dict(scaler=scaler.identity, data="exact"))
    rng = stage.tree_identity(_rng_state())
    with run_guard(tmp_path / "initial", binding) as folder:
        save_checkpoint(folder, model, optimizer, binding, step=0, sources=stage.sources)
        restored, other = initialize(scaler)
        saved = load_checkpoint(folder, restored, other, binding, sources=stage.sources)
        assert saved["step"] == 0 and not other.state
        assert model_identity(restored) == model_identity(model)
        assert stage.tree_identity(_rng_state()) == rng
        wrong = stage.binding_for(restored, dict(scaler=scaler.identity, data="changed"))
        with pytest.raises(ValueError, match="binding"):
            load_checkpoint(folder, restored, other, wrong, sources=stage.sources)


@pytest.mark.parametrize(
    "field,value",
    [
        ("step", 511),
        ("model_identity", "different"),
        ("checkpoint_SHA256", "different"),
    ],
)
def test_actual512_checkpoint_required(field, value):
    terminal = dict(
        status=stage.SUCCESS,
        completed_updates=512,
        fixed_target=512,
        model_identity="m",
        checkpoint_SHA256="c",
    )
    saved = dict(step=512, model_identity="m", checkpoint_SHA256="c")
    stage.validate_terminal(terminal, saved)
    saved[field] = value
    with pytest.raises(ValueError, match="actual checkpoint"):
        stage.validate_terminal(terminal, saved)


def test_frozen_state_supplies_validated_binding_omitted_by_loader(tmp_path, monkeypatch):
    _, scaler = samples()
    model, optimizer = initialize(scaler)
    binding = stage.binding_for(model, dict(scaler=scaler.identity))
    terminal = dict(
        status=stage.SUCCESS,
        completed_updates=512,
        fixed_target=512,
        model_identity=model_identity(model),
        checkpoint_SHA256="c",
    )
    folder = tmp_path / stage.ARM
    folder.mkdir()
    (folder / "TERMINAL.json").write_text(json.dumps(terminal))
    monkeypatch.setattr(
        stage, "load_inputs", lambda *a, **kw: ([], [], None, dict(scaler=scaler.identity), scaler)
    )
    # Match the exact frozen loader's return API: no binding key.
    monkeypatch.setattr(
        stage,
        "load_checkpoint",
        lambda *a, **kw: dict(
            step=512, model_identity=model_identity(model), checkpoint_SHA256="c"
        ),
    )
    saved = stage.frozen_state(None, tmp_path)[6]
    assert saved["binding"] == binding and not optimizer.state


def test_gate_equations_report_cash_short_and_saturation():
    s, w, r = np.array([0.5, 0.9999]), np.array([0.2, 0.9999]), np.array([0.01, 0.9999])
    requests = np.zeros((2, 6))
    requests[:, 0] = 1 - s
    requests[:, 1] = s * (1 - r) * (1 - w)
    requests[:, 4] = s * (1 - r) * w
    requests[:, 5] = s * r
    stats = export.gate_statistics(requests)
    for name, value in [("s", s), ("w", w), ("r", r)]:
        assert stats[name]["mean"] == pytest.approx(value.mean())
        assert stats[name]["fraction_gt99"] == 0.5
    with pytest.raises(ValueError, match="denominators"):
        export.gate_statistics(np.array([[1, 0, 0, 0, 0, 0.0]]))


@pytest.fixture
def native_bundle(tmp_path, monkeypatch):
    windows, scaler = samples(61)
    model, optimizer = initialize(scaler)
    count, decision = 61, windows.decision_us
    episode = SimpleNamespace(
        contexts=tuple(range(count)),
        windows=windows,
        eligible=np.ones((count, 6), bool),
        expert_state=np.zeros((count, 18)),
        expert_input_available_us=np.tile(decision[:, None], (1, 3)),
        expert_targets=np.zeros((count, 6, 5)),
        target_available_us=np.tile(decision[:, None], (1, 6)),
    )
    train = [
        SimpleNamespace(
            split_cutoff_us=int(decision[0]),
            label_available_us=np.array([decision[0] - 1]),
            windows=SimpleNamespace(
                valid=np.ones((1, 1, 5, 24), bool),
                available_us=np.full((1, 1, 5, 24), decision[0] - 1),
            ),
            expert_input_available_us=np.array([[decision[0] - 1]]),
        )
    ]
    folder = tmp_path / "fit"
    folder.mkdir()
    checkpoint = folder / "test-snapshot.pt"
    checkpoint.write_bytes(b"synthetic export checkpoint; no optimizer updates")
    binding = dict(run_id="test", specification=dict(sources={}))
    saved = dict(
        step=512,
        model_identity=model_identity(model),
        checkpoint_SHA256=sha(checkpoint),
        binding=binding,
    )
    terminal = dict(
        status=stage.SUCCESS,
        completed_updates=512,
        fixed_target=512,
        model_identity=saved["model_identity"],
        checkpoint_SHA256=saved["checkpoint_SHA256"],
    )
    pointer = dict(
        step=512,
        SHA256=sha(checkpoint),
        model_identity=saved["model_identity"],
        file=checkpoint.name,
        run_id="test",
    )
    for name, content in [
        ("RUN.json", binding),
        ("TERMINAL.json", terminal),
        ("latest.json", pointer),
    ]:
        (folder / name).write_text(json.dumps(content))
    (tmp_path / "four-fit").mkdir()
    np.savez_compressed(
        tmp_path / "four-fit/SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
    )
    requests = torch.tensor([[0.5, 0.2475, 0, 0, 0.2475, 0.005]] * count, dtype=torch.float64)
    monkeypatch.setattr(
        export,
        "frozen_state",
        lambda *a: (train, [episode], None, model, optimizer, folder, saved, terminal),
    )
    monkeypatch.setattr(export, "predict_episode", lambda *a, **kw: requests)
    monkeypatch.setattr(export, "sources", lambda: {})
    bundle = tmp_path / "native"
    receipt = export.export_native(tmp_path, tmp_path, bundle, stage.COMPARATOR_COMMIT)
    assert receipt["completed_updates"] == 512 and not optimizer.state
    return bundle, model, saved, terminal, episode


def test_full_native_export_api_and_repeatable_validation(native_bundle):
    bundle, model, saved, terminal, episode = native_bundle
    before = stage.tree_identity(_rng_state())
    manifest = export.validate_native_bundle(bundle, model, saved, terminal, episode)
    assert len(manifest["files"]) == 8 and before == stage.tree_identity(_rng_state())


@pytest.mark.parametrize("case", ["missing_checkpoint", "tampered_request", "forged_clock"])
def test_native_barrier_rejects_incomplete_or_changed_bundle(native_bundle, case):
    bundle, model, saved, terminal, episode = native_bundle
    if case == "missing_checkpoint":
        (bundle / "MODEL_ADAM_RNG.pt").unlink()
    else:
        with np.load(bundle / "REQUESTS.npz", allow_pickle=False) as z:
            arrays = {name: z[name].copy() for name in z.files}
        if case == "tampered_request":
            arrays["desired_expert_budget"][0, 2] = 0.1
        else:
            arrays["feature_available_us"][0] += 1
        np.savez_compressed(bundle / "REQUESTS.npz", **arrays)
        if case == "forged_clock":
            # Even a matching file hash cannot bless altered causal metadata.
            manifest = json.loads((bundle / "MANIFEST.json").read_text())
            manifest["files"]["REQUESTS.npz"] = dict(
                bytes=(bundle / "REQUESTS.npz").stat().st_size, sha256=sha(bundle / "REQUESTS.npz")
            )
            (bundle / "MANIFEST.json").write_text(json.dumps(manifest))
    with pytest.raises((ValueError, AssertionError)):
        export.validate_native_bundle(bundle, model, saved, terminal, episode)


def test_all_reused_economic_and_new_orchestration_sources_bound():
    bound = stage.sources()
    for name in [
        "modules/temporal_episode_weighting_v2/gradient.py",
        "modules/temporal_risk_proxy_v2/proxy.py",
        "modules/temporal_expert_input/checkpoint.py",
        "modules/temporal_prequential_transfer/model.py",
        "modules/temporal_fresh_initialization/export.py",
        "modules/temporal_fresh_initialization/test_initialization.py",
    ]:
        assert name in bound
