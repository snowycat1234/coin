"""Synthetic cash/inventory conservation through the actual new research entry."""
import hashlib

import numpy as np
import polars as pl
import pytest
from quant import backtest as legacy
from scripts.investment import bybit_spot_adapter as native


def history(prices=(('BTCUSDT',10000.),('ETHUSDT',1000.)), *, quote=1e10):
    start=1754006400000000
    times=np.arange(start-legacy.MINUTE_US,start+18*legacy.MINUTE_US,legacy.MINUTE_US,dtype=np.int64)
    minutes=pl.concat([pl.DataFrame(dict(symbol=[symbol]*len(times),open_us=times,
        close_us=times+legacy.MINUTE_US,available_us=times+legacy.MINUTE_US,
        open=np.full(len(times),price),close=np.full(len(times),price),quote_volume=np.full(len(times),quote)))
        for symbol,price in prices])
    targets=pl.DataFrame([{'symbol':symbol,'available_us':start,'target_weight':.3} for symbol,_ in prices],
        schema={'symbol':pl.String,'available_us':pl.Int64,'target_weight':pl.Float64})
    return minutes.select('symbol','available_us','close_us'),minutes,targets,start,start+18*legacy.MINUTE_US


def audit(result, prices):
    cash=shadowcash=result.config.initial_cash;positions={symbol:0. for symbol in prices};fees=execution=0.
    for row in result.trades.iter_rows(named=True):
        q=row['quantity'];assert q==row['gross_quantity'] and q>0
        side,symbol=row['side'],row['symbol'];r=result.config.fee_rate
        if side=='buy':
            assert row['fee_asset']==native.BASE[symbol]
            assert row['fee_amount']==pytest.approx(q*r)
            assert row['position_delta']==pytest.approx(q*(1-r))
            assert row['cash_delta']==pytest.approx(-q*row['fill_price'])
            assert row['fee_USDT_mid']==pytest.approx(q*r*row['mid_price'])
        else:
            assert q<=positions[symbol]  # actual received inventory, never gross buys
            assert row['fee_asset']=='USDT'
            assert row['position_delta']==-q
            assert row['cash_delta']==pytest.approx(q*row['fill_price']*(1-r))
            assert row['fee_amount']==pytest.approx(q*row['fill_price']*r)
            assert row['fee_USDT_mid']==row['fee_amount']
        assert row['fee']==row['fee_USDT_mid']
        assert row['notional']==pytest.approx(q*row['fill_price'])
        assert row['execution_cost']==pytest.approx(q*abs(row['fill_price']-row['mid_price']))
        assert row['execution_us']>=result.config.eligible_us(row['signal_us'])+1
        assert row['capacity_open_us']==row['execution_us']//legacy.MINUTE_US*legacy.MINUTE_US-legacy.MINUTE_US
        assert row['notional']<=row['capacity']+1e-8
        step=result.config.lot_step_by_symbol[symbol]
        assert q/step==pytest.approx(round(q/step),abs=1e-7)
        cash+=row['cash_delta'];positions[symbol]+=row['position_delta'];shadowcash-=row['position_delta']*row['mid_price']
        fees+=row['fee_USDT_mid'];execution+=row['execution_cost']
        net=cash+sum(positions[s]*prices[s] for s in prices)
        shadow=shadowcash+sum(positions[s]*prices[s] for s in prices)
        assert cash>=0 and positions[symbol]>=0
        assert cash==pytest.approx(row['cash_after'],abs=1e-8)
        assert net==pytest.approx(row['nav_after'],abs=1e-8)
        assert shadow-net==pytest.approx(fees+execution,abs=1e-8)
        if side=='buy':
            assert max(positions[s]*prices[s]/net for s in prices)<=result.config.max_weight+1e-9
            assert sum(positions[s]*prices[s] for s in prices)/net<=result.config.max_gross+1e-9
    assert result.summary['open_positions']==pytest.approx(positions)
    assert result.summary['final_nav']==pytest.approx(cash+sum(positions[s]*prices[s] for s in prices))
    assert result.summary['fees']==pytest.approx(fees)
    assert result.summary['execution_costs']==pytest.approx(execution)
    assert result.summary['gross_pnl_before_costs']==pytest.approx(shadowcash+sum(positions[s]*prices[s] for s in prices)-result.config.initial_cash)
    assert result.daily_nav['fees'].sum()==pytest.approx(fees)
    assert result.orders.filter(pl.col('filled_notional')==0)['quantity'].sum()==0
    assert result.orders['quantity'].sum()==pytest.approx(result.trades['quantity'].sum())
    return positions


