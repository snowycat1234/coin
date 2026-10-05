"""Local, read-only task window. Polls small receipts; never scans project data."""
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import hashlib
import json
import os
from pathlib import Path
import threading
import time

ROOT = Path("/mnt/d/codex/coin")
STATE = Path("/home/xflops/coin-state")
PROGRESS = STATE / "task-progress"
IDS = ("RIDGE-1", "XGB-S", "XGB-M", "TCN-S", "TCN-M", "MLPLOB-1", "TLOB-1",
       "TS2VEC-LINEAR-1", "TS2VEC-LGB-1", "RIVER-1")
FR69_POLICY = "FR69_STATIC_RIDGE_CONTINUOUS_RIVER_WEEKLY_XGB_FIXED_INITIAL_EXTERNAL_SCALERS_V1"
FR69_IDS = ("RIDGE-1", "XGB-S", "RIVER-1")
CACHE = {}
SNAPSHOT = {}
KNOWN = {}
LATEST_DISK = {}


def read_json(path):
    stamp = path.stat()
    key = (stamp.st_mtime_ns, stamp.st_size)
    cached = CACHE.get(path)
    if not cached or cached[0] != key:
        if stamp.st_size > 2_000_000:
            raise ValueError("Progress receipt exceeds 2MB")
        cached = key, json.loads(path.read_text())
        CACHE[path] = cached
    return cached[1]


def safe_path(raw):
    path = Path(raw)
    if not path.is_absolute():
        path = ROOT / path
    path = path.resolve()
    if not (path.is_relative_to(ROOT) or path.is_relative_to(STATE)):
        raise ValueError("Progress sources must stay on D-hosted project storage")
    return path


def processes():
    boot = time.time() - float(Path("/proc/uptime").read_text().split()[0])
    ticks = os.sysconf("SC_CLK_TCK")
    found = {}
    for folder in Path("/proc").iterdir():
        if not folder.name.isdigit():
            continue
        try:
            cgroup = (folder / "cgroup").read_text()
            if "/coin.slice/" not in cgroup:
                continue
            arguments = (folder / "cmdline").read_bytes().decode().strip("\0").split("\0")
            if not arguments:
                continue
            stat = (folder / "stat").read_text().split(") ", 1)[1].split()
            if stat[0] == "Z":
                continue
            found[int(folder.name)] = {"pid": int(folder.name), "args": arguments,
                "started_at": boot + int(stat[19]) / ticks, "process_state": stat[0],
                "start_ticks": int(stat[19])}
        except (OSError, UnicodeError, IndexError, ValueError):
            continue
    return found


def option(arguments, name):
    return arguments[arguments.index(name) + 1] if name in arguments else None


def registered_run_dir(task):
    raw = task.get("run_dir")
    if raw is None:
        # A separate link lets an exited V1 task retain its original receipt bytes.
        link = safe_path(PROGRESS / f"run-link-{task['id']}.json")
        if link.is_file():
            value = read_json(link)
            if value.get("task_id") != task["id"]:
                raise ValueError("Progress run link has a different task identity")
            raw = value["run_dir"]
    return safe_path(raw) if raw is not None else None


def receipt_sha256(path):
    with path.open("rb") as source:
        content = source.read(2_000_001)
    if len(content) > 2_000_000:
        raise ValueError("Progress receipt exceeds 2MB")
    return hashlib.sha256(content).hexdigest()


