"""Explicitly disabled Spot Testnet REST adapter; no mainnet order route exists."""

from __future__ import annotations

import hashlib
import hmac
import math
import re
import time
from collections import deque
from collections.abc import AsyncIterator, Callable
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

import httpx

TESTNET_ORIGIN = "https://testnet.binance.vision"
SYMBOLS = {"BTCUSDT", "ETHUSDT"}
ORDER_STATES = {"NEW", "PENDING_NEW", "PARTIALLY_FILLED", "FILLED", "CANCELED",
                "PENDING_CANCEL", "REJECTED", "EXPIRED", "EXPIRED_IN_MATCH"}
CLIENT_ID = re.compile(r"^[A-Za-z0-9._:/-]{1,36}$")
UNCERTAIN_CODES = {-1000, -1001, -1006, -1007, -1008, -1016}
KNOWN_REJECTION_CODES = ({-1002, -1013, -1014, -1015, -1020, -1021, -1022,
                         -2010, -2011, -2013, -2014, -2015, -2026, -2039} |
                        set(range(-1136, -1099)))
ALLOWED_ENDPOINTS = {
    ("GET", "/api/v3/time"), ("GET", "/api/v3/exchangeInfo"),
    ("GET", "/api/v3/account"), ("GET", "/api/v3/order"),
    ("POST", "/api/v3/order"), ("DELETE", "/api/v3/order"),
    ("POST", "/api/v3/order/test"), ("GET", "/api/v3/myTrades"),
    ("GET", "/api/v3/allOrders"), ("GET", "/api/v3/openOrders"),
}


