"""Daily constant-long portfolio reference using the normal shared target API.

N configured instruments share .6 raw gross and one account. Past30 covariance
only reduces risk. This remains a development benchmark, not an alpha claim.
"""
from scripts.investment import public_sma_perpetual as shared
STRATEGY_ID='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
MODES=('LONG_ONLY',)
DAY_US=shared.DAY_US
RULES=dict(timeframe_minutes=1440,completed_daily_eligibility_bars=200,
    past_covariance_daily_returns=30,annual_volatility_target=.10,
    absolute_target_per_asset=.3,gross_target_cap=.6,direction_is_constant=True,
    raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',
    SMA_alpha_or_original_Jesse_hooks_used=False)
signed_risk_weights=shared.signed_risk_weights

class _ConstantLongDirection:
    def should_long(self):return True
    def should_short(self):return False
    def update_position(self):return None

def fixed_targets(bars,decisions,mode='LONG_ONLY',*,symbols=shared.SYMBOLS,eligible_by_decision=None):
    shared.require(mode=='LONG_ONLY','Constant-long reference mode required')
    frame,meta=shared.fixed_targets(bars,decisions,mode,symbols=symbols,
        direction_factory=_ConstantLongDirection,eligible_by_decision=eligible_by_decision)
    for key in ('fast_period','slow_period','equality_holds_current_position','close_then_wait_next_daily_decision_to_reenter'):
        meta.pop(key,None)
    meta.update(strategy_id=STRATEGY_ID,rules=dict(RULES),
        original_long_and_short_and_exit_hooks_reused=False,
        original_SMA_alpha_used=False,direction_context_is_Jesse_strategy=False,
        funding_rates_used_for_signal=False,benchmark_scope='SEEN_DEVELOPMENT_NOT_LONG_TERM_APR',
        target_caps_are_not_instantaneous_position_caps=True)
    return frame,meta
