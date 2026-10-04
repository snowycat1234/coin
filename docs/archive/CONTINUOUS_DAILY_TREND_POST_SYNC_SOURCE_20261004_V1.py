"""Verify exact push and preserve scope distinction after normal module commit."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from datetime import UTC,datetime
ROOT=Path('/mnt/d/codex/coin');STATE=Path('/home/xflops/coin-state');PARENT='29393019aed0e1a3b643877eaf97947f38c25b0c'
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True).strip()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
p=argparse.ArgumentParser();p.add_argument('--remote-head',required=True);args=p.parse_args()
head=git('rev-parse','HEAD');assert os.environ['COIN_TASK_ID'] and head==args.remote_head and git('rev-parse','HEAD~1')==PARENT
assert not git('status','--porcelain=v1','--untracked-files=no')
prior=read(ROOT/'reports/GITHUB_COST_PROVENANCE_SYNC_VERIFIED_20261004_V1.json')
wip=git('ls-files','--others','--exclude-standard').splitlines();assert sorted(wip)==sorted(prior['preserved_untracked_paths']) and len(wip)==36
source=ROOT/'reports/GITHUB_CONTINUOUS_DAILY_TREND_SOURCE_BINDING_20261004_V1.json';s=read(source)
for name,h in s['source_hashes'].items():assert sha(ROOT/name)==h,name
gate=ROOT/'reports/GITHUB_CONTINUOUS_DAILY_TREND_STAGED_GATE_20261004_V1.json';g=read(gate)
assert g['status']=='STAGED_MODULE_CHECKPOINT_PASS' and g['worktree_staged_byte_mismatches']==g['high_confidence_secret_pattern_hits']==g['runtime_private_changed_paths']==0
titles=dict(SOURCE='D064已闭合实际连续303日模块来源保存',GATE='D064提交前源码字节和敏感信息门槛',COMMIT='D064连续303日经济对照正常提交',PUSH='D064已验收连续303日模块推送GitHub',REMOTE='D064精确核对远端main提交')
tasks=[read(p) for p in (STATE/'task-progress').glob('task-*.json')];roles={}
for role,title in titles.items():
    found=[t for t in tasks if t['title']==title];assert len(found)==1
    t=found[0];assert t['status']=='completed' and t['exit_code']==0 and t['ended_at'];roles[role]=dict(task=t,raw_task_sha256=sha(STATE/'task-progress'/('task-'+t['id']+'.json')))
for ident,proof in s['closed_actual_roles'].items():
    t=read(STATE/'task-progress'/('task-'+ident+'.json'));assert t['ended_at'] and t['status']==proof['status'] and t['exit_code']==proof['actual_exit_code']
lock=sha(ROOT/'state/dataset_lock.json');assert lock=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
r=dict(status='PUSHED_AND_EXACT_REMOTE_MAIN_VERIFIED',parent_commit=PARENT,local_HEAD=head,remote_main=args.remote_head,
    remote='https://github.com/snowycat1234/coin.git',closed_actual_roles=roles,source_binding_sha256=sha(source),staged_gate_sha256=sha(gate),
    preserved_untracked_paths=wip,tracked_worktree_clean=True,private_SHA_only=lock,private_body_read=False,force_push=False,new_authentication=False,
    main_accounts=12,complete_saved_calendars=12,producer_budget_passed_accounts=8,producer_budget_failed_accounts=4,complete_financial_calls=12,paired_cases=8,
    HPO=0,models_fit=0,downloads=0,new_QA=0,orders_sent=0,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE',
    adopted='NORMAL_CONTINUOUS_SOURCE_DAILY_ENTRY_FILTER_AND_ECONOMIC_DIAGNOSTICS',
    paused='STATIC_MEMBER_BUDGET_DONCHIAN_INVESTMENT_PROMOTION_UNCERTIFIED_NATIVE_UNITS',
    next_handoff='Active-only signal allocation one-factor full shared-account experiment; no research running after closure.',
    source_sha256=sha(Path(__file__)),created_utc=datetime.now(UTC).isoformat(),own_artifact_untracked_until_next_normal_module=True)
out=ROOT/'reports/GITHUB_CONTINUOUS_DAILY_TREND_SYNC_VERIFIED_20261004_V1.json'
with out.open('x') as f:json.dump(r,f,indent=2);f.write('\n')
print(json.dumps(dict(path=str(out),sha256=sha(out),local_HEAD=head,remote_main=args.remote_head,preserved_WIP=36)),flush=True)
