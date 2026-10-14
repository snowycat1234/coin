"""Direct cold bootstrap: verify freeze then compile checked source bytes."""
from pathlib import Path
import argparse,hashlib,importlib.machinery,json,sys,types,unittest
HERE=Path(__file__).resolve().parent

def main():
 p=argparse.ArgumentParser();p.add_argument('--preparation-manifest-sha',required=True)
 p.add_argument('command',choices=('metadata','source-check','case','tests','benchmark','audit','checks'))
 args,rest=p.parse_known_args()
 if args.command=='source-check':raise ValueError('WALLET_LOCATOR_REVISION_REUSES_EXACT_EC309_SOURCE_RECEIPT_NO_NEW_SOURCE_ATTEMPT')
 raw=(HERE/'PREPARATION_MANIFEST.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=args.preparation_manifest_sha:raise ValueError('EXTERNAL_PREPARATION_FREEZE_MISMATCH')
 manifest=json.loads(raw)
 for name,r in manifest['files'].items():
  path=Path(name)
  if path.is_absolute() or '..' in path.parts or (HERE/path).is_symlink():raise ValueError('FROZEN_PATH_REFUSED')
  data=(HERE/path).read_bytes()
  if hashlib.sha256(data).hexdigest()!=r['SHA256'] or len(data)!=r['bytes']:raise ValueError('PREPARATION_BYTES_CHANGED:'+name)
 if 'verified_source' in sys.modules:raise ValueError('PRELOADED_SOURCE_BOOTSTRAP_REFUSED')
 path=HERE/'verified_source.py';raw=path.read_bytes();want=manifest['files']['verified_source.py']['SHA256']
 if hashlib.sha256(raw).hexdigest()!=want:raise ValueError('BOOTSTRAP_SOURCE_CHANGED')
 module=types.ModuleType('verified_source');module.__file__=str(path)
 module.__spec__=importlib.machinery.ModuleSpec('verified_source',loader=None,origin=str(path));sys.modules['verified_source']=module
 exec(compile(raw,str(path),'exec'),module.__dict__)
 mode='generated' if args.command in ('tests','benchmark','audit','checks') else 'source_case'
 runtime=module.install(args.preparation_manifest_sha,mode)
 if args.command=='tests':
  suite=unittest.defaultTestLoader.loadTestsFromNames(['test_preparation','test_evidence','test_corrections','test_locator'])
  result=unittest.TextTestRunner(verbosity=2).run(suite);runtime.audit();return 0 if result.wasSuccessful() else 1
 target={'benchmark':'benchmark_generated','audit':'audit_generated_evidence','checks':'run_preparation_checks'}.get(args.command,'driver')
 imported=__import__(target)
 sys.argv=[str(HERE/(target+'.py')),*([args.command] if target=='driver' else []),*rest]
 if target=='benchmark_generated':return imported.main()
 if target=='audit_generated_evidence':return imported.main()
 return imported.main()

if __name__=='__main__':raise SystemExit(main())
