"""Unchanged native methods on synthetic accounts, never historical wallets."""

from decimal import Decimal as D
from types import SimpleNamespace

import numpy as np
import pytest
import torch

from modules.temporal_two_expert.inputs import CORE5
from quant.bybit_isolated_account import BybitIsolatedAccount
from quant.perpetual_account import HALTS

from .native_contract import native_methods
from .proxy import _breached, _cost

MINUTE = 60_000_000
NativeDailySimulator = native_methods()


def marked_account(mid="120", *, short=False):
    account = BybitIsolatedAccount(symbols=CORE5)
    account.update_marks(0, {s: dict(price="100", close_us=0, available_us=0) for s in CORE5})
    for i, s in enumerate(CORE5):
        result = account.execute_fill(
            s,
            "SELL" if short else "BUY",
            "11.682",
            MINUTE + 1,
            0,
            f"OPEN:{i}",
            execution_mid_price="100",
            quote_available_us=MINUTE,
            available_quantity="100",
        )
        assert result["status"] == "FILLED"
    account.update_marks(
        2 * MINUTE,
        {s: dict(price=mid, close_us=2 * MINUTE, available_us=2 * MINUTE) for s in CORE5},
    )
    return account


def scheduler(account, *, capacity="0.02"):
    # Bind the actual frozen methods; no alternative execution engine.
    frame = SimpleNamespace(
        account=account,
        symbols=CORE5,
        terminal=False,
        pending={},
        breaches=[],
        rejections=[],
        sequence=0,
        mode="SYNTHETIC_TEST",
        cost={"id": "FROZEN_COST"},
        unit={"id": "CONDITIONAL_UNIT", "scale": 1},
        persist_cash_close=False,
        previous_quote={s: D(capacity) * account.marks[s][-1]["price"] / D(".001") for s in CORE5},
        first_entry=None,
        completion="ACTIVE",
        stop=None,
        observe=lambda *args: None,
        event_cursor=0,
        funding_journal=[],
    )
    frame.schedule = lambda *a, **kw: NativeDailySimulator.schedule(frame, *a, **kw)
    frame.risk_schedule = lambda *a, **kw: NativeDailySimulator.risk_schedule(frame, *a, **kw)
    return frame


def market(mid="120"):
    return {s: {"open": mid} for s in CORE5}


def test_native_signal_latency_frozen_intent_partial_cost_and_no_increase():
    account = marked_account()
    assert account.status == "BOUND_BREACH_REDUCTION_REQUIRED" and account.status not in HALTS
    frame = scheduler(account)
    frame.risk_schedule(2 * MINUTE)
    frozen = {s: o["target"] for s, o in frame.pending.items()}
    old = {s: account.positions[s].quantity for s in CORE5}
    n = np.array([float(abs(old[s]) * account.marks[s][-1]["price"]) for s in CORE5])
    scale = min(
        1, 0.99 * 0.3 * float(account.nav()) / n.max(), 0.99 * 0.6 * float(account.nav()) / n.sum()
    )
    np.testing.assert_allclose(
        [float(frozen[s] / old[s]) for s in CORE5], scale, atol=3e-16, rtol=0
    )
    count = len(account.trades)
    NativeDailySimulator.attempt(frame, 2 * MINUTE, market())
    assert len(account.trades) == count  # one minute latency, plus 1us
    before = float(account.nav())
    NativeDailySimulator.attempt(frame, 3 * MINUTE, market())
    fills = account.trades[count:]
    assert len(fills) == 5 and all(r["leg"] == "CLOSE" for r in fills)
    assert all(r["quantity"] == 0.02 for r in fills)
    assert all(o["attempts"] == 1 for o in frame.pending.values())
    assert {s: o["target"] for s, o in frame.pending.items()} == frozen
    expected = float(
        _cost(
            torch.full((5,), -0.02, dtype=torch.float64),
            torch.full((5,), 120.0, dtype=torch.float64),
        )[0]
    )
    assert before - float(account.nav()) == pytest.approx(expected, abs=2e-12)
    assert frame.breaches[0]["reduction_latency_us"] == MINUTE + 1
    frame.pending[CORE5[0]].update(target=old[CORE5[0]] + D(1), kind="DAILY_TARGET")
    NativeDailySimulator.attempt(frame, 4 * MINUTE, market())
    assert any(r["reason"] == "RISK_PRIORITY_NO_INCREASE" for r in frame.rejections)


