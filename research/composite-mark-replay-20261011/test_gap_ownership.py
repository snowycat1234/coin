"""Missing future mark cannot release an already-owned synthetic position."""
from test_composite import fixture,LEFT,RIGHT,MINUTE
from composite_bars import composite_bars,minute_observation
from quant.perpetual_account import USDTLinearPerpetualAccount,D


def test_gap_keeps_existing_position_and_never_reports_paid_flat_or_nav():
    reader,month,_,decode=fixture();bars,_=composite_bars(reader,month,LEFT,RIGHT,decode=decode)
    at=LEFT*1000
    account=USDTLinearPerpetualAccount(symbols=('BTCUSDT',))
    account.update_marks(at,{'BTCUSDT':dict(price=D(100),close_us=at-MINUTE,available_us=at)})
    receipt=account.execute_fill('BTCUSDT','BUY',D(1),at+1,at-MINUTE,'FIXTURE_ENTRY',
        execution_mid_price=D(100),quote_available_us=at,available_quantity=D(10))
    assert receipt['status']=='FILLED' and account.positions['BTCUSDT'].quantity==1
    before=account.summary();gap=at+9*MINUTE
    assert minute_observation(bars,gap,gap)['status']=='NOT_YET_KNOWN'
    result=minute_observation(bars,gap,gap+MINUTE)
    assert not result['path_certifiable'] and result['price'] is None
    assert account.positions['BTCUSDT'].quantity==1 and account.summary()==before
    assert 'NAV' not in result and 'terminal_cash_realized' not in result
