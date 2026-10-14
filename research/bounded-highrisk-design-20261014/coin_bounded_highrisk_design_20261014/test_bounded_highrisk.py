import unittest
from decimal import Decimal, ROUND_DOWN
from copy import deepcopy
import numpy as np
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from source_preflight import original_account_module, verify
from bounded_policy import (
    CapitalGuard, FiniteAddsPlan, FiniteAddsState, HighRiskToyAccount,
    ProgramBudget, ReservationBook, RiskStage, STAGE, SYMBOLS, bounded_weights,
    matched_csh_h090_intents,
    validate_intent_envelope,
)
from vendor_quant.perpetual_account import PerpetualConfig, USDTLinearPerpetualAccount
from toy_fixtures import (D, MINUTE_US, fill, fresh, generated_case,
                          generated_finite_program, mark, terminal60)


class SourceTests(unittest.TestCase):
    def test_source_identity_and_only_reviewed_diff(self):
        self.assertTrue(verify()["original_finance_methods_unchanged"])

    def test_missing_and_invalid_freeze_fail_closed(self):
        with TemporaryDirectory() as directory, patch("source_preflight.HERE", Path(directory)):
            with self.assertRaises(ValueError):
                verify()
            for invalid in ({}, {"version": "H090_SYNTHETIC_FREEZE_V2", "source_files_SHA256": {}},
                            [], {"source_files_SHA256": {"../escape.py": "0" * 64}}):
                (Path(directory) / "SOURCE_FREEZE.json").write_text(json.dumps(invalid))
                with self.assertRaises(ValueError):
                    verify()

    def test_original_rejects_raised_cap(self):
        original = original_account_module()
        with self.assertRaises(ValueError):
            original.PerpetualConfig(max_gross_weight=".90")

    def test_extended_still_rejects_leverage_asset_and_120(self):
        for kwargs in (dict(leverage="2"), dict(max_asset_weight=".31"),
                       dict(max_gross_weight="1.20")):
            with self.assertRaises(ValueError):
                PerpetualConfig(**kwargs)

    def test_fixed_stage_rejects_other_scope(self):
        for kwargs in (dict(gross_cap=D("1.2")), dict(initial_cash_floor=D("0")),
                       dict(annual_vol_target=D(".20")), dict(leverage=D("2"))):
            with self.assertRaises(ValueError):
                RiskStage(**kwargs)

    def test_finance_parity_under_original_cap(self):
        original = original_account_module()
        a = fresh(original.USDTLinearPerpetualAccount, original.PerpetualConfig())
        b = fresh(USDTLinearPerpetualAccount, PerpetualConfig())
        for account in (a, b):
            for s, side in zip(SYMBOLS, ("BUY", "SELL", "BUY", "SELL", "BUY")):
                fill(account, s, side, 8)
            for s in SYMBOLS:
                account.apply_funding(s, f"PARITY:{s}", 2 * MINUTE_US, ".0002", 0)
            mark(account, 3 * MINUTE_US, dict(zip(SYMBOLS, (90, 110, 85, 105, 95))))
            terminal60(account, signal=4 * MINUTE_US, mid=100, prior_quote=100000)
        self.assertEqual(a.snapshot(), b.snapshot())

    def test_snapshot_roundtrip_extension_identity(self):
        account = fresh()
        fill(account, "BTCUSDT", "BUY", 10, guard=True)
        restored = HighRiskToyAccount.from_snapshot(account.snapshot())
        self.assertEqual(restored.snapshot(), account.snapshot())


