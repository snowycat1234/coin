"""Synthetic causality and account invariants; no historical wallet/tape use."""
from __future__ import annotations

from decimal import Decimal as D
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
REPO = next((p for p in HERE.parents if (p / 'src/quant/perpetual_account.py').exists()), None)
if REPO is None:
    REPO = HERE.parent / 'coin_native_half_mix_20261013' / 'repo'
sys.path[:0] = [str(REPO), str(REPO / 'src')]
# The bounded local research checkout lacks an unrelated old strategy import.
# Its verified transport-only bootstrap supplies exactly the frozen scheduler.
if not (REPO / 'scripts/research_v8/public_donchian_adapter.py').exists():
    p = REPO / 'research/static50-sma-20261013/local_native_apis.py'
    spec = importlib.util.spec_from_file_location('verified_local_native_port', p)
    port = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(port)

from quant.perpetual_account import InstrumentProfile, USDTLinearPerpetualAccount
from scripts.investment.perpetual_directional import DAY, MINUTE
from scripts.investment.resumable_perpetual import NativeDailySimulator
from scripts.investment.perpetual_directional import COSTS, UNITS
from scripts.investment.bybit_cost_inputs import scenario_config
from protective_policy import ProtectiveFullExitSimulator, POLICY_ID

BASE = .53197408
HALF_LOSS_MARK = .8
HALT_MARK = 1.06181663


def account_factory(config, *, symbols):
    return USDTLinearPerpetualAccount(config, symbols=symbols,
        instrument_profiles={'XRPUSDT': InstrumentProfile(quantity_step=D('100'))},
        closing_min_notional_exempt=True)


def make_window(days=1, *, stress_mark=None, zero_capacity_after=None):
    length = days * 1440
    prices = np.full(length, BASE)
    if stress_mark is not None:
        prices[10:] = stress_mark
    quotes = np.full(length, 1e6)
    if zero_capacity_after is not None:
        quotes[zero_capacity_after:] = 0
    return dict(start=0, end=days * DAY, symbols=('XRPUSDT',),
        daily=pl.DataFrame([dict(symbol='XRPUSDT', close_us=d * DAY,
            close=BASE if d == 0 else (stress_mark or BASE)) for d in range(days)]),
        events=[], market={'XRPUSDT': dict(open=prices, close=prices,
            mark=prices, quote_volume=quotes)})


def simulator(window, cls=ProtectiveFullExitSimulator):
    return cls(window, 'LONG_SHORT', COSTS[0], UNITS[0],
               account_factory=account_factory, persist_cash_close=False,
               final_day_target_zero=False)


