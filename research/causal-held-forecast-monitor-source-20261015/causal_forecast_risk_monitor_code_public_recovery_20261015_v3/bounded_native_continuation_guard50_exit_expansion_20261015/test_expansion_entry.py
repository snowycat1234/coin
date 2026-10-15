"""Temporary actual-input gates with all financial/launch boundaries prohibited.

Generated review/GO fixture bytes exist in memory only. No live authorization,
account construction, history advance, download, holdout access or publication.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
import os
from pathlib import Path
import tempfile
from types import MappingProxyType, SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
import expansion_entry as e


def raw(value):
    return e._canonical(value)


def fixture_review(preparation):
    p = json.loads(preparation)
    return raw(dict(schema=e.REVIEW_SCHEMA, status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        **e._authorization_common(preparation, p),
        generated_native_scheduler_phase_order_passed=True, generated_shared_pending_32_corner_passed=True,
        generated_preview_isolation_passed=True, generated_causal_quality_passed=True,
        generated_terminal_taxonomy_passed=True, generated_unknown_quality_no_new_exit_passed=True,
        generated_guard50_paid_exit_no_topup_passed=True,
        generated_exact_cell_year_tier_target_quality_gates_passed=True,
        generated_frozen_manifest_and_ordered_tranche_gates_passed=True,
        generated_pool_resource_and_aggregate_pressure_gates_passed=True,
        generated_canonical_launch_claim_duplicate_and_existing_output_gates_passed=True,
        generated_global_controller_lease_inherited_worker_FD_gates_passed=True,
        generated_helper_thread_affinity_and_compute_pool_contract_passed=True,
        generated_actual_held_exposure_forecast_overshoot_reporting_passed=True,
        actual_2023_2024_accounts_constructed=0, actual_2023_2024_financial_runs=0,
        historical_market_minutes_advanced=0, publication_actions=0, locked_source_reads=0))


def fixture_go(preparation, review, *, tranche=e.FIRST_TRANCHE, permitted_cells=None):
    p = json.loads(preparation)
    cpus = sorted(os.sched_getaffinity(0))[:2]
    return raw(dict(schema=e.GO_SCHEMA, action='RUN_FRESH_EXACT_ORDERED_EXPANSION_TRANCHE_ONLY',
        **e._authorization_common(preparation, p), tranche=tranche,
        permitted_cells=list(e.tranche_cells(tranche)) if permitted_cells is None else permitted_cells,
        requested_worker_count=len(cpus), worker_CPUs=cpus, independent_review_SHA256=e._sha(review)))


@contextmanager
def source_only_boundaries():
    """Prohibit native/accounts, old GOs, claims and process launch in preparation."""
    stack = ExitStack()
    mocks = []
    import expansion as integration
    targets = [(integration, 'construct_case'), (integration.D, 'construct_case'),
        (integration.V2, 'construct_case'), (integration.ExpansionAccount, '__init__'),
        (integration.D.Guard50ExitAccount, '__init__'),
        (integration.V2.ContinuationAccount, '__init__'),
        (integration.V2.ENGINE.USDTLinearPerpetualAccount, '__init__'),
        (e.a24.n, '_construct_case'), (e.a24.n, 'runtime'), (e.a24.g, 'make_account'),
        (e.a23, 'make_annual_case'), (e.a23, 'validate_root_go'),
        (e.a24, 'make_annual_case'), (e.a24, 'validate_root_go'),
        (e.a24.h, 'make_smoke_case'), (e.a24.h, 'validate_root_go'),
        (e.old, 'make_annual_case'), (e.old, 'validate_root_go')]
    # Cover worker launch and system process/network entry points too.
    import subprocess
    import multiprocessing
    import fcntl
    targets.extend([(fcntl, 'flock'), (subprocess, 'Popen'), (subprocess, 'run'),
        (multiprocessing.Process, 'start'), (os, 'system')])
    if (e.HERE / 'run_expansion.py').is_file():
        import run_expansion as runner
        for name in ('run_case', '_run_case', 'run_tranche', 'launch_case', '_worker_main', 'case',
                'controller', 'run_pool', '_run_pool', 'claim_launch', 'acquire_controller_lease', 'controller_lease'):
            if hasattr(runner, name):
                targets.append((runner, name))
    for target, name in targets:
        mocks.append(stack.enter_context(patch.object(target, name,
            side_effect=AssertionError('SOURCE_ONLY_ZERO_FINANCE_OR_LAUNCH_CALLS:' + name))))
    try:
        yield mocks
        for mocked in mocks:
            mocked.assert_not_called()
    finally:
        stack.close()


class ExpansionSourceGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='expansion_source_only_gate_')
        cls.directory = Path(cls.temp.name) / 'prepared'
        cls.forbidden = source_only_boundaries()
        cls.finance_mocks = cls.forbidden.__enter__()
        cls.addClassCleanup(cls.forbidden.__exit__, None, None, None)
        existing = os.environ.get('GUARD50_EXPANSION_PREPARATION')
        if existing:
            import shutil
            shutil.copytree(existing, cls.directory)
            cls.prep = e._validate_preparation((cls.directory / 'PREPARATION.json').read_bytes())
            if cls.prep['code_identity'] != e.code_identity():
                raise AssertionError('PERSISTED_PREPARATION_CODE_IDENTITY_CHANGED')
        else:
            cls.prep = e.prepare_source_only(e.SOURCE_ROOTS, cls.directory)
        cls.preparation = (cls.directory / 'PREPARATION.json').read_bytes()
        cls.review = fixture_review(cls.preparation)
        cls.go = fixture_go(cls.preparation, cls.review)
        cls.remaining_go = fixture_go(cls.preparation, cls.review, tranche=e.REMAINING_TRANCHE)

    @classmethod
    def tearDownClass(cls):
        try:
            for mock in cls.finance_mocks:
                mock.assert_not_called()
        finally:
            cls.temp.cleanup()

    def validate(self, go=None, *, cell_id='2024_STATIC50_LOW', policy_variant=e.POLICY_VARIANT):
        go = self.go if go is None else go
        return e.validate_root_go(self.preparation, go, e._sha(go), cell_id=cell_id, policy_variant=policy_variant)

    def admit(self, cell_id='2024_STATIC50_LOW', *, go=None, callback=None, **kwargs):
        go = self.remaining_go if go is None and cell_id in e.tranche_cells(e.REMAINING_TRANCHE) else (self.go if go is None else go)
        return e.make_case(e.SOURCE_ROOTS, self.directory, go, e._sha(go), cell_id=cell_id,
            review_raw=self.review, expected_review_sha256=e._sha(self.review),
            constructor_callback=callback or (lambda **values: values), **kwargs)

    def test_source_only_exact_manifest_all17_and_unchanged_original_artifacts(self):
        p = self.prep
        self.assertEqual(len(p['cells']), 17)
        self.assertEqual(p['ordered_cells'], [cell['cell_id'] for cell in e.frozen_manifest()['cells']])
        self.assertNotIn('2024_STATIC50_MID', p['cells'])
        self.assertEqual(p['resource_limits'], e.frozen_manifest()['resource_design'])
        self.assertEqual(p['resource_execution_contract'], e.RESOURCE_EXECUTION_CONTRACT)
        self.assertEqual(p['launch_claim_contract'], e.LAUNCH_CLAIM_CONTRACT)
        self.assertEqual(p['global_controller_lease_contract'], e.GLOBAL_CONTROLLER_LEASE_CONTRACT)
        self.assertEqual((p['accounts_created'], p['accounts_advanced'], p['historical_market_minutes_advanced'], p['financial_runs'], p['publication_actions']), (0, 0, 0, 0, 0))
        for key in ('annual_returns_computed', 'outcomes_inspected', 'locked_or_holdout_consumed',
                'other_years_or_2025_authorized', 'historical_admission', 'performance_selection_allowed',
                'preserved_old_root_GO_is_new_authority'):
            self.assertIs(p[key], False)
        self.assertEqual(p['policy_identity'], e._json_sha(p['policy']))
        for year in e.YEARS:
            _, original, annual = e._annual(year)
            self.assertEqual((self.directory / f'{year}/ANNUAL_SOURCE_PREPARATION.json').read_bytes(), original)
            for name, pin in annual['artifacts'].items():
                self.assertEqual(p['artifacts'][f'{year}/' + name], pin)
                self.assertEqual((self.directory / f'{year}' / name).read_bytes(), (e.ANNUAL_PREPARATIONS[year] / name).read_bytes())
            info = p['years'][str(year)]
            self.assertEqual(info['source_files'], annual['source_files'])
            self.assertEqual(info['frozen_annual_target_identity'], annual['target_identity'])
            with np.load(self.directory / f'{year}/TARGETS.npz', allow_pickle=False) as z:
                for cell in e.frozen_manifest()['cells']:
                    if cell['year'] == year:
                        self.assertEqual(e._sha(z[cell['config']].tobytes()), cell['selected_target_raw_SHA256'])
        self.assertEqual(p['code_identity'], e.code_identity())
        for name in ('expansion.py', 'expansion_entry.py', 'run_expansion.py', 'saved_native_reconciliation.py', e.MANIFEST_NAME):
            self.assertIn(e.HERE.name + '/' + name, p['code_identity'])

    def test_exact_2023_minute_mark_provenance_is_bound_separately_from_daily(self):
        info = self.prep['years']['2023']
        proof = json.loads((self.directory / info['quality_sidecar']).read_bytes())
        self.assertEqual((proof['monthly_streams'], proof['actual_daily_repair_streams'], proof['mark_cells']), (60, 5, 2628000))
        self.assertEqual(len(proof['raw_mark_streams']), 65)
        self.assertEqual(info['quality_intervals'], [])
        self.assertIsNone(info['original_genuine_observation_us'])
        self.assertEqual(proof['initial_prior_mark'], 'UNKNOWN')
        self.assertEqual(proof['first_genuine_minute_available_us'], e.a23.START + e.a24.n.MINUTE)
        self.assertFalse(proof['provider_arrival_certified'])
        self.assertFalse(proof['venue_methodology_certified'])
        self.assertEqual(len(info['auxiliary_source_pins']), 160)
        for name, digest in e.PROVENANCE_2023_PINS.items():
            self.assertEqual(info['auxiliary_source_pins'][name]['SHA256'], digest)
        self.assertEqual(len([name for name in info['auxiliary_source_pins'] if name.endswith('.zip')]), 65)
        self.assertEqual(len([name for name in info['auxiliary_source_pins'] if name.endswith('.zip.CHECKSUM')]), 65)

    def test_exact_2024_adapter_interval_and_genuine_clock_unchanged(self):
        info = self.prep['years']['2024']
        self.assertEqual(info['quality_intervals'], [[1723456980000000, 1723457100000000, list(e.a24.g.SYMBOLS)]])
        self.assertEqual(info['original_genuine_observation_us'], 1723456920000000)
        self.assertEqual(info['quality_sidecar_sha256'], 'b62fbc5bfd10b24e4c31b23c37099195ea1c12d6c9c4ff2612987c4e96706b2b')
        self.assertEqual(info['auxiliary_source_pins'], {})

    def test_all17_exact_ordered_tranche_go_admissions_source_only(self):
        for cell_id in e.tranche_cells():
            self.assertEqual(self.validate(cell_id=cell_id), self.prep)
        for cell_id in e.tranche_cells(e.REMAINING_TRANCHE):
            self.assertEqual(self.validate(self.remaining_go, cell_id=cell_id), self.prep)
        for cell_id in ('2024_STATIC50_MID', '2025_STATIC50_LOW', '2022_STATIC50_LOW', '2024_STATIC50_LOW_EXTRA', '', None, 2023):
            with self.subTest(cell_id=cell_id), self.assertRaises(ValueError):
                self.validate(cell_id=cell_id)

    def test_permitted_cells_must_be_entire_exact_ordered_tranche_never_outcome_subset(self):
        original = json.loads(self.go)
        cells = list(e.tranche_cells())
        for permitted in ([], cells[:1], cells[::-1], cells[1:] + cells[:1], cells + [cells[0]],
                cells + ['2024_STATIC50_MID'], cells + list(e.tranche_cells(e.REMAINING_TRANCHE)),
                list(e.tranche_cells(e.REMAINING_TRANCHE)), [None], [True], {'cell': cells[0]}, cells[0]):
            with self.subTest(permitted=permitted), self.assertRaises(ValueError):
                self.validate(raw({**original, 'permitted_cells': permitted}))
        for tranche in ('ALL17', 'ANY', 'STATIC50_FIRST_FIVE', '', None, []):
            with self.subTest(tranche=tranche), self.assertRaises(ValueError):
                self.validate(raw({**original, 'tranche': tranche}))
        with self.assertRaises(ValueError):
            self.validate(self.remaining_go)

    def test_missing_nonbytes_wrong_hash_duplicate_keys_and_integer_bool_lookalikes_fail(self):
        for body, digest in ((None, None), (self.go.decode(), e._sha(self.go)), (self.go, '0' * 64), (self.go, e._sha(self.go).upper())):
            with self.assertRaises(ValueError):
                e.validate_root_go(self.preparation, body, digest, cell_id='2024_STATIC50_LOW')
        for body in (b'[]', b'{', b'{"schema":1,"schema":2}', b'{"schema":NaN}'):
            with self.assertRaises(ValueError):
                self.validate(body)
        for mode in ('CONTINUE_ONLY', 'TOPUP_THEN_CONTINUE', 'NATIVE_STOP_REFERENCE', 'D', '', None):
            with self.assertRaises(ValueError):
                self.validate(policy_variant=mode)
        for key, value in (('fresh_genesis_only', 1), ('automatic_retry_authorized', 0), ('publication_authorized', 0),
                ('other_years_or_2025_authorized', 0), ('requested_worker_count', True), ('worker_CPUs', [True])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.validate(raw({**json.loads(self.go), key: value}))

    def test_every_review_and_go_identity_safety_and_resource_field_is_required(self):
        for key in json.loads(self.go):
            if key == 'tranche':
                continue  # absent tranche safely defaults to exact first-five only
            bad = json.loads(self.go)
            del bad[key]
            with self.subTest(go_missing=key), self.assertRaises(ValueError):
                self.validate(raw(bad))
        for key in json.loads(self.review):
            bad = json.loads(self.review)
            del bad[key]
            body = raw(bad)
            go = fixture_go(self.preparation, body)
            with self.subTest(review_missing=key), self.assertRaises(ValueError):
                e._validate_independent_review(self.preparation, self.prep, body, e._sha(body), go)
        for key, value in (('generated_exact_cell_year_tier_target_quality_gates_passed', 1),
                ('generated_pool_resource_and_aggregate_pressure_gates_passed', False),
                ('generated_canonical_launch_claim_duplicate_and_existing_output_gates_passed', False),
                ('generated_global_controller_lease_inherited_worker_FD_gates_passed', False),
                ('generated_helper_thread_affinity_and_compute_pool_contract_passed', False),
                ('actual_2023_2024_accounts_constructed', False), ('actual_2023_2024_financial_runs', 1),
                ('historical_market_minutes_advanced', 1), ('code_identity', {}), ('cells', {}), ('years', {})):
            body = raw({**json.loads(self.review), key: value})
            with self.subTest(review_field=key), self.assertRaises(ValueError):
                e._validate_independent_review(self.preparation, self.prep, body, e._sha(body), fixture_go(self.preparation, body))
        go = json.loads(self.go)
        for key, value in (('resource_limits', {}), ('resource_execution_contract', {}), ('launch_claim_contract', {}), ('global_controller_lease_contract', {}), ('worker_CPUs', [-1]), ('requested_worker_count', 3),
                ('worker_CPUs', [sorted(os.sched_getaffinity(0))[0]] * 2), ('policy_identity', '0' * 64),
                ('manifest_SHA256', '0' * 64), ('years', {}), ('cells', {}), ('code_identity', {}),
                ('reused_2024_STATIC50_MID_rerun_authorized', True), ('performance_selection_allowed', True),
                ('preserved_old_root_GO_is_new_authority', True), ('fresh_genesis_only', False),
                ('halted_snapshot_resume_authorized', True), ('other_years_or_2025_authorized', True)):
            with self.subTest(go_field=key), self.assertRaises(ValueError):
                self.validate(raw({**go, key: value}))

    def test_old_annual_D_and_V2_go_never_new_authority(self):
        for name in self.prep['preserved_evidence_pins']:
            if 'go' in name.lower():
                with self.subTest(name=name), self.assertRaises(ValueError):
                    self.validate((e.ROOT / name).read_bytes())
        for path in (e.D_ROOT / 'ROOT_GO_APPROVED_D_20261015_0804.json',):
            with self.assertRaises(ValueError):
                self.validate(path.read_bytes())

    def test_modified_manifest_or_preparation_cross_year_config_and_quality_swaps_refused(self):
        for mutate in ('manifest', 'year', 'config', 'target', 'quality', 'source', 'covariance'):
            p = deepcopy(self.prep)
            cell = p['cells']['2024_STATIC50_LOW']
            if mutate == 'manifest': p['manifest']['cells'][0]['tier'] = 'HIGH'
            elif mutate == 'year': cell['descriptor']['year'] = 2023
            elif mutate == 'config': cell['descriptor']['config'] = 'STATIC50_HIGH'
            elif mutate == 'target': cell['selected_target_raw_SHA256'] = p['cells']['2024_STATIC50_HIGH']['selected_target_raw_SHA256']
            elif mutate == 'quality': p['years']['2024']['quality_intervals'] = []
            elif mutate == 'source': p['years']['2024']['source_identity'] = p['years']['2023']['source_identity']
            elif mutate == 'covariance': cell['covariance_raw_SHA256'] = p['years']['2023']['covariance_raw_SHA256']
            with self.subTest(mutate=mutate), self.assertRaises(ValueError):
                e._validate_preparation(raw(p))
        with patch.object(e, 'MANIFEST_SHA256', '0' * 64):
            with self.assertRaises(ValueError): e.frozen_manifest()

    def test_missing_or_mismatched_review_blocks_before_late_source_or_callback(self):
        reached = []
        with patch.object(e, 'validate_case_inputs', side_effect=AssertionError('NO_LATE_SOURCE')):
            with self.assertRaises(ValueError):
                e.make_case(e.SOURCE_ROOTS, self.directory, self.go, e._sha(self.go), cell_id='2024_STATIC50_LOW',
                    constructor_callback=lambda **values: reached.append(values))
        self.assertEqual(reached, [])
        with self.assertRaises(ValueError):
            e._validate_independent_review(self.preparation, self.prep, self.review, '0' * 64, self.go)

    def test_all17_callbacks_receive_sealed_cell_inputs_without_finance_or_fake_scope(self):
        for cell in e.frozen_manifest()['cells']:
            with self.subTest(cell_id=cell['cell_id']):
                values = self.admit(cell['cell_id'])
                scope = values['scope']
                self.assertIs(type(scope), e.CaseExecutionScope)
                self.assertEqual((scope.cell_id, scope.year, scope.strategy, scope.tier_name, scope.config),
                    (cell['cell_id'], cell['year'], cell['strategy'], cell['tier'], cell['config']))
                self.assertEqual(len(values['decisions']), cell['days'])
                self.assertEqual(values['targets'].shape, (cell['days'], 5))
                self.assertEqual(len(values['source_rows']), 2820 if cell['year'] == 2023 else 2825)
                self.assertFalse(values['decisions'].flags.writeable)
                self.assertFalse(values['targets'].flags.writeable)
                self.assertIs(type(values['source_rows']), tuple)
                self.assertTrue(all(isinstance(r, MappingProxyType) for r in values['source_rows']))
                self.assertNotIn('generated_scope', values)
                self.assertNotIn('initial_prior', values['window'])
                self.assertNotIn('previous_quote', values['window'])
                self.assertTrue(scope.validate_current())
                self.assertTrue(scope.validate_inputs(values['window'], values['source_rows'], values['decisions'], values['targets']))
                self.assertIs(deepcopy(scope), scope)
                metadata = scope.metadata
                metadata['year'] = 2025
                metadata['calendar'][0] = 0
                self.assertEqual(scope.metadata['year'], cell['year'])
                self.assertEqual(scope.metadata['calendar'], cell['calendar'])
                with self.assertRaises(FrozenInstanceError): scope.year = 2025
                with self.assertRaises(ValueError): replace(scope, _seal=object())
                for changes in ({'year': 2025}, {'tier_name': 'HIGH' if cell['tier'] != 'HIGH' else 'LOW'},
                        {'config': 'STATIC50_MID'}, {'quality_sidecar_sha256': '0' * 64},
                        {'quality_intervals': ((0, 1, e.a24.g.SYMBOLS),)}, {'source_identity': '0' * 64}):
                    if changes == {'config': cell['config']}:
                        continue
                    with self.subTest(changes=changes), self.assertRaises(ValueError):
                        replace(scope, **changes).validate_current()
                with self.assertRaises(ValueError): scope.validate_inputs(values['window'], values['source_rows'], values['decisions'].copy(), values['targets'])

    def test_cross_source_roots_refused_and_other_year_mapping_denied(self):
        with self.assertRaises(ValueError):
            e.validate_case_inputs({2023:e.SOURCE_ROOTS[2024], 2024:e.SOURCE_ROOTS[2023]}, self.directory,
                self.go, e._sha(self.go), cell_id='2024_STATIC50_LOW')
        for roots in ({2023:e.SOURCE_ROOTS[2023]}, {**e.SOURCE_ROOTS, 2025:e.SOURCE_ROOTS[2024]},
                {'2023':e.SOURCE_ROOTS[2023], '2024':e.SOURCE_ROOTS[2024]}):
            with self.assertRaises(ValueError): e._source_roots(roots)

    def test_captured_providers_are_year_specific_immutable_and_no_late_source_reads(self):
        for cell_id in ('2023_STATIC50_LOW', '2024_STATIC50_LOW'):
            values = self.admit(cell_id)
            provider = values['window']['minute_blocks']
            with patch.object(Path, 'read_bytes', side_effect=AssertionError('NO_LATE_SOURCE_READ')):
                block = next(iter(provider()))
            self.assertEqual(int(block['times'][0]), values['window']['start'])
            self.assertEqual(len(block['times']), 1440)
            self.assertEqual(tuple(block['market']), e.a24.g.SYMBOLS)
            for market in block['market'].values():
                for array in market.values(): self.assertFalse(array.flags.writeable)
            with self.assertRaises(FrozenInstanceError): provider.year = 2025

    def test_default_callback_passes_exact_local_module_scope_intervals_no_generated_flag(self):
        values = self.admit('2023_STATIC50_LOW')
        reached = []
        fake = SimpleNamespace(__file__=str(e.HERE / 'expansion.py'),
            construct_case=lambda *args, **kwargs: reached.append((args, kwargs)) or 'RECORDED')
        with patch.object(e.importlib, 'import_module', return_value=fake):
            self.assertEqual(e._default_constructor_callback(**values), 'RECORDED')
        args, kwargs = reached[0]
        self.assertEqual(set(kwargs), {'policy_variant', 'historical_scope', 'quality_intervals'})
        self.assertEqual(kwargs['quality_intervals'], ())
        self.assertIs(kwargs['historical_scope'], values['scope'])
        self.assertEqual(kwargs['policy_variant'], e.POLICY_VARIANT)
        fake.__file__ = str(e.D_ROOT / 'guard50_exit.py')
        with patch.object(e.importlib, 'import_module', return_value=fake):
            with self.assertRaises(ValueError): e._default_constructor_callback(**values)

    def test_exclusive_output_never_overwritten_and_source_artifact_tamper_caught(self):
        with self.assertRaises(ValueError): e.prepare_source_only(e.SOURCE_ROOTS, self.directory)
        path = self.directory / '2024/CAUSAL_MARK_ADAPTER.json'
        before = path.read_bytes()
        try:
            path.write_bytes(before + b' ')
            with self.assertRaises(ValueError): self.admit()
        finally:
            path.write_bytes(before)
        values = self.admit('2023_STATIC50_LOW')
        scope = values['scope']
        source_name = next(name for name, _, _ in scope._source_pins if name.endswith('/2023-01.json'))
        real = e.a24.h._read_exact
        def fail_provenance(path, *args, **kwargs):
            if str(path).endswith(source_name): raise ValueError('TEST_AUXILIARY_PROVENANCE_CHANGED')
            return real(path, *args, **kwargs)
        with patch.object(e.a24.h, '_read_exact', side_effect=fail_provenance):
            with self.assertRaisesRegex(ValueError, 'TEST_AUXILIARY_PROVENANCE_CHANGED'): scope.validate_current()


if __name__ == '__main__':
    unittest.main(verbosity=2)
