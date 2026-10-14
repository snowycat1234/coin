"""Independent generated-only science, admission, resource and pinned-code probes."""
import contextlib, hashlib, importlib.util, json, marshal, math, os, pathlib, shutil, struct, sys, tempfile, unittest
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
RUNNER=pathlib.Path(os.environ['REVIEW_RUNNER_ROOT']).resolve()
sys.path.insert(0,str(RUNNER))
MANIFEST=hashlib.sha256((RUNNER/'RUNNER_MANIFEST.json').read_bytes()).hexdigest()
if MANIFEST != 'd0148be6c9e3ecd24742cd005fff93b512f11a0f59346fddd5113f04c269e297':raise ValueError('EXACT_REVIEWED_FREEZE_REQUIRED')
manifest=json.loads((RUNNER/'RUNNER_MANIFEST.json').read_text())
for name,digest in manifest['files_SHA256'].items():
    source=RUNNER/name
    if source.is_symlink() or hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('RUNNER_MEMBER_IDENTITY_MISMATCH')
import types,importlib.machinery
cli=types.ModuleType('source_cli');cli.__file__=str(RUNNER/'source_cli.py')
cli.__spec__=importlib.machinery.ModuleSpec('source_cli',loader=None,origin=cli.__file__)
sys.modules['source_cli']=cli
exec(compile((RUNNER/'source_cli.py').read_bytes(),cli.__file__,'exec'),cli.__dict__)
if hasattr(cli,'bootstrap_gate'):
    gate=cli.bootstrap_gate(MANIFEST)
    for name in ('sha','read','check','import_file','verify_runner','verify_dependencies','load_paired','authorization'):setattr(cli,name,getattr(gate,name))
    a=gate.import_file('source_analysis',RUNNER/'source_analysis.py',gate.read(RUNNER/'RUNNER_MANIFEST.json')['files_SHA256']['source_analysis.py'])
else:
    import source_gate as gate
    import source_analysis as a
ROOTS=json.loads(pathlib.Path(os.environ['PAIRED_TEST_CODE_ROOTS']).read_text())
PINS,CASES=gate.verify_dependencies(ROOTS)
PAIR=gate.load_paired(ROOTS)
MANIFEST=gate.sha(RUNNER/'RUNNER_MANIFEST.json')

