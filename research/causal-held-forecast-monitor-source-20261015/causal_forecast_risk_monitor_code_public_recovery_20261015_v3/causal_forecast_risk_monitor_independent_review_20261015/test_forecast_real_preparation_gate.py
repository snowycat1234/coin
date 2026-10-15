"""Root-authorized admission METADATA callbacks on exact persisted preparation.

No account, minute-provider iteration, financial advancement, process or claim is
permitted. Every temporary scope is revoked before its recording callback exits.
No GO or review envelope is written or retained in the receipt.
"""
from contextlib import ExitStack
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import Mock, patch

from generated_helpers import f
import forecast_entry as e
import forecast_historical as historical
import run_forecast as runner

HERE = Path(__file__).resolve().parent
DIRECTORY = e.HERE / 'source_preparation_attempt003'


class RealPreparationMetadataAdmission(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.stack = ExitStack()
        cls.addClassCleanup(cls.stack.close)
        cls.blocked = {}
        native = f.V2.native.runtime()[1].NativeDailySimulator
        targets = ((f.V2.ENGINE.USDTLinearPerpetualAccount, '__init__', 'native_account_genesis'),
            (f.ForecastRiskAccount, '__init__', 'generated_forecast_genesis'),
            (historical.HistoricalForecastRiskAccount, '__init__', 'historical_account_genesis'),
            (f.V2.grid, 'make_account', 'grid_account_genesis'),
            (f.V2.native, '_construct_case', 'native_financial_constructor'),
            (native, '__init__', 'native_simulator_genesis'),
            (native, 'advance_day', 'native_financial_advance'),
            (e.BASE._CapturedMinuteProvider, '__call__', 'captured_minute_provider_iteration'),
            (historical, 'construct_historical_case', 'historical_case_constructor'),
            (runner, 'case', 'finite_case'), (runner, 'controller', 'finite_controller'),
            (runner, 'claim_launch', 'canonical_claim'),
            (runner, 'controller_lease', 'canonical_lease'), (runner, 'run_pool', 'worker_pool'),
            (subprocess, 'Popen', 'process_spawn'), (subprocess, 'run', 'process_run'),
            (socket.socket, 'connect', 'network_connect'),
            (socket, 'create_connection', 'network_connection_factory'))
        for owner, name, label in targets:
            blocked = Mock(side_effect=AssertionError('FORBIDDEN_IN_POSITIVE_METADATA_GATE:' + label))
            cls.blocked[label] = cls.stack.enter_context(patch.object(owner, name, blocked))
        cls.raw = (DIRECTORY / 'PREPARATION.json').read_bytes()
        cls.prep = e._validate_preparation(cls.raw)
        cls.identity = e.code_identity()
        if cls.prep['code_identity'] != cls.identity:
            raise AssertionError('REAL_PREPARATION_DOES_NOT_BIND_CURRENT_EXACT_SOURCE')
        cls.records = []

    @classmethod
    def tearDownClass(cls):
        counts = {name: blocked.call_count for name, blocked in cls.blocked.items()}
        for blocked in cls.blocked.values():
            blocked.assert_not_called()
        assert len(cls.records) == 4
        assert e.code_identity() == cls.identity
        assert (DIRECTORY / 'PREPARATION.json').read_bytes() == cls.raw
        report = dict(status='PASS_INDEPENDENT_FOUR_REAL_PREPARATION_METADATA_CALLBACKS_NO_FINANCE',
            preparation_SHA256=sha256(cls.raw).hexdigest(), code_identity=cls.identity,
            test_file_SHA256=sha256(Path(__file__).read_bytes()).hexdigest(),
            callbacks=cls.records, callback_count=4, metadata_scopes_created=4,
            metadata_scopes_revoked_before_callback_return=4,
            authority_envelopes_written=0, authority_envelopes_retained=0,
            historical_accounts_constructed=0, historical_financial_runs=0,
            historical_minutes_advanced=0, provider_iterations=0,
            claims_created=0, leases_acquired=0, processes_launched=0,
            actual_root_GO_authority_created=False, historical_execution_authorized=False,
            source_evidence_read_only=True, old_GO_evidence_is_new_authority=False,
            scope_or_input_objects_retained_for_execution=0, forbidden_boundary_call_counts=counts)
        (HERE / 'INDEPENDENT_REAL_PREPARATION_METADATA_REVIEW.json').write_text(
            json.dumps(report, sort_keys=True, indent=2) + '\n')
        # Only source/preparation metadata persists. Temporary authority bytes
        # are function-local in each test and no scope escapes its callback.
        cls.records.clear()

    def check_cell(self, index):
        cell_id = e.tranche_cells()[index]
        cell = e.cell_descriptor(cell_id)
        common = e._authorization_common(self.raw, self.prep)
        review = dict(schema=e.REVIEW_SCHEMA, status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
            **common, **dict.fromkeys(e.REVIEW_FLAGS, True), actual_2023_2024_accounts_constructed=0,
            actual_2023_2024_financial_runs=0, historical_market_minutes_advanced=0,
            publication_actions=0, locked_source_reads=0,
            generated_metadata_test_only=True, not_external_root_authority=True)
        review_raw = e._canonical(review)
        go = dict(schema=e.GO_SCHEMA, action=e.ACTION, **common, tranche=e.FIRST_TRANCHE,
            permitted_cells=list(e.tranche_cells()), requested_worker_count=2, worker_CPUs=[2, 3],
            independent_review_SHA256=e._sha(review_raw), generated_metadata_test_only=True,
            not_external_root_authority=True)
        go_raw = e._canonical(go)
        revoked = []
        def record(*, scope, preparation, window, source_rows, decisions, targets, captured):
            try:
                self.assertIs(type(scope), e.ForecastExecutionScope)
                self.assertEqual(scope.cell_id, cell_id)
                self.assertEqual(scope.year, cell['year'])
                self.assertEqual(scope.tier_name, 'MID')
                self.assertTrue(scope.validate_inputs(window, source_rows, decisions, targets))
                self.assertTrue(scope.validate_current())
                self.assertFalse(decisions.flags.writeable)
                self.assertFalse(targets.flags.writeable)
                self.assertFalse(scope._bound_covariance.flags.writeable)
                self.assertEqual(e._sha(targets.tobytes()), cell['selected_target_raw_SHA256'])
                year = preparation['years'][str(cell['year'])]
                self.assertEqual(e._sha(scope._bound_covariance.tobytes()), year['covariance_raw_SHA256'])
                self.assertEqual(scope.quality_intervals, e._immutable(year['quality_intervals']))
                self.assertEqual(scope.quality_sidecar_sha256, year['quality_sidecar_sha256'])
                self.assertEqual(scope.original_genuine_observation_us, year['original_genuine_observation_us'])
                self.assertIs(deepcopy(scope), scope)
                with self.assertRaises(ValueError):
                    scope.validate_inputs(window, source_rows, decisions, targets.copy())
                with self.assertRaises(ValueError):
                    scope.validate_inputs(window, source_rows, decisions.copy(), targets)
                metadata = scope.metadata
                metadata['cell_id'] = 'CALLER_MUTATED_COPY'
                self.assertEqual(scope.metadata['cell_id'], cell_id)
                self.assertNotIn('fixture_scope', window)
                return dict(cell_id=cell_id, year=cell['year'], config=cell['config'],
                    selected_target_raw_SHA256=e._sha(targets.tobytes()),
                    covariance_raw_SHA256=year['covariance_raw_SHA256'],
                    source_identity=scope.source_identity,
                    quality_sidecar_sha256=scope.quality_sidecar_sha256,
                    quality_intervals=e._plain(scope.quality_intervals),
                    original_genuine_observation_us=scope.original_genuine_observation_us,
                    exact_reference_and_immutable_array_gates=True, generated_fixture_flag_used=False,
                    recording_metadata_only=True, financial_constructor_calls=0)
            finally:
                object.__setattr__(scope, '_seal', None)
                with self.assertRaises(ValueError):
                    scope.validate_current()
                revoked.append(True)
        result = e.make_case(e.SOURCE_ROOTS, DIRECTORY, go_raw, e._sha(go_raw), cell_id=cell_id,
            review_raw=review_raw, expected_review_sha256=e._sha(review_raw), constructor_callback=record)
        self.assertEqual(revoked, [True])
        result['scope_revoked_before_return'] = True
        # Reject executable objects in what this test retains or persists.
        json.dumps(result, sort_keys=True, allow_nan=False)
        self.records.append(result)
        del go_raw, review_raw, go, review, common

    def test_2023_static_mid_metadata_only(self):
        self.check_cell(0)

    def test_2023_hold_mid_metadata_only(self):
        self.check_cell(1)

    def test_2024_static_mid_metadata_only(self):
        self.check_cell(2)

    def test_2024_hold_mid_metadata_only(self):
        self.check_cell(3)


if __name__ == '__main__':
    unittest.main()
