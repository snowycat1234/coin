"""Independent SOURCE-ONLY gate tests; every late source/finance hook is forbidden.

Authorization-envelope tests explicitly mock preparation validation. They do not
certify real annual source preparation or confer any historical authority.
"""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from generated_helpers import f
import forecast_entry as e
import forecast_historical as historical
import run_forecast as runner


def encoded(value):
    return e._canonical(value)


def fake_preparation():
    # In-memory envelope only. No annual artifacts, providers or actual GOs.
    return dict(ordered_cells=list(e.tranche_cells()), code_identity={'GENERATED_ONLY_SENTINEL': '1' * 64},
        policy_identity='2' * 64, artifacts={}, years={}, cells={},
        preserved_evidence_pins={'GENERATED_OLD_EVIDENCE_NOT_AUTHORITY': 'a' * 64})


def review_bytes(preparation_raw, prep):
    return encoded(dict(schema=e.REVIEW_SCHEMA, status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        **e._authorization_common(preparation_raw, prep), **dict.fromkeys(e.REVIEW_FLAGS, True),
        actual_2023_2024_accounts_constructed=0, actual_2023_2024_financial_runs=0,
        historical_market_minutes_advanced=0, publication_actions=0, locked_source_reads=0))


def go_bytes(preparation_raw, prep, review):
    return encoded(dict(schema=e.GO_SCHEMA, action=e.ACTION,
        **e._authorization_common(preparation_raw, prep), tranche=e.FIRST_TRANCHE,
        permitted_cells=list(e.tranche_cells()), requested_worker_count=2, worker_CPUs=[2, 3],
        independent_review_SHA256=e._sha(review)))


