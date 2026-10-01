import asyncio
import hashlib
import hmac
from urllib.parse import parse_qs

import httpx
import pytest

from quant.testnet import (
    ClockNotReady,
    ExecutionUnknown,
    NetworkDisabled,
    PaginationIncomplete,
    ProtocolRejected,
    RateLimited,
    SpotTestnetAdapter,
)

API_KEY = "synthetic-testnet-key"
SECRET = "synthetic-testnet-secret"
NOW = 1_800_000_000_000
ORDER = {"symbol": "BTCUSDT", "side": "BUY", "type": "LIMIT",
         "quantity": "0.01000000", "price": "30000.00", "timeInForce": "GTC",
         "newClientOrderId": "coin-001"}


def order_response(**changes):
    return {"symbol": "BTCUSDT", "orderId": 100, "clientOrderId": "coin-001",
            "origQty": "0.01000000", "executedQty": "0.00000000",
            "cummulativeQuoteQty": "0.00000000", "status": "NEW", **changes}


def trade(trade_id):
    return {"symbol": "BTCUSDT", "id": trade_id, "orderId": 100,
            "qty": "0.003", "price": "30000.00", "quoteQty": "90.00",
            "commission": "0.0003", "commissionAsset": "BNB", "time": NOW,
            "isBuyer": True, "isMaker": False}


def adapter(handler, calls, clock=None):
    def handle(request):
        calls.append(request)
        assert request.url.host == "testnet.binance.vision"
        if request.url.path == "/api/v3/time":
            return httpx.Response(200, json={"serverTime": NOW + 200})
        return handler(request)
    return SpotTestnetAdapter(api_key=API_KEY, api_secret=SECRET,
                             transport=httpx.MockTransport(handle),
                             clock_ms=clock or (lambda: NOW))


def test_default_cannot_access_network_or_discover_environment_keys(monkeypatch):
    monkeypatch.setenv("BINANCE_API_KEY", "never-read")
    monkeypatch.setenv("BINANCE_API_SECRET", "never-read")
    async def scenario():
        async with SpotTestnetAdapter() as client:
            assert not client.network
            assert client.environment == "spot_testnet"
            with pytest.raises(NetworkDisabled):
                await client.server_time()
    asyncio.run(scenario())
    with pytest.raises(ValueError):
        SpotTestnetAdapter(enable_network="false")


def test_HMAC_signs_exact_sent_query_and_explicit_clock_offset():
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(200, json=order_response()), calls) as client:
            with pytest.raises(ClockNotReady):
                await client.submit(ORDER)
            assert calls == []
            assert (await client.sync_time())["offset_ms"] == 200
            result = await client.submit(ORDER)
            assert result["orderId"] == 100
    asyncio.run(scenario())
    request = calls[-1]
    query = request.url.query.decode()
    payload, signature = query.rsplit("&signature=", 1)
    assert signature == hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    values = parse_qs(payload)
    assert values["timestamp"] == [str(NOW + 200)]
    assert values["recvWindow"] == ["5000"]
    assert values["quantity"] == ["0.01000000"]
    assert values["newOrderRespType"] == ["FULL"]
    assert request.headers["X-MBX-APIKEY"] == API_KEY
    assert SECRET not in query
    assert len(calls) == 2


@pytest.mark.parametrize("status,body", [
    (504, {"code": -1007, "msg": "timeout"}),
    (400, {"code": -1007, "msg": "timeout"}),
    (400, {"code": -1006, "msg": "unknown bus response"}),
    (400, {"code": -99999, "msg": "new undocumented error"}),
])
def test_unknown_execution_never_blindly_retries_write(status, body):
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(status, json=body), calls) as client:
            await client.sync_time()
            with pytest.raises(ExecutionUnknown) as error:
                await client.submit(ORDER)
            assert not error.value.status_known_rejected
    asyncio.run(scenario())
    assert [call.method for call in calls] == ["GET", "POST"]


