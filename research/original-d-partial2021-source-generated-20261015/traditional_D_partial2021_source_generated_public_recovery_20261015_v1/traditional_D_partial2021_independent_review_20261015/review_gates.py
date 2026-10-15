"""Portable cold SOURCE/admission-negative review; never mints a scope or GO."""
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[key]='1'
os.sched_setaffinity(0,{4})
import sys,json,time,resource,subprocess,multiprocessing,fcntl,socket,urllib.request,tempfile
from pathlib import Path
from hashlib import sha256
from contextlib import ExitStack
from copy import deepcopy
from io import BytesIO
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];HERE=Path(__file__).resolve().parent
NEW=ROOT/'traditional_D_partial2021_20261015';SOURCE=ROOT/'native_2021_source_restore_20261015'
PREPARATION=Path(sys.argv[1]).resolve()
allowed_json_roots=(NEW,SOURCE,ROOT/'traditional_three_tier_freeze_20261015',ROOT/'bounded_account_continuation_20261015',PREPARATION)
old_private_body_attempts=[];old_private_body_reads=[];open_count=0
def audit(event,args):
    global open_count
    if event!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
    mode=args[1] if len(args)>1 else None
    flags=args[2] if len(args)>2 else 0
    if isinstance(mode,str) and any(c in mode for c in ('w','a','x')):return
    if mode is None and type(flags) is int and flags & os.O_WRONLY:return
    path=Path(os.fsdecode(args[0])).resolve();open_count+=1
    is_old_private=(path.suffix.lower()=='.json' and ROOT in path.parents
        and not any(path==root or root in path.parents for root in allowed_json_roots))
    is_old_private|=(('annual_go' in path.parts or 'annual_go_2024' in path.parts or path.name.upper().startswith('ROOT_GO'))
        and NEW not in path.parents and PREPARATION not in path.parents)
    if is_old_private:
        old_private_body_attempts.append(str(path));raise AssertionError('OLD_PRIVATE_AUTHORITY_BODY_FORBIDDEN:'+str(path))
sys.addaudithook(audit)
sys.path.insert(0,str(NEW))
import numpy as np
import partial_entry as e
import partial_d as d
import run_partial as runner

def pin(path):
    b=Path(path).read_bytes();return dict(SHA256=sha256(b).hexdigest(),bytes=len(b))
def raw(value):return e._canonical(value)
def fixture_authority(preparation):
    p=json.loads(preparation)
    review=raw(dict(schema=e.REVIEW_SCHEMA,status='PASS_SOURCE_ONLY_AND_GENERATED_NO_HISTORICAL_GO',
        **e._authorization_common(preparation,p),**dict.fromkeys(e.REVIEW_FLAGS,True),actual_2021_accounts_constructed=0,
        actual_2021_financial_runs=0,historical_market_minutes_advanced=0,publication_actions=0,locked_source_reads=0))
    go=raw(dict(schema=e.GO_SCHEMA,action=e.ACTION,**e._authorization_common(preparation,p),tranche=e.FIRST_TRANCHE,
        permitted_cells=list(e.tranche_cells()),requested_worker_count=1,worker_CPUs=[4],independent_review_SHA256=e._sha(review)))
    return review,go
checks=[]
def refuses(name,call):
    try:call()
    except (ValueError,TypeError,KeyError,FileNotFoundError):checks.append(name);return
    raise AssertionError('NEGATIVE_GATE_ACCEPTED:'+name)

targets=[(d,'construct_case'),(d.ExpansionAccount,'__init__'),(d.D,'construct_case'),
    (d.D.Guard50ExitAccount,'__init__'),(d.V2,'construct_case'),(d.V2.ContinuationAccount,'__init__'),
    (d.V2.ENGINE.USDTLinearPerpetualAccount,'__init__'),(d.V2.native,'_construct_case'),
    (e.s.g,'make_account'),(e.s.CapturedMinuteProvider,'__call__'),
    (d.V2.native.runtime()[2].EarlierTerminalSimulator,'advance_day'),(e.CaseExecutionScope,'__post_init__'),
    (runner,'case'),(runner,'controller'),(runner,'run_pool'),(runner,'_run_pool'),(runner,'claim_launch'),
    (runner,'controller_lease'),(runner,'save'),(runner,'write_bytes'),(subprocess,'Popen'),(subprocess,'run'),
    (multiprocessing.Process,'start'),(os,'system'),(fcntl,'flock'),(socket,'create_connection'),(urllib.request,'urlopen')]
