"""Generated-only finite scheduler, pressure, identity and reporting gates."""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import run_partial as runner
from saved_native_reconciliation import checker_sha256


def cheap_job(cell,fail=False):
    def builder(directory,cpu):
        script=("import json,os,time,pathlib,sys; p=pathlib.Path(sys.argv[1]); time.sleep(.25); "
            + ("sys.exit(7)" if fail else
               "r={'status':'GENERATED_TERMINAL','cell_id':p.name}; (p/'CASE_RECEIPT.json').write_text(json.dumps(r)); (p/'TERMINAL_CHECKPOINT.json').write_text(json.dumps({'generated_only':True}))"))
        return [sys.executable,'-B','-c',script,str(directory)]
    return cell,builder


def cheap_validate(path,cell):
    r=json.loads((path/'CASE_RECEIPT.json').read_bytes())
    if r['cell_id']!=cell:raise ValueError('TAMPER')
    return r


class MatrixRunnerTests(unittest.TestCase):
    def setUp(self):
        self.cpus=([int(x) for x in os.environ['PARTIAL2021_TEST_CPUS'].split(',')] if os.environ.get('PARTIAL2021_TEST_CPUS')
            else ([6] if 6 in os.sched_getaffinity(0) else sorted(os.sched_getaffinity(0))[:1]))
        self.host=runner.host_observation()

    def test_distinct_allowed_cpu_validation_and_serial_preflight(self):
        if len(self.cpus)<2:self.skipTest('two available CPUs needed')
        self.assertEqual(runner.choose_worker_count(2,self.cpus,self.host),2)
        low=deepcopy(self.host);low['MemAvailable_bytes']=3_000_000_000
        self.assertEqual(runner.choose_worker_count(2,self.cpus,low),1)
        low['MemAvailable_bytes']=1_000_000_000
        with self.assertRaisesRegex(RuntimeError,'MEMORY'):runner.choose_worker_count(2,self.cpus,low)
        for cpus in ([self.cpus[0],self.cpus[0]],[-1,self.cpus[0]],[True,self.cpus[0]]):
            with self.assertRaises(ValueError):runner.choose_worker_count(2,cpus,self.host)

    def test_generated_concurrent_native_calendars_and_observed_thread_affinity(self):
        if len(self.cpus)<2:self.skipTest('two available CPUs needed')
        from profile_generated import profile
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            report=profile(Path(tmp))
            self.assertEqual(len(report['cases']),2)
            overlap=[r for r in report['observations'] if len([w for w in r['workers'] if w['RSS_bytes']>0])==2]
            self.assertTrue(overlap)
            for sample in overlap:
                self.assertLess(sample['aggregate_live_RSS_bytes'],runner.LIMITS['aggregate_live_worker_RSS_stop_bytes'])
                self.assertEqual(len(set(w['CPU_affinity'][0] for w in sample['workers'])),2)
                for worker in sample['workers']:
                    self.assertTrue(all(t['CPU_affinity']==worker['CPU_affinity'] for t in worker['tasks']))
            for case in report['cases']:
                receipt=json.loads((Path(tmp)/case['cell_id']/'CASE_RECEIPT.json').read_bytes())
                self.assertEqual(receipt['generated_minutes'],4320)
                self.assertTrue(all(v=='1' for v in receipt['thread_environment'].values()))

    def test_pressure_serial_fallback_before_launch(self):
        if len(self.cpus)<2:self.skipTest('two available CPUs needed')
        low=deepcopy(self.host);low['MemAvailable_bytes']=3_000_000_000
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            report=runner.run_pool([cheap_job('A'),cheap_job('B')],tmp,requested_workers=2,cpus=self.cpus,
                validator=cheap_validate,observation_callback=lambda:low)
            self.assertTrue(all(len(r['workers'])<=1 for r in report['observations']))
            self.assertEqual([r['cell_id'] for r in report['cases']],['A','B'])

    def test_pressure_drop_between_first_and_second_launch_is_honored(self):
        if len(self.cpus)<2:self.skipTest('two available CPUs needed')
        calls=[0];low=deepcopy(self.host);low['MemAvailable_bytes']=3_000_000_000
        def changing():
            calls[0]+=1
            return self.host if calls[0]<=2 else low
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            report=runner.run_pool([cheap_job('A'),cheap_job('B')],tmp,requested_workers=2,cpus=self.cpus,
                validator=cheap_validate,observation_callback=changing)
            self.assertTrue(all(len(r['workers'])<=1 for r in report['observations']))
            self.assertEqual(len(report['cases']),2)

    def test_atomic_exclusive_publication_and_existing_controller_refusal(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            path=Path(tmp);runner.save(path/'IMMUTABLE.json',{'generated_only':True})
            with self.assertRaises(FileExistsError):runner.save(path/'IMMUTABLE.json',{'replacement':True})
            self.assertEqual(json.loads((path/'IMMUTABLE.json').read_bytes()),{'generated_only':True})
            self.assertEqual(list(path.glob('.*.tmp')),[])
            os.link(path/'IMMUTABLE.json',path/'SECOND_HARDLINK.json')
            self.assertEqual(runner.own_bytes(path),(path/'IMMUTABLE.json').stat().st_size)
            with self.assertRaisesRegex(ValueError,'RESUME_NOT_SUPPORTED'):runner.controller(SimpleNamespace(output=tmp))

    def test_duplicate_completed_not_launched_and_unfinished_never_retried(self):
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            path=Path(tmp)
            runner.run_pool([cheap_job('A')],path,requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate)
            def forbidden(*args):raise AssertionError('DUPLICATE_LAUNCH')
            report=runner.run_pool([('A',forbidden)],path,requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate)
            self.assertTrue(report['cases'][0]['reused_saved_terminal'])
            (path/'B').mkdir()
            with self.assertRaisesRegex(RuntimeError,'EXISTING_UNFINISHED'):
                runner.run_pool([cheap_job('B')],path,requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate)
            with self.assertRaisesRegex(ValueError,'UNIQUE'):
                runner.run_pool([cheap_job('C'),cheap_job('C')],path,requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate)

    def test_worker_failure_pauses_no_automatic_retry_or_next_launch(self):
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            with self.assertRaisesRegex(RuntimeError,'WORKER_FAILED_EXECUTION_NOT_ECONOMIC_HALT'):
                runner.run_pool([cheap_job('FAIL',True),cheap_job('UNLAUNCHED')],tmp,requested_workers=1,
                    cpus=self.cpus[:1],validator=cheap_validate)
            self.assertFalse((Path(tmp)/'UNLAUNCHED').exists())
            with self.assertRaisesRegex(RuntimeError,'EXISTING_UNFINISHED'):
                runner.run_pool([cheap_job('FAIL')],tmp,requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate)

    def test_aggregate_live_rss_guard_stops_generated_workers(self):
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            limits=dict(runner.LIMITS,aggregate_live_worker_RSS_stop_bytes=1)
            with patch.object(runner,'LIMITS',limits),self.assertRaisesRegex(RuntimeError,'AGGREGATE_LIVE_RSS_LIMIT'):
                runner.run_pool([cheap_job('GUARD')],tmp,requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate)
            self.assertFalse((Path(tmp)/'GUARD'/'TERMINAL_CHECKPOINT.json').exists())

    def test_generated_checkpoint_tamper_rejected(self):
        from profile_generated import worker,validate
        # Use subprocess: limits and affinity must never mutate the test process.
        import subprocess
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            path=Path(tmp)/'GENERATED';path.mkdir()
            with runner.controller_lease(Path(tmp)/'GENERATED_ONLY_LEASE') as fd:
                env=runner.environment();env['MATRIX_CONTROLLER_LEASE_FD']=str(fd)
                subprocess.run([sys.executable,'-B',str(runner.HERE/'profile_generated.py'),'--worker',str(path),
                    '--cpu',str(self.cpus[0])],check=True,env=env,pass_fds=(fd,))
            validate(path,'GENERATED')
            with (path/'GENERATED_AUDIT.json').open('ab') as f:f.write(b' ')
            with self.assertRaisesRegex(ValueError,'TAMPER'):validate(path,'GENERATED')

    def test_resealed_self_minted_GO_not_external_authority(self):
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            path=Path(tmp)
            for name in runner.TERMINAL_FILES:(path/name).write_bytes(b'{}\n')
            runner.save(path/'TERMINAL_CHECKPOINT.json',dict(cell_id='2021_STATIC50_LOW_APR2_DEC31_D',all_evidence_fsynced=True,
                restart_financial_snapshot_permission=False,checker_SHA256=checker_sha256(),
                files={name:runner.sha((path/name).read_bytes()) for name in runner.TERMINAL_FILES}))
            with self.assertRaisesRegex(ValueError,'EXACT_NEW_EXTERNAL_PARTIAL2021_ROOT_GO'):
                runner.validate_saved_terminal(path,preparation_raw=b'{}',preparation_directory=path,cell_id='2021_STATIC50_LOW_APR2_DEC31_D',
                    expected_go_sha256='a'*64,expected_review_sha256='b'*64)

    def test_permanent_claim_blocks_cross_output_and_failed_spawn(self):
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            root=Path(tmp);registry=root/'TEMP_REGISTRY'
            def reserve(cell,path,cpu):
                runner.claim_launch(registry,cell_id=cell,manifest_sha256=runner.MANIFEST_SHA256,
                    metadata=dict(case_output=str(path),root_GO_SHA256='a'*64))
            jobs=[cheap_job('2021_STATIC50_LOW_APR2_DEC31_D')]
            runner.run_pool(jobs,root/'FIRST',requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate,before_launch=reserve)
            with self.assertRaisesRegex(RuntimeError,'PERMANENT_CANONICAL_CELL_CLAIM'):
                runner.run_pool(jobs,root/'SECOND',requested_workers=1,cpus=self.cpus[:1],validator=cheap_validate,before_launch=reserve)
            with patch.object(runner.subprocess,'Popen',side_effect=OSError('GENERATED_FAILED_SPAWN')):
                with self.assertRaisesRegex(OSError,'FAILED_SPAWN'):
                    runner.run_pool([cheap_job('2021_STATIC50_HIGH_APR2_DEC31_D')],root/'SPAWN',requested_workers=1,
                        cpus=self.cpus[:1],validator=cheap_validate,before_launch=reserve)
            self.assertTrue((registry/runner.MANIFEST_SHA256/'2021_STATIC50_HIGH_APR2_DEC31_D.json').is_file())
            with self.assertRaisesRegex(RuntimeError,'PERMANENT_CANONICAL_CELL_CLAIM'):
                runner.run_pool([cheap_job('2021_STATIC50_HIGH_APR2_DEC31_D')],root/'AFTER',requested_workers=1,
                    cpus=self.cpus[:1],validator=cheap_validate,before_launch=reserve)
            with self.assertRaises(ValueError):runner.claim_launch(registry,cell_id='2024_STATIC50_MID',
                manifest_sha256=runner.MANIFEST_SHA256,metadata={})

    def test_direct_case_missing_claim_cannot_construct_account(self):
        from types import SimpleNamespace
        import partial_entry as entry
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            args=SimpleNamespace(cpu=self.cpus[0],cell_id='2021_STATIC50_LOW_APR2_DEC31_D',case_output=tmp)
            with patch.object(runner,'apply_limits'),patch.object(runner,'validate_scope_worker',return_value=(b'{}',b'{}',b'{}')),patch.object(entry,'make_case',side_effect=AssertionError('ACCOUNT_CONSTRUCTION_FORBIDDEN')) as constructor:
                with self.assertRaisesRegex(ValueError,'CANONICAL_PRELAUNCH_CLAIM'):runner.case(args)
                constructor.assert_not_called()

    def test_worker_claim_scope_and_pid_start_tick_handshake(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            root=Path(tmp);directory=root/'CASE';directory.mkdir();registry=root/'TEMP_REGISTRY'
            args=SimpleNamespace(cell_id='2021_STATIC50_LOW_APR2_DEC31_D',case_output=str(directory),cpu=self.cpus[0])
            prep=runner.body(dict(years={'2021':{'source_identity':'generated-source'}},code_identity={'test':'generated'}))
            go,review=b'generatedGO',b'generatedREVIEW'
            descriptor=json.loads((runner.HERE/'FROZEN_NINE_CELL_MANIFEST.json').read_bytes())['cells'][0]
            metadata=dict(schema='CANONICAL_IMMUTABLE_MANIFEST_CELL_LAUNCH_CLAIM_V1',manifest_SHA256=runner.MANIFEST_SHA256,
                cell_id=args.cell_id,year=2021,config=descriptor['config'],source_identity='generated-source',
                selected_target_raw_SHA256=descriptor['selected_target_raw_SHA256'],preparation_SHA256=runner.sha(prep),
                code_identity={'test':'generated'},root_GO_SHA256=runner.sha(go),independent_review_SHA256=runner.sha(review),
                requested_CPU=args.cpu,case_output=str(directory.resolve()),controller_PID=os.getppid(),
                status='RESERVED_BEFORE_PROCESS_SPAWN',automatic_clear_or_retry=False,financial_snapshot_resume=False)
            target=registry/runner.MANIFEST_SHA256;target.mkdir(parents=True)
            runner.save(target/(args.cell_id+'.json'),metadata)
            owner=dict(cell_id=args.cell_id,PID=os.getpid(),CPU=args.cpu,controller_PID=os.getppid(),process_start_ticks='GENERATED_START')
            runner.save(directory/'PROCESS_OWNERSHIP.json',owner)
            observed=dict(CPU_affinity=[args.cpu],process_start_ticks='GENERATED_START',tasks=[{'CPU_affinity':[args.cpu]}])
            with patch.object(runner,'process_observation',return_value=observed):
                self.assertTrue(runner.validate_worker_claim(args,preparation_raw=prep,go_raw=go,review_raw=review,registry_root=registry))
                with self.assertRaisesRegex(ValueError,'CLAIM_SCOPE'):
                    runner.validate_worker_claim(args,preparation_raw=prep,go_raw=b'forgedGO',review_raw=review,registry_root=registry)
            observed['process_start_ticks']='REUSED_PID'
            with patch.object(runner,'process_observation',return_value=observed),self.assertRaisesRegex(ValueError,'PID_START'):
                runner.validate_worker_claim(args,preparation_raw=prep,go_raw=go,review_raw=review,registry_root=registry)

    def test_saved_actual_held_report_recomputed_and_minute_tamper_rejected(self):
        import numpy as np
        import partial_d as e
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            path=Path(tmp);prepdir=path/'PREP';(prepdir/'2021').mkdir(parents=True)
            columns=['close_us','nav','free_cash','isolated_balance','gross_weight']+[s+'_signed_weight' for s in e.S]
            values=np.zeros((1440,len(columns)));values[:,0]=np.arange(1,1441)*e.MINUTE
            values[:,1]=10000;values[:,2]=9000;values[:,3]=1000;values[:,4]=.4;values[:,5]=.2;values[:,6]=-.2
            decisions=np.array([0],dtype=np.int64);cov=np.array([np.eye(5)]);targets=np.zeros((1,5))
            targetpath=prepdir/'2021/TARGETS.npz';np.savez_compressed(targetpath,decision_us=decisions,annual_covariance=cov,STATIC50_MID=targets)
            runner.save(prepdir/'PREPARATION.json',dict(artifacts={'2021/TARGETS.npz':{'SHA256':runner.sha(targetpath.read_bytes())}}))
            np.savez_compressed(path/'MINUTE.npz',values=values,columns=np.asarray(columns))
            runner.save(path/'GUARD_RECEIPTS.json',[])
            report=runner.held_risk_report(values,columns,decisions,cov,targets,'MID',[])
            runner.save(path/'ACTUAL_HELD_RISK_REPORT.json',report)
            kwargs=dict(preparation_directory=prepdir,preparation_raw=(prepdir/'PREPARATION.json').read_bytes(),cell={'calendar':[0,1440*e.MINUTE],'year':2021,'config':'STATIC50_MID','tier':'MID'},
                receipt={'completed_minutes':1440,'account_stop_us':None},result={'summary':{'NAV':10000.,'free_cash':9000.,'isolated_balance':1000.,'gross_weight':.4}})
            runner.validate_saved_risk_report(path,**kwargs)
            external_raw=kwargs['preparation_raw'];kwargs['preparation_raw']=b'forged-preparation'
            with self.assertRaisesRegex(ValueError,'EXTERNAL_PREPARATION'):runner.validate_saved_risk_report(path,**kwargs)
            kwargs['preparation_raw']=external_raw
            report['gross_exposure_max']=.01;(path/'ACTUAL_HELD_RISK_REPORT.json').write_bytes(runner.body(report))
            with self.assertRaisesRegex(ValueError,'RECOMPUTATION'):runner.validate_saved_risk_report(path,**kwargs)
            values[0,0]+=e.MINUTE;np.savez_compressed(path/'MINUTE.npz',values=values,columns=np.asarray(columns))
            with self.assertRaisesRegex(ValueError,'CALENDAR'):runner.validate_saved_risk_report(path,**kwargs)

    def test_global_controller_lease_excludes_disjoint_controller(self):
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            with runner.controller_lease(tmp):
                with self.assertRaisesRegex(RuntimeError,'GLOBAL_CONTROLLER_LEASE_HELD'):
                    with runner.controller_lease(tmp):self.fail('OVERLAPPING_CONTROLLER')
            with runner.controller_lease(tmp):pass

    def test_controller_death_keeps_lease_held_by_inherited_child_FD(self):
        import subprocess,time,signal
        with tempfile.TemporaryDirectory(dir=runner.HERE) as tmp:
            root=Path(tmp);status=root/'CHILD.json'
            script=("import sys,os,json,subprocess,pathlib; os.sched_setaffinity(0,{int(sys.argv[4])}); sys.path.insert(0,sys.argv[1]); import run_partial as r; "
                "lease=r.controller_lease(sys.argv[2]); fd=lease.__enter__(); "
                "child=subprocess.Popen([sys.executable,'-B','-c','import time;time.sleep(1.5)'],pass_fds=(fd,)); "
                "pathlib.Path(sys.argv[3]).write_text(json.dumps({'PID':child.pid})); os._exit(0)")
            parent=subprocess.run([sys.executable,'-B','-c',script,str(runner.HERE),str(root/'TEMP_REGISTRY'),str(status),str(self.cpus[0])],check=True)
            child=json.loads(status.read_bytes())['PID']
            try:
                with self.assertRaisesRegex(RuntimeError,'GLOBAL_CONTROLLER_LEASE_HELD'):
                    with runner.controller_lease(root/'TEMP_REGISTRY'):self.fail('ORPHAN_WORKER_LEASE_LOST')
                # The generated child has a known bounded1.5s lifetime. This
                # verifies lease release after its actual inherited FD closes.
                deadline=time.monotonic()+5
                while True:
                    try:
                        with runner.controller_lease(root/'TEMP_REGISTRY'):break
                    except RuntimeError:
                        if time.monotonic()>deadline:raise
                        time.sleep(.05)
            finally:
                try:os.kill(child,signal.SIGKILL)
                except ProcessLookupError:pass

    def test_actual_held_weights_and_forecast_overshoots_reported(self):
        import numpy as np
        import partial_d as e
        names=['close_us','nav','free_cash','isolated_balance','gross_weight']+[s+'_signed_weight' for s in e.S]
        values=np.zeros((1440,len(names)));values[:,0]=np.arange(1,1441)*e.MINUTE
        values[:,1]=10000;values[:,2]=9000;values[:,3]=1000;values[:,4]=.4
        values[:,5]=.2;values[:,6]=-.2
        cov=np.array([np.eye(5)])
        report=runner.held_risk_report(values,names,np.array([0]),cov,np.zeros((1,5)),'MID',[])
        self.assertEqual(report['gross_exposure_max'],.4)
        self.assertEqual(report['actual_net_signed_weight_max'],0)
        self.assertGreater(report['forecast_volatility_breach_minutes'],0)
        self.assertGreater(report['forecast_volatility_breach_max_absolute'],0)
        self.assertTrue(report['nominal_tier_equality_is_not_exact_realized_risk_matching'])


if __name__=='__main__':unittest.main()
