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
 def __init__(self,*args,arm='GRID',daily_closes=None,covariance=None,**kwargs):
  if arm not in ('CONTROL','CASH','GRID'):raise ValueError('FIXED_ARM')
  self.arm=arm;self.grid=None;self.prepared=None;self.binding=None
  self.base_btc=ZERO;self.base_desired=ZERO;self.original_desired=ZERO
  self.daily_closes=daily_closes or {};self.covariance=covariance or {}
  self.allocations=[];self.funding_allocations=[];self.policy_events=[]
  self.seen_native_legs=set();self.seen_native_funding=set();self.settling=False
  self._inside_funding=False;self._last_attempt_open=None;self.original_target=dict.fromkeys(S,ZERO)
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
  self._cancel_grid_binding(clock)
  self.grid.expire(max(clock,self.grid.last_clock));self.settling=not self.grid.settled()
  self.policy_events.append(dict(event_us=clock,kind='PAID_GRID_SETTLEMENT_REQUIRED',reason=reason,owned=str(self.grid.inventory())))

 def _prepare(self,signal,original):
  if self.arm!='GRID' or original<=0 or signal//DAY%7!=4:return
  # 1970-01-01 is Thursday; modulo4 is Monday. Source rows/availability are
  # already complete at the decision; no current minute open is read here.
  closes=self.daily_closes.get(signal)
  if closes is None:return
  price=D(str(self.daily_prices[BTC][signal]))
  try:
   g=H.weekly_plan(closes,signal,H.CompletedMinute(signal,price,signal),
      float(self.account.nav()),[self.weights[signal][s] for s in S])
  except ValueError as e:
   self.policy_events.append(dict(event_us=signal,kind='GRID_INACTIVE',reason=str(e)));return
  # Original scheduler's .99 signalNAV is retained, so replacement collar is
  # based on the actual native original quantity, not a fresh extra wallet.
  if g is not None:
   g=H.FixedGrid(closes,signal,H.CompletedMinute(signal,price,signal),original*D('.1')*price)
   self.prepared=g

 def schedule(self,target,signal,kind,only_symbols=None):
  if self.arm=='CONTROL':return super().schedule(target,signal,kind,only_symbols)
  kinds=[kind[s] for s in S] if isinstance(kind,dict) else [kind]
  if any(k in ('TERMINAL','RISK_REDUCTION','POOL_EXIT','DATA_GAP_EXIT','PROTECTIVE_STOP') for k in kinds):
   self._expire(signal,'NATIVE_'+','.join(sorted(set(kinds))))
   return super().schedule(target,signal,kind,only_symbols)
  incoming={s:D(str(target[s])) for s in S};self.original_target=deepcopy(incoming);self.original_desired=incoming[BTC]
  self.base_desired=incoming[BTC]*D('.9') if incoming[BTC]>0 else incoming[BTC]
  if self.arm=='CASH':
   incoming[BTC]=self.base_desired;return super().schedule(incoming,signal,kind,only_symbols)
  self._cancel_grid_binding(signal)
  if self.grid is not None:
   if incoming[BTC]<=0 or signal>=self.grid.session_end_us:
    self._expire(signal,'SIGN_CHANGE_OR_WEEKLY_RESET')
   elif self.grid.budget>incoming[BTC]*D('.1')*D(str(self.daily_prices[BTC][signal])):
    self._expire(signal,'DAILY_REPLACEMENT_BUDGET_DECREASE')
  self._prepare(signal,incoming[BTC])
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
   remaining=ZERO
   for intent in binding['intents']:
    current=self.grid.pending.get(intent.slot)
    if current is None:continue
    if current.order_id!=intent.order_id or current.session_id!=binding['session_id'] or current.side!=intent.side:
     raise ValueError('STALE_HELPER_BINDING_BEFORE_FINANCE')
    remaining+=current.quantity if current.side=='BUY' else -current.quantity
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

 def _reservation(self):
  # Actual native wallet plus existing orders plus all grid inventory that
  # could fill. This is a conservative envelope, not future risk certification.
  nav=self.account.nav();bounds={};cash=ZERO
  for s in S:
   actual=abs(self.account.positions[s].quantity);pending=abs(self.pending[s]['target']) if s in self.pending else actual
   bound=max(actual,pending)
   if s==BTC and self.grid:
    bound=max(bound,abs(self.base_btc)+self.grid.reserve_quantity())
   mark=self.account.marks[s][-1]['price'] if self.account.marks[s] else D(str(self.daily_prices[s][self.cursor]))
   bounds[s]=bound*mark
   cash+=max(ZERO,bound-actual)*mark*D('1.00135044')
  good=nav>0 and sum(bounds.values(),ZERO)<=D('.6')*nav and max(bounds.values())<=D('.3')*nav and cash<=self.account.free_cash
  # Check all actual/pending inventory endpoints with the original causal
  # covariance. This is observed ex-ante arithmetic only, not risk parity.
  cov=self.covariance.get(self.cursor)
  if cov is None:
   return False,dict(reason='CAUSAL_COVARIANCE_UNBOUND')
  try:c=np.asarray(RISK.check_covariance(cov),dtype=float)
  except ValueError:return False,dict(reason='CAUSAL_COVARIANCE_UNKNOWN_OR_SINGULAR')
  marks=np.array([float(self.account.marks[s][-1]['price']) for s in S])
  ref=np.array([float(self.original_target[s]) for s in S])*marks/float(nav)
  ref_sigma=float(np.sqrt(max(0.,ref@c@ref)))
  ends=[]
  for s in S:
   q=self.account.positions[s].quantity
   if s==BTC and self.grid:ends.append((self.base_btc,self.base_btc+self.grid.reserve_quantity()))
   else:ends.append((q,self.pending[s]['target'] if s in self.pending else q))
  max_sigma=0.
  for values in product(*ends):
   w=np.array([float(v) for v in values])*marks/float(nav)
   max_sigma=max(max_sigma,float(np.sqrt(max(0.,w@c@w))))
  good=good and max_sigma<=min(.10,ref_sigma)+1e-12
  return good,dict(causal_sigma_bound=max_sigma,original_target_sigma=ref_sigma,gross_bound=str(sum(bounds.values(),ZERO)),cash_required=str(cash),free_cash=str(self.account.free_cash),NAV=str(nav))

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
    if BTC not in self.pending:
     super().schedule({BTC:self.base_desired},stamp,'DAILY_TARGET',only_symbols=(BTC,))
   elif BTC not in self.pending:
    super().schedule({BTC:floor(max(ZERO,min(self.base_btc,self.base_desired)))},stamp,'PROTECTIVE_STOP',only_symbols=(BTC,))
   return
  if any(o["kind"]=="RISK_REDUCTION" for o in self.pending.values()):return
  if self.grid is None and self.prepared is not None and BTC not in self.pending:
   if stamp>=self.prepared.session_end_us:self.prepared=None;return
   self.grid=self.prepared;self.prepared=None
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
  target=self.account.positions[BTC].quantity+delta
  super().schedule({BTC:target},stamp,'DAILY_TARGET',only_symbols=(BTC,))
  self.binding=dict(native_order=self.pending[BTC]['order_id'],intents=list(intents),session_id=self.grid.session_id)
  self.policy_events.append(dict(event_us=stamp,kind='GRID_NATIVE_BOUND',native_order=self.binding['native_order'],orders=[i.order_id for i in intents]))

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
   seen_native_funding=self.seen_native_funding,last_attempt=self._last_attempt_open))
  result['adapter_restore']='NOT_IMPLEMENTED_NO_HISTORICAL_GO'
  return result

 @classmethod
 def from_snapshot(cls,*args,**kwargs):
  raise ValueError('ADAPTER_RESTORE_NOT_IMPLEMENTED_NO_HISTORICAL_GO')

 def fork(self):raise ValueError('ADAPTER_FORK_NOT_IMPLEMENTED_NO_HISTORICAL_GO')
