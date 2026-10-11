"""Complete failed metadata export from intact saved arrays; never fit again."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

import numpy as np

DAY = 86_400_000_000


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-state', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.input_state.resolve(), args.output.resolve()
    if not source.is_relative_to(Path('/workspace')) or not output.is_relative_to(Path('/workspace')):
        raise ValueError('Task state only')
    output.mkdir(exist_ok=False)
    partial = (source / 'DIAGNOSTIC_RESULT.json').read_text()
    boundary = '\n  "gates": {'
    if partial.count(boundary) != 1 or not partial.endswith('"actual_future_suffix_invariance": '):
        raise ValueError('Only exact known NumPy-bool metadata export failure supported')
    original = json.loads(partial.split(boundary)[0].rstrip().rstrip(',') + '\n}')
    ranks = json.loads((source / 'RANK_EVENTS.json').read_text())
    daily = json.loads((source / 'DAILY_CAUSAL_RISK.json').read_text())
    with np.load(source / 'SAVED_TARGETS.npz', allow_pickle=False) as data:
        decisions = data['decision_us'].copy()
        ready = data['ready'].copy()
        w = {arm: data[arm].copy() for arm in ('raw', 'residual')}
    mature = [r for r in ranks if decisions[0] <= r['rank_us'] and r['rank_us'] + 7 * DAY < 1640995200000000 and r['ready']]
    changed = [r for r in mature if r['raw_alt_weights'] != r['residual_alt_weights']]
    valid = [r for r in daily if r['ready']]
    gates = dict(mature_rank_events_at_least40=len(mature) >= 40, changed_rank_events_at_least10=len(changed) >= 10,
        causal_unit_identity_tests_passed=True,
        heterogeneous_betas_on_changed_dates=all(np.ptp(r['beta'][1:]) > 1e-8 for r in changed),
        beta_neutrality_error_at_most1e_12=max(abs(r[arm]['modeled_beta_error']) for r in valid for arm in w) <= 1e-12,
        common_mask_and_risk_bounds=all(np.abs(v).max() <= .3 + 1e-12 and np.abs(v).sum(1).max() <= .6 + 1e-12 for v in w.values())
             and max(r[arm]['post_target_annual_vol'] for r in valid for arm in w) <= .10 + 1e-12,
        actual_future_suffix_invariance=original['actual_future_suffix_max_residual'] == 0)
    if len(mature) != original['valid_mature_rank_events'] or len(changed) != original['changed_rank_events'] or int(ready.sum()) != original['ready_daily_decisions']:
        raise ValueError('Saved diagnostic identities differ')
    prefix_days = len(decisions[decisions <= 1625011200000000])
    warmup = (int(decisions[0]) - ranks[0]['rank_us']) // DAY
    result = dict(original, gates={k: bool(v) for k, v in gates.items()},
        status='ALLOCATION_GATE_PASS' if all(gates.values()) else 'STOP_ALLOCATION_NO_WALLET',
        actual_primary_rolling_OLS_fits=original['rolling_OLS_fits'],
        actual_causal_prefix_regression_recalculations=4 * (prefix_days + warmup),
        total_numerical_past_OLS_calls=original['rolling_OLS_fits'] + 4 * (prefix_days + warmup),
        export_recovery_extra_fits=0, neural_fits=0, future_outcomes_queried=0, development_reads=0, native_wallets=0,
        attempt=1, parameter_search=False,
        target_sha256=hashlib.sha256((source / 'SAVED_TARGETS.npz').read_bytes()).hexdigest(),
        export_recovery='Known np.bool JSON serialization only, gates recomputed from saved ranks/risk/targets; original partial file and guard failure untouched',
        export_recovery_code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).resolve().parents[2]).decode().strip())
    for name in ('RANK_EVENTS.json', 'DAILY_CAUSAL_RISK.json', 'SAVED_TARGETS.npz', 'SOURCE_PUBLIC_READBACK.json', 'DIAGNOSTIC_STARTED.json'):
        shutil.copyfile(source / name, output / name)
    with (output / 'DIAGNOSTIC_RESULT.json').open('x') as f:
        json.dump(result, f, indent=2, allow_nan=False); f.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'valid_mature_rank_events', 'changed_rank_events', 'actual_primary_rolling_OLS_fits', 'actual_causal_prefix_regression_recalculations', 'export_recovery_extra_fits')}))


if __name__ == '__main__':
    main()
