"""One bounded actual-import regression over 19 exact file-backed runtime modules."""
from pathlib import Path
import argparse,importlib,json,sys,unittest
ap=argparse.ArgumentParser(add_help=False);ap.add_argument('--module',type=Path,required=True);ap.add_argument('--roots',type=Path,required=True);a,tail=ap.parse_known_args();sys.argv=[sys.argv[0],*tail];sys.path.insert(0,str(a.module.resolve()))
import v2_launcher as v
ROOTS=json.loads(a.roots.read_text());PORT,_,_=v.load_engine(ROOTS)
class Regression(unittest.TestCase):
 def test_every_file_backed_runtime_module_path_and_spec_shadow_rejects(self):
  names=['quant.execution_contract','quant.perpetual_account','quant.disk','quant.metrics','quant.paths','quant.resources','scripts.investment.resumable_perpetual','scripts.investment.perpetual_directional','scripts.investment.bybit_cost_inputs','scripts.investment.perpetual_closing_exempt_account','scripts.research_v8.funding_price_source_v2','scripts.research_v8.registry','fine_account','freeze_bootstrap','terminal_adapter']
  modules=[importlib.import_module(n) for n in names]+[PORT,PORT.grid,PORT.state_io,PORT.activity]
  self.assertEqual(len(modules),19)
  for module in modules:
   for field in ('file','origin'):
    with self.subTest(module=module.__name__,field=field):
     if field=='file':old=module.__file__;module.__file__='/UNTRUSTED_SYNTHETIC_SHADOW/module.py'
     else:old=module.__spec__.origin;module.__spec__.origin='/UNTRUSTED_SYNTHETIC_SHADOW/module.py'
     try:
      with self.assertRaisesRegex(v.GateError,'FINANCIAL_IMPORT_SHADOW'):v.verify_imported_financial(ROOTS,PORT)
     finally:
      if field=='file':module.__file__=old
      else:module.__spec__.origin=old
  v.verify_imported_financial(ROOTS,PORT)
if __name__=='__main__':unittest.main(verbosity=2)
