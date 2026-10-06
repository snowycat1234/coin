"""Persistent continuation from complete development evidence to final publication.

Only small reports are committed on the server. The caller pushes this normal
Git history through its existing authenticated Git client, without force push.
"""
import argparse,json,os,shutil,subprocess,time
from pathlib import Path
from .train import atomic,sha
from .locked_gate import authorize_locked
from .report import compact_case

def public_locked(result,state):
    return dict(status=result['status'],protocol_sha256=result['protocol_sha256'],formal_run=result.get('formal_run',1),
                total_cases=result.get('total_cases',0),rows=[compact_case(c) for c in result['cases']],errors=result.get('errors',[]),
                data_audit=result.get('data_audit'),source_full_results_sha256=sha(Path(state)/'TRANSFORMER_V2_LOCKED_RESULTS.json'),
                source_role='Full immutable native summaries, artifacts and independent audits are in external STATE; no large ledger or checkpoint in Git',
                investment_state='NONE/CASH',no_outcome_driven_selection=True)

def git(repo,*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()

def append_record(repo,event_type,state,locked):
    from scripts.research_v8.registry import append_event,read_verified
    path=repo/'reports/experiment_registry.jsonl';records=read_verified(path.read_bytes())
    event_id='TRANSFORMER_V2_20261007:'+event_type
    if any(r['event_id']==event_id for r in records):return
    prior=next(r for r in records if r['event_id']=='TRANSFORMER_V2_20261007:PREREGISTRATION')
    event={k:v for k,v in prior.items() if k not in ('record_sha256','previous_record_sha256','created_utc')}
    event.update(event_id=event_id,event_type=event_type,git_commit=git(repo,'rev-parse','HEAD'),locked_consumed=locked,
                 result_influenced_later_choice=not locked,success_failure=event_type,
                 reason_for_next_experiment='Registered development choice frozen; one locked experiment only' if not locked else 'Final registered decision; no additional Transformer family or post-locked tuning')
    if locked:event['final_decision_sha256']=sha(state/'TRANSFORMER_V2_FINAL_DECISION.json')
    else:event['candidate_freeze_sha256']=sha(state/'LOCKED_CANDIDATE_FREEZE.json')
    append_event(path,event)

def publish(repo,state,locked=False):
    # Reject unrelated work before any report copy or documentation mutation.
    assert not git(repo,'status','--porcelain'),'Publication refuses a dirty checkout; preserve WIP'
    dest=repo/'reports/transformer_v2';names=['TRANSFORMER_V2_DEV_RESULTS.json','TRANSFORMER_V2_DEV_REPORT.md','TRANSFORMER_V2_DEV_SUMMARY.csv',
                                          'LOCKED_CANDIDATE_FREEZE.json','PREDICTION_METRICS.json','TRANSFORMER_V2_FINAL_FIT_AUDIT.json','DEV_EXPOSURE_RESULTS.json']
    if locked:
        names=['TRANSFORMER_V2_FINAL_REPORT.md','TRANSFORMER_V2_FINAL_DECISION.json','TRANSFORMER_V2_LOCKED_SUMMARY.csv',
               'LOCKED_PREDICTION_METRICS.json','LOCKED_READ_AUTHORIZATION.json','LOCKED_ORACLE_SUPPORT_raw_fraction.json','LOCKED_ORACLE_SUPPORT_raw_percent.json']
    for name in names:
        source=state/name
        if not source.exists():
            assert locked and name in ('TRANSFORMER_V2_LOCKED_SUMMARY.csv','LOCKED_PREDICTION_METRICS.json','LOCKED_ORACLE_SUPPORT_raw_fraction.json','LOCKED_ORACLE_SUPPORT_raw_percent.json')
            continue
        assert source.stat().st_size<=5_000_000,'Compact reports only'
        target=dest/name
        if target.exists():assert target.read_bytes()==source.read_bytes(),'Existing frozen report differs; do not overwrite'
        else:shutil.copyfile(source,target)
    if locked:
        result=json.loads((state/'TRANSFORMER_V2_LOCKED_RESULTS.json').read_text());atomic(dest/'TRANSFORMER_V2_LOCKED_RESULTS.json',public_locked(result,state))
        manifest=json.loads((state/'LOCKED_DATA_MANIFEST.json').read_text())
        atomic(dest/'LOCKED_DATA_AUDIT.json',{k:v for k,v in manifest.items() if k not in ('artifacts','work')})
    dev=json.loads((state/'TRANSFORMER_V2_DEV_RESULTS.json').read_text());status=repo/'docs/RESEARCH_STATUS.md';raw=status.read_bytes()
    first=raw.index('## 2026-10-07：Transformer v2'.encode());end=raw.index('## 2026-10-07：归档'.encode(),first)
    if locked:
        verdict=json.loads((state/'TRANSFORMER_V2_FINAL_DECISION.json').read_text())['decision']
        paragraph=f'## 2026-10-07：Transformer v2 完整研究\n\n最终决定 {verdict["choice"]}. {verdict["decision"]}。投资状态 NONE/CASH，不部署。120个开发fit、24个过去数据最终fit审计通过；开发账户保留全部seed/ensemble/方向/中性/组合与oracle，冻结开发候选后只开一次184日封存实验。{verdict["reason"]}。详见 reports/transformer_v2/TRANSFORMER_V2_FINAL_REPORT.md 与 FINAL_DECISION.json，全部旧证据保留。\n\n'
    else:
        paragraph='## 2026-10-07：Transformer v2 开发报告已冻结\n\n120个开发fit和24个最终past-only fit均审计通过；720个开发原生账户已完成，旧控制账户复用。固定候选 '+dev['chosen']['family']+'/'+dev['chosen']['mapping']+'，development gate='+str(dev['development_gate_pass'])+'。三seed固定平均，未选择赢家seed或pool。开发报告与候选清单已提交后才允许一次2026-03~08封存评估；当前投资状态仍NONE/CASH。详见 reports/transformer_v2/TRANSFORMER_V2_DEV_REPORT.md。\n\n'
    status.write_bytes(raw[:first]+paragraph.encode()+raw[end:])
    with (repo/'docs/RESEARCH_DECISION_LOG.md').open('ab') as f:f.write(('\n\n'+paragraph.rstrip()+'\n').encode())
    append_record(repo,'FINAL_COMPLETE' if locked else 'DEVELOPMENT_FROZEN',state,locked)
    subprocess.run(['git','-C',str(repo),'add','reports/transformer_v2','docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl'],check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Codex','-c','user.email=codex@localhost','commit','-m',
                    'Record final Transformer v2 locked evidence and registered decision' if locked else 'Freeze complete development report and candidate before locked access'],check=True)
    atomic(state/('FINAL_PUBLICATION.json' if locked else 'DEVELOPMENT_PUBLICATION.json'),dict(git_commit=git(repo,'rev-parse','HEAD'),locked=locked,pushed_to_GitHub=False))

