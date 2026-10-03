"""UNRUN D044 target draft: constant long beta through the frozen causal risk loop.

This is a COIN USDT-linear-perpetual benchmark, not SMA alpha, Jesse execution,
Spot EWMA buy-and-hold, or a qualified investment candidate. The original daily
eligibility/calendar/availability and covariance kernel are reused unchanged.
"""
from __future__ import annotations

import hashlib
from types import SimpleNamespace

from quant.paths import ROOT
from scripts.investment import public_sma_perpetual as shared
from scripts.investment import public_long_development_adapter as private

STRATEGY_ID = 'COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
MODES = ('LONG_ONLY',)
DAY_US = shared.DAY_US
PINS = {
    'scripts/investment/public_sma_perpetual.py':
        'c90a9d383fe3365681bfdd5772c0f8a9a8977d57e423627b9159098ce25f30df',
    'scripts/investment/public_long_development_adapter.py':
        '15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f',
}
RULES = {
    'raw_signed_target_by_symbol': {'BTCUSDT': .3, 'ETHUSDT': .3},
    'mode': 'LONG_ONLY',
    'timeframe_minutes': 1440,
    'completed_daily_eligibility_bars': 200,
    'past_covariance_daily_returns': 30,
    'annual_volatility_target': .10,
    'absolute_target_per_asset': .3,
    'gross_target_cap': .6,
    'direction_is_constant': True,
    'SMA_alpha_or_original_Jesse_hooks_used': False,
    'Spot_EWMA_strategy_replicated': False,
    'new_account_or_financial_engine_implemented': False,
}
# Exact public callable alias; no covariance/scaler or risk implementation here.
signed_risk_weights = shared.signed_risk_weights


class _ConstantLongDirection:
    """Direction-only context consumed by the frozen eligibility/state loop."""
    def should_long(self):
        return True

    def should_short(self):
        return False

    def update_position(self):
        return None


def _private_target():
    for relative, expected in PINS.items():
        path = ROOT / relative
        shared.require(hashlib.sha256(path.read_bytes()).hexdigest() == expected,
            'D044 frozen risk/calendar/namespace source bytes changed: ' + relative)
    derivation = []
    direction = SimpleNamespace(_load_public_hooks=lambda: _ConstantLongDirection,
        PINNED_HASHES=dict(PINS))
    environment = private.namespace(shared, ('fixed_targets',),
        {'MODES': MODES, 'public': direction}, derivation)
    shared.require(len(derivation) == 1
        and derivation[0]['original_AST_sha256'] == derivation[0]['derived_AST_sha256']
        and derivation[0]['changes'] == [], 'D044 reuses the complete unchanged target-function AST')
    shared.require(environment['signed_risk_weights'] is shared.signed_risk_weights,
        'D044 must call the original signed covariance kernel')
    return environment['fixed_targets'], derivation


def fixed_targets(bars, decisions, mode='LONG_ONLY'):
    """Same input/output schema and strict eligibility as the original controller.

    At every eligible closed UTC day raw directions are +.3/+ .3. The original
    past30 covariance downscales them; no signal threshold or future funding is
    used. Fresh indicator state starts at the first scoring decision, never
    during warmup. Native timing/fills/fees/position drift remain caller duties.
    """
    shared.require(mode == 'LONG_ONLY', 'D044 is one fixed LONG_ONLY benchmark')
    target, receipt = _private_target()
    frame, metadata = target(bars, decisions, mode)
    for key in ('fast_period', 'slow_period', 'equality_holds_current_position',
            'close_then_wait_next_daily_decision_to_reenter'):
        metadata.pop(key, None)
    metadata.update(strategy_id=STRATEGY_ID, source=dict(PINS), rules=dict(RULES),
        raw_direction='ALWAYS_LONG_BTC_AND_ETH_THEN_FROZEN_PAST30_COVARIANCE',
        original_long_and_short_and_exit_hooks_reused=False,
        original_SMA_alpha_used=False, Spot_EWMA_strategy_replicated=False,
        direction_context_is_Jesse_strategy=False,
        warmup_used_for_indicator_eligibility_only=True,
        risk_kernel='PUBLIC_SMA_PERPETUAL_SIGNED_RISK_WEIGHTS_UNCHANGED',
        namespace_derivation=receipt,
        benchmark_scope='SEPARATE_SEEN_WINDOWS_NOT_LONG_TERM_APR',
        target_caps_are_not_instantaneous_position_caps=True)
    return frame, metadata