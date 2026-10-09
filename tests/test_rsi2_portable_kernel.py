"""Exact old-wrapper numerical parity and unchanged daily strategy behavior."""
import importlib.util
from pathlib import Path
import subprocess

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_rsi2_indicator as indicator
from scripts.investment import public_rsi2_adapter as strategy
from scripts.investment import rsi2_daily_pool_target as daily


@pytest.fixture
def original_wrapper(tmp_path,monkeypatch):
    source=subprocess.check_output(['git','show','390271379f24b251eb0659d1e8c62db2c4917af9:scripts/investment/public_rsi2_indicator.py'])
    p=tmp_path/'original_wrapper.py';p.write_bytes(source)
    spec=importlib.util.spec_from_file_location('original_rsi_wrapper',p);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    root=indicator.ROOT;vendor=indicator.VENDOR;target=Path(__import__('os').environ['COIN_RSI2_KERNEL_TARGET']).resolve()
    old.ROOT=root;old.VENDOR=vendor
    # Only filesystem location is remapped in this unchanged historical
    # reference. All source, strategy, indicator and kernel bytes are original.
    legacy=old.KERNEL_TARGET;old.KERNEL_TARGET=target
    old.Path=lambda p:target if Path(p)==legacy else Path(p)
    return old


def test_exact_scalar_and_sequential_numerical_parity(original_wrapper):
    rng=np.random.default_rng(781)
    paths=[np.full(300,100.),np.arange(1.,301.),np.arange(301.,1.,-1.),100*np.exp(np.cumsum(rng.normal(0,.02,300)))]
    for close in paths:
        candle=np.column_stack([np.arange(len(close)),close,close,close+.1,close-.1,np.ones(len(close))])
        for n in (240,241,300):assert indicator.rsi(candle[:n])==original_wrapper.rsi(candle[:n])
        assert indicator.rsi(close)==original_wrapper.rsi(close)
        assert np.array_equal(indicator.rsi_series(close),original_wrapper.rsi_series(close),equal_nan=True)
    assert indicator.kernel_receipt()['official_functions_ast_sha256']==original_wrapper.kernel_receipt()['official_functions_ast_sha256']


def test_daily_long_short_state_and_future_causality_match_original_wrapper(original_wrapper,monkeypatch):
    day=86_400_000_000;names=('ETHUSDT','BTCUSDT')
    series=[np.array([50.]*230+[500.]*6+[100.]*5+[101.,100.,100.,999.]),np.array([400.]*230+[50.]*6+[300.]*5+[299.9,300.,300.,777.])]
    bars=pl.concat([pl.DataFrame(dict(symbol=[s]*len(x),open_us=np.arange(len(x))*day,close_us=(np.arange(len(x))+1)*day,available_us=(np.arange(len(x))+1)*day,open=x,high=x+.1,low=x-.1,close=x,volume=np.ones(len(x)))) for s,x in zip(names,series,strict=True)])
    decisions=np.arange(240,245,dtype=np.int64)*day
    current,meta=daily.fixed_targets(bars,decisions,'LONG_SHORT',symbols=names)
    monkeypatch.setattr(strategy,'indicator',original_wrapper)
    reference,ref_meta=daily.fixed_targets(bars,decisions,'LONG_SHORT',symbols=names)
    assert current.equals(reference) and meta==ref_meta
    expected=np.array([[1,-1],[1,-1],[0,0],[1,-1],[1,-1]])*.3
    assert np.array_equal(current['raw_signed_target'].to_numpy().reshape(5,2),expected)
    changed=bars.with_columns([pl.when(pl.col('close_us')>decisions[1]).then(pl.col(k)*9).otherwise(pl.col(k)).alias(k) for k in ('open','high','low','close')])
    prefix,_=daily.fixed_targets(changed,decisions[:2],'LONG_SHORT',symbols=names)
    assert current.filter(pl.col('available_us')<=decisions[1]).equals(prefix)


def test_portable_location_rejects_unverified_install(tmp_path,monkeypatch):
    monkeypatch.setenv('COIN_RSI2_KERNEL_TARGET',str(tmp_path));monkeypatch.setattr(indicator,'_CONTEXT',None)
    with pytest.raises(FileNotFoundError):indicator.kernel_receipt()
