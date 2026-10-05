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


def half_hold_targets(bars, decisions, *, symbols=shared.SYMBOLS):
    """The existing blend's HOLD leg alone, in one full-capital wallet.

    This is a component removal control, not a fitted volatility target or
    a rescaling of old NAV. Signals, eligibility and past risk are unchanged.
    """
    frame, meta = hold.fixed_targets(bars, decisions, 'LONG_ONLY', symbols=symbols,
        allocation='EQUAL', annual_vol_target=.10)
    frame=frame.with_columns(pl.col('target_weight')*.5,pl.col('raw_signed_target')*.5)
    for r in meta['risk']:
        r['component_HOLD_unscaled_vol']=r['unscaled_signed_covariance_annual_vol']
        for k in ('unscaled_signed_covariance_annual_vol','net_target_weight','gross_target_weight'):r[k]*=.5
    meta.update(strategy_id='COIN_HALF_HOLD10_COMPONENT_REMOVAL_CONTROL',
        rules=dict(meta['rules'],after_component_risk_weight=.5,donchian_weight=0,
            component_volatility_budget=.10,full_shared_capital=True,weights_fitted=False),
        attribution_limit='REMOVES_EXIT10_COMPONENT_NOT_MATCHED_REALIZED_RISK',
        account_NAVs_scaled_or_averaged=False)
    return frame,meta


def fixed_targets(bars, decisions, mode='LONG_ONLY', *, symbols=shared.SYMBOLS,
                  eligible_by_decision=None, allocation=ALLOCATION,
                  signal_interval_minutes=1440, risk_bars=None, trend_filter_interval_minutes=None):
    shared.require(mode == 'LONG_ONLY' and allocation == ALLOCATION,
        'Only the predeclared half HOLD10 / half ACTIVE_EQUAL EXIT10 target blend')
    symbols = shared.symbol_order(symbols)
    common = dict(symbols=symbols, eligible_by_decision=eligible_by_decision)
    if signal_interval_minutes == 1440:
        h, hm = hold.fixed_targets(bars, decisions, mode, allocation='EQUAL',
            annual_vol_target=.10, **common)
    else:
        shared.require(signal_interval_minutes == 240 and risk_bars is not None,
            'Four-hour blend requires separate daily HOLD/risk bars')
        daily_times = np.unique(np.asarray(decisions, dtype=np.int64)//DAY_US*DAY_US)
        hd, hdm = hold.fixed_targets(risk_bars, daily_times, mode, allocation='EQUAL',
            annual_vol_target=.10, **common)
        positions = {int(t):i for i,t in enumerate(daily_times)}
        carried, carried_risk = [], []
        for t in decisions:
            i = positions[int(t//DAY_US*DAY_US)]
            carried.append(hd.slice(i*len(symbols),len(symbols)).with_columns(
                pl.lit(int(t)).cast(pl.Int64).alias('available_us')))
            r = dict(hdm['risk'][i], decision_us=int(t),
                original_daily_hold_decision_us=int(daily_times[i]))
            carried_risk.append(r)
        h = pl.concat(carried)
        hm = dict(hdm, risk=carried_risk)
    d, dm = donchian.fixed_targets(bars, decisions, mode, allocation='ACTIVE_EQUAL',
        exit_period=10, reentry_period=20, signal_interval_minutes=signal_interval_minutes,
        risk_bars=risk_bars, trend_filter_interval_minutes=trend_filter_interval_minutes, **common)
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
    if signal_interval_minutes == 240:
        meta['strategy_id'] = STRATEGY_ID.replace('_1D_', '_4H_')
        meta['rules'] = dict(RULES, timeframe_minutes=240, hold_timeframe_minutes=1440,
            signal_periods_in_four_hour_bars=True, risk_timeframe_minutes=1440,
            combined_target_refresh_minutes=240, daily_HOLD_target_forward_carried=True,
            donchian_strategy_id=dm['strategy_id'], missing_component_policy='STOP_BLEND_ON_ELIGIBILITY_MISMATCH')
        meta['attribution_limit'] = 'SIGNAL_HORIZON_AND_COMBINED_REBALANCE_CADENCE_CHANGED_NOT_SIGNAL_ONLY'
        for r in risk:
            r.update(daily_risk_close_us=r['decision_us']//DAY_US*DAY_US,
                original_daily_hold_decision_us=r['decision_us']//DAY_US*DAY_US)
    if trend_filter_interval_minutes is not None:
        meta['strategy_id'] += '_DAILY_TREND'
        meta['rules'].update(trend_filter_timeframe_minutes=1440,
            donchian_strategy_id=dm['strategy_id'])
        meta['attribution_limit'] = 'DAILY_ENTRY_FILTER_ONLY_VERSUS_SAME_FOUR_HOUR_CONTROL_NOT_MATCHED_ACTUAL_RISK'
    return frame, meta