class SharedCapitalTests(unittest.TestCase):
    def test_shared_reserve_finite_program_and_cash_floor(self):
        book = ReservationBook()
        book.reserve("CSH_REPLACED90", 8000)
        book.reserve(FiniteAddsPlan().owner, FiniteAddsPlan().total_sleeve_investment)
        self.assertEqual(book.available_initial_capital(), D("1000"))
        with self.assertRaises(ValueError):
            book.reserve("EXTRA_BOT", 1)

    def test_no_duplicate_capital_or_hidden_topup(self):
        book = ReservationBook()
        book.reserve("CSH", 8000)
        with self.assertRaises(ValueError):
            book.reserve("CSH", 8000)
        with self.assertRaises(ValueError):
            ReservationBook(initial_cash=D("20000")).reserve("TOPUP", 1)

    def test_release_only_after_actual_flat_and_cancelled(self):
        book = ReservationBook()
        book.reserve("MART", 1000)
        for q, pending in ((".00000001", 0), (0, 1)):
            with self.assertRaises(ValueError):
                book.release("MART", actual_quantity=q, pending_increase_count=pending)
        book.release("MART", actual_quantity=0, pending_increase_count=0)
        with self.assertRaises(ValueError):
            book.reserve("MART", 1000)

    def test_retired_capital_cannot_be_reused_under_new_owner(self):
        book = ReservationBook()
        book.reserve("OLD", 9000)
        book.release("OLD", actual_quantity=0, pending_increase_count=0)
        self.assertEqual(book.available_initial_capital(), D("1000"))
        with self.assertRaises(ValueError):
            book.reserve("RENAMED", 1)

    def test_capital_guard_exact_preview_and_no_mutation_on_reject(self):
        account = fresh()
        for s in SYMBOLS[:-1]:
            self.assertEqual(fill(account, s, "BUY", 20, guard=True)["status"], "FILLED")
        before = deepcopy(account.snapshot())
        result = fill(account, SYMBOLS[-1], "BUY", 6, guard=True)
        self.assertEqual(result["reason"], "SHARED_CAPITAL_OR_RESERVE_CAP")
        self.assertEqual(account.snapshot(), before)

    def test_reductions_not_denied_by_new_floor(self):
        account = fresh()
        fill(account, "BTCUSDT", "BUY", 10, guard=True)
        account.apply_funding("BTCUSDT", "TOY_CASH_DRAIN", 2 * MINUTE_US, "8.1", 0)
        self.assertLess(account.free_cash, STAGE.initial_cash_floor)
        receipt = fill(account, "BTCUSDT", "SELL", 1, signal=2 * MINUTE_US,
                       event=3 * MINUTE_US + 1, guard=True, reduce_only=True)
        self.assertEqual(receipt["status"], "FILLED")

    def test_duplicate_fill_replay_survives_later_floor_breach(self):
        account = fresh()
        first = fill(account, "BTCUSDT", "BUY", 10, fill_id="REPLAY", guard=True)
        account.apply_funding("BTCUSDT", "DRAIN", 2 * MINUTE_US, "8.1", 0)
        before = deepcopy(account.snapshot())
        replay = fill(account, "BTCUSDT", "BUY", 10, fill_id="REPLAY", guard=True)
        self.assertEqual(replay, first)
        self.assertEqual(account.snapshot(), before)
        with self.assertRaises(ValueError):
            fill(account, "BTCUSDT", "BUY", 11, fill_id="REPLAY", guard=True)


