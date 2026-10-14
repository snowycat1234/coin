"""Normal closing-filter specialization of the shared perpetual account.

Positive closing legs keep the instrument's quantity step and actual capacity,
but are exempt from its declared opening minimum notional. Filters remain
uncertified research assumptions. Historical hash-bound runners require their
original Git revision; this module does not reproduce their AST adapters.
"""
from __future__ import annotations

from quant import perpetual_account as shared

PerpetualConfig = shared.PerpetualConfig
InstrumentProfile = shared.InstrumentProfile
SYMBOLS = shared.SYMBOLS
VERSION = 'usdt_linear_perpetual_closing_exempt_account_v2'
FILTER_PROFILE_ID = 'CLOSING_MIN_NOTIONAL_EXEMPT_CONFIGURED_INSTRUMENT_PROFILE_V2'


class USDTLinearPerpetualAccount(shared.USDTLinearPerpetualAccount):
    """One shared wallet; closing policy is an explicit account identity."""

    VERSION = VERSION

    def __init__(self, config=None, *, symbols=SYMBOLS, instrument_profiles=None,
                 closing_min_notional_exempt=True,
                 cost_context=None,
                 market_type='LINEAR_USDT_PERPETUAL', external_gross_notional=0):
        if closing_min_notional_exempt is not True:
            raise ValueError('closing account requires its exact exemption profile')
        super().__init__(config, symbols=symbols, instrument_profiles=instrument_profiles,
            closing_min_notional_exempt=True, market_type=market_type,
            external_gross_notional=external_gross_notional, cost_context=cost_context)

    def contract_metadata(self):
        metadata = super().contract_metadata()
        metadata.update(filter_profile_id=FILTER_PROFILE_ID,
            opening_min_notional_assumption_USDT=metadata['min_notional_assumption_USDT'],
            min_quantity_assumption=metadata['quantity_step_assumption'],
            native_filters_certified=False, historical_filters_certified=False,
            instrument_API_profile_available=False,
            closing_semantics_source='https://www.bybit.com/en/help-center/article/Futures-Trading-Rules',
            closing_semantics_scope='CURRENT_PUBLIC_RULE_NOT_HISTORICAL_INSTRUMENT_CERTIFICATION')
        return metadata
