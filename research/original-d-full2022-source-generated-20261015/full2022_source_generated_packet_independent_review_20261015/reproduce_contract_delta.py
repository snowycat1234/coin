"""Independent fake-only diagnosis; writes only new reviewer artifacts."""
import os,sys,json,time,resource,runpy
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
CPU=1
os.sched_setaffinity(0,{CPU});sys.dont_write_bytecode=True
THREADS=('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','POLARS_MAX_THREADS','VECLIB_MAXIMUM_THREADS')
for key in THREADS:os.environ[key]='1'
HERE=Path(__file__).resolve().parent;PACKET=HERE.parent/'full2022_source_generated_packet_20261015_v1'
os.environ['FULL2022_REVIEW_DIR']='traditional_D_full2022_20261015_v2'
initial={p.relative_to(PACKET).as_posix():sha256(p.read_bytes()).hexdigest() for p in PACKET.rglob('*.py')}
reads=[];denied=[];affinity_remaps=[]
def audit(event,args):
    if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
        denied.append(event);raise AssertionError('NETWORK_OR_EXTERNAL_PROCESS_FORBIDDEN')
    if event!='open' or not args or not isinstance(args[0],(str,bytes,os.PathLike)):return
    p=Path(os.fsdecode(args[0])).resolve()
    if PACKET in p.parents:
        rel=p.relative_to(PACKET).as_posix()
        if 'source_only_projections' in p.parts or p.suffix.lower() in ('.npz','.npy','.zip','.parquet','.bin') or p.name in ('PREPARATION.json','TARGET_PROOFS.json','SOURCE_PREP_GO.json','ROOT_SOURCE_STAGE_GO_APPROVED_attempt001.json'):
            denied.append(rel);raise AssertionError('SOURCE_ARRAY_OR_PRIVATE_AUTHORITY_BODY_FORBIDDEN')
        reads.append(rel)
    elif HERE.parent in p.parents and HERE not in p.parents and HERE.parent/'coin_partial_restore_20261014/.venv' not in p.parents:
        denied.append('OUTSIDE_PACKET_WORKSPACE_READ');raise AssertionError('WORKSPACE_READ_OUTSIDE_REVIEW_PACKET_FORBIDDEN')
sys.addaudithook(audit)
original=os.sched_setaffinity
def affinity(pid,mask):
    assert pid==0 and set(mask)=={6}
    affinity_remaps.append({'original_CPU':6,'assigned_CPU':CPU});return original(0,{CPU})
began=time.monotonic()
with patch.object(os,'sched_setaffinity',affinity):
    m=runpy.run_path(str(PACKET/'traditional_D_full2022_independent_review_20261015/review_generated_core.py'),run_name='independent_original_generated_review')
np=m['np'];d=m['d'];old=m['old']
def delta(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        out=[]
        for key in sorted(set(a)|set(b)):
            at=path+'/'+key
            if key not in a:out.append(dict(path=at,kind='ADDED_KEY',new=b[key]))
            elif key not in b:out.append(dict(path=at,kind='MISSING_KEY',old=a[key]))
            else:out.extend(delta(a[key],b[key],at))
        return out
    if isinstance(a,list) and isinstance(b,list):
        if len(a)!=len(b):return [dict(path=path,kind='LIST_LENGTH_CHANGED',old=len(a),new=len(b))]
        return [item for i,(x,y) in enumerate(zip(a,b)) for item in delta(x,y,path+'/'+str(i))]
    return [] if type(a) is type(b) and a==b else [dict(path=path,kind='TYPE_OR_VALUE_CHANGED',old=a,new=b)]
expected=[dict(path='/contract/actual_historical_liquidation_or_no_liquidation_certified',kind='ADDED_KEY',new=False),dict(path='/contract/source27_event_and_position_interval_impact',kind='ADDED_KEY',new='PENDING_ACTUAL_SAVED_EVIDENCE')]
cases=[]
for tier in d.TIERS:
    window,rows,decisions=m['fixture'](1)
    assert window['fixture_scope']=='GENERATED_FAKE_ORIGIN_ONLY'
    baseline,bg=old.construct_case(window,rows,decisions,np.full((1,5),.03),tier_name=tier,generated_scope=old.GENERATED)
    current,cg=d.construct_case(window,rows,decisions,np.full((1,5),.03),tier_name=tier,generated_scope=d.GENERATED)
    for sim in (baseline,current):m['run'](sim)
    before=m['financial_snapshot'](baseline.account);after=m['financial_snapshot'](current.account)
    differences=delta(before,after);assert differences==expected,(tier,differences)
    assert before!=after
    for row in expected:after['contract'].pop(row['path'].rsplit('/',1)[1])
    assert before==after
    left=baseline.result()['minute'].to_numpy();right=current.result()['minute'].to_numpy()
    assert left.shape==right.shape and left.dtype==right.dtype and left.tobytes()==right.tobytes()
    assert bg.receipts==cg.receipts
    result=d.case_result(current,cg);assert result['economics']['paid_flat']
    result.pop('minute');result['targets']=result['targets'].to_dicts()
    proof=m['reconcile_saved_native'](m['export'](current.account),d.V2.OWNED.export_tree(result),expected_continuation_version=d.VERSION)
    assert proof['passed'] and not proof['tolerance_or_epsilon_used']
    assert not current.account.transfer_journal and not current.account.settlement_journal
    cases.append(dict(tier=tier,exact_archived_whole_snapshot_equality=False,structural_differences=differences,missing_keys=0,changed_existing_values=0,complete_snapshot_equal_after_removing_only_two_new_contract_keys=True,minute_matrix_bits_equal=True,minute_matrix_shape=list(left.shape),minute_matrix_dtype=str(left.dtype),minute_matrix_SHA256=sha256(left.tobytes()).hexdigest(),guard_receipts_equal=True,native_reconciliation_passed=True,native_reconciliation_tolerance_or_epsilon_used=False))
changed=[name for name,digest in initial.items() if sha256((PACKET/name).read_bytes()).hexdigest()!=digest];assert not changed
record=dict(schema='INDEPENDENT_FULL2022_FAKE_ONLY_CONTRACT_DELTA_DIAGNOSIS_V1',status='PASS_PRECISE_TWO_NEW_CONTRACT_KEY_DIAGNOSIS',exact_archived_whole_snapshot_test_status='FAIL_REPRODUCED_UNMODIFIED_EXPECTATION',not_claimed_resolved_or_passed=True,fixture_scope='GENERATED_FAKE_ORIGIN_ONLY',cases=cases,CPU_affinity=sorted(os.sched_getaffinity(0)),all_TID_affinities={p.name:sorted(os.sched_getaffinity(int(p.name))) for p in Path('/proc/self/task').iterdir()},CPU_only_archived_load_time_remaps=affinity_remaps,thread_environment={key:os.environ[key] for key in THREADS},actual_source_reads=0,actual_accounts=0,actual_historical_market_minutes=0,actual_GO_or_claims=0,network_or_subprocess_calls=0,blocked_forbidden_attempts=denied,source_files_changed=changed,read_file_set=sorted(set(reads)),wall_seconds=time.monotonic()-began,max_RSS_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,script_SHA256=sha256(Path(__file__).read_bytes()).hexdigest())
assert not denied
(HERE/'INDEPENDENT_GENERATED_CONTRACT_DIAGNOSIS.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n')
print(json.dumps({key:record[key] for key in ('status','exact_archived_whole_snapshot_test_status','actual_source_reads','actual_accounts','wall_seconds','max_RSS_bytes')}))
