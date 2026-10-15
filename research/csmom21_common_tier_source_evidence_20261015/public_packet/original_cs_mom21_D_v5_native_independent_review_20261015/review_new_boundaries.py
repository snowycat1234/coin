"""Pure exact FIRST6 wrappers and invented saved worker phase mutations."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_common as c
import cs_entry as entry
import cs_verified_wires as v
import cs_saved as saved
from test_cs_entry import fake_preparation


def phases():
    receipt=dict(cell_id='GENERATED_ONLY_CELL',root_GO_SHA256='a'*64,preparation_SHA256='b'*64,PID=123,
                 financial_code_manifest_SHA256='c'*64)
    fixed=dict(schema='CS_WORKER_PREFINANCE_PHASE_V1',cell_id=receipt['cell_id'],root_GO_SHA256='a'*64,
               preparation_SHA256='b'*64,PID=123,historical_scopes_constructed=0,providers_constructed=0,accounts_constructed=0)
    first=dict(fixed,phase='EXACT_EXECUTABLE_GO_VERIFIED_OUTSIDE_UNCHANGED_SOURCE_GUARD',
        financial_code_manifest_SHA256='c'*64,claim_SHA256=c.sha(b'GENERATED_CLAIM'),source_capture_started=False,UTC='2026-10-15T16:00:00.000000Z')
    second=dict(fixed,phase='SOURCE_RECAPTURE_AND_SAVED_TARGET_BINDING_ACCEPTED_GUARD_EXITED',
        source_guard_receipt_SHA256=c.sha(b'GENERATED_GUARD'),verified_wires_revoked=True,UTC='2026-10-15T16:00:01.000000Z')
    return first,second,dict(receipt=receipt,claim_raw=b'GENERATED_CLAIM',source_guard_raw=b'GENERATED_GUARD')


class NewBoundaryReview(unittest.TestCase):
    def test_frozen_actual_preparation_metadata_is_exact_wrapper_only(self):
        raw=(ROOT/'original_cs_mom21_D_20261015_v4/source_attempts/FIRST6_attempt001/PREPARATION.json').read_bytes()
        self.assertEqual(c.sha(raw),'8bb8c74a9c439ed1af4d22228c8243cfa12a40791642869f0031c44809b62c63')
        self.assertEqual(set(v.exact_preparation_shape(raw)['years']),{'2022','2023'})
        self.assertFalse(entry._ACTIVE_SOURCE);self.assertFalse(entry._ACTIVE_FINANCIAL)

    def test_unknown_top_year_cell_and_pin_wrappers_rejected(self):
        p=fake_preparation();cell=entry.tranche_cells(entry.FIRST6)[0]
        for label,path in [('top',()),('year',('years','2022')),('cell',('cells',cell)),('pin',('artifacts','2022/TARGETS.npz'))]:
            bad=deepcopy(p);node=bad
            for part in path:node=node[part]
            node['EXTRA_AUTHORITY_WRAPPER']=False
            with self.subTest(label=label),self.assertRaises(ValueError):v.exact_preparation_shape(c.canonical(bad))

    def test_extra_year_cell_and_artifact_scopes_rejected(self):
        p=fake_preparation()
        for label in ('year','cell','artifact'):
            bad=deepcopy(p)
            if label=='year':bad['years']['2026']=deepcopy(bad['years']['2023'])
            if label=='cell':bad['cells']['2026_UNAPPROVED_D']=deepcopy(next(iter(bad['cells'].values())))
            if label=='artifact':bad['artifacts']['2026/TARGETS.npz']=dict(SHA256='a'*64,bytes=1)
            with self.subTest(label=label),self.assertRaises(ValueError):v.exact_preparation_shape(c.canonical(bad))

    def test_missing_wrapper_and_saved_artifact_keys_rejected(self):
        p=fake_preparation()
        for key in p:
            bad=deepcopy(p);bad.pop(key)
            with self.subTest(top=key),self.assertRaises((ValueError,KeyError,TypeError)):v.exact_preparation_shape(c.canonical(bad))
        for key in p['artifacts']:
            bad=deepcopy(p);bad['artifacts'].pop(key)
            with self.subTest(artifact=key),self.assertRaises((ValueError,KeyError)):v.exact_preparation_shape(c.canonical(bad))

    def test_saved_phase_chain_positive_and_every_missing_required_field_rejected(self):
        first,second,args=phases();self.assertTrue(saved.saved_worker_phases(first,second,**args))
        for index,value in enumerate((first,second)):
            for key in value:
                bad=[deepcopy(first),deepcopy(second)];bad[index].pop(key)
                with self.subTest(index=index,missing=key),self.assertRaises((ValueError,KeyError)):saved.saved_worker_phases(*bad,**args)

    def test_saved_phase_type_claim_source_code_go_and_order_mutations_rejected(self):
        first,second,args=phases()
        for index,key,value in [(0,'accounts_constructed',False),(1,'providers_constructed',1),(0,'historical_scopes_constructed',1),
             (0,'PID',True),(0,'cell_id','OTHER'),(1,'root_GO_SHA256','f'*64),(1,'preparation_SHA256','f'*64),
             (0,'financial_code_manifest_SHA256','f'*64),(0,'claim_SHA256','f'*64),(0,'source_capture_started',True),
             (1,'source_guard_receipt_SHA256','f'*64),(1,'verified_wires_revoked',False),(1,'UTC','2026-10-15T15:59:59.000000Z')]:
            bad=[deepcopy(first),deepcopy(second)];bad[index][key]=value
            with self.subTest(index=index,key=key),self.assertRaises(ValueError):saved.saved_worker_phases(*bad,**args)
        for key in ('claim_raw','source_guard_raw'):
            bad=dict(args);bad[key]+=b'!'
            with self.subTest(key=key),self.assertRaises(ValueError):saved.saved_worker_phases(first,second,**bad)

if __name__=='__main__':unittest.main(verbosity=2)
