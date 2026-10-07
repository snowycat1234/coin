"""Durable finite server pipeline, strict phase order, no restart of valid outputs.

Source commits are explicit release gates. The already authorized outcome-blind
protocol is committed after completed replay analysis, without editing sources,
model search, locked tuning or destructive recovery.
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

def commit_protocol(state,repo,relative):
    if not committed(repo,relative):
        # One generated metadata file only. Other staged/unstaged work is never
        # included; no source recipe or parameter is changed by this operation.
        subprocess.run(['git','-C',str(repo),'add','--',relative],check=True)
        subprocess.run(['git','-C',str(repo),'-c','user.name=Codex','-c','user.email=codex@localhost',
            'commit','--only','-m','Freeze oracle-policy protocol after complete v2 neutral replay analysis','--',relative],check=True)
    if not committed(repo,relative):raise ValueError('Generated protocol not committed exactly')
    head=subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
    receipt=state/'PROTOCOL_COMMIT_RECEIPT.json'
    value=dict(protocol_sha256=sha(repo/relative),committed_HEAD=head,source_editing=False)
    if receipt.exists():
        prior=json.loads(receipt.read_text())
        if prior['protocol_sha256']!=value['protocol_sha256']:raise ValueError('Protocol commit receipt changed')
    else:atomic(receipt,value)

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

def run_cpu_gpu_modules(state,cpu_args,gpu_args,final=False):
    label='PARALLEL_GPU_FINAL_FITS_AND_CPU_POLICY_WALLETS' if final else 'PARALLEL_GPU_POLICY_FITS_AND_CPU_HALF_CONTROLS'
    progress(state,label)
    children=[]
    for module,args in (('evaluate_policy',cpu_args),('final_policy' if final else 'train_policy',gpu_args)):
        child=subprocess.Popen([sys.executable,'-u','-m','modules.transformer_v3.'+module,*args]);children.append((module,child))
    while children:
        remaining=[]
        for module,child in children:
            code=child.poll()
            if code is None:remaining.append((module,child))
            elif code:
                # Other independent work can retain its valid completed outputs;
                # downstream development and locked stages are never released.
                raise RuntimeError(module+' failed with exit '+str(code)+'; inspect preserved checkpoints/log')
        children=remaining
        progress(state,label,active_modules=[m for m,_ in children])
        if children:time.sleep(10)

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
        commit_protocol(state,repo,proto)
        progress(state,'PROTOCOL_COMMITTED',protocol_sha256=sha(repo/proto),workers=workers)
        train_args=['--state',a.state,'--collector-root',a.collector_root,'--work',a.work,'--source-run',a.source_run]
        half_args=[*full_args,'--half-controls-only','--workers',str(workers)]
        proto_data=json.loads((repo/proto).read_text())
        if proto_data['neutral_replay_gate']:
            # User priority: a stable repaired old neutral signal first receives
            # the fixed risk-budget check before adding new policy supervision.
            run_module(state,'evaluate_policy',half_args,state/'half-controls/HALF_CONTROL_RESULTS.json')
            run_module(state,'train_policy',train_args,state/'POLICY_FIT_PROGRESS.json')
        else:run_cpu_gpu_modules(state,half_args,train_args)
        run_cpu_gpu_modules(state,[*full_args,'--workers',str(workers)],train_args,final=True)
        run_module(state,'development_report',['--state',a.state,'--v2-state',a.v2_state,'--source-run',a.source_run],state/'TRANSFORMER_V3_DEV_RESULTS.json')
        run_module(state,'locked_bridge_data',full_args)
        run_module(state,'locked_evaluate',[*full_args,'--workers',str(workers)],state/'IMPUTED_LOCKED_SENSITIVITY.json')
        run_module(state,'final_report',['--state',a.state],state/'TRANSFORMER_V3_FINAL_RESULTS.json')
        progress(state,'COMPLETE_ALL_REGISTERED_RESEARCH_PHASES',report_sha256=sha(state/'TRANSFORMER_V3_FINAL_REPORT.md'),
                 remaining='SOURCE_AND_SMALL_EVIDENCE_PUBLICATION_PLUS_PROTECTED_V2_INTEGRITY_CLOSEOUT')
    except BaseException as exc:
        progress(state,'FAILED_PRESERVE_AND_INSPECT',error_type=type(exc).__name__,error=str(exc));raise

if __name__=='__main__':main()
