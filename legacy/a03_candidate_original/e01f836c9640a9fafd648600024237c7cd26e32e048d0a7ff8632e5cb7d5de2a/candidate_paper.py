"""Frozen candidate four-account branch; no network or trading is started here."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import disk
from .concurrent_budget import ConcurrentCollector
from .holdout import HoldoutDenied, _development_gate, verify_paper_release
from .paths import STATE
from .research import FEATURE_NAMES, INTERVAL_US, canonical_hash
from .shadow import (
    DAY_MS,
    HOUR_MS,
    MINUTE_MS,
    SYMBOLS,
    Quote,
    ShadowConfig,
)
from .shadow_v2 import ShadowEngineV2

SCENARIOS = ("candidate", "B2", "fee_x2", "slippage_x2")
PROTECTED_DATABASES = {
    "live.sqlite3",
    "shadow.sqlite3",
    "shadow_budget_v2.sqlite3",
    "live_budget_v2.sqlite3",
    "paper.sqlite3",
}


def validate_model(model: dict, mode: str) -> None:
    if mode not in {"engineering_simulation", "live_paper"}:
        raise HoldoutDenied("候选来源模式无效")
    if mode == "engineering_simulation" and model.get("provenance") != "engineering_simulation":
        raise HoldoutDenied("工程分支必须使用明确标识的合成模型")
    if (
        tuple(model.get("features", [])) != FEATURE_NAMES
        or model.get("classes") != [0, 1]
        or model.get("interval") not in INTERVAL_US
        or model.get("configuration", {}).get("interval") != model.get("interval")
    ):
        raise HoldoutDenied("Logistic模型字段或时间级别合同不符")
    for name in ("scaler_mean", "scaler_scale", "coefficients"):
        values = np.asarray(model.get(name, []), dtype=float)
        if values.shape != (len(FEATURE_NAMES),) or not np.isfinite(values).all():
            raise HoldoutDenied("冻结模型系数无效")
        if name == "scaler_scale" and np.any(values <= 0):
            raise HoldoutDenied("冻结scaler尺度必须为正")
    threshold = model["configuration"].get("threshold", 0)
    if not 0.5 <= threshold < 1 or not math.isfinite(float(model.get("intercept", math.nan))):
        raise HoldoutDenied("冻结模型概率合同无效")


def _new_features() -> dict:
    return {
        "last_open_us": None,
        "count": 0,
        "fast": None,
        "slow": None,
        "history": [],
        "latest": None,
        "pending_minutes": [],
    }


def update_features(state: dict, bar: dict, interval: str) -> dict | None:
    """Incremental exact trailing formulas, with persistent EWMA and gap resets."""
    step = INTERVAL_US[interval]
    if state["last_open_us"] is not None and bar["open_us"] != state["last_open_us"] + step:
        state.update(_new_features())
    price = float(bar["close"])
    state["fast"] = (
        price if state["fast"] is None else state["fast"] + (price - state["fast"]) * 2 / 21
    )
    state["slow"] = (
        price if state["slow"] is None else state["slow"] + (price - state["slow"]) * 2 / 101
    )
    state["last_open_us"] = bar["open_us"]
    state["count"] += 1
    state["history"] = (state["history"] + [{"close": bar["close"], "volume": bar["volume"]}])[
        -100:
    ]
    state["latest"] = None
    if state["count"] < 100:
        return None
    history = state["history"]
    closes = np.array([item["close"] for item in history], dtype=float)
    returns = np.diff(np.log(closes))
    volumes = np.array([item["volume"] for item in history[-96:]], dtype=float)
    values = [
        returns[-1],
        math.log(price / closes[-5]),
        math.log(price / closes[-17]),
        float(np.std(returns[-24:], ddof=1)),
        float(np.std(returns[-96:], ddof=1)),
        float((volumes[-1] - np.mean(volumes)) / (np.std(volumes, ddof=1) + 1e-12)),
        (bar["high"] - bar["low"]) / price,
        (price - bar["open"]) / bar["open"],
        state["fast"] / state["slow"] - 1,
        bar["taker_buy_base"] / bar["volume"] if bar["volume"] > 0 else 0.5,
    ]
    result = {
        **dict(zip(FEATURE_NAMES, values, strict=True)),
        "available_us": bar["available_us"],
        "symbol": bar["symbol"],
        "interval": interval,
        "received_us": bar["received_us"],
    }
    if not all(math.isfinite(value) for value in values):
        raise ValueError("因果特征含无效值")
    state["latest"] = result
    return result


class CandidatePaperEngine(ShadowEngineV2):
    """Reuse P05 execution/risk mechanics, with four independent paper accounts."""

    def __init__(
        self,
        collector_db: str | Path,
        db_path: str | Path,
        *,
        model: dict,
        config: ShadowConfig | None = None,
        release: dict | None = None,
        started_ms: int | None = None,
        initial_health: dict | None = None,
        **kwargs: Any,
    ):
        original = config or ShadowConfig(version="candidate_paper_v1")
        if Path(collector_db).resolve() == Path(db_path).resolve():
            raise HoldoutDenied("候选与source数据库必须分开")
        validate_model(model, original.mode)
        if original.mode == "live_paper":
            verify_paper_release(release or {}, model)
            if (initial_health or {}).get("qualified_72h") is not True:
                raise HoldoutDenied("候选开始前缺真实72小时采集资格")
        if not Path(db_path).resolve().is_relative_to(STATE.resolve()):
            raise HoldoutDenied("候选四路径SQLite必须使用独立native STATE")
        self.model = copy.deepcopy(model)
        self.model_sha = canonical_hash(model)
        self._active_account: str | None = None
        self.binding = {
            "model_sha256": self.model_sha,
            "source": original.mode,
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "release_sha256": (release or {}).get("receipt_sha256"),
            "dependencies": {
                name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in ("collector.py", "shadow.py", "concurrent_budget.py", "research.py",
                             "shadow_v2.py", "execution_contract.py")
            },
        }
        frozen = replace(
            original, version=original.version + ":" + canonical_hash(self.binding)[:16]
        )
        super().__init__(
            collector_db,
            db_path,
            config=frozen,
            started_ms=started_ms,
            initial_health=initial_health,
            **kwargs,
        )
        self._frozen_config = self.config
        if "candidate_binding" in self.state:
            if self.state["candidate_binding"] != self.binding:
                self.close()
                raise HoldoutDenied("模型、来源或实现版本变化，禁止恢复旧候选账本")
            self._restore_features()
        else:
            now = self.state["started_ms"]
            self.state["candidate_binding"] = self.binding
            self.state["features"] = {symbol: _new_features() for symbol in SYMBOLS}
            self.state["feature_anchors"] = {}
            self.state["last_candidate_end"] = None
            self.state["account_controls"] = {
                name: {"capacity_used": {}, "consumed_quotes": {}} for name in SCENARIOS
            }
            with self.db:
                for name in SCENARIOS:
                    if name != "B2":
                        self.state["accounts"][name] = copy.deepcopy(self.state["accounts"]["B2"])
                        self._append(
                            now,
                            "start",
                            {
                                "account": name,
                                "scenario": name,
                                "role": "candidate" if name == "candidate" else "cost_stress",
                                "mode": original.mode,
                                "source": "live" if original.mode == "live_paper" else "synthetic",
                                "initial_cash": original.initial_cash,
                                "qualified_72h_at_start": original.mode == "live_paper"
                                and (initial_health or {}).get("qualified_72h") is True,
                                "binding": self.binding,
                            },
                            f"start:{name}",
                        )
                for symbol in SYMBOLS:
                    self._snapshot_features(now, symbol)
                self._checkpoint(now)

    def _snapshot_features(self, now: int, symbol: str) -> None:
        """One trailing snapshot per completed decision bar, never per quote/minute."""
        self._append(
            now,
            "feature_snapshot",
            {"symbol": symbol, "state": self.state["features"][symbol]},
            f"feature_snapshot:{symbol}:{self.seq + 1}",
        )
        self.state["feature_anchors"][symbol] = self.seq

    def _checkpoint(self, now: int) -> None:
        if "features" not in self.state:
            return super()._checkpoint(now)
        self.state["last_checkpoint_ms"] = now
        financial = {key: value for key, value in self.state.items() if key != "features"}
        self._append(now, "checkpoint", financial, f"checkpoint:{now}:{self.seq + 1}")

    def _restore_features(self) -> None:
        """Rebuild features only. No trading, heartbeat credit, or journal writes."""
        self.state["features"] = {}
        anchors = {}
        for symbol in SYMBOLS:
            row = self.db.execute(
                "SELECT seq,payload FROM records WHERE kind='feature_snapshot' "
                "AND json_extract(payload,'$.symbol')=? ORDER BY seq DESC LIMIT 1",
                (symbol,),
            ).fetchone()
            if not row:
                self.close()
                raise HoldoutDenied("缺已认证特征锚，禁止推测恢复")
            declared = self.state.get("feature_anchors", {}).get(symbol)
            if declared is not None and int(row["seq"]) < declared:
                self.close()
                raise HoldoutDenied("金融checkpoint引用未来或缺失特征锚")
            self.state["features"][symbol] = json.loads(row["payload"])["state"]
            anchors[symbol] = int(row["seq"])
        # A feature-only transaction may follow the last financial checkpoint.
        # The complete hash chain is already verified by the parent constructor.
        for row in self.db.execute(
            "SELECT seq,payload FROM records WHERE kind='feature_minute' AND seq>? ORDER BY seq",
            (min(anchors.values()),),
        ):
            minute = json.loads(row["payload"])
            if int(row["seq"]) > anchors[minute["symbol"]]:
                self._apply_feature_minute(minute)
        self.state["feature_anchors"] = anchors

    def _apply_feature_minute(self, minute: dict) -> tuple[dict | None, bool]:
        """Pure feature-state transition reused by live ingestion and recovery."""
        symbol, opened, end = minute["symbol"], minute["open_us"], minute["close_us"]
        state = self.state["features"][symbol]
        minutes = state["pending_minutes"]
        step = INTERVAL_US[self.model["interval"]]
        if minutes and (
            opened != minutes[-1]["open_us"] + MINUTE_MS * 1000
            or opened // step != minutes[-1]["open_us"] // step
        ):
            minutes = []
        names = (
            "symbol", "open_us", "close_us", "open", "high", "low", "close", "volume",
            "quote_volume", "taker_buy_base", "taker_buy_quote",
        )
        minutes = minutes + [{name: minute[name] for name in names}]
        state["pending_minutes"] = minutes
        if end % step:
            return None, False
        complete = (
            len(minutes) == step // (MINUTE_MS * 1000)
            and minutes[0]["open_us"] == end - step
        )
        state["pending_minutes"] = []
        if not complete:
            state.update(_new_features())
            return None, True
        aggregate = {
            "symbol": symbol,
            "open_us": end - step,
            "close_us": end,
            "available_us": end,
            "received_us": minute["received_us"],
            "open": minutes[0]["open"],
            "close": minutes[-1]["close"],
            "high": max(row["high"] for row in minutes),
            "low": min(row["low"] for row in minutes),
            **{
                name: sum(row[name] for row in minutes)
                for name in ("volume", "quote_volume", "taker_buy_base", "taker_buy_quote")
            },
        }
        return update_features(state, aggregate, self.model["interval"]), True

    def _append(self, now: int, kind: str, payload: dict, key: str) -> None:
        active = self._active_account
        if active is not None and active != "B2":
            payload = {**payload}
            for name in ("account", "scenario"):
                if payload.get(name) == "B2":
                    payload[name] = active
            key = active + ":" + key
        super()._append(now, kind, payload, key)

    def _guard(self) -> None:
        if self.config != self._frozen_config or canonical_hash(self.model) != self.model_sha:
            raise HoldoutDenied("运行中的冻结模型/参数改变，禁止生成新记录或订单")
        super()._guard()

    @contextmanager
    def _account(self, scenario: str):
        # Only the reused fill routine sees an alias. The journal retains actual names.
        old_config, old_b2 = self.config, self.state["accounts"]["B2"]
        old_capacity, old_consumed = self.state["capacity_used"], self.state["consumed_quotes"]
        controls = self.state["account_controls"][scenario]
        self.state["accounts"]["B2"] = self.state["accounts"][scenario]
        self.state["capacity_used"], self.state["consumed_quotes"] = (
            controls["capacity_used"],
            controls["consumed_quotes"],
        )
        self._active_account = scenario
        if scenario == "fee_x2":
            self.config = replace(self.config, fee_bps=self.config.fee_bps * 2)
        elif scenario == "slippage_x2":
            self.config = replace(
                self.config, extra_slippage_bps=self.config.extra_slippage_bps * 2
            )
        try:
            yield
        finally:
            controls.update(
                capacity_used=self.state["capacity_used"],
                consumed_quotes=self.state["consumed_quotes"],
            )
            self.state["accounts"]["B2"] = old_b2
            self.state["capacity_used"], self.state["consumed_quotes"] = old_capacity, old_consumed
            self.config, self._active_account = old_config, None

    def _cancel_pending(self, now: int, reason: str) -> bool:
        if "account_controls" not in self.state:
            return super()._cancel_pending(now, reason)
        changed = False
        for scenario in SCENARIOS:
            with self._account(scenario):
                changed |= super()._cancel_pending(now, reason)
        return changed

    def ingest_bar(self, bar: dict, received_ms: int) -> bool:
        """Only originally received complete minute klines; no REST repair inference."""
        self._guard()
        required = (
            "symbol",
            "open_us",
            "close_us",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "quote_volume",
            "taker_buy_base",
            "taker_buy_quote",
        )
        if any(name not in bar for name in required) or bar.get("source") != "websocket":
            raise ValueError("缺原始closed WS kline或V/Q，不得补造候选特征")
        symbol, opened = bar["symbol"], int(bar["open_us"])
        end, received_us = int(bar["close_us"]), received_ms * 1000
        if symbol not in SYMBOLS or opened % (MINUTE_MS * 1000) or end - opened != MINUTE_MS * 1000:
            raise ValueError("closed minute bar时间合同无效")
        if not end <= received_us <= end + 15_000_000:
            raise ValueError("未来、未收盘或迟到回补bar不能生成候选信号")
        normalized = {name: bar[name] for name in required}
        normalized.update(
            received_us=received_us,
            available_us=received_us,
            source="synthetic" if self.config.mode == "engineering_simulation" else "live",
        )
        for name in required[3:]:
            normalized[name] = float(normalized[name])
            if not math.isfinite(normalized[name]) or normalized[name] < 0:
                raise ValueError("bar数值无效")
        if not (
            0
            < normalized["low"]
            <= min(normalized["open"], normalized["close"])
            <= max(normalized["open"], normalized["close"])
            <= normalized["high"]
            and normalized["taker_buy_base"] <= normalized["volume"]
            and normalized["taker_buy_quote"] <= normalized["quote_volume"]
        ):
            raise ValueError("OHLC或主动买入量无效")
        key = f"feature_minute:{symbol}:{opened}"
        previous = self.db.execute(
            "SELECT payload FROM records WHERE event_key=?", (key,)
        ).fetchone()
        if previous:
            stored = json.loads(previous[0])
            # A repeated delivery may have a new receipt time, never changed market data.
            comparison = {name: normalized[name] for name in required}
            comparison["source"] = normalized["source"]
            if any(stored[name] != value for name, value in comparison.items()):
                raise ValueError("已接收候选bar内容改变，禁止重写")
            return False
        state = self.state["features"][symbol]
        minutes = state["pending_minutes"]
        if minutes and opened <= minutes[-1]["open_us"]:
            raise ValueError("候选bar乱序")
        if state["last_open_us"] is not None and opened < state["last_open_us"]:
            raise ValueError("已完成特征前的历史资料不能回补")
        old_state, old_seq, old_head = copy.deepcopy(self.state), self.seq, self.head
        try:
            with self.db:
                self._append(received_ms, "feature_minute", normalized, key)
                result, boundary = self._apply_feature_minute(normalized)
                if result:
                    self._append(received_ms, "feature", result, f"feature:{symbol}:{end}")
                if boundary:
                    self._snapshot_features(received_ms, symbol)
        except Exception:
            self.state, self.seq, self.head = old_state, old_seq, old_head
            raise
        return True

    def _decision(self, now: int) -> bool:
        hour_end = now // HOUR_MS * HOUR_MS
        complete_hour = all(
            self.source.execute(
                "SELECT COUNT(*) FROM closed_bars WHERE symbol=? AND open_ms>=? AND open_ms<? "
                "AND received_ms<=? AND source='websocket'",
                (symbol, hour_end - HOUR_MS, hour_end, now),
            ).fetchone()[0]
            == 60
            for symbol in SYMBOLS
        )
        changed = super()._decision(now) if complete_hour else False
        step_ms = INTERVAL_US[self.model["interval"]] // 1000
        end = now // step_ms * step_ms
        if (
            end <= self.state["started_ms"]
            or self.state["last_candidate_end"] == end
            or now - end > self.config.signal_max_lag_ms
        ):
            return changed
        raw, probabilities = {}, {}
        for symbol in SYMBOLS:
            feature = self.state["features"][symbol]["latest"]
            if (
                feature is None
                or feature["available_us"] != end * 1000
                or feature["received_us"] > now * 1000
            ):
                self.state["strategy_state"] = "CANDIDATE_FEATURE_WARMUP_OR_MISSING"
                return changed
            vector = np.array([feature[name] for name in FEATURE_NAMES])
            standardized = (vector - np.array(self.model["scaler_mean"])) / np.array(
                self.model["scaler_scale"]
            )
            score = float(
                standardized @ np.array(self.model["coefficients"]) + self.model["intercept"]
            )
            probability = float(1 / (1 + math.exp(-float(np.clip(score, -700, 700)))))
            probabilities[symbol] = probability
            raw[symbol] = (
                self.config.single_asset_max
                if probability >= self.model["configuration"]["threshold"]
                else 0.0
            )
        self.state["last_candidate_end"] = end
        for scenario in ("candidate", "fee_x2", "slippage_x2"):
            # Each scenario uses the same risk policy with its own actual cost reserve.
            with self._account(scenario):
                weights, status = self._risk_weights(raw, now)
            self.state["strategy_state"] = status
            account = self.state["accounts"][scenario]
            account["pending"] = {}
            self._append(
                now,
                "decision",
                {
                    "scenario": scenario,
                    "account": scenario,
                    "bar_end_ms": end,
                    "probabilities": probabilities,
                    "raw_weights": raw,
                    "target_weights": weights,
                    "state": status,
                    "model_sha256": self.model_sha,
                },
                f"decision:{scenario}:{end}",
            )
            for symbol, weight in weights.items():
                order = {
                    "order_id": f"{scenario}:{end}:{symbol}",
                    "account": scenario,
                    "symbol": symbol,
                    "target_weight": weight,
                    **self.execution_contract.order_times_ms(end * 1000, now),
                }
                account["pending"][symbol] = order
                self._append(
                    now,
                    "order",
                    {**order, "scenario": scenario, "status": "OPEN"},
                    f"order:{order['order_id']}",
                )
        return True

    def _fill(self, now: int, quotes: dict[str, Quote]) -> bool:
        changed = False
        for scenario in SCENARIOS:
            with self._account(scenario):
                changed |= super()._fill(now, quotes)
        return changed

    def _seal_days(self, now: int) -> bool:
        changed = False
        for day in range(self.state["last_day"] + 1, now // DAY_MS):
            end = (day + 1) * DAY_MS
            if now < end + 2000:
                break
            for scenario in SCENARIOS:
                row = self.db.execute(
                    "SELECT payload FROM records WHERE kind='position' AND "
                    "received_us<? AND json_extract(payload,'$.scenario')=? "
                    "ORDER BY seq DESC LIMIT 1",
                    (end * 1000, scenario),
                ).fetchone()
                account = (
                    json.loads(row[0])
                    if row
                    else {
                        "cash": self.config.initial_cash,
                        "positions": dict.fromkeys(SYMBOLS, 0.0),
                    }
                )
                marks, stale = {}, False
                for symbol in SYMBOLS:
                    mark = self.source.execute(
                        "SELECT open_ms,close FROM closed_bars WHERE symbol=? "
                        "AND open_ms<? AND received_ms<=? AND source='websocket' "
                        "ORDER BY open_ms DESC LIMIT 1",
                        (symbol, end, now),
                    ).fetchone()
                    if account["positions"][symbol] > 0 and (
                        not mark or mark["open_ms"] != end - MINUTE_MS
                    ):
                        stale = True
                    marks[symbol] = float(mark["close"]) if mark else 0.0
                nav = account["cash"] + sum(
                    account["positions"][symbol] * marks[symbol] for symbol in SYMBOLS
                )
                fills = [
                    json.loads(item[0])
                    for item in self.db.execute(
                        "SELECT payload FROM records WHERE kind='fill' "
                        "AND received_us>=? AND received_us<? "
                        "AND json_extract(payload,'$.scenario')=?",
                        (day * DAY_MS * 1000, end * 1000, scenario),
                    )
                ]
                prior = self.db.execute(
                    "SELECT payload FROM records WHERE kind='nav' AND "
                    "json_extract(payload,'$.scenario')=? ORDER BY seq DESC LIMIT 1",
                    (scenario,),
                ).fetchone()
                prior_nav = json.loads(prior[0])["nav"] if prior else self.config.initial_cash
                timely = now - end <= 120_000
                complete = day * DAY_MS >= self.state["started_ms"]
                self._append(
                    now,
                    "nav",
                    {
                        "scenario": scenario,
                        "account": scenario,
                        "date": datetime.fromtimestamp(day * DAY_MS / 1000, UTC).date().isoformat(),
                        "nav": nav,
                        "cash": account["cash"],
                        "positions": account["positions"],
                        "return": nav / prior_nav - 1,
                        "marks": marks,
                        "fees": sum(fill["fee"] for fill in fills),
                        "execution_costs": sum(fill["execution_cost"] for fill in fills),
                        "turnover": sum(fill["notional"] for fill in fills) / prior_nav,
                        "stale_exposure": stale,
                        "daily_risk_observable": not stale and timely,
                        "timely_recorded": timely,
                        "complete_utc_day": complete,
                        "source": "live" if self.config.mode == "live_paper" else "synthetic",
                        "observation_status": "FORWARD" if timely else "MISSED_WHILE_STOPPED",
                    },
                    f"nav:{scenario}:{day}",
                )
            self.state["last_day"] = day
            changed = True
        return changed

    def status(self) -> dict:
        return {
            **super().status(),
            "scope": "frozen_candidate_four_accounts_no_money_authorization",
            "model_sha256": self.model_sha,
            "source": self.config.mode,
            "actual_qualification_days": 0
            if self.config.mode == "engineering_simulation"
            else self.state["healthy_seconds"] / 86_400,
            "accounts": list(SCENARIOS),
        }

    def _reasons(self, now: int, health: dict, quotes: dict[str, Quote]) -> list[str]:
        reasons = super()._reasons(now, health, quotes)
        if self.state.get("candidate_fault"):
            reasons.append(self.state["candidate_fault"])
        return reasons

    def ingest_tick(self, tick: dict) -> dict:
        now = int(tick["received_ms"])
        if tick.get("bar"):
            try:
                self.ingest_bar(tick["bar"], now)
            except ValueError as error:
                with self.db:
                    self.state["candidate_fault"] = "candidate_feature_contract_invalid"
                    self._append(
                        now,
                        "incident",
                        {"kind": "candidate_feature_contract_invalid", "detail": str(error)},
                        f"feature_invalid:{now}",
                    )
                    self._cancel_pending(now, "candidate_feature_contract_invalid")
                    self._checkpoint(now)
        snapshot = tick["health"]
        health = {
            **snapshot,
            "qualified_72h": snapshot.get("qualification", {}).get("qualified_72h", False),
            "state": "RUNNING"
            if snapshot.get("connected") and snapshot.get("live_session")
            else "STOPPED",
        }
        quotes = [
            Quote(
                symbol,
                float(row["bid"]),
                float(row["ask"]),
                int(row["received_ms"]),
                int(row["update_id"]),
            )
            for symbol, row in tick["quotes"].items()
        ]
        return self.process_tick(now, health, quotes)


class CandidateCollector(ConcurrentCollector):
    """Preserve original V/Q through a new subclass without editing frozen Collector."""

    def __init__(
        self,
        *args: Any,
        candidate: CandidatePaperEngine | None = None,
        candidate_factory: Callable | None = None,
        candidate_mode: str | None = None,
        activation_quote_age_ms: int = 5000,
        **kwargs: Any,
    ):
        self.candidate = candidate
        self.candidate_factory = candidate_factory
        self.candidate_mode = (
            candidate.config.mode if candidate else (candidate_mode or "engineering_simulation")
        )
        if (candidate is None) == (candidate_factory is None):
            raise ValueError("必须提供工程candidate或准入后的延迟factory之一")
        self.stage = "CANDIDATE_ACTIVE" if candidate else "WAITING_FOR_REAL_72H"
        self._last_candidate_quote_ms: int | None = None
        self._last_candidate_ready_end: int | None = None
        self.activation_quote_age_ms = min(5000, activation_quote_age_ms)
        if "tick_callback" in kwargs:
            raise ValueError("candidate桥接入口独占回调，禁止替换")
        if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
            raise HoldoutDenied("候选采集仅允许D盘hpc_linux WSL")
        target = Path(
            args[0] if args else kwargs.get("db_path") or STATE / "candidate_live.sqlite3"
        ).resolve()
        if not target.is_relative_to(STATE.resolve()) or target.name in PROTECTED_DATABASES:
            raise HoldoutDenied("候选source须使用独立native STATE，禁止复用现有参考库")
        if candidate is not None and target == candidate.path:
            raise HoldoutDenied("候选与source数据库必须分开")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._source_lock = target.with_suffix(".lock").open("a+")
        try:
            fcntl.flock(self._source_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            self._source_lock.close()
            raise RuntimeError("另一个writer持有候选source锁") from None
        self._candidate_closed = False
        try:
            normalized_args = (target, *args[1:]) if args else ()
            if not args:
                kwargs["db_path"] = target
            super().__init__(*normalized_args, tick_callback=self._candidate_tick, **kwargs)
        except Exception:
            self._source_lock.close()
            raise

    def _candidate_tick(self, tick: dict) -> None:
        if self.candidate is None:
            health = tick["health"]
            qualification = health.get("qualification", {})
            qualified = qualification.get("qualified_72h") is True
            now = tick["received_ms"]
            asof = qualification.get("asof_ms")
            fresh_qualification = isinstance(asof, int) and 0 <= now - asof <= 45_000
            disk_status = health.get("disk", {})
            disk_asof = disk_status.get("asof_ms")
            fresh_disk = (
                disk_status.get("status") in {"OK", "WARNING"}
                and isinstance(disk_asof, int)
                and 0 <= now - disk_asof <= 45_000
            )
            fresh_quotes = all(
                symbol in tick["quotes"]
                and tick["quotes"][symbol].get("source") == "websocket"
                and tick["quotes"][symbol].get("fresh") is True
                and isinstance(tick["quotes"][symbol].get("received_ms"), int)
                and 0 <= now - tick["quotes"][symbol]["received_ms"] <= self.activation_quote_age_ms
                for symbol in SYMBOLS
            )
            if not (
                qualified
                and fresh_qualification
                and fresh_disk
                and fresh_quotes
                and health.get("healthy") is True
                and health.get("connected")
                and health.get("live_session")
            ):
                return
            self.candidate = self.candidate_factory(tick["received_ms"], health)
            if self.candidate.config.mode != self.candidate_mode:
                self.candidate.close()
                raise HoldoutDenied("延迟工厂与冻结来源模式不符")
            self.stage = "CANDIDATE_ACTIVE"
        self.candidate.ingest_tick(tick)

    async def _refresh_disk_budget(self) -> None:
        await super()._refresh_disk_budget()
        if self.candidate is not None:
            self.candidate.refresh_disk_budget(self._disk_ledger)

    def _notify(
        self,
        kind: str,
        symbol: str,
        received_ms: int,
        exchange_ms: int | None,
        bar: dict | None = None,
    ) -> None:
        if kind == "quote":
            previous = self._last_candidate_quote_ms
            ready = False
            if self.candidate is not None and received_ms > self.candidate.state["last_tick_ms"]:
                end = received_ms // (INTERVAL_US[self.candidate.model["interval"]] // 1000)
                end *= INTERVAL_US[self.candidate.model["interval"]] // 1000
                ready = self._last_candidate_ready_end != end and (
                    self.candidate.state["last_candidate_end"] != end
                ) and all(
                    feature["latest"] is not None
                    and feature["latest"]["available_us"] == end * 1000
                    for feature in self.candidate.state["features"].values()
                )
                if ready:
                    self._last_candidate_ready_end = end
            if previous is not None and 0 <= received_ms - previous < 1000 and not ready:
                return
            self._last_candidate_quote_ms = received_ms
        original = self.tick_callback

        def enriched(tick: dict) -> None:
            if bar is not None:
                tick["bar"]["raw_kline"] = dict(bar)
                if "V" in bar and "Q" in bar:
                    tick["bar"].update(
                        taker_buy_base=float(bar["V"]), taker_buy_quote=float(bar["Q"])
                    )
            original(tick)

        self.tick_callback = enriched
        try:
            super()._notify(kind, symbol, received_ms, exchange_ms, bar)
        finally:
            self.tick_callback = original

    async def run(self, *args: Any, **kwargs: Any) -> dict:
        if self.candidate_mode != "live_paper":
            raise HoldoutDenied("engineering_simulation禁止启动真实网络采集")
        result = await super().run(*args, **kwargs)
        return {
            **result,
            "candidate_stage": self.stage,
            "candidate": self.candidate.status() if self.candidate else None,
            "candidate_qualification": "真实180天门槛由P06只读报告评估；本入口不授冠军",
        }

    def close(self) -> None:
        if self._candidate_closed:
            return
        self._candidate_closed = True
        try:
            super().close()
        finally:
            if self.candidate is not None:
                self.candidate.close()
            self._source_lock.close()


def create_candidate_pipeline(
    development_report_path: str | Path,
    model_path: str | Path,
    *,
    release: dict | None = None,
    collector_db: str | Path | None = None,
    candidate_db: str | Path | None = None,
    config: ShadowConfig | None = None,
    **kwargs: Any,
) -> CandidateCollector:
    """Preflight STOP before model/key/db/network I/O; return an explicit dormant runner."""
    report = json.loads(Path(development_report_path).read_text())
    _development_gate(report)
    model = json.loads(Path(model_path).read_text())
    if canonical_hash(model) != report["frozen_model_sha256"]:
        raise HoldoutDenied("接入模型与开发冻结版本不符")
    config = config or ShadowConfig(version="candidate_paper_v1")
    if config.mode != "live_paper":
        raise HoldoutDenied("真实接入入口不接受工程模拟准入；工程直接构造离线对象")
    verify_paper_release(release or {}, model)
    source_path = Path(collector_db or STATE / "candidate_live.sqlite3")
    journal_path = Path(candidate_db or STATE / "candidate_paper.sqlite3")
    if not source_path.resolve().is_relative_to(STATE.resolve()):
        raise HoldoutDenied("候选采集须使用独立native STATE")
    if source_path.name in PROTECTED_DATABASES or journal_path.name in PROTECTED_DATABASES:
        raise HoldoutDenied("禁止复用当前实测/参考数据库")
    if source_path.resolve() == journal_path.resolve():
        raise HoldoutDenied("候选与source数据库必须分开")

    def factory(now: int, health: dict) -> CandidatePaperEngine:
        engine_options = {**kwargs, "initial_disk": runner._disk_ledger}
        return CandidatePaperEngine(
            source_path,
            journal_path,
            model=model,
            config=config,
            release=release,
            started_ms=now,
            initial_health={
                "qualified_72h": health["qualification"]["qualified_72h"],
                "qualification": dict(health["qualification"]),
                "heartbeat_ms": health["heartbeat_ms"],
            },
            **engine_options,
        )

    runner = CandidateCollector(
        source_path,
        candidate_factory=factory,
        candidate_mode="live_paper",
        activation_quote_age_ms=config.max_quote_age_ms,
        disk_check=kwargs.get("disk_check", disk.check),
    )
    return runner
