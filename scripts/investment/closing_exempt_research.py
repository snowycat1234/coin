"""D048 conditional closing-filter control using two frozen public strategies.

Eight independent full303-day accounts share the original market inputs and
cost/unit conditions. Turtle's account filter is replaced without signal or
controller changes. HOLD also reuses the accepted D046 two-anchor risk-order
normalization, which the older D045 HOLD control did not have; comparison to
that older control is therefore not a pure account-only change. Both recipes
use the current declared rules. This is not a native profile or adoption.
"""
from __future__ import annotations

import argparse
import ast
from pathlib import Path
from types import FunctionType, SimpleNamespace

from quant.paths import ROOT
from scripts.investment import perpetual_directional as base
from scripts.investment import perpetual_303_research as parent
from scripts.investment import perpetual_risk_reduction_research_v2 as reduction
from scripts.investment import turtle_perpetual_research_v2 as turtle
from scripts.investment import vol_managed_perpetual_target as hold
from scripts.investment import public_long_development_adapter as private
from scripts.investment import perpetual_closing_exempt_account as closing

CONTRACT = 'D048_FIXED303D_TURTLE_AND_HOLD_CLOSING_EXEMPT_CONDITIONAL_V1'
STATUS = 'COMPLETE_D048_EIGHT_CLOSING_EXEMPT_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
PROTOCOL_PATH = 'protocols/CLOSING_EXEMPT_RESEARCH_20261003_V1.json'
LOCK_SHA256 = '29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
TURTLE_SELECTOR, HOLD_SELECTOR = 'TURTLE_LONG_SHORT', 'HOLD_LONG_ONLY'
SELECTORS = (TURTLE_SELECTOR, HOLD_SELECTOR)
TURTLE_ID, HOLD_ID = turtle.STRATEGY_ID, hold.STRATEGY_ID
RULES = dict(base.RULES, modes=list(SELECTORS), period_id=parent.PERIOD,
    score_start=parent.START, score_end_exclusive=parent.END,
    strategy_design=[dict(selector=TURTLE_SELECTOR, strategy_id=TURTLE_ID, mode='LONG_SHORT',
        signal_timeframe_minutes=240), dict(selector=HOLD_SELECTOR, strategy_id=HOLD_ID,
        mode='LONG_ONLY', signal_timeframe_minutes=1440)],
    signal='FROZEN_TURTLE4H_CALLBACK_AND_DAILY_CONTROLLED_HOLD_TWO_STRATEGIES',
    turtle_recipe=turtle.RULES, hold_recipe=hold.RULES,
    planned_selectors=8, planned_trading_account_simulations=8, planned_constant_cash_baselines=0,
    account_version=closing.VERSION, filter_profile_id=closing.FILTER_PROFILE_ID,
    opening_min_notional_assumption_USDT=10, closing_min_notional_exempt=True,
    min_notional_scope='OPENING_LEGS_ONLY', min_quantity_assumption=1e-8,
    quantity_profile_status='UNCERTIFIED_PROXY_NOT_API_PROFILE',
    native_filters_certified=False, historical_filters_certified=False,
    funding_unit_conditions_not_HPO=True, original_Turtle_and_HOLD_accounts_replayed=False,
    no_strategy_or_risk_parameter_search=True, realized_risk_equalized=False,
    classification='ONE_COMPLETE_SEEN303_WINDOW_KNOWN_CLOSING_RULE_CONDITIONAL_CONTROL')
PINS = {
    'src/quant/perpetual_account.py': closing.SOURCE_SHA256,
    'scripts/investment/perpetual_closing_exempt_account.py': 'd4c1636be51b067be6b86437cd69f158320f47c258f0d78f0a47f21806c617ac',
    'scripts/investment/perpetual_directional.py': '547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3',
    'scripts/investment/perpetual_303_research.py': 'fe72e7f1a1913c890148927374d5aea43d4911280ac6645b512ccc791a583832',
    'scripts/investment/perpetual_risk_reduction_research_v2.py': 'd9f4310d482e2acfb275bb518e532f239b0befbafcbd699775d6d37fc7336fa6',
    'scripts/investment/turtle_perpetual_research.py': '13853407be3dda41c3b13ef76b4216b713e4f23c0bc9fa7006536464b1333c55',
    'scripts/investment/turtle_perpetual_research_v2.py': 'dff1fc4fbcdb5fade74a9b824c703caabf5e1a65a14cdedf90b4c0dd1b2fa211',
    'scripts/investment/turtle_perpetual_bridge.py': '6056ead6e354df08dbdfa8cb19db2f70bc0d10a4f76035640779914d4a7c213b',
    'scripts/investment/vol_managed_perpetual_target.py': '63cb91583a70efe1ae2be0607370713cd98828d298cb09cb1da2adf41cdd11d6',
    'scripts/investment/public_sma_perpetual.py': 'c90a9d383fe3365681bfdd5772c0f8a9a8977d57e423627b9159098ce25f30df',
    'scripts/investment/public_long_development_adapter.py': '15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f',
}


