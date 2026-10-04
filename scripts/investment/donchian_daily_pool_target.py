"""Pinned public Donchian entry/filter/exit hooks on shared daily targets.

The upstream class prescribes no timeframe. Daily signals and capped shared
portfolio sizing are explicit COIN adaptations, not native Jesse execution.
"""
from __future__ import annotations

import ast
import hashlib
from collections import namedtuple
from types import SimpleNamespace

import numpy as np

from quant.paths import ROOT
from scripts.investment import public_sma_perpetual as shared

STRATEGY_ID = 'COIN_JESSE_DONCHIAN20_SMA200_1D_USDM_CONFIGURED_POOL_ADAPTER'
EXIT10_STRATEGY_ID = 'COIN_JESSE_DONCHIAN20_SMA200_EXIT10_1D_USDM_CONFIGURED_POOL_VARIANT'
MODES = ('LONG_ONLY', 'CASH')
DAY_US = shared.DAY_US
VENDOR = ROOT / 'third_party/jesse_example_donchian'
PINNED_HASHES = {
    'donchian_original.py': 'fc635b257ad1e12951dc140dae46a63bd37e9abfa5f2d681ef1e754d8ce393fe',
    'donchian_indicator_original.py': 'b7e96ebe3ba476c771a65b353c269a84d02e04587f0d76166c5f322bbbb3a401',
    'LICENSE': '80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d',
    'JESSE_LICENSE': '8985ca8447e233f34397a52fe77989c02e27b8145d43bd8c715ae9c7a96056d4',
}
RULES = dict(timeframe_minutes=1440, completed_daily_eligibility_bars=200,
    donchian_period=20, trend_SMA_period=200, channel_excludes_current_completed_day=True,
    SMA_includes_current_completed_day=True,
    entry_predicate='CLOSE_GT_PREVIOUS20_HIGH_AND_CLOSE_GT_CURRENT_SMA200',
    exit_predicate='HELD_LONG_AND_CLOSE_LT_PREVIOUS20_LOW',
    trend_filter_applies_only_to_entry=True, strict_inequalities=True,
    original_short_entry_is_false=True, short_entries_allowed=False,
    original_long_entry_filter_and_exit_hooks_used=True,
    original_whole_balance_order_hooks_called=False,
    upstream_timeframe_prescribed=False, fixed_daily_timeframe_is_COIN_adaptation=True,
    close_then_wait_next_daily_decision_to_reenter=True,
    strategy_stop_or_take_profit_added=False, pyramiding_added=False,
    past_covariance_daily_returns=30, annual_volatility_target=.10,
    absolute_target_per_asset=.3, gross_target_cap=.6,
    raw_allocation='EQUAL_SHARE_OF_0.6_GROSS_TO_CONFIGURED_ELIGIBLE_MEMBERS',
    inactive_signal_budget_redistributed=False, allocation='EQUAL',
    fresh_flat_each_window=True, missing_or_exited_member_state='RESET_FLAT_KEEP_SYMBOL_IDENTITY',
    native_Jesse_or_Bybit_execution_replicated=False, funding_rates_used_for_signal=False,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED')


def strategy_id(exit_period=20):
    shared.require(type(exit_period) is int and exit_period in (20, 10),
        'Explicit preselected 20 or 10 completed-day exit required')
    return STRATEGY_ID if exit_period == 20 else EXIT10_STRATEGY_ID


def strategy_rules(allocation='EQUAL', exit_period=20):
    strategy_id(exit_period)
    shared.require(allocation in ('EQUAL', 'ACTIVE_EQUAL'), 'Explicit Donchian allocation required')
    rules = dict(RULES)
    if allocation == 'ACTIVE_EQUAL':
        rules.update(raw_allocation='MIN_0.3_0.6_DIVIDED_BY_ACTIVE_ELIGIBLE_SIGNALS',
            inactive_signal_budget_redistributed=True, allocation=allocation,
            active_signal_zero_is_cash=True, clipped_budget_not_redistributed=True)
    if exit_period != 20:
        rules.update(exit_period=exit_period,
            exit_predicate='HELD_LONG_AND_CLOSE_LT_PREVIOUS10_LOW',
            original_long_entry_filter_and_exit_hooks_used=False,
            original_long_entry_filter_hooks_used=True, original_exit_hook_used=False,
            exit_period_is_COIN_adaptation=True)
    return rules


def _load_public_hooks(exit_period=20):
    """Load unchanged pinned source nodes with the small scalar context API."""
    strategy_id(exit_period)
    for name, sha in PINNED_HASHES.items():
        shared.require(hashlib.sha256((VENDOR / name).read_bytes()).hexdigest() == sha,
            'Pinned original MIT Donchian source/license changed: ' + name)
    namespace = dict(np=np, slice_candles=lambda candles, sequential: candles,
        DonchianChannel=namedtuple('DonchianChannel', 'upperband middleband lowerband'))
    indicator = ast.parse((VENDOR / 'donchian_indicator_original.py').read_text())
    functions = [node for node in indicator.body
        if isinstance(node, ast.FunctionDef) and node.name == 'donchian']
    shared.require(len(functions) == 1, 'Exactly the original Donchian indicator required')
    exec(compile(ast.Module(functions, type_ignores=[]),
        str(VENDOR / 'donchian_indicator_original.py'), 'exec'), namespace)
    namespace.update(Strategy=object, utils=None, ta=SimpleNamespace(
        donchian=namespace['donchian'],
        sma=lambda candles, period: float(np.mean(candles[-period:, 2]))
            if len(candles) >= period else np.nan))
    strategy = ast.parse((VENDOR / 'donchian_original.py').read_text())
    classes = [node for node in strategy.body
        if isinstance(node, ast.ClassDef) and node.name == 'Donchian']
    shared.require(len(classes) == 1, 'Exactly the original public Donchian class required')
    exec(compile(ast.Module(classes, type_ignores=[]),
        str(VENDOR / 'donchian_original.py'), 'exec'), namespace)
    original = namespace['Donchian']

    class DailyDirection(original):
        # The shared target API supplies completed-bar price. Upstream reads close.
        @property
        def close(self):
            return self.price

        def should_long(self):
            # Jesse evaluates filters separately; the shared hook API does not.
            return super().should_long() and all(f() for f in self.filters())

    if exit_period == 20:
        return DailyDirection

    class Exit10Direction(DailyDirection):
        def update_position(self):
            lower = namespace['ta'].donchian(self.candles[:-1], period=exit_period).lowerband
            if self.close < lower:
                self.liquidate()

    return Exit10Direction


def fixed_targets(bars, decisions, mode='LONG_ONLY', *, symbols=shared.SYMBOLS,
                  eligible_by_decision=None, allocation='EQUAL', exit_period=20):
    shared.require(mode in MODES and allocation in ('EQUAL', 'ACTIVE_EQUAL'),
        'Fixed daily Donchian LONG_ONLY/CASH and equal allocation required')
    frame, meta = shared.fixed_targets(bars, decisions, mode, symbols=symbols,
        direction_factory=_load_public_hooks(exit_period), eligible_by_decision=eligible_by_decision,
        allocation=allocation, completed_bar_count=200)
    for key in ('fast_period', 'slow_period', 'equality_holds_current_position', 'source'):
        meta.pop(key, None)
    rules = strategy_rules(allocation, exit_period)
    meta.update(strategy_id=strategy_id(exit_period), rules=rules, allocation=allocation,
        original_long_and_short_and_exit_hooks_reused=False,
        original_long_entry_filter_and_exit_hooks_reused=exit_period == 20,
        original_short_entry_is_false=True, original_whole_balance_order_hooks_called=False,
        original_SMA50_200_alpha_used=False, direction_context_is_Jesse_strategy=True,
        original_example_commit='7c91e0a37bf62165790120d730442e4f6eb00364',
        original_indicator_commit='417f8765225e3bfc12043d4b712f19fe15a3c078',
        public_upstream_license='MIT', public_upstream_sha256=dict(PINNED_HASHES),
        upstream_timeframe_prescribed=False, fixed_daily_timeframe_is_COIN_adaptation=True,
        original_cancel_entry_hook_called=False,
        sizing_and_pending_order_policy='EXISTING_COIN_SHARED_PORTFOLIO_NOT_JESSE_FULL_BALANCE',
        reused_target_api='public_sma_perpetual.fixed_targets(direction_factory,completed_bar_count=200)',
        benchmark_scope='SEEN_DEVELOPMENT_NOT_LONG_TERM_APR',
        target_caps_are_not_instantaneous_position_caps=True)
    if exit_period != 20:
        meta.update(exit_period=exit_period, original_exit_hook_reused=False,
            original_long_entry_filter_hooks_reused=True, exit_is_COIN_variant=True)
    return frame, meta
