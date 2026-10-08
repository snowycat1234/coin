"""Bind caller-owned E6 NPZ arrays without downloading or inventing missing panels.

Field names are explicit in field_map, avoiding guesses about a producer's NPZ
schema. Baseline validation rebuilds the exact original desired -> ramp -> net
target path before any local regret experiment is admitted.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import numpy as np
from scripts.investment.perpetual_directional import DAY,need
from .teacher import DayContext,Proposal,simplex


class BoundE6Inputs:
    REQUIRED=('decision_us','symbol_order','expert_targets','expert_available_us',
              'expert_eligible','past_returns30','market_features','market_feature_names','market_available_us')
    BASELINE=('action_desired_budgets','original_selector_ramped_budgets','original_selector_targets')

    def __init__(self,path,sha256,field_map,binding):
        path=Path(path)
        need(hashlib.sha256(path.read_bytes()).hexdigest()==sha256,'Exact E6 NPZ input bytes')
        need(set(self.REQUIRED)<=set(field_map),'Explicit complete NPZ field map')
        with np.load(path,allow_pickle=False) as f:
            need(all(v in f.files for v in field_map.values()),'Mapped NPZ field is absent; no panel imputation')
            self.arrays={key:f[name].copy() for key,name in field_map.items()}
        self.path=str(path.resolve())
        self.sha256=sha256
        self.binding=dict(binding)
        self.symbols=tuple(self.arrays['symbol_order'].tolist())
        dates=self.arrays['decision_us']
        need(dates.ndim==1 and len(dates)>0 and dates.dtype.kind in ('i','u') and
             dates[0]%DAY==0 and np.all(np.diff(dates)==DAY),'Complete fixed daily input dates')
        self.index={int(d):i for i,d in enumerate(dates)}
        n,s=len(dates),len(self.symbols)
        need(self.arrays['expert_targets'].shape==(n,6,s),'Ordered E6 expert panel')
        need(self.arrays['expert_eligible'].shape in ((n,6),(n,6,s)),'E6 eligibility panel')
        need(self.arrays['past_returns30'].shape==(n,30,s),'Ordered past-only return panel')
        need(self.arrays['market_features'].shape==(n,len(self.arrays['market_feature_names'])),
             'Market feature panel and names')
        need(self.arrays['market_available_us'].shape==(n,),'Per-decision feature availability')
        for a in self.arrays.values():a.flags.writeable=False

    def context_at(self,stamp):
        need(stamp in self.index,'Requested input date absent')
        i=self.index[stamp]
        if 'action_eligible' in self.arrays:
            need(np.all(self.arrays['action_eligible'][i,:6]),'E6 request action unavailable on this date')
        clocks=self.arrays['expert_available_us']
        need(clocks.shape[0]==len(self.index),'Per-date expert availability')
        return DayContext(stamp,int(self.arrays['market_available_us'][i]),
                          tuple(self.arrays['market_features'][i].tolist()),
                          tuple(self.arrays['market_feature_names'].tolist()),
                          self.arrays['expert_targets'][i],clocks[i],self.arrays['past_returns30'][i],self.binding,
                          self.arrays['expert_eligible'][i])

    def validate_original_path(self,mapper,initial_budget,selector_index,*,tolerance=0.):
        """Strict default byte-equal rebuilt budgets/targets; tolerance is explicit.

        Compare preterminal targets, then apply the same mandatory final-day
        zero convention to both rebuilt and stored native paths.
        """
        need(set(self.BASELINE)<=set(self.arrays),'Original selector panels absent; local regret unavailable')
        need(selector_index in (0,1) and 0<=tolerance<=1e-12,'Explicit STATE or MARKET baseline')
        n,s=len(self.index),len(self.symbols)
        need(self.arrays['action_desired_budgets'].shape==(n,8,6) and
             self.arrays['original_selector_ramped_budgets'].shape==(n,2,6) and
             self.arrays['original_selector_targets'].shape==(n,2,s),'Original request/budget/target shapes')
        prior=simplex(initial_budget)
        built=[]
        for i,d in enumerate(self.arrays['decision_us']):
            context=self.context_at(int(d))
            request=self.arrays['action_desired_budgets'][i,6+selector_index]
            proposal=mapper(prior.copy(),request.copy(),context)
            proposal.validate(prior,s)
            expected_budget=self.arrays['original_selector_ramped_budgets'][i,selector_index]
            expected_target=self.arrays['original_selector_targets'][i,selector_index]
            computed_target=np.asarray(proposal.targets) if i<n-1 else np.zeros(s)
            def equal(a,b):
                return np.array_equal(a,b) if tolerance==0 else np.allclose(a,b,rtol=0,atol=tolerance)
            need(equal(np.asarray(proposal.budget),expected_budget),'Existing selector ramp mismatch on date '+str(int(d)))
            need(equal(computed_target,expected_target),'Existing selector net target mismatch on date '+str(int(d)))
            built.append(Proposal('STATE_EXACT' if selector_index==0 else 'MARKET_EXACT',
                                  tuple(request),tuple(expected_budget),tuple(expected_target),
                                  'VALIDATED_SAVED_ORIGINAL_EXACT_FEASIBLE_PROPOSAL'))
            prior=expected_budget.copy()
        self.validated_baseline={int(d):p for d,p in zip(self.arrays['decision_us'],built,strict=True)}
        return dict(status='EXACT' if tolerance==0 else 'EXPLICIT_ABSOLUTE_TOLERANCE',
                    tolerance=tolerance,days=n,selector_index=selector_index,input_sha256=self.sha256,
                    forced_final_day_zero=True)

    def baseline_at(self,sim,context):
        need(hasattr(self,'validated_baseline'),'Validate original selector path before native branching')
        need(tuple(sim.symbols)==self.symbols,'Exact native input symbol order')
        proposal=self.validated_baseline[context.decision_us]
        proposal.validate(sim.budget,len(sim.symbols))
        i=self.index[context.decision_us]
        if i>0:
            previous=self.validated_baseline[int(self.arrays['decision_us'][i-1])].budget
            need(np.array_equal(np.asarray(sim.budget),np.asarray(previous)),
                 'Local comparison is on the actual original selector budget trajectory')
        return proposal
