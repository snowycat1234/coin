import gzip,json
import numpy as np
import polars as pl
import pytest
from .storage import pack_case,hydrated_account
from modules.transformer_v2.train import sha
from .test_liquidation_engine import observed_window,targets,START,SYMBOLS
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as engine,audit_shared_direction as auditor

def test_storage_preserves_exact_json_decimals_and_ieee_floats(tmp_path):
    folder=tmp_path/'account';folder.mkdir()
    data=b'{"decimal_strings":{"margin":"0.123456789012345678901234567890"}}\n'
    (folder/'trades.json').write_bytes(data)
    values=np.array([0.,-0.,1e-100,1e100,np.nan,np.inf,-np.inf]*30)
    frame=pl.DataFrame(dict(close_us=np.arange(len(values)),nav=values));frame.write_parquet(folder/'minute_nav_inventory.parquet',compression='zstd')
    saved=dict(artifacts={p.name:dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in folder.iterdir()})
    packed=pack_case(saved,folder)
    assert gzip.decompress((folder/'trades.json.gz').read_bytes())==data
    with hydrated_account(folder,tmp_path/'scratch') as hydrated:
        assert (hydrated/'trades.json').read_bytes()==data
        restored=pl.read_parquet(hydrated/'minute_nav_inventory.parquet')
        assert np.array_equal(restored['nav'].to_numpy().view('uint64'),values.view('uint64'))
    assert not list((tmp_path/'scratch').iterdir())
    assert packed['artifacts']['trades.json']['uncompressed_sha256']

def test_storage_rejects_protected_symlink_and_detects_modified_compressed_json(tmp_path):
    old=tmp_path/'protected.json';old.write_text('{"unchanged":true}')
    folder=tmp_path/'new';folder.mkdir();p=folder/'trades.json';p.symlink_to(old)
    saved=dict(artifacts={p.name:dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)})
    with pytest.raises(ValueError,match='owned'):pack_case(saved,folder)
    assert old.read_text()=='{"unchanged":true}'

def test_xor_storage_rehydrates_real_liquidation_wallet_and_independent_auditor(tmp_path):
    window=observed_window(True)
    for s in SYMBOLS:
        window['market'][s]['mark']*=np.exp(.00001*np.sin(np.arange(4320)))
    case=engine.simulate(window,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=targets,account_factory=BybitIsolatedAccount,persist_cash_close=True)
    folder=tmp_path/'account';saved=engine.save_case(case,folder)
    (folder/'summary.json').write_text(json.dumps(saved['summary']))
    minute=case['minute'];ref=pl.DataFrame(dict(close_us=minute['close_us'],**{s:window['market'][s]['mark'] for s in SYMBOLS}))
    path=tmp_path/'observed_marks.parquet';ref.write_parquet(path)
    packed=pack_case(saved,folder,path)
    assert packed['artifacts']['minute_nav_inventory.parquet']['xor_market_reference']
    with hydrated_account(folder,tmp_path/'scratch') as hydrated:
        assert minute.equals(pl.read_parquet(hydrated/'minute_nav_inventory.parquet'))
        proof=auditor.verify(hydrated,SYMBOLS,1.)
        assert proof['terminal_cash_realized'] and proof['maximum_NAV_error_USDT']<1e-7
    path.write_bytes(b'broken reference')
    with pytest.raises(ValueError,match='reference changed'):
        with hydrated_account(folder,tmp_path/'scratch'):pass
