"""Source-adapter counterexamples; no account/model/provider actions."""
import importlib.util
from pathlib import Path
import pandas as pd
import pytest
spec=importlib.util.spec_from_file_location('year2023_source',Path(__file__).with_name('source.py'));s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)
def rows(times,prices):
    from modules.collector_research.pipeline.normalize import PRICE_COLUMNS
    return pd.DataFrame([[t,p,p,p,p,1,t+59999,1,1,1,1,0] for t,p in zip(times,prices)],columns=PRICE_COLUMNS)
def test_source_union_retains_actual_missing_rows_and_rejects_conflict():
    old=rows([0,120000],[100,102]);day=rows([0,60000,120000],[100,101,102]);m,p=s.union_exact(old,day,'klines',0,180000)
    assert m.timestamp_ms.tolist()==[0,60000,120000] and m.close.tolist()==[100,101,102] and p['added_actual_rows']==1 and p['common_rows']==2
    wrong=day.copy();wrong.loc[0,['open','high','low','close']]=99
    with pytest.raises(ValueError,match='Conflicting'):s.union_exact(old,wrong,'klines',0,180000)
def test_source_clock_and_price_domain_reject_wrong_units_or_invalid_volume():
    from modules.collector_research.pipeline.normalize import validate_price
    f=rows([0,60000],[100,101]);f.loc[1,'timestamp_ms']=60000000
    with pytest.raises(ValueError,match='MILLISECONDS'):validate_price(f,'klines',0,120000)
    f=rows([0,60000],[100,101]);f.loc[1,'quote_volume']=-1
    with pytest.raises(ValueError,match='volume'):validate_price(f,'klines',0,120000)
