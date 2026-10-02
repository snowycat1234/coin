"""One new D034 synthetic route/date/daily-availability case; no account replay."""
from copy import deepcopy
from datetime import date
import numpy as np
import polars as pl
import pytest
from scripts.investment import public_long_vol_managed_adapter as adapter

def test_single_vm_parent_namespace_and_completed_daily_causality():
    spec=deepcopy(adapter.parent_metadata())
    spec.update(strategy_ids=[adapter.STRATEGY],planned_ledgers=1,maximum_new_owned_bytes=300_000_000,
        namespace_parent_protocol=dict(path=adapter.PARENT_PROTOCOL,sha256=adapter.PARENT_PROTOCOL_SHA),
        reused_minute_input=dict(report_path=adapter.PARENT_REPORT,report_sha256=adapter.PARENT_REPORT_SHA,
            path=str(adapter.INPUT_PATH),sha256=adapter.INPUT_SHA))
    before=(adapter.parent.old.START,adapter.parent.old.LOCKED,adapter.parent.timeguard.BEGIN,
        adapter.parent.timeguard.END,adapter.parent.v2.causal_vol_multiplier,
        adapter.parent.bulk.common,adapter.parent.native.BEGIN_US,adapter.parent.native.END_US)
    ns=adapter.context(spec);strategies,windows,planned=ns['comparison_plan'](spec)
    _,lower,start,end=windows[0]
    assert strategies==(adapter.STRATEGY,) and planned==1
    assert (start-lower)//adapter.parent.old.DAY_US==31 and (end-start)//adapter.parent.old.DAY_US==547
    assert len(ns['period_aggregate']([],strategies))==1 and ns['period_aggregate']([],strategies)[0]['spread_bps']==8
    private=ns['benchmarks'];bulk=ns['bulk_fixed_targets'];risk=private.causal_vol_multiplier
    assert bulk.fixed_targets.__globals__['common'] is private
    assert risk.__globals__['_time'] is private._time and risk.__globals__['_v1'] is private._v1
    assert private._v1.causal_vol_multiplier is adapter.parent.v1.causal_vol_multiplier
    assert ns['research'].__globals__['bulk_fixed_targets'] is bulk
    assert ns['research'].__globals__['PERIOD_NATIVE'] is ns['PERIOD_NATIVE']
    assert ns['research'].__globals__['reused_minute_input'] is adapter.parent.old.reused_minute_input
    # Complete synthetic UTC days establish the preserved daily-reference route;
    # all actual source prices, account kernels and fee math remain unexecuted.
    day,minute=adapter.parent.old.DAY_US,adapter.parent.old.MINUTE_US
    beginning=adapter.parent.old.day_us(date(2023,12,23))
    opens=beginning+np.arange(10*1440,dtype=np.int64)*minute
    day_index=np.arange(len(opens))//1440
    prices=100*np.cumprod(1+np.array([0.,.10,-.09,.08,-.07,.06,-.05,.04,-.03,.02]))
    raw=pl.DataFrame(dict(symbol=np.tile(['BTCUSDT','ETHUSDT'],len(opens)),
        open_us=np.repeat(opens,2),close_us=np.repeat(opens+minute,2),
        available_us=np.repeat(opens+minute,2),close=np.repeat(prices[day_index],2),minute_valid=np.ones(len(opens)*2,dtype=bool)))
    daily=ns['reference_daily_returns'](raw)
    assert daily.height==9 and daily['day_end_us'][0]==beginning+2*day
    assert daily.filter(pl.col('day_end_us')==start)['available_us'][0]==start
    calendar=start+np.arange(4,dtype=np.int64)*minute
    closes=ns['signal_close_view'](raw,calendar)
    plan=bulk.fixed_targets(adapter.STRATEGY,closes,calendar,daily_returns=daily)
    observed=plan.calendar_ledger
    assert not plan.receipt['warmup_failed'] and plan.receipt['paired_comparison_allowed']
    assert plan.receipt['strategy_id']==adapter.STRATEGY and plan.receipt['decision_count']==4
    assert 0<observed['target_weight'][0]<.3
    assert observed.filter(pl.col('decision_us')<calendar[-1])['target_weight'].n_unique()==1
    assert observed.filter(pl.col('decision_us')==calendar[-1])['target_weight'].to_list()==[0.,0.]
    assert observed.filter(pl.col('decision_us')==calendar[-1])['reason'].unique().to_list()==['COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL']
    assert observed['earliest_permissible_order_us'].to_numpy().tolist()==(observed['decision_us'].to_numpy()+5_000_000).tolist()
    # Future completed-day return and future raw prices cannot affect this prefix.
    future=raw.with_columns(pl.when(pl.col('open_us')>=start).then(pl.col('close')*7).otherwise(pl.col('close')).alias('close'))
    shifted=bulk.fixed_targets(adapter.STRATEGY,ns['signal_close_view'](future,calendar),calendar,
        daily_returns=ns['reference_daily_returns'](future))
    assert plan.targets.equals(shifted.targets) and observed.equals(shifted.calendar_ledger)
    # A delayed newest completed UTC day is not forward-filled or traded.
    delayed=daily.with_columns(pl.when(pl.col('day_end_us')==start).then(pl.col('available_us')+minute)
        .otherwise(pl.col('available_us')).alias('available_us'))
    unavailable=bulk.fixed_targets(adapter.STRATEGY,closes,calendar,daily_returns=delayed)
    assert unavailable.receipt['warmup_failed'] and not unavailable.receipt['paired_comparison_allowed']
    assert unavailable.calendar_ledger.filter(pl.col('decision_us')==start)['target_weight'].to_list()==[0.,0.]
    assert risk(daily,start) is not None
    # Span7 describes the EWMA; an eighth older return still sets its seed.
    seed_changed=daily.with_columns(pl.when(pl.col('day_end_us')==beginning+2*day).then(.6)
        .otherwise(pl.col('gross_exposure_return')).alias('gross_exposure_return'))
    assert risk(seed_changed,start)!=risk(daily,start)
    with pytest.raises(ValueError):adapter.parent.v2.causal_vol_multiplier(daily,start)
    with pytest.raises(ValueError):private.calendar_array(np.array([end,end+minute],dtype=np.int64))
    assert np.array_equal(private.calendar_array(np.array([end-2*minute,end-minute],dtype=np.int64)),[end-2*minute,end-minute])
    for key,value in [('strategy_ids',['CASH',adapter.STRATEGY]),('planned_ledgers',3),
        ('reused_minute_input',{**spec['reused_minute_input'],'path':str(adapter.INPUT_PATH.with_suffix('.arrow'))}),
        ('costs',{**spec['costs'],'spread_bps':[2,4,8]})]:
        with pytest.raises(ValueError):adapter.context({**spec,key:value})
    assert before==(adapter.parent.old.START,adapter.parent.old.LOCKED,adapter.parent.timeguard.BEGIN,
        adapter.parent.timeguard.END,adapter.parent.v2.causal_vol_multiplier,
        adapter.parent.bulk.common,adapter.parent.native.BEGIN_US,adapter.parent.native.END_US)
