"""Reproduce registered effect/intervals from small saved score evidence, no forecasts."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scores", type=Path, required=True)
    parser.add_argument("--result", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    cfg = json.loads((Path(__file__).parent/"config.json").read_text())
    result = json.loads(args.result.read_text())
    with args.scores.open(newline='') as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == result["evaluation_windows"] == 2265
    dates = np.array([int(row['origin_us']) for row in rows], dtype=np.int64)
    assets = np.array([int(row['asset']) for row in rows])
    blocks = np.array([int(row['block']) for row in rows])
    model = np.array([float(row['model_crps']) for row in rows])
    assert len(set(zip(dates, assets, strict=True))) == len(rows)
    groups = {}
    for i, (date, block) in enumerate(zip(dates, blocks, strict=True)):
        start = int(np.datetime64(cfg['evaluation'][block][0], 'us').astype(np.int64))
        key = int(block), int((date-start)//(44*86400000000))
        groups.setdefault(key, []).append(i)
    keys = list(groups)
    counts = np.array([len(indices) for indices in groups.values()])
    smodel = np.array([model[indices].sum() for indices in groups.values()])
    comparisons = {}
    for name, field, expected_key in [('shape', 'shape_control_crps', 'paired_effect_and_uncertainty'),
                                      ('saved_EWMA', 'a1_crps', 'earlier_EWMA_comparison_paired_uncertainty')]:
        control = np.array([float(row[field]) for row in rows])
        sums = np.array([control[indices].sum() for indices in groups.values()])
        rng = np.random.default_rng(cfg['bootstrap']['seed'])
        draws = []
        for _ in range(cfg['bootstrap']['replicates']):
            pick = []
            for block in sorted(set(k[0] for k in keys)):
                candidates = [i for i, key in enumerate(keys) if key[0] == block]
                pick.extend(rng.choice(candidates, len(candidates), replace=True))
            draws.append(pick)
        draws = np.array(draws)
        absolute = (smodel[draws].sum(1)-sums[draws].sum(1))/counts[draws].sum(1)
        relative = 1-smodel[draws].sum(1)/sums[draws].sum(1)
        actual = {'model_minus_control': float((model-control).mean()), 'relative_gain': float(1-model.mean()/control.mean()),
                  'ci95': np.quantile(absolute, [.025, .975]).tolist(),
                  'relative_gain_ci95': np.quantile(relative, [.025, .975]).tolist()}
        expected = result[expected_key]
        for key, values in actual.items():
            assert np.max(abs(np.asarray(values)-expected[key])) < 1e-14, (name, key)
        comparisons[name] = actual
    output = {'status': 'PASS', 'scope': 'READ_ONLY_REPRODUCTION_OF_SAVED_SCORE_EFFECTS_AND_INTERVALS',
              'scores_sha256': hashlib.sha256(args.scores.read_bytes()).hexdigest(), 'score_rows': len(rows),
              'clusters': len(groups), 'cluster_counts': counts.tolist(), 'replicates': 2000,
              'comparisons': comparisons, 'new_controls': 0, 'new_fits': 0, 'new_inference': 0}
    args.output.write_text(json.dumps(output, indent=2)+'\n')
    print(json.dumps(output))


if __name__ == '__main__':
    main()