class Checks(unittest.TestCase):
    def test_exact_freeze_and_registry_projection(self):
        gate.verify_runner(MANIFEST)
        registry=gate.read(pathlib.Path(ROOTS['input_module'])/'INPUT_BINDINGS.json')
        for year in (2023,2024,2025):
            case=CASES['years'][str(year)]
            self.assertEqual(case,{k:registry['years'][str(year)][k] for k in case})
            self.assertEqual(len(case['months']),12)
            self.assertEqual(sum(m['minutes'] for m in case['months']), (366 if year==2024 else 365)*1440)
        self.assertEqual(CASES['years']['2024']['derived_mark_cells'],10)
        self.assertEqual(set(CASES['years']), {'2023','2024','2025'})

    def test_independent_all_six_bruteforce_full_endpoint_populations(self):
        n=43240; rng=np.random.default_rng(7162)
        times=np.arange(n,dtype=np.int64)*a.MINUTE
        marks=100*np.exp(np.cumsum(rng.normal(0,.007,n)))
        opens=np.r_[marks[0],marks[:-1]]*np.exp(rng.normal(0,.015,n))
        f=PAIR.features(times,marks,opens)
        def h(m,g,s):
            r=np.exp(np.minimum(m,0) if s==1 else np.maximum(m,0))
            ff=r*np.exp(np.minimum(g,0) if s==1 else np.maximum(g,0))*(1-s*.0008)
            return .005*r+np.abs(ff-r)+.00055*ff-s*(r-1)
        logs=np.log(marks)
        for i in (43200,43207,43239):
            mark_indices=np.arange(i-43200,i+1)
            j=np.arange(i-43200+6,i+1)
            legacy_move=np.arange(i-43200+5,i+1)
            legacy_gap=np.arange(i-43200+1,i+1)
            self.assertEqual((len(mark_indices),len(j),len(legacy_move),len(legacy_gap)),(43201,43195,43196,43200))
            m=logs[j-1]-logs[j-6]; g=np.log(opens[j])-logs[j-1]
            lm=logs[legacy_move]-logs[legacy_move-5]
            lg=np.log(opens[legacy_gap])-logs[legacy_gap-1]
            for direction,s in [('long',1),('short',-1)]:
                k=max(float(h(m,g,s).max()),float(h(0.,0.,s)))
                self.assertAlmostEqual(f[direction+'_hurdle'][i],k,places=14)
                marginal=(min if s==1 else max)
                self.assertAlmostEqual(f['aligned_independent_'+direction+'_hurdle'][i],float(h(marginal(m),marginal(g),s)),places=14)
                self.assertAlmostEqual(f['legacy_independent_'+direction+'_hurdle'][i],float(h(marginal(lm),marginal(lg),s)),places=14)

    def test_same_event_latest_open_left_edge_and_legacy_population(self):
        n=43203; t=np.arange(n,dtype=np.int64)*a.MINUTE
        marks=np.full(n,100.); opens=np.full(n,100.)
        opens[5]=10000.; opens[6]=200.; opens[43201]=1000000.
        marks[43200]=300.
        f=PAIR.features(t,marks,opens)
        self.assertAlmostEqual(f['short_hurdle'][43200],float(PAIR.pair_hurdles(0,np.log(2))['short']),places=13)
        self.assertGreater(f['legacy_independent_short_hurdle'][43200],f['aligned_independent_short_hurdle'][43200])
        self.assertGreater(f['short_hurdle'][43201],f['short_hurdle'][43200])
        m,g=PAIR.paired_observations(marks,opens)
        self.assertEqual(m[6],0)
        self.assertAlmostEqual(g[6],np.log(2),places=14)

    def test_original_readiness_43201_marks_and_no_added_warmup(self):
        n=86600;t=np.arange(n,dtype=np.int64)*a.MINUTE
        m=np.full(n,100.);o=m.copy();d=np.zeros(n,bool);d[43300]=True
        f=PAIR.features(t,m,o,d)
        self.assertFalse(f['ready'][43199]);self.assertTrue(f['ready'][43200])
        self.assertFalse(f['ready'][86500]);self.assertTrue(f['ready'][86501])
        self.assertEqual(f['reason'][86500],'DERIVED_OR_UNKNOWN_MARK')
        self.assertEqual(f['reason'][0],'WARMUP_30_COMPLETE_DAYS')
        for field in a.FIELDS: self.assertTrue(np.isnan(f[field][~f['ready']]).all())

    def test_long_counterexample_prohibits_universal_dominance(self):
        moves=np.log([.5,1.]);gaps=np.log([1.,.0001])
        paired=float(PAIR.pair_hurdles(moves,gaps)['long'].max())
        independent=float(PAIR._hurdle(moves.min(),gaps.min(),1))
        self.assertGreater(paired,independent)
        self.assertAlmostEqual(paired,1.004900134956,places=12)

    def test_authorization_adversarial_binding_mutations(self):
        common={'runner_manifest_SHA256':MANIFEST,'paired_publication_commit':gate.BASE_COMMIT,
          'source_cases_SHA256':gate.sha(RUNNER/'SOURCE_CASES.json'),'resource_policy_SHA256':gate.sha(RUNNER/'RESOURCE_POLICY.json'),
          'scope':'CACHED_MARK_TRADE_SOURCE_ONLY_NO_WALLETS'}
        review=dict(common,schema='INDEPENDENT_PAIRED_SOURCE_RUNNER_REVIEW_V1',status='PASS_CODE_TOY_ONLY_NO_HISTORICAL_EXECUTION')
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);rp=root/'generated_review.json';gp=root/'generated_go.json'
            rp.write_text(json.dumps(review));rs=gate.sha(rp)
            valid=dict(common,schema='EXPLICIT_PARENT_PAIRED_SOURCE_YEAR_GO_V1',parent_GO=True,year=2023,review_SHA256=rs,wallet_GO=False,new_market_downloads=0,source_index_SHA256=CASES['years']['2023']['index']['SHA256'])
            for field,bad in [('runner_manifest_SHA256','0'*64),('source_cases_SHA256','0'*64),('resource_policy_SHA256','0'*64),('paired_publication_commit','0'*40),('scope','WALLETS'),('parent_GO',False),('year',2024),('review_SHA256','0'*64),('wallet_GO',True),('new_market_downloads',1),('source_index_SHA256','0'*64)]:
                changed=dict(valid);changed[field]=bad;gp.write_text(json.dumps(changed))
                with self.assertRaises(ValueError,msg=field):gate.authorization(2023,MANIFEST,rp,rs,gp,gate.sha(gp))
            for excluded in (2021,2022,2026,2027):
                with self.assertRaisesRegex(ValueError,'EXCLUDED_YEAR'):gate.authorization(excluded,MANIFEST,'MISSING','0'*64,'MISSING','0'*64)

    def test_no_source_loader_under_missing_go_subprocess(self):
        # The in-process gate check above is read-only metadata; no roots ever include caches.
        with self.assertRaises(KeyError):_ = ROOTS['source2023']
        with self.assertRaises(KeyError):_ = ROOTS['source2024']
        with self.assertRaises(KeyError):_ = ROOTS['source2025']

    def test_equal_prefix_catches_float_mask_and_reason_changes(self):
        f={'ready':np.array([False,True]),'reason':np.array(['WARMUP_30_COMPLETE_DAYS','READY'])}
        f.update({k:np.array([np.nan,.1]) for k in a.FIELDS})
        for key in f:
            changed={k:v.copy() for k,v in f.items()}
            if key=='ready':changed[key][1]=False
            elif key=='reason':changed[key][1]='GENERATED_BAD_REASON'
            else:changed[key][1]=.2
            with self.assertRaisesRegex(ValueError,'PREFIX_DIFFERENCE'):a.equal_prefix(f,changed,2)

    def test_resource_dispatch_preserves_all_failure_modes_without_spawning(self):
        import signal
        policy=gate.read(RUNNER/'RESOURCE_POLICY.json')
        good={'host_used':1,'SwapTotal':0,'cgroup_swap_current':0,'cgroup_limit_verified':True,'cgroup_memory_current':1,'cgroup_memory_max':100}
        class FakeProcess:
            pid=123456
            def __init__(self,code,stopping=False):self.code=code;self.polls=0;self.stopping=stopping
            def poll(self):self.polls+=1;return None if self.stopping or self.polls==1 else self.code
            def wait(self):return self.code
        for mode in ('child_failure','rss','wall','output','disk','host','swap','cgroup','final_reserve','pass'):
            with tempfile.TemporaryDirectory() as td:
                out=pathlib.Path(td)/'attempt';args=SimpleNamespace(output=str(out),year=2023,runner_manifest_sha=MANIFEST,review_sha='0'*64,parent_go_sha='0'*64,roots=os.environ['PAIRED_TEST_CODE_ROOTS'],review='GENERATED',parent_go='GENERATED')
                fake=FakeProcess(5 if mode=='child_failure' else 0,mode not in ('pass','child_failure','final_reserve'))
                memory=dict(good)
                if mode=='host':memory['host_used']=policy['shared_host_limit_bytes']+1
                if mode=='swap':memory['SwapTotal']=1
                if mode=='cgroup':memory['cgroup_memory_current']=101
                pol=dict(policy)
                if mode=='wall':pol['wall_seconds_per_year']=0
                rss=policy['RSS_stop_bytes']+1 if mode=='rss' else 1000
                size=policy['output_total_bytes_max']+1 if mode=='output' else (policy['data_output_bytes_max']+1 if mode=='final_reserve' else 0)
                guard=SimpleNamespace(process_rss=lambda pid:rss,memory_observation=lambda:memory)
                external=SimpleNamespace(controller_lock=contextlib.nullcontext)
                with patch.object(cli,'resource_modules',return_value=(guard,external,None)),patch.object(cli,'resource_admission',return_value={'allowed_cpus':[0,1]}),patch.object(cli,'read',return_value=pol),patch.object(cli.subprocess,'Popen',return_value=fake),patch.object(cli.os,'killpg') as kill,patch.object(cli,'bytes_used',return_value=size),patch.object(cli.shutil,'disk_usage',return_value=SimpleNamespace(free=0 if mode=='disk' else 10**15)),patch.object(cli.os,'write',side_effect=lambda fd,data:len(data)):
                    if mode=='pass':cli.dispatch(args,ROOTS,PINS,CASES)
                    else:
                        with self.assertRaises(SystemExit):cli.dispatch(args,ROOTS,PINS,CASES)
                receipt=json.loads((out/'RESOURCE_RECEIPT.json').read_text())
                self.assertEqual(receipt['status'],'PASS_BOUNDED_SOURCE_ONLY' if mode=='pass' else 'FAIL_BOUNDED_SOURCE_ONLY_PRESERVED')
                self.assertTrue((out/'START.json').exists());self.assertTrue((out/'WORKER.log').exists())
                if mode in ('rss','wall','output','disk','host','swap','cgroup'):kill.assert_called_once_with(fake.pid,signal.SIGKILL)

    def test_admission_failure_and_preexisting_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            out=pathlib.Path(td)/'attempt';args=SimpleNamespace(output=str(out),year=2023,runner_manifest_sha=MANIFEST,review_sha='0'*64,parent_go_sha='0'*64)
            external=SimpleNamespace(controller_lock=contextlib.nullcontext)
            with patch.object(cli,'resource_modules',return_value=(None,external,None)),patch.object(cli,'resource_admission',side_effect=RuntimeError('GENERATED_ADMISSION_REFUSAL')),patch.object(cli.subprocess,'Popen') as popen:
                with self.assertRaisesRegex(RuntimeError,'ADMISSION_REFUSAL'):cli.dispatch(args,ROOTS,PINS,CASES)
                popen.assert_not_called()
                self.assertTrue((out/'ADMISSION_FAILURE.json').exists())
                with self.assertRaisesRegex(FileExistsError,'NO_RESUME_OR_OVERWRITE'):cli.dispatch(args,ROOTS,PINS,CASES)
                popen.assert_not_called()

