"""D049 recorded finance: reuse the accepted independent closing ledger.

Only recipe identity checks are adapted from D048 to the two fixed Turtle
directions. The original HandLedger, chronology, prices, costs, collateral,
funding, NAV, gross, covariance and tolerances remain unchanged. An additional
check over already loaded legs forbids opening the opposite direction.
"""
import ast
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path('/mnt/d/codex/coin')
ENTRY = 'scripts/investment/audit_closing_exempt_research.py'
ENTRY_SHA = '459b8bd766105539a0c1807b9e8053530743d1b47245ccd171723966eb2b25b2'
CORRECTION = 'scripts/investment/audit_closing_exempt_research_v2.py'
CORRECTION_SHA = 'b42a92edee8fd93c2dba0f5d055caee70ef73680bf473af7881f39abbfec514b'
PRIVATE = 'scripts/investment/public_long_development_adapter.py'
PRIVATE_SHA = '15ea3a089f39149d9d669fa3425fa35821c2c01b3cce1c15f751fd1723a9406f'
SID = 'COIN_JESSE_TURTLERULES_4H_USDM_DELAYED_STOP_ADAPTER'
CONTRACT = 'D049_FIXED303D_TURTLE_DIRECTION_ABLATION_CONDITIONAL_V1'
ACTUAL_STATUS = 'COMPLETE_D049_EIGHT_TURTLE_DIRECTION_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
STATUS = 'PASS_D049_EIGHT_RECORDED_TURTLE_DIRECTION_ACCOUNTING_NOT_NATIVE_FILTERS_OR_LONG_TERM_APR'
RECIPES = {'TURTLE_LONG_ONLY': 'LONG_ONLY', 'TURTLE_SHORT_ONLY': 'SHORT_ONLY'}
SELECTORS = {key: key for key in RECIPES}


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def module(path, digest, name):
    if sha(ROOT / path) != digest:
        raise ValueError('Exact reused metadata/finance dependency: ' + path)
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    value = importlib.util.module_from_spec(spec)
    sys.modules[name] = value
    spec.loader.exec_module(value)
    return value


def prepare():
    entry = module(ENTRY, ENTRY_SHA, '_d049_prior_finance_metadata')
    correction = module(CORRECTION, CORRECTION_SHA, '_d049_accepted_closing_journal')
    private = module(PRIVATE, PRIVATE_SHA, '_d049_private_metadata_adapter')
    derivation = []

    def recorded_finance():
        reuse = entry.recorded_finance()
        adapted = SimpleNamespace(**vars(reuse))

        def prepare_financial_only(base):
            function, proof = reuse.prepare_financial_only(base)
            proof['closing_filter_financial_journal_derivation'] = deepcopy(base._closing_journal_derivation)
            proof['direction_metadata_derivation'] = deepcopy(derivation)
            proof['additional_open_leg_direction_check'] = True
            return function, proof

        def independent_base():
            base = correction.patched_base(reuse)
            journals = base.financial_journals

            def financial_journals(window, case, trades, funds, reference, maximum):
                allowed = 'BUY' if case['mode'] == 'LONG_ONLY' else 'SELL'
                entry.need(case['mode'] in RECIPES.values(), 'Declared independent direction')
                entry.need(all(row['leg'] != 'OPEN' or row['side'] == allowed for row in trades),
                           'Every actual opening leg has the permitted direction')
                return journals(window, case, trades, funds, reference, maximum)

            base.financial_journals = financial_journals
            return base

        adapted.base_module = independent_base
        adapted.prepare_financial_only = prepare_financial_only
        return adapted

    def transform(node, changes):
        replacements = [
            ('DIRECTION_DESIGN_METADATA',
             "[dict(selector=SELECTORS[s], strategy_id=s, mode=mode, signal_timeframe_minutes=240 if mode == 'LONG_SHORT' else 1440) for s, mode in RECIPES.items()]",
             "[dict(selector=selector, strategy_id=SID, mode=mode, signal_timeframe_minutes=240) for selector, mode in RECIPES.items()]"),
            ('DIRECTION_EXPECTED_IDENTITIES',
             '{(strategy, mode, cost, unit) for strategy, mode in RECIPES.items() for cost in base.COSTS for unit in base.UNITS}',
             '{(SID, mode, cost, unit) for mode in RECIPES.values() for cost in base.COSTS for unit in base.UNITS}'),
            ('DIRECTION_SELECTOR_IDENTITY', "c['selector_mode'] == SELECTORS[c['strategy_id']]",
             "RECIPES[c['selector_mode']] == c['mode']"),
            ('NEW_PRODUCER_SOURCE_BINDING', "'scripts/investment/closing_exempt_research.py'",
             "'scripts/investment/turtle_direction_research.py'"),
            ('NO_NEW_HOLD_CONTROLLER', "'ACCEPTED_D046_TWO_RISK_ORDER_NORMALIZATION_ANCHORS_ALSO_REUSED_NOT_REBUILT'",
             "'NO_NEW_HOLD_ACCOUNT_REPLAY'"),
        ]
        for name, old, new in replacements:
            node = private.literal(node, changes, name, old, new, 1)
        fields = [item for item in ast.walk(node) if isinstance(item, ast.keyword)
                  and item.arg == 'HOLD_change_vs_older_D045_is_pure_account_only_effect']
        entry.need(len(fields) == 1 and isinstance(fields[0].value, ast.Constant)
                   and fields[0].value.value is False, 'Exact legacy HOLD-only metadata')
        fields[0].value = ast.Constant(None)
        changes.append(dict(change='HONEST_NO_NEW_HOLD_CHANGE', matches=1))
        return private.literal(node, changes, 'HONEST_DIRECTION_FAILURE_STATUS',
            "'FAIL_D048_RECORDED_CLOSING_EXEMPT_ACCOUNTING'", "'FAIL_D049_RECORDED_TURTLE_DIRECTION_ACCOUNTING'", 1)

    environment = private.namespace(entry, ['main'], dict(__file__=__file__,
        recorded_finance=recorded_finance, CONTRACT=CONTRACT, ACTUAL_STATUS=ACTUAL_STATUS,
        STATUS=STATUS, RECIPES=RECIPES, SELECTORS=SELECTORS, SID=SID), derivation, transform)
    return environment


def main():
    prepare()['main']()
    if sha(ROOT / ENTRY) != ENTRY_SHA or sha(ROOT / CORRECTION) != CORRECTION_SHA:
        raise ValueError('Consumed independent sources changed')


if __name__ == '__main__':
    main()
