from __future__ import annotations
import hashlib
import inspect
import json
from dataclasses import replace
from datetime import date, datetime, timezone
from pathlib import Path
import sys

ROOT = Path('/mnt/d/codex/coin')
STATE = Path('/home/xflops/coin-state/test-v8-adversarial-20261002-v1')
sys.path.insert(0, str(ROOT / 'scripts/research_v8'))
import numpy as np
import polars as pl
import labels as v8

FILES = ['protocols/LABEL_CONTRACT_V8.json', 'scripts/research_v8/labels.py', 'tests/test_v8_label_contract.py']
source_sha = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in FILES}
xml_path = Path('/home/xflops/coin-state/test-v8-label-contract-20261002-v1.xml')
contract = v8.contract()
n = 1000
base = v8.day_us(date(2025, 7, 1))
times = base + np.arange(n, dtype=np.int64) * v8.BAR_US
rows = {'timestamp': times}
for i, s in enumerate(v8.STREAMS):
    rows.update({s+'__available_us': times + v8.BAR_US,
                 s+'__quality': np.zeros(n, dtype=np.int32),
                 s+'__aggressive_buy_notional': np.full(n, 100. + i),
                 s+'__aggressive_sell_notional': np.full(n, 80. + i),
                 s+'__close': 100. + i * 10 + np.arange(n) * .01,
                 s+'__last_trade_us': times + v8.BAR_US - 1_000_000})
joint = pl.DataFrame(rows)
decisions = base + np.asarray([1800, 1860], dtype=np.int64) * v8.US
d = int(decisions[0])
probes = []
findings = []

# Positive control for all registered variants.
for variant in contract['labels']:
    labels = v8.label_table(joint, decisions, variant)
    probes.append({'id': 'control_exact_'+variant, 'all_valid': bool(labels['label_valid'].all()),
                   'observed_maturity_lag_us': (labels['label_mature_us'].to_numpy()-decisions).tolist()})

# GAP10 has a full bar in the latency interval before the return entry anchor.
gap_time = d + 150 * v8.US
late_available = d + 2000 * v8.US
s = v8.STREAMS[0]
late_gap = joint.with_columns(pl.when(pl.col('timestamp') == gap_time)
    .then(late_available).otherwise(pl.col(s+'__available_us')).alias(s+'__available_us'))
late_labels = v8.label_table(late_gap, decisions[:1], 'EARLY_LATE_150S_GAP10')
observed_maturity = int(late_labels['label_mature_us'][0])
gap_used_for_validity = bool(late_labels['label_valid'][0])
probes.append({'id': 'gap10_late_quality_availability', 'accepted': True,
               'gap_bar_timestamp_us': gap_time, 'gap_quality_available_us': late_available,
               'label_valid': gap_used_for_validity, 'label_mature_us': observed_maturity,
               'expected_minimum_label_mature_us': late_available,
               'maturity_understatement_us': late_available-observed_maturity})
if gap_used_for_validity and observed_maturity < late_available:
    findings.append({'id': 'V8A-01', 'priority': 'P1', 'status': 'CONFIRMED',
        'title': 'GAP10 quality availability is used but omitted from maturity',
        'source_lines': [105,106,107,113],
        'contract_fields': ['maturity', 'missing_policy', 'split'],
        'evidence_probe': 'gap10_late_quality_availability',
        'impact': 'The t+150s bar quality is read by validity over first_flow:exit_row, but flow maturity stops at t+150s and return maturity starts at the t+155s entry anchor. A valid offline label is reported mature at t+310s while required quality is unavailable until t+2000s. Chronology using this emitted maturity can fit before all needed information exists.',
        'required_fix': 'Compute maturity over every source field/bar used for label values or label validity, including any registered latency interval quality, or remove unsupported gap-quality dependencies with an explicit contract-consistent rule.'})

# Public nonoverlap/direct guard accepts a registered GAP10 label contracted to GAP5.
labels10 = v8.label_table(joint, decisions[:1], 'EARLY_LATE_150S_GAP10')
changed_entry = labels10.with_columns((pl.col('flow_label_end_us')+5*v8.US).alias('return_label_start_us'),
    (pl.col('flow_label_end_us')+5*v8.US).alias('delayed_entry_us'),
    (pl.col('return_label_end_us')-5*v8.US).alias('return_label_end_us'))
v8.assert_nonoverlap(changed_entry)
v8.direct_return_labels(changed_entry)
probes.append({'id': 'registered_gap10_contracted_to_gap5', 'assert_nonoverlap_accepted': True,
               'direct_return_labels_accepted': True, 'label_variant': changed_entry['label_variant'][0],
               'registered_gap_us': 10*v8.US,
               'accepted_gap_us': int(changed_entry['return_label_start_us'][0]-changed_entry['flow_label_end_us'][0])})