class ProtectivePolicyTests(unittest.TestCase):
    def test_next_open_full_close_and_direction_reset(self):
        sim = simulator(make_window(3, stress_mark=HALF_LOSS_MARK))
        sim.advance_day({'XRPUSDT': -.02})
        signals = [r for r in sim.protective_events if r['kind'] == 'FULL_EXIT_SIGNAL']
        flats = [r for r in sim.protective_events if r['kind'] == 'FULL_EXIT_FLAT']
        self.assertEqual(len(signals), 1)
        self.assertEqual(len(flats), 1)
        self.assertEqual(signals[0]['event_us'], 11 * MINUTE)
        self.assertEqual(flats[0]['event_us'], 12 * MINUTE + 1)
        self.assertEqual(sim.account.positions['XRPUSDT'].quantity, 0)
        self.assertEqual(sim.account.trades[-1]['leg'], 'CLOSE')
        self.assertEqual(sim.account.trades[-1]['event_us'], flats[0]['event_us'])
        self.assertEqual(sim.account.trades[-1]['quantity'], 300)
        self.assertGreater(sim.account.fees, 0)
        self.assertGreater(sim.account.execution_cost, 0)
        trades = len(sim.account.trades)
        sim.advance_day({'XRPUSDT': -.02})
        self.assertEqual(len(sim.account.trades), trades)
        self.assertEqual(sim.account.positions['XRPUSDT'].quantity, 0)
        self.assertIn('XRPUSDT', sim.protective_locks)
        sim.advance_day({'XRPUSDT': .02})
        self.assertNotIn('XRPUSDT', sim.protective_locks)
        self.assertEqual(len([r for r in sim.protective_events
                              if r['kind'] == 'RESET_BY_NEW_DAILY_DIRECTION']), 1)
        self.assertEqual(sim.result()['summary']['protective_policy_id'], POLICY_ID)

    def test_one_mark_gap_halts_before_guard_can_act(self):
        sim = simulator(make_window(stress_mark=HALT_MARK))
        sim.advance_day({'XRPUSDT': -.02})
        self.assertEqual(sim.account.status, 'LIQUIDATION_REQUIRED_HALT')
        self.assertEqual(sim.protective_events, [])
        self.assertEqual(sim.result()['summary']['completion'],
                         'NOT_EVALUABLE_ACCOUNT_HALT_NO_LIQUIDATION_SIMULATED')

    def test_zero_capacity_persists_and_fails_honestly(self):
        sim = simulator(make_window(stress_mark=HALF_LOSS_MARK, zero_capacity_after=10))
        sim.advance_day({'XRPUSDT': -.02})
        self.assertEqual(sim.account.positions['XRPUSDT'].quantity, -300)
        self.assertEqual(sim.pending['XRPUSDT']['kind'], 'PROTECTIVE_STOP')
        self.assertGreater(sim.protective_locks['XRPUSDT']['deferred_no_lot_minutes'], 1000)
        self.assertLess(len(sim.rejections), 20)
        self.assertEqual(sim.completion, 'NOT_EVALUABLE_PROTECTIVE_EXIT_UNFILLED_AT_HORIZON')
        self.assertEqual(len([r for r in sim.protective_events
                              if r['kind'] == 'FULL_EXIT_FLAT']), 0)

    def test_short_capacity_gap_then_fill_at_later_open(self):
        window = make_window(stress_mark=HALF_LOSS_MARK)
        window['market']['XRPUSDT']['quote_volume'][10:20] = 0
        sim = simulator(window)
        sim.advance_day({'XRPUSDT': -.02})
        self.assertEqual(sim.account.positions['XRPUSDT'].quantity, 0)
        self.assertEqual(sim.protective_locks['XRPUSDT']['deferred_no_lot_minutes'], 10)
        flat = next(r for r in sim.protective_events if r['kind'] == 'FULL_EXIT_FLAT')
        self.assertEqual(flat['event_us'], 21 * MINUTE + 1)

    def test_capacity_limited_partial_close_then_gap_halts(self):
        window = make_window(stress_mark=HALF_LOSS_MARK)
        market = window['market']['XRPUSDT']
        market['quote_volume'][11] = 110_000  # About 103 XRP at first eligible open.
        for field in ('open', 'close', 'mark'):
            market[field][12:] = HALT_MARK
        sim = simulator(window)
        sim.advance_day({'XRPUSDT': -.02})
        closes = [r for r in sim.account.trades if r['leg'] == 'CLOSE']
        self.assertEqual(len(closes), 1)
        self.assertEqual(closes[0]['quantity'], 100)
        self.assertEqual(sim.account.positions['XRPUSDT'].quantity, -200)
        self.assertEqual(sim.account.status, 'LIQUIDATION_REQUIRED_HALT')
        self.assertFalse(any(r['kind'] == 'FULL_EXIT_FLAT'
                             for r in sim.protective_events))

    def test_cap_breach_preserves_original_five_attempt_stop(self):
        sim = simulator(make_window(stress_mark=HALF_LOSS_MARK,
                                    zero_capacity_after=10))
        sim.advance_day({'XRPUSDT': -.30})
        self.assertEqual(sim.account.status, 'BOUND_BREACH_REDUCTION_REQUIRED')
        self.assertEqual(sim.completion, 'NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION')
        self.assertEqual(len(sim.breaches), 1)
        self.assertLess(sim.rows_written, 20)
        self.assertFalse(any(r['kind'] == 'FULL_EXIT_FLAT'
                             for r in sim.protective_events))

    def test_cap_resolves_then_full_exit_intent_rearms(self):
        window = make_window(stress_mark=HALF_LOSS_MARK)
        window['market']['XRPUSDT']['quote_volume'][13:] = 0
        sim = simulator(window)
        sim.advance_day({'XRPUSDT': -.30})
        self.assertEqual(len(sim.breaches), 1)
        self.assertEqual(sim.account.status, 'ACTIVE')
        self.assertLess(abs(sim.account.positions['XRPUSDT'].quantity), 5500)
        self.assertEqual(sim.completion,
                         'NOT_EVALUABLE_PROTECTIVE_EXIT_UNFILLED_AT_HORIZON')
        self.assertEqual(sim.pending['XRPUSDT']['kind'], 'PROTECTIVE_STOP')
        self.assertGreater(sim.protective_locks['XRPUSDT']['deferred_no_lot_minutes'], 1000)

    def test_all_same_close_funding_precedes_guard(self):
        window = make_window(stress_mark=HALF_LOSS_MARK)
        length = len(window['market']['XRPUSDT']['open'])
        window['symbols'] = ('BTCUSDT', 'XRPUSDT')
        window['daily'] = pl.concat([window['daily'], pl.DataFrame([
            dict(symbol='BTCUSDT', close_us=0, close=100.)])])
        window['market']['BTCUSDT'] = dict(
            open=np.full(length, 100.), close=np.full(length, 100.),
            mark=np.full(length, 100.), quote_volume=np.full(length, 1e6))
        close_us = 11 * MINUTE
        window['events'] = [
            dict(symbol='BTCUSDT', event_us=close_us, raw_rate=0.),
            dict(symbol='XRPUSDT', event_us=close_us, raw_rate=-100.),
        ]

        def two_symbol_account(config, *, symbols):
            return USDTLinearPerpetualAccount(config, symbols=symbols,
                instrument_profiles={
                    'BTCUSDT': InstrumentProfile(quantity_step=D('.001')),
                    'XRPUSDT': InstrumentProfile(quantity_step=D('100')),
                }, closing_min_notional_exempt=True)

        sim = ProtectiveFullExitSimulator(window, 'LONG_SHORT', COSTS[0], UNITS[0],
                                          account_factory=two_symbol_account)
        sim.advance_day({'BTCUSDT': 0., 'XRPUSDT': -.02})
        self.assertEqual(sim.account.status, 'BANKRUPT_HALT')
        self.assertEqual(sim.stop, close_us)
        self.assertEqual([r for r in sim.protective_events
                          if r['kind'] == 'FULL_EXIT_SIGNAL'], [])

    def test_snapshot_identity_and_state_roundtrip(self):
        window = make_window(2, stress_mark=HALF_LOSS_MARK)
        window['market']['XRPUSDT']['quote_volume'][10:1440] = 0
        sim = simulator(window)
        sim.advance_day({'XRPUSDT': -.02})
        self.assertEqual(sim.account.positions['XRPUSDT'].quantity, -300)
        self.assertEqual(sim.pending['XRPUSDT']['kind'], 'PROTECTIVE_STOP')
        image = sim.snapshot()
        restored = ProtectiveFullExitSimulator.from_snapshot(
            image, window, account_class=USDTLinearPerpetualAccount)
        self.assertEqual(restored.state_hash(), sim.state_hash())
        restored.advance_day({'XRPUSDT': -.02})
        sim.advance_day({'XRPUSDT': -.02})
        self.assertEqual(restored.state_hash(), sim.state_hash())
        self.assertEqual(restored.account.positions['XRPUSDT'].quantity, 0)
        image['protective_policy']['protocol_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            ProtectiveFullExitSimulator.from_snapshot(
                image, window, account_class=USDTLinearPerpetualAccount)

    def test_no_trigger_matches_original_scheduler(self):
        window = make_window()
        guarded = simulator(window)
        original = simulator(window, NativeDailySimulator)
        guarded.advance_day({'XRPUSDT': -.02})
        original.advance_day({'XRPUSDT': -.02})
        self.assertEqual(guarded.protective_events, [])
        self.assertEqual(guarded.account.snapshot(), original.account.snapshot())
        self.assertEqual(guarded.rows_written, original.rows_written)
        self.assertEqual(guarded.account.nav(), original.account.nav())

    def test_partial_close_cannot_repair_ratio_by_itself(self):
        account = account_factory(scenario_config(COSTS[0]), symbols=('XRPUSDT',))
        account.update_marks(0, {'XRPUSDT': dict(price=D(str(BASE)),
                                           close_us=0, available_us=0)})
        account.execute_fill('XRPUSDT', 'SELL', 300, MINUTE + 1, 0, 'open',
            execution_mid_price=D(str(BASE)), quote_available_us=MINUTE,
            available_quantity=300)
        account.update_marks(2 * MINUTE, {'XRPUSDT': dict(price=D('0.8'),
            close_us=2 * MINUTE, available_us=2 * MINUTE)})
        p = account.positions['XRPUSDT']
        ratio_before = (p.isolated_balance + p.quantity * (D('.8') - p.entry_price)) / (
            abs(p.quantity) * D('.8') * D('.005'))
        account.execute_fill('XRPUSDT', 'BUY', 100, 3 * MINUTE + 1,
            2 * MINUTE, 'partial', execution_mid_price=D('.8'),
            quote_available_us=3 * MINUTE, available_quantity=100, reduce_only=True)
        p = account.positions['XRPUSDT']
        ratio_after = (p.isolated_balance + p.quantity * (D('.8') - p.entry_price)) / (
            abs(p.quantity) * D('.8') * D('.005'))
        self.assertEqual(ratio_after, ratio_before)
        self.assertEqual(p.quantity, -200)


if __name__ == '__main__':
    unittest.main(verbosity=2)
