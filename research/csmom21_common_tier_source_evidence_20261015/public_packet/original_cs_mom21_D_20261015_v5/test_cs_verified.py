"""Generated-only metadata/claim lifecycle checks; temporary registry only."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import cs_common as c
import cs_process_runtime as r
import cs_supersession as s

class SupersessionTests(unittest.TestCase):
    def test_exact_old_metadata_evidence_read_only_and_stable_registry(self):
        value=s.validate_evidence()
        self.assertFalse(value['financial_execution_authorized'])
        self.assertEqual(s.registry_root(),c.ROOT/'original_cs_mom21_D_20261015_v4/EXECUTION_CLAIMS')
        for cell in s.FAILED_CELLS:self.assertEqual(s.claim_path(cell).name,value['failed_claims'][cell]['SHA256']+'.json')

    def test_generated_one_use_and_original_claim_unchanged(self):
        cell=s.FAILED_CELLS[0]
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);base=root/s.SCOPE_SHA;base.mkdir();old=base/(cell+'.json');old.write_bytes(b'GENERATED_ORIGINAL_CLAIM')
            value=s.packet();go=dict(manual_failed_pre_finance_claim_supersession_authorized=True,
                failed_claim_supersession_packet_SHA256=s.PACKET_SHA,stable_cross_version_claim_registry=s.STABLE_REGISTRY_REL,
                automatic_retry_authorized=False,preparation_SHA256=value['preparation_SHA256'])
            metadata=dict(root_GO_SHA256='a'*64)
            with patch.object(s,'registry_root',return_value=root),patch.object(s,'validate_evidence',return_value=value):
                with r.controller_lease(root):
                    path=s.reserve(cell_id=cell,metadata=metadata,go=go)
                    self.assertTrue(path.is_file());self.assertEqual(old.read_bytes(),b'GENERATED_ORIGINAL_CLAIM')
                    with self.assertRaisesRegex(RuntimeError,'ALREADY_CONSUMED'):s.reserve(cell_id=cell,metadata=metadata,go=go)
                for key in go:
                    bad=go.copy();bad.pop(key)
                    with self.assertRaises(ValueError):s.reserve(cell_id=cell,metadata=metadata,go=bad)
            self.assertEqual(old.read_bytes(),b'GENERATED_ORIGINAL_CLAIM')

    def test_reservation_without_stable_lease_denied(self):
        value=s.packet();go=dict(manual_failed_pre_finance_claim_supersession_authorized=True,
            failed_claim_supersession_packet_SHA256=s.PACKET_SHA,stable_cross_version_claim_registry=s.STABLE_REGISTRY_REL,
            automatic_retry_authorized=False,preparation_SHA256=value['preparation_SHA256'])
        with patch.object(s,'validate_evidence',return_value=value),self.assertRaisesRegex(ValueError,'LEASE_REQUIRED'):
            s.reserve(cell_id=s.FAILED_CELLS[0],metadata={},go=go)

class SavedPhaseTests(unittest.TestCase):
    def test_exact_generated_phase_chain_and_resealed_mutation_denials(self):
        import cs_saved
        from copy import deepcopy
        claim=b'GENERATED_CLAIM';guard=b'GENERATED_OBSERVED_GUARD'
        receipt=dict(cell_id='GENERATED_CELL',root_GO_SHA256='a'*64,preparation_SHA256='b'*64,PID=12,
                     financial_code_manifest_SHA256='c'*64)
        common=dict(schema='CS_WORKER_PREFINANCE_PHASE_V1',cell_id=receipt['cell_id'],root_GO_SHA256=receipt['root_GO_SHA256'],
            preparation_SHA256=receipt['preparation_SHA256'],PID=12,historical_scopes_constructed=0,providers_constructed=0,accounts_constructed=0)
        first=dict(common,phase='EXACT_EXECUTABLE_GO_VERIFIED_OUTSIDE_UNCHANGED_SOURCE_GUARD',
            financial_code_manifest_SHA256='c'*64,claim_SHA256=c.sha(claim),source_capture_started=False,UTC='2026-10-15T00:00:00+00:00')
        second=dict(common,phase='SOURCE_RECAPTURE_AND_SAVED_TARGET_BINDING_ACCEPTED_GUARD_EXITED',
            source_guard_receipt_SHA256=c.sha(guard),verified_wires_revoked=True,UTC='2026-10-15T00:00:01+00:00')
        cs_saved.saved_worker_phases(first,second,receipt=receipt,claim_raw=claim,source_guard_raw=guard)
        for which,original in enumerate((first,second)):
            for key in original:
                pair=[deepcopy(first),deepcopy(second)];pair[which].pop(key)
                with self.subTest(which=which,key=key),self.assertRaises(ValueError):
                    cs_saved.saved_worker_phases(*pair,receipt=receipt,claim_raw=claim,source_guard_raw=guard)
        for which,key,value in ((0,'accounts_constructed',False),(0,'claim_SHA256','d'*64),(1,'verified_wires_revoked',False),
                                (1,'UTC','2026-10-14T00:00:00+00:00'),(0,'phase','AFTER_ACCOUNT')):
            pair=[deepcopy(first),deepcopy(second)];pair[which][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                cs_saved.saved_worker_phases(*pair,receipt=receipt,claim_raw=claim,source_guard_raw=guard)

    def test_remaining9_reservation_denied_before_evidence_or_effects(self):
        with patch.object(s,'validate_evidence',side_effect=AssertionError('NO_EVIDENCE_READ')),self.assertRaisesRegex(ValueError,'FIRST6'):
            s.reserve(cell_id='2024_CSMOM21_COMMON_TIER_LOW_D',metadata={},go={})

if __name__=='__main__':unittest.main()
