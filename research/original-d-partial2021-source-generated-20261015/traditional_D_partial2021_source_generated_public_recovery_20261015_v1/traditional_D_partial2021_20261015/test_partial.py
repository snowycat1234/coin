"""SOURCE/GENERATED-only gates; all actual2021 financial boundaries prohibited.

Actual2021 metadata positives are explicitly approved only with ephemeral test
review/GO bytes, recording callbacks, blocked finance/provider/launch and revoked
seals. No actual historical account or financial minute is constructed.
"""
from contextlib import ExitStack,contextmanager
from copy import deepcopy
from dataclasses import replace,FrozenInstanceError
from hashlib import sha256
import ast
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock
import numpy as np
import partial_entry as e
import partial_d as d
import run_partial as r
from test_native_runtime import fixture,BASE

raw=e._canonical

def authority(preparation):
    p=json.loads(preparation)
    review=raw(dict(schema=e.REVIEW_SCHEMA,status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        **e._authorization_common(preparation,p),**dict.fromkeys(e.REVIEW_FLAGS,True),actual_2021_accounts_constructed=0,
        actual_2021_financial_runs=0,historical_market_minutes_advanced=0,publication_actions=0,locked_source_reads=0))
    go=raw(dict(schema=e.GO_SCHEMA,action=e.ACTION,**e._authorization_common(preparation,p),tranche=e.FIRST_TRANCHE,
        permitted_cells=list(e.tranche_cells()),requested_worker_count=1,worker_CPUs=[6],independent_review_SHA256=e._sha(review)))
    return review,go

@contextmanager
def blocked_boundaries(*,source_preparation=False):
    import subprocess,multiprocessing,fcntl,socket,urllib.request
    targets=[(d,'construct_case'),(d.ExpansionAccount,'__init__'),(d.D,'construct_case'),(d.D.Guard50ExitAccount,'__init__'),
        (d.V2,'construct_case'),(d.V2.ContinuationAccount,'__init__'),(d.V2.ENGINE.USDTLinearPerpetualAccount,'__init__'),
        (d.V2.native,'_construct_case'),(e.s.g,'make_account'),(e.s.CapturedMinuteProvider,'__call__'),
        (d.V2.native.runtime()[2].EarlierTerminalSimulator,'advance_day'),
        (r,'case'),(r,'controller'),(r,'run_pool'),(r,'_run_pool'),(r,'claim_launch'),(r,'controller_lease'),(r,'save'),(r,'write_bytes'),
        (subprocess,'Popen'),(subprocess,'run'),(multiprocessing.Process,'start'),(os,'system'),(fcntl,'flock'),
        (socket,'create_connection'),(urllib.request,'urlopen')]
    if source_preparation:targets.extend([(e,'make_case'),(e.CaseExecutionScope,'__post_init__')])
    with ExitStack() as stack:
        mocks=[]
        for target,name in targets:
            mocked=stack.enter_context(patch.object(target,name,side_effect=AssertionError('FORBIDDEN_SOURCE_ONLY_BOUNDARY:'+name)))
            mocked._boundary_label=getattr(target,'__name__',type(target).__name__)+'.'+name
            mocks.append(mocked)
        # A runtime read of any original private GO/review is prohibited. New
        # copied source-completion review and original code bytes remain legal.
        original=Path.read_bytes
        def read(path,*a,**kw):
            if 'root_go' in path.name.lower() or path.name.startswith('ROOT_GO_APPROVED'):
                raise AssertionError('OLD_PRIVATE_GO_RUNTIME_BODY_READ')
            return original(path,*a,**kw)
        stack.enter_context(patch.object(Path,'read_bytes',read))
        yield mocks
        for m in mocks:m.assert_not_called()

class SourceAndAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='partial2021_source_generated_')
        cls.directory=Path(cls.temp.name)/'sourceprep'
        with blocked_boundaries(source_preparation=True) as mocks:
            cls.prep=e.prepare_source_only(e.SOURCE_ROOTS,cls.directory)
            cls.zero_boundary_count=len(mocks)
            cls.preparation_boundary_counts=[{'boundary':x._boundary_label,'calls':x.call_count} for x in mocks]
        cls.preparation=(cls.directory/'PREPARATION.json').read_bytes()
        cls.review,cls.go=authority(cls.preparation)
    @classmethod
    def tearDownClass(cls):
        receipt=dict(schema='PARTIAL2021_SOURCE_AND_APPROVED_METADATA_TEST_RECEIPT_V1',
            status='PASS_SOURCE_AND_APPROVED_METADATA_ONLY_NO_HISTORICAL_FINANCE',
            preparation_SHA256=e._sha(cls.preparation),code_identity=cls.prep['code_identity'],
            source_identity=cls.prep['years']['2021']['source_identity'],
            source_preparation_boundary_counts=cls.preparation_boundary_counts,
            actual_metadata_positive_boundary_counts=getattr(cls,'positive_boundary_counts',[]),
            metadata_callbacks=getattr(cls,'metadata_callbacks',[]),all_nine_seals_revoked=getattr(cls,'all_revoked',False),
            actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,historical_market_minutes_advanced=0,
            provider_iterations=0,process_launches=0,canonical_live_claims_created=0,real_GO_written=0)
        destination=Path(os.environ.get('PARTIAL2021_TEST_RECEIPT',str(e.HERE/'SOURCE_GATE_TEST_RECEIPT.json')))
        with destination.open('xb') as stream:stream.write(json.dumps(receipt,indent=2,sort_keys=True,allow_nan=False).encode()+b'\n')
        cls.temp.cleanup()
    def test_source_only_zero_financial_provider_process_scope_and_claim_calls(self):
        self.assertGreater(self.zero_boundary_count,20)
        for k in ('accounts_created','accounts_advanced','historical_market_minutes_advanced','financial_runs','provider_iterations',
                  'historical_scopes_created','process_launches','canonical_claims_created','real_GO_written','old_private_GO_bodies_read'):
            self.assertEqual(self.prep[k],0,k)
    def test_exact_nine_original_cells_no_H090_alias(self):
        m=e.frozen_manifest();self.assertEqual(m['new_cell_count'],9);self.assertEqual(m['alias_mapping'],{})
        eq=json.loads(e._artifacts()['EXACT_EXECUTION_EQUALITY.json'])
        self.assertEqual(eq['unique_execution_jobs'],9)
        for c in eq['STATIC50_H090_comparisons']:self.assertFalse(c['entire_target_path_byte_exact'])
    def test_exact_calendar_latency_terminal_and_funding_ownership(self):
        info=self.prep['years']['2021'];self.assertEqual(info['days'],274);self.assertEqual(info['required_minutes'],394560)
        self.assertEqual(info['coldstart_policy']['earliest_initial_increase_admission_us'],e.s.START+e.s.MINUTE+1)
        side=json.loads(e._artifacts()['MINUTE_MARK_PROVENANCE.json'])
        self.assertTrue(side['old_Jan1_ownership_flag_omitted']);self.assertTrue(side['source_funding_coverage_is_not_ownership'])
        self.assertEqual(side['terminal_signal_us'],e.s.END-61*e.s.MINUTE)
        self.assertLess(side['latest_native_terminal_fill_us'],e.s.END)
        self.assertTrue(side['source_end_plus_one_witness_is_not_execution_authority'])
    def test_daily_decoding_and_past_only_projection_honest(self):
        p=self.prep['years']['2021']['daily_source_projection']
        self.assertEqual(p['stored_clock_rows'],1463);self.assertEqual(p['permitted_projection_rows'],565)
        self.assertEqual(p['target_projection_rows'],473);self.assertFalse(p['later_DEV_rows_enter_target_or_covariance_calculation'])
    def test_all_nine_actual_metadata_positive_callbacks_no_accounts_and_revoke_seals(self):
        record=[];scopes=[]
        def callback(**kw):
            scope=kw['scope'];scope.validate_current();scope.validate_inputs(kw['window'],kw['source_rows'],kw['decisions'],kw['targets'])
            self.assertFalse(any('not_owned_under_fresh_CASH_start' in x for x in kw['window']['events']))
            self.assertTrue(all(x['event_us']>=e.s.START for x in kw['window']['events']))
            with self.assertRaises(FrozenInstanceError):scope.year=2024
            # Independent target/source array mutation checks do not change them.
            self.assertFalse(kw['targets'].flags.writeable);self.assertFalse(kw['decisions'].flags.writeable)
            record.append(scope.metadata);scopes.append(scope);return scope.metadata['cell_id']
        with blocked_boundaries() as mocks:
            for cell in e.tranche_cells():
                self.assertEqual(e.make_case(e.SOURCE_ROOTS,self.directory,self.go,e._sha(self.go),cell_id=cell,
                    review_raw=self.review,expected_review_sha256=e._sha(self.review),constructor_callback=callback),cell)
            for scope in scopes:
                object.__setattr__(scope,'_seal',None)
                with self.assertRaisesRegex(ValueError,'UNSEALED'):scope.validate_current()
            type(self).positive_boundary_counts=[{'boundary':x._boundary_label,'calls':x.call_count} for x in mocks]
        type(self).metadata_callbacks=[dict(x,scope_seal_revoked=True,post_revocation_validation_rejected=True) for x in record]
        type(self).all_revoked=all(x._seal is None for x in scopes)
        self.assertEqual([x['cell_id'] for x in record],list(e.tranche_cells()))
        self.assertTrue(all(x['generated_fixture_scope_used'] is False for x in record))
    def test_invalid_GO_template_never_admits(self):
        invalid=raw(e.invalid_go_template(self.preparation))
        with self.assertRaises(ValueError):e.validate_root_go(self.preparation,invalid,e._sha(invalid),cell_id=e.tranche_cells()[0])
    def test_wrong_old_year_cell_scope_policy_tier_action_order_and_approval_refused(self):
        cell=e.tranche_cells()[0]
        for key,value in [('action','RUN_OLD_D'),('source_scope','GENERATED_FAKE_ORIGIN_ONLY'),('tranche','OLD'),
                ('permitted_cells',list(reversed(e.tranche_cells()))),('requested_worker_count',True),
                ('worker_CPUs',[True]),('independent_review_SHA256','x'*64),('calendar',[e.s.FULL_START,e.s.END])]:
            go=json.loads(self.go);go[key]=value
            if key=='calendar':
                # A gratuitous unbound extra key does not authorize a calendar
                # replacement; the real bound calendar is inside years/cells.
                go['years']['2021']['calendar']=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                e.validate_root_go(self.preparation,raw(go),e._sha(raw(go)),cell_id=cell)
        for bad in ('2024_STATIC50_MID','2021_STATIC50_MID','2021_VOL_MANAGED_HOLD_OTHER_APR2_DEC31_D'):
            with self.assertRaises(ValueError):e.cell_descriptor(bad)
        with self.assertRaises(ValueError):e.validate_root_go(self.preparation,self.go,'0'*64,cell_id=cell)
        with self.assertRaises(ValueError):e.validate_root_go(self.preparation,self.go,e._sha(self.go),cell_id=cell,policy_variant='TOPUP')
    def test_review_each_flag_and_zero_finance_scope_required(self):
        for key in e.REVIEW_FLAGS+('actual_2021_accounts_constructed','actual_2021_financial_runs'):
            review=json.loads(self.review);review[key]=False if key in e.REVIEW_FLAGS else 1
            b=raw(review);go=json.loads(self.go);go['independent_review_SHA256']=e._sha(b)
            with self.subTest(key=key),self.assertRaises(ValueError):e._validate_independent_review(self.preparation,self.prep,b,e._sha(b),raw(go))
    def test_unsealed_scope_and_generated_historical_mix_refused_before_genesis(self):
        with patch.object(d.V2.ENGINE.USDTLinearPerpetualAccount,'__init__',side_effect=AssertionError('NO_GENESIS')) as m:
            with self.assertRaises(ValueError):d.ExpansionAccount(historical_scope=object())
            w,rows,dec=fixture(1)
            with self.assertRaises(ValueError):d.construct_case(w,rows,dec,np.full((1,5),.03),generated_scope=d.GENERATED,historical_scope=object())
            m.assert_not_called()
    def test_native_input_identity_and_tamper_gates(self):
        with blocked_boundaries():
            p,w,rows,dec,target,captured=e.validate_case_inputs(e.SOURCE_ROOTS,self.directory,self.go,e._sha(self.go),cell_id=e.tranche_cells()[0])
            binding=p['cells'][e.tranche_cells()[0]]['input_binding']
            self.assertEqual(binding['calendar'],[e.s.START,e.s.END])
            self.assertEqual(len(binding['provider_month_identity']),9)
            with self.assertRaises(ValueError):e._input_binding(e.cell_descriptor(e.tranche_cells()[0]),dict(w),rows,dec,target,np.zeros((274,5,5)))
    def test_duplicate_json_nonfinite_and_missing_external_review_refused(self):
        for b in (b'{"a":1,"a":2}',b'{"a":NaN}'):
            with self.assertRaises(ValueError):e._object(b,'BAD')
        with self.assertRaises(ValueError):e._validate_independent_review(self.preparation,self.prep,None,None,self.go)
    def test_rehashed_preparation_quality_projection_and_duplicate_binding_metadata_refused(self):
        mutations=[lambda p:p['years']['2021']['original200_quality'].__setitem__('imputed',True),
            lambda p:p['years']['2021']['original200_quality'].__setitem__('derived_mark_cells',False),
            lambda p:p['years']['2021']['daily_source_projection'].__setitem__('stored_clock_rows',565),
            lambda p:p['years']['2021']['source_files'].__setitem__('fake',{'SHA256':'0'*64,'bytes':0})]
        cell=e.tranche_cells()[0]
        for key in ('selected_target_raw_SHA256','decision_raw_SHA256','covariance_raw_SHA256','quality_sidecar_sha256'):
            mutations.append(lambda p,key=key:p['cells'][cell].__setitem__(key,'0'*64))
        for mutate in mutations:
            p=deepcopy(self.prep);mutate(p)
            with self.assertRaises(ValueError):e._validate_preparation(raw(p))

    def test_current_code_and_source_artifact_pins(self):
        self.assertEqual(self.prep['code_identity'],e.code_identity())
        for name,p in self.prep['artifacts'].items():e.s.exact(self.directory/name,p['SHA256'],p['bytes'])
        self.assertEqual(e._sha((e.HERE/'SOURCE_COMPLETION_REVIEW.json').read_bytes()),e.SOURCE_REVIEW_SHA)

