"""No-fit funding cash sensitivity on immutable saved training decisions."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import zipfile

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

HERE = Path(__file__).resolve().parent
DAY = 86_400_000_000
BAND = 60_000_000
PARENT = 'aeb65469bdbdbe6bfdc491b1182584abe3a6da3e'
DATA_COMMIT = 'e0d3400b23842f11f167a63e7d80856d76501de8'
DATA_DIR = 'research/temporal-feature-data-20261009/'
ARCHIVE_SHA = 'bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def save(path, value):
    with path.open('x') as f:
        json.dump(value, f, indent=2, allow_nan=False)
        f.write('\n')


def signed_cash(signed_quantity, rates, marks, scale=1.):
    """A short has negative quantity; positive rate gives positive cash."""
    if not math.isfinite(signed_quantity) or not math.isfinite(scale) or scale <= 0:
        raise ValueError('Invalid quantity/scale')
    if len(rates) != len(marks) or not np.isfinite(rates).all() or not np.isfinite(marks).all() or np.any(np.asarray(marks) <= 0):
        raise ValueError('Unknown charge mark/rate is never zero-filled')
    return float(-signed_quantity * scale * math.fsum(float(r) * float(m) for r, m in zip(rates, marks)))


def enclosure(coefficients, low_marks, high_marks, optional):
    """Signed linear interval bounds; optional boundary ownership includes 0."""
    if len({len(coefficients), len(low_marks), len(high_marks), len(optional)}) != 1:
        raise ValueError('Mismatched event bound arrays')
    lows, highs = [], []
    for c, lo, hi, choice in zip(coefficients, low_marks, high_marks, optional):
        if not math.isfinite(c + lo + hi) or lo <= 0 or hi < lo:
            raise ValueError('Invalid conditional mark bound')
        a, b = sorted((c * lo, c * hi))
        lows.append(min(0., a) if choice else a)
        highs.append(max(0., b) if choice else b)
    return [math.fsum(lows), math.fsum(highs)]


def event_window(t, hours, start, end):
    if not (start < end and np.all(np.diff(t) > 0) and np.isfinite(hours).all() and np.all(hours > 0)):
        raise ValueError('Event identity/interval invalid')
    lower, upper = start - BAND, end + BAND
    before = int(np.searchsorted(t, lower, side='left')) - 1
    after = int(np.searchsorted(t, upper, side='right'))
    if before < 0 or after >= len(t):
        raise ValueError('Unbracketed holding/event window')
    gaps = np.diff(t[before:after + 1])
    h = hours[before:after + 1] * 3_600_000_000
    valid = (np.abs(gaps - h[:-1]) <= BAND) | (np.abs(gaps - h[1:]) <= BAND)
    if not valid.all():
        raise ValueError('Missing or unexplained funding event; no filtered result')
    indices = np.flatnonzero((t >= lower) & (t <= upper))
    central = (t[indices] > start) & (t[indices] <= end)
    optional = (np.abs(t[indices] - start) <= BAND) | (np.abs(t[indices] - end) <= BAND)
    return indices, central, optional


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--protocol-sha256', required=True)
    args = parser.parse_args()
    state = args.state.resolve()
    if not state.is_relative_to(Path('/workspace')):
        raise ValueError('Task STATE must be under /workspace')
    state.mkdir(parents=True, exist_ok=True)
    def budget_check():
        if sum(p.stat().st_size for p in state.rglob('*') if p.is_file()) > 10_485_760:
            raise ValueError('10MiB task-output budget exceeded')
    budget_check()
    root = HERE.parents[1]
    git = lambda *a: subprocess.check_output(['git', *a], cwd=root)
    if git('rev-parse', 'HEAD').decode().strip() != args.source_commit or git('status', '--porcelain').strip():
        raise ValueError('Clean exact published implementation required')
    protocol_raw = (HERE / 'ECONOMIC_CHECK_PROTOCOL.json').read_bytes()
    if sha(protocol_raw) != args.protocol_sha256:
        raise ValueError('Frozen economic check differs')
    bound_files = ['results/PREDICTIONS.json', 'results/SAMPLE_IDENTITIES.json', 'results/RESULT.json', 'PRICE_PATCH.json']
    for name in bound_files:
        if (HERE / name).read_bytes() != git('show', PARENT + ':research/short-funding-residual-20261011/' + name):
            raise ValueError('Original science bytes changed')
    save(state / 'ECONOMIC_STARTED.json', dict(source_commit=args.source_commit, protocol_sha256=sha(protocol_raw), fits=0, original_STOP_unchanged=True))
    index = json.loads(git('show', DATA_COMMIT + ':' + DATA_DIR + 'INDEX.json'))
    if args.archive:
        raw = args.archive.read_bytes()
    else:
        parts = [git('show', DATA_COMMIT + ':' + DATA_DIR + p['file']) for p in index['parts']]
        if any(sha(b) != p['SHA256'] or len(b) != p['bytes'] for b, p in zip(parts, index['parts'])):
            raise ValueError('Public data part differs')
        raw = b''.join(parts)
    if sha(raw) != ARCHIVE_SHA or len(raw) != index['bytes']:
        raise ValueError('Source archive differs')
    identities = json.loads((HERE / 'results/SAMPLE_IDENTITIES.json').read_text())
    predictions = json.loads((HERE / 'results/PREDICTIONS.json').read_text())
    original = json.loads((HERE / 'results/RESULT.json').read_text())
    a = np.asarray(predictions['baseline_prediction']) > 0
    b = np.asarray(predictions['augmented_prediction']) > 0
    if len(identities) != 248 or len(a) != 248 or len(b) != 248:
        raise ValueError('Saved decision axis differs')
    prices, funding, projected = {}, {}, []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if z.testzip() is not None:
            raise ValueError('Source CRC invalid')
        members = json.loads(z.read('MEMBERS.json'))['files']
        def member(name):
            raw_member = z.read(name)
            if sha(raw_member) != members[name]['SHA256'] or len(raw_member) != members[name]['bytes']:
                raise ValueError('Public member differs')
            return raw_member
        for symbol in ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT'):
            price_raw = member('source_tables_not_model_inputs/daily_features/' + symbol + '.parquet')
            dtype = pq.read_schema(io.BytesIO(price_raw)).field('dt').type
            left = pa.scalar(datetime(2022, 1, 1, tzinfo=timezone.utc), type=dtype)
            right = pa.scalar(datetime(2022, 12, 31, tzinfo=timezone.utc), type=dtype)
            tab = pq.read_table(io.BytesIO(price_raw), columns=['dt', 'close', 'complete_kline'], filters=[('dt', '>=', left), ('dt', '<', right)])
            t = tab['dt'].to_numpy().astype('datetime64[us]').astype(np.int64) + DAY
            p = tab['close'].to_numpy()
            ok = np.asarray(tab['complete_kline'].to_pylist())
            prices[symbol] = {int(ti): float(pi) for ti, pi, good in zip(t, p, ok) if good and np.isfinite(pi) and pi > 0}
            event_raw = member('source_tables_not_model_inputs/economics/' + symbol + '_funding_events.parquet')
            tab = pq.read_table(io.BytesIO(event_raw), columns=['calc_time_ms', 'last_funding_rate', 'funding_interval_hours', 'past_mark_price', 'past_mark_available_us'], filters=[('calc_time_ms', '>=', 1640995200000), ('calc_time_ms', '<', 1672531200000)]).sort_by([('calc_time_ms', 'ascending')])
            t, r, h, m, mt = [tab[n].to_numpy() for n in tab.column_names]
            t = t.astype(np.int64) * 1000
            if not np.isfinite(r).all() or np.any(t >= 1672531200000000):
                raise ValueError('Funding cutoff/rate invalid')
            known = np.isfinite(m) & np.isfinite(mt)
            if np.any(known & ((m <= 0) | (t - mt <= 0) | (t - mt > BAND))):
                raise ValueError('Past-minute proxy clock invalid')
            m = np.where(known, m, np.nan)
            funding[symbol] = (t, r, h, m)
            projected.append(dict(symbol=symbol, event_rows=len(t), last_event_us=int(t.max()), exact_charge_marks=0))
    patch = json.loads((HERE / 'PRICE_PATCH.json').read_text())
    for row in patch['records']:
        t = int(datetime.fromisoformat(row['bar_start']).replace(tzinfo=timezone.utc).timestamp() * 1_000_000) + DAY
        if t not in prices[row['symbol']]:
            prices[row['symbol']][t] = row['close']
    ledger, probes, missing_common = [], [], []
    calendar_a, calendar_b = {}, {}
    for i, row in enumerate(identities):
        d, end, symbol = row['decision_us'], row['label_end_us'], row['symbol']
        p0, p1 = prices[symbol].get(d), prices[symbol].get(end)
        if p0 is None or p1 is None:
            raise ValueError('Eligible future/entry price missing; no filtered result')
        q = .12 / p0
        price = .12 * ((1 - .0008) * (1 - .00055) - p1 / p0 * (1 + .0008) * (1 + .00055))
        calendar_a[d] = calendar_a.get(d, 0.) + (price if a[i] else 0.)
        calendar_b[d] = calendar_b.get(d, 0.) + (price if b[i] else 0.)
        delta = int(b[i]) - int(a[i])
        if not (a[i] or b[i]):
            continue
        t, r, h, m = funding[symbol]
        indices, central, optional = event_window(t, h, d, end)
        if not delta:
            for j in indices[central & ~np.isfinite(m[indices])]:
                missing_common.append(dict(symbol=symbol, decision_us=d, event_us=int(t[j]), paired_effect='EXACTLY_CANCELS_UNDER_SAME_PROXY_QUANTITY_OWNERSHIP'))
            continue
        probe = dict(saved_index=i, symbol=symbol, decision_us=d, label_end_us=end,
                     entry_price=p0, quantity_per_reference_capital=q, baseline_selected=bool(a[i]), augmented_selected=bool(b[i]), delta=delta,
                     central_events=int(central.sum()), optional_boundary_events=int(optional.sum()), role=row['role'])
        probes.append(probe)
        for position, j in enumerate(indices):
            ledger.append(dict(saved_index=i, symbol=symbol, decision_us=d, event_us=int(t[j]), role=row['role'],
                q=q, delta=delta, rate=float(r[j]), past_mark=float(m[j]) if np.isfinite(m[j]) else None,
                entry_price=p0, central_held=bool(central[position]), optional=bool(optional[position])))
    dates = sorted(calendar_a)
    actual_price = math.fsum(calendar_b[d] - calendar_a[d] for d in dates) / len(dates)
    if len(dates) != 50 or abs(actual_price - original['overall']['calendar_price_cost_increment']) > 1e-14:
        raise ValueError('Original paid-price calendar proxy differs')
    summaries = {}
    for role in ('all2022', 'train_screen2022H1', 'train_screen2022H2'):
        rows = ledger if role == 'all2022' else [r for r in ledger if r['role'] == role]
        n = 50 if role == 'all2022' else 25
        price_increment = actual_price if role == 'all2022' else original['halves'][role]['calendar_price_cost_increment']
        center_rows = [r for r in rows if r['central_held']]
        central = None if any(r['past_mark'] is None for r in center_rows) else math.fsum(r['delta'] * r['q'] * r['rate'] * r['past_mark'] for r in center_rows) / n
        scales = {}
        for scale in (1., .01):
            ranges = []
            for epsilon in (.01, .05, .20):
                lows = [(1 - epsilon) * r['past_mark'] if r['past_mark'] is not None else .8 * r['entry_price'] for r in rows]
                highs = [(1 + epsilon) * r['past_mark'] if r['past_mark'] is not None else 1.2 * r['entry_price'] for r in rows]
                lo, hi = enclosure([r['delta'] * r['q'] * r['rate'] * scale for r in rows], lows, highs, [r['optional'] for r in rows])
                ranges.append(dict(assumed_relative_charge_mark_error=epsilon, paired_funding_interval=[lo / n, hi / n], price_plus_funding_interval=[price_increment + lo / n, price_increment + hi / n]))
            scales[str(scale)] = dict(central_past_minute_funding=None if central is None else central * scale,
                central_price_plus_funding=None if central is None else price_increment + central * scale, conditional_sensitivity=ranges)
        summaries[role] = dict(calendar_market_weeks=n, unchanged_price_cost_increment=price_increment, differential_events=len(rows), central_events=len(center_rows), missing_central_proxy_marks=sum(r['past_mark'] is None for r in center_rows), scales=scales)
    save(state / 'ECONOMIC_EVENTS.json', ledger)
    save(state / 'ECONOMIC_PROBES.json', probes)
    result = dict(status='CONDITIONAL_FIXED_QUANTITY_FUNDING_CHECK_NOT_NATIVE_WALLET', source_commit=args.source_commit,
        protocol_sha256=sha(protocol_raw), parent_science_commit=PARENT, archive_sha256=ARCHIVE_SHA,
        saved_decision_source={name: sha((HERE / name).read_bytes()) for name in bound_files},
        fits=0, new_predictions=0, development_reads=0, original_decision=original['decision'], original_gates=original['gates'],
        baseline_selected=int(a.sum()), augmented_selected=int(b.sum()), common_selected=int((a & b).sum()), differential_probes=len(probes),
        common_missing_marks_cancelled=missing_common, projected_source=projected, summaries=summaries,
        rate_unit='DOCUMENTARY_DECIMAL_FRACTION_CONVENTION_WITH_EXPLICIT_ALTERNATE_SCALE; NOT_PER_EVENT_API_CERTIFIED',
        exact_charge_cash='UNAVAILABLE: no exact charge mark, official API HTTP451; prior-minute marks and ownership/quantity are declared proxy assumptions',
        absolute_arm_funding_cash='UNAVAILABLE: common missing marks retained; only paired cancellation is identifiable conditionally',
        negative_coefficient='Rejects this registered prior positive direction; observed MSE increment remains and does not refute all predictive value',
        original_PASS_FAIL_changed=False, native_wallets=0, API_probes=1, API_retries_or_bypass=0)
    save(state / 'ECONOMIC_RESULT.json', result)
    budget_check()
    print(json.dumps(dict(status=result['status'], differential_probes=len(probes), overall=summaries['all2022'], original_STOP_unchanged=True)), flush=True)


if __name__ == '__main__':
    main()
