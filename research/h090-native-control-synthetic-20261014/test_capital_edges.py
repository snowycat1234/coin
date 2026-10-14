"""Generated-only exact capital boundaries and reviewed charged-cost arithmetic.

All inventory, fees, funding and cash states below are produced by the copied,
reviewed Decimal account, using generated scalar marks and quotes. No history,
network, credentials, live account, publication or recovery claim is involved.
The facade's native-risk callback is deliberately pure-allow ONLY in these
standalone capital tests. Native controller admission is tested separately.

``CASH_TICK`` is an explicitly chosen 1e-8 USDT comparison increment, not an
exchange-certified cash filter. ``quantity_step`` is the reviewed, uncertified
research profile. Exact one-quantity-tick charged margin/cash deltas are also
checked. No balance or position is manually seeded.
"""
from copy import deepcopy
from dataclasses import fields
from decimal import Decimal as D, localcontext
import unittest

from cost_factory import (
    COSTS, POLICY, h090_account_for_cost, h090_config_from_original,
)


BASE27 = dict(id="BASE27", half_spread_bps=4, slippage_bps=4,
              roundtrip_bps=27)
STRESS43 = dict(id="STRESS43", half_spread_bps=8, slippage_bps=8,
                roundtrip_bps=43)
SCENARIOS = (BASE27, STRESS43)
ZERO = D("0")
CASH_TICK = D(".00000001")
FIRST_FILL_US = 60_000_001


def exact(row, name):
    """Assertions consume reviewed exact journal strings, never JSON floats."""
    return D(row["decimal_strings"][name])


def generated_account(cost=BASE27, *, allow_capital_only=True):
    account = h090_account_for_cost(cost)
    if allow_capital_only:
        # Intentional isolation of the capital gate, not native admission proof.
        account.risk_admission = lambda args, kwargs: {
            "allow_increases": True,
            "reason": "GENERATED_STANDALONE_CAPITAL_TEST_PURE_ALLOW",
        }
    account.update_marks(0, {
        symbol: dict(price="100", close_us=0, available_us=0)
        for symbol in POLICY.SYMBOLS
    })
    return account


def request(symbol, side, quantity, fill_id, event_us=FIRST_FILL_US,
            *, reduce_only=False, **changes):
    result = dict(symbol=symbol, side=side, quantity=quantity,
                  event_us=event_us, signal_us=0, fill_id=fill_id,
                  execution_mid_price="100", quote_available_us=0,
                  reduce_only=reduce_only)
    result.update(changes)
    return result


def account_probe(account, fill_request):
    """Use the exact reviewed engine to establish the unconstrained outcome."""
    probe = deepcopy(account.engine, {
        id(account.instrument_profiles): account.instrument_profiles,
    })
    return probe, probe.execute_fill(**fill_request)


def margin(account):
    with localcontext() as ctx:
        ctx.prec = 40
        return sum((p.isolated_balance for p in account.positions.values()), ZERO)


def lawful_margin_prefix(test, cost=BASE27):
    """First three real fills of a four-position, 8500-margin program.

    Equal BUY/SELL midpoint notionals make the final total exactly 8500 under
    both reviewed symmetric-friction scenarios, with every asset below .30 NAV.
    """
    account = generated_account(cost)
    for index, (symbol, side, quantity) in enumerate((
        ("BTCUSDT", "BUY", "25"),
        ("ETHUSDT", "SELL", "25"),
        ("SOLUSDT", "BUY", "17.5"),
    )):
        receipt = account.execute_fill(**request(
            symbol, side, quantity, f"margin-prefix-{index}",
            FIRST_FILL_US + index,
        ))
        test.assertEqual(receipt["status"], "FILLED")
        test.assertEqual(receipt["fills"][0]["leg"], "OPEN")
    return account


