"""Prepared D032-only independent gate hook over the accepted pair finance span.
No production gate/account function is called; no account loop is copied here.
"""
import ast, copy, hashlib, math
from decimal import Decimal, localcontext
from pathlib import Path
DAY=86_400_000_000
EXIT_REASON='PAST_OWNED_FUNDING_7D_LAG1_NONPOSITIVE_PERMANENT_CASH'

class GateAudit:
    def __init__(self,core):
        self.core=core;self.rows=[];self.checks=[];self.numeric=[]
    def record(self,saved,independent_cash):
        c=self.core
        c.need(type(saved['event_us']) is int and type(saved['ownership_qualified']) is bool,'Original gate clock/ownership')
        c.number(saved['signed_funding_USDT']);c.close(saved['signed_funding_USDT'],independent_cash)
        self.rows.append(dict(event_us=saved['event_us'],owned=saved['ownership_qualified'],
            credited=saved['signed_funding_USDT'],independent_cash=independent_cash))
    def witness(self,day_close,entry):
        c=self.core;c.need(type(day_close) is int and day_close%DAY==0,'Exact independent UTC gate boundary')
        seen=day_close+1;lo=day_close-8*DAY;hi=day_close-DAY
        w=dict(decision_price_close_us=day_close,decision_observation_us=seen,window_start_us=lo,
            window_end_exclusive_us=hi,entry_us=entry,publication_assumption='UNCERTIFIED_ONE_UTC_DAY_LAG',
            historical_availability_certified=False,eligible=False,action='NO_ACTION',
            selected_row_indices=[],selected_event_times_us=[],owned_event_count=0,
            signed_owned_funding_sum_USDT=None,maximum_assumed_available_us=None)
        if seen-entry<8*DAY:w['reason']='HOLD_LESS_THAN_EXACT_EIGHT_DAYS';return w
        if lo<=entry:w['reason']='WINDOW_START_NOT_STRICTLY_AFTER_ENTRY';return w
        selected=[(i,r) for i,r in enumerate(self.rows) if lo<=r['event_us']<hi and r['owned']]
        amounts=[r['credited'] for i,r in selected];total=math.fsum(amounts)
        # Exact finite Float64 Decimal sum, independent of the wallet's arithmetic context.
        with localcontext() as context:
            context.prec=2000
            exact_credited=sum((Decimal.from_float(float(v)) for v in amounts),Decimal(0))
            independent=sum((r['independent_cash'] for i,r in selected),Decimal(0))
        disagreement=len({total<=0.,exact_credited<=0,independent<=0})>1
        c.close(total,independent,c.USDT_TOL)
        stamps=[r['event_us'] for i,r in selected]
        c.need(all(t+DAY<seen for t in stamps),'No recent/current/future event in lagged owned cash')
        w.update(eligible=True,reason='FIXED_FULL_WINDOW_UNCERTIFIED_OWNED_CASH',
            selected_row_indices=[i for i,r in selected],selected_event_times_us=stamps,
            owned_event_count=len(selected),signed_owned_funding_sum_USDT=total,
            maximum_assumed_available_us=max(stamps)+DAY if stamps else None,condition_met=total<=0.)
        self.numeric.append(dict(decision_observation_us=seen,fsum_actual_credited_USDT=total,
            exact_selected_credited_float_Decimal_sum_USDT=str(exact_credited),
            independent_wallet_Decimal_sum_USDT=str(independent),
            float_condition_met=total<=0.,exact_credited_condition_met=exact_credited<=0,
            independent_condition_met=independent<=0,
            predicate_sign_disagreement=disagreement,rounding_sensitive_trigger=disagreement,
            status='ROUNDING_SENSITIVE_TRIGGER_WITNESS' if disagreement else 'NO_SIGN_DISAGREEMENT',
            predicate='EXACT_MATH_FSUM_ACTUAL_INDEPENDENTLY_AUDITED_FLOAT_CREDITS_LE_ZERO_NO_EPS',
            amount_comparison_tolerance_USDT=str(c.USDT_TOL)))
        return w
    def verify(self,summary):
        c=self.core;saved=summary['past_funding_gate_checks'];c.need(len(saved)==len(self.checks),'Every daily gate witness')
        for got,expected in zip(saved,self.checks,strict=True):
            c.need(set(got)==set(expected),'Frozen gate witness schema')
            for key,value in expected.items():
                if key=='signed_owned_funding_sum_USDT' and value is not None:
                    c.need(type(got[key]) in (int,float) and got[key]==value,'Exact primary Float64 fsum predicate witness')
                else:c.need(got[key]==value,'Independent causal gate mismatch:'+key)
        c.need(summary['past_funding_gate_scheduled']==sum(r['action']=='SCHEDULE_PERMANENT_FULL_EXIT' for r in self.checks)
               and summary['funding_gate_publication_certified'] is False,'No gate availability certification')

