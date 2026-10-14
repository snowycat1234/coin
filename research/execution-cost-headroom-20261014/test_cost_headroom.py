import copy
import json
import unittest
from decimal import Decimal as D
from fractions import Fraction
from pathlib import Path
from analyze_cost_headroom import analyze, sensitivity, run
ROOT=Path(__file__).resolve().parent

class ArithmeticTests(unittest.TestCase):
    def test_baseline(self):
        self.assertEqual(sensitivity(D(100),D(10),D(20))['scenarios']['1']['static_net_PnL_USDT'],100)
    def test_three_times(self):
        self.assertEqual(sensitivity(D(100),D(10),D(20))['scenarios']['3']['static_net_PnL_USDT'],40)
    def test_fractional_multiplier(self):
        self.assertEqual(sensitivity(D('0.13'),D('0.01'),D('0.02'))['scenarios']['1.5']['static_net_PnL_USDT'],D('0.115'))
    def test_breakeven(self):
        self.assertEqual(sensitivity(D(100),D(10),D(15))['breakeven_multiplier'],5)
    def test_zero_cost(self):
        self.assertIsNone(sensitivity(D(100),D(0),D(0))['breakeven_multiplier'])
    def test_negative_charge(self):
        with self.assertRaises(ValueError): sensitivity(D(1),D(-1),D(2))
    def test_already_losing(self):
        self.assertEqual(sensitivity(D(-20),D(10),D(10))['breakeven_multiplier'],0)
    def fixture(self):
        return json.loads((ROOT/'inputs/2023_csh_FINANCIAL.json').read_text())
    def test_wrong_funding_sign_rejected(self):
        d=self.fixture(); d['decimal_strings']['funding_USDT']=str(-D(d['decimal_strings']['funding_USDT']))
        with self.assertRaises(ValueError): analyze(d)
    def test_incomplete_rejected(self):
        d=self.fixture(); d['complete_calendar']=False
        with self.assertRaises(ValueError): analyze(d)
    def test_unpaid_rejected(self):
        d=self.fixture(); d['decimal_strings']['unpaid_liability']='1'
        with self.assertRaises(ValueError): analyze(d)
    def test_capital_mismatch_rejected(self):
        d=self.fixture(); d['paid_NAV_decimal']='1'
        with self.assertRaises(ValueError): analyze(d)
    def test_all_saved_sources_and_independent_rationals(self):
        r=run(ROOT)
        for s in json.loads((ROOT/'SOURCE_CATALOG.json').read_text()):
            v=json.loads((ROOT/s['input_file']).read_text())['decimal_strings']
            n,f,e,u,g=[Fraction(v[k]) for k in ['net_PnL','fees_USDT','execution_cost_USDT','funding_USDT','gross_PnL_same_quantities']]
            a=r['arms'][s['id']]
            self.assertLessEqual(abs(n-(g-f-e+u)),Fraction('1e-30'))
            for m in ('1','1.5','2','3'):
                self.assertEqual(Fraction(a['scenarios'][m]['static_net_PnL_USDT']),n-(Fraction(m)-1)*(f+e))
            self.assertEqual(Fraction(a['breakeven_exact_numerator'])/Fraction(a['breakeven_exact_denominator']),1+n/(f+e))
        for year in ('2023','2025'):
            p=r['paired'][year]; g,c=[r['arms'][f'{year}_{a}'] for a in ('grid','cash')]
            for m in ('1','1.5','2','3'):
                self.assertEqual(p['scenarios_GRID_minus_CASH_USDT'][m],g['scenarios'][m]['static_net_PnL_USDT']-c['scenarios'][m]['static_net_PnL_USDT'])
            eq=Fraction(p['equality_exact_numerator'])/Fraction(p['equality_exact_denominator'])
            self.assertEqual(Fraction(p['baseline_GRID_minus_CASH_USDT'])-(eq-1)*Fraction(p['GRID_minus_CASH_cost_USDT']),0)

if __name__=='__main__': unittest.main(verbosity=2)