def lawful_cash_floor_prefix(test, cost=BASE27, *, extra_funding_debit=ZERO):
    """Lawful charged fills and one actual funding debit, without seeded cash.

    Four alternating 20-unit positions use exactly 8000 isolated USDT. BTC's
    2000 midpoint notional makes the required Decimal funding rate terminate
    exactly. A subsequent one-unit DOGE BUY leaves precisely 1000 free USDT.
    This caller-declared generated funding rate is no market-data assertion.
    """
    account = generated_account(cost)
    for index, (symbol, side) in enumerate(zip(
            POLICY.SYMBOLS[:4], ("BUY", "SELL", "BUY", "SELL"))):
        receipt = account.execute_fill(**request(
            symbol, side, "20", f"cash-prefix-{index}",
            FIRST_FILL_US + index,
        ))
        test.assertEqual(receipt["status"], "FILLED")
    test.assertEqual(margin(account), D("8000"))
    next_request = request("DOGEUSDT", "BUY", "1", "cash-boundary",
                           FIRST_FILL_US + 5)
    probe, preview = account_probe(account, next_request)
    test.assertEqual(preview["status"], "FILLED")
    charged_cash = -exact(preview["fills"][0], "free_cash_delta")
    with localcontext() as ctx:
        ctx.prec = 40
        target_before = D("1000") + charged_cash - extra_funding_debit
        debit = account.free_cash - target_before
        rate = debit / D("2000")
    test.assertGreater(debit, ZERO)
    funding = account.apply_funding(
        "BTCUSDT", "cash-floor-funding", FIRST_FILL_US + 4, rate, 0,
    )
    test.assertEqual(exact(funding, "signed_funding_USDT"), -debit)
    test.assertEqual(account.free_cash, target_before)
    test.assertEqual(account.status, "ACTIVE")
    return account, next_request


class ReservationBoundaryChecks(unittest.TestCase):
    def test_reservation_exact_9000_and_one_cash_tick_above(self):
        book = POLICY.ReservationBook()
        book.reserve("generated-full-program", D("9000"))
        self.assertEqual(book.reservations, {"generated-full-program": D("9000")})
        self.assertEqual(book.available_initial_capital(), D("1000"))
        before = deepcopy(vars(book))
        with self.assertRaisesRegex(ValueError, "committed capital cap exceeded"):
            book.reserve("generated-extra-program", CASH_TICK)
        self.assertEqual(vars(book), before)

        fresh = POLICY.ReservationBook()
        before = deepcopy(vars(fresh))
        with self.assertRaisesRegex(ValueError, "committed capital cap exceeded"):
            fresh.reserve("generated-over-budget", D("9000") + CASH_TICK)
        self.assertEqual(vars(fresh), before)

    def test_shared_reservation_sum_accepts_last_tick_and_retirement_does_not_reuse(self):
        book = POLICY.ReservationBook()
        book.reserve("generated-first", D("9000") - CASH_TICK)
        book.reserve("generated-last-tick", CASH_TICK)
        self.assertEqual(book.available_initial_capital(), D("1000"))
        book.release("generated-first", actual_quantity=ZERO, pending_increase_count=0)
        self.assertEqual(book.available_initial_capital(), D("1000"))
        before = deepcopy(vars(book))
        with self.assertRaisesRegex(ValueError, "committed capital cap exceeded"):
            book.reserve("generated-new-owner", CASH_TICK)
        self.assertEqual(vars(book), before)

    def test_planning_reservations_never_fund_or_mutate_the_account(self):
        account = generated_account()
        before = account.snapshot()
        book = POLICY.ReservationBook()
        book.reserve("generated-program", "9000")
        book.release("generated-program", actual_quantity=ZERO, pending_increase_count=0)
        self.assertEqual(account.snapshot(), before)
        self.assertEqual(account.free_cash, D("10000"))