began=time.monotonic()
with ExitStack() as stack:
    mocks=[stack.enter_context(patch.object(obj,name,side_effect=AssertionError('FORBIDDEN:'+name))) for obj,name in targets]
    preparation=(PREPARATION/'PREPARATION.json').read_bytes();prep=e._validate_preparation(preparation)
    assert prep['code_identity']==e.code_identity()
    review,go=fixture_authority(preparation);cell=e.tranche_cells()[0]
    # Positive source/byte validation only. There are no positive make_case or
    # scope calls here; the nine approved callback probes belong to the author.
    for cell_id in e.tranche_cells():
        admitted,w,rows,decisions,weights,captured=e.validate_case_inputs(e.SOURCE_ROOTS,PREPARATION,go,e._sha(go),cell_id=cell_id)
        assert admitted==prep and not decisions.flags.writeable and not weights.flags.writeable
        assert w['start']==e.s.START and w['end']==e.s.END
        assert all('not_owned_under_fresh_CASH_start' not in x for x in w['events'])
    e._validate_independent_review(preparation,prep,review,e._sha(review),go)
    for key,value in (('action','RUN_OLD_D'),('schema','ROOT_GO_2024'),('policy_version','FORECAST_MONITOR'),
            ('source_scope','GENERATED_FAKE_ORIGIN_ONLY'),('tranche','OLD'),('permitted_cells',list(reversed(e.tranche_cells()))),
            ('requested_worker_count',True),('requested_worker_count',1.0),('requested_worker_count',3),('worker_CPUs',[True]),('worker_CPUs',[-1]),
            ('independent_review_SHA256','x'*64),('preparation_SHA256','0'*64),('policy_identity','0'*64),
            ('fresh_genesis_only',False),('automatic_retry_authorized',True),('halted_snapshot_resume_authorized',True),
            ('annualization_allowed',True),('wallet_compounding_allowed',True),('old_private_GO_bodies_required',True)):
        bad=json.loads(go);bad[key]=value;b=raw(bad)
        refuses('GO:'+key+':'+repr(value),lambda b=b:e.validate_root_go(preparation,b,e._sha(b),cell_id=cell))
    for badcell in ('2024_STATIC50_MID','2021_STATIC50_MID','2021_STATIC50_LOW_APR1_DEC31_D'):
        refuses('CELL:'+badcell,lambda badcell=badcell:e.validate_root_go(preparation,go,e._sha(go),cell_id=badcell))
    for digest in e.OLD_EVIDENCE_HASHES.values():
        refuses('OLD_GO_SHA:'+digest,lambda digest=digest:e.validate_root_go(preparation,go,digest,cell_id=cell))
    refuses('INVALID_TEMPLATE',lambda:e.validate_root_go(preparation,raw(e.invalid_go_template(preparation)),e._sha(raw(e.invalid_go_template(preparation))),cell_id=cell))
    refuses('MISSING_REVIEW_MAKE_CASE',lambda:e.make_case(e.SOURCE_ROOTS,PREPARATION,go,e._sha(go),cell_id=cell))
    refuses('MISSING_GO_MAKE_CASE',lambda:e.make_case(e.SOURCE_ROOTS,PREPARATION,b'{}',e._sha(b'{}'),cell_id=cell))
    badcode=dict(prep['code_identity']);badcode['traditional_D_partial2021_20261015/partial_d.py']='0'*64
    with patch.object(e,'code_identity',return_value=badcode):
        refuses('STALE_CODE_IDENTITY',lambda:e.validate_case_inputs(e.SOURCE_ROOTS,PREPARATION,go,e._sha(go),cell_id=cell))
    for roots in ({2024:e.s.SOURCE_ROOT},{True:e.s.SOURCE_ROOT},{'2021':e.s.SOURCE_ROOT}):
        refuses('SOURCE_ROOT_KEYS:'+repr(list(roots)),lambda roots=roots:e._source_roots(roots))
    for key in e.REVIEW_FLAGS+('actual_2021_accounts_constructed','actual_2021_financial_runs','historical_market_minutes_advanced'):
        bad=json.loads(review);bad[key]=1 if key in e.REVIEW_FLAGS else True;b=raw(bad)
        fixture_go=json.loads(go);fixture_go['independent_review_SHA256']=e._sha(b)
        refuses('REVIEW_TYPE:'+key,lambda b=b,fixture_go=fixture_go:e._validate_independent_review(preparation,prep,b,e._sha(b),raw(fixture_go)))
    for label,change in (
        ('quality_bool_as_zero',lambda p:p['years']['2021']['original200_quality'].__setitem__('imputed',0)),
        ('quality_false_certification',lambda p:p['years']['2021']['original200_quality'].__setitem__('funding_units_certified',True)),
        ('projection_count',lambda p:p['years']['2021']['daily_source_projection'].__setitem__('target_projection_rows',474)),
        ('calendar',lambda p:p['years']['2021'].__setitem__('calendar',[e.s.FULL_START,e.s.END])),
        ('warmup_as_trading',lambda p:p['years']['2021']['original200_quality'].__setitem__('warmup_only_before',e.s.FULL_START)),
        ('source_pin',lambda p:p['years']['2021']['source_files'][e.s.DAILY_MEMBER].__setitem__('SHA256','0'*64)),
        ('duplicate_target_pin',lambda p:p['cells'][cell].__setitem__('selected_target_raw_SHA256','0'*64)),
        ('duplicate_quality_pin',lambda p:p['cells'][cell].__setitem__('quality_sidecar_sha256','0'*64)),
        ('descriptor_tier',lambda p:p['cells'][cell]['descriptor'].__setitem__('tier','HIGH')),
        ('resource_bool',lambda p:p['resource_limits'].__setitem__('maximum_live_workers',True))):
        bad=deepcopy(prep);change(bad)
        refuses('PREPARATION:'+label,lambda bad=bad:e._validate_preparation(raw(bad)))
    for value in (b'{"x":1,"x":2}',b'{"x":NaN}',b'[]',b'null',b'{"x":Infinity}'):
        refuses('JSON:'+value.decode(),lambda value=value:e._object(value,'BAD_JSON'))
    # Input swaps are checked without minting scopes or iterating providers.
    c=e.cell_descriptor(cell)
    with np.load(BytesIO((PREPARATION/'2021/TARGETS.npz').read_bytes()),allow_pickle=False) as z:cov=z['annual_covariance'].copy()
    cov.setflags(write=False)
    _,w,rows,decisions,weights,_=e.validate_case_inputs(e.SOURCE_ROOTS,PREPARATION,go,e._sha(go),cell_id=cell)
    refuses('INPUT_MUTABLE_WINDOW',lambda:e._input_binding(c,dict(w),rows,decisions,weights,cov))
    refuses('INPUT_MUTABLE_ROWS',lambda:e._input_binding(c,w,tuple(dict(r) for r in rows),decisions,weights,cov))
    refuses('INPUT_MUTABLE_COVARIANCE',lambda:e._input_binding(c,w,rows,decisions,weights,cov.copy()))
    mutable=weights.copy()
    refuses('INPUT_MUTABLE_TARGET',lambda:e._input_binding(c,w,rows,decisions,mutable,cov))
    swap=weights.copy();swap[0,0]+=1e-9;swap.setflags(write=False)
    refuses('INPUT_CHANGED_TARGET',lambda:e._input_binding(c,w,rows,decisions,swap,cov))
    for mock in mocks:mock.assert_not_called()
    counts=[dict(boundary=obj.__name__+'.'+name,calls=mock.call_count) for (obj,name),mock in zip(targets,mocks)]
