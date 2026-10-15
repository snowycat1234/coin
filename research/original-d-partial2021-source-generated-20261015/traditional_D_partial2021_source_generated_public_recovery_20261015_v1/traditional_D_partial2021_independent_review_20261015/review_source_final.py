"""Independent local SOURCE-only review. No scope, finance or provider iteration."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{4})
import sys,json,time,resource,subprocess,multiprocessing,fcntl,socket,urllib.request
from pathlib import Path
from hashlib import sha256
from contextlib import ExitStack
from io import BytesIO
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'traditional_D_partial2021_20261015'))
import numpy as np
import partial_source as s
import partial_d as d
import partial_entry as e
import run_partial as runner

def pin(path):
    b=Path(path).read_bytes();return dict(SHA256=sha256(b).hexdigest(),bytes=len(b))
def out(name,value):
    p=HERE/name
    with p.open('x') as f:json.dump(value,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

began=time.monotonic()
targets=[(d,'construct_case'),(d.ExpansionAccount,'__init__'),(d.D,'construct_case'),
    (d.D.Guard50ExitAccount,'__init__'),(d.V2,'construct_case'),(d.V2.ContinuationAccount,'__init__'),
    (d.V2.ENGINE.USDTLinearPerpetualAccount,'__init__'),(d.V2.native,'_construct_case'),
    (s.g,'make_account'),(s.CapturedMinuteProvider,'__call__'),
    (d.V2.native.runtime()[2].EarlierTerminalSimulator,'advance_day'),
    (e,'make_case'),(e.CaseExecutionScope,'__post_init__'),(runner,'case'),(runner,'controller'),
    (runner,'run_pool'),(runner,'_run_pool'),(runner,'claim_launch'),(runner,'controller_lease'),
    (subprocess,'Popen'),(subprocess,'run'),(multiprocessing.Process,'start'),(os,'system'),(fcntl,'flock'),
    (socket,'create_connection'),(urllib.request,'urlopen')]
with ExitStack() as stack:
    mocks=[stack.enter_context(patch.object(obj,name,side_effect=AssertionError('FORBIDDEN:'+name))) for obj,name in targets]
    projected=s.project()
    manifest=e.frozen_manifest()
    artifacts=e._artifacts()
    with np.load(BytesIO(artifacts['TARGETS.npz']),allow_pickle=False) as z:
        assert set(z.files)==set(s.CONFIGS)|{'decision_us','annual_covariance'}
        assert z['decision_us'].tobytes()==projected['decisions'].tobytes()
        assert z['annual_covariance'].tobytes()==projected['covariance'].tobytes()
        for key in s.CONFIGS:assert z[key].tobytes()==projected['targets'][key].tobytes()
    p=np.asarray([[r['close'] for r in projected['source_rows'][i:i+5]] for i in range(0,len(projected['source_rows']),5)])
    t=np.asarray([r['close_us'] for r in projected['source_rows'][::5]],dtype=np.int64)
    assert p.shape==(473,5) and t.shape==(473,)
    prefix_matches=0;future_perturbations=0
    for i,at in enumerate(projected['decisions']):
        k=int(np.searchsorted(t,at));one=np.asarray([at],dtype=np.int64)
        td,values,cov,proof=s.g.build_target_grid(p[:k+1],t[:k+1],t[:k+1],one)
        assert td[0]==at and cov[0].tobytes()==projected['covariance'][i].tobytes()
        for key in s.CONFIGS:
            assert values[key][0].tobytes()==projected['targets'][key][i].tobytes(),(i,key)
            prefix_matches+=1
        changed=p.copy()
        changed[k+1:]*=np.arange(1,len(changed)-k,dtype=float)[:,None]+123.456
        _,values,cov,_=s.g.build_target_grid(changed,t,t,one)
        assert cov[0].tobytes()==projected['covariance'][i].tobytes()
        for key in s.CONFIGS:
            assert values[key][0].tobytes()==projected['targets'][key][i].tobytes(),('future',i,key)
            future_perturbations+=1
    # Later stored DEV fields can be decoded but must never enter the selected
    # target/covariance rows. Inject only in-memory copies behind the source
    # capture seam, never modify original pinned bytes or admit this fixture.
    captured=projected['captured']
    with np.load(BytesIO(captured[s.DAILY_MEMBER]),allow_pickle=False) as z:
        symbols=z['symbol_order'];stored_t=z['close_available_us'];stored_p=z['close'].copy()
    outside=(stored_t<s.ALLOWED_START)|(stored_t>s.END)
    assert int(outside.sum())==898
    stored_p[outside]*=np.arange(1,int(outside.sum())+1,dtype=float)[:,None]+1000.
    buffer=BytesIO();np.savez_compressed(buffer,symbol_order=symbols,close_available_us=stored_t,close=stored_p)
    changed_bodies=dict(captured);changed_bodies[s.DAILY_MEMBER]=buffer.getvalue()
    with patch.object(s,'_source_pins',return_value=(projected['source_files'],changed_bodies)):
        perturbed=s.project()
    assert perturbed['decisions'].tobytes()==projected['decisions'].tobytes()
    assert perturbed['covariance'].tobytes()==projected['covariance'].tobytes()
    for key in s.CONFIGS:assert perturbed['targets'][key].tobytes()==projected['targets'][key].tobytes()
    side=projected['sidecar'];events=projected['window']['events']
    assert len(events)==4110 and all(s.START<=x['event_us']<s.END for x in events)
    assert not any('not_owned_under_fresh_CASH_start' in x for x in events)
    assert side['funding_ownership']=='CURRENT_NATIVE_ACTUAL_QUANTITY_ONLY_AFTER_PAID_FILLS'
    assert side['terminal_signal_us']==s.END-61*s.MINUTE
    assert side['terminal_eligible_open_range']==[s.END-60*s.MINUTE,s.END-s.MINUTE]
    assert side['latest_native_terminal_fill_us']==s.END-s.MINUTE+1<s.END
    assert len(projected['decisions'])==274 and len(s.CONFIGS)==9
    assert len(projected['window']['minute_blocks'].identity)==9
    assert sum(x['native_minutes'] for x in side['minute_quote_capacity_bindings'])==394560
    for m in mocks:m.assert_not_called()
    calls={str(obj.__name__)+'.'+name:mock.call_count for (obj,name),mock in zip(targets,mocks)}
record=dict(status='PASS_SOURCE_ONLY',code_files={name:pin(s.HERE/name) for name in ('partial_source.py','partial_d.py','partial_entry.py','run_partial.py')},
    source_completion=pin(s.SOURCE_ROOT/'FINAL_LOCAL_SOURCE_PINS.json'),source_qualification=pin(s.SOURCE_ROOT/'SOURCE_QUALIFICATION_2021_APR_DEC.json'),
    source_identity=projected['source_identity'],calendar=[s.START,s.END],decision_count=274,native_source_minutes=394560,
    all_nine_targets_prefix_byte_equal_checks=prefix_matches,all_nine_targets_future_row_perturbation_checks=future_perturbations,
    covariance_prefix_checks=274,covariance_future_row_perturbation_checks=274,
    outside_permitted_projection_mutated_rows=898,outside_projection_target_and_covariance_bytes_invariant=True,
    physical_daily_fields_decoded=['symbol_order','close_available_us','close'],physically_decoded_close_shape=[1463,5],
    allowed_projection_rows=565,effective_target_input_rows=473,source_funding_events=4110,funding_coverage_not_ownership=True,
    source_provider_iteration_calls=0,actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,historical_scopes_created=0,
    historical_market_minutes_advanced=0,real_GO_written=0,prohibited_boundary_call_counts=calls,
    test_script=pin(__file__),wall_seconds=time.monotonic()-began,CPU_affinity=sorted(os.sched_getaffinity(0)),
    observed_task_affinities={p.name:sorted(os.sched_getaffinity(int(p.name))) for p in Path('/proc/self/task').iterdir()},
    maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
out('SOURCE_REVIEW_FINAL.json',record)
print(json.dumps({k:record[k] for k in ('status','all_nine_targets_prefix_byte_equal_checks','all_nine_targets_future_row_perturbation_checks','wall_seconds','maximum_RSS_bytes')},sort_keys=True),flush=True)
