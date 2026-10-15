"""Predeclared same-budget diagnostics from saved native minute observations.

This is reporting only. It never changes targets, positions, costs or returns.
No post-hoc return scaling or realized-risk-matched excess is computed.
"""
from collections import Counter
import numpy as np
import frozen_grid as g

BREACH_NUMERICAL_TOLERANCE = 1e-10


def risk_diagnostics(values, columns, decisions, covariance, targets, tier_name, receipts):
    data=np.asarray(values);names=list(columns)
    def column(name):return data[:,names.index(name)]
    tier=g.tier_named(tier_name)
    if data.ndim!=2 or len(data)==0 or not np.isfinite(data).all():
        raise ValueError('FINITE_NONEMPTY_NATIVE_MINUTE_REPORT_REQUIRED')
    clocks=column('close_us').astype(np.int64)
    if not np.array_equal(clocks,np.arange(clocks[0],clocks[0]+len(clocks)*g.DAY//1440,g.DAY//1440,dtype=np.int64)):
        raise ValueError('CONTIGUOUS_NATIVE_MINUTE_REPORT_REQUIRED')
    nav=column('nav')
    if (nav<=0).any():raise ValueError('POSITIVE_NAV_REQUIRED_FOR_WEIGHT_VOL_DIAGNOSTICS')
    weights=np.column_stack([column(s+'_signed_weight') for s in g.SYMBOLS])
    di=np.searchsorted(decisions,clocks-1,side='right')-1
    if (di<0).any() or (di>=len(covariance)).any():raise ValueError('PAST_ONLY_BOUND_COVARIANCE_REQUIRED')
    forecast=np.empty(len(data))
    # Avoid materializing a full year of repeated5x5 matrices.
    for index in np.unique(di):
        mask=di==index;w=weights[mask]
        forecast[mask]=np.sqrt(np.maximum(0,np.einsum('ij,jk,ik->i',w,covariance[index],w)))
    excess=np.maximum(0,forecast-tier.annual_vol_target)
    end_indices=np.arange(1439,len(data),1440)
    daily_nav=np.r_[10000.,nav[end_indices]]
    daily_returns=daily_nav[1:]/daily_nav[:-1]-1
    reason_counts=Counter();selections=Counter();capital_reasons=Counter()
    for receipt in receipts:
        if 'fraction' in receipt:selections[str(receipt['fraction'])]+=1
        for outcome in [receipt]+receipt.get('evaluations',[]):
            if not outcome.get('allowed',True):
                reason=str(outcome.get('reason','UNSPECIFIED'))
                reason_counts[reason]+=1
                if any(word in reason.upper() for word in ('CAPITAL','CASH','MARGIN')):
                    capital_reasons[reason]+=1
    gross=column('gross_weight');asset=np.abs(weights)
    raw_gross=np.sum(np.abs(targets),axis=1)
    cash=column('free_cash');margin=column('isolated_balance')
    return {'schema':'SAME_NOMINAL_BUDGET_NATIVE_OBSERVED_RISK_REPORT_V1',
        'observation_count':len(data),'complete_calendar_days':len(end_indices),
        'observation':'POST_TRANSITION_MINUTE_CLOSE; INTRAMINUTE_MDD_REPORTED_SEPARATELY',
        'gross_exposure_max':float(gross.max()),'gross_exposure_mean':float(gross.mean()),
        'asset_exposure_absolute_max':float(asset.max()),
        'asset_exposure_absolute_mean_by_symbol':dict(zip(g.SYMBOLS,asset.mean(axis=0).tolist())),
        'forecast_annual_volatility_max':float(forecast.max()),
        'forecast_annual_volatility_mean':float(forecast.mean()),
        'nominal_annual_volatility_budget':tier.annual_vol_target,
        'forecast_volatility_breach_minutes':int(np.sum(excess>BREACH_NUMERICAL_TOLERANCE)),
        'forecast_volatility_breach_max_absolute':float(excess.max()),
        'forecast_volatility_breach_max_relative_to_budget':float(excess.max()/tier.annual_vol_target),
        'breach_numerical_tolerance':BREACH_NUMERICAL_TOLERANCE,
        'realized_daily_simple_return_annual_volatility':float(daily_returns.std(ddof=1)*np.sqrt(365)) if len(daily_returns)>1 else None,
        'realized_volatility_formula':'std(ddof1, complete daily NAV simple returns including initial10000)*sqrt365',
        'raw_target_gross_max':float(raw_gross.max()),'raw_target_gross_mean':float(raw_gross.mean()),
        'positive_raw_target_minus_actual_gross_mean':float(np.maximum(0,raw_gross[di]-gross).mean()),
        'exposure_shortfall_is_not_attributed_to_capital_alone':True,
        'minimum_observed_free_cash_USDT':float(cash.min()),
        'maximum_observed_isolated_margin_USDT':float(margin.max()),
        'minutes_observed_free_cash_below1000':int(np.sum(cash<1000-1e-8)),
        'minutes_observed_margin_above8500':int(np.sum(margin>8500+1e-8)),
        'capital_limits_apply_to_risk_increases_not_continuous_marked_state':True,
        'guard_selection_counts':dict(selections),
        'guard_rejected_candidate_reason_counts':dict(reason_counts),
        'guard_named_capital_rejection_reason_counts_not_exhaustive':dict(capital_reasons),
        'exact_capital_binding_count':'NOT_IDENTIFIABLE_FROM_FROZEN_COMPACT_RECEIPTS',
        'capital_count_qualification':'Compact rejected-corner reasons may combine gross/asset/vol/capital failures. No named capital reason does not imply no capital binding. Exposure shortfall is not capital-attributed.',
        'binding_reason_counts_include_repeated_candidate_previews_not_unique_fills':True,
        'riskmatched_excess_method':'NOT_PREREGISTERED_NOT_CLAIMED',
        'comparison_role':'SAME_NOMINAL_BUDGET_WITH_OBSERVED_RISK_QUALIFICATION'}
