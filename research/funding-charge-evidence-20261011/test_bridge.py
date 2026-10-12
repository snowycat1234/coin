import importlib.util
import json
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location('charge_bridge',Path(__file__).with_name('bridge.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

EVENT=dict(symbol='BTCUSDT',calc_time_ms=1664841600010,last_funding_rate='.0001',past_mark_price='19000')
ROW=dict(symbol='BTCUSDT',fundingTime=1664841600010,fundingRate='.0001000',markPrice='19001')


def test_stored_numeric_pair_dedups_but_cannot_selfcertify_authority():
    paired,proof=m.pair_events([EVENT],json.dumps([ROW,ROW]).encode())
    assert paired[0]['charge_mark_price']=='19001' and proof['paired_events']==1
    assert not proof['native_funding_certified'] and not proof['unit_inferred']


def test_unstored_or_clock_shifted_charge_point_cannot_use_nearest_bar():
    paired,_=m.pair_events([EVENT]);assert paired[0]['charge_mark_price'] is None
    shifted={**ROW,'fundingTime':ROW['fundingTime']-10}
    paired,_=m.pair_events([EVENT],json.dumps([shifted]).encode())
    assert paired[0]['status'].startswith('BLOCKED') and not paired[0]['old_past_mark_substituted']


@pytest.mark.parametrize('field,value',[('fundingRate','.01'),('markPrice','19002')])
def test_exact_event_conflicting_source_cannot_dedup(field,value):
    with pytest.raises(ValueError,match='Conflicting'):m.pair_events([EVENT],json.dumps([ROW,{**ROW,field:value}]).encode())


def test_percent_change_missing_price_or_nonfinite_is_not_accepted():
    with pytest.raises(ValueError,match='rawrateconflict'):m.pair_events([EVENT],json.dumps([{**ROW,'fundingRate':'.01'}]).encode())
    missing={k:v for k,v in ROW.items() if k!='markPrice'}
    with pytest.raises(ValueError,match='no minute-price fallback'):m.pair_events([EVENT],json.dumps([missing]).encode())
    with pytest.raises(ValueError,match='Finite'):m.pair_events([EVENT],json.dumps([{**ROW,'markPrice':'NaN'}]).encode())
