import sys
from pathlib import Path
import numpy as np
import pytest
from composite_bars import composite_bars,minute_observation,descriptor,MINUTE

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core5-continuous-mark-20261011'))
from test_mark import frame,row

LEFT=1640995200000;RIGHT=LEFT+86400000


def source(period,sha):
    r=row(period=period);r.update(ZIP_SHA256=sha*64,ZIP_bytes=123,official_checksum_text='fixture checksum\n',CHECKSUM_member_SHA256=None)
    return r


def fixture():
    month=source('2022-01','a');day=source('2022-01-01','b');monthly=frame().drop(index=9).reset_index(drop=True)
    reader=type('FixtureReader',(),{})()
    def decode(reader,r,l,h):return (monthly.copy() if r['frequency']=='monthly' else frame(),0)
    return reader,month,day,decode


def test_independent_added_owner_overlap_support_and_identical_ref_dedup():
    reader,month,day,decode=fixture()
    bars,merged=composite_bars(reader,month,LEFT,RIGHT,[day,day],decode)
    assert len(merged)==1440 and bars.provenance['identical_source_references_removed']==1
    assert bars.provenance['minute_owner_index'][9]==1 and bars.provenance['minute_support_bits'][9]==2
    assert bars.provenance['minute_owner_index'][10]==0 and bars.provenance['minute_support_bits'][10]==3
    assert bars.provenance['receipts'][1]['common_rows']==1439 and bars.provenance['receipts'][1]['added_actual_rows']==1
    assert bars.source_sha256 not in (month['ZIP_SHA256'],day['ZIP_SHA256'])
    with pytest.raises(ValueError):bars.provenance['minute_owner_index'][9]=0


def test_conflicting_one_numeric_field_hard_stops_and_domain_mixing_refused():
    reader,month,day,decode=fixture()
    def conflict(reader,r,l,h):
        d,_=decode(reader,r,l,h)
        if r['frequency']=='daily':d.loc[10,'high']=120
        return d,0
    with pytest.raises(ValueError,match='Conflicting'):composite_bars(reader,month,LEFT,RIGHT,[day],conflict)
    wrong={**day,'family':'klines'}
    with pytest.raises(ValueError,match='family'):composite_bars(reader,month,LEFT,RIGHT,[wrong],decode)


def test_daily_union_has_real_independent_provenance():
    reader,month,day,decode=fixture()
    union=dict(kind='DAILY_UNION',family=month['family'],symbol=month['symbol'],month=month['month'],daily_sources=[day])
    bars,_=composite_bars(reader,union,LEFT,RIGHT,decode=decode)
    assert np.all(bars.provenance['minute_owner_index']==0) and len(bars.provenance['missing_open_ms'])==0


def test_real_hole_is_unknown_until_completion_and_no_price_ffill():
    reader,month,_,decode=fixture()
    bars,_=composite_bars(reader,month,LEFT,RIGHT,decode=decode)
    missing=LEFT*1000+9*MINUTE
    assert minute_observation(bars,missing,missing)['status']=='NOT_YET_KNOWN'
    status=minute_observation(bars,missing,missing+MINUTE)
    assert status['status']=='SOURCE_MISSING_AT_COMPLETION' and status['price'] is None and not status['path_certifiable']
    assert len(bars.open_us)==1439 and bars.provenance['missing_open_ms'].tolist()==[missing//1000]


def test_same_day_legacy_close_golden_after_composite_repair():
    from mark_bars import source_bars,day_block,legacy_projection
    reader,month,day,decode=fixture();mark,_=composite_bars(reader,month,LEFT,RIGHT,[day],decode)
    trade_row=row('klines');trade_row['ZIP_SHA256']='c'*64
    trade=source_bars(frame(),trade_row,'klines')
    block=day_block(('BTCUSDT',),{'BTCUSDT':trade},{'BTCUSDT':mark},LEFT*1000)
    np.testing.assert_array_equal(legacy_projection(block)['market']['BTCUSDT']['mark'],frame().close.to_numpy())
    assert block['mark_sidecars']['BTCUSDT']['source_provenance']['kind']=='COMPOSITE_ORIGINAL_PRICE_SOURCES'
