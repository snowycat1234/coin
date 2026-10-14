#!/usr/bin/env python3
"""Portable offline generated-only reproduction; no downloads or historical inputs.

Supply four explicit local code directories restored from the public source maps.
The reviewed modules remain unchanged. Exact test-file layout is staged under the
fresh output directory so caller directory names do not affect the AST regression.
"""
import argparse,ast,datetime,hashlib,json,os
from pathlib import Path
import resource,signal,sys,time,types,unittest

START=time.monotonic()
ap=argparse.ArgumentParser(description=__doc__)
for option in ('code-root','v3-dir','v4-dir','module-dir','output'):
    ap.add_argument('--'+option,type=Path,required=True)
ap.add_argument('--runtime-site',type=Path,action='append',required=True,
    help='Explicit NumPy/Polars site-packages directory; repeat if needed under -S.')
ap.add_argument('--rounds',type=int,default=25)
ap.add_argument('--bench-only',action='store_true')
args=ap.parse_args()
if not(sys.flags.isolated and sys.flags.no_site and sys.flags.dont_write_bytecode and not sys.flags.optimize):
    raise RuntimeError('RUN_WITH_I_S_B_AND_ASSERTIONS')
if sys.version_info[:3]!=(3,12,14):raise RuntimeError('PYTHON_3_12_14_REQUIRED')
if not 0<=args.rounds<=10000:raise ValueError('ROUNDS_MUST_BE_0_TO_10000')
ROOT=args.code_root.resolve(strict=True);V3=args.v3_dir.resolve(strict=True);V4=args.v4_dir.resolve(strict=True)
MODULE=args.module_dir.resolve(strict=True);SITES=[p.resolve(strict=True) for p in args.runtime_site]
if any(not p.is_dir() for p in (ROOT,V3,V4,MODULE,*SITES)):raise ValueError('EXISTING_CODE_DIRECTORIES_REQUIRED')
if args.output.exists():raise FileExistsError('OUTPUT_MUST_BE_FRESH')
args.output=args.output.resolve();args.output.mkdir(parents=True)
os.sched_setaffinity(0,{min(os.sched_getaffinity(0))})
for key,limit in ((resource.RLIMIT_CPU,120),(resource.RLIMIT_AS,2_000_000_000),(resource.RLIMIT_FSIZE,25_000_000)):
    resource.setrlimit(key,(limit,limit))
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS'):os.environ[name]='1'
def bounds(*unused):
    if time.monotonic()-START>=120:raise TimeoutError('WALL120')
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024>2_000_000_000:raise MemoryError('RSS2GB')
    if sum(p.stat().st_size for p in args.output.rglob('*') if p.is_file())>25_000_000:raise OSError('TOTAL_OUTPUT25MB')
signal.signal(signal.SIGALRM,bounds);signal.setitimer(signal.ITIMER_REAL,.05,.05)
forbidden={'.npy','.npz','.parquet','.csv','.tsv','.zip','.gz','.arrow','.feather','.pq','.pkl','.pickle'}
def audit(event,values):
    if event.startswith('socket.') or event in ('subprocess.Popen','os.system','os.fork','os.forkpty','os.posix_spawn','os.exec'):
        raise RuntimeError('OFFLINE_GENERATED_ONLY_NO_NETWORK_OR_CHILDREN')
    if event=='open' and isinstance(values[0],(str,bytes,os.PathLike)):
        if Path(os.fsdecode(values[0])).suffix.lower() in forbidden:raise RuntimeError('NO_DATA_CONTAINER_ACCESS')
sys.addaudithook(audit)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
# These three digests identify already-public code manifests, never market data.
V3_MANIFEST_SHA='03e664cb17641fcd54b06300f66e746fde444422501b565a29227270c4c0a65f'
PUBLIC_MAP_SHA='b677ec0a7296062bfef4f755c2c67a7c9723896565f92bea64d244484452a1ed'
V4_MANIFEST_SHA='24b91fdda425e2dc9e28d1ccc22bb0182c3c8fb11b0c2a5ab0c00819900a34f4'
REVIEWED_NEW_CODE={
 'owned_adapter.py':'9fe5a7aa6b937129f69e8b34683ac8e9fb66c1b03247596ab9ca099ebbbacf61',
 'owned_journals.py':'8ee3a50cfa8f45476e401363d7b752d645b19968bdfa9ee302b735658616d002',
 'owned_preview.py':'934942fb7ae3b4e3ba4883b129b47ba23c78d792ae078f752877a54dc2387b49',
 'owned_simulator.py':'572db3defe3272ea949f71e0f926c9c4e10e41a255a3241b228a292eddb4d5a8',
 'test_owned_preview.py':'526da7a959b4d7834ff9980cc449929c9300dc1a51ab10436298088189aa69cb',
 'shared_journal_preview.py':'f9fa63fa680cb0d7991f7897fab1e2a09cd55547dbdddb74611fba5312436a5a',
 'test_shared_journal.py':'c87ccf2260f1891c4adc4f08231e001a3f74e5cc92f1258ac445e8499117e896'}
