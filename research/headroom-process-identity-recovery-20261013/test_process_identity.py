"""Pure process relation tests and one real sleeping-child fixture; no finance."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from process_identity import own_process_ids,fixed_external_observation

MARK='coin_headroom_risk_candidate_20261013/run_cases.py'
GATE=SimpleNamespace(PACK_RELATIVE='pack.py',PACK_VERIFY_RELATIVE='verify_pack.py',PACK_RESERVED_BYTES=2_000_000_000,
    PRIOR_RUNNERS=(MARK,),task_reservation=lambda:{'pack_task_released':True,'task_reserved_bytes':0,'task_busy_cpus':[],'release_receipt_SHA256':'fixture'})

def record(root,pid,ppid,financial=True,valid=True):
    p=root/str(pid);p.mkdir();(p/'status').write_text(f'Pid:\t{pid}\nPPid:\t{ppid}\n' if valid else 'UNKNOWN')
    (p/'cmdline').write_bytes(('python\0'+(MARK if financial else 'sleep.py')+'\0').encode())

class IdentityTests(unittest.TestCase):
    def test_only_self_and_real_descendants_no_children_file_needed(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);record(p,100,90);record(p,101,100);record(p,102,101);record(p,90,1)
            self.assertEqual(own_process_ids(p,100),{100,101,102})

    def test_financial_parent_sibling_orphan_still_external(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);pid=os.getpid();record(p,pid,700001);record(p,700001,1);record(p,700002,700001);record(p,700003,1)
            observed=fixed_external_observation(GATE,p)
            self.assertEqual(set(observed['prior_historical_processes']),{700001,700002,700003})

    def test_matching_unknown_parent_identity_never_assumed_own(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);record(p,700004,os.getpid(),valid=False)
            self.assertEqual(fixed_external_observation(GATE,p)['prior_historical_processes'],[700004])

    def test_unrelated_cycle_is_not_own(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);record(p,100,90);record(p,200,201);record(p,201,200)
            self.assertEqual(own_process_ids(p,100),{100})

    def test_real_child_status_detected_when_children_file_absent(self):
        child=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)',MARK,'SYNTHETIC_ONLY_NO_FINANCE'])
        try:
            self.assertIn(child.pid,own_process_ids())
            self.assertNotIn(child.pid,fixed_external_observation(GATE)['prior_historical_processes'])
        finally:child.terminate();child.wait()

    def test_operation_namespace_has_exact_original_case_and_review(self):
        import hashlib
        h=Path(__file__).resolve().parent;c=h.parent/'coin_headroom_risk_candidate_20261013'
        for name in ('CASE_BINDINGS.json','REVIEW_RECEIPT.json'):
            self.assertEqual(hashlib.sha256((h/'operation_namespace'/name).read_bytes()).digest(),hashlib.sha256((c/name).read_bytes()).digest())

    def test_cloud_original_marker_and_account_evidence_block_duplicate(self):
        from run_fixed import require_cloud_unstarted
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);self.assertEqual(require_cloud_unstarted(p)['historical_wallets_started'],0)
            (p/'HISTORICAL_LAUNCH.json').write_text('{}')
            with self.assertRaises(RuntimeError):require_cloud_unstarted(p)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);d=p/'state_old'/'Y2024_STATIC50_FINE_HEADROOM';d.mkdir(parents=True);(d/'BINDING.json').write_text('{}')
            with self.assertRaises(RuntimeError):require_cloud_unstarted(p)

if __name__=='__main__':unittest.main(verbosity=2)
