"""Separate fit and score entrypoints. Source preparation never fits."""
from __future__ import annotations
import argparse
import hashlib
import json
import shutil
import time
from pathlib import Path
import numpy as np
import core

HERE = Path(__file__).resolve().parent


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def frozen():
    manifest = json.loads((HERE / 'FROZEN.json').read_text())
    for name, expected in manifest['files'].items():
        if sha(HERE / name) != expected:
            raise ValueError('Frozen scientific source changed: ' + name)
    if shutil.disk_usage(HERE).free < 15 * 1024**3:
        raise RuntimeError('15GiB shared disk reserve required')
    return manifest


def load(path):
    with np.load(path, allow_pickle=False) as z:
        return {name: z[name].copy() for name in
                ('decision_us', 'features', 'target_return', 'label_mature_us')}


def verify_prepared(root):
    record = json.loads((root / 'PREPARATION.json').read_text())
    for name, expected in record['outputs_SHA256'].items():
        if sha(root / name) != expected:
            raise ValueError('Prepared source changed: ' + name)
    if record['freeze_SHA256'] != sha(HERE / 'FROZEN.json'):
        raise ValueError('Preparation does not bind this freeze')
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('fit', 'score'))
    parser.add_argument('--prepared', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--model-sha256')
    args = parser.parse_args()
    frozen(); preparation = verify_prepared(args.prepared)
    if args.output.exists():
        raise FileExistsError('Never replace an existing scientific attempt')
    args.output.mkdir(parents=True)
    began = time.monotonic()
    if args.phase == 'fit':
        train = load(args.prepared / 'TRAIN.npz')
        model = core.fit(train['decision_us'], train['features'], train['target_return'], train['label_mature_us'])
        model.update(freeze_SHA256=sha(HERE / 'FROZEN.json'), preparation_SHA256=sha(args.prepared / 'PREPARATION.json'))
        save(args.output / 'MODEL.json', model)
        save(args.output / 'FIT.json', dict(seconds=time.monotonic()-began, fit_groups=2,
             actual_asset_systems=10, deterministic_OLS=True, scientific_attempts=1,
             source_SHA256=preparation['outputs_SHA256'], model_SHA256=sha(args.output / 'MODEL.json'),
             wallets=0, providers=0, validation_scores=0))
        print('FROZEN_MODEL_SHA256', sha(args.output / 'MODEL.json'), flush=True)
    else:
        if args.model is None or args.model_sha256 is None or sha(args.model) != args.model_sha256:
            raise ValueError('Explicit already-frozen model path and exact SHA required')
        model = json.loads(args.model.read_text())
        if model['freeze_SHA256'] != sha(HERE / 'FROZEN.json') or model['preparation_SHA256'] != sha(args.prepared / 'PREPARATION.json'):
            raise ValueError('Model/source/freeze identity differs')
        reports = {}
        for year in (2023, 2024, 2025):
            a = load(args.prepared / f'Y{year}.npz')
            reports[str(year)], arrays = core.score(model, a['decision_us'], a['features'], a['target_return'], a['label_mature_us'], year)
            np.savez_compressed(args.output / f'Y{year}.npz', **arrays)
            save(args.output / f'Y{year}.json', reports[str(year)])
        save(args.output / 'RESULT.json', dict(status='PASS_NEXT_STAGE_INFORMATION_ONLY' if all(r['primary_gate'] for r in reports.values()) else 'STOP_FIXED_SIGNED_SERIAL_RECIPE',
             years=reports, all_seen_development=True, seconds=time.monotonic()-began,
             model_SHA256=args.model_sha256, freeze_SHA256=sha(HERE / 'FROZEN.json'),
             preparation_SHA256=sha(args.prepared / 'PREPARATION.json'), fits=0, wallets=0,
             providers=0, price_cost_probe_is_not_net_wallet_income=True))
        print(json.dumps(reports, allow_nan=False), flush=True)


if __name__ == '__main__':
    main()
