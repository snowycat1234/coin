"""Observational ownership of ONE native wallet; no owner cash accounts."""
from copy import deepcopy
from decimal import Decimal as D,localcontext
from native_control import S
BASE='CSH';FINITE='MART_FINITE_REPLACE10';OWNERS=(BASE,FINITE);BTC=S[0];Z=D(0)


def exact(row,name):return D(row['decimal_strings'][name])


class OwnerLedger:
    def __init__(self):
        self.quantity={o:dict.fromkeys(S,Z) for o in OWNERS}
        self.basis={o:dict.fromkeys(S,Z) for o in OWNERS}
        self.realized=dict.fromkeys(OWNERS,Z)
        self.fees=dict.fromkeys(OWNERS,Z)
        self.execution_cost=dict.fromkeys(OWNERS,Z)
        self.funding=dict.fromkeys(OWNERS,Z)
        self.funding_debits=dict.fromkeys(OWNERS,Z)
        self.realized_losses=dict.fromkeys(OWNERS,Z)
        self.fill_allocations=[];self.funding_allocations=[]

    def trade(self,row,owner):
        if owner not in OWNERS or owner==FINITE and row['symbol']!=BTC:
            raise ValueError('EXPLICIT_ACTUAL_FILL_OWNER_REQUIRED')
        s=row['symbol'];q=exact(row,'quantity');delta=exact(row,'position_delta')
        price=exact(row,'fill_price');before=self.quantity[owner][s]
        with localcontext() as ctx:
            ctx.prec=40
            economic=Z
            if row['leg']=='OPEN':
                if before and before*delta<0:raise AssertionError('OWNER_DIRECTION_COLLISION')
                after=before+delta
                self.basis[owner][s]=(abs(before)*self.basis[owner][s]+q*price)/abs(after)
                self.quantity[owner][s]=after
            elif row['leg']=='CLOSE':
                if not before or before*delta>=0 or q>abs(before):
                    raise AssertionError('PAID_CLOSE_EXCEEDS_ACTUAL_OWNER_INVENTORY')
                economic=(D(1) if before>0 else D(-1))*q*(price-self.basis[owner][s])
                self.realized[owner]+=economic
                self.realized_losses[owner]+=max(-economic,Z)
                self.quantity[owner][s]=before+delta
                if self.quantity[owner][s]==0:self.basis[owner][s]=Z
            else:raise AssertionError('UNSUPPORTED_NATIVE_FINANCIAL_LEG')
            fee=exact(row,'fee_amount');cost=exact(row,'execution_cost')
            self.fees[owner]+=fee;self.execution_cost[owner]+=cost
            self.fill_allocations.append({'fill_id':row['fill_id'],'leg':row['leg'],
                'owner':owner,'symbol':s,'quantity':str(q),'fee':str(fee),
                'execution_cost':str(cost),'native_realized_PnL':str(exact(row,'realized_PnL')),
                'owner_actual_fill_realized_PnL':str(economic),
                'realized_classification_bridge':str(exact(row,'realized_PnL')-economic)})

    def funding_event(self,row):
        s=row['symbol'];amount=exact(row,'signed_funding_USDT');native_q=exact(row,'quantity')
        with localcontext() as ctx:
            ctx.prec=40
            if sum((self.quantity[o][s] for o in OWNERS),Z)!=native_q:
                raise AssertionError('FUNDING_ACTUAL_OWNER_QUANTITY_MISMATCH')
            base=amount*self.quantity[BASE][s]/native_q if native_q else Z
            allocated={BASE:base,FINITE:amount-base}
            for owner,value in allocated.items():
                expected=-self.quantity[owner][s]*exact(row,'mark_price')*exact(row,'rate_fraction') if row['owned'] else Z
                self.funding[owner]+=value;self.funding_debits[owner]+=max(-value,Z)
                self.funding_allocations.append({'event_id':row['event_id'],'owner':owner,
                    'symbol':s,'owned_quantity':str(self.quantity[owner][s]),
                    'signed_native_funding_allocated':str(value),
                    'allocation_rounding_bridge':str(value-expected)})
        return allocated

    def unrealized(self,owner,account):
        with localcontext() as ctx:
            ctx.prec=40
            return sum((self.quantity[owner][s]*(account.marks[s][-1]['price']-self.basis[owner][s])
                for s in S if self.quantity[owner][s]),Z)

    def pnl(self,owner,account):
        with localcontext() as ctx:
            ctx.prec=40
            return self.realized[owner]+self.unrealized(owner,account)+self.funding[owner]-self.fees[owner]

    def margins(self,account):
        # Native isolated balance is attributed by current actual owned quantity.
        # This is observational allocation, never a transfer/top-up. The finite
        # owner receives the explicit final Decimal remainder for exact totals.
        result=dict.fromkeys(OWNERS,Z)
        with localcontext() as ctx:
            ctx.prec=40
            for s,pos in account.positions.items():
                total=sum((self.quantity[o][s] for o in OWNERS),Z)
                if total!=pos.quantity:raise AssertionError('ACTUAL_OWNER_QUANTITY_BRIDGE')
                if total==0:
                    if pos.isolated_balance!=0:raise AssertionError('FLAT_NATIVE_MARGIN_UNATTRIBUTED')
                    continue
                if any(q*total<0 for q in (self.quantity[o][s] for o in OWNERS)):
                    raise AssertionError('OPPOSING_OWNER_INVENTORY_FORBIDDEN')
                base=pos.isolated_balance*abs(self.quantity[BASE][s])/abs(total)
                result[BASE]+=base;result[FINITE]+=pos.isolated_balance-base
        return result

    def reconcile(self,account):
        margins=self.margins(account)
        with localcontext() as ctx:
            ctx.prec=40
            if sum(self.fees.values(),Z)!=account.fees:raise AssertionError('OWNER_FEE_BRIDGE')
            if sum(self.execution_cost.values(),Z)!=account.execution_cost:raise AssertionError('OWNER_EXECUTION_COST_BRIDGE')
            funding_bridge=account.funding_cash-sum(self.funding.values(),Z)
            # Exact native event totals and independently accumulated owner
            # totals can differ by a Decimal ulp. Preserve every allocation;
            # expose native minus owners, never credit it to owner economics.
            if abs(funding_bridge)>D('1e-25'):raise AssertionError('OWNER_FUNDING_BRIDGE:'+str(funding_bridge))
            realized_bridge=account.realized_PnL-sum(self.realized.values(),Z)
            native_unrealized=sum((p.quantity*(account.marks[s][-1]['price']-p.entry_price)
                for s,p in account.positions.items() if p.quantity),Z)
            unrealized_bridge=native_unrealized-sum((self.unrealized(o,account) for o in OWNERS),Z)
            owner_pnl={o:self.pnl(o,account) for o in OWNERS}
            residual=account.nav()-D('10000')-sum(owner_pnl.values(),Z)
            # Preserve the residual explicitly. Never add it to an owner's PnL,
            # position, margin, cash, or fee to make a test appear exact.
            if abs(residual)>D('1e-25'):raise AssertionError('OWNER_ECONOMIC_PNL_UNRECONCILED:'+str(residual))
            return {'owner_quantities':{o:{s:str(q) for s,q in self.quantity[o].items()} for o in OWNERS},
                'actual_attributed_isolated_margin':{o:str(v) for o,v in margins.items()},
                'owner_actual_fill_net_PnL':{o:str(v) for o,v in owner_pnl.items()},
                'native_wallet_net_PnL':str(account.nav()-D('10000')),
                'native_realized_classification_bridge':str(realized_bridge),
                'native_unrealized_classification_bridge':str(unrealized_bridge),
                'explicit_cumulative_funding_rounding_bridge':str(funding_bridge),
                'funding_rounding_bridge_convention':'USDT; native cumulative funding minus summed owner cumulative funding; independent Decimal40 addition order; never allocated as owner profit or cash',
                'explicit_decimal_rounding_bridge':str(residual),
                'economic_rounding_bridge_convention':'USDT; native NAV minus 10000 minus summed owner actual-fill net PnL; never allocated to an owner',
                'owner_cash_accounts':False,'synthetic_cash_transfers':False}

    def snapshot(self):
        return {'quantity':{o:{s:str(v) for s,v in x.items()} for o,x in self.quantity.items()},
                'basis':{o:{s:str(v) for s,v in x.items()} for o,x in self.basis.items()},
                **{k:{o:str(v) for o,v in getattr(self,k).items()} for k in
                    ('realized','fees','execution_cost','funding','funding_debits','realized_losses')},
                'fill_allocations':deepcopy(self.fill_allocations),'funding_allocations':deepcopy(self.funding_allocations)}