def compact_append_event(path, event):
    value = dict(event)
    ref = dict(protocol_path=PROTOCOL_PATH, protocol_sha256=value['protocol_hash'])
    value['source_hashes'] = {PROTOCOL_PATH: value['protocol_hash']}
    value['hyperparameters'] = dict(ref, protocol_fields=['rules'])
    value['thresholds'] = dict(ref, protocol_fields=['rules'], policy='FIXED_NO_SEARCH')
    value['cost_assumptions'] = dict(ref, protocol_fields=['cost_scenarios', 'unit_scenarios'])
    return base.append_event(path, value)


def _account_clone(function, receipt, label):
    """The accepted simulation code object in independent account globals."""
    environment = dict(function.__globals__, USDTLinearPerpetualAccount=closing.USDTLinearPerpetualAccount)
    cloned = FunctionType(function.__code__, environment, function.__name__, function.__defaults__, function.__closure__)
    cloned.__kwdefaults__ = function.__kwdefaults__
    cloned.__annotations__ = dict(function.__annotations__)
    receipt.append(dict(change='CLOSING_PROFILE_ONLY_'+label, matches=1,
        complete_simulation_code_object_unchanged=cloned.__code__ is function.__code__,
        original_function_globals_mutated=False, account_source_path='scripts/investment/perpetual_closing_exempt_account.py',
        account_source_sha256=PINS['scripts/investment/perpetual_closing_exempt_account.py'],
        original_account_source_sha256=closing.SOURCE_SHA256, filter_profile_id=closing.FILTER_PROFILE_ID))
    return cloned


def adapted_simulate():
    """Private construction only: no source payload or account execution."""
    for path, digest in PINS.items():
        base.need(turtle.sha(ROOT / path) == digest, 'Frozen closing-control dependency '+path)
    original_turtle, derivation = turtle.adapted_simulate()
    original_hold, hold_derivation = reduction.adapted_simulate(SimpleNamespace(fixed_targets=hold.fixed_targets))
    derivation.extend(hold_derivation)
    simulated_turtle = _account_clone(original_turtle, derivation, 'TURTLE')
    simulated_hold = _account_clone(original_hold, derivation, 'HOLD')

    def dispatch(window, mode, cost, unit, progress=None, guard=None):
        base.need(mode in SELECTORS, 'Exactly two declared strategy selectors; no CASH or other mode')
        if mode == TURTLE_SELECTOR:
            return simulated_turtle(window, 'LONG_SHORT', cost, unit, progress, guard)
        return simulated_hold(window, 'LONG_ONLY', cost, unit, progress, guard)

    return dispatch, simulated_turtle, simulated_hold, derivation


