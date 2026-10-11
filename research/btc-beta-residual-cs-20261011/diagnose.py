"""Price-only2021 causal allocation diagnostic; no outcome/wallet queries."""
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import subprocess
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from signals import paired_targets, SYMBOLS, DAY

HERE = Path(__file__).resolve().parent
DATA_COMMIT = 'e0d3400b23842f11f167a63e7d80856d76501de8'
DATA_DIR = 'research/temporal-feature-data-20261009/'
ARCHIVE_SHA = 'bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30'


def stamp(day):
    return int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp() * 1_000_000)


def save(path, data):
    with path.open('x') as f:
        json.dump(data, f, indent=2, allow_nan=False); f.write('\n')


def prices(root, archive_path=None):
    if archive_path:
        raw = archive_path.read_bytes()
    else:
        index = json.loads(subprocess.check_output(['git', 'show', DATA_COMMIT + ':' + DATA_DIR + 'INDEX.json'], cwd=root))
        parts = [subprocess.check_output(['git', 'show', DATA_COMMIT + ':' + DATA_DIR + part['file']], cwd=root) for part in index['parts']]
        if any(hashlib.sha256(b).hexdigest() != p['SHA256'] or len(b) != p['bytes'] for b, p in zip(parts, index['parts'])):
            raise ValueError('Source part differs')
        raw = b''.join(parts)
    if hashlib.sha256(raw).hexdigest() != ARCHIVE_SHA:
        raise ValueError('Source archive differs')
    clocks = np.arange(stamp('2020-01-02'), stamp('2022-01-01'), DAY, dtype=np.int64)
    close = np.full((len(clocks), 5), np.nan)
    source = []
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        members = json.loads(z.read('MEMBERS.json'))['files']
        for i, symbol in enumerate(SYMBOLS):
            name = 'source_tables_not_model_inputs/daily_features/' + symbol + '.parquet'
            member = z.read(name)
            if hashlib.sha256(member).hexdigest() != members[name]['SHA256']:
                raise ValueError('Source price member differs')
            dtype = pq.read_schema(io.BytesIO(member)).field('dt').type
            tab = pq.read_table(io.BytesIO(member), columns=['dt', 'close', 'complete_kline'], filters=[
                ('dt', '>=', pa.scalar(datetime(2020, 1, 1, tzinfo=timezone.utc), type=dtype)),
                ('dt', '<', pa.scalar(datetime(2021, 12, 31, tzinfo=timezone.utc), type=dtype))])
            available = tab['dt'].to_numpy().astype('datetime64[us]').astype(np.int64) + DAY
            values = tab['close'].to_numpy()
            valid = np.asarray(tab['complete_kline'].to_pylist(), dtype=bool)
            if len(np.unique(available)) != len(available) or np.any(available >= stamp('2022-01-01')):
                raise ValueError('Unique2021 price cutoff required')
            close[(available - clocks[0]) // DAY, i] = np.where(valid, values, np.nan)
            source.append(dict(symbol=symbol, projected_rows=len(available), latest_available_us=int(available.max())))
    return clocks, close, source


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--archive', type=Path)
    parser.add_argument('--source-commit', required=True)
    parser.add_argument('--test-report', type=Path, required=True)
    args = parser.parse_args()
    state = args.state.resolve()
    if not state.is_relative_to(Path('/workspace')):
        raise ValueError('Task state must be under /workspace')
    state.mkdir(parents=True, exist_ok=True)
    root = HERE.parents[1]
    git = lambda *cmd: subprocess.check_output(['git', *cmd], cwd=root)
    if git('rev-parse', 'HEAD').decode().strip() != args.source_commit or git('status', '--porcelain').strip():
        raise ValueError('Clean exact published source required')
    suites = list(ET.parse(args.test_report).getroot().iter('testsuite'))
    if sum(int(s.get('tests', 0)) for s in suites) < 8 or any(int(s.get('failures', 0)) + int(s.get('errors', 0)) for s in suites):
        raise ValueError('All required causal/identity/math tests must pass')
    save(state / 'DIAGNOSTIC_STARTED.json', dict(source_commit=args.source_commit, attempt=1, future_outcome_queries=0, wallets=0))
    t, close, sources = prices(root, args.archive)
    decisions = np.arange(stamp('2021-01-01'), stamp('2022-01-01'), DAY, dtype=np.int64)
    data = paired_targets(close, t, decisions)
    mature = [r for r in data['rank_events'] if decisions[0] <= r['rank_us'] and r['rank_us'] + 7 * DAY < stamp('2022-01-01') and r['ready']]
    changed = [r for r in mature if r['raw_alt_weights'] != r['residual_alt_weights']]
    heterogeneous = all(np.ptp(np.asarray(r['beta'])[1:]) > 1e-8 for r in changed)
    daily = [r for r in data['daily_checks'] if r['ready']]
    error = max(abs(r[arm]['modeled_beta_error']) for r in daily for arm in ('raw', 'residual'))
    cov = max(r[arm]['post_target_annual_vol'] for r in daily for arm in ('raw', 'residual'))
    gates = dict(mature_rank_events_at_least40=len(mature) >= 40, changed_rank_events_at_least10=len(changed) >= 10,
                 causal_unit_identity_tests_passed=True,
                 heterogeneous_betas_on_changed_dates=heterogeneous, beta_neutrality_error_at_most1e_12=error <= 1e-12,
                 common_mask_and_risk_bounds=cov <= .10 + 1e-12 and all(np.abs(v).max() <= .3 + 1e-12 and np.abs(v).sum(1).max() <= .6 + 1e-12 for v in data['weights'].values()))
    # Actual future-input suffix perturbation, with no future outcomes loaded.
    cutoff = stamp('2021-06-30')
    mutated = close.copy(); mutated[t > cutoff] *= np.linspace(1.01, 2., int((t > cutoff).sum()))[:, None]
    alternative = paired_targets(mutated, t, decisions[decisions <= cutoff])
    prefix = decisions <= cutoff
    residual = max(np.max(np.abs(data['weights'][arm][prefix] - alternative['weights'][arm])) for arm in ('raw', 'residual'))
    gates['actual_future_suffix_invariance'] = residual == 0
    save(state / 'RANK_EVENTS.json', data['rank_events'])
    save(state / 'DAILY_CAUSAL_RISK.json', data['daily_checks'])
    with (state / 'SAVED_TARGETS.npz').open('xb') as f:
        np.savez_compressed(f, decision_us=data['decision_us'], symbol_order=data['symbol_order'], beta=data['beta'], alpha=data['alpha'], ready=data['ready'], raw=data['weights']['raw'], residual=data['weights']['residual'])
    result = dict(status='ALLOCATION_GATE_PASS' if all(gates.values()) else 'STOP_ALLOCATION_NO_WALLET',
        source_commit=args.source_commit, protocol_sha256=hashlib.sha256((HERE / 'PROTOCOL.json').read_bytes()).hexdigest(),
        sources=sources, ready_daily_decisions=int(data['ready'].sum()), total_daily_decisions=len(decisions),
        rolling_OLS_fits=data['rolling_OLS_fits'], neural_fits=0, source_daily_observations_per_regression=84,
        valid_mature_rank_events=len(mature), changed_rank_events=len(changed), allocation_change_fraction=len(changed) / len(mature),
        maximum_modeled_beta_error=error, maximum_target_covariance_annual_vol=cov,
        actual_future_suffix_max_residual=float(residual), gates=gates,
        future_outcomes_queried=0, development_reads=0, native_wallets=0,
        attempt=1, parameter_search=False, source_archive_sha256=ARCHIVE_SHA,
        target_sha256=hashlib.sha256((state / 'SAVED_TARGETS.npz').read_bytes()).hexdigest(),
        interpretation='Causal allocation difference only; no predictive/economic advantage established')
    save(state / 'DIAGNOSTIC_RESULT.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'rolling_OLS_fits', 'valid_mature_rank_events', 'changed_rank_events', 'maximum_modeled_beta_error', 'actual_future_suffix_max_residual')}), flush=True)


if __name__ == '__main__':
    main()
