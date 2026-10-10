"""Pure financial formulas and synthetic saved receipts; no wallet instances."""
import inspect,json,sys
from decimal import Decimal as D,localcontext
from pathlib import Path
import numpy as np
import polars as pl
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'research/recover-frozen-runner-20261009'))
import native_margin_risk_summary as risk


@pytest.mark.parametrize('q,collateral,mark,leverage',[('2','100','60','2'),('-2','100','140','2'),('2','115','70','2'),('-2','115','140','2'),('2','200','10','1'),('-2','200','200','1')])
def test_source_formula_and_array_scan_agree(q,collateral,mark,leverage):
    r=risk.scalar_risk(q,100,collateral,mark,leverage=leverage)
    v=risk.vector_risk(np.array([float(q)]),np.array([100.]),np.array([float(collateral)]),np.array([float(mark)]),float(leverage),.00055,np.array([.005]),np.array([0.]))
    for field in ('margin_headroom','normalized_margin_headroom','engine_trigger_headroom','liquidation_price','adverse_price_distance'):
        if r[field] is None:assert np.isnan(v[field][0])
        else:assert float(r[field])==pytest.approx(v[field][0],abs=1e-12)
    with localcontext() as ctx:
        ctx.prec=40;q=D(q);extra=D(collateral)-abs(q)*100/D(leverage);side=1 if q>0 else -1
        expected=D(r['margin_headroom'])+side*extra*D('.00055')/(1-side*D('.00055'))
        assert abs(D(r['engine_trigger_headroom'])-expected)<D('1e-35')


def test_flat_and_fully_collateralized_long_have_no_positive_price_trigger():
    flat=risk.scalar_risk(0,0,0,100)
    assert flat['side']=='FLAT' and flat['liquidation_price'] is None and flat['margin_headroom'] is None and not flat['threshold_crossed']
    long=risk.scalar_risk(2,100,200,1)
    assert D(long['liquidation_price'])==0 and not long['positive_price_trigger'] and long['adverse_price_distance'] is None
    with pytest.raises(ValueError):risk.scalar_risk(0,100,200,100)


def test_exact_price_override_avoids_float64_one_x_long_cancellation():
    exact=risk.scalar_risk('.3','.1','.03','.2')
    assert D(exact['liquidation_price'])==0
    r=risk.vector_risk(np.array([.3]),np.array([.1]),np.array([.03]),np.array([.2]),1.,.00055,np.array([.005]),np.array([0.]),price_override=np.array([float(exact['liquidation_price'])]))
    assert r['liquidation_price'][0]==0 and np.isnan(r['adverse_price_distance'][0])


@pytest.mark.parametrize('side',[1,-1])
def test_size_and_collateral_scaling_preserves_price_threshold(side):
    full=risk.scalar_risk(side*10,100,1000,150)
    small=risk.scalar_risk(side,100,100,150)
    assert full['liquidation_price']==small['liquidation_price']
    assert full['adverse_price_distance']==small['adverse_price_distance']
    assert D(full['margin_headroom'])==10*D(small['margin_headroom'])
    assert 'free_cash' not in inspect.signature(risk.scalar_risk).parameters


@pytest.mark.parametrize('arm',['Static50','Cash50'])
def test_verified_xrp_takeover_and_model_headroom(arm):
    evidence=json.loads((risk.HERE/'q4-native92/xrp-liquidation-explanation/EVIDENCE.json').read_bytes())
    event=next(e for e in evidence['events'] if e['arm']==arm)
    for b,expected_crossed in ((event['before'],True),(event['selected_model_same_observable_time']['metrics'],False)):
        r=risk.scalar_risk(b['quantity'],b['entry_price_USDT_per_XRP'],b['isolated_collateral_USDT'],b['mark_price_USDT_per_XRP'])
        assert r['threshold_crossed']==expected_crossed
        for actual,expected in [('liquidation_price','liquidation_threshold_USDT_per_XRP'),('isolated_equity','isolated_equity_USDT'),('maintenance','maintenance_USDT'),('margin_headroom','equity_minus_maintenance_USDT')]:
            assert abs(D(r[actual])-D(b[expected]))<D('1e-35')
        assert (D(r['adverse_price_distance'])<=0)==expected_crossed