class CapitalBoundaryChecks(unittest.TestCase):
    def test_standalone_factory_requires_native_binding_unless_explicitly_isolated(self):
        account = generated_account(allow_capital_only=False)
        before = account.snapshot()
        self.assertEqual(account.execute_fill(**request(
            "BTCUSDT", "BUY", "1", "unbound-increase")), {
                "status": "POLICY_REJECTED",
                "reason": "NATIVE_H090_RISK_BINDING_REQUIRED",
            })
        self.assertEqual(account.snapshot(), before)

    def test_actual_margin_exact_8500_is_committed_with_exact_charged_fills(self):
        for cost in SCENARIOS:
            with self.subTest(cost=cost["id"]):
                account = lawful_margin_prefix(self, cost)
                fill_request = request("XRPUSDT", "SELL", "17.5", "margin-boundary",
                                       FIRST_FILL_US + 3)
                probe, preview = account_probe(account, fill_request)
                self.assertEqual(preview["status"], "FILLED")
                self.assertEqual(margin(probe), D("8500"))
                self.assertGreater(probe.free_cash, D("1000"))
                self.assertEqual(account.execute_fill(**fill_request), preview)
                self.assertEqual(account.snapshot(), probe.snapshot())
                self.assertEqual(margin(account), D("8500"))
                self.assertEqual(account.free_cash, D("1495.325"))
                self.assertEqual(sum((exact(row, "margin_allocated")
                                      for row in account.trades), ZERO), D("8500"))
                self.assertEqual(account.fees, D("4.675"))

    def test_margin_8500_plus_one_quantity_tick_preview_rejects_without_any_mutation(self):
        for cost in SCENARIOS:
            with self.subTest(cost=cost["id"]):
                account = lawful_margin_prefix(self, cost)
                step = account.instrument_profiles["XRPUSDT"].quantity_step
                fill_request = request("XRPUSDT", "SELL", D("17.5") + step,
                                       "margin-one-tick-over", FIRST_FILL_US + 3)
                probe, preview = account_probe(account, fill_request)
                self.assertEqual(preview["status"], "FILLED")
                one_charged_margin_tick = step * exact(preview["fills"][0], "fill_price")
                self.assertEqual(margin(probe), D("8500") + one_charged_margin_tick)
                self.assertGreater(probe.free_cash, D("1000"))
                before = account.snapshot()
                self.assertEqual(account.execute_fill(**fill_request), {
                    "status": "POLICY_REJECTED", "reason": "SHARED_CAPITAL_OR_RESERVE_CAP",
                })
                self.assertEqual(account.snapshot(), before)
                self.assertNotIn(fill_request["fill_id"], account.fill_requests)

    def test_post_fill_cash_exact_1000_is_committed(self):
        for cost in SCENARIOS:
            with self.subTest(cost=cost["id"]):
                account, fill_request = lawful_cash_floor_prefix(self, cost)
                probe, preview = account_probe(account, fill_request)
                self.assertEqual(preview["status"], "FILLED")
                self.assertEqual(probe.free_cash, D("1000"))
                self.assertLess(margin(probe), D("8500"))
                self.assertEqual(account.execute_fill(**fill_request), preview)
                self.assertEqual(account.snapshot(), probe.snapshot())
                self.assertEqual(account.free_cash, D("1000"))

    def test_post_fill_cash_1000_minus_one_cash_tick_rejects_without_any_mutation(self):
        for cost in SCENARIOS:
            with self.subTest(cost=cost["id"]):
                account, fill_request = lawful_cash_floor_prefix(
                    self, cost, extra_funding_debit=CASH_TICK)
                probe, preview = account_probe(account, fill_request)
                self.assertEqual(preview["status"], "FILLED")
                self.assertEqual(probe.free_cash, D("1000") - CASH_TICK)
                self.assertLess(margin(probe), D("8500"))
                before = account.snapshot()
                self.assertEqual(account.execute_fill(**fill_request), {
                    "status": "POLICY_REJECTED", "reason": "SHARED_CAPITAL_OR_RESERVE_CAP",
                })
                self.assertEqual(account.snapshot(), before)

    def test_post_fill_cash_one_quantity_tick_includes_fee_in_exact_boundary(self):
        for cost in SCENARIOS:
            with self.subTest(cost=cost["id"]):
                account, fill_request = lawful_cash_floor_prefix(self, cost)
                step = account.instrument_profiles["DOGEUSDT"].quantity_step
                fill_request["quantity"] = D("1") + step
                probe, preview = account_probe(account, fill_request)
                self.assertEqual(preview["status"], "FILLED")
                with localcontext() as ctx:
                    ctx.prec = 40
                    charged_cash_tick = (step * exact(preview["fills"][0], "fill_price")
                                         * (D("1") + account.config.fee_rate))
                self.assertEqual(probe.free_cash, D("1000") - charged_cash_tick)
                before = account.snapshot()
                self.assertEqual(account.execute_fill(**fill_request)["status"], "POLICY_REJECTED")
                self.assertEqual(account.snapshot(), before)

    def test_exception_in_engine_preview_does_not_mutate_live_account(self):
        account = generated_account()
        before = account.snapshot()
        malformed = request("BTCUSDT", "BUY", "1", "too-early-preview", event_us=60_000_000)
        with self.assertRaisesRegex(ValueError, "execution latency"):
            account.execute_fill(**malformed)
        self.assertEqual(account.snapshot(), before)

    def test_reductions_remain_allowed_after_lawful_funding_crosses_cash_floor(self):
        account, boundary_request = lawful_cash_floor_prefix(self)
        self.assertEqual(account.execute_fill(**boundary_request)["status"], "FILLED")
        debit_event = FIRST_FILL_US + 6
        funding = account.apply_funding("BTCUSDT", "below-floor-funding", debit_event,
                                        CASH_TICK / D("2000"), 0)
        self.assertEqual(exact(funding, "signed_funding_USDT"), -CASH_TICK)
        self.assertEqual(account.free_cash, D("1000") - CASH_TICK)
        before = account.snapshot()
        increasing = request("DOGEUSDT", "BUY", ".1", "below-floor-increase", debit_event + 1)
        self.assertEqual(account.execute_fill(**increasing), {
            "status": "POLICY_REJECTED", "reason": "INITIAL_CASH_FLOOR_BREACHED",
        })
        self.assertEqual(account.snapshot(), before)

        def no_increase_admission(args, kwargs):
            raise AssertionError("Reduce-only must bypass increase admission")
        account.risk_admission = no_increase_admission
        # A one-quantity-tick reduction is below the opening minimum notional;
        # it still releases only its own actual remaining isolated collateral.
        step = account.instrument_profiles["DOGEUSDT"].quantity_step
        reduction = request("DOGEUSDT", "SELL", step, "below-floor-reduction",
                            debit_event + 1, reduce_only=True)
        before_quantity = account.positions["DOGEUSDT"].quantity
        before_margin = account.positions["DOGEUSDT"].isolated_balance
        probe, preview = account_probe(account, reduction)
        receipt = account.execute_fill(**reduction)
        self.assertEqual(receipt, preview)
        self.assertEqual(receipt["status"], "FILLED")
        self.assertEqual(receipt["fills"][0]["leg"], "CLOSE")
        self.assertLess(step * exact(receipt["fills"][0], "fill_price"), D("10"))
        self.assertEqual(exact(receipt["fills"][0], "margin_released"),
                         before_margin * step / before_quantity)
        self.assertEqual(account.positions["DOGEUSDT"].quantity, before_quantity - step)
        self.assertEqual(account.snapshot(), probe.snapshot())

    def test_duplicate_replay_precedes_current_native_and_capital_guards(self):
        account, fill_request = lawful_cash_floor_prefix(self)
        receipt = account.execute_fill(**fill_request)
        account.apply_funding("BTCUSDT", "replay-below-floor", FIRST_FILL_US + 6,
                              CASH_TICK / D("2000"), 0)
        self.assertLess(account.free_cash, D("1000"))

        def forbidden_current_admission(args, kwargs):
            raise AssertionError("Known receipt replay must precede native admission")
        account.risk_admission = forbidden_current_admission
        before = account.snapshot()
        self.assertEqual(account.execute_fill(**fill_request), receipt)
        # Exercise the unchanged reviewed CapitalGuard itself as well: the
        # facade intentionally routes known IDs straight to the reviewed engine.
        self.assertEqual(account.capital_guard.execute_fill(**fill_request), receipt)
        self.assertEqual(account.snapshot(), before)
        # Returned replays are defensive copies, never mutable journal aliases.
        replay = account.execute_fill(**fill_request)
        replay["fills"].clear()
        self.assertEqual(account.execute_fill(**fill_request), receipt)
        conflicting = dict(fill_request, quantity=D("1.00000001"))
        with self.assertRaisesRegex(ValueError, "conflicting fill identity"):
            account.execute_fill(**conflicting)
        with self.assertRaisesRegex(ValueError, "conflicting fill identity"):
            account.capital_guard.execute_fill(**conflicting)
        self.assertEqual(account.snapshot(), before)


