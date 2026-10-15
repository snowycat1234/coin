"""Independent append-only fake-registry checks; actual old claims read-only."""
from copy import deepcopy
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_common as c
import cs_process_runtime as r
import cs_supersession as s


def fake_go(value):
    return dict(manual_failed_pre_finance_claim_supersession_authorized=True,
        failed_claim_supersession_packet_SHA256=s.PACKET_SHA,stable_cross_version_claim_registry=s.STABLE_REGISTRY_REL,
        automatic_retry_authorized=False,preparation_SHA256=value['preparation_SHA256'])

class SupersessionReview(unittest.TestCase):
    def test_exact_packet_actual_old_claims_and_audit_hashes_readonly(self):
        value=s.validate_evidence();self.assertFalse(value['financial_execution_authorized'])
        self.assertFalse(value['retry_or_claim_supersession_authorized'])
        self.assertEqual(tuple(value['failed_claims']),s.FAILED_CELLS)
        self.assertEqual(s.registry_root(),c.ROOT/'original_cs_mom21_D_20261015_v4/EXECUTION_CLAIMS')
        for cell,pin in value['failed_claims'].items():
            raw=(ROOT/pin['path']).read_bytes();self.assertEqual(c.sha(raw),pin['SHA256'])
            self.assertEqual(s.claim_path(cell).name,pin['SHA256']+'.json')
        self.assertEqual(set(value['evidence']),{
            'original_cs_mom21_D_v4_FIRST6_saved_results_independent_review_20261015/FAILED_ATTEMPT001_INDEPENDENT_AUDIT.json',
            'original_cs_mom21_D_v4_FIRST6_saved_results_independent_review_20261015/FAILED_ATTEMPT001_ROOT_EXIT_BINDING.json'})

    def test_both_exact_oldclaim_hashes_permanently_consume_in_fake_registry(self):
        value=s.packet();go=fake_go(value)
        with tempfile.TemporaryDirectory(prefix='CS_INDEPENDENT_FAKE_REGISTRY_') as td:
            root=Path(td);base=root/s.SCOPE_SHA;base.mkdir()
            originals={cell:('GENERATED_OLD_'+cell).encode() for cell in s.FAILED_CELLS}
            for cell,raw in originals.items():(base/(cell+'.json')).write_bytes(raw)
            with patch.object(s,'registry_root',return_value=root),patch.object(s,'validate_evidence',return_value=value):
                with r.controller_lease(root):
                    for cell in s.FAILED_CELLS:
                        path=s.reserve(cell_id=cell,metadata=dict(root_GO_SHA256='a'*64),go=go)
                        record=c.exact_object(path.read_bytes());self.assertTrue(record['one_use_consumption_permanent'])
                        self.assertEqual(record['superseded_claim_SHA256'],value['failed_claims'][cell]['SHA256'])
                        self.assertEqual(record['failed_claim_supersession_packet_SHA256'],s.PACKET_SHA)
                        self.assertEqual(path.parent,base/'SUPERSESSION_CONSUMPTIONS')
                        for second_go in ('a'*64,'b'*64):
                            with self.assertRaisesRegex(RuntimeError,'ALREADY_CONSUMED'):
                                s.reserve(cell_id=cell,metadata=dict(root_GO_SHA256=second_go),go=go)
                for cell,raw in originals.items():self.assertEqual((base/(cell+'.json')).read_bytes(),raw)

    def test_without_lease_or_wrong_lease_inode_denied_before_reservation(self):
        value=s.packet();go=fake_go(value)
        with tempfile.TemporaryDirectory(prefix='CS_INDEPENDENT_FAKE_LEASE_') as td:
            a=Path(td)/'a';b=Path(td)/'b';(b/s.SCOPE_SHA).mkdir(parents=True)
            (b/s.SCOPE_SHA/'CONTROLLER_LEASE.lock').touch()
            with patch.object(s,'registry_root',return_value=b),patch.object(s,'validate_evidence',return_value=value):
                with self.assertRaisesRegex(ValueError,'LEASE_REQUIRED'):s.reserve(cell_id=s.FAILED_CELLS[0],metadata={},go=go)
                with r.controller_lease(a):
                    with self.assertRaisesRegex(ValueError,'LEASE_INODE'):s.reserve(cell_id=s.FAILED_CELLS[0],metadata={},go=go)
            self.assertFalse((b/s.SCOPE_SHA/'SUPERSESSION_CONSUMPTIONS').exists())

    def test_missing_or_changed_go_supersession_bindings_denied_before_lease(self):
        value=s.packet();good=fake_go(value)
        with patch.object(s,'validate_evidence',return_value=value):
            for key in good:
                bad=deepcopy(good);bad.pop(key)
                with self.subTest(missing=key),self.assertRaisesRegex(ValueError,'FRESH_ROOT_GO'):s.reserve(cell_id=s.FAILED_CELLS[0],metadata={},go=bad)
            for key,replacement in [('manual_failed_pre_finance_claim_supersession_authorized',False),('failed_claim_supersession_packet_SHA256','a'*64),
                    ('stable_cross_version_claim_registry','V5_NEW_NAMESPACE'),('automatic_retry_authorized',True),('preparation_SHA256','a'*64)]:
                bad=dict(good);bad[key]=replacement
                with self.subTest(changed=key),self.assertRaisesRegex(ValueError,'FRESH_ROOT_GO'):s.reserve(cell_id=s.FAILED_CELLS[0],metadata={},go=bad)

    def test_unfailed_first6_claim_uses_normal_permanent_namespace(self):
        value=s.packet();go=fake_go(value);cell='2022_CSMOM21_COMMON_TIER_HIGH_D'
        with tempfile.TemporaryDirectory(prefix='CS_INDEPENDENT_FAKE_HIGH_') as td:
            root=Path(td)
            with patch.object(s,'registry_root',return_value=root),patch.object(s,'validate_evidence',return_value=value):
                with r.controller_lease(root):
                    path=s.reserve(cell_id=cell,metadata=dict(root_GO_SHA256='a'*64),go=go)
                    self.assertEqual(path,root/s.SCOPE_SHA/(cell+'.json'))
                    with self.assertRaisesRegex(RuntimeError,'PERMANENT_CANONICAL'):s.reserve(cell_id=cell,metadata={},go=go)
                self.assertFalse((root/s.SCOPE_SHA/'SUPERSESSION_CONSUMPTIONS').exists())

if __name__=='__main__':unittest.main(verbosity=2)
