"""Fake metadata/bytes only. Positive validation never mints actual scopes."""
from copy import deepcopy
from dataclasses import fields
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest
from unittest.mock import Mock, patch
import zipfile

import numpy as np

import cs_common as c
import cs_config as config
import cs_entry as entry
import cs_finance_gate as gate
import cs_loader as loader
import cs_admission as admission
import cs_generated as generated
import cs_saved as saved
import cs_process_runtime as runtime
from cs_source_guard import SourceOnlyGuard
from test_cs_entry import fake_preparation


def fake_bundle():
    prep = c.canonical(fake_preparation()); p = c.exact_object(prep); code = gate.code_identity()
    prepared = dict(schema=gate.PREPARED_REVIEW_SCHEMA, status='PASS', source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
        scope_manifest_SHA256=entry.manifest_sha(), source_contract_map_SHA256=entry.contract_sha(),
        tranche=entry.FIRST6, ordered_cells=list(entry.tranche_cells(entry.FIRST6)), years=[2022, 2023],
        preparation_SHA256=c.sha(prep), source_stage_GO_SHA256=p['source_stage_GO_SHA256'], source_review_SHA256=p['source_review_SHA256'],
        per_cell_input_binding_SHA256={key: row['input_binding_SHA256'] for key, row in p['cells'].items()},
        per_year_array_raw_SHA256={key: row['array_raw_SHA256'] for key, row in p['years'].items()},
        old_D_GO_reused_as_authority=False, native_financial_gate_reviewed=False, financial_execution_authorized=False)
    native = dict(schema=gate.NATIVE_REVIEW_SCHEMA, status='PASS', source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
        financial_code_manifest_SHA256=code, scope_manifest_SHA256=entry.manifest_sha(), tranche=entry.FIRST6,
        ordered_cells=list(entry.tranche_cells(entry.FIRST6)), native_financial_gate_reviewed=True,
        financial_execution_authorized=False, actual_source_or_target_bodies_read=False, old_D_GO_reused_as_authority=False,
        generated_two_worker_probe_passed=True, worker_CPUs=[4, 5], maximum_observed_live_workers=2,
        generated_resource_probe_SHA256='0' * 64)
    pr, nr = c.canonical(prepared), c.canonical(native)
    review = dict(schema=gate.REVIEW_SCHEMA, status='PASS', source_code_manifest_SHA256=gate.SOURCE_CODE_SHA256,
        financial_code_manifest_SHA256=code, scope_manifest_SHA256=entry.manifest_sha(), source_contract_map_SHA256=entry.contract_sha(),
        preparation_SHA256=c.sha(prep), tranche=entry.FIRST6, ordered_cells=list(entry.tranche_cells(entry.FIRST6)),
        source_stage_GO_SHA256=p['source_stage_GO_SHA256'], old_D_GO_reused_as_authority=False,
        native_financial_gate_reviewed=True, financial_execution_authorized=False,
        prepared_source_target_review_SHA256=c.sha(pr), native_generated_review_SHA256=c.sha(nr),
        real_CLI_generated_GO_guard_integration_reviewed=True,
        failed_claim_supersession_packet_SHA256=gate.supersession.PACKET_SHA,
        stable_cross_version_claim_registry=gate.supersession.STABLE_REGISTRY_REL,
        permanent_one_use_failed_claim_consumption_reviewed=True)
    rr = c.canonical(review); go = c.canonical(gate.policy(prep, c.sha(rr), c.sha(pr), c.sha(nr), [4, 5]))
    return prep, go, rr, pr, nr


def validate(bundle):
    prep, go, rr, pr, nr = bundle
    return gate.validate(prep, go, c.sha(go), rr, c.sha(rr), pr, c.sha(pr), nr, c.sha(nr))


