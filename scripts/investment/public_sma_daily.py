"""D038 original public SMA50/200 hooks on the accepted daily target loop.

Long-only COIN port: the original comparison hooks are preserved, while the
original whole-balance/short sizing and Jesse execution engine are not used.
"""
from __future__ import annotations
import ast
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import polars as pl
from quant.paths import ROOT
from scripts.investment import public_donchian_daily as prior
from scripts.investment import public_long_development_adapter as reuse

STRATEGY_ID = 'COIN_JESSE_SMA50_200_1D_SPOT_ADAPTER'
DAY_US, MINUTE_US = prior.DAY_US, prior.MINUTE_US
VENDOR = ROOT / 'third_party/jesse_example_smacrossover'
PINNED_HASHES = {
    'smacrossover_original.py':'453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae',
    'LICENSE':'80d873148413a3eb2f96bbe22657bf57ae42046e4d95e81852109c5f3a949d2d'}
PRIOR_SHA256 = '82796e9dac68089a24a6d4bd61c561672043e446c806cbe87a6737a459d35c4a'
RULES = dict(timeframe_minutes=1440,fast_SMA_period=50,slow_SMA_period=200,
    SMA_includes_current_completed_day=True,entry_predicate='FAST_GT_SLOW_NOT_CROSS_EVENT',
    exit_predicate='HELD_LONG_AND_FAST_LT_SLOW',equal_policy='HOLD_CURRENT_STATE',
    long_only=True,per_symbol_target=.3,fresh_flat_each_scoring_period=True,
    warmup_positions=False,day_close_equals_decision_permitted=True,
    daily_availability='EXCLUSIVE_UTC_DAY_CLOSE_PROXY_NOT_PUBLICATION_CERTIFIED',
    missing_policy='WHOLE_PAIRED_PERIOD_NOT_EVALUABLE_NO_RETROACTIVE_TARGET_ZEROING')
calendar_array, daily_view = prior.calendar_array, prior.daily_view


class _StrategyContext:
    is_long = False
    is_short = False
    def filters(self):
        return []  # Jesse Strategy default; original class has no custom filter.


def sma(candles,period=200,sequential=False):
    """Official Polars rolling kernel supplies the original ta.sma scalar API."""
    prior.common.require(type(period) is int and period in (50,200) and sequential is False,
        'Only fixed original50/200 nonsequential SMA context')
    values = pl.Series(np.asarray(candles)[:,2])
    if len(values)<period: return np.nan
    value = values.rolling_mean(window_size=period,min_samples=period)[-1]
    return np.nan if value is None else float(value)


def _load_public_hooks():
    for name,digest in PINNED_HASHES.items():
        prior.common.require(reuse.native.file_sha(VENDOR/name)==digest,'Pinned original MIT SMA source/license changed')
    tree = ast.parse((VENDOR/'smacrossover_original.py').read_text())
    classes = [node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='SMACrossover']
    prior.common.require(len(classes)==1,'Exactly the original public SMACrossover class required')
    namespace = dict(Strategy=_StrategyContext,ta=SimpleNamespace(sma=sma),utils=None)
    exec(compile(ast.fix_missing_locations(ast.Module(classes,type_ignores=[])),
        str(VENDOR/'smacrossover_original.py')+'<COIN-long-only-context>','exec'),namespace)
    return namespace['SMACrossover']


def _target_change(node,changes):
    return reuse.native._replace(node,changes,'D038_ORIGINAL_HOOK_LONG_SHORT_STATE_CONTEXT',
        'rules.close = float(candles[index,2])',
        'rules.close = float(candles[index,2])\nrules.is_long = held\nrules.is_short = False')


def fixed_targets(daily_bars,calendar):
    prior.common.require(reuse.native.file_sha(ROOT/'scripts/investment/public_donchian_daily.py')==PRIOR_SHA256,
        'Preserved accepted daily eligibility/state loop required')
    changes = []
    environment = reuse.namespace(prior,('fixed_targets',),dict(STRATEGY_ID=STRATEGY_ID,RULES=RULES,
        public=SimpleNamespace(_load_public_hooks=_load_public_hooks,PINNED_HASHES=PINNED_HASHES)),changes,_target_change)
    plan = environment['fixed_targets'](daily_bars,calendar)
    plan.receipt.update(SMA_kernel='OFFICIAL_POLARS_ROLLING_MEAN_SCALAR_LAST50_LAST200',
        preserved_daily_loop_sha256=PRIOR_SHA256,target_loop_derivation=changes,
        original_short_and_whole_balance_sizing_transplanted=False,
        source_hashes={'scripts/investment/public_sma_daily.py':reuse.native.file_sha(Path(__file__)),
            'scripts/investment/public_donchian_daily.py':PRIOR_SHA256})
    return plan