findings.append({'id': 'V8A-02', 'priority': 'P1', 'status': 'CONFIRMED',
    'title': 'Exported frame guard accepts changed registered variant boundaries',
    'source_lines': [159,162,167,236,238],
    'contract_fields': ['labels.EARLY_LATE_150S_GAP10', 'exact_window_note', 'overlap_assertions', 'DIRECT_RETURN_BASELINE'],
    'evidence_probe': 'registered_gap10_contracted_to_gap5',
    'impact': 'assert_nonoverlap hardcodes a minimum 5s gap and does not bind endpoints to label_variant. A GAP10 frame with return start/end moved 5s earlier passes the guard and direct target selection, despite retaining registered GAP10 identity and stale anchor provenance.',
    'required_fix': 'Validate each frame against its registered variant, exact offsets/durations, registered gap, price-anchor timestamps/availability and maturity fields before direct target selection or comparison.'})

# Observed future-flow signal is made falsely available at the decision timestamp.
observed = v8.label_table(joint, decisions[:1], signal_kind='OBSERVED_FUTURE_FLOW_DIAGNOSTIC')
false_early = observed.with_columns(pl.col('decision_us').alias('signal_available_us'),
    (pl.col('decision_us')+5*v8.US).alias('earliest_order_us'),
    (pl.col('decision_us')+5*v8.US).alias('earliest_permissible_order_us'))
v8.assert_nonoverlap(false_early)
v8.direct_return_labels(false_early)
probes.append({'id': 'observed_flow_made_available_at_decision', 'assert_nonoverlap_accepted': True,
    'direct_return_labels_accepted': True, 'signal_kind': false_early['signal_kind'][0],
    'signal_available_us': int(false_early['signal_available_us'][0]),
    'observed_future_flow_available_us': int(false_early['observed_future_flow_available_us'][0]),
    'accepted_earliest_order_us': int(false_early['earliest_order_us'][0]),
    'required_earliest_order_us': int(false_early['flow_label_mature_us'][0])+5*v8.US})
findings.append({'id': 'V8A-03', 'priority': 'P1', 'status': 'CONFIRMED',
    'title': 'Exported guard does not bind diagnostic signal availability to future-flow maturity',
    'source_lines': [159,164,165,166,236,238],
    'contract_fields': ['earliest_order_rule', 'overlap_assertions'],
    'evidence_probe': 'observed_flow_made_available_at_decision',
    'impact': 'An OBSERVED_FUTURE_FLOW_DIAGNOSTIC frame keeps flow maturity at decision+300s but changes signal_available to decision and both earliest-order aliases to decision+5s. The guard and direct target selector accept this causal violation.',
    'required_fix': 'Resolve actual signal availability from signal_kind, require observed signal availability and observed_future_flow_available to equal flow_label_mature, and require predicted availability to follow its declared past-only decision provenance.'})

# Missing future notional should invalidate labels under the contract, not abort the batch.
missing = joint.with_columns(pl.when(pl.col('timestamp') == d+5*v8.US)
    .then(float('nan')).otherwise(pl.col(s+'__aggressive_buy_notional')).alias(s+'__aggressive_buy_notional'))
try:
    missing_out = v8.label_table(missing, decisions)
    missing_evidence = {'id': 'missing_future_notional_policy', 'raised': False,
        'label_valid': missing_out['label_valid'].to_list()}
except Exception as exc:
    missing_evidence = {'id': 'missing_future_notional_policy', 'raised': True,
                       'exception_type': type(exc).__name__, 'exception': str(exc)}
probes.append(missing_evidence)
if missing_evidence['raised']:
    findings.append({'id': 'V8A-04', 'priority': 'P2', 'status': 'CONFIRMED',
        'title': 'Missing future notionals abort labels instead of per-row invalidation',
        'source_lines': [126,127,128,151,152,153],
        'contract_fields': ['missing_policy'],
        'evidence_probe': 'missing_future_notional_policy',
        'impact': 'A NaN in the first row future buy notional raises ValueError for the entire frame. The required result is label_valid=false and NaN label values for affected rows, with unaffected rows preserved. This is a missing-policy implementation gap, not proven leakage.',
        'required_fix': 'Validate future notional inputs by affected label windows and propagate invalidity/NaNs without interpolation or a batch-wide abort for row-level missing future data.'})

# The chronology helper exposes training/validation cutoff only.
split_params = list(inspect.signature(v8.assert_fit_chronology).parameters)
v8.assert_fit_chronology(fit_cutoff_us=299, validation_start_us=1000,
    embargo_us=100, max_label_lag_us=600, fitting_label_mature_us=[298])
probes.append({'id': 'split_guard_coverage', 'parameters': split_params,
    'training_cutoff_control_accepted': True,
    'validation_label_maturity_input_present': False,
    'test_start_input_present': False,
    'actual_label_lag_derivation_or_crosscheck_present': False})
findings.append({'id': 'V8A-05', 'priority': 'P1', 'status': 'STATIC_IMPLEMENTATION_GAP',
    'title': 'Validation-to-test maturity boundary and observed maximum lag are not implemented',
    'source_lines': [170,171,172,173],
    'contract_fields': ['split', 'maturity'],
    'evidence_probe': 'split_guard_coverage',
    'impact': 'The only split chronology helper has no validation label maturities or test_start, so it cannot enforce validation labels mature strictly before test_start-embargo. It also trusts caller max_label_lag_us without comparison to decision-to-maturity lags. This file does not implement the full declared split contract; this is not a claim that an external pipeline was audited or leaked.',
    'required_fix': 'Add explicit full split receipt verification with decision IDs/timestamps, actual observed maturity lag, registered conservative lag, validation maturities and test_start; reject any declared lag below the observed maximum.'})

