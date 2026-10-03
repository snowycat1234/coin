"""D049 fixed Turtle long-only / short-only conditional direction ablation.

Eight new independent303-day accounts reuse D048's complete Turtle simulation
code object and closing-filter account. Only entry/add direction permission
changes; callbacks, protective reductions, market inputs, fees and risk stay
the same. Saved long-short, HOLD and CASH controls are not replayed. Quantity
filters and funding units remain conditional, not native Bybit certification.
"""
from __future__ import annotations

import ast
from functools import partial
from types import FunctionType, SimpleNamespace

from quant.paths import ROOT
from scripts.investment import closing_exempt_research as reuse
from scripts.investment import turtle_direction_mask as mask

base, parent, turtle, private = reuse.base, reuse.parent, reuse.turtle, reuse.private
closing = reuse.closing
CONTRACT = 'D049_FIXED303D_TURTLE_DIRECTION_ABLATION_CONDITIONAL_V1'
STATUS = 'COMPLETE_D049_EIGHT_TURTLE_DIRECTION_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
PROTOCOL_PATH = 'protocols/TURTLE_DIRECTION_ABLATION_20261003_V1.json'
LONG_SELECTOR, SHORT_SELECTOR = 'TURTLE_LONG_ONLY', 'TURTLE_SHORT_ONLY'
SELECTORS = (LONG_SELECTOR, SHORT_SELECTOR)
STRATEGY_ID = mask.STRATEGY_ID
RULES = dict(reuse.RULES, modes=list(SELECTORS),
    strategy_design=[dict(selector=LONG_SELECTOR, strategy_id=STRATEGY_ID, mode='LONG_ONLY',
        signal_timeframe_minutes=240), dict(selector=SHORT_SELECTOR, strategy_id=STRATEGY_ID,
        mode='SHORT_ONLY', signal_timeframe_minutes=240)],
    signal='ORIGINAL_TURTLE4H_DIRECTION_PERMISSION_ONLY_NO_MIRRORED_SIGNAL',
    direction_mask_rules=mask.RULES,
    classification='ONE_COMPLETE_SEEN303_WINDOW_FIXED_DIRECTION_ABLATION',
    saved_LONG_SHORT_HOLD_CASH_accounts_replayed=False)
del RULES['hold_recipe']
PINS = dict(reuse.PINS, **{
    'scripts/investment/closing_exempt_research.py': '173b03ee5b2ce3bb263d695a712be694cec7a15a89025092bc6f53ced81fd98b',
    'scripts/investment/turtle_direction_mask.py': '748033f2f9b8b717324ed2db5f28556f5e9e88c1e53af65b07f513a74a2f906f',
})


def _pins():
    for path, digest in PINS.items():
        base.need(turtle.sha(ROOT / path) == digest, 'Frozen direction-ablation dependency '+path)


def _direction_clone(function, mode, derivation):
    """Same financial code object, isolated globals and fixed bridge mode."""
    base.need(mode in ('LONG_ONLY', 'SHORT_ONLY'), 'Only the two new declared directions')
    strategy = SimpleNamespace(**dict(vars(function.__globals__['strategy']),
        TurtlePerpetualBridge=partial(mask.TurtlePerpetualBridge, mode=mode)))
    environment = dict(function.__globals__, strategy=strategy)
    cloned = FunctionType(function.__code__, environment, function.__name__, function.__defaults__, function.__closure__)
    cloned.__kwdefaults__ = function.__kwdefaults__
    cloned.__annotations__ = dict(function.__annotations__)
    derivation.append(dict(change='FIXED_TURTLE_DIRECTION_PERMISSION_'+mode, matches=1,
        complete_simulation_code_object_unchanged=cloned.__code__ is function.__code__,
        original_function_globals_mutated=False, original_strategy_module_mutated=False,
        bridge_source_path='scripts/investment/turtle_direction_mask.py',
        bridge_source_sha256=PINS['scripts/investment/turtle_direction_mask.py'],
        direction_mode=mode, direction_mask_version=mask.VERSION, direction_mask_rules=mask.RULES))
    return cloned


def adapted_simulate():
    """Private construction only; no account execution or source payload IO."""
    _pins()
    original, derivation = turtle.adapted_simulate()
    conditional = reuse._account_clone(original, derivation, 'TURTLE_DIRECTION_ABLATION')
    long_only = _direction_clone(conditional, 'LONG_ONLY', derivation)
    short_only = _direction_clone(conditional, 'SHORT_ONLY', derivation)

    def dispatch(window, mode, cost, unit, progress=None, guard=None):
        base.need(mode in SELECTORS, 'Exactly long-only and short-only selectors; no old control replay')
        if mode == LONG_SELECTOR:
            return long_only(window, 'LONG_ONLY', cost, unit, progress, guard)
        return short_only(window, 'SHORT_ONLY', cost, unit, progress, guard)

    return dispatch, long_only, short_only, derivation


