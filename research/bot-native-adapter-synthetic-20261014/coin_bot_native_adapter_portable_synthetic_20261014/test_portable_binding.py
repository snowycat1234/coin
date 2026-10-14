import unittest
from unittest.mock import patch
from pathlib import Path
import json,os,tempfile
import bind_sources as B

class PortableBindingTests(unittest.TestCase):
 def test_code_gate_scope_and_no_arrays(self):
  r=B.verify_code_only()
  self.assertEqual(r['status'],'PASS_SYNTHETIC_CODE_CARRIER_ONLY')
  self.assertIs(r['original26_historical_closure_verified'],False)
  self.assertEqual(r['historical_target_artifacts_hashed'],0)
  self.assertFalse(any(p.suffix in ('.npz','.npy','.parquet','.arrow') for p in B.HERE.rglob('*')))

 def test_loading_cannot_read_arrays(self):
  import numpy as np
  raw_read=Path.read_bytes
  def guarded(path):
   if path.suffix in ('.npz','.npy'):raise AssertionError('ARRAY_HASH_OR_READ_FORBIDDEN')
   return raw_read(path)
  with patch.object(np,'load',side_effect=AssertionError('ARRAY_LOAD_FORBIDDEN')),patch.object(Path,'read_bytes',guarded):
   port,*_=B.load()
  for method in (port.verify,port.window,port.prepared,B.verify_financial,B.history_admission,B.bind_saved_targets,B.source_window):
   with self.assertRaisesRegex(B.GateError,'REFUSES_ORIGINAL26'):method('Y2023')

 def test_explicit_runtime_sites_required(self):
  for value in ([],None,False,['/definitely/missing/runtime/site']):
   if value is None:
    with patch.dict('os.environ',{'BOT_NATIVE_RUNTIME_SITES':'null'}):
     with self.assertRaises(B.GateError):B.configure_runtime()
   else:
    with self.assertRaises(B.GateError):B.configure_runtime(value)

 def test_assertions_required(self):
  with patch.dict('os.environ',{'PYTHONOPTIMIZE':'1'}):
   with self.assertRaisesRegex(B.GateError,'ASSERTIONS'):B.configure_runtime()

 def test_wrong_source_origin_rejected(self):
  port,*_=B.load();origin=port.__spec__.origin
  try:
   port.__spec__.origin='/tmp/incorrect_port_source.py'
   with self.assertRaisesRegex(B.GateError,'SHADOW'):B.load()
  finally:port.__spec__.origin=origin

 def test_runtime_site_priority_cannot_use_cached_other_site(self):
  B.configure_runtime()
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'numpy';p.mkdir();(p/'__init__.py').write_text("__version__='2.3.5'\n")
   sites=[folder,*json.loads(os.environ['BOT_NATIVE_RUNTIME_SITES'])]
   with self.assertRaisesRegex(B.GateError,'PRIORITY_OR_CACHED_SHADOW'):B.configure_runtime(sites)

if __name__=='__main__':unittest.main()
