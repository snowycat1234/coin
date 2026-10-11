from pathlib import Path
import sys
import numpy as np
import polars as pl
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from persist_wallets import encode_column,decode_column


def test_float_bits_exact_with_signed_zero_and_small_amounts():
    a=np.array([0.,-0.,1e-18,-1234.123456789,1e18,1.0000000000000002])
    spec,data=encode_column(pl.Series('nav',a))
    assert decode_column(spec,data).tobytes()==a.tobytes()


def test_microsecond_integer_clocks_exact_above_float_precision():
    a=np.array([2**60+1,2**60+2,2**60+60000000],dtype=np.int64)
    spec,data=encode_column(pl.Series('close_us',a))
    assert decode_column(spec,data).tobytes()==a.tobytes()


def test_payload_corruption_and_wrong_size_rejected():
    spec,data=encode_column(pl.Series('quantity',[1.,2.,3.]))
    with pytest.raises(ValueError,match='byte count'):decode_column(spec,data[:-1])
    with pytest.raises(ValueError,match='SHA'):decode_column(spec,bytes([data[0]^1])+data[1:])
