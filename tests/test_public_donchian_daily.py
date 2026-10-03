"""One new daily boundary/hook -> same native-fee/minute-ledger case."""
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from scripts.investment import public_donchian_daily as daily
from scripts.investment import public_donchian_daily_runner as runner
from scripts.investment import compare_simple_strategies as common
from scripts.investment import bybit_spot_adapter as native


def daily_fixture(start):
    opens = start + np.arange(-200,3,dtype=np.int64)*common.DAY_US
    close = np.full(len(opens),100.)
    close[199:] = [103.,104.,90.,999.]
    return pl.concat([pl.DataFrame(dict(symbol=[symbol]*len(opens),interval=['1d']*len(opens),
        open_us=opens,close_us=opens+common.DAY_US,available_us=opens+common.DAY_US,
        open=close*factor,high=(close+.1)*factor,low=(close-.1)*factor,close=close*factor,
        volume=np.full(len(opens),1000.)))
        for symbol,factor in zip(common.SYMBOLS,(1.,.5),strict=True)]).sort(['open_us','symbol'])


def minute_fixture(start,end):
    times = np.arange(start-31*common.DAY_US,end,common.MINUTE_US,dtype=np.int64)
    price = np.full(len(times),100.)
    price[(times>=start-common.DAY_US)&(times<start+common.DAY_US)] = 103.
    price[(times>=start+common.DAY_US)&(times<start+2*common.DAY_US)] = 104.
    price[times>=start+2*common.DAY_US] = 90.
    return pl.concat([pl.DataFrame(dict(symbol=[symbol]*len(times),open_us=times,
        close_us=times+common.MINUTE_US,available_us=times+common.MINUTE_US,
        open=price*factor,high=(price+.1)*factor,low=(price-.1)*factor,close=price*factor,
        quote_volume=np.full(len(times),100_000_000.),valid_day=np.ones(len(times),dtype=bool),
        minute_valid=np.ones(len(times),dtype=bool),missing_reason=[None]*len(times)))
        for symbol,factor in zip(common.SYMBOLS,(1.,.5),strict=True)]).sort(['open_us','symbol'])


