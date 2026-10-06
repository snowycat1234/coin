"""Read-only final evidence and registered decision; never chooses a locked winner."""
import argparse,csv,json
from pathlib import Path
import numpy as np
from .train import atomic,sha
from .report import compact_case

STATIC=('BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3')
CHOICES=('PROMOTE FOR FURTHER PAPER-TRADING','CONTINUE RESEARCH, NOT YET PROMOTED','STOP THIS TRANSFORMER DIRECTION')

def median(values):
    values=[v for v in values if v is not None and np.isfinite(v)]
    return float(np.median(values)) if values else None

def risk_audit(case):
    import polars as pl
    entry=case['artifacts']['minute_nav_inventory.parquet'];assert sha(entry['path'])==entry['sha256']
    symbols=case['summary']['symbols'];cols=['gross_weight']+[s+'_signed_weight' for s in symbols]
    minute=pl.read_parquet(entry['path'],columns=cols)
    breach=(minute['gross_weight'].to_numpy()>.6+1e-9)
    for symbol in symbols:breach|=abs(minute[symbol+'_signed_weight'].to_numpy())>.3+1e-9
    edges=np.diff(np.r_[False,breach,False].astype(int));starts=np.flatnonzero(edges==1);ends=np.flatnonzero(edges==-1);lengths=ends-starts
    # The unchanged native account's risk-reduction contract permits five attempts.
    return dict(total_cap_breach_minutes=int(breach.sum()),maximum_consecutive_cap_breach_minutes=int(lengths.max()) if len(lengths) else 0,
                persistent_cap_breach_minutes=int(lengths[lengths>5].sum()),scope='ACTUAL_MINUTE_MARK_SNAPSHOTS; FIVE_ATTEMPT_NATIVE_REDUCTION_BUDGET; NOT_INTRAMINUTE_RISK_CERTIFICATION')

def stable_relative_evidence(dev_metrics,locked_metrics,family):
    evidence=[]
    for scale in (1.,.01):
        dev=[r for r in dev_metrics if r['family']==family and str(r['seed'])=='ENSEMBLE' and r['funding_scale']==scale]
        locked=[r for r in locked_metrics if r['family']==family and str(r['seed'])=='ENSEMBLE' and r['funding_scale']==scale]
        ic=bool(len(dev)==5 and all(r.get('rank_IC_median') is not None for r in dev) and sum(r['rank_IC_median']>0 for r in dev)>=4
                and len(locked)==1 and (locked[0].get('rank_IC_median') or 0)>0)
        utility=bool(len(dev)==5 and all(r.get('utility_rank') is not None for r in dev) and sum(r['utility_rank']>0 for r in dev)>=4
                     and len(locked)==1 and (locked[0].get('utility_rank') or 0)>0)
        evidence.append(dict(funding_scale=scale,stable_IC=ic,stable_relative_utility=utility,
            development_median_IC=median([r.get('rank_IC_median') for r in dev]),locked_IC=locked[0].get('rank_IC_median') if locked else None,
            development_median_utility_rank=median([r.get('utility_rank') for r in dev]),locked_utility_rank=locked[0].get('utility_rank') if locked else None))
    return evidence

