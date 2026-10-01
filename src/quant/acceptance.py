"""Offline HTTP-level execution acceptance. Never configures real credentials."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from decimal import Decimal
from pathlib import Path
from typing import Callable

import httpx

FAKE_KEY = "offline-acceptance-key"
FAKE_SECRET = "offline-acceptance-secret"


class OfflineSpotExchange:
    """An isolated HTTP mock that accepts an order before losing its response.

    The first query cannot see the asynchronous record. The later query and
    trade list prove a fill. This exercises the real request/signature adapter,
    rather than a fake adapter method that bypasses protocol handling.
    """

    def __init__(self, clock_ms: Callable[[], int] | None = None):
        self.clock_ms = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self.submissions = 0
        self.queries = 0
        self.order = None
        self.trade = None
        self.requests = []
        self.assets = {"USDT": Decimal("10000"), "BTC": Decimal("0"),
                       "ETH": Decimal("0"), "BNB": Decimal("0")}

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.url.scheme != "https" or request.url.host != "testnet.binance.vision":
            raise AssertionError("offline acceptance received an unexpected host")
        path, method = request.url.path, request.method
        self.requests.append({"method": method, "path": path})
        if path == "/api/v3/time" and method == "GET":
            return httpx.Response(200, json={"serverTime": self.clock_ms()})
        encoded = request.url.query.decode()
        parameters, signature = encoded.rsplit("&signature=", 1)
        expected = hmac.new(FAKE_SECRET.encode(), parameters.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise AssertionError("adapter signed different bytes from the actual HTTP request")
        if request.headers.get("X-MBX-APIKEY") != FAKE_KEY:
            raise AssertionError("offline acceptance has no matching synthetic key")
        params = dict(request.url.params)
        if path == "/api/v3/order" and method == "POST":
            self.submissions += 1
            if self.submissions != 1:
                raise AssertionError("UNKNOWN order was blindly submitted twice")
            quantity = Decimal(params["quantity"])
            price = Decimal(params["price"])
            notional = price * quantity
            commission = notional * Decimal(".001")
            base = "BTC" if params["symbol"] == "BTCUSDT" else "ETH"
            if params["side"] != "BUY":
                raise AssertionError("acceptance scenario expects a buy")
            self.assets["USDT"] -= notional + commission
            self.assets[base] += quantity
            self.order = {
                "symbol": params["symbol"], "orderId": 123,
                "clientOrderId": params["newClientOrderId"], "status": "FILLED",
                "side": "BUY", "type": "LIMIT", "timeInForce": "GTC",
                "price": str(price), "origQty": str(quantity), "executedQty": str(quantity),
                "cummulativeQuoteQty": str(notional), "transactTime": self.clock_ms(),
            }
            self.trade = {
                "symbol": params["symbol"], "id": 456, "orderId": 123,
                "price": str(price), "qty": str(quantity), "quoteQty": str(notional),
                "commission": str(commission), "commissionAsset": "USDT",
                "time": self.clock_ms(), "isBuyer": True, "isMaker": False,
                "isBestMatch": True,
            }
            raise httpx.ReadTimeout("offline lost response after fill", request=request)
        if path == "/api/v3/order" and method == "GET":
            self.queries += 1
            if self.queries == 1 or self.order is None:
                return httpx.Response(400, json={"code": -2013, "msg": "Order does not exist."})
            if params.get("origClientOrderId") != self.order["clientOrderId"]:
                raise AssertionError("recovery queried a different client order ID")
            return httpx.Response(200, json=self.order)
        if path == "/api/v3/myTrades" and method == "GET":
            rows = [self.trade] if self.trade else []
            return httpx.Response(200, json=rows)
        if path == "/api/v3/account" and method == "GET":
            return httpx.Response(200, json={"canTrade": True, "balances": [
                {"asset": asset, "free": str(value), "locked": "0"}
                for asset, value in self.assets.items()
            ]})
        if path == "/api/v3/openOrders" and method == "GET":
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected offline request: {method} {path}")


async def run_execution_acceptance(db_path: Path, *, disk_check=None) -> dict:
    """Exercise loss, asynchronous lookup, exact fees, dedupe and real recovery."""
    from .execution import ExecutionEngine, ExecutionFrozen, RiskContext, SymbolRules
    from .paths import utc_now_us
    from .testnet import SpotTestnetAdapter

    if db_path.exists():
        raise FileExistsError("offline acceptance refuses to overwrite an existing ledger")
    server = OfflineSpotExchange()
    adapter = SpotTestnetAdapter(api_key=FAKE_KEY, api_secret=FAKE_SECRET,
                                transport=httpx.MockTransport(server.handle))
    engine = None
    try:
        await adapter.sync_time()
        engine = ExecutionEngine(adapter, db_path=db_path, disk_check=disk_check)
        engine.bootstrap({asset: {"free": str(value), "locked": "0"}
                          for asset, value in server.assets.items()})
        now = utc_now_us()
        rules = SymbolRules(
            symbol="BTCUSDT", base_asset="BTC", quote_asset="USDT", asof_us=now,
            filters=(
                {"filterType": "PRICE_FILTER", "minPrice": "1", "maxPrice": "1000000",
                 "tickSize": ".01"},
                {"filterType": "LOT_SIZE", "minQty": ".00001", "maxQty": "100",
                 "stepSize": ".00001"},
                {"filterType": "MIN_NOTIONAL", "minNotional": "5", "applyToMarket": True,
                 "avgPriceMins": 5},
            ),
        )
        minute = now // 60_000_000 * 60_000_000
        context = RiskContext(
            now_us=now, bid="49999", ask="50000", quote_received_us=now,
            quote_update_id=1, healthy=True, disk_ok=True, asset_marks={"BTC": "50000"},
            marks_asof_us=now, estimated_annual_vol=".05", volatility_asof_us=minute,
            previous_closed_quote_volume="10000000",
            previous_minute_open_us=minute - 60_000_000,
            conservative_fee_bps="20", fee_asof_us=now,
            fee_source="synthetic_mock_account",
        )
        cid = engine.prepare("offline-timeout-fill", symbol="BTCUSDT", side="BUY",
                             quantity=".001", price="50000", rules=rules, context=context)
        sent = await engine.submit(cid, rules=rules, context=context)
        assert sent["state"] == "UNKNOWN" and server.submissions == 1
        assert engine.status()["frozen"]
        duplicate = await engine.submit(cid, rules=rules, context=context)
        assert duplicate["state"] == "UNKNOWN" and server.submissions == 1
        try:
            engine.prepare("new-intent-while-unknown", symbol="BTCUSDT", side="BUY",
                           quantity=".001", price="50000", rules=rules, context=context)
        except ExecutionFrozen:
            pass
        else:
            raise AssertionError("an unknown order did not freeze a new intent")
        missing = await engine.query(cid)
        assert missing["state"] == "UNKNOWN" and engine.status()["frozen"]
        assert server.queries == 1 and server.submissions == 1
        recovered = await engine.recover()
        assert recovered["passed"], recovered
        assert engine.order(cid)["state"] == "FILLED"
        assert engine.apply_fills(cid, [server.trade]) == 0
        assert engine.reconcile(await adapter.balances())["passed"]
        before = engine.status()
        assert not before["frozen"]
        assert Decimal(before["balances"]["USDT"]) == Decimal("9949.95")
        assert Decimal(before["balances"]["BTC"]) == Decimal(".001")
        assert engine.db.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 1
        engine.close()
        engine = ExecutionEngine(adapter, db_path=db_path, disk_check=disk_check)
        assert engine.status()["frozen"]  # startup requires current account reconciliation
        assert (await engine.recover())["passed"]
        same = engine.prepare("offline-timeout-fill", symbol="BTCUSDT", side="BUY",
                              quantity=".001", price="50000", rules=rules, context=context)
        assert same == cid
        assert (await engine.submit(cid, rules=rules, context=context))["state"] == "FILLED"
        after = engine.status()
        assert after["balances"] == before["balances"] and not after["frozen"]
        assert after["order_count"] == 1 and server.submissions == 1
        return {
            "module": "P07_execution_integration", "status": "OFFLINE_ENGINEERING_PASS",
            "mode": "offline_engineering", "real_testnet_days": 0, "exchange_orders": 0,
            "http_mock_mutations": server.submissions, "query_not_found_retained_unknown": True,
            "query_resolved_fill": True, "commission_asset": "USDT", "commission": ".05",
            "trade_deduplication": True, "restart_same_client_id": True,
            "network_enabled": adapter.network, "real_money_authorized": False,
            "requests": server.requests, "initial_assets": {"USDT": "10000", "BTC": "0"},
            "final": after, "sources": {name: hashlib.sha256(
                Path(__file__).with_name(name + ".py").read_bytes()).hexdigest()
                for name in ("execution", "testnet", "acceptance")},
        }
    finally:
        if engine is not None:
            engine.close()
        await adapter.close()


def write_execution_acceptance(report: dict, output: Path) -> None:
    from .disk import check

    output = output.resolve()
    if not str(output).startswith("/mnt/d/"):
        raise ValueError("acceptance reports must remain on D:")
    check(reserve=100_000)
    output.mkdir(parents=True, exist_ok=True)
    (output / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "REPORT.md").write_text(
        "# P07 离线串联验收\n\n状态：通过。使用虚构凭证和HTTP mock，"
        "交易所订单0笔，真实测试环境0天。\n\n"
        "真实接口签名→持久下单意图→丢失成交响应→UNKNOWN冻结→首查不存在仍冻结→"
        "查询确认成交→逐笔佣金→余额核对→重启恢复和幂等，完整串联通过。\n\n"
        "USDT由10000变为9949.95，BTC为0.001，手续费0.05USDT；"
        "重复成交/重复意图/重启没有再次发单或扣费。\n\n"
        "本报告没有验收主网成交、真实测试账户或30天连续运行，也不授权真钱。\n"
    )
