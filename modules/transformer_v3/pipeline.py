"""Durable finite server pipeline, strict phase order, no restart of valid outputs.

Source/protocol commits are explicit release gates; no automatic source editing,
model search, locked tuning or destructive recovery is performed by this runner.
"""
import argparse,json,os,platform,subprocess,sys,time
from pathlib import Path
from modules.transformer_v2.train import atomic,sha

def progress(state,stage,**extra):
    value=dict(stage=stage,pid=os.getpid(),updated_at=time.time(),**extra)
    atomic(state/'pipeline-progress.json',value);print(json.dumps(value),flush=True)

def wait_file(state,path,predicate,stage,service=None):
    while True:
        if path.exists():
            value=json.loads(path.read_text())
            if predicate(value):return value
            if value.get('status')=='FAILED' or value.get('errors'):raise RuntimeError('Prior phase failure preserved: '+str(path))
        if service:
            active=subprocess.check_output(['systemctl','show',service,'-p','ActiveState','--value'],text=True).strip()
            if active not in ('active','activating'):raise RuntimeError('Prior phase service is not running and no successful receipt exists')
        detail={}
        old=state/'replay-progress.json'
        if stage=='WAIT_FROZEN_V2_REPLAY' and old.exists():detail=json.loads(old.read_text())
        progress(state,stage,detail=detail);time.sleep(20)

def committed(repo,relative):
    path=repo/relative
    if not path.exists():return False
    value=subprocess.run(['git','-C',str(repo),'show','HEAD:'+relative],capture_output=True)
    return value.returncode==0 and value.stdout==path.read_bytes()

def require_release(state,repo):
    names=('scripts/investment/audit_shared_direction.py','src/quant/bybit_isolated_account.py',
           'modules/transformer_v3/isolated_audit.py','modules/transformer_v3/wallet.py')
    receipt=state/'EVENT_ORDERING_REPAIR_RECEIPT.json'
    while True:
        if receipt.exists() and all(committed(repo,n) for n in names):
            proof=json.loads(receipt.read_text())
            if proof.get('status')=='PASS_EVENT_ORDERING_AND_DEFAULT_GOLDEN' and all(sha(repo/n)==proof['sources'][n] for n in names):return
        progress(state,'WAIT_COMMITTED_EVENT_ORDERING_REPAIR_AND_TESTS');time.sleep(20)

def run_module(state,module,args,expected=None):
    if expected is not None and expected.exists():
        prior=json.loads(expected.read_text())
        if prior.get('status') not in ('COMPLETE','DEVELOPMENT_COMPLETE_LOCKED_ECONOMICS_NOT_READ','FINAL_IMPUTED_LOCKED_SENSITIVITY_COMPLETE'):
            # Resumable modules independently validate every saved checkpoint/task;
            # a partially completed aggregate is not considered completed here.
            pass
        elif not prior.get('errors'):
            progress(state,module,action='VERIFY_AND_REUSE_COMPLETED_OUTPUT')
    progress(state,module,action='RUN_OR_VALIDATE_AND_RESUME')
    subprocess.run([sys.executable,'-u','-m','modules.transformer_v3.'+module,*args],check=True)

def main():
    p=argparse.ArgumentParser()
    for flag in ('state','v2-state','collector-root','work','source-run'):p.add_argument('--'+flag,required=True)
    p.add_argument('--workers',type=int,default=None);a=p.parse_args()
    if platform.system()!='Linux' or os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower():raise RuntimeError('Independent cloud Linux server only')
    state=Path(a.state).resolve();repo=Path(__file__).resolve().parents[2]
    if state.is_relative_to(repo):raise ValueError('External immutable scientific state required')
    if not committed(repo,'modules/transformer_v3/pipeline.py'):raise ValueError('Commit runner source before dispatch')
    workers=a.workers or len(os.sched_getaffinity(0));full_args=['--state',a.state,'--v2-state',a.v2_state,'--collector-root',a.collector_root,'--work',a.work,'--source-run',a.source_run]
    try:
        wait_file(state,state/'V2_BYBIT_LIQUIDATION_REPLAY.json',lambda r:r.get('status')=='COMPLETE' and not r.get('errors') and len(r['cases'])==864,
                  'WAIT_FROZEN_V2_REPLAY','coin-transformer-v3-replay-full-20261007.service')
        if not (state/'V2_REPLAY_ANALYSIS.json').exists():run_module(state,'replay_analysis',['--state',a.state,'--v2-state',a.v2_state])
        require_release(state,repo)
        proto='reports/transformer_v3/TRANSFORMER_V3_PROTOCOL.json'
        if not (repo/proto).exists():run_module(state,'protocol',['--state',a.state])
        while not committed(repo,proto):progress(state,'WAIT_COMMITTED_PROTOCOL_BEFORE_ANY_POLICY_FIT');time.sleep(20)
        progress(state,'PROTOCOL_COMMITTED',protocol_sha256=sha(repo/proto),workers=workers)
        # This fixed risk comparison receives priority before any new policy fit.
        run_module(state,'evaluate_policy',[*full_args,'--half-controls-only','--workers',str(workers)],state/'half-controls/HALF_CONTROL_RESULTS.json')
        train_args=['--state',a.state,'--collector-root',a.collector_root,'--work',a.work,'--source-run',a.source_run]
        run_module(state,'train_policy',train_args,state/'POLICY_FIT_PROGRESS.json')
        run_module(state,'final_policy',train_args,state/'POLICY_FINAL_FITS.json')
        run_module(state,'evaluate_policy',[*full_args,'--workers',str(workers)],state/'policy-development/POLICY_DEVELOPMENT_RESULTS.json')
        run_module(state,'development_report',['--state',a.state,'--v2-state',a.v2_state,'--source-run',a.source_run],state/'TRANSFORMER_V3_DEV_RESULTS.json')
        run_module(state,'locked_bridge_data',full_args)
        run_module(state,'locked_evaluate',[*full_args,'--workers',str(workers)],state/'IMPUTED_LOCKED_SENSITIVITY.json')
        run_module(state,'final_report',['--state',a.state],state/'TRANSFORMER_V3_FINAL_RESULTS.json')
        progress(state,'COMPLETE_ALL_REGISTERED_RESEARCH_PHASES',report_sha256=sha(state/'TRANSFORMER_V3_FINAL_REPORT.md'),
                 remaining='SOURCE_AND_SMALL_EVIDENCE_PUBLICATION_PLUS_PROTECTED_V2_INTEGRITY_CLOSEOUT')
    except BaseException as exc:
        progress(state,'FAILED_PRESERVE_AND_INSPECT',error_type=type(exc).__name__,error=str(exc));raise

if __name__=='__main__':main()