GATE_STATE='''
tracker=GateAudit(core)
def independent_past_gate(index,closed,stamp):
    nonlocal full_pending,exit_time,exit_reason,stop_signal
    if not held or closed%DAY:return
    witness=tracker.witness(closed,entry)
    witness.update(account_state='HELD',pending_full_exit_before=full_pending,pending_pair_symbols_before=sorted(pending))
    if witness['eligible']:
        if full_pending is not None:
            witness.update(action='KEEP_ALREADY_PENDING_FULL_EXIT',existing_exit_reason=exit_reason)
        elif witness['condition_met']:
            following=(stamp-(START+STEP))//STEP+1
            if following>=COUNT:
                witness.update(action='NO_FUTURE_CLOSED_PRICE_FIXED_TERMINAL_ONLY')
            else:
                full_pending=following;stop_signal=stamp;exit_time=START+(following+1)*STEP+1;exit_reason=EXIT_REASON
                witness.update(action='SCHEDULE_PERMANENT_FULL_EXIT',fill_index=following,
                    scheduled_fill_price_close_us=START+(following+1)*STEP,scheduled_fill_us=exit_time)
    tracker.checks.append(witness)
'''

def financial(core,accepted_pair,delta,calendar):
    """Resolve exact spans and hooks before any arrays; two calendars only."""
    source=Path(accepted_pair.__file__);tree=ast.parse(source.read_text())
    main=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='main']
    core.need(len(main)==1,'One accepted independent pair entry')
    trials=[n for n in main[0].body if isinstance(n,ast.Try)];core.need(len(trials)==1,'One guarded financial span')
    body=trials[0].body
    def assigned(n,name):return isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)
    begin=[i for i,n in enumerate(body) if assigned(n,'wallet')];end=[i for i,n in enumerate(body) if assigned(n,'receipt')]
    core.need(len(begin)==len(end)==1 and begin[0]<end[0],'Unique accepted pair finance begin/end')
    nodes=copy.deepcopy(body[begin[0]:end[0]])
    original=ast.dump(ast.Module(body=nodes,type_ignores=[]),include_attributes=False)
    old_values={732:calendar['events'],122:calendar['days']};changes=[]
    for root in nodes:
        for n in ast.walk(root):
            if isinstance(n,ast.Constant) and type(n.value) is int and n.value in old_values:
                old=n.value;n.value=old_values[old];changes.append(dict(old=old,new=n.value,line=n.lineno))
    core.need({r['old'] for r in changes}=={732,122},'Pair literals only; minute grid remains COUNT namespace')
    counts={'record':0,'dispatch':0}
    record_old=ast.dump(ast.parse('owned+=qual').body[0],include_attributes=False)
    dispatch_old=ast.dump(ast.parse("risk(index,stamp,'CLOSED_MINUTE_BEFORE_SCHEDULED_FILLS')").body[0],include_attributes=False)
    def inject(parent):
        for field,value in ast.iter_fields(parent):
            if isinstance(value,list):
                result=[]
                for item in value:
                    if isinstance(item,ast.AST):
                        tag=ast.dump(item,include_attributes=False)
                        if tag==record_old:
                            result.extend(ast.parse('tracker.record(saved,wallet.funding-prior_fund)').body);counts['record']+=1
                        inject(item);result.append(item)
                        if tag==dispatch_old:
                            result.extend(ast.parse('independent_past_gate(index,closed,stamp)').body);counts['dispatch']+=1
                    else:result.append(item)
                setattr(parent,field,result)
            elif isinstance(value,ast.AST):inject(value)
    module=ast.Module(body=nodes,type_ignores=[]);inject(module)
    core.need(counts==dict(record=1,dispatch=1),'One funding-history hook and exact gate dispatch hook')
    prefix=ast.parse(GATE_STATE).body
    suffix=ast.parse('tracker.verify(summary)\nreturn locals()').body
    params=('actual','summary','prices','events','frames','fills','fundrows','daily','report')
    function=ast.FunctionDef(name='verify_pair_finance_with_independent_gate',
        args=ast.arguments(posonlyargs=[],args=[ast.arg(arg=p) for p in params],vararg=None,
            kwonlyargs=[],kw_defaults=[],kwarg=None,defaults=[]),
        body=prefix+module.body+suffix,decorator_list=[],type_params=[])
    compiled=ast.fix_missing_locations(ast.Module(body=[function],type_ignores=[]))
    namespace=dict(vars(accepted_pair));namespace.update(core=core,delta=delta,need=core.need,close=core.close,
        number=core.number,D=core.D,Z=core.ZERO,START=calendar['start'],END=calendar['end'],COUNT=calendar['minutes'],
        MONTHS=tuple(calendar['months']),GateAudit=GateAudit,DAY=DAY,EXIT_REASON=EXIT_REASON)
    exec(compile(compiled,str(source)+':D032_INDEPENDENT_GATE_ONLY','exec'),namespace)
    return namespace[function.name],dict(accepted_pair_source_path=str(source),start_line=nodes[0].lineno,
        end_line=nodes[-1].end_lineno,original_financial_AST_sha256=hashlib.sha256(original.encode()).hexdigest(),
        derived_financial_AST_sha256=hashlib.sha256(ast.dump(compiled,include_attributes=False).encode()).hexdigest(),
        period_literal_changes=changes,new_gate_hook_counts=counts,
        old_fee_wallet_margin_cap_and_partial_statements_unchanged=True,production_simulate_called=False)