"""UNRUN D048 recovery: one closing-only independent journal predicate.

Consumed V1 and every accepted financial source stay byte exact. Its main is
called in private globals; only the old all-fill minimum-notional assertion in
financial_journals admits CLOSE. Quantity/step/capacity, no-cross, fees, wallet,
margin, clocks and original tolerances are retained without other changes.
"""
from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import importlib.util
from pathlib import Path
import sys
from types import FunctionType, SimpleNamespace

ROOT = Path('/mnt/d/codex/coin')
ENTRY = 'scripts/investment/audit_closing_exempt_research.py'
ENTRY_SHA = '459b8bd766105539a0c1807b9e8053530743d1b47245ccd171723966eb2b25b2'
PROFILE = 'CLOSING_MIN_NOTIONAL_EXEMPT_WITH_UNCERTIFIED_1E8_QUANTITY_V1'


def need(ok, message):
    if not bool(ok):
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def dump(node):
    return ast.dump(node, include_attributes=False)


def digest(node):
    return hashlib.sha256(dump(node).encode()).hexdigest()


def entry_module():
    path = ROOT / ENTRY
    need(not path.is_symlink() and sha(path) == ENTRY_SHA, 'Exact consumed V1 metadata source')
    spec = importlib.util.spec_from_file_location('d048_consumed_v1_metadata', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def patched_base(reuse):
    original = reuse.base_module()
    path = ROOT / reuse.BASE
    need(sha(path) == reuse.BASE_SHA, 'Exact original independent journal source')
    functions = [n for n in ast.parse(path.read_bytes()).body
                 if isinstance(n, ast.FunctionDef) and n.name == 'financial_journals']
    need(len(functions) == 1, 'One complete original financial journal span')
    source = functions[0]
    derived = deepcopy(source)
    old = ast.parse('q * fill >= 10', mode='eval').body
    new = ast.parse("q * fill >= 10 or r['leg'] == 'CLOSE'", mode='eval').body
    message = 'No invented below-notional fill/dust forgiveness'

    def targets(node, predicate):
        return [call for call in ast.walk(node) if isinstance(call, ast.Call)
                and isinstance(call.func, ast.Name) and call.func.id == 'need'
                and len(call.args) == 2 and not call.keywords
                and isinstance(call.args[1], ast.Constant) and call.args[1].value == message
                and dump(call.args[0]) == dump(predicate)]

    matches = targets(derived, old)
    need(len(matches) == 1, 'Exactly one old whole-fill notional assertion')
    matches[0].args[0] = deepcopy(new)
    # Normalize ONLY the selected predicate, then compare the entire function.
    # This proves every other statement, guard and arithmetic AST is untouched.
    prior, after = deepcopy(source), deepcopy(derived)
    for function, predicate in ((prior, old), (after, new)):
        selected = targets(function, predicate)
        need(len(selected) == 1, 'Unique normalization slot')
        selected[0].args[0] = ast.Constant('CLOSING_NOTIONAL_PREDICATE_SLOT')
    need(dump(prior) == dump(after), 'No other financial journal AST change')
    namespace = dict(vars(original))
    exec(compile(ast.fix_missing_locations(ast.Module([derived], type_ignores=[])),
                 '<D048-independent-closing-only-notional-guard>', 'exec'), namespace)
    private = SimpleNamespace(**vars(original))
    private.financial_journals = namespace['financial_journals']
    private._closing_journal_derivation = dict(
        original_source_path=reuse.BASE, original_source_sha256=reuse.BASE_SHA,
        original_function_AST_sha256=digest(source), derived_function_AST_sha256=digest(derived),
        number_of_changed_predicates=1, old_predicate_AST_sha256=digest(old),
        new_predicate_AST_sha256=digest(new), non_predicate_function_AST_sha256=digest(prior),
        every_other_financial_statement_and_guard_AST_unchanged=True,
        change="q*fill>=10 OR leg=='CLOSE'; unchanged independent no-cross/step/capacity checks still follow",
        filter_profile_id=PROFILE, native_filters_certified=False,
        original_cash_tolerance_USDT=original.CASH_TOL, original_ratio_tolerance=original.RATIO_TOL,
        consumed_V1_metadata_source_path=ENTRY, consumed_V1_metadata_source_sha256=ENTRY_SHA,
        original_module_globals_mutated=False, producer_finance_imported=False)
    return private


def main():
    entry = entry_module()
    original_recorded = entry.recorded_finance

    def recorded_finance():
        reuse = original_recorded()

        def prepare_financial_only(base):
            function, proof = reuse.prepare_financial_only(base)
            proof['closing_filter_financial_journal_derivation'] = deepcopy(base._closing_journal_derivation)
            return function, proof

        private = SimpleNamespace(**vars(reuse))
        private.base_module = lambda: patched_base(reuse)
        private.prepare_financial_only = prepare_financial_only
        return private

    environment = dict(vars(entry), __file__=__file__, recorded_finance=recorded_finance)
    delegated = FunctionType(entry.main.__code__, environment, entry.main.__name__,
                             entry.main.__defaults__, entry.main.__closure__)
    delegated.__kwdefaults__ = entry.main.__kwdefaults__
    delegated()
    need(sha(ROOT / ENTRY) == ENTRY_SHA, 'Consumed V1 remains byte exact after attempt')


if __name__ == '__main__':
    main()
