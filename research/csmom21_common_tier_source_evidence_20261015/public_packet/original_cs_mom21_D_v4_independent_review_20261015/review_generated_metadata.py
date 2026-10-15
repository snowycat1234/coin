"""Independent fake metadata/recording scopes only; never admits source/history."""
from contextlib import ExitStack
from copy import deepcopy
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v4'))
import cs_common as c
import cs_config as config
import cs_entry as entry

CONTRACTS=json.loads((c.HERE/'SOURCE_CONTRACT_MAP.json').read_bytes())
CODE='1'*64;SCOPE='2'*64;CONTRACT='3'*64

def fixture():
    tranche=entry.FIRST6;ordered=entry.tranche_cells(tranche)
    artifacts={'SOURCE_STAGE_AUTHORIZATION.json':dict(SHA256='4'*64,bytes=1),
               'SOURCE_INDEPENDENT_REVIEW.json':dict(SHA256='5'*64,bytes=1)}
    years={};cells={}
    for year in entry.tranche_years(tranche):
        period=config.period_named(year);contract=CONTRACTS['years'][str(year)]
        keys=['decision_us','annual_covariance','weekly_raw_CS','original_sized_CS']+[config.STRATEGY+'_'+t for t in config.TIERS]
        hashes={key:c.jsha(['INVENTED_FIXTURE_ARRAY',year,key]) for key in keys}
        info=dict(source_identity=contract['source_identity'],source_contract_SHA256=c.jsha(contract),days=period['days'],
            calendar=[period['start'],period['end']],provider_months_source='MEMORY_ONLY_EXACT_OLD_NATIVE_CAPTURE' if year==2022 else 'EXISTING_PINNED_CANONICAL_MONTHS',
            quality_cells_SHA256=contract.get('normalized_quality_cells_SHA256',c.jsha([])),all_CS_position_and_event_impacts_pending=True,
            source_quality_sidecar_SHA256=c.jsha(['INVENTED_FIXTURE_QUALITY',year]),source_rows_SHA256=c.jsha(['INVENTED_FIXTURE_ROWS',year]),
            funding_events_SHA256=c.jsha(['INVENTED_FIXTURE_FUNDING',year]),array_raw_SHA256=hashes)
        years[str(year)]=info
        names=['TARGETS.npz','SOURCE_INPUTS.npz','RAW_EVENTS.json','MINUTE_MARK_PROVENANCE.json','TARGET_PROOFS.json']
        if year==2022:names.append('NORMALIZATION_EQUIVALENCE.json')
        for name in names:artifacts[str(year)+'/'+name]=dict(SHA256=info['source_quality_sidecar_SHA256'] if name=='MINUTE_MARK_PROVENANCE.json' else c.jsha(['INVENTED_FIXTURE_ARTIFACT',year,name]),bytes=1)
        for cell_id in ordered:
            cell=config.cell_named(cell_id)
            if cell['year']!=year:continue
            tier=cell['tier'];binding=dict(schema='EXACT_NEW_CS_CELL_SOURCE_TARGET_BINDING_V2',cell_id=cell_id,
                strategy=config.STRATEGY,year=year,tier=tier,calendar=[cell['start_us'],cell['end_exclusive_us']],
                source_identity=contract['source_identity'],source_contract_SHA256=c.jsha(contract),source_rows_SHA256=info['source_rows_SHA256'],
                funding_events_SHA256=info['funding_events_SHA256'],source_quality_sidecar_SHA256=info['source_quality_sidecar_SHA256'],quality_cells_SHA256=info['quality_cells_SHA256'],
                provider_months=[[r['path'],r['start'],r['count'],r['hash'],r['size'],r['lo'],r['hi']] for r in contract['months']],
                decision_raw_SHA256=hashes['decision_us'],covariance_raw_SHA256=hashes['annual_covariance'],weekly_raw_CS_SHA256=hashes['weekly_raw_CS'],
                original_sized_CS_SHA256=hashes['original_sized_CS'],selected_target_raw_SHA256=hashes[config.STRATEGY+'_'+tier],cost='BASE27',policy_variant='GUARD50_EXIT_ONLY',
                quantity_profile_SHA256='94b2238b25ed345a24a1fa148c6f35523b8efe9bf47496958028844432cb8ebf')
            cells[cell_id]=dict(descriptor=cell,input_binding=binding,input_binding_SHA256=c.jsha(binding))
    return dict(schema='PREPARED_CSMOM21_SOURCE_TARGET_ONLY_V2',candidate=config.STRATEGY,tranche=tranche,ordered_cells=list(ordered),years=years,cells=cells,
        code_manifest_SHA256=CODE,scope_manifest_SHA256=SCOPE,source_contract_map_SHA256=CONTRACT,source_stage_GO_SHA256='4'*64,source_review_SHA256='5'*64,artifacts=artifacts,
        historical_admission=False,financial_runs=0,accounts_created=0,accounts_advanced=0,provider_iterations=0,process_launches=0,canonical_claims_created=0,real_financial_GO_written=0,publication_actions=0)

