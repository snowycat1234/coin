import importlib.util
from pathlib import Path
from copy import deepcopy
import pytest
from quant.perpetual_account import USDTLinearPerpetualAccount,D

spec=importlib.util.spec_from_file_location('finite_exit',Path(__file__).with_name('exit.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def owned_anchor(quantity=1000,close=0):
    a=USDTLinearPerpetualAccount(symbols=('DOGEUSDT',));t=m.START-2*m.MINUTE
    a.update_marks(t,{'DOGEUSDT':dict(price='0.06',close_us=t,available_us=t)})
    a.execute_fill('DOGEUSDT','BUY',quantity,t+1,t-m.MINUTE,'SYNTHETIC_OPEN',execution_mid_price='.06',quote_available_us=t)
    if close:
        a.execute_fill('DOGEUSDT','SELL',close,t+2,t-m.MINUTE,'SYNTHETIC_CLOSE',execution_mid_price='.06',quote_available_us=t,reduce_only=True)
    for at in (m.START-m.MINUTE,m.START):a.update_marks(at,{'DOGEUSDT':dict(price='0.06',close_us=at,available_us=at)})
    s=a.summary();s.update(cost_scenario=m.COSTS[0],pending_orders_at_stop={})
    return dict(summary=s,trades=deepcopy(a.trades),funding=deepcopy(a.funding)),deepcopy(a.marks)


def minute_rows(count=10,quote=20000):
    return [(m.START+i*m.MINUTE,{'DOGEUSDT':dict(open=.06,close=.06,mark=.06,quote_volume=quote)}) for i in range(count)]


def test_exact_financial_anchor_does_not_claim_missing_original_snapshot():
    body,marks=owned_anchor();a,proof=m.financial_anchor(body,marks)
    assert a.summary()['positions']==body['summary']['positions']
    assert proof['historical_fill_requests']=='UNKNOWN_NOT_RESTORED' and proof['original_market_minutes_replayed']==0
    with pytest.raises(ValueError,match='fill requests missing actual trades'):
        USDTLinearPerpetualAccount.from_snapshot(a.snapshot())
    bad=deepcopy(body);bad['summary']['decimal_strings']['fees_USDT']='0'
    with pytest.raises(ValueError,match='cost total bridge'):m.financial_anchor(bad,marks)


def test_capacity_paid_reduce_only_extension_exceeds_five_attempts_without_upsize():
    body,marks=owned_anchor(quantity=2000);a,_=m.financial_anchor(body,marks)
    e=m.extend(a,minute_rows(quote=18000),[],{'DOGEUSDT':18000.},m.START,m.START+10*m.MINUTE)
    assert len(e['attempts'])>5 and e['exact_paid_flat']
    assert e['fees_paid_USDT']>0 and e['execution_loss_paid_USDT']>0 and e['events_applied']==0
    assert all(r['leg']=='CLOSE' and r['side']=='SELL' for r in e['new_trades'])
    assert e['before']['contract']==e['after']['contract'] and not e['after']['contract']['closing_min_notional_exempt']


def test_original_minnotional_dust_kept_to_deadline_no_free_clearance():
    body,marks=owned_anchor(close=900);a,_=m.financial_anchor(body,marks)
    e=m.extend(a,minute_rows(6),[],{'DOGEUSDT':20000.},m.START,m.START+6*m.MINUTE)
    assert not e['exact_paid_flat'] and e['status']=='STOP_EXIT_DEADLINE_WITH_RESIDUAL'
    assert a.positions['DOGEUSDT'].quantity==100 and e['fees_paid_USDT']==0
    assert all(r['receipt']['reason']=='BELOW_MIN_NOTIONAL_OR_CAPACITY' for r in e['attempts'])


def test_future_actual_funding_paid_before_first_exit_and_cannot_replay_past():
    body,marks=owned_anchor();a,_=m.financial_anchor(body,marks)
    events=[dict(symbol='DOGEUSDT',event_us=m.START+10000,raw_rate=.001)]
    e=m.extend(a,minute_rows(),events,{'DOGEUSDT':20000.},m.START,m.START+10*m.MINUTE)
    assert e['events_applied']==1 and abs(e['funding_cash_USDT']+.06)<1e-12
    assert e['new_funding'][0]['event_us']<e['new_trades'][0]['event_us']
    a,_=m.financial_anchor(body,marks);events[0]['event_us']=m.START-1
    with pytest.raises(ValueError,match='new future funding'):m.extend(a,minute_rows(),events,{'DOGEUSDT':20000.},m.START,m.START+10*m.MINUTE)


def test_step_rounding_dust_is_not_forgiven_and_exact_boundary_funding_is_retained():
    body,marks=owned_anchor(quantity=2000);a,_=m.financial_anchor(body,marks)
    e=m.extend(a,minute_rows(),[dict(symbol='DOGEUSDT',event_us=m.START,raw_rate=.001)],
        {'DOGEUSDT':20000.},m.START,m.START+10*m.MINUTE)
    assert e['events_applied']==1 and e['new_funding'][0]['mark_close_us']==m.START-m.MINUTE
    assert not e['exact_paid_flat'] and a.positions['DOGEUSDT'].quantity==D('.00000002')


def test_missing_held_mark_stops_without_erasing_position_or_fees():
    body,marks=owned_anchor();a,_=m.financial_anchor(body,marks);q=a.positions['DOGEUSDT'].quantity
    e=m.extend(a,[(m.START,{})],[],{'DOGEUSDT':20000.},m.START,m.START+6*m.MINUTE)
    assert e['status']=='STOP_MISSING_HELD_EXECUTION_OR_MARK' and a.positions['DOGEUSDT'].quantity==q
    assert not e['new_trades'] and e['fees_paid_USDT']==0


def test_factory_identity_cannot_be_changed_to_close_dust():
    body,marks=owned_anchor();body['summary']['contract']['closing_min_notional_exempt']=True
    with pytest.raises(ValueError,match='contract/profile/cost'):m.financial_anchor(body,marks)


@pytest.mark.parametrize('kind',['future','reverse'])
def test_same_price_cannot_hide_future_or_reversed_restored_mark_clock(kind):
    body,marks=owned_anchor()
    if kind=='future':marks['DOGEUSDT'][-1]['close_us']+=m.MINUTE;marks['DOGEUSDT'][-1]['available_us']+=m.MINUTE
    else:marks['DOGEUSDT'].reverse()
    with pytest.raises(ValueError,match='lasttwo completion clocks'):m.financial_anchor(body,marks)