class RejectedFreezeProbes(unittest.TestCase):
    @unittest.skipUnless(MANIFEST.startswith('6b563b6e'),'original rejected freeze only')
    def test_unlimited_worker_limits_reach_import_reproducer(self):
        import resource
        touched=[]
        def stop(*args):touched.append(args[0]);raise RuntimeError('GENERATED_STOP_BEFORE_SOURCE')
        with patch.dict(os.environ,{'_PAIRED_SOURCE_PARENT_PID':str(os.getppid())}),patch('os.sched_getaffinity',return_value={0}),patch('resource.getrlimit',return_value=(-1,-1)),patch.object(cli,'import_file',side_effect=stop):
            with self.assertRaisesRegex(RuntimeError,'GENERATED_STOP'):cli.worker(SimpleNamespace(year=2023),{'input_module':'GENERATED'}, {}, {})
        self.assertEqual(touched,['_paired_source_exact_input'])

    @unittest.skipUnless(MANIFEST.startswith('6b563b6e'),'original rejected freeze only')
    def test_self_declared_parent_without_controller_reaches_import_reproducer(self):
        import resource
        touched=[]
        def stop(*args):touched.append(args[0]);raise RuntimeError('GENERATED_STOP_BEFORE_SOURCE')
        def limits(which):return (4_000_000_000,4_000_000_000) if which==resource.RLIMIT_AS else (600,600)
        with patch.dict(os.environ,{'_PAIRED_SOURCE_PARENT_PID':str(os.getppid()),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}),patch('os.sched_getaffinity',return_value={0}),patch('resource.getrlimit',side_effect=limits),patch.object(cli,'import_file',side_effect=stop):
            with self.assertRaisesRegex(RuntimeError,'GENERATED_STOP'):cli.worker(SimpleNamespace(year=2023),{'input_module':'GENERATED'}, {}, {})
        self.assertEqual(touched,['_paired_source_exact_input'])

    @unittest.skipUnless(MANIFEST.startswith('6b563b6e'),'original rejected freeze only')
    def test_monitor_exception_does_not_cleanup_reproducer(self):
        class FakeProc:
            pid=123456
            def poll(self):return None
            def wait(self):return -9
        with tempfile.TemporaryDirectory() as td:
            out=pathlib.Path(td)/'attempt';args=SimpleNamespace(output=str(out),year=2023,runner_manifest_sha=MANIFEST,review_sha='0'*64,parent_go_sha='0'*64,roots=os.environ['PAIRED_TEST_CODE_ROOTS'],review='GENERATED',parent_go='GENERATED')
            guard=SimpleNamespace(process_rss=lambda pid:1000,memory_observation=lambda:(_ for _ in ()).throw(RuntimeError('GENERATED_OBSERVER_FAILURE')))
            external=SimpleNamespace(controller_lock=contextlib.nullcontext)
            with patch.object(cli,'resource_modules',return_value=(guard,external,None)),patch.object(cli,'resource_admission',return_value={'allowed_cpus':[0,1]}),patch.object(cli.subprocess,'Popen',return_value=FakeProc()),patch.object(cli.os,'killpg') as kill:
                with self.assertRaisesRegex(RuntimeError,'OBSERVER_FAILURE'):cli.dispatch(args,ROOTS,PINS,CASES)
                self.assertEqual(kill.call_count,0)
                self.assertFalse((out/'RESOURCE_RECEIPT.json').exists())

    @unittest.skipUnless(MANIFEST.startswith('6b563b6e'),'original rejected freeze only')
    def test_unverified_pyc_executes_after_pinned_source_reproducer(self):
        with tempfile.TemporaryDirectory() as td:
            source=pathlib.Path(td)/'generated.py';source.write_text('VALUE = "trusted"\n');digest=gate.sha(source)
            cached=pathlib.Path(importlib.util.cache_from_source(str(source)));cached.parent.mkdir()
            header=importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(source.stat().st_mtime),source.stat().st_size)
            cached.write_bytes(header+marshal.dumps(compile('VALUE = "UNVERIFIED_CACHED_CODE"\n',str(source),'exec')))
            gate.check(source,digest);loaded=gate.import_file('_generated_cached_identity_probe',source)
            self.assertEqual(loaded.VALUE,'UNVERIFIED_CACHED_CODE')

    @unittest.skipUnless(MANIFEST.startswith('6b563b6e'),'original rejected freeze only')
    def test_unpinned_vendor_initializer_executes_reproducer(self):
        for name in ('vendor','vendor.headroom_buffer'):sys.modules.pop(name,None)
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'vendor').mkdir()
            for rel in ('paired_buffer.py','vendor/headroom_buffer.py'):shutil.copyfile(pathlib.Path(ROOTS['paired_module'])/rel,root/rel)
            sentinel=root/'generated_initializer_ran'
            (root/'vendor/__init__.py').write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("generated")\n')
            gate.load_paired({'paired_module':str(root)})
            self.assertTrue(sentinel.exists())


