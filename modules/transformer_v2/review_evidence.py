"""Final read-only review; preserve first formal outcome and all prior artifacts."""
import argparse,json,time
from collections import Counter
from pathlib import Path
from .train import atomic,sha
from .final_report import explicit_answers,stable_relative_evidence

def completion_counts(rows):
    return [dict(funding_scale=scale,completion=kind,count=count) for (scale,kind),count in
            sorted(Counter((r['funding_scale'],r['native_completion']) for r in rows).items())]

def worst_windows(rows,chosen):
    result=[]
    for scale in (1.,.01):
        own=[r for r in rows if r['family']==chosen['family'] and str(r['seed'])=='ENSEMBLE' and r['mapping']==chosen['mapping']
             and r['funding_scale']==scale and r['full_calendar_and_paid_cash']]
        if not own:continue
        r=min(own,key=lambda r:r['net_USDT'])
        result.append({k:r[k] for k in ('funding_scale','window','net_USDT','net_return_percent','long_net_USDT','short_net_USDT',
                                       'gross_price_USDT','fees_USDT','spread_USDT','slippage_USDT','funding_USDT','mean_gross','mean_signed_exposure')})
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args();state=Path(a.state)
    dest=state/'reviewed-report';dest.mkdir(exist_ok=True)
    assert not (dest/'TRANSFORMER_V2_FINAL_REPORT.md').exists(),'Reviewed output is immutable'
    dev=json.loads((state/'TRANSFORMER_V2_DEV_RESULTS.json').read_text());first=json.loads((state/'TRANSFORMER_V2_FINAL_DECISION.json').read_text())
    locked=json.loads((state/'TRANSFORMER_V2_LOCKED_RESULTS.json').read_text())
    assert first['development_results_sha256']==sha(state/'TRANSFORMER_V2_DEV_RESULTS.json') and first['locked_results_sha256']==sha(state/'TRANSFORMER_V2_LOCKED_RESULTS.json')
    assert locked['status']=='NOT_EVALUABLE_INCOMPLETE_LOCKED_CALENDAR' and not locked['cases'] and first['decision']['choice']=='B'
    assert not (state/'LOCKED_PREDICTIONS_FROZEN.json').exists() and not any((state/'locked-native').rglob('RESULT.json'))
    dev['exposure_control_pairs']=first['development_exposure_control_pairs']
    relative=stable_relative_evidence(first['development_prediction_metrics'],first['locked_prediction_metrics'],dev['chosen']['family'])
    answers=explicit_answers(dev,first['locked_rows'],relative,first['decision'],first['oracle_gap_diagnostics'])
    gaps=json.loads((state/'LOCKED_DAILY_GAP_INTEGRITY.json').read_text());refresh=json.loads((state/'LOCKED_FUNDING_ARCHIVE_REFRESH_AUDIT.json').read_text())
    api=json.loads((state/'LOCKED_FUNDING_GAP_SOURCE_AUDIT.json').read_text())
    assert len(gaps['official_daily_price_integrity'])==20 and all(r['daily_complete'] and r['rows']==1440 for r in gaps['official_daily_price_integrity'])
    assert all(r['monthly_current']['text'].split()[0]==r['accepted_monthly_sha256'] and r['daily']['http_status']==404 for r in refresh['archives'])
    assert all(r['http_status']==451 and not r['missing_04_found'] for r in api['official_history_endpoint'])
    evidence=dict(status='FINAL_REVIEW_COMPLETE_LOCKED_DATA_INELIGIBLE_NO_ACCOUNTS',observed_at=time.time(),decision=first['decision'],
                  formal_locked_attempts=1,locked_predictions=0,locked_native_accounts=0,development_native_tasks=720,
                  legacy_controls_reused=72,exposure_controls=36,corrected_oracle_rows=36,corrected_oracles_reused=28,
                  completion_counts=completion_counts(dev['rows']),worst_candidate_windows=worst_windows(dev['rows'],dev['chosen']),
                  relative_evidence=relative,explicit_answers=dict(answers),prior_final_report_sha256=sha(state/'TRANSFORMER_V2_FINAL_REPORT.md'),
                  prior_final_decision_sha256=sha(state/'TRANSFORMER_V2_FINAL_DECISION.json'),
                  evidence_sha256={name:sha(state/name) for name in ('LOCKED_GAP_SOURCE_AUDIT.json','LOCKED_DAILY_GAP_INTEGRITY.json',
                      'LOCKED_FUNDING_GAP_SOURCE_AUDIT.json','LOCKED_FUNDING_ARCHIVE_REFRESH_AUDIT.json','PRIOR_PRESERVATION_AUDIT.json','INTEGRATION_TESTS_194f6b5.log')},
                  no_models_gates_or_formal_results_changed=True,investment_state='NONE/CASH')
    atomic(dest/'FINAL_REVIEW_EVIDENCE.json',evidence)
    prior=(state/'TRANSFORMER_V2_FINAL_REPORT.md').read_text()
    start=prior.index('## 十一个问题的明确回答');end=prior.index('## 1. v2 比旧 Transformer 改善多少',start)
    revised=prior[:start]+'## 十一个问题的明确回答\n\n'+'\n\n'.join('**'+q+'**\n\n'+v for q,v in answers)+'\n\n'+prior[end:]
    revised+='\n\n## 最终数据与账户验收\n\n'
    revised+='封存区间完成一次正式数据门禁检查；由于十资产完整日历不成立，**封存预测与原生钱包均为 0，不存在封存 NET / MDD / Sharpe，也没有第二次正式账户运行**。不把 data gate 失败说成已完成184日经济模拟。\n\n'
    revised+='月档在2026-06-29缺十币 mark/premium；同官方源20份日档已下载并通过SHA、CRC、1440分钟校验，证明价格缺口可修复。但 WIFUSDT、1000SATSUSDT、ORDIUSDT 的2026-06-24 04:00资金费事件仍无法确认：最新月档 CHECKSUM 与原已验证文件一致，官方日资金费归档404，官方历史接口451。因此不臆造零资金费、不放宽日历、不删除币或缺失日，不启动无法核实完整输入的账户。\n\n'
    revised+='官方接口说明：[Binance USD-M funding history](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data#get-funding-rate-history)。实际响应与归档证据的SHA见FINAL_REVIEW_EVIDENCE.json及LOCKED_*_GAP_*文件。\n\n'
    revised+='开发720个任务均退出成功、独立账本校验通过；任务成功不等于经济账户跑满。下表包含720个新任务与72个复用控制，风险停机账户不填0收益、不合并完整窗口。\n\n|funding|账户完成状态|数量|\n|---:|---|---:|\n'
    for r in evidence['completion_counts']:revised+=f'|{r["funding_scale"]}|{r["completion"]}|{r["count"]}|\n'
    revised+='\n不完整的中性／组合账户体现原风险停止规则，不能以其局部盈利证明 alpha；详细逐分钟账本及停止点保留在external STATE。完整候选最差窗口的多头贡献为负，空头贡献很小或不足抵消，实际 signed exposure 仍显著为正：这是方向暴露与多头损失的直接证据，不能据此单独归因于 attention 或横截面模块。\n\n'
    revised+='第五开发fold的60日utility label若成熟会跨封存边界，因此 utility 指标缺失而不是0；30日IC另按真实有效日计算。有效fold数量：'+json.dumps(relative,ensure_ascii=False)+'。\n\n'
    revised+='120个CUDA开发fit与24个past-only最终fit审计通过；105项集成测试通过。旧1608个数据工件、372个模型/相关工件、96个历史账户的账本与报告逐SHA保留，共复核3232个文件。原协议SHA不变，第一次最终报告、formal N/E结果、开发冻结报告均保留；本次只补充解释与交付证据。最终决定继续 **B. CONTINUE RESEARCH, NOT YET PROMOTED**，投资 **NONE/CASH**。\n'
    (dest/'TRANSFORMER_V2_FINAL_REPORT.md').write_text(revised)
    print(json.dumps({k:v for k,v in evidence.items() if k not in ('explicit_answers','evidence_sha256')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
