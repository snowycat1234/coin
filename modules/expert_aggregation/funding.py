"""Declared non-native funding stress; inherited Decimal wallet and explicit auditor view."""
from decimal import Decimal as D
from copy import deepcopy
import json,os,tempfile
from pathlib import Path
from quant.bybit_isolated_account import BybitIsolatedAccount
from modules.transformer_v3.isolated_audit import verify

def factor(quantity,rate):
    q,r=D(str(quantity)),D(str(rate))
    return D('2') if q*r>0 else D('.5') if q*r<0 else D('1')

class AdverseFundingAccount(BybitIsolatedAccount):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs);self._pressure_requests={}
    def apply_funding(self,symbol,event_id,event_us,rate,rate_available_us):
        rate=D(str(rate));key=(symbol,event_us);identity=(event_id,str(rate),rate_available_us)
        if key in self._pressure_requests:
            old_identity,old_receipt=self._pressure_requests[key]
            if old_identity!=identity:raise ValueError('Conflicting original funding pressure event')
            return deepcopy(old_receipt)
        quantity=self.positions[symbol].quantity
        f=factor(quantity,rate)
        receipt=super().apply_funding(symbol,event_id,event_us,rate*f,rate_available_us)
        result={**receipt,'original_fraction_rate':str(rate),'effective_fraction_rate':str(rate*f),
                'paid_received_multiplier':str(f),'funding_pressure':'PAYMENTS_X2_RECEIPTS_X0_5'}
        self._pressure_requests[key]=(identity,deepcopy(result));return result

def independent(directory,unit_scale,adverse,scratch):
    directory=Path(directory)
    if not adverse:return verify(directory,('BTCUSDT',),unit_scale)
    funds=json.loads((directory/'funding.json').read_bytes());view=[]
    for r in funds:
        r=dict(r);rate=D(str(r['raw_rate']))*D(str(unit_scale));f=factor(r['quantity'],rate)
        effective=rate*f
        if r.get('owned'):
            if D(r['original_fraction_rate'])!=rate or D(r['effective_fraction_rate'])!=effective or D(r['paid_received_multiplier'])!=f:raise ValueError('Declared adverse funding identity disagreement')
            expected=-D(str(r['quantity']))*D(str(r['mark_price']))*effective
            if abs(float(expected)-r['signed_funding_USDT'])>1e-7:raise ValueError('Independent ownership-signed adverse cash failed')
        r['original_raw_rate']=r['raw_rate'];r['raw_rate']=float(effective/D(str(unit_scale)))
        view.append(r)
    Path(scratch).mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='explicit-effective-rate-audit-',dir=scratch) as temp:
        p=Path(temp)
        for name in ('minute_nav_inventory.parquet','summary.json','trades.json','liquidations.json'):
            os.symlink((directory/name).resolve(),p/name)
        (p/'funding.json').write_text(json.dumps(view,allow_nan=False))
        result=verify(p,('BTCUSDT',),unit_scale)
    result.update(funding_adverse_independent_witness_count=len(funds),
        original_journal_preserved=True,auditor_view='EXPLICIT_EFFECTIVE_RATE_VIEW_AFTER_INDEPENDENT_ORIGINAL_RATE_AND_OWNERSHIP_FACTOR_CHECK',
        native_funding_certified=False)
    return result
