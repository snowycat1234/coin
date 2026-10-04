"""Pinned RSI2 long/exit hooks on closed daily configurable-pool targets.

The original class does not prescribe a timeframe. This fixed daily COIN port
retains the official scalar RSI's 240-bar context and replaces upstream sizing
and execution with the existing shared portfolio rules.
"""
from scripts.investment import public_rsi2_adapter as original
from scripts.investment import public_sma_perpetual as shared

STRATEGY_ID = 'COIN_JESSE_RSI2_1D_USDM_CONFIGURED_POOL_ADAPTER'
MODES = ('LONG_ONLY', 'CASH')
DAY_US = shared.DAY_US
PARAMETERS = dict(fast_sma_period=5, slow_sma_period=200, rsi_period=2,
    rsi_ob_threshold=90, rsi_os_threshold=10)
RULES = dict(timeframe_minutes=1440, completed_daily_eligibility_bars=240,
    scalar_candle_window=240, fast_SMA_period=5, slow_SMA_period=200,
    rsi_period=2, long_entry_RSI_maximum=10, original_short_RSI_minimum=90,
    entry_predicate='CURRENT_COMPLETED_CLOSE_GT_SMA200_AND_OFFICIAL_RSI2_LE_10',
    exit_predicate='HELD_LONG_AND_CURRENT_COMPLETED_CLOSE_GT_SMA5',
    equal_policy='PRICE_EQUAL_SMA200_BLOCKS_ENTRY_PRICE_EQUAL_SMA5_HOLDS_POSITION',
    rsi_initialization='OFFICIAL_NONSEQUENTIAL_SCALAR_ON_EACH_LAST240_CLOSED_DAILY_BARS',
    current_completed_day_in_indicators=True, short_entries_allowed=False,
    original_long_entry_and_long_exit_hooks_used=True,
    original_short_and_whole_balance_order_hooks_called=False,
    upstream_timeframe_prescribed=False, close_then_wait_next_daily_decision_to_reenter=True,
    strategy_stop_or_take_profit_added=False,
    past_covariance_daily_returns=30, annual_volatility_target=.10,
    absolute_target_per_asset=.3, gross_target_cap=.6,
    raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',
    inactive_signal_budget_redistributed=False, allocation='EQUAL',
    risk_scaling='ORIGINAL_SIGNED_COVARIANCE_10_PERCENT_SCALE_DOWN_ONLY',
    fresh_flat_each_window=True, missing_or_exited_member_state='RESET_FLAT_KEEP_SYMBOL_IDENTITY',
    native_Jesse_or_Bybit_execution_replicated=False, funding_rates_used_for_signal=False,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED')


def fixed_targets(bars, decisions, mode='LONG_ONLY', *, symbols=shared.SYMBOLS,
                  eligible_by_decision=None, allocation='EQUAL'):
    shared.require(mode in MODES and allocation == 'EQUAL',
        'Fixed daily RSI2 LONG_ONLY/CASH and equal allocation required')
    shared.require(original.SCALAR_CANDLE_WINDOW == 240,
        'Preserved official RSI scalar initialization context required')
    rules = original._load_public_hooks()
    shared.require(rules().vars == PARAMETERS, 'Original fixed RSI2 parameters required')
    frame, meta = shared.fixed_targets(bars, decisions, mode, symbols=symbols,
        direction_factory=rules, eligible_by_decision=eligible_by_decision,
        allocation='EQUAL', completed_bar_count=240)
    for key in ('fast_period', 'slow_period', 'equality_holds_current_position', 'source'):
        meta.pop(key, None)
    meta.update(strategy_id=STRATEGY_ID, rules=dict(RULES), allocation='EQUAL',
        rsi_parameters=dict(PARAMETERS), complete_daily_warmup=240,
        scalar_candle_window=240, scalar_API='OFFICIAL_JESSE_RSI_NONSEQUENTIAL_2D_CANDLES',
        original_long_and_short_and_exit_hooks_reused=False,
        original_long_entry_and_long_exit_hooks_reused=True,
        original_short_and_whole_balance_order_hooks_called=False,
        original_SMA50_200_alpha_used=False, direction_context_is_Jesse_strategy=True,
        original_example_commit='7c91e0a37bf62165790120d730442e4f6eb00364',
        original_indicator_commit='417f8765225e3bfc12043d4b712f19fe15a3c078',
        public_upstream_license='MIT', public_upstream_sha256=dict(original.PINNED_HASHES),
        public_raw_strategy_sha256=original.RAW_STRATEGY_SHA256,
        upstream_timeframe_prescribed=False, fixed_daily_timeframe_is_COIN_adaptation=True,
        original_cancel_entry_hook_called=False,
        sizing_and_pending_order_policy='EXISTING_COIN_SHARED_PORTFOLIO_NOT_JESSE_FULL_BALANCE',
        reused_target_api='scripts/investment/public_sma_perpetual.py:fixed_targets(direction_factory,completed_bar_count=240)',
        benchmark_scope='SEEN_DEVELOPMENT_NOT_LONG_TERM_APR',
        target_caps_are_not_instantaneous_position_caps=True)
    return frame, meta
