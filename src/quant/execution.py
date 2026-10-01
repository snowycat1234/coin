"""Durable, default-denied Spot Testnet execution. No transport or keys live here.

SQLite commits intent and dispatch state before awaiting an adapter. An uncertain
write is only resolved by observation; it is never submitted again.
"""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import os
import shutil
import sqlite3
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Protocol

from quant import disk
from quant.paths import ROOT, STATE, VHD, utc_now_us

ZERO = Decimal("0")
TERMINAL = {"FILLED", "CANCELED", "REJECTED", "EXPIRED", "RESET_INVALIDATED"}
ACTIVE = {"SUBMITTING", "NEW", "PARTIALLY_FILLED", "CANCEL_PENDING", "UNKNOWN"}
VENUE_STATES = {"NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"}


class ExecutionError(RuntimeError):
    pass


class RiskViolation(ExecutionError):
    pass


class GateDenied(ExecutionError):
    pass


class ExecutionFrozen(ExecutionError):
    pass


class EvidenceError(ExecutionError):
    pass


class AuditError(ExecutionError):
    pass


class EvidencePending(EvidenceError):
    """A later trade snapshot can precede the order query's eventual consistency."""


class OrderAdapter(Protocol):
    environment: str
    network: bool

    async def submit(self, order: dict) -> dict: ...
    async def query(self, symbol: str, client_order_id: str) -> dict | None: ...
    async def cancel(self, symbol: str, client_order_id: str) -> dict: ...
    async def trades(self, symbol: str, exchange_order_id: int) -> list[dict]: ...
    async def balances(self) -> dict: ...


@dataclass(frozen=True)
class NetworkGate:
    """Outer orchestrator must independently validate real evidence and authorize.

    These attestations are a second denial layer, not evidence verification. Never
    construct an enabled gate from synthetic acceptance results.
    """

    allow_testnet: bool = False
    authorized: bool = False
    real_72h_passed: bool = False
    real_180d_passed: bool = False
    candidate_passed: bool = False
    resources_passed: bool = False
    evidence_hashes: Mapping[str, str] = field(default_factory=dict)

    def check(self, adapter: OrderAdapter) -> None:
        if adapter.environment != "spot_testnet":
            raise GateDenied("Only Spot Testnet is implemented; mainnet execution is denied")
        if not adapter.network:
            return
        flags = (
            self.allow_testnet,
            self.authorized,
            self.real_72h_passed,
            self.real_180d_passed,
            self.candidate_passed,
            self.resources_passed,
        )
        hashes = [
            self.evidence_hashes.get(key, "")
            for key in ("candidate", "real_72h", "real_180d", "resources")
        ]
        if not all(flags) or not all(
            len(value) == 64 and all(c in "0123456789abcdef" for c in value) for value in hashes
        ):
            raise GateDenied(
                "Real prerequisite evidence and explicit Testnet authorization missing"
            )


def _d(value: Any, *, positive: bool = False) -> Decimal:
    if isinstance(value, (float, bool)):
        raise EvidenceError("Money and quantities require exact decimal strings")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as error:
        raise EvidenceError("Invalid decimal") from error
    if not number.is_finite() or number < 0 or (positive and number == 0):
        raise EvidenceError("Invalid nonnegative decimal")
    return number


def _s(value: Decimal) -> str:
    return format(value, "f")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


@dataclass(frozen=True)
class SymbolRules:
    symbol: str
    base_asset: str
    quote_asset: str
    filters: tuple[dict, ...]
    asof_us: int
    status: str = "TRADING"
    exchange_filters: tuple[dict, ...] = ()
    account_filters: tuple[dict, ...] = ()

    @classmethod
    def from_exchange_info(
        cls, info: dict, symbol: str, asof_us: int, account_filters: tuple[dict, ...] = ()
    ) -> SymbolRules:
        rows = [row for row in info["symbols"] if row["symbol"] == symbol]
        if len(rows) != 1:
            raise EvidenceError("Symbol metadata missing or duplicated")
        row = rows[0]
        return cls(
            symbol,
            row["baseAsset"],
            row["quoteAsset"],
            tuple(row["filters"]),
            asof_us,
            row["status"],
            tuple(info.get("exchangeFilters", ())),
            account_filters,
        )


@dataclass(frozen=True)
class RiskContext:
    now_us: int
    bid: str
    ask: str
    quote_received_us: int
    quote_update_id: int
    healthy: bool
    disk_ok: bool
    # Official filter reference, keyed by avgPriceMins, never an invented mid.
    reference_prices: Mapping[int, str] = field(default_factory=dict)
    reference_asof_us: int | None = None
    # Account-wide venue counts are needed for caps, including external orders.
    venue_open_orders: int | None = None
    venue_symbol_open_orders: int | None = None
    asset_marks: Mapping[str, str] = field(default_factory=dict)
    marks_asof_us: int | None = None
    estimated_annual_vol: str | None = None
    volatility_asof_us: int | None = None
    previous_closed_quote_volume: str | None = None
    previous_minute_open_us: int | None = None
    # Explicitly synthetic engineering exercises can omit portfolio estimators.
    # Any adapter with real network access must use all checks.
    portfolio_checks: bool = True
    conservative_fee_bps: str | None = None
    fee_asof_us: int | None = None
    fee_source: str | None = None


@dataclass(frozen=True)
class RiskLimits:
    max_order_notional: str = "100"
    max_reserved_quote: str = "500"
    max_base_position_quote: str = "1000"
    max_quote_age_us: int = 2_000_000
    max_rules_age_us: int = 3_600_000_000
    max_reference_age_us: int = 5_000_000
    max_balance_age_us: int = 60_000_000
    max_fee_age_us: int = 60_000_000
    max_volatility_age_us: int = 3_600_000_000
    single_asset_weight: str = "0.30"
    gross_weight: str = "0.60"
    estimated_annual_vol_cap: str = "0.10"
    minute_volume_fraction: str = "0.001"
    max_spread_bps: str = "20"
    max_price_deviation_bps: str = "100"
    fee_reserve_bps: str = "20"
    market_slippage_bps: str = "20"
    max_open_orders: int = 8
    balance_tolerance: str = "0.00000001"

    def __post_init__(self) -> None:
        for value, ceiling in (
            (self.single_asset_weight, "0.30"),
            (self.gross_weight, "0.60"),
            (self.estimated_annual_vol_cap, "0.10"),
            (self.minute_volume_fraction, "0.001"),
        ):
            if _d(value, positive=True) > Decimal(ceiling):
                raise RiskViolation("Frozen portfolio risk ceilings cannot be relaxed")


