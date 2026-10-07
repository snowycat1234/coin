import argparse,concurrent.futures,fcntl,multiprocessing,os,subprocess,sys,time,traceback
from pathlib import Path
from .common import atomic,guard,read,sha,stamp

def run(state,repo,workers):
    state.mkdir(parents=True,exist_ok=True);guard(state)
    lock=(state/'RUN.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    started=time.time();progress=state/'PROGRESS.json'
    def update(stage,label,**extra):
        value=dict(status='RUNNING',stage=stage,stages=6,label=label,updated=time.time(),started=started,workers=workers,**extra)
        atomic(progress,value);print(f'[{stamp()}] {stage}/6 {label} '+str(extra),flush=True)
    binding_path=state/'RUN_BINDING.json'
    sources=[p for p in sorted((repo/'modules/expert_aggregation').rglob('*')) if p.is_file() and p.suffix in ('.py','.json','.sh')]
    sources += [repo/p for p in ('scripts/investment/perpetual_directional.py','scripts/investment/frozen_expert_mixture.py','scripts/investment/cta_cycle_window.py','scripts/investment/audit_shared_direction.py','scripts/investment/bybit_cost_inputs.py','src/quant/perpetual_account.py','src/quant/bybit_isolated_account.py','modules/transformer_v3/isolated_audit.py')]
    current={p.relative_to(repo).as_posix():sha(p) for p in sources}
    if binding_path.exists():
        binding=read(binding_path)
        if binding['source_hashes']!=current:raise ValueError('Registered source changed; retain this run, use a new explicit run identity for changed science')
    else:
        atomic(binding_path,dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip(),source_hashes=current,
            preregistration_sha256=sha(repo/'modules/expert_aggregation/protocol.json'),created_at=stamp(),execution_server=os.uname().nodename,
            resource_limits='Actual server resources; no CPU/RAM quota; shared memmap; 15GiB free-disk guard',python=sys.version))
    update(1,'工程反例与既有强平/现金退出测试')
    tests=['tests/test_expert_aggregation_allocator.py','tests/test_expert_aggregation_funding.py','tests/test_cash_close_retry.py','modules/transformer_v3/test_liquidation.py','modules/transformer_v3/test_liquidation_engine.py']
    with (state/'TESTS.log').open('w') as log:
        status=subprocess.run([sys.executable,'-m','pytest','-q',*tests,'--basetemp',str(state/'pytest-temp')],cwd=repo,stdout=log,stderr=subprocess.STDOUT).returncode
    atomic(state/'TESTS.json',dict(exit_code=status,log_sha256=sha(state/'TESTS.log'),source_hashes=current))
    if status:raise RuntimeError('Synthetic/financial tests failed; see TESTS.log')
    update(2,'复用输入 SHA 与完整日历缓存')
    from .inputs import prepare
    cached=state/'cache/INPUT_BINDING.json'
    if not cached.exists():prepare(repo,state,state/'reuse')
    else:
        for entry in read(cached)['files']:
            if sha(state/'cache'/entry['path'])!=entry['sha256']:raise ValueError('Completed cache changed')
    update(3,'冻结因果权重与单钱包目标，验证过去协方差')
    from .paths import prepare as prepare_paths
    path_info=read(state/'PATHS.json') if (state/'PATHS.json').exists() else prepare_paths(state)
    protocol=read(repo/'modules/expert_aggregation/protocol.json');tasks=[]
    weight_map={(r['algorithm'],r['unit']):r for r in path_info['records']}
    for scenario in protocol['scenarios']:
        algorithms=protocol['dynamic_wallets']+protocol['base_controls'] if scenario=='BASE27' else protocol['pressure_wallets']
        for unit in protocol['units']:
            for algorithm in algorithms:
                entry=weight_map[algorithm,unit]
                if sha(entry['weights_path'])!=entry['weights_sha256'] or sha(entry['target_path'])!=entry['target_sha256']:raise ValueError('Frozen paths changed')
                tasks.append(dict(id=algorithm+'-'+unit+'-'+scenario,algorithm=algorithm,unit=unit,scenario=scenario,repo=str(repo),state=str(state),weight_sha256=entry['weights_sha256'],target_sha256=entry['target_sha256']))
    if len(tasks)!=28:raise ValueError('Finite registered 28-account budget')
    atomic(state/'TASKS.json',tasks);(state/'accounts').mkdir(exist_ok=True);(state/'progress').mkdir(exist_ok=True)
    update(4,'完整逐分钟账户与独立核验',completed=0,total=len(tasks))
    from .worker import execute
    receipts=[]
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) as pool:
        futures={pool.submit(execute,t):t for t in tasks}
        for future in concurrent.futures.as_completed(futures):
            receipt=future.result();receipts.append(receipt)
            atomic(state/'ACCOUNTS.json',receipts)
            update(4,'完整逐分钟账户与独立核验',completed=len(receipts),total=len(tasks),last=futures[future]['id'])
    receipts.sort(key=lambda r:r['task']['id']);update(5,'同口径比较、阶段贡献、块不确定性与报告')
    from .report import build
    result=build(state,repo,receipts);update(6,'按证据审查第二轮继续条件',classification=result['classification'],round_2=result['round_2'])
    atomic(progress,dict(status='COMPLETE',stage=6,stages=6,label='有限任务完成，报告已生成',completed=28,total=28,classification=result['classification'],updated=time.time(),started=started,workers=workers))
    print(f'[{stamp()}] COMPLETE {result["classification"]} {state/"delivery/REPORT.md"}',flush=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',type=Path,required=True);p.add_argument('--workers',type=int,default=min(8,os.cpu_count() or 1));args=p.parse_args()
    repo=Path(__file__).resolve().parents[2];state=args.state.resolve()
    if not state.is_relative_to(Path('/home/ubuntu/coin/execution-state')) or state.is_relative_to(repo):raise ValueError('External server run directory required')
    os.environ['QUANT_ROOT']=str(repo);os.environ['QUANT_STATE']='/home/ubuntu/coin/execution-state'
    sys.path.insert(0,str(repo/'src'));sys.path.insert(0,str(repo))
    try:run(state,repo,max(1,min(args.workers,os.cpu_count() or 1)))
    except Exception as exc:
        atomic(state/'FAILURE.json',dict(error=repr(exc),traceback=traceback.format_exc(),updated=time.time()))
        value=read(state/'PROGRESS.json') if (state/'PROGRESS.json').exists() else {}
        atomic(state/'PROGRESS.json',{**value,'status':'FAILED','error':str(exc),'updated':time.time()})
        raise

if __name__=='__main__':main()
