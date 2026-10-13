"""Nonfinancial gate tests; never imports or advances an account."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('public_entry_tested',HERE/'public_entry.py');entry=importlib.util.module_from_spec(spec);spec.loader.exec_module(entry)
INPUTS=Path('/workspace/coin-cloud/csh-execution-stress-20261013')
class PublicGate(unittest.TestCase):
 def test_original_restored_three_years_private_dedup_absent(self):
  self.assertFalse((HERE/'DEDUP.json').exists())
  for y in (2021,2023,2025):self.assertEqual(entry.verify(INPUTS,y)['years'],[2021,2023,2025])
 def test_financial_code_tamper_rejected(self):
  with tempfile.TemporaryDirectory(prefix='public-gate-',dir='/tmp') as d:
   root=Path(d)
   for n in ('PUBLIC_REPRODUCIBILITY.json','FREEZE.json','BASE_RESULTS.json','PINNED_CODE_AND_TARGETS.json','SOURCE_BINDINGS.json','execution.py','prepare2021.py','recover.py','run.py','runtime.py','test_execution.py'):(root/n).write_bytes((HERE/n).read_bytes())
   (root/'run.py').write_bytes((root/'run.py').read_bytes()+b'\n# tamper\n')
   old=entry.HERE;entry.HERE=root
   try:
    with self.assertRaisesRegex(AssertionError,'run.py'):entry.verify(INPUTS,2021)
   finally:entry.HERE=old
 def test_missing_authorization_no_output(self):
  with tempfile.TemporaryDirectory(prefix='public-gate-',dir='/tmp') as d:
   out=Path(d)/'must-not-exist'
   r=subprocess.run([sys.executable,str(HERE/'public_entry.py'),'--inputs',str(INPUTS),'--year','2021','--shock','FRICTION_DOUBLE','--output',str(out)],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertIn('Explicit authorization',r.stderr);self.assertFalse(out.exists())
 def test_check_does_not_import_financial_launcher(self):
  self.assertNotIn('run',sys.modules);self.assertNotIn('runtime',sys.modules)
if __name__=='__main__':unittest.main()
