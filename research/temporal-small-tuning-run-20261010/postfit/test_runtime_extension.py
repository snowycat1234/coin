"""Operational overlay tests: no optimizer update, inference or economic rollout."""

import inspect
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest
import RUNTIME_EXTENSION as extension
import torch
from modules.temporal_episode_weighting_v2.stage import tree_identity
from modules.temporal_prequential_transfer.model import initialize
from modules.temporal_small_tuning import controller, stage
from modules.temporal_small_tuning.checkpoint import (
    binding_for,
    load,
    optimizer_for,
    save,
)
from modules.temporal_small_tuning.protocol import plan, sources
from modules.temporal_two_expert.checkpoint import _atomic_json, _rng_state, run_guard
from modules.temporal_two_expert.inputs import Standardizer
from modules.temporal_two_expert.test_temporal import samples


@pytest.fixture(autouse=True)
def deterministic_no_updates(monkeypatch):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)

    def forbidden(*args, **kwargs):
        raise AssertionError("No optimizer updates or inference in operational tests")

    monkeypatch.setattr(torch.optim.Adam, "step", forbidden)
    monkeypatch.setattr(torch.nn.Module, "_call_impl", forbidden)


def test_exact_guard_constants_bytecode_signature_and_sources():
    hashes = sources()
    original = {
        fn: extension.code_record(fn.__code__) for fn in (stage.train_slice, controller.main)
    }
    for fn, is_controller in ((stage.train_slice, False), (controller.main, True)):
        changed = extension.patched_function(fn, controller=is_controller)
        assert changed.__code__.co_code == fn.__code__.co_code
        assert inspect.signature(changed) == inspect.signature(fn)
        extension._same_except_guard(fn.__code__, changed.__code__)
    patched_stage = extension.patched_function(stage.train_slice)
    assert 5400.0 in patched_stage.__code__.co_consts
    patched_controller = extension.patched_function(controller.main, controller=True)
    queue = next(
        c
        for c in patched_controller.__code__.co_consts
        if isinstance(c, types.CodeType) and c.co_name == "worker_queue"
    )
    assert sum(type(c) is int and c == 5400 for c in queue.co_consts) == 1
    assert sum(type(c) is float and c == 5400 for c in queue.co_consts) == 1
    assert 1100.0 in queue.co_consts
    assert 12000 in queue.co_consts
    assert 1024 in patched_stage.__code__.co_consts
    assert original == {fn: extension.code_record(fn.__code__) for fn in original}
    assert sources() == hashes and len(hashes) == 77


def test_unexpected_guard_source_fails_closed():
    def wrong():
        return 3601.0

    with pytest.raises(ValueError, match="exactly one"):
        extension.patched_function(wrong)


@pytest.fixture
def fake_proc(tmp_path, monkeypatch):
    root = tmp_path / "proc"
    root.mkdir()

    def path(*parts):
        if parts and parts[0] == "/proc":
            return Path(root, *parts[1:])
        return Path(*parts)

    monkeypatch.setattr(extension, "Path", path)

    def process(pid, state, tokens=()):
        folder = root / str(pid)
        folder.mkdir(exist_ok=True)
        (folder / "stat").write_bytes(f"{pid} (name with ) spaces) {state} 1 2\n".encode())
        (folder / "cmdline").write_bytes(b"\0".join(tokens) + b"\0")
        return folder

    return process


@pytest.mark.parametrize(
    "command",
    [
        [b"modules/temporal_small_tuning/controller.py"],
        [b"/workspace/coin-temporal/modules/temporal_small_tuning/controller.py"],
        [b"-m", b"modules.temporal_small_tuning", b"worker"],
        [str(extension.ROOT / "RUNTIME_EXTENSION.py").encode(), b"continue"],
        [str(extension.ROOT / "RUNTIME_EXTENSION.py").encode(), b"controller"],
    ],
)
def test_quiet_rejects_live_own_relative_absolute_module_and_overlay(tmp_path, fake_proc, command):
    output = tmp_path / "run"
    fake_proc(1234, "S", [b"python", *command, b"--output", str(output).encode()])
    with pytest.raises(ValueError, match="still active"):
        extension.assert_quiet(output, original_pid=None)


