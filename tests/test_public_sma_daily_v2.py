"""One new original SMA hook/daily state -> native fee/minute ledger case."""
from datetime import date
from pathlib import Path
import numpy as np
import polars as pl

from scripts.investment import public_sma_daily as sma
from scripts.investment import public_sma_daily_runner as runner
from scripts.investment import compare_simple_strategies as common


def daily_fixture(start):
    opens = start+np.arange(-200,4,dtype=np.int64)*common.DAY_US
    frames=[]
    for symbol,prices in zip(common.SYMBOLS,([101.,100.,99.,98.,777.],[100.,101.,99.,98.,777.]),strict=True):
        close=np.full(len(opens),100.);close[199:]=prices
        factor=1. if symbol=='BTCUSDT' else .5
        frames.append(pl.DataFrame(dict(symbol=[symbol]*len(opens),interval=['1d']*len(opens),
            open_us=opens,close_us=opens+common.DAY_US,available_us=opens+common.DAY_US,
            open=close*factor,high=(close+.1)*factor,low=(close-.1)*factor,close=close*factor,
            volume=np.full(len(opens),1000.))))
    return pl.concat(frames).sort(['open_us','symbol'])


def minute_fixture(start,end):
    times=np.arange(start-31*common.DAY_US,end,common.MINUTE_US,dtype=np.int64)
    frames=[]
    for symbol,values in zip(common.SYMBOLS,([101.,100.,99.,98.],[100.,101.,99.,98.]),strict=True):
        prices=np.full(len(times),100.)
        for day,value in enumerate(values):
            prices[(times>=start+day*common.DAY_US)&(times<start+(day+1)*common.DAY_US)]=value
        factor=1. if symbol=='BTCUSDT' else .5
        frames.append(pl.DataFrame(dict(symbol=[symbol]*len(times),open_us=times,
            close_us=times+common.MINUTE_US,available_us=times+common.MINUTE_US,
            open=prices*factor,high=(prices+.1)*factor,low=(prices-.1)*factor,close=prices*factor,
            quote_volume=np.full(len(times),100_000_000.),valid_day=np.ones(len(times),dtype=bool),
            minute_valid=np.ones(len(times),dtype=bool),missing_reason=[None]*len(times))))
    return pl.concat(frames).sort(['open_us','symbol'])


