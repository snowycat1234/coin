import numpy as np
from test_mark import frame
from recover_gapped import observed_primitives
import cold_gapped
import recover_gapped


def test_partial_day_extrema_risk_unknown_actual_last_boundary_retained():
    d=frame(3*1440);d=d.drop(index=[1440+9,1440+14]).reset_index(drop=True)
    v,t,five=observed_primitives(d,99.,1640995200000,1641254400000)
    assert v['observed_minutes'].tolist()==[1440,1438,1440]
    assert np.isnan(v['RV_1m'][1]) and np.isnan(v['high'][1]) and np.isnan(v['max_log_up'][1])
    assert v['close'][1]==101 and np.isfinite(v['RV_1m'][2])
    assert np.isnan(five[288+1]) and np.isnan(five[288+2])
    assert len(t)==3 and len(five)==3*288


def test_missing_day_end_never_ffill_next_day_anchor():
    d=frame(3*1440).drop(index=2*1440-1).reset_index(drop=True)
    v,_,_=observed_primitives(d,99.,1640995200000,1641254400000)
    assert np.isnan(v['close'][1]) and np.isnan(v['RV_1m'][2])
    assert v['observed_minutes'][2]==1440


def test_complete_observed_source_matches_original_primitives():
    from mark_source import measure
    d=frame();v,t,f=observed_primitives(d,99.,1640995200000,1641081600000)
    original,ot,of=measure(d,99.)
    for k,a in v.items():np.testing.assert_array_equal(a,original[k])
    np.testing.assert_array_equal(t,ot);np.testing.assert_array_equal(f,of)


def test_official_partial_day_union_preserves_shared_hole(monkeypatch):
    from test_mark import row
    d=frame().drop(index=9).reset_index(drop=True)
    month=row();day=row(period='2022-01-01')
    monkeypatch.setattr(recover_gapped,'decode',lambda *args:(d.copy(),0))
    reader=type('Reader',(),{'inventory':{'reusable_price_archives':[]}})()
    f,e=recover_gapped.observed_month(reader,month,1640995200000,1641081600000,
        daily_get=lambda *args:day)
    assert len(f)==1439 and e['remaining_missing_open_ms']==[1640995740000]
    assert not e['exact_complete_grid']
    assert e['repairs'][0]['common_rows']==1439 and e['repairs'][0]['added_actual_rows']==0
