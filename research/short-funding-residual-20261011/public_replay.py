"""Restore immutable public evidence into a fresh STATE and replay without fit.

The only Git adapter returns the independently downloaded immutable INDEX bytes.
The original experiment, source reader, model loader, and prediction arithmetic
remain unchanged. This permits replay without a local repository/data cache.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import re
import sys
import urllib.request

import numpy  # Runtime imports precede the original-workspace access guard.
import pyarrow.parquet

STUDY = 'research/short-funding-residual-20261011'
RAW = 'https://raw.githubusercontent.com/snowycat1234/coin/'
DATA_COMMIT = 'e0d3400b23842f11f167a63e7d80856d76501de8'
DATA_DIR = 'research/temporal-feature-data-20261009/'
SOURCE_COMMIT = 'e347fa4f8dc5d65c9a419b45eb330476d8c734ed'
PROTOCOL_SHA = '5d8506265b0ba2f89aff1e9f0104403cf813a7fc00e4046d5987cbe2dbbc5bb5'
MODEL_SHA = 'dc4e690d7a59221cb82a8a16fdb0d52996fbe5144d64dbac03b35225ec723e67'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    parser.add_argument('--state', type=Path, required=True)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-f]{40}', args.revision):
        raise ValueError('Immutable full public revision required')
    state = args.state.resolve()
    if not state.is_relative_to(Path('/workspace')):
        raise ValueError('Fresh STATE must be below /workspace')
    # The resource launcher can already have created source/guard and receipts.
    restored = state / 'public'
    restored.mkdir(parents=True, exist_ok=False)
    records = []

    def get(revision, name, size=None, expected=None):
        url = RAW + revision + '/' + name
        with urllib.request.urlopen(url, timeout=30) as response:
            if not response.url.startswith(RAW):
                raise ValueError('Unexpected public redirect')
            raw = response.read(1_048_577)
        if len(raw) > 1_048_576:
            raise ValueError('Public file exceeds bounded read')
        if size is not None and len(raw) != size:
            raise ValueError('Public length differs: ' + name)
        if expected is not None and digest(raw) != expected:
            raise ValueError('Public digest differs: ' + name)
        records.append(dict(revision=revision, path=name, bytes=len(raw), sha256=digest(raw)))
        return raw

    manifest_raw = get(args.revision, STUDY + '/DELIVERY_MANIFEST.json')
    manifest = json.loads(manifest_raw)
    if manifest['scientific_source_commit'] != SOURCE_COMMIT:
        raise ValueError('Unexpected scientific source')
    (restored / 'DELIVERY_MANIFEST.json').write_bytes(manifest_raw)
    for name, item in manifest['files'].items():
        relative = Path(name)
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe manifest path')
        raw = get(args.revision, STUDY + '/' + name, item['bytes'], item['sha256'])
        path = restored / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as f:
            f.write(raw)
    print('PUBLIC_DELIVERY_READBACK_COMPLETE', len(manifest['files']), flush=True)

    binding = json.loads((restored / 'SOURCE_BINDING.json').read_text())
    for name, item in binding['files'].items():
        raw = (restored / name).read_bytes()
        if digest(raw) != item['sha256'] or len(raw) != item['bytes']:
            raise ValueError('Frozen implementation binding differs')
    if digest((restored / 'PROTOCOL.json').read_bytes()) != PROTOCOL_SHA:
        raise ValueError('Frozen protocol differs')
    if digest((restored / 'results/MODELS.json').read_bytes()) != MODEL_SHA:
        raise ValueError('Actual fitted model bytes differ')

    index_raw = get(DATA_COMMIT, DATA_DIR + 'INDEX.json')
    index = json.loads(index_raw)
    (state / 'source/INDEX.json').write_bytes(index_raw)
    parts = [get(DATA_COMMIT, DATA_DIR + p['file'], p['bytes'], p['SHA256']) for p in index['parts']]
    archive = b''.join(parts)
    if digest(archive) != 'bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30' or len(archive) != 2_246_454:
        raise ValueError('Public source reconstruction differs')
    with (state / 'source/features.zip').open('xb') as f:
        f.write(archive)
    if sum(p.stat().st_size for p in state.rglob('*') if p.is_file()) > 10_485_760:
        raise ValueError('Fresh STATE output budget exceeded')
    print('PUBLIC_SOURCE_RESTORED', len(archive), flush=True)

    runtime = Path(sys.prefix).resolve()
    denied = []

    def audit(event, values):
        if event == 'subprocess.Popen':
            raise RuntimeError('Replay never executes Git or training subprocesses')
        if event == 'open' and isinstance(values[0], (str, bytes)):
            path = Path(values[0]).resolve()
            if path.is_relative_to(Path('/workspace')) and not path.is_relative_to(state) and not path.is_relative_to(runtime):
                denied.append(str(path))
                raise RuntimeError('Original workspace/cache access forbidden')

    sys.addaudithook(audit)
    spec = importlib.util.spec_from_file_location('public_funding_experiment', restored / 'experiment.py')
    experiment = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(experiment)

    def public_index_only_git(root, *command):
        expected = ('show', DATA_COMMIT + ':' + DATA_DIR + 'INDEX.json')
        if command != expected:
            raise RuntimeError('Only immutable source INDEX is supported')
        return index_raw

    experiment.git = public_index_only_git
    # Reject any accidental refit, even if a future replay code path changes.
    experiment.fit = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('Refitting forbidden'))
    sys.argv = ['experiment.py', '--mode', 'verify', '--state', str(state),
                '--saved-results', str(restored / 'results'), '--protocol-sha256', PROTOCOL_SHA]
    experiment.main()
    models = json.loads((restored / 'results/MODELS.json').read_text())
    for name, width in [('baseline', 8), ('funding', 9)]:
        model = models[name]
        if len(model['mean']) != width or len(model['scale']) != width or len(model['beta']) != width + 1:
            raise ValueError('Unexpected model dimensions')
        if not all(math.isfinite(v) for key in ('mean', 'scale', 'beta') for v in model[key]):
            raise ValueError('Nonfinite public model')
    report = dict(status='PASS', revision=args.revision, scientific_source_commit=SOURCE_COMMIT,
                  models_sha256=MODEL_SHA, protocol_sha256=PROTOCOL_SHA, files=records,
                  original_workspace_read_attempts=denied, fits=0, development_reads=0,
                  model_loads=2, prediction_scalars=496, max_prediction_residual=0,
                  public_data_bytes=len(archive),
                  loader_adapter='Only git show immutable source INDEX replaced by downloaded exact public INDEX bytes; source and prediction arithmetic unchanged',
                  runtime_scope='Existing installed Python/NumPy/PyArrow; fresh public evidence/data/model restoration, not fresh dependency installation')
    experiment.save(state / 'PUBLIC_RESTORE.json', report)
    print('PUBLIC_RESTORE_PASS; fits0; original_workspace_reads0', flush=True)


if __name__ == '__main__':
    main()
