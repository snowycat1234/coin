"""Frozen, conditional weekly rank-replacement attribution. Not a wallet replay.

Importing this module never opens market data. Real analysis needs an explicit
frozen-spec hash and verifies FREEZE.json before reading source arrays.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np

DAY = 86_400_000_000
MINUTE = 60_000_000
WEEK = 7 * DAY
START = 1_672_531_200_000_000
END = 1_704_067_200_000_000
ANCHOR = END  # Original 2024-01-01 Monday anchor, extended backwards.
SYMBOLS = ('BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'DOGEUSDT')
FEE = .00055
EXECUTION = .0008
COMPONENTS = ('price', 'funding', 'execution_cost', 'fee', 'net')
METRICS = tuple(f'{path}_{key}' for path in ('keep', 'switch', 'delta') for key in COMPONENTS)


def require(condition, message):
    if not bool(condition):
        raise ValueError(message)


def sha(path):
    with Path(path).open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256')
    return digest.hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def pin(path, record):
    require(Path(path).stat().st_size == record['bytes'], f'Byte mismatch: {path}')
    require(sha(path) == record['SHA256'], f'Hash mismatch: {path}')


def load_original_ranker(original_root):
    path = Path(original_root) / 'modules/transformer_v2/portfolio.py'
    spec = importlib.util.spec_from_file_location('frozen_original_portfolio', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.market_neutral


def validate_daily(close, available):
    require(available.ndim == 1 and available.dtype.kind in 'iu' and len(available),
            'Nonempty integer daily availability clock required')
    require(np.all(available >= 0) and np.all(available <= np.iinfo(np.int64).max),
            'Daily clock out of range')
    require(np.all(available % DAY == 0) and np.all(np.diff(available.astype(np.int64)) > 0),
            'Unique increasing daily availability required')
    require(close.shape == (len(available), len(SYMBOLS)), 'Ordered daily cube shape')


def past_context(close, available, timestamp):
    """Literal original eligibility and score convention, without risk sizing."""
    index = int(np.searchsorted(available, timestamp, side='right') - 1)
    valid = np.zeros(len(SYMBOLS), dtype=bool)
    if (index < 30 or available[index] != timestamp
            or np.any(np.diff(available[index - 30:index + 1]) != DAY)):
        return valid, None
    history = close[index - 30:index + 1]
    valid = np.all(np.isfinite(history) & (history > 0), axis=0)
    with np.errstate(invalid='ignore', divide='ignore'):
        momentum = history[-1] / history[-22] - 1.
    return valid, momentum


def names_for(mask):
    return [s for j, s in enumerate(SYMBOLS) if mask[j]]


def replacement_schedule(close, available, ranker, start=START, end=END, anchor=ANCHOR):
    """Recover predecessor scheduled state, then preserve original daily clears."""
    validate_daily(close, available)
    first_rank = anchor + (start - anchor) // WEEK * WEEK
    # Need the predecessor ranking even if the requested start itself is Monday.
    if first_rank == start:
        first_rank -= WEEK
    raw = np.zeros(len(SYMBOLS))
    previous_rank = None
    previous_rank_names = []
    prior_clears = []
    rows, forced, eligible = [], [], {}
    for timestamp in range(first_rank, end, DAY):
        valid, momentum = past_context(close, available, timestamp)
        eligible[timestamp] = valid
        incumbent = names_for(raw > 0)
        invalid_incumbent = names_for((raw > 0) & ~valid)
        if (timestamp - anchor) % WEEK == 0:
            scores = np.full(len(SYMBOLS), np.nan) if momentum is None else momentum
            new_raw = ranker(scores[None, :], valid[None, :], k=2, gross=.6)[0]
            incoming_target = names_for(new_raw > 0)
            outgoing = [s for s in incumbent if s not in incoming_target]
            incoming = [s for s in incoming_target if s not in incumbent]
            if timestamp >= start:
                require(previous_rank == timestamp - WEEK, 'Missing predecessor weekly state')
                rows.append({
                    'rank_us': timestamp, 'predecessor_rank_us': previous_rank,
                    'predecessor_rank_long_names': previous_rank_names.copy(),
                    'incumbent_before_rank': incumbent, 'new_rank_long_names': incoming_target,
                    'retained': [s for s in incumbent if s in incoming_target],
                    'outgoing': outgoing, 'incoming': incoming,
                    'n_outgoing': len(outgoing), 'n_incoming': len(incoming),
                    'm': max(len(outgoing), len(incoming)),
                    'cash_outgoing_padding': max(len(incoming) - len(outgoing), 0),
                    'cash_incoming_padding': max(len(outgoing) - len(incoming), 0),
                    'eligible': valid.tolist(),
                    'momentum': [float(scores[j]) if valid[j] else None
                                 for j in range(len(SYMBOLS))],
                    'forced_at_rank': invalid_incumbent,
                    'preceding_daily_forced_clears': prior_clears.copy(),
                    'entry_us': timestamp + MINUTE,
                    'exit_us': timestamp + WEEK + MINUTE,
                })
            raw = new_raw.copy()
            previous_rank = timestamp
            previous_rank_names = incoming_target.copy()
            prior_clears = []
        if invalid_incumbent:
            event = {'decision_us': timestamp, 'long_symbols': invalid_incumbent,
                     'kind': 'AT_SCHEDULED_RANK' if (timestamp - anchor) % WEEK == 0
                             else 'DAILY_ELIGIBILITY_FORCED_CLEAR'}
            forced.append(event)
            if (timestamp - anchor) % WEEK:
                prior_clears.append(event)
        raw[~valid] = 0.  # Exactly the original irreversible-until-next-rank clear.
    return rows, forced, eligible


def classify_week(row, eligibility, forced, source_start=START, source_end=END):
    """Uniform boundary exclusion first; no last-week shortening or gap deletion."""
    if row['entry_us'] < source_start or row['exit_us'] >= source_end:
        return 'BOUNDARY_EXCLUDED', [{
            'reason': 'FULL_ORIGINAL_MONDAY_TO_MONDAY_OPEN_INTERVAL_OUTSIDE_SOURCE',
            'required_entry_us': row['entry_us'], 'required_exit_us': row['exit_us'],
            'source_start_inclusive_us': source_start, 'source_end_exclusive_us': source_end,
        }]
    problems = []
    if row['forced_at_rank']:
        problems.append({'reason': 'FORCED_INVALID_INCUMBENT_AT_RANK',
                         'symbols': row['forced_at_rank']})
    # Eligibility at Tnext also matters: the actual terminal exit is Tnext+1 minute.
    # No asset in either differing basket may be counterfactually held invalid.
    compared = set(row['outgoing']) | set(row['incoming'])
    for timestamp in range(row['rank_us'], row['exit_us'], DAY):
        valid = eligibility.get(timestamp)
        require(valid is not None, 'Missing complete daily eligibility context')
        bad = [s for j, s in enumerate(SYMBOLS) if s in compared and not valid[j]]
        if bad:
            problems.append({'reason': 'INVALID_COMPARISON_ASSET_BEFORE_EXIT',
                             'decision_us': timestamp, 'symbols': bad})
    # A forced clear of a retained name also invalidates a claimed original two-slot path.
    for event in forced:
        if row['rank_us'] < event['decision_us'] < row['exit_us']:
            problems.append({'reason': 'ORIGINAL_LONG_PATH_FORCED_CLEAR_INSIDE_INTERVAL',
                             'event': event})
    if problems:
        return 'NOT_ESTIMABLE_FORCED_ELIGIBILITY', problems
    if row['m'] == 0:
        return 'COMPLETE_NO_CHANGE', []
    if row['preceding_daily_forced_clears']:
        return 'COMPLETE_CHANGE_AFTER_SEPARATELY_REPORTED_FORCED_CLEAR', []
    return ('COMPLETE_RANK_REPLACEMENT' if row['n_outgoing'] == row['n_incoming']
            else 'COMPLETE_RANK_CASH_TRANSITION'), []


def member_costs(entry, exit, funding=0., fee=FEE, execution=EXECUTION):
    """One initial trade-OPEN reference dollar; quote/fill distinction explicit."""
    require(np.isfinite([entry, exit, funding, fee, execution]).all()
            and entry > 0 and exit > 0 and fee >= 0 and 0 <= execution < 1,
            'Invalid accounting input')
    ratio = exit / entry
    return {
        'entry': entry, 'exit': exit, 'quantity_per_reference_USDT': 1. / entry,
        'terminal_reference_notional': ratio, 'price': ratio - 1., 'funding': funding,
        'initial_sell_execution': execution,
        'initial_sell_fee': fee * (1. - execution),
        'initial_buy_execution': execution,
        'initial_buy_fee': fee * (1. + execution),
        'terminal_sell_execution': execution * ratio,
        'terminal_sell_fee': fee * (1. - execution) * ratio,
    }


def compare_baskets(outgoing, incoming):
    """Unpaired sums, padded CASH, 1/m changed baskets and fixed two-slot primary."""
    m = max(len(outgoing), len(incoming))
    require(m <= 2, 'Original two-slot maximum exceeded')
    result = {'m': m, 'n_outgoing': len(outgoing), 'n_incoming': len(incoming)}
    keep = dict.fromkeys(COMPONENTS, 0.)
    switch = dict.fromkeys(COMPONENTS, 0.)
    if m:
        for member in outgoing:
            keep['price'] += member['price'] / m
            keep['funding'] += member['funding'] / m
            keep['execution_cost'] += member['terminal_sell_execution'] / m
            keep['fee'] += member['terminal_sell_fee'] / m
            switch['execution_cost'] += member['initial_sell_execution'] / m
            switch['fee'] += member['initial_sell_fee'] / m
        for member in incoming:
            switch['price'] += member['price'] / m
            switch['funding'] += member['funding'] / m
            switch['execution_cost'] += (member['initial_buy_execution']
                                         + member['terminal_sell_execution']) / m
            switch['fee'] += (member['initial_buy_fee'] + member['terminal_sell_fee']) / m
        for path in (keep, switch):
            path['net'] = path['price'] + path['funding'] - path['execution_cost'] - path['fee']
    for key in COMPONENTS:
        result[f'keep_{key}'] = keep[key]
        result[f'switch_{key}'] = switch[key]
        result[f'delta_{key}'] = switch[key] - keep[key]
    for key in METRICS:
        result[f'primary_{key}'] = (m / 2.) * result[key]
    require(abs(result['delta_net'] - (result['delta_price'] + result['delta_funding']
            - result['delta_execution_cost'] - result['delta_fee'])) < 1e-12,
            'Paired component identity')
    return result


def prepare_events(events, start=START, end=END):
    step = 8 * 60 * MINUTE
    slots = list(range(start, end, step))
    by_symbol = {s: [] for s in SYMBOLS}
    seen = set()
    for original in events:
        symbol = original['symbol']
        actual = original['event_us']
        require(type(actual) is int and symbol in by_symbol, 'Funding event identity/clock')
        slot = start + ((actual - start) // step) * step
        require(start <= slot < end and 0 <= actual - slot <= 1_000_000,
                'Funding slot mapping outside preserved one-second tolerance')
        require((symbol, slot) not in seen, 'Duplicate funding slot')
        require(original['reported_interval_hours'] == 8
                and np.isfinite(original['raw_rate']), 'Funding fraction/interval')
        seen.add((symbol, slot))
        by_symbol[symbol].append({**original, 'scheduled_slot_us': slot})
    require(len(seen) == len(SYMBOLS) * len(slots)
            and all((s, t) in seen for s in SYMBOLS for t in slots),
            'Incomplete full-calendar funding source')
    for rows in by_symbol.values():
        rows.sort(key=lambda event: event['event_us'])
    return by_symbol


def funding_events_between(events, entry_us, exit_us):
    require(all(event['event_us'] not in (entry_us, exit_us) for event in events),
            'Funding/fill timestamp collision is not resolved by this attribution')
    return [e for e in events if entry_us < e['event_us'] < exit_us]


def long_funding(symbol, entry_us, exit_us, entry_open, events, marks, times):
    rows = []
    quantity = 1. / entry_open
    for event in funding_events_between(events, entry_us, exit_us):
        # The fixed conservative proxy is inherited from settlement-window V2.
        mark_open = event['scheduled_slot_us'] - 2 * MINUTE
        raw_close = mark_open + MINUTE - 1_000
        available = mark_open + MINUTE
        require(raw_close < event['event_us'] and available < event['event_us'],
                'Strictly-past completed mark requirement')
        index = int(np.searchsorted(times, mark_open))
        require(index < len(times) and times[index] == mark_open, 'Missing fixed mark proxy')
        mark = float(marks[index])
        cash = -quantity * mark * event['raw_rate']
        rows.append({
            'symbol': symbol, 'scheduled_slot_us': event['scheduled_slot_us'],
            'actual_event_us': event['event_us'], 'mark_bar_open_us': mark_open,
            'mark_raw_close_us': raw_close, 'mark_logical_available_us': available,
            'mark_close_proxy': mark, 'rate_fraction': event['raw_rate'],
            'quantity_per_reference_USDT': quantity, 'long_funding_per_reference_USDT': cash,
        })
    return float(sum(r['long_funding_per_reference_USDT'] for r in rows)), rows


def mean_components(rows, primary=True):
    prefix = 'primary_' if primary else ''
    return {key: (float(np.mean([r[prefix + key] for r in rows])) * 10_000
                  if rows else None) for key in METRICS}


def bootstrap(rows, draws=2000, seed=20261021):
    """Joint weekly observations, circular two-week blocks, no tuning."""
    require(bool(rows), 'No complete weekly observations')
    keys = ['primary_' + key for key in METRICS]
    values = np.array([[row[key] for key in keys] for row in rows])
    n = len(rows)
    rng = np.random.default_rng(seed)
    means = np.empty((draws, len(keys)))
    for b in range(draws):
        indices = ((rng.integers(0, n, size=(n + 1) // 2)[:, None]
                    + np.arange(2)) % n).ravel()[:n]
        means[b] = values[indices].mean(axis=0)
    intervals = np.percentile(means * 10_000, [2.5, 97.5], axis=0)
    return {key: intervals[:, j].tolist() for j, key in enumerate(keys)}


def load_sources(source, restore, spec):
    """Verify whole source identities before reading only required raw arrays."""
    source = Path(source)
    for name, record in spec['restore_pins'].items():
        pin(Path(restore) / name, record)
    pin(source / 'SOURCE_INDEX.json', spec['source_index'])
    require((source / 'SOURCE_INDEX.json').read_bytes()
            == (Path(restore) / 'closure/SOURCE_INDEX.json').read_bytes(),
            'Reconstructed/original source index mismatch')
    index = json.loads((source / 'SOURCE_INDEX.json').read_text())
    require(index['calendar'] == [START, END] and index['symbol_order'] == list(SYMBOLS),
            'Source calendar/symbol order mismatch')
    source_pins = {'SOURCE_INDEX.json': spec['source_index']}
    for name, record in index['files'].items():
        pin(source / name, record)
        source_pins[name] = record
    chunks = []
    for record in index['months']:
        path = source / 'months' / (record['month'] + '.npz')
        record_pin = {'bytes': record['source_NPZ_bytes'], 'SHA256': record['source_NPZ_SHA256']}
        pin(path, record_pin)
        source_pins['months/' + path.name] = record_pin
        with np.load(path, allow_pickle=False) as z:
            chunks.append({key: z[key].copy() for key in ['times']
                           + [s + suffix for s in SYMBOLS for suffix in ('_open', '_close', '_mark')]})
    times = np.concatenate([chunk['times'] for chunk in chunks])
    require(np.array_equal(times, np.arange(START, END, MINUTE, dtype=np.int64)),
            'Incomplete, duplicate or nonmonotone full-year minute grid')
    data = {key: np.concatenate([chunk[key] for chunk in chunks])
            for key in chunks[0] if key != 'times'}
    require(all(np.isfinite(a).all() and (a > 0).all() for a in data.values()),
            'Missing/nonpositive raw trade or mark price: STOP, no week deletion')
    with np.load(Path(restore) / 'daily/INPUTS.npz', allow_pickle=False) as cube:
        # Do not access labels, rewards, targets, old NAV or other cube arrays.
        available = cube['close_available_us'].copy()
        close = cube['close'].copy()
    validate_daily(close, available)
    daily = json.loads((source / 'DAILY.json').read_text())
    seen = set()
    for row in daily:
        key = (row['symbol'], row['close_us'])
        require(key not in seen and row['symbol'] in SYMBOLS, 'DAILY duplicate/identity')
        seen.add(key)
        i = int(np.searchsorted(available, row['close_us']))
        require(i < len(available) and available[i] == row['close_us'], 'DAILY cube clock mismatch')
        j = SYMBOLS.index(row['symbol'])
        require(np.isclose(row['close'], close[i, j], rtol=1e-12, atol=0),
                'DAILY/cube close mismatch')
    require(seen == {(s, t) for s in SYMBOLS for t in range(START, END, DAY)},
            'Incomplete DAILY source')
    for s in SYMBOLS:
        for t in range(START + DAY, END + 1, DAY):
            i = int(np.searchsorted(available, t))
            require(i < len(available) and available[i] == t, 'Missing completed daily close')
            actual = data[s + '_close'][(t - START) // MINUTE - 1]
            require(np.isclose(actual, close[i, SYMBOLS.index(s)], rtol=1e-12, atol=0),
                    'Actual completed minute close/daily cube mismatch')
    events = prepare_events(json.loads((source / 'EVENTS.json').read_text()))
    return times, data, close, available, events, source_pins


def run(source, restore, output, spec, here):
    require(not output.exists(), 'Fresh output directory required')
    times, data, close, available, events, source_pins = load_sources(source, restore, spec)
    ranker = load_original_ranker(restore / 'closure/source')
    schedule, forced, eligibility = replacement_schedule(close, available, ranker)
    require(len(schedule) == 52, 'Original all-2023 Monday schedule must contain 52 dates')
    for row in schedule:
        row['status'], row['reasons'] = classify_week(row, eligibility, forced)
    boundary = [r for r in schedule if r['status'] == 'BOUNDARY_EXCLUDED']
    require(len(boundary) == 1 and boundary[0]['rank_us'] == END - WEEK,
            'Unexpected source-boundary interval exclusions')
    blocked = [r for r in schedule if r['status'] == 'NOT_ESTIMABLE_FORCED_ELIGIBILITY']
    output.mkdir()
    write_json(output / 'SCHEDULE.json', {'scheduled_weeks': schedule,
               'all_daily_forced_eligibility_clears': forced, 'boundary_exclusions': boundary})
    if blocked:
        write_json(output / 'STOP.json', {
            'status': 'NOT_ESTIMABLE_FORCED_ELIGIBILITY_NO_OUTCOMES_COMPUTED',
            'affected_weeks': blocked, 'reason': 'No frozen priced forced-exit counterfactual',
            'spec_SHA256': sha(here / 'SPEC.json'), 'source_pins': source_pins,
        })
        raise ValueError('Forced eligibility affects comparison; audit saved, economics not computed')
    weeks, funding_audit = [], []
    for scheduled in schedule:
        if scheduled['status'] == 'BOUNDARY_EXCLUDED':
            continue
        members = {}
        for role in ('outgoing', 'incoming'):
            members[role] = []
            for s in scheduled[role]:
                i0 = int(np.searchsorted(times, scheduled['entry_us']))
                i1 = int(np.searchsorted(times, scheduled['exit_us']))
                require(times[i0] == scheduled['entry_us'] and times[i1] == scheduled['exit_us'],
                        'Actual trade OPEN endpoint unavailable')
                entry, exit = float(data[s + '_open'][i0]), float(data[s + '_open'][i1])
                funding, audit = long_funding(s, scheduled['entry_us'], scheduled['exit_us'],
                                              entry, events[s], data[s + '_mark'], times)
                for event in audit:
                    funding_audit.append({'rank_us': scheduled['rank_us'], 'role': role, **event})
                members[role].append({'symbol': s, **member_costs(entry, exit, funding)})
        calculation = compare_baskets(members['outgoing'], members['incoming'])
        weeks.append({'rank_us': scheduled['rank_us'], 'entry_us': scheduled['entry_us'],
                      'exit_us': scheduled['exit_us'], 'status': scheduled['status'],
                      'month': str(np.datetime64(scheduled['rank_us'] // 1_000_000, 's'))[:7],
                      **calculation, 'members': members})
    require(len(weeks) == 51, 'Complete-week denominator must retain all 51 original intervals')
    changed = [row for row in weeks if row['m']]
    result = {
        'status': 'COMPLETE_CONDITIONAL_ORIGINAL_2023_WEEKLY_REPLACEMENT_ATTRIBUTION_NOT_WALLET',
        'scheduled_weeks': len(schedule), 'complete_weeks': len(weeks),
        'changed_complete_weeks': len(changed), 'unchanged_complete_weeks': len(weeks) - len(changed),
        'boundary_exclusions': boundary, 'forced_eligibility_audit': forced,
        'primary_all_complete_week_slotweighted_mean_bps': mean_components(weeks),
        'secondary_all_complete_week_changedset_mean_bps': mean_components(weeks, primary=False),
        'conditional_changed_week_changedset_mean_bps': mean_components(changed, primary=False),
        'joint_circular_two_week_bootstrap_interval_bps': bootstrap(weeks),
        'by_rank_month_all_complete_week_slotweighted_mean_bps': {
            month: {'complete_weeks': sum(r['month'] == month for r in weeks),
                    'mean_bps': mean_components([r for r in weeks if r['month'] == month])}
            for month in [f'2023-{m:02d}' for m in range(1, 13)]},
        'spec_SHA256': sha(here / 'SPEC.json'), 'code_SHA256': sha(here / 'analyze.py'),
        'freeze_SHA256': sha(here / 'FREEZE.json'), 'source_pins': source_pins,
        'restore_pins': spec['restore_pins'], 'source_recovery_commit': spec['source_recovery_commit'],
        'uncertainty': spec['uncertainty'], 'limitations': spec['limitations'],
        'provider_downloads': 0, 'wallet_advances': 0, 'fits': 0,
        'funding_event_membership': 'actual event timestamp strictly after entry and before exit',
        'funding_mark': spec['funding']['mark_proxy'],
    }
    write_json(output / 'RESULT.json', result)
    write_json(output / 'WEEKS.json', weeks)
    flat = [{k: v for k, v in row.items() if k != 'members'} for row in weeks]
    with (output / 'WEEKS.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(flat[0]))
        writer.writeheader()
        writer.writerows(flat)
    # Empty funding audit is possible in synthetic/CASH-only scenarios; schema is fixed.
    fields = ['rank_us', 'role', 'symbol', 'scheduled_slot_us', 'actual_event_us',
              'mark_bar_open_us', 'mark_raw_close_us', 'mark_logical_available_us',
              'mark_close_proxy', 'rate_fraction', 'quantity_per_reference_USDT',
              'long_funding_per_reference_USDT']
    with (output / 'FUNDING.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(funding_audit)
    print(json.dumps({'status': result['status'], 'complete_weeks': len(weeks),
                      'primary': result['primary_all_complete_week_slotweighted_mean_bps']}, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--restore', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute-frozen-spec', required=True,
                        help='Explicit SPEC.json SHA256. Preparation alone does not authorize a run.')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    require(args.execute_frozen_spec == sha(here / 'SPEC.json'), 'Frozen-spec hash acknowledgment')
    freeze = json.loads((here / 'FREEZE.json').read_text())
    require(freeze['status'] == 'SOURCE_ONLY_FROZEN_REAL_ANALYSIS_NOT_RUN', 'Freeze status')
    for name, record in freeze['files'].items():
        pin(here / name, record)
    spec = json.loads((here / 'SPEC.json').read_text())
    require(spec['schema'] == 'FIXED_WEEKLY_REPLACEMENT_ATTRIBUTION_V1', 'Unsupported spec')
    require(spec['fee_bps_each_fill'] == FEE * 10_000
            and spec['execution_bps_each_fill'] == EXECUTION * 10_000, 'Frozen cost constants')
    run(args.source.resolve(), args.restore.resolve(), args.output.resolve(), spec, here)


if __name__ == '__main__':
    main()
