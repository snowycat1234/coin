"""Module integration and sealed, development-only report entry points."""
import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime

import polars as pl

from .data import load_bars, load_minutes, verify_dataset_lock
from .disk import check
from .paths import ROOT


def date_us(value: str) -> int:
    return int(datetime.fromisoformat(value).replace(tzinfo=UTC).timestamp() * 1_000_000)


def frame_digest(frame: pl.DataFrame) -> str:
    import io

    stream = io.BytesIO()
    frame.write_ipc(stream)
    return hashlib.sha256(stream.getvalue()).hexdigest()


def run_baselines() -> dict:
    raise RuntimeError("P03 legacy is frozen; use the V2 baseline suite after A01 acceptance")
    from .backtest import BacktestConfig, baseline_targets, run_backtest

    lock = verify_dataset_lock()
    check(reserve=500_000_000)
    cutoff = date_us(lock["holdout_start_utc"].removesuffix("Z"))
    bars = load_bars().filter(pl.col("available_us") < cutoff)
    minutes = load_minutes().filter(pl.col("open_us") < cutoff)
    output = ROOT / "reports/generated/P03"
    results = {}
    for name in ("B0", "B1", "B2"):
        targets = baseline_targets(bars, name)
        scenarios = {"base": {}}
        if name != "B0":
            scenarios.update({"fee_x2": {"fee_multiplier": 2},
                              "slippage_x2": {"slippage_multiplier": 2},
                              "latency_1m": {"latency_minutes": 1}})
        results[name] = {}
        for scenario, extra in scenarios.items():
            result = run_backtest(bars, minutes, targets,
                                  BacktestConfig(end_us=cutoff, **extra))
            result.write_report(output, f"{name}_{scenario}", disk_checked=True)
            results[name][scenario] = result.summary
            print(json.dumps({"module": "P03", "baseline": name, "scenario": scenario,
                              "net_return": result.summary["total_return"],
                              "sharpe": result.summary["sharpe"]}), flush=True)
    # Real-data reproducibility gate; bounded interval plus causal risk warmup.
    start, end = date_us("2024-01-01"), date_us("2024-01-08")
    replay_minutes = minutes.filter((pl.col("open_us") >= date_us("2023-11-01")) &
                                    (pl.col("open_us") < end))
    replay_bars = bars.filter((pl.col("open_us") >= date_us("2023-11-01")) &
                              (pl.col("available_us") < end))
    replay_targets = baseline_targets(replay_bars, "B2")
    digests = []
    for _ in range(10):
        replay = run_backtest(replay_bars, replay_minutes, replay_targets,
                              BacktestConfig(start_us=start, end_us=end))
        digests.append(hashlib.sha256(json.dumps({
            "summary": replay.summary, "trades": frame_digest(replay.trades),
            "orders": frame_digest(replay.orders), "nav": frame_digest(replay.daily_nav),
        }, sort_keys=True).encode()).hexdigest())
    if len(set(digests)) != 1:
        raise RuntimeError("P03 real-data replay is not deterministic")
    report = {"dataset_id": lock["dataset_id"], "holdout_revealed": False,
              "development_end_exclusive": lock["holdout_start_utc"],
              "config": asdict(BacktestConfig()), "baselines": results,
              "replay_runs": 10, "replay_digest": digests[0], "disk": check()}
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(report, indent=2))
    rows = ["# P03 基线验收结果", "", "最终六个月未查看；仅报告研究区间。", "",
            "| 策略 | 净收益 | 日度Sharpe | 最大回撤 | 手续费USDT | 往返周期 |",
            "|---|---:|---:|---:|---:|---:|"]
    for name, scenarios in results.items():
        base = scenarios["base"]
        rows.append(f"| {name} | {base['total_return']:.2%} | {base['sharpe']:.3f} | "
                    f"{base['max_drawdown']:.2%} | {base['fees']:.2f} | "
                    f"{base['round_trip_count']} |")
    rows.extend(["", "回撤按 UTC 日度可观察 NAV 计算。持仓跨隔离日时，"
                 "未知日内路径不能用于认证回撤上限；恢复报价后的跨缺口损益完整计入。",
                 "", "10 次真实样本回放的订单、成交、NAV 和汇总完全一致。",
                 "", "完整机器记录和费用／滑点／一分钟延迟情景保存在同目录。"])
    (output / "REPORT.md").write_text("\n".join(rows) + "\n")
    return report


def run_registered_research(resume_reason: str | None = None) -> dict:
    raise RuntimeError("Logistic v1 STOP is frozen; use the separately registered V2 study")
    from .research import run_research

    lock = verify_dataset_lock()
    check(reserve=300_000_000)
    return run_research(load_bars(("1h", "15m")), load_minutes(),
                        ROOT / "configs/experiments/logistic_v1.json",
                        ROOT / "reports/generated/P04",
                        ROOT / "state/research_logistic_v1.json",
                        source_hashes={**lock["bar_files"], **lock["minute_files"]},
                        resume_reason=resume_reason)
