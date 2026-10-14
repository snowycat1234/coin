"""Exact native-financial body parity for all 33 fixed generated journals."""
from pathlib import Path
import hashlib
import json
import sys

FIELDS = ('account_final', 'native_trades', 'native_funding', 'scheduler_funding',
          'rejections', 'breaches', 'ownership_allocations', 'funding_allocations',
          'original_target_rows')


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    allow_nan=False).encode()).hexdigest()


def first_difference(left, right, path='$'):
    if type(left) is not type(right):
        return path + ':TYPE'
    if isinstance(left, dict):
        if set(left) != set(right):
            return path + ':KEYS'
        for key in left:
            result = first_difference(left[key], right[key], path + '/' + str(key))
            if result:
                return result
    elif isinstance(left, list):
        if len(left) != len(right):
            return path + ':LENGTH'
        for i, (a, b) in enumerate(zip(left, right)):
            result = first_difference(a, b, path + '/' + str(i))
            if result:
                return result
    elif left != right:
        return path + ':VALUE'
    return None


def main():
    if len(sys.argv) != 4:
        raise ValueError('Pass prior generated-journal directory, fresh directory and receipt path.')
    prior, fresh, receipt = map(Path, sys.argv[1:])
    old_files = {p.name: p for p in prior.glob('*.json')}
    new_files = {p.name: p for p in fresh.glob('*.json')}
    if len(old_files) != 33 or set(old_files) != set(new_files):
        raise ValueError('EXACT_33_JOURNAL_MEMBERS_REQUIRED')
    checks = []
    for name in sorted(old_files):
        old = json.loads(old_files[name].read_text())
        new = json.loads(new_files[name].read_text())
        assert old['fixture'] == new['fixture'] and old['arm'] == new['arm']
        assert old['evidence_origin'] == new['evidence_origin'] == 'GENERATED_ONLY_NO_MARKET_PERFORMANCE'
        bodies = []
        for field in FIELDS:
            difference = first_difference(old[field], new[field])
            bodies.append(dict(field=field, prior_SHA256=digest(old[field]),
                               portable_SHA256=digest(new[field]), exact_equal=difference is None,
                               first_difference=difference))
        checks.append(dict(journal=name, bodies=bodies, passed=all(b['exact_equal'] for b in bodies)))
    passed = all(c['passed'] for c in checks)
    result = dict(schema='INDEPENDENT_EXACT_33_NATIVE_JOURNAL_BODY_PARITY_V1',
                  status='PASS_EXACT_NATIVE_BODIES' if passed else 'FAIL_NATIVE_BODY_DIFFERENCE',
                  journals=33, exact_fields_per_journal=list(FIELDS), checks=checks,
                  note='Opaque helper session UUIDs are outside these native financial fields; no numeric or Decimal-string normalization is applied.',
                  historical_GO=False, risk_parity_certified=False)
    receipt.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({k: v for k, v in result.items() if k not in ('checks', 'exact_fields_per_journal')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
