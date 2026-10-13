"""Synthetic accounting and inference tests only; never load real input files."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import numpy as np

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cs_sma_score', HERE / 'score.py')
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


class AccountingTests(unittest.TestCase):
    def fixture(self, count=12):
        d = np.arange(count, dtype=np.int64) * score.DAY
        prices = np.column_stack([100 * 1.01 ** np.arange(count + 1),
                                  50 * .994 ** np.arange(count + 1),
                                  5 + .02 * np.arange(count + 1),
                                  .8 * 1.005 ** np.arange(count + 1),
                                  .12 * .998 ** np.arange(count + 1)])
        weights = np.tile([.15, -.12, .10, -.10, 0.], (count, 1))
        weights[count // 2:, 0] = -.15
        weights[count // 3, :] = 0
        funding = np.tile([.01, -.004, 0., .0001, -.00002], (count, 1))
        good = np.ones((count, 5), bool)
        return d, weights, prices[:-1], prices[1:], funding, good

    def test_decimal_saved_quantity_nav_price_cost_funding_and_terminal(self):
        d, w, p0, p1, fp, valid = self.fixture()
        metrics, rows = score.reference(d, w, p0, p1, fp, valid)
        saved = json.loads(json.dumps(rows))
        audit = score.decimal_audit(d, w, p0, p1, fp, metrics, saved)
        self.assertTrue(audit['passed'], audit)
        self.assertGreater(metrics['terminal_cost_proxy_USDT'], 0)
        self.assertEqual(metrics['positions'], [0.] * 5)
        self.assertAlmostEqual(metrics['net_USDT'], metrics['price_pnl'] - metrics['trading_cost'] + metrics['funding_cash'], places=9)

    def test_independent_audit_detects_modified_quantity_and_nav(self):
        d, w, p0, p1, fp, valid = self.fixture()
        metrics, rows = score.reference(d, w, p0, p1, fp, valid)
        rows[3]['held_quantity'][1] += .01
        rows[5]['nav_after'] += .10
        self.assertFalse(score.decimal_audit(d, w, p0, p1, fp, metrics, rows)['passed'])

    def test_positive_funding_debits_long_credits_short(self):
        d = np.array([0], dtype=np.int64)
        prices = np.full((1, 5), 100.)
        fp = np.full((1, 5), .02)
        good = np.ones((1, 5), bool)
        for sign in (1, -1):
            w = np.array([[sign * .12, 0, 0, 0, 0]])
            metrics, rows = score.reference(d, w, prices, prices, fp, good)
            self.assertEqual(np.sign(metrics['funding_cash']), -sign)
            self.assertAlmostEqual(rows[0]['funding_debit_proxy'], sign * .24)
            self.assertAlmostEqual(rows[0]['trading_cost_proxy'], 2 * 1200 * score.COST)
            self.assertTrue(score.decimal_audit(d, w, prices, prices, fp, metrics, rows)['passed'])

    def test_negative_funding_credits_long_debits_short(self):
        d, w, p0, p1, fp, valid = self.fixture(1)
        p1[:] = p0
        w[:] = 0
        w[0, 0] = .12
        fp[:] = -.02
        metrics, rows = score.reference(d, w, p0, p1, fp, valid)
        self.assertGreater(metrics['funding_cash'], 0)
        self.assertTrue(score.decimal_audit(d, w, p0, p1, fp, metrics, rows)['passed'])

    def test_reversal_turnover_two_sides_and_paid_terminal(self):
        d = np.array([0, score.DAY], dtype=np.int64)
        w = np.zeros((2, 5)); w[:, 0] = [.12, -.12]
        prices = np.full((2, 5), 100.)
        metrics, rows = score.reference(d, w, prices, prices, np.zeros_like(prices), np.ones_like(prices, bool))
        self.assertAlmostEqual(rows[0]['turnover_USDT'], 1200)
        self.assertAlmostEqual(rows[1]['turnover_USDT'], 1200 + rows[1]['nav_before'] * .12)
        self.assertAlmostEqual(metrics['terminal_cost_proxy_USDT'], rows[1]['nav_before'] * .12 * score.COST)
        self.assertTrue(score.decimal_audit(d, w, prices, prices, np.zeros_like(prices), metrics, rows)['passed'])

    def test_cash_unknown_assets_are_not_fabricated_or_charged(self):
        d = np.array([0, score.DAY], dtype=np.int64)
        w = np.zeros((2, 5))
        missing = np.full((2, 5), np.nan)
        metrics, rows = score.reference(d, w, missing, missing, missing, np.zeros_like(w, bool))
        self.assertEqual(metrics['net_USDT'], 0)
        self.assertEqual(metrics['trading_cost'], 0)
        self.assertTrue(score.decimal_audit(d, w, missing, missing, missing, metrics, rows)['passed'])

    def test_owned_missing_interval_stops_full_calendar_instead_of_skipping(self):
        d, w, p0, p1, fp, valid = self.fixture()
        valid[5, 1] = False
        metrics, rows = score.reference(d, w, p0, p1, fp, valid)
        self.assertEqual(metrics['days'], 5)
        self.assertIsNone(metrics['net_USDT'])
        self.assertFalse(metrics['hypothetical_cost_terminal'])
        self.assertFalse(score.decimal_audit(d, w, p0, p1, fp, metrics, rows)['passed'])

    def test_cash_exit_missing_execution_price_stops(self):
        d, w, p0, p1, fp, valid = self.fixture()
        w[1] = 0
        p0 = p0.copy()
        p0[1, 0] = np.nan
        metrics, _ = score.reference(d, w, p0, p1, fp, valid)
        self.assertEqual(metrics['days'], 1)
        self.assertIn('entry/exit', metrics['stop']['reason'])

    def test_synthetic_full365_decimal_accumulation(self):
        d, w, p0, p1, fp, valid = self.fixture(365)
        metrics, rows = score.reference(d, w, p0, p1, fp, valid)
        audit = score.decimal_audit(d, w, p0, p1, fp, metrics, rows)
        self.assertTrue(audit['passed'], audit)
        self.assertEqual(metrics['days'], 365)

    def test_exact_shared_indices_circular14day_and_seed_replay(self):
        for seed in score.SEEDS.values():
            indices = score.bootstrap_indices(365, seed)
            np.testing.assert_array_equal(indices, score.bootstrap_indices(365, seed))
            self.assertEqual(indices.shape, (1000, 365))
            for start in range(0, 365, 14):
                block = indices[:, start:min(start + 14, 365)]
                np.testing.assert_array_equal(np.diff(block, axis=1) % 365, np.ones((1000, block.shape[1] - 1), dtype=np.int64))
        self.assertFalse(np.array_equal(score.bootstrap_indices(365, 811760), score.bootstrap_indices(365, 811761)))

    def test_bootstrap_saved_samples_replay_and_deterministic_bytes(self):
        x = np.linspace(-.005, .005, 365)
        returns = {arm: x + index * .00001 for index, arm in enumerate(score.ARMS)}
        indices = score.bootstrap_indices(365, 811760)
        report, arrays = score.paired_inference(returns, indices)
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / 'first.npz'; second = Path(directory) / 'second.npz'
            score.save_npz(first, **arrays); score.save_npz(second, **arrays)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            with np.load(first, allow_pickle=False) as restored:
                replay, _ = score.paired_inference(returns, restored['indices'])
                self.assertEqual(report, replay)
                for control in score.CONTROLS:
                    samples = restored['sample_mean_AGREEMENT_minus_' + control]
                    self.assertGreater(samples.min(), 0)

    def test_diagnostic_cannot_rescue_failed_primary_gates(self):
        years = {}
        for year in score.YEARS:
            arms = {arm: dict(metrics=dict(days=365, hypothetical_cost_terminal=True,
                          net_USDT=100 if arm != 'AGREEMENT' else -10, drawdown=.01),
                          decimal_audit=dict(passed=True)) for arm in score.ARMS}
            arms['AGREEMENT_NO_REALLOCATION']['metrics']['net_USDT'] = 100000
            inference = {control: dict(CI_lower_positive=False) for control in score.CONTROLS}
            years[str(year)] = dict(arms=arms, inference=inference)
        result = score.protocol_gates(years, True)
        self.assertFalse(result['all_frozen_gates_pass'])
        self.assertFalse(result['gates']['primary_positive_net_both_years'])
        self.assertEqual(result['primary'], 'AGREEMENT')

    def test_actual_runner_denies_absent_remote_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'publication.json'
            path.write_text(json.dumps(dict(remote_verified=False)))
            with self.assertRaisesRegex(ValueError, 'prohibited'):
                score.run(path, Path(directory) / 'results')


if __name__ == '__main__':
    unittest.main(verbosity=2)
