"""All eleven scientific answers; every funding bridge, no best-bridge headline."""
import argparse,gzip,json
from collections import Counter
from pathlib import Path
import numpy as np
from modules.transformer_v2.train import atomic,sha
from .development_report import compact,regret_comparison
from .locked_bridge_data import require_freeze
from .funding_bridge import SCENARIOS
from .train_policy import FAMILIES

BASELINES=('BASE_HOLD','BASE_SMA200_SIGNED','BASE_STATIC_DIRECTION3')
DECISIONS=('A. PROMOTE FOR PAPER TRADING','B. CONTINUE RESEARCH','C. STOP THIS TRANSFORMER/PUBLIC-DATA DIRECTION')

def ranges(values):
    values=[float(v) for v in values if v is not None]
    return dict(min=min(values),median=float(np.median(values)),max=max(values),observations=len(values)) if values else dict(min=None,median=None,max=None,observations=0)

def research_signal(dev,replay):
    """Pre-locked registered descriptive signal/regret criteria, not a significance test."""
    rank=[];regret=[]
    families=('CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK',*FAMILIES)
    for family in families:
        counts=[]
        for scale in (1.,.01):
            rows=[r for r in dev['prediction_metrics'] if r['family']==family and str(r['seed'])=='ENSEMBLE' and r['funding_scale']==scale]
            counts.append(sum(r['rank_IC_mean'] is not None and r['rank_IC_mean']>0 for r in rows))
        rank.append(dict(family=family,positive_folds_by_units=counts,pass_registered_rule=min(counts)>=4))
    for family in FAMILIES:
        counts=[]
        for scale in (1.,.01):
            rows=[r for r in dev['regret_comparison'] if r['family']==family and str(r['seed'])=='ENSEMBLE' and r['funding_scale']==scale and r['metric']=='mean_soft_policy_oracle_regret']
            counts.append(sum(r['new_minus_old'] is not None and r['new_minus_old']<0 for r in rows))
        regret.append(dict(family=family,improved_folds_by_units=counts,pass_registered_rule=min(counts)>=3))
    return dict(actionable_descriptive_signal=replay['stable_neutral_gate_pass'] or any(r['pass_registered_rule'] for r in rank+regret),
        frozen_v2_neutral_gate=replay['stable_neutral_gate_pass'],rank_evidence=rank,proxy_regret_evidence=regret,
        not_statistical_significance=True)

def bridge_votes(rows,chosen):
    index={(r['scenario'],r['funding_scale'],r['family'],r['mapping'],r['profile']):r for r in rows};votes=[]
    for scenario in SCENARIOS:
        details=[]
        for scale in (1.,.01):
            r=index[scenario,scale,chosen['family'],chosen['mapping'],chosen['profile']]
            controls=[index[scenario,scale,b,'DIRECTIONAL',chosen['profile']] for b in BASELINES]
            complete=r['full_calendar_and_paid_cash'] and all(c['full_calendar_and_paid_cash'] for c in controls)
            strongest=max(c['net_return_percent'] for c in controls) if complete else None
            delta=r['net_return_percent']-strongest if complete else None
            vote='PASS' if complete and r['net_return_percent']>0 and delta>0 else 'FAIL' if complete else 'NOT_EVALUABLE'
            details.append(dict(funding_scale=scale,economic_vote=vote,net_return_percent=r['net_return_percent'],paired_strongest_static_delta_pct=delta,
                liquidation_count=r['liquidation_count'],liquidation_loss_USDT=r['liquidation_loss_USDT']))
        votes.append(dict(scenario=scenario,units=details,economic_vote='PASS' if all(d['economic_vote']=='PASS' for d in details) else 'NOT_EVALUABLE' if any(d['economic_vote']=='NOT_EVALUABLE' for d in details) else 'FAIL'))
    return votes

