"""Sample existing loop counters; never trace, refit, or change algorithm state."""
import json
import os
from pathlib import Path
import sys
import threading
import time

STATE = Path("/home/xflops/coin-state/task-progress")
ROOT = Path("/mnt/d/codex/coin")
START_TICKS = int(Path("/proc/self/stat").read_text().split(") ", 1)[1].split()[19])


def write_snapshot(value):
    STATE.mkdir(exist_ok=True)
    target = STATE / f"sample-{os.getpid()}.json"
    temporary = target.with_suffix(".tmp")
    value["start_ticks"] = START_TICKS
    temporary.write_text(json.dumps(value, ensure_ascii=False, allow_nan=False))
    os.replace(temporary, target)


def inspect_frame(frame):
    """Counters are lower bounds: a batch currently in flight is not completed."""
    name, file, local = frame.f_code.co_name, frame.f_code.co_filename, frame.f_locals
    if file == str(ROOT / "src/quant/disk.py") and name == "tree_bytes":
        return {"phase": "磁盘扫描", "completed": None, "total": None,
                "unit": "文件", "detail": "总文件数尚未知；保留原磁盘守卫",
                "metrics": {"已计入字节": local.get("total", 0),
                            "待扫描目录": len(local.get("pending", [])) + 1}}
    if file == str(ROOT / "src/quant/research_fast/trainer.py"):
        if name == "tabular_arrays" and "offset" in local:
            return {"phase": "准备共同样本", "completed": local["offset"],
                    "total": len(local["indices"]), "unit": "样本", "metrics": {}}
        if name == "fit_sequence" and "loaders" in local:
            history = local.get("history", [])
            # Determine the active phase from the original source line, not stale locals.
            lines = Path(file).read_text().splitlines()
            train_end = next(i + 1 for i, s in enumerate(lines)
                             if s.strip() == "model.eval()" and i + 1 > frame.f_code.co_firstlineno)
            train_loop = next(i + 1 for i, s in enumerate(lines)
                              if s.strip().startswith('for step, batch in enumerate(loaders["train"])'))
            test_start = next(i + 1 for i, s in enumerate(lines)
                              if s.strip() == "model.load_state_dict(best_state)")
            metrics = {"已完成轮次": len(history), "轮次上限": local.get("epochs", 10)}
            if train_loop < frame.f_lineno < train_end and "step" in local:
                return {"phase": f"训练第 {local.get('epoch', 0) + 1} 轮",
                        "completed": local["step"], "total": len(local["loaders"]["train"]),
                        "unit": "批次", "metrics": metrics,
                        "detail": "当前轮次批次进度；可能按原规则提前停止"}
            return {"phase": "测试预测" if frame.f_lineno >= test_start else (
                        "准备训练批次" if frame.f_lineno <= train_loop else "验证当前轮次"),
                    "completed": None, "total": None, "unit": "批次", "metrics": metrics}
    if file == str(ROOT / "third_party/ts2vec/ts2vec.py") and name == "fit":
        model = local.get("self")
        if model is not None:
            return {"phase": "TS2Vec 共同编码器训练", "completed": model.n_iters,
                    "total": local.get("n_iters"), "unit": "迭代", "metrics": {}}
    if file == str(ROOT / "src/quant/research_fast/representation_probes.py") and name == "encoded_arrays":
        return {"phase": "TS2Vec 样本编码", "completed": local.get("start", 0),
                "total": len(local["indices"]), "unit": "样本", "metrics": {}}
    if name == "pytest_runtestloop" and "session" in local and "item" in local:
        session, item = local["session"], local["item"]
        return {"phase": "测试", "completed": session.items.index(item),
                "total": len(session.items), "unit": "测试", "detail": item.name, "metrics": {}}
    return None


def sample_loop(main_id):
    while True:
        try:
            frame = sys._current_frames().get(main_id)
            result = None
            while frame is not None:
                result = inspect_frame(frame)
                if result:
                    break
                frame = frame.f_back
            if result:
                write_snapshot({**result, "pid": os.getpid(), "updated_at": time.time(),
                                "task_id": os.environ.get("COIN_TASK_ID")})
            else:
                # Clear an earlier phase rather than presenting stale counters as live.
                write_snapshot({"phase": "运行中 / 阶段待识别", "completed": None,
                                "total": None, "unit": "", "metrics": {},
                                "pid": os.getpid(), "updated_at": time.time(),
                                "task_id": os.environ.get("COIN_TASK_ID")})
            del frame
        except Exception:
            # Telemetry failure must never change the task result or exception.
            pass
        time.sleep(2)


def start():
    threading.Thread(target=sample_loop, args=(threading.main_thread().ident,), daemon=True,
                     name="task-progress-readonly").start()
