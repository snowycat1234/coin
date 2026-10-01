"""Retain the previously accepted diagnostic card when restarting the viewer."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path('/mnt/d/codex/coin')
RUN = Path('/home/xflops/coin-state/fr-rolling00-full-window-diagnostic-20261002-v1')
binding = json.loads((RUN / 'RUN_BINDING.json').read_text())
accepted = json.loads((ROOT / 'reports/fast_research/FR_ROLLING00_ROOT_ACCEPTANCE_20261002_V1.json').read_text())
digest = hashlib.sha256(json.dumps(binding,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()
assert digest == accepted['binding_sha256']
spec = importlib.util.spec_from_file_location('accepted_task_progress_window', ROOT / 'scripts/task_progress_window.py')
window = importlib.util.module_from_spec(spec)
spec.loader.exec_module(window)
# No old PID is treated as live. The viewer counts the original completion receipts.
window.KNOWN[('run', str(RUN))] = (0, 0)
window.main()
