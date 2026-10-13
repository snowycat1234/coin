"""Preparation-only manifest builder; no account import or historical advance."""
from pathlib import Path
import json,hashlib
H=Path(__file__).resolve().parent;R=H.parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=json.loads((R/'coin_sma_fine_completion_20261013/FROZEN_CODE.json').read_text())
deps=source['dependencies_SHA256'].copy()
# Only fine-profile infrastructure and frozen transport closure. No source body from retained data.
for p in (R/'coin_sma_fine_completion_20261013/terminal_diagnosis/DIAGNOSIS_RECEIPT.json',):deps[str(p.relative_to(R))]=sha(p)
names=['run_cases.py','preflight_terminal.py','terminal_adapter.py','PROTOCOL.md','CASE_BINDINGS.json','TERMINAL_QUOTE_GATE.json','resource_gate.py','worker_bounds.py','run_budget.py','test_synthetic.py','cold_audit.py']
m=dict(status='PREPARED_ONLY_ZERO_HISTORY_PENDING_REVIEW_AND_GO',bootstrap_SHA256=sha(H/'freeze_terminal.py'),files_SHA256={n:sha(H/n) for n in names},dependencies_SHA256=deps)
(H/'FROZEN_CODE.json').write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
