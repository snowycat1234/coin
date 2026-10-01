"""Frozen candidate four-account branch; no network or trading is started here."""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import math
import os
import sqlite3
from collections.abc import Callable
from contextlib import closing, contextmanager
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from . import disk
from .candidate_strategy import (
    FrozenCandidateStrategy,
    Hourly40FeatureProvider,
    LegacyFeatureProvider,
    LegacyPredictorAdapter,
)
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
    "collector_public_v3.sqlite3",
    "microstructure.sqlite3",
}


def validate_candidate_source(target: Path, mode: str) -> None:
    """Preflight existing source in readonly mode before any lock/schema write."""
    if target.name in PROTECTED_DATABASES or target.name.startswith(
        ("collector_public_", "microstructure")
    ):
        raise HoldoutDenied("禁止复用当前实测/参考数据库")
    if not target.exists():
        return
    try:
        with closing(sqlite3.connect(target.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
            tables = {
                row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            allowed = {
                "closed_bars",
                "quote_minutes",
                "gaps",
                "events",
                "sessions",
                "candidate_source_contract",
                "sqlite_sequence",
            }
            if tables - allowed:
                raise HoldoutDenied("源库有public/microstructure或未知来源绑定，禁止复用")
            if "candidate_source_contract" in tables:
                row = db.execute(
                    "SELECT payload FROM candidate_source_contract WHERE id=1"
                ).fetchone()
                expected = {
                    "version": "candidate_source_v2",
                    "mode": mode,
                    "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                }
                if row is None or json.loads(row[0]) != expected:
                    raise HoldoutDenied("候选source合同与来源/实现版本不同")
            elif tables and mode != "engineering_simulation":
                raise HoldoutDenied("既存source缺专用候选合同，仅明确离线fixture可接入")
    except (sqlite3.DatabaseError, ValueError) as error:
        if isinstance(error, HoldoutDenied):
            raise
        raise HoldoutDenied("候选source只读预检失败") from error


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
        model: dict | None = None,
        predictor=None,
        feature_provider=None,
        decision_policy: str | None = None,
        config: ShadowConfig | None = None,
        release: dict | None = None,
        started_ms: int | None = None,
        initial_health: dict | None = None,
        **kwargs: Any,
    ):
        original = config or ShadowConfig(version="candidate_paper_v1")
        if Path(collector_db).resolve() == Path(db_path).resolve():
            raise HoldoutDenied("候选与source数据库必须分开")
        self._generic = model is None
        if self._generic:
            if original.mode != "engineering_simulation":
                raise HoldoutDenied("STOP_v2：generic候选仅允许离线工程构造，无生产准入")
            if predictor is None:
                raise HoldoutDenied("Generic工程构造需要已载入FrozenPredictor")
            from .execution_contract import ExecutionContractV2

            execution = ExecutionContractV2()
            if any(
                getattr(original, field) != getattr(execution, other)
                for field, other in (
                    ("fee_bps", "fee_bps"),
                    ("half_spread_floor_bps", "half_spread_floor_bps"),
                    ("extra_slippage_bps", "extra_slippage_bps"),
                    ("single_asset_max", "max_weight"),
                    ("gross_max", "max_gross"),
                    ("annual_vol_target", "annual_vol_target"),
                    ("participation_rate", "participation_rate"),
                    ("min_notional", "min_notional"),
                )
            ):
                raise HoldoutDenied("Generic engine risk/cost differs from frozen model contract")
            provider = feature_provider or Hourly40FeatureProvider()
        else:
            if predictor is not None or feature_provider is not None or decision_policy is not None:
                raise HoldoutDenied("Legacy model与generic注入不能混用")
            validate_model(model, original.mode)
            predictor = LegacyPredictorAdapter(model)
            provider = LegacyFeatureProvider(model["interval"], _new_features, update_features)
        self.strategy = FrozenCandidateStrategy(predictor, provider, threshold=decision_policy)
        self.feature_provider = provider
        self.interval = self.strategy.interval
        self._strategy_identity = (id(self.strategy), id(provider), id(predictor))
        if original.mode == "live_paper":
            verify_paper_release(release or {}, model)
            if (initial_health or {}).get("qualified_72h") is not True:
                raise HoldoutDenied("候选开始前缺真实72小时采集资格")
        if not Path(db_path).resolve().is_relative_to(STATE.resolve()):
            raise HoldoutDenied("候选四路径SQLite必须使用独立native STATE")
        validate_candidate_source(Path(collector_db).resolve(), original.mode)
        self.model = copy.deepcopy(model) if model is not None else {"interval": self.interval}
        self.model_sha = (
            canonical_hash(model)
            if model is not None
            else self.strategy.binding()["model_native_sha256"]
        )
        self._model_guard_sha = canonical_hash(self.model)
        self._active_account: str | None = None
        self.binding = {
            "model_sha256": self.model_sha,
            "strategy": self.strategy.binding(),
            "source": original.mode,
            "implementation_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "release_sha256": (release or {}).get("receipt_sha256"),
            "dependencies": {
                name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
                for name in (
                    "collector.py",
                    "shadow.py",
                    "concurrent_budget.py",
                    "research.py",
                    "shadow_v2.py",
                    "execution_contract.py",
                    "candidate_strategy.py",
                    "predictor.py",
                    "features_v2.py",
                    "alpha_rules_v2.py",
                    "decision_policy.py",
                )
            },
        }
        self._binding_guard_sha = canonical_hash(self.binding)
        self._frozen_model_sha = self.model_sha
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
        reference = self.state.get("candidate_binding_sha256")
        if reference is not None:
            anchor = self.db.execute(
                "SELECT payload FROM records WHERE event_key='start:candidate' AND kind='start'"
            ).fetchone()
            if (
                reference != self._binding_guard_sha
                or anchor is None
                or json.loads(anchor[0])["binding"] != self.binding
            ):
                self.close()
                raise HoldoutDenied("候选immutable binding锚/金融引用不符，禁止恢复")
            self.state["candidate_binding"] = copy.deepcopy(self.binding)
        if "candidate_binding" in self.state:
            if self.state["candidate_binding"] != self.binding:
                self.close()
                raise HoldoutDenied("模型、来源或实现版本变化，禁止恢复旧候选账本")
            try:
                self._restore_features()
            except Exception:
                self.close()
                raise
        else:
            now = self.state["started_ms"]
            self.state["candidate_binding"] = self.binding
            self.state["features"] = self.feature_provider.new_state()
            self.state["feature_anchors"] = {}
            self.state["last_candidate_end"] = None
            self.state["account_controls"] = {
                name: {
                    "capacity_used": {},
                    "consumed_quotes": {},
                    "alpha_holding": {},
                    "decision_policy": self.strategy.new_policy_state(),
                }
                for name in SCENARIOS
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
                for symbol in SYMBOLS[:1] if self.feature_provider.pooled else SYMBOLS:
                    self._snapshot_features(now, symbol)
                self._checkpoint(now)

    def _snapshot_features(self, now: int, symbol: str) -> None:
        """One trailing snapshot per completed decision bar, never per quote/minute."""
        if self.feature_provider.pooled:
            self._append(
                now,
                "feature_provider_snapshot",
                self.feature_provider.snapshot(self.state["features"]),
                f"feature_provider_snapshot:{self.seq + 1}",
            )
            self.state["feature_anchors"] = {"provider": self.seq}
            return
        self._append(
            now,
            "feature_snapshot",
            {"symbol": symbol, "state": self.state["features"][symbol]},
            f"feature_snapshot:{symbol}:{self.seq + 1}",
        )
        self.state["feature_anchors"][symbol] = self.seq

    def _checkpoint(self, now: int) -> None:
        if "candidate_binding" not in self.state:
            return super()._checkpoint(now)
        self.state["last_checkpoint_ms"] = now
        self.state["candidate_binding_sha256"] = self._binding_guard_sha
        # The complete immutable binding is already hash-chained in start:candidate.
        # Refer to it; never duplicate model/source contracts in every attempt tick.
        financial = {
            key: value
            for key, value in self.state.items()
            if key not in {"features", "candidate_binding"}
        }
        financial["candidate_binding_sha256"] = self._binding_guard_sha
        self._append(now, "checkpoint", financial, f"checkpoint:{now}:{self.seq + 1}")

    def _restore_features(self) -> None:
        """Rebuild features only. No trading, heartbeat credit, or journal writes."""
        if self.feature_provider.pooled:
            row = self.db.execute(
                "SELECT seq,payload FROM records WHERE kind='feature_provider_snapshot' "
                "ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            declared = self.state.get("feature_anchors", {}).get("provider")
            if row is None or declared is None or row["seq"] < declared:
                self.close()
                raise HoldoutDenied("缺认证联合特征锚，禁止推测恢复")
            self.state["features"] = self.feature_provider.restore(json.loads(row["payload"]))
            for minute in self.db.execute(
                "SELECT payload FROM records WHERE kind='feature_minute' AND seq>? ORDER BY seq",
                (row["seq"],),
            ):
                self._apply_feature_minute(json.loads(minute[0]))
            self.state["feature_anchors"] = {"provider": int(row["seq"])}
            return
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
        self.feature_provider.validate(self.state["features"])

    def _apply_feature_minute(self, minute: dict) -> tuple[list[dict], bool]:
        """Pure feature-state transition reused by live ingestion and recovery."""
        return self.feature_provider.apply_minute(self.state["features"], minute)

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
        if getattr(self, "_tick_guard_checked", False):
            return super()._guard()
        if (
            self.config != self._frozen_config
            or canonical_hash(self.model) != self._model_guard_sha
            or self.interval != self.strategy.interval
            or self.model_sha != self._frozen_model_sha
            or canonical_hash(self.binding) != self._binding_guard_sha
            or (id(self.strategy), id(self.feature_provider), id(self.strategy.predictor))
            != self._strategy_identity
        ):
            raise HoldoutDenied("运行中的冻结模型/参数改变，禁止生成新记录或订单")
        self.strategy.guard()
        super()._guard()

    @contextmanager
    def _account(self, scenario: str):
        # Only the reused fill routine sees an alias. The journal retains actual names.
        old_config, old_b2 = self.config, self.state["accounts"]["B2"]
        old_capacity, old_consumed = self.state["capacity_used"], self.state["consumed_quotes"]
        old_holding = self.state.get("alpha_holding")
        controls = self.state["account_controls"][scenario]
        self.state["accounts"]["B2"] = self.state["accounts"][scenario]
        self.state["capacity_used"], self.state["consumed_quotes"] = (
            controls["capacity_used"],
            controls["consumed_quotes"],
        )
        self.state["alpha_holding"] = controls["alpha_holding"]
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
                alpha_holding=self.state["alpha_holding"],
            )
            self.state["accounts"]["B2"] = old_b2
            self.state["capacity_used"], self.state["consumed_quotes"] = old_capacity, old_consumed
            if old_holding is None:
                self.state.pop("alpha_holding", None)
            else:
                self.state["alpha_holding"] = old_holding
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
                results, boundary = self._apply_feature_minute(normalized)
                for result in results:
                    self._append(
                        received_ms, "feature", result, f"feature:{result['symbol']}:{end}"
                    )
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
        if complete_hour:
            with self._account("B2"):
                changed = super()._decision(now)
        else:
            changed = False
        step_ms = INTERVAL_US[self.interval] // 1000
        end = now // step_ms * step_ms
        if end <= self.state["started_ms"] or self.state["last_candidate_end"] == end:
            return changed
        ready = self.feature_ready(end, now)
        late = now - end > self.config.signal_max_lag_ms
        if self.strategy.legacy:
            if late or not ready:
                self.state["strategy_state"] = "CANDIDATE_FEATURE_WARMUP_OR_MISSING"
                return changed
        elif (
            not ready
            and not late
            and self.feature_provider.phase(self._feature_state(), end * 1000) == "WAITING_FOR_PAIR"
        ):
            # Book quotes can arrive before one or both closed Klines. Do not consume
            # this hour while a timely pair can still arrive in the accepted lag window.
            self.state["strategy_state"] = "WAITING_FOR_PAIRED_CLOSED_HOUR"
            return changed
        outputs = (
            self.strategy.predictions(self._feature_state(), end * 1000, now * 1000)
            if ready and not late
            else dict.fromkeys(SYMBOLS)
        )
        probabilities = {
            symbol: result["confidence"] if result else None for symbol, result in outputs.items()
        }
        # A risk judgement after missing/late evidence is made now, not backdated to
        # the unavailable model signal. Its next-minute eligibility starts from now.
        prediction_missing = any(result is None for result in outputs.values())
        decision_us = now * 1000 if late or not ready or prediction_missing else end * 1000
        self.state["last_candidate_end"] = end
        for scenario in ("candidate", "fee_x2", "slippage_x2"):
            controls = self.state["account_controls"][scenario]
            raw, policies = self.strategy.targets(outputs, end * 1000, controls["decision_policy"])
            raw = {
                symbol: min(self.config.single_asset_max, value) for symbol, value in raw.items()
            }
            with self._account(scenario):
                weights, status = self._risk_weights(raw, now)
                rate = self.execution_contract.execution_rate(
                    self.config.half_spread_floor_bps, self.config.extra_slippage_bps
                )
                reserve = self.execution_contract.rebalance_buffer(
                    rate, self.config.fee_bps / 10_000, self.config.gross_max
                )
                for symbol, policy in policies.items():
                    if policy["minimum_hold_minutes"] == 120:
                        hold = self.state["alpha_holding"].setdefault(
                            symbol,
                            {"last_raw": 0.0, "awaiting_first_fill": False, "first_fill_ms": 0},
                        )
                        if raw[symbol] > 0 and hold["last_raw"] <= 0:
                            hold["awaiting_first_fill"] = True
                        hold["last_raw"] = raw[symbol]
                        policy["risk_forced_exit"] = bool(
                            policy["risk_forced_exit"]
                            or (
                                raw[symbol] > 0
                                and (
                                    reserve <= 0 or weights[symbol] / reserve < raw[symbol] - 1e-12
                                )
                            )
                        )
            self.state["strategy_state"] = status
            account = self.state["accounts"][scenario]
            for symbol, old in account["pending"].items():
                self._append(
                    now,
                    "order_event",
                    {
                        "order_id": old["order_id"],
                        "account": scenario,
                        "symbol": symbol,
                        "scenario": scenario,
                        "status": "SUPERSEDED",
                    },
                    f"superseded:{old['order_id']}:{end}",
                )
            account["pending"] = {}
            self._append(
                now,
                "decision",
                {
                    "scenario": scenario,
                    "account": scenario,
                    "bar_end_ms": end,
                    "probabilities": probabilities,
                    "predictions": outputs,
                    "raw_weights": raw,
                    "target_weights": weights,
                    "state": status,
                    "model_sha256": self.model_sha,
                    "strategy_binding": canonical_hash(self.binding["strategy"]),
                    "decision_asof_us": now * 1000,
                    "risk_missing_or_late": late or not ready or prediction_missing,
                },
                f"decision:{scenario}:{end}",
            )
            for symbol, weight in weights.items():
                order = {
                    "order_id": f"{scenario}:{end}:{symbol}",
                    "account": scenario,
                    "symbol": symbol,
                    "target_weight": weight,
                    **self.execution_contract.order_times_ms(decision_us, now),
                    **policies[symbol],
                }
                account["pending"][symbol] = order
                self._append(
                    now,
                    "order",
                    {**order, "scenario": scenario, "status": "OPEN"},
                    f"order:{order['order_id']}",
                )
        return True

    def _feature_state(self) -> dict:
        return self.state.get("features", getattr(self, "_tick_features", None))

    def feature_ready(self, end_ms: int, now_ms: int) -> bool:
        """Collector readiness consumes provider public rows, including paired receipt."""
        return self.strategy.ready(
            self.feature_provider.latest(self._feature_state()), end_ms * 1000, now_ms * 1000
        )

    def notification_ready(self, end_ms: int, now_ms: int) -> bool:
        if not self.strategy.legacy:
            return self.feature_ready(end_ms, now_ms)
        # Preserve legacy quote coalescing hints. This only wakes a tick; actual
        # inference still requires a complete received_us through feature_ready.
        return all(
            row is not None and row.get("available_us") == end_ms * 1000
            for row in self.feature_provider.latest(self._feature_state()).values()
        )

    def process_tick(self, now_ms: int, health: dict, quotes: list[Quote] | None = None) -> dict:
        # Features only change in ingest_bar, never in a financial tick. Keep that
        # readonly state outside the parent's per-quote JSON rollback copy. Its
        # financial transaction/rollback algorithm and checkpoint remain unchanged.
        self._guard()
        features = self.state.pop("features")
        self._tick_features = features
        self._tick_guard_checked = True
        try:
            return super().process_tick(now_ms, health, quotes)
        finally:
            self.state["features"] = features
            del self._tick_features
            self._tick_guard_checked = False

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
        validate_candidate_source(target, self.candidate_mode)
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
            self.db.execute(
                "CREATE TABLE IF NOT EXISTS candidate_source_contract "
                "(id INTEGER PRIMARY KEY CHECK(id=1),payload TEXT NOT NULL)"
            )
            self.db.execute(
                "INSERT OR IGNORE INTO candidate_source_contract VALUES(1,?)",
                (
                    json.dumps(
                        {
                            "version": "candidate_source_v2",
                            "mode": self.candidate_mode,
                            "source_sha256": hashlib.sha256(
                                Path(__file__).read_bytes()
                            ).hexdigest(),
                        },
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                ),
            )
            self.db.execute(
                "CREATE INDEX IF NOT EXISTS candidate_closed_received "
                "ON closed_bars(symbol,source,received_ms)"
            )
            self.db.commit()
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
                end = received_ms // (INTERVAL_US[self.candidate.interval] // 1000)
                end *= INTERVAL_US[self.candidate.interval] // 1000
                ready = (
                    self._last_candidate_ready_end != end
                    and (self.candidate.state["last_candidate_end"] != end)
                    and self.candidate.notification_ready(end, received_ms)
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
