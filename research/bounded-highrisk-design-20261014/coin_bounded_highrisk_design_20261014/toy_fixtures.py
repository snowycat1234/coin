"""Generated downside, mark-gap, funding, capacity and finite-add fixtures.

The small fixture scheduler is NOT a historical NativeDailySimulator adapter.
It calls the unchanged account with original causal clock and shared capacity.
No fill is invented; the toy terminal convention is 60 charged real-minute
attempts, with residual inventory retained when those attempts cannot execute.
"""
from decimal import Decimal, ROUND_DOWN
from vendor_quant.execution_contract import ExecutionContractV2, MINUTE_US
from vendor_quant.perpetual_account import D, HALTS
from bounded_policy import (HighRiskToyAccount, CapitalGuard, FiniteAddsState,
                            ProgramBudget, ReservationBook, SYMBOLS)

ZERO = D("0")


def mark(account, event, price):
    prices = {s: D(str(price[s] if isinstance(price, dict) else price)) for s in SYMBOLS}
    return account.update_marks(event, {s: dict(price=p, close_us=event, available_us=event)
                                        for s, p in prices.items()})


def fresh(account_class=HighRiskToyAccount, config=None):
    account = account_class(config, symbols=SYMBOLS, closing_min_notional_exempt=True)
    mark(account, 0, 100)
    return account


def fill(account, symbol, side, quantity, *, event=MINUTE_US + 1, signal=0,
         fill_id=None, mid=100, prior_quote=10000000, reduce_only=False, guard=False):
    capacity = D(str(prior_quote)) * D(".001") / D(str(mid))
    executor = CapitalGuard(account) if guard else account
    return executor.execute_fill(symbol, side, D(str(quantity)), event, signal,
        fill_id or f"{symbol}:{event}:{side}", execution_mid_price=D(str(mid)),
        quote_available_us=event // MINUTE_US * MINUTE_US,
        available_quantity=capacity, reduce_only=reduce_only)


def terminal60(account, *, signal=2 * MINUTE_US, mid=100, prior_quote=10000000):
    """All outstanding inventory shares ONE per-symbol capacity each minute."""
    first_open = ExecutionContractV2().earliest_execution_us(signal)
    attempts = 0
    quantities_at_signal = {s: str(p.quantity) for s, p in account.positions.items()}
    for i in range(60):
        if account.status in HALTS:
            break
        open_us = first_open + i * MINUTE_US
        for symbol in SYMBOLS:
            q = account.positions[symbol].quantity
            if q:
                symbol_mid = mid[symbol] if isinstance(mid, dict) else mid
                fill(account, symbol, "SELL" if q > 0 else "BUY", abs(q),
                     event=open_us + 1, signal=signal, fill_id=f"TERMINAL:{symbol}:{i}",
                     mid=symbol_mid, prior_quote=prior_quote, reduce_only=True)
        mark(account, open_us + MINUTE_US, mid)
        attempts += 1
        if not any(p.quantity for p in account.positions.values()):
            break
    residual = {s: str(p.quantity) for s, p in account.positions.items() if p.quantity}
    return dict(signal_us=signal, first_attempt_open_us=first_open, actual_attempt_minutes=attempts,
                quantities_at_signal=quantities_at_signal, residual_quantities=residual,
                completion="INCOMPLETE_UNPAID_RESIDUAL" if residual else "COMPLETE_PAID_EXIT",
                native_scheduler_adapter_certified=False)


