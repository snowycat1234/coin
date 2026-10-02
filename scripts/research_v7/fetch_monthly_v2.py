"""Thin continuation of the byte-bound monthly converter with an audited monthly boundary."""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta
from pathlib import Path
import sys
import threading

from quant.paths import ROOT
from quant.research_fast.trade_flow_v2 import checksum, private_module, require

sys.path.insert(0, str(Path(__file__).resolve().parent))
from source_view import MONTHLY_STORE, monthly_records
from oracle_flow_ceiling import Progress

V1_SHA = "935917cd8a6215ded1b35e3e0a30a51a9d9c5b997f83a032fa37add9bd42b978"


def monthly_progress():
    """Reuse existing heartbeat/update; initialize honest unknown monthly counters."""
    require(os.environ.get("COIN_TASK_PROGRESS") == "0", "Disable auto sampler for existing explicit Progress writer")
    progress = Progress.__new__(Progress)
    progress.pid = os.getpid()
    progress.ticks = int(Path(f"/proc/{progress.pid}/stat").read_text().split(") ", 1)[1].split()[19])
    progress.value = {"pid": progress.pid, "start_ticks": progress.ticks,
                      "task_id": os.environ.get("COIN_TASK_ID"), "phase": "核对月档来源",
                      "completed": None, "total": None, "unit": "日", "metrics": {},
                      "detail": "来源/下载阶段轮次未知；仅显示真正已发布日数"}
    progress.stop = threading.Event()
    progress.thread = threading.Thread(target=progress.heartbeat, daemon=True)
    progress.thread.start()
    return progress


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", choices=("spot", "perp"), required=True)
    parser.add_argument("--symbol", choices=("BTCUSDT", "ETHUSDT"), required=True)
    parser.add_argument("--month", required=True)
    parser.add_argument("--prior-receipt", type=Path, required=True)
    parser.add_argument("--prior-qa", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    v1_path = ROOT / "scripts/research_v7/fetch_monthly.py"
    require(checksum(v1_path) == V1_SHA, "Accepted V1 monthly source changed")
    records, _ = monthly_records([(args.prior_receipt, args.prior_qa)])
    prior_day = date.fromisoformat(args.month + "-01") - timedelta(days=1)
    key = args.market, args.symbol, prior_day
    require(key in records, "Prior month-end independently audited source required")
    # Future current-month original sources must not be silently relabelled as monthly.
    first = prior_day + timedelta(days=1)
    last = (first.replace(day=28) + timedelta(days=4)).replace(day=1)
    for offset in range((last - first).days):
        day = first + timedelta(days=offset)
        require(not (ROOT / "data/research_fast/trade_flow_5s_v2" / args.market / args.symbol / f"{day}.manifest.json").exists(), "V2 continuation requires a fresh month; use V1 for existing daily overlap")
    module = private_module("v7_byte_bound_monthly_v1", v1_path)
    original_factory, original_sources = module.private_module, module.source_hashes
    module.source_hashes = lambda: {**original_sources(), "scripts/research_v7/fetch_monthly_v2.py": checksum(Path(__file__)), "scripts/research_v7/source_view.py": checksum(ROOT / "scripts/research_v7/source_view.py"), "scripts/research_v7/oracle_flow_ceiling.py": checksum(ROOT / "scripts/research_v7/oracle_flow_ceiling.py")}
    module.DAILY_STORE = MONTHLY_STORE  # V1 receipt records the actual monthly boundary path.

    def factory(name, path):
        value = original_factory(name, path)
        if Path(path) == ROOT / "scripts/hf_fetch_history.py":
            original_resume = value.resume_day

            def resume(market, symbol, day, previous, **kwargs):
                original = original_resume(market, symbol, day, previous, **kwargs)
                if original is not None:
                    return original
                requested = market, symbol, day
                return records[requested]["value"] if requested == key else None

            value.resume_day = resume
        return value

    module.private_module = factory
    progress = monthly_progress()
    original_publish = module.publish

    def publish(path, value):
        original_publish(path, value)
        if Path(path).resolve() != args.output.resolve():
            return
        # Observe the actual durable receipt, never infer completion from a loop index.
        receipt = json.loads(Path(path).read_text())
        done, total = receipt["completed_days"], receipt["required_days"]
        status = receipt["status"]
        if status == "FAILED_MONTHLY_V7_SOURCE_UNACCEPTED":
            phase = "月档失败，来源已保留"
        elif status == "OFFICIAL_MONTHLY_V7_COMPLETE_PENDING_INDEPENDENT_QA":
            phase = "月档转换完成，待独立QA"
        elif done == total:
            phase = "分日完成，最终检查阶段未知"
        elif receipt.get("checksum_status") == "PASS":
            phase = "月档逐日转换"
        else:
            phase = "官方下载/容量预查，具体阶段未知"
        progress.update(phase, done, total, "日", **{
            "已发布Parquet字节": sum(item["parquet_bytes"] for item in receipt["daily"]),
            "月ZIP字节": receipt.get("zip_bytes"), "进程峰值RAM": receipt.get("peak_rss_bytes"),
        })

    module.publish = publish
    try:
        result = module.fetch_month(args.market, args.symbol, args.month, args.run_dir, args.output)
        print(json.dumps({key: result[key] for key in ("status", "completed_days", "elapsed_seconds", "peak_rss_bytes", "raw_deleted")}))
    finally:
        progress.stop.set()
        progress.thread.join(timeout=3)


if __name__ == "__main__":
    main()
