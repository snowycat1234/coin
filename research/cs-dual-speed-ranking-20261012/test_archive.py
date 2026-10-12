"""Lossless layout may save bytes but must reproduce original NPZ and float bits."""
import numpy as np
from archive import encode_chunk,decode_chunk,sha
def test_columns_restore_original_npz_bytes_and_signed_zero(tmp_path):
    a=np.random.default_rng(811710).normal(size=(1440,36));a[0,:4]=[0.,-0.,np.nextafter(0.,1.),np.nextafter(1.,2.)]
    old=tmp_path/'old.npz';new=tmp_path/'new.npz';np.savez_compressed(old,minute_chunk=a);decode_chunk(encode_chunk(old),new,sha(old));assert old.read_bytes()==new.read_bytes()
    with np.load(new,allow_pickle=False) as z:np.testing.assert_array_equal(a.view(np.uint64),z['minute_chunk'].view(np.uint64))
