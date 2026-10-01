"""Synthetic execution incidents. None of these records are real trading evidence."""

import asyncio
import copy
import sqlite3
import tempfile
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from quant.execution import (
    AuditError,
    EvidenceError,
    ExecutionEngine,
    ExecutionError,
    ExecutionFrozen,
    GateDenied,
    NetworkGate,
    RiskContext,
    RiskLimits,
    RiskViolation,
    SymbolRules,
)
from quant.paths import STATE, utc_now_us


def rules(**changes):
    result = SymbolRules(
        "BTCUSDT",
        "BTC",
        "USDT",
        (
            {
                "filterType": "PRICE_FILTER",
                "minPrice": "1",
                "maxPrice": "1000000",
                "tickSize": "0.01",
            },
            {"filterType": "LOT_SIZE", "minQty": "0.00001", "maxQty": "100", "stepSize": "0.00001"},
            {
                "filterType": "MIN_NOTIONAL",
                "minNotional": "5",
                "applyToMarket": True,
                "avgPriceMins": 5,
            },
        ),
        utc_now_us() - 1_000_000,
    )
    return replace(result, **changes)


def context(**changes):
    now = utc_now_us()
    result = RiskContext(
        now,
        "9999",
        "10000",
        now,
        123,
        True,
        True,
        asset_marks={"BTC": "10000", "ETH": "1000"},
        marks_asof_us=now,
        estimated_annual_vol="0.08",
        volatility_asof_us=now // 60_000_000 * 60_000_000,
        previous_closed_quote_volume="1000000",
        previous_minute_open_us=now // 60_000_000 * 60_000_000 - 60_000_000,
        conservative_fee_bps="20",
        fee_asof_us=now,
        fee_source="synthetic_mock_account",
    )
    return replace(result, **changes)


def balances(usdt="1000", btc="0", bnb="1"):
    return {
        "USDT": {"free": usdt, "locked": "0"},
        "BTC": {"free": btc, "locked": "0"},
        "BNB": {"free": bnb, "locked": "0"},
    }


class Rejected(Exception):
    status_known_rejected = True
    code = -1013


class FakeAdapter:
    environment = "spot_testnet"
    network = False

    def __init__(self):
        self.posts = []
        self.cancels = []
        self.response = None
        self.submit_error = None
        self.cancel_error = None
        self.query_responses = []
        self.trade_rows = []
        self.account = balances()

    async def submit(self, order):
        self.posts.append(copy.deepcopy(order))
        if self.submit_error:
            raise self.submit_error
        return self.response or self.make_response(order["newClientOrderId"])

    @staticmethod
    def make_response(client_id, state="NEW", qty="0", quote="0", exchange_id=99):
        return {
            "symbol": "BTCUSDT",
            "clientOrderId": client_id,
            "orderId": exchange_id,
            "side": "BUY",
            "type": "LIMIT",
            "origQty": "0.001",
            "status": state,
            "executedQty": qty,
            "cummulativeQuoteQty": quote,
        }

    async def query(self, symbol, client_order_id):
        if self.query_responses:
            return self.query_responses.pop(0)
        return self.make_response(client_order_id)

    async def cancel(self, symbol, client_order_id):
        self.cancels.append(client_order_id)
        if self.cancel_error:
            raise self.cancel_error
        return self.response or self.make_response(client_order_id, "CANCELED")

    async def trades(self, symbol, exchange_order_id):
        return self.trade_rows

    async def balances(self):
        return self.account


def trade(qty="0.001", quote="10", fee="0.01", asset="USDT", trade_id=1, **changes):
    result = {
        "id": trade_id,
        "orderId": 99,
        "symbol": "BTCUSDT",
        "qty": qty,
        "quoteQty": quote,
        "price": "10000",
        "commission": fee,
        "commissionAsset": asset,
        "isBuyer": True,
        "time": utc_now_us() // 1000,
    }
    return {**result, **changes}