def wait_development(state):
    while not (state/'LOCKED_CANDIDATE_FREEZE.json').exists():
        for stage in ('evaluate','dev-report'):
            if stage=='evaluate' and (state/'NATIVE_DEV_RESULTS.json').exists():
                result=json.loads((state/'NATIVE_DEV_RESULTS.json').read_text())
                if result.get('status')=='COMPLETE':continue
                if result.get('status')=='FAILED':raise RuntimeError('Development cases failed; no locked release')
            active=subprocess.check_output(['systemctl','show',f'coin-transformer-v2-{stage}-20261007','-p','ActiveState','--value'],text=True).strip()
            if active not in ('active','activating'):
                # The report may have closed between the existence check and this query.
                if (state/'LOCKED_CANDIDATE_FREEZE.json').exists():return
                raise RuntimeError(f'{stage} is no longer live before development report completion; no blind restart')
        atomic(state/'pipeline-progress.json',dict(stage='WAIT_LIVE_DEVELOPMENT_ACCOUNT_AND_REPORT',pid=os.getpid(),updated_at=time.time()));time.sleep(15)

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);p.add_argument('--collector-root',required=True);p.add_argument('--work',required=True);p.add_argument('--source-run',required=True);a=p.parse_args()
    state=Path(a.state);repo=Path(__file__).resolve().parents[2]
    assert subprocess.check_output(['git','-C',str(repo),'show','HEAD:modules/transformer_v2/pipeline.py'])==Path(__file__).read_bytes()
    python=os.sys.executable
    def stage(name,module,args):
        atomic(state/'pipeline-progress.json',dict(stage=name,pid=os.getpid(),updated_at=time.time()))
        command=['sudo','systemd-run','--wait','--unit=coin-transformer-v2-'+name.lower().replace('_','-')+'-20261007',
                 '--property=User=ubuntu','--property=WorkingDirectory='+str(repo),'--property=Environment=PYTHONUNBUFFERED=1',
                 '--property=StandardOutput=append:'+str(state/(name.lower()+'.log')),'--property=StandardError=append:'+str(state/(name.lower()+'.log')),
                 python,'-m','modules.transformer_v2.'+module,*args]
        subprocess.run(command,check=True)
    common=['--state',str(state),'--collector-root',a.collector_root,'--work',a.work,'--source-run',a.source_run]
    try:
        wait_development(state)
        if not (state/'DEV_EXPOSURE_RESULTS.json').exists():stage('DEV_EXPOSURE','development_exposure',common+['--complete-run','/home/ubuntu/coin/execution-state/automation/server-complete-20261007-hardware','--workers','10'])
        if not (state/'DEVELOPMENT_PUBLICATION.json').exists():publish(repo,state)
        authorize_locked(state,repo)
        if not (state/'LOCKED_DATA_MANIFEST.json').exists():stage('LOCKED_DATA','locked_data',common+['--workers','16'])
        if not (state/'TRANSFORMER_V2_LOCKED_RESULTS.json').exists():stage('LOCKED_EVALUATE','locked_evaluate',common+['--workers','10'])
        stage('FINAL_REPORT','final_report',['--state',str(state)])
        if not (state/'FINAL_PUBLICATION.json').exists():publish(repo,state,True)
        atomic(state/'pipeline-progress.json',dict(stage='COMPLETE_RESEARCH_PENDING_HOST_PUSH_AND_FINAL_AUDIT',git_commit=git(repo,'rev-parse','HEAD'),updated_at=time.time()))
    except BaseException as exc:
        atomic(state/'PIPELINE_FAILURE.json',dict(error=str(exc),time=time.time(),stage=json.loads((state/'pipeline-progress.json').read_text()).get('stage')));raise

if __name__=='__main__':main()
