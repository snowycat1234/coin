"""Generated cold-loader regressions for source execution identity only."""
from pathlib import Path
import hashlib,importlib.util,os,subprocess,sys,unittest
import importlib._bootstrap_external as bytecode
HERE=Path(__file__).resolve().parent
FREEZE=hashlib.sha256((HERE/'SOURCE_FREEZE.json').read_bytes()).hexdigest()


def child(source):
    return subprocess.run([sys.executable,'-c',source],cwd=HERE,
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','OPENBLAS_NUM_THREADS':'1'},
        text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=20)


def boot(prefix=''):
    return """from pathlib import Path
import sys,types
root=Path.cwd()
"""+prefix+"""
p=root/'verified_source.py'
m=types.ModuleType('verified_source');m.__file__=str(p);sys.modules['verified_source']=m
exec(compile(p.read_bytes(),str(p),'exec'),m.__dict__)
runtime=m.install(%r)
"""%FREEZE


class ColdSourceLoaderChecks(unittest.TestCase):
    def test_matching_timestamp_project_pyc_is_never_consumed(self):
        paths=[HERE/'dependencies/repo/src/quant/perpetual_account.py',
               HERE/'dependencies/account/vendor_quant/perpetual_account.py',
               HERE/'dependencies/terminal_adapter.py',HERE/'native_control.py']
        made=[]
        try:
            for source in paths:
                cache=Path(importlib.util.cache_from_source(str(source)))
                cache.parent.mkdir(exist_ok=True)
                previous=cache.read_bytes() if cache.exists() else None
                stat=source.stat()
                wrong=compile("raise AssertionError('UNEXPECTED_PROJECT_BYTECODE_EXECUTED')",str(source),'exec')
                cache.write_bytes(bytecode._code_to_timestamp_pyc(wrong,int(stat.st_mtime),stat.st_size))
                made.append((cache,previous))
            result=child(boot()+"import native_control\nprint(runtime.audit())\n")
            self.assertEqual(result.returncode,0,result.stdout)
            self.assertIn("'project_bytecode_consumed': False",result.stdout)
        finally:
            for cache,previous in made:
                if previous is None:cache.unlink()
                else:cache.write_bytes(previous)

    def test_cached_project_module_matching_file_path_is_rejected(self):
        prefix="""import importlib.util
p=root/'dependencies/repo/src/quant/perpetual_account.py'
fake=types.ModuleType('quant.perpetual_account');fake.__file__=str(p)
fake.__spec__=importlib.util.spec_from_file_location(fake.__name__,p)
exec('def decimal(value): return 777',fake.__dict__)
sys.modules[fake.__name__]=fake
"""
        result=child(boot(prefix))
        self.assertNotEqual(result.returncode,0)
        self.assertIn('UNVERIFIED_CACHED_PROJECT_MODULE:quant.perpetual_account',result.stdout)

    def test_verified_cached_function_body_change_is_rejected(self):
        source=boot()+"""import native_control
from vendor_quant.perpetual_account import USDTLinearPerpetualAccount
exec('def replacement(self, *args, **kwargs): return 777',globals())
USDTLinearPerpetualAccount.execute_fill.__code__=replacement.__code__
runtime.audit()
"""
        result=child(source)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('CACHED_PROJECT_SOURCE_BODY_CHANGED:vendor_quant.perpetual_account',result.stdout)

    def test_cold_exact_file_spec_helpers_also_use_verified_loader(self):
        result=child(boot()+"""import native_control
names=('h090_exact_original_port','exact_quantity_grid_account','exact_continuous_state_io','exact_short_activity_audit')
assert all(name in runtime.records for name in names)
assert all(isinstance(runtime.records[name][4],m.VerifiedLoader) for name in names)
print(runtime.audit())
""")
        self.assertEqual(result.returncode,0,result.stdout)

if __name__=='__main__':unittest.main(verbosity=2)
