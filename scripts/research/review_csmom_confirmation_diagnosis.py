"""Independent saved-summary reconciliation; no model, market or wallet execution."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time

ROOT = Path(__file__).resolve().parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def near(a, b):
    assert math.isfinite(a) and math.isfinite(b)
    assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-7), (a, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--result', type=Path, default=ROOT/'reports/CSMOM_CONFIRMATION_DIAGNOSIS_20261008.json')
    ap.add_argument('--output', type=Path, default=ROOT/'reports/CSMOM_CONFIRMATION_DIAGNOSIS_REVIEW_20261008.json')
    a = ap.parse_args(); began = time.monotonic()
    r = json.loads(a.result.read_text())
    prior_path = ROOT/'reports/CSMOM_ABSOLUTE_SHORT_20261008.json'
    prior = json.loads(prior_path.read_text())
    assert r['status'] == 'COMPLETE_READ_ONLY_CONFIRMATION_MECHANISM'
    assert r['parent_result_sha256'] == sha(prior_path)
    assert r['inspector_sha256'] == sha(ROOT/'scripts/research/diagnose_csmom_confirmation.py')
    assert (r['new_wallets'], r['new_fits'], r['new_configs']) == (0, 0, 0)
    assert not r['locked_consumed'] and r['qualification'] == 'NONE_CASH'
    key = lambda x: (x['window'], x['funding_scale'])
    original = {key(x): x for x in prior['reused_controls']}
    new = {key(x): x for x in prior['cases']}
    assert set(original) == set(new) == {key(x) for x in r['cases']} and len(r['cases']) == 10
    comparisons = []
    for cell in r['cases']:
        k = key(cell)
        for role, source in (('old', original[k]), ('new', new[k])):
            actual = cell[role]['direction_from_actual_fills']
            categories = cell[role]['order_categories']
            for side in ('LONG', 'SHORT'):
                d = actual[side]; saved = source['contributions'][side]
                for field, name in (('gross', 'gross'), ('fees', 'fees'), ('execution', 'execution_cost'), ('funding', 'funding'), ('net', 'net_contribution')):
                    near(d[field], saved[name])
                near(d['gross'] - d['execution'] - d['fees'] + d['funding'], d['net'])
                legs = [v for label, v in categories.items() if label.startswith(side+'/')]
                for field in ('fees', 'execution'):
                    near(sum(x[field] for x in legs), d[field])
                assert all(x['fill_fragments'] >= x['logical_order_legs'] > 0 for x in legs)
            reopens = cell[role]['same_rank_gate_reopens']
            category = categories.get('SHORT/SAME_RANK_GATE_REOPEN', {})
            assert len(reopens) == category.get('logical_order_legs', 0)
            for field in ('fees', 'execution'):
                near(sum(x[field] for x in reopens), category.get(field, 0))
            assert role == 'new' or not reopens
            for event in reopens:
                assert event['close_signal_us'] < event['reopen_signal_us']
        delta = cell['economic_delta']
        for field, value in (('gross', new[k]['gross_PnL']-original[k]['gross_PnL']), ('funding', new[k]['funding']-original[k]['funding']), ('net', new[k]['net_PnL']-original[k]['net_PnL']), ('cost', new[k]['fees']+new[k]['execution_cost']-original[k]['fees']-original[k]['execution_cost'])):
            near(delta[field], value)
        near(delta['gross'] + delta['funding'] - delta['cost'], delta['net'])
        comparisons.append(dict(window=k[0], funding_scale=k[1], economic_delta=delta,
            same_rank_actual_reopens=len(cell['new']['same_rank_gate_reopens'])))
    targets = r['target_decomposition']
    assert len(targets) == 5 and {x['window'] for x in targets} == {x['id'] for x in prior['protocol']['windows']}
    for t in targets:
        assert 0 < t['confirmed_LONG_weight_days'] <= t['original_LONG_weight_days']
        assert 0 < t['extra_covariance_downscale_days'] <= t['measured_nonterminal_days']
        assert 0 < t['minimum_extra_scale'] < 1
        assert t['max_target_reconstruction_error'] < 1e-12
        assert t['mean_final_sigma'] <= .10 + 1e-12
    out = dict(status='PASS_SAVED_SUMMARY_RECONCILIATION_WITH_LIMITATIONS',
        result_sha256=sha(a.result), source_sha256=sha(__file__), parent_result_sha256=sha(prior_path),
        accounts_reconciled=20, target_summaries_checked=5, paired_comparisons=comparisons,
        new_wallets=0, new_fits=0, elapsed_seconds=time.monotonic()-began,
        qualification='NONE_CASH', limitations=[
            'Independent stdlib reconciliation against prior frozen financial summaries; server fill/target files were not re-executed by this reviewer.',
            'Target covariance and order classification are additionally code-reviewed, not independently reconstructed from raw market data here.',
            'Weight-days and reason-associated cost are not causal dollar attribution or counterfactual performance.'
        ])
    with a.output.open('x') as f:
        json.dump(out, f, indent=2); f.write('\n')
    print(json.dumps(dict(status=out['status'], accounts=20, wallets=0, fits=0)))


if __name__ == '__main__':
    main()
