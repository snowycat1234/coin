"""Independent progress truth and localhost boundary checks; all fixtures in STATE."""

import http.client
import importlib.util
import json
from pathlib import Path
import signal
import sys
import threading
import time
from types import SimpleNamespace

import pytest

ROOT = Path("/mnt/d/codex/coin")


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def modules(monkeypatch, tmp_path):
    assert str(tmp_path).startswith("/home/xflops/coin-state/")
    window = load("independent_progress_window", "scripts/task_progress_window.py")
    runner = load("independent_progress_runner", "scripts/task_progress_run.py")
    sampler = load("independent_progress_sampler", "tools/task_progress/task_progress_sample.py")
    progress = tmp_path / "task-progress"
    progress.mkdir()
    monkeypatch.setattr(window, "STATE", tmp_path)
    monkeypatch.setattr(window, "PROGRESS", progress)
    monkeypatch.setattr(runner, "STATE", progress)
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(sampler, "STATE", progress)
    return window, runner, sampler


def frame(name, relative, line, local, first=1):
    return SimpleNamespace(f_code=SimpleNamespace(co_name=name, co_filename=str(ROOT / relative),
                                                  co_firstlineno=first),
                           f_lineno=line, f_locals=local)


def trainer_lines():
    lines = (ROOT / "src/quant/research_fast/trainer.py").read_text().splitlines()
    return {"first": next(i + 1 for i, s in enumerate(lines) if s.startswith("def fit_sequence(")),
            "loop": next(i + 1 for i, s in enumerate(lines)
                         if s.strip().startswith('for step, batch in enumerate(loaders["train"])')),
            "eval": next(i + 1 for i, s in enumerate(lines) if s.strip() == "model.eval()"),
            "test": next(i + 1 for i, s in enumerate(lines)
                         if s.strip() == "model.load_state_dict(best_state)")}


@pytest.mark.parametrize("position", ["before_loop", "loop", "validation", "test"])
def test_sampler_never_reuses_previous_epoch_batch_counter(modules, position):
    sampler = modules[2]
    lines = trainer_lines()
    line = {"before_loop": lines["loop"] - 1, "loop": lines["loop"],
            "validation": lines["eval"] + 1, "test": lines["test"]}[position]
    local = {"loaders": {"train": list(range(10))}, "step": 9, "epoch": 1,
             "history": [{"epoch": 1}], "epochs": 10}
    result = sampler.inspect_frame(frame("fit_sequence", "src/quant/research_fast/trainer.py",
                                         line, local, lines["first"]))
    assert result["completed"] is None
    assert result["total"] is None
    assert result["metrics"]["已完成轮次"] == 1


def test_active_batch_and_ts_iteration_are_completed_lower_bounds(modules):
    sampler = modules[2]
    lines = trainer_lines()
    result = sampler.inspect_frame(frame("fit_sequence", "src/quant/research_fast/trainer.py",
        lines["loop"] + 1, {"loaders": {"train": list(range(10))}, "step": 3,
                            "epoch": 0, "history": [], "epochs": 10}, lines["first"]))
    assert (result["completed"], result["total"]) == (3, 10)
    result = sampler.inspect_frame(frame("fit", "third_party/ts2vec/ts2vec.py", 1,
        {"self": SimpleNamespace(n_iters=17), "n_iters": 600}))
    assert (result["completed"], result["total"]) == (17, 600)


def test_pytest_current_case_and_disk_unknown_total_are_not_counted_complete(modules):
    sampler = modules[2]
    items = [SimpleNamespace(name="first"), SimpleNamespace(name="in_flight")]
    result = sampler.inspect_frame(frame("pytest_runtestloop", "unused", 1,
        {"session": SimpleNamespace(items=items), "item": items[1]}))
    assert (result["completed"], result["total"]) == (1, 2)
    result = sampler.inspect_frame(frame("tree_bytes", "src/quant/disk.py", 1,
        {"total": 1000, "pending": ["directory"]}))
    assert result["completed"] is None and result["total"] is None
    assert result["metrics"]["已计入字节"] == 1000


def test_unrecognized_stack_clears_earlier_phase(modules, monkeypatch):
    sampler = modules[2]
    recorded = []
    monkeypatch.setattr(sampler.sys, "_current_frames", lambda: {})
    monkeypatch.setattr(sampler, "write_snapshot", recorded.append)
    def stop(_seconds):
        raise KeyboardInterrupt
    monkeypatch.setattr(sampler.time, "sleep", stop)
    with pytest.raises(KeyboardInterrupt):
        sampler.sample_loop(123456)
    assert len(recorded) == 1
    assert recorded[0]["completed"] is None and recorded[0]["total"] is None


