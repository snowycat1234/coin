"""UNRUN D046: four new303D LONG_SHORT accounts; unchanged accepted finance.

CLI --protocol --actual --run-dir --output; ACTUAL_BINDING follows D045.
Only this draft is new. The D045 context is privately cloned; its generated
main receives exact four-route AST changes immediately before compilation.
Reader, target_reference, audit_case, HandLedger and tolerances stay direct
accepted references. HOLD may be imported by the accepted prepare_stack but
its target function is never called. No CASH/HOLD or old financial replay.
The parent must freeze protocol/actual closed0 and the compact source map.
No Python, compile, arrays, LOCK, HTTP or finance has prepared this file.
"""
from __future__ import annotations
import ast, builtins, copy, hashlib, importlib.util, sys
from pathlib import Path
from types import FunctionType

ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
PARENT='docs/archive/PERPETUAL_303_FINANCIAL_INDEPENDENT_AUDITOR_20261003_V1.py'
PARENT_SHA='7b54675ca3c5c25932233cc3aa8d94be0dae8951faaa56c322e6d24ac97b170c'
PARENT_ROOT='reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json'
PARENT_ROOT_SHA='841a525d41162bbcbaedb14b0be0c3696bcf3356cfdb76542a864662797c4f58'
PARENT_ACTUAL='reports/fast_research/PERPETUAL_303_RESEARCH_ACTUAL_20261003_V1.json'
PARENT_ACTUAL_SHA='de350689cdfa86a40ee1d083795578d215c657e627d6d18b2885b2e59c1dfca3'
PARENT_FINANCE='reports/fast_research/PERPETUAL_303_RESEARCH_INDEPENDENT_20261003_V1.json'
PARENT_FINANCE_SHA='f2d3a9402b9606f30243caf6c274be2ae0e45af41b43ac173822f4ea72d79699'
CONTRACT='D046_FIXED303D_LONG_SHORT_PRODUCT_LEGAL_RISK_REDUCTION_V1'
ACTUAL_STATUS='COMPLETE_D046_FOUR_FIXED303D_LONG_SHORT_RISK_REDUCTION_CONTROLS_NOT_NATIVE_OR_LONG_TERM_APR'
STATUS='PASS_D046_FOUR_FIXED303D_LONG_SHORT_PERPETUAL_NUMERICAL_ACCOUNTING_AND_CAUSAL_SCOPE_NOT_NATIVE_OR_LONG_TERM_APR'
FAIL='FAIL_D046_FOUR_FIXED303D_LONG_SHORT_PERPETUAL_INDEPENDENT_AUDIT'
RUN=STATE/'d046-perpetual-risk-reduction-financial-independent-20261003-v1'
OUT=ROOT/'reports/fast_research/PERPETUAL_RISK_REDUCTION_INDEPENDENT_20261003_V1.json'


def need(ok,message):
    if not bool(ok):raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def parent_capability(spec,plan,g,fin,report):
    """Read one accepted small capability, not its old finance/QA payloads.

    Producer binding still matches its entire frozen_sources exactly. Only
    compact actual direct dependencies and capability references enter this
    audit's source map/registry; the historical union is not expanded.
    """
    need(plan['source_hashes'].get(PARENT_ROOT)==PARENT_ROOT_SHA
        and plan['source_hashes'].get(PARENT)==PARENT_SHA,
        'Accepted D045 orchestration and root capability explicitly pinned')
    prior,digest=g.small(fin.project(g,PARENT_ROOT),PARENT_ROOT_SHA)
    need(prior['status']=='PASS_ROOT_D045_TWENTY_FIXED303D_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
        and prior['completed_cases']==20 and prior['financial_case_calls']==17
        and prior['cash_aliases_verified']==3 and prior['completed_full_calendar_cases']==16
        and prior['incomplete_or_halted_cases']==4
        and prior['verified_actual_reports'].get(PARENT_ACTUAL)==PARENT_ACTUAL_SHA
        and prior['verified_actual_reports'].get(PARENT_FINANCE)==PARENT_FINANCE_SHA,
        'Old accepted scope stays16 full plus4 prefixes; no old replay')
    closed=g.closed(prior['binding']['task_id'])
    # These are economic functions used by the new accounts, not date/risk
    # adapters. The new risk-order route must have its own protocol pin.
    old=prior['scientific_source_hashes']
    for path in ('src/quant/perpetual_account.py',
                 'scripts/investment/public_sma_perpetual.py',
                 'third_party/jesse_example_smacrossover/smacrossover_original.py',
                 'environments/v8/uv.lock'):
        need(spec['frozen_sources'].get(path)==old[path]
            and plan['source_hashes'].get(path)==old[path],
            'Same frozen account/target/vendor/runtime source '+path)
    report['parent_accepted_capability']=dict(path=PARENT_ROOT,sha256=digest,
        actual_report_sha256=PARENT_ACTUAL_SHA,independent_report_sha256=PARENT_FINANCE_SHA,
        closed_task=closed,old_accounts_replayed=False,old_QA_repeated=False)


