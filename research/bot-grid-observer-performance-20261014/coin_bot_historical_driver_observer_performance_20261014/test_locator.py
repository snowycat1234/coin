"""Generated metadata/locator regressions; no historical arrays or accounts."""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase,mock
import hashlib,json,os,sys,tempfile
import bindings as B
import driver,native_locator as locator

class LocatorTests(TestCase):
 def go(self,action='SOURCE_ONLY_ORIGINAL_PROJECTION',prep=None):
  value=dict(schema='EXPLICIT_ORIGINAL_CSH_GRID_SOURCE_OR_CASE_GO_V1',parent_GO=True,action=action,year=2023,target_field='STATIC50_UNLAGGED',rank_feature_lag_hours=0,native_adapter_SHA256=B.SOURCE_ADAPTER_SHA if action=='SOURCE_ONLY_ORIGINAL_PROJECTION' else B.ADAPTER_SHA,input_manifest_SHA256=B.sha(B.HERE/'INPUT_MANIFEST.json'),preparation_manifest_SHA256=prep or B.SOURCE_PREPARATION_SHA)
  if action=='ONE_FRESH_NATIVE_CASE':value.update(arm='GRID',source_preparation_SHA256=B.SOURCE_PREPARATION_SHA)
  return value

 def test_only_relative_same_original_roots(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);review=base/'native_pair_replacement_review_20261014';carrier=review/'synthetic_dependencies_ca11e94d'
   for name in ('repo','fine','workspace'):(carrier/name).mkdir(parents=True)
   with mock.patch.object(locator,'ROOT',base),mock.patch.object(locator,'REVIEW',review):
    roots=locator.relocated_roots()
   self.assertEqual(roots,{name:str(carrier/name) for name in ('repo','fine','workspace')})
   self.assertNotIn('SYNTHETIC_ROOTS', (B.HERE/'native_locator.py').read_text())

 def test_missing_or_symlinked_root_refused(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);review=base/'native_pair_replacement_review_20261014';carrier=review/'synthetic_dependencies_ca11e94d';carrier.mkdir(parents=True)
   with mock.patch.object(locator,'ROOT',base),mock.patch.object(locator,'REVIEW',review):
    with self.assertRaisesRegex(ValueError,'CONSUMER_RELATIVE'):locator.relocated_roots()
    (carrier/'repo').symlink_to(base,target_is_directory=True)
    with self.assertRaisesRegex(ValueError,'SYMLINKED'):locator.relocated_roots()

 def test_exact_declared_runtime_sites_and_versions(self):
  report=locator.configure_runtime()
  self.assertEqual({n:r['version'] for n,r in report.items()},locator.RUNTIME_VERSIONS)
  self.assertTrue(all(len(r['package_entry_SHA256'])==64 for r in report.values()))

 def test_missing_runtime_sites_and_cached_shadow_refused(self):
  with mock.patch.dict(os.environ,{'BOT_NATIVE_RUNTIME_SITES':'[]'}):
   with self.assertRaisesRegex(ValueError,'EXPLICIT_ABSOLUTE'):locator.configure_runtime()
  module=sys.modules['polars'];fake=SimpleNamespace(__file__='/tmp/generated_cached_shadow.py',__spec__=SimpleNamespace(origin='/tmp/generated_cached_shadow.py'),__version__='1.44.2')
  with mock.patch.dict(sys.modules,{'polars':fake}):
   with self.assertRaisesRegex(ValueError,'CACHED_SHADOW'):locator.configure_runtime()
  self.assertIs(sys.modules['polars'],module)

 def test_generated_cannot_call_original26_loader(self):
  with self.assertRaisesRegex(ValueError,'BOUNDED_ORIGINAL26_RUNTIME_REQUIRED'):locator.load()

 def test_exact_ec309_source_and_new_wallet_GO_lineages(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'GO.json'
   for action,good in (('SOURCE_ONLY_ORIGINAL_PROJECTION',B.SOURCE_PREPARATION_SHA),('ONE_FRESH_NATIVE_CASE',B.sha(B.HERE/'PREPARATION_MANIFEST.json'))):
    path.write_text(json.dumps(self.go(action,good)));B.require_go(path,B.sha(path),action,2023,'GRID')
    path.write_text(json.dumps(self.go(action,'f'*64)))
    with self.assertRaisesRegex(ValueError,'EXACT_ORIGINAL'):B.require_go(path,B.sha(path),action,2023,'GRID')
   value=self.go('ONE_FRESH_NATIVE_CASE',B.sha(B.HERE/'PREPARATION_MANIFEST.json'));value['source_preparation_SHA256']='f'*64;path.write_text(json.dumps(value))
   with self.assertRaisesRegex(ValueError,'EXACT_EC309'):B.require_go(path,B.sha(path),'ONE_FRESH_NATIVE_CASE',2023,'GRID')

 def test_source_comparison_only_changes_label_and_never_saved_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'SOURCE_RECEIPT.json';saved=dict(preparation_manifest_SHA256=B.SOURCE_PREPARATION_SHA,target_raw_SHA256='GENERATED_FIXED',covariance_raw_SHA256='GENERATED_FIXED',roots_SHA256='GENERATED_FIXED');path.write_text(json.dumps(saved));before=path.read_bytes()
   current=dict(saved,preparation_manifest_SHA256=B.sha(B.HERE/'PREPARATION_MANIFEST.json'));args=SimpleNamespace(source_receipt=path)
   self.assertEqual(driver.compare_source_receipt(current,args),saved);self.assertEqual(path.read_bytes(),before)
   bad=dict(current,covariance_raw_SHA256='MUTATED')
   with self.assertRaisesRegex(ValueError,'SOURCE_PROJECTION_RECEIPT_CHANGED'):driver.compare_source_receipt(bad,args)
   for digest in (B.SOURCE_PREPARATION_SHA,'f'*64):
    bad=dict(current,preparation_manifest_SHA256=digest)
    with self.assertRaisesRegex(ValueError,'DUAL_SOURCE_WALLET'):driver.compare_source_receipt(bad,args)
   saved['preparation_manifest_SHA256']='f'*64;path.write_text(json.dumps(saved))
   with self.assertRaisesRegex(ValueError,'DUAL_SOURCE_WALLET'):driver.compare_source_receipt(current,args)

 def test_original26_financial_registry_and_raw_code_retained(self):
  closure=B.read(B.LEGACY/'EXECUTABLE_CLOSURE.json');self.assertEqual(len(closure['repo_files']),26)
  repo=B.ROOT/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d/repo'
  original=B.read(repo/closure['financial_port_manifest']['path']);self.assertEqual(set(original['sha256']),set(closure['repo_files']))
  checked=0
  for name,record in closure['repo_files'].items():
   self.assertEqual(original['sha256'][name],record['SHA256'])
   if name.endswith('.npz'):continue
   B.check(repo/name,record['SHA256'],record['bytes']);checked+=1
  self.assertEqual(checked,24)
  self.assertIn('port,account,sim=v.load_engine(roots)',(B.HERE/'native_locator.py').read_text())