class FinancialMetadataTests(unittest.TestCase):
    def tearDown(self):
        self.assertFalse(admission._LIVE); self.assertFalse(loader._LIVE)
        self.assertFalse(entry._ACTIVE_SOURCE); self.assertFalse(entry._ACTIVE_FINANCIAL)

    def test_full_fake_wire_positive_is_immutable_metadata_only(self):
        value = validate(fake_bundle())
        self.assertEqual(tuple(value['worker_CPUs']), (4, 5))
        with self.assertRaises(TypeError): value['cost'] = 'OTHER'

    def test_every_missing_root_field_and_resealed_wrong_policy_denied(self):
        bundle = fake_bundle(); original = c.exact_object(bundle[1])
        for key in original:
            bad = deepcopy(original); del bad[key]; changed = list(bundle); changed[1] = c.canonical(bad)
            with self.subTest(key=key), self.assertRaises(ValueError): validate(changed)
        for key, value in (('cost', 'STRESS43'), ('policy_variant', 'TOPUP'), ('worker_CPUs', [4, 4]),
                ('requested_worker_count', 1), ('saved_targets_rebuilt_during_finance', True),
                ('automatic_retry_authorized', True), ('debt_forgiveness_authorized', True),
                ('source_code_manifest_SHA256', 'a' * 64), ('ordered_cells', [])):
            bad = deepcopy(original); bad[key] = value; changed = list(bundle); changed[1] = c.canonical(bad)
            with self.subTest(key=key), self.assertRaises(ValueError): validate(changed)

    def test_reviews_cannot_exchange_domains_or_external_digests(self):
        bundle = fake_bundle()
        for index in (2, 4):
            changed = list(bundle); changed[index] = bundle[3]
            with self.subTest(index=index), self.assertRaises(ValueError): validate(changed)
        prep, go, rr, pr, nr = bundle
        with self.assertRaises(ValueError): gate.validate(prep, go, 'a' * 64, rr, c.sha(rr), pr, c.sha(pr), nr, c.sha(nr))
        for index in (2, 3, 4):
            original = c.exact_object(bundle[index])
            for key in original:
                bad = deepcopy(original); del bad[key]; changed = list(bundle); changed[index] = c.canonical(bad)
                with self.subTest(index=index, key=key), self.assertRaises(ValueError): validate(changed)

    def test_no_guard_loader_or_ducktype_scope_can_read_or_mint(self):
        forbidden = Mock(side_effect=AssertionError('NO_PREPARATION_OR_SOURCE_READ'))
        with patch.object(c, 'exact', forbidden), self.assertRaisesRegex(ValueError, 'SOURCE_GUARD_REQUIRED'):
            loader.load_year('/FAKE', expected_preparation_sha256='a' * 64, year=2022,
                source_go_raw=b'{}', expected_source_go_sha256='a' * 64, source_review_raw=b'{}', expected_source_review_sha256='b' * 64,
                financial_go_raw=b'{}', expected_financial_go_sha256='c' * 64, financial_review_raw=b'{}', expected_financial_review_sha256='d' * 64,
                prepared_review_raw=b'{}', expected_prepared_review_sha256='e' * 64, native_review_raw=b'{}', expected_native_review_sha256='f' * 64)
        forbidden.assert_not_called()
        for value in (None, object(), {'generated_scope': True}):
            with self.assertRaises(ValueError): admission.CapturedMinuteProvider(2022, value)
            with self.assertRaises(ValueError):
                with admission.admit_case(value, cell_id=entry.tranche_cells(entry.FIRST6)[0], go_raw=b'{}', expected_go_sha256='a' * 64,
                    review_raw=b'{}', expected_review_sha256='b' * 64, prepared_review_raw=b'{}', expected_prepared_review_sha256='c' * 64,
                    native_review_raw=b'{}', expected_native_review_sha256='d' * 64): self.fail('MINTED')

    def test_driver_authority_failure_precedes_lease_claim_and_spawn(self):
        import run_cs
        with patch.object(run_cs, 'wires', side_effect=ValueError('FAKE_AUTHORITY_DENIED')), \
             patch.object(runtime, 'controller_lease') as lease, patch.object(runtime, 'claim_launch') as claim, \
             patch.object(runtime.subprocess, 'Popen') as spawn:
            with self.assertRaisesRegex(ValueError, 'FAKE_AUTHORITY_DENIED'): run_cs.controller(SimpleNamespace())
        lease.assert_not_called(); claim.assert_not_called(); spawn.assert_not_called()

    def test_current_module_identity_cannot_reuse_an_old_flat_source_alias(self):
        with patch.object(gate.source_entry, '__file__', str(c.ROOT / 'original_cs_mom21_D_20261015_v3/cs_entry.py')):
            with self.assertRaisesRegex(ValueError, 'MODULE_IDENTITIES_REQUIRED'): gate.code_identity()