def fr69_progress(task, run, process):
    binding_path = safe_path(run / "RUN_BINDING.json")
    if not binding_path.is_file():
        return False
    binding = read_json(binding_path)
    if binding.get("policy") != FR69_POLICY:
        return False
    configs = binding.get("configs")
    if not isinstance(configs, dict) or set(configs) != set(FR69_IDS):
        raise ValueError("FR69 progress requires its three fixed bound configurations")
    binding_sha = hashlib.sha256(json.dumps(binding, sort_keys=True, separators=(",", ":"),
                                           allow_nan=False).encode()).hexdigest()
    sample_sha = binding.get("sample_ids_sha256")
    if not isinstance(sample_sha, str) or len(sample_sha) != 64:
        raise ValueError("FR69 progress requires bound sample identities")
    task.update(completed=0, total=len(configs), unit="配置", children=[])
    task["metrics"] = dict(task.get("metrics", {}))
    task["last_activity_at"] = max(task.get("last_activity_at", 0), binding_path.stat().st_mtime)
    receipt_hashes, problems = {}, []
    for model in FR69_IDS:
        receipt = safe_path(run / model / "COMPLETE.json")
        complete = False
        if receipt.is_file():
            value = read_json(receipt)
            complete = (value.get("status") == "COMPLETE_CONTINUOUS_REPLAY"
                        and value.get("config") == model
                        and value.get("binding_sha256") == binding_sha
                        and value.get("sample_ids_sha256") == sample_sha)
            if complete:
                receipt_hashes[model] = receipt_sha256(receipt)
                task["last_activity_at"] = max(task["last_activity_at"], receipt.stat().st_mtime)
            else:
                problems.append(model + " 完成凭证与来源绑定不一致")
        task["completed"] += int(complete)
        task["children"].append({"title": model, "status": "completed" if complete else "pending"})
    final_path = safe_path(run / "CONTINUOUS_REPLAY_COMPLETE.json")
    final_valid = False
    if final_path.is_file():
        final = read_json(final_path)
        final_valid = (final.get("status") == "FR69_CONTINUOUS_REPLAY_COMPLETE"
                       and final.get("binding_sha256") == binding_sha
                       and task["completed"] == task["total"]
                       and final.get("completion_receipt_sha256") == receipt_hashes)
        if final_valid:
            task["last_activity_at"] = max(task["last_activity_at"], final_path.stat().st_mtime)
        else:
            problems.append("总完成凭证与来源 / 模型凭证不一致")
    detail = "仅计数绑定一致的模型工件；3/3 仍待根侧验收"
    if not final_path.is_file():
        detail += "；总完成凭证尚未发布"
    if problems:
        detail += "；" + "；".join(problems)
    exit_code = task.get("exit_code")
    if exit_code is not None:
        detail += f"；实际退出码：{exit_code}"
    if task.get("status") == "failed" or (exit_code is not None and exit_code != 0):
        task.update(status="failed", phase="任务失败，已发布工件另行核验")
    elif task.get("status") == "completed" and exit_code == 0 and final_valid and not problems:
        task.update(status="completed", phase="三项模型工件与总凭证已发布，待根侧验收")
    elif process and not problems:
        task.update(status="running", phase="FR69 连续回放 / 模型工件发布")
    else:
        task.update(status="unconfirmed", phase="模型工件 / 结束记录待核验")
    task["detail"] = detail
    return True


def live_detail(process, phase="运行中"):
    return {"status": "running", "phase": phase, "started_at": process["started_at"],
            "completed": None, "total": None, "unit": "", "metrics": {}, "children": []}


def download_task(path, process):
    value = read_json(path)
    running = value.get("status") == "HISTORICAL_DATASET_BUILD_RUNNING"
    status = "running" if running and process else "unconfirmed" if running else (
        "failed" if "FAILED" in value.get("status", "") else "completed")
    days = value.get("complete_common_days", 0)
    return {"id": "download:" + str(path), "title": "币安官方历史数据", "status": status,
        "phase": "下载 / 校验 / 转换" if status == "running" else value.get("status"),
        "completed": value.get("completed_daily_stream_files", 0),
        "total": value.get("required_daily_stream_files"), "unit": "日文件",
        "started_at": datetime.fromisoformat(value["created_utc"]).timestamp(),
        "last_activity_at": path.stat().st_mtime, "detail": "四路共同完整日期",
        "metrics": {"完整历史天数": days, "目标历史天数": value.get("required_daily_stream_files", 0) // 4,
                    "特征数据字节": value.get("persistent_feature_bytes", 0)}, "children": []}