def test_transport_timeout_is_unknown_without_sensitive_request_text():
    calls = []
    def handle(request):
        raise httpx.ReadTimeout("sensitive URL " + str(request.url), request=request)
    async def scenario():
        async with adapter(handle, calls) as client:
            await client.sync_time()
            with pytest.raises(ExecutionUnknown) as error:
                await client.submit(ORDER)
            assert SECRET not in str(error.value)
            assert "signature=" not in str(error.value)
    asyncio.run(scenario())
    assert len(calls) == 2


def test_clear_rejection_and_not_found_query_have_distinct_meaning():
    calls = []
    def handle(request):
        code = -2013 if request.method == "GET" else -1013
        return httpx.Response(400, json={"code": code, "msg": "explicit rejected"})
    async def scenario():
        async with adapter(handle, calls) as client:
            await client.sync_time()
            with pytest.raises(ProtocolRejected) as error:
                await client.submit(ORDER)
            assert error.value.status_known_rejected
            assert error.value.code == -1013
            assert await client.query("BTCUSDT", "coin-001") is None
    asyncio.run(scenario())
    assert len([call for call in calls if call.method == "POST"]) == 1


@pytest.mark.parametrize("status,seconds", [(429, 10), (418, 120)])
def test_rate_limit_backoff_blocks_followup_requests(status, seconds):
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(status, headers={"Retry-After": str(seconds)},
                                                    json={"code": -1003}), calls) as client:
            await client.sync_time()
            with pytest.raises(RateLimited) as error:
                await client.submit(ORDER)
            assert error.value.retry_after_seconds == seconds
            assert client.cooldown_until_ms == NOW + seconds * 1000
            with pytest.raises(RateLimited):
                await client.server_time()
    asyncio.run(scenario())
    assert len(calls) == 2


def test_redirect_never_reaches_mainnet():
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(
            302, headers={"Location": "https://api.binance.com/api/v3/order"}), calls) as client:
            await client.sync_time()
            with pytest.raises(ExecutionUnknown):
                await client.submit(ORDER)
            with pytest.raises(ProtocolRejected):
                await client._request("POST", "https://api.binance.com/api/v3/order")
    asyncio.run(scenario())
    assert len(calls) == 2


def test_cancel_preserves_original_id_and_partial_fill_fields():
    calls = []
    body = order_response(clientOrderId="cancel-response-id", origClientOrderId="coin-001",
                          status="CANCELED", executedQty="0.00300000",
                          cummulativeQuoteQty="90.00")
    async def scenario():
        async with adapter(lambda _: httpx.Response(200, json=body), calls) as client:
            await client.sync_time()
            result = await client.cancel("BTCUSDT", "coin-001")
            assert result == body
    asyncio.run(scenario())
    assert calls[-1].method == "DELETE"
    assert parse_qs(calls[-1].url.query.decode())["origClientOrderId"] == ["coin-001"]


def test_account_decimal_balances_and_exchange_filters_remain_exact():
    calls = []
    rules = {"symbols": [{"symbol": "BTCUSDT", "status": "TRADING", "filters": [
        {"filterType": "LOT_SIZE", "stepSize": "0.00001000"},
        {"filterType": "NOTIONAL", "minNotional": "5.00000000"}]}], "rateLimits": []}
    def handle(request):
        return httpx.Response(200, json=rules if request.url.path.endswith("exchangeInfo") else {
            "balances": [{"asset": "USDT", "free": "1000.12345678", "locked": "30.00"}]})
    async def scenario():
        async with adapter(handle, calls) as client:
            assert await client.exchange_info("BTCUSDT") == rules
            await client.sync_time()
            assert await client.balances() == {
                "USDT": {"free": "1000.12345678", "locked": "30.00"}}
    asyncio.run(scenario())


