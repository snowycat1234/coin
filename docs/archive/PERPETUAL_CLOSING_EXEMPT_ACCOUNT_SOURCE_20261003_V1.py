"""Conditional linear-perpetual closing filter over the frozen account body.

Closing legs are exempt from the declared 10 USDT opening minimum notional.
The original 1e-8 quantity step/minimum remains an UNCERTIFIED assumption: this
is neither a retrieved Bybit instrument profile nor historical filter proof.
Fees, partial capacity, chronology, collateral and liquidation halts are reused.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from functools import lru_cache
import hashlib
from pathlib import Path

from quant import perpetual_account as legacy
from quant.paths import ROOT

PerpetualConfig = legacy.PerpetualConfig
VERSION = 'usdt_linear_perpetual_closing_exempt_account_v1'
FILTER_PROFILE_ID = 'CLOSING_MIN_NOTIONAL_EXEMPT_WITH_UNCERTIFIED_1E8_QUANTITY_V1'
SOURCE_PATH = 'src/quant/perpetual_account.py'
SOURCE_SHA256 = 'cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261'
METHODS = ('execute_fill', 'summary', 'snapshot', 'from_snapshot')


def _sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _digest(node):
    return hashlib.sha256(ast.dump(node, include_attributes=False).encode()).hexdigest()


def _pins():
    source = ROOT / SOURCE_PATH
    if Path(legacy.__file__).resolve() != source.resolve() or _sha(source) != SOURCE_SHA256:
        raise ValueError('Exact frozen original perpetual account required')


@lru_cache(maxsize=1)
def _methods():
    """Compile four original method bodies in private versioned globals."""
    _pins()
    tree = ast.parse((ROOT / SOURCE_PATH).read_text(encoding='utf-8'))
    classes = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'USDTLinearPerpetualAccount']
    if len(classes) != 1:
        raise ValueError('One exact original account class required')
    originals = [n for n in classes[0].body if isinstance(n, ast.FunctionDef) and n.name in METHODS]
    if len(originals) != len(METHODS) or {n.name for n in originals} != set(METHODS):
        raise ValueError('Exact original filter and recovery methods required')
    environment = dict(vars(legacy), VERSION=VERSION)
    receipt = dict(original_source_path=SOURCE_PATH, original_source_sha256=SOURCE_SHA256,
        adapter_path=Path(__file__).resolve().relative_to(ROOT).as_posix(), adapter_sha256=_sha(__file__),
        version=VERSION, filter_profile_id=FILTER_PROFILE_ID, original_globals_mutated=False,
        financial_leg_body_unchanged=True, config_unchanged=True, methods=[])
    expected = ast.parse('executable * fill < self.config.min_notional', mode='eval').body
    replacement = ast.parse('executable == ZERO or (executable * fill < self.config.min_notional and not reducing)', mode='eval').body
    for original in originals:
        node = deepcopy(original)
        changes = []
        if node.name == 'execute_fill':
            candidates = [n for n in ast.walk(node) if isinstance(n, ast.If)
                and ast.dump(n.test, include_attributes=False) == ast.dump(expected, include_attributes=False)]
            if len(candidates) != 1:
                raise ValueError('One exact whole-request minimum-notional predicate required')
            candidates[0].test = deepcopy(replacement)
            changes.append(dict(change='CLOSING_MIN_NOTIONAL_EXEMPT_QUANTITY_AND_CAPACITY_STILL_REQUIRED',
                matches=1, old_predicate_AST_sha256=_digest(expected), new_predicate_AST_sha256=_digest(replacement),
                opening_leg_minimum_guard_unchanged=True))
        if node.name == 'from_snapshot':
            if len(node.decorator_list) != 1 or not isinstance(node.decorator_list[0], ast.Name) or node.decorator_list[0].id != 'classmethod':
                raise ValueError('Exact classmethod recovery dispatch required')
            # The public wrapper retains classmethod dispatch; the financial
            # recovery body and its request/ledger/dedup checks remain intact.
            node.decorator_list = []
        elif node.decorator_list:
            raise ValueError('Unexpected original method decorator')
        exec(compile(ast.fix_missing_locations(ast.Module([node], type_ignores=[])),
            str(ROOT / SOURCE_PATH) + '<D048-private-closing-filter>', 'exec'), environment)
        receipt['methods'].append(dict(name=node.name, original_AST_sha256=_digest(original),
            derived_AST_sha256=_digest(node), original_body_AST_sha256=_digest(ast.Module(original.body, type_ignores=[])),
            derived_body_AST_sha256=_digest(ast.Module(node.body, type_ignores=[])), changes=changes))
    return {name: environment[name] for name in METHODS}, receipt


def derivation_receipt():
    _pins()
    return deepcopy(_methods()[1])


class USDTLinearPerpetualAccount(legacy.USDTLinearPerpetualAccount):
    """The same isolated wallet with an explicitly different filter profile."""

    def __init__(self, config=None, *, market_type='LINEAR_USDT_PERPETUAL', external_gross_notional=0):
        _pins()
        super().__init__(config, market_type=market_type, external_gross_notional=external_gross_notional)

    @staticmethod
    def contract_metadata():
        metadata = legacy.USDTLinearPerpetualAccount.contract_metadata()
        metadata.update(version=VERSION, filter_profile_id=FILTER_PROFILE_ID,
            closing_min_notional_exempt=True, min_notional_scope='OPENING_LEGS_ONLY',
            opening_min_notional_assumption_USDT=10, min_quantity_assumption='1e-8',
            quantity_step_assumption='1e-8', quantity_profile_status='UNCERTIFIED_PROXY_NOT_API_PROFILE',
            historical_filters_certified=False, native_filters_certified=False,
            instrument_API_profile_available=False,
            closing_semantics_source='https://www.bybit.com/en/help-center/article/Futures-Trading-Rules',
            closing_semantics_scope='CURRENT_PUBLIC_RULE_NOT_HISTORICAL_INSTRUMENT_CERTIFICATION')
        return metadata

    def execute_fill(self, symbol, side, quantity, event_us, signal_us, fill_id, *,
                     execution_mid_price, quote_available_us, available_quantity=None, reduce_only=False):
        return _methods()[0]['execute_fill'](self, symbol, side, quantity, event_us, signal_us, fill_id,
            execution_mid_price=execution_mid_price, quote_available_us=quote_available_us,
            available_quantity=available_quantity, reduce_only=reduce_only)

    def summary(self):
        return _methods()[0]['summary'](self)

    def snapshot(self):
        return _methods()[0]['snapshot'](self)

    @classmethod
    def from_snapshot(cls, snapshot):
        _pins()
        return _methods()[0]['from_snapshot'](cls, snapshot)
