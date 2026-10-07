from copy import deepcopy
from decimal import Decimal as D
import pytest
from quant.bybit_isolated_account import BybitIsolatedAccount,liquidation_price,validated_tiers
from quant.perpetual_account import USDTLinearPerpetualAccount

MINUTE=60_000_000
def marks(account,t,btc='100',eth='100'):
    return account.update_marks(t,{s:dict(price=p,close_us=t,available_us=t) for s,p in zip(account.symbols,(btc,eth))})
def fill(a,s,side,q,t,signal=0,identity='entry'):
    return a.execute_fill(s,side,q,t,signal,identity,execution_mid_price='100',quote_available_us=t)

def test_public_price_formulas_and_bankruptcy_one_x():
    assert liquidation_price(100,2,1,0,'.005','.00055',0,'LONG')==0
    assert abs(liquidation_price(100,2,1,0,'.005','.00055',0,'SHORT')-D(200)/D('1.005'))<D('1e-24')
    with pytest.raises(ValueError):liquidation_price(100,0,1,0,'.005',0,0,'SHORT')

def test_isolated_short_takeover_preserves_wallet_other_position_and_allows_next_rebalance():
    a=BybitIsolatedAccount();marks(a,0)
    fill(a,'BTCUSDT','SELL','10',MINUTE+1,identity='short');fill(a,'ETHUSDT','BUY','5',MINUTE+2,identity='long')
    before_free=a.free_cash;other=deepcopy(a.positions['ETHUSDT']);entry=a.positions['BTCUSDT'].entry_price
    marks(a,2*MINUTE,btc='250')
    assert a.positions['BTCUSDT'].quantity==0 and a.positions['ETHUSDT']==other and a.free_cash==before_free
    assert a.status=='ACTIVE' and len(a.liquidations)==1
    assert D(a.liquidations[0]['bankruptcy_price'])==2*entry
    assert abs(a.summary()['accounting_bridge_error_USDT'])<1e-10
    blocked=fill(a,'BTCUSDT','SELL','1',2*MINUTE+1,identity='stale')
    assert blocked['reason']=='LIQUIDATED_WAIT_NEXT_NORMAL_REBALANCE'
    marks(a,3*MINUTE)
    fill(a,'BTCUSDT','SELL','1',5*MINUTE+1,signal=4*MINUTE,identity='new-day')
    assert a.positions['BTCUSDT'].quantity==-1 and a.reentries['BTCUSDT']==1

def test_funding_consumes_available_before_own_margin_and_preserves_pre_takeover_ownership():
    a=BybitIsolatedAccount();marks(a,0)
    fill(a,'BTCUSDT','SELL','10',MINUTE+1)
    fill(a,'ETHUSDT','BUY','5',MINUTE+2,identity='other')
    margin=a.positions['BTCUSDT'].isolated_balance
    available=a.free_cash;other=deepcopy(a.positions['ETHUSDT'])
    # Synthetic shock exercises the routing boundary, not an exchange rate-cap claim.
    owed=available+margin-D(4)
    receipt=a.apply_funding('BTCUSDT','pay',2*MINUTE,-owed/D(1000),2*MINUTE)
    assert receipt['quantity']==-10 and D(receipt['decimal_strings']['signed_funding_USDT'])==-owed
    assert a.positions['BTCUSDT'].quantity==0 and a.free_cash==0
    assert D(a.liquidations[0]['isolated_margin_lost'])==4 and a.positions['ETHUSDT']==other
    assert a.status=='BOUND_BREACH_REDUCTION_REQUIRED' # remaining position must respect smaller surviving wallet NAV
    assert abs(a.summary()['accounting_bridge_error_USDT'])<1e-10
    a.apply_funding('ETHUSDT','same-clock',2*MINUTE,'-.001',2*MINUTE)
    assert a.free_cash==D('.5')

def test_normal_nonliquidating_paths_match_legacy_and_snapshot_recovers_takeover():
    old=USDTLinearPerpetualAccount(closing_min_notional_exempt=True);new=BybitIsolatedAccount()
    for a in (old,new):
        marks(a,0);fill(a,'BTCUSDT','SELL','10',MINUTE+1);marks(a,2*MINUTE,btc='105')
        a.apply_funding('BTCUSDT','fund',2*MINUTE+1,'.0001',2*MINUTE+1)
    assert old.nav()==new.nav() and old.free_cash==new.free_cash and old.trades==new.trades and old.funding==new.funding
    marks(new,3*MINUTE,btc='250')
    saved=new.snapshot();restored=BybitIsolatedAccount.from_snapshot(saved)
    assert restored.snapshot()==saved and restored.nav()==new.nav()
    broken=deepcopy(saved);broken['trades'][-1]['decimal_strings']['fill_price']='1'
    with pytest.raises(ValueError,match='takeover'):BybitIsolatedAccount.from_snapshot(broken)

def test_laddered_partial_ioc_rescues_position_when_observed_capacity_exists():
    rows=[dict(riskLimitValue='400',maintenanceMargin='.005',initialMargin='.1',mmDeduction='0',maxLeverage='10',isLowestRisk=1),
          dict(riskLimitValue='10000',maintenanceMargin='.04',initialMargin='.1',mmDeduction='0',maxLeverage='10',isLowestRisk=0)]
    a=BybitIsolatedAccount(risk_tiers={s:rows for s in ('BTCUSDT','ETHUSDT')},risk_authority='SYNTHETIC_TEST_TIERS')
    marks(a,0);fill(a,'BTCUSDT','SELL','5',MINUTE+1)
    a.liquidation_ioc_capacity['BTCUSDT']=D(10);marks(a,2*MINUTE,btc='195')
    assert -5<a.positions['BTCUSDT'].quantity<0 and abs(a.positions['BTCUSDT'].quantity)*D(195)<=400
    assert not a.liquidations and a.trades[-1]['liquidation_partial_IOC'] and a.status=='ACTIVE'
    assert BybitIsolatedAccount.from_snapshot(a.snapshot()).nav()==a.nav()

def test_missing_ioc_capacity_goes_to_bankruptcy_not_an_invented_partial_fill():
    rows=[dict(riskLimitValue='400',maintenanceMargin='.005',initialMargin='.1',mmDeduction='0',maxLeverage='10',isLowestRisk=1),
          dict(riskLimitValue='10000',maintenanceMargin='.04',initialMargin='.1',mmDeduction='0',maxLeverage='10',isLowestRisk=0)]
    a=BybitIsolatedAccount(risk_tiers={s:rows for s in ('BTCUSDT','ETHUSDT')});marks(a,0);fill(a,'BTCUSDT','SELL','5',MINUTE+1)
    marks(a,2*MINUTE,btc='195')
    assert a.positions['BTCUSDT'].quantity==0 and len(a.liquidations)==1
    assert not any(r.get('liquidation_partial_IOC') for r in a.trades)

def test_uncertified_profile_never_claims_a_native_lowest_tier_snapshot():
    a=BybitIsolatedAccount();meta=a.contract_metadata()
    assert not meta['native_risk_tiers_available'] and not meta['native_liquidation_certified']
    with pytest.raises(ValueError):validated_tiers([dict(riskLimitValue='100',maintenanceMargin='.005',initialMargin='.1',mmDeduction='0',maxLeverage='10',isLowestRisk=0)])
