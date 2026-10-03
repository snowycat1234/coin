"""D044 one constant-long reference, original signed financial body unchanged.

Three complete seen windows use independent whole-capital accounts. The
reference shares past30 covariance sizing, not the old Spot EWMA sleeve.
"""
from __future__ import annotations
import argparse, ast
from pathlib import Path
from types import SimpleNamespace
from quant.paths import ROOT
from scripts.investment import perpetual_directional as base
from scripts.investment import public_long_development_adapter as private
from scripts.investment import vol_managed_perpetual_target as target

CONTRACT='D044_THREE_SEEN_USDM_PAST30_COVARIANCE_HOLD_REFERENCE_V1'
STATUS='COMPLETE_D044_TWELVE_CONDITIONAL_PERPETUAL_HOLD_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
MANIFEST_STATUS='BOUND_D044_THREE_PREVIOUSLY_ACCEPTED_USDM_WINDOWS_NOT_ECONOMICS'
STRATEGY_ID='COIN_PAST30_COVARIANCE_CONSTANT_LONG_USDM_REFERENCE'
PERIODS=['213D','122D','90D']
WINDOWS=[('213D','2024-01-01T00:00:00+00:00','2024-08-01T00:00:00+00:00',213),
    ('122D','2025-08-01T00:00:00+00:00','2025-12-01T00:00:00+00:00',122),
    ('90D','2025-12-01T00:00:00+00:00','2026-03-01T00:00:00+00:00',90)]
PINS={'scripts/investment/perpetual_directional.py':'547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3',
    'src/quant/perpetual_account.py':'cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261',
    'scripts/investment/public_sma_perpetual.py':'c90a9d383fe3365681bfdd5772c0f8a9a8977d57e423627b9159098ce25f30df',
    'scripts/investment/public_long_development_adapter.py':'15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f'}
RULES=dict(base.RULES,modes=['LONG_ONLY'],signal='CONSTANT_LONG_RAW_POINT3_EACH_ASSET_NO_ALPHA_FILTER',
    strategy_id=STRATEGY_ID,planned_selectors=12,planned_trading_account_simulations=12,planned_constant_cash_baselines=0,
    signal_and_risk_timeframe_minutes=1440,raw_targets=[.3,.3],minimum_completed_available_daily_history=200,
    risk_histories='SAME30_COMPLETED_UTC_DAILY_RETURN_COVARIANCE',
    old_Spot_EWMA_reference_replicated=False,original_SMA_alpha_hooks_used=False,
    old_accounts_or_source_QA_replayed=False,classification='THREE_INDEPENDENT_SEEN_DEVELOPMENT_WINDOWS',
    funding_unit_conditions_not_HPO=True,original_547D_source_failure_preserved=True,
    realized_risk_equalized=False)

def context(spec):
    """Metadata and private compilation only; no economic arrays at this stage."""
    base.need(spec['contract_id']==CONTRACT and spec['rules']==RULES and spec['period_ids']==PERIODS
        and spec['cost_scenarios']==base.COSTS and spec['unit_scenarios']==base.UNITS,'Fixed three-window reference design')
    for name,digest in PINS.items():
        base.need(base.sha(ROOT/name)==digest and spec['frozen_sources'][name]==digest,'Unchanged accepted dependency '+name)
    manifest=base.relative_proof(spec['input_manifest'])
    base.need(manifest['status']==MANIFEST_STATUS and len(manifest['source_files'])==156
        and [(w['id'],w['start'],w['end_exclusive'],w['days']) for w in manifest['windows']]==WINDOWS,
        'Exact disjoint accepted source metadata, no new dates or invented source entries')
    derivation=[];strategy=SimpleNamespace(MODES=('LONG_ONLY',),fixed_targets=target.fixed_targets)
    simulated=private.namespace(base,['simulate'],dict(strategy=strategy),derivation)['simulate']

    def transform(node,changes):
        node=private.literal(node,changes,'THREE_FIXED_PERIOD_CLI',"['122D','90D','BOTH']","['213D','122D','90D','BOTH']",1)
        node=private.literal(node,changes,'THREE_FIXED_PERIOD_METADATA',"['122D','90D']","['213D','122D','90D']",1)
        node=private.literal(node,changes,'FOUR_PHYSICAL_TRADING_ACCOUNTS_PER_WINDOW','len(selected)*12','len(selected)*4',1)
        cash_keywords=[k for k in ast.walk(node) if isinstance(k,ast.keyword) and k.arg=='planned_constant_cash_baselines']
        base.need(len(cash_keywords)==1,'One original planned cash metadata keyword')
        cash_keywords[0].value=private.literal(cash_keywords[0].value,changes,'ZERO_NEW_CONSTANT_CASH_ACCOUNTS',
            'len(selected)','0',1)
        node=private.literal(node,changes,'NO_SHARED_CASH_RESULT_COUNT',
            "'NOMINAL_SCENARIO_SELECTORS_CASH_CONSTANT_ARTIFACTS_SHARED'","'TWELVE_NEW_PHYSICAL_HOLD_REFERENCE_ACCOUNTS_NO_CASH_REPLAY'",1)
        node=private.native._replace(node,changes,'EXACT_PRIVATE_DERIVATION_METADATA',"write(run/'RUN_BINDING.json',binding)",
            "binding['private_derivation'] = PRIVATE_DERIVATION\nwrite(run/'RUN_BINDING.json',binding)")
        old="result['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))"
        new="saved['summary']['strategy_id']=STRATEGY_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,strategy_id=STRATEGY_ID,cost_id=cost['id'],unit_id=unit['id'],**saved))"
        node=private.native._replace(node,changes,'EXPLICIT_CONSTANT_HOLD_STRATEGY_ID',old,new)
        node=private.literal(node,changes,'HONEST_CONSTANT_REFERENCE_FEATURE_METADATA',
            "'ORIGINAL_PUBLIC_SMA50_200_DAILY_SIGNED'","'CONSTANT_LONG_SHARED_PAST30_COVARIANCE_REFERENCE'",1)
        node=private.literal(node,changes,'PREDECLARED_BETA_QUESTION',"'Same product and capital four-direction comparison'",
            "'Does fixed public alpha beat same-product controlled market exposure across separate complete windows?'",1)
        return private.literal(node,changes,'REFERENCE_PROGRESS_DESCRIPTION',
            "'独立四方向、两成本和两条件资金费单位；不是真实市场资格'",
            "'三个独立窗口的受控持有基准；原成本与资金费条件，不是原生资格'",1)

    env=private.namespace(base,['main'],dict(__file__=__file__,CONTRACT=CONTRACT,STATUS=STATUS,
        MANIFEST_STATUS=MANIFEST_STATUS,RULES=RULES,strategy=strategy,simulate=simulated,
        STRATEGY_ID=STRATEGY_ID,PRIVATE_DERIVATION=derivation),derivation,transform)
    return dict(main=env['main'],simulate=simulated,derivation=derivation)

def main():
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--protocol',type=Path,required=True)
    a,_=p.parse_known_args();context(base.small(a.protocol))['main']()

if __name__=='__main__':main()
