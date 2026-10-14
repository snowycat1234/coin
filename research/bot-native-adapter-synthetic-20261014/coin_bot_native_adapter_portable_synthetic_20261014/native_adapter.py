"""Small generated-only policy adapter on the unchanged native financial engine.

One real shared account, no sleeve wallets. Ownership/fee/funding allocations are
observational and sum back to native journals; they never debit the account.
"""
from decimal import Decimal as D,localcontext,ROUND_DOWN
from copy import deepcopy
from itertools import product
import numpy as np
from bind_sources import load
PORT,ACCOUNT,NATIVE,H,RISK,F=load()
S=H.CORE5;BTC=S[0];M=H.MINUTE_US;DAY=1440*M;ZERO=D(0);STEP=H.STEP


def exact(row,key):return D(row['decimal_strings'][key])


def floor(x):return (x/STEP).to_integral_value(rounding=ROUND_DOWN)*STEP


class GridNativeAdapter(NATIVE):
 VERSION='generated_native_csh_grid_adapter_v1'
 def __init__(self,*args,arm='GRID',daily_closes=None,covariance=None,initial_observations=None,**kwargs):
  if arm not in ('CONTROL','CASH','GRID'):raise ValueError('FIXED_ARM')
  self.arm=arm;self.grid=None;self.prepared=None;self.binding=None
  self.base_btc=ZERO;self.base_desired=ZERO;self.original_desired=ZERO
  self.daily_closes=daily_closes or {};self.covariance=covariance or {};self.initial_observations=initial_observations or {}
  self.expired_sessions=set()
  self.allocations=[];self.funding_allocations=[];self.policy_events=[]
  self.seen_native_legs=set();self.seen_native_funding=set();self.settling=False
  self._inside_funding=False;self._last_attempt_open=None;self.original_target=dict.fromkeys(S,ZERO)
  self.restore_base_after_settlement=True
  self.native_certification='NOT_CERTIFIED_SYNTHETIC_ONLY'
  super().__init__(*args,**kwargs)

 def _cancel_grid_binding(self,clock):
  if self.binding is not None:
   native=self.pending.get(BTC)
   if native is not None and native["order_id"]==self.binding["native_order"]:
    self.pending.pop(BTC)
    self.rejections.append(dict(symbol=BTC,event_us=clock,order_id=native["order_id"],reason="BOT_NATIVE_CANCELLATION_CONFIRMED"))
   for slot,intent in list(self.grid.pending.items()):
    self.grid.on_cancel_confirmed(slot,order_id=intent.order_id,cancel_us=max(clock,self.grid.last_clock))
   self.policy_events.append(dict(event_us=clock,kind='CONFIRMED_NATIVE_SUPERSESSION',native_order=self.binding['native_order']))
   self.binding=None

 def _expire(self,clock,reason):
  if self.grid is None:return
  old=self.grid;self._cancel_grid_binding(clock)
  first_expiry=old.session_id not in self.expired_sessions
  self.expired_sessions.add(old.session_id)
  old.expire(max(clock,old.last_clock));self.settling=not old.settled()
  if first_expiry:self.policy_events.append(dict(event_us=clock,kind='PAID_GRID_SETTLEMENT_REQUIRED',reason=reason,owned=str(old.inventory()),session_id=old.session_id))
  if old.settled():
   # Paid-flat plus confirmed cancellation only; never release a live order
   # or owned inventory. A successor can now activate normally.
   self.grid=None

 def _prepare(self,signal,original):
  if self.arm!='GRID' or original<=0 or signal//DAY%7!=4:return
  # 1970-01-01 is Thursday; modulo4 is Monday. Source rows/availability are
  # already complete at the decision; no current minute open is read here.
  closes=self.daily_closes.get(signal)
  if closes is None:return
  budget_price=D(str(self.daily_prices[BTC][signal]))
  latest=self.account.marks[BTC][-1] if self.account.marks[BTC] else None
  observation=H.CompletedMinute(latest['available_us'],latest['price'],latest['close_us']) if latest else self.initial_observations.get(signal)
  if observation is None:
   self.policy_events.append(dict(event_us=signal,kind='GRID_INACTIVE',reason='INITIAL_COMPLETED_MINUTE_UNBOUND'));return
  try:
   g=H.weekly_plan(closes,signal,observation,
      float(self.account.nav()),[self.weights[signal][s] for s in S])
   # Original .99 signal-NAV collar is exact native quantity. This second
   # construction can fail a minimum that the preliminary helper passes.
   if g is not None:g=H.FixedGrid(closes,signal,observation,original*D('.1')*budget_price)
  except ValueError as e:
   self.policy_events.append(dict(event_us=signal,kind='GRID_INACTIVE',reason=str(e)));return
  if g is not None:self.prepared=g

 def schedule(self,target,signal,kind,only_symbols=None):
  if self.arm=='CONTROL':return super().schedule(target,signal,kind,only_symbols)
  active=S if only_symbols is None else tuple(only_symbols)
  btc_kind=(kind[BTC] if isinstance(kind,dict) else kind) if BTC in active else None
  if BTC not in active:return super().schedule(target,signal,kind,only_symbols)
  if btc_kind in ('TERMINAL','RISK_REDUCTION','POOL_EXIT','DATA_GAP_EXIT','PROTECTIVE_STOP'):
   self.restore_base_after_settlement=False;self.prepared=None
   self._expire(signal,'NATIVE_'+btc_kind)
   return super().schedule(target,signal,kind,only_symbols)
  incoming={s:D(str(target[s])) for s in S};self.original_target=deepcopy(incoming);self.original_desired=incoming[BTC]
  if self.arm=='CASH':
   self.base_desired=incoming[BTC]*D('.9') if incoming[BTC]>0 else incoming[BTC]
   incoming[BTC]=self.base_desired;return super().schedule(incoming,signal,kind,only_symbols)
  self.restore_base_after_settlement=True
  self._cancel_grid_binding(signal)
  if self.grid is not None:
   if incoming[BTC]<=0 or signal>=self.grid.session_end_us:
    self._expire(signal,'SIGN_CHANGE_OR_WEEKLY_RESET')
   elif self.grid.budget>incoming[BTC]*D('.1')*D(str(self.daily_prices[BTC][signal])):
    self._expire(signal,'DAILY_REPLACEMENT_BUDGET_DECREASE')
  admitted,witness=self._replacement_admitted(incoming)
  if admitted:self._prepare(signal,incoming[BTC])
  usable=(self.prepared is not None and signal<self.prepared.session_end_us or
    self.grid is not None and not self.grid.expired and signal<self.grid.session_end_us)
  if admitted and not usable:
   admitted=False;witness=dict(reasons=['NO_ADMITTED_FROZEN_WEEKLY_GRID'])
  self.base_desired=incoming[BTC]*D('.9') if admitted and incoming[BTC]>0 else incoming[BTC]
  if not admitted:
   self.prepared=None;self._expire(signal,'REPLACEMENT_TARGET_ENVELOPE_INADMISSIBLE')
   self.policy_events.append(dict(event_us=signal,kind='ORIGINAL_TARGET_FALLBACK',**witness))
  if self.settling:
   incoming[BTC]=floor(max(ZERO,min(self.base_btc,self.base_desired)))
   kinds={s:(kind[s] if isinstance(kind,dict) else kind) for s in S};kinds[BTC]='PROTECTIVE_STOP'
   super().schedule(incoming,signal,kinds,only_symbols)
  else:
   incoming[BTC]=self.base_desired+(self.grid.inventory() if self.grid else ZERO)
   super().schedule(incoming,signal,kind,only_symbols)

 def _allocate_external_close(self,qty):
  # Deterministic FIFO slot reductions from an actual native paid close.
  # This adapter-only callback cannot invent an account fill or free NAV.
  result=[]
  if self.grid is None:return result,qty
  for slot_id,slot in enumerate(self.grid.slots):
   use=min(qty,slot.owned)
   if use:
    slot.owned-=use;qty-=use;result.append(('GRID_EXIT',slot_id,use))
   if not qty:break
  return result,qty

 def _allocate_trade(self,row,purpose,binding):
  key=(row['fill_id'],row['leg'],row['event_us'])
  if key in self.seen_native_legs:raise ValueError('DUPLICATE_NATIVE_LEG')
  q=exact(row,'quantity');delta=exact(row,'position_delta');parts=[]
  if row['symbol']!=BTC or self.arm!='GRID':
   parts=[('BASE',None,q)]
   if row['symbol']==BTC:self.base_btc+=delta
  elif purpose=='GRID':
   remaining=q
   for intent in binding['intents']:
    current=self.grid.pending.get(intent.slot)
    if current is None:continue
    use=min(remaining,current.quantity)
    if use:
     fill_id=f'{row["fill_id"]}:{row["leg"]}:slot{intent.slot}'
     self.grid.on_fill(intent.slot,use,row['event_us'],order_id=intent.order_id,side=row['side'],fill_id=fill_id)
     parts.append(('GRID',intent.slot,use));remaining-=use
    if not remaining:break
   if remaining:raise ValueError('UNBOUND_GRID_FILL')
  elif delta<0 and (self.settling or self.terminal or purpose=='RISK_REDUCTION'):
   parts,remaining=self._allocate_external_close(q)
   if remaining:self.base_btc-=remaining;parts.append(('BASE',None,remaining))
  else:
   self.base_btc+=delta;parts=[('BASE',None,q)]
  if sum((a[2] for a in parts),ZERO)!=q:raise AssertionError('FILL_ALLOCATION_QUANTITY')
  with localcontext() as ctx:
   ctx.prec=40
   fee=exact(row,'fee_amount');friction=exact(row,'execution_cost');used_fee=used_cost=ZERO
   for i,(owner,slot,quantity) in enumerate(parts):
    last=i==len(parts)-1
    allocated_fee=fee-used_fee if last else fee*quantity/q
    allocated_cost=friction-used_cost if last else friction*quantity/q
    used_fee+=allocated_fee;used_cost+=allocated_cost
    self.allocations.append(dict(native_leg=list(key),owner=owner,slot=slot,quantity=str(quantity),side=row['side'],fee=str(allocated_fee),execution_cost=str(allocated_cost)))
  self.seen_native_legs.add(key)

 def _reconcile(self):
  grid=self.grid.inventory() if self.grid else ZERO
  if self.account.positions[BTC].quantity!=self.base_btc+grid:raise AssertionError('NATIVE_OWNERSHIP_BRIDGE')
  if grid and self.base_btc<0:raise AssertionError('OPPOSING_BTC_LEGS_FORBIDDEN')
  with localcontext() as ctx:
   ctx.prec=40
   if sum((D(a['fee']) for a in self.allocations),ZERO)!=self.account.fees:raise AssertionError('FEE_DOUBLE_COUNT')
   if sum((D(a['execution_cost']) for a in self.allocations),ZERO)!=self.account.execution_cost:raise AssertionError('FRICTION_DOUBLE_COUNT')

 def attempt(self,open_us,market_row):
  if type(open_us) is not int or self._last_attempt_open is not None and open_us<=self._last_attempt_open:
   raise ValueError('DUPLICATE_OR_REWOUND_NATIVE_ATTEMPT')
  old=self.pending.get(BTC);binding=self.binding
  if binding is not None:
   if old is None or old['order_id']!=binding['native_order']:raise ValueError('STALE_NATIVE_ORDER_BINDING')
   if self.grid is None or self.grid.session_id!=binding['session_id']:raise ValueError('STALE_HELPER_BINDING_BEFORE_FINANCE')
   remaining=ZERO;sides=set()
   for intent in binding['intents']:
    current=self.grid.pending.get(intent.slot)
    if current is None:continue
    if current.order_id!=intent.order_id or current.session_id!=binding['session_id'] or current.side!=intent.side:
     raise ValueError('STALE_HELPER_BINDING_BEFORE_FINANCE')
    sides.add(current.side)
    remaining+=current.quantity if current.side=='BUY' else -current.quantity
   if len(sides)!=1:raise ValueError('MIXED_OR_EMPTY_HELPER_BINDING_BEFORE_FINANCE')
   if old['target']!=self.account.positions[BTC].quantity+remaining:raise ValueError('NATIVE_PENDING_QUANTITY_UNBOUND')
  self._last_attempt_open=open_us
  before=len(self.account.trades)
  purpose=('GRID' if binding and old and old['order_id']==binding['native_order']
           else old['kind'] if old else 'BASE')
  # Exact original terminal60 method owns capacity, fill ordering, costs,
  # hard-risk, expiry and shared account. We never issue a second fill here.
  super().attempt(open_us,market_row)
  for row in self.account.trades[before:]:self._allocate_trade(row,purpose,binding)
  if binding and (BTC not in self.pending or self.pending[BTC]['order_id']!=binding['native_order']):
   self._cancel_grid_binding(open_us+1)
  self._reconcile()

 def funding_through(self,limit,inclusive):
  before=len(self.account.funding)
  self._inside_funding=True
  try:super().funding_through(limit,inclusive)
  finally:self._inside_funding=False
  for row in self.account.funding[before:]:
   key=row['event_id']
   if key in self.seen_native_funding:raise ValueError('DUPLICATE_FUNDING_ALLOCATION')
   amount=exact(row,'signed_funding_USDT');quantity=exact(row,'quantity')
   grid=self.grid.inventory() if row['symbol']==BTC and self.grid else ZERO
   with localcontext() as ctx:
    ctx.prec=40
    g=amount*grid/quantity if quantity and grid else ZERO
    self.funding_allocations.extend([dict(native_event=key,owner='GRID',cash=str(g)),dict(native_event=key,owner='BASE',cash=str(amount-g))])
   self.seen_native_funding.add(key)
  with localcontext() as ctx:
   ctx.prec=40
   if sum((D(a['cash']) for a in self.funding_allocations),ZERO)!=self.account.funding_cash:raise AssertionError('FUNDING_DOUBLE_COUNT')

 def _risk_envelope(self,ends,reference):
  nav=self.account.nav()
  if nav<=0:return False,dict(reasons=['NONPOSITIVE_NATIVE_NAV'])
  cov=self.covariance.get(self.cursor)
  if cov is None:return False,dict(reasons=['CAUSAL_COVARIANCE_UNBOUND'])
  try:c=np.asarray(RISK.check_covariance(cov),dtype=float)
  except (ValueError,TypeError):return False,dict(reasons=['CAUSAL_COVARIANCE_UNKNOWN_OR_SINGULAR'])
  marks=np.array([float(self.account.marks[s][-1]['price']) if self.account.marks[s]
    else float(self.daily_prices[s][self.cursor]) for s in S])
  ref=np.array([float(reference[s]) for s in S])*marks/float(nav)
  gross_ref=float(np.abs(ref).sum());net_ref=abs(float(ref.sum()))
  sigma_ref=float(np.sqrt(max(0.,ref@c@ref)))
  worst_gross=worst_net=worst_sigma=0.;worst_asset=np.zeros(5);reasons=set()
  for values in product(*ends):
   w=np.array([float(v) for v in values])*marks/float(nav)
   gross=float(np.abs(w).sum());net=abs(float(w.sum()));sigma=float(np.sqrt(max(0.,w@c@w)))
   worst_gross=max(worst_gross,gross);worst_net=max(worst_net,net);worst_sigma=max(worst_sigma,sigma)
   worst_asset=np.maximum(worst_asset,np.abs(w))
   if gross>min(.60,gross_ref)+1e-12:reasons.add('GROSS_CAP_OR_ORIGINAL_TARGET')
   if np.any(np.abs(w)>np.minimum(.30,np.abs(ref))+1e-12):reasons.add('ASSET_CAP_OR_ORIGINAL_TARGET')
   if net>net_ref+1e-12:reasons.add('ABS_NET_ORIGINAL_TARGET')
   if sigma>min(.10,sigma_ref)+1e-12:reasons.add('CAUSAL_VOL_ORIGINAL_TARGET')
  return not reasons,dict(reasons=sorted(reasons),causal_sigma_bound=worst_sigma,
   original_target_sigma=sigma_ref,gross_bound=worst_gross,original_target_gross=gross_ref,
   abs_net_bound=worst_net,original_target_abs_net=net_ref,asset_bounds=worst_asset.tolist(),
   original_target_asset=np.abs(ref).tolist())

 def _replacement_admitted(self,target):
  if target[BTC]<=0:return False,dict(reasons=['NO_POSITIVE_ORIGINAL_BTC'])
  ends=[(target[s]*D('.9'),target[s]) if s==BTC else (target[s],) for s in S]
  return self._risk_envelope(ends,target)

 def _reservation(self):
  # One actual native wallet plus outstanding native orders and ALL grid
  # inventory that could fill. Signed endpoint vertices include reversals.
  nav=self.account.nav();bounds={};cash=ZERO;ends=[]
  for s in S:
   position=self.account.positions[s].quantity
   target=self.pending[s]['target'] if s in self.pending else position
   points=[position,target]
   if s==BTC and self.grid:
    # A sell cannot release its owned inventory until the paid native fill.
    points.extend((self.base_btc,self.base_btc+self.grid.reserve_quantity()))
   ends.append(tuple(set(points)));bound=max(abs(q) for q in points)
   mark=self.account.marks[s][-1]['price'] if self.account.marks[s] else D(str(self.daily_prices[s][self.cursor]))
   bounds[s]=bound*mark
   # A reversal must reserve opening collateral even when abs(target) is
   # smaller than abs(actual); do not assume the close has released cash.
   opening=max((abs(q) if q*position<0 else max(ZERO,abs(q)-abs(position)) for q in points),default=ZERO)
   cash+=opening*mark*D('1.00135044')
  good,witness=self._risk_envelope(ends,self.original_target)
  if nav<=0 or sum(bounds.values(),ZERO)>D('.6')*nav or max(bounds.values())>D('.3')*nav:
   good=False;witness['reasons']=sorted(set(witness['reasons']+['ABSOLUTE_NATIVE_EXPOSURE_BOUND']))
  if cash>self.account.free_cash:
   good=False;witness['reasons']=sorted(set(witness['reasons']+['SHARED_NATIVE_CASH_UNFUNDED']))
  return good,dict(**witness,cash_required=str(cash),free_cash=str(self.account.free_cash),NAV=str(nav))

 def _completed_quote(self,stamp):
  # Original MarketTape already owns the immutable current day. Only the row
  # whose exclusive close equals this admitted close is read, never future rows.
  cache=self.tape.cache;start=self.tape.cache_start
  i=(stamp-start)//M-1 if start is not None else -1
  if cache is None or not 0<=i<len(cache) or cache[i][0]+M!=stamp:
   raise ValueError('COMPLETED_NATIVE_QUOTE_UNBOUND')
  return {s:D(str(cache[i][1][s]['quote_volume'])) for s in S}

 def risk_schedule(self,stamp):
  # Native close-phase calls this after equal-clock funding, preserving causal
  # mark/funding priority. Native risk reduction always wins over bot intents.
  super().risk_schedule(stamp)
  if (self.arm!='GRID' or self.terminal or self.stop is not None or self.account.status!='ACTIVE'
      or self._inside_funding or stamp%M or any(not self.account.marks[s] or self.account.marks[s][-1]['close_us']!=stamp for s in S)):
   return
  if self.grid is not None and stamp>=self.grid.session_end_us:self._expire(stamp,'FIXED_WEEK_END')
  if self.settling:
   if self.grid.settled() and BTC not in self.pending:
    self.grid=None;self.settling=False
    if self.restore_base_after_settlement and BTC not in self.pending:
     super().schedule({BTC:self.base_desired},stamp,'DAILY_TARGET',only_symbols=(BTC,))
   elif BTC not in self.pending:
    super().schedule({BTC:floor(max(ZERO,min(self.base_btc,self.base_desired)))},stamp,'PROTECTIVE_STOP',only_symbols=(BTC,))
   return
  if any(o["kind"]=="RISK_REDUCTION" for o in self.pending.values()):return
  if self.grid is None and self.prepared is not None and BTC not in self.pending:
   if stamp>=self.prepared.session_end_us:self.prepared=None;return
   self.grid=self.prepared;self.prepared=None
   self.policy_events.append(dict(event_us=stamp,kind='GRID_SESSION_ACTIVATED',session_id=self.grid.session_id,budget=str(self.grid.budget),reserved_quantity=str(self.grid.reserve_quantity())))
  if self.grid is None or BTC in self.pending:return
  if floor(self.base_btc)!=floor(self.base_desired):
   self.policy_events.append(dict(event_us=stamp,kind="BASE_UNFILLED_GRID_BLOCKED"));return
  good,witness=self._reservation()
  if not good:
   self.policy_events.append(dict(event_us=stamp,kind='RESERVATION_BLOCKED',**witness));return
  intents=self.grid.intents(stamp,H.CompletedMinute(stamp,self.account.marks[BTC][-1]['price'],stamp))
  if not intents:return
  # Never net opposite grid intents into a free virtual round trip. Native
  # one-way account receives SELL reductions first; other local unsubmitted
  # intents are explicitly canceled before the next observation may regenerate.
  selected='SELL' if any(i.side=='SELL' for i in intents) else 'BUY'
  for i in intents:
   if i.side!=selected:self.grid.on_cancel_confirmed(i.slot,order_id=i.order_id,cancel_us=stamp)
  intents=[i for i in intents if i.side==selected]
  delta=sum(((i.quantity if i.side=='BUY' else -i.quantity) for i in intents),ZERO)
  quote=self._completed_quote(stamp)[BTC]
  requested=abs(delta)*self.account.marks[BTC][-1]['price']
  if requested>quote*D('.001'):
   for i in intents:self.grid.on_cancel_confirmed(i.slot,order_id=i.order_id,cancel_us=stamp)
   self.policy_events.append(dict(event_us=stamp,kind='GRID_CAPACITY_ADMISSION_BLOCKED',
    requested_notional=str(requested),completed_prior_quote=str(quote)))
   return
  target=self.account.positions[BTC].quantity+delta
  super().schedule({BTC:target},stamp,'DAILY_TARGET',only_symbols=(BTC,))
  self.binding=dict(native_order=self.pending[BTC]['order_id'],intents=list(intents),session_id=self.grid.session_id)
  self.policy_events.append(dict(event_us=stamp,kind='GRID_NATIVE_BOUND',session_id=self.grid.session_id,native_order=self.binding['native_order'],orders=[i.order_id for i in intents]))

 def snapshot(self):
  result=super().snapshot()
  def pack(x):
   if isinstance(x,D):return str(x)
   if isinstance(x,dict):return {str(k):pack(v) for k,v in x.items()}
   if isinstance(x,(tuple,list,set)):return [pack(v) for v in x]
   if hasattr(x,'__dataclass_fields__'):return {k:pack(getattr(x,k)) for k in x.__dataclass_fields__}
   if isinstance(x,np.ndarray):return x.tolist()
   return x
  result['adapter_state']=pack(dict(arm=self.arm,base_btc=self.base_btc,base_desired=self.base_desired,
   original_target=self.original_target,grid=vars(self.grid) if self.grid else None,
   prepared=vars(self.prepared) if self.prepared else None,binding=self.binding,
   settling=self.settling,allocations=self.allocations,funding_allocations=self.funding_allocations,
   policy_events=self.policy_events,seen_native_legs=self.seen_native_legs,
   seen_native_funding=self.seen_native_funding,expired_sessions=self.expired_sessions,restore_base_after_settlement=self.restore_base_after_settlement,last_attempt=self._last_attempt_open))
  result['adapter_restore']='NOT_IMPLEMENTED_NO_HISTORICAL_GO'
  return result

 @classmethod
 def from_snapshot(cls,*args,**kwargs):
  raise ValueError('ADAPTER_RESTORE_NOT_IMPLEMENTED_NO_HISTORICAL_GO')

 def fork(self):raise ValueError('ADAPTER_FORK_NOT_IMPLEMENTED_NO_HISTORICAL_GO')
