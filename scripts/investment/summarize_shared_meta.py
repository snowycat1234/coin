"""Compact economic acceptance for the fixed public signal/meta paired run."""
import argparse,json
from pathlib import Path
from datetime import UTC,datetime
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.run_shared_meta import sha

def write(p,v):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

def main():
    ap=argparse.ArgumentParser()
    for k in ('actual','output','document'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();r=json.loads(a.actual.read_bytes())
    assert r['status']=='COMPLETE_ONE_SHARED_META_FIT_TWELVE_FRESH_MATCHED_ACCOUNTS_CONDITIONAL_PROXY'
    assert len(r['cases'])==r['required_accounts']==12 and r['models_fit']+r.get('fit_reused',{}).get('actual_fits_total',0)==1
    task=json.loads((STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')).read_bytes())
    assert task['status']=='completed' and task['exit_code']==0
    for p,digest in r['binding']['source_hashes'].items():assert sha(ROOT/p)==digest,p
    assert r['split_evidence']['maximum_training_label_available_us']<r['split_evidence']['fit_cutoff_us']
    assert r['public_intent_reference']['status'].startswith('PASS') and r['raw_target_golden'].startswith('PASS')
    raw=pl.read_parquet(Path(r['run_dir'])/'raw_intents.parquet');filtered=pl.read_parquet(Path(r['run_dir'])/'filtered_intents.parquet')
    assert raw.select('symbol','close_us','available_us').equals(filtered.select('symbol','close_us','available_us'))
    assert np.all((filtered['prediction'].to_numpy()==1)|(filtered['prediction'].to_numpy()==raw['prediction'].to_numpy()))
    rows=[];by={};assets=[]
    for c in r['cases']:
        for entry in c['artifacts'].values():assert sha(entry['path'])==entry['sha256']
        s=c['summary'];check=c['independent'];complete=s['completed_minutes']==s['required_minutes']
        dm=s['daily_metrics'] or {};ex=s.get('realized_exposure',{})
        assert s['required_minutes']==122*1440 and s['completed_minutes']==check['minutes']
        assert check['status']==('PASS_INDEPENDENT_SIGNED_JOURNAL_MINUTE_MARKED_NAV_FUNDING_AND_WALLET_IDENTITY' if complete else
            'PASS_INDEPENDENT_PREFIX_AND_STOPPED_JOURNAL_WALLET_DECLARED_MARK_NOT_FULL_CALENDAR')
        if c['strategy']!='HOLD':assert check['target_reference']['status'].startswith('PASS')
        assert s['cash_close_retry_policy']==r['protocol']['execution_policy']
        assert s['cost_scenario']['provenance']['fee_source_sha256']=='a406d4bd0e47ff4ae4895fda0a2f2698b5763667d82b22b7f264d6220e27e8bd'
        assert abs(sum(v['net'] for v in check['by_past_regime'].values())-s['net_PnL'])<1e-7
        row=dict(strategy=c['strategy'],cost=c['cost'],unit=c['unit'],net_USDT=s['net_PnL'] if complete else None,
            observed_stop_or_end_net_USDT=s['net_PnL'],complete_calendar=complete,completed_minutes=s['completed_minutes'],
            completed_full_days=len(check['daily_direction_contributions']),stop_us=s['stop_us'],account_status=s['account_status'],
            completion=s['completion'],gross_USDT=s['gross_PnL_same_quantities'],
            fee_USDT=s['fees_USDT'],spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],funding_USDT=s['funding_USDT'],
            LONG_USDT=s['long_short_marked_contribution']['LONG']['net_contribution'],SHORT_USDT=s['long_short_marked_contribution']['SHORT']['net_contribution'],CASH_USDT=0.,
            turnover=s.get('normalized_total_turnover'),minute_max_drawdown=s.get('minute_max_drawdown'),daily_annualized_volatility=dm.get('annual_volatility'),daily_sharpe=dm.get('sharpe'),
            mean_gross=ex.get('minute_mean_gross_weight'),max_gross=s['maximum_actual_gross_weight'],mean_net=ex.get('minute_mean_net_signed_weight'),
            mean_collateral=ex.get('minute_mean_isolated_collateral_over_initial_capital'),max_collateral=ex.get('minute_max_isolated_collateral_over_initial_capital'),
            residual_USDT=s['terminal_marked_notional'],liquidated=s['terminal_cash_realized'],by_past_regime=check['by_past_regime'],
            daily_concentration=s.get('daily_net_gain_concentration'),real_short_open_legs=check['actual_short_open_legs'],
            evidence_scope='FULL_MARKED_CALENDAR' if complete else 'STOPPED_PREFIX_NOT_SIMULATED_LIQUIDATION_OR_FULL_RETURN',
            account_reused_from_closed_predecessor=c['account_reused_from_closed_predecessor'])
        assert abs(row['LONG_USDT']+row['SHORT_USDT']-row['observed_stop_or_end_net_USDT'])<1e-7
        assert abs(row['gross_USDT']-row['fee_USDT']-row['spread_USDT']-row['slippage_USDT']+row['funding_USDT']-row['observed_stop_or_end_net_USDT'])<1e-7
        rows.append(row);by[(c['strategy'],c['cost'],c['unit'])]=row
        ledger={s:dict(gross=0.,fees=0.,execution=0.,funding=0.,legs=0) for s in r['protocol']['symbols']}
        for v in json.loads(Path(c['artifacts']['trades.json']['path']).read_bytes()):
            l=ledger[v['symbol']];l['gross']-=v['position_delta']*v['mid_price'];l['fees']+=v['fee_USDT_mid'];l['execution']+=v['execution_cost'];l['legs']+=1
        for v in json.loads(Path(c['artifacts']['funding.json']['path']).read_bytes()):ledger[v['symbol']]['funding']+=v['signed_funding_USDT']
        for symbol,l in ledger.items():
            l['gross']+=s['terminal_signed_marked_notional'][symbol];l['net']=l['gross']-l['fees']-l['execution']+l['funding']
            assets.append(dict(strategy=c['strategy'],cost=c['cost'],unit=c['unit'],symbol=symbol,**l))
        assert abs(sum(l['net'] for l in ledger.values())-s['net_PnL'])<1e-7
    comparisons=[]
    for cost in ('BASE27','STRESS43'):
        for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
            old=by[('PUBLIC_SMA_INTENT',cost,unit)];new=by[('PUBLIC_SMA_META',cost,unit)]
            paired=old['complete_calendar'] and new['complete_calendar']
            comparisons.append(dict(cost=cost,unit=unit,paired_full_calendar=paired,
                net_delta_USDT=new['net_USDT']-old['net_USDT'] if paired else None,
                DD_delta=new['minute_max_drawdown']-old['minute_max_drawdown'] if paired else None,
                vol_delta=new['daily_annualized_volatility']-old['daily_annualized_volatility'] if paired else None,
                cost_delta_USDT=sum(new[k]-old[k] for k in ('fee_USDT','spread_USDT','slippage_USDT')) if paired else None,
                adopted_condition=paired and new['net_USDT']>0 and new['net_USDT']>old['net_USDT']+1e-7))
    decision='RETAIN_META_AS_DEVELOPMENT_CHALLENGER' if all(v['adopted_condition'] for v in comparisons) else 'PAUSE_THIS_FITTED_RECIPE'
    accepted=dict(status='ACCEPTED_SHARED_META_ECONOMICS_NOT_INVESTMENT',binding=r['binding'],actual_path=str(a.actual),actual_sha256=sha(a.actual),
        decision=decision,qualified_investment='NONE/CASH',long_term_APR='NOT_EVALUABLE',actual_days=122,capital_USDT=10000,
        new_accounts=sum(not c['account_reused_from_closed_predecessor'] for c in r['cases']),
        reused_accounts=sum(c['account_reused_from_closed_predecessor'] for c in r['cases']),actual_accounts_total=12,
        complete_accounts=sum(v['complete_calendar'] for v in rows),models_fit=1,new_model_fits=r['models_fit'],
        retained_fit_recovery=r.get('fit_reused'),primary_fits=0,fit_configurations=1,hyperparameter_search=0,
        split_evidence=r['split_evidence'],gate_counts=r['gate_counts'],rows=rows,comparisons=comparisons,asset_contributions=assets,
        financial_scope='INDEPENDENT_RECORDED_FILLS_NAV_WALLET_FUNDING; NOT_NATIVE_ORDER_ENGINE_OR_HISTORICAL_TIERS',
        risk_scope='COMMON_CAPS_NOT_REALIZED_RISK_MATCHED; PAST_COV_SCALE_DOWN_ONLY; EXPLICIT_RESIDUALS',
        funding_unit='UNCONFIRMED_BOTH_SCENARIOS',primary_strategy_scope=r['protocol']['primary_signal'],
        causal_reference=r['public_intent_reference'],raw_target_golden=r['raw_target_golden'],regression=r['protocol']['regression'],
        resources={k:r[k] for k in ('elapsed_seconds','peak_RSS_bytes','shared_RAM_sampled_peak_bytes','owned_bytes','GPU_hours','disk_before')},
        maximum_independent_NAV_error_USDT=max(c['independent']['maximum_NAV_error_USDT'] for c in r['cases']),
        maximum_independent_wallet_error_USDT=max(c['independent']['maximum_wallet_error_USDT'] for c in r['cases']),created_utc=datetime.now(UTC).isoformat())
    write(a.output,accepted)
    lines=['# D090：固定公开双向意图与共享execute/reject','',f'决定：**{decision}**。投资资格NONE/CASH；长期APR NOT_EVALUABLE。','',
        '一个共享binary XGBoost120树depth3 CPU2、零搜参；固定SMA50/200第一层无fit，原should_long/should_short/update_position hooks复用。',
        '第一层为从Sep2024准备的外部意图状态，独立于账户成交/过滤；不是Jesse全余额或原生执行复制。过滤逐日keep/cash，不反转，不重新分配拒绝预算；重新计算过去协方差并完整跑账户。',
        'Sep2024–Feb2025训练，5d标签严格成熟于Mar1前；经济Mar–Jun2025连续122日、10币/完整10k共享资本，各账户重新初始化，不拼接。已见开发out-of-fit，不是unseen。',
        '标签：signed intent×未来5d trade-open收益>37bp，27bp成本+10bp余量只进入边界一次；资金费单位/发布时钟UNKNOWN而排除标签/特征。实际账户另外完整计费/滑点/点差/实际资金费两个解释。',
        '模型输入闭合日价量/ATR/vol/趋势/BTCETH/breadth/onehot symbol+固定方向；无第一层训练内概率，不需学习模型OOF。零意图/未知未来不训练；无early stopping、阈值调整或额外seed。',
        f"三策略×两成本×两资金费解释=12个实际账户；最后恢复阶段按SHA复用{accepted['reused_accounts']}个已完成账本、只新增{accepted['new_accounts']}个，首轮含一个模型拟合。全部相同persistent cash-close、逐仓1x、abs30%/gross60%、过去协方差scale-down。HOLD/现金保留，实际风险不同。",
        'Binance USD-M价格/mark/funding配Bybit用户taker5.5bp：跨场所代理，非Bybit原生。历史数量/保证金层级和瞬时mark极值未认证。','',
        '|策略|成本|资金费解释|净USDT|毛USDT|LONG|SHORT|费用/执行|资金费|换手|vol%|DD%|Sharpe|平均gross%|残仓USDT|',
        '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    def fmt(v,scale=1):return 'NOT_EVALUABLE' if v is None else f'{v*scale:.2f}'
    for v in rows:
        sh='UNKNOWN' if v['daily_sharpe'] is None else f"{v['daily_sharpe']:.2f}"
        lines.append(f"|{v['strategy']}|{v['cost']}|{v['unit']}|{fmt(v['net_USDT'])}|{v['gross_USDT']:.2f}|{v['LONG_USDT']:.2f}|{v['SHORT_USDT']:.2f}|{v['fee_USDT']+v['spread_USDT']+v['slippage_USDT']:.2f}|{v['funding_USDT']:.2f}|{fmt(v['turnover'])}|{fmt(v['daily_annualized_volatility'],100)}|{fmt(v['minute_max_drawdown'],100)}|{sh}|{fmt(v['mean_gross'],100)}|{v['residual_USDT']:.2f}|")
    lines+=['','CASH解析参照：净0、成本0、风险0、完整资本10k，不冒称模拟账户。全部净值含未平仓mark，正残仓未删除；非实际付费平仓的liquidated return NOT_EVALUABLE。','',
        '## 市场状态与方向贡献（BASE27/PCT，描述性）','',
        '|策略|状态|日数|LONG|SHORT|CASH|净USDT|','|---|---|---:|---:|---:|---:|---:|']
    for name in ('PUBLIC_SMA_INTENT','PUBLIC_SMA_META','HOLD'):
        for state,v in by[(name,'BASE27','RAW_AS_PERCENT')]['by_past_regime'].items():
            lines.append(f"|{name}|{state}|{v['days']}|{v['LONG']:.2f}|{v['SHORT']:.2f}|{v['CASH']:.2f}|{v['net']:.2f}|")
    lines+=['','BTC上一闭合日SMA200/20d方向与过去崩盘定义复用，仅描述性分层；收益含既有头寸与成本，不作入场因果归因。CASH不会产生虚构利息，费用仍属于实际多/空腿。','',
        '## 验收与复现','',
        '原公开状态独立scalar50/200窗口重算；公共raw目标与共有风险目标权重一致1e-12；每新账户独立复算全部分钟NAV/钱包/资金费/目标，所有工件SHA逐一验。',
        '2项新因果/label/identity回归通过；首次合成末尾未知label计数误写12而实际10的失败V1保留，修正fixture后V2通过。清算停止不得被完整日历断言遮蔽；新停止参考支持前缀与最后真实mark，全部缺口与残仓保留，不模拟免费清算。',
        '预测方向计数：'+json.dumps(r['gate_counts'],ensure_ascii=False),
        f"fit/account wall {r['elapsed_seconds']:.3f}s；共享RAM采样{r['shared_RAM_sampled_peak_bytes']/1e9:.3f}GB/RSS{r['peak_RSS_bytes']/1e9:.3f}GB、工件{r['owned_bytes']/1e6:.2f}MB/GPU0。磁盘运行前扫描{r['disk_before']['measured_utc']}：{r['disk_before']['total_bytes']/1e9:.3f}GB。",
        '源码commit/protocol/输入/全部工件SHA、保证金/敞口/集中度/逐币贡献见结构化验收；收益只有这122日，不能年化成长期APR。','',
        '```sh','scripts/with_task_progress.sh --title "共享元标签复现" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_shared_meta.py --protocol protocols/SHARED_SIGNAL_META_20261005_V1.json --run-dir /home/xflops/coin-state/d090-independent-reproduction --output reports/fast_research/SHARED_META_INDEPENDENT_REPRODUCTION.json','```']
    lines+=['','## 实际停止与完整性','',
        '停止账户费用、毛损益和方向贡献只属于停止前缀，不能与122日完整账户相减；停止后的日子没有补零。停止时mark独立账本核的是绑定summary声明价格，不冒充独立行情采样/清算成交。','',
        '|策略|成本/资金费解释|完成分钟|停止时净损益USDT（不是全窗）|状态|残仓USDT|',
        '|---|---|---:|---:|---|---:|']
    for v in rows:
        if not v['complete_calendar']:
            lines.append(f"|{v['strategy']}|{v['cost']}/{v['unit']}|{v['completed_minutes']}|{v['observed_stop_or_end_net_USDT']:.2f}|{v['account_status']}|{v['residual_USDT']:.2f}|")
    with a.document.open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(status=accepted['status'],decision=decision,comparisons=comparisons)))

if __name__=='__main__':main()
