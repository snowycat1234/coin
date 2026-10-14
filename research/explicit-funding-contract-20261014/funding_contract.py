#!/usr/bin/env python3
"""Offline, declaration-only linear funding contract; never certifies source data."""
import argparse
import json
import re
import sys
from decimal import Decimal, localcontext


class ContractError(ValueError):
    pass


def number(value, field):
    # No float coercion, %, NaN, Infinity, exponent bombs or implicit unit parsing.
    if not isinstance(value, str) or not re.fullmatch(r'-?\d{1,24}(?:\.\d{1,24})?', value):
        raise ContractError(f'{field}: require plain decimal string (at most 24 integer/fraction digits)')
    return Decimal(value)


def check(payload):
    required = {'raw_rate', 'unit', 'conversion', 'signed_base_quantity',
                'mark_price', 'expected_cashflow', 'provenance'}
    if not isinstance(payload, dict) or set(payload) != required:
        raise ContractError('exact input fields required: ' + ', '.join(sorted(required)))
    p = payload['provenance']
    fields = {'source_kind', 'source_reference', 'field', 'record_id', 'unit_basis',
              'product', 'rate_basis'}
    if not isinstance(p, dict) or set(p) != fields:
        raise ContractError('exact provenance fields required: ' + ', '.join(sorted(fields)))
    if any(not isinstance(v, str) or not v.strip() for v in p.values()):
        raise ContractError('provenance values must be nonempty strings')
    if p['source_kind'] not in ('synthetic', 'declared_source'):
        raise ContractError('source_kind must be synthetic or declared_source; no certified mode')
    if p['product'] != 'linear_quote_settled' or p['rate_basis'] != 'per_settlement':
        raise ContractError('only linear quote-settled per-settlement rates supported')
    if payload['unit'] == 'fraction':
        if payload['conversion'] != 'none':
            raise ContractError('fraction requires conversion=none')
        scale = Decimal('1')
    elif payload['unit'] == 'percent':
        if payload['conversion'] != 'explicit_percent_divide_100':
            raise ContractError('percent requires explicit_percent_divide_100 acknowledgement')
        scale = Decimal('0.01')
    else:
        raise ContractError('unit must explicitly be fraction or percent; never inferred')
    raw = number(payload['raw_rate'], 'raw_rate')
    qty = number(payload['signed_base_quantity'], 'signed_base_quantity')
    mark = number(payload['mark_price'], 'mark_price')
    expected = number(payload['expected_cashflow'], 'expected_cashflow')
    if mark <= 0:
        raise ContractError('mark_price must be positive')
    with localcontext() as ctx:
        ctx.prec = 200  # Exact for three bounded inputs; no exchange rounding model.
        rate = raw * scale
        amount = -qty * mark * rate
        match = amount == expected
        discrepancy = 'none'
        if not match:
            discrepancy = 'cashflow_mismatch'
            if expected and amount == expected * 100:
                discrepancy = 'computed_is_100x_expected_no_auto_correction'
            elif amount and expected == amount * 100:
                discrepancy = 'expected_is_100x_computed_no_auto_correction'
        return {'contract_version': 1, 'status': 'PASS' if match else 'FAIL',
                'raw_rate': payload['raw_rate'], 'declared_unit': payload['unit'],
                'conversion': payload['conversion'], 'applied_scale': str(scale),
                'rate_fraction': str(rate), 'signed_cashflow_quote': str(amount),
                'expected_cashflow_quote': str(expected), 'discrepancy': discrepancy,
                'provenance': dict(p), 'provenance_verified': False,
                'historical_dataset_certified': False,
                'scope': 'ARITHMETIC_UNDER_CALLER_DECLARED_UNITS_ONLY'}


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ContractError('duplicate JSON field: ' + key)
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', default='-', help='JSON file or stdin (-)')
    args = parser.parse_args()
    try:
        if args.input == '-':
            payload = json.load(sys.stdin, object_pairs_hook=unique_object)
        else:
            with open(args.input, encoding='utf-8') as stream:
                payload = json.load(stream, object_pairs_hook=unique_object)
        result = check(payload)
    except (ContractError, OSError, ValueError) as exc:
        print(json.dumps({'status': 'REJECTED', 'error': str(exc),
                          'historical_dataset_certified': False}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
