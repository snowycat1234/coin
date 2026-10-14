"""Fixed original-risk HEADROOM comparison, generated fixtures only.

Studied legacy uses byte-identical original float assessment. All studied arms
share one hard-risk priority correction, masks, finance, clocks and terminal60.
The unfixed original hook is retained as a separately named generated diagnostic.
"""
from copy import deepcopy
from decimal import Decimal as D
from bind_native import load
PORT,ACCOUNT,TERMINAL,ORIGINALS,LEGACY,TAPE,PROTECTIVE,HEADROOM,PAIRED=load()
import numpy as np
from scripts.investment.resumable_perpetual import NativeDailySimulator as NATIVE
from quant.perpetual_account import HALTS,ZERO
S=tuple(PORT.SYMBOLS);M=60_000_000;DAY=1440*M
ARMS=('disabled','legacy_shared_priority_fixed','aligned_independent','paired')

class ComparisonTape:
 """Exact-source construction in memory; original readiness is shared by arms."""
 def __init__(self,times,symbols,market,derived=None):
  if np.asarray(times).dtype.kind not in 'iu':raise ValueError('INTEGER_OPEN_CLOCKS_REQUIRED')
  times=np.array(times,dtype=np.int64,copy=True);self.symbols=tuple(symbols)
  if self.symbols!=S or set(market)!=set(S):raise ValueError('EXACT_ORIGINAL_CORE5_ORDER_REQUIRED')
  self.paired={};arrays={}
  for s in self.symbols:
   mark=np.array(market[s]['mark'],dtype=np.float64,copy=True)
   opens=np.array(market[s]['open'],dtype=np.float64,copy=True)
   mask=None if derived is None else derived[s]
   base=LEGACY.features(times,mark,opens,mask)
   pair=PAIRED.features(times,mark,opens,mask)
   if not np.array_equal(base['ready'],pair['ready']) or not np.array_equal(base['reason'],pair['reason']):
    raise ValueError('COMMON_ORIGINAL_READINESS_REQUIRED')
   self.paired[s]=pair
   arrays[s+'_mark']=mark;arrays[s+'_ready']=base['ready']
   arrays[s+'_reason_code']=np.array([TAPE.REASONS.index(x) for x in base['reason']],dtype=np.uint8)
   for k in ('a_down','a_up','g_down','g_up'):arrays[s+'_'+k]=base[k]
   for a in pair.values():a.flags.writeable=False
  binding={'scope':'GENERATED_ONLY_NO_HISTORICAL_ADMISSION','source_times_SHA256':TAPE.array_sha(times),
   'arrays_SHA256':{k:TAPE.array_sha(v) for k,v in arrays.items()},
   'paired_SHA256':{s:{k:TAPE.array_sha(v) for k,v in f.items()} for s,f in self.paired.items()}}
  self.legacy=TAPE.FeatureTape(times+M,self.symbols,arrays,binding)
 def at(self,s,stamp,mark,arm):
  ready,reason,feature=self.legacy.at(s,stamp,mark)
  if not ready or arm=='legacy_shared_priority_fixed':return ready,reason,feature
  if arm not in ('aligned_independent','paired'):raise ValueError('ARM')
  i=(int(stamp)-int(self.legacy.times[0]))//M
  prefix='' if arm=='paired' else arm+'_'
  f=self.paired[s]
  return ready,reason,{k:float(f[prefix+k][i]) for k in ('long_hurdle','short_hurdle')}
 def __deepcopy__(self,memo):return self

class Terminal60Protection:
 """Explicit priority glue. Does not replace any finance or attempt body."""
 def schedule(self,target,signal,kind,only_symbols=None):
  if kind=='TERMINAL' or self.terminal:
   return TERMINAL.schedule(self,target,signal,kind,only_symbols)
  return super().schedule(target,signal,kind,only_symbols)
 def attempt(self,open_us,market_row):
  if self.terminal:
   # Avoid protective retry/reschedule after the terminal order has expired.
   result=TERMINAL.attempt(self,open_us,market_row)
   # Record a genuinely paid terminal close, without reviving protection or
   # replacing any terminal order. This is lock bookkeeping only.
   for symbol,lock in self.protective_locks.items():
    if lock['flat_us'] is None and not self.account.positions[symbol].quantity:
     lock['flat_us']=int(open_us)+1
     kind='FLAT_ON_HALTED_ACCOUNT' if self.account.status in HALTS else 'FULL_EXIT_FLAT'
     self.protective_events.append(dict(kind=kind,symbol=symbol,event_us=lock['flat_us']))
   return result
  return super().attempt(open_us,market_row)
 def risk_schedule(self,stamp):
  if self.terminal:return NATIVE.risk_schedule(self,stamp)
  return super().risk_schedule(stamp)

class OriginalUnfixedLegacyTerminal60Diagnostic(Terminal60Protection,HEADROOM.HeadroomFullExitSimulator,TERMINAL):
 """Independent reference: unchanged original HEADROOM hook and legacy assess."""
 VERSION='generated_original_unfixed_legacy_headroom_terminal60_diagnostic_v1'
 def __init__(self,window,*args,**kwargs):
  if window.get('fixture_scope')!='GENERATED_PAIRED_HEADROOM_ONLY' or 'minute_blocks' in window:
   raise ValueError('GENERATED_DIAGNOSTIC_ONLY_HISTORY_NO_GO')
  super().__init__(window,*args,**kwargs)
 @classmethod
 def from_snapshot(cls,*args,**kwargs):
  raise ValueError('GENERATED_COMPOSITE_RESTORE_NOT_ADMITTED')

# Compatibility reference for the original-hook generated diagnostic only.
DirectLegacyTerminal60=OriginalUnfixedLegacyTerminal60Diagnostic