def test_quiet_checks_supplied_pid_and_ignores_exited_zombies(tmp_path, fake_proc):
    output = tmp_path / "run"
    fake_proc(1234, "R")
    with pytest.raises(ValueError, match="PID is still active"):
        extension.assert_quiet(output, original_pid=1234)
    fake_proc(
        1234,
        "Z",
        [
            b"python",
            b"modules/temporal_small_tuning/controller.py",
            str(output).encode(),
        ],
    )
    extension.assert_quiet(output, original_pid=1234)
    extension.assert_quiet(output, original_pid=5678)


def test_quiet_allows_unrelated_processes_and_other_outputs(tmp_path, fake_proc):
    output = tmp_path / "run"
    fake_proc(1234, "S", [b"python", b"unrelated.py", str(output).encode()])
    fake_proc(
        2345,
        "S",
        [
            b"python",
            b"modules/temporal_small_tuning/controller.py",
            str(tmp_path / "other").encode(),
        ],
    )
    extension.assert_quiet(output, original_pid=None)


def test_quiet_fails_closed_on_unreadable_process_state(tmp_path, fake_proc):
    folder = fake_proc(1234, "S")
    (folder / "stat").write_bytes(b"invalid stat")
    with pytest.raises(ValueError, match="Cannot verify"):
        extension.assert_quiet(tmp_path / "run", original_pid=1234)


def test_existing_clock_and_slice_indices_retained(tmp_path):
    for i, elapsed in enumerate((1100.0, 1100.25, 1101.25, 300.0), 1):
        _atomic_json(tmp_path / f"RESOURCE_SLICE_{i:02d}.json", dict(elapsed_seconds=elapsed))
    elapsed, paths = extension.resource_clock(tmp_path)
    assert elapsed == 3601.5 and len(paths) == 4
    _atomic_json(tmp_path / "RESOURCE_SLICE_06.json", dict(elapsed_seconds=1.0))
    with pytest.raises(ValueError, match="contiguous"):
        extension.resource_clock(tmp_path)


def fixture_run(tmp_path, status, terminal=True):
    _, scaler = samples()
    settings = plan()["actual_fit_tasks"][0]
    task_id = settings["task_id"]
    folder = tmp_path / task_id
    model, _ = initialize(scaler)
    optimizer = optimizer_for(model, settings)
    binding = binding_for(model, dict(synthetic_operational_test=True), settings)
    history = dict(
        status=status,
        completed_updates=0,
        best=None,
        validation=[],
        training_diagnostics=[],
        slices=[],
        failure=None,
    )
    with run_guard(folder, binding):
        pointer = save(folder, model, optimizer, binding, step=0, elapsed=3600.0, history=history)
    import numpy as np

    np.savez_compressed(
        folder / "SCALER.npz", mean=scaler.mean, scale=scaler.scale, count=scaler.count
    )
    _atomic_json(
        folder / "SCALER.json",
        dict(identity=scaler.identity, provenance=scaler.provenance),
    )
    if terminal:
        _atomic_json(
            folder / "TERMINAL.json",
            dict(status=status, latest=pointer, completed_updates=0, settings=settings),
        )
    for index in (1, 2):
        _atomic_json(folder / f"RESOURCE_SLICE_{index:02d}.json", dict(elapsed_seconds=1800.0))
    ready = {}
    for setting in plan()["actual_fit_tasks"]:
        ready[setting["task_id"]] = dict(settings=setting)
        if setting["task_id"] != task_id:
            other = tmp_path / setting["task_id"]
            other.mkdir()
            _atomic_json(other / "TERMINAL.json", dict(status="EARLY_STOP_RULE"))
    _atomic_json(tmp_path / "READY.json", dict(tasks=ready, sources=sources()))
    _atomic_json(
        tmp_path / "CONTROLLER_RECEIPT.json",
        dict(
            status="SIX_FIXED_TASKS_CONTROLLER_FINISHED",
            tasks=[
                dict(
                    task=task_id,
                    status="CONTROLLER_RESOURCE_STOP",
                    elapsed_seconds=3600.0,
                )
            ],
        ),
    )
    (tmp_path / "CONTROLLER_EVENTS.jsonl").write_text("{}\n")
    return model, optimizer, binding, pointer, folder, history