def transform_main(old,node,changes):
    """Exact changes to orchestration only; never edit a finance function."""
    swap=lambda before,after,label:old.replace_span(node,before,after,label,changes)
    swap("""for path,digest in [*spec['frozen_sources'].items(),*plan['source_hashes'].items()]:
    need(path not in hashes or hashes[path]==digest,'No conflicting source/dependency map');pin(g,fin,path,digest);hashes[path]=digest""",
        """parent_capability(spec,plan,g,fin,report)
for path,digest in plan['source_hashes'].items():
    need(path not in hashes or hashes[path]==digest,'No conflicting compact source/dependency map')
    pin(g,fin,path,digest);hashes[path]=digest""",
        'COMPACT_DIRECT_PINS_WITH_ACCEPTED_D045_CAPABILITY')
    swap("""need(rules['strategy_design']==[dict(strategy_id=SMA_ID,mode=m) for m in MODES[:-1]]
    +[dict(strategy_id=DONCHIAN_ID,mode='LONG_ONLY')],'Four SMA modes and accepted constant-long shared-risk reference')""",
        """need(rules['strategy_design']==[dict(strategy_id=SMA_ID,mode='LONG_SHORT')],
    'Only the original SMA LONG_SHORT family; no CASH/HOLD/new strategy')""",
        'ONLY_ONE_LS_RECIPE')
    swap("""need([c['id'] for c in actual['cases']]==selectors and len(actual['input_windows'])==1
    and actual['planned_trading_account_simulations']==actual['completed_trading_account_simulations']==16
    and actual['planned_constant_cash_baselines']==actual['completed_constant_cash_baselines']==1,
    'All20 selectors,16 physical trading accounts and1 exact constant CASH account')""",
        """need([c['id'] for c in actual['cases']]==selectors and len(selectors)==4
    and len(actual['input_windows'])==1
    and actual['planned_trading_account_simulations']==actual['completed_trading_account_simulations']==4
    and actual['planned_constant_cash_baselines']==actual['completed_constant_cash_baselines']==0,
    'Exactly four new LONG_SHORT accounts, no constant-cash alias')""",
        'EXACT_FOUR_NEW_ACCOUNT_SELECTORS')
    swap("""expected_targets={m:fin.target_reference(w,m) for m in MODES[:-1]}
expected_targets['HOLD_LONG_ONLY']=reference.target_reference(fin,w)
cash_original=cash_verified=None""",
        """expected_targets={'LONG_SHORT':fin.target_reference(w,'LONG_SHORT')}""",
        'ONLY_ACCEPTED_INDEPENDENT_SMA_LS_TARGET')
    swap("""expected_mode='LONG_ONLY' if selector=='HOLD_LONG_ONLY' else selector
strategy=DONCHIAN_ID if selector=='HOLD_LONG_ONLY' else SMA_ID""",
        """expected_mode='LONG_SHORT'
strategy=SMA_ID""",'NO_HOLD_DIRECTION_ALIAS')
    swap("""if selector=='CASH' and cash_original is not None:
    item=cash_alias(fin,case,cash_original,cash_verified,maximum)
    report['shared_CASH_artifact_equivalences_verified']+=1
else:
    item=h.financial_case_interface(fin,w,case,g,hand,run,target,witness,maximum)
    item.update(verification_method='UNCHANGED_ACCEPTED_FULL_FINANCIAL_BODY',financial_body_executed_for_this_selector=True)
    report['financial_case_calls']+=1
    if selector=='CASH':cash_original,cash_verified=case,item""",
        """item=h.financial_case_interface(fin,w,case,g,hand,run,target,witness,maximum)
item.update(verification_method='UNCHANGED_ACCEPTED_FULL_FINANCIAL_BODY',financial_body_executed_for_this_selector=True)
report['financial_case_calls']+=1""",'FOUR_DIRECT_ORIGINAL_FINANCIAL_CALLS_NO_ALIASES')
    swap("""need(len(rows)==20 and report['financial_case_calls']==17 and report['shared_CASH_artifact_equivalences_verified']==3,
    'Truthful17 full financial calls plus3 identical cash aliases, not20 physical replays')""",
        """need(len(rows)==4 and report['financial_case_calls']==4
    and report['shared_CASH_artifact_equivalences_verified']==0,
    'Four actual finance calls, each full or exactprefix; no old calls or aliases')""",
        'TRUTHFUL_FOUR_FINANCE_CALLS')
    labels={
        'D045-303D-TWENTY-FINANCIAL-INDEPENDENT-20261003-V1':'D046-303D-FOUR-LS-FINANCIAL-INDEPENDENT-20261003-V1',
        'SMA_DAILY_FOUR_DIRECTION_AND_CONSTANT_LONG_SHARED_RISK':'SMA_DAILY_LONG_SHORT_ONLY_RISK_ORDER_CORRECTNESS',
        'Actual20 fixed conditional selectors and exact new protocol':'Actual4 fixed LS conditional selectors and exact new protocol',
        '固定303日 · 20选择器独立资金与过去目标':'固定303日 · 四LS风险减仓独立资金验收',
        'FULL_OR_PREFIX_CASE_COUNTS_INCLUDE_EXACT_IDENTICAL_CASH_SELECTOR_ALIASES':'FOUR_NEW_LS_ACCOUNT_FULL_OR_PREFIX_COUNTS_NO_CASH_OR_HOLD_REPLAY'}
    found={key:0 for key in labels};count_anchors={key:0 for key in (
        'actual_count','planned_selectors','planned_trading_account_simulations',
        'planned_constant_cash_baselines','progress_writer','progress_total',
        'required_cases','completed_cases_verified')}
    for part in ast.walk(node):
        if isinstance(part,ast.Constant) and isinstance(part.value,str) and part.value in labels:
            found[part.value]+=1;part.value=labels[part.value]
        # Actual.required_cases == Actual.completed_cases ==20: metadata only.
        if (isinstance(part,ast.Compare) and isinstance(part.left,ast.Subscript)
            and isinstance(part.left.value,ast.Name) and part.left.value.id=='actual'
            and isinstance(part.left.slice,ast.Constant) and part.left.slice.value=='required_cases'):
            need(len(part.comparators)==2 and isinstance(part.comparators[-1],ast.Constant)
                and part.comparators[-1].value==20,'Original actual-count anchor')
            part.comparators[-1]=ast.Constant(4);count_anchors['actual_count']+=1
        if isinstance(part,ast.keyword) and part.arg in (
            'planned_selectors','planned_trading_account_simulations','planned_constant_cash_baselines',
            'required_cases','completed_cases_verified'):
            key=part.arg;expected,new={'planned_selectors':(20,4),
                'planned_trading_account_simulations':(16,4),'planned_constant_cash_baselines':(1,0),
                'required_cases':(20,4),'completed_cases_verified':(20,4)}[key]
            if key=='completed_cases_verified' and isinstance(part.value,ast.Call):
                need(ast.dump(part.value,include_attributes=False)
                    ==ast.dump(ast.parse('len(rows)',mode='eval').body,include_attributes=False),
                    'Finally keeps its truthful dynamic completed-case count')
                continue
            need(isinstance(part.value,ast.Constant) and part.value.value==expected,
                'Exact original metadata count '+key)
            part.value=ast.Constant(new);count_anchors[key]+=1
        if isinstance(part,ast.Call) and isinstance(part.func,ast.Name) and part.func.id=='progress_writer':
            need(len(part.args)==1 and isinstance(part.args[0],ast.Constant)
                and part.args[0].value==20,'Exact original progress total')
            part.args[0]=ast.Constant(4);count_anchors['progress_writer']+=1
        if (isinstance(part,ast.Call) and isinstance(part.func,ast.Attribute)
            and isinstance(part.func.value,ast.Name) and part.func.value.id=='progress'
            and part.func.attr=='update'):
            need(len(part.args)>=4 and isinstance(part.args[2],ast.Constant)
                and part.args[2].value==20 and not any(k.arg=='unit' for k in part.keywords),
                'Original progress call has no duplicate unit kwarg')
            part.args[2]=ast.Constant(4);count_anchors['progress_total']+=1
    need(all(found.values()) and all(value==1 for value in count_anchors.values()),
        'Every exact metadata label/count anchor unique before arrays')
    changes.extend(dict(anchor='metadata_label',old=k,new=labels[k],matches=v) for k,v in found.items())
    changes.extend(dict(anchor=k,matches=v) for k,v in count_anchors.items())
    # There is no remaining independent reference.target_reference call.
    need(not any(isinstance(p,ast.Call) and isinstance(p.func,ast.Attribute)
        and isinstance(p.func.value,ast.Name) and p.func.value.id=='reference'
        and p.func.attr=='target_reference' for p in ast.walk(node)),
        'No independent HOLD target calculation or old account replay')