def decision(dev,locked_rows,locked_cases,relative):
    chosen=dev['chosen'];index={(r['family'],str(r['seed']),r['mapping'],r['funding_scale']):r for r in locked_rows}
    chosen_rows=[index.get((chosen['family'],'ENSEMBLE',chosen['mapping'],scale)) for scale in (1.,.01)]
    if not all(r and r['full_calendar_and_paid_cash'] for r in chosen_rows):
        return dict(choice='B',decision=CHOICES[1],promotion=False,reason='Locked candidate lacks a complete paid-close calendar; no economic promotion claim',gates={},relative_evidence=relative)
    required=[(b,'FROZEN_RULE','DIRECTIONAL',scale) for scale in (1.,.01) for b in (*STATIC,*('EXPOSURE_MATCHED_'+s for s in STATIC))]
    if any(key not in index for key in required):
        return dict(choice='B',decision=CHOICES[1],promotion=False,reason='Required locked controls are missing; no promotion',gates={},relative_evidence=relative)
    controls=[index[b,'FROZEN_RULE','DIRECTIONAL',scale] for scale in (1.,.01) for b in STATIC]
    full_controls=all(r['full_calendar_and_paid_cash'] for r in controls)
    competitiveness=bool(full_controls and all(r['net_USDT']>=max(index[b,'FROZEN_RULE','DIRECTIONAL',r['funding_scale']]['net_USDT'] for b in STATIC) for r in chosen_rows))
    matched=[]
    for r in chosen_rows:
        baseline=[index['EXPOSURE_MATCHED_'+b,'FROZEN_RULE','DIRECTIONAL',r['funding_scale']] for b in STATIC]
        complete=all(b['full_calendar_and_paid_cash'] for b in baseline)
        # A same requested budget is not a certificate of equal realized exposure.
        equal=complete and all(abs(b['mean_gross']-r['mean_gross'])<=1e-6 for b in baseline)
        beats=complete and r['net_USDT']>max(b['net_USDT'] for b in baseline)
        matched.append(dict(funding_scale=r['funding_scale'],realized_gross_equality_certified=bool(equal),beats_requested_gross_matched_baselines=bool(beats),
                            candidate_mean_gross=r['mean_gross'],baseline_mean_gross={b['family']:b['mean_gross'] for b in baseline},
                            delta_to_strongest_requested_gross_matched_USDT=r['net_USDT']-max(b['net_USDT'] for b in baseline) if complete else None))
    candidate_cases=[c for c in locked_cases if c['task']['family']==chosen['family'] and c['task']['seed']=='ENSEMBLE' and c['task']['mapping']==chosen['mapping']]
    risk=all(c['summary']['completion']=='COMPLETE_CONDITIONAL_ACCOUNT' and c['summary']['terminal_cash_realized']
             and c['summary'].get('minute_max_drawdown',1)<=.20
             and (c['summary'].get('maximum_observed_first_risk_reduction_latency_us') or 0)<=5*60_000_000
             and c.get('v2_risk_audit',{}).get('persistent_cap_breach_minutes',1)==0 for c in candidate_cases)
    # Any persistent or unresolved reduction fails; bounded filled drift is separately visible.
    for c in candidate_cases:
        if 'HALT' in c['summary']['completion'] or 'UNEXECUTABLE' in c['summary']['completion']:risk=False
    neutral=chosen['mapping']!='NEUTRAL' or all(r['stable_IC'] for r in relative)
    gates=dict(development_walk_forward_and_ensemble=dev['development_gate_pass'],locked_both_scales_above_cash=all(r['net_USDT']>0 for r in chosen_rows),
               locked_risk_and_MDD=bool(risk),strongest_static_competitiveness=competitiveness,
               positive_gross_and_net=all(r['gross_price_USDT']>0 and r['net_USDT']>0 for r in chosen_rows),
               equal_realized_gross_alpha=all(r['realized_gross_equality_certified'] and r['beats_requested_gross_matched_baselines'] for r in matched),
               neutral_relative_evidence=neutral)
    if all(gates.values()):choice=0;reason='All registered development, locked, risk, baseline, cost and exposure gates passed'
    else:
        no_relative=not all(r['stable_IC'] or r['stable_relative_utility'] for r in relative)
        negative=all(r['net_USDT']<=0 for r in chosen_rows)
        lower=all(r['mean_gross']<index['BASE_HOLD','FROZEN_RULE','DIRECTIONAL',r['funding_scale']]['mean_gross'] for r in chosen_rows)
        no_matched_alpha=all(not r['beats_requested_gross_matched_baselines'] for r in matched)
        stop=negative and no_relative and lower and no_matched_alpha
        choice=2 if stop else 1
        reason='STOP PRICE/FUNDING/PREMIUM-ONLY DIRECTIONAL TRANSFORMER RESEARCH' if stop else 'At least one registered gate failed; locked comparisons do not replace the frozen development candidate'
    return dict(choice='ABC'[choice],decision=CHOICES[choice],promotion=choice==0,reason=reason,gates=gates,exposure_evidence=matched,relative_evidence=relative)