@pytest.mark.parametrize("status,terminal", [("CUMULATIVE_RESOURCE_CAP", True), ("RUNNING", False)])
def test_zero_update_archive_and_exact_state_resume(tmp_path, status, terminal):
    model, optimizer, binding, old, folder, history = fixture_run(tmp_path, status, terminal)
    before = extension._state_identity(model, optimizer)
    originals = {p.name: extension.sha(p) for p in folder.iterdir() if p.is_file()}
    completed = {
        str(p): extension.sha(p) for p in tmp_path.glob("*/TERMINAL.json") if p.parent != folder
    }
    hashes = sources()
    result = extension.prepare_continuation(tmp_path, dict(SHA256="a" * 64), original_pid=None)
    assert result["status"] == "CONDITIONAL_EXTENSION_PREPARED"
    archive = tmp_path / "RUNTIME_5400_ORIGINALS" / folder.name
    assert extension.sha(archive / old["file"]) == old["SHA256"]
    assert extension.sha(archive / "latest.json") == originals["latest.json"]
    assert not (folder / "TERMINAL.json").exists()
    saved, pointer = load(folder, model, optimizer, binding)
    assert saved["step"] == 0 and not optimizer.state
    assert saved["trainer_state"]["status"] == "RUNNING"
    assert extension._state_identity(model, optimizer) == before
    assert saved["elapsed_seconds"] == 3600.0
    assert saved["trainer_state"]["validation"] == history["validation"]
    if status == "RUNNING":
        assert pointer == old
    assert extension.resource_clock(folder)[0] == 3600.0
    assert completed == {p: extension.sha(p) for p in completed}
    assert sources() == hashes
    assert result["tasks"][0]["added_optimizer_updates"] == 0
    assert not (tmp_path / "CONTROLLER_RECEIPT.json").exists()
    assert (tmp_path / "RUNTIME_5400_ORIGINALS/CONTROLLER_RECEIPT.json").exists()
    assert tree_identity(_rng_state()) == before["RNG"]


def test_numeric_failure_and_completed_terminal_untouched(tmp_path):
    _, _, _, _, folder, _ = fixture_run(tmp_path, "STOP_NUMERICAL_OR_PATH_FAILURE")
    original = {str(p): extension.sha(p) for p in tmp_path.rglob("*") if p.is_file()}
    assert (
        extension.prepare_continuation(tmp_path, dict(SHA256="a" * 64), original_pid=None)["status"]
        == "NO_EXTENSION_NEEDED"
    )
    assert original == {p: extension.sha(p) for p in original}
    assert (folder / "TERMINAL.json").exists()


def test_cap_status_cannot_reenable_early_stop_snapshot(tmp_path):
    _, _, _, _, folder, _ = fixture_run(tmp_path, "EARLY_STOP_RULE")
    terminal = json.loads((folder / "TERMINAL.json").read_text())
    terminal["status"] = "CUMULATIVE_RESOURCE_CAP"
    _atomic_json(folder / "TERMINAL.json", terminal)
    before = extension.sha(folder / "latest.json")
    with pytest.raises(ValueError, match="incomplete"):
        extension.prepare_continuation(tmp_path, dict(SHA256="a" * 64), original_pid=None)
    assert extension.sha(folder / "latest.json") == before


