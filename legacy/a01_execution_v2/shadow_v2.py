"""V2 paper engine. The running legacy reference and its journal remain isolated."""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from pathlib import Path

import numpy as np

from .concurrent_budget import ConcurrentShadowEngine
from .execution_contract import ExecutionContractV2
from .shadow import DAY_MS, HOUR_MS, MINUTE_MS, SYMBOLS, Quote, ShadowConfig


class ShadowEngineV2(ConcurrentShadowEngine):
    def __init__(self, *args, config: ShadowConfig | None = None, **kwargs):
        self.execution_contract = ExecutionContractV2()
        original = config or ShadowConfig(version="paper_baselines_execution_v2")
        if original.order_lifetime_ms != self.execution_contract.max_order_wait_minutes * MINUTE_MS:
            raise ValueError("V2 order lifetime must be five minutes from eligibility")
        dependencies = ("shadow.py", "concurrent_budget.py", "shadow_v2.py",
                        "execution_contract.py")
        binding = self.execution_contract.digest() + "".join(
            hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in dependencies
        )
        frozen = replace(original, version=original.version + ":execution_v2:"
                         + hashlib.sha256(binding.encode()).hexdigest()[:16])
        super().__init__(*args, config=frozen, **kwargs)

    def _risk_weights(self, raw: dict, now: int) -> tuple[dict[str, float], str]:
        # Same 30-day/20-observation causal covariance as the canonical backtest.
        day = now // DAY_MS
        rows = self.source.execute(
            """
            WITH days AS (
                SELECT symbol,open_ms/? AS day,COUNT(*) n,MAX(open_ms) last_open
                FROM closed_bars WHERE open_ms>=? AND open_ms<? AND received_ms<=?
                AND source='websocket' GROUP BY symbol,day
            ) SELECT d.symbol,d.day,d.n,b.close FROM days d JOIN closed_bars b
            ON b.symbol=d.symbol AND b.open_ms=d.last_open WHERE d.n=1440
            """, (DAY_MS, (day - 31) * DAY_MS, day * DAY_MS, now),
        ).fetchall()
        values = {(r["symbol"], r["day"]): float(r["close"]) for r in rows}
        returns = []
        for d in range(day - 30, day):
            if all((s, d) in values and (s, d - 1) in values for s in SYMBOLS):
                returns.append([values[s, d] / values[s, d - 1] - 1 for s in SYMBOLS])
        weights = np.array([min(self.config.single_asset_max, max(0.0, raw[s]))
                            for s in SYMBOLS])
        if weights.sum() > self.config.gross_max:
            weights *= self.config.gross_max / weights.sum()
        if weights.sum() > 0:
            if len(returns) < 20:
                return dict.fromkeys(SYMBOLS, 0.0), "RISK_WARMUP"
            cov = np.atleast_2d(np.cov(np.asarray(returns).T, ddof=1)) * 365
            vol = math.sqrt(max(0, float(weights @ cov @ weights)))
            if vol > self.config.annual_vol_target:
                weights *= self.config.annual_vol_target / vol
        execution_rate = self.execution_contract.execution_rate(
            self.config.half_spread_floor_bps, self.config.extra_slippage_bps,
        )
        weights *= self.execution_contract.rebalance_buffer(
            execution_rate, self.config.fee_bps / 10_000, self.config.gross_max,
        )
        return dict(zip(SYMBOLS, map(float, weights), strict=True)), "READY"

    def _decision(self, now: int) -> bool:
        end = now // HOUR_MS * HOUR_MS
        if end <= self.state["started_ms"] or self.state["last_signal_hour"] == end:
            return False
        if now - end > self.config.signal_max_lag_ms:
            return False
        raw, complete, evidence = self._hour_weights(end, now)
        if not complete:
            self.state["strategy_state"] = "HOUR_INCOMPLETE"
            key = f"blocked_hour:{end}"
            if not self.db.execute("SELECT 1 FROM records WHERE event_key=?", (key,)).fetchone():
                self._append(now, "incident", {
                    "kind": "hour_unusable", "hour_end_ms": end,
                    "reason": "incomplete_or_non_websocket_hour",
                }, key)
                return True
            return False
        weights, status = self._risk_weights(raw, now)
        self.state["strategy_state"] = status
        self.state["last_signal_hour"] = end
        timing = self.execution_contract.order_times_ms(end * 1000, now)
        self._append(now, "decision", {
            "account": "B2", "scenario": "B2", "hour_end_ms": end,
            "raw_weights": raw, "target_weights": weights, "state": status,
            "evidence": evidence, **timing,
        }, f"decision:B2:{end}")
        account = self.state["accounts"]["B2"]
        for symbol, old in account["pending"].items():
            self._append(now, "order_event", {
                "order_id": old["order_id"], "account": "B2", "symbol": symbol,
                "status": "SUPERSEDED",
            }, f"superseded:{old['order_id']}:{end}")
        account["pending"] = {}
        for symbol, weight in weights.items():
            order = {"order_id": f"B2:{end}:{symbol}", "account": "B2",
                     "symbol": symbol, "target_weight": weight, **timing}
            account["pending"][symbol] = order
            self._append(now, "order", {**order, "status": "OPEN"}, f"order:{order['order_id']}")
        return True

    def _fill(self, now: int, quotes: dict[str, Quote]) -> bool:
        account = self.state["accounts"]["B2"]
        prices = {s: (quotes[s].bid + quotes[s].ask) / 2 for s in SYMBOLS}
        nav = account["cash"] + sum(account["positions"][s] * prices[s] for s in SYMBOLS)
        changed = False
        sequence = sorted(
            account["pending"],
            key=lambda s: (
                account["pending"][s]["target_weight"] * nav - account["positions"][s] * prices[s]
                >= 0,
                s,
            ),
        )
        for symbol in sequence:
            order = account["pending"][symbol]
            quote = quotes[symbol]
            if now >= order["expires_ms"]:
                self._append(
                    now,
                    "order_event",
                    {
                        "order_id": order["order_id"],
                        "account": "B2",
                        "symbol": symbol,
                        "status": "EXPIRED",
                    },
                    f"expired:{order['order_id']}",
                )
                del account["pending"][symbol]
                changed = True
                continue
            if (
                quote.received_ms < order["not_before_ms"]
                or quote.received_ms <= order["signal_received_ms"]
            ):
                continue
            if quote.received_ms // MINUTE_MS != now // MINUTE_MS:
                continue
            if quote.update_id <= self.state["consumed_quotes"].get(symbol, -1):
                continue
            prior_open = self.execution_contract.capacity_minute_us(now * 1000) // 1000
            capacity_bar = self.source.execute(
                "SELECT quote_volume,received_ms FROM closed_bars "
                "WHERE symbol=? AND open_ms=? AND source='websocket' AND received_ms<=?",
                (symbol, prior_open, quote.received_ms),
            ).fetchone()
            if not capacity_bar:
                continue
            mid = prices[symbol]
            nav = account["cash"] + sum(account["positions"][s] * prices[s] for s in SYMBOLS)
            weight = order["target_weight"]
            dollars = weight * nav - account["positions"][symbol] * mid
            if abs(dollars) <= 1e-7:
                del account["pending"][symbol]
                changed = True
                continue
            direction = 1 if dollars > 0 else -1
            half_spread = (quote.ask - quote.bid) / (2 * mid) * 10_000
            execution_rate = self.execution_contract.execution_rate(
                max(half_spread, self.config.half_spread_floor_bps),
                self.config.extra_slippage_bps,
            )
            price = mid * (1 + direction * execution_rate)
            fee_rate = self.config.fee_bps / 10_000
            cost_per_q = abs(price - mid) + price * fee_rate
            desired = abs(dollars) / (mid + direction * weight * cost_per_q)
            capacity_key = f"{symbol}:{now // MINUTE_MS}"
            cap = max(
                0,
                float(capacity_bar["quote_volume"]) * self.config.participation_rate
                - self.state["capacity_used"].get(capacity_key, 0),
            )
            quantity = min(desired, cap / price)
            if direction == -1:
                quantity = min(quantity, account["positions"][symbol])
            else:
                gross = sum(account["positions"][s] * prices[s] for s in SYMBOLS)
                quantity = min(
                    quantity,
                    account["cash"] / (price * (1 + fee_rate)),
                    max(
                        0,
                        (self.config.single_asset_max * nav - account["positions"][symbol] * mid)
                        / (mid + self.config.single_asset_max * cost_per_q),
                    ),
                    max(
                        0,
                        (self.config.gross_max * nav - gross)
                        / (mid + self.config.gross_max * cost_per_q),
                    ),
                )
                for other in SYMBOLS:
                    if other != symbol:
                        quantity = min(
                            quantity,
                            max(
                                0,
                                (
                                    nav
                                    - account["positions"][other]
                                    * prices[other]
                                    / self.config.single_asset_max
                                )
                                / cost_per_q,
                            ),
                        )
            step = 0.00001 if symbol == "BTCUSDT" else 0.0001
            quantity = math.floor(quantity / step + 1e-9) * step
            self.state["consumed_quotes"][symbol] = quote.update_id
            changed = True
            if quantity * price < self.config.min_notional:
                status = (
                    "DUST_UNEXECUTED"
                    if desired * price < self.config.min_notional
                    else "CAPACITY_OR_RISK"
                )
                self._append(
                    now,
                    "order_event",
                    {
                        "order_id": order["order_id"],
                        "account": "B2",
                        "symbol": symbol,
                        "status": status,
                        "quote_id": quote.update_id,
                    },
                    f"attempt:{order['order_id']}:{quote.update_id}",
                )
                if status == "DUST_UNEXECUTED":
                    del account["pending"][symbol]
                continue
            notional, fee = quantity * price, quantity * price * fee_rate
            account["cash"] -= direction * notional + fee
            cycle = account["cycles"][symbol]
            if direction == 1 and account["positions"][symbol] <= 1e-12:
                cycle = {"entry_ms": now, "cost": 0.0, "proceeds": 0.0, "fees": 0.0}
                account["cycles"][symbol] = cycle
            account["positions"][symbol] += direction * quantity
            if abs(account["positions"][symbol]) < 1e-10:
                account["positions"][symbol] = 0.0
            cycle["fees"] += fee
            if direction == 1:
                cycle["cost"] += notional + fee
            else:
                cycle["proceeds"] += notional - fee
            if direction == -1 and account["positions"][symbol] == 0:
                self._append(
                    now,
                    "round_trip",
                    {
                        "scenario": "B2",
                        "account": "B2",
                        "symbol": symbol,
                        "cycle_id": f"{symbol}:{cycle['entry_ms']}",
                        "pnl": cycle["proceeds"] - cycle["cost"],
                    },
                    f"round_trip:{symbol}:{cycle['entry_ms']}",
                )
            nav_after = account["cash"] + sum(account["positions"][s] * prices[s] for s in SYMBOLS)
            if account["cash"] < -1e-7 or min(account["positions"].values()) < -1e-10:
                raise AssertionError("negative paper cash or spot quantity")
            if direction == 1 and (
                max(account["positions"][s] * prices[s] / nav_after for s in SYMBOLS)
                > self.config.single_asset_max + 1e-9
                or sum(account["positions"][s] * prices[s] / nav_after for s in SYMBOLS)
                > self.config.gross_max + 1e-9
            ):
                raise AssertionError("new paper buy exceeds post-cost risk limits")
            self.state["capacity_used"][capacity_key] = (
                self.state["capacity_used"].get(capacity_key, 0) + notional
            )
            fill = {
                "execution_contract_version": self.execution_contract.version,
                "signal_us": order["decision_us"],
                "eligible_us": order["not_before_ms"] * 1000,
                "expires_us": order["expires_ms"] * 1000,
                "scenario": "B2",
                "account": "B2",
                "order_id": order["order_id"],
                "symbol": symbol,
                "side": "buy" if direction == 1 else "sell",
                "quantity": quantity,
                "price": price,
                "mid": mid,
                "notional": notional,
                "fee": fee,
                "execution_cost": quantity * abs(price - mid),
                "half_spread_bps": half_spread,
                "quote_id": quote.update_id,
                "quote_received_ms": quote.received_ms,
                "capacity_bar_open_ms": prior_open,
                "capacity_bar_received_ms": capacity_bar["received_ms"],
                "capacity_limit": float(capacity_bar["quote_volume"])
                * self.config.participation_rate,
            }
            self._append(now, "fill", fill, f"fill:{order['order_id']}:{quote.update_id}")
            self._append(
                now,
                "position",
                {
                    "account": "B2",
                    "scenario": "B2",
                    "cash": account["cash"],
                    "positions": account["positions"].copy(),
                },
                f"position:{order['order_id']}:{quote.update_id}",
            )
            if quantity >= desired * (1 - 1e-9):
                del account["pending"][symbol]
        self.state["capacity_used"] = {
            k: v
            for k, v in self.state["capacity_used"].items()
            if int(k.rsplit(":", 1)[1]) >= now // MINUTE_MS - 1
        }
        return changed

