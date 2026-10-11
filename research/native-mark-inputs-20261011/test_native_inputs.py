import sys
from pathlib import Path
import numpy as np
import pytest
from mark_bars import source_bars,day_block,legacy_projection,range_witness,exact_boundary,MINUTE,DAY
from economic_readiness import funding_readiness,unique_funding_events,risk_rule_readiness

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'core5-continuous-mark-20261011'))
from test_mark import frame,row

LEFT=1640995200000000


def bars(family='markPriceKlines',symbol='BTCUSDT',data=None):
    source=row(family,symbol);source['ZIP_SHA256']='a'*64
    return source_bars(frame() if data is None else data,source,family)


def bound():
    return dict(status='VERIFIED_HISTORICAL_AUTHORITY',SHA256='b'*64,venue='SYNTHETIC',product='TEST_LINEAR',symbol='BTCUSDT',
                effective_from_us=0,effective_to_us=2*LEFT)


def funding():
    return dict(symbol='BTCUSDT',event_us=LEFT,raw_rate='.01',raw_unit='PERCENT',unit_authority=bound(),
        charge_mark=dict(kind='EXACT_FUNDING_CHARGE_MARK',symbol='BTCUSDT',event_us=LEFT,price='100',
                         venue='SYNTHETIC',product='TEST_LINEAR',authority=bound()))


def test_trade_identity_cannot_supply_mark_and_illegal_ohlc_refused():
    r=row('klines');r['ZIP_SHA256']='a'*64
    with pytest.raises(ValueError,match='family'):source_bars(frame(),r,'markPriceKlines')
    d=frame();d.loc[0,'high']=99
    with pytest.raises(ValueError,match='OHLC'):bars(data=d)


def test_range_witness_has_no_liquidation_time_or_account_mutation():
    mark=bars()
    w=range_witness(mark,0,side='SHORT',threshold=105,known_at_us=LEFT+MINUTE,owned_since_us=LEFT-1)
    assert mark.values['close'][0]<105 and w['status']=='RANGE_WITNESS'
    assert w['extreme_event_us']=='UNKNOWN' and not w['account_transition_created'] and not w['liquidation_event_created']
    with pytest.raises(ValueError,match='Trade'):range_witness(bars('klines'),0,side='SHORT',threshold=105,
        known_at_us=LEFT+MINUTE,owned_since_us=LEFT-1)


def test_high_low_available_only_after_source_minute_completion():
    m=bars();assert m.close_us[0]==LEFT+MINUTE-1000 and m.available_us[0]==LEFT+MINUTE
    with pytest.raises(ValueError,match='unavailable'):range_witness(m,0,side='SHORT',threshold=105,
        known_at_us=LEFT,owned_since_us=LEFT-1)


@pytest.mark.parametrize('opened,events',[(LEFT+1,()),(LEFT-1,(LEFT+1,)),(None,())])
def test_intraminute_entry_funding_or_unknown_ownership_is_ambiguous(opened,events):
    w=range_witness(bars(),0,side='SHORT',threshold=105,known_at_us=LEFT+MINUTE,
                    owned_since_us=opened,events_us=events)
    assert w['status']=='AMBIGUOUS_INTRAMINUTE' and not w['fill_created']


def test_previous_source_boundary_never_forward_filled():
    m=bars();assert exact_boundary(m,LEFT+MINUTE)['price']==101
    missing=bars(data=frame().drop(index=0).reset_index(drop=True))
    with pytest.raises(ValueError,match='previous'):exact_boundary(missing,LEFT+MINUTE)


def test_held_asset_hole_never_removed_by_inner_join():
    trade={'BTCUSDT':bars('klines')};mark={'BTCUSDT':bars(data=frame().drop(index=9).reset_index(drop=True))}
    with pytest.raises(ValueError,match='SOURCE_GAPPED:BTCUSDT'):day_block(('BTCUSDT',),trade,mark,LEFT)


def test_wrong_asset_order_refused_and_legacy_projection_golden():
    names=('BTCUSDT','ETHUSDT');trade={s:bars('klines',s) for s in names};mark={s:bars(symbol=s) for s in names}
    with pytest.raises(ValueError,match='order'):day_block(names,dict(reversed(list(trade.items()))),mark,LEFT)
    block=day_block(names,trade,mark,LEFT);projected=legacy_projection(block)
    assert set(projected)=={'times','market'} and set(projected['market']['BTCUSDT'])=={'open','close','quote_volume','mark'}
    np.testing.assert_array_equal(projected['market']['BTCUSDT']['mark'],mark['BTCUSDT'].values['close'])
    assert block['mark_sidecars']['BTCUSDT']['mark_ohlc']['high'][0]==110
    with pytest.raises(ValueError):block['mark_sidecars']['BTCUSDT']['mark_ohlc']['high'][0]=0
    from scripts.investment.resumable_perpetual import MarketTape
    tape=MarketTape(dict(start=LEFT,end=LEFT+DAY,minute_blocks=lambda:iter([projected])),names)
    actual=tape.day(LEFT)
    assert len(actual)==1440 and actual[0][1]['BTCUSDT']['mark']==101 and actual[-1][0]==LEFT+DAY-MINUTE


