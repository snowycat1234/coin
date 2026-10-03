"""One new synthetic asset-contribution/snapshot case; no market or replay."""
import math
import numpy as np
import polars as pl
import pytest
from scripts.investment import public_exposure_attribution as attribution


def native_trade(symbol, side, gross, mid, execution_us):
    """Explicit fixture settlement, not a call to a production account engine."""
    fill = mid*(1.0008 if side == 'buy' else .9992)
    amount = gross*.001 if side == 'buy' else gross*fill*.001
    row = {key:0. for key in attribution.TRADE_COLUMNS}
    row.update(execution_us=int(execution_us),signal_us=int(execution_us)-attribution.MINUTE-1,
        capacity_open_us=int(execution_us)//attribution.MINUTE*attribution.MINUTE-attribution.MINUTE,
        symbol=symbol,side=side,fee_asset=symbol[:-4] if side == 'buy' else 'USDT',
        quantity=gross,gross_quantity=gross,mid_price=mid,fill_price=fill,notional=gross*fill,
        position_delta=gross*.999 if side == 'buy' else -gross,
        cash_delta=-gross*fill if side == 'buy' else gross*fill*(1-.001),
        fee_amount=amount,fee_USDT_mid=amount*mid if side == 'buy' else amount,
        fee=amount*mid if side == 'buy' else amount,execution_cost=gross*abs(fill-mid))
    return row


def typed_trades(rows):
    schema = {key:(pl.Int64 if key in ('execution_us','signal_us','capacity_open_us')
        else pl.String if key in ('symbol','side','fee_asset') else pl.Float64)
        for key in attribution.TRADE_COLUMNS}
    return pl.DataFrame(rows, schema=schema)


