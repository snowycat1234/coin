"""Read-only economic decision and compact publication for a completed fit."""
import argparse, hashlib, json
from pathlib import Path
from datetime import UTC, datetime
from quant.paths import ROOT

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()

def write(p,v):
    with Path(p).open('x',encoding='utf-8') as f:
        json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False); f.write('\n')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--actual',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--document',type=Path,required=True)
    a=ap.parse_args(); r=json.loads(a.actual.read_bytes())
    assert r['status']=='COMPLETE_ONE_SHARED_FIT_MATCHED_DIRECTION_AND_RULE_ECONOMICS_CONDITIONAL_PROXY'
    assert len(r['cases'])==r['required_accounts']==20
    for p,digest in r['binding']['source_hashes'].items(): assert sha(ROOT/p)==digest,p
    rows=[]; byid={}
    for c in r['cases']:
        for artifact in c['artifacts'].values(): assert sha(artifact['path'])==artifact['sha256']
        s=c['summary']; check=c['independent']
        assert s['completed_minutes']==s['required_minutes']==87840 and check['minutes']==87840
        assert check['status']=='PASS_INDEPENDENT_SIGNED_JOURNAL_MINUTE_MARKED_NAV_FUNDING_AND_WALLET_IDENTITY'
        assert s['cost_scenario']['provenance']['fee_source_sha256']=='a406d4bd0e47ff4ae4895fda0a2f2698b5763667d82b22b7f264d6220e27e8bd'
        assert abs(sum(v['net'] for v in check['by_past_regime'].values())-s['net_PnL'])<1e-7
        dm=s['daily_metrics']; ex=s['realized_exposure']
        row=dict(id=c['id'],strategy=c['strategy'],cost=c['cost_id'],unit=c['unit_id'],
            net_USDT=s['net_PnL'],gross_USDT=s['gross_PnL_same_quantities'],fee_USDT=s['fees_USDT'],
            spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],funding_USDT=s['funding_USDT'],
            LONG_USDT=s['long_short_marked_contribution']['LONG']['net_contribution'],
            SHORT_USDT=s['long_short_marked_contribution']['SHORT']['net_contribution'],CASH_USDT=0.,
            turnover=s['normalized_total_turnover'],fill_legs=s['trade_legs'],short_open_legs=check['actual_short_open_legs'],
            daily_annualized_volatility=dm['annual_volatility'],daily_sharpe=dm['sharpe'],
            minute_max_drawdown=s['minute_max_drawdown'],mean_gross=ex['minute_mean_gross_weight'],
            mean_net=ex['minute_mean_net_signed_weight'],max_gross=s['maximum_actual_gross_weight'],
            mean_collateral_over_initial_capital=ex['minute_mean_isolated_collateral_over_initial_capital'],
            max_collateral_over_initial_capital=ex['minute_max_isolated_collateral_over_initial_capital'],
            liquidated=s['terminal_cash_realized'],residual_marked_notional=s['terminal_marked_notional'],
            by_past_regime=check['by_past_regime'],daily_gain_concentration=s['daily_net_gain_concentration'])
        assert abs(row['LONG_USDT']+row['SHORT_USDT']-row['net_USDT'])<1e-7
        assert abs(row['gross_USDT']-row['fee_USDT']-row['spread_USDT']-row['slippage_USDT']+row['funding_USDT']-row['net_USDT'])<1e-7
        rows.append(row); byid[(c['strategy'],c['cost_id'],c['unit_id'])]=row
    # Asset PnL attribution uses the real signed legs and remaining marked
    # inventory; this is neither independent full-capital coin accounts nor a
    # claim that the strategy cause of each profit is identified.
    asset_rows=[]
    symbols=r['protocol']['symbols']
    for c in r['cases']:
        ledger={s:dict(gross=0.,fee=0.,execution=0.,funding=0.,legs=0) for s in symbols}
        trades=json.loads(Path(c['artifacts']['trades.json']['path']).read_bytes())
        funds=json.loads(Path(c['artifacts']['funding.json']['path']).read_bytes())
        for t in trades:
            v=ledger[t['symbol']]; v['gross']-=t['position_delta']*t['mid_price']
            v['fee']+=t['fee_USDT_mid']; v['execution']+=t['execution_cost']; v['legs']+=1
        for f in funds: ledger[f['symbol']]['funding']+=f['signed_funding_USDT']
        for s,v in ledger.items():
            v['gross']+=c['summary']['terminal_signed_marked_notional'][s]
            v['net']=v['gross']-v['fee']-v['execution']+v['funding']
            asset_rows.append(dict(case_id=c['id'],symbol=s,**v))
        assert abs(sum(v['net'] for v in ledger.values())-c['summary']['net_PnL'])<1e-7
    comparisons=[]
    for cost in ('BASE27','STRESS43'):
        for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
            ls=byid[('XGB_LONG_SHORT',cost,unit)]; lo=byid[('XGB_LONG_ONLY',cost,unit)]
            benefit=(ls['net_USDT']>lo['net_USDT']+1e-7 or ls['minute_max_drawdown']<lo['minute_max_drawdown']-1e-10
                or ls['daily_sharpe'] is not None and lo['daily_sharpe'] is not None and ls['daily_sharpe']>lo['daily_sharpe']+1e-10)
            comparisons.append(dict(cost=cost,unit=unit,net_delta_USDT=ls['net_USDT']-lo['net_USDT'],
                DD_delta=ls['minute_max_drawdown']-lo['minute_max_drawdown'],vol_delta=ls['daily_annualized_volatility']-lo['daily_annualized_volatility'],
                either_predeclared_benefit=benefit,short_contribution_positive=ls['SHORT_USDT']>0,
                scope='PAIRED_MARKED_NAV_NOT_SUM_OF_INDEPENDENT_LONG_AND_SHORT_WALLETS'))
    decision='RETAIN_FOR_RESEARCH_NOT_INVESTMENT' if all(c['either_predeclared_benefit'] for c in comparisons) else 'PAUSE_THIS_FIXED_RECIPE'
    native_model=json.loads((Path(r['run_dir'])/'xgb_shared.json').read_bytes())
    actual_tree_count=len(native_model['learner']['gradient_booster']['model']['trees'])
    accepted=dict(status='ACCEPTED_ECONOMIC_COMPARISON_MARKED_AND_LIQUIDATED_SCOPES_SEPARATE',
        actual_path=str(a.actual),actual_sha256=sha(a.actual),binding=r['binding'],actual_days=61,full_capital_USDT=10000,
        one_shared_fit_total=r.get('fit_reused',{}).get('actual_models_fit_total',r['models_fit']),
        accepted_accounts=20,actual_short_open_legs=sum(x['short_open_legs'] for x in rows),rows=rows,
        booster_rounds=120,actual_fitted_tree_count=actual_tree_count,configurations=1,
        comparisons=comparisons,asset_contributions=asset_rows,decision=decision,qualified_investment='NONE/CASH',long_term_APR='NOT_EVALUABLE',
        learned_regime_HMM='NOT_RUN',meta_labeling='NOT_RUN',new_unseen_evidence=False,
        derivative_features=r['protocol']['feature_missing'],classification=r['classification'],
        resources={k:r[k] for k in ('elapsed_seconds','peak_RSS_bytes','shared_RAM_sampled_peak_bytes','owned_bytes','GPU_hours','disk_before')},
        resource_peak_scope='PROCESS_RSS_AND_PER_RUN_SHARED_SAMPLES_NOT_RESET_KERNEL_LIFETIME_PEAK',
        maximum_independent_NAV_error_USDT=max(c['independent']['maximum_NAV_error_USDT'] for c in r['cases']),
        maximum_independent_wallet_error_USDT=max(c['independent']['maximum_wallet_error_USDT'] for c in r['cases']),
        original_failure_preserved=r.get('fit_reused'),created_utc=datetime.now(UTC).isoformat())
    write(a.output,accepted)
    lines=['# D085：共享三分类方向基线与真实账户对照','',
        f'决定：**{decision}**。投资候选仍 NONE/CASH，长期APR NOT_EVALUABLE。', '',
        f'一套10币共享XGBoost（120轮boosting、实际{actual_tree_count}棵分类树、depth3、CPU2、seed20261005），没有搜索、阈值挑选或逐币训练。',
        '训练Sep2024–Feb2025、诊断Mar–Apr2025、经济May–Jun2025共61日；所有币相同时间切分，5日标签严格成熟。',
        '数据已见开发筛选；Binance USD-M价格/mark/资金费配用户Bybit手续费，是跨场所代理。',
        '5日trade-open价格收益与37bp带比较，成本只进入边界一次；标签不含资金费/实际一分钟延迟。真实账户另外完整计费、容量、资金费与风险减仓。',
        '同资本10k、单币abs30%/gross60%、过去30日协方差最多10%年vol目标、逐仓1x；相同caps不代表实际风险相同。', '',
        '## 完整成本与方向账本', '',
        '|策略|成本|资金费解释|净USDT|毛USDT|LONG|SHORT|费|点差+滑点|资金费|换手|年vol%|分钟DD%|日Sharpe|残仓USDT|',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for x in rows:
        sh='UNKNOWN' if x['daily_sharpe'] is None else f"{x['daily_sharpe']:.2f}"
        lines.append(f"|{x['strategy']}|{x['cost']}|{x['unit']}|{x['net_USDT']:.2f}|{x['gross_USDT']:.2f}|{x['LONG_USDT']:.2f}|{x['SHORT_USDT']:.2f}|{x['fee_USDT']:.2f}|{x['spread_USDT']+x['slippage_USDT']:.2f}|{x['funding_USDT']:.2f}|{x['turnover']:.3f}|{x['daily_annualized_volatility']*100:.2f}|{x['minute_max_drawdown']*100:.2f}|{sh}|{x['residual_marked_notional']:.2f}|")
    lines += ['', 'CASH解析基准：净0、风险0、成本0，完整资本10k；不冒充模拟运行。上述净值包含全部残仓mark，残仓未删除；没有完成付费清仓的账户 **liquidated return NOT_EVALUABLE**。', '',
        '## 双向相对同模型多头的增量', '', '|成本|资金费解释|净增量USDT|DD变化百分点|vol变化百分点|预先任一改善|', '|---|---|---:|---:|---:|---|']
    for c in comparisons: lines.append(f"|{c['cost']}|{c['unit']}|{c['net_delta_USDT']:.2f}|{c['DD_delta']*100:.2f}|{c['vol_delta']*100:.2f}|{c['either_predeclared_benefit']}|")
    lines += ['', 'SHORT_ONLY、LONG_ONLY为同预测消融，独立账户不得相加成为伪组合；LONG_SHORT是唯一同步共享资本双向账户。', '',
        '## 过去可得的行情分层（描述性，不是HMM）','',
        'BTC close>SMA200且20d return>0为BULL，两者负为BEAR；单日<-5%且30d年vol>80%为HIGH_VOL_CRASH，其他SIDEWAYS。不使用未来行情定义状态。', '',
        '|策略(BASE27, RAW_AS_PERCENT)|状态|日数|LONG USDT|SHORT USDT|净 USDT|', '|---|---|---:|---:|---:|---:|']
    for strategy in ('XGB_LONG_SHORT','XGB_LONG_ONLY','XGB_SHORT_ONLY','HOLD','DONCHIAN_EXIT10'):
        x=byid[(strategy,'BASE27','RAW_AS_PERCENT')]
        for label,v in x['by_past_regime'].items():
            lines.append(f"|{strategy}|{label}|{v['days']}|{v['LONG']:.2f}|{v['SHORT']:.2f}|{v['net']:.2f}|")
    lines += ['', '## 资产贡献与成交成本（双向BASE27、RAW_AS_PERCENT）','',
        '|币|毛USDT|净USDT|手续费USDT|执行USDT|资金费USDT|成交腿|','|---|---:|---:|---:|---:|---:|---:|']
    for v in asset_rows:
        if v['case_id']=='XGB_LONG_SHORT_BASE27_RAW_AS_PERCENT':
            lines.append(f"|{v['symbol']}|{v['gross']:.2f}|{v['net']:.2f}|{v['fee']:.2f}|{v['execution']:.2f}|{v['funding']:.2f}|{v['legs']}|")
    lines += ['', '日方向贡献是资金流+当日持仓mark变化的净增量，不把平仓整笔利润任意归给订单原因；按状态分层是关联描述，不是因果证明。缺少的状态没有造样本。', '',
        '## 实际验证与局限', '',
        '所有分钟signed数量、现金流净值桥、资金费归属/正负/严格过去mark、手续费与已实现钱包=free+逐仓抵押物独立复算；检查全部61日，不只是期末。数量仍精确Decimal，独立gross/net统计见结构化验收。',
        '独立验证是记录成交的会计，不是独立重建订单选择、原生保证金层级或全盘价格来源认证；瞬时风险/跳空及历史规则未认证范围沿用原账户。',
        'funding物理单位仍UNKNOWN，两种情景均报告，不能挑更盈利解释。资金费/basis/OI未作为特征；日线可得性是已闭合时间代理，非原生发布认证。',
        '末尾50个未知5日标签保留缺失；重叠标签不是独立交易；模型没有CASH预测不能称已经学会现金择时。HMM/MLP/meta未跑。',
        '首次账户因为严格全额平仓断言而停止：原模型/成交/负结果/225USDT残仓与原退出码保存；修正的是验收范围，模型与原预测逐字一致并复用，首账户未重跑。', '',
        f"共享RAM采样峰值 {r['shared_RAM_sampled_peak_bytes']/1e9:.3f}GB，进程RSS峰值 {r['peak_RSS_bytes']/1e9:.3f}GB，输出增长 {r['owned_bytes']/1e6:.2f}MB，GPU0，swap0。磁盘实际扫描 {r['disk_before']['measured_utc']}：{r['disk_before']['total_bytes']/1e9:.3f}GB，不能当收尾扫描。", '',
        '## 复现', '', '```sh',
        'scripts/with_task_progress.sh --title "共享方向模型" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_shared_direction.py --protocol protocols/SHARED_XGB_DIRECTION_20261005_V1.json --run-dir /home/xflops/coin-state/d085-independent-reproduction --output reports/fast_research/SHARED_DIRECTION_INDEPENDENT_REPRODUCTION.json',
        '```', '',
        '从WSL项目ROOT运行；新独占目录，重新一拟合20账户，不覆盖原证据。所有实际工件位置/SHA、贡献/暴露/保证金/集中度与假设见结构化验收。',
        f'验收：`{a.output}`，SHA `{sha(a.output)}`。实际运行：`{a.actual}`，SHA `{sha(a.actual)}`。']
    with a.document.open('x',encoding='utf-8') as f: f.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(status=accepted['status'],decision=decision,short_open_legs=accepted['actual_short_open_legs'],comparisons=comparisons)))

if __name__=='__main__': main()
