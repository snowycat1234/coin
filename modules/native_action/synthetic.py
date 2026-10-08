"""Tiny executable smoke adapter. All prices/expert targets here are synthetic."""
from __future__ import annotations
import numpy as np
import polars as pl
from quant.bybit_isolated_account import BybitIsolatedAccount
from scripts.investment import perpetual_directional as engine
from scripts.investment.resumable_perpetual import NativeDailySimulator
from .runner import NativeExperiment
from .teacher import DayContext,E6,Proposal,linear_ramp_risk_mapper

START=1_704_067_200_000_000
SYMBOLS=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')


def build(options):
    days=int(options.get('days',3))
    if not 3<=days<=4:raise ValueError('Synthetic smoke only supports 3-4 days')
    n=days*1440
    dates=START+np.arange(days,dtype=np.int64)*engine.DAY
    times=START+np.arange(n,dtype=np.int64)*engine.MINUTE
    market={}
    for j,s in enumerate(SYMBOLS):
        price=(100.+j)*np.exp(np.arange(n)*(.000001 if j%2==0 else -.0000005))
        market[s]=dict(open=price,close=price,mark=price,quote_volume=np.full(n,20_000_000.))
    daily=pl.DataFrame([dict(symbol=s,close_us=int(d),close=100.+j if i==0 else float(market[s]['close'][i*1440-1]))
                       for i,d in enumerate(dates) for j,s in enumerate(SYMBOLS)])
    events=[dict(symbol=s,event_us=int(d)+offset,raw_rate=.0001,reported_interval_hours=8.)
            for d in dates for offset in (0,1000,8*60*engine.MINUTE) for s in SYMBOLS]
    window=dict(start=START,end=START+n*engine.MINUTE,symbols=SYMBOLS,times=times,
                market=market,daily=daily,events=events,input_proofs=[])
    sim=NativeDailySimulator(window,'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],
                            account_factory=BybitIsolatedAccount,persist_cash_close=True,final_day_target_zero=True)
    sim.budget=[1.,0.,0.,0.,0.,0.]
    targets=np.asarray([[0.,0.,0.,0.,0.],[.12]*5,[-.12,.12,-.12,.12,.12],
                        [.3,0,0,0,0],[0,.2,-.2,.2,0],[0,0,0,-.3,.3]])
    binding=dict(expert_order=list(E6),rank_checkpoint_sha256='1'*64,mapper_sha256='2'*64,
                 market_binding_sha256='3'*64,source_role='SYNTHETIC_SMOKE_NOT_MARKET_E6_EXPERIMENT')
    def context_at(stamp):
        return DayContext(stamp,stamp,(.01,.02),('ret21','vol30'),targets,
                          np.full(6,stamp,dtype=np.int64),
                          np.tile([.001,-.001,.002,.0005,-.0005],(30,1)),binding)
    def baseline_at(state,context):
        p=linear_ramp_risk_mapper(np.asarray(state.budget),np.full(6,1/6),context)
        return Proposal('SYNTHETIC_STATE',p.request,p.budget,p.targets,'SYNTHETIC_ONLY')
    return NativeExperiment(sim,context_at,linear_ramp_risk_mapper,baseline_at,binding)