class FixedFreezeProbes(unittest.TestCase):
    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_source_only_loader_ignores_valid_injected_cache(self):
        with tempfile.TemporaryDirectory() as td:
            source=pathlib.Path(td)/'generated.py';source.write_text('VALUE = "trusted"\n');digest=gate.sha(source)
            cached=pathlib.Path(importlib.util.cache_from_source(str(source)));cached.parent.mkdir()
            header=importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(source.stat().st_mtime),source.stat().st_size)
            cached.write_bytes(header+marshal.dumps(compile('VALUE = "UNVERIFIED_CACHED_CODE"\n',str(source),'exec')))
            loaded=gate.import_file('_independent_corrected_cache_probe',source,digest)
            self.assertEqual(loaded.VALUE,'trusted');self.assertEqual(loaded._verified_source_SHA256,digest)
            source.write_text('VALUE = "changed"\n')
            with self.assertRaisesRegex(ValueError,'SOURCE_SHA_MISMATCH'):gate.import_file('_independent_changed_source_probe',source,digest)

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_unpinned_vendor_initializer_is_never_executed(self):
        saved={n:sys.modules.pop(n) for n in ('vendor','vendor.headroom_buffer','_fixed_paired_headroom') if n in sys.modules}
        try:
            with tempfile.TemporaryDirectory() as td:
                root=pathlib.Path(td);(root/'vendor').mkdir()
                for rel in ('paired_buffer.py','vendor/headroom_buffer.py'):shutil.copyfile(pathlib.Path(ROOTS['paired_module'])/rel,root/rel)
                sentinel=root/'generated_initializer_ran'
                (root/'vendor/__init__.py').write_text(f'from pathlib import Path\nPath({str(sentinel)!r}).write_text("generated")\n')
                with self.assertRaisesRegex(ValueError,'UNPINNED_VENDOR_INITIALIZER'):gate.load_paired({'paired_module':str(root)})
                self.assertFalse(sentinel.exists())
        finally:sys.modules.update(saved)

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_finite_soft_hard_and_thread_refusal_before_import(self):
        import resource
        policy=gate.read(RUNNER/'RESOURCE_POLICY.json')
        env={'_PAIRED_SOURCE_PARENT_PID':str(os.getppid()),'OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1','NUMEXPR_NUM_THREADS':'1'}
        for kind,cap in ((resource.RLIMIT_AS,4_000_000_000),(resource.RLIMIT_CPU,600)):
            for bad in ((-1,-1),(1,-1),(-1,1),(0,1),(1,0),(2,1),(cap+1,cap+1),(1,cap+1)):
                def lim(which):return bad if which==kind else ((4_000_000_000,4_000_000_000) if which==resource.RLIMIT_AS else (600,600))
                with patch.dict(os.environ,env),patch('os.sched_getaffinity',return_value={0}),patch('resource.getrlimit',side_effect=lim):
                    with self.assertRaisesRegex(ValueError,'FINITE_SOFT_AND_HARD'):cli.bounded_worker_guard(policy)
        lim=lambda which:(4_000_000_000,4_000_000_000) if which==resource.RLIMIT_AS else (600,600)
        with patch.dict(os.environ,env),patch('os.sched_getaffinity',return_value={0}),patch('resource.getrlimit',side_effect=lim):
            cli.bounded_worker_guard(policy)
            for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
                with patch.dict(os.environ,{key:'2'}):
                    with self.assertRaisesRegex(ValueError,'ONE_MATH_THREAD'):cli.bounded_worker_guard(policy)

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_worker_without_handoff_refused_before_numerical_import(self):
        args=SimpleNamespace(roots=os.environ['PAIRED_TEST_CODE_ROOTS'],runner_manifest_sha=MANIFEST,year=2023,review_sha='1'*64,parent_go_sha='2'*64)
        with patch.dict(os.environ,{'_PAIRED_SOURCE_CONTROLLER_FD':'-1'}),patch.object(cli,'import_file') as imp:
            with self.assertRaisesRegex(ValueError,'VERIFIED_CONTROLLER_HANDOFF'):cli.require_controller_handoff(args)
            imp.assert_not_called()

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_handoff_packet_checks_every_binding_and_live_parent(self):
        args=SimpleNamespace(roots=os.environ['PAIRED_TEST_CODE_ROOTS'],runner_manifest_sha=MANIFEST,year=2023,review_sha='1'*64,parent_go_sha='2'*64)
        parent=os.getppid()
        for field in (None,'parent_pid','year','runner_manifest_SHA256','review_SHA256','parent_GO_SHA256','roots_SHA256','scope'):
            r,w=os.pipe();packet=cli.controller_packet(args);packet['parent_pid']=parent
            if field:packet[field]='GENERATED_MISMATCH'
            os.write(w,json.dumps(packet).encode());os.close(w)
            with patch.dict(os.environ,{'_PAIRED_SOURCE_CONTROLLER_FD':str(r),'_PAIRED_SOURCE_PARENT_PID':str(parent)}),patch.object(os,'kill') as live:
                if field:
                    with self.assertRaisesRegex(ValueError,'HANDOFF_BINDING_MISMATCH'):cli.require_controller_handoff(args)
                    live.assert_not_called()
                else:cli.require_controller_handoff(args);live.assert_called_once_with(parent,0)

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_actual_saved_archive_exact_bits_fields_dtype_missing_and_hash(self):
        f={'ready':np.array([False,True,True,True]),'reason':np.array(['WARMUP','READY','READY','READY'])}
        f.update({k:np.array([np.nan,0.,-0.,.2]) for k in a.FIELDS});runs=a.lossless_runs(f)
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'generated.npz';np.savez_compressed(p,**runs)
            self.assertTrue(a.validate_saved_archive(p,f,runs,gate.sha(p),gate.sha))
            with self.assertRaisesRegex(ValueError,'ARCHIVE_HASH'):a.validate_saved_archive(p,f,runs,'0'*64,gate.sha)
            for change in ('signed_zero','dtype','missing','fields','coverage','reason'):
                mutated={k:v.copy() for k,v in runs.items()}
                if change=='signed_zero':mutated['long_hurdle'][2]=0.
                elif change=='dtype':mutated['short_hurdle']=mutated['short_hurdle'].astype(np.float32)
                elif change=='missing':mutated['long_hurdle'][0]=0.
                elif change=='fields':mutated['GENERATED_EXTRA']=np.ones(1)
                elif change=='coverage':mutated['end_row_exclusive'][-1]=3
                elif change=='reason':mutated['reason_values'][0]='BAD'
                np.savez_compressed(p,**mutated)
                with self.assertRaises(ValueError,msg=change):a.validate_saved_archive(p,f,runs,gate.sha(p),gate.sha)

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_entire_cold_cli_ignores_poisoned_module_caches(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);runner=root/'runner';runner.mkdir()
            manifest=gate.read(RUNNER/'RUNNER_MANIFEST.json')
            for rel in [*manifest['files_SHA256'],'RUNNER_MANIFEST.json']:
                dest=runner/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(RUNNER/rel,dest)
            paired=root/'paired';paired.mkdir()
            for rel in PINS['paired_publication']['files_SHA256']:
                dest=paired/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(pathlib.Path(ROOTS['paired_module'])/rel,dest)
            inp=root/'input';inp.mkdir()
            for rel in PINS['input_publication']['files']:shutil.copyfile(pathlib.Path(ROOTS['input_module'])/rel,inp/rel)
            rg=root/'resource_guard.py';rr=root/'resource_release.json'
            shutil.copyfile(ROOTS['resource_guard'],rg);shutil.copyfile(ROOTS['resource_release'],rr)
            roots={'paired_module':str(paired),'input_module':str(inp),'resource_guard':str(rg),'resource_release':str(rr)}
            rp=root/'generated_code_roots.json';rp.write_text(json.dumps(roots))
            marker=root/'UNVERIFIED_CACHE_EXECUTED'
            targets=[runner/'source_gate.py',runner/'source_analysis.py',runner/'source_cli.py',runner/'test_source_runner.py',paired/'paired_buffer.py',paired/'vendor/headroom_buffer.py',inp/'inherited_input_binding.py',inp/'original_resource_gate.py',rg]
            for source in targets:
                cached=pathlib.Path(importlib.util.cache_from_source(str(source)));cached.parent.mkdir(exist_ok=True)
                payload=source.read_bytes()+f'\nfrom pathlib import Path\nPath({str(marker)!r}).write_text("BAD")\n'.encode()
                header=importlib.util.MAGIC_NUMBER+struct.pack('<III',0,int(source.stat().st_mtime),source.stat().st_size)
                cached.write_bytes(header+marshal.dumps(compile(payload,str(source),'exec')))
            env=dict(os.environ,PAIRED_TEST_CODE_ROOTS=str(rp))
            for mode in ('preflight','synthetic-tests'):
                result=subprocess.run([sys.executable,'-B',str(runner/'source_cli.py'),mode,'--runner-manifest-sha',MANIFEST,'--roots',str(rp)],env=env,capture_output=True,text=True,timeout=30)
                self.assertEqual(result.returncode,0,result.stderr[-3000:]);self.assertFalse(marker.exists())
                if mode=='preflight':self.assertIn('PASS_CODE_METADATA_ONLY_NO_SOURCE_ARRAY_READ',result.stdout)
                else:self.assertIn('Ran 27 tests',result.stderr)

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_cli_missing_go_refuses_with_code_only_roots(self):
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'generated_empty.json';p.write_text('{}')
            result=subprocess.run([sys.executable,'-B',str(RUNNER/'source_cli.py'),'run','--runner-manifest-sha',MANIFEST,'--roots',os.environ['PAIRED_TEST_CODE_ROOTS'],'--year','2023','--output',str(pathlib.Path(td)/'NO_ATTEMPT'),'--review',str(p),'--review-sha',gate.sha(p),'--parent-go',str(p),'--parent-go-sha',gate.sha(p)],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(result.returncode,0);self.assertIn('EXACT_REVIEW_GO_BINDING_REQUIRED',result.stderr)
            self.assertFalse((pathlib.Path(td)/'NO_ATTEMPT').exists())

    @unittest.skipIf(MANIFEST.startswith('6b563b6e'),'corrected freeze only')
    def test_observer_exception_kills_reaps_and_preserves_receipt(self):
        class FakeProc:
            pid=123456
            def poll(self):return None
            def wait(self):return -9
        with tempfile.TemporaryDirectory() as td:
            out=pathlib.Path(td)/'attempt';args=SimpleNamespace(output=str(out),year=2023,runner_manifest_sha=MANIFEST,review_sha='0'*64,parent_go_sha='0'*64,roots=os.environ['PAIRED_TEST_CODE_ROOTS'],review='GENERATED',parent_go='GENERATED')
            guard=SimpleNamespace(process_rss=lambda pid:1000,memory_observation=lambda:(_ for _ in ()).throw(RuntimeError('GENERATED_OBSERVER_FAILURE')))
            external=SimpleNamespace(controller_lock=contextlib.nullcontext);fake=FakeProc()
            with patch.object(cli,'resource_modules',return_value=(guard,external,None)),patch.object(cli,'resource_admission',return_value={'allowed_cpus':[0,1]}),patch.object(cli.subprocess,'Popen',return_value=fake),patch.object(cli.os,'killpg') as kill,patch.object(cli.os,'write',side_effect=lambda fd,data:len(data)),patch.object(fake,'wait',return_value=-9) as reap:
                with self.assertRaises(SystemExit):cli.dispatch(args,ROOTS,PINS,CASES)
                kill.assert_called_once();reap.assert_called_once()
            r=json.loads((out/'RESOURCE_RECEIPT.json').read_text())
            self.assertEqual(r['status'],'FAIL_BOUNDED_SOURCE_ONLY_PRESERVED')
            self.assertEqual(r['monitor_or_launch_error']['message'],'GENERATED_OBSERVER_FAILURE')

if __name__=='__main__':unittest.main(verbosity=2)
