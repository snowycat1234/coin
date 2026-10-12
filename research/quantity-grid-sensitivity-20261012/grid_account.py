"""Existing financial methods, one immutable assumed integer-lot profile."""
import hashlib,json
from pathlib import Path
from scripts.investment.perpetual_closing_exempt_account import USDTLinearPerpetualAccount as Fine,InstrumentProfile
HERE=Path(__file__).resolve().parent
def profile():return json.loads((HERE/'QUANTITY_PROFILE.json').read_text())
def profile_sha():return hashlib.sha256((HERE/'QUANTITY_PROFILE.json').read_bytes()).hexdigest()
def profiles(symbols):
    rows=profile()['rows'];assert set(symbols)==set(rows),'Frozen CORE5 quantity profile'
    return {s:InstrumentProfile(quantity_step=rows[s]['quantity_step'],min_notional='10') for s in symbols}
class QuantityGridAccount(Fine):
    VERSION='conditional_btc_anchored_quantity_grid_sensitivity_v1'
    def __init__(self,config=None,*,symbols=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT'),instrument_profiles=None,**kwargs):
        wanted=profiles(symbols)
        if instrument_profiles is not None:
            actual={s:InstrumentProfile(**p) if isinstance(p,dict) else p for s,p in instrument_profiles.items()}
            if actual!=wanted:raise ValueError('Frozen quantity profile mismatch')
        super().__init__(config,symbols=symbols,instrument_profiles=wanted,**kwargs)
    def contract_metadata(self):
        m=super().contract_metadata();m.update(filter_profile_id='BTC_EXAMPLE_PREP1_DECADE_GRID_SENSITIVITY_V1',quantity_profile_SHA256=profile_sha(),min_quantity_by_symbol={s:str(p.quantity_step) for s,p in self.instrument_profiles.items()},quantity_minimum_rule='MIN_QTY_EQUALS_STEP_POSITIVE_INTEGER_LOTS_ASSUMED',historical_filters_certified=False,native_filters_certified=False)
        return m
