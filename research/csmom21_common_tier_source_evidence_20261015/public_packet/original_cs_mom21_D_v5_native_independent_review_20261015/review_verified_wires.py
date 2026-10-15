"""Independent fake metadata capability and unchanged-guard checks. No accounts."""
from contextlib import contextmanager
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from unittest.mock import patch
import sys
import unittest
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'original_cs_mom21_D_20261015_v5'))
import cs_common as c
import cs_entry as entry
import cs_finance_gate as gate
import cs_loader as loader
import cs_verified_wires as v
from cs_source_guard import SourceOnlyGuard,SourceBoundaryViolation
from test_worker_integration import fixture,bundle
CELL='2023_CSMOM21_COMMON_TIER_LOW_D'


def fake():
    prep,_,_=fixture();raw,hashes=bundle(prep)
    claim=c.canonical(dict(cell_id=CELL,root_GO_SHA256=hashes['go'],preparation_SHA256=c.sha(prep),code_identity=gate.code_identity()))
    return dict(preparation_raw=prep,cell_id=CELL,raw=raw,hashes=hashes,claim_raw=claim)


def allowed():
    paths=[]
    for manifest in ('CODE_MANIFEST.json','FINANCIAL_CODE_MANIFEST.json'):
        paths.append(c.HERE/manifest);m=c.exact_object(paths[-1].read_bytes())
        paths += [c.HERE/k for k in m['files']]+[c.ROOT/k for k in m['dependencies']]
    return paths


def call(token,kw):
    return token.consume(preparation_raw=kw['preparation_raw'],year=2023,supplied=dict(kw['raw']))


class VerifiedWireReview(unittest.TestCase):
    def tearDown(self):
        self.assertFalse(v._LIVE);self.assertFalse(loader._LIVE)
        self.assertFalse(entry._ACTIVE_SOURCE);self.assertFalse(entry._ACTIVE_FINANCIAL);self.assertFalse(entry._ACTIVE_RECORDING)

    def test_positive_exact_executable_wire_consumes_without_guard_serialization(self):
        kw=fake();paths=allowed()
        with v.verify(**kw) as token:
            guard=SourceOnlyGuard(read_paths=paths,write_roots=())
            with guard:self.assertEqual(call(token,kw),kw['hashes']['go'])
            self.assertTrue(all(x==0 for x in guard.attempts.values()))
            with self.assertRaisesRegex(ValueError,'LIVE_UNUSED'):call(token,kw)
        with self.assertRaisesRegex(ValueError,'LIVE_UNUSED'):call(token,kw)

    def test_frozen_container_and_original_dict_aliases_are_immutable(self):
        kw=fake();expected=dict(kw['raw'])
        with v.verify(**kw) as token:
            with self.assertRaises(FrozenInstanceError):token.cell_id='OTHER'
            with self.assertRaises(TypeError):token.raw['go']=b'{}'
            with self.assertRaises(TypeError):token.hashes['go']='a'*64
            kw['raw']['go']=b'{}';kw['hashes']['go']='b'*64
            self.assertEqual(dict(token.raw),expected)
            impostor=replace(token)
            with self.assertRaisesRegex(ValueError,'LIVE_UNUSED'):call(impostor,dict(kw,raw=expected))

    def test_real_guard_still_denies_executable_authority_serialization(self):
        kw=fake();go=c.exact_object(kw['raw']['go']);guard=SourceOnlyGuard()
        with self.assertRaises(SourceBoundaryViolation):
            with guard:c.canonical(go)
        self.assertEqual(guard.attempts['financial_GO_writes'],1)

    def test_verify_inside_guard_denied_before_validation(self):
        kw=fake();guard=SourceOnlyGuard()
        with guard,patch.object(gate,'validate',side_effect=AssertionError('TOO_LATE')) as validate:
            with self.assertRaisesRegex(ValueError,'MUST_PRECEDE'):
                with v.verify(**kw):self.fail('MINTED')
            validate.assert_not_called()
        self.assertTrue(all(x==0 for x in guard.attempts.values()))

    def test_wrong_external_hash_and_mutable_bytes_rejected(self):
        for mode in ('hash','bytearray','missing','extra'):
            kw=fake()
            if mode=='hash':kw['hashes']['go']='a'*64
            if mode=='bytearray':kw['raw']['go']=bytearray(kw['raw']['go'])
            if mode=='missing':kw['raw'].pop('native-review')
            if mode=='extra':kw['raw']['another']=b'{}'
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                with v.verify(**kw):self.fail('MINTED')

    def test_every_claim_binding_mismatch_denies_before_registry(self):
        for key,value in (('cell_id','2023_CSMOM21_COMMON_TIER_HIGH_D'),('root_GO_SHA256','a'*64),('preparation_SHA256','a'*64),('code_identity','a'*64)):
            kw=fake();claim=c.exact_object(kw['claim_raw']);claim[key]=value;kw['claim_raw']=c.canonical(claim)
            with self.subTest(key=key),self.assertRaises(ValueError):
                with v.verify(**kw):self.fail('MINTED')

    def test_wrong_year_preparation_or_wire_revokes_immediately(self):
        for mode in ('year','boolyear','prep','GO','review','source-GO'):
            kw=fake()
            with v.verify(**kw) as token:
                args=dict(preparation_raw=kw['preparation_raw'],year=2023,supplied=dict(kw['raw']))
                if mode=='year':args['year']=2022
                elif mode=='boolyear':args['year']=True
                elif mode=='prep':args['preparation_raw']+=b' '
                else:args['supplied'][{'GO':'go','review':'review','source-GO':'source-go'}[mode]]=b'{}'
                with self.subTest(mode=mode),self.assertRaises(ValueError):token.consume(**args)
                self.assertFalse(v._LIVE)

    def test_inventory_exception_revokes_without_waiting_for_context_exit(self):
        kw=fake();real=c.exact;seen=[]
        target=c.HERE/'cs_loader.py'
        def check(path,*args,**kwargs):
            seen.append(Path(path))
            if Path(path)==target:raise ValueError('INJECTED_PINNED_INVENTORY_CHANGE')
            return real(path,*args,**kwargs)
        with v.verify(**kw) as token,patch.object(c,'exact',side_effect=check):
            with self.assertRaisesRegex(ValueError,'INJECTED_PINNED_INVENTORY'):call(token,kw)
            self.assertIn(target,seen);self.assertFalse(v._LIVE)

    def test_context_failure_revokes_unused_and_consumed_capability(self):
        for consume in (False,True):
            kw=fake()
            with self.assertRaisesRegex(RuntimeError,'INJECTED'):
                with v.verify(**kw) as token:
                    if consume:call(token,kw)
                    raise RuntimeError('INJECTED_EXIT')
            self.assertFalse(v._LIVE)

if __name__=='__main__':unittest.main(verbosity=2)
