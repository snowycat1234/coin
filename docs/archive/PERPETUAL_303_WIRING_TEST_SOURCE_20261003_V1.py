"""ONE UNRUN D045 case: new303 metadata/date wiring and causal target prefix.

All market-like values here are artificial. Matching a synthetic status string
never certifies a real source. No old source QA or financial suite is replayed.
"""
import calendar
import importlib.util
import sys

import numpy as np
import polars as pl
import pytest
from quant.paths import ROOT
from scripts.investment import perpetual_303_research as research


def test_new303_metadata_calendar_fixed_hold_and_future_prefix(monkeypatch):
    files={};roles={}
    layout={
        'trade_1m':('trade:1m:','USD_M_PERPETUAL_TRADE_KLINES','2024-09','2025-06','minute'),
        'mark_1m':('markPriceKlines:','USD_M_PERPETUAL_markPriceKlines','2024-09','2025-06','minute'),
        'funding':('fundingRate:','USD_M_PERPETUAL_fundingRate','2024-09','2025-06','event'),
        'trade_1d_warmup':('trade:1d:','USD_M_PERPETUAL_TRADE_KLINES','2024-02','2024-08','daily'),
        'trade_1d_score':('trade:1d:','USD_M_PERPETUAL_TRADE_KLINES','2024-09','2025-06','daily'),
    }
    for symbol in research.base.SYMBOLS:
        roles[symbol]={}
        for role,(prefix,product,lower,upper,kind) in layout.items():
            identities=[]
            for index,month in enumerate(research.prior.months(lower,upper)):
                days=calendar.monthrange(*map(int,month.split('-')))[1]
                identity=prefix+symbol+':'+month;identities.append(identity)
                count=days*1440 if kind=='minute' else days if kind=='daily' else index+2
                files[identity]=dict(symbol=symbol,product=product,month=month,rows=count)
            roles[symbol][role]=identities
    window=dict(id='303D',start=research.START,end_exclusive=research.END,days=303,
        minutes_per_symbol=436320,source_ids=roles)
    manifest=dict(status=research.MANIFEST_STATUS,funding_rate_unit='UNCONFIRMED',
        funding_unit_certified=False,locked_consumed=False,source_files=files,windows=[window])
    normalized=research.metadata_view(manifest)
    assert len(files)==94 and normalized['windows'][0]['symbols']['BTCUSDT']['rows_inherited_from_receipts']['funding']==65
    first,end=research.prior.stamp(research.START),research.prior.stamp(research.END)
    assert end-first==303*research.base.DAY and (end-first)//research.base.MINUTE==436320
    import copy
    missing=copy.deepcopy(manifest);missing['windows'][0]['source_ids']['ETHUSDT']['mark_1m'].pop()
    with pytest.raises(ValueError,match='Exact303 symbol/product/month'):
        research.metadata_view(missing)
    extra=copy.deepcopy(manifest);extra['source_files']['indexPriceKlines:BTCUSDT:2024-09']={}
    with pytest.raises(ValueError,match='Exact94'):
        research.metadata_view(extra)
    wider=copy.deepcopy(manifest);wider['windows'][0].update(end_exclusive='2026-03-02T00:00:00+00:00',days=547)
    with pytest.raises(ValueError,match='complete independent303'):
        research.metadata_view(wider)

    requested=[]
    def synthetic_proof(ref):
        requested.append(ref['path'])
        if ref['path']==research.INPUT:return manifest
        assert ref==research.PRECEDING_FAILURE
        return dict(completed_files=83,required_files=148,source_acceptance_granted=False)
    monkeypatch.setattr(research.base,'relative_proof',synthetic_proof)
    spec=dict(contract_id=research.CONTRACT,rules=research.RULES,period_ids=['303D'],
        cost_scenarios=research.base.COSTS,unit_scenarios=research.base.UNITS,
        input_manifest={'path':research.INPUT},preceding_failed_source=research.PRECEDING_FAILURE,
        frozen_sources=dict(research.PINS))
    wired=research.context(spec)  # Pure metadata + every exact AST anchor, no source payload call.
    assert requested==[research.PRECEDING_FAILURE['path'],research.INPUT]
    assert wired['load_window'] is research.base.load_window
    assert wired['simulate_SMA'].__globals__['strategy'] is research.sma
    assert wired['simulate_HOLD'].__globals__['strategy'].fixed_targets is research.hold.fixed_targets
    assert len(wired['main'].__globals__['strategy'].MODES)*len(research.base.COSTS)*len(research.base.UNITS)==20
    assert research.RULES['planned_trading_account_simulations']==16
    assert research.RULES['planned_constant_cash_baselines']==1
    finance_nodes=[row for row in wired['derivation'] if row['function']=='simulate']
    assert len(finance_nodes)==2 and all(row['changes']==[]
        and row['original_AST_sha256']==row['derived_AST_sha256'] for row in finance_nodes)
    assert all(row['matches']==1 for row in wired['derivation'][-1]['changes'])

    day=research.base.DAY;stamps=first+(np.arange(208,dtype=np.int64)-199)*day
    prices=np.r_[np.linspace(160.,100.,200),np.linspace(98.,91.,8)]
    bars=pl.DataFrame([dict(symbol=symbol,open_us=int(stamp-day),close_us=int(stamp),available_us=int(stamp),
        open=float(price),close=float(price),high=float(price+.1),low=float(price-.1),volume=1000.)
        for symbol in research.base.SYMBOLS for stamp,price in zip(stamps,prices,strict=True)])
    decisions=stamps[199:207];cut=int(decisions[2])
    outputs={'SMA':research.sma.fixed_targets(bars,decisions,'SHORT_ONLY')[0],
        'HOLD':research.hold.fixed_targets(bars,decisions,'LONG_ONLY')[0]}
    assert outputs['SMA'].filter(pl.col('available_us')==first)['target_weight'].max()<0
    assert outputs['HOLD'].filter(pl.col('available_us')==first)['target_weight'].min()>0
    changed=bars.with_columns(*[pl.when(pl.col('close_us')>cut).then(pl.col(key)*7)
        .otherwise(pl.col(key)).alias(key) for key in ('open','high','low','close')])
    for name,function,mode in [('SMA',research.sma.fixed_targets,'SHORT_ONLY'),('HOLD',research.hold.fixed_targets,'LONG_ONLY')]:
        after=function(changed,decisions,mode)[0]
        assert outputs[name].filter(pl.col('available_us')<=cut).equals(after.filter(pl.col('available_us')<=cut))
        with pytest.raises(ValueError,match='Complete independent scoring-day'):
            function(bars,decisions+1,mode)
        with pytest.raises(ValueError,match='Exactly200 completed available'):
            function(bars.filter(pl.col('close_us')>=first-198*day),decisions,mode)

    helper_path=ROOT/'docs/archive/PERPETUAL_303_INDEPENDENT_ADAPTER_HELPERS_20261003_V1.py'
    loader=importlib.util.spec_from_file_location('_d045_new303_independent_dates',helper_path)
    helper=importlib.util.module_from_spec(loader);sys.modules[loader.name]=helper;loader.loader.exec_module(helper)
    financial,reader,proof=helper.prepare_financial_adapter()  # Compile only, never call the reader/audit.
    assert proof['period']==('303D',research.START,research.END,303,436320)
    assert proof['only_changed_anchor']=='window_reader.expected date dictionary'
    assert proof['financial_functions_executed'] is False and proof['market_arrays_read'] is False
    assert reader.__globals__['audit_case'] is financial.audit_case