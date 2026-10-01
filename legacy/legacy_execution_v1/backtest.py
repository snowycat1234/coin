"""Deterministic, long-only spot research simulator; never sends exchange orders.

Kline open prices are an execution proxy. Default executions happen one microsecond
after the first minute open at or after signal availability. Capacity is measured
from the *previous* complete minute, and all costs are charged exactly once.
"""

from __future__ import annotations

import heapq
import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import polars as pl

from quant.metrics import daily_metrics

MINUTE_US = 60_000_000
DAY_US = 86_400_000_000
MAX_WEIGHT = 0.30
MAX_GROSS = 0.60
TARGET_ANNUAL_VOL = 0.10


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash: float = 10_000.0
    fee_bps: float = 10.0
    half_spread_bps: float = 1.0
    slippage_bps: float = 4.0
    fee_multiplier: float = 1.0
    slippage_multiplier: float = 1.0
    latency_minutes: int = 0
    start_us: int | None = None
    end_us: int | None = None  # exclusive
    max_weight: float = MAX_WEIGHT
    max_gross: float = MAX_GROSS
    target_annual_vol: float | None = TARGET_ANNUAL_VOL
    vol_window_days: int = 30
    min_vol_days: int = 20
    participation_rate: float = 0.001
    max_order_wait_minutes: int = 5
    liquidate_at_end: bool = False
    min_notional: float = 10.0
    lot_step_by_symbol: dict[str, float] = field(
        default_factory=lambda: {"BTCUSDT": 0.00001, "ETHUSDT": 0.0001},
    )

    def __post_init__(self) -> None:
        if not math.isfinite(self.initial_cash) or self.initial_cash <= 0:
            raise ValueError("initial_cash must be finite and positive")
        if not (0 < self.max_weight <= 0.30 and 0 < self.max_gross <= 0.60):
            raise ValueError("spot weight limits cannot exceed the frozen 30%/60% limits")
        if not 0 < self.participation_rate <= 0.001:
            raise ValueError("participation_rate must be in (0,0.001]")
        if self.target_annual_vol is not None and not 0 < self.target_annual_vol <= 0.10:
            raise ValueError("target_annual_vol cannot exceed the frozen 10% target")
        if not 0 <= self.min_vol_days <= self.vol_window_days or self.vol_window_days < 2:
            raise ValueError("invalid volatility history window")
        if self.latency_minutes < 0 or self.max_order_wait_minutes < 1:
            raise ValueError("invalid execution delay / order lifetime")
        costs = [
            self.fee_bps, self.half_spread_bps, self.slippage_bps,
            self.fee_multiplier, self.slippage_multiplier,
        ]
        if any(not math.isfinite(c) or c < 0 for c in costs):
            raise ValueError("cost parameters must be finite and nonnegative")
        if self.fee_rate >= 1 or self.execution_rate >= 1:
            raise ValueError("cost rates must be below 100%")
        if not math.isfinite(self.min_notional) or self.min_notional < 0:
            raise ValueError("min_notional must be finite and nonnegative")
        if any(not math.isfinite(step) or step <= 0 for step in self.lot_step_by_symbol.values()):
            raise ValueError("lot steps must be finite and positive")

    @property
    def fee_rate(self) -> float:
        return self.fee_bps * self.fee_multiplier / 10_000

    @property
    def execution_rate(self) -> float:
        return (self.half_spread_bps + self.slippage_bps * self.slippage_multiplier) / 10_000