class ExecutionEngine:
    """One process, one async mutation at a time, append-only audit, exact balances."""

    def __init__(
        self,
        adapter: OrderAdapter,
        *,
        db_path: Path | None = None,
        gate: NetworkGate | None = None,
        limits: RiskLimits | None = None,
        disk_check: Callable[..., dict] | None = None,
    ):
        if os.environ.get("WSL_DISTRO_NAME") != "hpc_linux":
            raise ExecutionError("Execution requires the D-hosted hpc_linux WSL environment")
        self.adapter = adapter
        self.gate = gate or NetworkGate()
        self.limits = limits or RiskLimits()
        self.db_path = Path(db_path or STATE / "execution.sqlite3").resolve()
        if not self.db_path.is_relative_to(STATE.resolve()):
            raise ExecutionError("Execution SQLite must be in native D-hosted STATE")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._disk_check = disk_check
        self._disk_failed = False
        self._async_lock = asyncio.Lock()
        self._closed = False
        self._lock_file = self.db_path.with_suffix(".writer.lock").open("a+")
        try:
            fcntl.flock(self._lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self._lock_file.close()
            raise ExecutionError("Execution database already has a writer") from error
        try:
            self._ledger = (disk_check or disk.check)(reserve=50_000_000)
            if self._ledger.get("status") not in {"OK", "WARNING"}:
                raise ExecutionFrozen("Disk ledger did not report an admissible state")
            self._ledger_mono = time.monotonic()
            self._vhd_bytes = VHD.stat().st_size if VHD.exists() else 0
            self._db_bytes = self._storage_bytes()
            self.db = sqlite3.connect(self.db_path, timeout=5, isolation_level=None)
            self.db.row_factory = sqlite3.Row
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=FULL")
            self.db.execute("PRAGMA busy_timeout=5000")
            self.db.executescript("""
                CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS orders(
                    client_id TEXT PRIMARY KEY, intent_key TEXT UNIQUE NOT NULL,
                    state TEXT NOT NULL, generation INTEGER NOT NULL, data TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS fills(
                    generation INTEGER NOT NULL, symbol TEXT NOT NULL, trade_id TEXT NOT NULL,
                    client_id TEXT NOT NULL, data TEXT NOT NULL,
                    PRIMARY KEY(generation,symbol,trade_id));
                CREATE TABLE IF NOT EXISTS audit(
                    seq INTEGER PRIMARY KEY, received_us INTEGER NOT NULL,
                    event TEXT NOT NULL, client_id TEXT, payload TEXT NOT NULL,
                    state_hash TEXT NOT NULL, previous_hash TEXT NOT NULL, hash TEXT NOT NULL);
                CREATE TRIGGER IF NOT EXISTS audit_no_update BEFORE UPDATE ON audit
                    BEGIN SELECT RAISE(ABORT,'append-only audit'); END;
                CREATE TRIGGER IF NOT EXISTS audit_no_delete BEFORE DELETE ON audit
                    BEGIN SELECT RAISE(ABORT,'append-only audit'); END;
            """)
            self.verify_audit()
            if not self.db.execute("SELECT 1 FROM meta").fetchone():
                self._commit(
                    "INITIALIZE",
                    None,
                    lambda: self._meta_set(
                        {
                            "generation": 0,
                            "balances": {},
                            "initialized": False,
                            "last_actual_free": {},
                            "freeze_reasons": [],
                            "reconcile_pending": True,
                            "last_reconcile_us": None,
                        }
                    ),
                )
            else:

                def restart() -> None:
                    for order in self.orders():
                        if order["state"] in ACTIVE:
                            order["prior_state"] = order["state"]
                            order["state"] = "UNKNOWN"
                            order["pending_action"] = "restart_query"
                            self._save_order(order)
                    self._meta_update(reconcile_pending=True)

                self._commit("PROCESS_RESTART", None, restart)
        except BaseException:
            if hasattr(self, "db"):
                self.db.close()
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            self._lock_file.close()
            raise

    def _storage_bytes(self) -> int:
        return sum(
            path.stat().st_size
            for path in (
                self.db_path,
                Path(str(self.db_path) + "-wal"),
                Path(str(self.db_path) + "-shm"),
            )
            if path.exists()
        )

    def _guard(self) -> None:
        if self._closed or self._disk_failed:
            raise ExecutionFrozen("Execution is closed or disk guard has failed")
        try:
            if self._disk_check:
                self._ledger = self._disk_check(reserve=1_000_000)
                if self._ledger.get("status") not in {"OK", "WARNING"}:
                    raise ExecutionFrozen("Disk ledger is not admissible")
            else:
                growth = max(0, self._storage_bytes() - self._db_bytes)
                vhd_growth = max(0, VHD.stat().st_size - self._vhd_bytes) if VHD.exists() else 0
                if growth > 45_000_000:
                    raise ExecutionFrozen("Execution disk reservation exhausted; refresh required")
                # Global VHD growth includes other research jobs; it is charged
                # to the global ledger, never to this writer's local allowance.
                free = shutil.disk_usage(ROOT).free
                disk.enforce(self._ledger["total_bytes"] + vhd_growth, 1_000_000, free)
                # Refresh is explicit and async; never block the socket with a directory walk.
                if time.monotonic() - self._ledger_mono > 900:
                    raise ExecutionFrozen("Full disk ledger expired; call refresh_disk()")
        except Exception as error:
            self._disk_failed = True
            raise ExecutionFrozen("Disk guard failed; execution frozen") from error

    async def refresh_disk(self) -> None:
        try:
            result = await asyncio.to_thread(self._disk_check or disk.check, reserve=50_000_000)
            if result.get("status") not in {"OK", "WARNING"}:
                raise ExecutionFrozen("Disk ledger is not admissible")
        except Exception as error:
            self._disk_failed = True
            raise ExecutionFrozen("Disk ledger refresh failed") from error
        self._ledger = result
        self._ledger_mono = time.monotonic()
        self._vhd_bytes = VHD.stat().st_size if VHD.exists() else 0
        self._db_bytes = self._storage_bytes()
        # An actual guard violation remains frozen until a new validated process.

    def _meta(self) -> dict:
        return {
            row["key"]: json.loads(row["value"])
            for row in self.db.execute("SELECT key,value FROM meta")
        }

    def _meta_set(self, values: dict) -> None:
        self.db.executemany(
            "INSERT OR REPLACE INTO meta VALUES (?,?)",
            [(key, _json(value)) for key, value in values.items()],
        )

    def _meta_update(self, **values: Any) -> None:
        self._meta_set(values)

    def _reason(self, reason: str) -> None:
        reasons = self._meta()["freeze_reasons"]
        if reason not in reasons:
            self._meta_update(freeze_reasons=reasons + [reason])

    def _state_hash(self) -> str:
        digest = hashlib.sha256()
        for table, columns, sort in (
            ("meta", "key,value", "key"),
            ("orders", "client_id,intent_key,state,generation,data", "client_id"),
            ("fills", "generation,symbol,trade_id,client_id,data", "generation,symbol,trade_id"),
        ):
            digest.update(table.encode())
            for row in self.db.execute(f"SELECT {columns} FROM {table} ORDER BY {sort}"):
                digest.update(_json(list(row)).encode())
                digest.update(b"\n")
        return digest.hexdigest()

    @staticmethod
    def _audit_hash(
        seq: int,
        received_us: int,
        event: str,
        client_id: str | None,
        payload: str,
        state_hash: str,
        previous_hash: str,
    ) -> str:
        return hashlib.sha256(
            _json([seq, received_us, event, client_id, payload, state_hash, previous_hash]).encode()
        ).hexdigest()

    def _commit(
        self,
        event: str,
        client_id: str | None,
        mutate: Callable[[], Any],
        payload: dict | None = None,
    ) -> Any:
        self._guard()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            prior = self.db.execute(
                "SELECT state_hash FROM audit ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            if prior and prior["state_hash"] != self._state_hash():
                raise AuditError("Unaudited materialized state modification before commit")
            result = mutate()
            head = self.db.execute(
                "SELECT seq,hash FROM audit ORDER BY seq DESC LIMIT 1"
            ).fetchone()
            seq, previous = (head["seq"] + 1, head["hash"]) if head else (1, "0" * 64)
            received, encoded, state_hash = utc_now_us(), _json(payload or {}), self._state_hash()
            digest = self._audit_hash(
                seq, received, event, client_id, encoded, state_hash, previous
            )
            self.db.execute(
                "INSERT INTO audit VALUES (?,?,?,?,?,?,?,?)",
                (seq, received, event, client_id, encoded, state_hash, previous, digest),
            )
            self.db.execute("COMMIT")
            return result
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def verify_audit(self) -> str:
        previous, seq, last_state = "0" * 64, 0, None
        for row in self.db.execute("SELECT * FROM audit ORDER BY seq"):
            seq += 1
            expected = self._audit_hash(
                row["seq"],
                row["received_us"],
                row["event"],
                row["client_id"],
                row["payload"],
                row["state_hash"],
                previous,
            )
            if row["seq"] != seq or row["previous_hash"] != previous or row["hash"] != expected:
                raise AuditError("Audit hash chain invalid")
            previous, last_state = row["hash"], row["state_hash"]
        if last_state is not None and last_state != self._state_hash():
            raise AuditError("Materialized order/balance/fill state differs from audit head")
        if last_state is None and self.db.execute("SELECT 1 FROM meta").fetchone():
            raise AuditError("State exists without audit")
        return previous

    def order(self, client_id: str) -> dict:
        row = self.db.execute("SELECT data FROM orders WHERE client_id=?", (client_id,)).fetchone()
        if not row:
            raise ExecutionError("Unknown local order")
        return json.loads(row["data"])

    def orders(self) -> list[dict]:
        return [
            json.loads(row["data"])
            for row in self.db.execute("SELECT data FROM orders ORDER BY client_id")
        ]

    def _save_order(self, order: dict) -> None:
        self.db.execute(
            "INSERT OR REPLACE INTO orders VALUES (?,?,?,?,?)",
            (
                order["client_id"],
                order["intent_key"],
                order["state"],
                order["generation"],
                _json(order),
            ),
        )

    @staticmethod
    def _balances(snapshot: dict) -> dict[str, str]:
        if not isinstance(snapshot, dict):
            raise EvidenceError("Balances require an asset map with free and locked")
        result = {}
        for asset, value in snapshot.items():
            if not isinstance(asset, str) or not asset.isalnum() or not isinstance(value, dict):
                raise EvidenceError("Invalid asset balance")
            result[asset] = _s(_d(value["free"]) + _d(value["locked"]))
        return result

    def bootstrap(self, balances: dict) -> None:
        totals = self._balances(balances)
        if self._meta()["initialized"] or self.orders():
            raise ExecutionError("Balances cannot overwrite an existing ledger")
        self._commit(
            "BOOTSTRAP_BALANCES",
            None,
            lambda: self._meta_update(
                balances=totals,
                initialized=True,
                reconcile_pending=False,
                last_actual_free={key: _s(_d(value["free"])) for key, value in balances.items()},
                last_reconcile_us=utc_now_us(),
            ),
            {"totals": totals},
        )

    def _debt(self, order: dict) -> bool:
        return _d(order["executed_qty"]) != _d(order["accounted_qty"]) or _d(
            order["executed_quote"]
        ) != _d(order["accounted_quote"])

    def _ready(self) -> None:
        meta = self._meta()
        if not meta["initialized"]:
            raise ExecutionFrozen("Initial balances missing")
        if (
            meta["freeze_reasons"]
            or meta["reconcile_pending"]
            or any(
                row["state"] in {"UNKNOWN", "SUBMITTING", "CANCEL_PENDING"} or self._debt(row)
                for row in self.orders()
                if row["generation"] == meta["generation"]
            )
        ):
            raise ExecutionFrozen("Uncertain orders, fill debt, or reconciliation require recovery")

    def _reserved(self, *, exclude: str | None = None) -> dict[str, Decimal]:
        result: dict[str, Decimal] = {}
        for order in self.orders():
            if order["client_id"] == exclude or order["state"] in TERMINAL:
                continue
            asset = order["reserve_asset"]
            result[asset] = result.get(asset, ZERO) + _d(order["reserve_remaining"])
        return result

    def _reference(self, context: RiskContext, minutes: int) -> Decimal:
        if (
            context.reference_asof_us is None
            or context.now_us < context.reference_asof_us
            or context.now_us - context.reference_asof_us > self.limits.max_reference_age_us
            or minutes not in context.reference_prices
        ):
            raise RiskViolation("Fresh official filter reference price missing")
        return _d(context.reference_prices[minutes], positive=True)

    def _risk(
        self, order: dict, rules: SymbolRules, context: RiskContext, *, exclude: str | None = None
    ) -> tuple[str, str]:
        limits = self.limits
        meta = self._meta()
        if (
            context.conservative_fee_bps is None
            or context.fee_asof_us is None
            or not context.fee_source
            or context.fee_asof_us > context.now_us
            or context.now_us - context.fee_asof_us > limits.max_fee_age_us
        ):
            raise RiskViolation("Fresh conservative total account fee evidence missing")
        if self.adapter.network and context.fee_source.startswith("synthetic"):
            raise RiskViolation("Synthetic fee evidence cannot authorize real network access")
        if _d(context.conservative_fee_bps) > _d(limits.fee_reserve_bps):
            raise RiskViolation("Conservative actual fee exceeds the risk reservation rate")
        if (
            meta["last_reconcile_us"] is None
            or context.now_us - meta["last_reconcile_us"] > limits.max_balance_age_us
        ):
            raise RiskViolation("Fresh reconciled account balances missing")
        if rules.symbol != order["symbol"] or rules.status != "TRADING":
            raise RiskViolation("Symbol unavailable or metadata mismatched")
        if (rules.base_asset, rules.quote_asset) != (order["base_asset"], order["quote_asset"]):
            raise RiskViolation("Symbol asset metadata changed")
        if rules.symbol not in {"BTCUSDT", "ETHUSDT"}:
            raise RiskViolation("Symbol outside initial universe")
        if (rules.base_asset, rules.quote_asset) != (rules.symbol[:-4], "USDT"):
            raise RiskViolation("Unexpected assets for the frozen symbol universe")
        if (
            context.now_us > utc_now_us() + 1_000_000
            or abs(context.now_us - utc_now_us()) > 5_000_000
        ):
            raise RiskViolation("Risk context clock stale or implausible")
        if (
            not context.healthy
            or not context.disk_ok
            or not isinstance(context.quote_update_id, int)
            or isinstance(context.quote_update_id, bool)
            or context.quote_update_id < 0
            or context.quote_received_us > context.now_us
            or context.now_us - context.quote_received_us > limits.max_quote_age_us
        ):
            raise RiskViolation("Collector health or genuine fresh quote missing")
        if (
            rules.asof_us > context.now_us
            or context.now_us - rules.asof_us > limits.max_rules_age_us
        ):
            raise RiskViolation("Exchange filters expired")
        bid, ask, qty = (
            _d(context.bid, positive=True),
            _d(context.ask, positive=True),
            _d(order["quantity"], positive=True),
        )
        if bid > ask or (ask - bid) / bid * 10_000 > _d(limits.max_spread_bps):
            raise RiskViolation("Invalid quote or excessive spread")
        order_type, side = order["type"], order["side"]
        if order_type not in {"LIMIT", "MARKET"} or side not in {"BUY", "SELL"}:
            raise RiskViolation("Only quantity-based LIMIT GTC and MARKET are implemented")
        if order_type == "MARKET" and order["price"] is not None:
            raise RiskViolation("MARKET orders cannot carry an unused limit price")
        px = (
            _d(order["price"], positive=True)
            if order_type == "LIMIT"
            else (ask * (1 + _d(limits.market_slippage_bps) / 10_000) if side == "BUY" else bid)
        )
        if order_type == "LIMIT" and abs(px / (ask if side == "BUY" else bid) - 1) * 10_000 > _d(
            limits.max_price_deviation_bps
        ):
            raise RiskViolation("Limit price too far from genuine quote")
        filters = rules.filters + rules.exchange_filters + rules.account_filters
        if not any(row.get("filterType") == "LOT_SIZE" for row in rules.filters):
            raise RiskViolation("Required LOT_SIZE filter missing")
        if order_type == "LIMIT" and not any(
            row.get("filterType") == "PRICE_FILTER" for row in rules.filters
        ):
            raise RiskViolation("Required PRICE_FILTER missing")
        reserved = self._reserved(exclude=exclude)
        balances = {key: _d(value) for key, value in self._meta()["balances"].items()}
        open_local = sum(
            row["state"] not in TERMINAL and row["client_id"] != exclude for row in self.orders()
        )
        if open_local >= limits.max_open_orders:
            raise RiskViolation("Local open order cap reached")
        for item in filters:
            kind = item.get("filterType")
            if kind in {"PRICE_FILTER", "LOT_SIZE", "MARKET_LOT_SIZE"}:
                if kind == "MARKET_LOT_SIZE" and order_type != "MARKET":
                    continue
                if kind == "PRICE_FILTER" and order_type != "LIMIT":
                    continue
                val = px if kind == "PRICE_FILTER" else qty
                low = _d(item["minPrice" if kind == "PRICE_FILTER" else "minQty"])
                high = _d(item["maxPrice" if kind == "PRICE_FILTER" else "maxQty"])
                step = _d(item["tickSize" if kind == "PRICE_FILTER" else "stepSize"])
                if (low and val < low) or (high and val > high) or (step and val % step != 0):
                    raise RiskViolation(f"{kind} violated")
            elif kind in {"MIN_NOTIONAL", "NOTIONAL"}:
                if order_type == "MARKET":
                    apply_min = item.get("applyToMarket", item.get("applyMinToMarket", False))
                    apply_max = item.get("applyMaxToMarket", False)
                    if not apply_min and not apply_max:
                        continue
                    notional = qty * self._reference(context, int(item["avgPriceMins"]))
                else:
                    notional, apply_min, apply_max = qty * px, True, kind == "NOTIONAL"
                if apply_min and notional < _d(item["minNotional"]):
                    raise RiskViolation("Minimum notional violated")
                if apply_max and _d(item["maxNotional"]) and notional > _d(item["maxNotional"]):
                    raise RiskViolation("Maximum notional violated")
            elif kind in {"PERCENT_PRICE", "PERCENT_PRICE_BY_SIDE"}:
                if order_type != "LIMIT":
                    continue
                ref = self._reference(context, int(item["avgPriceMins"]))
                prefix = "bid" if side == "BUY" else "ask"
                low = _d(
                    item[prefix + "MultiplierDown"]
                    if kind.endswith("BY_SIDE")
                    else item["multiplierDown"]
                )
                high = _d(
                    item[prefix + "MultiplierUp"]
                    if kind.endswith("BY_SIDE")
                    else item["multiplierUp"]
                )
                if not ref * low <= px <= ref * high:
                    raise RiskViolation("Percent price violated")
            elif kind in {"MAX_NUM_ORDERS", "EXCHANGE_MAX_NUM_ORDERS"}:
                count = (
                    context.venue_symbol_open_orders
                    if kind == "MAX_NUM_ORDERS"
                    else (context.venue_open_orders)
                )
                cap = int(item.get("maxNumOrders", 0))
                if count is None or count < 0 or cap <= 0 or count >= cap:
                    raise RiskViolation("Fresh venue order count missing or cap reached")
            elif kind in {
                "MAX_NUM_ALGO_ORDERS",
                "EXCHANGE_MAX_NUM_ALGO_ORDERS",
                "MAX_NUM_ICEBERG_ORDERS",
                "EXCHANGE_MAX_NUM_ICEBERG_ORDERS",
                "ICEBERG_PARTS",
                "TRAILING_DELTA",
                "MAX_NUM_ORDER_LISTS",
                "EXCHANGE_MAX_NUM_ORDER_LISTS",
            }:
                # No algo, iceberg, trailing, order list or SOR parameters are allowed.
                continue
            elif kind == "MAX_POSITION":
                pending = sum(
                    (_d(row["quantity"]) - _d(row["executed_qty"]))
                    for row in self.orders()
                    if row["symbol"] == order["symbol"]
                    and row["side"] == "BUY"
                    and row["state"] not in TERMINAL
                    and row["client_id"] != exclude
                )
                if side == "BUY" and balances.get(rules.base_asset, ZERO) + pending + qty > _d(
                    item["maxPosition"]
                ):
                    raise RiskViolation("Maximum base position violated")
            else:
                raise RiskViolation(f"Unsupported restrictive filter: {kind}")
        value = qty * px
        if value > _d(limits.max_order_notional):
            raise RiskViolation("Per-order notional cap exceeded")
        if side == "BUY":
            reserve = value * (1 + _d(limits.fee_reserve_bps) / 10_000)
            asset = rules.quote_asset
            if reserved.get(asset, ZERO) + reserve > _d(limits.max_reserved_quote):
                raise RiskViolation("Aggregate quote reservation cap exceeded")
            pending = sum(
                (_d(row["quantity"]) - _d(row["executed_qty"]))
                for row in self.orders()
                if row["base_asset"] == rules.base_asset
                and row["side"] == "BUY"
                and row["state"] not in TERMINAL
                and row["client_id"] != exclude
            )
            if (balances.get(rules.base_asset, ZERO) + pending + qty) * ask > _d(
                limits.max_base_position_quote
            ):
                raise RiskViolation("Base inventory exposure cap exceeded")
        else:
            asset, reserve = rules.base_asset, qty * (1 + _d(limits.fee_reserve_bps) / 10_000)
        if balances.get(asset, ZERO) - reserved.get(asset, ZERO) < reserve:
            raise RiskViolation("Insufficient unreserved balance")
        # Venue free already excludes locks observed at last reconciliation. Only
        # newer or undispatched local reservations are subtracted a second time.
        newer_reserve = sum(
            _d(row["reserve_remaining"])
            for row in self.orders()
            if row["reserve_asset"] == asset
            and row["state"] not in TERMINAL
            and row["client_id"] != exclude
            and (
                row["state"] == "PREPARED"
                or row.get("observed_us", row["created_us"]) > meta["last_reconcile_us"]
            )
        )
        if _d(meta["last_actual_free"].get(asset, "0")) - newer_reserve < reserve:
            raise RiskViolation("Venue free balance is insufficient; locked assets cannot be spent")
        self._portfolio_risk(order, context, exclude=exclude)
        return asset, _s(reserve)

    def _portfolio_risk(self, order: dict, context: RiskContext, *, exclude: str | None) -> None:
        if not context.portfolio_checks:
            if self.adapter.network:
                raise RiskViolation(
                    "Portfolio risk checks cannot be waived for real network access"
                )
            return
        limits, meta = self.limits, self._meta()
        minute_us = context.now_us // 60_000_000 * 60_000_000
        if (
            context.estimated_annual_vol is None
            or context.volatility_asof_us is None
            or context.volatility_asof_us > minute_us
            or context.now_us - context.volatility_asof_us > limits.max_volatility_age_us
        ):
            raise RiskViolation("Causal, current portfolio volatility estimate missing")
        if _d(context.estimated_annual_vol) > _d(limits.estimated_annual_vol_cap):
            raise RiskViolation("Estimated portfolio annual volatility exceeds 10 percent")
        if (
            context.previous_closed_quote_volume is None
            or context.previous_minute_open_us != minute_us - 60_000_000
        ):
            raise RiskViolation("Immediately previous closed minute volume missing")
        balances = {asset: _d(value) for asset, value in meta["balances"].items()}
        pending = [
            row
            for row in self.orders()
            if row["state"] not in TERMINAL
            and row["generation"] == meta["generation"]
            and row["client_id"] != exclude
        ]
        projected = {asset: balances.get(asset, ZERO) for asset in ("BTC", "ETH")}
        for row in pending + [order]:
            if row["side"] == "BUY":
                projected[row["base_asset"]] += _d(row["quantity"]) - _d(row["executed_qty"])
        needed = {asset for asset, amount in projected.items() if amount > 0}
        if needed and (
            context.marks_asof_us is None
            or context.marks_asof_us > context.now_us
            or context.now_us - context.marks_asof_us > limits.max_quote_age_us
            or not needed.issubset(context.asset_marks)
        ):
            raise RiskViolation("Fresh marks for held or potentially bought assets missing")
        marks = {asset: _d(context.asset_marks[asset], positive=True) for asset in needed}
        # Third fee assets are supported in balances but their value is excluded
        # from NAV rather than assigning an unobserved BNB conversion price.
        nav = balances.get("USDT", ZERO) + sum(
            balances.get(asset, ZERO) * price for asset, price in marks.items()
        )
        pending_notional = sum(self._remaining_notional(row) for row in pending + [order])
        nav -= pending_notional * _d(limits.fee_reserve_bps) / 10_000
        if nav <= 0:
            raise RiskViolation("Conservative fee-adjusted NAV is nonpositive")
        exposure = {asset: projected[asset] * marks[asset] for asset in needed}
        if any(value > nav * _d(limits.single_asset_weight) for value in exposure.values()):
            raise RiskViolation("Potential single-asset exposure exceeds 30 percent")
        if sum(exposure.values()) > nav * _d(limits.gross_weight):
            raise RiskViolation("Potential gross exposure exceeds 60 percent")
        used = sum(
            self._remaining_notional(row)
            for row in pending + [order]
            if row["symbol"] == order["symbol"]
        )
        for row in self.db.execute(
            "SELECT data FROM fills WHERE generation=? AND symbol=?",
            (meta["generation"], order["symbol"]),
        ):
            trade = json.loads(row["data"])
            if minute_us <= trade["exchange_time_us"] <= context.now_us:
                used += _d(trade["quoteQty"])
        capacity = _d(context.previous_closed_quote_volume) * _d(limits.minute_volume_fraction)
        if used > capacity:
            raise RiskViolation("Minute fills plus potential orders exceed 0.1 percent capacity")

    def _remaining_notional(self, order: dict) -> Decimal:
        quantity = _d(order["quantity"]) - _d(order["executed_qty"])
        if order["type"] == "LIMIT":
            return quantity * _d(order["price"], positive=True)
        # Persist a conservative market quote reservation even for SELL. Never
        # replace a prior market reservation with the current lower quote.
        return quantity * _d(order["risk_price"], positive=True)

    def prepare(
        self,
        intent_key: str,
        *,
        symbol: str,
        side: str,
        quantity: str,
        rules: SymbolRules,
        context: RiskContext,
        order_type: str = "LIMIT",
        price: str | None = None,
    ) -> str:
        if not isinstance(intent_key, str) or not 1 <= len(intent_key) <= 200:
            raise RiskViolation("Intent key must identify a single strategy decision")
        old = self.db.execute(
            "SELECT client_id FROM orders WHERE intent_key=?", (intent_key,)
        ).fetchone()
        canonical = {
            "symbol": symbol,
            "side": side,
            "quantity": _s(_d(quantity, positive=True)),
            "type": order_type,
            "price": _s(_d(price, positive=True)) if price else None,
        }
        if old:
            existing = self.order(old["client_id"])
            if any(existing[key] != value for key, value in canonical.items()):
                raise RiskViolation("Intent key reused with different economics")
            return old["client_id"]
        self.gate.check(self.adapter)
        self._ready()
        order = {
            **canonical,
            "client_id": "cq_" + uuid.uuid4().hex,
            "intent_key": intent_key,
            "base_asset": rules.base_asset,
            "quote_asset": rules.quote_asset,
            "state": "PREPARED",
            "generation": self._meta()["generation"],
            "created_us": utc_now_us(),
            "exchange_order_id": None,
            "executed_qty": "0",
            "executed_quote": "0",
            "accounted_qty": "0",
            "accounted_quote": "0",
            "pending_action": None,
            "last_error": None,
        }
        order["risk_price"] = order["price"] or _s(
            _d(context.ask, positive=True) * (1 + _d(self.limits.market_slippage_bps) / 10_000)
        )
        asset, reserve = self._risk(order, rules, context)
        order["last_risk_evidence"] = self._risk_evidence(rules, context)
        order.update(reserve_asset=asset, reserve_initial=reserve, reserve_remaining=reserve)
        self._commit(
            "PREPARE",
            order["client_id"],
            lambda: self._save_order(order),
            {
                "intent_key": intent_key,
                "quote_received_us": context.quote_received_us,
                "quote_update_id": context.quote_update_id,
                "risk_evidence": order["last_risk_evidence"],
            },
        )
        return order["client_id"]

    @staticmethod
    def _risk_evidence(rules: SymbolRules, context: RiskContext) -> dict:
        return {
            "context_us": context.now_us,
            "quote_received_us": context.quote_received_us,
            "quote_update_id": context.quote_update_id,
            "bid": str(context.bid),
            "ask": str(context.ask),
            "healthy": context.healthy,
            "disk_ok": context.disk_ok,
            "rules_asof_us": rules.asof_us,
            "rules_sha256": hashlib.sha256(
                _json(
                    [
                        rules.symbol,
                        rules.base_asset,
                        rules.quote_asset,
                        rules.status,
                        rules.filters,
                        rules.exchange_filters,
                        rules.account_filters,
                    ]
                ).encode()
            ).hexdigest(),
            "portfolio_checks": context.portfolio_checks,
            "asset_marks": {key: str(value) for key, value in context.asset_marks.items()},
            "marks_asof_us": context.marks_asof_us,
            "estimated_annual_vol": context.estimated_annual_vol,
            "volatility_asof_us": context.volatility_asof_us,
            "previous_closed_quote_volume": context.previous_closed_quote_volume,
            "previous_minute_open_us": context.previous_minute_open_us,
            "conservative_fee_bps": context.conservative_fee_bps,
            "fee_asof_us": context.fee_asof_us,
            "fee_source": context.fee_source,
            "reference_prices": {
                str(key): str(value) for key, value in context.reference_prices.items()
            },
            "reference_asof_us": context.reference_asof_us,
            "venue_open_orders": context.venue_open_orders,
            "venue_symbol_open_orders": context.venue_symbol_open_orders,
        }

    @staticmethod
    def _error(error: BaseException) -> dict:
        # Never persist credential-bearing exception messages or request objects.
        return {
            "type": type(error).__name__,
            "code": getattr(error, "code", None),
            "http_status": getattr(error, "http_status", None),
        }

    def _uncertain(self, client_id: str, action: str, error: BaseException) -> None:
        order = self.order(client_id)
        order.update(state="UNKNOWN", pending_action=action, last_error=self._error(error))
        self._commit(
            "EXECUTION_UNKNOWN",
            client_id,
            lambda: self._save_order(order),
            {"action": action, "error": self._error(error)},
        )

    async def submit(self, client_id: str, *, rules: SymbolRules, context: RiskContext) -> dict:
        async with self._async_lock:
            order = self.order(client_id)
            if order["state"] != "PREPARED":
                return order  # Persisted dispatch is never repeated, including after restart.
            self.gate.check(self.adapter)
            self._ready()
            if order["type"] == "MARKET":
                order["risk_price"] = _s(
                    _d(context.ask, positive=True)
                    * (1 + _d(self.limits.market_slippage_bps) / 10_000)
                )
            asset, reserve = self._risk(order, rules, context, exclude=client_id)
            order["last_risk_evidence"] = self._risk_evidence(rules, context)
            order.update(
                reserve_asset=asset,
                reserve_initial=reserve,
                reserve_remaining=reserve,
                state="SUBMITTING",
                pending_action="submit",
            )
            self._commit(
                "DISPATCH_SUBMIT",
                client_id,
                lambda: self._save_order(order),
                {"risk_evidence": order["last_risk_evidence"]},
            )
            request = {
                "symbol": order["symbol"],
                "side": order["side"],
                "type": order["type"],
                "quantity": order["quantity"],
                "newClientOrderId": client_id,
            }
            if order["type"] == "LIMIT":
                request.update(price=order["price"], timeInForce="GTC")
            try:
                response = await self.adapter.submit(request)
            except BaseException as error:
                # Duplicate rejection can refer to an already accepted order: still query it.
                known = (
                    getattr(error, "status_known_rejected", False)
                    and getattr(error, "code", None) != -2010
                )
                if known and isinstance(error, Exception):
                    order.update(
                        state="REJECTED",
                        pending_action=None,
                        reserve_remaining="0",
                        last_error=self._error(error),
                    )
                    self._commit(
                        "SUBMIT_REJECTED",
                        client_id,
                        lambda: self._save_order(order),
                        {"error": self._error(error)},
                    )
                else:
                    self._uncertain(client_id, "submit", error)
                if not isinstance(error, Exception):
                    raise
                return self.order(client_id)
            return await self._observe_and_fills(client_id, response, "SUBMIT_RESPONSE")

    def _observe(self, client_id: str, response: dict, event: str) -> dict:
        order = self.order(client_id)
        if order["generation"] != self._meta()["generation"]:
            raise EvidenceError("Historical reset generation cannot mutate current account")
        if not isinstance(response, dict):
            raise EvidenceError("Order response is not an object")
        response_id = response.get("origClientOrderId", response.get("clientOrderId"))
        if response_id != client_id or response.get("symbol") != order["symbol"]:
            raise EvidenceError("Order response identity mismatch")
        for field_name, local in (("side", "side"), ("type", "type")):
            if field_name in response and response[field_name] != order[local]:
                raise EvidenceError("Order response economics mismatch")
        if "origQty" in response and _d(response["origQty"]) != _d(order["quantity"]):
            raise EvidenceError("Order response quantity mismatch")
        exchange_id = response.get("orderId")
        if not isinstance(exchange_id, int) or isinstance(exchange_id, bool) or exchange_id < 0:
            raise EvidenceError("Exchange order ID missing")
        if order["exchange_order_id"] is not None and exchange_id != order["exchange_order_id"]:
            raise EvidenceError("Exchange order ID changed")
        state = {
            "EXPIRED_IN_MATCH": "EXPIRED",
            "PENDING_CANCEL": "CANCEL_PENDING",
            "PENDING_NEW": "NEW",
        }.get(response.get("status"), response.get("status"))
        if state not in VENUE_STATES | {"CANCEL_PENDING"}:
            raise EvidenceError("Venue state missing or unsupported")
        qty, quote = _d(response["executedQty"]), _d(response["cummulativeQuoteQty"])
        if qty > _d(order["quantity"]) or (qty == 0 and quote != 0) or (qty > 0 and quote <= 0):
            raise EvidenceError("Impossible or unavailable cumulative execution")
        if state == "FILLED" and qty != _d(order["quantity"]):
            raise EvidenceError("FILLED cumulative quantity incomplete")
        if state == "REJECTED" and qty:
            raise EvidenceError("REJECTED response contains fills")
        if qty < _d(order["executed_qty"]) or quote < _d(order["executed_quote"]):
            self._commit("STALE_ORDER_RESPONSE", client_id, lambda: None)
            return order
        previous_state = order.get("confirmed_state", order["state"])
        if previous_state == "FILLED":
            state = "FILLED"
        elif previous_state in {"CANCELED", "EXPIRED"} and state in {"NEW", "PARTIALLY_FILLED"}:
            state = previous_state
        if qty == _d(order["quantity"]) and qty > 0:
            state = "FILLED"
        order.update(
            state=state,
            confirmed_state=state,
            exchange_order_id=exchange_id,
            executed_qty=_s(qty),
            executed_quote=_s(quote),
            pending_action=None,
            observed_us=utc_now_us(),
            last_error=None,
        )
        if state in TERMINAL:
            order["reserve_remaining"] = "0"
        else:
            order["reserve_remaining"] = _s(
                _d(order["reserve_initial"]) * (1 - qty / _d(order["quantity"]))
            )
        self._commit(
            event,
            client_id,
            lambda: self._save_order(order),
            {
                "venue_state": response.get("status"),
                "executed_qty": _s(qty),
                "executed_quote": _s(quote),
                "exchange_order_id": exchange_id,
            },
        )
        return order

    async def _observe_and_fills(self, client_id: str, response: dict, event: str) -> dict:
        try:
            order = self._observe(client_id, response, event)
        except Exception as error:
            self._uncertain(client_id, "query", error)
            return self.order(client_id)
        if self._debt(order):
            try:
                rows = await self.adapter.trades(order["symbol"], order["exchange_order_id"])
                self.apply_fills(client_id, rows)
            except Exception as error:
                self._commit(
                    "FILL_EVIDENCE_UNAVAILABLE",
                    client_id,
                    lambda: self._meta_update(reconcile_pending=True),
                    {"error": self._error(error)},
                )
        return self.order(client_id)

    def apply_fills(self, client_id: str, rows: list[dict]) -> int:
        """Atomic economic trade dedupe. Partial/incomplete evidence never certifies a ledger."""
        order = self.order(client_id)
        if order["generation"] != self._meta()["generation"]:
            raise EvidenceError("Historical reset generation cannot mutate current account")
        try:
            if not isinstance(rows, list):
                raise EvidenceError("Trades require a complete list")
            normalized = []
            for row in rows:
                if not isinstance(row, dict) or row.get("orderId") != order["exchange_order_id"]:
                    raise EvidenceError("Trade order identity mismatch")
                if "symbol" in row and row["symbol"] != order["symbol"]:
                    raise EvidenceError("Trade symbol mismatch")
                if "isBuyer" in row and row["isBuyer"] != (order["side"] == "BUY"):
                    raise EvidenceError("Trade direction mismatch")
                trade_id = row["id"]
                if not isinstance(trade_id, int) or isinstance(trade_id, bool) or trade_id < 0:
                    raise EvidenceError("Trade ID missing")
                fee_asset = row["commissionAsset"]
                if not isinstance(fee_asset, str) or not fee_asset.isalnum():
                    raise EvidenceError("Commission asset missing")
                trade_time = row["time"]
                if (
                    not isinstance(trade_time, int)
                    or isinstance(trade_time, bool)
                    or trade_time <= 0
                    or trade_time * 1000 > utc_now_us() + 1_000_000
                ):
                    raise EvidenceError("Trade exchange time missing or implausible")
                normalized.append(
                    {
                        "id": trade_id,
                        "orderId": row["orderId"],
                        "qty": _s(_d(row["qty"], positive=True)),
                        "price": _s(_d(row["price"], positive=True)),
                        "quoteQty": _s(_d(row["quoteQty"], positive=True)),
                        "commission": _s(_d(row["commission"])),
                        "commissionAsset": fee_asset,
                        "exchange_time_us": trade_time * 1000,
                    }
                )

            def apply() -> int:
                balances = {key: Decimal(value) for key, value in self._meta()["balances"].items()}
                count, qty, quote = 0, _d(order["accounted_qty"]), _d(order["accounted_quote"])
                for trade in normalized:
                    key = (order["generation"], order["symbol"], str(trade["id"]))
                    old = self.db.execute(
                        "SELECT client_id,data FROM fills "
                        "WHERE generation=? AND symbol=? AND trade_id=?",
                        key,
                    ).fetchone()
                    if old:
                        if old["client_id"] != client_id or json.loads(old["data"]) != trade:
                            raise EvidenceError("Same trade ID has conflicting economic evidence")
                        continue
                    self.db.execute(
                        "INSERT INTO fills VALUES (?,?,?,?,?)", (*key, client_id, _json(trade))
                    )
                    amount, cost, fee = (
                        _d(trade["qty"]),
                        _d(trade["quoteQty"]),
                        _d(trade["commission"]),
                    )
                    base, cash = order["base_asset"], order["quote_asset"]
                    direction = 1 if order["side"] == "BUY" else -1
                    balances[base] = balances.get(base, ZERO) + direction * amount
                    balances[cash] = balances.get(cash, ZERO) - direction * cost
                    balances[trade["commissionAsset"]] = (
                        balances.get(trade["commissionAsset"], ZERO) - fee
                    )
                    qty, quote, count = qty + amount, quote + cost, count + 1
                if qty > _d(order["executed_qty"]) or quote > _d(order["executed_quote"]):
                    raise EvidencePending("Trades are ahead of the confirmed order query")
                if any(value < 0 for value in balances.values()):
                    raise EvidenceError(
                        "Fill consumes unavailable asset or untracked commission balance"
                    )
                order.update(accounted_qty=_s(qty), accounted_quote=_s(quote))
                self._save_order(order)
                self._meta_update(
                    balances={key: _s(value) for key, value in balances.items()},
                    reconcile_pending=True,
                )
                return count

            return self._commit(
                "APPLY_FILLS", client_id, apply, {"trade_ids": [x["id"] for x in normalized]}
            )
        except Exception as error:
            if isinstance(error, ExecutionFrozen):
                raise
            if isinstance(error, EvidencePending):
                self._commit(
                    "FILLS_AHEAD_OF_ORDER_QUERY",
                    client_id,
                    lambda: self._meta_update(reconcile_pending=True),
                )
                raise
            self._commit(
                "FILL_CONFLICT",
                client_id,
                lambda: self._reason("FILL_CONFLICT"),
                {"error": self._error(error)},
            )
            raise EvidenceError("Invalid/conflicting fill evidence; ledger frozen") from error

    async def cancel(self, client_id: str) -> dict:
        async with self._async_lock:
            order = self.order(client_id)
            if order["generation"] != self._meta()["generation"]:
                raise EvidenceError("Historical generation cannot issue cancellation")
            if order["state"] in TERMINAL:
                return order
            if order["state"] == "PREPARED":
                order.update(state="CANCELED", reserve_remaining="0", pending_action=None)
                self._commit(
                    "LOCAL_CANCEL_UNDISPATCHED", client_id, lambda: self._save_order(order)
                )
                return order
            if order["state"] in {"UNKNOWN", "SUBMITTING", "CANCEL_PENDING"}:
                return order  # Query first; repeated cancel requests are not sent blindly.
            self.gate.check(self.adapter)
            order.update(state="CANCEL_PENDING", pending_action="cancel")
            self._commit("DISPATCH_CANCEL", client_id, lambda: self._save_order(order))
            try:
                response = await self.adapter.cancel(order["symbol"], client_id)
            except BaseException as error:
                self._uncertain(client_id, "cancel", error)
                if not isinstance(error, Exception):
                    raise
                return self.order(client_id)
            return await self._observe_and_fills(client_id, response, "CANCEL_RESPONSE")

    async def _query(self, client_id: str) -> dict:
        self.gate.check(self.adapter)
        order = self.order(client_id)
        if order["generation"] != self._meta()["generation"]:
            raise EvidenceError("Historical generation cannot recover into current balances")
        try:
            response = await self.adapter.query(order["symbol"], client_id)
            if response is None:
                self._uncertain(client_id, "query_not_found", EvidenceError("Not yet observable"))
                return self.order(client_id)
            return await self._observe_and_fills(client_id, response, "QUERY_RESPONSE")
        except Exception as error:
            self._uncertain(client_id, "query", error)
            return self.order(client_id)

    async def query(self, client_id: str) -> dict:
        async with self._async_lock:
            return await self._query(client_id)

    def reconcile(self, balances: dict) -> dict:
        try:
            actual = self._balances(balances)
        except Exception as error:
            self._commit(
                "BALANCE_EVIDENCE_INVALID", None, lambda: self._reason("BALANCE_EVIDENCE_INVALID")
            )
            raise EvidenceError("Balance snapshot invalid") from error
        expected, tolerance = self._meta()["balances"], _d(self.limits.balance_tolerance)
        differences = {
            asset: _s(Decimal(actual.get(asset, "0")) - Decimal(expected.get(asset, "0")))
            for asset in actual.keys() | expected.keys()
            if abs(Decimal(actual.get(asset, "0")) - Decimal(expected.get(asset, "0"))) > tolerance
        }
        unresolved = any(
            row["state"] == "UNKNOWN" or self._debt(row)
            for row in self.orders()
            if row["generation"] == self._meta()["generation"]
        )

        def record() -> None:
            if differences:
                self._reason("BALANCE_MISMATCH")
            self._meta_update(
                reconcile_pending=bool(differences) or unresolved,
                last_reconcile_us=utc_now_us(),
                last_balance_differences=differences,
                last_actual_free={key: _s(_d(value["free"])) for key, value in balances.items()},
                last_actual_balances=actual,
            )

        self._commit(
            "RECONCILE", None, record, {"differences": differences, "unresolved": unresolved}
        )
        return {
            "passed": not differences and not unresolved,
            "differences": differences,
            "unresolved_orders_or_fills": unresolved,
        }

    async def recover(self) -> dict:
        async with self._async_lock:
            self.gate.check(self.adapter)
            for order in self.orders():
                if order["generation"] == self._meta()["generation"] and (
                    order["state"] in ACTIVE or self._debt(order)
                ):
                    await self._query(order["client_id"])
            try:
                snapshot = await self.adapter.balances()
                return self.reconcile(snapshot)
            except Exception as error:
                self._commit(
                    "RECOVERY_BALANCES_UNAVAILABLE",
                    None,
                    lambda: self._meta_update(reconcile_pending=True),
                    {"error": self._error(error)},
                )
                return {"passed": False, "reason": "BALANCE_EVIDENCE_UNAVAILABLE"}

    def acknowledge_incident(self, reason: str, *, evidence: str, approved: bool = False) -> None:
        """Clear a circuit only after correct totals, no unknown/debt, explicit review."""
        meta = self._meta()
        if (
            not approved
            or not evidence
            or meta["reconcile_pending"]
            or any(
                order["state"] == "UNKNOWN" or self._debt(order)
                for order in self.orders()
                if order["generation"] == meta["generation"]
            )
        ):
            raise ExecutionFrozen(
                "Incident requires resolved evidence and explicit acknowledgement"
            )
        if reason == "RESET_SUSPECTED":
            raise ExecutionFrozen("Reset requires a separate generation, never an incident waiver")
        self._commit(
            "ACKNOWLEDGE_INCIDENT",
            None,
            lambda: self._meta_update(
                freeze_reasons=[item for item in meta["freeze_reasons"] if item != reason]
            ),
            {"reason": reason, "evidence": evidence},
        )

    async def detect_reset(self, *, client_ids: list[str]) -> dict:
        """Multiple missing known orders plus changed cash => suspicion, never proof."""
        async with self._async_lock:
            self.gate.check(self.adapter)
            known = [self.order(client_id) for client_id in dict.fromkeys(client_ids)]
            if len(known) < 2 or any(
                row["exchange_order_id"] is None or row["generation"] != self._meta()["generation"]
                for row in known
            ):
                raise EvidenceError("Reset probe requires two distinct acknowledged orders")
            missing = []
            for order in known:
                if await self.adapter.query(order["symbol"], order["client_id"]) is None:
                    missing.append(order["client_id"])
            actual = self._balances(await self.adapter.balances())
            tolerance, expected = _d(self.limits.balance_tolerance), self._meta()["balances"]
            changed = any(
                abs(Decimal(actual.get(key, "0")) - Decimal(expected.get(key, "0"))) > tolerance
                for key in actual.keys() | expected.keys()
            )
            suspected = len(missing) >= 2 and changed

            def record() -> None:
                if suspected:
                    self._reason("RESET_SUSPECTED")
                    self._meta_update(
                        reset_evidence={
                            "missing": missing,
                            "actual": actual,
                            "received_us": utc_now_us(),
                        }
                    )
                for client_id in missing:
                    order = self.order(client_id)
                    order.update(state="UNKNOWN", pending_action="query_not_found")
                    self._save_order(order)
                self._meta_update(reconcile_pending=True)

            self._commit(
                "RESET_PROBE", None, record, {"missing": missing, "balances_changed": changed}
            )
            return {"suspected": suspected, "missing": missing, "confirmed": False}

    def acknowledge_reset(
        self, balances: dict, *, approved: bool = False, evidence: str = ""
    ) -> int:
        actual, meta = self._balances(balances), self._meta()
        if not approved or not evidence or "RESET_SUSPECTED" not in meta["freeze_reasons"]:
            raise ExecutionFrozen(
                "Reset rebaseline requires recorded suspicion and explicit evidence"
            )
        if actual != meta.get("reset_evidence", {}).get("actual"):
            raise EvidenceError("Reset rebaseline differs from the observed reset snapshot")
        generation = meta["generation"] + 1

        def reset() -> None:
            for order in self.orders():
                if order["state"] not in TERMINAL:
                    order.update(
                        state="RESET_INVALIDATED", reserve_remaining="0", pending_action=None
                    )
                    self._save_order(order)
            self._meta_update(
                generation=generation,
                balances=actual,
                freeze_reasons=[],
                last_actual_free={key: _s(_d(value["free"])) for key, value in balances.items()},
                reconcile_pending=False,
                last_reconcile_us=utc_now_us(),
            )

        self._commit(
            "ACKNOWLEDGE_TESTNET_RESET",
            None,
            reset,
            {"generation": generation, "evidence": evidence, "actual": actual},
        )
        return generation

    def status(self) -> dict:
        meta, orders = self._meta(), self.orders()
        unknown = sum(row["state"] == "UNKNOWN" for row in orders)
        debt = sum(self._debt(row) for row in orders if row["generation"] == meta["generation"])
        reasons = list(meta["freeze_reasons"])
        if unknown:
            reasons.append("UNKNOWN_ORDER")
        if debt:
            reasons.append("FILL_DEBT")
        if meta["reconcile_pending"]:
            reasons.append("RECONCILIATION_PENDING")
        if self._disk_failed:
            reasons.append("DISK_GUARD")
        try:
            self.gate.check(self.adapter)
            authorized = self.adapter.network
        except GateDenied:
            authorized = False
        return {
            "environment": self.adapter.environment,
            "network": self.adapter.network,
            "network_authorized": authorized,
            "database": str(self.db_path),
            "generation": meta["generation"],
            "initialized": meta["initialized"],
            "frozen": bool(reasons),
            "freeze_reasons": reasons,
            "unknown_orders": unknown,
            "fill_debt_orders": debt,
            "balances": meta["balances"],
            "reserved": {key: _s(value) for key, value in self._reserved().items()},
            "last_reconcile_us": meta["last_reconcile_us"],
            "audit_head": self.verify_audit(),
            "order_count": len(orders),
        }

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self.db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            self.db.close()
            fcntl.flock(self._lock_file, fcntl.LOCK_UN)
            self._lock_file.close()

    def __enter__(self) -> ExecutionEngine:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
