"""Pure recovery identity/budget tests; no historical finance advances."""
import unittest,json,math,ast
from pathlib import Path
from resume_limits import choose_cpu,require_live_cpu,require_combined_state,terminal_status
H=Path(__file__).resolve().parent
class Tests(unittest.TestCase):
 def test_same_two_durable_anchors_and_remaining_budget(self):
  p=json.loads((H/'RESUME_PLAN.json').read_text());self.assertEqual(p['max_parallel'],1);self.assertEqual(p['new_wallets'],0)
  self.assertEqual([c['durable_completed_minutes'] for c in p['cases']],[432000,475200])
  for c in p['cases']:
   self.assertEqual(c['resume_CPU_seconds'],869);self.assertEqual(c['resume_wall_seconds'],1200-math.ceil(c['original_elapsed_seconds']))
   self.assertLessEqual(c['original_elapsed_seconds']+c['resume_wall_seconds'],1200)
 def test_no_account_factory_or_new_simulator_history(self):
  t=ast.parse((H/'resume_cases.py').read_text())
  calls=[x for x in ast.walk(t) if isinstance(x,ast.Call)]
  self.assertFalse(any(isinstance(x.func,ast.Name) and x.func.id=='Simulator' for x in calls))
  self.assertTrue(any(isinstance(x.func,ast.Attribute) and x.func.attr=='from_snapshot' for x in calls))
 def test_original_resource_formula_retained(self):
  text=(H/'resume_cases.py').read_text();self.assertIn("resource_gate.admission(state,0,guard)",text)
  self.assertIn("resource_gate.check_external",text)
  self.assertNotIn('WORKER_RSS_LIMIT=',text);self.assertNotIn('HOST_USED_LIMIT=',text)
 def test_original_stop_preserved_new_sidecars(self):
  text=(H/'resume_cases.py').read_text();self.assertIn('RECOVERY_RUN_BINDING.json',text);self.assertIn('original_STOP_preserved=True',text)
  self.assertNotIn("original_state/'RESOURCE_RECEIPTS.json').write",text)
 def test_fresh_cpu_and_live_conflict(self):
  self.assertEqual(choose_cpu({'allowed_cpus':[3,4],'external_busy_cpus':[3]}),4)
  with self.assertRaises(RuntimeError):require_live_cpu(4,{'external_busy_cpus':[4]})
  with self.assertRaises(RuntimeError):choose_cpu({'allowed_cpus':[0],'external_busy_cpus':[0]})
 def test_combined_same_wallet_state_and_exception_status(self):
  self.assertEqual(require_combined_state(60_000_000,190_000_000),250_000_000)
  with self.assertRaises(RuntimeError):require_combined_state(60_000_001,190_000_000)
  self.assertEqual(terminal_status(True,[]),'STOP_PARTIAL')
  text=(H/'resume_cases.py').read_text();self.assertIn('except BaseException:',text)
  self.assertIn('failed=True\n        raise',text)
 def test_new_exact_recovery_publication_required(self):
  text=(H/'resume_cases.py').read_text();self.assertIn('publication=require_publication()',text)
  self.assertIn('recovery_publication_receipt_SHA256',text)
if __name__=='__main__':unittest.main(verbosity=2)