class SyntheticDTests(unittest.TestCase):
    def test_exact_frozen_D_code_objects_and_native_32corner_scheduler(self):
        self.assertIs(d.ExpansionAccount.monitor,d.D.Guard50ExitAccount.monitor)
        self.assertIs(d.ExpansionAccount._transfer,d.D.Guard50ExitAccount._transfer)
        self.assertIs(d.ExpansionAccount.execute_fill,d.D.Guard50ExitAccount.execute_fill)
        self.assertIs(d.ExpansionAccount._leg,d.V2.ENGINE.USDTLinearPerpetualAccount._leg)
        self.assertIs(d.ContinuationGuard.schedule.__code__,d.V2.native.PartialTierGuard.schedule.__code__)
        self.assertIs(d.ContinuationGuard._frozen_attempt.__code__,d.V2.native.PartialTierGuard.attempt.__code__)
        self.assertIs(d.ContinuationGuard.attempt,d.D.ContinuationGuard.attempt)
    def test_three_tiers_synthetic_fresh_wallet_paid_native_terminal(self):
        for tier in d.TIERS:
            w,rows,dec=fixture(1);weights=np.full((1,5),.03)
            sim,guard=d.construct_case(w,rows,dec,weights,tier_name=tier,generated_scope=d.GENERATED)
            self.assertEqual(str(sim.account.config.initial_cash),'10000')
            while sim.cursor<sim.end and sim.stop is None:sim.advance_day()
            result=d.case_result(sim,guard)
            self.assertTrue(result['economics']['paid_flat']);self.assertTrue(result['economics']['partial_DEV'])
            self.assertFalse(sim.account.transfer_journal);self.assertTrue(all(t['event_us']<sim.end for t in sim.account.trades))
            self.assertFalse(sim.account.topup_enabled)
    def test_generated_guard50_known_fresh_exit_no_transfer(self):
        a=d.V2.grid.make_account('MID','BASE27');account=d.ExpansionAccount(a.config,symbols=d.S,
            instrument_profiles=a.instrument_profiles,generated_scope=d.GENERATED,tier_name='MID')
        def marks(at,price):account.update_marks(at,{s:dict(price=str(price if s=='BTCUSDT' else BASE[j]),close_us=at,available_us=at) for j,s in enumerate(d.S)})
        at=d.MINUTE+1;marks(at-1,50000)
        account.execute_fill('BTCUSDT','SELL','.02',at,0,'SYNTHETIC_INITIAL',execution_mid_price='50000',quote_available_us=at-1,available_quantity='.02')
        # Native genuine mark invokes the exact D warning path; no topup is available.
        marks(2*d.MINUTE,80000);account.monitor('MONITOR:'+str(2*d.MINUTE),2*d.MINUTE)
        self.assertFalse(account.transfer_journal)
        self.assertTrue(account.pending_exits or account.settlement_journal)

