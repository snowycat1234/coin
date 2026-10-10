"""Fixed past30 long/cash direction using the existing portfolio target API.

This is a COIN mechanism hypothesis, not a reproduction of a public strategy.
The shared module retains calendar, eligibility, state and covariance sizing.
"""
from scripts.investment import public_sma_perpetual as shared

STRATEGY_ID = 'COIN_PAST30_ABSOLUTE_MOMENTUM_LONG_CASH_USDM_CONFIGURED_POOL_ADAPTER'
MODES = ('LONG_ONLY',)
DAY_US = shared.DAY_US
RULES = dict(timeframe_minutes=1440, completed_daily_eligibility_bars=200,
    momentum_completed_daily_return_days=30,
    entry_predicate='CURRENT_COMPLETED_CLOSE_GT_COMPLETED_CLOSE_30_DAYS_EARLIER',
    exit_predicate='HELD_LONG_AND_CURRENT_COMPLETED_CLOSE_LE_COMPLETED_CLOSE_30_DAYS_EARLIER',
    equal_policy='FLAT_ENTRY_BLOCKED_HELD_LONG_EXIT',
    short_entries_allowed=False, direction_is_constant=False,
    close_then_wait_next_daily_decision_to_reenter=True,
    past_covariance_daily_returns=30, annual_volatility_target=.10,
    absolute_target_per_asset=.3, gross_target_cap=.6,
    raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',
    inactive_signal_budget_redistributed=False, allocation='EQUAL',
    risk_scaling='ORIGINAL_SIGNED_COVARIANCE_10_PERCENT_SCALE_DOWN_ONLY',
    fresh_flat_each_window=True, missing_or_exited_member_state='RESET_FLAT_KEEP_SYMBOL_IDENTITY',
    SMA_alpha_or_original_Jesse_hooks_used=False, public_momentum_strategy_replicated=False,
    native_Jesse_or_Bybit_execution_replicated=False, funding_rates_used_for_signal=False,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED')


class _MomentumCashDirection:
    def should_long(self):
        return bool(self.candles[-1, 2] > self.candles[-31, 2])

    def should_short(self):
        return False

    def update_position(self):
        if self.is_long and self.candles[-1, 2] <= self.candles[-31, 2]:
            self.liquidate()


def fixed_targets(bars, decisions, mode='LONG_ONLY', *, symbols=shared.SYMBOLS,
                  eligible_by_decision=None, allocation='EQUAL'):
    shared.require(mode == 'LONG_ONLY' and allocation == 'EQUAL',
        'Fixed momentum LONG_ONLY and original equal allocation required')
    frame, meta = shared.fixed_targets(bars, decisions, mode, symbols=symbols,
        direction_factory=_MomentumCashDirection,
        eligible_by_decision=eligible_by_decision, allocation='EQUAL')
    # The shared path does not load its SMA vendor when this factory is given.
    for key in ('fast_period', 'slow_period', 'equality_holds_current_position',
                'whole_balance_sizing_replaced_by_capped_COINSizing', 'source'):
        meta.pop(key, None)
    meta.update(strategy_id=STRATEGY_ID, rules=dict(RULES), allocation='EQUAL',
        momentum_completed_daily_return_days=30,
        equality_exits_held_long=True, original_long_and_short_and_exit_hooks_reused=False,
        original_SMA_alpha_used=False, direction_context_is_Jesse_strategy=False,
        public_momentum_strategy_replicated=False,
        reused_target_api='scripts/investment/public_sma_perpetual.py:fixed_targets(direction_factory)',
        benchmark_scope='SEEN_DEVELOPMENT_NOT_LONG_TERM_APR',
        target_caps_are_not_instantaneous_position_caps=True)
    return frame, meta