def context(spec):
    """Frozen scalar metadata and private compilation before any market arrays."""
    base.need('state/dataset_lock.json' not in spec['frozen_sources'], 'Private lock must not enter exported source maps')
    base.need(spec['contract_id'] == CONTRACT and spec['rules'] == RULES
        and spec['period_ids'] == [parent.PERIOD] and spec['cost_scenarios'] == base.COSTS
        and spec['unit_scenarios'] == base.UNITS and spec['input_manifest']['path'] == parent.INPUT,
        'Fixed two-strategy eight-account303 conditional control')
    for path, digest in PINS.items():
        base.need(spec['frozen_sources'].get(path) == digest, 'Required unchanged direct source pin '+path)
    parent.metadata_view(base.relative_proof(spec['input_manifest']))
    warmup = base.relative_proof(spec['warmup_acceptance'])
    base.need(warmup['status'] == 'PASS_D047_OFFICIAL_4H_WARMUP_SOURCE_ONLY' and warmup['source_only'] is True,
        'Already accepted four4h warmup files, no new source qualification')
    dispatch, simulated_turtle, simulated_hold, derivation = adapted_simulate()

    def reader(manifest, window):
        return turtle.load_window(manifest, window, warmup)

    def transform(node, changes):
        node = private.literal(node, changes, 'ONE303_PERIOD_CLI', "['122D','90D','BOTH']", "['303D','BOTH']", 1)
        node = private.literal(node, changes, 'ONE303_PERIOD_METADATA', "['122D','90D']", "['303D']", 1)
        node = private.literal(node, changes, 'EIGHT_PHYSICAL_STRATEGY_ACCOUNTS', 'len(selected)*12', 'len(selected)*8', 1)
        cash = [n for n in ast.walk(node) if isinstance(n, ast.keyword) and n.arg == 'planned_constant_cash_baselines']
        base.need(len(cash) == 1 and isinstance(cash[0].value, ast.Call)
            and ast.dump(cash[0].value, include_attributes=False) == ast.dump(ast.parse('len(selected)', mode='eval').body, include_attributes=False),
            'One exact original planned cash keyword')
        cash[0].value = ast.Constant(0)
        changes.append(dict(change='ZERO_NEW_CASH_BASELINES', matches=1))
        node = private.literal(node, changes, 'NO_CASH_ALIAS_SCOPE',
            "'NOMINAL_SCENARIO_SELECTORS_CASH_CONSTANT_ARTIFACTS_SHARED'", "'EIGHT_DISTINCT_PHYSICAL_ACCOUNTS_NO_CASH_ALIAS'", 1)
        node = private.native._replace(node, changes, 'ACTUAL_ACCOUNT_AND_STRATEGY_DERIVATION',
            "write(run/'RUN_BINDING.json',binding)",
            "binding['closing_filter_and_strategy_derivation']=PRIVATE_DERIVATION\nwrite(run/'RUN_BINDING.json',binding)")
        node = private.native._replace(node, changes, 'CANONICAL_MODE_AND_DISTINCT_STRATEGY',
            "result['cases'].append(dict(id=case_id,period=window_spec['id'],mode=mode,cost_id=cost['id'],unit_id=unit['id'],**saved))",
            "saved['summary']['strategy_id']=TURTLE_ID if mode==TURTLE_SELECTOR else HOLD_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode='LONG_SHORT' if mode==TURTLE_SELECTOR else 'LONG_ONLY',selector_mode=mode,strategy_id=saved['summary']['strategy_id'],cost_id=cost['id'],unit_id=unit['id'],**saved))")
        node = private.literal(node, changes, 'HONEST_TWO_STRATEGY_FEATURE_METADATA',
            "'ORIGINAL_PUBLIC_SMA50_200_DAILY_SIGNED'", "'FROZEN_TURTLE4H_CALLBACK_AND_DAILY_COVARIANCE_HOLD_CLOSING_FILTER_CONTROL'", 1)
        node = private.literal(node, changes, 'KNOWN_RULE_CORRECTNESS_NOT_ALPHA_SEARCH',
            "'Same product and capital four-direction comparison'",
            "'Known current closing minimum-notional exemption; unchanged Turtle and same-product HOLD economic control with uncertified quantity profile'", 1)
        return private.literal(node, changes, 'TWO_STRATEGY_PROGRESS_DESCRIPTION',
            "'独立四方向、两成本和两条件资金费单位；不是真实市场资格'",
            "'Turtle与受控持有八账户：平仓规则薄适配、数量仍未认证；不是原生资格'", 1)

    environment = private.namespace(base, ['main'], dict(__file__=__file__, CONTRACT=CONTRACT, STATUS=STATUS,
        MANIFEST_STATUS=parent.MANIFEST_STATUS, RULES=RULES, strategy=SimpleNamespace(MODES=SELECTORS),
        sha=turtle.sha, relative_proof=parent.relative_proof, load_window=reader, simulate=dispatch,
        USDTLinearPerpetualAccount=closing.USDTLinearPerpetualAccount, append_event=compact_append_event,
        PRIVATE_DERIVATION=derivation, TURTLE_SELECTOR=TURTLE_SELECTOR, TURTLE_ID=TURTLE_ID, HOLD_ID=HOLD_ID),
        derivation, transform)
    return dict(main=environment['main'], simulate=dispatch, simulate_TURTLE=simulated_turtle,
        simulate_HOLD=simulated_hold, load_window=reader, derivation=derivation)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--protocol', type=Path, required=True)
    args, _ = parser.parse_known_args()
    base.need(turtle.sha(ROOT / 'state/dataset_lock.json') == LOCK_SHA256, 'Private lock unchanged before context; hash only')
    context(base.small(args.protocol))['main']()
    base.need(turtle.sha(ROOT / 'state/dataset_lock.json') == LOCK_SHA256, 'Private lock unchanged after successful main; hash only')


if __name__ == '__main__':
    main()
