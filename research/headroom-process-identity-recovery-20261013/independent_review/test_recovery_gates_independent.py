"""Pure recovery gate counterexamples; no account construction or launch."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import importlib.util,json,sys,unittest
H=Path(__file__).resolve().parent;M=H.parent/'coin_headroom_process_recovery_20261013';sys.path.insert(0,str(M))
spec=importlib.util.spec_from_file_location('independent_recovery_shim',M/'run_fixed.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
IDS=['Y2021_STATIC50_FINE_HEADROOM','Y2023_STATIC50_FINE_HEADROOM']
class RecoveryGateTests(unittest.TestCase):
 def fixture(self,root):
  c=root/'candidate';c.mkdir();state=c/'state_original';state.mkdir();h=root/'patch';h.mkdir()
  (state/'RUN_BINDING.json').write_text(json.dumps({'fine_case_ids':IDS}));(state/'RESOURCE_RECEIPTS.json').write_text(json.dumps({'status':'STOP_PARTIAL','unstarted_case_ids':IDS[1:]}));(state/(IDS[0]+'.log')).write_bytes(b'');(c/'HISTORICAL_LAUNCH.json').write_text('{}')
  names=['HISTORICAL_LAUNCH.json','state_original/RUN_BINDING.json','state_original/RESOURCE_RECEIPTS.json','state_original/'+IDS[0]+'.log']
  (h/'ZERO_HISTORY_INPUTS.json').write_text(json.dumps({'original_state_root':str(state.resolve()),'original_files_SHA256':{name:r.sha(c/name) for name in names}}))
  return c,state,h
 def test_no_account_abort_accepted_then_any_initial_account_directory_rejected(self):
  with TemporaryDirectory(dir=H) as d:
   c,state,h=self.fixture(Path(d))
   with patch.object(r,'HERE',h):
    self.assertEqual(r.require_original_zero_history(c,state)['historical_wallets_started'],0)
    (state/IDS[0]).mkdir()
    with self.assertRaisesRegex(RuntimeError,'account directory'):r.require_original_zero_history(c,state)
 def test_original_log_and_STOP_bytes_must_remain_exact(self):
  with TemporaryDirectory(dir=H) as d:
   c,state,h=self.fixture(Path(d))
   with patch.object(r,'HERE',h):
    (state/(IDS[0]+'.log')).write_text('account initialized without ACCOUNT.json')
    with self.assertRaisesRegex(ValueError,'bytes changed'):r.require_original_zero_history(c,state)
    (state/(IDS[0]+'.log')).write_bytes(b'');(state/'RESOURCE_RECEIPTS.json').write_text('{}')
    with self.assertRaisesRegex(ValueError,'bytes changed'):r.require_original_zero_history(c,state)
 def test_cloud_actual_reservation_binding_or_checkpoint_rejects_duplicate(self):
  for name in ['HISTORICAL_LAUNCH.json','state_old/RUN_BINDING.json','state_old/Y2024_STATIC50_FINE_HEADROOM/BINDING.json','state_old/Y2024_STATIC50_FINE_HEADROOM/recovery/POINTER.json']:
   with self.subTest(name=name),TemporaryDirectory(dir=H) as d:
    c=Path(d);self.assertEqual(r.require_cloud_unstarted(c)['historical_wallets_started'],0)
    p=c/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text('{}')
    with self.assertRaises(RuntimeError):r.require_cloud_unstarted(c)
 def test_dangling_local_account_symlink_rejected(self):
  with TemporaryDirectory(dir=H) as d:
   c,state,h=self.fixture(Path(d));(state/IDS[0]).symlink_to('missing_account')
   with patch.object(r,'HERE',h):
    with self.assertRaises(RuntimeError):r.require_original_zero_history(c,state)
if __name__=='__main__':unittest.main(verbosity=2)
