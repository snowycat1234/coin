"""Synthetic-only causality, gate, exact-flat, prefix, and resource tests."""
from __future__ import annotations
from copy import deepcopy
from decimal import Decimal as D
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REPO = ROOT / 'coin_native_half_mix_20261013/repo'
POLICY = ROOT / 'coin_margin_protective_policy_20261013'
sys.path[:0] = [str(REPO), str(REPO / 'src'), str(POLICY), str(HERE),
                str(ROOT / 'coin_quantity_resolution_20261013')]
spec = importlib.util.spec_from_file_location('old_guard_synthetic_helpers', POLICY / 'test_policy_synthetic.py')
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
from daily_reentry_policy import FreshDailyReentrySimulator, POLICY_ID
from fine_account import FineGridAccount
from reentry_freeze import verify
import reentry_preflight
from prefix_acceptance import financial_prefix, compare_prefix, load_minute
from resource_gate import check_external, task_reservation
from scripts.investment.resumable_perpetual import NativeDailySimulator
from quant.perpetual_account import USDTLinearPerpetualAccount

S = 'XRPUSDT'
DAY, MINUTE = old.DAY, old.MINUTE

def make(window, cls=FreshDailyReentrySimulator, factory=old.account_factory):
    return cls(window, 'LONG_SHORT', old.COSTS[0], old.UNITS[0],
               account_factory=factory, persist_cash_close=False, final_day_target_zero=False)

def first_day(window=None, cls=FreshDailyReentrySimulator):
    sim = make(window or old.make_window(3, stress_mark=old.HALF_LOSS_MARK), cls)
    sim.advance_day({S: -.02})
    return sim

def prefix(sim, through):
    output = sim.result()
    return financial_prefix(output['minute'].drop('close_us').to_numpy(), output['trades'], output['funding'],
                            start_us=sim.start, through_us=through)

