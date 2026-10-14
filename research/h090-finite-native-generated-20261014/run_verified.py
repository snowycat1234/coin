"""Cold source-verified entry. The required freeze hash comes from the reviewer."""
from pathlib import Path
import argparse,hashlib,json,sys,types,unittest
HERE=Path(__file__).resolve().parent


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--freeze-sha',required=True)
    p.add_argument('command',choices=('tests','generated','check-loader'))
    p.add_argument('--receipt-dir')
    a=p.parse_args()
    raw=(HERE/'SOURCE_FREEZE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.freeze_sha:raise ValueError('EXTERNAL_FREEZE_HASH_REQUIRED')
    freeze=json.loads(raw)
    path=HERE/'verified_source.py';source=path.read_bytes()
    if hashlib.sha256(source).hexdigest()!=freeze['files_SHA256']['verified_source.py']:
        raise ValueError('VERIFIED_BOOTSTRAP_SOURCE_HASH_REQUIRED')
    if 'verified_source' in sys.modules:raise ValueError('COLD_BOOTSTRAP_MODULE_ALREADY_PRESENT')
    module=types.ModuleType('verified_source');module.__file__=str(path)
    sys.modules['verified_source']=module
    exec(compile(source,str(path),'exec'),module.__dict__)
    runtime=module.install(a.freeze_sha)
    if a.command=='check-loader':
        import native_control
        print(json.dumps(runtime.audit(),sort_keys=True));return 0
    if a.command=='tests':
        names=['test_source_normalization','test_native_control','test_capital_edges','test_loader_binding']
        suite=unittest.defaultTestLoader.loadTestsFromNames(names)
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        runtime.audit()
        return 0 if result.wasSuccessful() else 1
    if not a.receipt_dir:raise ValueError('NEW_GENERATED_RECEIPT_DIRECTORY_REQUIRED')
    import run_generated
    result=run_generated.export(a.receipt_dir)
    runtime.audit()
    print(json.dumps(result,indent=2,allow_nan=False));return 0

if __name__=='__main__':raise SystemExit(main())
