"""Verify the actual normal module commit and exact remote main after push."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
from datetime import UTC, datetime
from quant.paths import ROOT, STATE
PARENT='55798a1795b75c64b63c291a70fa5a84b357ce7f'
assert os.environ['COIN_TASK_ID']
parser=argparse.ArgumentParser();parser.add_argument('--remote-head',required=True);args=parser.parse_args()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
head=git('rev-parse','HEAD');assert head==args.remote_head and git('rev-parse','HEAD~1')==PARENT
assert not git('status','--porcelain=v1','--untracked-files=no')
source=ROOT/'reports/GITHUB_DONCHIAN_ACTIVE_ALLOCATION_SOURCE_BINDING_20261004_V1.json';s=read(source)
for n,h in s['source_hashes'].items():assert sha(ROOT/n)==h,n
wip=git('ls-files','--others','--exclude-standard').splitlines()
assert sorted(wip)==sorted(s['prior_WIP_preserved']) and len(wip)==36
gate=ROOT/'reports/GITHUB_DONCHIAN_ACTIVE_ALLOCATION_STAGED_GATE_20261004_V1.json';g=read(gate)
assert g['status']=='STAGED_MODULE_CHECKPOINT_PASS' and g['worktree_staged_byte_mismatches']==g['high_confidence_secret_pattern_hits']==g['runtime_private_changed_paths']==0
tasks=[read(p) for p in (STATE/'task-progress').glob('task-*.json')]
roles={}
for role,title in dict(SOURCE='D065保存实际激活预算模块来源',GATE='D065提交前源码与敏感信息门槛',
    COMMIT='D065激活预算完整经济对照正常提交',PUSH='D065已验收激活预算模块推送GitHub',
    REMOTE='D065精确核对远端main提交').items():
    found=[t for t in tasks if t['title']==title];assert len(found)==1
    t=found[0];assert t['status']=='completed' and t['exit_code']==0 and t['ended_at'];roles[role]=t
for ident,proof in s['closed_actual_roles'].items():
    t=read(STATE/'task-progress'/('task-'+ident+'.json'))
    assert t['ended_at'] and t['status']==proof['status'] and t['exit_code']==proof['actual_exit_code']
lock=sha(ROOT/'state/dataset_lock.json');assert lock==s['private_SHA_only']
result=dict(status='PUSHED_AND_EXACT_REMOTE_MAIN_VERIFIED',parent_commit=PARENT,local_HEAD=head,
    remote_main=args.remote_head,remote='https://github.com/snowycat1234/coin.git',closed_actual_roles=roles,
    source_binding_sha256=sha(source),staged_gate_sha256=sha(gate),preserved_untracked_paths=wip,
    tracked_worktree_clean=True,private_SHA_only=lock,private_body_read=False,force_push=False,
    new_market_accounts=4,saved_control_accounts=4,financial_calls=4,paired_cases=4,HPO=0,models_fit=0,
    investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',orders_sent=0,locked_consumed=False,
    created_utc=datetime.now(UTC).isoformat(),actual_verifier_source_sha256=sha(Path(__file__)),
    own_artifact_untracked_until_next_normal_module=True)
out=ROOT/'reports/GITHUB_DONCHIAN_ACTIVE_ALLOCATION_SYNC_VERIFIED_20261004_V1.json'
with out.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(local_HEAD=head,remote_main=args.remote_head,path=str(out),sha256=sha(out))),flush=True)