def bridge_ranges(rows):
    keys=sorted({(r['family'],r['mapping'],r['profile'],r['funding_scale']) for r in rows});result=[]
    for family,mapping,profile,scale in keys:
        own=[r for r in rows if (r['family'],r['mapping'],r['profile'],r['funding_scale'])==(family,mapping,profile,scale)]
        if len(own)!=5 or {r['scenario'] for r in own}!=set(SCENARIOS):raise ValueError('All five preregistered bridges required for every comparison')
        complete=all(r['full_calendar_and_paid_cash'] for r in own)
        stats={k:ranges([r[k] for r in own]) for k in ('net_USDT','net_return_percent','funding_USDT','gross_price_USDT','fees_USDT','execution_cost_USDT',
            'long_net_USDT','short_net_USDT','liquidation_loss_USDT','liquidation_count','MDD','realized_vol','Sharpe','mean_gross')}
        result.append(dict(family=family,mapping=mapping,profile=profile,funding_scale=scale,complete_all_five=complete,statistics=stats,
            missing_funding_total_economic_range_USDT=stats['net_USDT']['max']-stats['net_USDT']['min'] if complete else None,
            missing_funding_total_economic_range_pct=stats['net_return_percent']['max']-stats['net_return_percent']['min'] if complete else None,
            range_scope='FULL_NATIVE_NET_DIFFERENCE_INCLUDES_SAME_FROZEN_MODEL_CAUSAL_FUNDING_INPUT_FEEDBACK; NOT_ONLY_DIRECT_CASHFLOW',
            incomplete_scenarios=[r['scenario'] for r in own if not r['full_calendar_and_paid_cash']]))
    return result

def direct_estimated_funding(case):
    artifact=case['artifacts']['funding.json'];p=Path(artifact['path'])
    if sha(p)!=artifact['sha256']:raise ValueError('Funding journal changed')
    raw=gzip.decompress(p.read_bytes()) if p.name.endswith('.gz') else p.read_bytes()
    rows=json.loads(raw)
    estimates=[r for r in rows if r.get('observed_settlement_event') is False]
    return dict(task_id=case['task']['id'],scenario=case['task']['scenario'],funding_scale=case['task']['funding_scale'],
        family=case['task']['family'],profile=case['task']['profile'],mapping=case['task']['mapping'],
        synthetic_event_rows=len(estimates),signed_estimated_funding_USDT=sum(r['signed_funding_USDT'] for r in estimates),
        rows=[{k:r.get(k) for k in ('symbol','event_us','quantity','raw_rate','signed_funding_USDT','funding_source_role','funding_bridge_scenario','exact_Binance_settlement','observed_settlement_event')} for r in estimates],
        event_scope='ONLY_THREE_PREREGISTERED_UNKNOWN_SETTLEMENTS; ZERO_QUANTITY_HAS_ZERO_CASH; NO_EXACT_EVENT_CERTIFICATION')

def choose_decision(dev,signal,votes,certified):
    if dev['development_gate_pass'] and certified and all(r['economic_vote']=='PASS' for r in votes):return DECISIONS[0]
    return DECISIONS[1] if signal['actionable_descriptive_signal'] else DECISIONS[2]