class EntryEnvelopeBoundaries(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.prep = fake_preparation(); self.raw = encoded(self.prep)
        self.real_preparation_validator = e._validate_preparation
        self.review = review_bytes(self.raw, self.prep)
        self.go = go_bytes(self.raw, self.prep, self.review)
        self.mock_preparation = self.stack.enter_context(patch.object(e, '_validate_preparation',
                                                     return_value=self.prep))
        self.forbidden = []
        for name in ('_year_projection', '_load_annual_artifacts', '_annual'):
            blocked = Mock(side_effect=AssertionError('FORBIDDEN_REAL_ANNUAL_SOURCE_OR_PROVIDER:' + name))
            self.stack.enter_context(patch.dict(e.G, {name: blocked}))
            self.forbidden.append(blocked)
        for target, name in ((historical.HistoricalForecastRiskAccount, '__init__'),
                (f.ForecastRiskAccount, '__init__'),
                (f.V2.ENGINE.USDTLinearPerpetualAccount, '__init__'),
                (subprocess, 'Popen'), (subprocess, 'run')):
            self.forbidden.append(self.stack.enter_context(patch.object(target, name,
                                  side_effect=AssertionError('FORBIDDEN_FINANCE_OR_PROCESS:' + name))))

    def tearDown(self):
        for blocked in self.forbidden:
            blocked.assert_not_called()

    def validate(self, value=None, *, digest=None, cell=None):
        value = self.go if value is None else value
        return e.validate_root_go(self.raw, value, e._sha(value) if digest is None else digest,
                                 cell_id=cell or e.tranche_cells()[0])

    def test_exact_four_ordered_new_mid_cells_and_controls_only_metadata(self):
        expected = ('2023_STATIC50_MID_CAUSAL_FORECAST', '2023_VOL_MANAGED_HOLD_MID_CAUSAL_FORECAST',
                    '2024_STATIC50_MID_CAUSAL_FORECAST', '2024_VOL_MANAGED_HOLD_MID_CAUSAL_FORECAST')
        self.assertEqual(e.tranche_cells(), expected)
        manifest = e.frozen_manifest()
        self.assertEqual(manifest['new_cell_count'], 4)
        self.assertTrue(manifest['source_generated_only_until_exact_new_root_GO'])
        self.assertFalse(manifest['financial_policy_changes_allowed'])
        refs = e.control_references()
        self.assertEqual([r['cell_id'] for r in refs['controls']], [c['control_id'] for c in manifest['cells']])
        self.assertTrue(all(r['rerun_authorized'] is False for r in refs['controls']))
        self.assertEqual(sha256((e.HERE / e.CONTROL_NAME).read_bytes()).hexdigest(),
                         '3b61ea88765455246acc7aa5393b7256cb915829737985e542c835579f207b79')
        for bad in ('2023_STATIC50_MID', '2024_STATIC50_MID', '2023_H090_MID_CAUSAL_FORECAST',
                    '2025_STATIC50_MID_CAUSAL_FORECAST', '2024_STATIC50_LOW_CAUSAL_FORECAST'):
            with self.assertRaises(ValueError):
                e.cell_descriptor(bad)

    def test_original_mid_budget_and_all_resource_limits_explicitly_bound(self):
        limits = e.frozen_manifest()['resource_design']
        expected = dict(maximum_live_workers=2, threads_per_worker=1,
                        per_case_CPU_seconds=600, per_case_wall_seconds=600,
                        per_case_RSS_stop_bytes=2_000_000_000, per_case_AS_bytes=4_000_000_000,
                        per_case_output_bytes=250_000_000, aggregate_live_worker_RSS_stop_bytes=3_500_000_000)
        for key, value in expected.items():
            self.assertEqual(limits[key], value)
            self.assertEqual(e.RESOURCE_LIMITS[key], value)
        policy = e._policy({'GENERATED_ONLY': '1' * 64})
        self.assertEqual(policy['original_forecast_budget'], .1)
        self.assertFalse(policy['automatic_topup'])
        self.assertFalse(policy['existing_controls_rerun_authorized'])
        self.assertFalse(policy['old_GO_is_new_authority'])
        self.assertFalse(policy['publication_authorized'])
        self.assertFalse(policy['candidate_threshold_or_performance_selection_allowed'])

    def test_mocked_preparation_envelope_only_accepts_entire_ordered_four(self):
        self.assertIs(self.validate(), self.prep)
        original = json.loads(self.go)
        cells = original['permitted_cells']
        for bad in ([], cells[:1], cells[::-1], cells[1:] + cells[:1], cells + [cells[0]]):
            value = deepcopy(original); value['permitted_cells'] = bad
            with self.assertRaises(ValueError):
                self.validate(encoded(value))

    def test_missing_wrong_bytes_hash_old_evidence_and_old_schema_fail_closed(self):
        for value in (None, True, {}, 'not bytes'):
            with self.assertRaises(ValueError):
                e.validate_root_go(self.raw, value, '0' * 64, cell_id=e.tranche_cells()[0])
        with self.assertRaises(ValueError):
            self.validate(digest='0' * 64)
        original = json.loads(self.go)
        for key, value in (('schema', e.BASE.GO_SCHEMA), ('action', 'INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION'),
                           ('old_GO_is_new_authority', True), ('source_scope', e.BASE.SOURCE_SCOPE)):
            wrong = deepcopy(original); wrong[key] = value
            if key == 'old_GO_is_new_authority':
                wrong['preserved_old_root_GO_is_new_authority'] = True
            with self.assertRaises(ValueError):
                self.validate(encoded(wrong))
        old = e._sha(self.go)
        self.prep['preserved_evidence_pins']['GENERATED_ONLY_OLD_GO_HASH'] = old
        with self.assertRaises(ValueError):
            self.validate()

    def test_cpu_count_bool_duplicate_and_resource_changes_are_rejected(self):
        original = json.loads(self.go)
        for workers, cpus in ((True, [2]), (0, []), (3, [1, 2, 3]), (2, [2, 2]),
                              (2, [True, 3]), (2, [-1, 3]), (1, [2, 3])):
            bad = deepcopy(original); bad.update(requested_worker_count=workers, worker_CPUs=cpus)
            with self.assertRaises(ValueError):
                self.validate(encoded(bad))
        for key in e.RESOURCE_LIMITS:
            bad = deepcopy(original); bad['resource_limits'][key] = None
            with self.assertRaises(ValueError):
                self.validate(encoded(bad))

    def test_every_independent_review_flag_and_zero_history_field_required(self):
        self.assertEqual(e._validate_independent_review(self.raw, self.prep, self.review,
                          e._sha(self.review), self.go)['schema'], e.REVIEW_SCHEMA)
        original = json.loads(self.review)
        for key in e.REVIEW_FLAGS:
            for replacement in (False, 1, None):
                bad = deepcopy(original); bad[key] = replacement
                body = encoded(bad); go = json.loads(self.go); go['independent_review_SHA256'] = e._sha(body)
                with self.assertRaises(ValueError):
                    e._validate_independent_review(self.raw, self.prep, body, e._sha(body), encoded(go))
        for key in ('actual_2023_2024_accounts_constructed', 'actual_2023_2024_financial_runs',
                    'historical_market_minutes_advanced', 'publication_actions', 'locked_source_reads'):
            bad = deepcopy(original); bad[key] = 1
            body = encoded(bad); go = json.loads(self.go); go['independent_review_SHA256'] = e._sha(body)
            with self.assertRaises(ValueError):
                e._validate_independent_review(self.raw, self.prep, body, e._sha(body), encoded(go))

    def test_missing_or_mismatched_review_blocks_before_late_input_and_callback(self):
        source_read = Mock(side_effect=AssertionError('LATE_INPUT_SOURCE_MUST_NOT_RUN'))
        callback = Mock(side_effect=AssertionError('HISTORICAL_CALLBACK_MUST_NOT_RUN'))
        with patch.dict(e.G, {'_source_roots': lambda _: {2023: Path('/GENERATED_ONLY_NO_SOURCE'),
                                                        2024: Path('/GENERATED_ONLY_NO_SOURCE')},
                            '_ordinary': lambda path: self.raw,
                            'validate_case_inputs': source_read}):
            for review, digest in ((None, None), (self.review, '0' * 64), (b'{}', e._sha(b'{}'))):
                with self.assertRaises(ValueError):
                    e.make_case({}, '/GENERATED_ONLY_PREPARATION', self.go, e._sha(self.go),
                        cell_id=e.tranche_cells()[0], review_raw=review,
                        expected_review_sha256=digest, constructor_callback=callback)
        source_read.assert_not_called(); callback.assert_not_called()

    def test_invalid_template_and_in_memory_fake_scope_never_admit_history(self):
        template = e.invalid_go_template(self.raw)
        self.assertEqual(template['action'], 'INVALID_TEMPLATE_NOT_ROOT_AUTHORIZATION')
        with self.assertRaises(ValueError):
            self.validate(encoded(template))
        with patch.object(f.V2.ENGINE.USDTLinearPerpetualAccount, '__init__',
                          side_effect=AssertionError('NATIVE_FRESH_GENESIS_FORBIDDEN')) as native:
            with self.assertRaisesRegex(ValueError, 'EXACT_SEALED_FOUR_CELL'):
                historical.construct_historical_case({}, (), (), (), historical_scope=object())
            native.assert_not_called()

    def test_real_preparation_parser_rejects_old_missing_duplicate_scope_without_source_reads(self):
        # Exercise the real parser and required top-level boundary while
        # explicitly replacing old evidence reads with an in-memory sentinel.
        with patch.dict(e.G, {'preserved_evidence_identity': lambda: self.prep['preserved_evidence_pins']}):
            for raw in (b'{}', encoded({'schema': e.BASE.PREPARATION_SCHEMA}),
                        b'{"schema":"first","schema":"duplicate"}', b'[]'):
                with self.subTest(raw=raw), self.assertRaises(ValueError):
                    self.real_preparation_validator(raw)


class RunnerFailClosedBoundaries(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.temp = tempfile.TemporaryDirectory(prefix='generated_forecast_runner_gate_')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.original_pool = runner.run_pool
        self.original_lease = runner.controller_lease
        self.forbidden = []
        for target, name in ((runner, 'claim_launch'), (runner, 'controller_lease'),
                (runner, 'run_pool'), (subprocess, 'Popen'), (subprocess, 'run'),
                (e, 'make_case'), (historical, 'construct_historical_case'),
                (historical.HistoricalForecastRiskAccount, '__init__'),
                (f.V2.ENGINE.USDTLinearPerpetualAccount, '__init__')):
            self.forbidden.append(self.stack.enter_context(patch.object(target, name,
                                    side_effect=AssertionError('FORBIDDEN_ACTUAL_LAUNCH_OR_FINANCE:' + name))))

    def tearDown(self):
        for blocked in self.forbidden:
            blocked.assert_not_called()

    def test_exact_immutable_pool_code_and_shared_new_lease_globals(self):
        self.assertIs(self.original_pool.__code__, runner.R.run_pool.__code__)
        self.assertIs(runner._POOL_GLOBALS['_run_pool'].__code__, runner.R._run_pool.__code__)
        self.assertIs(self.original_pool.__globals__, runner._POOL_GLOBALS)
        self.assertIs(runner._POOL_GLOBALS['_run_pool'].__globals__, runner._POOL_GLOBALS)
        self.assertIs(self.original_lease.__wrapped__.__globals__, runner._POOL_GLOBALS)
        self.assertEqual(runner._POOL_GLOBALS['MANIFEST_SHA256'], e.MANIFEST_SHA256)
        self.assertEqual(runner.MANIFEST_SHA256, e.MANIFEST_SHA256)
        self.assertEqual(sha256((f.FROZEN / 'run_expansion.py').read_bytes()).hexdigest(),
                         f.PINS['run_expansion.py'])

    def test_preflight_distinct_cpus_memory_and_cpu_quota_fallback_without_processes(self):
        host = dict(allowed_CPUs=[2, 3], MemAvailable_bytes=8_000_000_000, cgroup_observations={})
        self.assertEqual(runner.choose_worker_count(2, [2, 3], host), 2)
        low = deepcopy(host); low['MemAvailable_bytes'] = 3_000_000_000
        self.assertEqual(runner.choose_worker_count(2, [2, 3], low), 1)
        low['MemAvailable_bytes'] = 2_000_000_000
        with self.assertRaisesRegex(RuntimeError, 'MEMORY'):
            runner.choose_worker_count(2, [2, 3], low)
        limited = deepcopy(host); limited['cgroup_observations']['/sys/fs/cgroup/cpu.max'] = '100000 100000'
        self.assertEqual(runner.choose_worker_count(2, [2, 3], limited), 1)
        limited['cgroup_observations'] = {'/sys/fs/cgroup/memory.max': '4000000000',
                                        '/sys/fs/cgroup/memory.current': '2000000000'}
        with self.assertRaisesRegex(RuntimeError, 'MEMORY'):
            runner.choose_worker_count(2, [2, 3], limited)
        for cpus in ([2, 2], [2, 4], [True, 3]):
            with self.assertRaises(ValueError):
                runner.choose_worker_count(2, cpus, host)

    def test_direct_case_missing_worker_claim_stops_before_financial_construction(self):
        args = SimpleNamespace(cpu=3)
        with patch.object(runner, 'apply_limits') as limits, \
             patch.object(runner, 'validate_scope', return_value=(b'{}', b'GENERATED_GO', b'GENERATED_REVIEW')), \
             patch.object(runner, 'validate_worker_claim', side_effect=ValueError('GENERATED_MISSING_CLAIM')):
            with self.assertRaisesRegex(ValueError, 'MISSING_CLAIM'):
                runner.case(args)
            limits.assert_called_once_with(3)

    def test_absent_canonical_claim_cannot_admit_mock_worker(self):
        args = SimpleNamespace(cell_id=e.tranche_cells()[0], cpu=3,
                               case_output=str(self.directory / 'case'))
        with self.assertRaisesRegex(ValueError, 'CANONICAL_PRELAUNCH_CLAIM'):
            runner.validate_worker_claim(args, preparation_raw=b'{}', go_raw=b'GENERATED_GO',
                                         review_raw=b'GENERATED_REVIEW', registry_root=self.directory)

    def test_existing_output_refused_before_reading_go_or_any_launch_side_effect(self):
        args = SimpleNamespace(output=str(self.directory))
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('NO_GO_READ')) as read:
            with self.assertRaisesRegex(ValueError, 'EXISTING_OUTPUT'):
                runner.controller(args)
            read.assert_not_called()

    def test_bad_external_hash_stops_before_preflight_or_any_launch_side_effect(self):
        args = SimpleNamespace(output=str(self.directory / 'new'), go='GENERATED_NOT_REAL_GO', go_sha='0' * 64)
        with patch.object(Path, 'read_bytes', return_value=b'GENERATED_NOT_AUTHORITY'), \
             patch.object(runner, 'choose_worker_count', side_effect=AssertionError('NO_PREFLIGHT')) as preflight:
            with self.assertRaisesRegex(ValueError, 'EXACT_EXTERNAL_GO_BYTES'):
                runner.controller(args)
            preflight.assert_not_called()

    def test_review_failure_cannot_create_claim_lease_process_output_or_read_source(self):
        raw = encoded(dict(requested_worker_count=2, worker_CPUs=[2, 3]))
        args = SimpleNamespace(output=str(self.directory / 'new'), go='GENERATED_NOT_REAL_GO', go_sha=e._sha(raw))
        with patch.object(Path, 'read_bytes', return_value=raw), \
             patch.object(runner, 'choose_worker_count', return_value=2), \
             patch.object(runner, 'host_observation', return_value={}), \
             patch.object(runner.R, 'confine_existing_threads') as affinity, \
             patch.object(runner, 'validate_scope', side_effect=ValueError('GENERATED_REVIEW_REJECTED')), \
             patch.dict(os.environ, {}, clear=False):
            with self.assertRaisesRegex(ValueError, 'REVIEW_REJECTED'):
                runner.controller(args)
            affinity.assert_called_once_with([2, 3])
        self.assertFalse(Path(args.output).exists())

    def test_complete_new_source_identity_includes_entry_historical_runner_manifest_controls(self):
        identity = e.code_identity()
        for name in ('forecast_monitor.py', 'forecast_entry.py', 'forecast_historical.py',
                     'run_forecast.py', e.MANIFEST_NAME, e.CONTROL_NAME):
            key = e.HERE.name + '/' + name
            self.assertIn(key, identity)
            self.assertEqual(identity[key], sha256((e.HERE / name).read_bytes()).hexdigest())


class SavedGeneratedPolicyBoundaries(unittest.TestCase):
    """Read only our generated evidence, never a historical account or result."""
    @classmethod
    def setUpClass(cls):
        directory = Path(__file__).resolve().parent
        cls.audit = json.loads((directory / 'DISTINCT_ACTIVE_AUDIT.json').read_bytes())
        cls.result = json.loads((directory / 'DISTINCT_ACTIVE_RESULT.json').read_bytes())

    def test_exact_generated_paid_policy_evidence_is_accepted_without_account_construction(self):
        self.assertTrue(runner.validate_policy_evidence(self.audit, self.result, historical=False))

    def test_resealed_nonfinite_negative_or_wrong_projection_journal_is_rejected(self):
        for field, bad_value in (('sigma', float('nan')), ('sigma', float('inf')), ('sigma', -.1),
                                  ('alpha', float('nan')), ('alpha', float('inf')), ('alpha', 0),
                                  ('current_variance', float('inf')), ('current_variance', -1.),
                                  ('projected_variance', float('-inf')), ('projected_variance', -1.)):
            with self.subTest(field=field, value=bad_value):
                audit, result = deepcopy(self.audit), deepcopy(self.result)
                row = next(r for r in audit['forecast_journal'] if r['kind'] == 'COHORT_CREATED')
                row[field] = bad_value
                result['forecast_risk_monitor']['journal'] = deepcopy(audit['forecast_journal'])
                with self.assertRaises(ValueError):
                    runner.validate_policy_evidence(audit, result, historical=False)

    def test_transfer_topup_rerisk_or_atomic_metadata_cannot_be_relabelled_safe(self):
        for field in ('automatic_topup', 'no_autonomous_rerisking', 'partial_fills_atomic'):
            audit, result = deepcopy(self.audit), deepcopy(self.result)
            result['forecast_risk_monitor'][field] = not result['forecast_risk_monitor'][field]
            with self.assertRaises(ValueError):
                runner.validate_policy_evidence(audit, result, historical=False)
        audit, result = deepcopy(self.audit), deepcopy(self.result)
        audit['transfer_journal'] = [{'GENERATED_FORGED_TRANSFER': '1'}]
        result['continuation_economic_report']['transfers'] = deepcopy(audit['transfer_journal'])
        with self.assertRaises(ValueError):
            runner.validate_policy_evidence(audit, result, historical=False)


if __name__ == '__main__':
    unittest.main()
