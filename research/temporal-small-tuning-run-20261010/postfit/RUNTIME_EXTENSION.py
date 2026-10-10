"""Explicit operational3600->5400 overlay; frozen recipes/checkpoints stay bound.

No model inference or optimizer update occurs in preparation. The continue CLI
is deliberately not invoked by tests and requires a published permission receipt.
"""

import argparse
import copy
import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import types
from pathlib import Path

REPO = Path("/workspace/coin-temporal")
REAL_PYTHON = "/workspace/coin/.venv/bin/python"
PRODUCER = "565096a843e983b39bc38e8b9796fa9f96cc8de7"
ROOT = Path(__file__).resolve().parent
SCHEMA = "SOURCE_BOUND_OPERATIONAL_WALL_EXTENSION_3600_TO_5400_V1"
AUTH_COMMIT = "14e6b4a11a6249f4ac9cec488503cac27a55caee"
AUTH_PUBLIC_PATH = (
    "research/temporal-small-tuning-run-20261010/RUNTIME_EXTENSION_AUTHORIZATION.json"
)
LIMITS = dict(
    old_cumulative_seconds=3600,
    cumulative_seconds=5400,
    training_slice_seconds=1100,
    hard_slice_seconds=1200,
    maximum_workers=2,
    maximum_updates=1024,
    resident_bytes=2000000000,
    shared_bytes=8000000000,
    GPU=0,
    swap=0,
)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def overlay_sources():
    return {
        name: sha(ROOT / name)
        for name in (
            "RUNTIME_EXTENSION.py",
            "PYTHON_5400.py",
            "test_runtime_extension.py",
        )
    }


def _prepared_body(permission, frozen_sources):
    return dict(
        schema=SCHEMA,
        actual_extension_applied=False,
        permission=permission,
        original_producer_commit=PRODUCER,
        limits=LIMITS,
        frozen_sources=frozen_sources,
        overlay_sources=overlay_sources(),
        conditional="only_after_original_controller_finished;only_unfinished_or_genuine_wall_capped_tasks",
        recipe_changes=False,
        added_fits=0,
        selection_rule_changes=False,
        numeric_or_path_failures_retried=False,
        optimizer_updates=0,
    )


def prepared_template(permission):
    from modules.temporal_small_tuning import controller, stage
    from modules.temporal_small_tuning.protocol import sources

    return dict(
        _prepared_body(permission, sources()),
        transformations={
            name: dict(
                original_code_SHA256=code_sha(fn.__code__),
                extended_code_SHA256=code_sha(
                    patched_function(fn, controller=is_controller).__code__
                ),
                signature=str(inspect.signature(fn)),
            )
            for name, fn, is_controller in [
                ("stage.train_slice", stage.train_slice, False),
                ("controller.main.worker_queue", controller.main, True),
            ]
        },
    )


def verify_permission(path, commit, public_path, *, lightweight=False):
    path = Path(path).resolve()
    receipt = json.loads(path.read_text())
    if (
        commit != AUTH_COMMIT
        or public_path != AUTH_PUBLIC_PATH
        or receipt["schema"] != "AUTHORIZED_OPERATIONAL_CUMULATIVE_RUNTIME_EXTENSION_V1"
        or receipt["new_cumulative_wall_seconds"] != 5400
        or receipt["old_cumulative_wall_seconds"] != 3600
        or receipt["hard_guard_seconds"] != 1200
        or receipt["training_slice_seconds"] != 1100
        or receipt["maximum_training_workers"] != 2
        or receipt["maximum_updates"] != 1024
        or receipt["checkpoint_bindings_unchanged"] is not True
        or receipt["selection_and_early_stop_unchanged"] is not True
        or len(receipt["fitting_sources_preserved"]) != 77
    ):
        raise ValueError("Exact published operational5400 authorization required")
    published = subprocess.check_output(["git", "show", commit + ":" + public_path], cwd=REPO)
    if published != path.read_bytes():
        raise ValueError(
            "Permission receipt must be published byte-identically before continuation"
        )
    if not lightweight:
        from modules.temporal_small_tuning.protocol import sources

        if receipt["fitting_sources_preserved"] != sources():
            raise ValueError("Original fitting sources changed")
    for name, expected_hash in receipt["fitting_sources_preserved"].items():
        if sha(REPO / name) != expected_hash:
            raise ValueError("Original fitting-source bytes changed")
        public = subprocess.check_output(["git", "show", PRODUCER + ":" + name], cwd=REPO)
        if hashlib.sha256(public).hexdigest() != expected_hash:
            raise ValueError("Original producer source identity differs")
    return dict(receipt=receipt, SHA256=sha(path), public_commit=commit, public_path=public_path)


