"""One-step native oracle at continuous wallet states, with honest action scope."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import time
from typing import Callable
import numpy as np
from scripts.investment.perpetual_directional import DAY, need
from scripts.investment.public_sma_perpetual import signed_risk_weights

SCHEMA='NATIVE_NEXT_DAY_ACTION_TEACHER_V1'
E6=('CASH','VOL_HOLD','SIGNED_SMA50_200','DONCHIAN_EXIT10','CSMOM21','OOF_LEARNED_RANK')


def vector(value, size, name):
    x=np.asarray(value,dtype=np.float64)
    need(x.shape==(size,) and np.isfinite(x).all(),name+' finite ordered vector')
    return x


def simplex(value):
    x=vector(value,6,'E6 budget')
    need(np.all(x>=0) and abs(float(x.sum())-1)<1e-10,'Six nonnegative budgets sum to one')
    return x


@dataclass(frozen=True)
class DayContext:
    decision_us: int
    available_us: int
    market_features: tuple[float,...]
    market_feature_names: tuple[str,...]
    expert_targets: np.ndarray  # [6, ordered symbols], known at decision.
    expert_available_us: np.ndarray
    past_returns30: np.ndarray
    binding: dict  # Frozen expert identity, exact rank checkpoint and mapper identity.
    expert_eligible: np.ndarray | None=None

    def validate(self,sim):
        need(self.decision_us==sim.cursor and self.decision_us%DAY==0,
             'Fixed daily decision matches current wallet')
        need(self.available_us<=self.decision_us,'Market features must be available at decision')
        need(len(self.market_features)==len(self.market_feature_names) and
             len(set(self.market_feature_names))==len(self.market_feature_names),'Named causal feature schema')
        need(not any(any(word in name.lower() for word in ('winner','reward','regret','label','future','utility'))
                     for name in self.market_feature_names),'Outcome-like input feature rejected')
        need(np.isfinite(self.market_features).all(),'Finite causal features')
        targets=np.asarray(self.expert_targets)
        need(targets.shape==(6,len(sim.symbols)) and np.isfinite(targets).all(),'Ordered E6 expert targets')
        need(np.array_equal(targets[0],np.zeros(len(sim.symbols))),'CASH expert target is zero exposure')
        clocks=np.asarray(self.expert_available_us)
        need(clocks.shape in ((6,),(6,len(sim.symbols))) and clocks.dtype.kind in ('i','u') and
             np.all(clocks<=self.decision_us),'All expert targets causally available')
        returns=np.asarray(self.past_returns30)
        need(returns.shape==(30,len(sim.symbols)) and np.isfinite(returns).all(),'Thirty past ordered returns')
        if self.expert_eligible is not None:
            eligibility=np.asarray(self.expert_eligible)
            need(eligibility.shape in ((6,),(6,len(sim.symbols))) and
                 np.all((eligibility==0)|(eligibility==1)),'Explicit causal expert eligibility')
        need(self.binding.get('expert_order')==list(E6) and
             self.binding.get('rank_checkpoint_sha256') and self.binding.get('mapper_sha256') and
             self.binding.get('market_binding_sha256'),'Frozen expert, rank, mapper and market identities')
        for key in ('rank_checkpoint_sha256','mapper_sha256','market_binding_sha256'):
            digest=self.binding[key]
            need(isinstance(digest,str) and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),
                 'Exact SHA256 identity: '+key)


@dataclass(frozen=True)
class Proposal:
    name: str
    request: tuple[float,...]
    budget: tuple[float,...]
    targets: tuple[float,...]
    origin: str

    def validate(self, prior, n_symbols):
        simplex(self.request)
        budget=simplex(self.budget)
        need(np.abs(budget-simplex(prior)).sum()<=.1+1e-10,'Every candidate obeys daily L1<=.1')
        targets=vector(self.targets,n_symbols,'Native target')
        need(np.abs(targets).sum()<=.6+1e-10 and np.abs(targets).max()<=.3+1e-10,
             'Existing gross and per-asset target caps')


Mapper=Callable[[np.ndarray,np.ndarray,DayContext],Proposal]


def linear_ramp_risk_mapper(prior,request,context):
    """Executable reference adapter; bind/replace with the current E6 mapper.

    Production must check its outputs against saved selector ramped budgets and
    targets before using it. No assertion of equivalence to unavailable E6 code.
    """
    prior,request=simplex(prior),simplex(request)
    change=request-prior
    l1=float(np.abs(change).sum())
    budget=prior+change*min(1.,.1/l1) if l1 else prior.copy()
    target,_=signed_risk_weights(budget@context.expert_targets,context.past_returns30)
    return Proposal('REQUEST',tuple(request),tuple(budget),tuple(target),'LINEAR_L1_RAMP_EXISTING_SIGNED_RISK_MAPPER')


def causal_features(sim,context):
    """Whitelist current market/expert state and wallet state; no future labels."""
    context.validate(sim)
    need(sim.budget is not None,'Explicit current expert budget')
    values=list(context.market_features)
    names=['market.'+name for name in context.market_feature_names]
    for k,expert in enumerate(E6):
        for j,s in enumerate(sim.symbols):
            names.append('expert.'+expert+'.'+s)
            values.append(float(context.expert_targets[k,j]))
    if context.expert_eligible is not None:
        mask=np.asarray(context.expert_eligible)
        if mask.ndim==1:mask=np.repeat(mask[:,None],len(sim.symbols),axis=1)
        for k,expert in enumerate(E6):
            for j,s in enumerate(sim.symbols):
                names.append('expert.'+expert+'.'+s+'.eligible')
                values.append(float(mask[k,j]))
    nav=float(sim.account.nav())
    need(nav>0,'Positive active native wallet NAV')
    scalars=dict(nav_fraction=nav/10000,free_fraction=float(sim.account.free_cash)/nav,
                 unpaid_fraction=float(sim.account.unpaid_liability)/nav,
                 cumulative_fees_fraction=float(sim.account.fees)/nav,
                 cumulative_funding_fraction=float(sim.account.funding_cash)/nav,
                 peak_fraction=sim.peak/10000,drawdown=1-nav/sim.peak,
                 risk_reduction_required=float(sim.account.status=='BOUND_BREACH_REDUCTION_REQUIRED'))
    for key,value in scalars.items():names.append('wallet.'+key);values.append(value)
    for s in sim.symbols:
        p=sim.account.positions[s]
        mark=float(sim.account.marks[s][-1]['price']) if sim.account.marks[s] else float(sim.daily_prices[s][sim.cursor])
        order=sim.pending.get(s)
        fields=dict(signed_weight=float(p.quantity)*mark/nav,margin_fraction=float(p.isolated_balance)/nav,
                    entry_relative=float(p.entry_price)/mark-1 if p.quantity else 0.,
                    blocked=float(s in getattr(sim.account,'blocked_signals',{})),
                    previous_quote_fraction=float((sim.previous_quote or {}).get(s,0))/nav,
                    pending_weight=float(order['target'])*mark/nav if order else 0.,
                    pending_attempts=float(order['attempts']) if order else 0.,
                    pending_age_days=(sim.cursor-order['signal_us'])/DAY if order else 0.,
                    pending_risk=float(order is not None and order['kind']=='RISK_REDUCTION'))
        for key,value in fields.items():names.append('wallet.'+s+'.'+key);values.append(value)
    for k,expert in enumerate(E6):names.append('budget.'+expert);values.append(float(sim.budget[k]))
    need(np.isfinite(values).all(),'Finite state-conditioned causal features')
    return names,values


def replay_candidates(sim,context,mapper,*,baseline=None,state_role='TEACHER_SELF',time_limit_seconds=900):
    """Six native one-hot requests, optionally plus the exact actual proposal.

    Return winner state, distinct six-action labels, and optional local regret.
    A local winner is diagnostic only: the caller advances the baseline branch.
    """
    need(0<time_limit_seconds<=900,'Bounded candidate probe')
    names,features=causal_features(sim,context)
    prior=simplex(sim.budget)
    proposals=[]
    for k,expert in enumerate(E6):
        p=mapper(prior.copy(),np.eye(6)[k],context)
        p.validate(prior,len(sim.symbols))
        need(np.array_equal(np.asarray(p.request),np.eye(6)[k]),'Mapper preserves request identity')
        proposals.append(Proposal(expert,p.request,p.budget,p.targets,p.origin))
    if baseline is not None:
        baseline.validate(prior,len(sim.symbols))
        need(baseline.name not in E6,'Actual proposal has a distinct diagnostic name')
        proposals.append(baseline)
    start=time.monotonic()
    base_hash=sim.state_hash()
    before=float(sim.account.nav())
    first_event=sim.event_cursor
    candidate_rows=[]
    best=None
    actual=None
    mature=min(sim.cursor+DAY,sim.end)
    for index,p in enumerate(proposals):
        need(time.monotonic()-start<time_limit_seconds,'Candidate probe wall-clock budget exceeded')
        clock=time.monotonic()
        branch=sim.fork()
        clone_seconds=time.monotonic()-clock
        branch.budget=list(p.budget)
        result=branch.advance_day(dict(zip(sim.symbols,p.targets,strict=True)))
        complete=result['completed'] and branch.rows_written-sim.rows_written==(min(sim.cursor+DAY,sim.end)-sim.cursor)//60_000_000
        if branch.cursor==branch.end:
            complete=complete and all(pos.quantity==0 for pos in branch.account.positions.values())
        reward=float(branch.account.nav())-before if complete else None
        for raw in branch.funding_journal[first_event:]:
            mature=max(mature,int(raw.get('available_us',raw['event_us'])))
        # The day end dominates all mark/fill clocks; keep explicitly observed
        # publication delays as additional label-maturity constraints.
        mature=max(mature,int(branch.account.clock_us))
        row=dict(name=p.name,request=list(p.request),budget=list(p.budget),targets=list(p.targets),
                 applied_targets=[branch.weights[sim.cursor][s] for s in sim.symbols],
                 origin=p.origin,net_increment_USDT=reward,valid=complete,
                 completion=branch.completion,terminal_cash_realized=all(pos.quantity==0 for pos in branch.account.positions.values()),
                 clone_seconds=clone_seconds,replay_seconds=time.monotonic()-clock-clone_seconds,
                 state_after_hash=branch.state_hash())
        candidate_rows.append(row)
        if complete and (best is None or reward>best[0]):best=(reward,index,branch)
        if baseline is not None and index==6:actual=branch
    need(sim.state_hash()==base_hash,'Candidate replay contaminated source wallet')
    need(best is not None,'No fully evaluable one-day action; preserve diagnostics and stop')
    if baseline is None:
        need(all(r['valid'] for r in candidate_rows),'Incomplete E6 action cannot be used as a complete six-reward teacher label')
    else:need(candidate_rows[6]['valid'],'Actual proposal must be fully evaluable for fair regret')
    valid_e6=[(r['net_increment_USDT'],i) for i,r in enumerate(candidate_rows[:6]) if r['valid']]
    need(valid_e6,'No evaluable E6 action')
    # Stable first-action argmax on ties, used identically by student and teacher.
    e6_winner=max(valid_e6,key=lambda r:r[0])[1]
    e6_rewards=[r['net_increment_USDT'] for r in candidate_rows[:6]]
    sorted_rewards=sorted((r[0] for r in valid_e6),reverse=True)
    row=dict(schema=SCHEMA,decision_us=sim.cursor,interval_end_us=min(sim.cursor+DAY,sim.end),
             label_available_us=mature,feature_available_us=context.available_us,
             state_role=state_role,state_hash=base_hash,binding=context.binding,
             symbol_order=list(sim.symbols),action_order=list(E6),feature_names=names,features=features,
             budget_before=list(prior),wallet_before=sim.account.summary(),candidates=candidate_rows,
             e6_rewards_USDT=e6_rewards,e6_valid=[r['valid'] for r in candidate_rows[:6]],
             e6_winner=e6_winner,e6_gap_USDT=sorted_rewards[0]-sorted_rewards[1] if len(sorted_rewards)>1 else 0.,
             optimal_scope=('NATIVE_GREEDY_1D_E6_SELF_STATE' if baseline is None else 'NATIVE_LOCAL_1D_E6_PLUS_EXACT_ACTUAL'),
             candidate_winner=best[1],one_step_net_increment_USDT=best[0],
             global_native_upper_bound=False,elapsed_seconds=time.monotonic()-start)
    row['terminal_convention']=('FINAL_DAY_ZERO_PLUS_CHARGED_GLOBAL_TERMINAL' if sim.final_day_target_zero
                                else 'CHARGED_GLOBAL_END_MINUS_6_MINUTES')
    row['forced_terminal_day']=bool(sim.final_day_target_zero and sim.cursor+DAY>=sim.end)
    row['optimization_allowed']=not row['forced_terminal_day']
    if row['forced_terminal_day']:
        need(max(r['net_increment_USDT'] for r in candidate_rows)-
             min(r['net_increment_USDT'] for r in candidate_rows)<=1e-9,'Common forced cash day has identical utility')
        row['e6_winner']=None
        row['e6_gap_USDT']=0.
    if baseline is not None:
        regret=best[0]-candidate_rows[6]['net_increment_USDT']
        need(regret>=-1e-9,'Actual candidate guarantees nonnegative local regret')
        row.update(actual_candidate=6,local_regret_USDT=max(0.,regret),
                   regret_is_realizable_equity_curve=False,local_regret_must_not_be_summed_as_NAV=True)
    return row,best[2],actual


def training_state_relabel(sim,context,mapper,*,training_end_us):
    """Optional train-only student-state labeling; never relabel evaluation states."""
    need(sim.cursor<training_end_us and sim.cursor+DAY<=training_end_us,
         'Student-state relabel restricted to training intervals')
    row,winner,_=replay_candidates(sim,context,mapper,state_role='STUDENT_TRAIN_RELABEL')
    need(row['label_available_us']<=training_end_us,'Relabel must mature within training')
    return row,winner


def identity_digest(binding):
    return hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':')).encode()).hexdigest()
