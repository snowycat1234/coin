"""UNRUN D045 draft: one complete303-day window, original financial body reused.

Source acceptance is pending. This file is not an accepted run/protocol or a
replacement for the failed547-day design. No source arrays, QA, Python tests,
HTTP or financial account execution were used while preparing this draft.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from types import SimpleNamespace
from quant.paths import ROOT
from scripts.investment import perpetual_213_research as prior
from scripts.investment import perpetual_directional as base
from scripts.investment import public_sma_perpetual as sma
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import public_long_development_adapter as private

CONTRACT='D045_FIXED_303D_SMA_DIRECTIONS_AND_CONSTANT_LONG_CONDITIONAL_V1'
STATUS='COMPLETE_D045_FIXED303D_PERPETUAL_SCREENING_NOT_NATIVE_OR_LONG_TERM_APR'
MANIFEST_STATUS='PASS_D045_FIXED_303D_USDM_INPUT_SOURCE_BINDING_NOT_ECONOMICS'
INPUT='reports/fast_research/PERPETUAL_303D_INPUT_BINDING_20261003_V1.json'
PERIOD,START,END='303D','2024-09-01T00:00:00+00:00','2025-07-01T00:00:00+00:00'
SMA_ID=prior.SMA_ID
HOLD_ID,HOLD_SELECTOR=hold.STRATEGY_ID,'HOLD_LONG_ONLY'
SELECTORS=(*sma.MODES,HOLD_SELECTOR)
PRECEDING_FAILURE=prior.PRECEDING_FAILURE
PINS={
    'src/quant/perpetual_account.py':'cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261',
    'scripts/investment/perpetual_directional.py':'547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3',
    'scripts/investment/public_sma_perpetual.py':'c90a9d383fe3365681bfdd5772c0f8a9a8977d57e423627b9159098ce25f30df',
    'scripts/investment/vol_managed_perpetual_target.py':'63cb91583a70efe1ae2be0607370713cd98828d298cb09cb1da2adf41cdd11d6',
    'scripts/investment/public_long_development_adapter.py':'15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f',
    'scripts/investment/perpetual_213_research.py':'e4cc8fe6d4a490e078a794f6b0a842d9fe99a196f7c0beefe2c6b7637d8d9f7c',
}
RULES=dict(base.RULES,period_id=PERIOD,score_start=START,score_end_exclusive=END,
    strategy_design=[dict(strategy_id=SMA_ID,mode=mode) for mode in sma.MODES]
        +[dict(strategy_id=HOLD_ID,mode='LONG_ONLY')],planned_selectors=20,
    planned_trading_account_simulations=16,planned_constant_cash_baselines=1,
    fresh_flat_each_strategy_direction=True,no_saved_old_financial_accounts_replayed=True,
    signal_histories='200_COMPLETED_DAILY_SMA_OR_CONSTANT_LONG_WITH_SAME_ELIGIBILITY',
    risk_histories='SAME30_COMPLETED_UTC_DAILY_RETURN_COVARIANCE',
    conditional_unit_scenarios_are_sensitivity_not_HPO=True,
    classification='ONE_COMPLETE_SEEN303_WINDOW_NOT_REPAIRED_OR_STITCHED547',
    original_547D_source_failure_preserved=True,original_547D_source_completed=False,
    old_Spot_EWMA_reference_replicated=False,realized_risk_equalized=False)


def metadata_view(manifest):
    """Only exact scalar source roles; no source payload or implicit index/2h IO."""
    base.need(manifest['status']==MANIFEST_STATUS and manifest['funding_rate_unit']=='UNCONFIRMED'
        and manifest['funding_unit_certified'] is False and manifest['locked_consumed'] is False,
        'Accepted303 source-only metadata without unit qualification')
    base.need(len(manifest['windows'])==1 and len(manifest['source_files'])==94,'Exact94 explicit303 source entries')
    window=manifest['windows'][0]
    base.need((window['id'],window['start'],window['end_exclusive'],window['days'],window['minutes_per_symbol'])
        ==(PERIOD,START,END,303,436320),'One complete independent303-day score calendar')
    layout={
        'trade_1m':('trade:1m:','USD_M_PERPETUAL_TRADE_KLINES','2024-09','2025-06'),
        'mark_1m':('markPriceKlines:','USD_M_PERPETUAL_markPriceKlines','2024-09','2025-06'),
        'funding':('fundingRate:','USD_M_PERPETUAL_fundingRate','2024-09','2025-06'),
        'trade_1d_warmup':('trade:1d:','USD_M_PERPETUAL_TRADE_KLINES','2024-02','2024-08'),
        'trade_1d_score':('trade:1d:','USD_M_PERPETUAL_TRADE_KLINES','2024-09','2025-06'),
    }
    files=manifest['source_files'];symbols={};used=[]
    for symbol in base.SYMBOLS:
        roles=window['source_ids'][symbol];base.need(set(roles)==set(layout),'Exactly five used roles, no index/Spot/2h substitution')
        for role,(prefix,product,lower,upper) in layout.items():
            expected=[prefix+symbol+':'+month for month in prior.months(lower,upper)]
            base.need(roles[role]==expected,'Exact303 symbol/product/month chronology '+symbol+' '+role)
            for identity in expected:
                item=files[identity];base.need(item['symbol']==symbol and item['month']==identity[-7:]
                    and item['product']==product and type(item['rows']) is int and item['rows']>0,
                    'Exact accepted source record with actual row/event count')
            used.extend(expected)
        counts={role:sum(files[key]['rows'] for key in ids) for role,ids in roles.items()}
        base.need(counts['trade_1m']==counts['mark_1m']==436320 and counts['trade_1d_warmup']==213
            and counts['trade_1d_score']==303,'Complete303 minute calendar and213 completed warmup days')
        symbols[symbol]=dict(source_ids=roles,rows_inherited_from_receipts={'funding':counts['funding']})
    base.need(len(used)==len(set(used))==94 and set(used)==set(files),'Every explicit source consumed exactly once in metadata')
    return dict(manifest,windows=[dict(window,symbols=symbols)])


def relative_proof(ref):
    value=base.relative_proof(ref)
    return metadata_view(value) if ref['path']==INPUT else value


def context(spec):
    """Compile every exact private metadata anchor before any source array."""
    base.need(spec['contract_id']==CONTRACT and spec['rules']==RULES and spec['period_ids']==[PERIOD]
        and spec['cost_scenarios']==base.COSTS and spec['unit_scenarios']==base.UNITS
        and spec['input_manifest']['path']==INPUT,'One303 window and twenty fixed sensitivity selectors')
    base.need(spec['preceding_failed_source']==PRECEDING_FAILURE,'Original547 source defect is not repaired or hidden')
    failed=base.relative_proof(PRECEDING_FAILURE)
    base.need(failed['completed_files']==83 and failed['required_files']==148 and failed['source_acceptance_granted'] is False,
        'Rejected original547 remains rejected')
    for name,digest in PINS.items():base.need(base.sha(ROOT/name)==digest and spec['frozen_sources'][name]==digest,'Frozen reused code '+name)
    metadata_view(base.relative_proof(spec['input_manifest']))
    derivation=[]
    original=private.namespace(base,['simulate'],dict(strategy=sma),derivation)['simulate']
    derivation[-1]['target_binding']='ORIGINAL_SMA_FOUR_DIRECTIONS'
    reference=private.namespace(base,['simulate'],dict(strategy=SimpleNamespace(fixed_targets=hold.fixed_targets)),derivation)['simulate']
    derivation[-1]['target_binding']='D044_CONSTANT_LONG_SAME_PAST30_COVARIANCE'

    def dispatch(window,mode,cost,unit,progress=None,guard=None):
        return (reference(window,'LONG_ONLY',cost,unit,progress,guard) if mode==HOLD_SELECTOR
            else original(window,mode,cost,unit,progress,guard))

    def transform(node,changes):
        node=private.literal(node,changes,'ONE_FIXED_PERIOD_CLI',"['122D','90D','BOTH']","['303D','BOTH']",1)
        node=private.literal(node,changes,'ONE_FIXED_PERIOD_METADATA',"['122D','90D']","['303D']",1)
        node=private.literal(node,changes,'SIXTEEN_PHYSICAL_TRADING_ACCOUNTS','len(selected)*12','len(selected)*16',1)
        node=private.native._replace(node,changes,'RECORD_PRIVATE_METADATA_AND_SIGNAL_DERIVATION',
            "write(run/'RUN_BINDING.json',binding)","binding['private_history_derivation']=PRIVATE_DERIVATION\nwrite(run/'RUN_BINDING.json',binding)")
        before="result['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))"
        after="saved['summary']['strategy_id']=HOLD_ID if mode==HOLD_SELECTOR else SMA_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode='LONG_ONLY' if mode==HOLD_SELECTOR else mode,strategy_id=saved['summary']['strategy_id'],selector_mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))"
        node=private.native._replace(node,changes,'CANONICAL_DIRECTION_AND_EXPLICIT_STRATEGY_ID',before,after)
        node=private.literal(node,changes,'HONEST_FIVE_SELECTOR_FEATURE_METADATA',"'ORIGINAL_PUBLIC_SMA50_200_DAILY_SIGNED'","'ORIGINAL_SMA_DAILY_AND_CONSTANT_LONG_FIXED303'",1)
        return private.literal(node,changes,'PREDECLARED_COMPLETE_WINDOW_REASON',
            "'Same product and capital four-direction comparison'","'Complete303 independent window; failed547 remains rejected; same-product beta control'",1)

    strategy=SimpleNamespace(MODES=SELECTORS,fixed_targets=sma.fixed_targets)
    env=private.namespace(base,['main'],dict(__file__=__file__,CONTRACT=CONTRACT,STATUS=STATUS,MANIFEST_STATUS=MANIFEST_STATUS,
        RULES=RULES,strategy=strategy,relative_proof=relative_proof,load_window=base.load_window,simulate=dispatch,
        PRIVATE_DERIVATION=derivation,SMA_ID=SMA_ID,HOLD_ID=HOLD_ID,HOLD_SELECTOR=HOLD_SELECTOR),derivation,transform)
    return dict(main=env['main'],simulate=dispatch,simulate_SMA=original,simulate_HOLD=reference,
        load_window=base.load_window,derivation=derivation)


def main():
    parser=argparse.ArgumentParser(add_help=False);parser.add_argument('--protocol',type=Path,required=True)
    args,_=parser.parse_known_args();context(base.small(args.protocol))['main']()

if __name__=='__main__':main()