def fake_guard():
    zeros = dict.fromkeys(SourceOnlyGuard.CATEGORIES, 0)
    return dict(schema='OBSERVED_PORTABLE_CS_SOURCE_GUARD_V2', status='PASS_FINANCIAL_WORKER_SOURCE_ONLY_RECAPTURE',
        forbidden_attempts=zeros, error=None, attempted_targets=[], guard_active=False,
        historical_execution_authorized=False, financial_execution_authorized=False,
        source_scopes_revoked=True, saved_targets_and_covariance_rebuilt=False,
        observed_workspace_read_paths={'/FAKE_GENERATED_METADATA_ONLY.py': 1},
        checkpoints=[dict(label=label, attempts=deepcopy(zeros)) for label in (
            'FRESH_WORKER_CS_SOURCE_RECAPTURE_BEFORE_FINANCE_IMPORT', 'EXACT_SAVED_CS_TARGETS_LOADED_WITHOUT_REGENERATION')])


class SavedOnlyValidationTests(unittest.TestCase):
    def test_guard_receipt_exact_categories_observed_zero_and_checkpoints(self):
        saved.saved_source_guard(fake_guard())
        for key, value in (('forbidden_attempts', {}), ('guard_active', True), ('source_scopes_revoked', False),
                           ('error', 'CAUGHT'), ('attempted_targets', [{}]), ('checkpoints', []), ('observed_workspace_read_paths', {})):
            bad = fake_guard(); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): saved.saved_source_guard(bad)
        bad = fake_guard(); bad['forbidden_attempts']['network_calls'] = False
        with self.assertRaises(ValueError): saved.saved_source_guard(bad)

    def test_minute_positive_and_hostile_headers_deny_before_allocation(self):
        stream = BytesIO(); np.savez_compressed(stream, values=np.ones((3, 2)), columns=np.array(['a', 'b']))
        values, names = saved.saved_minute(stream.getvalue(), 3)
        self.assertEqual(values.shape, (3, 2)); self.assertEqual(names, ['a', 'b'])
        for shape, dtype, fortran in (((10 ** 12, 2), '<f8', False), ((3, 2), '<f4', False),
                                       ((3, 2), '|O', False), ((3, 2), '<f8', True)):
            header = BytesIO(); np.lib.format.write_array_header_1_0(header, dict(shape=shape, descr=dtype, fortran_order=fortran))
            columns = BytesIO(); np.save(columns, np.array(['a', 'b']), allow_pickle=False)
            archive = BytesIO()
            with zipfile.ZipFile(archive, 'w') as z:
                z.writestr('values.npy', header.getvalue()); z.writestr('columns.npy', columns.getvalue())
            with patch.object(np, 'load', side_effect=AssertionError('NO_ALLOCATION')) as load, self.assertRaises(ValueError):
                saved.saved_minute(archive.getvalue(), 3)
            load.assert_not_called()

    def test_saved_profile_and_tier_metadata_reconstructed_without_account(self):
        native = generated.native_reference(); engine = native.V2.ENGINE
        profile = c.exact_object((c.ROOT / 'bounded_account_continuation_20261015/QUANTITY_PROFILE.json').read_bytes())
        for tier in config.TIERS:
            cfg = engine.PerpetualConfig(initial_cash='10000', max_gross_weight=str(config.TIER_GROSS_CAPS[tier]),
                max_asset_weight='.30', leverage='1', half_spread_bps='4', slippage_bps='4')
            profiles = {s: engine.InstrumentProfile(quantity_step=profile['rows'][s]['quantity_step'], min_notional='10').metadata() for s in native.S}
            binding = {'FAKE_METADATA_ONLY': True}
            contract = dict(symbols=list(native.S), bound_nominal_tier=tier, free_cash_floor='1000', total_isolated_ceiling='8500',
                leverage=1, nominal_roundtrip_bps=27., taker_fee_bps_per_side=5.5, topup_enabled=False,
                policy_variant='GUARD50_EXIT_ONLY', quantity_profile_binding='FROZEN_COARSE_RESEARCH_PROFILE',
                historical_execution_admitted=True, generated_only=False, closing_min_notional_exempt=True,
                instrument_profiles=profiles, scope_binding=binding)
            audit = dict(symbols=list(native.S), positions=dict.fromkeys(native.S), marks=dict.fromkeys(native.S),
                config={f.name: str(getattr(cfg, f.name)) for f in fields(cfg)}, instrument_profiles=profiles,
                closing_min_notional_exempt=True, cost_context=None, bound_nominal_tier=tier,
                historical_execution_admitted=True, contract=contract, historical_execution_scope=binding)
            common = dict(tier=tier, gross_ceiling=config.TIER_GROSS_CAPS[tier], asset_ceiling=.30,
                annual_covariance_volatility_ceiling=config.TIER_BUDGETS[tier], initial_cash='10000',
                free_cash_increase_floor='1000', actual_isolated_margin_ceiling='8500', automatic_topup=False,
                policy_variant='GUARD50_EXIT_ONLY', historical_execution_admitted=True)
            saved.saved_account_contract(audit, {'common_execution_policy': common}, tier)
            for key, value in (('symbols', list(reversed(native.S))), ('cost_context', {}), ('closing_min_notional_exempt', False)):
                bad = deepcopy(audit); bad[key] = value
                with self.subTest(tier=tier, key=key), self.assertRaises(ValueError): saved.saved_account_contract(bad, {'common_execution_policy': common}, tier)
            bad = deepcopy(audit); bad['instrument_profiles']['BTCUSDT']['quantity_step'] = '.00001'
            with self.assertRaises(ValueError): saved.saved_account_contract(bad, {'common_execution_policy': common}, tier)

    def test_resource_fake_metadata_contradictions_deny(self):
        receipt = dict(cell_id='FAKE', requested_CPU=4, PID=101, controller_PID=100,
                       process_start_ticks='123', controller_lease_inode=99)
        bootstrap = dict(schema='STDLIB_PRE_NUMERICAL_IMPORT_RESOURCE_BOOTSTRAP_V1', PID=101, requested_CPU=4,
            actual_affinity=[4], limits={'AS': [4000000000] * 2, 'CPU': [600] * 2, 'RSS': [2000000000] * 2},
            thread_environment={key: '1' for key in runtime.THREAD_ENV})
        owner = dict(cell_id='FAKE', PID=101, CPU=4, controller_PID=100, process_start_ticks='123')
        claim = dict(controller_PID=100, controller_output='/FAKE')
        saved.saved_resources(receipt, bootstrap, owner, claim, lease_inode=99, directory='/FAKE/CASE')
        for target, key, value in ((bootstrap, 'PID', 102), (bootstrap, 'actual_affinity', [4, 5]),
                (owner, 'process_start_ticks', '124'), (claim, 'controller_PID', 101), (receipt, 'controller_lease_inode', 98)):
            changed = [deepcopy(x) for x in (receipt, bootstrap, owner, claim)]
            changed[[receipt, bootstrap, owner, claim].index(target)][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                saved.saved_resources(*changed, lease_inode=99, directory='/FAKE/CASE')


if __name__ == '__main__': unittest.main()
