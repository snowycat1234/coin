"""Actual source-only projection plus generated GO/review metadata boundaries.

Every positive construction test supplies a recording callback. NO historical
account or market advance is permitted. Fixture GO bytes stay in memory only.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import guard50_exit_entry as e
import guard50_exit as d
import run_guard50_exit as runner
from contextlib import ExitStack
from types import SimpleNamespace

SOURCE = e.ROOT / 'native_2024_source_restore_20261015'


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def fixture_review(preparation):
    p = json.loads(preparation)
    value = dict(schema=e.REVIEW_SCHEMA, policy_version=e.POLICY_VERSION, source_scope=e.SOURCE_SCOPE, status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        preparation_SHA256=e._sha(preparation), calendar=[e.START, e.END], config=e.CONFIG,
        cost=e.COST, modes=list(e.MODES), settlement_mode=e.SETTLEMENT_MODE,
        code_identity=p['code_identity'], source_identity=p['source_identity'],
        policy_identity=p['policy_identity'], artifacts=p['artifacts'],
        selected_target_raw_SHA256=p['selected_target_raw_SHA256'],
        input_binding_SHA256=p['input_binding_SHA256'],
        resource_limits=e.RESOURCE_LIMITS, preserved_evidence_pins=e.PRESERVED_EVIDENCE_PINS,
        preserved_old_root_GO_is_new_authority=False,
        B_C_reruns_authorized=False,
        mark_feed_adapter_version=e.a.m.VERSION, mark_quality_guard_version=e.a.q.VERSION,
        original_interpolated_mark_execution_admitted=False,
        coldstart_policy=p['coldstart_policy'],
        generated_native_scheduler_phase_order_passed=True,
        generated_shared_pending_32_corner_passed=True,
        generated_preview_isolation_passed=True, generated_causal_quality_passed=True,
        generated_terminal_taxonomy_passed=True,
        generated_unknown_quality_no_new_exit_passed=True,
        generated_guard50_paid_exit_no_topup_passed=True,
        generated_D_only_source_and_root_GO_gates_passed=True,
        actual_2024_accounts_constructed=0, actual_2024_financial_runs=0,
        historical_market_minutes_advanced=0, publication_actions=0, locked_source_reads=0)
    return raw(value)


def fixture_go(preparation, review, permitted=None):
    p = json.loads(preparation)
    return raw(dict(schema=e.GO_SCHEMA, policy_version=e.POLICY_VERSION, source_scope=e.SOURCE_SCOPE,
        action='RUN_FRESH_GUARD50_EXIT_ONLY_CASE_ONLY',
        preparation_SHA256=e._sha(preparation), calendar=[e.START, e.END], config=e.CONFIG,
        cost=e.COST, settlement_mode=e.SETTLEMENT_MODE, modes=list(e.MODES),
        code_identity=p['code_identity'], policy_identity=p['policy_identity'],
        source_identity=p['source_identity'], artifacts=p['artifacts'],
        selected_target_raw_SHA256=p['selected_target_raw_SHA256'],
        input_binding_SHA256=p['input_binding_SHA256'],
        resource_limits=e.RESOURCE_LIMITS, preserved_evidence_pins=e.PRESERVED_EVIDENCE_PINS,
        preserved_old_root_GO_is_new_authority=False,
        B_C_reruns_authorized=False,
        mark_feed_adapter_version=e.a.m.VERSION, mark_quality_guard_version=e.a.q.VERSION,
        original_interpolated_mark_execution_admitted=False,
        coldstart_policy=p['coldstart_policy'], serial_execution=True,
        automatic_retry_authorized=False, locked_or_holdout_consumed=False,
        other_years_authorized=False, publication_authorized=False,
        fresh_genesis_only=True, halted_snapshot_resume_authorized=False,
        permitted_modes=list(e.MODES) if permitted is None else permitted,
        independent_review_SHA256=e._sha(review)))


class Guard50ExitSourceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='guard50_exit_source_only_')
        cls.directory = Path(cls.temp.name) / 'prepared'
        cls.forbidden = ExitStack()
        cls.finance_mocks = []
        for target, name in ((d.Guard50ExitAccount, '__init__'),
                (d.V2.ContinuationAccount, '__init__'),
                (d.V2.ENGINE.USDTLinearPerpetualAccount, '__init__'),
                (e.a.n, '_construct_case'), (e.a.n, 'runtime'),
                (e.a.g, 'make_account'), (e.a, 'make_annual_case'),
                (e.a, 'validate_root_go')):
            cls.finance_mocks.append(cls.forbidden.enter_context(
                patch.object(target, name, side_effect=AssertionError('SOURCE_ONLY_ZERO_FINANCE_CALLS:'+name))))
        cls.addClassCleanup(cls.forbidden.close)
        # The actual integration/runner code identities are bound, while all
        # account constructors and financial entry points remain prohibited.
        existing = os.environ.get('GUARD50_EXIT_ONLY_PREPARATION')
        if existing:
            # Negative/tamper probes use exact byte copies, never alter the
            # persisted source-only preparation or its original evidence.
            source = Path(existing)
            cls.directory.mkdir()
            for name in (*e.ARTIFACTS, 'PREPARATION.json'):
                (cls.directory / name).write_bytes((source / name).read_bytes())
            cls.prep = e._validate_preparation((cls.directory / 'PREPARATION.json').read_bytes())
            if cls.prep['code_identity'] != e.code_identity():
                raise AssertionError('PERSISTED_PREPARATION_CODE_IDENTITY_CHANGED')
        else:
            with patch.object(e.a.n, '_construct_case', side_effect=AssertionError('NO_ACCOUNT')), \
                    patch.object(e.a.n, 'runtime', side_effect=AssertionError('NO_RUNTIME')), \
                    patch.object(e.a.g, 'make_account', side_effect=AssertionError('NO_GRID_ACCOUNT')), \
                    patch.object(e.a, 'make_annual_case', side_effect=AssertionError('NO_OLD_CONSTRUCTOR')), \
                    patch.object(e.a, 'validate_root_go', side_effect=AssertionError('NO_OLD_OR_FAKE_GO')):
                cls.prep = e.prepare_source_only(SOURCE, cls.directory)
        cls.preparation = (cls.directory / 'PREPARATION.json').read_bytes()
        cls.review = fixture_review(cls.preparation)
        cls.go = fixture_go(cls.preparation, cls.review)

    @classmethod
    def tearDownClass(cls):
        try:
            for mocked in cls.finance_mocks:
                mocked.assert_not_called()
        finally:
            cls.temp.cleanup()

    def validate(self, go=None, mode='GUARD50_EXIT_ONLY'):
        body = self.go if go is None else go
        return e.validate_root_go(self.preparation, body, e._sha(body), policy_variant=mode)

    def test_source_only_preparation_counts_exact_year_modes_and_limits(self):
        p = self.prep
        self.assertEqual(p['calendar'], [1704067200000000, 1735689600000000])
        self.assertEqual((p['days'], p['required_minutes']), (366, 527040))
        self.assertEqual(p['modes'], ['GUARD50_EXIT_ONLY'])
        self.assertEqual(p['mode_labels'], {'D': 'GUARD50_EXIT_ONLY'})
        self.assertEqual((p['configs'], p['cost'], p['settlement_mode']),
            (['STATIC50_MID'], 'BASE27', 'CONDITIONAL_COLLATERAL_FORFEITURE'))
        self.assertEqual(p['resource_limits'], dict(per_case_wall_seconds=600, CPU_threads=1,
            RSS_stop_bytes=2000000000, AS_bytes=4000000000, output_bytes=250000000, maximum_cases=1))
        self.assertEqual(p['source_counts'], dict(months=12, decisions=366, source_rows=2825,
            daily_records=1830, funding_events=5490, required_minutes=527040,
            actual_close_export_rows=566, actual_close_export_cells=2830,
            completed_actual_closes_per_decision=200, derived_mark_cells=10))
        self.assertEqual((p['accounts_created'], p['accounts_advanced'],
            p['historical_market_minutes_advanced'], p['financial_runs'], p['publication_actions']), (0, 0, 0, 0, 0))
        for key in ('annual_returns_computed', 'outcomes_inspected', 'locked_or_holdout_consumed',
                'other_years_authorized', 'historical_admission', 'preserved_old_root_GO_is_new_authority'):
            self.assertIs(p[key], False)
        self.assertEqual(p['policy_identity'], e._json_sha(p['policy']))

    def test_D_policy_schema_scope_and_newpath_code_identity_are_distinct(self):
        self.assertEqual(e.POLICY_VERSION, 'GUARD50_EXIT_ONLY_FULL2024_STATIC50_MID_V1')
        self.assertEqual(e.PREPARATION_SCHEMA, 'SOURCE_TARGET_ONLY_GUARD50_EXIT_ONLY_FULL2024_STATIC50_MID_V1')
        self.assertEqual(e.REVIEW_SCHEMA, 'INDEPENDENT_GUARD50_EXIT_ONLY_SOURCE_GENERATED_REVIEW_V1')
        self.assertEqual(e.GO_SCHEMA, 'ROOT_GO_GUARD50_EXIT_ONLY_FULL2024_STATIC50_MID_V1')
        self.assertEqual(e.SOURCE_SCOPE, 'ROOT_ADMITTED_FRESH_FINITE_FULL2024_GUARD50_EXIT_ONLY_CAUSAL_MARKS_V1')
        self.assertEqual(self.prep['policy_version'], e.POLICY_VERSION)
        self.assertEqual(self.prep['source_scope'], e.SOURCE_SCOPE)
        self.assertEqual(self.prep['input_binding']['schema'], 'ENTRY_OWNED_EXACT_FULL2024_GUARD50_EXIT_ONLY_INPUT_BINDING_V1')
        policy = self.prep['policy']
        self.assertEqual(policy['mark_quality_exit_policy_version'], 'UNKNOWN_MARK_NO_NEW_EXIT_V2')
        self.assertIs(policy['unknown_or_stale_mark_quality_blocks_topup'], True)
        self.assertIs(policy['unknown_or_stale_mark_quality_blocks_new_risk_increase'], True)
        self.assertIs(policy['unknown_or_stale_quality_itself_creates_new_warning_exit'], False)
        self.assertIs(policy['legitimate_preexisting_pending_exit_preserved'], True)
        self.assertIs(policy['ordinary_new_strategy_reductions_and_native_exits_preserved'], True)
        for name in ('guard50_exit_entry.py', 'guard50_exit.py', 'run_guard50_exit.py'):
            self.assertIn('bounded_native_continuation_guard50_exit_20261015/' + name, self.prep['code_identity'])
        for name, digest in e.FROZEN_V2_CODE_PINS.items():
            self.assertEqual(self.prep['code_identity']['bounded_native_continuation_v2_20261015/' + name], digest)
            self.assertEqual(d.BASE_PINS[name], digest)

    def test_V2_B_C_preparation_review_and_go_cannot_authorize_D(self):
        prep = deepcopy(self.prep)
        prep['schema'] = 'SOURCE_TARGET_ONLY_BOUNDED_NATIVE_CONTINUATION_FULL2024_STATIC50_MID_V2'
        with self.assertRaises(ValueError):
            e._validate_preparation(raw(prep))
        go = json.loads(self.go)
        go['schema'] = 'ROOT_GO_BOUNDED_NATIVE_CONTINUATION_FULL2024_STATIC50_MID_V2'
        with self.assertRaises(ValueError):
            self.validate(raw(go))
        review = json.loads(self.review)
        review['schema'] = 'INDEPENDENT_BOUNDED_NATIVE_CONTINUATION_SOURCE_GENERATED_REVIEW_V2'
        review = raw(review)
        with self.assertRaises(ValueError):
            e._validate_independent_review(self.preparation, self.prep, review,
                e._sha(review), fixture_go(self.preparation, review))

    def test_exact_original_artifacts_and_source_quality_pins_are_preserved(self):
        annual_raw, annual = e._frozen_preparation()
        self.assertEqual((self.directory / 'ANNUAL_SOURCE_PREPARATION.json').read_bytes(), annual_raw)
        for name in e.a.ARTIFACTS:
            self.assertEqual(self.prep['artifacts'][name], annual['artifacts'][name])
            self.assertEqual((self.directory / name).read_bytes(), (e.ANNUAL_PREPARATION / name).read_bytes())
        self.assertEqual(self.prep['source_files'], annual['source_files'])
        self.assertEqual(self.prep['original200_quality'], annual['original200_quality'])
        self.assertEqual(self.prep['frozen_annual_code_identity'], e.a.code_identity())
        self.assertEqual(self.prep['preserved_evidence_pins'], e.preserved_evidence_identity())
        with np.load(self.directory / 'TARGETS.npz', allow_pickle=False) as archive:
            self.assertEqual(archive[e.CONFIG].shape, (366, 5))
            self.assertEqual(e._sha(archive[e.CONFIG].tobytes()), self.prep['selected_target_raw_SHA256'])
            self.assertEqual(archive['decision_us'].tobytes(),
                np.arange(e.START, e.END, e.a.g.DAY, dtype=np.int64).tobytes())

    def test_exclusive_output_directory_is_never_overwritten(self):
        with self.assertRaisesRegex(ValueError, 'EXCLUSIVE_NEW'):
            e.prepare_source_only(SOURCE, self.directory)

    def test_exact_new_go_can_admit_each_only_fixed_mode(self):
        for mode in e.MODES:
            self.assertEqual(self.validate(mode=mode), self.prep)
        only_d = fixture_go(self.preparation, self.review, [e.MODES[0]])
        self.validate(only_d)
        for old_mode in ('CONTINUE_ONLY', 'TOPUP_THEN_CONTINUE'):
            with self.assertRaises(ValueError):
                self.validate(only_d, mode=old_mode)
        for mode in ('NATIVE_STOP_REFERENCE', 'D', 'B', '', None):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.validate(mode=mode)

    def test_missing_nonbytes_wrong_hash_duplicate_json_keys_fail(self):
        for body, digest in ((None, None), (self.go.decode(), e._sha(self.go)),
                (self.go, '0' * 64), (self.go, e._sha(self.go).upper())):
            with self.assertRaises(ValueError):
                e.validate_root_go(self.preparation, body, digest, policy_variant=e.MODES[0])
        for body in (b'[]', b'{', b'{"schema":1,"schema":2}', b'{"schema":NaN}'):
            with self.assertRaises(ValueError):
                self.validate(body)

    def test_old_go_is_not_new_continuation_authority(self):
        for name in e.PRESERVED_EVIDENCE_PINS:
            if 'root_go_2024' in name:
                with self.assertRaises(ValueError):
                    self.validate((e.ROOT / name).read_bytes())

    def test_every_go_identity_scope_and_safety_field_is_exact(self):
        original = json.loads(self.go)
        changes = dict(schema='OLD_SCHEMA', policy_version='V1', source_scope='V1', action='RUN_ANYTHING', preparation_SHA256='0' * 64,
            calendar=[e.START, e.END - e.a.g.DAY], config='STATIC50_LOW', cost='STRESS43',
            modes=['NATIVE_STOP_REFERENCE', *e.MODES], settlement_mode='UNKNOWN_UNSETTLED',
            code_identity={}, source_identity='0' * 64, policy_identity='0' * 64, artifacts={},
            selected_target_raw_SHA256='0' * 64, input_binding_SHA256='0' * 64,
            resource_limits={**e.RESOURCE_LIMITS, 'maximum_cases': 3}, preserved_evidence_pins={},
            preserved_old_root_GO_is_new_authority=True, mark_feed_adapter_version='ORIGINAL',
            mark_quality_guard_version='NONE', original_interpolated_mark_execution_admitted=True,
            coldstart_policy={'available_prior_source_used': True}, serial_execution=False,
            automatic_retry_authorized=True, locked_or_holdout_consumed=True,
            other_years_authorized=True, publication_authorized=True, fresh_genesis_only=False,
            halted_snapshot_resume_authorized=True, independent_review_SHA256='x' * 64)
        for key, value in changes.items():
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(raw({**original, key: value}))
        for key in original:
            bad = deepcopy(original)
            del bad[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                self.validate(raw(bad))

    def test_malformed_permitted_mode_types_duplicates_empty_and_extra_fail(self):
        original = json.loads(self.go)
        for permitted in ([], list(e.MODES) + ['D'], [e.MODES[0], e.MODES[0]],
                [None], [1], [[e.MODES[0]]], {'B': e.MODES[0]}, e.MODES[0]):
            with self.subTest(permitted=permitted), self.assertRaises(ValueError):
                self.validate(raw({**original, 'permitted_modes': permitted}))

    def test_go_true_and_integer_lookalikes_do_not_pass_exact_fields(self):
        original = json.loads(self.go)
        for key, value in (('serial_execution', 1), ('automatic_retry_authorized', 0),
                ('fresh_genesis_only', 1), ('other_years_authorized', 0)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(raw({**original, key: value}))

    def test_every_review_field_is_required_and_bound_to_new_go(self):
        original = json.loads(self.review)
        for key in original:
            bad = deepcopy(original)
            del bad[key]
            body = raw(bad)
            go = fixture_go(self.preparation, body)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                e._validate_independent_review(self.preparation, self.prep, body, e._sha(body), go)
        for key, value in (('generated_shared_pending_32_corner_passed', 1),
                ('generated_guard50_paid_exit_no_topup_passed', False),
                ('generated_D_only_source_and_root_GO_gates_passed', 1),
                ('generated_unknown_quality_no_new_exit_passed', False),
                ('generated_unknown_quality_no_new_exit_passed', 1),
                ('policy_version', 'V1'), ('source_scope', 'V1'),
                ('actual_2024_accounts_constructed', False), ('actual_2024_financial_runs', 1),
                ('code_identity', {}), ('policy_identity', '0' * 64)):
            body = raw({**original, key: value})
            go = fixture_go(self.preparation, body)
            with self.subTest(key=key), self.assertRaises(ValueError):
                e._validate_independent_review(self.preparation, self.prep, body, e._sha(body), go)
        with self.assertRaises(ValueError):
            e._validate_independent_review(self.preparation, self.prep, self.review, '0' * 64, self.go)

    def test_missing_review_blocks_callback_before_source_or_account(self):
        reached = []
        with patch.object(e, 'validate_annual_inputs', side_effect=AssertionError('NO_LATE_SOURCE')):
            with self.assertRaises(ValueError):
                e.make_annual_case(SOURCE, self.directory, self.go, e._sha(self.go),
                    policy_variant=e.MODES[0], constructor_callback=lambda **values: reached.append(values))
        self.assertEqual(reached, [])

    def test_callback_receives_immutable_exact_scope_no_fake_scope_or_clock_advance(self):
        reached = []
        with patch.object(e.a.n, '_construct_case', side_effect=AssertionError('NO_OLD_ACCOUNT')), \
                patch.object(e.a.n, 'runtime', side_effect=AssertionError('NO_FINANCIAL_RUNTIME')), \
                patch.object(e.a, 'make_annual_case', side_effect=AssertionError('NO_OLD_ENTRY')), \
                patch.object(e.a, 'validate_root_go', side_effect=AssertionError('NO_FAKE_GO')):
            result = e.make_annual_case(SOURCE, self.directory, self.go, e._sha(self.go),
                policy_variant=e.MODES[0], review_raw=self.review,
                expected_review_sha256=e._sha(self.review),
                constructor_callback=lambda **values: reached.append(values) or 'RECORDED_NO_ACCOUNT')
        self.assertEqual(result, 'RECORDED_NO_ACCOUNT')
        values = reached[0]
        self.assertEqual(set(values), {'scope', 'preparation', 'window', 'source_rows',
            'decisions', 'targets', 'captured'})
        self.assertEqual((len(values['source_rows']), len(values['decisions']), values['targets'].shape),
            (2825, 366, (366, 5)))
        self.assertEqual((len(values['window']['daily']), len(values['window']['events'])), (1830, 5490))
        self.assertFalse(values['targets'].flags.writeable)
        self.assertFalse(values['decisions'].flags.writeable)
        self.assertNotIn('generated_scope', values)
        self.assertNotIn('initial_prior', values['window'])
        self.assertNotIn('previous_quote', values['window'])
        scope = values['scope']
        self.assertIsInstance(scope, e.HistoricalExecutionScope)
        self.assertTrue(scope.validate_current())
        self.assertTrue(scope.validate_inputs(values['window'], values['source_rows'],
            values['decisions'], values['targets']))
        for key in ('window', 'source_rows', 'decisions', 'targets'):
            swapped = dict(values)
            swapped[key] = dict(values[key]) if key == 'window' else (
                tuple(dict(row) for row in values[key]) if key == 'source_rows' else values[key].copy())
            with self.subTest(swapped=key), self.assertRaises(ValueError):
                scope.validate_inputs(swapped['window'], swapped['source_rows'],
                    swapped['decisions'], swapped['targets'])
        for array in (values['decisions'], values['targets']):
            array.setflags(write=True)
            try:
                with self.assertRaises(ValueError):
                    scope.validate_inputs(values['window'], values['source_rows'],
                        values['decisions'], values['targets'])
            finally:
                array.setflags(write=False)
        array = values['targets']
        original = float(array[0, 0])
        array.setflags(write=True)
        array[0, 0] = np.nextafter(original, np.inf)
        array.setflags(write=False)
        try:
            with self.assertRaises(ValueError):
                scope.validate_inputs(values['window'], values['source_rows'],
                    values['decisions'], values['targets'])
        finally:
            array.setflags(write=True)
            array[0, 0] = original
            array.setflags(write=False)
        daily = values['window']['daily']
        close_index = daily.columns.index('close')
        original_close = daily['close'].clone()
        daily.replace_column(close_index, (original_close + 1).alias('close'))
        try:
            with self.assertRaises(ValueError):
                scope.validate_inputs(values['window'], values['source_rows'],
                    values['decisions'], values['targets'])
        finally:
            daily.replace_column(close_index, original_close)
        with self.assertRaises(FrozenInstanceError):
            values['window']['minute_blocks'].months = ()
        with self.assertRaises(TypeError):
            values['window']['events'][0]['raw_rate'] = 100
        with self.assertRaises(TypeError):
            values['window']['minute_blocks'] = lambda: iter(())
        self.assertFalse(scope.metadata['generated_fixture_scope_used'])
        self.assertEqual(scope.metadata['settlement_mode'], e.SETTLEMENT_MODE)
        self.assertEqual(scope.source_scope, e.SOURCE_SCOPE)
        self.assertEqual(scope.root_GO_SHA256, e._sha(self.go))
        self.assertIs(deepcopy(scope), scope)
        with self.assertRaises(ValueError):
            replace(scope, _source_pins=()).validate_current()
        with self.assertRaises(FrozenInstanceError):
            scope.policy_variant = 'CONTINUE_ONLY'
        with self.assertRaises(TypeError):
            scope.metadata['policy_variant'] = 'CONTINUE_ONLY'
        with self.assertRaises(ValueError):
            replace(scope, _seal=object())
        with patch.object(e, 'code_identity', return_value={}):
            with self.assertRaises(ValueError):
                scope.validate_current()
        body = (self.directory / 'PREPARATION.json').read_bytes()
        try:
            (self.directory / 'PREPARATION.json').write_bytes(body + b' ')
            with self.assertRaises(ValueError):
                scope.validate_current()
        finally:
            (self.directory / 'PREPARATION.json').write_bytes(body)


    def test_tampered_original_target_artifact_blocks_callback(self):
        path = self.directory / 'TARGETS.npz'
        body = path.read_bytes()
        reached = []
        try:
            path.write_bytes(body + b' ')
            with self.assertRaises(ValueError):
                e.make_annual_case(SOURCE, self.directory, self.go, e._sha(self.go),
                    policy_variant=e.MODES[0], review_raw=self.review,
                    expected_review_sha256=e._sha(self.review),
                    constructor_callback=lambda **values: reached.append(values))
        finally:
            path.write_bytes(body)
        self.assertEqual(reached, [])

    def test_original_generated_primitive_review_cannot_admit_history(self):
        name = 'bounded_account_continuation_independent_review_20261015/REVIEW.json'
        review = (e.ROOT / name).read_bytes()
        go = fixture_go(self.preparation, review)
        with self.assertRaises(ValueError):
            e._validate_independent_review(self.preparation, self.prep,
                review, e._sha(review), go)

    def test_default_callback_passes_reviewed_intervals_before_construction(self):
        # Replace the import with a recording object; never load native runtime.
        from types import SimpleNamespace
        observed = []
        module = SimpleNamespace(__file__=str(e.HERE / 'guard50_exit.py'),
            construct_case=lambda *args, **kwargs: observed.append((args, kwargs)) or 'RECORDED')
        scope = SimpleNamespace(policy_variant=e.MODES[0])
        with patch.object(e.importlib, 'import_module', return_value=module):
            result = e._default_constructor_callback(scope=scope, preparation={},
                window={}, source_rows=(), decisions=(), targets=(), captured={})
        self.assertEqual(result, 'RECORDED')
        args, kwargs = observed[0]
        self.assertEqual(kwargs['quality_intervals'],
            ((1723456980000000, 1723457100000000, e.a.g.SYMBOLS),))
        self.assertIs(kwargs['historical_scope'], scope)
        self.assertEqual(kwargs['policy_variant'], e.MODES[0])
        self.assertNotIn('generated_scope', kwargs)


    def test_provider_counts_only_captured_source_bytes_without_late_reads_or_account(self):
        # Source decoding is not financial replay: no account/clock exists.
        with patch.object(e.a.n, '_construct_case', side_effect=AssertionError('NO_ACCOUNT')), \
                patch.object(e.a.n, 'runtime', side_effect=AssertionError('NO_RUNTIME')), \
                patch.object(e.a.g, 'make_account', side_effect=AssertionError('NO_GRID_ACCOUNT')):
            _, window, rows, decisions, targets, _ = e.validate_annual_inputs(
                SOURCE, self.directory, self.go, e._sha(self.go), policy_variant=e.MODES[0])
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('NO_LATE_REOPEN')), \
                    patch.object(Path, 'open', side_effect=AssertionError('NO_LATE_OPEN')):
                sizes = []
                first = last = None
                stale_marks = {}
                for block in window['minute_blocks']():
                    stamps = block['times']
                    sizes.append(len(stamps))
                    if first is None:
                        first = int(stamps[0])
                    last = int(stamps[-1])
                    for at in (e.a.m.LAST_GENUINE_OPEN, *e.a.m.MISSING_OPENS):
                        if int(stamps[0]) <= at <= int(stamps[-1]):
                            offset = int(np.searchsorted(stamps, at))
                            stale_marks[at] = {symbol: float(block['market'][symbol]['mark'][offset])
                                for symbol in e.a.g.SYMBOLS}
        self.assertEqual(sizes, [1440] * 366)
        self.assertEqual((first, last), (e.START, e.END - e.a.n.MINUTE))
        self.assertEqual(stale_marks[e.a.m.LAST_GENUINE_OPEN], stale_marks[e.a.m.MISSING_OPENS[0]])
        self.assertEqual(stale_marks[e.a.m.LAST_GENUINE_OPEN], stale_marks[e.a.m.MISSING_OPENS[1]])



    def test_all_source_gate_financial_constructors_stay_at_zero_calls(self):
        for mocked in self.finance_mocks:
            mocked.assert_not_called()

    def test_no_cross_B_C_mode_or_resource_authority(self):
        self.assertEqual(e.MODES, ('GUARD50_EXIT_ONLY',))
        self.assertEqual(self.prep['maximum_cases'], 1)
        self.assertEqual(e.RESOURCE_LIMITS, runner.LIMITS)
        self.assertIs(self.prep['B_C_reruns_authorized'], False)
        self.assertIs(self.prep['policy']['B_C_reruns_authorized'], False)
        self.assertIs(self.prep['policy']['D_has_no_topup_or_internal_margin_transfer'], True)
        for mode in ('CONTINUE_ONLY', 'TOPUP_THEN_CONTINUE'):
            body = fixture_go(self.preparation, self.review, [mode])
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.validate(body, mode=mode)
            body = fixture_go(self.preparation, self.review, [e.MODES[0], mode])
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                self.validate(body)
        for field in ('B_C_reruns_authorized',):
            for data in (self.prep,):
                bad = deepcopy(data);bad[field] = True
                with self.assertRaises(ValueError):e._validate_preparation(raw(bad))
            bad = json.loads(self.go);bad[field] = True
            with self.assertRaises(ValueError):self.validate(raw(bad))
            bad = json.loads(self.review);bad[field] = True
            review = raw(bad)
            with self.assertRaises(ValueError):
                e._validate_independent_review(self.preparation, self.prep, review,
                    e._sha(review), fixture_go(self.preparation, review))

    def test_frozen_V2_saved_GO_and_review_bytes_cannot_authorize_D(self):
        old_go = (e.FROZEN_V2 / 'ROOT_GO_APPROVED_V2_20261015_0735.json').read_bytes()
        with self.assertRaises(ValueError):self.validate(old_go)
        old_prep = (e.FROZEN_V2 / 'source_only_preparation_attempt001/PREPARATION.json').read_bytes()
        with self.assertRaises(ValueError):e._validate_preparation(old_prep)
        for key in ('schema', 'policy_version', 'source_scope'):
            bad = json.loads(self.review)
            old = json.loads(old_prep)
            bad[key] = old.get(key, 'V2')
            review = raw(bad)
            with self.subTest(key=key), self.assertRaises(ValueError):
                e._validate_independent_review(self.preparation, self.prep, review,
                    e._sha(review), fixture_go(self.preparation, review))

    def test_runner_scope_accepts_only_single_exact_D_metadata_without_launch(self):
        with tempfile.TemporaryDirectory(prefix='guard50_gate_', dir=e.HERE) as folder:
            path = Path(folder)
            (path / 'PREPARATION.json').write_bytes(self.preparation)
            (path / 'REVIEW.json').write_bytes(self.review)
            go_path = path / 'GO_FIXTURE_IN_TEMP_ONLY.json'
            args = SimpleNamespace(preparation=str(path), review=str(path/'REVIEW.json'),
                review_sha=e._sha(self.review), go=str(go_path), go_sha=e._sha(self.go))
            go_path.write_bytes(self.go)
            with patch.object(runner.subprocess, 'Popen', side_effect=AssertionError('NO_LAUNCH')) as launch:
                self.assertEqual(runner.validate_scope(args), (self.preparation, self.go, self.review))
                for permitted in (['CONTINUE_ONLY'], ['TOPUP_THEN_CONTINUE'],
                        [e.MODES[0], 'CONTINUE_ONLY'], list(e.MODES)*2, []):
                    body = fixture_go(self.preparation, self.review, permitted)
                    go_path.write_bytes(body);args.go_sha=e._sha(body)
                    with self.subTest(permitted=permitted), self.assertRaises(ValueError):
                        runner.validate_scope(args)
                launch.assert_not_called()

    def test_default_callback_rejects_generic_or_mislocated_module(self):
        module = SimpleNamespace(__file__=str(e.FROZEN_V2 / 'integration.py'),
            construct_case=lambda *args, **kwargs: self.fail('NO_GENERIC_CONSTRUCTOR'))
        with patch.object(e.importlib, 'import_module', return_value=module) as load:
            with self.assertRaises(ValueError):
                e._default_constructor_callback(scope=SimpleNamespace(policy_variant=e.MODES[0]),
                    preparation={}, window={}, source_rows=(), decisions=(), targets=(), captured={})
            load.assert_called_once_with('guard50_exit')

    def test_runner_retains_frozen_precision100_reporting_limitation(self):
        import inspect
        source = inspect.getsource(runner.validate_saved_terminal)
        self.assertIn('ctx.prec=100', source)
        self.assertIn("cash=D(10000)+sum((D(r['free_cash_delta'])", source)
        self.assertIn('SAVED_PRIMARY_CASH_ISOLATED_DEBT_LEDGER_MISMATCH', source)
        self.assertNotIn('epsilon', source.replace('# replace this raw sum with native-40 event replay or an epsilon.', ''))


if __name__ == '__main__':
    unittest.main(verbosity=2)
