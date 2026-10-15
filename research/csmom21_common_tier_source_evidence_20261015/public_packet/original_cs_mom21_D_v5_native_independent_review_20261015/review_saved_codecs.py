"""Generated saved-minute hostile-header validation; never actual saved files."""
from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import zipfile
import numpy as np
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_saved as saved


def npy(a):
    out=BytesIO();np.save(out,a,allow_pickle=False);return out.getvalue()


def header(shape,descr='<f8',fortran=False,payload=b''):
    out=BytesIO();np.lib.format.write_array_header_1_0(out,dict(descr=descr,fortran_order=fortran,shape=shape))
    return out.getvalue()+payload


def archive(values=None,columns=None,extra=None):
    values=npy(np.ones((2,3),dtype='<f8')) if values is None else values
    columns=npy(np.array(['close_us','nav','free_cash'])) if columns is None else columns
    out=BytesIO()
    with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('values.npy',values);z.writestr('columns.npy',columns)
        if extra:z.writestr(*extra)
    return out.getvalue()


class SavedCodecReview(unittest.TestCase):
    def denied_before_load(self,raw,rows=2):
        with patch.object(saved.np,'load',side_effect=AssertionError('ALLOCATION_BEFORE_HEADER_VALIDATION')) as load:
            with self.assertRaises((ValueError,EOFError)):saved.saved_minute(raw,rows)
            load.assert_not_called()

    def test_generated_positive_values_columns_roundtrip(self):
        values,columns=saved.saved_minute(archive(),2)
        self.assertEqual(values.tobytes(),np.ones((2,3),dtype='<f8').tobytes())
        self.assertEqual(columns,['close_us','nav','free_cash'])

    def test_huge_claimed_shape_rejected_before_numpy_load(self):
        self.denied_before_load(archive(values=header((2**60,3))))
        self.denied_before_load(archive(values=header((2,2**60))))

    def test_wrong_rows_dimensions_dtype_and_fortran_rejected_before_load(self):
        for h in (header((3,3)),header((2,)),header((2,3,1)),header((2,3),'<i8'),header((2,3),'<f8',True),header((2,3),'|O')):
            with self.subTest(h=h[:30]):self.denied_before_load(archive(values=h))

    def test_wrong_payload_length_rejected_before_load(self):
        self.denied_before_load(archive(values=header((2,3),payload=b'\x00'*8)))
        self.denied_before_load(archive(values=header((2,3),payload=b'\x00'*49)))

    def test_columns_count_itemsize_object_and_dimensions_bounded_before_load(self):
        for h in (header((4,),'<U1',payload=b'\x00'*16),header((3,),'<U1000'),header((3,1),'<U1'),header((3,),'|O'),header((129,),'<U1')):
            with self.subTest(h=h[:30]):self.denied_before_load(archive(columns=h))

    def test_duplicate_or_extra_namespace_rejected_before_load(self):
        self.denied_before_load(archive(extra=('other.npy',b'NOT_ARRAY')))
        self.denied_before_load(archive(extra=('values.npy',b'NOT_ARRAY')))

    def test_oversized_npy_header_rejected_before_load(self):
        raw=b'\x93NUMPY\x01\x00'+(5000).to_bytes(2,'little')+b' '*5000
        self.denied_before_load(archive(values=raw))

    def test_ordinary_flat_members_not_symlinks(self):
        out=BytesIO()
        with zipfile.ZipFile(out,'w') as z:
            x=zipfile.ZipInfo('values.npy');x.create_system=3;x.external_attr=(0o120777<<16)
            z.writestr(x,npy(np.ones((2,3))));z.writestr('columns.npy',npy(np.array(['a','b','c'])))
        self.denied_before_load(out.getvalue())

    def test_finite_values_and_unique_columns_required_after_bounded_load(self):
        bad=np.ones((2,3));bad[0,0]=np.nan
        with self.assertRaises(ValueError):saved.saved_minute(archive(values=npy(bad)),2)
        with self.assertRaises(ValueError):saved.saved_minute(archive(columns=npy(np.array(['a','a','c']))),2)

    def test_exact_integer_completed_rows_bound(self):
        for rows in (-1,525601,True,2.0):
            self.denied_before_load(archive(),rows)

if __name__=='__main__':unittest.main(verbosity=2)
