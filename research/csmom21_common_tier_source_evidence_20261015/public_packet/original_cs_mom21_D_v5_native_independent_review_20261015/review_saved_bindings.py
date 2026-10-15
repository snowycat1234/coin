"""Invented saved-resource/source-quality records only; no account or scope."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_common as c
import cs_saved as saved
import cs_process_runtime as r


def resources():
    receipt=dict(requested_CPU=4,PID=101,controller_PID=100,process_start_ticks='12345',cell_id='GENERATED_ONLY_FAKE_CELL',controller_lease_inode=987)
    limits={name:[value,value] for name,value in [('AS',4000000000),('CPU',600),('RSS',2000000000)]}
    bootstrap=dict(schema='STDLIB_PRE_NUMERICAL_IMPORT_RESOURCE_BOOTSTRAP_V1',PID=101,requested_CPU=4,actual_affinity=[4],limits=limits,
                   thread_environment={key:'1' for key in r.THREAD_ENV})
    owner=dict(cell_id=receipt['cell_id'],PID=101,CPU=4,controller_PID=100,process_start_ticks='12345')
    claim=dict(controller_PID=100,controller_output='/GENERATED_ONLY_FAKE_ROOT')
    return receipt,bootstrap,owner,claim


def call(records,**kw):
    return saved.saved_resources(*records,lease_inode=kw.get('lease_inode',987),directory='/GENERATED_ONLY_FAKE_ROOT/FAKE_CASE')


def quality(cells):
    sidecar=dict(cells=cells,qualified_source_identity='a'*64,arrival_status='UNKNOWN_NOT_CERTIFIED',
        original_source_age_and_arrival_flags_preserved=True,actual_CS_event_impacts='PENDING_CS_SAVED_EXECUTION',
        actual_CS_position_interval_impacts='PENDING_CS_SAVED_EXECUTION_NOT_INHERITED_FROM_D')
    info=dict(quality_cells_SHA256=c.jsha(cells),source_identity='a'*64,source_quality_sidecar_SHA256='b'*64)
    return sidecar,info


class SavedBindingReview(unittest.TestCase):
    def test_pure_resource_positive(self):self.assertIsNone(call(resources()))
    def test_every_bootstrap_field_missing_or_changed_rejected(self):
        records=resources()
        for key in records[1]:
            bad=deepcopy(records);del bad[1][key]
            with self.subTest(missing=key),self.assertRaises(ValueError):call(bad)
        for key,value in [('PID',102),('requested_CPU',5),('actual_affinity',[4,5]),('limits',{}),('thread_environment',{})]:
            bad=deepcopy(records);bad[1][key]=value
            with self.subTest(changed=key),self.assertRaises(ValueError):call(bad)
    def test_owner_controller_starttick_and_lease_mismatches_rejected(self):
        records=resources()
        for key,value in [('cell_id','OTHER'),('PID',102),('CPU',5),('controller_PID',99),('process_start_ticks','12346')]:
            bad=deepcopy(records);bad[2][key]=value
            with self.subTest(owner=key),self.assertRaises(ValueError):call(bad)
        for key,value in [('controller_PID',99),('controller_output','/OTHER_ROOT')]:
            bad=deepcopy(records);bad[3][key]=value
            with self.subTest(claim=key),self.assertRaises(ValueError):call(bad)
        with self.assertRaises(ValueError):call(records,lease_inode=988)
    def test_invalid_process_id_parent_and_starttick_predicates_rejected(self):
        records=resources()
        for key,value in [('controller_PID',101),('controller_PID',0),('process_start_ticks',''),('process_start_ticks','abc')]:
            bad=deepcopy(records);bad[0][key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):call(bad)
    def test_pure_no_gap_quality_identity_has_no_invented_gap_cells(self):
        sidecar,info=quality([]);identity=saved.quality_identity(sidecar,info,'FAKE_FIXED_VERSION')
        self.assertEqual(identity['intervals'],[]);self.assertNotIn('source_clock_cells',identity)
        self.assertFalse(identity['native_venue_or_current_mark_certified'])
        self.assertEqual(identity['source_sidecar_sha256'],'b'*64)
    def test_generated_gap_quality_identity_binds_all_cell_bytes(self):
        sidecar,info=quality([dict(symbol='FAKE_ASSET',minute_open_us=60000000,anchor_completed_us=0)])
        identity=saved.quality_identity(sidecar,info,'FAKE_FIXED_VERSION')
        self.assertEqual(identity['source_clock_cells'],sidecar['cells']);self.assertTrue(identity['per_asset_genuine_recovery_required'])
        changed=deepcopy(sidecar);changed['cells'][0]['anchor_completed_us']=1
        with self.assertRaises(ValueError):saved.quality_identity(changed,info,'FAKE_FIXED_VERSION')
    def test_quality_source_arrival_actual_impact_and_D_borrowing_mutations_rejected(self):
        sidecar,info=quality([])
        for key,value in [('qualified_source_identity','c'*64),('arrival_status','KNOWN_GENUINE'),
            ('original_source_age_and_arrival_flags_preserved',False),('actual_CS_event_impacts','ZERO_INHERITED_FROM_D'),
            ('actual_CS_position_interval_impacts','ZERO_INHERITED_FROM_D')]:
            bad=deepcopy(sidecar);bad[key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):saved.quality_identity(bad,info,'FAKE_FIXED_VERSION')

if __name__=='__main__':unittest.main(verbosity=2)