@pytest.mark.parametrize('spread',[2,4,8])
def test_received_asset_cash_net_quantity_caps_and_fees_once(spread):
    bars,minutes,targets,start,end=history()
    # Add a flat exit early enough for repeated capacity/lot attempts.
    targets=pl.concat([targets,targets.with_columns(pl.lit(start+8*legacy.MINUTE_US,dtype=pl.Int64).alias('available_us'),
        pl.lit(0.,dtype=pl.Float64).alias('target_weight'))])
    config=legacy.BacktestConfig(start_us=start,end_us=end,target_annual_vol=None,
        half_spread_bps=spread/2,liquidate_at_end=True)
    original_namespace={name:id(value) for name,value in vars(legacy).items()}
    result=native.run_backtest(bars,minutes,targets,config)
    assert result.trades.filter(pl.col('side')=='buy').height>=2
    assert result.trades.filter(pl.col('side')=='sell').height>=2
    positions=audit(result,{'BTCUSDT':10000.,'ETHUSDT':1000.})
    assert all(0<=positions[s]<config.lot_step_by_symbol[s] for s in positions)
    assert result.summary['fee_settlement_version']==native.VERSION
    assert not result.summary['native_bybit_market_execution_proven']
    assert {name:id(value) for name,value in vars(legacy).items()}==original_namespace


def test_partial_capacity_and_real_positive_sublot_terminal_dust():
    bars,minutes,targets,start,end=history(quote=100000.)
    partial=native.run_backtest(bars,minutes,targets,legacy.BacktestConfig(start_us=start,end_us=end,
        target_annual_vol=None,liquidate_at_end=True))
    assert partial.orders.filter(pl.col('status')=='partial').height>0
    audit(partial,{'BTCUSDT':10000.,'ETHUSDT':1000.})
    bars,minutes,targets,start,end=history((('BTCUSDT',2997.),))
    closed=native.run_backtest(bars,minutes,targets,legacy.BacktestConfig(start_us=start,end_us=end,
        target_annual_vol=None,half_spread_bps=0,slippage_bps=0,liquidate_at_end=True,
        lot_step_by_symbol={'BTCUSDT':.001}))
    audit(closed,{'BTCUSDT':2997.})
    assert closed.summary['round_trip_count']==1
    assert closed.round_trips['pnl'].sum()==pytest.approx(closed.summary['final_nav']-10000.)
    bars,minutes,targets,start,end=history((('BTCUSDT',300000000.),))
    dust=native.run_backtest(bars,minutes,targets,legacy.BacktestConfig(start_us=start,end_us=end,
        target_annual_vol=None,half_spread_bps=0,slippage_bps=0,liquidate_at_end=True,
        lot_step_by_symbol={'BTCUSDT':1e-8}))
    positions=audit(dust,{'BTCUSDT':300000000.})
    assert 0<positions['BTCUSDT']<1e-10  # old absolute threshold must not erase it
    assert dust.summary['round_trip_count']==0
    assert dust.summary['final_nav']>dust.daily_nav['cash'][-1]


def test_exact_source_ast_export_no_perpetual_or_locked_substitution(monkeypatch,tmp_path):
    exported=native.export_derivation(tmp_path/'derivation')
    assert all(change['matches']==1 for change in exported['allowed_ast_changes'])
    assert len(exported['allowed_ast_changes'])==16
    assert hashlib.sha256(open(exported['derived_source_path'],'rb').read()).hexdigest()==exported['derived_source_file_sha256']
    bars,minutes,targets,start,end=history()
    with pytest.raises(ValueError,match='Non-VIP10bp'):
        native.run_backtest(bars,minutes,targets,legacy.BacktestConfig(fee_bps=5.5))
    moved=minutes.with_columns((pl.col('open_us')+native.END_US-start).alias('open_us'))
    with pytest.raises(ValueError,match='locked input'):
        native.run_backtest(bars,moved,targets)
    true_sha=native.file_sha
    monkeypatch.setattr(native,'file_sha',lambda path:'0'*64 if str(path).endswith('src/quant/backtest.py') else true_sha(path))
    with pytest.raises(ValueError,match='dependency changed'):
        native.derivation_receipt()
