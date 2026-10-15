"""Independent finite fresh-process source graph tests; fake boundaries only."""
from pathlib import Path
import importlib.machinery
import importlib.util
import json
import subprocess
import sys
import types
import unittest
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v4'))
import cs_source_guard as boundary
import cs_signal as signal
import cs_source_bridge

class GuardReview(unittest.TestCase):
    def assert_block(self,category,action):
        guard=boundary.SourceOnlyGuard()
        with self.assertRaisesRegex(boundary.SourceBoundaryViolation,'FORBIDDEN_ATTEMPTS_FATAL'):
            with guard:
                try:action()
                except boundary.SourceBoundaryViolation:pass
        self.assertEqual(guard.attempts[category],1)
        self.assertEqual(sum(guard.attempts.values()),1)
        self.assertFalse(guard.active)
        return guard
    def test_01_valid_pure_signal_graph_has_observed_zero(self):
        t=signal.ANCHOR+np.arange(-230,30,dtype=np.int64)*signal.DAY
        x=np.arange(len(t))[:,None]
        p=np.exp(x*np.array([.001,.002,.003,.004,.005])+.006*np.sin(x*np.array([.13,.17,.23,.29,.31])))*100
        read_paths=[signal.HERE/'sources/reference'/name for name in signal.SOURCE_PINS]+[signal.GRID_PATH]
        guard=boundary.SourceOnlyGuard(read_paths=read_paths)
        with guard:
            out=signal.project_arrays(p,t,t,t[220:234])
            guard.checkpoint('GENERATED_VALID_PURE_AST_SIGNAL_GRAPH')
        self.assertEqual(out[0].shape,(14,5))
        self.assertEqual(sum(guard.attempts.values()),0)
        self.assertFalse(hasattr(signal.common_grid(),'make_account'))
        self.assertFalse(hasattr(signal.common_grid(),'_vendor'))
        self.assertFalse(hasattr(signal.common_grid(),'_load'))
    def test_02_preloaded_and_captured_fake_finance_denied_before_body(self):
        fixture=types.ModuleType('_cs_guard_review_fixture');fixture.__source_guard_fixture__=True
        called=[]
        obj_type=type('FakeAccount',(),{'advance_day':lambda self:called.append('UNBLOCKED')})
        fixture.FakeAccount=obj_type;sys.modules[fixture.__name__]=fixture
        obj=object.__new__(obj_type);captured=obj.advance_day
        guard=boundary.SourceOnlyGuard()
        try:
            with self.assertRaisesRegex(boundary.SourceBoundaryViolation,'PRELOADED_FINANCIAL_GRAPH'):
                with guard:captured()
            self.assertEqual(called,[]);self.assertEqual(guard.attempts['financial_imports'],1)
            self.assertFalse(guard.active)
        finally:sys.modules.pop(fixture.__name__,None)
    def test_03_direct_filename_loader_is_blocked(self):
        self.assert_block('financial_imports',lambda:importlib.util.spec_from_file_location('_never_loaded',ROOT/'NEVER_OPENED.py'))
    def test_04_direct_source_loader_is_blocked(self):
        loader=importlib.machinery.SourceFileLoader('_never_loaded',str(ROOT/'NEVER_OPENED.py'))
        module=types.ModuleType('_never_loaded')
        self.assert_block('financial_imports',lambda:loader.exec_module(module))
    def test_05_subprocess_preflight_is_blocked_no_process(self):
        self.assert_block('process_launches',lambda:subprocess.run(['FORBIDDEN_NEVER_EXECUTED']))
    def test_06_financial_authority_serialization_is_blocked(self):
        self.assert_block('financial_GO_writes',lambda:json.dumps({'historical_execution_authorized':True}))
    def test_07_nonallowlisted_read_is_blocked_before_open(self):
        self.assert_block('nonallowlisted_file_reads',lambda:(ROOT/'DOES_NOT_EXIST_NO_MARKET_DATA').read_bytes())
    def test_08_nonallowlisted_write_is_blocked_before_open(self):
        self.assert_block('outside_source_writes',lambda:(ROOT/'NEVER_WRITTEN_BY_CS_REVIEW').write_text('forbidden'))

if __name__=='__main__':unittest.main(verbosity=2)
