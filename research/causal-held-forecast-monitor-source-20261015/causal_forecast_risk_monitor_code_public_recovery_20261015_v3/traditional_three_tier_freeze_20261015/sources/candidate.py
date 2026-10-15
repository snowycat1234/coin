"""Fixed-fraction CHANGE allocator; no signal, forecast or monetary implementation."""
from dataclasses import dataclass
from decimal import Decimal as D, localcontext
S=('BTCUSDT','ETHUSDT','SOLUSDT','XRPUSDT','DOGEUSDT')
FRACTIONS=(D('1'),D('.75'),D('.5'),D('.25'),D('0'))
PRIORITY=frozenset(('TERMINAL','RISK_REDUCTION','POOL_EXIT','DATA_GAP_EXIT','PROTECTIVE_STOP'))
def vector(v):
 if set(v)!=set(S):raise ValueError('EXACT_CORE5_REQUIRED')
 r={s:D(str(v[s])) for s in S}
 if any(isinstance(v[s],bool) or not r[s].is_finite() for s in S):raise ValueError('FINITE_NONBOOLEAN_QUANTITY_REQUIRED')
 return r
@dataclass(frozen=True)
class Evaluation:
 fraction:D
 target:dict
 allowed:bool
 witness:dict
@dataclass(frozen=True)
class Selection:
 raw_target:dict
 target:dict
 fraction:D|None
 evaluations:tuple
 all_invalid:bool=False

def reduction_only(actual,raw):
 return {s:(D(0) if actual[s]*raw[s]<=0 else raw[s] if abs(raw[s])<abs(actual[s]) else actual[s]) for s in S}

def select_partial(*,actual,raw_target,evaluate):
 """Full valid is exact baseline; otherwise enumerate ALL remaining candidates.
 Each oracle call must start from the same immutable actual/pending state.
 No bisection/monotonic shortcut; exceptions fail closed for that candidate.
 """
 actual=vector(actual);raw=vector(raw_target);checks=[]
 for lam in FRACTIONS:
  with localcontext() as ctx:
   ctx.prec=40;target={s:actual[s]+lam*(raw[s]-actual[s]) for s in S}
  try:
   result=evaluate(dict(target),lam)
   if not isinstance(result,dict) or type(result.get('allowed')) is not bool:raise ValueError('EXPLICIT_ORACLE_VERDICT_REQUIRED')
  except Exception as e:result={'allowed':False,'reason':'ORACLE_EXCEPTION:'+type(e).__name__}
  checks.append(Evaluation(lam,dict(target),result['allowed'],result))
  if lam==1 and result['allowed']:return Selection(raw,dict(raw),lam,tuple(checks))
 valid=[v for v in checks if v.allowed]
 if valid:
  best=max(valid,key=lambda x:x.fraction);return Selection(raw,dict(best.target),best.fraction,tuple(checks))
 # Preserve real inventory; only ORIGINAL paid reductions may be dispatched.
 return Selection(raw,reduction_only(actual,raw),None,tuple(checks),True)

class ScheduleAdapter:
 """Intent seam only. Native scheduler owns reductions, clocks and actual fills.
 Provider binds existing actual wallet/pending/covariance at the signal. Mandatory
 priority requests are delegated byte-for-byte, never interpolated or blocked.
 """
 def __init__(self,original_schedule,oracle_for_signal):self.original_schedule=original_schedule;self.oracle_for_signal=oracle_for_signal;self.receipts=[]
 def schedule(self,target,signal,kind,only_symbols=None):
  raw=vector(target);active=S if only_symbols is None else tuple(only_symbols)
  if len(set(active))!=len(active) or any(s not in S for s in active):raise ValueError('EXACT_ACTIVE_SYMBOLS_REQUIRED')
  kind_for=lambda s:kind[s] if isinstance(kind,dict) else kind
  if isinstance(kind,dict) and set(kind)!=set(S):raise ValueError('EXACT_CORE5_KINDS_REQUIRED')
  priority=tuple(s for s in active if kind_for(s) in PRIORITY)
  normal=tuple(s for s in active if s not in priority)
  if not normal:return self.original_schedule(target,signal,kind,only_symbols)
  # Split priority symbols only. A single reduction flag cannot bypass any
  # unrelated increase. Native schedule retains its own supersession semantics.
  if priority:self.original_schedule(target,signal,kind,priority)
  oracle=self.oracle_for_signal(signal)
  normal_raw={s:raw[s] if s in normal else oracle.actual[s] for s in S}
  selection=select_partial(actual=oracle.actual,raw_target=normal_raw,evaluate=oracle.evaluate);self.receipts.append(selection)
  return self.original_schedule(selection.target,signal,kind,normal if priority or only_symbols is not None else None)
