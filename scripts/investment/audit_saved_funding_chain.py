"""Independent scalar audit of accepted funding CSVs and saved research wallets.

No market replay and no producer parser/account imports. Archive physical units,
charge/publication clocks and native Bybit economics remain unconfirmed.
"""
from __future__ import annotations

import argparse
import csv
from decimal import Decimal, localcontext
from datetime import UTC, datetime
import hashlib
import io
import json
import os
from pathlib import Path
import resource
import subprocess
import time
import zipfile

import polars as pl
from quant.paths import ROOT, STATE
from quant import resources


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def checked(path, digest):
    path = Path(path).resolve()
    assert path.is_relative_to(STATE) or path.is_relative_to(ROOT), path
    assert sha(path) == digest, path
    return path


def read(receipt):
    return json.loads(checked(receipt['path'], receipt['sha256']).read_bytes())


def number(row, name):
    # Precise account strings take precedence over presentation floats.
    return Decimal(row.get('decimal_strings', {}).get(name, str(row[name])))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--protocol', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    started = time.monotonic()
    protocol = json.loads(args.protocol.read_bytes())
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                                   text=True).strip() == protocol['parent_commit']
    manifest = read(protocol['manifest'])
    assert manifest['start_us'] == protocol['start_us']
    assert manifest['end_us'] == protocol['end_us']
    selected = [r for r in manifest['market_records']
                if r['kind'] == 'fundingRate' and r['symbol'] in protocol['symbols']]
    assert len(selected) == protocol['budget']['archives'] == 20
    source_events, source_receipts = {}, []
    largest_decimal_difference = Decimal(0)
    source_bytes = 0
    for record in selected:
        receipt = json.loads(checked(record['receipt_path'],
                                    record['receipt_sha256']).read_bytes())
        archive = checked(receipt['zip_path'], receipt['zip_sha256'])
        checksum = checked(receipt['checksum_path'], receipt['checksum_sha256'])
        announced, filename = checksum.read_text().split()
        assert announced == receipt['zip_sha256'] and filename == archive.name
        normalized = checked(record['normalized_path'], record['normalized_sha256'])
        frame = pl.read_parquet(normalized)
        with zipfile.ZipFile(archive) as zipped:
            assert len(zipped.namelist()) == 1
            with zipped.open(zipped.namelist()[0]) as stream:
                rows = list(csv.reader(io.TextIOWrapper(stream, encoding='utf-8')))
        assert rows.pop(0) == ['calc_time', 'funding_interval_hours', 'last_funding_rate']
        assert len(rows) == frame.height == record['rows']
        for raw, normalized_row in zip(rows, frame.iter_rows(named=True), strict=True):
            assert len(raw) == 3 and raw[0].isascii() and raw[0].isdecimal()
            event = int(raw[0]) * 1000
            assert event == int(normalized_row['calc_time_ms']) * 1000
            assert protocol['start_us'] <= event < protocol['end_us']
            exact = Decimal(raw[2])
            assert exact.is_finite()
            # Producer keeps the raw numeric value; it does not apply a unit scale.
            assert float(raw[2]) == normalized_row['last_funding_rate']
            assert float(raw[1]) == normalized_row['funding_interval_hours']
            difference = abs(exact - Decimal(str(normalized_row['last_funding_rate'])))
            largest_decimal_difference = max(largest_decimal_difference, difference)
            key = record['symbol'], event
            assert key not in source_events
            source_events[key] = dict(raw_text=raw[2], raw_decimal=str(exact),
                raw_float=normalized_row['last_funding_rate'],
                interval=normalized_row['funding_interval_hours'])
        source_bytes += archive.stat().st_size + checksum.stat().st_size + normalized.stat().st_size
        source_receipts.append(dict(symbol=record['symbol'], month=record['month'],
            rows=len(rows), zip_path=str(archive), zip_sha256=receipt['zip_sha256'],
            checksum_path=str(checksum), checksum_sha256=receipt['checksum_sha256'],
            normalized_path=str(normalized), normalized_sha256=record['normalized_sha256'],
            receipt_path=record['receipt_path'], receipt_sha256=record['receipt_sha256']))
    assert len(source_events) == protocol['budget']['unique_source_events'] == 1818
    results = []
    for wallet in protocol['wallet_reports']:
        report = read(wallet)
        assert report['funding_unit_certified'] is False
        assert len(report['cases']) == 4
        for case in report['cases']:
            assert case['symbols'] == protocol['symbols']
            summary = case['summary']
            assert summary['completed_minutes'] == summary['required_minutes'] == 436320
            assert summary['terminal_cash_realized'] and summary['terminal_marked_notional'] == 0
            assert summary['unit_certified'] is False and summary['publication_certified'] is False
            artifacts = case['artifacts']
            funding = read(artifacts['funding.json'])
            trades = read(artifacts['trades.json'])
            scale = Decimal(str(summary['unit_scenario']['scale']))
            assert scale in (Decimal('1'), Decimal('0.01'))
            assert len(funding) == len(source_events)
            by_symbol = {s: sorted([t for t in trades if t['symbol'] == s],
                                  key=lambda x: x['event_us']) for s in protocol['symbols']}
            cursors = {s: 0 for s in protocol['symbols']}
            quantities = {s: Decimal(0) for s in protocol['symbols']}
            observed, groups, witnesses = set(), {}, {}
            maximum_amount_error = Decimal(0)
            with localcontext() as ctx:
                ctx.prec = 60
                total = Decimal(0)
                for row in funding:
                    s, event = row['symbol'], row['event_us']
                    key = s, event
                    assert key not in observed and key in source_events
                    observed.add(key)
                    raw = source_events[key]
                    assert row['raw_rate'] == raw['raw_float']
                    assert row['reported_interval_hours'] == raw['interval']
                    rate = Decimal(str(raw['raw_float'])) * scale
                    assert row['conditional_rate_scale'] == float(scale)
                    assert Decimal(row['assumed_fraction_decimal']) == rate
                    assert row['raw_rate_unit'] == 'UNCONFIRMED'
                    # Funding precedes fills at the same clock; independently derive
                    # position quantity from actual earlier fills, not receipt quantity.
                    tape = by_symbol[s]
                    while cursors[s] < len(tape) and tape[cursors[s]]['event_us'] < event:
                        trade = tape[cursors[s]]
                        assert number(trade, 'quantity_before') == quantities[s]
                        quantities[s] += number(trade, 'position_delta')
                        assert number(trade, 'quantity_after') == quantities[s]
                        cursors[s] += 1
                    owned = quantities[s] != 0
                    assert bool(row.get('owned', False)) == owned
                    amount = number(row, 'signed_funding_USDT')
                    if row.get('status') == 'NO_POSITION_NO_PAST_MARK':
                        assert not owned and quantities[s] == amount == 0
                        expected = Decimal(0)
                    else:
                        assert number(row, 'quantity') == quantities[s]
                        assert number(row, 'rate_fraction') == rate
                        assert row['rate_available_us'] == event
                        assert row['mark_close_us'] < event
                        mark = number(row, 'mark_price')
                        assert mark > 0
                        expected = -quantities[s] * mark * rate if owned else Decimal(0)
                    error = abs(expected - amount)
                    maximum_amount_error = max(maximum_amount_error, error)
                    assert error <= Decimal(protocol['amount_tolerance_USDT'])
                    category = 'RECEIVED' if amount > 0 else 'PAID' if amount < 0 else 'FLAT_ZERO'
                    group = groups.setdefault(s + ':' + category, dict(count=0, amount=Decimal(0)))
                    group['count'] += 1
                    group['amount'] += amount
                    total += amount
                    witnesses.setdefault(category, dict(symbol=s, event_us=event,
                        raw_text=raw['raw_text'], raw_float=raw['raw_float'], scale=str(scale),
                        assumed_fraction=str(rate), quantity_from_fills=str(quantities[s]),
                        mark=row.get('mark_price'), mark_close_us=row.get('mark_close_us'),
                        signed_funding_USDT=str(amount)))
                assert observed == set(source_events)
                error = abs(total - number(summary, 'funding_USDT'))
                assert error <= Decimal(protocol['summary_tolerance_USDT'])
                bridge = (number(summary, 'gross_PnL_same_quantities') - number(summary, 'fees_USDT')
                          - number(summary, 'execution_cost_USDT') + total - number(summary, 'net_PnL'))
                assert abs(bridge) <= Decimal(protocol['summary_tolerance_USDT'])
            results.append(dict(wallet=wallet['role'], case_id=case['id'], scale=str(scale),
                funding_events=len(funding), owned_events=sum(bool(x.get('owned')) for x in funding),
                funding_total_decimal=str(total), funding_summary_error_USDT=str(error),
                net_bridge_error_USDT=str(bridge), max_event_amount_error_USDT=str(maximum_amount_error),
                funding_by_asset_sign={k: dict(count=v['count'], amount=str(v['amount'])) for k,v in groups.items()},
                witnesses=witnesses, net_USDT=summary['net_PnL'],
                funding_artifact=artifacts['funding.json'], trade_artifact=artifacts['trades.json']))
    assert len(results) == protocol['budget']['wallets'] == 8
    result = dict(status='PASS_RAW_TO_CONDITIONAL_WALLET_CHAIN_NOT_UNIT_CERTIFICATION',
        parent_commit=protocol['parent_commit'], task_id=os.environ['COIN_TASK_ID'],
        created_utc=datetime.now(UTC).isoformat(), protocol_sha256=sha(args.protocol),
        audit_source_sha256=sha(__file__), manifest=protocol['manifest'],
        source_receipts=source_receipts, unique_source_events=len(source_events),
        actual_wallets=len(results), actual_wallet_events=sum(x['funding_events'] for x in results),
        max_raw_decimal_to_float_text_difference=str(largest_decimal_difference),
        source_bytes_read=source_bytes, wallets=results,
        archive_physical_unit='UNCONFIRMED', funding_unit_certified=False,
        archive_API_same_event_parity=False, settlement_publication_certified=False,
        past_mark_source_independently_revalidated=False,
        scope='SOURCE_VALUES_AND_SAVED_FILLS_TO_FUNDING_ONLY; MARKET_PRICE_QA_REUSED',
        new_market_replays=0, fits=0, HPO=0, API_calls=0, downloads=0,
        locked_consumed=False, orders_sent=0, native_Bybit_certified=False,
        elapsed_seconds=time.monotonic()-started,
        process_peak_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        resources_after=resources.status())
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2); stream.write('\n')
    print(json.dumps({k:result[k] for k in ('status','actual_wallets','actual_wallet_events',
                      'elapsed_seconds','process_peak_RSS_bytes')}))


if __name__ == '__main__':
    main()