class FiniteAddTests(unittest.TestCase):
    def test_multiplier_on_margin_not_quantity(self):
        plan = FiniteAddsPlan()
        self.assertEqual(plan.margins(), (D("150"), D("187.50"), D("234.3750"), D("292.968750")))
        self.assertEqual(plan.margin_total(), D("864.843750"))
        self.assertEqual(plan.cost_funding_reserve(), D("135.156250"))
        self.assertNotEqual(plan.margins()[1] / D("95"), plan.margins()[0] / D("100") * D("1.25"))

    def test_recomputed_average_trigger_and_signed_stop(self):
        long = FiniteAddsPlan()
        self.assertEqual(long.trigger_price(96), D("91.20"))
        self.assertTrue(long.loss_exit_due(-200))
        self.assertFalse(long.loss_exit_due(200))
        self.assertFalse(long.loss_exit_due(-199))
        with self.assertRaises(ValueError):
            FiniteAddsPlan(direction=-1)

    def test_finite_add_limit_not_automatic_exit(self):
        state = FiniteAddsState()
        account = fresh()
        for i, margin in enumerate(state.plan.margins()):
            self.assertEqual(state.next_order_margin(), margin)
            qty = (margin / D("100.08")).quantize(D(".00000001"), rounding=ROUND_DOWN)
            fill(account, "BTCUSDT", "BUY", qty, fill_id=f"ADD:{i}",
                 signal=2*i*MINUTE_US, event=(2*i+1)*MINUTE_US+1, guard=True)
            state.record_fill_receipt(account, f"ADD:{i}", i)
        self.assertIsNone(state.next_order_margin())
        self.assertFalse(state.terminal)
        with self.assertRaises(ValueError):
            state.record_complete_opening_order(1, 1)

    def test_direction_lock_partial_and_quantization(self):
        state = FiniteAddsState()
        with self.assertRaises(ValueError):
            state.record_complete_opening_order(-1, 150)
        with self.assertRaises(ValueError):
            state.record_complete_opening_order(1, 100)
        with self.assertRaises(ValueError):
            state.record_complete_opening_order(1, 1, quantization_remainder=149, maximum_remainder=150)
        account = fresh()
        fill(account, "BTCUSDT", "BUY", ".11", fill_id="PARTIAL:1", guard=True)
        state.record_fill_receipt(account, "PARTIAL:1", 0)
        self.assertEqual(state.completed_opening_orders, 0)
        before = state.current_order_filled_margin
        state.record_fill_receipt(account, "PARTIAL:1", 0)
        self.assertEqual(state.current_order_filled_margin, before)
        with self.assertRaises(ValueError):
            state.record_fill_receipt(account, "PARTIAL:1", 1)
        remaining = D("150") - state.current_order_filled_margin
        qty = (remaining / D("100.08")).quantize(D(".00000001"), rounding=ROUND_DOWN)
        fill(account, "BTCUSDT", "BUY", qty, fill_id="PARTIAL:2",
             signal=2*MINUTE_US, event=3*MINUTE_US+1, guard=True)
        state.record_fill_receipt(account, "PARTIAL:2", 0)
        self.assertEqual(state.completed_opening_orders, 1)
        short_account = fresh()
        fill(short_account, "BTCUSDT", "SELL", ".11", fill_id="SHORT", guard=True)
        with self.assertRaises(ValueError):
            FiniteAddsState().record_fill_receipt(short_account, "SHORT", 0)

    def test_terminal_cancels_further_increases(self):
        state = FiniteAddsState()
        state.begin_terminal()
        self.assertIsNone(state.next_order_margin())

    def test_no_unbounded_or_costless_program(self):
        for kwargs in (dict(maximum_adds=4), dict(margin_multiplier="2"),
                       dict(initial_order_margin="999"), dict(margin_multiplier="1.1"),
                       dict(total_sleeve_investment="864.84375")):
            with self.assertRaises(ValueError):
                FiniteAddsPlan(**kwargs)

    def test_fee_funding_reserve_not_reused_or_double_debited(self):
        budget = ProgramBudget()
        self.assertTrue(budget.record_cost_event("FEE1", actual_fee=1))
        budget.record_cost_event("FEE1", actual_fee=1)
        self.assertEqual(budget.consumed_fee_funding_reserve, 1)
        with self.assertRaises(ValueError):
            budget.record_cost_event("FEE1", actual_fee=2)
        budget.record_cost_event("CREDIT", signed_funding=100)
        self.assertEqual(budget.consumed_fee_funding_reserve, 1)
        self.assertFalse(budget.record_cost_event("DRAIN", signed_funding=-135))
        self.assertEqual(budget.consumed_fee_funding_reserve, 136)

    def test_actual_finite_orders_use_one_existing_shared_wallet(self):
        case = generated_finite_program()
        self.assertEqual(case["complete_opening_orders"], 4)
        self.assertIsNone(case["next_order_margin"])
        self.assertFalse(case["terminal_auto_triggered"])
        self.assertLess(case["summary"]["isolated_balance"], 8500)
        self.assertGreater(case["summary"]["free_cash"], 1000)
        self.assertLess(abs(case["summary"]["accounting_bridge_error_USDT"]), 1e-30)
        self.assertFalse(case["candidate_backtest"])


