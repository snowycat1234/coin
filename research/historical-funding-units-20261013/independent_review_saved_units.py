"""Independent read-only review. No imports/reruns of the audited writer.

Checks only its named saved funding inputs and existing recorded fee journals.
Writes one new receipt beside this file; never edits old inputs or audit outputs.
"""
import argparse, calendar, csv, hashlib, io, json, struct, zipfile
from collections import Counter
from decimal import Decimal as D, localcontext
from pathlib import Path
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
S = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')

def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_bytes())
def file_record(p):
    b = p.read_bytes()
    try:
        path = str(p.relative_to(ROOT))
    except ValueError:
        try:
            path = 'audit_folder/'+str(p.relative_to(OUT))
        except ValueError:
            path = p.name
    return dict(path=path, bytes=len(b), SHA256=sha(b))
def check_record(r):
    got = file_record(ROOT/r['path'])
    assert got == r, (got, r)
def bits(x): return struct.pack('d', float(x))
def dec(r, k): return D(r.get('decimal_strings', {}).get(k, str(r[k])))

def main():
    src = load(OUT/'SOURCE_IDENTITIES.json')
    audit = load(OUT/'FIXED_TAPE_FUNDING_AUDIT.json')
    run = load(OUT/'RUN_RECEIPT.json')
    for name, r in run['outputs'].items():
        actual = file_record(OUT/name)
        assert actual['bytes'] == r['bytes'] and actual['SHA256'] == r['SHA256']
    for r in src['inputs']: check_record(r)
    paths = {2021: 'coin_2021_source_closure_20261013/prepared_2021/EVENTS.json',
             2023: 'coin_native_half_mix_20261013/prepared_2023/EVENTS.json',
             2024: 'coin_expanded_coverage_20261013/prepared_2024/EVENTS.json',
             2025: 'coin_native_half_mix_20261013/prepared_2025/EVENTS.json'}
    events = {}
    for year, path in paths.items():
        rows = load(ROOT/path)
        keys = [(r['symbol'], int(r['event_us'])) for r in rows]
        assert len(set(keys)) == len(keys)
        assert set(r['symbol'] for r in rows) == set(S)
        events[year] = dict(zip(keys, rows))
        for s in S:
            rs = [r for r in rows if r['symbol'] == s]
            ts = [int(r['event_us']) for r in rs]
            assert len(ts) == (366 if calendar.isleap(year) else 365)*3
            assert all(r['reported_interval_hours'] == 8 for r in rs)
            assert all(abs(b-a-28800000000) <= 1000000 for a, b in zip(ts, ts[1:]))
    proofs = src['official_raw_members']
    expected_keys = {(y, s, f'{y}-{m:02d}') for y, ms in
                     ((2024, range(7, 13)), (2025, range(1, 13))) for s in S for m in ms}
    assert len(proofs) == 90
    assert {(r['year'], r['symbol'], r['month']) for r in proofs} == expected_keys
    archive_events = []
    archive_rows, archive_counts = Counter(), Counter()
    manifest_path = ROOT/'coin_native_half_mix_20261013/source/2025_FUND/MANIFEST.json'
    manifest25 = load(manifest_path)
    primitive_path = ROOT/'coin_native_half_mix_20261013/source/2025_FUND/PRIMITIVES.zip'
    assert file_record(primitive_path)['SHA256'] == manifest25['SHA256']
    consumer_path = ROOT/'coin_native_half_mix_20261013/source/2025_CONSUMER/CONSUMER.zip'
    consumer_manifest_path = ROOT/'coin_native_half_mix_20261013/source/2025_CONSUMER/MANIFEST.json'
    consumer_manifest = load(consumer_manifest_path)
    consumer_members = {r['path']: r for r in consumer_manifest['members']}
    assert file_record(consumer_path)['SHA256'] == consumer_manifest['archive_SHA256']
    assert file_record(consumer_path)['bytes'] == consumer_manifest['archive_bytes']
    assert {str(p.relative_to(ROOT)) for p in (manifest_path, consumer_path, consumer_manifest_path)} <= {r['path'] for r in src['inputs']}
    with zipfile.ZipFile(consumer_path) as consumer:
        consumer_tables = {}
        for s in S:
            name = f'economics2025/{s}_funding_events.parquet'
            b = consumer.read(name)
            assert sha(b) == consumer_members[name]['SHA256'] and len(b) == consumer_members[name]['bytes']
            rows = pq.read_table(io.BytesIO(b), columns=['calc_time_ms', 'last_funding_rate', 'funding_interval_hours']).to_pylist()
            keys = [int(r['calc_time_ms']) for r in rows]
            assert len(keys) == len(set(keys))
            consumer_tables[s] = dict(zip(keys, rows))
        wrappers = {p: zipfile.ZipFile(ROOT/p) for p in set(x['wrapper'] for x in proofs)}
        try:
            producer24 = json.loads(wrappers['coin_expanded_coverage_20261013/coin_public_tail_archives_20261008_part01.zip'].read('tail_data/reports/download_manifest.json'))['archives']
            for pr in proofs:
                y, s, m = pr['year'], pr['symbol'], pr['month']
                outer = wrappers[pr['wrapper']]
                b = outer.read(pr['member'])
                assert sha(b) == pr['ZIP_SHA256']
                url = f'https://data.binance.vision/data/futures/um/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip'
                assert pr['official_URL'] == url
                if y == 2024:
                    c = outer.read(pr['member']+'.CHECKSUM')
                    assert sha(c) == pr['CHECKSUM_SHA256'] and c.decode().split()[0] == sha(b)
                    r = next(r for r in producer24 if r.get('symbol') == s and r.get('family') == 'fundingRate' and r.get('year') == y and r.get('month') == int(m[-2:]))
                    assert r['sha256'] == sha(b) and r['url'] == url
                else:
                    rb = outer.read('receipts/'+pr['member'].split('/', 1)[1]+'.json')
                    r = json.loads(rb)
                    assert sha(rb) == pr['receipt_SHA256'] and r['SHA256'] == sha(b) and r['url'] == url
                    assert manifest25['members'][pr['member']]['SHA256'] == sha(b)
                with zipfile.ZipFile(io.BytesIO(b)) as z:
                    assert len(z.namelist()) == 1 and z.testzip() is None
                    cb = z.read(z.namelist()[0])
                    assert sha(cb) == pr['CSV_SHA256']
                    reader = csv.DictReader(io.StringIO(cb.decode()))
                    assert reader.fieldnames == ['calc_time', 'funding_interval_hours', 'last_funding_rate']
                    rows = list(reader)
                assert len(rows) == pr['raw_rows'] == pr['prepared_decimal_exact_matches'] == pr['prepared_float_exact_matches']
                assert len(rows) == calendar.monthrange(y, int(m[-2:]))[1]*3
                assert pr['consumer_parquet_float_exact_matches'] == (len(rows) if y == 2025 else 0)
                for r in rows:
                    t = int(r['calc_time'])
                    k = (s, t*1000)
                    q = events[y][k]
                    assert D(str(q['raw_rate'])) == D(r['last_funding_rate'])
                    assert q['reported_interval_hours'] == D(r['funding_interval_hours']) == 8
                    assert bits(q['raw_rate']) == bits(r['last_funding_rate'])
                    if y == 2025:
                        p = consumer_tables[s][t]
                        assert bits(p['last_funding_rate']) == bits(r['last_funding_rate']) and p['funding_interval_hours'] == 8
                    archive_events.append((y, *k))
                assert pr['semantic_unit_declaration_in_csv'] is None
                archive_rows[y] += len(rows)
                archive_counts[y] += 1
        finally:
            for z in wrappers.values(): z.close()
    assert len(archive_events) == len(set(archive_events)) == 8235
    assert dict(archive_rows) == {2024: 2760, 2025: 5475}
    assert dict(archive_counts) == {2024: 30, 2025: 60}
    e0 = src['source_matches']['e0_parquet']
    e0counts = Counter()
    replicated = []
    with zipfile.ZipFile(ROOT/'coin_native_half_mix_20261013/source/2023_FUND/features.zip') as z, zipfile.ZipFile(ROOT/'coin_expanded_coverage_20261013/H1.zip') as h1:
        mem = json.loads(z.read('MEMBERS.json'))['files']
        prov = json.loads(z.read('provenance/PRIOR_PUBLIC_SOURCE_RECEIPTS.json'))
        assert len([r for r in prov['objects'] if r.get('family') == 'fundingRate' and r.get('symbol') in S and any(r.get('month', '').startswith(str(y)) for y in (2021, 2023, 2024))]) == 120
        assert not any('/raw/fundingRate/' in n and n.endswith('.zip') for n in h1.namelist())
        for s in S:
            pr = next(r for r in e0['members'] if r['symbol'] == s)
            raw = z.read(pr['member'])
            assert sha(raw) == pr['member_SHA256'] == mem[pr['member']]['SHA256']
            hp = next(r for r in src['source_matches']['2024_H1_saved_parquet']['members'] if r['symbol'] == s)
            hr = h1.read(hp['member'])
            assert sha(hr) == hp['SHA256'] and raw == hr
            replicated.append(s)
            rows = pq.read_table(io.BytesIO(raw), columns=['calc_time_ms', 'last_funding_rate', 'funding_interval_hours']).to_pylist()
            assert len(rows) == pr['rows']
            seen, allkeys = Counter(), set()
            for r in rows:
                k = (s, int(r['calc_time_ms'])*1000)
                assert k not in allkeys
                allkeys.add(k)
                for year in (2021, 2023, 2024):
                    if k in events[year]:
                        q = events[year][k]
                        assert bits(q['raw_rate']) == bits(r['last_funding_rate'])
                        assert q['reported_interval_hours'] == r['funding_interval_hours'] == 8
                        seen[year] += 1
                        e0counts[year] += 1
            assert dict(seen) == {2021: 1095, 2023: 1095, 2024: 549}
            assert {str(k): v for k, v in seen.items()} == pr['matched_prepared_events'] == pr['seen_prepared_events']
            assert seen[2024] == hp['matched_prepared_events']
    assert dict(e0counts) == {2021: 5475, 2023: 5475, 2024: 2745}
    case_checks = []
    with localcontext() as ctx:
        ctx.prec = 70
        for case in audit['cases']:
            for r in case['inputs']: check_record(r)
            account = load(ROOT/case['inputs'][0]['path'])
            result = load(ROOT/case['inputs'][1]['path'])
            fs, year = account['funding'], case['year']
            ev = events[year]
            keys = [(r['symbol'], int(r['event_us'])) for r in fs]
            ids = [r['event_id'] for r in fs]
            assert len(fs) == len(set(keys)) == len(set(ids)) == len(ev) == case['events']
            assert set(keys) == set(ev)
            times = [k[1] for k in keys]
            assert all(a <= b for a, b in zip(times, times[1:]))
            sums = Counter()
            cash = absolute = err = cum = lo = hi = D(0)
            owned = zero = 0
            for r, k in zip(fs, keys):
                q = ev[k]
                assert r['raw_rate'] == q['raw_rate'] and r['reported_interval_hours'] == q['reported_interval_hours'] == 8
                amount = dec(r, 'signed_funding_USDT')
                cash += amount
                absolute += abs(amount)
                sums[r['symbol']] += amount
                cum += amount
                lo, hi = min(lo, cum), max(hi, cum)
                if r['owned']:
                    owned += 1
                    rate = dec(r, 'rate_fraction')
                    assert rate == D(str(q['raw_rate'])) and D(str(r['conditional_rate_scale'])) == 1
                    assert int(r['mark_close_us']) < int(r['event_us'])
                    expected = -dec(r, 'quantity')*dec(r, 'mark_price')*rate
                    err = max(err, abs(expected-amount))
                    assert expected == amount
                else:
                    zero += 1
                    assert amount == 0
            bridge = result['independent_decimal_NAV_bridge']
            assert cash == D(bridge['funding_cash_USDT'])
            net = D(bridge['NAV'])-10000
            assert abs(net-(D(bridge['gross_price_USDT'])-D(bridge['execution_USDT'])-D(bridge['fees_USDT'])+cash)) < D('1e-28')
            delta = -D('.99')*cash
            values = dict(recorded_signed_funding_cash_USDT=cash, recorded_absolute_funding_USDT=absolute,
                          maximum_signed_amount_equation_error_USDT=err, recorded_net_USDT=net,
                          recorded_net_return_percentage=net/100, recorded_funding_drag_percentage_points=-cash/100,
                          fixed_tape_scale_point01_minus_scale1_cash_USDT=delta,
                          fixed_tape_same_quantities_scale_point01_net_USDT=net+delta,
                          fixed_tape_cumulative_funding_cash_min_USDT=lo,
                          fixed_tape_cumulative_funding_cash_max_USDT=hi,
                          eventwise_unit_independent_conservative_cash_difference_abs_bound_USDT=D('.99')*absolute)
            for k, v in values.items(): assert D(case[k]) == v, (year, case['arm'], k, v, case[k])
            assert owned == case['owned_events'] and zero == case['zero_owned_events']
            assert {s: D(case['signed_funding_by_symbol'][s]) for s in S} == dict(sums)
            assert [D(x) for x in case['fixed_tape_cash_difference_uniform_scale_in_point01_to1_interval_USDT']] == [min(D(0), delta), max(D(0), delta)]
            assert case['duplicate_event_ids'] == 0 and case['source_rate_exact_matches'] == len(fs)
            assert case['actual_strategy_counterfactual_return'].startswith('NOT_COMPUTED_OR_BOUNDED')
            assert case['full_calendar'] == result.get('full_calendar', False) and case['paid_flat'] == result.get('paid_flat') and case['status'] == result['status']
            case_checks.append(dict(year=year, arm=case['arm'], events=len(fs), owned_events=owned,
                                    zero_owned_events=zero, duplicate_keys=0, duplicate_event_ids=0,
                                    source_numeric_exact_matches=len(fs), strict_prior_mark_violations=0,
                                    equation_error_USDT=str(err), funding_cash_USDT=str(cash),
                                    fixed_tape_point01_minus1_cash_USDT=str(delta),
                                    account_SHA256=case['inputs'][0]['SHA256'], result_SHA256=case['inputs'][1]['SHA256']))
    assert audit['formula'] == 'signed_cash=-recorded_owned_quantity*recorded_strict_prior_mark*raw_rate*scale; no hour factor'
    assert src['source_matches']['official_raw_matches']['economic_rate_unit_certified'] is False
    assert e0['unit_not_certified_by_receipts'] is True
    assert 'no claim of counterfactual strategy returns or native venue certification' in audit['scope']
    receipt = dict(
        status='PASS_FOR_NARROW_SOURCE_IDENTITY_AND_FIXED_RECORDED_TAPE_CLAIMS',
        review_date_UTC='2026-10-13',
        method='Independent read-only verifier, not an import or rerun of audit_saved_units.py. All 90 nested archive bodies and all eight existing funding journals were checked against named saved sources. No execution/financial kernels or provider, API, Library, wallet, target, fit or 2026 holdout calls.',
        reviewed_audit_files=[file_record(OUT/n) for n in ('audit_saved_units.py', 'SOURCE_IDENTITIES.json', 'FIXED_TAPE_FUNDING_AUDIT.json', 'RUN_RECEIPT.json')],
        review_code=file_record(Path(__file__).resolve()),
        checks=dict(all_reported_input_and_output_hashes_verified=True, official_archives=90,
                    final_consumer_archive_and_five_member_manifest_hashes_verified=True,
                    official_raw_event_rate_time_interval_exact_matches=8235,
                    official_archive_breakdown={'2024H2': dict(archives=30, events=2760), '2025': dict(archives=60, events=5475)},
                    archive_event_duplicates=0, reported_nominal_interval_hours=8,
                    event_time_rule='saved event_us equals int(raw calc_time_ms)*1000; no rounding of millisecond jitter',
                    e0_raw_numeric_matches_by_year={str(k): v for k, v in e0counts.items()}, H1_raw_numeric_matches_2024=2745,
                    e0_H1_members_byte_identical_symbols=replicated, fee_tapes=len(case_checks),
                    fee_journal_events=sum(x['events'] for x in case_checks),
                    strict_prior_mark_formula='-recorded_quantity * recorded_mark_price * raw_numeric_rate; no hour multiplier; exactly one journal record per symbol/event and funding sum equals saved NAV bridge',
                    all_eight_case_numerical_fields_recomputed_exactly=True),
        economic_interpretation='Numeric preservation certifies no source rate/interval scaling during these saved transformations. It does not certify the historical percentage-versus-fraction economics, venue charging/publication semantics, authentic live account outcomes, or actual strategy results under alternate units. A .01 scaling is conditional fee arithmetic on unchanged recorded quantities and marks. Cash/NAV feedback, sizing, fills, costs, halts and terminal outcomes can change in a rerun, which was not performed.',
        limitations=[
            'e0 and H1 member bytes are identical for all five symbols. H1 provides a second saved copy, not an independent observation of raw funding semantics. Neither wrapper retains corresponding original raw funding bodies.',
            'Official provenance is the retained checksums/producer manifests/receipts and their canonical data.binance.vision URLs; this review made no fresh provider requests.',
            'Strict-prior mark timing and fee arithmetic were verified from saved records; independently reconstructing each mark from market bars, ownership from fills, or full cash journals is outside this fee-only review.',
            'The zero provider/wallet/fit/Library/holdout/old-mutation counts in RUN_RECEIPT agree with the inspected writer design; historical process counts cannot be forensically certified from saved artifacts alone.'],
        verified_supplementary_inventory_inputs=[file_record(manifest_path), file_record(consumer_path), file_record(consumer_manifest_path)],
        case_checks=case_checks,
        review_scope_outcome='No numerical or scope defect found in requested narrow claims. Caveats above must accompany publication; do not label source numeric identity as economic-unit certification or fixed-tape fee changes as counterfactual strategy returns.')
    path = RECEIPT
    with path.open('x') as f:
        json.dump(receipt, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(dict(status=receipt['status'], receipt=file_record(path), archives=90,
                          official_exact_comparisons=8235, fee_cases=len(case_checks),
                          fee_events=sum(x['events'] for x in case_checks),
                          supplementary_inputs=receipt['verified_supplementary_inventory_inputs']), indent=2))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace-root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=OUT/'INDEPENDENT_REVIEW_RECEIPT.json', help='New receipt file path; must not already exist.')
    args = parser.parse_args()
    ROOT = args.workspace_root.resolve()
    RECEIPT = args.output.resolve()
    main()
