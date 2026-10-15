"""Exact final code/read map and invented external wire validation only."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_common as c
import cs_entry as e
import cs_finance_gate as g
import cs_verified_wires as v
import cs_supersession as s
import run_cs
from test_cs_finance import fake_bundle,validate
SOURCE='21e13995b6be9482ee4e20d8e63be6d63396229035f69c963901331713342fce'
CODE='86da3b35cca4d241a638825cb46c75e153833b980f4474be660abd9427b1bad2'

class FinalManifestReview(unittest.TestCase):
    def test_source21e_exact18_files4_dependencies_and_v4_byte_identity(self):
        self.assertEqual(e.code_identity(),SOURCE)
        manifest=c.exact_object((c.HERE/'CODE_MANIFEST.json').read_bytes());old=ROOT/'original_cs_mom21_D_20261015_v4'
        self.assertEqual((c.HERE/'CODE_MANIFEST.json').read_bytes(),(old/'CODE_MANIFEST.json').read_bytes())
        self.assertEqual((len(manifest['files']),len(manifest['dependencies'])),(18,4))
        for name in manifest['files']:self.assertEqual((c.HERE/name).read_bytes(),(old/name).read_bytes(),name)

    def test_financial_inventory_current_and_native_scheduler_bytes_unchanged(self):
        self.assertEqual(g.code_identity(),CODE)
        m=c.exact_object((c.HERE/'FINANCIAL_CODE_MANIFEST.json').read_bytes())
        self.assertEqual(m['source_code_manifest_SHA256'],SOURCE)
        self.assertEqual(m['predecessor_financial_code_manifest_SHA256'],'7ce4a2310cb7fa82b54296fb6b2e0f050f76909d871759f3cfc16b4e661a1e63')
        self.assertEqual(len(m['files']),18)
        for name in ('cs_native.py','cs_process_runtime.py','cs_generated.py'):
            self.assertEqual((c.HERE/name).read_bytes(),(ROOT/'original_cs_mom21_D_20261015_v4'/name).read_bytes())

    def test_exact_failure_metadata_reads_classified_and_guard_allowlisted(self):
        raw=(c.HERE/'RUNTIME_READ_CLASSIFICATION.json').read_bytes()
        self.assertEqual(c.sha(raw),'ecb97d0db1865bcf228eee912f0cba76995b4d92dba814ae54520a7657640cf7')
        record=c.exact_object(raw);self.assertEqual(record['financial_code_manifest_SHA256'],CODE)
        self.assertEqual(record['stable_claim_registry'],s.STABLE_REGISTRY_REL)
        self.assertFalse(record['fresh_GO_alone_sufficient_for_local_recovery'])
        self.assertTrue(record['public_packet_omits_private_recovery_bodies'])
        m=c.exact_object((c.HERE/'FINANCIAL_CODE_MANIFEST.json').read_bytes());packet=s.packet()
        expected=dict(packet['evidence']);expected.update({p['path']:{k:p[k] for k in ('SHA256','bytes')} for p in packet['failed_claims'].values()})
        self.assertEqual(record['local_failed_attempt_recovery_required_bodies'],expected)
        args=SimpleNamespace(preparation='/GENERATED_ONLY_NO_ACTUAL_PREPARATION')
        for name in run_cs.WIRE_NAMES:setattr(args,name.replace('-','_'),'/GENERATED_ONLY_'+name)
        paths=set(run_cs.read_paths(args,dict(artifacts={})))
        for name,pin in expected.items():
            self.assertEqual(m['dependencies'][name],pin);self.assertIn(ROOT/name,paths)
        self.assertIn(c.HERE/'FAILED_ATTEMPT_SUPERSESSION_PACKET.json',paths)

    def test_real_code_fake_external_metadata_gate_positive_and_old_flat_alias_denial(self):
        result=validate(fake_bundle());self.assertEqual(result['financial_code_manifest_SHA256'],CODE)
        self.assertFalse(e._ACTIVE_SOURCE);self.assertFalse(e._ACTIVE_FINANCIAL);self.assertFalse(v._LIVE)
        fake=SimpleNamespace(__file__=str(ROOT/'original_cs_mom21_D_20261015_v4/cs_entry.py'))
        with patch.object(g,'source_entry',fake),self.assertRaisesRegex(ValueError,'NO_FLAT_ALIAS'):g.code_identity()

if __name__=='__main__':unittest.main(verbosity=2)
