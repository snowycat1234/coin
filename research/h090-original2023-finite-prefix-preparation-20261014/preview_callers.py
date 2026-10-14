"""Explicit performance caller copies; single clone-invocation substitutions."""
from copy import deepcopy
from decimal import Decimal as D
from itertools import product
import math
import numpy as np
from native_control import H090NativeControl, S, DAY
from bounded_policy import CapitalGuard, STAGE, ZERO
from preview_prefix import clone_preview_account, install_preview_histories

class PrefixH090NativeControl(H090NativeControl):
    def _atomic_risk_admission(self,args,kwargs):
        t=self.cursor
        context=self.risk_contexts.get(t)
        event=args[3] if len(args)>3 else kwargs.get('event_us')
        if not context or not context['ready'] or type(event) is not int or not t<=event<min(t+DAY,self.end):
            return {'allow_increases':False,'reason':'SOURCE_FRESHNESS_REQUIRED_FOR_INCREASE'}
        # Preview exact charged finance; this does not mutate the real account.
        raw=self.account.engine
        probe=clone_preview_account(raw)
        probe.execute_fill(*args,**kwargs)
        nav=probe.nav()
        if nav<=0:return {'allow_increases':False,'reason':'NONPOSITIVE_ACTUAL_NAV'}
        prices=np.asarray([float(probe.marks[s][-1]['price']) if probe.marks[s]
                           else float(self.daily_prices[s][t]) for s in S])
        endpoints=[]
        for s in S:
            actual=probe.positions[s].quantity
            order=self.pending.get(s)
            target=order['target'] if order is not None else actual
            endpoints.append((actual,target) if target!=actual else (actual,))
        cov=context['covariance']
        worst_gross=worst_asset=worst_sigma=0.
        for point in product(*endpoints):
            w=np.asarray([float(v) for v in point])*prices/float(nav)
            gross=float(np.abs(w).sum());asset=float(np.abs(w).max())
            variance=float(w@cov@w)
            if not math.isfinite(variance) or variance < -1e-15:
                return {'allow_increases':False,'reason':'INVALID_ACTUAL_PENDING_COVARIANCE'}
            sigma=float(np.sqrt(max(variance,0.)))
            worst_gross=max(worst_gross,gross);worst_asset=max(worst_asset,asset);worst_sigma=max(worst_sigma,sigma)
            if gross>.90+1e-12 or asset>.30+1e-12 or sigma>.15+1e-12:
                return {'allow_increases':False,'reason':'SINGLE_OWNER_ACTUAL_PENDING_RISK_ENVELOPE'}
        return {'allow_increases':True,'reason':'PASS_SINGLE_OWNER_ACTUAL_PENDING_CORNER_ENVELOPE',
                'worst_gross':worst_gross,'worst_asset':worst_asset,'worst_annual_vol':worst_sigma}

class PrefixCapitalGuard(CapitalGuard):
    def execute_fill(self, *args, **kwargs):
        fill_id = args[5] if len(args) > 5 else kwargs.get("fill_id")
        if fill_id in self.account.fill_requests:
            # Original identity validation and duplicate replay must precede
            # current planning guards; no new fill occurs in the replay.
            return self.account.execute_fill(*args, **kwargs)
        if kwargs.get("reduce_only") is not True:
            if self.account.free_cash < STAGE.initial_cash_floor:
                return {"status": "POLICY_REJECTED", "reason": "INITIAL_CASH_FLOOR_BREACHED"}
            # The original scheduler fork shares this immutable profile map.
            probe = clone_preview_account(self.account)
            preview = probe.execute_fill(*args, **kwargs)
            margin = sum((p.isolated_balance for p in probe.positions.values()), ZERO)
            if probe.free_cash < STAGE.initial_cash_floor or margin > self.maximum_actual_isolated_margin:
                return {"status": "POLICY_REJECTED", "reason": "SHARED_CAPITAL_OR_RESERVE_CAP"}
            receipt = self.account.execute_fill(*args, **kwargs)
            if receipt != preview or self.account.snapshot() != probe.snapshot():
                raise AssertionError("Exact unchanged-account dry run and commit differ")
            return receipt
        return self.account.execute_fill(*args, **kwargs)

def configure_performance_simulator(sim):
    """Attach only to a newly constructed original CONTROL simulator."""
    if type(sim) is not H090NativeControl:
        raise TypeError("EXACT_ORIGINAL_CONTROL_SIMULATOR_REQUIRED")
    install_preview_histories(sim.account.engine)
    sim.__class__ = PrefixH090NativeControl
    sim.account.capital_guard = PrefixCapitalGuard(sim.account.engine)
    sim.account.risk_admission = sim._atomic_risk_admission
    return sim
