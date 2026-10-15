"""Generated metadata positives/negatives; no actual source or scope mints."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

import cs_common as c
import cs_config as config
import cs_entry as e
import cs_source as source


def fake_review(schema=e.SOURCE_REVIEW_SCHEMA, preparation_sha=None):
    record = dict(schema=schema, status='PASS', code_manifest_SHA256=e.code_identity(),
        scope_manifest_SHA256=e.manifest_sha(), source_contract_map_SHA256=e.contract_sha(),
        tranche=e.FIRST6, ordered_cells=list(e.tranche_cells(e.FIRST6)), years=[2022, 2023],
        old_D_GO_reused_as_authority=False)
    if preparation_sha is not None:
        record['preparation_SHA256'] = preparation_sha
    return c.canonical(record)


def fake_authority():
    review = fake_review(); go = c.canonical(e.source_policy(e.FIRST6, c.sha(review)))
    return go, c.sha(go), review, c.sha(review)


def fake_preparation():
    go, go_sha, review, review_sha = fake_authority()
    prep = dict(schema='PREPARED_CSMOM21_SOURCE_TARGET_ONLY_V2', candidate=config.STRATEGY,
        tranche=e.FIRST6, ordered_cells=list(e.tranche_cells(e.FIRST6)), years={}, cells={}, artifacts={},
        code_manifest_SHA256=e.code_identity(), scope_manifest_SHA256=e.manifest_sha(),
        source_contract_map_SHA256=e.contract_sha(), source_stage_GO_SHA256=go_sha,
        source_review_SHA256=review_sha, historical_admission=False, financial_runs=0,
        accounts_created=0, accounts_advanced=0, provider_iterations=0, process_launches=0,
        canonical_claims_created=0, real_financial_GO_written=0, publication_actions=0)
    for name, raw in (('SOURCE_STAGE_AUTHORIZATION.json', go), ('SOURCE_INDEPENDENT_REVIEW.json', review)):
        prep['artifacts'][name] = dict(SHA256=c.sha(raw), bytes=len(raw))
    for year in (2022, 2023):
        contract = e.contracts()['years'][str(year)]; period = config.period_named(year)
        fake = lambda key: c.sha(('GENERATED_METADATA_ONLY_' + str(year) + key).encode())
        hashes = {key: fake(key) for key in ('decision_us', 'annual_covariance', 'weekly_raw_CS', 'original_sized_CS',
            *(config.STRATEGY + '_' + tier for tier in config.TIERS))}
        info = dict(source_identity=contract['source_identity'], source_contract_SHA256=c.jsha(contract),
            days=period['days'], calendar=[period['start'], period['end']],
            provider_months_source='MEMORY_ONLY_EXACT_OLD_NATIVE_CAPTURE' if year == 2022 else 'EXISTING_PINNED_CANONICAL_MONTHS',
            source_quality_sidecar_SHA256=fake('sidecar'), quality_cells_SHA256=contract.get('normalized_quality_cells_SHA256', c.jsha([])),
            source_rows_SHA256=fake('rows'), funding_events_SHA256=fake('events'), array_raw_SHA256=hashes,
            all_CS_position_and_event_impacts_pending=True)
        prep['years'][str(year)] = info
        for name in ('TARGETS.npz', 'SOURCE_INPUTS.npz', 'RAW_EVENTS.json', 'MINUTE_MARK_PROVENANCE.json', 'TARGET_PROOFS.json'):
            prep['artifacts'][str(year) + '/' + name] = dict(SHA256=info['source_quality_sidecar_SHA256'] if name == 'MINUTE_MARK_PROVENANCE.json' else fake(name), bytes=1)
        if year == 2022:
            prep['artifacts']['2022/NORMALIZATION_EQUIVALENCE.json'] = dict(SHA256=fake('normalizer'), bytes=1)
        for cell_id in e.tranche_cells(e.FIRST6):
            cell = config.cell_named(cell_id)
            if cell['year'] != year:
                continue
            binding = dict(schema='EXACT_NEW_CS_CELL_SOURCE_TARGET_BINDING_V2', cell_id=cell_id,
                strategy=config.STRATEGY, year=year, tier=cell['tier'], calendar=info['calendar'],
                source_identity=contract['source_identity'], source_contract_SHA256=c.jsha(contract),
                source_rows_SHA256=info['source_rows_SHA256'], funding_events_SHA256=info['funding_events_SHA256'],
                source_quality_sidecar_SHA256=info['source_quality_sidecar_SHA256'], quality_cells_SHA256=info['quality_cells_SHA256'],
                provider_months=[[r['path'], r['start'], r['count'], r['hash'], r['size'], r['lo'], r['hi']] for r in contract['months']],
                decision_raw_SHA256=hashes['decision_us'], covariance_raw_SHA256=hashes['annual_covariance'],
                weekly_raw_CS_SHA256=hashes['weekly_raw_CS'], original_sized_CS_SHA256=hashes['original_sized_CS'],
                selected_target_raw_SHA256=hashes[config.STRATEGY + '_' + cell['tier']], cost='BASE27',
                policy_variant='GUARD50_EXIT_ONLY', quantity_profile_SHA256='94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf')
            prep['cells'][cell_id] = dict(descriptor=cell, input_binding=binding, input_binding_SHA256=c.jsha(binding))
    return prep


class AdmissionMetadataTests(unittest.TestCase):
    def test_first6_source_metadata_positive_mints_no_actual_scope(self):
        authority = e.validate_source_authority_metadata(*fake_authority())
        self.assertEqual(tuple(authority['policy']['years']), (2022, 2023))
        self.assertFalse(authority['policy']['historical_execution_authorized'])
        self.assertFalse(authority['policy']['source_only_2022_cache_creation_authorized'])
        self.assertFalse(e._ACTIVE_SOURCE); self.assertFalse(e._ACTIVE_FINANCIAL)

    def test_source_go_each_field_missing_changed_or_resealed_is_denied(self):
        go, _, review, review_sha = fake_authority(); original = c.exact_object(go)
        for key in original:
            bad = deepcopy(original); del bad[key]; raw = c.canonical(bad)
            with self.subTest(missing=key), self.assertRaises(ValueError):
                e.validate_source_authority_metadata(raw, c.sha(raw), review, review_sha)
        for key, value in (('candidate', 'STATIC50'), ('tranche', e.REMAINING9), ('financial_execution_authorized', True),
                           ('source_only_2022_cache_creation_authorized', True), ('years', [2023, 2022]),
                           ('old_D_GO_reused_as_authority', True), ('code_manifest_SHA256', 'a' * 64)):
            bad = deepcopy(original); bad[key] = value; raw = c.canonical(bad)
            with self.subTest(changed=key), self.assertRaises(ValueError):
                e.validate_source_authority_metadata(raw, c.sha(raw), review, review_sha)

    def test_source_review_wrong_code_scope_contract_tranche_or_old_authority_denied(self):
        go, _, review, _ = fake_authority()
        for key, value in (('code_manifest_SHA256', 'a'*64), ('scope_manifest_SHA256', 'a'*64),
                ('source_contract_map_SHA256', 'a'*64), ('tranche', e.REMAINING9), ('ordered_cells', []),
                ('years', [2022]), ('old_D_GO_reused_as_authority', True)):
            changed = c.exact_object(review); changed[key] = value; raw = c.canonical(changed)
            go_value = c.exact_object(go); go_value['independent_review_SHA256'] = c.sha(raw); go_raw = c.canonical(go_value)
            with self.subTest(key=key), self.assertRaises(ValueError):
                e.validate_source_authority_metadata(go_raw, c.sha(go_raw), raw, c.sha(raw))

    def test_exact_preparation_metadata_and_ephemeral_all_six_recordings(self):
        prep = fake_preparation(); e.validate_preparation_metadata(c.canonical(prep)); seen = []
        result = e.record_metadata_bindings(prep, lambda scope: (scope.validate_current(), seen.append(scope)))
        self.assertEqual(result['ordered_cells'], list(e.tranche_cells(e.FIRST6)))
        self.assertFalse(e._ACTIVE_RECORDING); self.assertFalse(e._ACTIVE_SOURCE)
        for scope in seen:
            with self.assertRaisesRegex(ValueError, 'REVOKED'): scope.validate_current()

    def test_resealed_every_cell_binding_mutation_is_denied(self):
        prep = fake_preparation(); cell_id = e.tranche_cells(e.FIRST6)[0]
        for key in prep['cells'][cell_id]['input_binding']:
            bad = deepcopy(prep); binding = bad['cells'][cell_id]['input_binding']; del binding[key]
            bad['cells'][cell_id]['input_binding_SHA256'] = c.jsha(binding)
            with self.subTest(key=key), self.assertRaises(ValueError):
                e.validate_preparation_metadata(c.canonical(bad))
        for key, value in (('tier', 'HIGH'), ('year', 2023), ('calendar', [0, 1]),
                ('source_identity', 'a'*64), ('provider_months', []), ('quality_cells_SHA256', c.jsha([])),
                ('selected_target_raw_SHA256', 'a'*64), ('cost', 'STRESS43')):
            bad = deepcopy(prep); binding = bad['cells'][cell_id]['input_binding']; binding[key] = value
            bad['cells'][cell_id]['input_binding_SHA256'] = c.jsha(binding)
            with self.subTest(changed=key), self.assertRaises(ValueError):
                e.validate_preparation_metadata(c.canonical(bad))

    def test_financial_metadata_requires_separate_exact_target_review_and_go(self):
        preparation = c.canonical(fake_preparation())
        review = fake_review(e.FINANCIAL_REVIEW_SCHEMA, c.sha(preparation)); review_sha = c.sha(review)
        go = c.canonical(e.financial_policy(preparation, e.FIRST6, review_sha))
        e.validate_financial_authority_metadata(preparation, go, c.sha(go), review, review_sha)
        self.assertFalse(e._ACTIVE_FINANCIAL)
        bad = c.exact_object(preparation); bad['source_stage_GO_SHA256'] = 'b'*64
        with self.assertRaises(ValueError):
            e.validate_financial_authority_metadata(c.canonical(bad), go, c.sha(go), review, review_sha)
        with self.assertRaises(ValueError):
            e.validate_financial_authority_metadata(preparation, go, c.sha(go), fake_review(), c.sha(fake_review()))

    def test_missing_authority_fails_before_any_source_reader_or_output(self):
        forbidden = Mock(side_effect=AssertionError('SOURCE_BODY_MUST_NOT_BE_READ'))
        with patch.object(source, 'capture_year', forbidden):
            with self.assertRaises(ValueError):
                source.prepare_source_only('/not/a/source/output', source_go_raw=b'{}', expected_source_go_sha256='a'*64,
                    review_raw=b'{}', expected_review_sha256='b'*64)
        forbidden.assert_not_called(); self.assertFalse(e._ACTIVE_SOURCE)

    def test_generated_or_old_scopes_do_not_pass_capture_or_bridge(self):
        for scope in (None, object(), {'generated_scope': True}, {'old_GO': 'a'*64}):
            with self.assertRaisesRegex(ValueError, 'EXACT_NEW_CS_SOURCE_SCOPE_REQUIRED'):
                source.capture_year(2022, scope)
        with self.assertRaisesRegex(ValueError, 'SEAL'):
            e.SourcePreparationScope(e.FIRST6, 'a'*64, 'b'*64, b'', b'', 'c'*64, object(), object())


if __name__ == '__main__':
    unittest.main()
