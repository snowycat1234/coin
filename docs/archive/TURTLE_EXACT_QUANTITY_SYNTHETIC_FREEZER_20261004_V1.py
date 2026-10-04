"""Freeze one new necessary quantity-identity regression; no market arrays."""
import ast,hashlib,json,os,subprocess
from datetime import UTC,datetime
from pathlib import Path
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state')
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
parent=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
assert os.environ['COIN_TASK_ID'] and parent=='bbb2d8dd943c4830579f79e5aa01bc8799b7a904'
archive=ROOT/'docs/archive/TURTLE_EXACT_QUANTITY_SYNTHETIC_FREEZER_20261004_V1.py'
with archive.open('xb') as f:f.write(Path(__file__).read_bytes())
old=json.loads((ROOT/'protocols/TURTLE_NO_ADD_SYNTHETIC_20261004_V1.json').read_bytes())
paths=set(old['frozen_sources'])-{'tests/test_turtle_no_add_direct.py','docs/archive/TURTLE_NO_ADD_FREEZER_SOURCE_20261004_V1.py'}
paths|={'tests/test_turtle_exact_candidate_quantity.py',str(archive.relative_to(ROOT)),
 'reports/fast_research/TURTLE_NO_ADD_RISK_ROUNDTRIP_COUNTEREXAMPLE_20261004_V1.json'}
for p in paths:
    if p.endswith('.py'):ast.parse((ROOT/p).read_bytes())
name='TURTLE_EXACT_QUANTITY_SYNTHETIC_20261004_V1'
spec=dict(old,contract_id='D061_EXACT_CANDIDATE_QUANTITY_SYNTHETIC_V1',git_commit=parent,
 created_utc=datetime.now(UTC).isoformat(),freeze_task_id=os.environ['COIN_TASK_ID'],
 frozen_sources={p:sha(ROOT/p) for p in sorted(paths)},tests=['tests/test_turtle_exact_candidate_quantity.py'],
 calculation_rules=dict(unscaled_candidates_preserve_Decimal_identity=True,scaled_risk_original_path=True,
    unchanged_caps_capacity_five_attempts=True,original_STOP_EXIT_partial_callback_preserved=True),
 run_dir=str(STATE/'d061-turtle-exact-quantity-synthetic-20261004-v1'),
 output_path='reports/fast_research/'+name+'.json',test_scope='ONE_NEW_FINANCIAL_RISK_SCHEDULING_COUNTEREXAMPLE_NOT_MARKET_REPLAY',
 old_tests_replayed=False,models_fit=0)
out=ROOT/'protocols'/f'{name}.json'
with out.open('x') as f:json.dump(spec,f,indent=2,allow_nan=False);f.write('\n')
print(json.dumps(dict(protocol=str(out),sha256=sha(out),source_count=len(paths),market_arrays_read=False)),flush=True)
