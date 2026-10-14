"""Explicit H090 config-class conversion; all charged finance stays reviewed."""
from copy import deepcopy
from dataclasses import fields
from decimal import Decimal as D
from bind_sources import load
PORT,ORIGINAL_ACCOUNT,NATIVE,POLICY,COSTS,ORIGINAL_FINANCE,ORIGINAL_TARGETS=load()
from vendor_quant.perpetual_account import PerpetualConfig as VendorConfig


class GuardedAccount:
    """A routing facade. It contains one real, unchanged reviewed Decimal account.

    No finance method is copied, overridden, or approximated. The narrow native
    risk callback is checked before CapitalGuard dry-run/commit; replay goes
    straight to the original receipt identity guard before current policies.
    """
    def __init__(self,account):
        object.__setattr__(self,'engine',account)
        object.__setattr__(self,'capital_guard',POLICY.CapitalGuard(account))
        object.__setattr__(self,'risk_admission',None)

    def __getattr__(self,name):
        return getattr(self.engine,name)

    def __setattr__(self,name,value):
        if name in ('engine','capital_guard','risk_admission'):
            object.__setattr__(self,name,value)
        else:
            setattr(self.engine,name,value)

    def execute_fill(self,*args,**kwargs):
        fill_id=args[5] if len(args)>5 else kwargs.get('fill_id')
        if fill_id in self.engine.fill_requests:
            return self.engine.execute_fill(*args,**kwargs)
        if kwargs.get('reduce_only') is not True:
            if self.risk_admission is None:
                return {'status':'POLICY_REJECTED','reason':'NATIVE_H090_RISK_BINDING_REQUIRED'}
            admission=self.risk_admission(args,kwargs)
            if not admission['allow_increases']:
                return {'status':'POLICY_REJECTED','reason':admission['reason']}
        return self.capital_guard.execute_fill(*args,**kwargs)


def h090_config_from_original(config, cost):
    if type(config) is not ORIGINAL_FINANCE.PerpetualConfig:
        raise ValueError('EXACT_ORIGINAL_CONFIG_CLASS_REQUIRED')
    expected=COSTS.scenario_config(cost)
    if config!=expected or config.max_gross_weight!=D('.6'):
        raise ValueError('EXACT_ORIGINAL_COST_AND_PROFILE_CONFIG_REQUIRED')
    values={f.name:getattr(config,f.name) for f in fields(config)}
    values['max_gross_weight']=D('.90')
    result=VendorConfig(**values)
    if any(getattr(result,k)!=v for k,v in values.items()):
        raise AssertionError('EXPLICIT_H090_CONFIG_CONVERSION_CHANGED_FIELD')
    return result


def h090_factory(cost):
    fixed=deepcopy(cost)
    # The original validates unchanged BASE27/STRESS43 or an explicit approved
    # cost hypothesis, including exact commission+spread+slippage roundtrip.
    COSTS.scenario_config(fixed)
    def factory(config,*,symbols,**kwargs):
        if tuple(symbols)!=POLICY.SYMBOLS:
            raise ValueError('EXACT_CORE5_ACCOUNT_ORDER_REQUIRED')
        vendor=h090_config_from_original(config,fixed)
        engine=POLICY.HighRiskToyAccount(vendor,symbols=tuple(symbols),**kwargs)
        if type(engine.config) is not VendorConfig:
            raise AssertionError('REVIEWED_VENDOR_CONFIG_CLASS_REQUIRED')
        return GuardedAccount(engine)
    return factory


def h090_account_for_cost(cost,symbols=POLICY.SYMBOLS):
    return COSTS.account_for_cost(cost,tuple(symbols),h090_factory(cost))
