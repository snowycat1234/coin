from rules import quantity_gate
from quant.perpetual_account import USDTLinearPerpetualAccount,D
def test_unknown_and_offgrid_reduce_only_cannot_be_native_ready():
    assert not quantity_gate('.00176847',None)['tradable']
    p=dict(minQty='.001',stepSize='.001',maxQty='1000');x=quantity_gate('.00176847',p);assert not x['tradable'] and 'OFF_QUANTITY_GRID' in x['errors'] and x['no_roundup']
    assert not quantity_gate('.0001',p)['tradable'] and quantity_gate('.002',p)['tradable']
def test_existing_exemption_keeps_paid_capacity_opening_floor_and_no_flip():
    a=USDTLinearPerpetualAccount(symbols=('ETHUSDT',));a.update_marks(0,dict(ETHUSDT=dict(price='2000',close_us=0,available_us=0)))
    a.execute_fill('ETHUSDT','SELL','.01',60000001,0,'open',execution_mid_price='2000',quote_available_us=60000000,available_quantity='.01')
    a.update_marks(120000000,dict(ETHUSDT=dict(price='2000',close_us=120000000,available_us=120000000)))
    a.execute_fill('ETHUSDT','BUY','.009',120000001,60000000,'shrink',execution_mid_price='2000',quote_available_us=120000000,available_quantity='.009',reduce_only=True);assert a.positions['ETHUSDT'].quantity==D('-.001')
    a.closing_min_notional_exempt=True
    a.update_marks(180000000,dict(ETHUSDT=dict(price='2000',close_us=180000000,available_us=180000000)))
    before=a.fees;r=a.execute_fill('ETHUSDT','BUY','.002',180000001,120000000,'smallpaid',execution_mid_price='2000',quote_available_us=180000000,available_quantity='.0004',reduce_only=True)
    assert r['status']=='PARTIAL' and a.positions['ETHUSDT'].quantity==D('-.0006') and a.fees>before and all(t['leg']=='CLOSE' for t in r['fills'])
    restored=USDTLinearPerpetualAccount.from_snapshot(a.snapshot());assert restored.snapshot()==a.snapshot()
    restored.update_marks(240000000,dict(ETHUSDT=dict(price='2000',close_us=240000000,available_us=240000000)))
    rejected=restored.execute_fill('ETHUSDT','BUY','.0001',240000001,180000000,'smallopen',execution_mid_price='2000',quote_available_us=240000000,available_quantity='.0001',reduce_only=False)
    # Existing position makes this a reduction; a fresh flat account testsopening.
    flat=USDTLinearPerpetualAccount(symbols=('ETHUSDT',),closing_min_notional_exempt=True);flat.update_marks(0,dict(ETHUSDT=dict(price='2000',close_us=0,available_us=0)))
    z=flat.execute_fill('ETHUSDT','BUY','.001',60000001,0,'underopen',execution_mid_price='2000',quote_available_us=60000000,available_quantity='.001');assert z['fills']==[] and flat.positions['ETHUSDT'].quantity==0
