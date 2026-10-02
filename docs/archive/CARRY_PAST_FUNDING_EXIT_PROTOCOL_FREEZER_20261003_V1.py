"""D032: freeze one new gate before synthetic or actual financial execution."""
from datetime import UTC, datetime
import hashlib
import json
import subprocess
from pathlib import Path
from scripts.investment import conditional_carry_past_funding_exit_adapter as gate

ROOT = Path('/mnt/d/codex/coin')
ARCHIVE = 'docs/archive/CARRY_PAST_FUNDING_EXIT_PROTOCOL_FREEZER_20261003_V1.py'
OUT = ROOT / gate.PROTOCOL
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert not OUT.exists()
assert Path(__file__).read_bytes() == (ROOT / ARCHIVE).read_bytes()
assert sha(ROOT / gate.ROOT_PATH) == 'ff5513fecd5d5dc3b887395bb585e0d1b6010c5efc5d3f642b6460460ebd8a77'
assert sha(ROOT / gate.TEST) == '47c6b112cf738b5968c29e12810baf0cceb1b273981099f650246d881cf5b5ff'
fixed, parents, periods = {}, {}, {}
for period, (name, digest) in gate.PARENT_CONTRACTS.items():
    assert sha(ROOT / name) == digest
    parent = json.loads((ROOT / name).read_bytes())
    parents[period] = parent
    for source, value in parent['frozen_sources'].items():
        assert source not in fixed or fixed[source] == value
        assert sha(ROOT / source) == value, source
        fixed[source] = value
    fixed[name] = digest
    periods[period] = {key: parent[key] for key in (
        'period_start', 'period_end_exclusive', 'source_calendar',
        'expected_price_files', 'expected_funding_files',
        'expected_minutes_per_asset', 'expected_funding_events',
        'source_options_path', 'source_options_sha256')}
for name in (
    ARCHIVE, gate.ROOT_PATH, gate.TEST,
    'docs/archive/CARRY_PAST_FUNDING_EXIT_STATIC_PREPARATION_20261003_V1.json',
    'docs/archive/CARRY_PAST_FUNDING_EXIT_D032_DECISION_PRE_RESULT_20261003_V1.md',
    'reports/fast_research/CARRY_PAST_FUNDING_EXIT_STATIC_REVIEW_20261003_V1.json',
    'reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_122D_ACTUAL_20261003_V1.json',
    'reports/fast_research/CONDITIONAL_CARRY_PAIR_TRIM_ROOT_ACCEPTANCE_20261003_V1.json',
    'reports/fast_research/CARRY_90D_PAIR_TRIM_ACTUAL_20261003_V1.json',
    'reports/fast_research/CARRY_90D_TWO_POLICY_ROOT_ACCEPTANCE_20261003_V1.json',
    'reports/GITHUB_CARRY_90D_SOURCE_BINDING_20261003_V1.json',
    'reports/GITHUB_CARRY_90D_SYNC_VERIFIED_20261003_V1.json'):
    fixed[name] = sha(ROOT / name)
spec = {
    'contract_id': gate.CONTRACT_ID,
    'created_utc': datetime.now(UTC).isoformat(),
    'git_commit_at_freeze': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
    'classification': 'WHOLE_SEEN_122D_AND90D_CONDITIONAL_SCREENING_NOT_UNSEEN_OR_LONG_TERM_APR',
    'decision': 'D032',
    'research_question': 'Can one fixed delayed past-owned-funding exit improve both full saved controls without worse event drawdown or losing most positive coupons?',
    'rules': gate.RULES, 'gate_rules': gate.GATE_RULES,
    'period_contracts': {period: dict(path=name, sha256=digest)
        for period, (name, digest) in gate.PARENT_CONTRACTS.items()},
    'period_metadata': periods,
    'fee_reference_profile_path': parents['122D']['fee_reference_profile_path'],
    'fee_reference_profile_sha256': parents['122D']['fee_reference_profile_sha256'],
    'selected_parent_source_identity': 'EXACT_PARENT_SOURCE_OPTIONS_SHA256_PER_PERIOD_NO_MASTER_ALIAS',
    'frozen_sources': fixed,
    'required_smoke_receipt': 'reports/fast_research/CARRY_PAST_FUNDING_EXIT_TINY_20261003_V1.json',
    'required_smoke_scope': 'ONE_NEW_GATE_BOUNDARY_INTERACTION_CASE_BOTH_CONTEXTS_NO_OLD_GREEN_REPLAY',
    'maximum_new_owned_bytes': 25_000_000, 'maximum_wall_seconds': 600,
    'combined_output_budget_bytes': 50_000_000,
    'shared_RAM_bytes': 5_000_000_000, 'swap': 0, 'GPU': False,
    'configurations': 1, 'actual_accounts': 2, 'seeds': 0,
    'hyperparameter_search': False, 'old_controls_replayed': False,
    'comparison': 'SEPARATE_FULL_PERIOD_SAVED_PAIR_TRIM_NO_CONCATENATION_OR_MONTH_SELECTION',
    'adoption_criteria': {
        'both_net_delta_gt_USDT': 1e-7,
        'all_observation_DD_increment_lte': 1e-10,
        'major_positive_coupon_foregone_share_gt': .5,
        'pause_rounding_sensitive_trigger': True,
        'no_trigger_is_no_adoption_evidence': True,
        'constraints_unchanged': True,
        'accounting_tolerances_not_statistical_significance': True},
    'decision_arithmetic': gate.GATE_RULES['decision_arithmetic'],
    'publication_assumption_certified': False,
    'funding_units': 'UNCONFIRMED_PRIOR_FRACTION_HYPOTHESIS',
    'candidate_status': 'NO_QUALIFIED_CANDIDATE',
    'capital_net_APR': 'NOT_EVALUABLE',
    'forbidden': ['LOCKED_PRICE_IO', 'REAL_ORDERS', 'ACCOUNT_KEYS', 'NEW_PAID_SERVICE',
        'GPU', 'FROZEN_OVERWRITE', 'LOWER_COST', 'HIGHER_LEVERAGE', 'REENTRY',
        'WINDOW_SEARCH', 'POST_RESULT_THRESHOLD_CHANGE']}
for name in ('fixed_control_path', 'fixed_control_sha256'):
    spec.pop(name, None)
# Compile only exact function AST / isolated namespaces. No arrays, test or wallet simulation.
contexts = {period: gate.context(spec, period) for period in gate.PARENT_CONTRACTS}
assert all(ns['FUNDING_GATE_DERIVATION']['event_loop_reordered'] is False for ns in contexts.values())
assert contexts['122D']['FUNDING_GATE_DERIVATION']['derived_simulate_AST_sha256'] == contexts['90D']['FUNDING_GATE_DERIVATION']['derived_simulate_AST_sha256']
spec['pre_array_metadata_compile'] = {period: dict(
    start_us=ns['START_US'], end_exclusive_us=ns['END_US'],
    simulate_AST_sha256=ns['FUNDING_GATE_DERIVATION']['derived_simulate_AST_sha256'],
    main_AST_sha256=ns['FUNDING_GATE_DERIVATION']['derived_main_AST_sha256'])
    for period, ns in contexts.items()}
with OUT.open('x') as stream:
    json.dump(spec, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps(dict(protocol=str(OUT), sha256=sha(OUT), frozen_files=len(fixed),
    both_contexts_compiled=True, market_arrays_read=False, financial_math_run=False)))
