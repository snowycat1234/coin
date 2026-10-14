"""Synthetic/account-only checks. No historical source is opened by these tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import numpy as np
import polars as pl

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT / "coin_native_half_mix_20261013/repo"
sys.path[:0] = [str(REPO), str(REPO / "src"), str(HERE),
                str(ROOT / "coin_margin_protective_policy_20261013")]

import preflight
from freeze_bootstrap import verify as verify_reviewed_freeze
from fine_account import FineGridAccount, SYMBOLS, profile_sha, profiles
from quant.perpetual_account import InstrumentProfile

spec = importlib.util.spec_from_file_location("frozen_coarse_account",
    REPO / "research/quantity-grid-sensitivity-20261012/grid_account.py")
coarse_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(coarse_module)
CoarseAccount = coarse_module.QuantityGridAccount


def mark(account, price="1", stamp=60_000_000):
    account.update_marks(stamp, {"DOGEUSDT": {
        "price": price, "close_us": stamp, "available_us": stamp}})


def fill(account, quantity, price, stamp, side="BUY", reduce_only=False):
    return account.execute_fill("DOGEUSDT", side, quantity, stamp, 60_000_000,
        f"synthetic-{stamp}-{side}", execution_mid_price=price,
        quote_available_us=stamp - 1, available_quantity=quantity,
        reduce_only=reduce_only)


class FineGridPureTests(unittest.TestCase):
    def test_profile_is_reused_shared_default_only(self):
        expected = InstrumentProfile()
        self.assertEqual(tuple(profiles()), SYMBOLS)
        self.assertTrue(all(p == expected for p in profiles().values()))
        declaration = json.loads((HERE / "FINE_PROFILE.json").read_text())
        self.assertEqual(declaration["opening_min_notional_USDT"], "10")
        self.assertTrue(declaration["closing_min_notional_exempt"])
        self.assertFalse(declaration["historical_venue_filters_certified"])
        self.assertEqual(profile_sha(), preflight.bindings()["fine_profile_SHA256"])

    def test_only_profile_differs_from_coarse_contract(self):
        fine, coarse = FineGridAccount(), CoarseAccount(symbols=SYMBOLS)
        self.assertEqual(fine.config, coarse.config)
        self.assertEqual(fine.closing_min_notional_exempt, coarse.closing_min_notional_exempt)
        self.assertEqual(fine.symbols, coarse.symbols)
        self.assertEqual(fine.cost_context, coarse.cost_context)
        for symbol in SYMBOLS:
            self.assertEqual(fine.instrument_profiles[symbol].min_notional,
                             coarse.instrument_profiles[symbol].min_notional)
            self.assertEqual(fine.instrument_profiles[symbol].quantity_asset,
                             coarse.instrument_profiles[symbol].quantity_asset)
        self.assertEqual(fine.instrument_profiles["DOGEUSDT"].quantity_step,
                         InstrumentProfile().quantity_step)
        self.assertNotEqual(fine.instrument_profiles["DOGEUSDT"].quantity_step,
                            coarse.instrument_profiles["DOGEUSDT"].quantity_step)

    def test_small_open_coarse_rejected_fine_accepted(self):
        fine, coarse = FineGridAccount(), CoarseAccount(symbols=SYMBOLS)
        mark(fine)
        mark(coarse)
        self.assertEqual(fill(coarse, "50", "1", 120_000_001)["status"], "REJECTED")
        self.assertEqual(fill(fine, "50", "1", 120_000_001)["status"], "FILLED")
        self.assertEqual(fine.positions["DOGEUSDT"].quantity, 50)

    def test_opening_min_notional_and_closing_exemption(self):
        low = FineGridAccount()
        mark(low)
        self.assertEqual(fill(low, "5", "1", 120_000_001)["status"], "REJECTED")
        account = FineGridAccount()
        mark(account)
        self.assertEqual(fill(account, "10", "1", 120_000_001)["status"], "FILLED")
        mark(account, price="0.5", stamp=180_000_000)
        receipt = fill(account, "10", "0.5", 240_000_001, side="SELL", reduce_only=True)
        self.assertEqual(receipt["status"], "FILLED")
        self.assertEqual(account.positions["DOGEUSDT"].quantity, 0)

    def test_profile_override_and_snapshot_mismatch_rejected(self):
        with self.assertRaisesRegex(ValueError, "Fine-grid profile mismatch"):
            FineGridAccount(instrument_profiles={s: InstrumentProfile(quantity_step="0.01")
                                                 for s in SYMBOLS})
        account = FineGridAccount()
        snapshot = account.snapshot()
        restored = FineGridAccount.from_snapshot(snapshot, expected_symbols=SYMBOLS)
        self.assertEqual(restored.contract_metadata(), account.contract_metadata())
        snapshot["instrument_profiles"]["DOGEUSDT"]["quantity_step"] = "1000"
        with self.assertRaises(ValueError):
            FineGridAccount.from_snapshot(snapshot, expected_symbols=SYMBOLS)

    def test_published_guard_stays_byte_identical(self):
        self.assertEqual(preflight.sha(ROOT / "coin_margin_protective_runner_20261013/run_guard_cases.py"),
                         preflight.RUNNER_SHA256)
        freeze = json.loads((ROOT / "coin_margin_protective_policy_20261013/FREEZE.json").read_text())
        self.assertEqual(preflight.sha(ROOT / "coin_margin_protective_policy_20261013/protective_policy.py"),
                         freeze["SHA256"]["adapter"])
        self.assertEqual(freeze["SHA256"]["quantity_profile"],
                         preflight.bindings()["coarse_profile_SHA256"])

    def test_unchanged_guard_accepts_fine_account_synthetic(self):
        # Bootstrap the frozen transport shim without opening any historical
        # source window or advancing a historical minute.
        port_file = REPO / "research/static50-sma-20261013/local_native_apis.py"
        port_spec = importlib.util.spec_from_file_location("fine_synthetic_port", port_file)
        port = importlib.util.module_from_spec(port_spec)
        port_spec.loader.exec_module(port)
        port.verify()
        from protective_policy import ProtectiveFullExitSimulator
        from scripts.investment.perpetual_directional import COSTS, UNITS, MINUTE
        n = 25
        base = .53197408
        daily = pl.DataFrame([{"symbol": s, "close_us": 0,
                               "close": base if s == "XRPUSDT" else 100.}
                              for s in SYMBOLS])
        market = {}
        for symbol in SYMBOLS:
            price = np.full(n, base if symbol == "XRPUSDT" else 100.)
            if symbol == "XRPUSDT":
                price[10:] = .8
            market[symbol] = {"open": price, "close": price.copy(),
                              "mark": price.copy(), "quote_volume": np.full(n, 1e6)}
        window = {"start": 0, "end": n * MINUTE, "symbols": SYMBOLS,
                  "daily": daily, "events": [], "market": market}
        sim = ProtectiveFullExitSimulator(window, "LONG_SHORT", COSTS[0], UNITS[0],
            account_factory=FineGridAccount, persist_cash_close=False,
            final_day_target_zero=False)
        sim.advance_day({s: -.02 if s == "XRPUSDT" else 0. for s in SYMBOLS})
        self.assertEqual(type(sim.account), FineGridAccount)
        self.assertEqual(sim.account.instrument_profiles["XRPUSDT"].quantity_step,
                         InstrumentProfile().quantity_step)
        self.assertEqual(sum(e["kind"] == "FULL_EXIT_SIGNAL" for e in sim.protective_events), 1)
        self.assertEqual(sum(e["kind"] == "FULL_EXIT_FLAT" for e in sim.protective_events), 1)
        self.assertEqual(sim.account.positions["XRPUSDT"].quantity, 0)
        restored = ProtectiveFullExitSimulator.from_snapshot(sim.snapshot(), window,
                                                              account_class=FineGridAccount)
        self.assertEqual(restored.state_hash(), sim.state_hash())
        self.assertEqual(restored.protective_events, sim.protective_events)

    def test_run_gate_rejects_unapproved_worker(self):
        from run_cases import worker
        case = preflight.bindings()["cases"][0]
        with self.assertRaises((FileNotFoundError, RuntimeError, ValueError)):
            worker(case, "ORIGINAL", HERE / "state_nonexistent_test")
        self.assertFalse((HERE / "state_nonexistent_test").exists())

    def test_reviewed_financial_code_drift_rejected_before_import(self):
        reviewed = verify_reviewed_freeze()
        self.assertEqual(reviewed["files_SHA256"]["fine_account.py"],
                         preflight.sha(HERE / "fine_account.py"))
        with tempfile.TemporaryDirectory() as temporary:
            copy = Path(temporary)
            for name in [*reviewed["files_SHA256"], "freeze_bootstrap.py",
                         "FROZEN_CODE.json", "REVIEW_RECEIPT.json"]:
                shutil.copy2(HERE / name, copy / name)
            self.assertEqual(verify_reviewed_freeze(copy)["freeze_manifest_SHA256"],
                             reviewed["freeze_manifest_SHA256"])
            (copy / "fine_account.py").write_bytes(
                (copy / "fine_account.py").read_bytes() + b"\n# synthetic drift\n")
            with self.assertRaisesRegex(ValueError, "fine_account.py"):
                verify_reviewed_freeze(copy)
            shutil.copy2(HERE / "fine_account.py", copy / "fine_account.py")
            (copy / "freeze_bootstrap.py").write_bytes(
                (copy / "freeze_bootstrap.py").read_bytes() + b"\n# synthetic drift\n")
            with self.assertRaisesRegex(ValueError, "manifest/receipt mismatch"):
                verify_reviewed_freeze(copy)


if __name__ == "__main__":
    unittest.main(verbosity=2)