assert not old_private_body_attempts
record=dict(status='PASS_PORTABLE_SOURCE_AND_NEGATIVE_GATES_NO_HISTORICAL_GO',preparation=pin(PREPARATION/'PREPARATION.json'),
    code_identity=e.code_identity(),source_validation_cells=9,negative_checks=len(checks),negative_check_names=checks,
    actual_2021_accounts_constructed=0,actual_2021_financial_runs=0,historical_scopes_created=0,historical_market_minutes_advanced=0,
    actual_positive_make_case_callbacks=0,author_nine_positive_callbacks_not_repeated=True,provider_iterations=0,process_launches=0,canonical_claims_created=0,
    real_GO_files_written=0,all_test_authority_ephemeral_in_memory_only=True,prohibited_boundary_call_counts=counts,
    cold_private_authority_open_attempts=old_private_body_attempts,cold_private_authority_body_reads=old_private_body_reads,
    allowed_permitted_source_and_frozen_public_code_only=True,source_completion_review_SHA256=e.SOURCE_REVIEW_SHA,
    test_script=pin(__file__),wall_seconds=time.monotonic()-began,CPU_affinity=sorted(os.sched_getaffinity(0)),
    observed_task_affinities={p.name:sorted(os.sched_getaffinity(int(p.name))) for p in Path('/proc/self/task').iterdir()},
    maximum_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024)
with (HERE/'GATE_REVIEW_ATTEMPT001.json').open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
print(json.dumps({k:record[k] for k in ('status','negative_checks','wall_seconds','maximum_RSS_bytes')},sort_keys=True),flush=True)