def verify_prepared(path, commit, public_path, permission, *, lightweight=False):
    path = Path(path).resolve()
    data = json.loads(path.read_text())
    if lightweight:
        body = {k: v for k, v in data.items() if k != "transformations"}
        valid = body == _prepared_body(
            permission, permission["receipt"]["fitting_sources_preserved"]
        ) and set(data["transformations"]) == {
            "stage.train_slice",
            "controller.main.worker_queue",
        }
    else:
        valid = data == prepared_template(permission)
    if not valid:
        raise ValueError("Exact tested overlay/source/transformation receipt required")
    published = subprocess.check_output(["git", "show", commit + ":" + public_path], cwd=REPO)
    if published != path.read_bytes():
        raise ValueError("Overlay receipt must be published before any continuation effect")
    return dict(SHA256=sha(path), public_commit=commit, public_path=public_path)


def code_record(code):
    """Stable typed code identity; marshal encodes incidental reference counts."""

    def constant(value):
        if isinstance(value, types.CodeType):
            return ["code", code_record(value)]
        if type(value) is tuple:
            return ["tuple", [constant(v) for v in value]]
        if type(value) is frozenset:
            return [
                "frozenset",
                sorted((constant(v) for v in value), key=lambda v: json.dumps(v)),
            ]
        if type(value) is bytes:
            return ["bytes", value.hex()]
        if type(value) is float:
            return ["float", value.hex()]
        if value is None or type(value) in (str, int, bool):
            return [type(value).__name__, value]
        raise ValueError("Unsupported code constant type")

    fields = (
        "co_argcount",
        "co_posonlyargcount",
        "co_kwonlyargcount",
        "co_nlocals",
        "co_stacksize",
        "co_flags",
        "co_names",
        "co_varnames",
        "co_filename",
        "co_name",
        "co_qualname",
        "co_firstlineno",
        "co_freevars",
        "co_cellvars",
    )
    result = {name: getattr(code, name) for name in fields}
    result.update(
        co_code=code.co_code.hex(),
        co_linetable=code.co_linetable.hex(),
        co_exceptiontable=code.co_exceptiontable.hex(),
        co_consts=[constant(v) for v in code.co_consts],
    )
    return result