def test_saved_asset_contributions_and_snapshot_scope():
    # Six complete snapshots straddle UTC midnight; the longest active run
    # must not be reset at the day boundary or called an event holding time.
    midnight = attribution.timestamp('2024-01-02')
    stamps = midnight+np.arange(-1,5,dtype=np.int64)*attribution.MINUTE
    rows = [native_trade('BTCUSDT','buy',20/.999,100.,int(stamps[0]-attribution.MINUTE+1)),
        native_trade('ETHUSDT','buy',.02/.999,100.,int(stamps[0]-attribution.MINUTE+1)),
        native_trade('BTCUSDT','sell',10.,250.,int(stamps[4]-attribution.MINUTE+1))]
    trades = typed_trades(rows)
    initial = 10_000.
    bought_cash = initial+rows[0]['cash_delta']+rows[1]['cash_delta']
    cash = np.r_[np.full(4,bought_cash),np.full(2,bought_cash+rows[2]['cash_delta'])]
    btc_qty = np.r_[np.full(4,20.),np.full(2,10.)]
    eth_qty = np.full(6,.02)
    btc_marked = btc_qty*np.array([100.,250.,260.,100.,250.,220.]); eth_marked = eth_qty*100.
    nav = cash+btc_marked+eth_marked
    buy_fees = math.fsum(r['fee_USDT_mid'] for r in rows[:2])
    buy_execution = math.fsum(r['execution_cost'] for r in rows[:2])
    cumulative_fee = np.r_[np.full(4,buy_fees),np.full(2,buy_fees+rows[2]['fee_USDT_mid'])]
    cumulative_execution = np.r_[np.full(4,buy_execution),np.full(2,buy_execution+rows[2]['execution_cost'])]
    inventory = pl.DataFrame(dict(close_us=stamps,cash=cash,BTCUSDT_quantity=btc_qty,
        BTCUSDT_marked_notional=btc_marked,ETHUSDT_quantity=eth_qty,ETHUSDT_marked_notional=eth_marked,
        nav=nav,gross_marked_nav_same_quantities=nav+cumulative_fee+cumulative_execution,
        cumulative_fee=cumulative_fee,cumulative_execution_cost=cumulative_execution,
        gross_weight=(btc_marked+eth_marked)/nav))
    # Summary net is derived independently from actual cash movements plus
    # terminal inventory, not from the production attribution gross formula.
    net = math.fsum(r['cash_delta'] for r in rows)+2200.+2.
    fee = math.fsum(r['fee_USDT_mid'] for r in rows); execution = math.fsum(r['execution_cost'] for r in rows)
    summary = dict(initial_nav=initial,net_cash_PnL=net,gross_cash_PnL_same_quantities=net+fee+execution,
        fees=fee,execution_costs=execution,spread_cost=execution*.5,slippage_cost=execution*.5,
        terminal_marked_notional=2202.,open_positions=dict(BTCUSDT=10.,ETHUSDT=.02),trade_count=3)
    result = attribution.summarize_inventory_trades(inventory,trades,summary)
    btc,eth = (result['per_asset'][s] for s in attribution.SYMBOLS)
    expected_btc_net = math.fsum(r['cash_delta'] for r in rows if r['symbol']=='BTCUSDT')+2200.
    assert abs(btc['net_PnL_USDT']-expected_btc_net) <= 1e-7
    assert abs(eth['net_PnL_USDT']-(rows[1]['cash_delta']+2.)) <= 1e-7
    assert abs(btc['gross_PnL_USDT']-2700.) <= 1e-7 and abs(eth['gross_PnL_USDT']) <= 1e-7
    assert btc['terminal_quantity']==10. and btc['terminal_marked_notional_USDT']==2200.
    assert btc['buy_fills']==1 and btc['sell_fills']==1 and eth['buy_fills']==1 and eth['sell_fills']==0
    assert btc['buy_base_fee_asset']=='BTC' and btc['sell_quote_fee_asset']=='USDT'
    assert abs(btc['fee_USDT_mid']-(rows[0]['fee_USDT_mid']+rows[2]['fee_USDT_mid'])) <= 1e-7
    assert abs(result['totals']['net_PnL_USDT']-net) <= 1e-7
    assert all(abs(value) <= 1e-7 for value in result['summary_bridge_absolute_errors_USDT'].values())
    assert btc['above_target_weight_minutes']==2 and eth['above_target_weight_minutes']==0
    assert abs(btc['mean_marked_weight']-float(np.mean(btc_marked/nav))) <= 1e-12
    assert btc['max_marked_weight']>.3
    material = btc['material_activity']; longest = material['longest_streak']
    assert material['observed_minutes']==6 and material['fraction_full_window']==1.
    assert longest==dict(observed_minutes=6,minute_occupancy_seconds=360,snapshot_span_seconds=300,
        first_close_us=int(stamps[0]),last_close_us=int(stamps[-1]),right_censored=True,left_censored=True)
    assert eth['positive_activity']['observed_minutes']==6 and eth['material_activity']['observed_minutes']==0
    assert eth['positive_activity']['longest_streak']['observed_minutes']==6
    assert eth['material_activity']['longest_streak']['first_close_us'] is None
    assert not result['event_holding_duration_certified'] and not result['alpha_beta_identified']
    assert not result['new_account_NAV_generated']
    interrupted = attribution.activity(np.array([True,True,False,True,True,True]),stamps)
    assert interrupted['observed_minutes']==5 and interrupted['longest_streak']==dict(
        observed_minutes=3,minute_occupancy_seconds=180,snapshot_span_seconds=120,
        first_close_us=int(stamps[3]),last_close_us=int(stamps[5]),right_censored=True,left_censored=False)
    tied = attribution.activity(np.array([True,True,False,True,True,False]),stamps)
    assert tied['longest_streak']==dict(observed_minutes=2,minute_occupancy_seconds=120,snapshot_span_seconds=60,
        first_close_us=int(stamps[0]),last_close_us=int(stamps[1]),right_censored=False,left_censored=True)
    # Zero trades keep all 23 native columns. Cash remains a complete window;
    # no absent coin, imputed trade or division by a zero exposure is created.
    zeros = np.zeros(6); all_cash = inventory.with_columns(
        *[pl.Series(k,zeros) for k in ('BTCUSDT_quantity','BTCUSDT_marked_notional','ETHUSDT_quantity',
            'ETHUSDT_marked_notional','cumulative_fee','cumulative_execution_cost','gross_weight')],
        *[pl.Series(k,np.full(6,initial)) for k in ('cash','nav','gross_marked_nav_same_quantities')])
    cash_summary = dict(initial_nav=initial,net_cash_PnL=0.,gross_cash_PnL_same_quantities=0.,fees=0.,
        execution_costs=0.,spread_cost=0.,slippage_cost=0.,terminal_marked_notional=0.,
        open_positions=dict(BTCUSDT=0.,ETHUSDT=0.),trade_count=0)
    cash_result = attribution.summarize_inventory_trades(all_cash,typed_trades([]),cash_summary)
    assert all(value==0. for value in cash_result['totals'].values())
    assert all(c['positive_activity']['observed_minutes']==0 and c['material_activity']['observed_minutes']==0
        and c['positive_activity']['longest_streak']['snapshot_span_seconds']==0 for c in cash_result['per_asset'].values())
    # Reject a changed accepted summary rather than using its net as input or
    # widening the fixed monetary tolerance to fit inconsistent evidence.
    with pytest.raises(ValueError):
        attribution.summarize_inventory_trades(inventory,trades,{**summary,'net_cash_PnL':net+1e-4})
    with pytest.raises(ValueError):
        attribution.summarize_inventory_trades(inventory.drop('ETHUSDT_quantity'),trades,summary)
