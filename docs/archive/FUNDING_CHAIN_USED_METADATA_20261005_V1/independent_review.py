"""D076 independent saved-fill/cash review; no account, parser or audit imports.

Quantity is reconstructed from BUY/SELL gross sizes rather than producer deltas.
The result does not validate past mark values against market sources or archive
units/publication. No price arrays, API calls, downloads, fits or market replay.
"""
import argparse
from collections import Counter
from datetime import UTC, datetime
from decimal import Decimal, localcontext
import hashlib
import json
import os
from pathlib import Path
import resource
import time

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state')
D = Decimal


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def exact(row, field):
    precise = row.get('decimal_strings', {})
    return D(precise[field]) if field in precise else D(str(row[field]))


def bound_read(item):
    path = Path(item['path']).resolve()
    assert path.is_relative_to(STATE) or path.is_relative_to(ROOT)
    assert path.stat().st_size < 5_000_000, 'Only small saved JSON inputs'
    assert digest(path) == item['sha256']
    return json.loads(path.read_bytes())


def expected_event(q, opened, event, mark_time, mark, rate):
    assert not q or opened is not None and opened < event
    assert mark_time < event
    assert mark > 0
    return -q * mark * rate if q else D(0)


def hand_cases():
    # Fixed hand-known signs and scales; the two invalid clocks must fail.
    assert expected_event(D(1), 1, 3, 2, D(100), D('.001')) == D('-.1')
    assert expected_event(D(-1), 1, 3, 2, D(100), D('.001')) == D('.1')
    assert expected_event(D(-1), 1, 3, 2, D(100), D('-.001')) == D('-.1')
    assert expected_event(D(0), None, 3, 2, D(100), D('.001')) == 0
    assert D('.001') * D('.01') == D('.00001')
    assert D('.001') * D('.01') != D('.001') * D('.01') * D('.01')
    for opened, mark_time in [(3, 2), (1, 3)]:
        try:
            expected_event(D(1), opened, 3, mark_time, D(100), D('.001'))
        except AssertionError:
            pass
        else:
            raise AssertionError('Same-clock ownership/mark incorrectly admitted')
    return 8


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--primary-result', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    started = time.monotonic()
    protocol = json.loads(a.protocol.read_bytes())
    primary = json.loads(a.primary_result.read_bytes())
    assert primary['status'] == 'PASS_RAW_TO_CONDITIONAL_WALLET_CHAIN_NOT_UNIT_CERTIFICATION'
    assert primary['protocol_sha256'] == digest(a.protocol)
    assert primary['funding_unit_certified'] is False
    compared = {(w['wallet'], w['case_id']): w for w in primary['wallets']}
    results, pins = [], []
    with localcontext() as context:
        context.prec = 70
        toy_count = hand_cases()
        for report_item in protocol['wallet_reports']:
            original = bound_read(report_item)
            pins.append(report_item)
            assert len(original['cases']) == 4
            for case in original['cases']:
                assert case['symbols'] == protocol['symbols'] == ['BTCUSDT', 'ETHUSDT']
                trades = bound_read(case['artifacts']['trades.json'])
                events = bound_read(case['artifacts']['funding.json'])
                summary = case['summary']
                pins.extend(case['artifacts'][name] for name in ('trades.json', 'funding.json'))
                assert len(events) == 1818 and summary['terminal_cash_realized']
                assert all(exact(pos, 'quantity') == 0 for symbol, pos in summary['positions'].items()
                           if symbol != 'decimal_strings')
                # Merge in original tape order; funding owns only earlier fills.
                assert [t['event_us'] for t in trades] == sorted(t['event_us'] for t in trades)
                assert [(r['event_us'], r['symbol']) for r in events] == sorted((r['event_us'], r['symbol']) for r in events)
                assert len({(r['symbol'], r['event_us']) for r in events}) == len(events)
                q = {s: D(0) for s in case['symbols']}
                opened = {s: None for s in case['symbols']}
                cursor, paid, received, zero, cash = 0, D(0), D(0), 0, D(0)
                max_event_error = D(0)
                by_sign = Counter()
                event_totals = []
                scale = D('1') if case['unit_id'] == 'RAW_AS_FRACTION' else D('.01')
                assert case['unit_id'] in ('RAW_AS_FRACTION', 'RAW_AS_PERCENT')

                def consume(t):
                    s = t['symbol']
                    size = exact(t, 'gross_quantity')
                    assert size > 0 and t['side'] in ('BUY', 'SELL')
                    before = q[s]
                    delta = size if t['side'] == 'BUY' else -size
                    q[s] += delta
                    assert exact(t, 'quantity_before') == before
                    assert exact(t, 'quantity_after') == q[s]
                    assert exact(t, 'position_delta') == delta
                    if q[s] == 0:
                        opened[s] = None
                    elif before == 0 or before * q[s] < 0:
                        opened[s] = t['event_us']
                    return exact(t, 'cash_delta')

                for r in events:
                    s, stamp = r['symbol'], r['event_us']
                    while cursor < len(trades) and trades[cursor]['event_us'] < stamp:
                        cash += consume(trades[cursor])
                        cursor += 1
                    # Do not trust saved position_delta or owned alone.
                    owned = q[s] != 0 and opened[s] is not None and opened[s] < stamp
                    assert r['owned'] == owned
                    assert exact(r, 'quantity') == q[s]
                    rate = D(str(r['raw_rate'])) * scale
                    assert D(r['assumed_fraction_decimal']) == rate
                    assert D(str(r['conditional_rate_scale'])) == scale
                    assert r['raw_rate_unit'] == 'UNCONFIRMED'
                    if r.get('status') == 'NO_POSITION_NO_PAST_MARK':
                        assert not owned and q[s] == 0
                        assert r['mark_price'] is None and r['mark_close_us'] is None
                        expected = D(0)
                    else:
                        assert r['rate_available_us'] == stamp
                        assert exact(r, 'rate_fraction') == rate
                        expected = expected_event(q[s], opened[s], stamp, r['mark_close_us'],
                                                  exact(r, 'mark_price'), rate)
                    amount = exact(r, 'signed_funding_USDT')
                    error = abs(amount - expected)
                    assert error <= D('1e-30')
                    max_event_error = max(max_event_error, error)
                    if amount < 0:
                        paid += amount
                        by_sign[s + ':PAID'] += 1
                    elif amount > 0:
                        received += amount
                        by_sign[s + ':RECEIVED'] += 1
                    else:
                        zero += 1
                        by_sign[s + ':FLAT_ZERO'] += 1
                    event_totals.append(amount)
                while cursor < len(trades):
                    cash += consume(trades[cursor])
                    cursor += 1
                assert all(v == 0 for v in q.values())
                funding = sum(event_totals, D(0))
                # cash_delta excludes collateral movements; they cancel internally.
                expected_nav = D('10000') + cash + funding
                wallet_error = abs(expected_nav - exact(summary, 'NAV'))
                assert wallet_error <= D('1e-30')
                assert abs(funding - exact(summary, 'funding_USDT')) <= D('1e-30')
                key = (report_item['role'], case['id'])
                target = compared.pop(key)
                assert D(target['funding_total_decimal']) == funding
                assert target['funding_events'] == len(events)
                assert target['owned_events'] == sum(bool(r['owned']) for r in events)
                assert {k: v['count'] for k, v in target['funding_by_asset_sign'].items()} == dict(by_sign)
                results.append(dict(wallet=key[0], case_id=key[1], events=len(events),
                    funding_decimal=str(funding), paid_decimal=str(paid), received_decimal=str(received),
                    zero_events=zero, trade_cash_decimal=str(cash), expected_terminal_NAV_decimal=str(expected_nav),
                    terminal_wallet_error_USDT=str(wallet_error), max_event_error_USDT=str(max_event_error),
                    quantity_source='BUY_SELL_GROSS_SIZE_TAPE_NOT_POSITION_DELTA', opened_time_verified=True))
    assert len(results) == 8 and not compared
    result = dict(status='PASS_INDEPENDENT_SIGNED_FILL_OWNERSHIP_AND_FULL_CAPITAL_CASH_NOT_UNIT_CERTIFICATION',
        created_utc=datetime.now(UTC).isoformat(), task_id=os.environ.get('COIN_TASK_ID'),
        source_sha256=digest(__file__), protocol_sha256=digest(a.protocol), primary_result_sha256=digest(a.primary_result),
        input_pins=pins, hand_known_checks=toy_count, wallets=results,
        total_wallet_events=sum(r['events'] for r in results),
        archive_raw_values_independently_reread=False, market_mark_values_independently_reread=False,
        archive_units_certified=False, publication_certified=False, exchange_clock_certified=False,
        main_function_imports=False, account_or_parser_imports=False, market_replays=0, fits=0, API_calls=0,
        downloads=0, locked_consumed=False, orders_sent=0,
        elapsed_seconds=time.monotonic()-started,
        peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
    with a.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k:result[k] for k in ('status', 'total_wallet_events', 'elapsed_seconds', 'peak_RSS_bytes')}))


if __name__ == '__main__':
    main()