def run_task(run, process, inventory):
    binding_path = run / "RUN_BINDING.json"
    task = {"id": "run:" + str(run), "title": "完整窗口 · 十配置比较",
            **(live_detail(process) if process else {"status": "unconfirmed", "metrics": {}}),
            "completed": 0, "total": 10, "unit": "配置", "children": []}
    if not binding_path.is_file():
        task.update(phase="校验来源 / 预处理", detail="来源绑定尚未发布")
        return task
    binding = read_json(binding_path)
    folds = binding.get("folds", [])
    task["total"] = len(folds) * len(IDS)
    if len(folds) == 6:
        task["title"] = "正式六窗口 · 十配置比较"
    task["detail"] = "单窗口诊断；正式六窗口结果另行验收" if len(folds) == 1 else "固定配置，共同评价"
    task.setdefault("started_at", binding_path.stat().st_mtime)
    task["last_activity_at"] = binding_path.stat().st_mtime
    ledger = binding.get("ledger_before") or binding.get("initial_disk")
    if ledger:
        update_disk(ledger, binding_path.stat().st_mtime)
    workers = [p for p in inventory.values() if option(p["args"], "--run-dir") == str(run)
               and "--worker" in p["args"]]
    active_fold = folds[0] if folds else None
    active = option(workers[0]["args"], "--worker") if workers else None
    if workers and any(Path(a).name == "fr_run_first_round.py" for a in workers[0]["args"]):
        active_fold = active
        active = workers[0]["args"][workers[0]["args"].index("--worker") + 2]
    task["phase"] = f"{active} 训练 / 测试" if active else "来源扫描 / 模型验收"
    if workers:
        task["metrics"]["当前模型开始时间"] = workers[0]["started_at"]
        task["metrics"]["当前模型已运行秒"] = int(time.time() - workers[0]["started_at"])
        sample_path = PROGRESS / f"sample-{workers[0]['pid']}.json"
        if sample_path.is_file():
            sample = read_json(sample_path)
            if time.time() - sample["updated_at"] <= 6 and sample.get("start_ticks") == workers[0]["start_ticks"]:
                task["phase"] = active + " · " + sample["phase"]
                task["metrics"].update(sample.get("metrics", {}))
                if sample.get("total") is not None:
                    task["metrics"]["当前阶段进度"] = (
                        f"{sample['completed']} / {sample['total']} {sample['unit']}")
    for fold in folds:
        for model in IDS:
            receipt = run / fold / model / "COMPLETE.json"
            complete = receipt.is_file() and read_json(receipt).get("status") == "COMPLETE"
            task["completed"] += int(complete)
            is_active = active is not None and fold == active_fold and active in (
                model, "TS2VEC-SHARED" if model.startswith("TS2VEC-") else None)
            state = "completed" if complete else "running" if is_active else "pending"
            task["children"].append({"title": model if len(folds) == 1 else fold + " / " + model,
                                     "status": state})
            if complete:
                task["last_activity_at"] = max(task["last_activity_at"], receipt.stat().st_mtime)
    if active:
        # Only the active model's small checkpoint metadata is read, never its weights.
        directory = run / active_fold / active
        if directory.is_dir():
            for attempt in directory.glob("attempt-*"):
                for filename in ("best.pt", "encoder.pt"):
                    checkpoint = attempt / filename
                    if checkpoint.is_file():
                        task["last_activity_at"] = max(task["last_activity_at"], checkpoint.stat().st_mtime)
        if not (PROGRESS / f"sample-{workers[0]['pid']}.json").is_file():
            task["detail"] += "；正在运行的旧任务未提供实时轮次"
    if task["completed"] == task["total"]:
        task.update(status="completed", phase="全部训练 / 测试工件已发布，待根侧验收")
    return task


def update_disk(ledger, stamp):
    global LATEST_DISK
    if ledger.get("total_bytes") and stamp > LATEST_DISK.get("measured_at", 0):
        LATEST_DISK = {"bytes": ledger["total_bytes"], "limit_bytes": ledger.get('hard_limit_bytes',150_000_000_000),
                       "measured_at": stamp, "status": "最近已完成扫描的记录"}


def resources():
    disk_path = PROGRESS / "last-disk.json"
    if disk_path.is_file():
        recorded = read_json(disk_path)
        update_disk(recorded["ledger"], recorded["measured_at"])
    relative = Path("/proc/self/cgroup").read_text().strip().split("::", 1)[1]
    parent = Path("/sys/fs/cgroup") / relative.lstrip("/")
    while parent.name != "coin.slice":
        parent = parent.parent
        if parent == Path("/sys/fs/cgroup"):
            raise ValueError("Window must run inside the shared bounded slice")
    def read(name):
        return int((parent / name).read_text().strip())
    return {"ram_current_bytes": read("memory.current"), "ram_peak_bytes": read("memory.peak"),
            "ram_limit_bytes": read("memory.max"), "swap_bytes": read("memory.swap.current"),
            "gpu_used": False, "disk": LATEST_DISK or {"bytes": None,
                "limit_bytes": 150_000_000_000, "measured_at": None, "status": "尚无完成扫描记录"}}