def test_native_zero_capacity_expiry_stops_without_fake_fill():
    account = marked_account()
    frame = scheduler(account, capacity="0")
    frame.risk_schedule(2 * MINUTE)
    before, count = account.nav(), len(account.trades)
    for k in range(5):
        NativeDailySimulator.attempt(frame, (3 + k) * MINUTE, market())
    assert frame.completion == "NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION"
    assert account.nav() == before and len(account.trades) == count


def test_native_partial_expiry_inside_caps_does_not_demand_unfilled_buffer():
    account = marked_account()
    frame = scheduler(account)
    frame.risk_schedule(2 * MINUTE)
    target = {s: o["target"] for s, o in frame.pending.items()}
    for s in CORE5:
        amount = abs(account.positions[s].quantity - target[s]) * D(".18")
        frame.previous_quote[s] = amount * D(120) / D(".001")
    for k in range(5):
        NativeDailySimulator.attempt(frame, (3 + k) * MINUTE, market())
    assert account.status == "ACTIVE" and frame.stop is None and not frame.pending
    assert all(abs(account.positions[s].quantity) > abs(target[s]) for s in CORE5)
    assert any(r.get("reason") == "FIVE_ATTEMPTS_EXPIRED" for r in frame.rejections)


def test_native_funding_tie_owns_pre_reduction_quantity_and_strictly_past_mark():
    account = marked_account()
    frame = scheduler(account, capacity="10")
    frame.risk_schedule(2 * MINUTE)
    event = 3 * MINUTE
    frame.window = {"events": [dict(event_us=event, symbol=CORE5[0], raw_rate=0.001)]}
    held = account.positions[CORE5[0]].quantity
    NativeDailySimulator.funding_through(frame, event + 1, True)
    payment = frame.funding_journal[0]
    assert payment["quantity"] == float(held)
    assert payment["mark_close_us"] == 2 * MINUTE
    assert payment["signed_funding_USDT"] == pytest.approx(
        -float(held * D(120) * D(".001")), abs=1e-12
    )
    NativeDailySimulator.attempt(frame, event, market())
    assert account.positions[CORE5[0]].quantity < held
    assert frame.funding_journal[0]["quantity"] == float(held)


@pytest.mark.parametrize("short,mid", [(False, "120"), (True, "120")])
def test_native_completed_reduce_only_cost_matches_signed_surrogate(short, mid):
    account = marked_account(mid, short=short)
    assert account.status == "BOUND_BREACH_REDUCTION_REQUIRED"
    frame = scheduler(account, capacity="100")
    frame.risk_schedule(2 * MINUTE)
    before = account.nav()
    quantities = np.array([float(account.positions[s].quantity) for s in CORE5])
    count = len(account.trades)
    NativeDailySimulator.attempt(frame, 3 * MINUTE, market(mid))
    after = np.array([float(account.positions[s].quantity) for s in CORE5])
    expected = _cost(
        torch.tensor(after - quantities), torch.full((5,), float(mid), dtype=torch.float64)
    )[0]
    assert float(before - account.nav()) == pytest.approx(float(expected), abs=4e-12)
    assert len(account.trades[count:]) == 5
    assert all(r["leg"] == "CLOSE" for r in account.trades[count:])
    assert all(r["side"] == ("BUY" if short else "SELL") for r in account.trades[count:])
    assert not frame.pending and account.status == "ACTIVE"


def test_cap_equality_and_mark_tape_not_identifiable_from_daily_endpoints():
    equity = torch.tensor(10000.0, dtype=torch.float64)
    price = torch.full((5,), 100.0, dtype=torch.float64)
    equal = torch.full((5,), 12.0, dtype=torch.float64)
    assert not _breached(equal, price, equity)
    assert _breached(equal + 1e-8, price, equity)
    # Both can have the same 100->100 daily endpoint; intermediate 120 requires
    # orders whereas flat intraday marks do not. Daily endpoints omit this fact.
    flat, spike = marked_account("100"), marked_account("120")
    assert flat.status == "ACTIVE" and spike.status == "BOUND_BREACH_REDUCTION_REQUIRED"
    a, b = scheduler(flat), scheduler(spike)
    a.risk_schedule(2 * MINUTE)
    b.risk_schedule(2 * MINUTE)
    assert not a.pending and len(b.pending) == 5
