"""D045 actual module push verification; no market IO or credential output.
Args: exact actual commit, actual commit host result, actual push host result.
Existing accepted Windows remote-head transport is reused; no git/proxy changes.
"""
from datetime import UTC,datetime
import hashlib,json,re,subprocess,sys
from pathlib import Path
root=Path('/mnt/d/codex/coin');state=Path('/home/xflops/coin-state')
archive='docs/archive/PERPETUAL_303_PUSH_VERIFICATION_SOURCE_20261003_V1.py'
acceptance='reports/fast_research/PERPETUAL_303_RESEARCH_ROOT_ACCEPTANCE_20261003_V1.json'
preflight='reports/GITHUB_PERPETUAL_303_STAGED_PREFLIGHT_20261003_V1.json'
out=root/'reports/GITHUB_PERPETUAL_303_SYNC_VERIFIED_20261003_V1.json'
LOCK='state/dataset_lock.json';LOCK_SHA='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
TITLE='D045303日对照 · GitHub同步'
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def small(p):
    p=Path(p);assert p.suffix=='.json' and p.is_file() and not p.is_symlink() and p.stat().st_size<=2_000_000
    return json.loads(p.read_bytes())
assert len(sys.argv)==4 and re.fullmatch('[0-9a-f]{40}',sys.argv[1]) and sys.argv[2] and sys.argv[3]
assert Path(__file__).read_bytes()==(root/archive).read_bytes() and not out.exists()
local=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert local==sys.argv[1]
assert subprocess.check_output(['git','remote','get-url','origin'],cwd=root,text=True).strip()=='https://github.com/snowycat1234/coin.git'
helper='docs/archive/FUNDING_INCOME_REMOTE_HEAD_SOURCE_20261003_V1.ps1';cached='.cache/funding_income_remote_head_20261003_v1.ps1'
assert (root/helper).read_bytes()==(root/cached).read_bytes()
reply=subprocess.check_output(['powershell.exe','-NoProfile','-File','D:/codex/coin/.cache/funding_income_remote_head_20261003_v1.ps1'],cwd=root,timeout=55).decode().strip()
assert re.fullmatch(r'[0-9a-f]{40}\s+refs/heads/main',reply) and reply.split()[0]==local
push_tasks=[]
for p in (state/'task-progress').glob('task-*.json'):
    v=small(p)
    if v.get('title')==TITLE:push_tasks.append(dict(path=str(p),sha256=sha(p),task=v))
assert len(push_tasks)==1 and push_tasks[0]['task']['status']=='completed' and type(push_tasks[0]['task']['exit_code']) is int and push_tasks[0]['task']['exit_code']==0
proof=small(root/acceptance);assert proof['status']=='PASS_ROOT_D045_TWENTY_FIXED303D_CONDITIONAL_ACCOUNTS_NOT_NATIVE_OR_LONG_TERM_APR'
root_task=state/'task-progress'/('task-'+proof['binding']['task_id']+'.json');closed=small(root_task)
assert closed['id']==proof['binding']['task_id'] and closed['status']=='completed' and type(closed['exit_code']) is int and closed['exit_code']==0
assert proof['local_non_git_hash_guard']=={LOCK:LOCK_SHA} and sha(root/LOCK)==LOCK_SHA
assert small(root/preflight)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
value=dict(status='ACKNOWLEDGED_PUSH_AND_EXACT_REMOTE_MAIN_VERIFIED',created_utc=datetime.now(UTC).isoformat(),
    local_commit=local,remote_main=reply.split()[0],module='D045 fixed complete303D source94 and twenty conditional SMA/HOLD/CASH selectors;70 first QA and24 accepted reuse; saved direction/risk comparison, no NAV stitching, funding unit unconfirmed and no native/long APR qualification',
    actual_commit_host_result=sys.argv[2],actual_commit_exit=0,actual_push_host_result=sys.argv[3],actual_git_exit=0,
    host_result_provenance='CALLER_SUPPLIED_ACTUAL_TOOL_RESULTS_WITH_REAL_COMPLETED0_PUSH_TASK_AND_EXACT_REMOTE_HEAD',
    task_bindings=push_tasks,root_actual_closed0_task=dict(path=str(root_task),sha256=sha(root_task),task=closed),
    private_scientific_lock_separately_stream_SHA_verified=True,private_lock_body_read_or_exported=False,
    root_acceptance_path=acceptance,root_acceptance_sha256=sha(root/acceptance),remote_head_transport_path=helper,
    remote_head_transport_sha256=sha(root/helper),force=False,existing_push_transport_path='docs/archive/GITHUB_EXISTING_WINDOWS_TRANSPORT_20261002_V1.ps1',
    preflight=preflight,preflight_sha256=sha(root/preflight),this_verifier_changes_global_git_or_proxy_settings=False,
    credential_scope='Existing authorization; no new credentials',candidate='NO_QUALIFIED_CANDIDATE',long_term_APR='NOT_EVALUABLE')
payload=(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode();assert len(payload)<=4_000_000
with out.open('xb') as f:f.write(payload)
print(json.dumps(dict(status=value['status'],local=local,remote=reply.split()[0],sha256=sha(out))))
