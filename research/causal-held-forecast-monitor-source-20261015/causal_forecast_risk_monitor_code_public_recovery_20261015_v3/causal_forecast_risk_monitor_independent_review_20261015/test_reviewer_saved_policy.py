"""Pure generated audit export and resealed-policy negative probes."""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from generated_helpers import f, make_sim, seed_paid, trigger
sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'causal_forecast_risk_monitor_20261015'))
import run_forecast as runner
import forecast_entry as entry
from test_core import active_fixture

class ReviewerSavedPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        w,rows,d,t=active_fixture()
        sim,g=f.construct_case(w,rows,d,t,generated_scope=f.GENERATED)
        sim.advance_day()
        cls.audit=f.V2.OWNED.export_tree(sim.account.snapshot())
        cls.result=f.case_result(sim,g)
        cls.result.pop('minute');cls.result['targets']=cls.result['targets'].to_dicts()
        cls.result=f.V2.OWNED.export_tree(cls.result)

    def test_exact_generated_policy_and_active_cohort_are_json_exportable(self):
        self.assertTrue(runner.validate_policy_evidence(self.audit,self.result,historical=False))
        json.dumps(self.audit,allow_nan=False);json.dumps(self.result,allow_nan=False)
        sim,g,_=make_sim(.5)
        seed_paid(sim.account,{'BTCUSDT':'.05'},sim.start)
        trigger(sim)
        snap=f.V2.OWNED.export_tree(sim.account.snapshot())
        self.assertIsNotNone(snap['forecast_active'])
        self.assertTrue(all(type(v) is str for v in snap['forecast_active']['targets'].values()))
        json.dumps(snap,allow_nan=False)

    def test_defining_policy_changes_are_rejected_even_if_journals_are_resealed(self):
        modifications=[
            ('audit',lambda a,r:a['contract'].__setitem__('topup_enabled',True)),
            ('common',lambda a,r:r['common_execution_policy'].__setitem__('no_autonomous_rerisking',False)),
            ('budget',lambda a,r:r['forecast_risk_monitor'].__setitem__('original_mid_budget',.11)),
            ('transfer',lambda a,r:a['transfer_journal'].append({'quantity':'1'})),
            ('transfer_identity',lambda a,r:a['transfer_ids'].__setitem__('GHOST','1')),
            ('economics',lambda a,r:r['continuation_economic_report']['transfers'].append({'quantity':'1'})),
            ('wrong_history',lambda a,r:a['contract'].__setitem__('historical_execution_admitted',True)),
        ]
        for name,change in modifications:
            with self.subTest(name=name):
                a,r=deepcopy(self.audit),deepcopy(self.result);change(a,r)
                with self.assertRaises(ValueError):runner.validate_policy_evidence(a,r,historical=False)
        for field,bad in [('alpha',.999),('sigma',float('inf')),('current_variance',float('inf')),
                          ('projected_variance',float('-inf')),('projected_variance',-1.)]:
            with self.subTest(field=field,bad=bad):
                a,r=deepcopy(self.audit),deepcopy(self.result)
                created=next(x for x in a['forecast_journal'] if x['kind']=='COHORT_CREATED')
                created[field]=bad;r['forecast_risk_monitor']['journal']=deepcopy(a['forecast_journal'])
                with self.assertRaises(ValueError):runner.validate_policy_evidence(a,r,historical=False)

    def test_conflicting_cached_callback_module_cannot_receive_sealed_arguments(self):
        foreign=SimpleNamespace(__file__='/GENERATED_FOREIGN_MODULE/forecast_historical.py',
                                construct_historical_case=lambda *a,**k: self.fail('FOREIGN_CALLBACK_CALLED'))
        with patch.dict(sys.modules,{'forecast_historical':foreign}):
            with self.assertRaisesRegex(ValueError,'EXACT_LOCAL_FORECAST_HISTORICAL_CALLBACK'):
                entry._default_constructor_callback(scope=object(),preparation={},window={},source_rows=(),decisions=(),targets=(),captured={})

    def test_pool_and_controller_lease_reuse_exact_frozen_code_objects(self):
        self.assertIs(runner.run_pool.__code__,runner.R.run_pool.__code__)
        self.assertIs(runner._POOL_GLOBALS['_run_pool'].__code__,runner.R._run_pool.__code__)
        self.assertIs(runner.controller_lease.__wrapped__.__code__,runner.R.controller_lease.__wrapped__.__code__)
        self.assertIs(runner.run_pool.__globals__,runner.controller_lease.__wrapped__.__globals__)
        self.assertEqual(runner._POOL_GLOBALS['MANIFEST_SHA256'],entry.MANIFEST_SHA256)
        self.assertIsNone(runner._POOL_GLOBALS['_CONTROLLER_LEASE_FD'])

if __name__=='__main__':unittest.main()
