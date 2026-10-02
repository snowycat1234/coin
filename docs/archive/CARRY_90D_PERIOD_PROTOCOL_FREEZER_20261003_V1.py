"""Freeze common new-period controls before synthetic or historical arrays."""
from datetime import UTC, datetime
import hashlib,json,subprocess
from pathlib import Path
from scripts.investment import conditional_carry_90d_period_adapter as period
ROOT=Path('/mnt/d/codex/coin');sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
ARCHIVE='docs/archive/CARRY_90D_PERIOD_PROTOCOL_FREEZER_20261003_V1.py'
OUT=ROOT/'protocols/CONDITIONAL_CARRY_90D_FIXED_PERIOD_20261003_V1.json'
assert not OUT.exists() and Path(__file__).read_bytes()==(ROOT/ARCHIVE).read_bytes()
prior_path='protocols/CONDITIONAL_CARRY_PAIR_TRIM_122D_20261003_V1.json'
assert sha(ROOT/prior_path)=='5c13850c48e0cbd86bf2ae3629284f6b14d61803b0c299fef3796582ae5eba49'
prior=json.loads((ROOT/prior_path).read_bytes());fixed=dict(prior['frozen_sources'])
for name,digest in fixed.items():assert sha(ROOT/name)==digest,name
view_path='reports/fast_research/CARRY_90D_SOURCE_VIEW_20261003_V1.json'
view=json.loads((ROOT/view_path).read_bytes())
for name in (ARCHIVE,prior_path,period.ROOT_PATH,period.TEST,view_path,
             'docs/archive/CARRY_90D_PERIOD_STATIC_PREPARATION_20261003_V1.json',
             'reports/GITHUB_CARRY_CHRONOLOGY_SOURCE_BINDING_20261003_V1.json',
             'reports/GITHUB_CARRY_CHRONOLOGY_SOURCE_SYNC_VERIFIED_20261003_V1.json'):
    fixed[name]=sha(ROOT/name)
for path,digest,status in period.SOURCE_PROOFS.values():
    assert sha(ROOT/path)==digest and json.loads((ROOT/path).read_bytes())['status']==status
    fixed[path]=digest
spec={**prior,'contract_id':'CONDITIONAL_CARRY_90D_FIXED_PERIOD_V1','created_utc':datetime.now(UTC).isoformat(),
    'git_commit_at_freeze':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
    'decision':'D031','classification':'FIXED_90D_DEVELOPMENT_TIME_EXTRAPOLATION_SCREENING_NOT_UNSEEN_OR_LONG_TERM_APR',
    'research_question':'Do unchanged all-flat and pair-trim carry rules preserve net edge in the fixed next90 calendar?',
    'period_start':'2025-12-01','period_end_exclusive':'2026-03-01','source_calendar':list(period.MONTHS),
    'expected_price_files':18,'expected_funding_files':6,'expected_minutes_per_asset':129600,
    'expected_funding_events':view['funding_event_total'],'expected_funding_events_by_symbol':view['funding_counts_by_symbol'],
    'source_view_path':view_path,'source_view_sha256':sha(ROOT/view_path),
    'source_options_path':view_path,'source_options_sha256':sha(ROOT/view_path),
    'policies':period.POLICIES,'frozen_sources':fixed,
    'required_smoke_receipt':'reports/fast_research/CARRY_90D_PERIOD_TINY_20261003_V1.json',
    'required_smoke_scope':'ONE_NEW_PERIOD_SOURCE_ENDPOINT_CASE_BOTH_CONTEXTS_NO_OLD_FINANCIAL_REPLAY',
    'maximum_new_owned_bytes':50_000_000,'maximum_wall_seconds':600,
    'configurations':2,'seeds':0,'hyperparameter_search':False,
    'comparison':'SHARED_ACCEPTED_DATA_C0_COST_CAPS_MARGIN_DIFFERENT_FIXED_EXIT_POLICIES',
    'old122_control_replayed':False,'old_funding_count_not_assumed':True,
    'funding_units':'UNCONFIRMED_EXPLICIT_PRIOR_FRACTION_HYPOTHESIS_NOT_CERTIFIED_FOR_NEW_MONTHS',
    'combined_output_budget_bytes':50_000_000,'shared_RAM_bytes':5_000_000_000,'swap':0,'GPU':False}
# Eliminate obsolete single-policy smoke/control bindings in this common protocol.
for name in ('rules','fixed_control_path','fixed_control_sha256'):
    spec.pop(name,None)
period.verify_spec(spec)
with OUT.open('x') as w:json.dump(spec,w,indent=2,ensure_ascii=False);w.write('\n')
print(json.dumps(dict(protocol=str(OUT),sha256=sha(OUT),frozen_files=len(fixed),events=spec['expected_funding_events'],market_arrays_read=False,account_math_run=False)))