class FreshDailyTests(unittest.TestCase):
    def test_same_direction_only_next_new_daily_and_guard_exact_prefix(self):
        window = old.make_window(3, stress_mark=old.HALF_LOSS_MARK)
        new, guard = first_day(window), first_day(window, old.ProtectiveFullExitSimulator)
        self.assertEqual(new.account.snapshot(), guard.account.snapshot())
        self.assertEqual(new.reentry_events, [])
        lock = new.protective_locks[S]
        self.assertEqual(lock['flat_us'], 12 * MINUTE + 1)
        self.assertEqual(new.account.positions[S].quantity, D('0'))
        self.assertGreater(new.account.fees, 0)
        self.assertGreater(new.account.execution_cost, 0)
        self.assertEqual(new.account.trades[-1]['leg'], 'CLOSE')
        self.assertEqual(new.account.trades[-1]['event_us'], lock['flat_us'])
        new.advance_day({S: -.02}); guard.advance_day({S: -.02})
        event = new.reentry_events[0]
        self.assertEqual(event['kind'], 'SAME_DIRECTION_REENTRY_ALLOWED')
        self.assertEqual(event['signal_us'], DAY)
        self.assertGreater(event['signal_us'], event['flat_us'])
        self.assertNotEqual(new.account.positions[S].quantity, 0)
        self.assertEqual(guard.account.positions[S].quantity, 0)
        self.assertTrue(all(r['signal_us'] == DAY for r in new.account.trades if r['event_us'] > DAY))
        receipt = compare_prefix(prefix(new, DAY), prefix(guard, DAY), through_us=DAY)
        self.assertEqual(receipt['minute_rows'], 1440)

    def test_zero_opposite_and_same_fresh_targets_all_unlock(self):
        for desired in (D('0'), D('20'), D('-20')):
            with self.subTest(desired=desired):
                sim = first_day()
                signal = sim.protective_locks[S]['flat_us'] + 1
                sim.schedule({S: desired}, signal, 'DAILY_TARGET')
                self.assertNotIn(S, sim.protective_locks)
                self.assertEqual(sim.pending[S]['target'], desired)
                self.assertEqual(len(sim.reentry_events), 1)

    def test_same_clock_old_signal_and_non_daily_cannot_unlock(self):
        for kind in ('DAILY_TARGET', 'RISK_REDUCTION', 'POOL_EXIT', 'DATA_GAP_EXIT'):
            for offset in (-1, 0):
                sim = first_day()
                flat = sim.protective_locks[S]['flat_us']
                sim.schedule({S: D('20')}, flat + offset, kind)
                self.assertIn(S, sim.protective_locks)
                self.assertEqual(sim.reentry_events, [])
                self.assertNotIn(S, sim.pending)
        for kind in ('RISK_REDUCTION', 'POOL_EXIT', 'DATA_GAP_EXIT'):
            sim = first_day();sim.schedule({S: D('20')}, DAY, kind)
            self.assertIn(S, sim.protective_locks)

    def test_one_fine_step_residue_is_not_flat(self):
        sim = first_day()
        account = FineGridAccount()
        account.update_marks(0, {S: {'price': '1', 'close_us': 0, 'available_us': 0}})
        account.execute_fill(S, 'BUY', '10', MINUTE + 1, 0, 'synthetic-open',
            execution_mid_price='1', quote_available_us=MINUTE, available_quantity='10')
        account.update_marks(2 * MINUTE, {S: {'price': '1', 'close_us': 2 * MINUTE, 'available_us': 2 * MINUTE}})
        account.execute_fill(S, 'SELL', '9.99999999', 3 * MINUTE + 1, 2 * MINUTE, 'synthetic-close',
            execution_mid_price='1', quote_available_us=3 * MINUTE, available_quantity='9.99999999', reduce_only=True)
        self.assertEqual(account.positions[S].quantity, D('.00000001'))
        sim.account = account
        sim.protective_locks[S]['stopped_sign'] = 1
        sim.protective_locks[S]['flat_us'] = None
        sim.schedule({S: D('10')}, DAY, 'DAILY_TARGET')
        self.assertEqual(sim.pending[S]['kind'], 'PROTECTIVE_STOP')
        self.assertEqual(sim.pending[S]['target'], 0)
        self.assertEqual(sim.reentry_events, [])

    def test_partial_fills_daily_targets_never_supersede_live_exit(self):
        class Probe(FreshDailyReentrySimulator):
            saw_partial = False
            def attempt(self, stamp, row):
                result = super().attempt(stamp, row)
                if S in self.protective_locks and self.account.positions[S].quantity:
                    self.saw_partial = True
                    intent = self.pending[S]
                    self.schedule({S: D('20')}, stamp + 1, 'DAILY_TARGET')
                    if self.pending[S] is not intent or self.pending[S]['target'] != 0:
                        raise AssertionError('Partial protective exit overwritten')
                return result
        window = old.make_window(3, stress_mark=old.HALF_LOSS_MARK)
        window['market'][S]['quote_volume'][11:20] = 100_000
        sim = first_day(window, Probe)
        self.assertTrue(sim.saw_partial)
        self.assertEqual(sim.account.positions[S].quantity, 0)
        closes = [r for r in sim.account.trades if r['leg'] == 'CLOSE']
        self.assertGreater(len(closes), 1)
        self.assertEqual(sim.reentry_events, [])

    def test_same_clock_funding_batch_halts_before_trigger(self):
        window = old.make_window(3, stress_mark=old.HALF_LOSS_MARK)
        length = len(window['market'][S]['open'])
        window['symbols'] = ('BTCUSDT', S)
        window['daily'] = old.pl.concat([window['daily'], old.pl.DataFrame([
            dict(symbol='BTCUSDT', close_us=d * DAY, close=100.) for d in range(3)])])
        window['market']['BTCUSDT'] = {k: np.full(length, 1e6 if k == 'quote_volume' else 100.)
            for k in ('open', 'close', 'mark', 'quote_volume')}
        window['events'] = [dict(symbol='BTCUSDT', event_us=11 * MINUTE, raw_rate=0.),
                            dict(symbol=S, event_us=11 * MINUTE, raw_rate=-100.)]
        def factory(config, *, symbols):
            return USDTLinearPerpetualAccount(config, symbols=symbols,
                instrument_profiles={s: old.InstrumentProfile(quantity_step=D('100') if s == S else D('.001'))
                                     for s in symbols}, closing_min_notional_exempt=True)
        sim = make(window, factory=factory)
        sim.advance_day({'BTCUSDT': 0., S: -.02})
        self.assertEqual(sim.account.status, 'BANKRUPT_HALT')
        self.assertEqual(sim.protective_events, [])
        self.assertEqual(len(sim.funding_journal), 2)
        self.assertEqual(sim.reentry_events, [])

    def test_funding_batch_never_decides_between_two_symbols(self):
        window = old.make_window(3, stress_mark=old.HALF_LOSS_MARK)
        length = len(window['market'][S]['open'])
        window['symbols'] = ('BTCUSDT', S)
        window['daily'] = old.pl.concat([window['daily'], old.pl.DataFrame([
            dict(symbol='BTCUSDT', close_us=d * DAY, close=100.) for d in range(3)])])
        window['market']['BTCUSDT'] = {k: np.full(length, 1e6 if k == 'quote_volume' else 100.)
            for k in ('open', 'close', 'mark', 'quote_volume')}
        window['events'] = [dict(symbol='BTCUSDT', event_us=11 * MINUTE, raw_rate=0.),
                            dict(symbol=S, event_us=11 * MINUTE, raw_rate=-.1)]
        def factory(config, *, symbols):
            return USDTLinearPerpetualAccount(config, symbols=symbols,
                instrument_profiles={s: old.InstrumentProfile(quantity_step=D('100') if s == S else D('.001'))
                                     for s in symbols}, closing_min_notional_exempt=True)
        class Probe(FreshDailyReentrySimulator):
            checked = False
            def risk_schedule(self, stamp):
                result = super().risk_schedule(stamp)
                if stamp == 11 * MINUTE and self.event_cursor == 1:
                    self.checked = True
                    if self.protective_events:
                        raise AssertionError('Protection fired between funding events')
                return result
        new, guard = make(window, Probe, factory), make(window, old.ProtectiveFullExitSimulator, factory)
        new.advance_day({'BTCUSDT': 0., S: -.02});guard.advance_day({'BTCUSDT': 0., S: -.02})
        self.assertTrue(new.checked)
        self.assertEqual(new.account.snapshot(), guard.account.snapshot())
        self.assertEqual(new.protective_events, guard.protective_events)
        self.assertEqual(len(new.funding_journal), 2)
        self.assertEqual(next(e['event_us'] for e in new.protective_events if e['kind'] == 'FULL_EXIT_SIGNAL'),
                         11 * MINUTE)

    def test_halt_has_priority_even_after_paid_flat(self):
        for status in ('BANKRUPT_HALT', 'LIQUIDATION_REQUIRED_HALT', 'BOUND_BREACH_REDUCTION_REQUIRED'):
            sim = first_day();sim.account.status = status
            sim.schedule({S: D('-20')}, DAY, 'DAILY_TARGET')
            self.assertIn(S, sim.protective_locks)
            self.assertEqual(sim.reentry_events, [])
        sim = first_day();sim.stop = DAY
        sim.schedule({S: D('-20')}, DAY, 'DAILY_TARGET')
        self.assertEqual(sim.reentry_events, [])

    def test_terminal_never_reenters_and_old_protective_attempts_remain(self):
        sim = first_day();sim.terminal = True
        sim.schedule({S: D('-20')}, DAY, 'DAILY_TARGET')
        self.assertIn(S, sim.protective_locks)
        self.assertEqual(sim.reentry_events, [])
        window = old.make_window(stress_mark=old.HALF_LOSS_MARK, zero_capacity_after=10)
        new, guard = first_day(window), first_day(window, old.ProtectiveFullExitSimulator)
        compare_prefix(prefix(new, None), prefix(guard, None), through_us=None)
        self.assertEqual(new.pending[S]['kind'], 'PROTECTIVE_STOP')
        self.assertEqual(new.pending[S]['attempts'], guard.pending[S]['attempts'])
        self.assertEqual(new.terminal_attempt_observations, {})
        self.assertEqual(new.reentry_events, [])

    def test_terminal_protective_attempts_are_classified_separately(self):
        window = old.make_window(stress_mark=old.HALF_LOSS_MARK)
        window['market'][S]['quote_volume'][10:1434] = 0
        window['market'][S]['quote_volume'][1434:] = 100_000
        new, guard = first_day(window), first_day(window, old.ProtectiveFullExitSimulator)
        compare_prefix(prefix(new, None), prefix(guard, None), through_us=None)
        records = list(new.terminal_attempt_observations.values())
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]['kind'], 'PROTECTIVE_STOP')
        self.assertEqual(records[0]['actual_attempts'], 3)
        self.assertEqual(new.account.positions[S].quantity, 0)
        self.assertEqual(new.reentry_events, [])

    def test_fine_grid_full_simulator_prefix_and_paid_flat(self):
        symbols = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
        window = old.make_window(2, stress_mark=old.HALF_LOSS_MARK)
        window['symbols'] = symbols
        length = len(window['market'][S]['open'])
        for symbol in symbols:
            if symbol == S: continue
            window['market'][symbol] = {k: np.full(length, 1e6 if k == 'quote_volume' else 100.)
                for k in ('open', 'close', 'mark', 'quote_volume')}
        window['daily'] = old.pl.DataFrame([dict(symbol=symbol, close_us=d * DAY,
            close=(old.BASE if d == 0 else old.HALF_LOSS_MARK) if symbol == S else 100.)
            for d in range(2) for symbol in symbols])
        targets = dict.fromkeys(symbols, 0.);targets[S] = -.02
        new, guard = make(window, factory=FineGridAccount), make(window, old.ProtectiveFullExitSimulator, FineGridAccount)
        new.advance_day(targets);guard.advance_day(targets)
        self.assertEqual(new.account.positions[S].quantity, 0)
        self.assertTrue(all(p.quantity_step == D('.00000001') for p in new.account.instrument_profiles.values()))
        new.advance_day(targets);guard.advance_day(targets)
        self.assertEqual(new.reentry_events[0]['signal_us'], DAY)
        compare_prefix(prefix(new, DAY), prefix(guard, DAY), through_us=DAY)
        self.assertTrue(any(t['event_us'] > DAY and t['leg'] == 'OPEN' for t in new.account.trades))

    def test_terminal_regular_orders_record_actual_kind(self):
        sim = make(old.make_window())
        sim.advance_day({S: -.02})
        self.assertTrue(sim.terminal)
        self.assertTrue(sim.terminal_attempt_observations)
        self.assertTrue(all(r['kind'] == 'TERMINAL' for r in sim.terminal_attempt_observations.values()))
        self.assertTrue(all(r['actual_attempts'] <= 5 for r in sim.terminal_attempt_observations.values()))
        self.assertEqual(sim.account.positions[S].quantity, 0)

    def test_original_cap_five_attempt_STOP_exact_guard_path(self):
        window = old.make_window(stress_mark=old.HALF_LOSS_MARK, zero_capacity_after=10)
        new, guard = make(window), make(window, old.ProtectiveFullExitSimulator)
        new.advance_day({S: -.30});guard.advance_day({S: -.30})
        compare_prefix(prefix(new, None), prefix(guard, None), through_us=None)
        self.assertEqual(new.completion, 'NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION')
        self.assertEqual(new.stop, guard.stop)
        self.assertEqual(new.reentry_events, [])
        attempts = [r for r in new.rejections if r.get('kind') == 'RISK_REDUCTION']
        self.assertTrue(attempts)

    def test_repeated_trigger_after_new_entry_and_duplicate_schedule(self):
        window = old.make_window(3, stress_mark=old.HALF_LOSS_MARK)
        for field in ('open', 'close', 'mark'):
            window['market'][S][field][1450:] = 1.2
        sim = first_day(window)
        sim.advance_day({S: -.02})
        self.assertEqual(sum(e['kind'] == 'FULL_EXIT_SIGNAL' for e in sim.protective_events), 2)
        self.assertEqual(sum(e['kind'] == 'FULL_EXIT_FLAT' for e in sim.protective_events), 2)
        self.assertEqual(len(sim.reentry_events), 1)
        flat = sim.protective_locks[S]['flat_us']
        sim.schedule({S: D('-20')}, flat, 'DAILY_TARGET')
        sim.schedule({S: D('-20')}, flat, 'DAILY_TARGET')
        self.assertEqual(len(sim.reentry_events), 1)

    def test_no_guard_trigger_matches_native_and_old_guard_exactly(self):
        window = old.make_window(2)
        sims = [make(window, c) for c in (FreshDailyReentrySimulator, old.ProtectiveFullExitSimulator, NativeDailySimulator)]
        for sim in sims:
            sim.advance_day({S: -.02});sim.advance_day({S: .02})
        for sim in sims[1:]:
            compare_prefix(prefix(sims[0], None), prefix(sim, None), through_us=None)
            self.assertEqual(sims[0].account.snapshot(), sim.account.snapshot())
        self.assertEqual(sims[0].reentry_events, [])

    def test_opposite_daily_after_flat_keeps_old_financial_path(self):
        window = old.make_window(3, stress_mark=old.HALF_LOSS_MARK)
        new, guard = first_day(window), first_day(window, old.ProtectiveFullExitSimulator)
        new.advance_day({S: .02});guard.advance_day({S: .02})
        compare_prefix(prefix(new, None), prefix(guard, None), through_us=None)
        self.assertEqual(new.account.snapshot(), guard.account.snapshot())

    def test_snapshot_roundtrip_and_identity_fail_closed(self):
        window = old.make_window(3, stress_mark=old.HALF_LOSS_MARK)
        sim = first_day(window);sim.advance_day({S: -.02})
        snapshot = sim.snapshot()
        restored = FreshDailyReentrySimulator.from_snapshot(snapshot, window, account_class=USDTLinearPerpetualAccount)
        self.assertEqual(restored.state_hash(), sim.state_hash())
        restored.advance_day({S: -.02});sim.advance_day({S: -.02})
        self.assertEqual(restored.state_hash(), sim.state_hash())
        snapshot['daily_reentry_policy']['policy_id'] = 'wrong'
        with self.assertRaises(ValueError):
            FreshDailyReentrySimulator.from_snapshot(snapshot, window, account_class=USDTLinearPerpetualAccount)

    def test_prefix_acceptance_catches_every_bit_and_journal(self):
        p = {'minute': np.zeros((2, 3), dtype=np.float64), 'trades': [{'event_us': 1}], 'funding': [{'event_us': 2}]}
        compare_prefix(p, deepcopy(p), through_us=2)
        for key in ('minute', 'trades', 'funding'):
            changed = deepcopy(p)
            if key == 'minute': changed[key][0, 0] = -0.0
            else: changed[key][0]['event_us'] += 1
            with self.assertRaises(ValueError): compare_prefix(p, changed, through_us=2)
        negative_zero = deepcopy(p);positive_zero = deepcopy(p)
        negative_zero['trades'][0]['value'] = -0.0;positive_zero['trades'][0]['value'] = 0.0
        with self.assertRaises(ValueError): compare_prefix(negative_zero, positive_zero, through_us=2)
        self.assertEqual(financial_prefix(np.zeros((3, 2)), [{'event_us': 2}, {'event_us': 3}], [],
            start_us=0, through_us=2 * MINUTE)['minute'].shape, (2, 2))

    def test_no_GO_cli_and_direct_worker_fail_before_history(self):
        import subprocess
        for arguments in ([], ['--worker-case', 'Y2024_STATIC50']):
            process = subprocess.run([sys.executable, str(HERE / 'run_cases.py'), *arguments],
                cwd=ROOT, capture_output=True, text=True, check=False)
            self.assertEqual(process.returncode, 2)
            self.assertNotIn('WALLET_STARTED', process.stdout)
        self.assertFalse(any(HERE.glob('state*')))

    def test_lossless_minute_loader_uses_frozen_codec(self):
        from prefix_acceptance import sha
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            recovery = Path(temporary)
            a = np.arange(72., dtype=np.float64).reshape(2, 36)
            np.savez_compressed(recovery / 'DAY_0000.npz', minute_chunk=a)
            pointer = {'completed_minutes': 2, 'chunks': [{'path': 'DAY_0000.npz',
                'rows': 2, 'columns': 36, 'SHA256': sha(recovery / 'DAY_0000.npz')}]}
            (recovery / 'POINTER.json').write_text(json.dumps(pointer))
            self.assertEqual(load_minute(recovery).tobytes(), a.tobytes())

    def test_freeze_tamper_and_review_gate(self):
        verify()
        with self.assertRaises((FileNotFoundError, RuntimeError)):verify(require_review=True)
        with tempfile.TemporaryDirectory(dir=HERE.parent) as temporary:
            root = Path(temporary) / HERE.name
            shutil.copytree(HERE, root)
            with (root / 'daily_reentry_policy.py').open('a') as file:file.write('\n# tamper\n')
            with self.assertRaisesRegex(ValueError, 'prepared bytes changed'):verify(root)

    def test_task_reservation_requires_parent_release_not_absent_PID(self):
        with tempfile.TemporaryDirectory(dir=HERE) as temporary:
            path = Path(temporary) / 'RELEASE.json'
            self.assertEqual(task_reservation(path)['task_reserved_bytes'], 2_000_000_000)
            self.assertEqual(task_reservation(path)['task_busy_cpus'], [8])
            path.write_text(json.dumps({'status': 'PID_GONE'}))
            with self.assertRaises(RuntimeError): task_reservation(path)
        self.assertTrue(task_reservation()['pack_task_released'])
        self.assertEqual(task_reservation()['task_reserved_bytes'], 0)

    def test_exact_three_cases_and_shared_resource_pack_reservation(self):
        self.assertEqual(len(reentry_preflight.bindings()['cases']), 3)
        base = {'memory': {'host_used': 1_000_000_000, 'cgroup_limit_verified': False}, 'allowed_cpus': [0, 1, 8]}
        external = {'guard_pack_processes': [{'pid': 123, 'allowed_cpus': [8]}],
                    'prior_historical_processes': [], 'external_reserved_bytes': 2_000_000_000,
                    'external_busy_cpus': [8]}
        guard = SimpleNamespace(WORKER_RSS_LIMIT=2_000_000_000, HOST_USED_LIMIT=8_000_000_000)
        result = check_external(base, external, 1, guard)
        self.assertEqual(result['allowed_cpus'], [0, 1])
        self.assertEqual(result['new_financial_committed_bytes'], 4_000_000_000)
        base['memory']['host_used'] = 3_000_000_000
        with self.assertRaises(RuntimeError):check_external(base, external, 1, guard)
        external['prior_historical_processes'] = [123]
        with self.assertRaises(RuntimeError):check_external(base, external, 0, guard)

if __name__ == '__main__':
    unittest.main(verbosity=2)
