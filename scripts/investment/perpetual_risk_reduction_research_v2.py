"""UNRUN D046: four303D LONG_SHORT controls with product-legal risk reductions.

Only original simulate's RISK_REDUCTION requested-quantity and completion
branches are privately patched. The original account/DAILY_TARGET/clock,
capacity, fees, floor/min-notional and marks/caps remain immutable. A larger
legal reduce-only order can overshoot the risk target toward zero, never add
risk or cross zero. Less-than10USDT capacity or whole-position dust cannot be
fabricated into a fill. This cache draft has not run Python or read payloads.
"""
from __future__ import annotations
import argparse, ast
from decimal import Decimal as D, ROUND_CEILING, localcontext
from pathlib import Path
from types import SimpleNamespace
from quant.paths import ROOT
from quant.execution_contract import ExecutionContractV2
from scripts.investment import perpetual_303_research as parent
from scripts.investment import perpetual_directional as base
from scripts.investment import public_sma_perpetual as sma
from scripts.investment import public_long_development_adapter as private

PARENT='scripts/investment/perpetual_303_research.py'
PARENT_SHA='fe72e7f1a1913c890148927374d5aea43d4911280ac6645b512ccc791a583832'
CONTROLLER='scripts/investment/perpetual_directional.py'
CONTROLLER_SHA='547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3'
ACCOUNT='src/quant/perpetual_account.py'
ACCOUNT_SHA='cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261'
CONTRACT='D046_FIXED303D_LONG_SHORT_PRODUCT_LEGAL_RISK_REDUCTION_V1'
STATUS='COMPLETE_D046_FOUR_FIXED303D_LONG_SHORT_RISK_REDUCTION_CONTROLS_NOT_NATIVE_OR_LONG_TERM_APR'
STEP,MIN_NOTIONAL=D('0.00000001'),D('10')
MODES=('LONG_SHORT',)
RISK_FIX=dict(request_scope='RISK_REDUCTION_REDUCE_ONLY_AT_ORIGINAL_ELIGIBLE_ATTEMPT',
    quantity_rule='MIN_ABS_POSITION_OF_MAX_CEIL_DELTA_STEP_AND_CEIL_MIN10_OVER_CURRENT_DIRECTIONAL_FILL',
    minimum_filter_scope='DECLARED_RESEARCH_FILTERS_NOT_NATIVE_BYBIT_FILTER_CERTIFICATION',
    completion_rule='EXACT_TARGET_OR_SAME_SIGN_ABS_POSITION_LE_TARGET_OR_FLAT',
    arithmetic='DECIMAL40_CEILING_AND_EXACT_MINNOTIONAL_NO_EPSILON',
    execution_quote='CAUSALLY_AVAILABLE_CURRENT_TRADE_OPEN_ORIGINAL_DIRECTIONAL_SPREAD_SLIPPAGE',
    future_quote_used=False,capacity_override=False,cap_or_fee_loosened=False,
    general_DAILY_TARGET_or_TERMINAL_change=False)
RULES=dict(parent.RULES,strategy_design=[dict(strategy_id=parent.SMA_ID,mode='LONG_SHORT')],
    planned_selectors=4,planned_trading_account_simulations=4,planned_constant_cash_baselines=0,
    risk_reduction_product_normalization=RISK_FIX,
    classification='ONE_COMPLETE_SEEN303_WINDOW_NEW_RISK_CORRECTNESS_CONTROL',
    unchanged_saved_comparisons_not_replayed=16)
PINS=dict(parent.PINS,**{PARENT:PARENT_SHA})


def _ceil_step(value):
    return (value/STEP).to_integral_value(rounding=ROUND_CEILING)*STEP


def risk_reduction_request(position,target,trade_mid,cost):
    """Only a signed reduction; do not modify the frozen signal target.

    Caller runs at the original permitted fill clock. Quote/capacity belongs
    to that attempt; the risk target does not use a future quote. The core's
    original capacity/floor/min10 check remains authoritative for any fill.
    """
    position,target,mid=(D(str(v)) for v in (position,target,trade_mid))
    base.need(all(v.is_finite() for v in (position,target,mid)) and mid>0
        and abs(position)%STEP==0 and position*target>=0 and abs(target)<=abs(position),
        'Known finite quote and same-side lot inventory reducing toward target only')
    if position==target:return D(0)
    with localcontext() as ctx:
        ctx.prec=40
        direction=D(1) if position<0 else D(-1)
        rate=D(str(ExecutionContractV2.execution_rate(float(cost['half_spread_bps']),float(cost['slippage_bps']))))
        fill=mid*(1+direction*rate)
        base.need(fill>0,'Positive original directional execution price')
        minimum=_ceil_step(MIN_NOTIONAL/fill)
        # Division can round only its intermediate quotient. Check the exact
        # declared notional at the same precision as the immutable fill core.
        if minimum*fill<MIN_NOTIONAL:minimum+=STEP
        requested=max(_ceil_step(abs(target-position)),minimum)
        return min(abs(position),requested)