def generated_case(name):
    account = fresh()
    sides = ("BUY", "BUY", "BUY", "SELL", "SELL")
    for s, side in zip(SYMBOLS, sides):
        fill(account, s, side, 16, guard=True)
    before = account.summary()
    samples = [before["NAV"]]
    terminal = None
    if name == "BENIGN_PAID_TERMINAL":
        terminal = terminal60(account)
    elif name == "CORRELATED_ADVERSE_GAP":
        prices = dict(zip(SYMBOLS, (70, 70, 70, 130, 130)))
        mark(account, 2 * MINUTE_US, prices)
        samples.append(account.summary()["NAV"])
        terminal = terminal60(account, mid=prices, prior_quote=0)
    elif name == "FUNDING_DRAIN":
        # Generated extreme stress: real event signs, not a claimed fee forecast.
        for i in range(1, 6):
            event = (2 + i) * MINUTE_US
            for s, side in zip(SYMBOLS, sides):
                account.apply_funding(s, f"TOY:{i}:{s}", event,
                                      D(".03") if side == "BUY" else D("-.03"), 0)
            samples.append(account.summary()["NAV"])
    elif name == "SHORT_ISOLATED_LIQUIDATION_GAP":
        mark(account, 2 * MINUTE_US, {s: D("198.9") if side == "SELL" else D("100")
                                     for s, side in zip(SYMBOLS, sides)})
    elif name == "SHORT_ISOLATED_BANKRUPTCY_GAP":
        mark(account, 2 * MINUTE_US, {s: D("200") if side == "SELL" else D("100")
                                     for s, side in zip(SYMBOLS, sides)})
    elif name == "ZERO_LIQUIDITY_TERMINAL":
        terminal = terminal60(account, prior_quote=0)
    elif name == "LATE_PARTIAL_TERMINAL":
        terminal = terminal60(account, prior_quote=10000)
    else:
        raise ValueError("Fixed generated scenario name required")
    summary = account.summary()
    samples.append(summary["NAV"])
    peak = 10000.
    drawdown = 0.
    for nav in samples:
        peak = max(peak, nav)
        drawdown = max(drawdown, 1 - nav / peak)
    return dict(name=name, observations="GENERATED_TOY_NOT_MARKET",
                sampled_max_drawdown=drawdown, terminal=terminal,
                summary=summary,
                limitations="Endpoint-only toy drawdown; no path probability or annual return inference")


def generated_finite_program():
    """One generated shared-cash CSH-like sleeve plus four finite margin orders.

    The four non-BTC holdings are fixture inventory, not fitted CSH signals.
    The next add follows the ACTUAL quantity-weighted filled entry basis.
    """
    account = fresh()
    state, budget, book = FiniteAddsState(), ProgramBudget(), ReservationBook()
    book.reserve("CSH_SYNTHETIC_INTENTS", 8000)
    book.reserve(state.plan.owner, state.plan.total_sleeve_investment)
    for symbol in SYMBOLS[1:]:
        fill(account, symbol, "BUY", 19, guard=True)
    orders = []
    for i, planned_margin in enumerate(state.plan.margins()):
        signal = 0 if i == 0 else (2 * i) * MINUTE_US
        mid = D("100") if i == 0 else state.plan.trigger_price(account.positions["BTCUSDT"].entry_price)
        if i:
            mark(account, signal, {s: mid if s == "BTCUSDT" else D("100") for s in SYMBOLS})
        execution_price = mid * D("1.0008")
        requested = (planned_margin / execution_price).quantize(D(".00000001"), rounding=ROUND_DOWN)
        receipt = fill(account, "BTCUSDT", "BUY", requested, signal=signal,
                       event=signal + MINUTE_US + 1, mid=mid,
                       fill_id=f"FINITE:{i}", guard=True)
        if receipt["status"] != "FILLED":
            raise AssertionError("Generated complete finite add unexpectedly unfilled")
        trade = receipt["fills"][0]["decimal_strings"]
        actual_margin, fee = D(trade["margin_allocated"]), D(trade["fee_amount"])
        state.record_fill_receipt(account, f"FINITE:{i}", i)
        budget.record_cost_event(f"FINITE:{i}", actual_fee=fee)
        orders.append(dict(index=i, planned_order_margin=str(planned_margin),
                           actual_filled_margin=str(actual_margin), requested_quantity=str(requested),
                           trigger_or_initial_mid=str(mid), actual_fill_price=str(execution_price),
                           actual_weighted_entry_basis=str(account.positions["BTCUSDT"].entry_price)))
    return dict(name="FINITE_MARGIN_PROGRAM_SHARED_CASH", generated_only=True,
                complete_opening_orders=state.completed_opening_orders,
                next_order_margin=state.next_order_margin(), terminal_auto_triggered=state.terminal,
                remaining_initial_uncommitted_cash=str(book.available_initial_capital()),
                cost_funding_reserve_consumed=str(budget.consumed_fee_funding_reserve),
                cost_funding_reserve_cap=str(state.plan.cost_funding_reserve()),
                orders=orders, summary=account.summary(),
                candidate_backtest=False, original_csh_signals_used=False)
