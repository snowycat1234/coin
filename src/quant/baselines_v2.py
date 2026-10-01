"""Fixed hourly comparators. Signals are causal; canonical evaluation requires A01."""

from __future__ import annotations

import hashlib
import json
import math
import statistics
from collections import deque
from dataclasses import asdict, replace
from pathlib import Path

import polars as pl

from .backtest import BacktestConfig, baseline_targets, run_backtest
from .paths import ROOT

HOUR_US = 3_600_000_000
LOCKED_HISTORICAL_START_US = 1_772_323_200_000_000  # 2026-03-01 UTC
NAMES = ("B0", "B1", "B2", "B3", "B4")
ACTIVE_NAMES = ("B2", "B3", "B4")
RULES = {
    "B3": {"interval": "1h", "entry_previous_high_hours": 55, "exit_previous_low_hours": 20},
    "B4": {"interval": "1h", "return_lag_hours": 168, "ema_span_hours": 168},
}
TARGET_SCHEMA = {"available_us": pl.Int64, "symbol": pl.String, "target_weight": pl.Float64}
SIGNAL_SCHEMA = {
    **TARGET_SCHEMA, "open_us": pl.Int64, "close_us": pl.Int64, "close": pl.Float64,
    "is_long": pl.Boolean, "warmup_complete": pl.Boolean, "entry_channel": pl.Float64,
    "exit_channel": pl.Float64, "ema168": pl.Float64, "return_168h": pl.Float64,
}


class BaselineAdmissionError(ValueError):
    """No canonical performance may run without current execution-parity evidence."""


def _hourly(bars: pl.DataFrame) -> pl.DataFrame:
    required = {"symbol", "interval", "open_us", "close_us", "available_us", "open", "high",
                "low", "close"}
    if not required.issubset(bars.columns):
        raise ValueError("Complete hourly OHLC and availability fields are required")
    frame = bars.select(sorted(required)).sort(["symbol", "open_us"])
    if frame.select(pl.struct(["symbol", "open_us"]).is_duplicated().any()).item():
        raise ValueError("Duplicate hourly bars are prohibited")
    previous: dict[str, int] = {}
    for row in frame.iter_rows(named=True):
        opened, end, available = row["open_us"], row["close_us"], row["available_us"]
        symbol = row["symbol"]
        if (
            symbol not in {"BTCUSDT", "ETHUSDT"}
            or row["interval"] != "1h"
            or not all(isinstance(value, int) for value in (opened, end, available))
            or opened % HOUR_US or end - opened != HOUR_US or available < end
        ):
            raise ValueError("Baseline bars must be complete, aligned BTC/ETH 1h bars")
        if symbol in previous and available <= previous[symbol]:
            raise ValueError(
                "Availability must strictly increase; delayed future inputs prohibited"
            )
        previous[symbol] = available
        values = [row[name] for name in ("open", "high", "low", "close")]
        if any(value is None or not math.isfinite(float(value)) for value in values):
            raise ValueError("OHLC must be finite")
        if not (0 < row["low"] <= min(row["open"], row["close"])
                <= max(row["open"], row["close"]) <= row["high"]):
            raise ValueError("Invalid hourly OHLC")
    return frame


def strong_baseline_signals(bars: pl.DataFrame, name: str) -> pl.DataFrame:
    """B3/B4 long/flat decisions after each full bar. Missing hours reset warmup.

    Breakouts use the observed close against *previous* complete-hour extrema.
    No intrabar touch fill or forward-filled missing hour is inferred.
    """
    if name not in RULES:
        raise ValueError("Strong baseline name must be B3 or B4")
    output = []
    for group in _hourly(bars).partition_by("symbol", maintain_order=True):
        highs, lows, prices = deque(maxlen=55), deque(maxlen=20), deque(maxlen=169)
        last_open, ema, count, long = None, None, 0, False
        for bar in group.iter_rows(named=True):
            opened, price = bar["open_us"], float(bar["close"])
            if last_open is not None and opened != last_open + HOUR_US:
                highs.clear()
                lows.clear()
                prices.clear()
                ema, count, long = None, 0, False
            upper, lower = (max(highs) if len(highs) == 55 else None,
                            min(lows) if len(lows) == 20 else None)
            ema = price if ema is None else ema + (price - ema) * 2 / 169
            count += 1
            prices.append(price)
            lag_return = price / prices[0] - 1 if len(prices) == 169 else None
            warm = upper is not None if name == "B3" else lag_return is not None and count >= 168
            if name == "B3":
                if not warm:
                    long = False
                elif long and price < lower:
                    long = False
                elif not long and price > upper:
                    long = True
            else:
                long = bool(warm and lag_return > 0 and price > ema)
            output.append({
                "available_us": bar["available_us"], "symbol": bar["symbol"],
                "open_us": opened, "close_us": bar["close_us"], "close": price,
                "is_long": long, "warmup_complete": warm,
                "target_weight": 0.30 if long else 0.0,
                "entry_channel": upper if name == "B3" else None,
                "exit_channel": lower if name == "B3" else None,
                "ema168": ema if name == "B4" and count >= 168 else None,
                "return_168h": lag_return if name == "B4" else None,
            })
            highs.append(float(bar["high"]))
            lows.append(float(bar["low"]))
            last_open = opened
    if not output:
        return pl.DataFrame(schema=SIGNAL_SCHEMA)
    return pl.DataFrame(output, schema=SIGNAL_SCHEMA).sort(["available_us", "symbol"])