@pytest.mark.parametrize("group,expected", [
    ("TLOB-1", ["rolling_04 / TLOB-1"]),
    ("TS2VEC-SHARED", ["rolling_04 / TS2VEC-LINEAR-1", "rolling_04 / TS2VEC-LGB-1"]),
])
def test_formal_worker_nargs_two_marks_only_actual_fold_and_group(modules, tmp_path, group, expected):
    window = modules[0]
    run = tmp_path / "run"
    run.mkdir()
    (run / "RUN_BINDING.json").write_text(json.dumps({"folds": ["rolling_00", "rolling_04"]}))
    worker = {"pid": 22, "started_at": 123., "args": ["python",
        str(ROOT / "scripts/fr_run_first_round.py"), "--run-dir", str(run),
        "--worker", "rolling_04", group]}
    task = window.run_task(run, {"started_at": 100.}, {22: worker})
    assert [child["title"] for child in task["children"] if child["status"] == "running"] == expected
    assert group in task["phase"]


def history_receipt(path):
    path.write_text(json.dumps({"status": "HISTORICAL_DATASET_BUILD_RUNNING",
        "created_utc": "2026-10-01T00:00:00+00:00", "complete_common_days": 30,
        "completed_daily_stream_files": 120, "required_daily_stream_files": 720}))


def test_exited_history_is_unconfirmed_and_pid_reuse_is_not_liveness(modules, tmp_path, monkeypatch):
    window = modules[0]
    report = tmp_path / "history.json"
    history_receipt(report)
    assert window.download_task(report, None)["status"] == "unconfirmed"
    window.KNOWN[("download", str(report))] = (42, 100)
    unrelated = {"pid": 42, "start_ticks": 200, "started_at": time.time(), "args": ["python", "unrelated.py"]}
    monkeypatch.setattr(window, "processes", lambda: {42: unrelated})
    monkeypatch.setattr(window, "resources", lambda: {})
    task = window.build_snapshot()["tasks"][0]
    assert task["status"] == "unconfirmed"


@pytest.mark.parametrize("exit_kind,expected_code,expected_child_code", [
    ("success", 0, 0), ("failure", 7, 7), ("signal", 143, -signal.SIGTERM),
])
def test_wrapper_records_actual_exit_without_losing_signal(modules, monkeypatch, exit_kind,
                                                            expected_code, expected_child_code):
    runner = modules[1]
    program = {"success": "raise SystemExit(0)", "failure": "raise SystemExit(7)",
               "signal": "import os,signal; os.kill(os.getpid(),signal.SIGTERM)"}[exit_kind]
    monkeypatch.setattr(sys, "argv", ["task_progress_run", "--title", "isolated fixture", "--",
                                     "/usr/bin/python3", "-c", program])
    monkeypatch.setattr(runner.signal, "signal", lambda *_args: None)
    assert runner.main() == expected_code
    receipts = list(runner.STATE.glob("task-*.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["exit_code"] == expected_child_code
    assert receipt["status"] == ("completed" if expected_code == 0 else "failed")
    assert receipt["ended_at"] >= receipt["started_at"]


def test_spawn_failure_has_final_failed_receipt(modules, tmp_path, monkeypatch):
    runner = modules[1]
    monkeypatch.setattr(sys, "argv", ["task_progress_run", "--title", "isolated missing command",
                                     "--", str(tmp_path / "definitely-not-a-command")])
    assert runner.main() == 127
    receipt = json.loads(next(runner.STATE.glob("task-*.json")).read_text())
    assert receipt["status"] == "failed" and receipt["exit_code"] == 127
    assert "pid" not in receipt and "FileNotFoundError" in receipt["detail"]


def test_sources_stay_in_allowed_storage_and_http_is_local_readonly(modules, tmp_path, monkeypatch):
    window = modules[0]
    monkeypatch.setattr(window, "ROOT", tmp_path / "project")
    assert window.safe_path(str(tmp_path / "permitted.json")).is_relative_to(tmp_path)
    with pytest.raises(ValueError, match="D-hosted"):
        window.safe_path("/etc/passwd")
    window.SNAPSHOT = {"tasks": [], "resources": {"disk": {"bytes": None}}, "errors": []}
    server = window.ThreadingHTTPServer(("127.0.0.1", 0), window.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=3)
    try:
        connection.request("GET", "/api/status")
        response = connection.getresponse()
        assert response.status == 200
        assert json.loads(response.read())["resources"]["disk"]["bytes"] is None
        connection.request("GET", "/api/status", headers={"Host": "external.invalid"})
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        connection.request("GET", "/api/status", headers={"Sec-Fetch-Site": "cross-site"})
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        connection.request("POST", "/api/status")
        response = connection.getresponse()
        assert response.status in (403, 405, 501)
        response.read()
        connection.request("GET", "/unknown")
        response = connection.getresponse()
        assert response.status == 404
        response.read()
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