class PairedNativeAdapter(OriginalUnfixedLegacyTerminal60Diagnostic):
 VERSION='generated_original_paired_headroom_shared_priority_terminal60_v2'
 def __init__(self,window,mode,cost,unit,*,arm,target_factory=None,account_factory=ACCOUNT,
              persist_cash_close=False,final_day_target_zero=False):
  if window.get('fixture_scope')!='GENERATED_PAIRED_HEADROOM_ONLY' or 'minute_blocks' in window:
   raise ValueError('GENERATED_ONLY_HISTORY_NO_GO')
  if arm not in ARMS or mode!='LONG_SHORT' or account_factory is not ACCOUNT:
   raise ValueError('FIXED_ARM_ORIGINAL_ACCOUNT_REQUIRED')
  if cost!=PORT.native.COSTS[0] or unit!=PORT.native.UNITS[0]:
   raise ValueError('EXACT_BASE27_CONDITIONAL_RAW_FUNDING_REQUIRED')
  if persist_cash_close is not False or final_day_target_zero is not False:
   raise ValueError('UNCHANGED_TARGET_TERMINAL_FLAGS')
  if not isinstance(window.get('comparison_features'),ComparisonTape):
   raise ValueError('EXACT_COMMON_COMPARISON_TAPE')
  self.arm=arm
  def checked(daily,clocks,mode):
   frame,meta=target_factory(daily,clocks,mode)
   for t in clocks:
    rows=frame.filter(PORT.native.pl.col('available_us')==t)
    w=np.array(rows['target_weight'])
    if not np.isfinite(w).all() or np.abs(w).max()>.3+1e-12 or np.abs(w).sum()>.6+1e-12:
     raise ValueError('ORIGINAL_030_060_TARGET_CAPS')
   return frame,meta
  super().__init__(window,mode,cost,unit,target_factory=checked if target_factory else None,
   account_factory=account_factory,persist_cash_close=False,final_day_target_zero=False)
  if self.account.config.max_gross_weight!=D('.6') or self.account.config.max_asset_weight!=D('.3') or self.account.config.leverage!=D(1) or self.account.config.initial_cash!=D(10000):
   raise ValueError('ORIGINAL_ACCOUNT_CONSTANTS')
 def risk_schedule(self,stamp):
  if self.arm=='disabled' or self.terminal:return NATIVE.risk_schedule(self,stamp)
  same_clock_funding_left=(self.event_cursor<len(self.window['events']) and
   self.window['events'][self.event_cursor]['event_us']==int(stamp))
  if self.account.status not in HALTS and int(stamp)%M==0 and not same_clock_funding_left:
   for symbol in self.symbols:
    position=self.account.positions[symbol]
    if not position.quantity or symbol in self.protective_locks:continue
    marks=self.account.marks[symbol]
    if not marks or marks[-1]['close_us']!=int(stamp):continue
    mark=marks[-1]['price'];balance=position.isolated_balance
    equity=balance+position.quantity*(mark-position.entry_price)
    ready,reason,feature=self.window['comparison_features'].at(symbol,stamp,mark,self.arm)
    coverage=self.headroom_coverage[symbol]
    if not ready:
     coverage['not_ready_invested_hook_evaluations']+=1
     coverage['not_ready_reasons'][reason]=coverage['not_ready_reasons'].get(reason,0)+1
     continue
    coverage['ready_invested_hook_evaluations']+=1
    # Keep original legacy operation grouping, with no normalized boundary.
    assessor=LEGACY.assess if self.arm=='legacy_shared_priority_fixed' else PAIRED.assess
    stress=assessor(float(position.quantity),float(equity),float(mark),**feature)
    if not bool(stress['trigger']):continue
    self.protective_locks[symbol]={'stopped_sign':PROTECTIVE.sign(position.quantity),
     'trigger_us':int(stamp),'flat_us':None,'deferred_no_lot_minutes':0}
    self.protective_events.append(dict(kind='FULL_EXIT_SIGNAL',symbol=symbol,event_us=int(stamp),
     quantity=str(position.quantity),mark=str(mark),isolated_balance=str(balance),isolated_equity=str(equity),
     stress_features=feature,stress_assessment={k:float(v) for k,v in stress.items() if k!='trigger'}))
    # Preserve the native cap order object, partial target, signal and attempts.
    # The original protective executor resumes full exit after cap resolution.
    if self.pending.get(symbol,{}).get('kind')!='RISK_REDUCTION':
     NATIVE.schedule(self,{symbol:ZERO},int(stamp),'PROTECTIVE_STOP',only_symbols=(symbol,))
  NATIVE.risk_schedule(self,stamp)
 def result(self):
  case=super().result()
  case['protective_policy'].update(terminal_opens=60,policy_id=self.VERSION,arm=self.arm,
   scope='GENERATED_MECHANICS_ONLY',historical_GO=False,common_readiness=True,
   reused_execution='ORIGINAL_GUARD50_NONTERMINAL_EXECUTOR_PLUS_ORIGINAL_TERMINAL60',
   terminal_protection_priority='TERMINAL_DOMINATES_NO_PROTECTION_RESCHEDULE',
   legacy_assess='BYTE_IDENTICAL_ORIGINAL_FLOAT_OPERATION_ORDER',
   shared_hard_risk_priority='NEW_LOCK_NEVER_REPLACES_PENDING_ORIGINAL_RISK_ORDER',
   original_unfixed_diagnostic='SEPARATE_GENERATED_CONTROL_NOT_MAIN_LEGACY')
  case['summary']['protective_policy_id']=self.VERSION
  return case
 def snapshot(self):
  raise ValueError('GENERATED_COMPOSITE_RESTORE_NOT_ADMITTED')