def test_daily_public_native_route(tmp_path):
    start = common.day_us(date(2024,1,1))
    end = start+3*common.DAY_US
    calendar = np.arange(start,end,common.MINUTE_US,dtype=np.int64)
    bars = daily_fixture(start)
    plan = daily.fixed_targets(bars,calendar)
    assert plan.receipt['paired_comparison_allowed'] and not plan.receipt['warmup_failed']
    assert plan.receipt['original_public_hook_reused'] and plan.receipt['timeframe_minutes']==1440
    assert plan.receipt['daily_prices_used_for_execution_or_risk'] is False
    assert plan.targets['available_us'].min()==start  # no warmup account/targets
    for symbol in common.SYMBOLS:
        intents = plan.calendar_ledger.filter(pl.col('symbol')==symbol)
        assert intents.height==len(calendar)
        assert intents['target_weight'][0]==.3
        assert intents['target_weight'][1440]==.3
        assert intents['target_weight'][2880]==0.
        assert intents['target_weight'][-1]==0.
    # Independently inspect the pinned raw hooks against fixed scalar formulas.
    cls = daily.public._load_public_hooks()
    for symbol in common.SYMBOLS:
        rows = bars.filter((pl.col('symbol')==symbol)&(pl.col('close_us')<=start)).sort('close_us')
        candles = np.column_stack((rows['close_us'].to_numpy()//1000,rows['open'].to_numpy(),
            rows['close'].to_numpy(),rows['high'].to_numpy(),rows['low'].to_numpy(),rows['volume'].to_numpy()))
        rules = cls(); rules.vars={}; rules.candles=candles; rules.close=float(candles[-1,2])
        assert rules.should_long()==bool(candles[-1,2]>np.max(candles[-21:-1,3]))
        assert all(filter_() for filter_ in rules.filters())==bool(candles[-1,2]>np.mean(candles[-200:,2]))
    # A current daily close is usable exactly at UTC00; future finite poison is
    # not permitted to change earlier intents or terminal clipped day inputs.
    future = bars.with_columns([pl.when(pl.col('open_us')>=start+common.DAY_US)
        .then(pl.col(field)*10).otherwise(pl.col(field)).alias(field) for field in ('open','high','low','close')])
    poisoned = daily.fixed_targets(future,calendar)
    prefix = pl.col('decision_us')<start+2*common.DAY_US
    assert plan.calendar_ledger.filter(prefix).equals(poisoned.calendar_ledger.filter(prefix))
    terminal_poison = bars.with_columns([pl.when(pl.col('close_us')==end)
        .then(pl.col(field)*20).otherwise(pl.col(field)).alias(field) for field in ('open','high','low','close')])
    assert daily.fixed_targets(terminal_poison,calendar).targets.equals(plan.targets)
    # Missing/delayed actual warmup or newly closed bars fail paired comparison;
    # late invalidity cannot retroactively overwrite earlier causal target rows.
    missing = bars.filter(pl.col('open_us')!=start-2*common.DAY_US)
    assert not daily.fixed_targets(missing,calendar).receipt['paired_comparison_allowed']
    delayed = bars.with_columns(pl.when(pl.col('close_us')==start+common.DAY_US)
        .then(pl.col('available_us')+common.MINUTE_US).otherwise(pl.col('available_us')).alias('available_us'))
    delayed_plan = daily.fixed_targets(delayed,calendar)
    assert not delayed_plan.receipt['paired_comparison_allowed']
    assert delayed_plan.calendar_ledger.filter(pl.col('decision_us')<start+common.DAY_US).equals(
        plan.calendar_ledger.filter(pl.col('decision_us')<start+common.DAY_US))
    delayed_start = bars.with_columns(pl.when(pl.col('close_us')==start)
        .then(pl.col('available_us')+common.MINUTE_US).otherwise(pl.col('available_us')).alias('available_us'))
    delayed_start_plan = daily.fixed_targets(delayed_start,calendar)
    btc = delayed_start_plan.calendar_ledger.filter(pl.col('symbol')=='BTCUSDT')
    assert btc['target_weight'][0]==0. and btc['target_weight'][1]==.3
    # A prior warmup breakout does not create held state at a fresh-flat score.
    extra_warmup = bars.filter(pl.col('open_us')==start-200*common.DAY_US).with_columns(
        pl.lit(start-201*common.DAY_US).cast(pl.Int64).alias('open_us'),
        pl.lit(start-200*common.DAY_US).cast(pl.Int64).alias('close_us'),
        pl.lit(start-200*common.DAY_US).cast(pl.Int64).alias('available_us'))
    warmup_breakout = pl.concat([extra_warmup,bars]).sort(['open_us','symbol']).with_columns([
        pl.when(pl.col('open_us')==start-2*common.DAY_US)
        .then(pl.lit(value)*pl.when(pl.col('symbol')=='BTCUSDT').then(1.).otherwise(.5))
        .otherwise(pl.col(field)).alias(field)
        for field,value in (('open',103.),('close',103.),('high',103.1),('low',102.9))])
    flat = warmup_breakout.with_columns([pl.when(pl.col('open_us')==start-common.DAY_US)
        .then(pl.lit(value)*pl.when(pl.col('symbol')=='BTCUSDT').then(1.).otherwise(.5))
        .otherwise(pl.col(field)).alias(field)
        for field,value in (('open',100.),('close',100.),('high',100.1),('low',99.9))])
    assert daily.fixed_targets(flat,calendar).calendar_ledger['target_weight'][0]==0.
    for key in ('symbol','interval'):
        bad = bars.with_columns(pl.when(pl.col('open_us')==start-200*common.DAY_US)
            .then(None).otherwise(pl.col(key)).alias(key))
        with pytest.raises(ValueError,match='Only BTC/ETH'):
            daily.fixed_targets(bad,calendar)
    with pytest.raises(ValueError,match='integer minute'):
        daily.fixed_targets(bars,calendar.astype(float))
    # Same isolated native entry used by real runner: changed date globals only.
    minutes = minute_fixture(start,end)
    derivation=[]
    namespace = runner.native_namespace(date(2023,12,1),date(2024,1,4),derivation)
    assert native.BEGIN_US==1751328000000000 and native.END_US==1772323200000000
    assert all(row['original_AST_sha256']==row['derived_AST_sha256'] for row in derivation)
    config = common.comparison_config(start,end,8)
    result = namespace.run_backtest(minutes.select('symbol','close_us','available_us'),minutes,plan.targets,config)
    ledger = common.write_ledger(tmp_path/'daily-native-ledger',result,minutes)
    trades = result.trades.sort('execution_us',maintain_order=True).to_dicts()
    assert any(row['side']=='buy' for row in trades) and any(row['side']=='sell' for row in trades)
    cash = config.initial_cash; quantities=dict.fromkeys(common.SYMBOLS,0.)
    fee,execution = 0.,0.
    for row in trades:
        q,fill,mid = (row[key] for key in ('quantity','fill_price','mid_price'))
        assert row['execution_us']>=row['signal_us']+common.MINUTE_US+1
        assert start<=row['signal_us']<end
        if row['side']=='buy':
            assert row['signal_us']==start
            cash-=q*fill; quantities[row['symbol']]+=q*.999; fee+=q*.001*mid
            assert row['fee_asset']==row['symbol'][:-4] and row['position_delta']<q
        else:
            assert q<=quantities[row['symbol']]+1e-10
            quantities[row['symbol']]-=q; cash+=q*fill*.999; fee+=q*fill*.001
            assert row['fee_asset']=='USDT'
        execution+=q*abs(fill-mid)
        assert abs(cash-row['cash_after'])<=1e-7
    inventory = pl.read_parquet(Path(ledger['directory'])/'minute_nav_inventory.parquet')
    last_prices={symbol:minutes.filter(pl.col('symbol')==symbol)['close'][-1] for symbol in common.SYMBOLS}
    final = cash+sum(quantities[symbol]*last_prices[symbol] for symbol in common.SYMBOLS)
    assert abs(inventory['nav'][-1]-final)<=1e-7
    assert abs(ledger['summary']['fees']-fee)<=1e-7
    assert abs(ledger['summary']['execution_costs']-execution)<=1e-7
    assert ledger['summary']['same_quantity_gross_minus_cost_equals_net']
    assert not ledger['summary']['candidate_qualification_allowed']
