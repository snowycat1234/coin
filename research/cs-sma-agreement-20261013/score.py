"""Frozen five-arm research scorer. Actual scoring requires verified publication.

The economic kernel and reference are imported unchanged. Decimal independently
checks the ORIGINAL saved binary-float quantities, not a re-sized Decimal policy.
This is a daily hypothetical-filled proxy, not live APR or native-wallet evidence.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, localcontext
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import sys
import zipfile

# This fixed daily-proxy experiment has a single-process, threads1 budget.
for _variable in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
                  'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
    os.environ[_variable] = '1'
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RECOVERY = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REFERENCE_PATH = ROOT / 'research/settled-funding-direction-20261012/core.py'
_spec = importlib.util.spec_from_file_location('cs_sma_unchanged_reference', REFERENCE_PATH)
_reference = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_reference)
reference = _reference.reference
DAY = _reference.DAY
SYMBOLS = _reference.SYMBOLS
ARMS = ('CS', 'SMA200', 'STATIC50', 'AGREEMENT', 'AGREEMENT_NO_REALLOCATION')
CONTROLS = ('CS', 'SMA200', 'STATIC50')
YEARS = (2023, 2025)
SEEDS = {2023: 811760, 2025: 811761}
COST = .00135
CAPITAL = 10000.
PROTOCOL_SHA256 = 'bb37fd619777bd69e043eddfe3ade6c564e00ebe0eef0257181b68d25fe7f47c'
DECIMAL_USDT_TOLERANCE = '0.00000001'
SOURCE_HASHES = {
    'research/settled-funding-direction-20261012/core.py': 'e536049425dd404fac155d9fc757e5ee82199d88e3733ca49216c40a29253245',
    'modules/collector_research/pipeline/economics.py': '637441050d0d42bc1a579510272b3fa5f456620dbfb8b45932cc37e894e34a3e',
    'research/portfolio-risk-budget-20261012/risk_budget.py': '69de58ac83536dfbf1ec3715aadfa65da741c970c4cb5b417bb4c1e8062b19a6',
}
INPUT_HASHES = {
    2023: '1c500e9d5b0244a1daaabc597d7cc5ae97a21a156cc42d8a44a1504b821e599f',
    2025: '88a698ceed87603a36ca2bcf4ae76d805aa90085b344bbeee47e58a8c9770add',
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text())


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def save_npz(path, **arrays):
    """Byte-reproducible NPZ: fixed ZIP dates, ordered keys, no object arrays."""
    with zipfile.ZipFile(path, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for key in sorted(arrays):
            array = np.asarray(arrays[key])
            if array.dtype.hasobject:
                raise ValueError('Object arrays are prohibited')
            buffer = io.BytesIO()
            np.lib.format.write_array(buffer, array, allow_pickle=False)
            info = zipfile.ZipInfo(key + '.npy', date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, buffer.getvalue())


def _decimal(value):
    """Exact value of the saved binary float, avoiding string-rounding changes."""
    value = float(value)
    if not np.isfinite(value):
        raise ValueError('Decimal audit requires finite touched quantities/prices')
    return Decimal.from_float(value)


def decimal_audit(decisions, weights, p0, p1, funding_per_unit, summary, rows):
    """Independent inventory, signed funding, cost, terminal and NAV audit.

    The reference folds terminal fees into the final day's trading_cost_proxy
    but excludes terminal turnover from turnover_USDT. Both are reconciled,
    and terminal notional is reported separately without altering that trace.
    """
    if not summary['hypothetical_cost_terminal'] or len(rows) != len(decisions):
        return dict(status='NOT_AUDITABLE_INCOMPLETE_REFERENCE', passed=False)
    maxima = {key: Decimal(0) for key in (
        'target_quantity_notional', 'price_pnl', 'funding_debit', 'turnover',
        'trading_cost', 'nav_before', 'nav_after', 'terminal_cost', 'net',
        'summary_price_pnl', 'summary_trading_cost', 'summary_funding_cash')}
    errors = []
    max_daily_return_error = Decimal(0)
    with localcontext() as context:
        context.prec = 60
        tolerance = Decimal(DECIMAL_USDT_TOLERANCE)
        nav = _decimal(CAPITAL)
        previous_q = [Decimal(0)] * len(SYMBOLS)
        totals = dict(price_pnl=Decimal(0), trading_cost=Decimal(0),
                      funding_debit=Decimal(0), rebalance_turnover=Decimal(0))
        terminal_notional = Decimal(0)
        terminal_fee = Decimal(0)
        fee_rate = _decimal(COST)

        def compare(key, actual, expected, day=None):
            delta = abs(_decimal(actual) - expected)
            maxima[key] = max(maxima[key], delta)
            if delta > tolerance:
                errors.append(dict(field=key, day=day, absolute_error_USDT=str(delta)))

        for i, row in enumerate(rows):
            if int(row['decision_us']) != int(decisions[i]):
                raise ValueError('Saved quantity trace calendar differs from frozen targets')
            q = [_decimal(value) for value in row['held_quantity']]
            if len(q) != len(SYMBOLS):
                raise ValueError('Saved quantity trace CORE5 mismatch')
            compare('nav_before', row['nav_before'], nav, i)
            turnover = Decimal(0)
            pnl = Decimal(0)
            funding = Decimal(0)
            for j, (held, previous) in enumerate(zip(q, previous_q)):
                holding = abs(float(weights[i, j])) > 1e-15
                touching = abs(float(previous)) > 1e-15 or holding
                if holding:
                    start, end, fp = map(_decimal, (p0[i, j], p1[i, j], funding_per_unit[i, j]))
                    intended = _decimal(row['nav_before']) * _decimal(weights[i, j]) / start
                    quantity_notional_error = abs((held - intended) * start)
                    maxima['target_quantity_notional'] = max(maxima['target_quantity_notional'], quantity_notional_error)
                    if quantity_notional_error > tolerance:
                        errors.append(dict(field='target_quantity_notional', day=i, asset=j,
                                           absolute_error_USDT=str(quantity_notional_error)))
                    pnl += held * (end - start)
                    funding += held * fp
                elif held != 0:
                    errors.append(dict(field='quantity_on_cash_target', day=i, asset=j))
                if touching:
                    turnover += abs(held - previous) * _decimal(p0[i, j])
            fee = turnover * fee_rate
            if i == len(rows) - 1:
                terminal_notional = sum((abs(held) * _decimal(p1[i, j])
                                         for j, held in enumerate(q) if held != 0), Decimal(0))
                terminal_fee = terminal_notional * fee_rate
                fee += terminal_fee
            compare('price_pnl', row['price_pnl'], pnl, i)
            compare('funding_debit', row['funding_debit_proxy'], funding, i)
            compare('turnover', row['turnover_USDT'], turnover, i)
            compare('trading_cost', row['trading_cost_proxy'], fee, i)
            previous_nav = nav
            nav += pnl - fee - funding
            compare('nav_after', row['nav_after'], nav, i)
            daily_return_error = abs(_decimal(row['daily_return']) - (nav / previous_nav - 1))
            max_daily_return_error = max(max_daily_return_error, daily_return_error)
            if daily_return_error > Decimal('0.00000000000001'):
                errors.append(dict(field='daily_return', day=i, absolute_error=str(daily_return_error)))
            totals['price_pnl'] += pnl
            totals['trading_cost'] += fee
            totals['funding_debit'] += funding
            totals['rebalance_turnover'] += turnover
            previous_q = q
        compare('terminal_cost', summary['terminal_cost_proxy_USDT'], terminal_fee)
        compare('net', summary['net_USDT'], nav - _decimal(CAPITAL))
        compare('summary_price_pnl', summary['price_pnl'], totals['price_pnl'])
        compare('summary_trading_cost', summary['trading_cost'], totals['trading_cost'])
        compare('summary_funding_cash', summary['funding_cash'], -totals['funding_debit'])
        if any(float(value) != 0 for value in summary['positions']):
            errors.append(dict(field='nonzero_final_positions'))
        return dict(status='PASS' if not errors else 'FAIL', passed=not errors,
                    method='Decimal.from_float original saved quantity rows; precision60',
                    absolute_tolerance_USDT=DECIMAL_USDT_TOLERANCE,
                    max_absolute_errors_USDT={key: str(value) for key, value in maxima.items()},
                    max_absolute_daily_return_error=str(max_daily_return_error),
                    decimal_final_NAV=str(nav), decimal_net_USDT=str(nav - _decimal(CAPITAL)),
                    decimal_price_pnl_USDT=str(totals['price_pnl']),
                    decimal_trading_cost_USDT=str(totals['trading_cost']),
                    decimal_funding_cash_USDT=str(-totals['funding_debit']),
                    decimal_rebalance_turnover_USDT=str(totals['rebalance_turnover']),
                    decimal_terminal_turnover_USDT=str(terminal_notional),
                    decimal_total_turnover_USDT=str(totals['rebalance_turnover'] + terminal_notional),
                    decimal_terminal_cost_USDT=str(terminal_fee), errors=errors)


def bootstrap_indices(length, seed, draws=1000, block_days=14):
    if length < 1 or draws != 1000 or block_days != 14:
        raise ValueError('Frozen 1000 draws and 14-calendar-day circular blocks required')
    rng = np.random.default_rng(seed)
    indices = np.empty((draws, length), dtype=np.int64)
    for draw in range(draws):
        starts = rng.integers(0, length, int(np.ceil(length / block_days)))
        indices[draw] = ((starts[:, None] + np.arange(block_days)) % length).ravel()[:length]
    return indices


def paired_inference(daily_returns, indices):
    """All arms and all controls share every saved paired-date resample."""
    values = np.column_stack([daily_returns[arm] for arm in ARMS])
    indices = np.asarray(indices, dtype=np.int64)
    if indices.shape != (1000, len(values)) or np.any(indices < 0) or np.any(indices >= len(values)):
        raise ValueError('Saved bootstrap indices must be 1000 full-calendar draws')
    samples = values[indices].mean(axis=1)
    report = {}
    output = {'indices': indices, 'arm_order': np.asarray(ARMS), 'sample_mean_daily_returns': samples}
    primary = ARMS.index('AGREEMENT')
    for control in CONTROLS:
        delta = daily_returns['AGREEMENT'] - daily_returns[control]
        paired_samples = delta[indices].mean(axis=1)
        output['sample_mean_AGREEMENT_minus_' + control] = paired_samples
        low, high = np.quantile(paired_samples, [.025, .975])
        report[control] = dict(mean_daily_return_increment=float(delta.mean()),
                               paired_mean_daily_return_95pct_CI=[float(low), float(high)],
                               CI_lower_positive=bool(low > 0))
        if not np.allclose(paired_samples, samples[:, primary] - samples[:, ARMS.index(control)], rtol=0, atol=1e-16):
            raise ValueError('Paired resampling internal inconsistency')
    return report, output


def exposure_summary(weights, proof, arm):
    weights = np.asarray(weights, dtype=float)
    diagnostics = [row['arms'][arm] for row in proof]
    post_sigma = np.array([row['post_sigma'] for row in diagnostics], dtype=float)
    shortfall = np.array([row['shortfall'] for row in diagnostics], dtype=float)
    gross = np.abs(weights).sum(axis=1)
    long = np.maximum(weights, 0).sum(axis=1)
    short = -np.minimum(weights, 0).sum(axis=1)
    factors = [float(row['factor']) for row in diagnostics if row.get('factor') is not None]
    return dict(days=len(weights), cash_days=int(np.count_nonzero(gross == 0)),
                mean_gross=float(gross.mean()), max_gross=float(gross.max()),
                mean_long=float(long.mean()), mean_short=float(short.mean()),
                mean_net=float(weights.sum(axis=1).mean()),
                max_asset_absolute_weight=float(np.abs(weights).max()),
                mean_nonzero_legs=float(np.count_nonzero(weights, axis=1).mean()),
                asset_cap_days=int(np.count_nonzero(np.max(np.abs(weights), axis=1) >= .30 - 1e-12)),
                gross_cap_days=int(np.count_nonzero(gross >= .60 - 1e-12)),
                cap_bound_days=sum(row.get('cap_bound') is True for row in diagnostics),
                risk_target_met_days=sum(row.get('risk_target_met') is True for row in diagnostics),
                risk_shortfall_days=int(np.count_nonzero(shortfall > 1e-12)),
                mean_risk_shortfall=float(shortfall.mean()), max_risk_shortfall=float(shortfall.max()),
                mean_estimated_annual_risk=float(post_sigma.mean()), max_estimated_annual_risk=float(post_sigma.max()),
                above_nominal_estimated_risk_days=int(np.count_nonzero(post_sigma > .10 + 1e-12)),
                scale_amplification_days=sum(factor > 1 + 1e-12 for factor in factors),
                maximum_scale_factor=max(factors) if factors else None,
                caution='Common nominal risk policy does not imply all-day matched achieved or realized risk; filtered diagnostic can remove hedges.')


def protocol_gates(years, source_pass):
    """Only AGREEMENT is candidate. Diagnostic never enters winner selection."""
    full = all(all(value['metrics']['days'] == 365 and value['metrics']['hypothetical_cost_terminal']
                   and value['decimal_audit']['passed'] for value in year['arms'].values())
               for year in years.values())
    positive = all(year['arms']['AGREEMENT']['metrics']['net_USDT'] is not None
                   and year['arms']['AGREEMENT']['metrics']['net_USDT'] > 0 for year in years.values())
    increments = all(year['arms']['AGREEMENT']['metrics']['net_USDT'] is not None
                     and year['arms'][control]['metrics']['net_USDT'] is not None
                     and year['arms']['AGREEMENT']['metrics']['net_USDT'] > year['arms'][control]['metrics']['net_USDT']
                     for year in years.values() for control in CONTROLS)
    ci = all(year.get('inference') and year['inference'][control]['CI_lower_positive']
             for year in years.values() for control in CONTROLS)
    drawdown = all(year['arms']['AGREEMENT']['metrics']['drawdown'] <= .12 for year in years.values())
    gates = dict(source_identity_and_causal_tests=bool(source_pass),
                 full365_and_paid_proxy_terminal_both_years=bool(full),
                 primary_positive_net_both_years=bool(positive),
                 primary_positive_increment_over_each_CS_SMA_STATIC50_both_years=bool(increments),
                 paired_daily_increment_CI_lower_over_each_control_positive_both_years=bool(ci),
                 primary_MDD_max=bool(drawdown))
    return dict(gates=gates, all_frozen_gates_pass=all(gates.values()), primary='AGREEMENT',
                diagnostic='AGREEMENT_NO_REALLOCATION; exposure diagnostic only; no alternative winner selection')


def _require_publication(record_path):
    record = read_json(record_path)
    if (record.get('repository') != 'snowycat1234/coin'
            or record.get('branch') != 'research/cs-sma-agreement-20261013'
            or record.get('remote_verified') is not True
            or not re.fullmatch(r'[0-9a-f]{40}', record.get('commit_sha', ''))):
        raise ValueError('Actual economics prohibited until exact remote publication is verified')
    required = [HERE / name for name in ('score.py', 'test_accounting.py', 'core.py', 'test_core.py',
                                       'PROTOCOL.json', 'QA.json', 'TARGETS_MANIFEST.json',
                                       'DEDUP_REVIEW.json', 'SOURCE_PROVENANCE.json', 'prepare_targets.py')]
    required += [HERE / 'targets' / f'Y{year}{suffix}' for year in YEARS
                 for suffix in ('.npz', '_PROOF.json')]
    required += [ROOT / relative for relative in SOURCE_HASHES]
    provenance = read_json(HERE / 'SOURCE_PROVENANCE.json')
    required += [ROOT / entry['repository_path'] for entry in provenance['exact_source_files']]
    for entry in provenance['exact_source_files']:
        if sha256(ROOT / entry['repository_path']) != entry['SHA256']:
            raise ValueError('Prepared source provenance mismatch: ' + entry['repository_path'])
    for path in required:
        relative = path.relative_to(ROOT).as_posix()
        if record.get('files', {}).get(relative) != sha256(path):
            raise ValueError('Publication hash missing or mismatched: ' + relative)
    for relative, expected in SOURCE_HASHES.items():
        if sha256(ROOT / relative) != expected:
            raise ValueError('Unchanged economic reference/source identity failed: ' + relative)
    return record


def _load_year(year, manifest):
    entry = manifest['years'][str(year)]
    input_path = ROOT / entry['input_relative_path']
    target_path = HERE / entry['target_relative_path']
    proof_path = HERE / entry['proof_relative_path']
    if sha256(input_path) != INPUT_HASHES[year] or entry['input_SHA256'] != INPUT_HASHES[year]:
        raise ValueError('Original INPUTS_FINAL identity mismatch')
    if sha256(target_path) != entry['target_SHA256'] or sha256(proof_path) != entry['proof_SHA256']:
        raise ValueError('Frozen target/proof manifest mismatch')
    with np.load(input_path, allow_pickle=False) as archive:
        inputs = {key: archive[key] for key in archive.files}
    with np.load(target_path, allow_pickle=False) as archive:
        targets = {key: archive[key] for key in archive.files}
    first = int(datetime(year, 1, 1, tzinfo=timezone.utc).timestamp() * 1_000_000)
    calendar = first + np.arange(365, dtype=np.int64) * DAY
    if not np.array_equal(inputs['decision_us'], calendar) or not np.array_equal(targets['decision_us'], calendar):
        raise ValueError('Both independent wallets require complete Jan1-Dec31 365-day calendars')
    for packet in (inputs, targets):
        if tuple(packet['symbol_order']) != SYMBOLS:
            raise ValueError('CORE5 source ordering mismatch')
    if not np.all(targets['source_status'] == 'READY'):
        raise ValueError('Frozen source admission failed; do not score unknown days')
    for key in ('p0', 'p1', 'funding_per_unit', 'owned_interval_valid'):
        if inputs[key].shape != (365, 5):
            raise ValueError('Owned execution array shape mismatch')
    if (not inputs['owned_interval_valid'].all() or not np.isfinite(inputs['funding_per_unit']).all()
            or not np.isfinite(inputs['p0']).all() or not np.isfinite(inputs['p1']).all()
            or (inputs['p0'] <= 0).any() or (inputs['p1'] <= 0).any()
            or not np.array_equal(inputs['p1'][:-1], inputs['p0'][1:])):
        raise ValueError('Full original owned intervals/terminal boundary required')
    for arm in ARMS:
        weights = targets[arm]
        if (weights.shape != (365, 5) or not np.isfinite(weights).all()
                or np.abs(weights).max() > .3 + 1e-12 or np.abs(weights).sum(axis=1).max() > .6 + 1e-12):
            raise ValueError('Frozen finite/capped arm targets required')
    proof = read_json(proof_path)
    if len(proof) != 365 or any(int(row['decision_us']) != int(calendar[i]) for i, row in enumerate(proof)):
        raise ValueError('Complete target scale diagnostics required')
    return inputs, targets, proof


def run(publication_record, output_dir):
    publication = _require_publication(publication_record)
    protocol = read_json(HERE / 'PROTOCOL.json')
    if sha256(HERE / 'PROTOCOL.json') != PROTOCOL_SHA256:
        raise ValueError('Preregistered protocol bytes changed')
    if tuple(protocol['arms']) != ARMS or tuple(protocol['years']) != YEARS or protocol['capital_per_independent_wallet'] != CAPITAL:
        raise ValueError('Frozen protocol scope changed')
    manifest = read_json(HERE / 'TARGETS_MANIFEST.json')
    qa = read_json(HERE / 'QA.json')
    dedup = read_json(HERE / 'DEDUP_REVIEW.json')
    source_pass = (qa.get('status') == 'PASS_FROZEN_CAUSAL_TARGETS_NO_ECONOMIC_SCORING'
                   and qa.get('economic_runs_started') is False and qa.get('tests_run') == 23
                   and qa.get('failures') == 0 and qa.get('errors') == 0
                   and dedup.get('status') == 'NO_EXACT_DUPLICATE_FOUND_IN_TARGETED_REVIEW'
                   and dedup.get('admit_single_frozen_experiment') is True)
    for relative, entry in manifest['files'].items():
        if sha256(HERE / relative) != entry['SHA256']:
            raise ValueError('Prepared manifest mismatch: ' + relative)
    if not source_pass:
        raise ValueError('Source identity and causal-test preparation not certified')
    # Load/validate BOTH full calendars before the first economic kernel call.
    prepared = {year: _load_year(year, manifest) for year in YEARS}
    output = Path(output_dir)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Refuse to overwrite previous score artifacts')
    output.mkdir(parents=True, exist_ok=True)
    result = dict(experiment=protocol['experiment'], published_commit=publication['commit_sha'],
                  economic_model='UNCHANGED_CONDITIONAL_DAILY_QUANTITY_REFERENCE',
                  runtime=dict(python_version=sys.version.split()[0], numpy_version=np.__version__,
                               numerical_threads=1, processes=1),
                  price_cost_funding_policy='Original p0/p1/funding/mask; cost .00135 each side; paid hypothetical Jan1 terminal',
                  return_measure='Cumulative net return of separate 10000 USDT wallets; not live APR',
                  inference_label='Conditional seen-historical 95% paired daily-return intervals; not research-selection-adjusted',
                  dedup_scope=dedup['scope'],
                  limitations=['No capacity, margin/MMR, liquidation, minQty or fill certification',
                               'Known development years; not pristine OOS or holdout qualification'],
                  protocol_SHA256=sha256(HERE / 'PROTOCOL.json'),
                  publication_record_SHA256=sha256(publication_record),
                  code_target_hashes=publication['files'], input_hashes={str(y): INPUT_HASHES[y] for y in YEARS},
                  bootstrap=dict(block_days=14, draws=1000, seeds={str(k): v for k, v in SEEDS.items()},
                                 shared_indices_across_all_arms=True, outcome='Mean paired paid-terminal daily-return increment'),
                  years={})
    artifacts = {}
    for year in YEARS:
        inputs, targets, proof = prepared[year]
        year_result = dict(arms={}, inference=None)
        daily_returns = {}
        for arm in ARMS:
            metrics, rows = reference(inputs['decision_us'], targets[arm], inputs['p0'], inputs['p1'],
                                      inputs['funding_per_unit'], inputs['owned_interval_valid'])
            trace_path = output / f'Y{year}_{arm}_ROWS.json'
            write_json(trace_path, rows)
            # Read the persisted original floats before independent Decimal audit.
            saved_rows = read_json(trace_path)
            audit = decimal_audit(inputs['decision_us'], targets[arm], inputs['p0'], inputs['p1'],
                                  inputs['funding_per_unit'], metrics, saved_rows)
            metrics['cumulative_net_return'] = metrics['net_USDT'] / CAPITAL if metrics['net_USDT'] is not None else None
            metrics['rebalance_turnover_USDT'] = sum(row['turnover_USDT'] for row in saved_rows)
            metrics['terminal_turnover_USDT'] = metrics['terminal_cost_proxy_USDT'] / COST
            metrics['total_turnover_USDT'] = metrics['rebalance_turnover_USDT'] + metrics['terminal_turnover_USDT']
            year_result['arms'][arm] = dict(metrics=metrics, decimal_audit=audit,
                                            exposure=exposure_summary(targets[arm], proof, arm),
                                            quantity_rows_file=trace_path.name, quantity_rows_SHA256=sha256(trace_path))
            artifacts[trace_path.name] = sha256(trace_path)
            if len(saved_rows) == 365 and metrics['hypothetical_cost_terminal'] and audit['passed']:
                daily_returns[arm] = np.array([row['daily_return'] for row in saved_rows])
        if len(daily_returns) == len(ARMS):
            indices = bootstrap_indices(365, SEEDS[year])
            inference, samples = paired_inference(daily_returns, indices)
            sample_path = output / f'Y{year}_BOOTSTRAP.npz'
            save_npz(sample_path, **samples)
            # Replay from saved samples, not regenerated random state.
            with np.load(sample_path, allow_pickle=False) as archive:
                replayed, _ = paired_inference(daily_returns, archive['indices'])
                if replayed != inference:
                    raise ValueError('Saved bootstrap replay mismatch')
                for key, value in samples.items():
                    if not np.array_equal(value, archive[key]):
                        raise ValueError('Saved bootstrap sample mismatch')
            year_result['inference'] = inference
            year_result['bootstrap_file'] = sample_path.name
            year_result['bootstrap_SHA256'] = sha256(sample_path)
            artifacts[sample_path.name] = sha256(sample_path)
        result['years'][str(year)] = year_result
    result.update(protocol_gates(result['years'], source_pass))
    result_path = output / 'RESULTS.json'
    write_json(result_path, result)
    artifacts[result_path.name] = sha256(result_path)
    write_json(output / 'OUTPUTS_MANIFEST.json', dict(status='SCORED_FROZEN_FIVE_ARMS_TWO_YEARS', files=artifacts,
              protocol_SHA256=result['protocol_SHA256'], published_commit=publication['commit_sha'],
              source_input_target_code_hashes=result['code_target_hashes'], original_input_hashes=result['input_hashes']))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publication-record', type=Path, required=True,
                        help='Parent-created remote-verification record; exact pre-score hashes required')
    parser.add_argument('--output-dir', type=Path, default=HERE / 'results')
    args = parser.parse_args()
    result = run(args.publication_record, args.output_dir)
    print(json.dumps(dict(all_frozen_gates_pass=result['all_frozen_gates_pass'], gates=result['gates']), sort_keys=True))


if __name__ == '__main__':
    main()