def test_sma_daily_native_route(tmp_path):
    start=common.day_us(date(2024,1,1));end=start+4*common.DAY_US
    calendar=np.arange(start,end,common.MINUTE_US,dtype=np.int64)
    bars=daily_fixture(start);plan=sma.fixed_targets(bars,calendar)
    assert plan.strategy_id==sma.STRATEGY_ID and plan.receipt['paired_comparison_allowed']
    assert plan.receipt['original_public_hook_reused'] and plan.receipt['model_fits']==0
    assert not plan.receipt['original_short_and_whole_balance_sizing_transplanted']
    assert not plan.receipt['daily_prices_used_for_execution_or_risk']
    assert plan.targets['available_us'].min()==start
    for symbol,expected in zip(common.SYMBOLS,([.3,.3,.3,0.],[0.,.3,.3,0.]),strict=True):
        weights=plan.calendar_ledger.filter(pl.col('symbol')==symbol)['target_weight']
        assert [weights[day*1440] for day in range(4)]==expected
        assert weights[-1]==0.
    # Read the original class hooks on each fresh current day. Polars values
    # must agree with scalar last50/200, including held/flat exact equality.
    cls=sma._load_public_hooks()
    for symbol in common.SYMBOLS:
        held=False;rules=cls()
        for day in range(4):
            rows=bars.filter((pl.col('symbol')==symbol)&(pl.col('close_us')<=start+day*common.DAY_US)).sort('close_us').tail(201)
            rules.candles=np.column_stack((rows['close_us'].to_numpy()//1000,rows['open'].to_numpy(),
                rows['close'].to_numpy(),rows['high'].to_numpy(),rows['low'].to_numpy(),rows['volume'].to_numpy()))
            fast=float(np.mean(rules.candles[-50:,2]));slow=float(np.mean(rules.candles[-200:,2]))
            assert abs(rules.fast_sma-fast)<=1e-12 and abs(rules.slow_sma-slow)<=1e-12
            assert rules.should_long()==bool(fast>slow) and rules.should_short()==bool(fast<slow)
            rules.is_long=held;rules.is_short=False;exited=[False]
            rules.liquidate=lambda:exited.__setitem__(0,True)
            rules.update_position()
            assert exited[0]==bool(held and fast<slow)
            if held and exited[0]:held=False
            elif not held and fast>slow:held=True
            if day==2:assert fast==slow and held  # equal held: do not exit
            if symbol=='ETHUSDT' and day==0:assert fast==slow and not held
    # Above-slow entry is permitted even when the relation already existed
    # before scoring: original rule is a comparison, not a same-day cross.
    prior_breakout=bars.filter(pl.col('open_us')==start-200*common.DAY_US).with_columns(
        pl.lit(start-201*common.DAY_US).cast(pl.Int64).alias('open_us'),
        pl.lit(start-200*common.DAY_US).cast(pl.Int64).alias('close_us'),
        pl.lit(start-200*common.DAY_US).cast(pl.Int64).alias('available_us'))
    established=pl.concat([prior_breakout,bars]).with_columns([
        pl.when(pl.col('open_us').is_between(start-51*common.DAY_US,start-common.DAY_US,closed='both'))
        .then(pl.lit(value)*pl.when(pl.col('symbol')=='BTCUSDT').then(1.).otherwise(.5))
        .otherwise(pl.col(field)).alias(field)
        for field,value in (('open',101.),('close',101.),('high',101.1),('low',100.9))])
    assert sma.fixed_targets(established,calendar).calendar_ledger['target_weight'][0]==.3
    future=bars.with_columns([pl.when(pl.col('open_us')>=start+2*common.DAY_US)
        .then(pl.col(field)*10).otherwise(pl.col(field)).alias(field) for field in ('open','high','low','close')])
    prefix=pl.col('decision_us')<start+3*common.DAY_US
    assert sma.fixed_targets(future,calendar).calendar_ledger.filter(prefix).equals(plan.calendar_ledger.filter(prefix))
    terminal=bars.with_columns([pl.when(pl.col('close_us')==end).then(pl.col(field)*20)
        .otherwise(pl.col(field)).alias(field) for field in ('open','high','low','close')])
    assert sma.fixed_targets(terminal,calendar).targets.equals(plan.targets)
    missing=bars.filter(pl.col('open_us')!=start-2*common.DAY_US)
    assert not sma.fixed_targets(missing,calendar).receipt['paired_comparison_allowed']
    late=bars.with_columns(pl.when(pl.col('close_us')==start+common.DAY_US)
        .then(pl.col('available_us')+common.MINUTE_US).otherwise(pl.col('available_us')).alias('available_us'))
    late_plan=sma.fixed_targets(late,calendar)
    assert not late_plan.receipt['paired_comparison_allowed']
    assert late_plan.calendar_ledger.filter(pl.col('decision_us')<start+common.DAY_US).equals(
        plan.calendar_ledger.filter(pl.col('decision_us')<start+common.DAY_US))
    assert not sma.fixed_targets(bars.filter(pl.col('open_us')>start-200*common.DAY_US),calendar).receipt['paired_comparison_allowed']
    # Same accepted private native path: old financial/date/fee functions, with
    # daily target changes only. Reconstruct settlement once, no old green suite.
    minutes=minute_fixture(start,end);derivation=[]
    account=runner.native_namespace(date(2023,12,1),date(2024,1,5),derivation)
    assert all(row['original_AST_sha256']==row['derived_AST_sha256'] for row in derivation)
    config=common.comparison_config(start,end,8)
    result=account.run_backtest(minutes.select('symbol','close_us','available_us'),minutes,plan.targets,config)
    ledger=common.write_ledger(tmp_path/'sma-native-ledger',result,minutes)
    trades=result.trades.sort('execution_us',maintain_order=True).to_dicts()
    assert all(any(row['side']=='buy' and row['symbol']==symbol for row in trades) for symbol in common.SYMBOLS)
    assert any(row['side']=='sell' for row in trades)
    cash=config.initial_cash;quantities=dict.fromkeys(common.SYMBOLS,0.);fees=execution=0.
    entry=dict(BTCUSDT=start,ETHUSDT=start+common.DAY_US)
    first_buy_seen=set()
    # Independent fixture state: another sleeve's entry may legally rebalance
    # an already held sleeve. All buys must still use a fixed held UTC day.
    allowed_buy_signal_days={
        'BTCUSDT':{start,start+common.DAY_US,start+2*common.DAY_US},
        'ETHUSDT':{start+common.DAY_US,start+2*common.DAY_US}}
    for row in trades:
        q,fill,mid=(row[key] for key in ('quantity','fill_price','mid_price'))
        assert row['execution_us']>=row['signal_us']+common.MINUTE_US+1
        if row['side']=='buy':
            assert start<=row['signal_us']<end
            assert row['signal_us'] in allowed_buy_signal_days[row['symbol']]
            assert row['execution_us']<start+3*common.DAY_US  # no buy after the fixed flat day
            if row['symbol'] not in first_buy_seen:
                assert row['signal_us']==entry[row['symbol']]
                first_buy_seen.add(row['symbol'])
            else:
                assert quantities[row['symbol']]>0  # subsequent buy only rebalances an existing holding
            cash-=q*fill;quantities[row['symbol']]+=q*.999;fees+=q*.001*mid
            assert row['fee_asset']==row['symbol'][:-4] and row['position_delta']<q
        else:
            assert q<=quantities[row['symbol']]+1e-10
            quantities[row['symbol']]-=q;cash+=q*fill*.999;fees+=q*fill*.001
            assert row['fee_asset']=='USDT'
        execution+=q*abs(fill-mid)
        assert abs(cash-row['cash_after'])<=1e-7
    inventory=pl.read_parquet(Path(ledger['directory'])/'minute_nav_inventory.parquet')
    final=cash+sum(quantities[symbol]*minutes.filter(pl.col('symbol')==symbol)['close'][-1] for symbol in common.SYMBOLS)
    assert abs(inventory['nav'][-1]-final)<=1e-7
    assert abs(ledger['summary']['fees']-fees)<=1e-7 and abs(ledger['summary']['execution_costs']-execution)<=1e-7
    assert ledger['summary']['same_quantity_gross_minus_cost_equals_net']
    assert not ledger['summary']['candidate_qualification_allowed']
