"""Fixed public SMA50/200 long-flat mechanism control for a configured pool.

The teaching example does not represent the strongest open-source strategies.
"""
from scripts.investment import public_sma_perpetual as shared
from scripts.investment import vol_managed_perpetual_target as hold

STRATEGY_ID = 'COIN_JESSE_SMA50_200_1D_USDM_CONFIGURED_POOL_ADAPTER'
MODES = ('LONG_ONLY',)
RULES = dict(hold.RULES, direction_is_constant=False,
    SMA_alpha_or_original_Jesse_hooks_used=True, fast_SMA_period=50, slow_SMA_period=200,
    SMA_includes_current_completed_day=True, entry_predicate='FAST_GT_SLOW_NOT_CROSS_EVENT',
    exit_predicate='HELD_LONG_AND_FAST_LT_SLOW', equal_policy='HOLD_CURRENT_STATE',
    close_then_wait_next_daily_decision_to_reenter=True,
    inactive_signal_budget_redistributed=False, allocation='EQUAL',
    fresh_flat_each_window=True, native_Jesse_or_Bybit_execution_replicated=False,
    funding_rates_used_for_signal=False,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED')


def fixed_targets(bars, decisions, mode='LONG_ONLY', *, symbols=shared.SYMBOLS,
                  eligible_by_decision=None, allocation='EQUAL'):
    shared.require(mode == 'LONG_ONLY' and allocation == 'EQUAL',
        'Fixed SMA pool LONG_ONLY and original equal allocation required')
    # Omitting direction_factory loads the pinned original SMACrossover hooks.
    frame, meta = shared.fixed_targets(bars, decisions, mode, symbols=symbols,
        eligible_by_decision=eligible_by_decision, allocation='EQUAL')
    meta.update(strategy_id=STRATEGY_ID, rules=dict(RULES), allocation='EQUAL',
        original_SMA_alpha_used=True, direction_context_is_Jesse_strategy=True,
        benchmark_scope='SEEN_DEVELOPMENT_NOT_LONG_TERM_APR',
        target_caps_are_not_instantaneous_position_caps=True,
        teaching_strategy_scope='MECHANISM_CONTROL_NOT_REPRESENTATIVE_OF_STRONG_OPEN_SOURCE_STRATEGIES')
    return frame, meta
