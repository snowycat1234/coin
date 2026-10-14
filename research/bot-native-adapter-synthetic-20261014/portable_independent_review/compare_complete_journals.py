"""Complete JSON equivalence with only enumerated identity/set exceptions."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
import sys
from compare_native_bodies import first_difference

SESSION = re.compile(r'^(CSH_BTC_GRID_REPLACE10:[0-9]+:)([0-9a-f]{32})$')
ORDER = re.compile(r'^(CSH_BTC_GRID_REPLACE10:[0-9]+:)([0-9a-f]{32})(:[0-9]+)$')
SET_PATHS = {('adapter_state_final', 'seen_native_legs'),
             ('adapter_state_final', 'seen_native_funding'),
             ('adapter_state_final', 'expired_sessions'),
             ('adapter_state_final', 'grid', 'seen_fill_ids')}


def serialized(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def canonical(journal):
    mapping = {}
    for event in journal['policy_events']:
        if 'session_id' in event:
            match = SESSION.fullmatch(event['session_id'])
            if match is None:
                raise ValueError('INVALID_SESSION_ID')
            mapping.setdefault(match.groups(), 'IDENTITY_' + str(len(mapping)))
        for order in event.get('orders', []):
            match = ORDER.fullmatch(order)
            if match is None:
                raise ValueError('INVALID_ORDER_ID')
            key = match.groups()[:2]
            mapping.setdefault(key, 'IDENTITY_' + str(len(mapping)))

    def normalize(value, path=()):
        if isinstance(value, dict):
            return {key: normalize(child, path + (key,)) for key, child in value.items()}
        if isinstance(value, list):
            out = [normalize(child, path + ('*',)) for child in value]
            if path in SET_PATHS:
                encoded = [serialized(child) for child in out]
                if len(set(encoded)) != len(encoded):
                    raise ValueError('DUPLICATE_SET_IDENTITY')
                return [child for _, child in sorted(zip(encoded, out), key=lambda pair: pair[0])]
            return out
        session_path = (path in {('adapter_state_final', 'expired_sessions', '*'),
                                  ('adapter_state_final', 'grid', 'session_id')}
                        or path in {('policy_events', '*', 'session_id'),
                                    ('adapter_state_final', 'policy_events', '*', 'session_id')})
        order_path = path in {('policy_events', '*', 'orders', '*'),
                             ('adapter_state_final', 'policy_events', '*', 'orders', '*')}
        if session_path or order_path:
            match = (SESSION if session_path else ORDER).fullmatch(value)
            if match is None or match.groups()[:2] not in mapping:
                raise ValueError('UNBOUND_OR_INVALID_IDENTIFIER')
            prefix, nonce = match.groups()[:2]
            suffix = match.group(3) if order_path else ''
            return prefix + mapping[(prefix, nonce)] + suffix
        if isinstance(value, str) and (SESSION.fullmatch(value) or ORDER.fullmatch(value)):
            raise ValueError('UNDECLARED_IDENTIFIER_FIELD')
        return value
    return normalize(journal)


def differs(old, new):
    try:
        return first_difference(canonical(old), canonical(new)) is not None
    except ValueError:
        return True


def negative_controls(original):
    checks = []
    def verify(label, change):
        mutated = deepcopy(original)
        change(mutated)
        if not differs(original, mutated):
            raise AssertionError('MUTATION_NOT_REJECTED:' + label)
        checks.append(label)
    verify('native_decimal_fee', lambda j: j['native_trades'][0]['decimal_strings'].__setitem__('fee_amount', '0'))
    verify('additional_policy_field', lambda j: j['policy_events'][0].__setitem__('unapproved', True))
    verify('policy_clock', lambda j: j['policy_events'][0].__setitem__('event_us', j['policy_events'][0]['event_us'] + 1))
    verify('policy_clock_type', lambda j: j['policy_events'][0].__setitem__('event_us', float(j['policy_events'][0]['event_us'])))
    verify('duplicate_set_entry', lambda j: j['adapter_state_final']['seen_native_legs'].append(j['adapter_state_final']['seen_native_legs'][0]))
    first_order = next(i for i, e in enumerate(original['policy_events']) if e.get('orders'))
    verify('order_index', lambda j: j['policy_events'][first_order]['orders'].__setitem__(0, j['policy_events'][first_order]['orders'][0] + '1'))
    verify('uuid_reference_crosswire', lambda j: j['policy_events'][first_order].__setitem__('session_id', j['policy_events'][first_order]['session_id'][:-32] + '0' * 32))
    verify('session_timestamp', lambda j: j['policy_events'][first_order].__setitem__('session_id', j['policy_events'][first_order]['session_id'].replace(':17884800000000:', ':17884800000001:')))
    verify('uuid_outside_declared_path', lambda j: j['adapter_state_final'].__setitem__('undocumented_id', j['policy_events'][0]['session_id']))
    return checks


def main():
    prior, fresh, receipt = map(Path, sys.argv[1:])
    members = sorted(p.name for p in prior.glob('*.json'))
    if len(members) != 33 or set(members) != {p.name for p in fresh.glob('*.json')}:
        raise ValueError('EXACT_33_MEMBERS_REQUIRED')
    checks = []
    for name in members:
        old_raw, new_raw = (prior/name).read_bytes(), (fresh/name).read_bytes()
        old, new = json.loads(old_raw), json.loads(new_raw)
        difference = first_difference(canonical(old), canonical(new))
        checks.append(dict(journal=name, raw_bytes_equal=old_raw == new_raw,
                           raw_prior_SHA256=hashlib.sha256(old_raw).hexdigest(),
                           raw_fresh_SHA256=hashlib.sha256(new_raw).hexdigest(),
                           normalized_complete_SHA256=hashlib.sha256(serialized(canonical(new)).encode()).hexdigest(),
                           complete_equal=difference is None, first_difference=difference))
    negatives = negative_controls(json.loads((prior/'RANGE_GRID.json').read_text()))
    passed = all(c['complete_equal'] for c in checks)
    result = dict(schema='INDEPENDENT_COMPLETE_33_JOURNAL_IDENTITY_EQUIVALENCE_V1',
                  status='PASS_COMPLETE_DECLARED_IDENTITY_EQUIVALENCE' if passed else 'FAIL',
                  journals=33, checks=checks, negative_controls_rejected=negatives,
                  exception_scope=dict(uuid_alpha_rename='Only documented session/order fields; session timestamp, order suffix, repeated-reference consistency retained',
                                       set_list_sort=['/'.join(p) for p in sorted(SET_PATHS)]),
                  discarded_fields=[], number_or_decimal_normalization=False,
                  historical_GO=False, risk_parity_certified=False)
    receipt.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks', 'exception_scope')}))
    return 0 if passed else 1


if __name__ == '__main__':
    raise SystemExit(main())