class EnvelopeTests(unittest.TestCase):
    def test_opposing_sleeves_do_not_hide_asset_risk(self):
        result = validate_intent_envelope({"CSH": {"BTCUSDT": 2000},
                                           "BOT": {"BTCUSDT": -2000}}, 10000,
                                          actual_signed_notionals=dict.fromkeys(SYMBOLS, 0),
                                          pending_increases={})
        self.assertEqual(result["net_notional"], "0")
        self.assertIn("CONSERVATIVE_ASSET_CAP", result["reasons"])

    def test_pending_increases_and_mark_drift_not_clipped(self):
        legs = {"CSH": dict.fromkeys(SYMBOLS, D("1700"))}
        self.assertTrue(validate_intent_envelope(legs, 10000,
            actual_signed_notionals=dict.fromkeys(SYMBOLS, 0), pending_increases={})["allow_increases"])
        actual = dict.fromkeys(SYMBOLS, D("1700"))
        result = validate_intent_envelope(legs, 8000, actual_signed_notionals=actual,
                                         pending_increases={"MART": {"BTCUSDT": 500}})
        self.assertFalse(result["allow_increases"])
        self.assertFalse(result["cap_guaranteed_after_mark"])
        self.assertEqual(result["risk_gross_including_pending"], "9000")

    def test_actual_and_pending_asset_and_net_caps_are_independent(self):
        actual = dict.fromkeys(SYMBOLS, D("0"))
        actual["BTCUSDT"] = D("2500")
        result = validate_intent_envelope({}, 10000, actual_signed_notionals=actual,
            pending_increases={"BOT": {"BTCUSDT": 600}})
        self.assertIn("CONSERVATIVE_ASSET_CAP", result["reasons"])
        actual = dict.fromkeys(SYMBOLS, D("1840"))
        result = validate_intent_envelope({}, 10000, actual_signed_notionals=actual, pending_increases={})
        self.assertIn("NET_CAP", result["reasons"])
        with self.assertRaises(ValueError):
            validate_intent_envelope({}, 10000, actual_signed_notionals={"BTCUSDT": 1}, pending_increases={})
        with self.assertRaises(TypeError):
            validate_intent_envelope({}, 10000)
        with self.assertRaises(ValueError):
            validate_intent_envelope({}, 10000, actual_signed_notionals=None, pending_increases={})
        with self.assertRaises(ValueError):
            validate_intent_envelope({}, 10000, actual_signed_notionals=dict.fromkeys(SYMBOLS, 0),
                                     pending_increases=None)

    def test_covariance_controller_fixed_stage_and_past_window(self):
        rng = np.random.default_rng(807)
        r = rng.normal(0, .015, (60, 5))
        raw = np.array([.9, -.8, .7, -.6, .5])
        w, meta = bounded_weights(raw, r)
        self.assertLessEqual(float(abs(w).sum()), .90 + 1e-14)
        self.assertLessEqual(float(abs(w).max()), .30 + 1e-14)
        r[:30] *= 50
        np.testing.assert_array_equal(w, bounded_weights(raw, r)[0])
        covariance = np.cov(r[-30:], rowvar=False, ddof=1) * 365
        self.assertLessEqual(float(np.sqrt(w @ covariance @ w)), .15 + 1e-14)
        with self.assertRaises(ValueError):
            bounded_weights(raw, r, gross_cap=1.2, vol_target=.20)

    def test_same_highrisk_csh_control_not_new_signal_fitting(self):
        r = np.tile(np.array([.0001, -.0002, .0003, -.0004, .0005]), (30, 1))
        original = np.array([.12, .12, .12, -.12, -.12])
        weights, metadata = matched_csh_h090_intents(original, r)
        np.testing.assert_allclose(weights, 1.5 * original, atol=1e-15)
        self.assertTrue(metadata["original_strategy_parameters_unchanged"])
        self.assertFalse(metadata["realized_risk_matching_certified"])
        with self.assertRaises(ValueError):
            matched_csh_h090_intents(np.ones(5), r)

    def test_higher_cap_is_not_an_actual_exposure_guarantee(self):
        account = fresh()
        for s, side in zip(SYMBOLS, ("BUY", "BUY", "BUY", "SELL", "SELL")):
            fill(account, s, side, 16, guard=True)
        mark(account, 2 * MINUTE_US, dict(zip(SYMBOLS, (70, 70, 70, 130, 130))))
        self.assertEqual(account.status, "BOUND_BREACH_REDUCTION_REQUIRED")
        self.assertGreater(account.summary()["gross_weight"], .90)
        result = fill(account, "BTCUSDT", "BUY", 1, event=3 * MINUTE_US + 1,
                      signal=2 * MINUTE_US)
        self.assertEqual(result["reason"], "BOUND_BREACH_REDUCTION_REQUIRED")