def final_analysis(state):
    state=Path(state);release_path,release=require_freeze(state)
    source=state/'IMPUTED_LOCKED_SENSITIVITY.json';data=json.loads(source.read_text())
    if data['status']!='COMPLETE_IMPUTED_LOCKED_SENSITIVITY' or len(data['cases'])!=400 or data['scenarios']!=list(SCENARIOS):raise ValueError('Every locked bridge must finish before final report')
    dev=json.loads((state/'TRANSFORMER_V3_DEV_RESULTS.json').read_text());replay=json.loads((state/'V2_REPLAY_ANALYSIS.json').read_text())
    if sha(state/'TRANSFORMER_V3_DEV_RESULTS.json')!=release['development_results_sha256']:raise ValueError('Frozen development evidence changed')
    rows=[]
    for c in data['cases']:
        r=compact(c,c['task']['profile']);r['scenario']=c['task']['scenario'];rows.append(r)
    grouped=bridge_ranges(rows);votes=bridge_votes(rows,release['chosen']);signal=research_signal(dev,replay)
    decision=choose_decision(dev,signal,votes,certified=False)
    chosen=[g for g in grouped if all(g[k]==release['chosen'][k] for k in ('family','mapping','profile'))]
    candidates=[g for g in grouped if g['missing_funding_total_economic_range_USDT'] is not None]
    max_impact=max(candidates,key=lambda r:r['missing_funding_total_economic_range_USDT']) if candidates else None
    dev_chosen=[r for r in dev['rows'] if str(r['seed'])=='ENSEMBLE' and all(r[k]==release['chosen'][k] for k in ('family','mapping','profile'))]
    worst=sorted(dev_chosen,key=lambda r:float('inf') if r['net_USDT'] is None else r['net_USDT'])
    losses=[]
    for scale in (1.,.01):
        for scenario in SCENARIOS:
            own=[r for r in rows if r['scenario']==scenario and r['funding_scale']==scale and all(r[k]==release['chosen'][k] for k in ('family','mapping','profile'))]
            if len(own)!=1:raise ValueError('One frozen selected wallet per independent funding source required')
            r=own[0];losses.append(dict(scenario=scenario,funding_scale=scale,count=r['liquidation_count'],loss_USDT=r['liquidation_loss_USDT'],
                counts_by_symbol=r['liquidation_counts_by_symbol'],reentries=r['reentry_after_liquidation']))
    attribution=[dict(funding_scale=g['funding_scale'],long_net_USDT=g['statistics']['long_net_USDT'],short_net_USDT=g['statistics']['short_net_USDT'],
        native_total_net_USDT=g['statistics']['net_USDT'],mapping=g['mapping'],
        scope='LONG_AND_SHORT_ARE_DISJOINT_JOURNAL_CONTRIBUTIONS; NEUTRAL_IS_A_SEPARATE_MAPPING_NOT_A_THIRD_ADDITIVE_COMPONENT') for g in chosen]
    answers=[
        dict(question=1,answer='RESTORATION_COUNTS',restored=replay['restored_original_incomplete'],original=111,by_reason=replay['restoration_counts']),
        dict(question=2,answer='ISOLATED_HALT_ENGINE_FAILURE_IS_TESTED_SEPARATELY_FROM_COMPLETE_WALLET_SIGNAL',
             repaired_counts=replay['restoration_counts'],neutral_gate=replay['stable_neutral_gate_pass'],
             remaining_scope='CAPACITY_LIMITED_RISK_REDUCTION_OR_REAL_INSOLVENCY_REMAIN_EXPLICIT_N_E; PROFITABILITY_IS_SEPARATE_FROM_RESTORATION'),
        dict(question=3,answer='COMPLETE_WALLET_NEUTRAL_GATES',full_replayed=replay['stable_neutral_gate_pass'],
             original_full_neutral=[s for s in replay['summaries'] if s['family'] in ('CROSS_ASSET_MULTITASK','PATCH_CROSS_ASSET_MULTITASK') and s['mapping']=='NEUTRAL'],
             half_and_new_development=[s for s in dev['summaries']+dev['comparator_summaries'] if s['mapping']=='NEUTRAL']),
        dict(question=4,answer='PAIRED_MATURE_DAILY_PROXY_REGRET',evidence=signal['proxy_regret_evidence'],
             all_seed_fold_deltas=dev['regret_comparison'],qualification='DESCRIPTIVE_REDUCTION_NOT_SIGNIFICANCE_OR_NATIVE_OPTIMAL_ORACLE_PROOF'),
        dict(question=5,answer='ALL_SIX_WINDOW_ROWS_AND_WORST_REGISTERED_CANDIDATE',windows=worst,
             new_policy_fold_action_participation=[{k:r[k] for k in ('family','fold','funding_scale','policy_participation')} for r in dev['prediction_metrics'] if r['family'] in FAMILIES and str(r['seed'])=='ENSEMBLE'],
             qualification='REALIZED_GROSS_AND_SIGNED_EXPOSURE_WITH_LONG_SHORT_PNL_DESCRIBE_PARTICIPATION; ACTION_HIT_AND_REGRET_DESCRIBE_POLICY; NO_WORST_WINDOW_TUNING'),
        dict(question=6,answer='MATCHED_FULL_HALF_NON_LINEARITY',pairs=dev['half_linearity'],
             qualification='HALF_MINUS_HALF_FULL_IS_DIAGNOSTIC; RESIZING_FEES_AND_NAV_FEEDBACK_CAN_BE_NONLINEAR_WITHOUT_LIQUIDATION'),
        dict(question=7,answer='ONLY_IMPUTED_SENSITIVITY_AVAILABLE',exact_recovered='NOT_AVAILABLE',formal_v2='PERMANENT_NOT_EVALUABLE',
             bridge_votes=votes,economic_decision_consistent=len({v['economic_vote'] for v in votes})==1,
             qualification='CONSISTENT_BRIDGES_DO_NOT_MAKE_UNKNOWN_BINANCE_EVENTS_EXACT'),
        dict(question=8,answer='FIVE_BRIDGE_MATCHED_NATIVE_NET_RANGE',largest_complete_comparison=max_impact,
             selected_candidate=chosen,incomplete_groups=[g for g in grouped if not g['complete_all_five']],
             qualification='NOT_A_BOUND_ON_UNKNOWN_TRUE_RATE; ONLY_REGISTERED_SCENARIO_RANGE_INCLUDES_FORECAST_FEEDBACK'),
        dict(question=9,answer='SELECTED_RESET_WALLET_LIQUIDATION_LOSS_PER_BRIDGE_UNIT',selected_wallets=losses,
             original720_diagnostic_loss_USDT=replay['original_model_liquidation_loss_USDT'],original720_counts_by_symbol=replay['original_model_liquidation_counts_by_symbol'],
             qualification='SUMS_ACROSS_MODEL_RESET_WALLETS_ARE_DIAGNOSTIC_WORKLOAD_TOTALS_NOT_ONE_INVESTMENT_LOSS'),
        dict(question=10,answer='DISJOINT_LONG_SHORT_ATTRIBUTION_AND_SEPARATE_NEUTRAL_MAPPING',selected=attribution,
             neutral_comparisons=[g for g in grouped if g['mapping']=='NEUTRAL']),
        dict(question=11,answer=decision,development_gate=dev['development_gate_pass'],research_signal=signal,bridge_votes=votes,
             native_risk_certified=False,qualification='NO_REAL_ORDER_OR_PAPER_DEPLOYMENT_EXECUTED; INVESTMENT_STATE_NONE_CASH')]
    return dict(status='FINAL_IMPUTED_LOCKED_SENSITIVITY_COMPLETE',decision=decision,chosen=release['chosen'],answers=answers,
        rows=rows,bridge_ranges=grouped,bridge_votes=votes,headline_selected_min_median_max=chosen,
        direct_estimated_funding=[direct_estimated_funding(c) for c in data['cases']],
        complete_locked_accounts=sum(r['full_calendar_and_paid_cash'] for r in rows),locked_accounts=400,
        original_v2_evidence_and_formal_N_E_preserved=True,no_locked_tuning=True,no_best_scenario_selection=True,
        locked_development_freeze_sha256=sha(release_path),locked_evidence_sha256=sha(source),
        development_results_sha256=sha(state/'TRANSFORMER_V3_DEV_RESULTS.json'),replay_analysis_sha256=sha(state/'V2_REPLAY_ANALYSIS.json'),
        source_sha256=sha(__file__),investment_state='NONE/CASH',native_risk_certified=False,
        data_scope='BINANCE_PUBLIC_PRICES_WITH_BYBIT_STYLE_MINUTE_MARK_LIQUIDATION_AND_UNCERTIFIED_MMR0.005_MMD0; FIVE_IMPUTED_FUNDING_SCENARIOS')

