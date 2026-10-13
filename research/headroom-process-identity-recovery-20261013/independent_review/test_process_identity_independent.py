"""Pure /proc fixtures for own children versus external financial identity."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util, json, unittest
H=Path(__file__).resolve().parent
W=H.parent

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
m=load('independent_process_fix',W/'coin_headroom_process_recovery_20261013/process_identity.py')
g=load('independent_original_gate',W/'coin_headroom_risk_candidate_20261013/resource_gate.py')
ROOT=100
RUN='/x/coin_headroom_risk_candidate_20261013/run_cases.py'
OLD='/x/coin_earlier_terminal_exit_20261013/run_cases.py'
TASK={'pack_task_released':True,'task_reserved_bytes':0,'task_busy_cpus':[],'release_receipt_SHA256':'synthetic'}

class IdentityTests(unittest.TestCase):
 def node(self,root,pid,ppid,command=RUN,status=True,status_pid=None):
  d=root/str(pid);d.mkdir()
  (d/'cmdline').write_bytes(('python\0'+command+'\0').encode())
  if status:(d/'status').write_text(f'Name:\tpython\nPid:\t{pid if status_pid is None else status_pid}\nPPid:\t{ppid}\nVmRSS:\t100 kB\n')
  return d
 def observe(self,root,task=TASK):
  with patch.object(m.os,'getpid',return_value=ROOT),patch.object(g,'task_reservation',return_value=task):return m.fixed_external_observation(g,root)
 def test_supported_ppid_owns_child_and_grandchild_without_children_files(self):
  with TemporaryDirectory(dir=H) as d:
   root=Path(d)
   for pid,parent in [(ROOT,10),(101,ROOT),(102,101)]:self.node(root,pid,parent)
   self.assertEqual(m.own_process_ids(root,ROOT),{ROOT,101,102})
   self.assertEqual(self.observe(root)['prior_historical_processes'],[])
 def test_real_financial_parent_sibling_and_orphan_still_block(self):
  with TemporaryDirectory(dir=H) as d:
   root=Path(d)
   for pid,parent,cmd in [(ROOT,10,RUN),(101,ROOT,RUN),(10,1,OLD),(11,10,RUN),(200,1,RUN)]:self.node(root,pid,parent,cmd)
   actual=self.observe(root)
   self.assertEqual(set(actual['prior_historical_processes']),{10,11,200})
   with self.assertRaisesRegex(RuntimeError,'Prior financial'):
    g.check_external({'memory':{'host_used':0},'allowed_cpus':[0,1]},actual,0,type('Guard',(),{'WORKER_RSS_LIMIT':2_000_000_000,'HOST_USED_LIMIT':8_000_000_000}))
 def test_missing_status_never_assumed_own(self):
  with TemporaryDirectory(dir=H) as d:
   root=Path(d);self.node(root,ROOT,1);self.node(root,101,ROOT,status=False)
   self.assertEqual(self.observe(root)['prior_historical_processes'],[101])
 def test_mismatched_pid_and_malformed_ppid_fail_closed(self):
  with TemporaryDirectory(dir=H) as d:
   root=Path(d);self.node(root,ROOT,1);self.node(root,101,ROOT,status_pid=999)
   p=self.node(root,102,ROOT);(p/'status').write_text('Pid:\t102\nPPid:\tunknown\n')
   self.assertEqual(set(self.observe(root)['prior_historical_processes']),{101,102})
 def test_external_pack_reservation_and_busy_cpus_unchanged(self):
  with TemporaryDirectory(dir=H) as d:
   root=Path(d);self.node(root,ROOT,1);self.node(root,101,ROOT)
   self.node(root,300,1,'/x/'+g.PACK_RELATIVE);self.node(root,301,1,'/x/'+g.PACK_VERIFY_RELATIVE)
   task={**TASK,'pack_task_released':False,'task_reserved_bytes':2_000_000_000,'task_busy_cpus':[8]}
   with patch.object(m.os,'sched_getaffinity',return_value={3}):result=self.observe(root,task)
   self.assertEqual(result['external_reserved_bytes'],4_000_000_000)
   self.assertEqual(result['external_busy_cpus'],[3,8]);self.assertEqual(len(result['guard_pack_processes']),2)
 def test_exact_original_misclassification_reproduced_and_minimal_fix(self):
  with TemporaryDirectory(dir=H) as d:
   root=Path(d);self.node(root,ROOT,1);self.node(root,101,ROOT);self.node(root,200,1,OLD)
   with patch.object(g.os,'getpid',return_value=ROOT),patch.object(g,'task_reservation',return_value=TASK):old=g.external_observation(root)
   self.assertEqual(set(old['prior_historical_processes']),{101,200})
   self.assertEqual(self.observe(root)['prior_historical_processes'],[200])

if __name__=='__main__':unittest.main(verbosity=2)
