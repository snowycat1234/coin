"""Isolated freeze-first bootstrap for one explicit original2023 H090 bridge."""
import sys
if not (sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and sys.flags.optimize==0):
 raise RuntimeError('ISOLATED_NO_SITE_NO_BYTECODE_ASSERTIONS_ENABLED_LAUNCH_REQUIRED')
from pathlib import Path
import argparse,hashlib,importlib.machinery,json,types,unittest
HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--preparation-manifest-sha',required=True)
 p.add_argument('command',choices=('metadata','tests','quality-tests','source-view-tests','case'));a,rest=p.parse_known_args()
 raw=(HERE/'PREPARATION_MANIFEST.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=a.preparation_manifest_sha:raise ValueError('EXTERNAL_BRIDGE_FREEZE_REQUIRED')
 f=json.loads(raw)
 for name,r in f['files'].items():
  rel=Path(name)
  if rel.is_absolute() or '..' in rel.parts or (HERE/rel).is_symlink():raise ValueError('FROZEN_PATH_REFUSED')
  data=(HERE/rel).read_bytes()
  if hashlib.sha256(data).hexdigest()!=r['SHA256'] or len(data)!=r['bytes']:raise ValueError('FROZEN_PREPARATION_CHANGED:'+name)
 if 'verified_source' in sys.modules:raise ValueError('COLD_SOURCE_BOOTSTRAP_REQUIRED')
 path=HERE/'verified_source.py';source=path.read_bytes();m=types.ModuleType('verified_source');m.__file__=str(path)
 m.__spec__=importlib.machinery.ModuleSpec('verified_source',loader=None,origin=str(path));sys.modules['verified_source']=m
 exec(compile(source,str(path),'exec'),m.__dict__);runtime=m.install(a.preparation_manifest_sha,'generated' if a.command in ('tests','quality-tests','source-view-tests') else 'source_case')
 import bridge_runtime_locator
 runtime.runtime_packages=bridge_runtime_locator.configure_runtime()
 if a.command in ('tests','quality-tests','source-view-tests'):
  suite=unittest.defaultTestLoader.loadTestsFromNames(['test_source_view'] if a.command=='source-view-tests' else (['test_proof_consumer','test_registry_boundary','test_bridge.Bridge.test_case_GO_types_year_arm_review_and_control_first'] if a.command=='quality-tests' else ['test_bridge']));result=unittest.TextTestRunner(verbosity=2).run(suite)
  print(json.dumps({'tests_run':result.testsRun,'tests_passed':result.wasSuccessful(),'source_audit':runtime.audit(),'historical_GO':False},sort_keys=True));return 0 if result.wasSuccessful() else 1
 import driver
 sys.argv=[str(HERE/'driver.py'),a.command,*rest];return driver.main()
if __name__=='__main__':raise SystemExit(main())