class StressTests(unittest.TestCase):
    def test_positive_nav_and_free_cash_cannot_rescue_isolated_gap(self):
        case = generated_case("SHORT_ISOLATED_LIQUIDATION_GAP")
        summary = case["summary"]
        self.assertEqual(summary["account_status"], "LIQUIDATION_REQUIRED_HALT")
        self.assertGreater(summary["free_cash"], 1000)
        self.assertGreater(summary["NAV"], 0)
        self.assertFalse(summary["contract"]["native_liquidation_certified"])

    def test_bankruptcy_halt_is_not_whole_wallet_ruin(self):
        summary = generated_case("SHORT_ISOLATED_BANKRUPTCY_GAP")["summary"]
        self.assertEqual(summary["account_status"], "BANKRUPT_HALT")
        self.assertGreater(summary["NAV"], 1000)

    def test_zero_liquidity_terminal_retains_residual(self):
        case = generated_case("ZERO_LIQUIDITY_TERMINAL")
        self.assertEqual(case["terminal"]["actual_attempt_minutes"], 60)
        self.assertEqual(len(case["terminal"]["residual_quantities"]), 5)
        self.assertEqual(case["terminal"]["completion"], "INCOMPLETE_UNPAID_RESIDUAL")

    def test_late_partial_terminal_is_not_free_complete_exit(self):
        case = generated_case("LATE_PARTIAL_TERMINAL")
        self.assertEqual(case["terminal"]["actual_attempt_minutes"], 60)
        self.assertTrue(case["terminal"]["residual_quantities"])
        self.assertGreater(case["summary"]["fees_USDT"], 4.4)
        self.assertGreater(case["summary"]["execution_cost_USDT"], 6.4)

    def test_benign_terminal_is_paid_and_accounting_bridge_exact(self):
        summary = generated_case("BENIGN_PAID_TERMINAL")["summary"]
        self.assertEqual(summary["accounting_bridge_error_USDT"], 0)
        self.assertLess(summary["NAV"], 10000)
        self.assertTrue(all(p["quantity"] == 0 for p in summary["positions"].values()))

    def test_funding_drain_is_not_zero_cost_or_rescued(self):
        summary = generated_case("FUNDING_DRAIN")["summary"]
        self.assertEqual(summary["funding_USDT"], -1200)
        self.assertLess(summary["free_cash"], 1000)
        self.assertEqual(summary["accounting_bridge_error_USDT"], 0)


if __name__ == "__main__":
    unittest.main()
