"""Direct Turtle event hooks into the normal shared perpetual simulator.

Official 4h rules, fill callbacks and completed-minute delayed stops reuse
the existing adapter. Finances remain in the shared account and event loop.
Historical AST controllers are reproduced with their Git revision, not here.
"""
from __future__ import annotations
from functools import partial
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import polars as pl
from quant.paths import STATE
from scripts.investment import perpetual_directional as engine
from scripts.investment import turtle_direction_mask as strategy
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount

FOUR_HOURS=14_400_000_000
MODES=strategy.MODES
STRATEGY_ID=strategy.STRATEGY_ID


def load_window(manifest,window,warmup):
    """Read accepted normalized sources; no new archive, format QA or imputation."""
    result=engine.load_window(manifest,window,trade_ranges=True)
    symbols=result['symbols'];frames=[]
    for item in warmup['files']:
        path=Path(item['normalized_path']).resolve()
        engine.need(path.is_relative_to(STATE) and not path.is_symlink()
            and path.stat().st_size==item['normalized_bytes']
            and engine.sha(path)==item['normalized_sha256'],'Accepted official4h warmup bytes')
        frame=pl.read_parquet(path)
        engine.need(set(frame['symbol'].to_list())<=set(symbols),'Warmup product identity')
        frames.append(frame)
        result['input_proofs'].append(dict(id=item['source_id'],path=str(path),
            sha256=item['normalized_sha256'],bytes=item['normalized_bytes'],role='OFFICIAL_4H_WARMUP_ONLY'))
    engine.need(bool(frames),'Observed official4h warmup required')
    result['warmup_4h']=pl.concat(frames).sort(['symbol','open_us'])
    return result


def prepare_signal_context(window):
    """Sequential asset computation, synchronized decisions and no future input."""
    context={}
    for symbol in window['symbols']:
        market=window['market'][symbol]
        minute=pl.DataFrame(dict(open_us=window['times'],open=market['open'],
            close=market['close'],high=market['high'],low=market['low'],volume=market['volume']))
        bars=(minute.with_columns((pl.col('open_us')//FOUR_HOURS*FOUR_HOURS).alias('bucket'))
            .group_by('bucket',maintain_order=True).agg(pl.col('open').first(),pl.col('close').last(),
                pl.col('high').max(),pl.col('low').min(),pl.col('volume').sum(),pl.len().alias('rows'))
            .sort('bucket'))
        engine.need(bars['rows'].eq(240).all(),'Every4h signal owns exactly240 real minutes')
        score=bars.select(pl.col('bucket').alias('open_us'),'open','close','high','low','volume')
        warm=window['warmup_4h'].filter(pl.col('symbol')==symbol).select(score.columns).sort('open_us')
        engine.need(warm.height>=240 and warm['open_us'][-1]+FOUR_HOURS==window['start'],
                    'Contiguous observed official perpetual4h pre-score history')
        whole=pl.concat([warm,score],how='vertical').sort('open_us')
        stamps=whole['open_us'].to_numpy().astype(np.int64)+FOUR_HOURS
        engine.need(np.all(np.diff(stamps)==FOUR_HOURS),'Complete causal4h history, gaps not deleted')
        values=whole.select('open','close','high','low','volume').to_numpy()
        engine.need(np.isfinite(values).all() and np.all(values[:,:4]>0) and np.all(values[:,4]>=0),
                    'Finite actual signal OHLCV')
        daily=window['daily'].filter(pl.col('symbol')==symbol).sort('close_us')
        context[symbol]=dict(stamps=stamps,available=stamps.copy(),
            candles=np.column_stack((whole['open_us'].to_numpy()/1000,values)),
            daily_stamps=daily['close_us'].to_numpy(),daily_available=daily['available_us'].to_numpy(),
            daily_close=daily['close'].to_numpy())
    return context


def decision(bridge,histories,stamp):
    candles,availability,returns,daily_ends={},{},[],[]
    for symbol in bridge.symbols:
        c=histories[symbol]
        i=int(np.searchsorted(c['stamps'],stamp,side='right')-1)
        engine.need(i>=239 and c['stamps'][i]==stamp,'240 completed4h observations before decision')
        candles[symbol]=c['candles'][i-239:i+1];availability[symbol]=c['available'][i-239:i+1]
        d=int(np.searchsorted(c['daily_stamps'],stamp,side='right')-1)
        engine.need(d>=30 and np.all(c['daily_available'][d-30:d+1]<=stamp),
                    'Thirty actual past daily returns, never future covariance')
        engine.need(np.array_equal(c['daily_stamps'][d-30:d+1],
            np.arange(c['daily_stamps'][d]-30*engine.DAY,c['daily_stamps'][d]+1,engine.DAY)),
                    'Past covariance dates complete')
        close=c['daily_close'][d-30:d+1]
        returns.append(np.diff(close)/close[:-1]);daily_ends.append(int(c['daily_stamps'][d]))
    engine.need(len(set(daily_ends))==1,'Common ordered risk observation cutoff')
    bridge.on_bar_close(int(stamp),candles,np.column_stack(returns),daily_ends[0],
                        availability_us_by_symbol=availability)


def simulate(window,mode,cost,unit,progress=None,guard=None,*,allow_pyramiding=True):
    engine.need(mode in MODES and type(allow_pyramiding) is bool,'Explicit fixed direction and ADD permission')
    events=SimpleNamespace(FOUR_HOURS=FOUR_HOURS,prepare_signal_context=prepare_signal_context,
        decision=decision,bridge_factory=partial(strategy.TurtlePerpetualBridge,
            allow_pyramiding=allow_pyramiding))
    result=engine.simulate(window,mode,cost,unit,progress,guard,
                           account_factory=USDTLinearPerpetualAccount,event_strategy=events)
    result['summary'].update(strategy_id=STRATEGY_ID,allow_pyramiding=allow_pyramiding,
        signal_timeframe_minutes=240,native_Jesse_intrabar_replicated=False)
    return result
