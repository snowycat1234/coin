"""Wrap an authorized command and retain its real exit code for the local viewer."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time
import uuid

ROOT = Path("/mnt/d/codex/coin")
STATE = Path("/home/xflops/coin-state/task-progress")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--title", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("A command is required")
    STATE.mkdir(exist_ok=True)
    identity = uuid.uuid4().hex
    target = STATE / f"task-{identity}.json"
    value = {"id": identity, "title": args.title, "status": "running",
             "started_at": time.time(), "phase": "启动", "completed": None,
             "total": None, "unit": "", "metrics": {}, "children": []}

    def publish():
        temporary = target.with_suffix(".tmp")
        temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False))
        os.replace(temporary, target)

    publish()
    environment = {**os.environ, "COIN_TASK_PROGRESS": "1", "COIN_TASK_ID": identity,
                   "PYTHONPATH": str(ROOT / "tools/task_progress") + os.pathsep
                   + os.environ.get("PYTHONPATH", ""), "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        process = subprocess.Popen(command, env=environment)
    except OSError as error:
        code = 127 if isinstance(error, FileNotFoundError) else 126
        value.update(status="failed", exit_code=code, phase="启动失败",
                     last_activity_at=time.time(), ended_at=time.time(),
                     detail=f"未生成子进程：{type(error).__name__}，包装器退出码 {code}")
        publish()
        return code
    value.update(pid=process.pid, phase="运行中", last_activity_at=time.time())
    try:
        value["start_ticks"] = int(Path(f"/proc/{process.pid}/stat").read_text().split(") ", 1)[1].split()[19])
    except OSError:
        pass  # A very short command may already have exited; wait() below records it.
    publish()
    def forward(signum, _frame):
        process.send_signal(signum)
    signal.signal(signal.SIGTERM, forward)
    signal.signal(signal.SIGINT, forward)
    code = process.wait()
    value.update(status="completed" if code == 0 else "failed", exit_code=code,
                 phase="完成" if code == 0 else "失败", last_activity_at=time.time(),
                 detail=f"实际退出码：{code}", ended_at=time.time())
    publish()
    return code if code >= 0 else 128 - code


if __name__ == "__main__":
    raise SystemExit(main())
