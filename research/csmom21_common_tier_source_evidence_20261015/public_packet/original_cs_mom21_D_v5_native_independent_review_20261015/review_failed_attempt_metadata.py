"""Saved failure/code metadata only. No GO bodies, sources, targets or replay."""
from hashlib import sha256
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parent.parent
V4=ROOT/'original_cs_mom21_D_20261015_v4'
ATTEMPT=V4/'financial_attempts/FIRST6_attempt001'
AUDITDIR=ROOT/'original_cs_mom21_D_v4_FIRST6_saved_results_independent_review_20261015'
LOW='2022_CSMOM21_COMMON_TIER_LOW_D';MID='2022_CSMOM21_COMMON_TIER_MID_D'
SCOPE='9a5ef547d61272d5eb0bfb1b61fef8005a752d82f4e0007d18cbe65f06445a8a'
PINS={LOW:'e32cc07014744d68478e517798b4bdeea35a11fa67f133af32e4073dc46391b4',MID:'8677183908c35b3a63263ca5a20c2e0158db3542ed72c41021164f63f67c298b'}


def exact(path,digest):
    raw=path.read_bytes();assert sha256(raw).hexdigest()==digest,(path,digest)
    return json.loads(raw)


class FailedAttemptMetadataReview(unittest.TestCase):
    def setUp(self):
        self.audit=exact(AUDITDIR/'FAILED_ATTEMPT001_INDEPENDENT_AUDIT.json','c472fac023fb646e5ebf2dcc5829e688ffb7ca0e853461c263936161f53be90f')
        self.binding=exact(AUDITDIR/'FAILED_ATTEMPT001_ROOT_EXIT_BINDING.json','67378985670e6d157b505af4ac438e30f3e56880f3470c5f0bcb094426dbd3ca')
    def test_root_observed_exit1_and_no_economic_HALT_no_retry_authority(self):
        root=exact(ATTEMPT/'ROOT_OBSERVED_EXIT_CONFIRMED.json','6a9a0bad0520d9b0e67487dc89afe4e09dcd2d0e2b1383b7d109b656aa1a89d4')
        self.assertEqual(root['observed_exit_code'],1)
        self.assertEqual(root,self.binding['root_observed_exit'])
        self.assertFalse(root['automatic_retry']);self.assertFalse(self.binding['retry_permission'])
        self.assertTrue(self.audit['no_economic_HALT_or_conditional_settlement_classification'])
        self.assertFalse(self.audit['retry_or_claim_supersession_authorized_by_this_review'])
    def test_LOW_observed_zero_constructors_provider_scope_and_trace_before_capture(self):
        guard=exact(ATTEMPT/LOW/'FAILED_SOURCE_RECAPTURE_GUARD_RECEIPT.json','926836cc7ca8c3f5ff55923add1f6436dd69923330c16688b5177282878aa9b1')
        self.assertEqual(guard['forbidden_attempts']['financial_GO_writes'],1)
        self.assertTrue(all(n==0 for k,n in guard['forbidden_attempts'].items() if k!='financial_GO_writes'))
        self.assertEqual([p['label'] for p in guard['checkpoints']],['FRESH_WORKER_CS_SOURCE_RECAPTURE_BEFORE_FINANCE_IMPORT'])
        self.assertFalse(any(k.endswith(('.npz','.csv','.zip')) for k in guard['observed_workspace_read_paths']))
        failure=exact(ATTEMPT/LOW/'FAILURE.json','81d871623ce20846283ee13c44c7b2889449f614a6a8083fee0c1d873b22cd5f')
        self.assertIn('gate.validate(raw, financial_go_raw',failure['traceback'])
        self.assertIn('EXECUTABLE_FINANCIAL_AUTHORITY_CONTENT',failure['traceback'])
        self.assertEqual(self.audit['LOW']['actual_source_capture_calls'],0)
    def test_MID_telemetry_absence_is_explicit_not_fabricated_observed_zero(self):
        self.assertFalse((ATTEMPT/MID/'FAILED_SOURCE_RECAPTURE_GUARD_RECEIPT.json').exists())
        self.assertEqual((ATTEMPT/(MID+'.log')).stat().st_size,0)
        self.assertFalse(self.binding['MID_observed_guard_counters_available'])
        self.assertTrue(self.binding['MID_code_phase_inference_preserved'])
        self.assertEqual(self.audit['source_and_financial_activity']['MID_raw_capture_count_inferred_via_unavoidable_blocker'],0)
        self.assertTrue(self.audit['source_and_financial_activity']['counts_are_control_flow_findings_not_fabricated_runtime_telemetry'])
    def test_both_permanent_preserved_prefinance_claims_exact_and_no_finance_results(self):
        for cell,pin in PINS.items():
            claim=exact(V4/'EXECUTION_CLAIMS'/SCOPE/(cell+'.json'),pin)
            self.assertEqual((V4/'EXECUTION_CLAIMS'/SCOPE/(cell+'.json')).read_bytes(),(ATTEMPT/cell/'LAUNCH_CLAIM.json').read_bytes())
            self.assertEqual(claim['root_GO_SHA256'],'44fb51cfc989a3499105e05144c855ead4840d775e23812a59250a24ed99d8ef')
            self.assertEqual(claim['code_identity'],'7ce4a2310cb7fa82b54296fb6b2e0f050f76909d871759f3cfc16b4e661a1e63')
            self.assertEqual(claim['status'],'RESERVED_BEFORE_PROCESS_SPAWN')
            self.assertFalse(claim['automatic_clear_or_retry']);self.assertFalse(claim['financial_snapshot_resume'])
            for name in ('SOURCE_RECAPTURE_GUARD_RECEIPT.json','ACCOUNT_FINANCIAL_AUDIT.json','FAILED_ACCOUNT_FINANCIAL_AUDIT.json','NATIVE_RESULT.json','TERMINAL_CHECKPOINT.json'):
                self.assertFalse((ATTEMPT/cell/name).exists(),(cell,name))
    def test_frozen_control_phase_and_pool_kill_wait_barriers(self):
        driver=(V4/'run_cs.py').read_bytes();self.assertEqual(sha256(driver).hexdigest(),'4781fc774f1886f2bcc37615c81366d5ea12e21dfa5498157abc9f72e200ae1d')
        loader=(V4/'cs_loader.py').read_bytes();self.assertEqual(sha256(loader).hexdigest(),'71edc30118ce395cb9bfcc0e32aa1681c21428d9ec426a9c22c641ef3ba07e08')
        text=loader.decode();self.assertLess(text.index('gate.validate(raw,'),text.index('captured = source.capture_year'))
        text=driver.decode();case=text[text.index('def case(args):'):text.index('\ndef command(')]
        self.assertLess(case.index("r.save(directory / 'SOURCE_RECAPTURE_GUARD_RECEIPT.json'"),case.index('import cs_admission'))
        self.assertLess(case.index('import cs_admission'),case.index('with cs_admission.admit_case'))
        self.assertTrue(self.audit['code_phase_locations']['failed_worker_triggers_pool_kill_and_wait_code_inspected'])

if __name__=='__main__':unittest.main(verbosity=2)
