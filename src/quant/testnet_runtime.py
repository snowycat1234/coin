"""G47: verified candidate -> Spot Testnet orchestration, default STOP before secrets.

The engineering branch requires MockTransport and labelled synthetic artifacts.
It exercises the complete order loop but can never grant real network permission.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import math
import os
import sqlite3
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_UP, Decimal
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx
import numpy as np
import websockets

from . import collector, disk, resources
from .candidate_paper import validate_model
from .execution import ExecutionEngine, ExecutionError, NetworkGate, RiskContext, SymbolRules
from .forward_report import read_forward_report
from .holdout import _development_gate, verify_paper_release
from .paths import ROOT, STATE, utc_now_us
from .research import canonical_hash, evaluate_gates
from .shadow import read_forward_evidence
from .testnet import (
    TESTNET_ORIGIN,
    ExecutionUnknown,
    NetworkDisabled,
    ProtocolRejected,
    RateLimited,
    SpotTestnetAdapter,
    decimal_text,
)

SYMBOLS = ("BTCUSDT", "ETHUSDT")
DAY_US = 86_400_000_000
MINUTE_US = 60_000_000
EXTRA_READS = {
    "/api/v3/account/commission",
    "/api/v3/myFilters",
    "/api/v3/referencePrice",
    "/api/v3/avgPrice",
    "/api/v3/ticker/price",
}


class RuntimeDenied(ValueError):
    pass


def exact(value: Any) -> Decimal:
    return Decimal(decimal_text(value, positive=False))


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _read_json(path: Path | None) -> dict:
    if path is None:
        raise RuntimeDenied("Required evidence artifact is absent")
    target = Path(path).resolve()
    if not (target.is_relative_to(ROOT.resolve()) or target.is_relative_to(STATE.resolve())):
        raise RuntimeDenied("Evidence must remain on D in ROOT or native STATE")
    return json.loads(target.read_text())


def _native(path: Path | None) -> Path:
    if path is None or not Path(path).resolve().is_relative_to(STATE.resolve()):
        raise RuntimeDenied("A native D-hosted STATE database is required")
    return Path(path).resolve()


@dataclass(frozen=True)
class EvidenceBundle:
    development_path: Path | None = None
    model_path: Path | None = None
    protocol_path: Path | None = None
    release_path: Path | None = None
    collector_db: Path | None = None
    paper_db: Path | None = None
    version: str | None = None
    engineering_fixture: bool = False


class EvidenceVerifier:
    """Re-read actual sources. No caller-supplied PASS or NetworkGate is consumed."""

    def __init__(self, bundle: EvidenceBundle, *, engineering_disk_check: Callable | None = None):
        if engineering_disk_check and not bundle.engineering_fixture:
            raise RuntimeDenied("Disk evidence injection is confined to engineering fixtures")
        self.bundle = bundle
        self.disk_check = engineering_disk_check or disk.check

    def _release(self, receipt: dict, model: dict) -> None:
        if not self.bundle.engineering_fixture:
            verify_paper_release(receipt, model)
            return
        if (
            receipt.get("status") != "ENGINEERING_ONLY"
            or receipt.get("engineering") is not True
            or model.get("provenance") != "engineering_simulation"
        ):
            raise RuntimeDenied("Engineering artifacts must be explicitly synthetic")
        db = sqlite3.connect(f"file:{_native(Path(receipt['state_db']))}?mode=ro", uri=True)
        try:
            row = db.execute(
                "SELECT receipt_sha,receipt FROM receipts WHERE ticket_sha=?",
                (receipt["ticket_sha256"],),
            ).fetchone()
            body = {
                key: value
                for key, value in receipt.items()
                if key not in {"receipt_sha256", "state_db"}
            }
            if (
                not row
                or canonical_hash(body) != row[0]
                or row[0] != receipt["receipt_sha256"]
                or json.loads(row[1]) != body
            ):
                raise RuntimeDenied("Engineering receipt lacks matching persisted content")
            sqls = dict(db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger'"))
            for table in ("attempts", "receipts"):
                for action in ("update", "delete"):
                    sql = sqls.get(f"{table}_no_{action}", "")
                    if f"BEFORE {action.upper()} ON {table}" not in sql or "RAISE(ABORT" not in sql:
                        raise RuntimeDenied("Release ledger lacks immutable triggers")
        finally:
            db.close()

    def verify(self) -> dict:
        result = {
            "status": "STOP",
            "live_eligible": False,
            "engineering": self.bundle.engineering_fixture,
            "reasons": [],
            "network_authorized": False,
        }
        try:
            if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
                raise RuntimeDenied("D-hosted hpc_linux is required")
            # This deliberately precedes reading models, private credentials, or any HTTP.
            development = _read_json(self.bundle.development_path)
            _development_gate(development)
            model, protocol = (
                _read_json(self.bundle.model_path),
                _read_json(self.bundle.protocol_path),
            )
            receipt = _read_json(self.bundle.release_path)
            validate_model(
                model, "engineering_simulation" if self.bundle.engineering_fixture else "live_paper"
            )
            model_sha, protocol_sha = canonical_hash(model), canonical_hash(protocol)
            if (
                development["frozen_model_sha256"] != model_sha
                or development["protocol_sha256"] != protocol_sha
                or model["protocol_sha256"] != protocol_sha
                or receipt["model_sha256"] != model_sha
                or receipt["protocol_sha256"] != protocol_sha
                or receipt["dataset_id"] != development["dataset_id"]
            ):
                raise RuntimeDenied("Candidate, dataset and protocol bindings differ")
            if protocol.get("risk") != {
                "single_asset_max": 0.3,
                "gross_max": 0.6,
                "annual_vol_target": 0.1,
            }:
                raise RuntimeDenied("Frozen portfolio contract has changed")
            thresholds = {
                "positive_net_return": True,
                "minimum_sharpe": 0.8,
                "maximum_drawdown": 0.15,
                "minimum_round_trips": 30,
                "maximum_quarter_profit_fraction": 0.7,
                "exceed_B2": True,
                "nonnegative_cost_stress": True,
            }
            if protocol["gates"] != thresholds or protocol.get("primary_baseline") != "B2":
                raise RuntimeDenied("Candidate admission thresholds cannot be weakened")
            for evidence in (development["candidates"][model["interval"]], receipt["result"]):
                # Recompute from recorded metrics; don't trust gate booleans.
                computed = evaluate_gates(
                    evidence["summary"],
                    evidence["B2"],
                    evidence["stress"],
                    evidence["quarter_profit_fraction"],
                    thresholds,
                )
                if not computed["development_passed"]:
                    raise RuntimeDenied("Recomputed development/holdout metrics failed admission")
            self._release(receipt, model)
            paper_db, live_db = _native(self.bundle.paper_db), _native(self.bundle.collector_db)
            snapshot = read_forward_evidence(paper_db, self.bundle.version)
            starts = [
                row
                for row in snapshot["records"]
                if row["version"] == self.bundle.version
                and row["kind"] == "start"
                and row["payload"].get("role") == "candidate"
            ]
            if len(starts) != 1:
                raise RuntimeDenied("One frozen candidate start is required")
            binding = starts[0]["payload"].get("binding", {})
            if binding.get("model_sha256") != model_sha:
                raise RuntimeDenied("Forward candidate is not the admitted frozen model")
            if binding.get("release_sha256") != receipt["receipt_sha256"]:
                raise RuntimeDenied("Forward candidate did not start from this admitted release")
            for name, digest in binding.get("dependencies", {}).items():
                target = Path(__file__).with_name(name)
                if name not in {
                    "collector.py",
                    "shadow.py",
                    "research.py",
                    "concurrent_budget.py",
                } or (hashlib.sha256(target.read_bytes()).hexdigest() != digest):
                    raise RuntimeDenied("Forward candidate dependency changed")
            if set(binding.get("dependencies", {})) != {
                "collector.py",
                "shadow.py",
                "research.py",
                "concurrent_budget.py",
            }:
                raise RuntimeDenied("Forward source implementation bindings missing")
            if (
                binding.get("implementation_sha256")
                != hashlib.sha256(
                    Path(__file__).with_name("candidate_paper.py").read_bytes()
                ).hexdigest()
            ):
                raise RuntimeDenied("Candidate signal implementation changed")
            forward = read_forward_report(paper_db, self.bundle.version)
            if self.bundle.engineering_fixture:
                if (
                    snapshot["mode"] != "engineering_simulation"
                    or snapshot["provenance"] != "synthetic"
                ):
                    raise RuntimeDenied("Engineering journal has no synthetic provenance")
                if forward["status"] == "FAIL":
                    raise RuntimeDenied("Engineering forward chain is invalid")
                db = sqlite3.connect(f"file:{live_db}?mode=ro", uri=True)
                try:
                    marker = db.execute("SELECT mode FROM runtime_fixture").fetchone()
                    if not marker or marker[0] != "engineering_simulation":
                        raise RuntimeDenied("Engineering market source marker missing")
                finally:
                    db.close()
                collection = {"qualified_72h": False, "source": "synthetic", "real_hours": 0}
            else:
                collection = collector.status(live_db)
                if collection["qualified_72h"] is not True:
                    raise RuntimeDenied("Recomputed real 72-hour collection evidence did not pass")
                if forward["status"] != "PASS" or forward.get("actual_elapsed_days", 0) < 180:
                    raise RuntimeDenied("Recomputed real P06 evidence did not pass 180 days")
                if forward["last_received_us"] > utc_now_us():
                    raise RuntimeDenied("Forward journal claims observations in the future")
            memory, ledger = resources.status(), self.disk_check(reserve=100_000_000)
            if memory["ram_current_bytes"] >= 4_500_000_000 or ledger["status"] not in {
                "OK",
                "WARNING",
            }:
                raise RuntimeDenied("Insufficient bounded process resources")
            evidence_hashes = {
                "candidate": canonical_hash(receipt),
                "real_72h": canonical_hash(collection),
                "real_180d": canonical_hash(forward),
                "resources": canonical_hash([memory, ledger]),
            }
            result.update(
                status="ENGINEERING_READY" if self.bundle.engineering_fixture else "VERIFIED",
                live_eligible=not self.bundle.engineering_fixture,
                model=model,
                protocol=protocol,
                model_sha256=model_sha,
                release=receipt,
                version=self.bundle.version,
                paper_head=snapshot["head_hash"],
                paper_seq=snapshot["seq"],
                candidate_start=starts[0],
                evidence_hashes=evidence_hashes,
                collection=collection,
                forward=forward,
                memory=memory,
                disk=ledger,
            )
        except Exception as error:
            result["reasons"] = [f"{type(error).__name__}: {error}"]
        return result


class RuntimeTestnetAdapter(SpotTestnetAdapter):
    """Additional read-only endpoints; the frozen order adapter remains unchanged."""

    async def _extra_read(
        self, path: str, *, symbol: str | None = None, signed: bool = True
    ) -> Any:
        if path not in EXTRA_READS and path != "/api/v3/openOrders":
            raise ProtocolRejected("Runtime metadata endpoint not allowlisted")
        if symbol is not None and symbol not in SYMBOLS:
            raise ProtocolRejected("Symbol outside frozen universe")
        if not self.network and self._transport is None:
            raise NetworkDisabled("Network is disabled before metadata request")
        now = self._clock()
        if now < self.cooldown_until_ms:
            raise RateLimited((self.cooldown_until_ms - now) / 1000, self.cooldown_until_ms)
        params, headers = ({"symbol": symbol} if symbol else {}), {"Accept": "application/json"}
        if signed:
            if (
                not self._api_key
                or not self._secret
                or self._synced_at_ms is None
                or not 0 <= now - self._synced_at_ms <= 1_800_000
            ):
                raise ProtocolRejected("Explicit keys and synchronized clock are required")
            params.update(timestamp=now + self._offset_ms, recvWindow=self.recv_window_ms)
            headers["X-MBX-APIKEY"] = self._api_key
        query = urlencode(params)
        if signed:
            query += (
                "&signature="
                + hmac.new(self._secret.encode(), query.encode(), hashlib.sha256).hexdigest()
            )
        while self._request_times and self._request_times[0] <= now - 60_000:
            self._request_times.popleft()
        recent = [stamp for stamp in self._request_times if stamp > now - 10_000]
        if len(self._request_times) >= 60 or len(recent) >= 40:
            until = (
                self._request_times[0] + 60_000
                if len(self._request_times) >= 60
                else recent[0] + 10_000
            )
            self.cooldown_until_ms = until
            raise RateLimited((until - now) / 1000, until)
        self._request_times.append(now)
        if self._client is None:
            self._client = httpx.AsyncClient(
                transport=self._transport,
                timeout=self._timeout,
                follow_redirects=False,
                trust_env=False,
            )
        try:
            response = await self._client.get(TESTNET_ORIGIN + path + "?" + query, headers=headers)
        except httpx.TransportError:
            raise ExecutionUnknown("Runtime metadata transport failed") from None
        if response.status_code in {418, 429}:
            try:
                retry = float(response.headers.get("Retry-After", "60"))
                if not math.isfinite(retry) or retry < 0:
                    raise ValueError
            except ValueError:
                retry = 60
            self.cooldown_until_ms = now + math.ceil(retry * 1000)
            raise RateLimited(retry, self.cooldown_until_ms, response.status_code)
        if response.status_code >= 500 or 300 <= response.status_code < 400:
            raise ExecutionUnknown("Metadata HTTP failure or forbidden redirect")
        try:
            body = response.json()
        except ValueError:
            raise ExecutionUnknown("Metadata JSON malformed") from None
        if isinstance(body, dict) and isinstance(body.get("code"), int) and body["code"] < 0:
            if body["code"] == -1021:
                self._synced_at_ms = None
            raise ProtocolRejected("Metadata API rejected", code=body["code"])
        if response.status_code >= 400:
            raise ExecutionUnknown("Metadata HTTP error lacks confirmed data")
        return body

    async def commission(self, symbol: str) -> dict:
        return await self._extra_read("/api/v3/account/commission", symbol=symbol)

    async def relevant_filters(self, symbol: str) -> dict:
        return await self._extra_read("/api/v3/myFilters", symbol=symbol)

    async def all_open_orders(self) -> list:
        body = await self._extra_read("/api/v3/openOrders")
        if not isinstance(body, list):
            raise ExecutionUnknown("Account-wide open order snapshot is incomplete")
        return body

    async def references(self, symbol: str, minutes: set[int]) -> tuple[dict[int, str], int]:
        try:
            body = await self._extra_read("/api/v3/referencePrice", symbol=symbol, signed=False)
        except ProtocolRejected as error:
            if error.code != -2043:
                raise
            body = {"symbol": symbol, "referencePrice": None}
        if body.get("symbol") != symbol:
            raise ExecutionUnknown("Reference price symbol mismatch")
        if body.get("referencePrice") is not None:
            asof = body["timestamp"] * 1000
            price = decimal_text(body["referencePrice"])
            return dict.fromkeys(minutes, price), asof
        values, asof = {}, utc_now_us()
        if 0 in minutes:
            last = await self._extra_read("/api/v3/ticker/price", symbol=symbol, signed=False)
            if last.get("symbol") != symbol:
                raise ExecutionUnknown("Last price symbol mismatch")
            values[0] = decimal_text(last["price"])
        if minutes - {0}:
            average = await self._extra_read("/api/v3/avgPrice", symbol=symbol, signed=False)
            if set(minutes) - {0, average.get("mins")}:
                raise RuntimeDenied("Official avgPrice window does not match the active filter")
            values[int(average["mins"])] = decimal_text(average["price"])
            asof = min(asof, average["closeTime"] * 1000)
        return values, asof


def conservative_fee_bps(body: dict, symbol: str, side: str) -> str:
    if not isinstance(body, dict) or body.get("symbol") != symbol or side not in {"BUY", "SELL"}:
        raise RuntimeDenied("Account commission identity invalid")
    supplement = "buyer" if side == "BUY" else "seller"
    total = Decimal(0)
    for category in ("standardCommission", "specialCommission", "taxCommission"):
        rates = body[category]
        # Discount is deliberately not credited; BNB depletion must not change risk.
        total += max(exact(rates["maker"]), exact(rates["taker"])) + exact(rates[supplement])
    return format(total * 10_000, "f")


class TestnetMarketFeed:
    """Bounded genuine Testnet WS quote/closed-minute buffers, no persisted raw ticks."""

    def __init__(self):
        self.quotes: dict[str, dict] = {}
        self.bars: dict[str, dict] = {}
        self.connected = False
        self.error: str | None = None

    def snapshot(self) -> dict:
        return {
            "quotes": {key: dict(value) for key, value in self.quotes.items()},
            "bars": {key: dict(value) for key, value in self.bars.items()},
            "healthy": self.connected and self.error is None,
            "source": "testnet_websocket",
        }

    async def run(self, stop: asyncio.Event) -> None:
        streams = "/".join(
            f"{symbol.lower()}@{channel}"
            for symbol in SYMBOLS
            for channel in ("bookTicker", "kline_1m")
        )
        url = "wss://stream.testnet.binance.vision/stream?streams=" + streams
        delay = 1
        while not stop.is_set():
            try:
                async with websockets.connect(
                    url, ping_interval=20, ping_timeout=20, max_queue=16, max_size=65536
                ) as socket:
                    self.connected, self.error, delay = True, None, 1
                    opened = time.monotonic()
                    wall, mono = utc_now_us(), time.monotonic()
                    while not stop.is_set() and time.monotonic() - opened < 23 * 3600 + 50 * 60:
                        raw = await asyncio.wait_for(socket.recv(), timeout=30)
                        now, new_mono = utc_now_us(), time.monotonic()
                        if abs((now - wall) / 1_000_000 - (new_mono - mono)) > 1:
                            raise RuntimeDenied("Market-feed local wall clock jumped")
                        wall, mono = now, new_mono
                        body = json.loads(raw)["data"]
                        if "k" in body and body["k"].get("x") is True:
                            kline = body["k"]
                            self.bars[body["s"]] = {
                                "open_us": kline["t"] * 1000,
                                "close_us": (kline["T"] + 1) * 1000,
                                "quote_volume": kline["q"],
                                "received_us": now,
                            }
                        elif "b" in body and "a" in body:
                            symbol = body["s"]
                            if body["u"] > self.quotes.get(symbol, {}).get("update_id", -1):
                                self.quotes[symbol] = {
                                    "bid": body["b"],
                                    "ask": body["a"],
                                    "update_id": body["u"],
                                    "received_us": now,
                                    "source": "testnet_websocket",
                                }
            except asyncio.CancelledError:
                raise
            except Exception as error:
                self.error = type(error).__name__
            finally:
                self.connected = False
                self.quotes.clear()
            if not stop.is_set():
                try:
                    await asyncio.wait_for(stop.wait(), timeout=delay)
                except TimeoutError:
                    pass
                delay = min(30, delay * 2)


class CandidateBridge:
    """Only read an admitted frozen candidate's auditable decisions; no fallback signal."""

    def __init__(self, bundle: EvidenceBundle, verified: dict):
        self.bundle, self.model_sha = bundle, verified["model_sha256"]
        self.paper_db, self.collector_db = _native(bundle.paper_db), _native(bundle.collector_db)

    def latest(self, now_us: int) -> dict | None:
        snapshot = read_forward_evidence(self.paper_db, self.bundle.version)
        decisions = [
            row
            for row in snapshot["records"]
            if row["version"] == self.bundle.version
            and row["kind"] == "decision"
            and row["payload"].get("scenario") == "candidate"
        ]
        if not decisions:
            return None
        record = decisions[-1]
        body = record["payload"]
        if body.get("model_sha256") != self.model_sha:
            raise RuntimeDenied("Decision model differs from the frozen admitted model")
        if not record["received_us"] <= now_us <= record["received_us"] + 300_000_000:
            return None
        if body["bar_end_ms"] * 1000 > record["received_us"] or body.get("state") != "READY":
            return None
        weights = body["target_weights"]
        if (
            set(weights) != set(SYMBOLS)
            or any(not 0 <= exact(str(v)) <= Decimal(".3") for v in weights.values())
            or (sum(exact(str(v)) for v in weights.values()) > Decimal(".6"))
        ):
            raise RuntimeDenied("Frozen candidate decision violates the portfolio contract")
        # Preserve the frozen next-minute rule and five-minute expiry.
        not_before = (record["received_us"] // MINUTE_US + 1) * MINUTE_US
        return {
            "record_hash": record["hash"],
            "weights": weights,
            "received_us": record["received_us"],
            "not_before_us": not_before,
            "expires_us": record["received_us"] + 300_000_000,
        }

    def covariance(self, now_us: int) -> tuple[np.ndarray, int]:
        day = now_us // DAY_US
        db = sqlite3.connect(f"file:{self.collector_db}?mode=ro", uri=True)
        try:
            rows = db.execute(
                "WITH days AS (SELECT symbol,open_ms/? AS day,COUNT(*) n,MAX(open_ms) last_open "
                "FROM closed_bars WHERE open_ms>=? AND open_ms<? AND received_ms<=? AND source=? "
                "GROUP BY symbol,day) SELECT d.symbol,d.day,d.n,b.close FROM days d "
                "JOIN closed_bars b ON b.symbol=d.symbol AND b.open_ms=d.last_open WHERE d.n=1440",
                (
                    DAY_US // 1000,
                    (day - 31) * DAY_US // 1000,
                    day * DAY_US // 1000,
                    now_us // 1000,
                    "synthetic" if self.bundle.engineering_fixture else "websocket",
                ),
            ).fetchall()
        finally:
            db.close()
        closes = {(symbol, dated): float(price) for symbol, dated, _, price in rows}
        values = [
            [closes[s, dated] / closes[s, dated - 1] - 1 for s in SYMBOLS]
            for dated in range(day - 30, day)
            if all((s, dated) in closes and (s, dated - 1) in closes for s in SYMBOLS)
        ]
        if len(values) < 20:
            raise RuntimeDenied("Fewer than 20 causal complete daily covariance observations")
        matrix = np.atleast_2d(np.cov(np.asarray(values).T, ddof=1)) * 365
        if matrix.shape != (2, 2) or not np.isfinite(matrix).all():
            raise RuntimeDenied("Causal covariance is invalid")
        return matrix, day * DAY_US


@dataclass(frozen=True)
class RuntimeConfig:
    enable_testnet: bool = False
    authorization: str = ""
    db_path: Path = STATE / "testnet-execution.sqlite3"
    poll_seconds: float = 5

    def __post_init__(self):
        _native(self.db_path)
        if not 1 <= self.poll_seconds <= 60:
            raise RuntimeDenied("Polling must stay within the bounded runtime contract")


class TestnetRuntime:
    def __init__(
        self,
        bundle: EvidenceBundle | None = None,
        *,
        config: RuntimeConfig | None = None,
        credential_loader: Callable[[], tuple[str, str]] | None = None,
        transport: httpx.MockTransport | None = None,
        market_provider: Callable | None = None,
        engineering_disk_check: Callable | None = None,
    ):
        self.bundle = bundle or EvidenceBundle()
        self.config = config or RuntimeConfig()
        self.verifier = EvidenceVerifier(self.bundle, engineering_disk_check=engineering_disk_check)
        if transport is not None and (
            not self.bundle.engineering_fixture or not isinstance(transport, httpx.MockTransport)
        ):
            raise RuntimeDenied("Injected transport requires labelled engineering fixtures")
        if self.bundle.engineering_fixture and self.config.enable_testnet:
            raise RuntimeDenied("Engineering evidence can never enable actual network")
        self.credential_loader, self.transport = credential_loader, transport
        self.market_provider = market_provider
        self.adapter: RuntimeTestnetAdapter | None = None
        self.engine: ExecutionEngine | None = None
        self._verified: dict | None = None
        self._last_verify = 0.0
        self._state = "STOP"
        self._reasons = ["NOT_VERIFIED"]
        self._last_covariance: tuple[np.ndarray, int] | None = None
        self._cycle_ok = False
        self._last_tick: tuple[float, int, bool] | None = None
        self._counters: dict = {}
        self._last_market: dict | None = None

    def status(self) -> dict:
        return {
            "module": "G47",
            "state": self._state,
            "reasons": list(self._reasons),
            "engineering": self.bundle.engineering_fixture,
            "network_enabled": bool(self.adapter and self.adapter.network),
            "real_money_authorized": False,
            "credentials_loaded": bool(self.adapter) and not self.bundle.engineering_fixture,
            "mock_keys_injected": bool(self.adapter) and self.bundle.engineering_fixture,
            "engine": self._engine_view() if self.engine else None,
            "observation": dict(self._counters),
        }

    def _engine_view(self) -> dict:
        assert self.engine
        meta, orders = self.engine._meta(), self.engine.orders()
        reasons = list(meta["freeze_reasons"])
        current = [row for row in orders if row["generation"] == meta["generation"]]
        if any(row["state"] == "UNKNOWN" for row in current):
            reasons.append("UNKNOWN_ORDER")
        if any(self.engine._debt(row) for row in current):
            reasons.append("FILL_DEBT")
        if meta["reconcile_pending"]:
            reasons.append("RECONCILIATION_PENDING")
        if self.engine._disk_failed:
            reasons.append("DISK_GUARD")
        return {"initialized": meta["initialized"], "frozen": bool(reasons),
                "freeze_reasons": reasons, "balances": meta["balances"],
                "generation": meta["generation"], "order_count": len(orders),
                "audit_scope": "verified_at_open_and_state_checked_at_each_commit"}

    def _persist_status(self) -> None:
        if self.engine:
            now, mono = utc_now_us(), time.monotonic()
            current_healthy = self._cycle_ok and self._state in {"RUNNING", "WAITING"}
            if self._last_tick:
                previous_mono, previous_wall, previous_healthy = self._last_tick
                elapsed = max(0.0, mono - previous_mono)
                self._counters["observed_seconds"] += elapsed
                drift = abs((now - previous_wall) / 1_000_000 - elapsed)
                if drift > 1:
                    self._counters["clock_incidents"] += 1
                if previous_healthy and current_healthy and elapsed <= 45 and drift <= 1:
                    self._counters["healthy_seconds"] += elapsed
            self._last_tick = (mono, now, current_healthy)
            self._counters["last_received_us"] = now
            observed = self._counters.get("observed_seconds", 0.0)
            self._counters["health_fraction"] = (
                self._counters.get("healthy_seconds", 0.0) / observed if observed else 0.0
            )
            # These counters describe a genuine current process session, never a 30d grant.
            self._counters["qualified_30d"] = False
            payload = {"state": self._state, "reasons": self._reasons, "asof_us": now,
                       "engineering": self.bundle.engineering_fixture,
                       "network_enabled": bool(self.adapter and self.adapter.network)
                       and self._state not in {"STOP", "STOPPED"},
                       "real_money_authorized": False}
            self.engine._commit("RUNTIME_HEARTBEAT", None,
                                lambda: self.engine._meta_update(
                                    runtime_status=payload, runtime_counters=self._counters),
                                {"observation": self._counters})
            day = now // DAY_US
            if self._last_market and self.engine._meta().get("runtime_last_snapshot_day") != day:
                snapshot = {
                    "utc_day": day, "received_us": now,
                    "source": "synthetic" if self.bundle.engineering_fixture else "live_testnet",
                    "balances": self._engine_view()["balances"],
                    "quotes": self._last_market.get("quotes", {}),
                    "net_return": None, "partial_session_day": True,
                    "unknown_conversion_assets": [
                        asset for asset, amount in self._engine_view()["balances"].items()
                        if asset not in {"BTC", "ETH", "USDT"} and exact(amount) != 0
                    ],
                }
                self.engine._commit("RUNTIME_DAY_SNAPSHOT", None,
                                    lambda: self.engine._meta_update(runtime_last_snapshot_day=day),
                                    snapshot)

    async def _connect(self) -> bool:
        verified = await asyncio.to_thread(self.verifier.verify)
        if verified["status"] == "STOP":
            self._state, self._reasons = "STOP", verified["reasons"]
            return False
        engineering = self.bundle.engineering_fixture
        if engineering:
            if self.transport is None or self.market_provider is None:
                self._state, self._reasons = "STOP", ["ENGINEERING_TRANSPORT_AND_MARKET_REQUIRED"]
                return False
            key, secret = "engineering-key", "engineering-secret"
        else:
            if (
                not self.config.enable_testnet
                or self.config.authorization != "spot_testnet_only"
                or not verified["live_eligible"]
                or self.credential_loader is None
            ):
                self._state, self._reasons = "STOP", ["EXPLICIT_TESTNET_AUTHORIZATION_REQUIRED"]
                return False
            # No environment/file lookup is performed; this callback occurs after all gates.
            key, secret = self.credential_loader()
            if not key or not secret:
                self._state, self._reasons = "STOP", ["EXPLICIT_TESTNET_CREDENTIALS_REQUIRED"]
                return False
        self.adapter = RuntimeTestnetAdapter(
            api_key=key, api_secret=secret, transport=self.transport, enable_network=not engineering
        )
        gate = NetworkGate(
            not engineering,
            not engineering,
            not engineering,
            not engineering,
            not engineering,
            not engineering,
            verified["evidence_hashes"],
        )
        self.engine = ExecutionEngine(
            self.adapter,
            db_path=self.config.db_path,
            gate=gate,
            disk_check=self.verifier.disk_check if engineering else None,
        )
        binding = {
            "model_sha256": verified["model_sha256"],
            "version": verified["version"],
            "engineering": engineering,
            "runtime_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "execution_sha256": hashlib.sha256(
                Path(__file__).with_name("execution.py").read_bytes()
            ).hexdigest(),
            "adapter_sha256": hashlib.sha256(
                Path(__file__).with_name("testnet.py").read_bytes()
            ).hexdigest(),
        }
        old = self.engine._meta().get("runtime_binding")
        if old is not None and old != binding:
            raise RuntimeDenied(
                "Runtime/candidate implementation changed; old account cannot resume"
            )
        if old is None:
            self.engine._commit(
                "RUNTIME_BINDING", None, lambda: self.engine._meta_update(runtime_binding=binding)
            )
        self._verified, self._last_verify = verified, time.monotonic()
        self._counters = {
            "session_started_us": utc_now_us(), "observed_seconds": 0.0,
            "healthy_seconds": 0.0, "clock_incidents": 0,
            "source": "synthetic" if engineering else "live_testnet",
            "engineering": engineering, "qualified_30d": False,
        }
        self._last_tick = (time.monotonic(), self._counters["session_started_us"], False)
        self.engine._commit("RUNTIME_SESSION", None,
                            lambda: self.engine._meta_update(runtime_counters=self._counters),
                            {**self._counters, "admission_hashes": verified["evidence_hashes"]})
        self._state, self._reasons = "RUNNING", []
        return True

    async def _cycle(self) -> None:
        assert self.adapter and self.engine and self._verified
        self._cycle_ok = False
        if time.monotonic() - self._last_verify >= 600:
            verified = await asyncio.to_thread(self.verifier.verify)
            if (
                verified["status"] == "STOP"
                or verified["model_sha256"] != self._verified["model_sha256"]
            ):
                raise RuntimeDenied("Prerequisite evidence no longer verifies")
            self._verified, self._last_verify = verified, time.monotonic()
            await self.engine.refresh_disk()
        await self.adapter.sync_time()
        source_healthy = True
        if not self.bundle.engineering_fixture:
            # Current data health is checked independently between expensive full admissions.
            source = sqlite3.connect(f"file:{_native(self.bundle.collector_db)}?mode=ro", uri=True)
            try:
                current = source.execute(
                    "SELECT state,heartbeat_ms,clock_offset_ms FROM sessions "
                    "ORDER BY id DESC LIMIT 1"
                ).fetchone()
                gaps = source.execute(
                    "SELECT COUNT(*) FROM gaps WHERE repaired_ms IS NULL"
                ).fetchone()[0]
                if (
                    not current
                    or current[0] != "RUNNING"
                    or current[1] is None
                    or not 0 <= utc_now_us() // 1000 - current[1] <= 45000
                    or current[2] is None
                    or abs(current[2]) > 5000
                    or gaps
                ):
                    source_healthy = False
            finally:
                source.close()
        known = {row["client_id"] for row in self.engine.orders()}
        opened = await self.adapter.all_open_orders()
        if any(
            not isinstance(row, dict) or row.get("clientOrderId") not in known for row in opened
        ):
            raise RuntimeDenied("Untracked external open orders require review")
        account = await self.adapter.account()
        if account.get("canTrade") is not True or account.get("accountType") != "SPOT":
            raise RuntimeDenied("Account is not a trading-enabled Spot Testnet account")
        totals = {
            row["asset"]: {"free": row["free"], "locked": row["locked"]}
            for row in account["balances"]
        }
        if len(totals) != len(account["balances"]):
            raise RuntimeDenied("Account balance assets are duplicated")
        if not self._engine_view()["initialized"]:
            self.engine.bootstrap(totals)
        else:
            await self.engine.recover()
        if not source_healthy:
            for order in self.engine.orders():
                if order["state"] in {"PREPARED", "NEW", "PARTIALLY_FILLED"}:
                    await self.engine.cancel(order["client_id"])
            self._state, self._reasons = "RECOVERING", ["MAINNET_SOURCE_UNHEALTHY_NEW_ORDERS_BLOCKED"]
            return
        # Expire confirmed live orders safely. UNKNOWN remains held and queried.
        now = utc_now_us()
        for order in self.engine.orders():
            if (
                order["state"] in {"PREPARED", "NEW", "PARTIALLY_FILLED"}
                and now - order["created_us"] > 300_000_000
            ):
                await self.engine.cancel(order["client_id"])
        if self._engine_view()["frozen"]:
            self._state, self._reasons = "RECOVERING", self._engine_view()["freeze_reasons"]
            return
        market = self.market_provider()
        self._last_market = market
        self._cycle_ok = market.get("healthy") is True and all(
            name in market.get("quotes", {})
            and 0 <= utc_now_us() - market["quotes"][name]["received_us"] <= 2_000_000
            for name in SYMBOLS
        )
        bridge = CandidateBridge(self.bundle, self._verified)
        decision = await asyncio.to_thread(bridge.latest, utc_now_us())
        if decision is None:
            self._state, self._reasons = "WAITING", ["NO_CURRENT_FROZEN_CANDIDATE_DECISION"]
            return
        if utc_now_us() < decision["not_before_us"]:
            self._state, self._reasons = "WAITING", ["NEXT_MINUTE_REQUIRED"]
            return
        info = await self.adapter.exchange_info()
        # Causal covariance excludes the current incomplete UTC day.
        day = utc_now_us() // DAY_US * DAY_US
        if self._last_covariance is None or self._last_covariance[1] != day:
            self._last_covariance = await asyncio.to_thread(bridge.covariance, utc_now_us())
        covariance, covariance_asof = self._last_covariance
        for symbol in SYMBOLS:
            intent = f"testnet:{decision['record_hash']}:{symbol}"
            if any(row["intent_key"] == intent for row in self.engine.orders()):
                continue
            relevant = await self.adapter.relevant_filters(symbol)
            if not all(
                isinstance(relevant.get(key), list)
                for key in ("exchangeFilters", "symbolFilters", "assetFilters")
            ):
                raise RuntimeDenied("Relevant account filters are incomplete")
            rule = SymbolRules.from_exchange_info(
                info,
                symbol,
                utc_now_us(),
                account_filters=tuple(
                    relevant["symbolFilters"]
                    + relevant["assetFilters"]
                    + relevant["exchangeFilters"]
                ),
            )
            fees = await self.adapter.commission(symbol)
            fee_asof = utc_now_us()
            windows = {
                int(row["avgPriceMins"])
                for row in rule.filters + rule.account_filters
                if row["filterType"] in {"PERCENT_PRICE", "PERCENT_PRICE_BY_SIDE"}
            }
            refs, ref_asof = (
                await self.adapter.references(symbol, windows) if windows else ({}, None)
            )
            market = self.market_provider()
            expected_source = (
                "engineering_mock" if self.bundle.engineering_fixture else "testnet_websocket"
            )
            if market.get("source") != expected_source:
                raise RuntimeDenied("Testnet quote feed has wrong provenance")
            if market.get("healthy") is not True or not all(
                name in market.get("quotes", {}) and name in market.get("bars", {})
                for name in SYMBOLS
            ):
                self._state, self._reasons = "WAITING", ["GENUINE_MARKET_FEED_WARMUP"]
                return
            now, minute = utc_now_us(), utc_now_us() // MINUTE_US * MINUTE_US
            quotes = market["quotes"]
            quote = quotes[symbol]
            bar = market["bars"][symbol]
            if (
                bar["open_us"] != minute - MINUTE_US
                or bar["close_us"] != minute
                or bar["received_us"] > now
                or bar["close_us"] > bar["received_us"]
            ):
                self._state, self._reasons = "WAITING", ["PREVIOUS_CLOSED_TESTNET_MINUTE_REQUIRED"]
                return
            balances = {key: exact(value) for key, value in self._engine_view()["balances"].items()}
            marks = {}
            for asset, ticker in (("BTC", "BTCUSDT"), ("ETH", "ETHUSDT")):
                entry = quotes[ticker]
                if (
                    entry.get("source") != expected_source
                    or not 0 <= now - entry["received_us"] <= 2_000_000
                ):
                    self._state, self._reasons = "WAITING", ["FRESH_TESTNET_QUOTES_REQUIRED"]
                    return
                marks[asset] = exact(entry["bid"])
            nav = balances.get("USDT", Decimal(0)) + sum(
                balances.get(asset, Decimal(0)) * mark for asset, mark in marks.items()
            )
            target_quantity = exact(str(decision["weights"][symbol])) * nav / marks[rule.base_asset]
            delta = target_quantity - balances.get(rule.base_asset, Decimal(0))
            side = "BUY" if delta > 0 else "SELL"
            fee_bps = conservative_fee_bps(fees, symbol, side)
            price_raw = exact(quote["ask"] if side == "BUY" else quote["bid"])
            price_filter = next(row for row in rule.filters if row["filterType"] == "PRICE_FILTER")
            tick = exact(price_filter["tickSize"])
            price = (
                (price_raw / tick).to_integral_value(
                    rounding=ROUND_UP if side == "BUY" else ROUND_DOWN
                )
                * tick
                if tick
                else price_raw
            )
            lot = next(row for row in rule.filters if row["filterType"] == "LOT_SIZE")
            step = exact(lot["stepSize"])
            # Explicit default permission remains100 USDT/order; skip untradeable dust.
            capped = min(abs(delta), Decimal("100") / price)
            quantity = (
                (capped / step).to_integral_value(rounding=ROUND_DOWN) * step if step else capped
            )
            if quantity <= 0 or quantity * price < 10:
                continue
            projected = np.array(
                [float(balances.get(asset, Decimal(0))) for asset in ("BTC", "ETH")]
            )
            for order in self.engine.orders():
                if order["side"] == "BUY" and order["state"] not in {
                    "FILLED",
                    "CANCELED",
                    "REJECTED",
                    "EXPIRED",
                    "RESET_INVALIDATED",
                }:
                    projected[0 if order["base_asset"] == "BTC" else 1] += float(
                        exact(order["quantity"]) - exact(order["executed_qty"])
                    )
            if side == "BUY":
                projected[0 if rule.base_asset == "BTC" else 1] += float(quantity)
            weights = projected * np.array([float(marks["BTC"]), float(marks["ETH"])]) / float(nav)
            vol = math.sqrt(max(0, float(weights @ covariance @ weights)))
            context = RiskContext(
                now,
                str(quote["bid"]),
                str(quote["ask"]),
                quote["received_us"],
                quote["update_id"],
                True,
                True,
                reference_prices=refs,
                reference_asof_us=ref_asof,
                venue_open_orders=len(opened),
                venue_symbol_open_orders=sum(row["symbol"] == symbol for row in opened),
                asset_marks={key: str(value) for key, value in marks.items()},
                marks_asof_us=min(row["received_us"] for row in quotes.values()),
                estimated_annual_vol=str(vol),
                volatility_asof_us=minute,
                previous_closed_quote_volume=bar["quote_volume"],
                previous_minute_open_us=bar["open_us"],
                conservative_fee_bps=fee_bps,
                fee_asof_us=fee_asof,
                fee_source="synthetic_runtime_commission"
                if self.bundle.engineering_fixture
                else "venue_standard_special_tax_commission",
            )
            self.engine._guard()
            client_id = self.engine.prepare(
                intent,
                symbol=symbol,
                side=side,
                quantity=str(quantity),
                price=str(price),
                rules=rule,
                context=context,
            )
            self.engine._commit(
                "CANDIDATE_BRIDGE",
                client_id,
                lambda: None,
                {
                    "decision_hash": decision["record_hash"],
                    "candidate_model": bridge.model_sha,
                    "fee_sha256": canonical_hash(fees),
                    "filter_sha256": canonical_hash(relevant),
                    "covariance_source_cutoff_us": covariance_asof,
                    "volatility_computed_asof_us": minute,
                },
            )
            await self.engine.submit(client_id, rules=rule, context=context)
            await self.engine.recover()
            if self._engine_view()["frozen"]:
                break
        self._state, self._reasons = (
            ("RECOVERING", self._engine_view()["freeze_reasons"])
            if self._engine_view()["frozen"]
            else ("RUNNING", [])
        )

    async def run(
        self, *, run_seconds: float | None = None, stop_event: asyncio.Event | None = None
    ) -> dict:
        if run_seconds is not None and run_seconds < 0:
            raise ValueError("run_seconds must be nonnegative")
        stop = stop_event or asyncio.Event()
        feed_task = None
        started = time.monotonic()
        try:
            if self.engine is None and not await self._connect():
                return self.status()
            if self.market_provider is None:
                feed = TestnetMarketFeed()
                self.market_provider = feed.snapshot
                feed_task = asyncio.create_task(feed.run(stop))
            while not stop.is_set():
                try:
                    await self._cycle()
                except RateLimited:
                    self._state, self._reasons = "COOLDOWN", ["RATE_LIMITED"]
                except (
                    RuntimeDenied,
                    ProtocolRejected,
                    ExecutionError,
                    KeyError,
                    ValueError,
                ) as error:
                    self._state, self._reasons = "STOP", [type(error).__name__]
                    if self.engine:
                        self.engine._commit(
                            "RUNTIME_STOP", None, lambda: None, {"reason": type(error).__name__}
                        )
                    break
                except Exception as error:
                    self._state, self._reasons = "RECOVERING", [type(error).__name__]
                self._persist_status()
                if run_seconds is not None and time.monotonic() - started >= run_seconds:
                    break
                delay = self.config.poll_seconds
                if self.adapter and self.adapter.cooldown_until_ms:
                    delay = max(
                        delay,
                        min(60, (self.adapter.cooldown_until_ms - self.adapter._clock()) / 1000),
                    )
                try:
                    await asyncio.wait_for(stop.wait(), timeout=delay)
                except TimeoutError:
                    pass
            return self.status()
        except Exception as error:
            self._state, self._reasons = "STOP", [type(error).__name__]
            return self.status()
        finally:
            if feed_task:
                stop.set()
                feed_task.cancel()
                await asyncio.gather(feed_task, return_exceptions=True)

    async def resume(self, **kwargs: Any) -> dict:
        await self.close()
        self._last_covariance = None
        return await self.run(**kwargs)

    async def close(self) -> None:
        if self.engine:
            self._state, self._reasons = "STOPPED", []
            try:
                self._persist_status()
            except ExecutionError:
                pass  # A failed disk guard must not cause additional unsafe writes.
            self.engine.close()
            self.engine = None
        if self.adapter:
            await self.adapter.close()
            self.adapter = None