def baseline_targets_v2(bars: pl.DataFrame, name: str) -> pl.DataFrame:
    """Raw capped weights. The shared backtester performs volatility/cost scaling once."""
    if name not in NAMES:
        raise ValueError("Baseline must be B0..B4")
    if name in RULES:
        return strong_baseline_signals(bars, name).select(list(TARGET_SCHEMA))
    return baseline_targets(_hourly(bars), name)


def _v2_preflight(config: BacktestConfig, parity_receipt: str | Path) -> dict:
    receipt_path = Path(parity_receipt).resolve()
    if not receipt_path.is_relative_to(ROOT):
        raise BaselineAdmissionError("A01 acceptance must be a project artifact")
    if not receipt_path.exists():
        raise BaselineAdmissionError("A01 parity acceptance is not available; no evaluation")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    _verify_parity_receipt(receipt)
    _verify_v2_config(config)
    return receipt


def _verify_parity_receipt(receipt: dict) -> None:
    if (
        receipt.get("status") != "PASS"
        or receipt.get("execution_contract_version") != "execution_v2"
        or receipt.get("cross_engine_parity", {}).get("pass") is not True
        or receipt.get("canonical_baselines", {}).get("status") != "PASS"
    ):
        raise BaselineAdmissionError("A01 canonical baseline/parity receipt has not passed")
    sources = receipt.get("source_hashes")
    if not isinstance(sources, dict) or not sources:
        raise BaselineAdmissionError("A01 current source hashes are missing")
    seen = set()
    source_root = (ROOT / "src/quant").resolve()
    for raw, digest in sources.items():
        relative = Path(raw)
        if relative.is_absolute() or ".." in relative.parts:
            raise BaselineAdmissionError("A01 source paths must be safe relative project files")
        if relative.parts[:2] == ("src", "quant"):
            relative = Path(*relative.parts[2:])
        target = (source_root / relative).resolve()
        if (not target.is_relative_to(source_root) or not target.is_file()
                or target in seen or not isinstance(digest, str)
                or hashlib.sha256(target.read_bytes()).hexdigest() != digest):
            raise BaselineAdmissionError("A01 source digest differs from current implementation")
        seen.add(target)
    if not {source_root / "backtest.py", source_root / "execution_contract.py"}.issubset(seen):
        raise BaselineAdmissionError("A01 execution and historical source bindings are incomplete")
    try:
        from .execution_contract import ExecutionContractV2
    except ImportError as error:
        raise BaselineAdmissionError("ExecutionContractV2 is not implemented") from error
    contract = ExecutionContractV2()
    if (
        receipt.get("execution_contract_sha256") != contract.digest()
        or contract.earliest_execution_us(HOUR_US) != HOUR_US + 60_000_000
    ):
        raise BaselineAdmissionError("ExecutionContractV2 boundary semantics differ")
    baseline = receipt["canonical_baselines"]
    artifact = Path(baseline.get("path", ""))
    artifact = (artifact if artifact.is_absolute() else ROOT / artifact).resolve()
    if not artifact.is_relative_to(ROOT):
        raise BaselineAdmissionError("A01 baseline artifact must stay in project storage")
    if artifact.is_dir():
        artifact /= "summary.json"
    if (not artifact.is_file() or not isinstance(baseline.get("artifact_sha256"), str)
            or hashlib.sha256(artifact.read_bytes()).hexdigest() != baseline["artifact_sha256"]):
        raise BaselineAdmissionError("A01 canonical baseline artifact is absent or changed")