def _context_metadata(node, changes):
    """Only context/report literals change, never the simulation function."""
    old_case = "saved['summary']['strategy_id']=TURTLE_ID if mode==TURTLE_SELECTOR else HOLD_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode='LONG_SHORT' if mode==TURTLE_SELECTOR else 'LONG_ONLY',selector_mode=mode,strategy_id=saved['summary']['strategy_id'],cost_id=cost['id'],unit_id=unit['id'],**saved))"
    new_case = "saved['summary']['strategy_id']=TURTLE_ID if mode==TURTLE_SELECTOR else HOLD_ID\nresult['cases'].append(dict(id=case_id,period=window_spec['id'],mode='LONG_ONLY' if mode==TURTLE_SELECTOR else 'SHORT_ONLY',selector_mode=mode,strategy_id=saved['summary']['strategy_id'],cost_id=cost['id'],unit_id=unit['id'],**saved))"
    replacements = [
        ('DECLARED_CANONICAL_DIRECTION_CASE_METADATA', old_case, new_case),
        ('FIXED_DIRECTION_CONTEXT_GUARD_DESCRIPTION', 'Fixed two-strategy eight-account303 conditional control',
            'Fixed two-direction eight-account303 conditional control'),
        ('DIRECTION_FEATURE_METADATA', "'FROZEN_TURTLE4H_CALLBACK_AND_DAILY_COVARIANCE_HOLD_CLOSING_FILTER_CONTROL'",
            "'FROZEN_TURTLE4H_LONG_ONLY_AND_SHORT_ONLY_DIRECTION_PERMISSION_ABLATION'"),
        ('DIRECTION_EXPERIMENT_REASON', "'Known current closing minimum-notional exemption; unchanged Turtle and same-product HOLD economic control with uncertified quantity profile'",
            "'Fixed original Turtle long-only and short-only permission ablation; saved controls not replayed; filters and funding units uncertified'"),
        ('DIRECTION_PROGRESS_DESCRIPTION', "'Turtle与受控持有八账户：平仓规则薄适配、数量仍未认证；不是原生资格'",
            "'原Turtle仅多或仅空八账户；原费用风险、数量与资金费单位仍未认证'"),
    ]
    for label, before, after in replacements:
        node = private.literal(node, changes, label, repr(before), repr(after), 1)
    for before, after in [('simulate_TURTLE', 'simulate_LONG_ONLY'), ('simulate_HOLD', 'simulate_SHORT_ONLY')]:
        fields = [n for n in ast.walk(node) if isinstance(n, ast.keyword) and n.arg == before]
        base.need(len(fields) == 1, 'One exact returned private function field '+before)
        fields[0].arg = after
        changes.append(dict(change='RETURN_DIRECTION_API_'+after, matches=1))
    return node


def compact_append_event(path, event):
    """Reuse the accepted compact registry fields with this exact protocol."""
    receipt = []
    environment = private.namespace(reuse, ['compact_append_event'],
        dict(PROTOCOL_PATH=PROTOCOL_PATH), receipt)
    return environment['compact_append_event'](path, event)


def context(spec):
    """All original scalar/source/calendar guards before any market arrays."""
    _pins()
    receipt = []
    environment = private.namespace(reuse, ['context'], dict(__file__=__file__, CONTRACT=CONTRACT,
        STATUS=STATUS, RULES=RULES, PINS=PINS, SELECTORS=SELECTORS, TURTLE_SELECTOR=LONG_SELECTOR,
        HOLD_SELECTOR=SHORT_SELECTOR, TURTLE_ID=STRATEGY_ID, HOLD_ID=STRATEGY_ID,
        adapted_simulate=adapted_simulate, compact_append_event=compact_append_event), receipt, _context_metadata)
    result = environment['context'](spec)
    result['derivation'].extend(receipt)
    return result


def main():
    """Inherited CLI and exact private lock byte guards; hash only."""
    _pins()
    receipt = []
    environment = private.namespace(reuse, ['main'], dict(__file__=__file__, context=context), receipt)
    environment['main']()


if __name__ == '__main__':
    main()
