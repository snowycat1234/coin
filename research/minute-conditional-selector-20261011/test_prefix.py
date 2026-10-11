import io
import zipfile
import numpy as np
import pytest
from prepare_selector import prefix_array


def test_future_feature_rows_never_parsed_and_prefix_invariant():
    a=np.arange(4*5*2,dtype=np.float32).reshape(4,5,2)
    first=io.BytesIO();np.savez_compressed(first,x=a)
    changed=a.copy();changed[2:]=np.nan
    second=io.BytesIO();np.savez_compressed(second,x=changed)
    with zipfile.ZipFile(io.BytesIO(first.getvalue())) as z:x=prefix_array(z,'x',2)
    with zipfile.ZipFile(io.BytesIO(second.getvalue())) as z:y=prefix_array(z,'x',2)
    np.testing.assert_array_equal(x,a[:2]);np.testing.assert_array_equal(x,y)
    assert x.shape==(2,5,2)


def test_fortran_axis_must_not_read_future_rows():
    f=io.BytesIO();np.savez_compressed(f,x=np.asfortranarray(np.ones((4,5,2))))
    with zipfile.ZipFile(io.BytesIO(f.getvalue())) as z:
        with pytest.raises(AssertionError):prefix_array(z,'x',2)
