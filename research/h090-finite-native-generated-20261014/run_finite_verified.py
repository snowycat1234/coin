"""New finite-candidate entry; immutable CONTROL bootstrap source is reused."""
from pathlib import Path
import argparse,hashlib,json,sys,types,unittest
HERE=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser();p.add_argument('--freeze-sha',required=True)
    p.add_argument('command',choices=('demo','tests','witnesses'));p.add_argument('--receipt-dir')
    a=p.parse_args();raw=(HERE/'SOURCE_FREEZE.json').read_bytes()
    if hashlib.sha256(raw).hexdigest()!=a.freeze_sha:raise ValueError('EXTERNAL_CANDIDATE_FREEZE_REQUIRED')
    f=json.loads(raw);path=HERE/'verified_source.py';source=path.read_bytes()
    if hashlib.sha256(source).hexdigest()!=f['files_SHA256']['verified_source.py']:raise ValueError('IMMUTABLE_CONTROL_BOOTSTRAP_REQUIRED')
    if 'verified_source' in sys.modules:raise ValueError('COLD_BOOTSTRAP_REQUIRED')
    m=types.ModuleType('verified_source');m.__file__=str(path);sys.modules['verified_source']=m
    exec(compile(source,str(path),'exec'),m.__dict__);runtime=m.install(a.freeze_sha)
    if a.command=='tests':
        suite=unittest.defaultTestLoader.loadTestsFromNames(['test_source_normalization','test_native_control','test_capital_edges','test_loader_binding','test_finite_candidate','test_finite_atomic','test_finite_review_boundaries'])
        result=unittest.TextTestRunner(verbosity=2).run(suite)
        print(json.dumps({'source_audit':runtime.audit(),'tests_run':result.testsRun,'tests_passed':result.wasSuccessful()},sort_keys=True))
        return 0 if result.wasSuccessful() else 1
    if a.command=='witnesses':
        from test_finite_atomic import generated_boundary_witnesses
        result=generated_boundary_witnesses();result['source_audit']=runtime.audit()
        path=Path(a.receipt_dir);path.mkdir(parents=False,exist_ok=False)
        (path/'OWNER_BOUNDARIES.json').write_text(json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n')
        print(json.dumps({'scope':result['scope'],'cases':len(result['cases']),'historical_status':'NO_GO'}));return 0
    from finite_fixtures import run_demo
    result=run_demo(a.receipt_dir);result['source_audit']=runtime.audit();print(json.dumps(result,indent=2,allow_nan=False));return 0

if __name__=='__main__':raise SystemExit(main())
