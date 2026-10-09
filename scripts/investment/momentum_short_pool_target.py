"""Fixed short-side counterpart of the established 30-day absolute momentum rule."""
from scripts.investment import momentum_cash_pool_target as original
from scripts.investment import public_sma_perpetual as shared

STRATEGY_ID='COIN_PAST30_ABSOLUTE_MOMENTUM_SHORT_CASH_CORE5_DEVELOPMENT'
RULES=dict(original.RULES,
    entry_predicate='CURRENT_COMPLETED_CLOSE_LT_COMPLETED_CLOSE_30_DAYS_EARLIER',
    exit_predicate='HELD_SHORT_AND_CURRENT_COMPLETED_CLOSE_GE_COMPLETED_CLOSE_30_DAYS_EARLIER',
    equal_policy='FLAT_ENTRY_BLOCKED_HELD_SHORT_EXIT',short_entries_allowed=True,long_entries_allowed=False,
    hypothesis_selected_after_seeing_June2024=True)


class _MomentumShortDirection(original._MomentumCashDirection):
    def should_long(self):return False

    def should_short(self):
        return bool(self.candles[-1,2]<self.candles[-31,2])

    def update_position(self):
        if self.is_short and self.candles[-1,2]>=self.candles[-31,2]:self.liquidate()


def fixed_targets(bars,decisions,mode='SHORT_ONLY',*,symbols=shared.SYMBOLS):
    shared.require(mode=='SHORT_ONLY','One fixed30-day short momentum hypothesis required')
    frame,meta=shared.fixed_targets(bars,decisions,mode,symbols=symbols,direction_factory=_MomentumShortDirection,allocation='EQUAL',completed_bar_count=200)
    for key in ('fast_period', 'slow_period', 'equality_holds_current_position',
                'whole_balance_sizing_replaced_by_capped_COINSizing', 'source'):
        meta.pop(key, None)
    meta.update(strategy_id=STRATEGY_ID,rules=dict(RULES),allocation='EQUAL',
        original_long_strategy_unchanged=True,variant='MIRROR_ESTABLISHED_MOMENTUM30_TO_SHORT_CASH',
        original_SMA_alpha_used=False,public_momentum_strategy_replicated=False,
        evidence_role='HYPOTHESIS_SELECTED_AFTER_SEEING_JUNE2024; KNOWN_DEVELOPMENT_NOT_OOS')
    return frame,meta