def context():
    need(not (ROOT/PARENT).is_symlink() and sha(ROOT/PARENT)==PARENT_SHA,
        'Immutable accepted D045 orchestration')
    spec=importlib.util.spec_from_file_location('_d046_accepted_d045',ROOT/PARENT)
    old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
    ns=dict(vars(old),__file__=__file__,CONTRACT=CONTRACT,ACTUAL_STATUS=ACTUAL_STATUS,
        STATUS=STATUS,FAIL=FAIL,RUN=RUN,OUT=OUT,MODES=('LONG_SHORT',),
        parent_capability=parent_capability)
    interceptions=[]
    def compile_route(tree,filename,mode,*args,**kwargs):
        if filename=='<D045-private-303-accepted-audit-main>':
            need(isinstance(tree,ast.Module) and len(tree.body)==1
                and isinstance(tree.body[0],ast.FunctionDef) and tree.body[0].name=='main'
                and not interceptions,'One final D045 generated main compile hook')
            node=copy.deepcopy(tree.body[0]);before=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest();changes=[]
            transform_main(old,node,changes)
            proof=ns['MAIN_PROOF'];proof.update(parent_D045_main_AST_sha256=before,
                derived_main_AST_sha256=hashlib.sha256(ast.dump(node,include_attributes=False).encode()).hexdigest(),
                D046_only_orchestration_changes=changes,HOLD_target_function_called=False,
                old_financial_accounts_replayed=False,compact_source_map_no_historical_union_expansion=True)
            interceptions.append(proof['derived_main_AST_sha256'])
            tree=ast.fix_missing_locations(ast.Module([node],type_ignores=[]))
        return builtins.compile(tree,filename,mode,*args,**kwargs)
    ns['compile']=compile_route
    # Copy just context/prepare_stack function globals, not any finance body.
    # MAIN_PROOF is set by the cloned context and shared with prepare_stack.
    ns['prepare_stack']=FunctionType(old.prepare_stack.__code__,ns,'prepare_stack',
        old.prepare_stack.__defaults__,old.prepare_stack.__closure__)
    make=FunctionType(old.context.__code__,ns,'context',old.context.__defaults__,old.context.__closure__)
    main,proof=make()
    main.__globals__['parent_capability']=parent_capability
    need(len(interceptions)==1 and main.__globals__['MODES']==('LONG_SHORT',)
        and main.__globals__['CONTRACT']==CONTRACT,'Final four-route namespace compiled before payload')
    return main,proof


def main():
    entry,_=context();entry()


if __name__=='__main__':main()
