"""One fixed target blend of existing HOLD10 and EXIT10 research recipes.

Both components use the same ordered assets, available bars and covariance.
Their already risk-reduced targets share one wallet; this is not a blend of
independent account NAVs and does not multiply the capital or risk limits.
"""
from __future__ import annotations

import numpy as np
import polars as pl

from scripts.investment import public_sma_perpetual as shared
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import donchian_daily_pool_target as donchian

STRATEGY_ID = 'COIN_HALF_HOLD10_HALF_EXIT10_ACTIVE_EQUAL_1D_USDM_CONFIGURED_POOL_BLEND'
ALLOCATION = 'HALF_HOLD_HALF_ACTIVE_EQUAL_EXIT10'
MODES = ('LONG_ONLY',)
DAY_US = shared.DAY_US
RULES = dict(hold_weight=.5, donchian_weight=.5,
    hold_strategy_id=hold.STRATEGY_ID, donchian_strategy_id=donchian.EXIT10_STRATEGY_ID,
    hold_allocation='EQUAL', donchian_allocation='ACTIVE_EQUAL',
    annual_volatility_target=.10, exit_period=10, reentry_period=20,
    blend_stage='AFTER_COMPONENT_RISK_SCALING_NO_EXTRA_RESCALE',
    separate_component_capital=False, timeframe_minutes=1440,
    completed_daily_eligibility_bars=200, past_covariance_daily_returns=30,
    absolute_target_per_asset=.3, gross_target_cap=.6,
    blend_weights_fitted=False, component_NAVs_averaged=False,
    component_signal_states_independent_of_executed_blended_position=True)


def fixed_targets(bars, decisions, mode='LONG_ONLY', *, symbols=shared.SYMBOLS,
                  eligible_by_decision=None, allocation=ALLOCATION):
    shared.require(mode == 'LONG_ONLY' and allocation == ALLOCATION,
        'Only the predeclared half HOLD10 / half ACTIVE_EQUAL EXIT10 target blend')
    symbols = shared.symbol_order(symbols)
    common = dict(symbols=symbols, eligible_by_decision=eligible_by_decision)
    h, hm = hold.fixed_targets(bars, decisions, mode, allocation='EQUAL',
        annual_vol_target=.10, **common)
    d, dm = donchian.fixed_targets(bars, decisions, mode, allocation='ACTIVE_EQUAL',
        exit_period=10, reentry_period=20, **common)
    keys = ('available_us', 'symbol', 'mode', 'eligibility_reason')
    shared.require(h.columns == d.columns and h.height == d.height and all(
        h[k].to_list() == d[k].to_list() for k in keys),
        'Components must have identical ordered calendar, identity and eligibility')
    values = .5 * h['target_weight'].to_numpy() + .5 * d['target_weight'].to_numpy()
    raw = .5 * h['raw_signed_target'].to_numpy() + .5 * d['raw_signed_target'].to_numpy()
    shared.require(np.isfinite(values).all() and np.all(values >= 0.) and
        np.max(values) <= .3 + 1e-12 and
        np.max(np.sum(np.abs(values.reshape(-1, len(symbols))), axis=1)) <= .6 + 1e-12,
        'A convex target blend preserves the existing absolute and gross caps')
    frame = h.with_columns(pl.Series('target_weight', values), pl.Series('raw_signed_target', raw))
    component_targets = dict(HOLD=h['target_weight'].to_list(), EXIT10=d['target_weight'].to_list())
    component_raw = dict(HOLD=h['raw_signed_target'].to_list(), EXIT10=d['raw_signed_target'].to_list())
    risk = []
    for i, (hr, dr) in enumerate(zip(hm['risk'], dm['risk'], strict=True)):
        shared.require(hr['decision_us'] == dr['decision_us'] and
            hr['symbol_order'] == dr['symbol_order'] == list(symbols) and
            hr['covariance_symbol_order'] == dr['covariance_symbol_order'],
            'Both components must use the same past-only ordered covariance inputs')
        rows = slice(i * len(symbols), (i + 1) * len(symbols))
        risk.append(dict(decision_us=hr['decision_us'], symbol_order=list(symbols),
            covariance_symbol_order=hr['covariance_symbol_order'], eligibility=hr['eligibility'],
            component_HOLD_target=component_targets['HOLD'][rows],
            component_EXIT10_target=component_targets['EXIT10'][rows],
            component_HOLD_raw=component_raw['HOLD'][rows],
            component_EXIT10_raw=component_raw['EXIT10'][rows],
            component_HOLD_unscaled_vol=hr['unscaled_signed_covariance_annual_vol'],
            component_EXIT10_unscaled_vol=dr['unscaled_signed_covariance_annual_vol'],
            covariance_observations=hr['covariance_observations'],
            covariance_assets=hr['covariance_assets'], past_only=True,
            net_target_weight=float(np.sum(values[rows])),
            gross_target_weight=float(np.sum(np.abs(values[rows])))))
    meta = dict(strategy_id=STRATEGY_ID, allocation=ALLOCATION, mode=mode,
        symbols=list(symbols), rules=dict(RULES), risk=risk,
        components=dict(HOLD={k:v for k,v in hm.items() if k != 'risk'},
                        EXIT10={k:v for k,v in dm.items() if k != 'risk'}),
        complete_daily_warmup=200, funding_rates_used_for_signal=False,
        native_Jesse_or_Bybit_execution_replicated=False,
        target_caps_are_not_instantaneous_position_caps=True,
        benchmark_scope='SEEN_DEVELOPMENT_NOT_LONG_TERM_APR',
        sizing_and_execution='COMBINED_TARGET_ONE_SHARED_ACCOUNT_NORMAL_RISK_AND_PAID_FILLS')
    return frame, meta