def test_real_completed_adam_moments_and_rng_survive_metadata_only_copy(tmp_path):
    """Use a COPY of immutable BASE640; never alter or rerun the real fit."""
    _, _, _, _, folder, _ = fixture_run(tmp_path, "CUMULATIVE_RESOURCE_CAP")
    original = (
        Path("/workspace/coin-state/work/temporal-two-expert-20261009/small-tuning-run")
        / folder.name
    )
    pointer = json.loads((original / "latest.json").read_text())
    assert pointer["step"] == 640
    copied = ["RUN.json", "SCALER.npz", "SCALER.json", "latest.json", pointer["file"]]
    hashes = {name: extension.sha(original / name) for name in copied}
    for name in copied:
        shutil.copy2(original / name, folder / name)
    import numpy as np

    with np.load(folder / "SCALER.npz", allow_pickle=False) as z:
        meta = json.loads((folder / "SCALER.json").read_text())
        scaler = Standardizer(z["mean"], z["scale"], z["count"], meta["provenance"])
    model, _ = initialize(scaler)
    settings = plan()["actual_fit_tasks"][0]
    optimizer = optimizer_for(model, settings)
    binding = json.loads((folder / "RUN.json").read_text())
    saved, _ = load(folder, model, optimizer, binding)
    before = extension._state_identity(model, optimizer)
    assert len(optimizer.state) == 13
    assert all(float(v["step"]) == 640 for v in optimizer.state.values())
    history = saved["trainer_state"]
    history["status"] = "CUMULATIVE_RESOURCE_CAP"  # simulated cap metadata only in isolated fixture
    with run_guard(folder, binding):
        cap = save(
            folder,
            model,
            optimizer,
            binding,
            step=640,
            elapsed=max(3600.0, saved["elapsed_seconds"]),
            history=history,
        )
    _atomic_json(
        folder / "TERMINAL.json",
        dict(
            status="CUMULATIVE_RESOURCE_CAP",
            latest=cap,
            completed_updates=640,
            settings=settings,
        ),
    )
    result = extension.prepare_continuation(tmp_path, dict(SHA256="a" * 64), original_pid=None)
    resumed, _ = load(folder, model, optimizer, binding)
    assert resumed["step"] == 640
    assert extension._state_identity(model, optimizer) == before
    assert all(float(v["step"]) == 640 for v in optimizer.state.values())
    assert result["tasks"][0]["added_optimizer_updates"] == 0
    assert hashes == {name: extension.sha(original / name) for name in copied}


def test_published_authorization_and_prepared_overlay_identity():
    permission = extension.verify_permission(
        extension.REPO / extension.AUTH_PUBLIC_PATH,
        extension.AUTH_COMMIT,
        extension.AUTH_PUBLIC_PATH,
    )
    receipt = extension.prepared_template(permission)
    assert receipt["permission"]["public_commit"] == extension.AUTH_COMMIT
    assert len(receipt["frozen_sources"]) == 77
    assert len(receipt["overlay_sources"]) == 3
    assert receipt["limits"]["cumulative_seconds"] == 5400
    assert receipt["limits"]["hard_slice_seconds"] == 1200
    assert receipt["limits"]["maximum_updates"] == 1024
    assert receipt["actual_extension_applied"] is False and receipt["optimizer_updates"] == 0


def test_fresh_scheduler_verification_loads_no_torch_and_code_hash_is_stable():
    script = """
import json, resource, sys
from concurrent.futures import ThreadPoolExecutor
import RUNTIME_EXTENSION as extension
from modules.temporal_small_tuning import controller
permission = extension.verify_permission(extension.REPO / extension.AUTH_PUBLIC_PATH,
    extension.AUTH_COMMIT, extension.AUTH_PUBLIC_PATH, lightweight=True)
assert 'torch' not in sys.modules and 'numpy' not in sys.modules
resource.setrlimit(resource.RLIMIT_AS, (1000000000, resource.getrlimit(resource.RLIMIT_AS)[1]))
with ThreadPoolExecutor(max_workers=2) as executor:
    assert list(executor.map(lambda value: value + 1, [1, 2])) == [2, 3]
patched = extension.patched_function(controller.main, controller=True)
print(json.dumps(dict(original=extension.code_sha(controller.main.__code__),
    extended=extension.code_sha(patched.__code__),
    frozen_sources=len(permission['receipt']['fitting_sources_preserved']), torch_loaded=False)))
"""
    result = json.loads(subprocess.check_output([sys.executable, "-c", script]))
    assert result["original"] == extension.code_sha(controller.main.__code__)
    assert result["extended"] == extension.code_sha(
        extension.patched_function(controller.main, controller=True).__code__
    )
    assert result["frozen_sources"] == 77 and result["torch_loaded"] is False