def architecture_diagnostics(dev):
    rows=dev['rows'];index={(r['family'],str(r['seed']),r['mapping'],r['funding_scale'],r['window']):r for r in rows}
    comparisons=[('CROSS_ASSET_UTILITY','TRANSFORMER_SHARED','cross_asset_plus_readouts'),('CROSS_ASSET_MULTITASK','CROSS_ASSET_UTILITY','multitask'),
                 ('PATCH_CROSS_ASSET_MULTITASK','CROSS_ASSET_MULTITASK','eight_day_patching')];out=[]
    for family,base,label in comparisons:
        for scale in (1.,.01):
            for mapping in ('DIRECTIONAL','NEUTRAL','COMBINED'):
                own=[r for r in rows if r['family']==family and str(r['seed'])=='ENSEMBLE' and r['mapping']==mapping and r['funding_scale']==scale]
                delta=[];exposure=[]
                for row in own:
                    other=index[base,'ENSEMBLE',mapping,scale,row['window']]
                    if row['net_return_percent'] is not None and other['net_return_percent'] is not None:delta.append(row['net_return_percent']-other['net_return_percent'])
                    if row['mean_gross'] is not None and other['mean_gross'] is not None:exposure.append(row['mean_gross']-other['mean_gross'])
                out.append(dict(change=label,family=family,reference=base,mapping=mapping,funding_scale=scale,paired_median_delta_pct=median(delta),paired_median_gross_exposure_delta=median(exposure),common_windows=len(delta)))
    return out