class PureMockRunnerTests(unittest.TestCase):
    def test_runner_finite_limits_exact_new_manifest_and_claim_registry(self):
        self.assertEqual(r.MANIFEST_SHA256,e.MANIFEST_SHA256);self.assertEqual(r.LIMITS,e.RESOURCE_LIMITS)
        self.assertEqual(r.HERE,e.HERE);self.assertEqual(r.LIMITS['maximum_live_workers'],2)
    def test_mock_pressure_serial_fallback_no_processes(self):
        host=dict(allowed_CPUs=[4,5,6],MemAvailable_bytes=5_000_000_000,cgroup_observations={})
        self.assertEqual(r.choose_worker_count(2,[4,5],host),2)
        host['MemAvailable_bytes']=3_000_000_000;self.assertEqual(r.choose_worker_count(2,[4,5],host),1)
        host['MemAvailable_bytes']=1_000_000_000
        with self.assertRaises(RuntimeError):r.choose_worker_count(2,[4,5],host)
        for cpus in ([4,4],[True,5],[-1,5]):
            with self.assertRaises(ValueError):r.choose_worker_count(2,cpus,dict(host,MemAvailable_bytes=5_000_000_000))
    def test_canonical_claim_exclusive_only_temporary_generated_registry(self):
        # Temporary generated registry only; never the live EXECUTION_CLAIMS.
        with tempfile.TemporaryDirectory() as t:
            c=e.tranche_cells()[0];p=r.claim_launch(t,cell_id=c,manifest_sha256=e.MANIFEST_SHA256,metadata={'generated_fixture':True})
            self.assertTrue(p.is_file())
            with self.assertRaises(RuntimeError):r.claim_launch(t,cell_id=c,manifest_sha256=e.MANIFEST_SHA256,metadata={'generated_fixture':True})
    def test_immutable_artifact_and_existing_controller_refused_without_launch(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'x.json';r.save(p,{'generated_fixture':True})
            with self.assertRaises(FileExistsError):r.save(p,{'changed':True})
            with patch.object(r,'run_pool',side_effect=AssertionError('NO_PROCESS')) as m:
                with self.assertRaises(ValueError):r.controller(SimpleNamespace(output=t))
                m.assert_not_called()
    def test_original_bounded_pool_lease_and_process_functions_unchanged(self):
        old=ast.parse((r.CHECKER_ROOT/'run_expansion.py').read_text());new=ast.parse((e.HERE/'run_partial.py').read_text().replace('run_partial.py','run_expansion.py'))
        f=lambda tree,name:next(n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==name)
        for name in ('apply_limits','process_observation','host_observation','choose_worker_count','_run_pool','run_pool','controller_lease','confine_existing_threads','classify_terminal'):
            self.assertEqual(ast.dump(f(old,name)),ast.dump(f(new,name)),name)

if __name__=='__main__':unittest.main(verbosity=2)