def saved_fixture(directory,*,deplete=False):
    """Hand-written receipt fixture including a mark takeover before its flat row."""
    minute=risk.MINUTE;symbol='XRPUSDT';initial=300 if deplete else 10000
    tier=dict(riskLimitValue=None,maintenanceMargin='.005',mmDeduction='0',initialMargin='1',maxLeverage='1',isLowestRisk=1)
    contract=dict(version='bybit_style_isolated_bankruptcy_takeover_v1',margin_mode='ISOLATED',market_type='LINEAR_USDT_PERPETUAL',quantity_asset='BASE',contract_multiplier=1,leverage=1,taker_fee_bps_per_side=5.5,historical_risk_tiers_certified=False,instrument_profiles={symbol:dict(quantity_asset='BASE',contract_multiplier='1')},risk_tiers={symbol:[tier]})
    trades=[]
    def trade(t,q0,q1,e0,e1,collateral_delta,cash_delta,mark,actual=False):
        x={k:str(v) for k,v in dict(quantity_before=q0,quantity_after=q1,position_delta=q1-q0,entry_price_before=e0,entry_price_after=e1,isolated_balance_delta=collateral_delta,free_cash_delta=cash_delta,mark_price=mark).items()}
        trades.append(dict(symbol=symbol,event_us=t,decimal_strings=x,fill_id='LIQ' if actual else str(len(trades)),liquidation_takeover=actual))
    trade(minute+1,0,-2,0,100,200,-200,100)
    lost=199 if deplete else 100
    if not deplete:trade(3*minute+1,-2,-1,100,100,-100,50,180)
    trade(4*minute,-2 if deplete else -1,0,100,0,-lost,0,200,True)
    if not deplete:
        trade(4*minute+1,0,1,0,200,200,-200,200)
        trade(6*minute+1,1,0,200,0,-200,210,210)
    funding=[dict(symbol=symbol,event_us=2*minute+1,mark_close_us=2*minute,quantity=-2,mark_price=150,signed_funding_USDT=-101 if deplete else -1,decimal_strings=dict(mark_price='150',signed_funding_USDT='-101' if deplete else '-1'))]
    liqs=[dict(id='LIQ',symbol=symbol,event_us=4*minute,phase='MARK_OBSERVATION',quantity='-2' if deplete else '-1',entry_price='100',mark_price='200',isolated_margin_lost=str(lost),tier=tier)]
    rows=[]
    if deplete:states=[(0,0,0,100,initial),(-2,100,200,150,100),(-2,100,199,180,0),(0,0,0,200,0)]
    else:states=[(0,0,0,100,initial),(-2,100,200,150,9800),(-2,100,200,180,9799),(0,0,0,200,9849),(1,200,200,205,9649),(1,200,200,210,9649),(0,0,0,210,9859)]
    for i,(q,e,c,p,free) in enumerate(states):rows.append(dict(close_us=(i+1)*minute,free_cash=float(free),**{symbol+'_quantity':float(q),symbol+'_signed_marked_notional':float(q*p),symbol+'_isolated_balance':float(c),symbol+'_isolated_equity':float(c+q*(p-e))}))
    summary=dict(contract=contract,symbols=[symbol],completed_minutes=len(rows),liquidation_count=1,liquidation_loss_USDT=lost,net_PnL=states[-1][-1]-initial)
    for name,value in [('summary',summary),('trades',trades),('funding',funding),('liquidations',liqs)]: (directory/(name+'.json')).write_text(json.dumps(value))
    pl.DataFrame(rows).write_parquet(directory/'minute_nav_inventory.parquet')


def test_actual_lifetimes_include_pre_takeover_and_keep_free_cash_separate(tmp_path):
    saved_fixture(tmp_path);r=risk.summarize(tmp_path,'fixture',near_distance=.2)
    assert r['actual_liquidations']==1 and len(r['lifetimes'])==2
    short,long=r['lifetimes'];assert short['closing_cause']=='LIQUIDATION' and long['closing_cause']=='NORMAL_PAID_CLOSE'
    assert short['start_us']==risk.MINUTE+1 and short['end_us']==4*risk.MINUTE and short['minute_observations']==2
    w=short['minimum_margin_headroom']['witness'];assert w['phase']=='ACTUAL_LIQUIDATION_BEFORE_TAKEOVER'
    assert D(w['metrics']['isolated_collateral'])==100 and D(w['account_free_cash'])==9849 and D(w['metrics']['margin_headroom'])==-1
    assert short['crossed_event_observations']==1 and short['crossed_minute_observations']==0
    assert short['near_minute_observations']==1 and short['near_event_observations']==2
    assert short['near_minute_intervals']==[dict(first_us=3*risk.MINUTE,last_us=3*risk.MINUTE,observations=1,minimum_adverse_distance=short['near_minute_intervals'][0]['minimum_adverse_distance'])]
    assert long['minimum_adverse_price_distance'] is None and r['original_net_PnL_USDT']==-141
    assert r['reconciliation']['all_input_hashes_unchanged']


def test_funding_debit_exhausts_free_cash_then_only_own_collateral(tmp_path):
    saved_fixture(tmp_path,deplete=True);r=risk.summarize(tmp_path,'debit')
    assert r['funding_debits_consuming_isolated_collateral']==1 and D(r['account_free_cash']['minimum_event_USDT'])==0
    w=r['lifetimes'][0]['actual_liquidation_witnesses'][0]['risk']
    assert D(w['metrics']['isolated_collateral'])==199 and D(w['account_free_cash'])==0
    assert D(w['metrics']['margin_headroom'])==-3 and r['original_net_PnL_USDT']==-300


def test_reject_incomplete_or_changed_saved_position(tmp_path):
    saved_fixture(tmp_path);p=tmp_path/'minute_nav_inventory.parquet';df=pl.read_parquet(p)
    df.with_columns((pl.col('XRPUSDT_quantity')+.01).alias('XRPUSDT_quantity')).write_parquet(p)
    with pytest.raises(ValueError):risk.summarize(tmp_path,'changed')