@dataclass
class BacktestResult:
    daily_nav: pl.DataFrame
    trades: pl.DataFrame
    orders: pl.DataFrame
    round_trips: pl.DataFrame
    summary: dict[str, float | int | str | dict]
    config: BacktestConfig

    def write_report(
        self, output_dir: str | Path, name: str = "backtest", *, disk_checked: bool = False,
    ) -> Path:
        """Save a report to D, after reserving its uncompressed size plus 1 MB.

        Batch callers may set disk_checked=True only after one aggregate reservation
        covering every report; this avoids repeatedly scanning the whole project.
        An individual report is bounded to 50 MB even with a batch reservation.
        """
        from quant.disk import check

        destination = Path(output_dir).resolve()
        if not str(destination).startswith("/mnt/d/"):
            raise ValueError("reports must be saved on D: via /mnt/d")
        if Path(name).name != name:
            raise ValueError("name must be a filename stem")
        reserve = sum(frame.estimated_size() for frame in (
            self.daily_nav, self.trades, self.orders, self.round_trips,
        )) + 1_000_000
        if reserve > 50_000_000:
            raise RuntimeError("individual report exceeds the 50 MB artifact budget")
        if not disk_checked:
            check(reserve=reserve)
        destination.mkdir(parents=True, exist_ok=True)
        for label, frame in (
            ("daily_nav", self.daily_nav), ("trades", self.trades),
            ("orders", self.orders), ("round_trips", self.round_trips),
        ):
            frame.write_parquet(destination / f"{name}_{label}.parquet")
        payload = {"config": asdict(self.config), "summary": self.summary}
        (destination / f"{name}.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        summary = self.summary
        terminal_policy = (
            "期末提出清仓目标，并按容量及金额/数量过滤器执行；剩余持仓继续按市值计价。"
            if self.config.liquidate_at_end else "期末按市值计价，没有强制清仓。"
        )
        report = (
            f"# {name}：现货回测报告\n\n"
            f"区间：{summary['start_utc']} 至 {summary['end_utc']}（终点不含）。\n\n"
            "执行采用可用时刻后的分钟开盘价代理；真实成交质量须另行前向验证。"
            "年化依据 UTC 日度 NAV、365 天；首尾不足整日亦按日观测计数。\n\n"
            f"净收益 {summary['total_return']:.4%}；年化收益 {summary['annual_return']:.4%}；"
            f"日度年化波动 {summary['annual_volatility']:.4%}；Sharpe {summary['sharpe']:.4f}；"
            f"最大回撤 {summary['max_drawdown']:.4%}。\n\n"
            f"成交 {summary['trade_count']} 笔；已闭合持仓周期 {summary['round_trip_count']} 笔；"
            f"手续费 {summary['fees']:.4f} USDT；点差与滑点成本 "
            f"{summary['execution_costs']:.4f} USDT；累计单边换手 {summary['turnover']:.4f}。\n\n"
            f"期末持仓：{json.dumps(summary['open_positions'], ensure_ascii=False)}。"
            f"{terminal_policy}未闭合周期不计入往返交易门槛。\n\n"
            f"缺口冻结尝试 {summary['gap_blocks']} 次；容量限额触发 "
            f"{summary['capacity_limits']} 次；过期撤销 {summary['expired_orders']} 次；"
            f"波动历史不足 {summary['warmup_signals']} 次。\n\n"
            f"日终估值缺口 {summary['valuation_gap_days']} 天，其中持仓使用旧价格 "
            f"{summary['exposed_valuation_gap_days']} 天。缺口内数量与现金保留，"
            "下一可得价恢复估值，跨缺口盈亏完整计入；旧价格不是无风险或无价格变动的证据。"
            "最大回撤仅为UTC日度已观察NAV；缺口和日内极值可能造成更大回撤，"
            "存在持仓估值缺口时不能据此认证实际最大回撤门槛。\n\n"
            f"最低金额/余数订单拒绝 {summary['dust_orders']} 次；金额门槛 "
            f"{self.config.min_notional} USDT；数量步长 "
            f"{json.dumps(self.config.lot_step_by_symbol)}。当前过滤器快照用于研究近似，"
            "不代表当年的历史交易规则。\n\n"
            "同目录保存配置、汇总、日度 NAV、成交、订单尝试与闭合周期 Parquet。"
            "费用仅在实际成交时记账，失败尝试没有虚构收益或成本。\n"
        )
        path = destination / f"{name}.md"
        path.write_text(report, encoding="utf-8")
        return path


def _utc(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp / 1_000_000, UTC).isoformat()


def _frame(rows: list[dict], schema: dict[str, pl.DataType]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=schema) if rows else pl.DataFrame(schema=schema)


def baseline_targets(bars: pl.DataFrame, name: str) -> pl.DataFrame:
    """Frozen B0 cash, B1 monthly equal allocation, B2 hourly EMA20/100.

    Returns raw 0/30% weights. The simulator applies the common causal risk policy.
    B2 always requires 1h bars and 100 complete observations before entering.
    """
    if name not in {"B0", "B1", "B2"}:
        raise ValueError("baseline must be B0, B1 or B2")
    if name == "B2" and bars.get_column("interval").unique().to_list() != ["1h"]:
        raise ValueError("B2 is frozen to 1h EMA20/EMA100")
    rows: list[dict] = []
    for symbol in sorted(bars.get_column("symbol").unique().to_list()):
        asset = bars.filter(pl.col("symbol") == symbol).sort("open_us")
        prices = asset.get_column("close").to_numpy()
        available = asset.get_column("available_us").to_numpy()
        open_times = asset.get_column("open_us").to_numpy()
        fast = slow = None
        previous_month = None
        previous_open = None
        consecutive = 0
        for i, (price, timestamp) in enumerate(zip(prices, available, strict=True)):
            if name == "B0" and i > 0:
                continue
            month = datetime.fromtimestamp(int(timestamp) / 1_000_000, UTC).strftime("%Y-%m")
            if name == "B1" and month == previous_month:
                continue
            previous_month = month
            if name == "B2":
                current_open = int(open_times[i])
                if previous_open is None or current_open != previous_open + 60 * MINUTE_US:
                    fast = slow = None
                    consecutive = 0
                previous_open = current_open
                consecutive += 1
                fast = float(price) if fast is None else fast + (float(price) - fast) * 2 / 21
                slow = float(price) if slow is None else slow + (float(price) - slow) * 2 / 101
                weight = MAX_WEIGHT if consecutive >= 100 and fast > slow else 0.0
            else:
                weight = MAX_WEIGHT if name == "B1" else 0.0
            rows.append({"available_us": int(timestamp), "symbol": symbol,
                         "target_weight": weight})
    return _frame(rows, {"available_us": pl.Int64, "symbol": pl.String,
                         "target_weight": pl.Float64}).sort(["available_us", "symbol"])


class _MinuteAsset:
    def __init__(self, frame: pl.DataFrame) -> None:
        self.times = frame.get_column("open_us").to_numpy()
        self.opens = frame.get_column("open").to_numpy()
        self.closes = frame.get_column("close").to_numpy()
        self.quotes = frame.get_column("quote_volume").to_numpy()

    def index(self, timestamp: int) -> int:
        return int(np.searchsorted(self.times, timestamp))

    def mark(self, timestamp: int, close: bool = False) -> tuple[float, bool]:
        index = self.index(timestamp)
        if index < len(self.times) and self.times[index] == timestamp:
            return float(self.closes[index] if close else self.opens[index]), False
        prior = index - 1
        if prior < 0:
            raise ValueError("valuation precedes available minute prices")
        return float(self.closes[prior]), True


def _daily_covariances(
    minutes: pl.DataFrame, symbols: list[str], config: BacktestConfig,
) -> tuple[np.ndarray, list[np.ndarray | None]]:
    """Covariance uses only completed, complete, consecutive UTC days."""
    daily = (
        minutes.with_columns((pl.col("open_us") // DAY_US).alias("day"))
        .group_by(["symbol", "day"])
        .agg(pl.len().alias("count"), pl.col("close").last().alias("close"))
        .filter(pl.col("count") == 1440)
    )
    values = {(r["symbol"], r["day"]): r["close"] for r in daily.iter_rows(named=True)}
    days = sorted(set(daily.get_column("day").to_list()))
    dates: list[int] = []
    covs: list[np.ndarray | None] = []
    returns: list[tuple[int, np.ndarray]] = []
    for day in days:
        valid = all((symbol, day) in values and (symbol, day - 1) in values
                    for symbol in symbols)
        if valid:
            observation = np.array([values[(s, day)] / values[(s, day - 1)] - 1
                                    for s in symbols])
            returns.append((day, observation))
        history = [value for d, value in returns if day - config.vol_window_days < d <= day]
        dates.append((day + 1) * DAY_US)
        cov = None
        if len(history) >= max(2, config.min_vol_days):
            cov = np.atleast_2d(np.cov(np.asarray(history).T, ddof=1)) * 365
        covs.append(cov)
    return np.asarray(dates, dtype=np.int64), covs


def run_backtest(
    bars: pl.DataFrame,
    minute_bars: pl.DataFrame,
    targets: pl.DataFrame,
    config: BacktestConfig | None = None,
) -> BacktestResult:
    """Replay target weights with causal risk, conservative costs and partial fills.

    Pass minute history before ``start_us`` for the 30-day volatility warmup.
    No target from after ``end_us`` is used. ``bars`` establishes allowed decision
    availability timestamps and must contain only complete aggregated bars.
    """
    config = config or BacktestConfig()
    needed = {"symbol", "open_us", "open", "close", "quote_volume"}
    if not needed.issubset(minute_bars.columns) or minute_bars.is_empty():
        raise ValueError("minute_bars requires symbol/open_us/open/close/quote_volume")
    if not {"available_us", "symbol", "target_weight"}.issubset(targets.columns):
        raise ValueError("targets requires available_us/symbol/target_weight")
    minutes = minute_bars.select(sorted(needed)).sort(["symbol", "open_us"])
    if minutes.null_count().to_numpy().sum():
        raise ValueError("minute prices and timestamps cannot be null")
    symbols = sorted(minutes.get_column("symbol").unique().to_list())
    if len(symbols) > 2:
        raise ValueError("first-version simulator supports at most two spot symbols")
    if minutes.select(pl.struct(["symbol", "open_us"]).n_unique()).item() != len(minutes):
        raise ValueError("duplicate minute primary keys")
    bad = minutes.filter(
        (pl.col("open_us") % MINUTE_US != 0)
        | ~pl.col("open").is_finite() | ~pl.col("close").is_finite()
        | ~pl.col("quote_volume").is_finite()
        | (pl.col("open") <= 0) | (pl.col("close") <= 0)
        | (pl.col("quote_volume") < 0)
    )
    if len(bad):
        raise ValueError("invalid minute timestamp, price or liquidity")
    if targets.select(pl.struct(["symbol", "available_us"]).n_unique()).item() != len(targets):
        raise ValueError("duplicate target primary keys")
    if targets.select("symbol", "available_us", "target_weight").null_count().to_numpy().sum():
        raise ValueError("target fields cannot be null")
    if targets.filter(~pl.col("target_weight").is_finite()).height:
        raise ValueError("target weights must be finite")
    if not set(targets.get_column("symbol").unique().to_list()).issubset(symbols):
        raise ValueError("target symbol has no minute prices")
    if not {"symbol", "available_us", "close_us"}.issubset(bars.columns):
        raise ValueError("bars requires symbol/available_us/close_us")
    if bars.filter(pl.col("available_us") < pl.col("close_us")).height:
        raise ValueError("bar cannot be available before its exclusive close")
    allowed = bars.select("symbol", "available_us").unique()
    if targets.select("symbol", "available_us").join(
        allowed, on=["symbol", "available_us"], how="anti",
    ).height:
        raise ValueError("target must use an observed complete bar availability timestamp")
    assets = {symbol: _MinuteAsset(minutes.filter(pl.col("symbol") == symbol))
              for symbol in symbols}
    first = max(int(asset.times[0]) for asset in assets.values())
    last_exclusive = min(int(asset.times[-1]) for asset in assets.values()) + MINUTE_US
    start = first if config.start_us is None else config.start_us
    end = last_exclusive if config.end_us is None else config.end_us
    if start % MINUTE_US or end % MINUTE_US:
        raise ValueError("backtest boundaries must be minute aligned")
    if not first <= start < end <= last_exclusive:
        raise ValueError("boundaries must fit all symbol price histories")
    covariance_times, covariances = _daily_covariances(minutes, symbols, config)
    target_events: dict[int, list[dict]] = {}
    raw = {symbol: 0.0 for symbol in symbols}
    sorted_targets = targets.sort(["available_us", "symbol"])
    prior_targets = sorted_targets.filter(pl.col("available_us") < start)
    for row in prior_targets.group_by("symbol", maintain_order=True).last().iter_rows(named=True):
        target_events.setdefault(start + config.latency_minutes * MINUTE_US, []).append(row)
    for row in sorted_targets.filter(
        (pl.col("available_us") >= start) & (pl.col("available_us") < end)
    ).iter_rows(named=True):
        available = int(row["available_us"])
        when = ((available + MINUTE_US - 1) // MINUTE_US + config.latency_minutes) * MINUTE_US
        if when < end:
            target_events.setdefault(when, []).append(row)
    if config.liquidate_at_end:
        target_events.setdefault(end - MINUTE_US, []).extend(
            {"available_us": end - MINUTE_US - 1, "symbol": s, "target_weight": 0.0}
            for s in symbols
        )
    marks = set()
    for day in range(start // DAY_US, (end - 1) // DAY_US + 1):
        marks.add(min((day + 1) * DAY_US, end) - MINUTE_US)
    queue = sorted(set(target_events) | marks)
    heapq.heapify(queue)
    scheduled = set(queue)
    cash = config.initial_cash
    positions = {symbol: 0.0 for symbol in symbols}
    pending: dict[str, dict] = {}
    cycles = {symbol: {"entry_us": 0, "cost": 0.0, "proceeds": 0.0, "fees": 0.0}
              for symbol in symbols}
    trades: list[dict] = []
    orders: list[dict] = []
    round_trips: list[dict] = []
    daily: list[dict] = []
    daily_fees = daily_costs = daily_notional = 0.0
    previous_nav = config.initial_cash
    warmup_signals = gap_blocks = capacity_limits = expired_orders = dust_orders = 0
    max_observed_weight = max_observed_gross = 0.0
    while queue:
        timestamp = heapq.heappop(queue)
        scheduled.discard(timestamp)
        prices = {symbol: assets[symbol].mark(timestamp)[0] for symbol in symbols}
        nav = cash + sum(positions[s] * prices[s] for s in symbols)
        if timestamp in target_events:
            for row in target_events[timestamp]:
                raw[row["symbol"]] = float(np.clip(row["target_weight"], 0, config.max_weight))
            weights = np.array([raw[s] for s in symbols])
            if weights.sum() > config.max_gross:
                weights *= config.max_gross / weights.sum()
            if config.target_annual_vol is not None and weights.sum() > 0:
                cov_index = int(np.searchsorted(covariance_times, timestamp, side="right")) - 1
                cov = covariances[cov_index] if cov_index >= 0 else None
                if cov is None:
                    weights[:] = 0
                    warmup_signals += 1
                else:
                    annual_vol = float(np.sqrt(max(0, weights @ cov @ weights)))
                    if annual_vol > config.target_annual_vol:
                        weights *= config.target_annual_vol / annual_vol
            # Reserve worst-case sell+buy costs for a full allowed rebalance.
            # Otherwise the second buy's fee can push the first coin above 30% NAV.
            rebalance_cost = config.execution_rate + (1 + config.execution_rate) * config.fee_rate
            weights *= max(0.0, 1 - 2 * config.max_gross * rebalance_cost)
            signal_time = max(int(row["available_us"]) for row in target_events[timestamp])
            for symbol, weight in zip(symbols, weights, strict=True):
                pending[symbol] = {"weight": float(weight), "signal_us": signal_time,
                                   "expires_us": timestamp
                                   + config.max_order_wait_minutes * MINUTE_US}
        liquidity = {}
        gap = False
        for symbol, asset in assets.items():
            i = asset.index(timestamp)
            valid = (i < len(asset.times) and asset.times[i] == timestamp and i > 0
                     and asset.times[i - 1] == timestamp - MINUTE_US)
            gap |= not valid
            liquidity[symbol] = float(asset.quotes[i - 1]) if valid else 0.0
        # Sells release cash before buys; ties use sorted symbols for deterministic replay.
        sequence = sorted(pending, key=lambda s: (
            pending[s]["weight"] * nav - positions[s] * prices[s] >= 0, s,
        ))
        for symbol in sequence:
            goal = pending[symbol]
            mid = prices[symbol]
            nav = cash + sum(positions[s] * prices[s] for s in symbols)
            desired_dollars = goal["weight"] * nav - positions[symbol] * mid
            if abs(desired_dollars) < max(1e-7, nav * 1e-10):
                del pending[symbol]
                continue
            side = "buy" if desired_dollars > 0 else "sell"
            order = {"open_us": timestamp, "signal_us": goal["signal_us"],
                     "symbol": symbol, "side": side, "requested_notional": abs(desired_dollars),
                     "capacity": liquidity[symbol] * config.participation_rate,
                     "filled_notional": 0.0, "status": ""}
            if timestamp >= goal["expires_us"]:
                order["status"] = "expired"
                expired_orders += 1
                del pending[symbol]
            elif gap:
                order["status"] = "gap_frozen"
                gap_blocks += 1
            elif timestamp + 1 <= goal["signal_us"]:
                raise AssertionError("execution is not strictly after signal availability")
            else:
                direction = 1 if side == "buy" else -1
                fill = mid * (1 + direction * config.execution_rate)
                cost_per_quantity = abs(fill - mid) + fill * config.fee_rate
                weight = goal["weight"]
                desired_quantity = abs(desired_dollars) / (
                    mid + weight * cost_per_quantity if side == "buy"
                    else mid - weight * cost_per_quantity
                )
                capacity_quantity = order["capacity"] / fill
                quantity = min(desired_quantity, capacity_quantity)
                if side == "sell":
                    quantity = min(quantity, positions[symbol])
                else:
                    gross = sum(positions[s] * prices[s] for s in symbols)
                    asset_limit = max(0.0, (config.max_weight * nav - positions[symbol] * mid)
                                      / (mid + config.max_weight * cost_per_quantity))
                    gross_limit = max(0.0, (config.max_gross * nav - gross)
                                      / (mid + config.max_gross * cost_per_quantity))
                    quantity = min(quantity, cash / (fill * (1 + config.fee_rate)),
                                   asset_limit, gross_limit)
                    if cost_per_quantity > 0:
                        for other in symbols:
                            if other != symbol:
                                other_limit = max(
                                    0.0,
                                    (nav - positions[other] * prices[other] / config.max_weight)
                                    / cost_per_quantity,
                                )
                                quantity = min(quantity, other_limit)
                step = config.lot_step_by_symbol.get(symbol)
                if step is not None:
                    quantity = math.floor(quantity / step + 1e-9) * step
                if desired_quantity * fill < config.min_notional or (
                    step is not None and desired_quantity < step - 1e-12
                ):
                    order["status"] = "below_min_notional" if side == "buy" else "dust_unexecuted"
                    dust_orders += 1
                    del pending[symbol]
                elif quantity * fill < config.min_notional and quantity > 1e-12:
                    order["status"] = "capacity_below_min" if (
                        capacity_quantity < desired_quantity
                    ) else "below_min_notional"
                    capacity_limits += int(capacity_quantity < desired_quantity)
                    if order["status"] == "below_min_notional":
                        dust_orders += 1
                        del pending[symbol]
                elif quantity <= 1e-12:
                    order["status"] = (
                        "capacity_zero" if capacity_quantity <= 1e-12 else "risk_limit"
                    )
                    capacity_limits += int(capacity_quantity <= 1e-12)
                else:
                    notional = quantity * fill
                    fee = notional * config.fee_rate
                    execution_cost = quantity * abs(fill - mid)
                    cash -= direction * notional + fee
                    if side == "buy" and positions[symbol] <= 1e-12:
                        cycles[symbol] = {"entry_us": timestamp + 1, "cost": 0.0,
                                          "proceeds": 0.0, "fees": 0.0}
                    positions[symbol] += direction * quantity
                    if abs(positions[symbol]) < 1e-10:
                        positions[symbol] = 0.0
                    cycle = cycles[symbol]
                    cycle["fees"] += fee
                    if side == "buy":
                        cycle["cost"] += notional + fee
                    else:
                        cycle["proceeds"] += notional - fee
                    if side == "sell" and positions[symbol] == 0:
                        round_trips.append({"symbol": symbol, "entry_us": cycle["entry_us"],
                                            "exit_us": timestamp + 1,
                                            "pnl": cycle["proceeds"] - cycle["cost"],
                                            "fees": cycle["fees"]})
                    daily_fees += fee
                    daily_costs += execution_cost
                    daily_notional += notional
                    order["filled_notional"] = notional
                    partial = quantity < desired_quantity * (1 - 1e-9)
                    order["status"] = "partial" if partial else "filled"
                    capacity_limits += int(partial and capacity_quantity < desired_quantity)
                    if not partial:
                        del pending[symbol]
                    nav_after = cash + sum(positions[s] * prices[s] for s in symbols)
                    gross_weight = sum(positions[s] * prices[s] for s in symbols) / nav_after
                    asset_weight = positions[symbol] * mid / nav_after
                    all_asset_weights = [positions[s] * prices[s] / nav_after for s in symbols]
                    max_observed_weight = max(max_observed_weight, *all_asset_weights)
                    max_observed_gross = max(max_observed_gross, gross_weight)
                    if cash < -1e-7 or positions[symbol] < -1e-10:
                        raise AssertionError("negative cash or spot position")
                    if side == "buy" and (
                        max(all_asset_weights) > config.max_weight + 1e-9
                        or gross_weight > config.max_gross + 1e-9
                    ):
                        raise AssertionError("new buy exceeds post-cost spot risk limits")
                    trades.append({"execution_us": timestamp + 1, "signal_us": goal["signal_us"],
                                   "symbol": symbol, "side": side, "quantity": quantity,
                                   "mid_price": mid, "fill_price": fill, "notional": notional,
                                   "fee": fee, "execution_cost": execution_cost,
                                   "cash_after": cash, "nav_after": nav_after,
                                   "asset_weight_after": asset_weight,
                                   "gross_weight_after": gross_weight,
                                   "capacity": order["capacity"]})
            orders.append(order)
        retry = timestamp + MINUTE_US
        if pending and retry < end and retry not in scheduled:
            heapq.heappush(queue, retry)
            scheduled.add(retry)
        if timestamp in marks:
            close_marks = {s: assets[s].mark(timestamp, close=True) for s in symbols}
            nav = cash + sum(positions[s] * close_marks[s][0] for s in symbols)
            daily.append({"date": datetime.fromtimestamp(timestamp / 1_000_000, UTC).date(),
                          "nav": nav, "return": nav / previous_nav - 1,
                          "cash": cash, "fees": daily_fees, "execution_costs": daily_costs,
                          "turnover": daily_notional / previous_nav,
                          "gross_weight": sum(positions[s] * close_marks[s][0]
                                              for s in symbols) / nav,
                          "stale_prices": any(mark[1] for mark in close_marks.values()),
                          "stale_exposure": any(close_marks[s][1] and positions[s] > 1e-12
                                                for s in symbols)})
            previous_nav = nav
            daily_fees = daily_costs = daily_notional = 0.0
    daily_frame = _frame(daily, {"date": pl.Date, "nav": pl.Float64, "return": pl.Float64,
                               "cash": pl.Float64, "fees": pl.Float64,
                               "execution_costs": pl.Float64, "turnover": pl.Float64,
                               "gross_weight": pl.Float64, "stale_prices": pl.Boolean,
                               "stale_exposure": pl.Boolean})
    trade_frame = _frame(trades, {"execution_us": pl.Int64, "signal_us": pl.Int64,
                                 "symbol": pl.String, "side": pl.String,
                                 "quantity": pl.Float64, "mid_price": pl.Float64,
                                 "fill_price": pl.Float64, "notional": pl.Float64,
                                 "fee": pl.Float64, "execution_cost": pl.Float64,
                                 "cash_after": pl.Float64, "nav_after": pl.Float64,
                                 "asset_weight_after": pl.Float64,
                                 "gross_weight_after": pl.Float64, "capacity": pl.Float64})
    order_frame = _frame(orders, {"open_us": pl.Int64, "signal_us": pl.Int64,
                                 "symbol": pl.String, "side": pl.String,
                                 "requested_notional": pl.Float64, "capacity": pl.Float64,
                                 "filled_notional": pl.Float64, "status": pl.String})
    cycle_frame = _frame(round_trips, {"symbol": pl.String, "entry_us": pl.Int64,
                                      "exit_us": pl.Int64, "pnl": pl.Float64, "fees": pl.Float64})
    summary = daily_metrics(daily_frame, config.initial_cash)
    summary.update({"start_utc": _utc(start), "end_utc": _utc(end),
                    "trade_count": len(trades), "round_trip_count": len(round_trips),
                    "open_positions": positions.copy(), "gap_blocks": gap_blocks,
                    "capacity_limits": capacity_limits, "expired_orders": expired_orders,
                    "dust_orders": dust_orders,
                    "valuation_gap_days": int(daily_frame["stale_prices"].sum()),
                    "exposed_valuation_gap_days": int(daily_frame["stale_exposure"].sum()),
                    "daily_risk_observable": not daily_frame["stale_exposure"].any(),
                    "drawdown_basis": "UTC_daily_observed_NAV",
                    "warmup_signals": warmup_signals,
                    "max_observed_weight": max_observed_weight,
                    "max_observed_gross": max_observed_gross,
                    "cost_rate_one_way_bps": (config.fee_rate + config.execution_rate) * 10_000,
                    "gross_pnl_before_costs": summary["final_nav"] - config.initial_cash
                    + summary["fees"] + summary["execution_costs"]})
    return BacktestResult(daily_frame, trade_frame, order_frame, cycle_frame, summary, config)
