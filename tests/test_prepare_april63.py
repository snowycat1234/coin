"""Calendar/source recovery fixtures; no model fitting or account advancement."""
import json,sys
from pathlib import Path
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'research/recover-frozen-runner-20261009'))
import prepare_april63 as april
native=april.native;base=april.base;STATE=ROOT.parent/'coin-recovery-state'


def forbidden(*args,**kwargs):raise AssertionError('Dependent market/model/account work must not start')


def test_non63_calendar_rejected_before_inputs(monkeypatch):
    cal=dict(april.CALENDAR);cal.update(days=62,minutes=62*1440,end_exclusive=cal['start']+62*base.frozen.DAY)
    monkeypatch.setattr(base.frozen,'modules',forbidden)
    with pytest.raises(ValueError,match='Exactly63'):native.readiness(STATE,calendar=cal,contract_path=april.PUBLIC/'ADAPTER_CONTRACT.json')


def test_explicit_context_cannot_use_january_contract(monkeypatch):
    monkeypatch.setattr(base,'contexts',forbidden)
    with pytest.raises(ValueError,match='calendar/contract'):native.canonical_contexts(STATE,calendar=april.CALENDAR,contract_path=native.CONTRACT)


def test_corrupt_context_stops_before_market(tmp_path,monkeypatch):
    contract=base.frozen.read(april.PUBLIC/'ADAPTER_CONTRACT.json');name='CANONICAL_CONTEXTS63.npz'
    (tmp_path/name).write_bytes(b'altered retained context');contract['context_files']={name:contract['context_files'][name]}
    path=tmp_path/'ADAPTER_CONTRACT.json';path.write_text(json.dumps(contract))
    monkeypatch.setattr(base.frozen,'modules',lambda state:None);monkeypatch.setattr(base,'source_market_check',forbidden)
    with pytest.raises(ValueError,match='context bytes differ'):native.readiness(STATE,calendar=april.CALENDAR,contract_path=path)


@pytest.mark.parametrize('change',['missing_slot','interval_changed','nonfinite_rate'])
def test_funding_total_does_not_hide_bad_asset_clock_or_rate(monkeypatch,change):
    cal=april.CALENDAR;start=cal['start'];minute=base.frozen.MINUTE
    events=[dict(symbol=symbol,event_us=start+i*28800000000,raw_rate=.0001,reported_interval_hours=8) for symbol in base.frozen.SYMBOLS for i in range(189)]
    if change=='missing_slot':events[-1]['event_us']-=28800000000
    elif change=='interval_changed':events[-1]['reported_interval_hours']=4
    else:events[-1]['raw_rate']=float('nan')
    block=dict(times=np.arange(start,cal['end_exclusive'],minute,dtype=np.int64),market={s:dict(open=np.ones(90720),mark=np.ones(90720),quote_volume=np.ones(90720)) for s in base.frozen.SYMBOLS})
    monkeypatch.setattr(base.frozen,'modules',lambda state:None);monkeypatch.setattr(base,'source_market_check',lambda *args:{})
    monkeypatch.setattr(base,'market',lambda state,calendar:dict(events=events,minute_blocks=lambda:iter([block])))
    monkeypatch.setattr(native,'canonical_contexts',forbidden)
    with pytest.raises(ValueError,match='189 signed funding slots'):native.readiness(STATE,calendar=cal,contract_path=april.PUBLIC/'ADAPTER_CONTRACT.json')


def test_actual_prefix_keeps_raw_maturity_gap():
    report=april.prefix_availability(STATE)
    assert report['precutoff_decisions']==749 and report['raw_labels_mature_strictly_before_cutoff']==748
    assert report['crossing_sample_decision_us']==[1711843200000000]
    assert report['crossing_raw_label_available_us']==[1711929660000001]
    assert report['prospective_unique_feature_rows']==878
    assert report['terminal_clock_is_conditional_not_an_observed_label'] is True
    assert report['last_decision_plus_one_minute_plus_one_us']<april.CALENDAR['start']
    assert report['scaler_values'].startswith('NOT_FIT') and report['fits']==report['wallets_run']==0