def test_trade_pagination_uses_inclusive_ID_cursor_and_preserves_commission():
    calls = []
    def handle(request):
        params = parse_qs(request.url.query.decode())
        assert params["orderId"] == ["100"]
        cursor = int(params["fromId"][0])
        rows = [trade(10), trade(11)] if cursor == 0 else [trade(12)]
        return httpx.Response(200, json=rows)
    async def scenario():
        async with adapter(handle, calls) as client:
            await client.sync_time()
            fills = [row async for row in client.iter_trades("BTCUSDT", order_id=100, limit=2)]
            assert [row["id"] for row in fills] == [10, 11, 12]
            assert all(row["commissionAsset"] == "BNB" for row in fills)
    asyncio.run(scenario())
    pages = [parse_qs(call.url.query.decode())["fromId"] for call in calls[1:]]
    assert pages == [["0"], ["12"]]


def test_pagination_budget_and_repeated_trade_ID_fail_instead_of_certifying_partial_list():
    async def scenario(repeated=False):
        calls = []
        def handle(request):
            cursor = int(parse_qs(request.url.query.decode())["fromId"][0])
            return httpx.Response(200, json=[trade(0 if repeated else cursor)])
        async with adapter(handle, calls) as client:
            await client.sync_time()
            with pytest.raises(ExecutionUnknown if repeated else PaginationIncomplete):
                _ = [row async for row in client.iter_trades(
                    "BTCUSDT", order_id=100, limit=1, max_pages=2)]
    asyncio.run(scenario())
    asyncio.run(scenario(True))


def test_query_parameter_combinations_and_decimal_float_refused_before_network():
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(200, json=[]), calls) as client:
            with pytest.raises(ProtocolRejected):
                await client.trades_page("BTCUSDT", order_id=100, start_ms=0)
            with pytest.raises(ProtocolRejected):
                await client.all_orders_page("BTCUSDT", start_ms=0, end_ms=86_400_001)
            with pytest.raises(ProtocolRejected):
                await client.submit({**ORDER, "quantity": .01})
    asyncio.run(scenario())
    assert calls == []


def test_mutation_response_identity_mismatch_or_nonJSON_is_unknown():
    async def scenario(response):
        calls = []
        async with adapter(lambda _: response, calls) as client:
            await client.sync_time()
            with pytest.raises(ExecutionUnknown):
                await client.submit(ORDER)
        assert len(calls) == 2
    asyncio.run(scenario(httpx.Response(200, json=order_response(clientOrderId="different"))))
    asyncio.run(scenario(httpx.Response(200, text="invalid response")))


def test_timestamp_rejection_invalidates_sync_without_automatic_resend():
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(400, json={"code": -1021, "msg": "timestamp"}),
                           calls) as client:
            await client.sync_time()
            with pytest.raises(ProtocolRejected):
                await client.submit(ORDER)
            with pytest.raises(ClockNotReady):
                await client.submit(ORDER)
    asyncio.run(scenario())
    assert len(calls) == 2


def test_test_order_is_a_separate_signed_protocol_not_a_live_submit():
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(200, json={}), calls) as client:
            await client.sync_time()
            assert await client.validate_order(ORDER) == {}
    asyncio.run(scenario())
    assert calls[-1].method == "POST"
    assert calls[-1].url.path == "/api/v3/order/test"


def test_local_burst_limit_and_missing_credentials_prevent_HTTP():
    calls = []
    async def scenario():
        async with adapter(lambda _: httpx.Response(200, json=[]), calls) as client:
            for _ in range(40):
                await client.server_time()
            with pytest.raises(RateLimited):
                await client.server_time()
        async with SpotTestnetAdapter(transport=httpx.MockTransport(
            lambda _: pytest.fail("Unsigned account call reached HTTP"))) as missing:
            with pytest.raises(ProtocolRejected):
                await missing.balances()
    asyncio.run(scenario())
    assert len(calls) == 40


def test_missing_trade_time_cannot_be_used_for_reconciliation():
    calls = []
    row = trade(1)
    del row["time"]
    async def scenario():
        async with adapter(lambda _: httpx.Response(200, json=[row]), calls) as client:
            await client.sync_time()
            with pytest.raises(ExecutionUnknown):
                await client.trades("BTCUSDT", 100)
    asyncio.run(scenario())