class ExactCostAndFundingChecks(unittest.TestCase):
    def test_config_conversion_changes_only_original_gross_cap(self):
        for cost in SCENARIOS:
            with self.subTest(cost=cost["id"]):
                original = COSTS.scenario_config(cost)
                converted = h090_config_from_original(original, cost)
                changed = [field.name for field in fields(original)
                           if getattr(original, field.name) != getattr(converted, field.name)]
                self.assertEqual(changed, ["max_gross_weight"])
                self.assertEqual(original.max_gross_weight, D(".6"))
                self.assertEqual(converted.max_gross_weight, D(".90"))
                self.assertEqual(converted.fee_rate, D(".00055"))
                self.assertEqual(2 * (converted.fee_rate * D("10000")
                                     + converted.half_spread_bps + converted.slippage_bps),
                                 D(str(cost["roundtrip_bps"])))

    def test_base27_stress43_exact_buy_sell_fee_friction_funding_signs_and_cash_bridge(self):
        for cost in SCENARIOS:
            for opening_side, sign in (("BUY", D("1")), ("SELL", D("-1"))):
                with self.subTest(cost=cost["id"], opening_side=opening_side):
                    account = generated_account(cost)
                    rate = (D(str(cost["half_spread_bps"]))
                            + D(str(cost["slippage_bps"]))) / D("10000")
                    quantity, mid = D("10"), D("100")
                    open_fill = mid * (D("1") + sign * rate)
                    close_fill = mid * (D("1") - sign * rate)
                    opening = account.execute_fill(**request(
                        "BTCUSDT", opening_side, quantity, "cost-open"))
                    self.assertEqual(opening["status"], "FILLED")
                    row = opening["fills"][0]
                    self.assertEqual(exact(row, "fill_price"), open_fill)
                    self.assertEqual(exact(row, "fee_amount"), quantity * open_fill * D(".00055"))
                    self.assertEqual(exact(row, "execution_cost"), quantity * mid * rate)
                    self.assertEqual(exact(row, "margin_allocated"), quantity * open_fill)
                    self.assertEqual(exact(row, "free_cash_delta"),
                                     -quantity * open_fill * (D("1") + D(".00055")))

                    for index, funding_rate in enumerate((D(".0001"), D("-.0001"))):
                        before_cash, before_margin = account.free_cash, margin(account)
                        funding = account.apply_funding(
                            "BTCUSDT", f"cost-funding-{index}", FIRST_FILL_US + 1 + index,
                            funding_rate, 0,
                        )
                        expected = -sign * quantity * mid * funding_rate
                        self.assertTrue(funding["owned"])
                        self.assertEqual(exact(funding, "signed_funding_USDT"), expected)
                        self.assertEqual(account.free_cash, before_cash + expected)
                        self.assertEqual(margin(account), before_margin)
                    self.assertEqual(account.funding_cash, ZERO)
                    closing_side = "SELL" if opening_side == "BUY" else "BUY"
                    closing = account.execute_fill(**request(
                        "BTCUSDT", closing_side, quantity, "cost-close", FIRST_FILL_US + 3,
                        reduce_only=True,
                    ))
                    self.assertEqual(closing["status"], "FILLED")
                    row = closing["fills"][0]
                    self.assertEqual(exact(row, "fill_price"), close_fill)
                    self.assertEqual(exact(row, "fee_amount"), quantity * close_fill * D(".00055"))
                    self.assertEqual(exact(row, "execution_cost"), quantity * mid * rate)
                    self.assertEqual(exact(row, "realized_PnL"), -D("2") * quantity * mid * rate)
                    self.assertEqual(exact(row, "margin_released"), quantity * open_fill)
                    self.assertEqual(account.positions["BTCUSDT"].quantity, ZERO)
                    self.assertEqual(margin(account), ZERO)
                    self.assertEqual(account.fees, D("1.1"))
                    self.assertEqual(account.execution_cost, D("2") * quantity * mid * rate)
                    nominal_cost = quantity * mid * D(str(cost["roundtrip_bps"])) / D("10000")
                    self.assertEqual(account.fees + account.execution_cost, nominal_cost)
                    self.assertEqual(account.free_cash, D("10000") - nominal_cost)
                    self.assertEqual(account.nav(), account.free_cash)
                    summary = account.summary()
                    self.assertEqual(exact(summary, "accounting_bridge_error_USDT"), ZERO)
                    self.assertEqual(exact(summary, "gross_PnL_same_quantities"), ZERO)
                    self.assertEqual(exact(summary, "net_PnL"), -nominal_cost)
                    flat_funding = account.apply_funding(
                        "BTCUSDT", "cost-flat-funding", FIRST_FILL_US + 4, ".0001", 0)
                    self.assertFalse(flat_funding["owned"])
                    self.assertEqual(exact(flat_funding, "signed_funding_USDT"), ZERO)
                    self.assertEqual(account.free_cash, D("10000") - nominal_cost)


if __name__ == "__main__":
    unittest.main(verbosity=2)
