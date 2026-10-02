"""Freeze one reduced-only mechanism control before any new financial run."""
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from scripts.investment import conditional_carry_reduce_adapter as adapter

ROOT=Path('/mnt/d/codex/coin');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ARCHIVE='docs/archive/CONDITIONAL_CARRY_PAIR_TRIM_PROTOCOL_FREEZER_20261003_V1.py'
OUT=ROOT/'protocols/CONDITIONAL_CARRY_PAIR_TRIM_122D_20261003_V1.json'
assert not OUT.exists() and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
old_path='protocols/CONDITIONAL_CARRY_ACCOUNT_122D_20261003_V1.json'
accepted=json.loads((ROOT/'reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json').read_bytes())
assert sha(ROOT/old_path)==accepted['source_hashes'][old_path]
old=json.loads((ROOT/old_path).read_bytes())
fixed=dict(old['frozen_sources'])
for name,digest in fixed.items():assert sha(ROOT/name)==digest,name
assert fixed[adapter.BASE_PATH]==adapter.BASE_SHA
for name in (ARCHIVE,adapter.ROOT_PATH,adapter.TEST,old_path,
             'reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json',
             'reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_DECIMAL_INDEPENDENT_AUDIT_20261003_V1.json',
             'reports/fast_research/CONDITIONAL_CARRY_ROOT_ACCEPTANCE_20261003_V1.json',
             'reports/GITHUB_CONDITIONAL_CARRY_SOURCE_BINDING_20261003_V1.json'):
    fixed[name]=sha(ROOT/name)
spec={**old, 'contract_id':adapter.CONTRACT_ID,'created_utc':datetime.now(UTC).isoformat(),
    'git_commit_at_freeze':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'classification':'ONE_SEEN_SAME_CAP_COST_MECHANISM_CONTROL_NOT_UNSEEN_OR_LONG_TERM_APR',
    'research_question':'Can reduced-only matched-pair cap maintenance extend carry long enough to amortize unchanged costs?',
    'decision':'D030','rules':adapter.RULES,'frozen_sources':fixed,
    'base_account_path':adapter.BASE_PATH,'base_account_sha256':adapter.BASE_SHA,
    'required_smoke_receipt':'reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_TINY_20261003_V1.json',
    'fixed_control_path':'reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json',
    'fixed_control_sha256':fixed['reports/fast_research/CONDITIONAL_CARRY_ACCOUNT_122D_ACTUAL_20261003_V1.json'],
    'control_replayed':False,'configurations':1,'seeds':0,'hyperparameter_search':False,
    'size_frozen_at_first_signal':'MIN_HELD_0.25_SIGNAL_NAV_OVER_SIGNAL_SPOT_PLUS_MARK',
    'partial_realized_loss':'FREE_CASH_FIRST_THEN_OWN_ISOLATED_DEBIT_NO_CREDIT_OR_RESERVE_RESET',
    'partial_funding_tie':'EXCLUDE_CLOSING_QUANTITY_ONLY_CONTINUING_QUANTITY_RETAINS_ORIGINAL_ENTRY',
    'same_original_margin_reserve_and_absolute_guard':True,
    'funding_within_5s_entry_or_exit':'REPORT_FULL_AND_PARTIAL_BOUNDARY_WITNESSES_NO_POSTHOC_SELECTION'}
adapter.verify_spec(spec)
with OUT.open('x') as w:json.dump(spec,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps(dict(protocol=str(OUT),sha256=sha(OUT),frozen_files=len(fixed),market_arrays_read=False,new_account_math_run=False)))