def number(value):return 'N/E' if value is None else f'{value:.4f}'

def main():
    p=argparse.ArgumentParser();p.add_argument('--state',required=True);a=p.parse_args();state=Path(a.state);result=final_analysis(state)
    path=state/'TRANSFORMER_V3_FINAL_RESULTS.json'
    if path.exists():
        if json.loads(path.read_text())!=result:raise ValueError('Preserve existing final evidence')
    else:atomic(path,result)
    lines=['# Transformer v3：Oracle policy、逐仓强平与五种资金费敏感性','',
        '**'+result['decision']+'**；投资状态 NONE/CASH。','',
        result['data_scope'],'', '原 v2 证据、负结果与 formal locked NOT_EVALUABLE 永久保留。本报告是新增条件实验，插值并未恢复精确交易所事件。',
        f"实际封存期账户 {result['locked_accounts']} 个，完整日历及收费终值现金 {result['complete_locked_accounts']} 个。全部五种方案、两种原资金费单位解释保留，未选 winner seed 或最佳补值。",'',
        '## 冻结候选的五方案范围','',json.dumps(result['chosen']), '',
        '|Funding scale|Net USDT min / median / max|Net % min / median / max|Liq loss USDT min / median / max|All five complete|',
        '|---:|---|---|---|---|']
    for g in result['headline_selected_min_median_max']:
        def triple(k):return ' / '.join(number(g['statistics'][k][q]) for q in ('min','median','max'))
        lines.append(f"|{g['funding_scale']}|{triple('net_USDT')}|{triple('net_return_percent')}|{triple('liquidation_loss_USDT')}|{g['complete_all_five']}|")
    a=result['answers'];restore=a[0]
    lines+=['','## 十一个问题逐项回答','',
        f"1. 原111个不完整账户恢复 {restore['restored']}/111；按旧原因：{json.dumps(restore['by_reason'])}。未恢复者保留 N/E。",
        f"2. 修复后继续运行的强平账户证明旧整钱包停机属于执行语义问题；完整账户是否赚钱另行判断。原 v2 neutral 稳定门槛：{a[1]['neutral_gate']}。剩余容量约束停机不伪作完整收益。",
        '3. v2 multitask/patch 的完整 neutral 六窗口及 HALF 比较逐行保留。'+json.dumps(a[2]['original_full_neutral']),
        '4. 新 policy 与旧 utility 的同 fold、同 funding、同成熟标签 regret 配对：'+json.dumps(a[3]['evidence'])+'；是日频 expert proxy 的描述性改善，不是原生钱包最优性或统计显著性证明。',
        '5. 最差开发窗口及其 LONG/SHORT、净敞口、gross、cost和当时目标全部列入结果。'+json.dumps([{k:r.get(k) for k in ('window','funding_scale','net_USDT','mean_gross','mean_signed_exposure','long_net_USDT','short_net_USDT','causal_target_participation')} for r in a[4]['windows'][:2]])+'；每fold的SMA/HOLD/CASH概率另列，不用未来标签可得性过滤参与度，没有看坏窗口再改模型。',
        '6. FULL/HALF 的所有 matched half_net−0.5×full_net USDT、强平次数与损失列在开发结果；费用与NAV反馈也可能产生非线性，不自动归因于强平。',
        '7. 精确/恢复的封存收益无法评价，只有 imputed 五方案。各方案同一候选经济判断：'+json.dumps(result['bridge_votes'])+f"；是否一致 {a[6]['economic_decision_consistent']}。",
        '8. 最大五方案完整账户收益范围：'+json.dumps(a[7]['largest_complete_comparison'])+'。这是登记方案范围，不是未知真实资金费的数学上界。包含相同冻结模型因果 funding 特征改变的间接影响；三条估算事件直接现金另列。',
        '9. 冻结候选各独立封存账户强平损失和币种计数：'+json.dumps(a[8]['selected_wallets'])+'。多个独立钱包不能相加为一次真实投资损失。',
        '10. LONG/SHORT 是同一钱包的互斥账本归因；NEUTRAL 是独立 mapping，不是可再加一次的第三条贡献。冻结候选范围：'+json.dumps(a[9]['selected']),
        '11. **'+result['decision']+'**。开发门槛及预测/后悔值条件和封存五方案规则均事前登记；风险档位未取得官方认证，没有发出任何交易订单。','',
        '## 证据','', 'TRANSFORMER_V3_FINAL_RESULTS.json 保留400行所有映射、模型、profile、方案、费用、执行、资金费、gross/MDD/vol/Sharpe、强平、再入场和独立审计SHA。',
        'TRANSFORMER_V3_DEV_RESULTS.json 保留所有 seed、六开发窗口、费用与 FULL/HALF 配对。模型可用性只使用当时可得输入；未来标签只进入成熟训练或事后诊断。',
        '数据价格来源与费用/强平场所不同；分钟 close 不能证明逐笔交易所触发，MMR与历史risk档位为显式未认证条件。任何 N/E 都不被部分收益代替；独立10k钱包不拼APR。']
    (state/'TRANSFORMER_V3_FINAL_REPORT.md').write_text('\n\n'.join(lines)+'\n')
    print(result['decision'],result['complete_locked_accounts'],'/400 complete locked wallets',flush=True)

if __name__=='__main__':main()