def risk_target_reached(target,position):
    """Exact direction predicate, no tolerance or permission to increase."""
    target,position=D(str(target)),D(str(position))
    base.need(target.is_finite() and position.is_finite(),'Finite risk completion inventory')
    return position==0 or position==target or position*target>0 and abs(position)<=abs(target)


def adapted_simulate(strategy=None):
    """Two exact original simulate anchors, compiled before any market IO."""
    for path,digest in ((CONTROLLER,CONTROLLER_SHA),(ACCOUNT,ACCOUNT_SHA)):
        base.need(base.sha(ROOT/path)==digest,'Unchanged controller/account source '+path)
    receipt=[]
    def transform(node,changes):
        node=private.native._replace(node,changes,'RISK_REDUCTION_LEGAL_GROSS_REQUEST_ONLY',
            'requested=min(abs(delta),abs(position))',
            "requested=min(abs(delta),abs(position))\nif order['kind']=='RISK_REDUCTION':\n    requested=risk_reduction_request(position,target,D(str(window['market'][s]['open'][index])),cost)")
        return private.literal(node,changes,'RISK_REDUCTION_DIRECTIONAL_COMPLETION_ONLY',
            'remaining==0',
            "remaining==0 or (order['kind']=='RISK_REDUCTION' and risk_target_reached(order['target'],account.positions[s].quantity))",1)
    namespace=private.namespace(base,['simulate'],dict(strategy=sma if strategy is None else strategy,
        risk_reduction_request=risk_reduction_request,risk_target_reached=risk_target_reached),receipt,transform)
    base.need(len(receipt)==1 and len(receipt[0]['changes'])==2
        and all(row['matches']==1 for row in receipt[0]['changes']),
        'Only two unique original risk-reduction AST changes')
    return namespace['simulate'],receipt


def context(spec):
    """Reuse original303 input view; no source, account or old-control replay."""
    base.need(spec['contract_id']==CONTRACT and spec['rules']==RULES and spec['period_ids']==[parent.PERIOD]
        and spec['cost_scenarios']==base.COSTS and spec['unit_scenarios']==base.UNITS
        and spec['input_manifest']['path']==parent.INPUT,'Exactly four303 LS cost/unit controls')
    base.need(spec['preceding_failed_source']==parent.PRECEDING_FAILURE,'Rejected547 source preserved')
    for path,digest in PINS.items():
        base.need(base.sha(ROOT/path)==digest and spec['frozen_sources'][path]==digest,'Frozen reused scientific source '+path)
    parent.metadata_view(base.relative_proof(spec['input_manifest']))
    simulation,derivation=adapted_simulate()
    strategy=SimpleNamespace(MODES=MODES,fixed_targets=sma.fixed_targets)
    def transform(node,changes):
        node=private.literal(node,changes,'ONLY303_PERIOD_CLI',"['122D','90D','BOTH']","['303D','BOTH']",1)
        node=private.literal(node,changes,'ONLY303_PERIOD_METADATA',"['122D','90D']","['303D']",1)
        node=private.literal(node,changes,'ONLY_FOUR_NEW_LS_ACCOUNTS','len(selected)*12','len(selected)*4',1)
        cash=[part for part in ast.walk(node) if isinstance(part,ast.keyword) and part.arg=='planned_constant_cash_baselines']
        base.need(len(cash)==1 and ast.dump(cash[0].value,include_attributes=False)
            ==ast.dump(ast.parse('len(selected)',mode='eval').body,include_attributes=False),
            'One exact original planned CASH count metadata keyword')
        cash[0].value=ast.Constant(0);changes.append(dict(change='ZERO_NEW_CASH_BASELINES',matches=1))
        node=private.native._replace(node,changes,'EXACT_NEW_REDUCTION_DERIVATION',
            "write(run/'RUN_BINDING.json',binding)",
            "binding['private_risk_reduction_derivation']=PRIVATE_DERIVATION\nwrite(run/'RUN_BINDING.json',binding)")
        node=private.native._replace(node,changes,'DISTINCT_STRATEGY_SELECTOR_METADATA',
            "result['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))",
            "saved['summary']['strategy_id']=SMA_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,selector_mode=mode,strategy_id=SMA_ID,cost_id=cost['id'],unit_id=unit['id'],**saved))")
        return private.literal(node,changes,'CORRECTNESS_CONTROL_NOT_ALPHA_SELECTION',
            "'Same product and capital four-direction comparison'",
            "'Four fixed303 LONG_SHORT product-legal risk reduction controls; preserve original prefix halt'",1)
    namespace=private.namespace(base,['main'],dict(__file__=__file__,CONTRACT=CONTRACT,STATUS=STATUS,
        MANIFEST_STATUS=parent.MANIFEST_STATUS,RULES=RULES,strategy=strategy,
        relative_proof=parent.relative_proof,load_window=base.load_window,simulate=simulation,
        PRIVATE_DERIVATION=derivation,SMA_ID=parent.SMA_ID),derivation,transform)
    return dict(main=namespace['main'],simulate=simulation,derivation=derivation)


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--protocol',type=Path,required=True)
    args,_=parser.parse_known_args();context(base.small(args.protocol))['main']()


if __name__=='__main__':main()