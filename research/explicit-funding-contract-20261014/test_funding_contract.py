import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from funding_contract import ContractError, check


def fixture():
    return {'raw_rate': '0.0001', 'unit': 'fraction', 'conversion': 'none',
            'signed_base_quantity': '2', 'mark_price': '50000',
            'expected_cashflow': '-10', 'provenance': {
                'source_kind': 'synthetic', 'source_reference': 'synthetic-example-v1',
                'field': 'example_rate', 'record_id': 'example-event-1',
                'unit_basis': 'synthetic fixture explicitly defines a fraction',
                'product': 'linear_quote_settled', 'rate_basis': 'per_settlement'}}


class ContractTests(unittest.TestCase):
    def test_long_short_sign_matrix(self):
        for qty, rate, expected in [('2','0.0001','-10'),('-2','0.0001','10'),
                                    ('2','-0.0001','10'),('-2','-0.0001','-10'),
                                    ('0','0.0001','0'),('2','0','0')]:
            with self.subTest(qty=qty, rate=rate):
                p = fixture(); p.update(signed_base_quantity=qty, raw_rate=rate, expected_cashflow=expected)
                self.assertEqual(check(p)['status'], 'PASS')

    def test_percent_requires_explicit_conversion(self):
        p = fixture(); p.update(raw_rate='0.01', unit='percent')
        with self.assertRaises(ContractError): check(p)
        p['conversion'] = 'explicit_percent_divide_100'
        r = check(p)
        self.assertEqual(r['status'], 'PASS')
        self.assertEqual(r['applied_scale'], '0.01')

    def test_100x_discrepancy_is_not_corrected(self):
        p = fixture(); p['raw_rate'] = '0.01'
        r = check(p)
        self.assertEqual(r['status'], 'FAIL')
        self.assertEqual(r['discrepancy'], 'computed_is_100x_expected_no_auto_correction')
        self.assertEqual(r['signed_cashflow_quote'], '-1000.00')
        p = fixture(); p['expected_cashflow'] = '-1000'
        self.assertEqual(check(p)['discrepancy'], 'expected_is_100x_computed_no_auto_correction')

    def test_percent_sign_matrix_and_scale_mismatch(self):
        for qty, rate, expected in [('2','0.01','-10'),('-2','0.01','10'),
                                    ('2','-0.01','10'),('-2','-0.01','-10')]:
            with self.subTest(qty=qty, rate=rate):
                p = fixture(); p.update(signed_base_quantity=qty, raw_rate=rate,
                    expected_cashflow=expected, unit='percent',
                    conversion='explicit_percent_divide_100')
                self.assertEqual(check(p)['status'], 'PASS')
                p.update(unit='fraction', conversion='none')
                r = check(p)
                self.assertEqual(r['status'], 'FAIL')
                self.assertEqual(r['discrepancy'], 'computed_is_100x_expected_no_auto_correction')

    def test_bad_units(self):
        for unit in ['auto', 'UNCONFIRMED', '', None, 'bps']:
            p = fixture(); p['unit'] = unit
            with self.subTest(unit=unit), self.assertRaises(ContractError): check(p)

    def test_invalid_numeric_inputs(self):
        for field in ['raw_rate','signed_base_quantity','mark_price','expected_cashflow']:
            for value in [0.0001, True, None, 'NaN', 'Infinity', '1e1000000', '0.01%', '', '1'*25]:
                p = fixture(); p[field] = value
                with self.subTest(field=field,value=value), self.assertRaises(ContractError): check(p)

    def test_positive_mark_required(self):
        for mark in ['0','-1']:
            p = fixture(); p['mark_price'] = mark
            with self.assertRaises(ContractError): check(p)

    def test_all_provenance_required(self):
        for key in fixture()['provenance']:
            p = fixture(); del p['provenance'][key]
            with self.subTest(key=key), self.assertRaises(ContractError): check(p)

    def test_no_certification_by_declaration(self):
        p = fixture(); p['provenance']['source_kind'] = 'declared_source'
        r = check(p)
        self.assertFalse(r['historical_dataset_certified'])
        self.assertFalse(r['provenance_verified'])
        p['provenance']['source_kind'] = 'certified'
        with self.assertRaises(ContractError): check(p)

    def test_wrong_product_or_rate_basis(self):
        for key, value in [('product','inverse'),('rate_basis','annualized'),('unit_basis',' ')]:
            p = fixture(); p['provenance'][key] = value
            with self.assertRaises(ContractError): check(p)

    def test_extra_fields_fail_closed(self):
        p = fixture(); p['scale'] = '0.01'
        with self.assertRaises(ContractError): check(p)

    def test_wrong_sign_mismatch(self):
        p = fixture(); p['expected_cashflow'] = '10'
        self.assertEqual(check(p)['status'], 'FAIL')

    def test_input_unchanged(self):
        p = fixture(); before = copy.deepcopy(p); check(p)
        self.assertEqual(p, before)

    def test_cli_exit_codes(self):
        script = str(Path(__file__).with_name('funding_contract.py'))
        for payload, code in [(fixture(),0), ({**fixture(),'expected_cashflow':'10'},1), ({},2)]:
            r = subprocess.run([sys.executable,script],input=json.dumps(payload),text=True,capture_output=True)
            self.assertEqual(r.returncode, code, r.stderr)
            self.assertFalse(json.loads(r.stdout)['historical_dataset_certified'])
        r = subprocess.run([sys.executable,script],input='{"unit":"percent","unit":"fraction"}',text=True,capture_output=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn('duplicate', r.stdout)


if __name__ == '__main__': unittest.main()
