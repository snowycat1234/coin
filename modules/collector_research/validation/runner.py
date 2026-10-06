"""Replay frozen fold targets on the common, preflighted complete-data windows."""
import concurrent.futures,csv,fcntl,json,multiprocessing,os,signal,sys,time
from datetime import datetime,timezone
from pathlib import Path
from .runtime import ROOT,WORK,REPO,STATE,RUN,SOURCE,CONFIG,DAY,atomic,sha,progress,kernel_guard
from .data import (MODELS,CONTROLS,target_series,market_window,Reporter,engine,independent,
    USDTLinearPerpetualAccount,saved_case_valid)
import numpy as np
import polars as pl
from .audit import plan


def frozen_targets(study,name,symbols,window):
    dates,weights=target_series(Path(study),name,symbols)
    selected=(dates>=window['start'])&(dates<window['end']);dates=dates[selected];weights=weights[selected]
    if not np.array_equal(dates,np.arange(window['start'],window['end'],DAY,dtype=np.int64)):
        raise ValueError('Frozen model lacks exact requested window calendar')
    inactive=[i for i,s in enumerate(symbols) if s not in window['active_symbols']]
    if inactive and np.any(weights[:,inactive]!=0):raise ValueError('Target outside original fold training universe')
    weights=weights.copy();weights[dates>=window['end']-DAY]=0.
    return dates,weights

def worker(task):
    name,tag,scale,window,selection,run,binding=task
    base=Path(run)/'native'/tag/window['id']/name;base.mkdir(parents=True,exist_ok=True)
    result=base/'RESULT.json';status=base/'progress.json'
    if result.exists():
        value=json.loads(result.read_text());saved_case_valid(value,binding);return value
    attempts=[p for p in base.glob('attempt-*') if p.is_dir()]
    if len(attempts)>=2:raise RuntimeError('Two native attempts used; review failure artifacts before retry')
    attempt=base/f'attempt-{len(attempts)+1}';attempt.mkdir();atomic(attempt/'BINDING.json',binding)
    reporter=Reporter(status,f'{window["id"]} {name}, funding={scale}')
    reporter.update('载入完整窗口',0,window['days']*1440)
    began=time.monotonic()
    try:
        dates,weights=frozen_targets(selection['studies'][tag],name,selection['symbols'],window)
        account_input=market_window(selection['symbols'],window['start'],window['end'])
        assert selection['closing_policy']['buffer_days']==1 and selection['closing_policy']['persist_cash_close'] is True
        blocks=account_input['minute_blocks']
        def complete_blocks():
            for block in blocks():
                if not set(window['active_symbols'])<=set(block['market']):
                    raise ValueError('Preflighted complete window contains a missing required asset')
                yield block
        account_input['minute_blocks']=complete_blocks
        targets=pl.DataFrame(dict(available_us=np.repeat(dates,len(selection['symbols'])),
            symbol=selection['symbols']*len(dates),target_weight=weights.reshape(-1)))
        def factory(bars,decisions,mode):
            assert np.array_equal(decisions,dates)
            return targets,dict(source='REUSED_FROZEN_FOLD_TARGETS_COMMON_COMPLETE_WINDOW',
                window_id=window['id'],fold=window['fold'],independent_initial_capital=10000,
                source_study=selection['studies'][tag],no_return_splicing=True,closing_policy=selection['closing_policy'])
        def guard():
            kernel_guard()
            if kernel_guard().get('resource_policy')!='server' and time.monotonic()-began>3600:raise RuntimeError('Finite one-hour per-window-case budget exhausted')
        case=engine.simulate(account_input,'LONG_SHORT',engine.COSTS[0],
            dict(id='RAW_AS_FRACTION' if scale==1 else 'RAW_AS_PERCENT',scale=scale),reporter,guard,
            target_factory=factory,account_factory=USDTLinearPerpetualAccount,persist_cash_close=True)
        directory=attempt/'account';saved=engine.save_case(case,directory);atomic(directory/'summary.json',saved['summary'])
        del case,account_input,targets
        import gc;gc.collect()
        reporter.update('独立核对窗口账本',None,None)
        audit=independent.verify(directory,selection['symbols'],scale);atomic(attempt/'INDEPENDENT_AUDIT.json',audit)
        s=saved['summary'];full=s['completed_minutes']==s['required_minutes'] and s['terminal_cash_realized']
        value=dict(binding=binding,window=window,model=name,funding_scale=scale,summary=s,
            summary_path=str(directory/'summary.json'),summary_sha256=sha(directory/'summary.json'),
            artifacts=saved['artifacts'],independent_audit=audit,independent_audit_path=str(attempt/'INDEPENDENT_AUDIT.json'),
            independent_audit_sha256=sha(attempt/'INDEPENDENT_AUDIT.json'),
            economic_calendar_complete=s['completed_minutes']==s['required_minutes'],terminal_cash_realized=s['terminal_cash_realized'],
            elapsed_seconds=time.monotonic()-began)
        atomic(result,value)
        reporter.update('账户案例完成',s['completed_minutes'],s['required_minutes'],full_window_and_cash=full)
        return value
    except Exception as exc:
        atomic(attempt/'FAILURE.json',dict(error_type=type(exc).__name__,error=str(exc)));raise

