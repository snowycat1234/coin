"""Generated-only regressions for the three admission/transport corrections."""
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase,mock
import importlib.machinery,json,os,py_compile,resource,sys,tempfile,types
import bindings as B
import driver
from verified_source import VerifiedLoader,require_runtime

class CorrectionsTests(TestCase):
 def args(self,folder,command='case'):
  roots=Path(folder)/'GENERATED_ROOTS.json';roots.write_text('{}')
  return SimpleNamespace(command=command,year=2023,arm='GRID' if command=='case' else None,output=str(Path(folder)/'fresh'),roots=str(roots),review='UNUSED',review_sha='1'*64,source_go='UNUSED',source_go_sha='2'*64,source_receipt='UNUSED',source_receipt_sha='3'*64,case_go='UNUSED',case_go_sha='4'*64,remaining_seconds='595')

 def test_valid_timestamp_bytecode_never_supersedes_checked_source(self):
  with tempfile.TemporaryDirectory() as temp:
   path=Path(temp)/'generated.py';path.write_text("VALUE='STALE'\n");os.utime(path,(1234567890,1234567890));py_compile.compile(str(path),doraise=True)
   raw=b"VALUE='EXACT'\n";path.write_bytes(raw);os.utime(path,(1234567890,1234567890))
   generated=SimpleNamespace(bytes=lambda p:raw,loading={},records={},mode='generated')
   loader=VerifiedLoader(generated,'generated_verified_sentinel',path)
   module=types.ModuleType('generated_verified_sentinel');module.__file__=str(path);module.__spec__=importlib.machinery.ModuleSpec(module.__name__,loader,origin=str(path))
   loader.exec_module(module);self.assertEqual(module.VALUE,'EXACT')

 def test_unverified_cached_project_module_refused(self):
  runtime=require_runtime();saved=sys.modules.get('evidence');fake=types.ModuleType('evidence');fake.__file__=str(B.HERE/'evidence.py')
  try:
   sys.modules['evidence']=fake
   with self.assertRaisesRegex(ValueError,'UNVERIFIED_CACHED_PROJECT_MODULE'):runtime.check_cache()
  finally:
   if saved is None:sys.modules.pop('evidence',None)
   else:sys.modules['evidence']=saved

 def test_generated_runtime_cannot_waive_original26_financial_closure(self):
  with mock.patch.object(B,'require_go',return_value={'original26_hash_only_target_artifacts':['Y2023.npz','Y2025.npz']}):
   with self.assertRaisesRegex(ValueError,'CACHED_PROJECT_SOURCE_BODY_CHANGED|ORIGINAL26_HISTORICAL_RUNTIME_REQUIRED'):
    B.load_runtime('GENERATED_MOCK_ONLY','GENERATED_MOCK_ONLY',2023,'GRID')

 def test_infinite_soft_or_hard_resource_caps_refused_before_handoff(self):
  args=SimpleNamespace(remaining_seconds='595')
  for pair in ((-1,-1),(1,-1),(-1,600),(601,601),(0,600),(600,599)):
   with mock.patch.dict(os.environ,{'_GRID_PREP_PARENT_PID':'123'}),mock.patch.object(os,'getppid',return_value=123),mock.patch.object(os,'sched_getaffinity',return_value={0}),mock.patch.object(resource,'getrlimit',return_value=pair):
    with self.assertRaisesRegex(ValueError,'FINITE_SOFT_AND_HARD'):driver.bounded_worker_guard(args)

 def test_direct_worker_missing_controller_pipe_refused(self):
  with tempfile.TemporaryDirectory() as temp:
   with mock.patch.dict(os.environ,{'_GRID_PREP_CONTROLLER_FD':'-1'}):
    with self.assertRaisesRegex(ValueError,'VERIFIED_CONTROLLER_HANDOFF'):driver.require_controller_handoff(self.args(temp))

 def test_inherited_pipe_binding_and_year_mismatch(self):
  with tempfile.TemporaryDirectory() as temp:
   args=self.args(temp)
   for mismatch in (False,True):
    r,w=os.pipe();packet=driver.controller_packet(args);packet['parent_pid']=123
    if mismatch:packet['year']=2025
    os.write(w,json.dumps(packet).encode());os.close(w)
    with mock.patch.dict(os.environ,{'_GRID_PREP_CONTROLLER_FD':str(r),'_GRID_PREP_PARENT_PID':'123'}),mock.patch.object(os,'getppid',return_value=123),mock.patch.object(os,'kill'):
     if mismatch:
      with self.assertRaisesRegex(ValueError,'HANDOFF_BINDING_MISMATCH'):driver.require_controller_handoff(args)
     else:driver.require_controller_handoff(args)

 def test_monitor_exception_kills_reaps_and_preserves_receipt(self):
  with tempfile.TemporaryDirectory() as temp:
   args=self.args(temp)
   child=SimpleNamespace(pid=99999999,poll=mock.Mock(return_value=None),wait=mock.Mock(return_value=-9))
   guard=SimpleNamespace(process_rss=mock.Mock(return_value=100),memory_observation=mock.Mock(side_effect=RuntimeError('generated observer failure')),CASE_LIMIT=250000000)
   controller=SimpleNamespace(original_resource_guard=lambda roots:guard,resource_admission=lambda roots,out:{'allowed_cpus':[0,1]})
   with mock.patch.object(driver,'case_gates',return_value={}),mock.patch.object(B,'load_controller',return_value=controller),mock.patch.object(driver.subprocess,'Popen',return_value=child),mock.patch.object(os,'write',side_effect=lambda fd,data:len(data)),mock.patch.object(os,'killpg') as kill:
    receipt=driver.dispatch(args);kill.assert_called_once();child.wait.assert_called_once()
   self.assertEqual(receipt['resource_stop'],'LAUNCH_MONITOR_OR_ADMISSION_EXCEPTION')
   self.assertEqual(receipt['controller_error']['message'],'generated observer failure')
   self.assertTrue((Path(args.output)/'DISPATCH_RECEIPT.json').exists())

 def test_launch_exception_source_only_preserves_zero_wallet_failure(self):
  with tempfile.TemporaryDirectory() as temp:
   args=self.args(temp,'source-check');guard=SimpleNamespace(CASE_LIMIT=250000000)
   controller=SimpleNamespace(original_resource_guard=lambda roots:guard,resource_admission=lambda roots,out:{'allowed_cpus':[0,1]})
   with mock.patch.object(driver,'source_gates',return_value={}),mock.patch.object(B,'load_controller',return_value=controller),mock.patch.object(driver.subprocess,'Popen',side_effect=OSError('generated launch failure')),mock.patch.object(os,'killpg') as kill:
    receipt=driver.dispatch(args);kill.assert_not_called()
   self.assertEqual(receipt['controller_error']['message'],'generated launch failure');self.assertEqual(receipt['historical_wallets'],0)
   self.assertTrue(Path(args.output+'.source_attempt','DISPATCH_RECEIPT.json').exists())
