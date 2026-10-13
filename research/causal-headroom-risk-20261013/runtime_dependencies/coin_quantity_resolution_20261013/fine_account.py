"""Fine-grid research account: unchanged shared Decimal finance and closing rules."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from freeze_bootstrap import verify as verify_reviewed_freeze

verify_reviewed_freeze()

from scripts.investment.perpetual_closing_exempt_account import (
    InstrumentProfile, USDTLinearPerpetualAccount,
)

HERE = Path(__file__).resolve().parent
VERSION = "conditional_shared_default_fine_grid_sensitivity_v1"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")


def profile_sha() -> str:
    return hashlib.sha256((HERE / "FINE_PROFILE.json").read_bytes()).hexdigest()


def profiles(symbols=SYMBOLS):
    declaration = json.loads((HERE / "FINE_PROFILE.json").read_text())
    if tuple(symbols) != tuple(declaration["symbols"]):
        raise ValueError("Frozen CORE5 symbol order differs")
    step = declaration["quantity_step_base_asset"]
    minimum = declaration["opening_min_notional_USDT"]
    if (step != "0.00000001" or minimum != "10"
            or declaration["closing_min_notional_exempt"] is not True
            or declaration["assumed_min_quantity_base_asset"] != step):
        raise ValueError("Fine-grid research declaration changed")
    requested = InstrumentProfile(quantity_step=step, min_notional=minimum)
    if requested != InstrumentProfile():
        raise ValueError("The fine-grid profile no longer matches the shared-account default")
    return {symbol: requested for symbol in symbols}


class FineGridAccount(USDTLinearPerpetualAccount):
    VERSION = VERSION

    def __init__(self, config=None, *, symbols=SYMBOLS, instrument_profiles=None,
                 closing_min_notional_exempt=True, **kwargs):
        wanted = profiles(symbols)
        if closing_min_notional_exempt is not True:
            raise ValueError("Closing exemption is frozen true")
        if instrument_profiles is not None:
            actual = {s: InstrumentProfile(**p) if isinstance(p, dict) else p
                      for s, p in instrument_profiles.items()}
            if actual != wanted:
                raise ValueError("Fine-grid profile mismatch")
        super().__init__(config, symbols=symbols, instrument_profiles=wanted,
                         closing_min_notional_exempt=True, **kwargs)

    def contract_metadata(self):
        metadata = super().contract_metadata()
        metadata.update(filter_profile_id="SHARED_ACCOUNT_DEFAULT_FINE_1E8_SENSITIVITY_V1",
                        quantity_profile_SHA256=profile_sha(),
                        min_quantity_by_symbol={s: "0.00000001" for s in self.symbols},
                        quantity_minimum_rule="MIN_QTY_EQUALS_STEP_ASSUMED_FOR_SENSITIVITY",
                        historical_filters_certified=False, native_filters_certified=False)
        return metadata
