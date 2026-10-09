"""Fixed short-only20/10 Donchian hypothesis, without a trend filter.

Explicit COIN variant of the established long/cash expert. The unchanged MIT
channel kernel, shared200-bar eligibility, EQUAL sizing and risk mapper are
reused. This variant was selected after seeing June2024; development only.
"""
from scripts.investment import donchian_daily_pool_target as baseline
from scripts.investment import public_sma_perpetual as shared
from scripts.investment.cta_classics import channel_kernel

STRATEGY_ID = 'COIN_DONCHIAN20_EXIT10_SHORT_ONLY_NO_TREND_FILTER_CORE5_DEVELOPMENT'
RULES = dict(timeframe_minutes=1440, completed_daily_eligibility_bars=200,
    entry_period=20, exit_period=10, channel_excludes_current_completed_day=True,
    entry_predicate='FLAT_AND_CLOSE_LT_PREVIOUS20_LOW',
    exit_predicate='HELD_SHORT_AND_CLOSE_GT_PREVIOUS10_HIGH',
    entry_crossing_semantics='STRICT_COMPLETED_CLOSE_OUTSIDE_PRIOR_CHANNEL; NO_EXTRA_PREVIOUS_CLOSE_CROSS_TEST',
    trend_filter=False, strict_inequalities=True, long_entries_allowed=False,
    close_then_wait_next_daily_decision_to_reenter=True, fresh_flat_each_window=True,
    warmup_positions=False, allocation='EQUAL',
    raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',
    inactive_signal_budget_redistributed=False, past_covariance_daily_returns=30,
    annual_volatility_target=.10, absolute_target_per_asset=.3, gross_target_cap=.6,
    funding_rates_used_for_signal=False,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED',
    hypothesis_selected_after_seeing_June2024=True)


def direction_factory():
    kernel = channel_kernel()
    original = baseline._load_public_hooks(exit_period=20)

    class ShortOnlyDirection(original):
        def should_long(self):
            return False

        def should_short(self):
            return self.close < self.donchian.lowerband

        def update_position(self):
            if self.close > kernel(self.candles[:-1], period=10).upperband:
                self.liquidate()

    return ShortOnlyDirection


def fixed_targets(bars, decisions, mode='SHORT_ONLY', *, symbols=shared.SYMBOLS):
    shared.require(mode=='SHORT_ONLY', 'One fixed short-only recipe required')
    frame, meta = shared.fixed_targets(bars, decisions, mode, symbols=symbols,
        direction_factory=direction_factory(), allocation='EQUAL', completed_bar_count=200)
    meta.update(strategy_id=STRATEGY_ID, rules=dict(RULES), allocation='EQUAL',
        original_strategy_short_hook_reused=False, original_strategy_short_hook_is_false=True,
        original_nonsequential_channel_kernel_reused=True,
        original_public_upstream_sha256=dict(baseline.PINNED_HASHES),
        variant='MIRROR20_ENTRY10_EXIT_WITHOUT_SMA200_FILTER',
        evidence_role='POST_JUNE_HYPOTHESIS_SEEN_DEVELOPMENT_NOT_OOS',
        missing_or_exited_member_state='RESET_FLAT_KEEP_SYMBOL_IDENTITY')
    return frame, meta
