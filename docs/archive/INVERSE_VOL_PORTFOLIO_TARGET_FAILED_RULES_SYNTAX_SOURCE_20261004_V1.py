"""Daily constant-long portfolio reference using the normal shared target API.

N configured instruments share .6 raw gross and one account. Past30 covariance
only reduces risk. This remains a development benchmark, not an alpha claim.
"""
from scripts.investment import public_sma_perpetual as shared
STRATEGY_ID='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
INVERSE_STRATEGY_ID='COIN_PAST30_INVERSE_VOL_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
MODES=('LONG_ONLY',)
DAY_US=shared.DAY_US
RULES=dict(timeframe_minutes=1440,completed_daily_eligibility_bars=200,
    past_covariance_daily_returns=30,annual_volatility_target=.10,
    absolute_target_per_asset=.3,gross_target_cap=.6,direction_is_constant=True,
    raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',
    SMA_alpha_or_original_Jesse_hooks_used=False)
INVERSE_VOL_RULES={**RULES,
    raw_allocation='0.6_TIMES_NORMALIZED_INVERSE_PAST30_SAMPLE_DAILY_VOLATILITY_THEN_ASSET_CLIP_0.3',
    allocation='INVERSE_VOL_30D',allocation_sample_std_ddof=1,
    allocation_returns='PAST30_COMPLETED_SIMPLE_DAILY_RETURNS_NOT_ANNUALIZED',
    clipped_budget_redistributed=False,
    zero_nonfinite_or_missing_member_volatility='WHOLE_PORTFOLIO_FLAT_UNKNOWN_NO_REDISTRIBUTION',
    risk_scaling='ORIGINAL_SIGNED_COVARIANCE_10_PERCENT_SCALE_DOWN_ONLY',
    equal_risk_contribution_or_return_optimization=False)
signed_risk_weights=shared.signed_risk_weights

class _ConstantLongDirection:
    def should_long(self):return True
    def should_short(self):return False
    def update_position(self):return None

def fixed_targets(bars,decisions,mode='LONG_ONLY',*,symbols=shared.SYMBOLS,
                  eligible_by_decision=None,allocation='EQUAL'):
    shared.require(mode=='LONG_ONLY','Constant-long reference mode required')
    frame,meta=shared.fixed_targets(bars,decisions,mode,symbols=symbols,
        direction_factory=_ConstantLongDirection,eligible_by_decision=eligible_by_decision,
        allocation=allocation)
    for key in ('fast_period','slow_period','equality_holds_current_position','close_then_wait_next_daily_decision_to_reenter'):
        meta.pop(key,None)
    meta.update(strategy_id=STRATEGY_ID if allocation=='EQUAL' else INVERSE_STRATEGY_ID,
        rules=dict(RULES if allocation=='EQUAL' else INVERSE_VOL_RULES),
        original_long_and_short_and_exit_hooks_reused=False,
        original_SMA_alpha_used=False,direction_context_is_Jesse_strategy=False,
        funding_rates_used_for_signal=False,benchmark_scope='SEEN_DEVELOPMENT_NOT_LONG_TERM_APR',
        target_caps_are_not_instantaneous_position_caps=True)
    if allocation!='EQUAL':meta['allocation']=allocation
    return frame,meta