verified=[]
def verify_file(path,digest,size=None):
    if path.is_symlink() or sha(path)!=digest or size is not None and path.stat().st_size!=size:
        raise ValueError('EXACT_PUBLIC_OR_REVIEWED_CODE_REQUIRED')
    verified.append((path,digest))
def verify_again():
    if any(sha(path)!=digest for path,digest in verified):raise ValueError('SOURCE_CHANGED_DURING_GENERATED_TEST')
receipt={'schema':'PORTABLE_OWNED_GENERATED_REPRODUCTION_V1','scope':'EXPLICIT_OWNED_GENERATED_VARIANT_ONLY',
 'historical_GO':False,'historical_arrays_read':0,'network_used':False,'rounds':args.rounds,
 'start_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'new_module_SHA256':REVIEWED_NEW_CODE,
 'bounds':{'wall_seconds':120,'CPU_seconds':120,'address_space_bytes':2_000_000_000,'single_CPU':True}}
rc=1
print('PORTABLE_GENERATED_START',json.dumps({'rounds':args.rounds}),flush=True)
try:
    verify_file(V3/'SYNTHETIC_ONLY_MANIFEST.json',V3_MANIFEST_SHA)
    verify_file(V3/'SYNTHETIC_ONLY_RESTORE_MAP.json',PUBLIC_MAP_SHA)
    verify_file(V4/'SOURCE_MANIFEST.json',V4_MANIFEST_SHA)
    v3_manifest=json.loads((V3/'SYNTHETIC_ONLY_MANIFEST.json').read_text())
    public_map=json.loads((V3/'SYNTHETIC_ONLY_RESTORE_MAP.json').read_text())
    v4_manifest=json.loads((V4/'SOURCE_MANIFEST.json').read_text())
    for name in ('candidate.py','native_preview.py','test_synthetic.py'):
        record=v3_manifest['files'][name];verify_file(V3/name,record['SHA256'],record['bytes'])
    for name in ('causal_adapter.py','test_causal_integration.py'):
        record=v4_manifest['files']['adapter'][name];verify_file(V4/name,record['SHA256'],record['bytes'])
    if len(public_map['bodies'])!=18:raise ValueError('PUBLIC_MINIMAL18_DEPENDENCIES_REQUIRED')
    for name,record in public_map['bodies'].items():
        relative=Path(name)
        if relative.is_absolute() or '..' in relative.parts:raise ValueError('PUBLIC_RELATIVE_CODE_DESTINATION_REQUIRED')
        verify_file(ROOT/relative,record['SHA256'],record['bytes'])
    for name,digest in REVIEWED_NEW_CODE.items():verify_file(MODULE/name,digest)
    # Preserve the reviewed test's literal sibling-source lookup without changing
    # its bytes or requiring any particular caller directory layout.
    stage=args.output/'staged_code';HERE=stage/'owned-journal-preview-v2-20261014';HERE.mkdir(parents=True)
    sibling=stage/'original-csh-causal-execution-v4-20261014';sibling.mkdir()
    for name,digest in REVIEWED_NEW_CODE.items():
        (HERE/name).write_bytes((MODULE/name).read_bytes());verify_file(HERE/name,digest)
    (sibling/'causal_adapter.py').write_bytes((V4/'causal_adapter.py').read_bytes())
    verify_file(sibling/'causal_adapter.py',v4_manifest['files']['adapter']['causal_adapter.py']['SHA256'])
    FROZEN=ROOT/'native_pair_replacement_review_20261014/synthetic_dependencies_ca11e94d';REPO=FROZEN/'repo'
    sys.path[:0]=[str(HERE),str(V4),str(V3),*(str(p) for p in SITES),str(FROZEN/'fine'),str(REPO),str(REPO/'src')]
    import numpy as np,polars as pl
    assert(np.__version__,pl.__version__)==('2.3.5','1.44.2')
    receipt['runtime']={'Python':'3.12.14','NumPy':np.__version__,'Polars':pl.__version__}
    def selected(name,path,names):
        tree=ast.parse(path.read_bytes());nodes=[]
        for node in tree.body:
            if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name in names:nodes.append(node)
            elif isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in names for t in node.targets):nodes.append(node)
        assert len(nodes)==len(names)
        module=types.ModuleType(name);module.__file__=str(path)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),str(path),'exec'),module.__dict__);sys.modules[name]=module
    selected('scripts.investment.perpetual_directional',REPO/'scripts/investment/perpetual_directional.py',{'MINUTE','DAY','need'})
    selected('scripts.investment.public_sma_perpetual',REPO/'scripts/investment/public_sma_perpetual.py',{'SYMBOLS','require','symbol_order'})
    sys.path.insert(0,str(ROOT/'coin_h090_finite_native_20261014/dependencies'))
    import terminal_adapter
    native=types.ModuleType('native_control');native.NATIVE=terminal_adapter.EarlierTerminalSimulator;sys.modules['native_control']=native
    import test_synthetic,test_causal_integration,test_shared_journal as helpers,test_owned_preview as tests
    from decimal import Decimal as D
    from candidate import S
    from causal_adapter import CausalPartialAdapter,FreshExecutionPreview
    from native_preview import ChargedPreview
    from owned_journals import OwnedFineGridAccount,admit_owned_account,fork_owned_account,JOURNALS
    from owned_preview import BoundedChargedPreview,BoundedFreshExecutionPreview
    from owned_adapter import OwnedCausalPartialAdapter
    if not args.bench_only:
        suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls) for cls in
            (test_synthetic.Tests,test_causal_integration.Tests,tests.OwnedV3Tests,tests.OwnedV4Tests,tests.OwnershipTests))
        with (args.output/'TEST_LOG.txt').open('x') as log:result=unittest.TextTestRunner(stream=log,verbosity=2,failfast=True).run(suite)
        receipt['tests_run']=result.testsRun;receipt['tests_passed']=result.wasSuccessful()
        if not result.wasSuccessful():raise AssertionError('OWNERSHIP_PARITY_TEST_FAILED_SEE_LOG')
    timings=[]
    def measure(name,fn):
        beg=time.perf_counter();value=fn();seconds=time.perf_counter()-beg
        timings.append({'operation':name,'seconds':seconds});print('MEASURE',json.dumps(timings[-1]),flush=True);bounds();return value
    a=measure('generate_native_history',lambda:helpers.generated(args.rounds))
    owned=measure('one_time_explicit_owned_admission',lambda:admit_owned_account(a,generated_only=True))
    before=measure('native_full_snapshot',a.snapshot)
    portable=measure('owned_full_native_snapshot',owned.snapshot)
    assert before==portable;receipt['full_snapshot_exact']=True
    receipt['counts']={name:len(getattr(owned,name)) for name in JOURNALS}
    token=measure('owned_exact_state_token',owned.preview_state_token)
    fork=measure('owned_persistent_fork',lambda:fork_owned_account(owned))
    assert fork.preview_state_token()==token
    def grow_owned():
        result=admit_owned_account(helpers.account(),generated_only=True)
        for i in range(args.rounds):
            event=60_000_001+i*3;symbol=S[i%5]
            helpers.fill(result,'BUY','.10000000',event,f'GENERATED:{i}:OPEN',symbol)
            result.apply_funding(symbol,f'GENERATED:{i}:FUND',event+1,D(0),0)
            helpers.fill(result,'SELL','.10000000',event+2,f'GENERATED:{i}:CLOSE',symbol,reduce_only=True)
        return result
    grown=measure('generate_directly_into_owned_history',grow_owned)
    assert grown.snapshot()==before;receipt['live_owned_appends_exact']=True
    del grown,portable
    target=dict.fromkeys(S,D('.1'))
    optimized=measure('bounded_signal_constructor',lambda:helpers.oracle(owned,BoundedChargedPreview))
    witness=measure('bounded_signal_32_corners_with_exact_root_guards',lambda:optimized.evaluate(target,D(1)))
    assert witness['allowed'] and len(witness['corners_checked'])==32
    receipt['optimized_corners']=32
    baseline=helpers.oracle(a,ChargedPreview)
    if args.rounds<=100:
        expected=measure('frozen_signal_32_corners',lambda:baseline.evaluate(target,D(1)))
        assert expected==witness;receipt['full_32_corner_witness_parity']=True
    else:
        bp,bw=measure('frozen_one_native_charged_corner',lambda:baseline._charged(target,'EXACT_TAG'))
        cp,cw=measure('owned_one_native_charged_corner',lambda:optimized._charged(target,'EXACT_TAG'))
        assert bw==cw and bp.snapshot()==cp.snapshot();receipt['large_complete_native_corner_exact']=True
        del bp,cp
    fixtures=test_causal_integration.Tests();binding=fixtures.source().bind(test_causal_integration.SIGNAL)
    fresh_kwargs=dict(binding=binding,prices=dict.fromkeys(S,D(100)),price_available_us=dict.fromkeys(S,test_causal_integration.SIGNAL+test_causal_integration.MINUTE),
        pending=target,capacity=dict.fromkeys(S,D(100)),event_us=test_causal_integration.SIGNAL+test_causal_integration.MINUTE+1,
        signal_us=test_causal_integration.SIGNAL,quote_available_us=test_causal_integration.SIGNAL+test_causal_integration.MINUTE)
    def full_guard():
        state=owned.preview_state_token();preview=BoundedFreshExecutionPreview(owned,**fresh_kwargs)
        result=preview.evaluate(target,D(1));assert owned.preview_state_token()==state
        assert result['allowed'] and len(result['corners_checked'])==32
        return result
    fresh=measure('bounded_complete_fresh_guard_envelope',full_guard)
    if args.rounds<=100:
        expected=FreshExecutionPreview(a,**fresh_kwargs).evaluate(target,D(1))
        assert fresh==expected;receipt['fresh_full_witness_exact']=True
    sim=tests.owned_sim(fixtures.sim());sim.account=fork_owned_account(owned)
    adapter=OwnedCausalPartialAdapter(sim,fixtures.source())
    measure('owned_native_schedule_valid_lambda1',lambda:adapter.schedule(target,test_causal_integration.SIGNAL,'DAILY_TARGET'))
    receipt['lambda1_schedule_evaluation_count']=len(adapter.receipts[-1].evaluations)
    assert receipt['lambda1_schedule_evaluation_count']==1
    measure('owned_full_native_attempt_all_guarded_fills',lambda:adapter.attempt(test_causal_integration.SIGNAL+test_causal_integration.MINUTE,fixtures.market()))
    assert all(pos.quantity==D('.1') for pos in sim.account.positions.values())
    assert len(adapter.execution_receipts)==5 and all(r['allowed'] for r in adapter.execution_receipts)
    assert not sim.pending
    receipt['full_native_execution_fills']=5;receipt['full_native_execution_guards']=len(adapter.execution_receipts)
    stress_sim=tests.owned_sim(fixtures.sim());stress_sim.account=fork_owned_account(owned)
    stress_adapter=OwnedCausalPartialAdapter(stress_sim,fixtures.source())
    stress_target={s:D(30) if s==S[0] else D(0) for s in S}
    measure('owned_native_schedule_five_fraction_rejection_path',lambda:stress_adapter.schedule(stress_target,test_causal_integration.SIGNAL,'DAILY_TARGET'))
    receipt['rejected_full_schedule_evaluation_count']=len(stress_adapter.receipts[-1].evaluations)
    receipt['rejected_full_schedule_selected_fraction']=str(stress_adapter.receipts[-1].fraction)
    assert receipt['rejected_full_schedule_evaluation_count']==5
    assert owned.preview_state_token()==token and owned.snapshot()==before and a.snapshot()==before
    receipt['source_live_and_owned_seed_unchanged']=True
    receipt['timings']=timings
    verify_again();receipt['public_minimal_dependency_count']=18
    receipt['source_hashes_verified_before_and_after']=True
    receipt['status']='PASS_PORTABLE_GENERATED_PARITY';rc=0
except BaseException as exc:
    # Do not embed caller filesystem paths or arbitrary exception contents in a
    # portable receipt. Detailed failing unittest logs require separate review.
    receipt.update(status='FAILED_PORTABLE_GENERATED_CHECK',error_type=type(exc).__name__)
finally:
    signal.setitimer(signal.ITIMER_REAL,0);usage=resource.getrusage(resource.RUSAGE_SELF)
    receipt['resources']={'wall_seconds':time.monotonic()-START,'CPU_seconds':usage.ru_utime+usage.ru_stime,'peak_RSS_bytes':usage.ru_maxrss*1024,'exit':rc}
    (args.output/'PORTABLE_RECEIPT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print('PORTABLE_GENERATED_TERMINAL',json.dumps({'status':receipt['status'],'resource':receipt['resources']}),flush=True)
sys.exit(rc)
