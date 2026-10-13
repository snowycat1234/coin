"""Pure original-SMA admission tests; no historical simulator advances."""
import json,unittest,tempfile,shutil
from pathlib import Path
import numpy as np
from freeze_sma import verify
from preflight_sma import validate_terminal,bindings
from run_budget import stop_on_worker_failure,ensure_single_unstarted_batch
from worker_bounds import require_worker_bounds
H=Path(__file__).resolve().parent
class Gates(unittest.TestCase):
 def test_fixed_three(self):
  b=bindings();self.assertEqual([c['year'] for c in b['cases']],[2023,2024,2025]);self.assertEqual(b['modes'],['ORIGINAL'])
 def test_economic_vs_program_stop(self):
  self.assertFalse(stop_on_worker_failure(0));self.assertTrue(stop_on_worker_failure(1));self.assertTrue(stop_on_worker_failure(-9))
 def test_worker_bounds(self):
  require_worker_bounds({0},(4_000_000_000,4_000_000_000),(1200,1200))
  for pair in [(-1,-1),(0,4_000_000_001)]:
   with self.assertRaises(RuntimeError):require_worker_bounds({0},pair,(1200,1200))
  with self.assertRaises(RuntimeError):require_worker_bounds({0,1},(1,1),(1200,1200))
 def test_terminal_causal_five(self):
  end=1704067200000000;t=np.arange(end-6*60_000_000,end,60_000_000,dtype=np.int64);p=np.ones(6)
  r=validate_terminal(t,t+60_000_000,p,p,p,end);self.assertEqual(r['attempt_count'],5);self.assertTrue(r['all_attempts_before_end'])
  with self.assertRaises(ValueError):validate_terminal(t[:-1],t[:-1]+60_000_000,p,p,p,end)
  bad=p.copy();bad[2]=np.nan
  with self.assertRaises(ValueError):validate_terminal(t,t+60_000_000,bad,p,p,end)
 def test_single_batch(self):
  with tempfile.TemporaryDirectory() as d:
   h=Path(d);ensure_single_unstarted_batch(h,h/'state_first');(h/'state_old').mkdir();(h/'state_old/RUN_BINDING.json').write_text('{}')
   with self.assertRaises(RuntimeError):ensure_single_unstarted_batch(h,h/'state_second')
 def test_freeze_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   # Full dependency roots are unnecessary: local tamper must fail before them.
   h=Path(d);m=json.loads((H/'FROZEN_CODE.json').read_text());m['files_SHA256']={'run_cases.py':m['files_SHA256']['run_cases.py']};m['dependencies_SHA256']={}
   shutil.copy(H/'freeze_sma.py',h/'freeze_sma.py');(h/'run_cases.py').write_text('tamper');(h/'FROZEN_CODE.json').write_text(json.dumps(m))
   with self.assertRaises(ValueError):verify(h)
if __name__=='__main__':unittest.main(verbosity=2)