# Positive control: delayed return-window availability is reflected.
late_exit = joint.with_columns(pl.when(pl.col('timestamp') == d+600*v8.US-v8.BAR_US)
    .then(d+1800*v8.US).otherwise(pl.col(s+'__available_us')).alias(s+'__available_us'))
late_exit_labels = v8.label_table(late_exit, decisions[:1])
probes.append({'id': 'control_late_exit_maturity', 'label_mature_us': int(late_exit_labels['label_mature_us'][0]),
               'expected_label_mature_us': d+1800*v8.US,
               'correct': int(late_exit_labels['label_mature_us'][0]) == d+1800*v8.US})

# Positive OOF guard checks use purely synthetic metadata and predictions.
receipt = v8.OOFPredictionReceipt((10,11),(1000,1100),(1000,1100),(0,1,2),(500,600,650),700,100,'a'*64)
receipt.validate()
try:
    replace(receipt, fit_row_ids=(0,1,10)).validate()
    oof_rejected = False
except ValueError:
    oof_rejected = True
try:
    v8.fit_train_scaler(np.asarray([[1.,2.],[2.,3.]]), [0,1], [0,1], [700,701], 700)
    scaler_rejected = False
except ValueError:
    scaler_rejected = True
probes.append({'id': 'control_oof_scaler', 'fitted_forecast_id_rejected': oof_rejected,
               'future_scaler_source_rejected': scaler_rejected})

end_sha = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in FILES}
if source_sha != end_sha:
    raise RuntimeError('Audited source changed during independent probe')
raw = {'source_sha256': source_sha, 'source_unchanged_during_probe': True, 'probes': probes}
raw_path = STATE / 'probes.json'
raw_path.write_text(json.dumps(raw, indent=2)+'\n')
report = {'report_id': 'V8_LABEL_ADVERSARIAL_AUDIT_20261002_V1',
    'auditor_role': 'independent_adversarial_auditor',
    'created_at_utc': datetime.now(timezone.utc).isoformat(),
    'status': 'FAIL_CONTRACT_IMPLEMENTATION',
    'candidate_status': 'NO_QUALIFIED_CANDIDATE',
    'P1_statistical_economic_gate': 'NOT_EVALUATED',
    'qualification_claim': False,
    'git_base': '40e77fc3bec0257e2a173ca08f12efa02928d839',
    'diff_note': 'All three audited files were untracked new files relative to Git HEAD; their full bytes are the audited new-file diff. Ordinary tracked-file git diff was empty.',
    'audited_sources_sha256': source_sha,
    'source_unchanged_during_probe': True,
    'provided_test_output': {'path': str(xml_path), 'sha256': hashlib.sha256(xml_path.read_bytes()).hexdigest(),
                             'reported_tests': 11, 'reported_failures': 0, 'reported_errors': 0,
                             'interpretation': 'Existing synthetic unit tests omit the confirmed counterexamples; unit PASS is not a P1 gate result.'},
    'scope': {'read_market_data': False, 'read_OOS_metrics': False, 'read_builder_status_or_plan_documents': False,
              'fit_market_model': False, 'consume_locked_holdout': False, 'GPU_used': False,
              'modified_audited_sources': False, 'modified_top_level_docs': False,
              'synthetic_probe_directory': str(STATE),
              'python': '/home/xflops/coin-state/research-env-v6/bin/python',
              'PYTHONPATH': '/mnt/d/codex/coin/src',
              'execution_wrapper': 'scripts/with_task_progress.sh --title V8 独立反例审计 -- env PYTHONPATH=/mnt/d/codex/coin/src /home/xflops/coin-state/research-env-v6/bin/python /home/xflops/coin-state/test-v8-adversarial-20261002-v1/probe.py',
              'resource_policy': 'shared bounded.sh 5,000,000,000-byte RAM; swap0; GPU0'},
    'evidence': {'probe_script': str(STATE/'probe.py'), 'probe_output': str(raw_path),
                 'probe_output_sha256': hashlib.sha256(raw_path.read_bytes()).hexdigest(),
                 'probes': probes},
    'findings': findings,
    'blocker_ids': [f['id'] for f in findings if f['priority']=='P1'],
    'decision': 'Do not accept this implementation as complete LABEL_CONTRACT_V8 compliance until the confirmed guard/maturity defects and full split receipt gap are fixed and independently retested. Keep P1 screening/economic/statistical status NOT_EVALUATED and candidate status NO_QUALIFIED_CANDIDATE.'}
report_path = ROOT/'reports/fast_research/V8_LABEL_ADVERSARIAL_AUDIT_20261002_V1.json'
if report_path.exists():
    raise RuntimeError('Refusing to overwrite prior audit report')
report_path.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps({'report': str(report_path), 'status': report['status'], 'findings': [f['id'] for f in findings],
                  'blockers': report['blocker_ids'], 'source_unchanged': True}))