def read_runtime_status(db_path: Path = STATE / "testnet-execution.sqlite3") -> dict:
    """Read and audit native persistent state without credentials, HTTP, or a writer."""
    path = _native(db_path)
    if not path.exists():
        return {"state": "NOT_STARTED", "network_enabled": False, "real_money_authorized": False}
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN")  # Audit and metadata must use one consistent read-only snapshot.
        # The frozen verifier only accesses .db; no engine constructor or lock is invoked.
        audit_reader = object.__new__(ExecutionEngine)
        audit_reader.db = db
        head = audit_reader.verify_audit()
        meta = {row["key"]: json.loads(row["value"]) for row in db.execute("SELECT * FROM meta")}
        recorded = meta.get("runtime_status", {"state": "NO_RUNTIME_HEARTBEAT"})
        result = {**recorded, "database": str(path), "audit_head": head,
                  "balances": meta["balances"], "generation": meta["generation"],
                  "binding": meta.get("runtime_binding"), "read_only": True,
                  "observation": meta.get("runtime_counters"),
                  "real_money_authorized": False}
        if result["state"] not in {"STOPPED", "STOP"} and (
            not 0 <= utc_now_us() - result.get("asof_us", 0) <= 45_000_000
        ):
            result.update(state="STALE", network_enabled=False)
        return result
    finally:
        db.close()
