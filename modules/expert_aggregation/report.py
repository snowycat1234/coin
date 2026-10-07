"""One same-window comparison, descriptive uncertainty and predeclared stopping gate."""
import csv
from pathlib import Path
import numpy as np
import polars as pl
from .common import DAY,atomic,read,sha

def build(state,repo,receipts):
    from quant.metrics import block_bootstrap_mean_ci
    protocol=read(repo/'modules/expert_aggregation/protocol.json');rows=[];navs={};summaries={};details=[]
    bars=pl.read_parquet(state/'cache/daily.parquet')
    prices=bars.filter((pl.col('close_us')>=protocol['evaluation_start_us'])&(pl.col('close_us')<=protocol['evaluation_end_us']))['close'].to_numpy()
    market_returns=prices[1:]/prices[:-1]-1
    for receipt in receipts:
        task=receipt['task'];s=receipt['saved']['summary'];key=(task['algorithm'],task['unit'],task['scenario'])
        d=pl.read_parquet(Path(receipt['directory'])/'daily_nav.parquet');nav=d['nav'].to_numpy();r=nav/np.r_[10000.,nav[:-1]]-1
        navs[key]=nav;summaries[key]=s
        beta=float(np.cov(r,market_returns,ddof=1)[0,1]/np.var(market_returns,ddof=1)) if len(r)==365 else None
        row=dict(algorithm=key[0],unit=key[1],scenario=key[2],complete=receipt['native_complete'],
            full_calendar_days=len(nav),completed_minutes=s['completed_minutes'],required_minutes=s['required_minutes'],
            terminal_cash=s['terminal_cash_realized'],net_PnL_USDT=s['net_PnL'],net_return_percent=100*s['net_PnL']/10000,
            minute_MDD=s.get('minute_max_drawdown'),all_observation_MDD=s['all_observation_max_drawdown'],
            daily_volatility=s.get('daily_metrics',{}).get('annual_volatility') if s.get('daily_metrics') else None,
            realized_mean_gross=s.get('realized_exposure',{}).get('minute_mean_gross_weight'),
            realized_mean_net=s.get('realized_exposure',{}).get('minute_mean_net_signed_weight'),BTC_beta=beta,
            fees_USDT=s['fees_USDT'],execution_cost_USDT=s['execution_cost_USDT'],funding_USDT=s['funding_USDT'],
            turnover_USDT=s['gross_fill_turnover_USDT'],liquidation_count=s['liquidation_count'],risk_reduction_signals=s['risk_reduction_signal_count'],
            audit_NAV_error=receipt['independent']['maximum_NAV_error_USDT'],audit_wallet_error=receipt['independent']['maximum_wallet_error_USDT'],
            seconds=receipt['elapsed_seconds'])
        rows.append(row)
        details.append(dict(algorithm=key[0],unit=key[1],scenario=key[2],
            long_short_attribution=s['long_short_marked_contribution'],months=s['months'],
            spread_cost_USDT=s['spread_cost_USDT'],slippage_cost_USDT=s['slippage_cost_USDT'],
            funding_original_events=s['funding_original_events'],funding_observed_events=s['funding_observed_events'],
            input_and_account_artifacts=receipt['saved']['artifacts'],independent=receipt['independent']))
    look={(r['algorithm'],r['unit'],r['scenario']):r for r in rows};comparisons=[];gate=[]
    for candidate in ('HEDGE','FIXED_SHARE'):
        passed=True;reasons=[]
        for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
            for scenario in ('BASE27','EXECUTION_X2','FUNDING_ADVERSE'):
                key=(candidate,unit,scenario);c=look[key]
                if not c['complete'] or c['audit_NAV_error']>=1e-7 or c['audit_wallet_error']>=1e-7:
                    passed=False;reasons.append(unit+' '+scenario+' incomplete or audit')
                if c['net_PnL_USDT']<=0:passed=False;reasons.append(unit+' '+scenario+' net not positive')
                for control in ('FAMILY_EW','STATIC_TRAIN_FROZEN'):
                    bkey=(control,unit,scenario);b=look[bkey]
                    pair_complete=c['complete'] and b['complete']
                    delta=c['net_PnL_USDT']-b['net_PnL_USDT'] if pair_complete else None
                    item=dict(candidate=candidate,control=control,unit=unit,scenario=scenario,net_delta_USDT=delta)
                    if not pair_complete:
                        passed=False;reasons.append(unit+' '+scenario+' incomplete comparison vs '+control)
                        item['comparison_status']='N/E_INCOMPLETE_CALENDAR_OR_TERMINAL';comparisons.append(item);continue
                    if scenario=='BASE27' and c['complete'] and b['complete']:
                        cn,bn=navs[key],navs[bkey];cr=cn/np.r_[10000.,cn[:-1]]-1;br=bn/np.r_[10000.,bn[:-1]]-1
                        lo,hi=block_bootstrap_mean_ci(cr-br,block_days=30,samples=1000,seed=20261007)
                        quarter_ends=(90,181,273,365);cq=np.diff(np.r_[10000.,cn[np.array(quarter_ends)-1]]);bq=np.diff(np.r_[10000.,bn[np.array(quarter_ends)-1]])
                        qdelta=cq-bq;positive=np.maximum(qdelta,0);share=float(positive.max()/positive.sum()) if positive.sum()>0 else None
                        item.update(paired_mean_daily_excess_ci_95=[lo,hi],quarter_candidate_PnL_USDT=cq.tolist(),quarter_control_PnL_USDT=bq.tolist(),
                            quarter_delta_USDT=qdelta.tolist(),positive_delta_quarters=int((qdelta>0).sum()),max_positive_quarter_delta_share=share)
                        if delta<100:passed=False;reasons.append(unit+' BASE incremental <100 vs '+control)
                        if (qdelta>0).sum()<3 or share is None or share>.6:passed=False;reasons.append(unit+' BASE stage consistency vs '+control)
                        item['risk_comparison_status']='N/A_ZERO_EXPOSURE_CONTROL' if b['realized_mean_gross']==0 else 'EVALUATED'
                        if b['realized_mean_gross']>0:
                            if c['all_observation_MDD']>b['all_observation_MDD']+1e-12:passed=False;reasons.append(unit+' BASE MDD vs '+control)
                            if c['realized_mean_gross']>b['realized_mean_gross']*1.1+1e-12 or abs(c['BTC_beta'])>abs(b['BTC_beta'])*1.1+1e-12:
                                passed=False;reasons.append(unit+' BASE higher exposure/beta vs '+control)
                    elif delta<=0:passed=False;reasons.append(unit+' '+scenario+' incremental not positive vs '+control)
                    comparisons.append(item)
            for control in ('SMA200_SIGNED','CASH'):
                c=look[(candidate,unit,'BASE27')];b=look[(control,unit,'BASE27')]
                delta=c['net_PnL_USDT']-b['net_PnL_USDT'] if c['complete'] and b['complete'] else None
                comparisons.append(dict(candidate=candidate,control=control,unit=unit,scenario='BASE27',net_delta_USDT=delta,
                    role='STRONG_SINGLE_AND_CASH_REFERENCE_NOT_NEW_PRESSURE_GRID'))
                if delta is None:passed=False;reasons.append(unit+' BASE incomplete '+control+' comparison')
                elif control=='SMA200_SIGNED' and delta<100:passed=False;reasons.append(unit+' BASE incremental <100 vs strong SMA200_SIGNED')
        gate.append(dict(candidate=candidate,passes_registered_gate=passed,failed_conditions=sorted(set(reasons))))
    complete=all(r['complete'] for r in rows)
    classification=('INSUFFICIENT_EVIDENCE' if not complete else 'DYNAMIC_CAPTURE_PRELIMINARY' if any(g['passes_registered_gate'] for g in gate)
        else 'STATIC_EDGE_ONLY' if all(any(look[(c,u,'BASE27')]['net_PnL_USDT']>0 for c in ('FAMILY_EW','STATIC_TRAIN_FROZEN','SMA200_SIGNED')) for u in ('RAW_AS_FRACTION','RAW_AS_PERCENT'))
        else 'NO_NET_EDGE_IN_TESTED_CLASS')
    # Original projection proved feasible for every path; no evidence triggers a new solver/pool.
    result=dict(status='COMPLETE_FINITE_HISTORICAL_EXPERT_AGGREGATION',classification=classification,
        protocol=protocol,run_binding=read(state/'RUN_BINDING.json'),input_binding=read(state/'cache/INPUT_BINDING.json'),
        path_index_sha256=sha(state/'PATHS.json'),accounts=rows,account_details=details,comparisons=comparisons,gates=gate,
        weight_and_intention_diagnostics=read(state/'PATHS.json')['diagnostics'],
        native_account_count=len(rows),gpu_training_count=0,
        round_2=dict(status='NOT_TRIGGERED',reason='Original projection feasible with independently verified past covariance. No justified same-path projection ablation; no automatic expert/ML expansion.'),
        conclusion_scope='Conditional seen historical BTC proxy; units/risk tiers/publication unconfirmed, no native execution or fresh OOS claim',
        investment_status='NONE_CASH_NO_DEPLOYMENT',oracle_capture_ratio=None,
        oracle_capture_ratio_reason='No compatible 2023 REGIME_EXPOST actual wallet; original 730-day oracle is historical continuity only',
        old_reference_report='reports/FROZEN_EXPERT_MIXTURE_REVIEW_20261006_V1.json',
        old_reference_scope='730-day historical comparisons, different initial window/core; not substituted for 2023 independent 10k controls',
        accounts_directory=str(state/'accounts'))
    out=state/'delivery';out.mkdir(exist_ok=True);atomic(out/'RESULTS.json',result)
    with (out/'RESULTS.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    lines=['# BTC 因果专家组合首轮结果','',f'结论：**{classification}**。共 {len(rows)} 个完整设计账户；GPU 训练 0 次。',
        '', '2022 年的 364 条已成熟反馈只用于冻结尺度、静态选择和在线组合初始状态；2023 年从独立 10000 USDT 开始，保留全部 365 天。专家反馈来自旧连续净账本，组合混合目标仓位后进入同一个逐仓钱包。',
        '', '2022—2023 和已有 v3/carry 数据均为研究者已见历史，结果不构成 fresh OOS。资金费两种原单位解释、事件即时发布、MMR=.005/MMD=0 为条件假设。行情/成交为已接受 Binance USDM 代理，费用为用户 Bybit 当前费率情景。',
        '', '|组合|资金费解释|情景|净收益 USDT|总收益|全观察点回撤|平均 gross|BTC beta|',
        '|---|---|---|---:|---:|---:|---:|---:|']
    for r in rows:
        lines.append(f"|{r['algorithm']}|{r['unit']}|{r['scenario']}|{r['net_PnL_USDT']:.2f}|{r['net_return_percent']:.2f}%|{100*r['all_observation_MDD']:.2f}%|{r['realized_mean_gross'] if r['realized_mean_gross'] is not None else 'N/E'}|{r['BTC_beta'] if r['BTC_beta'] is not None else 'N/E'}|")
    lines+=['','同一天结束的收益延后 1µs 才可见，所以每天决策只消费更早已结束的收益。所有真实损失、费用、强平和空仓日保持原值；效用裁剪仅影响组合权重。训练选出的静态策略为有限 one-hot 域最佳，未声称连续混合全局最优。',
        '', '执行成本翻倍情景每边 11bp 手续费、8bp 半价差、8bp 滑点，往返 54bp；不利资金费按实际持仓将付款×2、收款×0.5。压力复用基础权重路径。原始 funding 列保持原值，审计先独立验证有效率再用显式转换视图对完整钱包核对。',
        '', '动态组合必须同时超过 family-EW 与训练冻结静态，在两种资金费解释下净收益为正，基础增量≥100 USDT，至少三季度增量为正，最大单季度贡献≤60%，回撤不变差且平均 gross/绝对 BTC beta 不超过静态的1.1倍；两个压力场景仍须净收益及增量为正。门槛不由结果调整。']
    for g in gate:lines+=['',g['candidate']+'：'+('通过预登记门槛' if g['passes_registered_gate'] else '未通过；'+ '；'.join(g['failed_conditions']))]
    lines+=['','块分析为30天循环块、1000次、固定seed的配对日收益区间；仅描述时间依赖下的不确定性，不修正研究选择偏差。两种资金费解释和四季度不是独立市场样本。',
        '', '旧 EQUAL_EXPERTS、STATIC_DIRECTION3 和60日 Oracle 保留原730日证据，不能把旧某一年截取后充作新10k对照。没有同窗口实际 REGIME_EXPOST 钱包，OCR 为 N/A。EWMA仅作权重诊断，不增加第三个动态回放。',
        '', '第二轮未触发：原投影及过去协方差均通过；没有证据支持新增投影、专家池、context 或 ML。若动态已通过门槛，应冻结并寻找真正未见数据；若未通过，应停止本配方追加搜索。无交易部署。',
        '', f'服务器证据：`{state}`。机器结果及全部逐分钟账本可按 CLI 恢复；完成账户按 SHA 校验后直接复用。']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n')
    try:
        import matplotlib;matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axs=plt.subplots(2,1,figsize=(11,7),sharex=True)
        for ax,u in zip(axs,('RAW_AS_FRACTION','RAW_AS_PERCENT')):
            for a in ('HEDGE','FIXED_SHARE','FAMILY_EW','STATIC_TRAIN_FROZEN','SMA200_SIGNED','CASH'):
                v=navs[(a,u,'BASE27')];ax.plot(np.arange(len(v)),v,label=a+(' (N/E prefix)' if len(v)!=365 else ''))
            ax.set_ylabel('USDT NAV');ax.set_title(u+' | seen historical 2023 | BASE27');ax.grid(alpha=.2)
        axs[0].legend(ncol=3,fontsize=8);axs[-1].set_xlabel('Calendar day (all 365 days)');fig.tight_layout();fig.savefig(out/'NAV.png',dpi=150);plt.close(fig)
    except ImportError:pass
    atomic(out/'DELIVERY_INDEX.json',dict(files=[dict(name=p.name,sha256=sha(p),bytes=p.stat().st_size) for p in sorted(out.iterdir()) if p.is_file() and p.name!='DELIVERY_INDEX.json']))
    return result