class MetadataReview(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack()
        for name,value in [('code_identity',CODE),('manifest_sha',SCOPE),('contract_sha',CONTRACT),('contracts',CONTRACTS)]:
            self.stack.enter_context(patch.object(entry,name,return_value=value))
    def tearDown(self):self.stack.close()
    def test_01_exact_first6_recording_only_scopes_revoke(self):
        p=fixture();self.assertEqual(entry.validate_preparation_metadata(c.canonical(p)),p)
        observed=[]
        receipt=entry.record_metadata_bindings(p,lambda scope:(scope.validate_current(),observed.append(scope)))
        self.assertEqual(receipt['ordered_cells'],list(entry.tranche_cells(entry.FIRST6)))
        self.assertEqual(len(observed),6);self.assertTrue(receipt['metadata_scopes_revoked'])
        self.assertEqual(receipt['historical_scopes_created'],0);self.assertEqual(receipt['accounts_created'],0);self.assertEqual(receipt['actual_provider_iterations'],0)
        for scope in observed:
            with self.assertRaisesRegex(ValueError,'REVOKED'):scope.validate_current()
        self.assertEqual(entry._ACTIVE_SOURCE,{});self.assertEqual(entry._ACTIVE_FINANCIAL,{})
    def test_02_resealed_cell_binding_mutations_fail_closed(self):
        original=fixture();cell_id=entry.tranche_cells(entry.FIRST6)[0]
        replacements={'year':2025,'tier':'HIGH','calendar':[0,1],'source_identity':'a'*64,'source_contract_SHA256':'b'*64,
            'source_rows_SHA256':'c'*64,'funding_events_SHA256':'d'*64,'source_quality_sidecar_SHA256':'e'*64,'quality_cells_SHA256':'f'*64,
            'decision_raw_SHA256':'a'*64,'covariance_raw_SHA256':'b'*64,'weekly_raw_CS_SHA256':'c'*64,'original_sized_CS_SHA256':'d'*64,
            'selected_target_raw_SHA256':'e'*64,'cost':'FREE','policy_variant':'TOPUP','quantity_profile_SHA256':'f'*64}
        for key,value in replacements.items():
            p=deepcopy(original);record=p['cells'][cell_id];record['input_binding'][key]=value;record['input_binding_SHA256']=c.jsha(record['input_binding'])
            with self.subTest(key=key),self.assertRaises(ValueError):entry.validate_preparation_metadata(c.canonical(p))
        p=deepcopy(original);record=p['cells'][cell_id];record['input_binding']['provider_months'][0][3]='a'*64;record['input_binding_SHA256']=c.jsha(record['input_binding'])
        with self.assertRaises(ValueError):entry.validate_preparation_metadata(c.canonical(p))
    def test_03_year_scope_quality_duplicate_and_GO_lineage_fail_closed(self):
        original=fixture()
        mutations=[lambda p:p['ordered_cells'].append(p['ordered_cells'][0]),lambda p:p['years']['2022'].__setitem__('source_identity','a'*64),
            lambda p:p['years']['2022'].__setitem__('quality_cells_SHA256','a'*64),lambda p:p.__setitem__('source_stage_GO_SHA256','a'*64),
            lambda p:p['artifacts'].__setitem__('../ESCAPE',dict(SHA256='a'*64,bytes=1)),lambda p:p.__setitem__('accounts_created',1)]
        for fn in mutations:
            p=deepcopy(original);fn(p)
            with self.assertRaises(ValueError):entry.validate_preparation_metadata(c.canonical(p))
    def test_04_source_metadata_wire_is_immutable_external_and_first6_bound(self):
        review=dict(schema=entry.SOURCE_REVIEW_SCHEMA,status='PASS',code_manifest_SHA256=CODE,scope_manifest_SHA256=SCOPE,
            source_contract_map_SHA256=CONTRACT,tranche=entry.FIRST6,ordered_cells=list(entry.tranche_cells(entry.FIRST6)),years=[2022,2023],old_D_GO_reused_as_authority=False)
        reviewraw=c.canonical(review);rsha=c.sha(reviewraw);policy=entry.source_policy(entry.FIRST6,rsha);raw=c.canonical(policy)
        result=entry.validate_source_authority_metadata(raw,c.sha(raw),reviewraw,rsha)
        with self.assertRaises(TypeError):result['policy']['years']=(2025,)
        with self.assertRaises(ValueError):entry.validate_source_authority_metadata(raw,'a'*64,reviewraw,rsha)
        changed=deepcopy(review);changed['tranche']=entry.REMAINING9;changedraw=c.canonical(changed)
        with self.assertRaises(ValueError):entry.validate_source_authority_metadata(raw,c.sha(raw),changedraw,c.sha(changedraw))
        with self.assertRaises(ValueError):entry.source_policy(entry.REMAINING9,rsha)
        self.assertFalse(policy['source_only_2022_cache_creation_authorized']);self.assertFalse(policy['account_construction_authorized'])
        self.assertEqual(entry._ACTIVE_SOURCE,{})
    def test_05_old_review_and_scope_types_cannot_admit(self):
        with self.assertRaises(ValueError):entry.SourcePreparationScope(entry.FIRST6,'a'*64,'b'*64,b'',b'',CODE,object(),object())
        old=dict(schema='INDEPENDENT_ORIGINAL_CS_REVIEW_V1',status='PASS')
        raw=c.canonical(old)
        with self.assertRaises(ValueError):entry._review(raw,c.sha(raw),entry.SOURCE_REVIEW_SCHEMA,tranche=entry.FIRST6)
    def test_06_strict_duplicate_nonfinite_json(self):
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}',b'{"x":Infinity}'):
            with self.assertRaises(ValueError):c.exact_object(raw)

if __name__=='__main__':unittest.main(verbosity=2)
