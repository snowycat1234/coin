"""Two actual shared-capital Spot accounts versus saved conditional perpetuals.

Reuses the normal Spot wallet and daily past-covariance target interface. Price,
inventory, commission asset and funding differ by product; this is a product
contrast, not a matched-risk alpha estimate or a funding-only intervention.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import UTC, datetime
import gc
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import time

import numpy as np
import polars as pl
from quant import disk, resources
from quant.backtest import BacktestConfig, run_backtest
from quant.paths import ROOT, STATE
from scripts.investment.vol_managed_perpetual_target import fixed_targets
from scripts.investment import hold_donchian_blend_target as blend
from scripts.research_v7.oracle_flow_ceiling import Progress
from scripts.research_v8.registry import FIELDS, append_event

DAY = 86_400_000_000
MINUTE = 60_000_000


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def write(path, value):
    with Path(path).open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False); f.write('\n')


def read(receipt):
    path = Path(receipt['path']).resolve()
    assert path.is_relative_to(ROOT) or path.is_relative_to(STATE)
    assert sha(path) == receipt['sha256'], path
    return json.loads(path.read_bytes())


def save_frame(frame, path):
    assert not path.exists()
    frame.write_parquet(path)
    return dict(path=str(path), sha256=sha(path), bytes=path.stat().st_size, rows=frame.height)


def daily_reduction(frame):
    one = (frame.sort('open_us').with_columns((pl.col('open_us')//DAY*DAY).alias('day'))
        .group_by(['symbol','day']).agg(pl.col('open').first(), pl.col('high').max(),
            pl.col('low').min(), pl.col('close').last(), pl.col('volume').sum(),
            pl.len().alias('rows'), pl.col('open_us').first().alias('first_open'),
            pl.col('open_us').last().alias('last_open'), pl.col('available_us').max().alias('last_available')))
    assert one['rows'].eq(1440).all() and one['first_open'].eq(one['day']).all()
    assert one['last_open'].eq(one['day']+DAY-MINUTE).all()
    assert one['last_available'].eq(one['day']+DAY).all()
    return one.select('symbol','open','high','low','close','volume').with_columns(
        pl.Series('open_us',one['day']), pl.Series('close_us',one['day']+DAY),
        pl.Series('available_us',one['day']+DAY), pl.lit('1d').alias('interval'))


def inventory_path(minutes, trades, symbols, start, end, summary):
    """Saved fills marked on every actual minute close, without simulating fills."""
    times = np.arange(start+MINUTE,end+1,MINUTE,dtype=np.int64)
    stamps = trades['execution_us'].to_numpy()
    assert np.all(np.diff(stamps)>=0)
    indexes = np.searchsorted(stamps,times,side='left')
    cash_states = np.r_[10000.,10000.+np.cumsum(trades['cash_delta'].to_numpy())]
    cash = cash_states[indexes]
    nav, gross = cash.copy(), np.zeros(len(times),dtype=np.float64)
    columns = dict(close_us=times,cash=cash)
    for symbol in symbols:
        tape = trades.filter(pl.col('symbol')==symbol)
        states = np.r_[0.,np.cumsum(tape['position_delta'].to_numpy())]
        q = states[np.searchsorted(tape['execution_us'].to_numpy(),times,side='left')]
        market = minutes.filter((pl.col('symbol')==symbol)&(pl.col('open_us')>=start)&(pl.col('open_us')<end)).sort('open_us')
        assert np.array_equal(market['open_us'].to_numpy()+MINUTE,times)
        mark = market['close'].to_numpy()
        nav += q*mark; gross += np.abs(q*mark)
        columns['quantity_'+symbol]=q; columns['mark_'+symbol]=mark
        assert np.min(q)>=-1e-12 and np.max(np.abs(q*mark)/nav)<1
    assert np.isfinite(nav).all() and np.min(nav)>0 and np.min(cash)>=-1e-7
    columns.update(nav=nav,gross_weight=gross/nav,net_weight=gross/nav)
    frame=pl.DataFrame(columns)
    final_error=abs(nav[-1]-summary['final_nav'])
    assert final_error<=1e-7
    maximum_asset=max(float(np.max(np.abs(columns['quantity_'+s]*columns['mark_'+s])/nav)) for s in symbols)
    maximum_gross=float(np.max(gross/nav))
    # No minute risk-cut implementation is claimed. A observed breach invalidates
    # the comparison instead of silently disabling necessary reductions.
    caps_ok=maximum_asset<=.3+1e-9 and maximum_gross<=.6+1e-9
    running_peak=np.maximum.accumulate(np.r_[10000.,nav])[1:]
    minute_mdd=float(np.max(1-nav/running_peak))
    risk=dict(minute_max_drawdown=minute_mdd,minute_mean_gross_weight=float(np.mean(gross/nav)),
        minute_max_gross_weight=maximum_gross,minute_mean_net_weight=float(np.mean(gross/nav)),
        minute_max_asset_weight=maximum_asset,complete_minute_observations=len(times),
        reconstructed_NAV_final_error_USDT=final_error,observed_caps_ok=caps_ok,
        scope='POST_REPLAY_SAVED_FILL_MINUTE_CLOSE_MARKS_NOT_INTRAMINUTE_OR_NATIVE_RISK',
        continuous_drift_risk_reduction_implemented=False)
    return frame,risk


def comparison(spot, perpetual):
    s,p=spot['summary'],perpetual['summary']
    # Both returns use their full initial capital. Terminal liquidation status
    # remains separate from marked NAV so Spot dust cannot become free cash.
    net=s['final_nav']-10000.
    gross=s['gross_pnl_before_costs']
    deltas=dict(net=net-p['net_PnL'],gross=gross-p['gross_PnL_same_quantities'],
        fees=s['fees']-p['fees_USDT'],execution=s['execution_costs']-p['execution_cost_USDT'],
        funding=0.-p['funding_USDT'])
    assert abs(deltas['net']-(deltas['gross']-deltas['fees']-deltas['execution']+deltas['funding']))<1e-7
    return dict(spot_id=spot['id'],perpetual_id=perpetual['id'],net_delta_USDT=deltas['net'],
        gross_delta_USDT=deltas['gross'],fee_delta_USDT=deltas['fees'],execution_delta_USDT=deltas['execution'],
        funding_delta_USDT=deltas['funding'],spot_net_USDT=net,perpetual_net_USDT=p['net_PnL'],
        spot_daily_annual_volatility=s['annual_volatility'],perpetual_daily_annual_volatility=p['daily_metrics']['annual_volatility'],
        spot_daily_max_drawdown=s['max_drawdown'],perpetual_daily_max_drawdown=p['daily_metrics']['max_drawdown'],
        spot_minute_max_drawdown=spot['risk']['minute_max_drawdown'],perpetual_minute_max_drawdown=p['minute_max_drawdown'],
        spot_turnover_over_full_initial_capital=spot['turnover_over_full_initial_capital'],
        perpetual_turnover_over_full_initial_capital=p['normalized_total_turnover'],
        spot_terminal_cash_realized=spot['terminal_cash_realized'],perpetual_terminal_cash_realized=p['terminal_cash_realized'],
        comparison_basis='FULL_CAPITAL_FINAL_MARKED_NAV_WITH_REAL_END_TRADES_AND_RETAINED_RESIDUAL',
        funding_only_causal_effect=False,actual_risk_matched=False)


def spot_comparison(challenger, control):
    """Same-product full-capital contrast, retaining both actual risk paths."""
    assert challenger['config'] == control['config']
    s, p = challenger['summary'], control['summary']
    delta = dict(net=s['final_nav']-p['final_nav'],
        gross=s['gross_pnl_before_costs']-p['gross_pnl_before_costs'],
        fees=s['fees']-p['fees'], execution=s['execution_costs']-p['execution_costs'])
    assert abs(delta['net']-(delta['gross']-delta['fees']-delta['execution'])) < 1e-7
    return dict(challenger_id=challenger['id'], control_id=control['id'],
        net_delta_USDT=delta['net'], gross_delta_USDT=delta['gross'],
        fee_delta_USDT=delta['fees'], execution_delta_USDT=delta['execution'],
        funding_delta_USDT=0, actual_risk_matched=False,
        comparison_basis='SAME_SPOT_INPUT_COST_ACCOUNT_FULL_CAPITAL_DIFFERENT_FIXED_TARGET_RECIPE',
        challenger_daily_vol=s['annual_volatility'], control_daily_vol=p['annual_volatility'],
        challenger_daily_MDD=s['max_drawdown'], control_daily_MDD=p['max_drawdown'],
        challenger_minute_MDD=challenger['risk']['minute_max_drawdown'],
        control_minute_MDD=control['risk']['minute_max_drawdown'],
        challenger_turnover=challenger['turnover_over_full_initial_capital'],
        control_turnover=control['turnover_over_full_initial_capital'])


def cached_market(control):
    """Use exact accepted artifacts without copying or reducing source again."""
    assert control['status'] == 'COMPLETE_SPOT_PRODUCT_MARKED_COMPARISON_NOT_NATIVE_OR_APR'
    frames = []
    for key in ('daily_bars', 'market_minutes'):
        receipt = control[key]; path = Path(receipt['path'])
        assert path.resolve().is_relative_to(STATE) and not path.is_symlink()
        assert path.stat().st_size == receipt['bytes'] and sha(path) == receipt['sha256']
        frame = pl.read_parquet(path)
        assert frame.height == receipt['rows']
        frames.append(frame)
    return (*frames, control['source_records'])


def main():
    p=argparse.ArgumentParser(); p.add_argument('--protocol',type=Path,required=True)
    p.add_argument('--run-dir',type=Path,required=True); p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); config=json.loads(a.protocol.read_bytes())
    run=a.run_dir.resolve(); assert run.is_relative_to(STATE) and not run.exists() and not a.output.exists()
    assert os.environ.get('COIN_TASK_ID')
    for name,h in config['source_hashes'].items(): assert sha(ROOT/name)==h,name
    assert sha(ROOT/'state/dataset_lock.json')=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
    source=read(config['spot_source'])
    recipe=config.get('recipe','HOLD8')
    assert recipe in ('HOLD8','HALF_HOLD10_EXIT10')
    control=read(config['spot_control']) if recipe=='HALF_HOLD10_EXIT10' else None
    perpetual=read(config['perpetual_report']) if control is None else None
    assert source['status']=='PASS_REUSED_FROZEN_SPOT_MINUTE_SOURCE_578D_CALENDAR'
    assert (control or perpetual)['actual_calendar_days']==303
    symbols=config['symbols']; assert symbols==['BTCUSDT','ETHUSDT']
    start,end=config['start_us'],config['end_us']; assert end-start==303*DAY
    assert config['annual_vol_target']==(.08 if control is None else .10) and config['terminal_exit_minutes']==5
    assert config['minimum_notional_USDT']==10 and config['quantity_step']=='1E-8'
    run.mkdir(); progress=Progress(); began=time.monotonic()
    peak=resources.status()['ram_current_bytes']
    result=dict(status='STARTED_NOT_COMPLETE',task_id=os.environ['COIN_TASK_ID'],
        git_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        protocol_sha256=sha(a.protocol),source_hashes=config['source_hashes'],cases=[],comparisons=[],
        price_source='BINANCE_SPOT_VS_BINANCE_USDM_WITH_USER_BYBIT_VIP0_COST_SCENARIOS',
        candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',
        source_QA_reused=True,new_downloads=0,API_calls=0,new_model_fits=0,HPO=0,
        locked_consumed=False,orders_sent=0,native_Bybit_certified=False,
        funding_unit_certified=False,actual_calendar_days=303,
        spot_source=config['spot_source'],perpetual_report=config.get('perpetual_report'),
        spot_control=config.get('spot_control'),recipe=recipe)
    module=config.get('module','D077')
    if control is not None:
        result['price_source']='BINANCE_SPOT_WITH_USER_BYBIT_VIP0_COST_SCENARIOS'
    def guard():
        nonlocal peak
        peak=max(peak,resources.status()['ram_current_bytes'])
        assert time.monotonic()-began<=config['budget']['wall_seconds']
        assert sum(x.stat().st_size for x in run.rglob('*') if x.is_file())<=config['budget']['owned_bytes']
    event=dict.fromkeys(FIELDS);event.update(event_id=module+':START',event_type='OPERATIONAL_RESEARCH_START',
        experiment_id=config['experiment_id'],git_commit=result['git_commit'],protocol_hash=sha(a.protocol),
        model_family='NORMAL_SPOT_'+recipe, fits=0)
    append_event(ROOT/'reports/experiment_registry.jsonl',event)
    try:
        progress.update('容量守卫，扫描总量未知',None,None,'扫描')
        result['disk_before']=disk.check(config['budget']['owned_bytes'])
        result['disk_before']['measured_utc']=datetime.now(UTC).isoformat()
        assert result['disk_before']['total_bytes']+config['budget']['owned_bytes']<32_000_000_000
        rows=[x for x in source['sources'] if x['symbol'] in symbols and '2024-01'<=x['month']<='2025-06']
        assert len(rows)==36 and len({(x['symbol'],x['month']) for x in rows})==36
        daily,execution,receipts=[],[],[]
        cols=['symbol','open_us','close_us','available_us','open','high','low','close','volume','quote_volume']
        for i,row in enumerate(rows if control is None else []):
            path=Path(row['normalized_path'])
            expected=ROOT/'data/normalized/spot'/row['symbol']/'1m'/(row['month']+'.parquet')
            assert path==expected and path.resolve()==expected and not path.is_symlink()
            assert path.stat().st_size==row['old_quality']['normalized_bytes']
            assert sha(path)==row['normalized_sha256']
            frame=pl.read_parquet(path,columns=cols)
            assert frame.height==row['rows']
            daily.append(daily_reduction(frame))
            if row['month']>='2024-08': execution.append(frame)
            receipts.append(dict(path=str(path),sha256=row['normalized_sha256'],symbol=row['symbol'],month=row['month'],rows=row['rows']))
            progress.update('复用已接受现货源及完整日线',i+1,len(rows),'文件')
            guard()
        if control is None:
            bars=pl.concat(daily).sort(['symbol','open_us']); minutes=pl.concat(execution).sort(['symbol','open_us'])
            del frame
        else:
            bars,minutes,receipts=cached_market(control)
            assert len(receipts)==len(rows)
            assert {(r['symbol'],r['month'],r['sha256']) for r in receipts} == {
                (r['symbol'],r['month'],r['normalized_sha256']) for r in rows}
            assert control['spot_source']==config['spot_source']
            assert all(c['symbols']==symbols and c['config']['start_us']==start
                and c['config']['end_us']==end and c['fee_snapshot']==config['fee_snapshot']
                and c['risk']['observed_caps_ok'] for c in control['cases'])
            progress.update('已接受现货缓存SHA匹配，无复制',2,2,'工件')
        del daily,execution;gc.collect()
        decisions=np.arange(start,end,DAY,dtype=np.int64)
        if control is None:
            targets,meta=fixed_targets(bars,decisions,'LONG_ONLY',symbols=symbols,allocation='EQUAL',annual_vol_target=.08)
        else:
            targets,meta=blend.fixed_targets(bars,decisions,'LONG_ONLY',symbols=symbols)
        meta['source_target_builder_id']=meta['strategy_id']
        meta['strategy_id']='COIN_SPOT_'+recipe+'_1D_SHARED_CAPITAL'
        assert targets.height==303*len(symbols)
        assert targets['target_weight'].is_finite().all()
        result['target_meta']=meta; result['source_records']=receipts
        result['market_minutes']=save_frame(minutes,run/'source_minutes.parquet') if control is None else control['market_minutes']
        result['daily_bars']=save_frame(bars,run/'source_daily_bars.parquet') if control is None else control['daily_bars']
        result['target_artifact']=save_frame(targets,run/'targets.parquet')
        fee_source=read(config['fee_snapshot'])
        fee_row=next(x for x in fee_source['product_rates'] if x['product_id']=='SPOT_CRYPTO_STANDARD')
        assert float(fee_row['taker_rate_fraction'])==float(fee_row['taker_bps'])/10000==.001
        assert float(fee_row['taker_percent_display'].removesuffix('%'))/100==.001
        assert fee_source['mnt_discount_enabled'] is False
        for cost in config['costs']:
            progress.update('同本金真实现货账户回放',len(result['cases']),len(config['costs']),'账户',cost=cost['id'])
            bc=BacktestConfig(initial_cash=10000,fee_bps=float(fee_row['taker_bps']),
                fee_settlement='RECEIVED_ASSET',half_spread_bps=cost['half_spread_bps'],slippage_bps=cost['slippage_bps'],
                start_us=start,end_us=end,target_annual_vol=None,latency_minutes=1,max_order_wait_minutes=5,
                min_notional=10,lot_step_by_symbol={s:1e-8 for s in symbols},
                liquidate_at_end=True,terminal_exit_minutes=5)
            account=run_backtest(bars,minutes,targets,bc)
            assert account.daily_nav.height==303 and not account.daily_nav['stale_prices'].any()
            path,risk=inventory_path(minutes,account.trades,symbols,start,end,account.summary)
            day_path=path.filter(pl.col('close_us')%DAY==0).rename({'close_us':'day_end_us'})
            assert day_path.height==303
            assert np.max(np.abs(day_path['nav'].to_numpy()-account.daily_nav['nav'].to_numpy()))<=1e-7
            daily_frame=account.daily_nav.with_columns(pl.Series('day_end_us',day_path['day_end_us']))
            for name in day_path.columns:
                if name not in daily_frame.columns:daily_frame=daily_frame.with_columns(day_path[name])
            directory=run/cost['id'];directory.mkdir()
            terminal_marks={s:dict(price=float(path['mark_'+s][-1]),clock=end) for s in symbols}
            residual=sum(account.summary['open_positions'][s]*terminal_marks[s]['price'] for s in symbols)
            cash_realized=all(q==0 for q in account.summary['open_positions'].values())
            case=dict(id=cost['id'],cost_id=cost['perpetual_cost_id'],symbols=symbols,config=asdict(bc),
                summary=account.summary,terminal_marks=terminal_marks,risk=risk,
                terminal_cash_realized=cash_realized,terminal_marked_inventory_USDT=residual,
                liquidated_return=('COMPLETE_CASH_RETURN' if cash_realized else 'NOT_EVALUABLE'),
                turnover_over_full_initial_capital=float(account.trades['notional'].sum()/10000),
                funding_USDT=0,fee_snapshot=config['fee_snapshot'],fee_historical_scope=fee_source['historical_use'],
                artifacts={'targets.parquet':result['target_artifact'],
                    'trades.parquet':save_frame(account.trades,directory/'trades.parquet'),
                    'orders.parquet':save_frame(account.orders,directory/'orders.parquet'),
                    'daily_nav.parquet':save_frame(daily_frame,directory/'daily_nav.parquet'),
                    'minute_nav_inventory.parquet':save_frame(path,directory/'minute_nav_inventory.parquet')})
            case['artifacts']['trades']=case['artifacts']['trades.parquet']
            case['artifacts']['daily_nav']=case['artifacts']['daily_nav.parquet']
            result['cases'].append(case)
            for pc in (control or perpetual)['cases']:
                if control is not None and pc['id']==case['id']:
                    result['comparisons'].append(spot_comparison(case,pc))
                elif control is None and pc['cost_id']==cost['perpetual_cost_id']:
                    result['comparisons'].append(comparison(case,pc))
            guard();del account,path,daily_frame;gc.collect()
        assert len(result['cases'])==2 and len(result['comparisons'])==(4 if control is None else 2)
        result['status']=(('COMPLETE_SPOT_PRODUCT_MARKED_COMPARISON_NOT_NATIVE_OR_APR' if control is None
                          else 'COMPLETE_SPOT_DEFENSIVE_MARKED_COMPARISON_NOT_NATIVE_OR_APR')
            if all(c['risk']['observed_caps_ok'] for c in result['cases'])
            else 'FAILED_OBSERVED_CAPS_PRODUCT_COMPARISON_LIMITED_DIAGNOSTIC')
        progress.update('产品账户保存完成',2,2,'账户')
    except Exception as error:
        result.update(status='FAILED_PRODUCT_REPLAY_PRESERVED',error_type=type(error).__name__,reason=str(error));raise
    finally:
        result.update(elapsed_seconds=time.monotonic()-began,process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            shared_RAM_sampled_peak_bytes=peak,resources_after=resources.status(),
            owned_bytes=sum(x.stat().st_size for x in run.rglob('*') if x.is_file()),created_utc=datetime.now(UTC).isoformat())
        write(a.output,result)
        append_event(ROOT/'reports/experiment_registry.jsonl',dict(event,event_id=module+':RESULT',event_type='OPERATIONAL_RESEARCH_RESULT',
            success_failure=result['status'],artifact_path=str(a.output),artifact_sha256=sha(a.output)))
        progress.stop.set();progress.thread.join(timeout=3)
    print(json.dumps(dict(status=result['status'],cases=len(result['cases']),elapsed_seconds=result['elapsed_seconds'],process_peak_RSS_bytes=result['process_peak_RSS_bytes'])))


if __name__=='__main__':main()
