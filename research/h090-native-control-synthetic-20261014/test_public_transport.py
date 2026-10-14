"""Operational transport checks only; not a financial reviewer-agent verdict."""
from pathlib import Path
import hashlib,importlib.util,json,shutil,tempfile,unittest
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('h090_public_transport_only',HERE/'run_public_cold.py')
transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
EXPECTED=hashlib.sha256((HERE/'PUBLIC_PAYLOAD_MANIFEST.json').read_bytes()).hexdigest()
class PublicTransportChecks(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory(prefix='h090_transport_');self.base=Path(self.temp.name)/'payload';self.base.mkdir()
  manifest=json.loads((HERE/'PUBLIC_PAYLOAD_MANIFEST.json').read_bytes())
  for n in [*manifest['files'],'PUBLIC_PAYLOAD_MANIFEST.json']:
   p=self.base/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((HERE/n).read_bytes())
  self.old=transport.HERE;transport.HERE=self.base
 def tearDown(self):transport.HERE=self.old;self.temp.cleanup()
 def test_exact_manifest_original_closure_and_nine_saved_native_bodies(self):
  identity,bodies=transport.verify(EXPECTED);self.assertEqual(identity['exact_source_closure_members'],79);self.assertEqual(len(bodies),9);self.assertEqual(identity['existing_public_target_archive_bytes'],50586);self.assertEqual(identity['NPZ_arrays_parsed'],0)
 def test_wrong_external_public_manifest_fails(self):
  with self.assertRaisesRegex(ValueError,'PUBLIC_MANIFEST_HASH_MISMATCH'):transport.verify('0'*64)
 def test_nonhash_external_manifest_fails(self):
  with self.assertRaisesRegex(ValueError,'EXTERNAL_PUBLIC_MANIFEST_SHA_REQUIRED'):transport.verify('packet-selected')
 def test_changed_frozen_science_fails(self):
  p=self.base/'native_control.py';p.write_bytes(p.read_bytes()+b'\n')
  with self.assertRaisesRegex(ValueError,'PUBLIC_MEMBER_IDENTITY_MISMATCH'):transport.verify(EXPECTED)
 def test_changed_original_dependency_fails(self):
  p=self.base/'dependencies/repo/src/quant/perpetual_account.py';p.write_bytes(p.read_bytes()+b'\n')
  with self.assertRaisesRegex(ValueError,'PUBLIC_MEMBER_IDENTITY_MISMATCH'):transport.verify(EXPECTED)
 def test_changed_checksum_archive_fails_without_array_parsing(self):
  p=self.base/'dependencies/repo/research/static50-sma-20261013/input/Y2023.npz';b=p.read_bytes();p.write_bytes(b[:-1]+bytes([b[-1]^1]))
  with self.assertRaisesRegex(ValueError,'PUBLIC_MEMBER_IDENTITY_MISMATCH'):transport.verify(EXPECTED)
 def test_missing_checksum_archive_is_not_silently_relaxed(self):
  (self.base/'dependencies/repo/research/static50-sma-20261013/input/Y2025.npz').unlink()
  with self.assertRaises(FileNotFoundError):transport.verify(EXPECTED)
 def test_changed_compressed_saved_native_body_fails(self):
  p=self.base/'saved_generated_journals/GENERATED_JOURNALS.tar.gz';p.write_bytes(p.read_bytes()+b'changed')
  with self.assertRaisesRegex(ValueError,'PUBLIC_MEMBER_IDENTITY_MISMATCH'):transport.verify(EXPECTED)
 def test_changed_parent_financial_review_fails(self):
  p=self.base/'PUBLIC_PARENT_FINANCIAL_REVIEW.json';p.write_bytes(p.read_bytes()+b' ')
  with self.assertRaisesRegex(ValueError,'PUBLIC_MEMBER_IDENTITY_MISMATCH'):transport.verify(EXPECTED)
 def test_failed_separate_reviewer_status_is_retained(self):
  status=json.loads((self.base/'REVIEW_WORKER_STATUS.json').read_bytes());self.assertEqual(status['review_status'],'NOT_PERFORMED');self.assertTrue(status['producer_checks_are_not_independent_review'])
 def test_literal_source_symlink_rejected(self):
  p=self.base/'native_control.py';body=p.read_bytes();p.unlink();target=Path(self.temp.name)/'native_control.py';target.write_bytes(body);p.symlink_to(target)
  with self.assertRaisesRegex(ValueError,'SYMLINKED_PUBLIC_MEMBER'):transport.verify(EXPECTED)
 def test_unsafe_member_paths_are_rejected(self):
  for n in ['../outside','/absolute','dependencies/../escape','./relative']:
   with self.subTest(path=n):
    with self.assertRaisesRegex(ValueError,'UNSAFE_PUBLIC_MANIFEST_PATH'):transport.safe(n)
if __name__=='__main__':unittest.main(verbosity=2)