class ProtocolRejected(Exception):
    """The particular request was definitely rejected; not an original order status."""

    status_known_rejected = True

    def __init__(self, message: str, *, code: int | None = None,
                 http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class NetworkDisabled(ProtocolRejected):
    pass


class ClockNotReady(ProtocolRejected):
    pass


class ExecutionUnknown(TimeoutError):
    """A request may have reached the matching engine; query, never blind resend."""

    status_known_rejected = False

    def __init__(self, message: str, *, code: int | None = None,
                 http_status: int | None = None):
        super().__init__(message)
        self.code = code
        self.http_status = http_status


class RateLimited(ExecutionUnknown):
    def __init__(self, retry_after_seconds: float, cooldown_until_ms: int,
                 http_status: int | None = None):
        super().__init__("Testnet请求受限，冷却期间禁止继续请求", http_status=http_status)
        self.retry_after_seconds = retry_after_seconds
        self.cooldown_until_ms = cooldown_until_ms


class PaginationIncomplete(ExecutionUnknown):
    pass


def decimal_text(value: Any, *, positive: bool = True) -> str:
    """Use decimal strings throughout the protocol, not rounded binary floats."""
    if isinstance(value, float) or isinstance(value, bool):
        raise ProtocolRejected("数量和价格必须使用Decimal、整数或十进制字符串")
    try:
        number = Decimal(str(value))
    except InvalidOperation as error:
        raise ProtocolRejected("十进制字段格式无效") from error
    if not number.is_finite() or (number <= 0 if positive else number < 0):
        raise ProtocolRejected("十进制字段范围无效")
    return format(number, "f")


def _symbol(value: str) -> str:
    if value not in SYMBOLS:
        raise ProtocolRejected("首版Testnet仅允许BTCUSDT与ETHUSDT")
    return value


def _client_id(value: str) -> str:
    if not isinstance(value, str) or not CLIENT_ID.fullmatch(value):
        raise ProtocolRejected("client order ID格式无效")
    return value


def _integer(value: Any, name: str) -> int:
    if isinstance(value, bool):
        raise ProtocolRejected(f"{name}必须为非负整数")
    try:
        result = int(value)
    except (TypeError, ValueError) as error:
        raise ProtocolRejected(f"{name}必须为非负整数") from error
    if str(result) != str(value) or result < 0:
        raise ProtocolRejected(f"{name}必须为非负整数")
    return result


class SpotTestnetAdapter:
    """No constructor I/O, key discovery, redirects, environment proxies, or retries."""

    environment = "spot_testnet"

    def __init__(self, *, api_key: str | None = None, api_secret: str | None = None,
                 transport: httpx.MockTransport | None = None, enable_network: bool = False,
                 clock_ms: Callable[[], int] | None = None,
                 recv_window_ms: str | int | Decimal = 5000, timeout_seconds: float = 10):
        if transport is not None and not isinstance(transport, httpx.MockTransport):
            raise ValueError("离线注入仅接受httpx.MockTransport")
        if not isinstance(enable_network, bool):
            raise ValueError("enable_network必须显式为布尔值")
        if any(value is not None and not isinstance(value, str) for value in (api_key, api_secret)):
            raise ValueError("凭证只接受显式字符串，不读取环境或文件")
        window = Decimal(decimal_text(recv_window_ms))
        if window > 60000 or window.as_tuple().exponent < -3:
            raise ValueError("recvWindow必须≤60000毫秒且最多三位小数")
        if not math.isfinite(timeout_seconds) or not 0 < timeout_seconds <= 30:
            raise ValueError("请求超时时间须在(0,30]秒")
        if enable_network and transport is not None:
            raise ValueError("mock与真实网络模式不能混用")
        self.network = bool(enable_network)
        self._transport = transport
        self._api_key = api_key
        self._secret = api_secret
        self._clock = clock_ms or (lambda: time.time_ns() // 1_000_000)
        self.recv_window_ms = format(window, "f")
        self._timeout = timeout_seconds
        self._client: httpx.AsyncClient | None = None
        self._offset_ms = 0
        self._synced_at_ms: int | None = None
        self.cooldown_until_ms = 0
        self.rate_headers: dict[str, str] = {}
        self._request_times: deque[int] = deque()

    async def __aenter__(self) -> SpotTestnetAdapter:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _safe_message(self, message: Any) -> str:
        safe = str(message)[:500]
        for secret in (self._api_key, self._secret):
            if secret:
                safe = safe.replace(secret, "[redacted]")
        return re.sub(r"signature=[a-fA-F0-9]+", "signature=[redacted]", safe)

    async def _request(self, method: str, path: str, params: dict[str, Any] | None = None,
                       *, signed: bool = False) -> Any:
        if (method, path) not in ALLOWED_ENDPOINTS:
            raise ProtocolRejected("请求路径不在固定Spot Testnet白名单")
        if not self.network and self._transport is None:
            raise NetworkDisabled("Testnet网络未显式启用；没有发送任何请求")
        now = self._clock()
        if now < self.cooldown_until_ms:
            raise RateLimited((self.cooldown_until_ms - now) / 1000, self.cooldown_until_ms)
        parameters = dict(params or {})
        headers = {"Accept": "application/json"}
        if signed:
            if not self._api_key or not self._secret:
                raise ProtocolRejected("签名请求缺少显式传入的Testnet凭证")
            if self._synced_at_ms is None or not 0 <= now - self._synced_at_ms <= 1_800_000:
                raise ClockNotReady("先显式同步Testnet时间；过期或倒退的时钟禁止签名请求")
            parameters.update(timestamp=now + self._offset_ms, recvWindow=self.recv_window_ms)
            headers["X-MBX-APIKEY"] = self._api_key
        query = urlencode(parameters)
        if signed:
            signature = hmac.new(self._secret.encode(), query.encode(), hashlib.sha256).hexdigest()
            query += "&signature=" + signature
        # A conservative local burst cap supplements, but cannot replace, IP-wide limits.
        while self._request_times and self._request_times[0] <= now - 60_000:
            self._request_times.popleft()
        short_window = [stamp for stamp in self._request_times if stamp > now - 10_000]
        if len(self._request_times) >= 60 or len(short_window) >= 40:
            until = (self._request_times[0] + 60_000 if len(self._request_times) >= 60
                     else short_window[0] + 10_000)
            self.cooldown_until_ms = max(self.cooldown_until_ms, until)
            raise RateLimited((until - now) / 1000, until)
        self._request_times.append(now)
        if self._client is None:
            self._client = httpx.AsyncClient(transport=self._transport, timeout=self._timeout,
                                              follow_redirects=False, trust_env=False)
        try:
            response = await self._client.request(method, TESTNET_ORIGIN + path + "?" + query,
                                                  headers=headers)
        except httpx.TransportError as error:
            raise ExecutionUnknown(f"Testnet传输状态未知：{type(error).__name__}") from None
        self.rate_headers = {key: value for key, value in response.headers.items()
                             if key.lower().startswith(("x-mbx-used-weight", "x-mbx-order-count"))}
        if response.status_code in (418, 429):
            try:
                retry = float(response.headers.get("Retry-After", "60"))
                if not math.isfinite(retry) or retry < 0:
                    raise ValueError
            except ValueError:
                retry = 60.0
            self.cooldown_until_ms = now + math.ceil(retry * 1000)
            raise RateLimited(retry, self.cooldown_until_ms, response.status_code)
        if response.status_code >= 500 or 300 <= response.status_code < 400:
            raise ExecutionUnknown("服务端或重定向响应不能确认执行状态",
                                   http_status=response.status_code)
        try:
            body = response.json()
        except ValueError:
            raise ExecutionUnknown(
                "Testnet响应不是可验证JSON", http_status=response.status_code
            ) from None
        code = body.get("code") if isinstance(body, dict) else None
        if isinstance(code, int) and code < 0:
            message = self._safe_message(body.get("msg", "Testnet API error"))
            if code in UNCERTAIN_CODES:
                raise ExecutionUnknown(message, code=code, http_status=response.status_code)
            if code not in KNOWN_REJECTION_CODES:
                raise ExecutionUnknown("未登记错误码，不能认定写请求已拒绝",
                                       code=code, http_status=response.status_code)
            if code == -1021:
                self._synced_at_ms = None
            raise ProtocolRejected(message, code=code, http_status=response.status_code)
        if response.status_code >= 400:
            raise ExecutionUnknown("HTTP错误没有明确API拒绝证据", http_status=response.status_code)
        return body

    async def server_time(self) -> dict:
        body = await self._request("GET", "/api/v3/time")
        if not isinstance(body, dict) or type(body.get("serverTime")) is not int:
            raise ExecutionUnknown("服务器时间响应无效")
        return body

    async def sync_time(self) -> dict:
        before = self._clock()
        body = await self.server_time()
        after = self._clock()
        if not 0 <= after - before <= float(self.recv_window_ms) / 2:
            self._synced_at_ms = None
            raise ClockNotReady("时间同步延迟或本地时钟跳变超限")
        self._offset_ms = body["serverTime"] - (before + after) // 2
        self._synced_at_ms = after
        return {"server_time_ms": body["serverTime"], "offset_ms": self._offset_ms,
                "round_trip_ms": after - before}

    async def exchange_info(self, symbol: str | None = None) -> dict:
        body = await self._request("GET", "/api/v3/exchangeInfo",
                                   {"symbol": _symbol(symbol)} if symbol else {})
        if not isinstance(body, dict) or not isinstance(body.get("symbols"), list):
            raise ExecutionUnknown("exchangeInfo响应缺少规则")
        return body

    @staticmethod
    def _order_params(order: dict) -> dict:
        allowed = {"symbol", "side", "type", "quantity", "price", "timeInForce",
                   "newClientOrderId", "newOrderRespType", "selfTradePreventionMode"}
        if set(order) - allowed:
            raise ProtocolRejected("订单包含未支持字段")
        params = {"symbol": _symbol(order.get("symbol")), "side": order.get("side"),
                  "type": order.get("type"), "quantity": decimal_text(order.get("quantity")),
                  "newClientOrderId": _client_id(order.get("newClientOrderId")),
                  "newOrderRespType": "FULL"}
        if params["side"] not in {"BUY", "SELL"} or params["type"] not in {"LIMIT", "MARKET"}:
            raise ProtocolRejected("首版仅支持BUY/SELL与LIMIT/MARKET")
        if order.get("newOrderRespType", "FULL") != "FULL":
            raise ProtocolRejected("执行对账要求FULL订单响应")
        if params["type"] == "LIMIT":
            params["price"] = decimal_text(order.get("price"))
            if order.get("timeInForce") not in {"GTC", "IOC", "FOK"}:
                raise ProtocolRejected("LIMIT订单须明确timeInForce")
            params["timeInForce"] = order["timeInForce"]
        elif "price" in order or "timeInForce" in order:
            raise ProtocolRejected("MARKET订单不接受price/timeInForce")
        if "selfTradePreventionMode" in order:
            params["selfTradePreventionMode"] = order["selfTradePreventionMode"]
        return params

    @staticmethod
    def _order_response(body: Any, symbol: str, client_order_id: str) -> dict:
        if not isinstance(body, dict) or body.get("status") not in ORDER_STATES:
            raise ExecutionUnknown("订单响应缺少明确状态；查询原client ID，禁止重发")
        ids = {body.get("clientOrderId"), body.get("origClientOrderId")}
        if body.get("symbol") != symbol or client_order_id not in ids:
            raise ExecutionUnknown("订单响应身份不符")
        try:
            _integer(body["orderId"], "orderId")
            quantity = Decimal(decimal_text(body["origQty"]))
            executed = Decimal(decimal_text(body["executedQty"], positive=False))
            if executed > quantity:
                raise ProtocolRejected("累计成交量超过订单数量")
        except (KeyError, ProtocolRejected) as error:
            raise ExecutionUnknown(f"订单响应数量/标识不可验证：{type(error).__name__}") from None
        return body

    async def submit(self, order: dict) -> dict:
        params = self._order_params(order)
        body = await self._request("POST", "/api/v3/order", params, signed=True)
        return self._order_response(body, params["symbol"], params["newClientOrderId"])

    async def validate_order(self, order: dict) -> dict:
        body = await self._request("POST", "/api/v3/order/test", self._order_params(order),
                                   signed=True)
        if not isinstance(body, dict):
            raise ExecutionUnknown("Test order响应格式无效")
        return body

    async def query(self, symbol: str, client_order_id: str) -> dict | None:
        params = {"symbol": _symbol(symbol), "origClientOrderId": _client_id(client_order_id)}
        try:
            body = await self._request("GET", "/api/v3/order", params, signed=True)
        except ProtocolRejected as error:
            if error.code == -2013:
                return None
            raise
        return self._order_response(body, symbol, client_order_id)

    async def cancel(self, symbol: str, client_order_id: str) -> dict:
        params = {"symbol": _symbol(symbol), "origClientOrderId": _client_id(client_order_id)}
        body = await self._request("DELETE", "/api/v3/order", params, signed=True)
        return self._order_response(body, symbol, client_order_id)

    async def account(self) -> dict:
        body = await self._request("GET", "/api/v3/account", signed=True)
        if not isinstance(body, dict) or not isinstance(body.get("balances"), list):
            raise ExecutionUnknown("账户响应缺少balances")
        return body

    async def balances(self) -> dict[str, dict[str, str]]:
        body = await self.account()
        balances = {}
        try:
            for row in body["balances"]:
                asset = row["asset"]
                if asset in balances or not isinstance(asset, str):
                    raise ProtocolRejected("账户资产重复或格式无效")
                balances[asset] = {name: decimal_text(row[name], positive=False)
                                   for name in ("free", "locked")}
        except (KeyError, ProtocolRejected) as error:
            raise ExecutionUnknown(f"账户余额不可验证：{type(error).__name__}") from None
        return balances

    @staticmethod
    def _page_params(symbol: str, limit: int, start_ms: int | None, end_ms: int | None) -> dict:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 1000:
            raise ProtocolRejected("分页limit须在1到1000")
        params: dict[str, Any] = {"symbol": _symbol(symbol), "limit": limit}
        if start_ms is not None:
            params["startTime"] = _integer(start_ms, "startTime")
        if end_ms is not None:
            params["endTime"] = _integer(end_ms, "endTime")
        if start_ms is not None and end_ms is not None and not 0 <= end_ms - start_ms <= 86_400_000:
            raise ProtocolRejected("成交/订单查询时间范围须为最多24小时")
        return params

    async def trades_page(self, symbol: str, *, order_id: int | str | None = None,
                          from_id: int | None = None, start_ms: int | None = None,
                          end_ms: int | None = None, limit: int = 1000) -> list[dict]:
        params = self._page_params(symbol, limit, start_ms, end_ms)
        if (order_id is not None or from_id is not None) and (
            start_ms is not None or end_ms is not None
        ):
            raise ProtocolRejected("myTrades的orderId/fromId不得与时间范围混用")
        if order_id is not None:
            params["orderId"] = _integer(order_id, "orderId")
        if from_id is not None:
            params["fromId"] = _integer(from_id, "fromId")
        body = await self._request("GET", "/api/v3/myTrades", params, signed=True)
        if not isinstance(body, list) or any(not isinstance(row, dict) for row in body):
            raise ExecutionUnknown("成交分页响应格式无效")
        return body

    async def iter_trades(self, symbol: str, *, order_id: int | str | None = None,
                          from_id: int = 0, limit: int = 1000,
                          max_pages: int = 20) -> AsyncIterator[dict]:
        if not isinstance(max_pages, int) or isinstance(max_pages, bool) or max_pages <= 0:
            raise ProtocolRejected("max_pages必须为正整数")
        cursor = _integer(from_id, "fromId")
        for _ in range(max_pages):
            page = await self.trades_page(symbol, order_id=order_id, from_id=cursor, limit=limit)
            previous = cursor - 1
            for trade in page:
                try:
                    trade_id = _integer(trade["id"], "tradeId")
                    if trade_id < cursor or trade_id <= previous or trade["symbol"] != symbol:
                        raise ProtocolRejected("成交分页未向前推进或币种不符")
                    if order_id is not None and str(trade["orderId"]) != str(order_id):
                        raise ProtocolRejected("成交不属于查询订单")
                    _integer(trade["orderId"], "orderId")
                    _integer(trade["time"], "trade time")
                    for name in ("price", "qty", "quoteQty", "commission"):
                        decimal_text(trade[name], positive=name != "commission")
                    if not isinstance(trade["commissionAsset"], str):
                        raise ProtocolRejected("佣金资产格式无效")
                except (KeyError, ProtocolRejected) as error:
                    raise ExecutionUnknown(f"成交证据不可验证：{type(error).__name__}") from None
                yield trade
                previous = trade_id
            if len(page) < limit:
                return
            cursor = previous + 1
        raise PaginationIncomplete("成交查询达到分页预算，不能将不完整列表用于最终对账")

    async def trades(self, symbol: str, exchange_order_id: int | str) -> list[dict]:
        return [trade async for trade in self.iter_trades(symbol, order_id=exchange_order_id)]

    async def all_orders_page(self, symbol: str, *, order_id: int | None = None,
                              start_ms: int | None = None, end_ms: int | None = None,
                              limit: int = 1000) -> list[dict]:
        params = self._page_params(symbol, limit, start_ms, end_ms)
        if order_id is not None:
            params["orderId"] = _integer(order_id, "orderId")
        body = await self._request("GET", "/api/v3/allOrders", params, signed=True)
        if not isinstance(body, list):
            raise ExecutionUnknown("订单分页响应格式无效")
        return body

    async def open_orders(self, symbol: str) -> list[dict]:
        body = await self._request("GET", "/api/v3/openOrders", {"symbol": _symbol(symbol)},
                                   signed=True)
        if not isinstance(body, list):
            raise ExecutionUnknown("openOrders响应格式无效")
        return body