def _verify_v2_config(config: BacktestConfig) -> None:
    expected = {
        "latency_minutes": 1, "max_weight": 0.30, "max_gross": 0.60,
        "target_annual_vol": 0.10, "participation_rate": 0.001,
        "max_order_wait_minutes": 5, "fee_bps": 10.0, "half_spread_bps": 1.0,
        "slippage_bps": 4.0, "fee_multiplier": 1.0, "slippage_multiplier": 1.0,
        "vol_window_days": 30, "min_vol_days": 20, "min_notional": 10.0,
        "lot_step_by_symbol": {"BTCUSDT": 0.00001, "ETHUSDT": 0.0001},
    }
    if any(getattr(config, key) != value for key, value in expected.items()):
        raise BaselineAdmissionError("Canonical V2 execution/cost/risk parameters must be frozen")
    if config.start_us is None or config.end_us is None or config.start_us >= config.end_us:
        raise BaselineAdmissionError("Explicit common start/end are required")
    if config.end_us > LOCKED_HISTORICAL_START_US:
        raise BaselineAdmissionError("Locked historical test cannot be evaluated by baseline suite")


def run_baseline_suite(
    bars: pl.DataFrame, minute_bars: pl.DataFrame, config: BacktestConfig, *,
    parity_receipt: str | Path = ROOT / "reports/A01_EXECUTION_PARITY_ACCEPTANCE.json",
    output_dir: str | Path | None = None, dataset_id: str | None = None,
) -> dict:
    """Evaluate all fixed B0..B4 under V2, after the parent A01 gate passes.

    No dataset loading, model fitting, parameter selection, or release occurs.
    The caller supplies development-only frames; locked-history rows are rejected.
    """
    parity = _v2_preflight(config, parity_receipt)
    if (
        (bars.height and bars["available_us"].max() >= LOCKED_HISTORICAL_START_US)
        or (minute_bars.height and minute_bars["open_us"].max() >= LOCKED_HISTORICAL_START_US)
    ):
        raise BaselineAdmissionError("Inputs contain locked historical test rows")
    target_sets = {name: baseline_targets_v2(bars, name) for name in NAMES}
    destination = Path(output_dir).resolve() if output_dir is not None else None
    if destination is not None:
        if not str(destination).startswith("/mnt/d/"):
            raise BaselineAdmissionError("Reports must use project D storage")
        if destination.exists() and any(destination.iterdir()):
            raise BaselineAdmissionError("Existing evidence cannot be overwritten")
    from . import disk

    # Bound a batch before computing; result frames are released after each report.
    disk.check(reserve=752_000_000)  # 15 reports × 50 MB upper bound plus the summary.
    scenarios = {
        "base": config,
        "fee_x2": replace(config, fee_multiplier=2.0),
        "slippage_x2": replace(config, slippage_multiplier=2.0),
    }
    report = {
        "status": "BASELINE_REPORT_V2", "execution_contract": "ExecutionContractV2",
        "evidence_scope": "DEVELOPMENT_HISTORY", "alpha_candidate": False,
        "locked_historical_test_read": False, "true_forward_days": 0,
        "config": asdict(config), "rules": RULES, "dataset_id": dataset_id,
        "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "A01": parity, "scenarios": {}, "active_baselines": list(ACTIVE_NAMES),
    }
    for scenario, settings in scenarios.items():
        metrics = {}
        for name in NAMES:
            result = run_backtest(bars, minute_bars, target_sets[name], settings)
            metrics[name] = result.summary
            if destination is not None:
                result.write_report(destination, f"{name}_{scenario}", disk_checked=True)
        report["scenarios"][scenario] = {
            "baselines": metrics,
            "active_median_net_return": statistics.median(
                metrics[name]["total_return"] for name in ACTIVE_NAMES
            ),
            "active_median_sharpe": statistics.median(
                metrics[name]["sharpe"] for name in ACTIVE_NAMES
            ),
        }
    if destination is not None:
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "summary.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        lines = ["# A02：固定强基线 V2", "", "仅为开发历史证据，不授予策略或真实前向资格。",
                 "", "执行合同 V2：向分钟上取整后再等一分钟；使用前一完整分钟容量。",
                 "", "|情景|基线|净收益|Sharpe|观察日度MDD|手续费|点差/滑点|换手|闭合周期|",
                 "|---|---|---:|---:|---:|---:|---:|---:|---:|"]
        for scenario, result in report["scenarios"].items():
            for name, value in result["baselines"].items():
                lines.append(
                    f"|{scenario}|{name}|{value['total_return']:.4%}|{value['sharpe']:.4f}|"
                    f"{value['max_drawdown']:.4%}|{value['fees']:.2f}|"
                    f"{value['execution_costs']:.2f}|{value['turnover']:.3f}|"
                    f"{value['round_trip_count']}|"
                )
        lines += ["", "主动基线中位数仅包含 B2/B3/B4；Cash 与 BuyHold 单列。",
                  "缺口、持仓旧价和日内极值风险由每份底层报告保留。",
                  "旧 legacy_execution_v1 报告保持不变；2026-03..08 未消费。"]
        (destination / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
