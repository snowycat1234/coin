import unittest,tempfile,hashlib,sys
from pathlib import Path
import numpy as np
import input_binding as b
class Tests(unittest.TestCase):
 def test_waiting(self):self.assertEqual(b.target_gate(),'WAITING_TARGET_BINDING / NO_GO')
 def test_no_arbitrary_targets(self):
  with self.assertRaises(ValueError):b.target_gate({'candidate':'old'})
 def test_paths(self):
  for n in ['/tmp/x','../x','a/../../x']:
   with self.assertRaises(ValueError):b.safe('.',n)
 def test_byte_tamper(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'event';p.write_bytes(b'raw');rec={'bytes':3,'SHA256':hashlib.sha256(b'raw').hexdigest()};b.check_file(d,'event',rec);p.write_bytes(b'bad')
   with self.assertRaises(ValueError):b.check_file(d,'event',rec)
 def test_schema(self):
  # Source-only synthetic quote arrays, never strategy targets or wallets.
  class Z(dict):
   @property
   def files(self):return list(self)
  z=Z(times=np.array([0,60000000],dtype=np.int64))
  for s in b.S:
   for k in ('open','close','quote_volume','mark'):z[s+'_'+k]=np.ones(2,dtype=np.float64)
  b.schema(z,0,2);z['times'][1]=60000001
  with self.assertRaises(AssertionError):b.schema(z,0,2)
 def test_no_financial_imports(self):self.assertFalse(any(x.startswith(('quant.','scripts.investment')) for x in sys.modules))
if __name__=='__main__':unittest.main()