def code_sha(code):
    return hashlib.sha256(
        json.dumps(code_record(code), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _patch_code(code, replacements, *, recursive):
    counts = {kind: 0 for kind in replacements}
    constants = []
    for value in code.co_consts:
        kind = type(value)
        if kind in replacements and value == 3600:
            counts[kind] += 1
            value = replacements[kind]
        elif recursive and isinstance(value, types.CodeType):
            value, nested = _patch_code(value, replacements, recursive=True)
            for key, count in nested.items():
                counts[key] += count
        constants.append(value)
    return code.replace(co_consts=tuple(constants)), counts


def _same_except_guard(old, new):
    """Exact inverse proves no bytecode/metadata/other constants changed."""
    values = []
    for before, after in zip(old.co_consts, new.co_consts, strict=True):
        if isinstance(before, types.CodeType):
            if not isinstance(after, types.CodeType):
                raise ValueError("Code structure changed")
            _same_except_guard(before, after)
            values.append(before)
        elif type(before) in (int, float) and before == 3600 and after == 5400:
            if type(before) is not type(after):
                raise ValueError("Guard constant type changed")
            values.append(before)
        elif before != after:
            raise ValueError("Non-guard constant changed")
        else:
            values.append(after)
    restored = new.replace(co_consts=tuple(values))
    if code_record(restored) != code_record(old):
        raise ValueError("Only guard constants may change")


def patched_function(function, *, controller=False):
    original = function.__code__
    if controller:
        constants, count, edits = [], 0, None
        for value in original.co_consts:
            if isinstance(value, types.CodeType) and value.co_name == "worker_queue":
                value, edits = _patch_code(value, {int: 5400, float: 5400.0}, recursive=False)
                count += 1
            constants.append(value)
        if count != 1 or edits != {int: 1, float: 1}:
            raise ValueError("Expected exactly two nested controller wall-guard constants")
        code = original.replace(co_consts=tuple(constants))
    else:
        code, edits = _patch_code(original, {float: 5400.0}, recursive=False)
        if edits != {float: 1}:
            raise ValueError("Expected exactly one trainer cumulative wall-guard constant")
    _same_except_guard(original, code)
    patched = types.FunctionType(
        code,
        function.__globals__,
        function.__name__,
        function.__defaults__,
        function.__closure__,
    )
    patched.__kwdefaults__ = function.__kwdefaults__
    patched.__annotations__ = function.__annotations__.copy()
    patched.__dict__.update(function.__dict__)
    patched.__qualname__ = function.__qualname__
    if inspect.signature(patched) != inspect.signature(function):
        raise ValueError("Frozen method signature changed")
    return patched


def process_active(pid):
    if pid is None:
        return False
    try:
        stat = Path("/proc", str(pid), "stat").read_bytes()
    except (FileNotFoundError, ProcessLookupError):
        return False
    except OSError as error:
        raise ValueError("Cannot verify original or continuation process state") from error
    # The parenthesized command name can contain spaces and closing parentheses.
    fields = stat.rsplit(b")", 1)
    tail = fields[1].split() if len(fields) == 2 else []
    if not tail or len(tail[0]) != 1:
        raise ValueError("Cannot verify original or continuation process state")
    return tail[0] not in (b"Z", b"X")


def assert_quiet(output, original_pid):
    if process_active(original_pid):
        raise ValueError("Original worker/controller PID is still active")
    output_bytes = str(Path(output).resolve()).encode()
    for entry in Path("/proc").iterdir():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        if not process_active(int(entry.name)):
            continue
        try:
            command = (entry / "cmdline").read_bytes()
        except (OSError, ProcessLookupError):
            continue
        tokens = command.rstrip(b"\0").split(b"\0")
        owns_output = output_bytes in tokens
        own_frozen = (
            b"modules.temporal_small_tuning" in tokens
            or b"modules/temporal_small_tuning/controller.py" in tokens
            or any(t.endswith(b"/modules/temporal_small_tuning/controller.py") for t in tokens)
        )
        own_overlay = str(ROOT / "RUNTIME_EXTENSION.py").encode() in tokens and (
            b"continue" in tokens or b"controller" in tokens
        )
        if owns_output and (own_frozen or own_overlay):
            raise ValueError("Original or continuation worker/controller is still active")


def resource_clock(folder):
    files = sorted(Path(folder).glob("RESOURCE_SLICE_*.json"))
    indices = [int(p.stem.rsplit("_", 1)[1]) for p in files]
    if indices != list(range(1, len(files) + 1)):
        raise ValueError("Existing resource slice indices must be contiguous")
    records = [json.loads(p.read_text()) for p in files]
    if any(
        type(r["elapsed_seconds"]) not in (int, float)
        or not 0 <= r["elapsed_seconds"] < float("inf")
        for r in records
    ):
        raise ValueError("Finite prior resource clocks required")
    return sum(r["elapsed_seconds"] for r in records), files


def _state_identity(model, optimizer):
    from modules.temporal_episode_weighting_v2.stage import tree_identity
    from modules.temporal_two_expert.checkpoint import _rng_state, model_identity

    return dict(
        model=model_identity(model),
        optimizer=tree_identity(optimizer.state_dict()),
        RNG=tree_identity(_rng_state()),
        training=model.training,
    )


def _archive(path, destination, records):
    from modules.temporal_two_expert.checkpoint import _sync_directory

    target = destination / path.name
    shutil.copy2(path, target)
    if sha(target) != sha(path):
        raise ValueError("Immutable original archive differs")
    with target.open("rb") as stream:
        os.fsync(stream.fileno())
    _sync_directory(destination)
    records[path.name] = dict(SHA256=sha(target), bytes=target.stat().st_size)


def prepare_continuation(output, permission, *, original_pid=32532):
    """Archive originals and reenable only genuine cap metadata, without a model update."""
    import numpy as np
    from modules.temporal_prequential_transfer.model import initialize
    from modules.temporal_small_tuning.checkpoint import load, optimizer_for, save
    from modules.temporal_small_tuning.protocol import sources, task
    from modules.temporal_two_expert.checkpoint import _atomic_json, run_guard
    from modules.temporal_two_expert.inputs import Standardizer

    output = Path(output).resolve()
    assert_quiet(output, original_pid)
    ready = json.loads((output / "READY.json").read_text())
    original = json.loads((output / "CONTROLLER_RECEIPT.json").read_text())
    if (
        original["status"] != "SIX_FIXED_TASKS_CONTROLLER_FINISHED"
        or ready["sources"] != sources()
        or len(ready["tasks"]) != 6
    ):
        raise ValueError("Original completed six-task controller and frozen sources required")
    archive = output / "RUNTIME_5400_ORIGINALS"
    if archive.exists():
        raise FileExistsError("One immutable continuation preparation; never repeat reenable")
    pending = []
    for task_id in ready["tasks"]:
        folder = output / task_id
        terminal_path = folder / "TERMINAL.json"
        terminal = json.loads(terminal_path.read_text()) if terminal_path.exists() else None
        if terminal is not None and terminal["status"] != "CUMULATIVE_RESOURCE_CAP":
            if terminal["status"] not in {
                "EARLY_STOP_RULE",
                "UPDATE_CAP_NOT_CONVERGENCE",
                "STOP_NUMERICAL_OR_PATH_FAILURE",
            }:
                raise ValueError("Unknown terminal status; never reenable it")
            continue
        elapsed, resources = resource_clock(folder)
        stopped = [
            r
            for r in original["tasks"]
            if r.get("task") == task_id and r["status"] == "CONTROLLER_RESOURCE_STOP"
        ]
        if terminal is None and len(stopped) != 1:
            raise ValueError("Missing terminal requires original controller-stop evidence")
        if elapsed >= LIMITS["cumulative_seconds"]:
            continue
        pending.append((task_id, terminal, elapsed, resources))
    if not pending:
        return dict(status="NO_EXTENSION_NEEDED", added_optimizer_updates=0)
    # Check every intended transition before creating archives or changing metadata.
    for task_id, terminal, elapsed, _ in pending:
        folder = output / task_id
        settings = task(task_id)
        with np.load(folder / "SCALER.npz", allow_pickle=False) as z:
            meta = json.loads((folder / "SCALER.json").read_text())
            scaler = Standardizer(z["mean"], z["scale"], z["count"], meta["provenance"])
        model, _ = initialize(scaler)
        optimizer = optimizer_for(model, settings)
        binding = json.loads((folder / "RUN.json").read_text())
        saved, pointer = load(folder, model, optimizer, binding)
        history = saved["trainer_state"]
        if saved["step"] > 1024 or history["status"] not in {
            "RUNNING",
            "CUMULATIVE_RESOURCE_CAP",
        }:
            raise ValueError(
                "Only unchanged incomplete RUNNING/genuine wall-cap snapshots may resume"
            )
        if terminal is not None and (
            history["status"] != "CUMULATIVE_RESOURCE_CAP"
            or terminal["latest"] != pointer
            or terminal["completed_updates"] != saved["step"]
            or terminal["settings"] != settings
            or max(elapsed, saved["elapsed_seconds"]) < 3600
        ):
            raise ValueError("Terminal cap must match the authoritative old snapshot and clock")
        if terminal is None and history["status"] != "RUNNING":
            raise ValueError("Missing terminal cannot silently reenable a stopped fit")
    archive.mkdir()
    archived = {}
    for name in ("CONTROLLER_RECEIPT.json", "CONTROLLER_EVENTS.jsonl"):
        path = output / name
        if path.exists():
            _archive(path, archive, archived)
    transitions = []
    for task_id, terminal, elapsed, resources in pending:
        settings = task(task_id)
        folder, backup = output / task_id, archive / task_id
        backup.mkdir()
        with np.load(folder / "SCALER.npz", allow_pickle=False) as z:
            meta = json.loads((folder / "SCALER.json").read_text())
            scaler = Standardizer(z["mean"], z["scale"], z["count"], meta["provenance"])
        model, _ = initialize(scaler)
        optimizer = optimizer_for(model, settings)
        binding = json.loads((folder / "RUN.json").read_text())
        with run_guard(folder, binding):
            saved, pointer = load(folder, model, optimizer, binding)
            history = copy.deepcopy(saved["trainer_state"])
            if saved["step"] > 1024 or history["status"] not in {
                "RUNNING",
                "CUMULATIVE_RESOURCE_CAP",
            }:
                raise ValueError(
                    "Only unchanged incomplete RUNNING/genuine wall-cap snapshots may resume"
                )
            if terminal is not None and (
                history["status"] != "CUMULATIVE_RESOURCE_CAP"
                or terminal["latest"] != pointer
                or terminal["completed_updates"] != saved["step"]
                or terminal["settings"] != settings
                or max(elapsed, saved["elapsed_seconds"]) < 3600
            ):
                raise ValueError("Terminal cap must match the authoritative old snapshot and clock")
            if terminal is None and history["status"] != "RUNNING":
                raise ValueError("Missing terminal cannot silently reenable a stopped fit")
            before = _state_identity(model, optimizer)
            files = {}
            for path in [
                folder / pointer["file"],
                folder / "latest.json",
                folder / "RUN.json",
                *resources,
                *([folder / "TERMINAL.json"] if terminal else []),
            ]:
                _archive(path, backup, files)
            if history["status"] == "CUMULATIVE_RESOURCE_CAP":
                history["status"] = "RUNNING"
                history["runtime_extension"] = dict(
                    permission_SHA256=permission["SHA256"],
                    old_status="CUMULATIVE_RESOURCE_CAP",
                    cumulative_resource_seconds=elapsed,
                    added_optimizer_updates=0,
                )
                resumed = save(
                    folder,
                    model,
                    optimizer,
                    binding,
                    step=saved["step"],
                    elapsed=saved["elapsed_seconds"],
                    history=history,
                )
                (folder / "TERMINAL.json").unlink()
                from modules.temporal_two_expert.checkpoint import _sync_directory

                _sync_directory(folder)
            else:
                resumed = pointer
            if before != _state_identity(model, optimizer):
                raise ValueError("Metadata transition changed model/Adam/RNG/training mode")
            transitions.append(
                dict(
                    task_id=task_id,
                    previous_pointer=pointer,
                    resumed_pointer=resumed,
                    preserved_state_identity=before,
                    prior_resource_seconds=elapsed,
                    prior_slice_count=len(resources),
                    archived_files=files,
                    added_optimizer_updates=0,
                )
            )
    result = dict(
        schema=SCHEMA,
        status="CONDITIONAL_EXTENSION_PREPARED",
        permission=permission,
        limits=LIMITS,
        original_controller_files=archived,
        tasks=transitions,
        added_fits=0,
        added_optimizer_updates=0,
        frozen_sources_unchanged=True,
        overlay_sources=overlay_sources(),
    )
    _atomic_json(archive / "RECEIPT.json", result)
    _atomic_json(output / "RUNTIME_EXTENSION_5400.json", result)
    # Frozen controller requires an exclusive new receipt; the original is archived above.
    (output / "CONTROLLER_RECEIPT.json").unlink()
    from modules.temporal_two_expert.checkpoint import _sync_directory

    _sync_directory(output)
    return result


def worker(arguments, permission, prepared):
    import resource

    import torch
    from modules.temporal_small_tuning import stage

    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--seconds", type=float, required=True)
    args = parser.parse_args(arguments)
    if (
        os.environ.get("COIN_CLOUD_BOUNDED") != "1"
        or len(os.sched_getaffinity(0)) != 1
        or resource.getrlimit(resource.RLIMIT_CPU)[1] != 1200
        or resource.getrlimit(resource.RLIMIT_AS)[1] != 4000000000
    ):
        raise ValueError("Only the unchanged one-CPU resident/wall guard may dispatch a worker")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    receipt = json.loads((args.output / "RUNTIME_EXTENSION_5400.json").read_text())
    if (
        receipt["permission"] != permission
        or receipt["overlay_sources"] != overlay_sources()
        or receipt.get("prepared_receipt") != prepared
    ):
        raise ValueError("Published source-bound continuation preparation required")
    if args.task not in {r["task_id"] for r in receipt["tasks"]}:
        raise ValueError("Only specifically archived conditional continuation tasks required")
    if resource_clock(args.output / args.task)[0] >= LIMITS["cumulative_seconds"]:
        raise ValueError("No optimizer work may restart beyond cumulative5400 resource seconds")
    patched_function(stage.train_slice)(args.state, args.output, args.task, seconds=args.seconds)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("describe", "continue", "controller"))
    parser.add_argument("--permission", type=Path)
    parser.add_argument("--permission-commit", default=AUTH_COMMIT)
    parser.add_argument("--permission-public-path", default=AUTH_PUBLIC_PATH)
    parser.add_argument("--prepared", type=Path)
    parser.add_argument("--prepared-commit")
    parser.add_argument("--prepared-public-path")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--state", type=Path)
    parser.add_argument("--cpus", default="3,4")
    parser.add_argument("--original-controller-pid", type=int, default=32532)
    args = parser.parse_args()
    if args.action == "describe":
        if args.permission is None:
            parser.error("Describe requires the published authorization receipt path")
        permission = verify_permission(
            args.permission, args.permission_commit, args.permission_public_path
        )
        print(json.dumps(prepared_template(permission), indent=2, sort_keys=True))
        return
    if any(
        value is None
        for value in (
            args.permission,
            args.permission_commit,
            args.permission_public_path,
            args.output,
            args.state,
            args.prepared,
            args.prepared_commit,
            args.prepared_public_path,
        )
    ):
        parser.error("Continuation requires state/output and exact public permission path/commit")
    permission = verify_permission(
        args.permission,
        args.permission_commit,
        args.permission_public_path,
        lightweight=args.action == "controller",
    )
    prepared = verify_prepared(
        args.prepared,
        args.prepared_commit,
        args.prepared_public_path,
        permission,
        lightweight=args.action == "controller",
    )
    if args.action == "continue":
        import torch
        from modules.temporal_two_expert.checkpoint import _atomic_json

        torch.set_num_threads(1)
        torch.use_deterministic_algorithms(True)
        preparation = prepare_continuation(
            args.output, permission, original_pid=args.original_controller_pid
        )
        if preparation["status"] == "NO_EXTENSION_NEEDED":
            print(json.dumps(preparation))
            return
        preparation["prepared_receipt"] = prepared
        _atomic_json(args.output / "RUNTIME_EXTENSION_5400.json", preparation)
        _atomic_json(args.output / "RUNTIME_5400_ORIGINALS/RECEIPT.json", preparation)
        # Discard Torch's virtual mappings before the frozen stdlib scheduler
        # installs its original1GB parent ceiling and starts its two threads.
        os.execv(
            REAL_PYTHON,
            [REAL_PYTHON, str(Path(__file__).resolve()), "controller", *sys.argv[2:]],
        )
    if "torch" in sys.modules or "numpy" in sys.modules:
        raise ValueError("Fresh stdlib-only controller process required")
    assert_quiet(args.output, args.original_controller_pid)
    runtime = json.loads((args.output / "RUNTIME_EXTENSION_5400.json").read_text())
    if runtime["permission"] != permission or runtime["prepared_receipt"] != prepared:
        raise ValueError("Conditional source-bound preparation required")
    from modules.temporal_small_tuning import controller

    trace = json.loads(args.prepared.read_text())["transformations"]["controller.main.worker_queue"]
    extended_controller = patched_function(controller.main, controller=True)
    if trace["original_code_SHA256"] != code_sha(controller.main.__code__) or trace[
        "extended_code_SHA256"
    ] != code_sha(extended_controller.__code__):
        raise ValueError("Published controller constant transformation differs")
    os.environ.update(
        COIN_TUNING_EXTENSION_PERMISSION=str(args.permission.resolve()),
        COIN_TUNING_EXTENSION_COMMIT=args.permission_commit,
        COIN_TUNING_EXTENSION_PUBLIC_PATH=args.permission_public_path,
        COIN_TUNING_EXTENSION_PREPARED=str(args.prepared.resolve()),
        COIN_TUNING_EXTENSION_PREPARED_COMMIT=args.prepared_commit,
        COIN_TUNING_EXTENSION_PREPARED_PUBLIC_PATH=args.prepared_public_path,
    )
    sys.argv = [
        "frozen_controller_with_5400_guard",
        "--state",
        str(args.state),
        "--output",
        str(args.output),
        "--python",
        str(ROOT / "PYTHON_5400.py"),
        "--cpus",
        args.cpus,
    ]
    extended_controller()


if __name__ == "__main__":
    main()
