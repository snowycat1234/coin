"""Independent bounded transport probes. Mock child, no account/source/history executes."""
import argparse,inspect,json,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
ap=argparse.ArgumentParser(add_help=False);ap.add_argument('--module',type=Path,required=True);a,tail=ap.parse_known_args();sys.argv=[sys.argv[0],*tail];MODULE=a.module.resolve();sys.path.insert(0,str(MODULE))
import recovery_transport as r
from test_transport import Fixture

class Independent(unittest.TestCase):
 def test_actual_parent_path_calls_only_unchanged_candidate_and_preserves_ledger(self):
  with tempfile.TemporaryDirectory() as tmp:
   f=Fixture(tmp);before=f.ledger_path.read_bytes();calls=[];commands=[]
   v=SimpleNamespace(read=lambda p:({'files':{'Y2025_TARGETS.npz':{'SHA256':'c'*64}}} if Path(p).name=='TARGET_REMOTE_BINDING.json' else r.read(p)),HERE=f.root,
     inp=SimpleNamespace(registry=lambda:{'years':{'2025':{'index':{'SHA256':'b'*64}}}}),verify_financial=lambda roots:calls.append('finance_guard'),require_review=lambda *x:calls.append('original_review'),bind_saved_targets=lambda *x:calls.append('targets'),source_window=lambda *x:calls.append('source'))
   guard=SimpleNamespace(DISK_RESERVE=1,HOST_USED_LIMIT=8_000_000_000,process_rss=lambda pid:1,memory_observation=lambda:{'host_used':1,'SwapTotal':0})
   original=SimpleNamespace(v=v,publication_identity=lambda *x:calls.append('original_publication'),go_identity=lambda *x:calls.append(('original_go',x[4],x[5])),resource_admission=lambda *x:(calls.append('resource') or {'allowed_cpus':[7,8]}),original_resource_guard=lambda roots:guard)
   args=SimpleNamespace(original_module=str(f.root/'original'),roots=str(f.roots_path),original_ledger=str(f.ledger_path),control_case=str(f.control_case),recovery_receipt=str(f.zero_path),recovery_results=str(f.results_path),recovery_admission=str(f.admission_path),recovery_admission_sha=r.sha(f.admission_path),original_review='/TOY_REVIEW',original_go=str(MODULE/'recovery_evidence/PARENT_GO_2025.json'),transport_commit='1'*40,transport_review='/TOY_NEW_REVIEW',transport_review_sha='d'*64,transport_go='/TOY_NEW_GO',transport_go_sha='e'*64,output=str(f.workspace/r.OUTPUT_NAMESPACE))
   def popen(command,**kw):
    calls.append('child');commands.append((command,kw));case=Path(args.output)/r.CASE;case.mkdir();(case/'SUMMARY.json').write_text(json.dumps({'transport_stop_reason':None,'mock_only':True}))
    with patch.object(r.os,'sched_setaffinity') as affinity,patch.object(r.resource,'setrlimit') as limits:
     kw['preexec_fn']();affinity.assert_called_once_with(0,{7});self.assertIn(((r.resource.RLIMIT_AS,(4_000_000_000,4_000_000_000)),),[(q.args,) for q in limits.call_args_list]);cpu=[q.args[1] for q in limits.call_args_list if q.args[0]==r.resource.RLIMIT_CPU][0];self.assertTrue(0<cpu[0]<=600);self.assertEqual(cpu[0],cpu[1])
    return SimpleNamespace(pid=999999,returncode=0,poll=lambda:0,wait=lambda:0)
   with f.pins(),patch.object(r,'HERE',f.root),patch.object(r,'verify_freeze',return_value=f.policy),patch.object(r,'transport_authorization',return_value=r.sha(f.freeze_path)),patch.object(r,'load_original',return_value=original),patch.object(r.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout=f.freeze_path.read_bytes())),patch.object(r.subprocess,'Popen',side_effect=popen),patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=10**12)),patch.object(r.fcntl,'flock'):
    result=r.dispatch(args);self.assertEqual(result['completed'],['2025_candidate']);self.assertEqual(len(commands),1);cmd,kw=commands[0]
    for flag,value in [('--year','2025'),('--arm','candidate'),('--publication-commit',r.ORIGINAL_COMMIT),('--review-sha',r.ORIGINAL_REVIEW_SHA256),('--parent-go-sha',r.ORIGINAL_GO_SHA256)]:self.assertEqual(cmd[cmd.index(flag)+1],value)
    self.assertIn('--worker',cmd);self.assertEqual(cmd[2],str((f.root/'original/dispatcher.py').resolve()));self.assertTrue(kw['start_new_session']);self.assertEqual(kw['env']['_V2_PARENT_PID'],str(r.os.getpid()));self.assertLess(calls.index('source'),calls.index('resource'));self.assertLess(calls.index('resource'),calls.index('child'))
    effective=r.read(Path(args.output)/'EFFECTIVE_COMPLETION_INPUT.json');self.assertEqual(effective['completed'],[*r.PRIOR_COMPLETED,'2025_control']);self.assertFalse(effective['original_transport_control_success']);self.assertEqual(effective['original_control_attempt']['exit_code'],-9);self.assertEqual(before,f.ledger_path.read_bytes());self.assertEqual(result['original_elapsed_seconds'],1308.5219291619942);self.assertEqual(result['cumulative_elapsed_seconds'],result['original_elapsed_seconds']+result['elapsed_seconds'])
    with self.assertRaisesRegex(r.GateError,'NO_DUPLICATE'):r.dispatch(args)
    args.output=str(f.workspace/'alternate')
    with self.assertRaisesRegex(r.GateError,'SINGLE_CANDIDATE'):r.dispatch(args)
    self.assertEqual(len(commands),1)

 def test_all_retained_resource_stop_paths(self):
  guard=SimpleNamespace(DISK_RESERVE=15_000_000_000,HOST_USED_LIMIT=8_000_000_000,process_rss=lambda pid:1,memory_observation=lambda:{'host_used':1,'SwapTotal':0});process=SimpleNamespace(pid=1);case=Path('/SYNTHETIC_ONLY/case');policy={'output_cap_bytes':500_000_000}
  with patch.object(r.time,'monotonic',return_value=101),patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=10**12)),patch.object(r,'case_bytes',return_value=1):
   self.assertIsNone(r.monitor_stop(guard,process,case,policy,1308.5219291619942,0,100))
   for observation,expected in [({'host_used':8_000_000_001,'SwapTotal':0},'HOST_SWAP_RESOURCE_GATE'),({'host_used':1,'SwapTotal':1},'HOST_SWAP_RESOURCE_GATE'),({'host_used':1,'SwapTotal':0,'cgroup_swap_current':1},'HOST_SWAP_RESOURCE_GATE'),({'host_used':1,'SwapTotal':0,'cgroup_limit_verified':True,'cgroup_memory_current':11,'cgroup_memory_max':10},'CGROUP_MEMORY')]:
    with patch.object(guard,'memory_observation',return_value=observation):self.assertEqual(r.monitor_stop(guard,process,case,policy,1308,0,100),expected)
   with patch.object(guard,'process_rss',return_value=2_000_000_001):self.assertEqual(r.monitor_stop(guard,process,case,policy,1308,0,100),'DESCENDANT_RSS2GB')
   with patch.object(r.shutil,'disk_usage',return_value=SimpleNamespace(free=guard.DISK_RESERVE-1)):self.assertEqual(r.monitor_stop(guard,process,case,policy,1308,0,100),'DISK15GIB')
   with patch.object(r.time,'monotonic',return_value=700):self.assertEqual(r.monitor_stop(guard,process,case,policy,1308,0,100),'HARD_WALL_BUDGET')
   self.assertEqual(r.monitor_stop(guard,process,case,policy,3599.5,0,100),'HARD_WALL_BUDGET')

if __name__=='__main__':unittest.main(verbosity=2)