@pytest.fixture
def setup_engine():
    STATE.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="execution-test-", dir=STATE) as directory:
        adapter = FakeAdapter()
        path = Path(directory) / "execution.sqlite3"
        engine = ExecutionEngine(adapter, db_path=path, disk_check=lambda **_: {"status": "OK"})
        engine.bootstrap(balances())
        try:
            yield engine, adapter, path
        finally:
            engine.close()


def prepared(engine, intent="a", **changes):
    args = dict(
        symbol="BTCUSDT",
        side="BUY",
        quantity="0.001",
        price="10000",
        rules=rules(),
        context=context(),
    )
    return engine.prepare(intent, **{**args, **changes})


def submit(engine, client_id, **changes):
    return asyncio.run(engine.submit(client_id, rules=rules(), context=context(**changes)))


def test_timeout_not_found_then_filled_never_resends(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.submit_error = TimeoutError("response lost after matching")
    assert submit(engine, client_id)["state"] == "UNKNOWN"
    assert engine.status()["reserved"]["USDT"] == "10.020000"
    adapter.query_responses = [None]
    assert asyncio.run(engine.query(client_id))["state"] == "UNKNOWN"
    assert submit(engine, client_id)["state"] == "UNKNOWN"
    with pytest.raises(ExecutionFrozen):
        prepared(engine, "b")
    adapter.query_responses = [adapter.make_response(client_id, "FILLED", "0.001", "10")]
    adapter.trade_rows = [trade()]
    adapter.account = balances("989.99", "0.001")
    assert asyncio.run(engine.recover())["passed"]
    assert engine.order(client_id)["state"] == "FILLED"
    assert not engine.status()["frozen"]
    assert len(adapter.posts) == 1
    assert engine.apply_fills(client_id, adapter.trade_rows) == 0
    assert engine.reconcile(adapter.account)["passed"]
    assert engine.status()["balances"]["USDT"] == "989.99"
    assert submit(engine, client_id)["state"] == "FILLED"
    assert prepared(engine) == client_id
    assert len(adapter.posts) == 1


def test_restart_queries_active_orders_and_preserves_id(setup_engine):
    engine, adapter, path = setup_engine
    client_id = prepared(engine)
    assert submit(engine, client_id)["state"] == "NEW"
    engine.close()
    with ExecutionEngine(
        adapter, db_path=path, disk_check=lambda **_: {"status": "OK"}
    ) as restored:
        assert restored.order(client_id)["state"] == "UNKNOWN"
        assert submit(restored, client_id)["state"] == "UNKNOWN"
        assert asyncio.run(restored.recover())["passed"]
        assert restored.order(client_id)["state"] == "NEW"
        assert prepared(restored) == client_id
        assert len(adapter.posts) == 1


def test_single_writer_and_sqlite_wal_reader(setup_engine):
    engine, adapter, path = setup_engine
    with pytest.raises(ExecutionError, match="writer"):
        ExecutionEngine(adapter, db_path=path, disk_check=lambda **_: {"status": "OK"})
    reader = sqlite3.connect(path)
    try:
        prepared(engine)
        assert reader.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 1
        assert reader.execute("PRAGMA journal_mode").fetchone()[0] == "wal"
    finally:
        reader.close()


def test_audit_append_only_and_materialized_tamper_detected(setup_engine):
    engine, adapter, path = setup_engine
    client_id = prepared(engine)
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        engine.db.execute("DELETE FROM audit")
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        engine.db.execute("UPDATE audit SET event='altered'")
    engine.db.execute("UPDATE orders SET state='FILLED' WHERE client_id=?", (client_id,))
    with pytest.raises(AuditError):
        engine.verify_audit()
    engine.close()
    with pytest.raises(AuditError):
        ExecutionEngine(adapter, db_path=path, disk_check=lambda **_: {"status": "OK"})


def test_duplicate_intent_economics_and_global_id_uniqueness(setup_engine):
    engine, _, _ = setup_engine
    first = prepared(engine)
    assert prepared(engine) == first
    assert 1 <= len(first) <= 36
    with pytest.raises(RiskViolation, match="economics"):
        prepared(engine, quantity="0.002")
    assert prepared(engine, "b") != first
    asyncio.run(engine.cancel(first))
    assert engine.order(first)["state"] == "CANCELED"
    assert prepared(engine) == first


def test_clear_rejection_releases_reservation_but_duplicate_is_unknown(setup_engine):
    engine, adapter, _ = setup_engine
    first = prepared(engine)
    adapter.submit_error = Rejected()
    assert submit(engine, first)["state"] == "REJECTED"
    assert engine.status()["reserved"] == {}
    second = prepared(engine, "b")
    duplicate = Rejected()
    duplicate.code = -2010
    adapter.submit_error = duplicate
    assert submit(engine, second)["state"] == "UNKNOWN"
    assert len(adapter.posts) == 2


def test_cancel_partial_fill_race_and_late_final_fill(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    submit(engine, client_id)
    adapter.response = adapter.make_response(client_id, "CANCELED", "0.0004", "4")
    adapter.response["origClientOrderId"] = client_id
    adapter.response["clientOrderId"] = "cancel-generated-id"
    adapter.trade_rows = [trade("0.0004", "4", "0.004")]
    result = asyncio.run(engine.cancel(client_id))
    assert result["state"] == "CANCELED" and result["accounted_qty"] == "0.0004"
    assert result["reserve_remaining"] == "0"
    assert engine.reconcile(balances("995.996", "0.0004"))["passed"]
    adapter.query_responses = [adapter.make_response(client_id, "FILLED", "0.001", "10")]
    adapter.trade_rows.append(trade("0.0006", "6", "0.006", trade_id=2))
    assert asyncio.run(engine.query(client_id))["state"] == "FILLED"
    assert engine.reconcile(balances("989.990", "0.0010"))["passed"]
    assert len(adapter.cancels) == 1
    asyncio.run(engine.cancel(client_id))
    assert len(adapter.cancels) == 1


def test_cancel_rejection_does_not_reject_original_order(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    submit(engine, client_id)
    error = Rejected()
    error.code = -2011
    adapter.cancel_error = error
    assert asyncio.run(engine.cancel(client_id))["state"] == "UNKNOWN"
    assert engine.order(client_id)["reserve_remaining"] != "0"
    adapter.query_responses = [adapter.make_response(client_id, "FILLED", "0.001", "10")]
    adapter.trade_rows = [trade()]
    adapter.account = balances("989.99", "0.001")
    assert asyncio.run(engine.recover())["passed"]
    assert engine.order(client_id)["state"] == "FILLED"


@pytest.mark.parametrize(
    "asset,fee,expected_btc,expected_usdt,expected_bnb",
    [
        ("USDT", "0.01", "0.001", "989.99", "1"),
        ("BTC", "0.000001", "0.000999", "990", "1"),
        ("BNB", "0.00002", "0.001", "990", "0.99998"),
    ],
)
def test_commissions_all_assets_and_locked_total_reconciliation(
    setup_engine, asset, fee, expected_btc, expected_usdt, expected_bnb
):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "FILLED", "0.001", "10")
    adapter.trade_rows = [trade(asset=asset, fee=fee)]
    submit(engine, client_id)
    snapshot = balances(expected_usdt, expected_btc, expected_bnb)
    snapshot["USDT"] = {"free": str(Decimal(expected_usdt) - 50), "locked": "50"}
    assert engine.reconcile(snapshot)["passed"]
    assert engine.status()["balances"]["BNB"] == expected_bnb
    assert engine.status()["balances"]["BTC"] == expected_btc


def test_missing_trades_is_fill_debt_not_zero_commission(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "FILLED", "0.001", "10")
    submit(engine, client_id)
    assert engine.status()["fill_debt_orders"] == 1
    assert not engine.reconcile(balances())["passed"]
    with pytest.raises(ExecutionFrozen):
        prepared(engine, "b")


def test_conflicting_duplicate_fill_rolls_back_and_freezes(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "FILLED", "0.001", "10")
    adapter.trade_rows = [trade()]
    submit(engine, client_id)
    before = engine.status()["balances"]
    with pytest.raises(EvidenceError):
        engine.apply_fills(client_id, [trade(fee="0.02")])
    assert engine.status()["balances"] == before
    assert "FILL_CONFLICT" in engine.status()["freeze_reasons"]
    assert engine.verify_audit()


def test_unknown_commission_asset_fails_without_invented_balance(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "FILLED", "0.001", "10")
    adapter.trade_rows = [trade(asset="XYZ", fee="1")]
    submit(engine, client_id)
    assert "FILL_CONFLICT" in engine.status()["freeze_reasons"]
    assert engine.status()["balances"] == {"USDT": "1000", "BTC": "0", "BNB": "1"}


def test_balance_mismatch_sticky_and_no_auto_rebaseline(setup_engine):
    engine, _, _ = setup_engine
    assert not engine.reconcile(balances("999"))["passed"]
    assert engine.status()["balances"]["USDT"] == "1000"
    assert engine.reconcile(balances())["passed"]
    assert engine.status()["frozen"]
    with pytest.raises(ExecutionFrozen):
        engine.acknowledge_incident("BALANCE_MISMATCH", evidence="cash transfer accounted")
    engine.acknowledge_incident(
        "BALANCE_MISMATCH", evidence="false snapshot corrected", approved=True
    )
    assert not engine.status()["frozen"]


@pytest.mark.parametrize(
    "change",
    [
        {"healthy": False},
        {"disk_ok": False},
        {"quote_received_us": 1},
        {"bid": "10001"},
        {"ask": "11000"},
        {"quote_update_id": -1},
        {"asset_marks": {}},
        {"marks_asof_us": 1},
        {"estimated_annual_vol": None},
        {"estimated_annual_vol": "0.10001"},
        {"previous_closed_quote_volume": None},
        {"previous_minute_open_us": 1},
        {"previous_closed_quote_volume": "9999"},
        {"conservative_fee_bps": None},
        {"conservative_fee_bps": "20.0001"},
        {"fee_asof_us": 1},
        {"fee_source": None},
    ],
)
def test_missing_or_excessive_risk_evidence_denied(setup_engine, change):
    engine, adapter, _ = setup_engine
    with pytest.raises(RiskViolation):
        prepared(engine, context=context(**change))
    assert not adapter.posts and not engine.orders()


@pytest.mark.parametrize(
    "quantity,price",
    [("0.001001", "10000"), ("0.001", "10000.001"), ("0.00001", "10000"), ("0.02", "10000")],
)
def test_lot_price_notional_and_absolute_cap(setup_engine, quantity, price):
    engine, _, _ = setup_engine
    with pytest.raises(RiskViolation):
        prepared(engine, quantity=quantity, price=price)


def test_pre_submit_risk_rechecked(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    with pytest.raises(RiskViolation):
        submit(engine, client_id, healthy=False)
    assert engine.order(client_id)["state"] == "PREPARED"
    assert not adapter.posts


def test_minute_capacity_includes_all_reservations_and_actual_fills(setup_engine):
    engine, adapter, _ = setup_engine
    first = prepared(engine, context=context(previous_closed_quote_volume="15000"))
    with pytest.raises(RiskViolation, match="capacity"):
        prepared(engine, "b", context=context(previous_closed_quote_volume="15000"))
    adapter.response = adapter.make_response(first, "FILLED", "0.001", "10")
    adapter.trade_rows = [trade()]
    submit(engine, first)
    engine.reconcile(balances("989.99", "0.001"))
    with pytest.raises(RiskViolation, match="capacity"):
        prepared(engine, "c", context=context(previous_closed_quote_volume="15000"))


def test_potential_inventory_cap_counts_pending_buys_and_keeps_pending_sells(setup_engine):
    engine, _, _ = setup_engine
    # Total NAV1000, holding29.5% BTC; adding10 USDT breaches30% after fees.
    engine.close()
    path = engine.db_path.with_name("inventory.sqlite3")
    with ExecutionEngine(
        FakeAdapter(), db_path=path, disk_check=lambda **_: {"status": "OK"}
    ) as other:
        other.bootstrap(balances("705", "0.0295"))
        prepared(other, "sell", side="SELL")
        with pytest.raises(RiskViolation, match="30 percent"):
            prepared(other, "buy")


def test_frozen_risk_caps_cannot_be_relaxed():
    for change in (
        {"single_asset_weight": "0.31"},
        {"gross_weight": "0.61"},
        {"estimated_annual_vol_cap": "0.11"},
        {"minute_volume_fraction": "0.002"},
    ):
        with pytest.raises(RiskViolation):
            RiskLimits(**change)


def test_market_filters_require_actual_reference_and_unsupported_filters_deny(setup_engine):
    engine, _, _ = setup_engine
    with pytest.raises(RiskViolation, match="reference"):
        prepared(engine, order_type="MARKET", price=None)
    now = utc_now_us()
    prepared(
        engine,
        "market",
        order_type="MARKET",
        price=None,
        context=context(reference_prices={5: "10000"}, reference_asof_us=now),
    )
    with pytest.raises(RiskViolation, match="Unsupported"):
        prepared(
            engine,
            "new-filter",
            rules=rules(filters=rules().filters + ({"filterType": "MAX_ASSET", "limit": "1"},)),
        )


def test_network_default_gate_mainnet_and_engineering_opt_out_denied(setup_engine):
    engine, adapter, _ = setup_engine
    adapter.network = True
    with pytest.raises(GateDenied):
        prepared(engine)
    assert not adapter.posts
    adapter.network = False
    adapter.environment = "mainnet"
    with pytest.raises(GateDenied):
        prepared(engine)
    adapter.environment = "spot_testnet"
    prepared(engine, context=context(portfolio_checks=False, estimated_annual_vol=None))
    adapter.network = True
    engine.gate = NetworkGate(
        True,
        True,
        True,
        True,
        True,
        True,
        {key: "a" * 64 for key in ("candidate", "real_72h", "real_180d", "resources")},
    )
    with pytest.raises(RiskViolation, match="cannot be waived"):
        prepared(
            engine, "b", context=context(portfolio_checks=False, fee_source="venue_commission")
        )


def test_locked_funds_cannot_be_spent_and_reserve_does_not_increase_balance(setup_engine):
    engine, _, _ = setup_engine
    engine.reconcile(
        {
            "USDT": {"free": "1", "locked": "999"},
            "BTC": {"free": "0", "locked": "0"},
            "BNB": {"free": "1", "locked": "0"},
        }
    )
    with pytest.raises(RiskViolation, match="Venue free"):
        prepared(engine)
    assert engine.status()["balances"]["USDT"] == "1000"


def test_disk_failure_freezes_before_dispatch(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)

    def failed(**_):
        raise RuntimeError("synthetic disk capacity failure")

    engine._disk_check = failed
    with pytest.raises(ExecutionFrozen, match="Disk"):
        submit(engine, client_id)
    assert not adapter.posts
    assert "DISK_GUARD" in engine.status()["freeze_reasons"]


def test_task_cancellation_during_send_is_durable_unknown(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.submit_error = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        submit(engine, client_id)
    assert engine.order(client_id)["state"] == "UNKNOWN"
    assert len(adapter.posts) == 1


def test_testnet_reset_requires_multiple_missing_orders_and_explicit_new_generation(setup_engine):
    engine, adapter, _ = setup_engine
    first = prepared(engine)
    submit(engine, first)
    second = prepared(engine, "b")
    adapter.response = adapter.make_response(second, exchange_id=100)
    submit(engine, second)
    with pytest.raises(EvidenceError):
        asyncio.run(engine.detect_reset(client_ids=[first]))
    adapter.query_responses = [None, None]
    adapter.account = balances("2000")
    result = asyncio.run(engine.detect_reset(client_ids=[first, second]))
    assert result["suspected"] and not result["confirmed"]
    with pytest.raises(ExecutionFrozen):
        engine.acknowledge_reset(adapter.account, evidence="reset documentation")
    assert engine.acknowledge_reset(adapter.account, evidence="reviewed reset", approved=True) == 1
    assert engine.order(first)["state"] == "RESET_INVALIDATED"
    assert engine.status()["balances"]["USDT"] == "2000"
    assert not engine.status()["frozen"]
    assert prepared(engine, "c") not in {first, second}
    with pytest.raises(EvidenceError):
        engine.apply_fills(first, [trade()])


def test_stale_query_cannot_regress_fills(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "FILLED", "0.001", "10")
    adapter.trade_rows = [trade()]
    submit(engine, client_id)
    adapter.query_responses = [adapter.make_response(client_id)]
    assert asyncio.run(engine.query(client_id))["state"] == "FILLED"
    assert engine.order(client_id)["executed_qty"] == "0.001"
    engine.verify_audit()


def test_native_state_path_enforced():
    with pytest.raises(ExecutionError, match="native"):
        ExecutionEngine(FakeAdapter(), db_path=Path("/mnt/d/codex/coin/state/unsafe.sqlite3"))


def test_wrong_distro_refused(monkeypatch):
    monkeypatch.setenv("WSL_DISTRO_NAME", "Ubuntu-on-C")
    with pytest.raises(ExecutionError, match="hpc_linux"):
        ExecutionEngine(FakeAdapter())


def test_stp_expired_in_match_is_confirmed_terminal_with_partial_fill(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "EXPIRED_IN_MATCH", "0.0004", "4")
    adapter.trade_rows = [trade("0.0004", "4", "0.004")]
    result = submit(engine, client_id)
    assert result["state"] == "EXPIRED" and result["reserve_remaining"] == "0"
    assert result["accounted_qty"] == "0.0004"
    assert engine.reconcile(balances("995.996", "0.0004"))["passed"]
    assert not engine.status()["frozen"]


def test_query_lags_trades_freezes_then_recovers_without_fee_conflict(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "PARTIALLY_FILLED", "0.0004", "4")
    adapter.trade_rows = [trade()]
    submit(engine, client_id)
    assert engine.status()["frozen"]
    assert "FILL_CONFLICT" not in engine.status()["freeze_reasons"]
    assert engine.status()["balances"]["USDT"] == "1000"
    adapter.query_responses = [adapter.make_response(client_id, "FILLED", "0.001", "10")]
    adapter.account = balances("989.99", "0.001")
    assert asyncio.run(engine.recover())["passed"]
    assert not engine.status()["frozen"]


def test_shared_vhd_growth_does_not_consume_local_writer_allowance(setup_engine):
    engine, _, _ = setup_engine
    engine._disk_check = None
    engine._ledger["total_bytes"] = 1_000_000_000
    engine._vhd_bytes -= 200_000_000
    # A concurrent job used200 MB of the shared VHD, while this DB stayed small.
    client_id = prepared(engine)
    assert engine.order(client_id)["state"] == "PREPARED"
    assert not engine.status()["frozen"]


def test_expired_disk_ledger_and_failed_refresh_fail_closed(setup_engine):
    engine, _, _ = setup_engine
    engine._disk_check = None
    engine._ledger["total_bytes"] = 1_000_000_000
    engine._ledger_mono -= 901
    with pytest.raises(ExecutionFrozen, match="Disk"):
        prepared(engine)
    assert engine.status()["frozen"]


def test_sell_cash_asset_and_eth_fee_accounting(setup_engine):
    engine, adapter, _ = setup_engine
    snapshot = balances("900", "0.01")
    snapshot["ETH"] = {"free": "0.05", "locked": "0"}
    path = engine.db_path.with_name("sell.sqlite3")
    with ExecutionEngine(adapter, db_path=path, disk_check=lambda **_: {"status": "OK"}) as seller:
        seller.bootstrap(snapshot)
        client_id = prepared(seller, side="SELL")
        adapter.response = adapter.make_response(client_id, "FILLED", "0.001", "10")
        adapter.response["side"] = "SELL"
        adapter.trade_rows = [trade(asset="ETH", fee="0.00001", isBuyer=False)]
        submit(seller, client_id)
        expected = balances("910", "0.009")
        expected["ETH"] = {"free": "0.04999", "locked": "0"}
        assert seller.reconcile(expected)["passed"]
        assert seller.status()["balances"]["ETH"] == "0.04999"


def test_pending_buy_worst_case_and_nav_fee_deduction(setup_engine):
    engine, adapter, _ = setup_engine
    path = engine.db_path.with_name("pending.sqlite3")
    with ExecutionEngine(
        adapter,
        db_path=path,
        disk_check=lambda **_: {"status": "OK"},
        limits=RiskLimits(max_order_notional="300"),
    ) as buyer:
        buyer.bootstrap(balances("1000"))
        prepared(buyer, "first", quantity="0.015")
        with pytest.raises(RiskViolation, match="30 percent"):
            prepared(buyer, "second", quantity="0.015")


def test_filters_percent_caps_market_lot_and_stale_metadata(setup_engine):
    engine, _, _ = setup_engine
    with pytest.raises(RiskViolation, match="expired"):
        prepared(engine, rules=rules(asof_us=1))
    extra = {
        "filterType": "PERCENT_PRICE",
        "multiplierDown": "0.99",
        "multiplierUp": "1.01",
        "avgPriceMins": 5,
    }
    with pytest.raises(RiskViolation, match="reference"):
        prepared(engine, rules=rules(filters=rules().filters + (extra,)))
    with pytest.raises(RiskViolation, match="Percent"):
        prepared(
            engine,
            rules=rules(filters=rules().filters + (extra,)),
            context=context(reference_prices={5: "11000"}, reference_asof_us=utc_now_us() - 1000),
        )
    cap = {"filterType": "MAX_NUM_ORDERS", "maxNumOrders": 1}
    with pytest.raises(RiskViolation, match="count"):
        prepared(engine, rules=rules(filters=rules().filters + (cap,)))
    with pytest.raises(RiskViolation, match="cap"):
        prepared(
            engine,
            rules=rules(filters=rules().filters + (cap,)),
            context=context(venue_symbol_open_orders=1),
        )
    lot = {"filterType": "MARKET_LOT_SIZE", "minQty": "0.01", "maxQty": "1", "stepSize": "0.001"}
    with pytest.raises(RiskViolation, match="MARKET_LOT_SIZE"):
        prepared(
            engine,
            order_type="MARKET",
            price=None,
            rules=rules(filters=rules().filters + (lot,)),
            context=context(reference_prices={5: "10000"}, reference_asof_us=utc_now_us() - 1000),
        )


def test_malformed_and_unavailable_cumulative_results_are_unknown(setup_engine):
    engine, adapter, _ = setup_engine
    client_id = prepared(engine)
    adapter.response = adapter.make_response(client_id, "FILLED", "0.001", "-1")
    assert submit(engine, client_id)["state"] == "UNKNOWN"
    assert engine.status()["reserved"]["USDT"] != "0"
    assert len(adapter.posts) == 1


def test_snapshot_reconciliation_does_not_double_deduct_existing_venue_locks(setup_engine):
    engine, adapter, _ = setup_engine
    first = prepared(engine)
    submit(engine, first)
    snapshot = balances()
    snapshot["USDT"] = {"free": "990", "locked": "10"}
    assert engine.reconcile(snapshot)["passed"]
    second = prepared(engine, "second")
    assert engine.order(second)["state"] == "PREPARED"
    assert engine.status()["balances"]["USDT"] == "1000"
    assert Decimal(engine.status()["reserved"]["USDT"]) == Decimal("20.04")