def build_snapshot():
    inventory, errors, tasks = processes(), [], []
    for process in inventory.values():
        arguments = process["args"]
        if any(Path(a).name == "hf_fetch_history.py" for a in arguments):
            output = option(arguments, "--output")
            if output:
                KNOWN[("download", str(safe_path(output)))] = (process["pid"], process["start_ticks"])
        if any(Path(a).name in ("fr_rolling00_full_window_diagnostic_v6.py", "fr_run_first_round.py")
               for a in arguments) and "--worker" not in arguments:
            run = option(arguments, "--run-dir")
            if run:
                KNOWN[("run", str(safe_path(run)))] = (process["pid"], process["start_ticks"])
    for (kind, raw), (pid, start_ticks) in KNOWN.items():
        try:
            path = Path(raw)
            process = inventory.get(pid)
            if process and process["start_ticks"] != start_ticks:
                process = None
            task = download_task(path, process) if kind == "download" else run_task(path, process, inventory)
            tasks.append(task)
        except (OSError, ValueError, KeyError) as error:
            errors.append(f"读取任务进度失败：{type(error).__name__}")
    samples = {}
    if PROGRESS.is_dir():
        for pid in inventory:
            path = PROGRESS / f"sample-{pid}.json"
            if not path.is_file():
                continue
            try:
                sample = read_json(path)
                if (sample["pid"] in inventory and time.time() - sample["updated_at"] <= 6
                        and sample.get("start_ticks") == inventory[sample["pid"]]["start_ticks"]):
                    samples[sample["pid"]] = sample
            except (OSError, ValueError, KeyError):
                pass
        for path in sorted(PROGRESS.glob("task-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:32]:
            try:
                task = dict(read_json(path))
                process = inventory.get(task.get("pid"))
                if process and process["start_ticks"] != task.get("start_ticks"):
                    process = None
                run = registered_run_dir(task)
                artifact_progress = run is not None and fr69_progress(task, run, process)
                children = [s for s in samples.values() if s.get("task_id") == task["id"]]
                if task["status"] == "running" and children:
                    sample = max(children, key=lambda s: s["updated_at"])
                    if artifact_progress:
                        task["phase"] = "FR69 · " + sample["phase"]
                        task["metrics"].update(sample.get("metrics", {}))
                        if sample.get("total") is not None:
                            task["metrics"]["当前阶段进度"] = (
                                f"{sample['completed']} / {sample['total']} {sample['unit']}")
                        task["last_activity_at"] = max(task["last_activity_at"], sample["updated_at"])
                    else:
                        task.update({k: sample[k] for k in ("phase", "completed", "total", "unit", "metrics")})
                        task.update(detail=sample.get("detail", ""), last_activity_at=sample["updated_at"])
                if task["status"] == "running" and (not process or process["start_ticks"] != task.get("start_ticks")):
                    task.update(status="unconfirmed", phase="进程已退出，结束记录待核验")
                tasks.append(task)
            except (OSError, ValueError, KeyError):
                errors.append("读取已登记任务失败")
    return {"generated_at": time.time(), "tasks": tasks, "resources": resources(), "errors": errors}


def refresh():
    global SNAPSHOT
    while True:
        try:
            SNAPSHOT = build_snapshot()
        except Exception as error:
            SNAPSHOT = {**(SNAPSHOT or {"generated_at": None, "tasks": [], "resources": {}}),
                        "errors": [f"进度刷新失败：{type(error).__name__}"]}
        time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.headers.get("Host") not in (f"127.0.0.1:{self.server.server_port}",
                                            f"localhost:{self.server.server_port}"):
            self.send_error(403)
            return
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self.send_error(403)
            return
        if self.path == "/api/status":
            body, kind = json.dumps(SNAPSHOT, ensure_ascii=False, allow_nan=False).encode(), "application/json"
        elif self.path == "/":
            body, kind = (ROOT / "tools/task_progress/index.html").read_bytes(), "text/html"
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header("Content-Type", kind + "; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; "
                         "script-src 'unsafe-inline'; connect-src 'self'; frame-ancestors 'self'")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
        raise RuntimeError("Use the D-hosted hpc_linux distro")
    resources()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    server.daemon_threads = True
    threading.Thread(target=refresh, daemon=True).start()
    print(f"Task progress: http://localhost:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