def test_raw_rate_without_unit_authority_or_exact_mark_stays_blocked():
    assert funding_readiness(None,venue='BINANCE',product='USD_M_PERPETUAL')['rate_fraction'] is None
    event=dict(symbol='BTCUSDT',event_us=LEFT,raw_rate='.01')
    r=funding_readiness(event,venue='BINANCE',product='USD_M_PERPETUAL')
    assert r['rate_fraction'] is None and r['source_status']=='EXACT_FUNDING_BLOCKED'
    event=funding();r=funding_readiness(event,venue='SYNTHETIC',product='TEST_LINEAR')
    assert r['rate_fraction']=='0.0001' and r['wallet_status']=='NOT_RUN' and r['authority_body_verification_required']


@pytest.mark.parametrize('kind',['MINUTE_CLOSE','PREVIOUS_COMPLETED_MINUTE','TRADE_OPEN'])
def test_bar_price_is_never_exact_funding_charge_mark(kind):
    event=funding();event['charge_mark']['kind']=kind
    assert funding_readiness(event,venue='SYNTHETIC',product='TEST_LINEAR')['source_status']=='EXACT_FUNDING_BLOCKED'


def test_wrong_event_price_clock_and_conflicting_points_refused():
    event=funding();event['charge_mark']['event_us']-=1
    assert funding_readiness(event,venue='SYNTHETIC',product='TEST_LINEAR')['source_status']=='EXACT_FUNDING_BLOCKED'
    a,b=funding(),funding();b['charge_mark']['price']='101'
    with pytest.raises(ValueError,match='Conflicting'):unique_funding_events([a,b])
    assert len(unique_funding_events([a,a]))==1


def test_default_mmr_cannot_certify_historical_rule_or_close_fee():
    rule=dict(tiers=[dict(max_notional_USDT='100000',MMR='.005',MMD_USDT='0')])
    r=risk_rule_readiness(rule,symbol='BTCUSDT',event_us=LEFT,venue='SYNTHETIC',product='TEST_LINEAR')
    assert r['source_status']=='HISTORICAL_NATIVE_LIQUIDATION_BLOCKED'
    rule.update(version='SYNTHETIC',authority=bound(),symbol='BTCUSDT')
    r=risk_rule_readiness(rule,symbol='BTCUSDT',event_us=LEFT,venue='SYNTHETIC',product='TEST_LINEAR')
    assert r['historical_tiers']=='DECLARED_EFFECTIVE_RULE' and r['source_status']=='HISTORICAL_NATIVE_LIQUIDATION_BLOCKED'
    rule['authority']['effective_to_us']=LEFT
    assert risk_rule_readiness(rule,symbol='BTCUSDT',event_us=LEFT,venue='SYNTHETIC',product='TEST_LINEAR')['historical_tiers'].startswith('BLOCKED')


def test_other_asset_authority_cannot_certify_risk_or_funding():
    rule=dict(symbol='BTCUSDT',version='SYNTHETIC',authority=bound(),tiers=[dict(max_notional_USDT='100000',MMR='.005',MMD_USDT='0')])
    assert risk_rule_readiness(rule,symbol='DOGEUSDT',event_us=LEFT,venue='SYNTHETIC',product='TEST_LINEAR')['historical_tiers'].startswith('BLOCKED')
    event=funding();event['unit_authority']['symbol']='DOGEUSDT';event['charge_mark']['authority']['symbol']='DOGEUSDT'
    status=funding_readiness(event,venue='SYNTHETIC',product='TEST_LINEAR')
    assert status['raw_unit'].startswith('BLOCKED') and status['charge_mark'].startswith('BLOCKED')


def test_added_daily_rows_cannot_inherit_original_monthly_sha():
    r=row();r['ZIP_SHA256']='a'*64
    with pytest.raises(ValueError,match='composite'):source_bars(frame(),r,'markPriceKlines',added_repair_rows=1)


@pytest.mark.parametrize('tiers',[
    [dict(max_notional_USDT='100',MMR='.005',MMD_USDT='1000')],
    [dict(max_notional_USDT='100',MMR='.01',MMD_USDT='0'),dict(max_notional_USDT='200',MMR='.005',MMD_USDT='0')]
])
def test_negative_or_decreasing_tier_maintenance_refused(tiers):
    rule=dict(symbol='BTCUSDT',version='SYNTHETIC',authority=bound(),tiers=tiers,
        close_fee=dict(symbol='BTCUSDT',version='SYNTHETIC',reserve_formula='TEST_ONLY',release_rule='TEST_ONLY',authority=bound()))
    status=risk_rule_readiness(rule,symbol='BTCUSDT',event_us=LEFT,venue='SYNTHETIC',product='TEST_LINEAR')
    assert status['historical_tiers'].startswith('BLOCKED') and status['source_status']=='HISTORICAL_NATIVE_LIQUIDATION_BLOCKED'
