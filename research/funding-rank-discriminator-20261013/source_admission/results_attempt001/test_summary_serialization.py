"""Tiny future-reporting regression; no source or historical engine calls."""
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from run_baskets_serialization_fixed import clean
import numpy as np


class SummarySerializationTest(unittest.TestCase):
    def test_numpy_scalar_count_and_boolean_become_plain_JSON(self):
        counts={'count':np.int64(4),'tied':np.bool_(False),'nested':{'rate':np.float64(.001)}}
        encoded=json.dumps(clean(counts),allow_nan=False)
        self.assertEqual(json.loads(encoded),{'count':4,'tied':False,'nested':{'rate':.001}})


if __name__=='__main__':unittest.main(verbosity=2)