def oracle_gaps(rows,candidate,mapping):
    out=[]
    for row in rows:
        if not row['noncausal']:continue
        pool=[r for r in rows if r['window']==row['window'] and r['funding_scale']==row['funding_scale']]
        own=next((r for r in pool if r['family']==candidate and str(r['seed'])=='ENSEMBLE' and r['mapping']==mapping),None)
        baseline=next((r for r in pool if r['family']=='BASE_SMA200_SIGNED'),None)
        if row['net_USDT'] is None or own is None or own['net_USDT'] is None or baseline is None or baseline['net_USDT'] is None:continue
        gap=row['net_USDT']-baseline['net_USDT']
        out.append(dict(window=row['window'],funding_scale=row['funding_scale'],oracle=row['family'],oracle_net_USDT=row['net_USDT'],
                        oracle_net_return_percent=row['net_return_percent'],gap_over_full_calendar_SMA_USDT=gap,
                        diagnostic_capture_ratio=(own['net_USDT']-baseline['net_USDT'])/gap if gap>0 else None,
                        qualification='HORIZON_SUPPORTED_ORACLE_WITH_TERMINAL_CASH_VS_FULL_CALENDAR_CAUSAL_ACCOUNTS; NOT_TIGHT_CEILING_OR_PROMOTION_METRIC'))
    return out

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args();state=Path(a.state);repo=Path(__file__).resolve().parents[2]
    protocol_path=repo/'reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json';dev=json.loads((state/'TRANSFORMER_V2_DEV_RESULTS.json').read_text())
    freeze=json.loads((state/'LOCKED_CANDIDATE_FREEZE.json').read_text());assert sha(state/'TRANSFORMER_V2_DEV_RESULTS.json')==freeze['development_results_sha256'] and dev['chosen']==freeze['chosen']
    locked=json.loads((state/'TRANSFORMER_V2_LOCKED_RESULTS.json').read_text());assert locked['protocol_sha256']==sha(protocol_path)
    rows=[]
    for case in locked['cases']:
        assert sha(case['summary_path'])==case['summary_sha256'] and sha(case['independent_audit_path'])==case['independent_audit_sha256']
        row=compact_case(case);rows.append(row);assert row['contribution_sum_error']<1e-6
        if case['task']['family']==dev['chosen']['family'] and str(case['task']['seed'])=='ENSEMBLE' and case['task']['mapping']==dev['chosen']['mapping']:
            case['v2_risk_audit']=risk_audit(case)
    metrics=json.loads((state/'PREDICTION_METRICS.json').read_text())['rows']
    locked_metrics=json.loads((state/'LOCKED_PREDICTION_METRICS.json').read_text())['rows'] if (state/'LOCKED_PREDICTION_METRICS.json').exists() else []
    relative=stable_relative_evidence(metrics,locked_metrics,dev['chosen']['family']);verdict=decision(dev,rows,locked['cases'],relative)
    if locked['status']!='COMPLETE_ONE_FORMAL_LOCKED_EXPERIMENT':verdict.update(choice='B',decision=CHOICES[1],promotion=False,reason='Full locked experiment is NOT_EVALUABLE or has preserved engineering failures; no post-outcome rerun')
    diagnostic=architecture_diagnostics(dev);gaps=oracle_gaps(dev['rows'],dev['chosen']['family'],dev['chosen']['mapping'])+oracle_gaps(rows,dev['chosen']['family'],dev['chosen']['mapping'])
    evidence=dict(protocol_sha256=sha(protocol_path),development_results_sha256=sha(state/'TRANSFORMER_V2_DEV_RESULTS.json'),locked_results_sha256=sha(state/'TRANSFORMER_V2_LOCKED_RESULTS.json'),
                  chosen=dev['chosen'],decision=verdict,architecture_comparisons=diagnostic,oracle_gap_diagnostics=gaps,locked_rows=rows,
                  development_prediction_metrics=metrics,locked_prediction_metrics=locked_metrics,
                  candidate_risk_audits=[dict(funding_scale=c['task']['funding_scale'],**c['v2_risk_audit']) for c in locked['cases'] if 'v2_risk_audit' in c],
                  investment_state='NONE/CASH',deployment_authorized=False)
    atomic(state/'TRANSFORMER_V2_FINAL_DECISION.json',evidence)
    if rows:
        with (state/'TRANSFORMER_V2_LOCKED_SUMMARY.csv').open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    def fmt(v):return 'NOT_EVALUABLE' if v is None else f'{v:.4f}'
    lines=['# Transformer v2 最终研究报告','',f'最终决定：**{verdict["choice"]}. {verdict["decision"]}**。',verdict['reason'],
           '投资状态继续为 NONE/CASH。本报告为研究证据，不授权实盘。','## 证据边界',
           '开发集是已见历史的五折 walk-forward、六个独立满资金窗口；每个账户初始 10k USDT，收益不能相加冒充连续 APR。封存测试是 2026-03-01 至 2026-08-31 的一次正式连续 184 日实验。',
           '固定候选来自开发集排名：'+json.dumps(dev['chosen'],ensure_ascii=False),
           '封存状态：'+locked['status']+'。没有按封存 PnL 换候选、挑 seed、改 K、改 gate 或重跑赢家。',
           '全部账户复用原分钟交易内核、费用、逐仓 1x、abs 单币 30% / gross 60% 边界及独立账本核验。价格源 Binance USD-M 与既有费用假设仍是跨场所代理；资金费原始单位未确证，1.0/0.01 两种解释并列保留。',
           '## 1. v2 比旧 Transformer 改善多少',
           '|模型/组合|funding|开发集窗口收益中位数 %|对旧冻结 Transformer 配对中位差 pct|胜 SMA 窗口|最差窗口 %|',
           '|---|---:|---:|---:|---:|---:|']
    for summary in dev['summaries']:
        for s in summary['scenarios']:
            if not s['complete']:continue
            lines.append(f'|{summary["family"]}/{summary["mapping"]}|{s["funding_scale"]}|{fmt(s["median_net_return_percent"])}|{fmt(s["median_paired_delta_old_transformer_pct"])}|{s["wins_vs_SMA"]}/6|{fmt(s["worst_window_return_percent"])}|')
    lines+=['## 2. 改善来源与 exposure',
            '下表是同窗口配对差。cross-asset utility 与本轮重训旧架构的差同时含 cross-asset attention 和 readout 变化，不能单独归因给 attention。multitask 与 patch 比较使用固定 seed、协议和组合。',
            '|变化|组合|funding|配对中位收益差 pct|配对中位实际 gross 差|','|---|---|---:|---:|---:|']
    for r in diagnostic:lines.append(f'|{r["change"]}|{r["mapping"]}|{r["funding_scale"]}|{fmt(r["paired_median_delta_pct"])}|{fmt(r["paired_median_gross_exposure_delta"])}|')
    lines+=['三 seed 全部列在 DEV_RESULTS / LOCKED_SUMMARY；ensemble 是预测的固定平均。开发集每个模型的 seed dispersion、ensemble 标准差和最差窗口稳定性检查在 DEV_RESULTS。CLS / attention / last 的开发集独立 readout 账户保留，未选优。',
            '封存期 equal-requested-gross 对照：'+json.dumps(verdict.get('exposure_evidence',[]),ensure_ascii=False),
            '同一 requested gross 不保证同一 realized gross，成交容量和风险减仓会造成差别。未证明实际 exposure 相等时，不能宣称排除了 exposure 解释，也不能通过对应 gate。',
            '## 3–4. 方向与横截面 alpha',
            '下表分别列方向、中性、组合的封存 ensemble；中性组合固定 top2 / bottom2，每腿 0.15，净 dollar target=0，不宣称 beta 中性。毛价格 PnL、费用、执行、资金费及多空贡献同时呈现。',
            '|模型/组合|funding|NET USDT|毛价格 USDT|fee|spread|slippage|funding|long NET|short NET|MDD|Sharpe|实际 gross|',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if str(r['seed'])!='ENSEMBLE':continue
        values=[r[k] for k in ('funding_scale','net_USDT','gross_price_USDT','fees_USDT','spread_USDT','slippage_USDT','funding_USDT','long_net_USDT','short_net_USDT','MDD','Sharpe','mean_gross')]
        lines.append('|'+r['family']+'/'+r['mapping']+'|'+'|'.join(fmt(v) for v in values)+'|')
    lines+=['跨阶段 relative 证据：'+json.dumps(relative,ensure_ascii=False),
            '稳定诊断使用五个开发 fold 至少四个正 IC（或正 utility rank）及封存期同向，两个 funding interpretations 均保留；它不是新增模型选择规则。所有预测指标及有效 IC 日数列在 FINAL_DECISION.json。',
            '## 5–6. Oracle ceiling 与 gap 捕获',
            '三个 oracle 永远 NONCAUSAL / NONDEPLOYABLE，使用同本金、成本、资金费、风险和成交。专家 oracle 的 60 日 utility 是日频 quantity proxy；方向和排序 oracle 为未来 30 日价格信息。',
            '终端未来 horizon 不足和中间缺口明确现金，因此以下是有限支持的策略空间诊断，无法证明严格完整日历最优 ceiling。gap 分母只有正值才报告比率；基线和模型为全日历账户，支持差异使比率只能作诊断，不是可推广捕获率。',
            '|窗口|funding|oracle|NET %|相对 SMA gap USDT|诊断捕获率|','|---|---:|---|---:|---:|---:|']
    for r in gaps:lines.append(f'|{r["window"]}|{r["funding_scale"]}|{r["oracle"]}|{fmt(r["oracle_net_return_percent"])}|{fmt(r["gap_over_full_calendar_SMA_USDT"])}|{fmt(r["diagnostic_capture_ratio"])}|')
    lines+=['## 7. 哪些市场阶段赚钱或亏钱','冻结候选开发阶段：','|独立窗口|funding|NET %|long NET|short NET|实际 signed exposure|','|---|---:|---:|---:|---:|---:|']
    for r in dev['rows']:
        if r['family']==dev['chosen']['family'] and str(r['seed'])=='ENSEMBLE' and r['mapping']==dev['chosen']['mapping']:
            lines.append(f'|{r["window"]}|{r["funding_scale"]}|{fmt(r["net_return_percent"])}|{fmt(r["long_net_USDT"])}|{fmt(r["short_net_USDT"])}|{fmt(r["mean_signed_exposure"])}|')
    lines+=['封存期各月是同一连续账户的可核对分解，不是每月重置：','|月份|funding|NET USDT|毛价格|fee|执行|funding|','|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['family']==dev['chosen']['family'] and str(r['seed'])=='ENSEMBLE' and r['mapping']==dev['chosen']['mapping']:
            for m in r['monthly_PnL']:lines.append('|'+m['month']+'|'+str(r['funding_scale'])+'|'+'|'.join(fmt(v) for v in (m['net_PnL'],m['gross_PnL'],m['fees'],m['spread_cost']+m['slippage_cost'],m['funding_USDT']))+'|')
    lines+=['## 8–9. 多空贡献和成本','多空贡献由原始成交、持仓和资金费逐笔归属，long NET + short NET 与账户 NET 的误差小于 1e-6 USDT。fee + spread + slippage 占正毛价格 PnL 的比率保留在逐账户 summary；毛价格非正时该比率为 NOT_EVALUABLE，不能拿负分母制造“低成本”。',
            '|冻结候选 funding|NET %|毛价格 USDT|交易成本占正毛价格|turnover USDT|long NET|short NET|','|---:|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['family']==dev['chosen']['family'] and str(r['seed'])=='ENSEMBLE' and r['mapping']==dev['chosen']['mapping']:
            lines.append('|'+str(r['funding_scale'])+'|'+'|'.join(fmt(r[k]) for k in ('net_return_percent','gross_price_USDT','cost_share_of_positive_gross','turnover_USDT','long_net_USDT','short_net_USDT'))+'|')
    lines+=['## 10. 封存 2026-03~08 与 causal 对照','|策略|funding|NET %|MDD|实际 gross|完整日历且付费清仓|','|---|---:|---:|---:|---:|---|']
    for r in rows:
        if str(r['seed'])=='ENSEMBLE' or r['family'].startswith('BASE_') or r['family'] in ('OLD_FROZEN_TRANSFORMER_SHARED','PER_ASSET_XGB'):
            lines.append(f'|{r["family"]}/{r["mapping"]}|{r["funding_scale"]}|{fmt(r["net_return_percent"])}|{fmt(r["MDD"])}|{fmt(r["mean_gross"])}|{r["full_calendar_and_paid_cash"]}|')
    lines+=['## 11. 最终决定与 gate',json.dumps(verdict,ensure_ascii=False,indent=2),
            '旧冻结 Transformer / XGB 是最后开发 fold 的权重与 scaler，未伪装成最终全量重训；本轮新旧架构均按相同 past-only median-epoch 规则重训。即使其他封存组合较好，也不会事后替换开发候选或晋级。',
            '## 复现与完整工件',
            'Git 分支 research/transformer-v2 保留 fit 前协议、源代码、哈希和精简报告。大型行情、模型、检查点和原始账本保存在独立 external STATE。协议 SHA：'+sha(protocol_path),
            'TRANSFORMER_V2_FINAL_DECISION.json 保留全部 gate、配对架构诊断、预测指标、oracle gap 和账户表；LOCKED_RESULTS 原始分钟账户 summary / 独立账本审计引用不可变。']
    (state/'TRANSFORMER_V2_FINAL_REPORT.md').write_text('\n\n'.join(lines)+'\n')
    print(json.dumps(verdict,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
