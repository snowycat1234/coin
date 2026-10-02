"""CPU dependency isolation and tiny reproducible artifact; no market/model research."""
import hashlib
import argparse
import importlib
import importlib.metadata
import json
import os
import resource
import subprocess
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler

from quant.paths import ROOT, STATE

EXPECTED = {
    'numpy': '2.5.3', 'scipy': '1.18.1', 'polars': '1.44.2', 'pyarrow': '23.0.1',
    'sklearn': '1.9.1', 'xgboost': '3.4.1', 'lightgbm': '4.7.0',
    'httpx': '0.28.1', 'websockets': '16.1.1', 'torch': '2.7.1+cpu',
    'river': '0.26.1', 'einops': '0.8.2', 'narwhals': '2.26.0',
}
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--environment', type=Path, required=True)
p.add_argument('--run-dir', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
args = p.parse_args()
env, out = args.environment.resolve(), args.run_dir.resolve()
assert env.is_relative_to(STATE.resolve()) and out.is_relative_to(STATE.resolve())
assert args.output.resolve().is_relative_to((ROOT/'reports/fast_research').resolve())
out.mkdir(exist_ok=False)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


assert Path(sys.prefix).resolve() == env.resolve()
assert not any('research-env-v6' in p or '/coin/.venv/' in p for p in sys.path)
actual = {}
for name, expected in EXPECTED.items():
    module = importlib.import_module(name)
    assert module.__version__ == expected, name
    origin = Path(module.__file__).resolve()
    assert origin.is_relative_to(env.resolve()), (name, origin)
    actual[name] = {'version': module.__version__, 'path': str(origin)}
assert importlib.metadata.version('pytorch-tcn') == '1.2.3'
assert importlib.import_module('torch').version.cuda is None
assert not any(b'research-env-v6' in p.read_bytes() or b'/coin/.venv/' in p.read_bytes()
               for p in env.rglob('*.pth'))

# One artificial model fits eight invented rows; there is no market outcome access.
random = np.random.default_rng(20261001)
x = random.normal(size=(12, 3))
y = .1 * x[:8, 0] - .05 * x[:8, 1]
scaler = StandardScaler().fit(x[:8])
model = Ridge(alpha=1.0).fit(scaler.transform(x[:8]), y)
artifact = out/'synthetic-ridge.joblib'
joblib.dump((scaler, model), artifact)
np.save(out/'inputs.npy', x[8:])
expected = model.predict(scaler.transform(x[8:]))
np.save(out/'expected.npy', expected)
child = out/'reproduce.py'
child.write_text('''import sys, joblib, numpy as np
from pathlib import Path
p=Path(sys.argv[1]); scaler, model=joblib.load(p/'synthetic-ridge.joblib')
result=model.predict(scaler.transform(np.load(p/'inputs.npy')))
assert np.array_equal(result,np.load(p/'expected.npy'))
np.save(p/'reproduced.npy',result)
''')
subprocess.run([sys.executable, '-I', str(child), str(out)], check=True, env=dict(os.environ))
assert sha(out/'expected.npy') == sha(out/'reproduced.npy')
receipt = {'status': 'PASS_CLEAN_COMPLETE_CPU_LOCK_AND_SYNTHETIC_ARTIFACT_REPRODUCTION',
    'created_utc': datetime.now(UTC).isoformat(),
    'source_hashes': {str(p.relative_to(ROOT)): sha(p) for p in [
        Path(__file__), ROOT/'environments/v8/pyproject.toml', ROOT/'environments/v8/uv.lock']},
    'python_executable': sys.executable, 'python_version': sys.version,
    'sys_prefix': sys.prefix, 'imported_dependencies': actual,
    'complete_lock_package_count': len(tomllib.loads((ROOT/'environments/v8/uv.lock').read_text())['package']),
    'overlay_site_paths': [], 'external_pth_links': [],
    'synthetic_model_fit_calls': 1, 'market_model_fit_calls': 0,
    'seed': 20261001, 'artifact_directory': str(out),
    'artifacts': {p.name: sha(p) for p in out.iterdir() if p.is_file()},
    'reproduction_exact_prediction_bytes_equal': True,
    'peak_process_ram_bytes': resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
    'locked_consumed': False, 'gpu_used': False, 'orders_sent': 0,
    'P1_economic_gate_passed': False,
    'limitations': ['Isolated runtime and synthetic checkpoint test, not research validation.',
                    'CI workflow and separate mutation gates still need execution.',
                    'CPU torch is locked for capability preservation; formal deep research remains paused.']}
dest = args.output
with dest.open('x') as f:
    json.dump(receipt, f, ensure_ascii=False, indent=2)
print(json.dumps({'status': receipt['status'], 'report': str(dest)}, ensure_ascii=False), flush=True)
