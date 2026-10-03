"""D047 private controller correction: two exact adjacent statement anchors.

The consumed V1 controller remains unchanged. Its functions are compiled in
private globals; only its five-statement preparation and two-statement stop
observation anchors use sequence matching. Account, callbacks, timing and the
first-market V1 logical protocol are unchanged. This file runs no market IO at
import or controller construction.
"""
from __future__ import annotations

import argparse
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

from scripts.investment import turtle_perpetual_research as original

ROOT, STATE = original.ROOT, original.STATE
base, parent, strategy, private = original.base, original.parent, original.strategy, original.private
CONTRACT, STATUS, STRATEGY_ID = original.CONTRACT, original.STATUS, original.STRATEGY_ID
FOUR_HOURS, MODES, RULES = original.FOUR_HOURS, original.MODES, original.RULES
prepare_signal_context, decision, load_window = original.prepare_signal_context, original.decision, original.load_window
sha = original.sha
PINS = {
    'scripts/investment/turtle_perpetual_research.py': '13853407be3dda41c3b13ef76b4216b713e4f23c0bc9fa7006536464b1333c55',
    'scripts/investment/perpetual_directional.py': '547a1ca2d8e4b9278f599a1972f099bfe449910e34791e5a0e16873ce67d5ef3',
}
SEQUENCE_ANCHORS = {
    'CAUSAL4H_CONTEXT_NO_PREGENERATED_POSITION_STATE': 5,
    'OBSERVE_KNOWN_MINUTE_STOP_WITHOUT_INTRABAR_BACKFILL': 2,
}
PROTOCOL_PATH = 'protocols/TURTLE_PERPETUAL_RESEARCH_20261003_V1.json'


def compact_append_event(path, event):
    """Keep attempt/conclusion fields and exact pointers to complete metadata."""
    value = dict(event)
    reference = dict(protocol_path=PROTOCOL_PATH, protocol_sha256=value['protocol_hash'])
    value['source_hashes'] = {PROTOCOL_PATH: value['protocol_hash']}
    value['hyperparameters'] = dict(reference, protocol_fields=['rules'])
    value['thresholds'] = dict(reference, protocol_fields=['rules'], policy='FIXED_NO_SEARCH')
    value['cost_assumptions'] = dict(reference, protocol_fields=['cost_scenarios', 'unit_scenarios'])
    return original.original_append_event(path, value)


def _replace(tree, changes, name, old, new):
    """Delegate single statements; match only the two known exact sequences."""
    anchors = ast.parse(old).body
    if len(anchors) == 1:
        return private.native._replace(tree, changes, name, old, new)
    base.need(SEQUENCE_ANCHORS.get(name) == len(anchors), 'Only two declared multi-statement anchors')
    expected = [ast.dump(n, include_attributes=False) for n in anchors]
    matches = []
    for node in ast.walk(tree):
        for _, values in ast.iter_fields(node):
            if not isinstance(values, list) or not values or not all(isinstance(n, ast.stmt) for n in values):
                continue
            for i in range(len(values) - len(anchors) + 1):
                actual = [ast.dump(n, include_attributes=False) for n in values[i:i + len(anchors)]]
                if actual == expected:
                    matches.append((values, i))
    base.need(len(matches) == 1, 'One exact adjacent statement sequence required: ' + name)
    replacements = ast.parse(new).body
    values, index = matches[0]
    values[index:index + len(anchors)] = deepcopy(replacements)
    before = ast.Module(anchors, type_ignores=[])
    after = ast.Module(replacements, type_ignores=[])
    changes.append(dict(change=name, matches=1, anchor_statement_count=len(anchors),
        replacement_statement_count=len(replacements), exact_adjacent_sequence=True,
        old_ast_sha256=private.native._digest(before), new_ast_sha256=private.native._digest(after),
        old_statement=ast.unparse(before), new_statement=ast.unparse(after)))
    return tree


def _namespace():
    for path, digest in PINS.items():
        base.need(sha(ROOT / path) == digest, 'Frozen V1 controller dependency changed: ' + path)
    base.need(Path(original.__file__).resolve() == (ROOT / next(iter(PINS))).resolve(), 'Exact V1 module location')
    native = SimpleNamespace(**dict(vars(private.native), _replace=_replace))
    local_private = SimpleNamespace(**dict(vars(private), native=native))
    construction = []
    environment = private.namespace(original, ['adapted_simulate', 'context'],
        dict(private=local_private, compact_append_event=compact_append_event,
            __file__=str(Path(__file__).resolve())), construction)
    return environment


def adapted_simulate():
    return _namespace()['adapted_simulate']()


def context(spec):
    return _namespace()['context'](spec)


def main():
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--protocol', type=Path, required=True)
    args, _ = parser.parse_known_args()
    context(base.small(args.protocol))['main']()


if __name__ == '__main__':
    main()
