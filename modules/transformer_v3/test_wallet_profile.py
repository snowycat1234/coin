from decimal import Decimal
from functools import partial
import numpy as np
import pytest
from quant.perpetual_account import PerpetualConfig
from .wallet import profile_account
from .test_liquidation_engine import observed_window,targets
from scripts.investment import perpetual_directional as engine

def test_half_is_native_gross_constraint_and_keeps_asset_cap_leverage_and_costs():
    cfg=PerpetualConfig();full=profile_account(cfg,profile='FULL',symbols=('BTCUSDT','ETHUSDT'));half=profile_account(cfg,profile='HALF',symbols=('BTCUSDT','ETHUSDT'))
    assert full.config.max_gross_weight==Decimal('.6') and half.config.max_gross_weight==Decimal('.3')
    assert half.config.max_asset_weight==cfg.max_asset_weight and half.config.leverage==cfg.leverage==1
    assert half.config.fee_rate==cfg.fee_rate and half.config.slippage_bps==cfg.slippage_bps
    with pytest.raises(ValueError):profile_account(cfg,profile='POSTHOC_0.4',symbols=('BTCUSDT','ETHUSDT'))

def test_half_native_engine_obeys_lower_gross_with_capacity_and_real_cash_close():
    def half_targets(*args):
        frame,meta=targets(*args)
        return frame.with_columns((frame['target_weight']*.5).alias('target_weight')),meta
    case=engine.simulate(observed_window(False),'LONG_SHORT',engine.COSTS[0],engine.UNITS[0],target_factory=half_targets,
                         account_factory=partial(profile_account,profile='HALF'),persist_cash_close=True)
    assert case['summary']['completed_minutes']==4320 and case['summary']['terminal_cash_realized']
    assert case['summary']['maximum_actual_gross_weight']<.3
