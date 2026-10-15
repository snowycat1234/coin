"""Saved generated probe verification only. Never launches a process."""
from hashlib import sha256
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_common as c
import cs_finance_gate as gate
import cs_process_runtime as runtime
import profile_cs_generated as profile
P=c.HERE/'GENERATED_POOL_PROBE_001'
EXPECTED='15ce21c98c5fa39d4793bcbb8e73938a2c0cd5cb334df3f2eb26c5d852fbfb9d'
CODE='86da3b35cca4d241a638825cb46c75e153833b980f4474be660abd9427b1bad2'


class FinalProbeReview(unittest.TestCase):
    def test_exact_final_probe_full_saved_native40_and_source_guard_evidence(self):
        raw=(P/'GENERATED_POOL_PROFILE.json').read_bytes();self.assertEqual(c.sha(raw),EXPECTED)
        report=c.exact_object(raw)
        self.assertEqual(report['source_code_manifest_SHA256'],gate.SOURCE_CODE_SHA256)
        self.assertEqual(gate.code_identity(),CODE);self.assertEqual(report['maximum_observed_live_workers'],2)
        self.assertEqual(report['coordinator_CPU_affinity'],[4,5]);self.assertEqual(report['limits'],runtime.LIMITS)
        self.assertTrue(report['generated_only']);self.assertFalse(report['annual_resource_envelope_certified'])
        self.assertEqual(max(len(row['workers']) for row in report['observations']),2)
        self.assertLess(max(row['aggregate_live_RSS_bytes'] for row in report['observations']),3500000000)
        self.assertEqual({row['CPU'] for row in report['cases']},{4,5})
        for row in report['cases']:
            path=P/row['cell_id'];receipt=profile.validate(path,row['cell_id'])
            self.assertEqual(c.sha((path/'TERMINAL_CHECKPOINT.json').read_bytes()),row['checkpoint_SHA256'])
            self.assertEqual(receipt['financial_code_manifest_SHA256'],CODE)
            self.assertEqual(receipt['generated_minutes'],2880);self.assertGreater(receipt['paid_trade_rows'],0)
            self.assertTrue(receipt['lease_FD_inherited']);self.assertEqual(receipt['actual_affinity'],[row['CPU']])
            self.assertTrue(all(a==[row['CPU']] for a in receipt['all_TID_affinities']))
            self.assertTrue(all(v=='1' for v in receipt['thread_environment'].values()))
            self.assertLess(receipt['max_RSS_bytes'],2000000000);self.assertLess(receipt['wall_seconds'],600)
            self.assertLess(receipt['CPU_seconds'],600)
            self.assertEqual(receipt['historical_financial_runs'],0);self.assertEqual(receipt['actual_source_bodies_read'],0)
    def test_no_actual_authority_source_targets_claims_or_annual_resource_certification(self):
        report=c.exact_object((P/'GENERATED_POOL_PROFILE.json').read_bytes())
        for key in ('historical_account_objects_constructed','historical_financial_runs','actual_source_bodies_read',
                    'actual_claims_created','actual_targets_generated'):
            self.assertEqual(report[key],0)
        self.assertFalse(report['annual_resource_envelope_certified']);self.assertFalse(report['host_quota_guaranteed'])

if __name__=='__main__':unittest.main(verbosity=2)