def stamp(value):return datetime.fromtimestamp(value/1e6,timezone.utc).strftime('%Y-%m-%d')

def report(run,publish_original=False):
    selection=json.loads((run/'VALIDATION_PLAN.json').read_text());data=json.loads((run/'NATIVE_RESULTS.json').read_text())
    rows=[]
    for c in data['cases']:
        s=c['summary'];full=c['economic_calendar_complete'] and c['terminal_cash_realized']
        rows.append(dict(window=c['window']['id'],fold=c['window']['fold'],start_UTC=stamp(c['window']['start']),
            end_inclusive_UTC=stamp(c['window']['end']-DAY),days=c['window']['days'],model=c['model'],funding_scale=c['funding_scale'],
            complete_calendar=c['economic_calendar_complete'],terminal_cash=c['terminal_cash_realized'],
            net_USDT=s['net_PnL'] if full else None,return_percent=s['net_return_on_full_initial_capital_percent'] if full else None,
            minute_MDD=s.get('minute_max_drawdown'),all_observation_MDD=s['all_observation_max_drawdown'],
            fees_USDT=s['fees_USDT'],execution_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],
            native_completion=s['completion'],completed_minutes=s['completed_minutes'],required_minutes=s['required_minutes'],
            audit_NAV_error=c['independent_audit']['maximum_NAV_error_USDT'],summary_path=c['summary_path']))
    with (run/'WINDOW_COMPARISON.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lookup={(r['funding_scale'],r['window'],r['model']):r for r in rows}
    table=[]
    for scale in (1.,.01):
        common=[w['id'] for w in selection['windows'] if all(
            (scale,w['id'],m) in lookup and lookup[scale,w['id'],m]['return_percent'] is not None for m in MODELS+CONTROLS)]
        for model in MODELS+CONTROLS:
            subset=[lookup[scale,w,model] for w in common]
            own=[r for r in rows if r['funding_scale']==scale and r['model']==model]
            delta=[r['return_percent']-lookup[scale,r['window'],'BASE_SMA200_SIGNED']['return_percent'] for r in subset]
            table.append(dict(model=model,funding_scale=scale,full_windows=sum(r['return_percent'] is not None for r in own),
                planned_windows=len(selection['windows']),common_comparable_windows=len(common),
                median_window_return_percent=float(np.median([r['return_percent'] for r in subset])) if subset else None,
                median_delta_vs_SMA_percent_points=float(np.median(delta)) if delta else None,
                wins_vs_SMA=sum(v>0 for v in delta),not_a_continuous_account_return=True))
    atomic(run/'MODEL_WINDOW_SUMMARY.json',dict(rows=table,common_windows_required_across_all_models_and_controls=True,
        aggregate_capital_return_not_computed=True,original_promotion_gate_changed=False))
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    matrix=[]
    for scale in (1.,.01):
        matrix.append(np.array([[lookup.get((scale,w['id'],m),{}).get('return_percent')
            if lookup.get((scale,w['id'],m),{}).get('return_percent') is not None else np.nan
            for w in selection['windows']] for m in MODELS+CONTROLS],float))
    finite=np.concatenate([a[np.isfinite(a)] for a in matrix]);limit=max(1.,float(np.abs(finite).max())) if len(finite) else 1.
    fig,axes=plt.subplots(1,2,figsize=(15,6),constrained_layout=True)
    for ax,scale,a in zip(axes,(1.,.01),matrix):
        im=ax.imshow(a,cmap='RdYlGn',vmin=-limit,vmax=limit,aspect='auto')
        ax.set_yticks(range(8),MODELS+CONTROLS)
        ax.set_xticks(range(len(selection['windows'])),[w['id'] for w in selection['windows']],rotation=55,ha='right')
        ax.set_title(f'Independent complete-window net return %; funding={scale}')
        for i in range(8):
            for j in range(len(selection['windows'])):
                ax.text(j,i,'N/E' if not np.isfinite(a[i,j]) else f'{a[i,j]:.1f}',ha='center',va='center',fontsize=8)
    fig.colorbar(im,ax=axes,label='Net return %; independent 10,000 USDT per window')
    fig.savefig(run/'WINDOW_RETURNS.png',dpi=150);plt.close(fig)
    lines=['# COIN 模型与完整数据窗口验证','',
        f'账户案例：{len(rows)}/{selection["total_cases"]}；完整日历且真实平仓：{sum(r["return_percent"] is not None for r in rows)}。',
        f'数据完整区间覆盖 {selection["eligible_days"]}/{selection["requested_days"]} 天，共 {len(selection["windows"])} 段。',
        '全部模型和基线使用相同的数据完整性规则、窗口、成本和资本。区间在本轮账户运行前按来源完整性冻结，不根据盈亏选择。',
        '每段、每模型、每资金费条件是一份独立 10,000 USDT 账户，末尾实际平仓并计费。各段收益不相加、也不拼接成一个长期账户收益。',
        '每段最后24小时统一发出现金目标，复用仓库持续平仓规则，按实际分钟成交量逐步减仓；这一天的全部时间、价格、资金费和执行成本仍计入窗口。',
        '这是已见开发历史的后验完整数据筛查，不是全日历策略收益，也不是独立未见测试。资金费单位仍为两种条件解释。','',
        '## 训练复用与检查',
        '现有模型折和预测全部复用。训练时间切分、标签成熟与配置的时间隔离、过去数据标准化、模型文件哈希和加载权重预测复现检查通过。',
        '训练标签仍是原来的日频数量账户代理，不冒充原生分钟账户标签。原先两资金费条件均未通过基线门槛，最终模型未拟合的结论保持。',
        '详情：TRAINING_AUDIT.json；旧训练报告及旧缺口停止报告保留在原运行目录。','',
        '## 比较摘要',
        '下表为共同完成窗口的等权中位数，不是累计收益；若任一模型在某窗口出现金融停止，该窗口不进入任何模型的共同摘要，但停止案例仍完整保留。',
        '|模型|资金费条件|完整窗口|共同窗口|窗口收益中位数 %|相对 SMA 中位数 百分点|胜过 SMA 窗口|',
        '|---|---:|---:|---:|---:|---:|---:|']
    for row in table:
        num=lambda v:'NOT_EVALUABLE' if v is None else f'{v:.3f}'
        lines.append(f'|{row["model"]}|{row["funding_scale"]}|{row["full_windows"]}/{row["planned_windows"]}|{row["common_comparable_windows"]}|'
            f'{num(row["median_window_return_percent"])}|{num(row["median_delta_vs_SMA_percent_points"])}|{row["wins_vs_SMA"]}|')
    lines.extend(['','## 每个窗口的实际净收益率 %'])
    for scale in (1.,.01):
        lines.extend(['',f'资金费条件 {scale}；所有费用、执行成本和资金费已计入。',
            '|窗口|天数|'+'|'.join(MODELS+CONTROLS)+'|','|---|---:|'+'|'.join(['---:']*8)+'|'])
        for w in selection['windows']:
            vals=[]
            for model in MODELS+CONTROLS:
                row=lookup.get((scale,w['id'],model));v=row['return_percent'] if row else None
                vals.append('NOT_EVALUABLE' if v is None else f'{v:.2f}')
            lines.append(f'|{w["id"]}|{w["days"]}|'+'|'.join(vals)+'|')
    lines.extend(['','## 排除与边界',
        '缺口日期只排除在新的完整窗口验证中；原行情、标签、权重、预测和旧验证结果未改写。'])
    for missing in selection['excluded_gap_days']:
        lines.append(f'- 排除 UTC {stamp(missing["day_us"])}，fold {missing["fold"]}：'+', '.join(missing['reasons']))
    for small in selection['excluded_short_blocks']:
        lines.append(f'- 排除完整但不足冻结的最短窗口长度的区间：{stamp(small["start"])} 至 {stamp(small["end"]-DAY)}，{small["days"]} 天。')
    for row in rows:
        if row['return_percent'] is None:lines.append(f'- 账户未完整且平仓：{row["window"]} {row["model"]} funding={row["funding_scale"]}，{row["native_completion"]}')
    lines.extend(['','数据规则和来源哈希：VALIDATION_PLAN.json / BINDING.json',
        '逐窗口盈亏、回撤、费用、资金费和核验误差：WINDOW_COMPARISON.csv',
        '逐窗口净收益图：WINDOW_RETURNS.png',
        '全部原生账本和独立核验引用：NATIVE_RESULTS.json。没有部署或实盘交易。'])
    (run/'FINAL_REPORT.md').write_text('\n'.join(lines)+'\n')
    complete=len(rows)==selection['total_cases'] and not data['errors']
    assert complete,'Incomplete execution cannot publish a final report'
    if publish_original:
        original=SOURCE/'FINAL_REPORT.md'
        if not (SOURCE/'FINAL_REPORT.before-complete-windows.md').exists():
            import shutil;shutil.copy2(original,SOURCE/'FINAL_REPORT.before-complete-windows.md')
        temp=original.with_suffix('.tmp')
        temp.write_text((run/'FINAL_REPORT.md').read_text()+'\n\n本报告目录：'+str(run)+'\n');temp.replace(original)
    return dict(report=str(run/'FINAL_REPORT.md'),cases=len(rows),fully_closed=sum(r['return_percent'] is not None for r in rows))

def main():
    RUN.mkdir(parents=True,exist_ok=True);resources=kernel_guard()
    unrestricted=resources['resource_policy']=='server'
    workers=CONFIG.get('workers') or (len(os.sched_getaffinity(0)) if unrestricted else 2)
    lock=(STATE/'workflow.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if not (RUN/'VALIDATION_PLAN.json').exists():plan(RUN,RUN/'plan-progress.json')
    selection=json.loads((RUN/'VALIDATION_PLAN.json').read_text())
    assert selection['status']=='FROZEN_BEFORE_NEW_NATIVE_RESULTS'
    assert selection['source_binding_sha256']==sha(SOURCE/'BINDING.json')
    assert selection['dataset_sha256']==sha(WORK/'reports/DATASET_MANIFEST.json')
    for path,digest in selection['reused_artifacts'].items():assert sha(path)==digest,'Reused artifact changed: '+path
    binding=dict(plan_sha256=sha(RUN/'VALIDATION_PLAN.json'),source_binding_sha256=selection['source_binding_sha256'],
        code_sha256={p.name:sha(p) for p in [Path(__file__),Path(__file__).with_name('audit.py')]},
        workers=workers,resource_policy=resources['resource_policy'],RAM_limit_bytes=resources['memory_max'],
        host_memory_bytes=resources['memory_total_bytes'],runtime_common_sha256=sha(Path(__file__).with_name('runtime.py')),original_models_retrained=False,financial_core_sha256={str(p.relative_to(REPO)):sha(p) for p in sorted((REPO/'src/quant').glob('*.py'))+sorted((REPO/'scripts/investment').glob('*.py'))})
    if (RUN/'BINDING.json').exists():assert json.loads((RUN/'BINDING.json').read_text())==binding,'Changed validation recipe; do not reuse silently'
    atomic(RUN/'BINDING.json',binding)
    started=time.time();done=[];errors=[];tasks=[]
    for w in selection['windows']:
        for tag,scale in [('raw_fraction',1.),('raw_percent',.01)]:
            for name in MODELS+CONTROLS:tasks.append((name,tag,scale,w,selection,str(RUN),binding))
    # Restore verified, completed cases before scheduling; never rerun them.
    todo=[]
    for task in tasks:
        name,tag,scale,w,*_=task;p=RUN/'native'/tag/w['id']/name/'RESULT.json'
        if p.exists():
            value=json.loads(p.read_text());saved_case_valid(value,binding);done.append(value)
        else:todo.append(task)
    def publish(state,module='完整窗口原生验证',detail='',**extra):
        resources=kernel_guard()
        atomic(RUN/'status.json',dict(status=state,module=module,module_index=5 if state!='COMPLETE' else 6,
            completed_modules=4 if state!='COMPLETE' else 6,total_modules=6,detail=detail,run_dir=str(RUN),
            elapsed_seconds=time.time()-started,pid=os.getpid(),updated_at=time.time(),
            completed_cases=len(done),total_cases=len(tasks),failed_cases=len(errors),
            memory_current_bytes=resources['memory_current'],host_memory_bytes=resources['memory_total_bytes'],resource_policy=resources['resource_policy'],**extra))
    def interrupted(signum,frame):raise KeyboardInterrupt('Stopped; all finished-case checkpoints retained')
    signal.signal(signal.SIGTERM,interrupted);signal.signal(signal.SIGINT,interrupted)
    pool=concurrent.futures.ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn'))
    pending={};cursor=0
    try:
        while cursor<len(todo) or pending:
            while cursor<len(todo) and len(pending)<workers:
                task=todo[cursor];pending[pool.submit(worker,task)]=task;cursor+=1
            publish('RUNNING',detail=f'仅复用模型，{workers}个CPU账户进程；每个窗口独立资金，不拼接收益')
            finished,_=concurrent.futures.wait(pending,timeout=3,return_when=concurrent.futures.FIRST_COMPLETED)
            for future in finished:
                task=pending.pop(future)
                try:
                    value=future.result();done.append(value)
                    print(f'COMPLETE {len(done)}/{len(tasks)} {task[3]["id"]} {task[0]} funding={task[2]} '
                        f'full={value["economic_calendar_complete"] and value["terminal_cash_realized"]}',flush=True)
                except Exception as exc:
                    errors.append(dict(window=task[3]['id'],model=task[0],funding_scale=task[2],error=str(exc),error_type=type(exc).__name__))
                    print('FAILED '+json.dumps(errors[-1]),flush=True)
            atomic(RUN/'NATIVE_RESULTS.json',dict(status='RUNNING',cases=done,errors=errors,total_cases=len(tasks)))
            if errors:raise RuntimeError('Native case failed; completed cases retained, inspect service log and FAILURE.json')
            if not unrestricted and time.time()-started>4*3600:raise RuntimeError('Finite four-hour workflow budget exhausted; checkpoints retained')
        pool.shutdown();atomic(RUN/'NATIVE_RESULTS.json',dict(status='COMPLETED',cases=done,errors=errors,total_cases=len(tasks)))
        result=report(RUN,publish_original=CONFIG.get('publish_source_report',False));atomic(RUN/'REPORT_RESULT.json',result)
        publish('COMPLETE',module='修正验证与报告已完成',detail='训练未重跑，完整区间验证和报告已保存',report=result['report'])
    except BaseException as exc:
        for process in (getattr(pool,'_processes',None) or {}).values():
            if process.is_alive():process.terminate()
        pool.shutdown(wait=True,cancel_futures=True)
        atomic(RUN/'LAST_FAILURE.json',dict(error_type=type(exc).__name__,error=str(exc),time=time.time()))
        publish('STOPPED' if isinstance(exc,KeyboardInterrupt) else 'FAILED',detail=str(exc));raise

def run():
    try:
        from pipeline.common import exclusive_lock
        with exclusive_lock():main()
    except BaseException as exc:
        current=json.loads((RUN/'status.json').read_text()) if (RUN/'status.json').exists() else {}
        other_live=current.get('status')=='RUNNING' and Path('/proc/'+str(current.get('pid',0))).exists()
        if current.get('pid')!=os.getpid() and not other_live:
            atomic(RUN/'status.json',dict(status='FAILED',module='验证启动检查',module_index=5,completed_modules=4,total_modules=6,
                detail=str(exc),run_dir=str(RUN),elapsed_seconds=0,pid=os.getpid(),updated_at=time.time()))
        raise

if __name__=='__main__':run()
