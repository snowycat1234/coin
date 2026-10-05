"""Common-capital economics and descriptive regimes for frozen CTA rules."""
import argparse,json,hashlib
from pathlib import Path
from datetime import datetime,UTC
from quant.paths import ROOT,STATE
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,v):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')

def main():
    ap=argparse.ArgumentParser()
    for k in ('actual','output','document'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();r=json.loads(a.actual.read_bytes())
    assert r['status']=='COMPLETE_FROZEN_CTA_56_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS' and len(r['cases'])==r['required_accounts']==56
    assert r['models_fit']==0 and r['search_configurations']==0 and r['signal_reference']['status'].startswith('PASS')
    t=json.loads((STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')).read_bytes());assert t['status']=='completed' and t['exit_code']==0
    for p,h in r['binding']['source_hashes'].items():assert sha(ROOT/p)==h
    rows=[];identities=set();by={}
    for c in r['cases']:
        identity=(c['strategy'],c['mode'],c['cost'],c['unit']);assert identity not in identities;identities.add(identity)
        for p in c['artifacts'].values():assert sha(p['path'])==p['sha256']
        s=c['summary'];complete=s['completed_minutes']==s['required_minutes'];check=c['independent'];dm=s['daily_metrics'] or {};ex=s.get('realized_exposure',{})
        assert s['required_minutes']==175680 and check['minutes']==s['completed_minutes'] and check['status'].startswith('PASS_INDEPENDENT')
        assert check['target_reference']['status'].startswith('PASS')
        assert s['cash_close_retry_policy']=='PERSIST_DAILY_ZERO_TARGET_UNTIL_FILLED_OR_SUPERSEDED_NO_FREE_FILL'
        assert abs(s['gross_PnL_same_quantities']-s['fees_USDT']-s['spread_cost_USDT']-s['slippage_cost_USDT']+s['funding_USDT']-s['net_PnL'])<1e-7
        assert abs(sum(v['net'] for v in check['by_past_regime'].values())-s['net_PnL'])<1e-7
        row=dict(strategy=c['strategy'],mode=c['mode'],cost=c['cost'],unit=c['unit'],complete=complete,
            net_USDT=s['net_PnL'] if complete else None,return_full_capital=s['net_PnL']/10000 if complete else None,
            stopped_prefix_net_USDT=s['net_PnL'] if not complete else None,completed_minutes=s['completed_minutes'],stop_us=s['stop_us'],status=s['account_status'],
            gross_USDT=s['gross_PnL_same_quantities'],fee_USDT=s['fees_USDT'],spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],funding_USDT=s['funding_USDT'],
            LONG_USDT=s['long_short_marked_contribution']['LONG']['net_contribution'],SHORT_USDT=s['long_short_marked_contribution']['SHORT']['net_contribution'],CASH_USDT=0.,
            turnover=s.get('normalized_total_turnover'),vol=dm.get('annual_volatility'),DD=s.get('minute_max_drawdown'),Sharpe=dm.get('sharpe'),
            mean_gross=ex.get('minute_mean_gross_weight'),max_gross=s['maximum_actual_gross_weight'],mean_net=ex.get('minute_mean_net_signed_weight'),
            max_abs_asset=s['maximum_actual_asset_weights'],mean_margin=ex.get('minute_mean_isolated_collateral_over_initial_capital'),max_margin=ex.get('minute_max_isolated_collateral_over_initial_capital'),
            residual=s['terminal_marked_notional'],paid_flat=s['terminal_cash_realized'],by_past_regime=check['by_past_regime'],
            positive_days=s.get('return_concentration',{}),scope='FULL122D' if complete else 'STOPPED_PREFIX_NOT_COMMON_CALENDAR')
        if c['mode']=='LONG_ONLY':assert abs(row['SHORT_USDT'])<1e-7
        if c['mode']=='SHORT_ONLY':assert abs(row['LONG_USDT'])<1e-7
        if c['strategy']=='CASH':assert complete and s['net_PnL']==0 and s['gross_fill_turnover_USDT']==0 and row['residual']==0
        rows.append(row);by[identity]=row
    paired=[]
    for family in r['protocol']['families']:
        for cost in ('BASE27','STRESS43'):
            for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
                lo=by[(family,'LONG_ONLY',cost,unit)];sh=by[(family,'SHORT_ONLY',cost,unit)];ls=by[(family,'LONG_SHORT',cost,unit)]
                comparable=lo['complete'] and ls['complete']
                paired.append(dict(strategy=family,cost=cost,unit=unit,full_pair=comparable,
                    long_short_minus_long_USDT=ls['net_USDT']-lo['net_USDT'] if comparable else None,
                    DD_delta=ls['DD']-lo['DD'] if comparable else None,vol_delta=ls['vol']-lo['vol'] if comparable else None,
                    short_only_net_USDT=sh['net_USDT'],short_complete=sh['complete'],
                    interpretation='PAIRED_POLICY_TOTAL_EFFECT; SIGNED_COV_AND_CAPITAL_COMPETITION_CHANGE_ACTUAL_RISK; NOT_PURE_SHORT_ALPHA'))
    primary=[v for v in rows if v['cost']=='BASE27' and v['unit']=='RAW_AS_PERCENT']
    complete=sorted((v for v in primary if v['complete']),key=lambda v:v['net_USDT'],reverse=True)
    best=complete[0] if complete else None
    decision='NO_INVESTMENT_QUALIFICATION_RETAIN_FROZEN_BENCHMARKS'
    accepted=dict(status='ACCEPTED_FROZEN_CTA_COMMON_CAPITAL_CONDITIONAL_PROXY',actual_path=str(a.actual),actual_sha256=sha(a.actual),
        binding=r['binding'],rows=rows,paired_direction=paired,base_pct_descriptive_ranking=[(v['strategy'],v['mode'],v['net_USDT']) for v in complete],
        complete_accounts=sum(v['complete'] for v in rows),stopped_accounts=sum(not v['complete'] for v in rows),models_fit=0,parameter_search=0,
        decision=decision,best_development=best,qualified_investment='NONE/CASH',long_term_APR='NOT_EVALUABLE',actual_days=122,full_capital_USDT=10000,
        source_scope='PUBLIC_RULE_COINSIZING_ADAPTER_NOT_FULL_MOP_FABER_OR_TURTLE_REPLICATION',funding_unit='UNKNOWN_BOTH_SCENARIOS',
        data_role='PREVIOUSLY_SEEN_DEVELOPMENT; 122D_NOT_COMPLETE_BULL_BEAR_CYCLES',
        resources={k:r[k] for k in ('elapsed_seconds','peak_RSS_bytes','shared_RAM_sampled_peak_bytes','owned_bytes','GPU_hours','disk_before')},created_utc=datetime.now(UTC).isoformat())
    write(a.output,accepted)
    fmt=lambda x,scale=1:'NOT_EVALUABLE' if x is None else f'{x*scale:.2f}'
    lines=['# 传统 CTA Leaderboard：冻结参数、零训练','',
        '10币/完整10,000 USDT共享账户，2025-03-01至07-01共122日。全部为已见开发数据与Binance USD-M + Bybit用户费用跨场所代理；不是独立候选或原生Bybit。',
        '固定4规则family：真实12日历月TSMOM（月初更新、持有一个月）；SMA200日线close与均线sign；Donchian20/10；20/10+55/20+12m等权forecast。',
        '各币独立信号；past30 sample inverse-vol分配0.6预算、不把cash预算再分配，signed covariance过去30日10%波动只向下缩放。abs30%/gross60%、共享资本、逐仓1x不自动加保证金。',
        '使用既有MIT Jesse Donchian内核、NumPy reduction和原共享账户，零模型/阈值训练/搜参。文献规则的COIN日线组合适配，非完整MOP/Faber/Turtle复制；无Turtle ATR stop/加仓/原单位风控或盈利交易跳过规则。',
        '公开规则来源：[Moskowitz/Ooi/Pedersen 2012](https://doi.org/10.1016/j.jfineco.2011.11.003)、[Faber原作者说明](https://mebfaber.com/2016/09/14/episode-20-listener-qa/)、[Original Turtle Rules](https://www.followingthetrend.com/?mdocs-file=2551)。Faber原long/cash与10月规则不是本signed200日变体；论文传统期货证据不是crypto盈利证明。',
        'BASE27/STRESS43往返假设含taker11bp、spread8/16bp、slip8/16bp；所有已记录funding事件按scale1/.01分别运行，单位未知，不择优解释。',
        '56个实际共享账户，CASH/HOLD每个情景只跑一次作为所有family共同控制。所有停止账本保留并排除完整收益排名；停止后没有补0。','',
        '## BASE27 / RAW_AS_PERCENT 开发排名（描述性，非晋级）','',
        '|策略|方向|净USDT|完整资本收益%|LONG|SHORT|毛PnL|费用/执行|资金费|换手|vol%|DD%|Sharpe|平均gross%|平均净敞口%|峰值保证金%|残仓|',
        '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for v in complete+[v for v in primary if not v['complete']]:
        lines.append('|'+ '|'.join([v['strategy'],v['mode'],fmt(v['net_USDT']),fmt(v['return_full_capital'],100),fmt(v['LONG_USDT']),fmt(v['SHORT_USDT']),fmt(v['gross_USDT']),fmt(v['fee_USDT']+v['spread_USDT']+v['slippage_USDT']),fmt(v['funding_USDT']),fmt(v['turnover']),fmt(v['vol'],100),fmt(v['DD'],100),fmt(v['Sharpe']),fmt(v['mean_gross'],100),fmt(v['mean_net'],100),fmt(v['max_margin'],100),fmt(v['residual'])])+'|')
    lines+=['','CASH Sharpe无定义；停止行的毛损益/方向/成本为前缀，其净收益/风险完整窗口指标NOT_EVALUABLE。所有NAV包括真实未平仓mark；非实付清仓的liquidated return不可评价。','',
        '## 同策略方向对照（完整配对才相减）','',
        '|策略|成本/资金费解释|多空减仅多 净USDT|DD差百分点|vol差百分点|仅空净USDT|',
        '|---|---|---:|---:|---:|---:|']
    for v in paired:lines.append(f"|{v['strategy']}|{v['cost']}/{v['unit']}|{fmt(v['long_short_minus_long_USDT'])}|{fmt(v['DD_delta'],100)}|{fmt(v['vol_delta'],100)}|{fmt(v['short_only_net_USDT'])}|")
    lines+=['','## 过去可知状态中的实际贡献（BASE/PCT）','',
        '|策略|方向|状态|完整日数|含停止部分日|LONG|SHORT|净USDT|',
        '|---|---|---|---:|---|---:|---:|---:|']
    for v in primary:
        for state,b in v['by_past_regime'].items():
            lines.append(f"|{v['strategy']}|{v['mode']}|{state}|{b['days']}|{b.get('partial_stop_day',False)}|{b['LONG']:.2f}|{b['SHORT']:.2f}|{b['net']:.2f}|")
    lines+=['','BTC过去SMA200/20d/crash状态仅描述性，非未来牛熊真值，未用于选择方向或参数；122日不等于长期完整周期。',
        '多空相对仅多的变化包括持仓方向、协方差缩放和同资本竞争；独立SHORT_ONLY不是LONG_SHORT账本中SHORT贡献，相同caps不等于相同实际风险。',
        '本轮可回答指定规则/窗口/成本下的方向与风险机制，不能因负结果永久否定整个short或crypto。投资NONE/CASH，长期APR NOT_EVALUABLE。','',
        '## 资源、验收与复现','',
        f"56账户wall {r['elapsed_seconds']:.2f}s；进程peakRSS {r['peak_RSS_bytes']/1e9:.3f}GB，共享组采样peak {r['shared_RAM_sampled_peak_bytes']/1e9:.3f}GB，工件{r['owned_bytes']/1e9:.3f}GB，GPU0。",
        '独立scalar通道/12m/SMA信号、标的重排/未来扰动/未知预热、inversevol+signedcov目标、逐分钟NAV/钱包/资金费及停止前缀参考验收；来源/SHA/成本/各情景完整指标见结构化报告。',
        '```sh',
        'scripts/with_task_progress.sh --title "传统CTA复现" -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_cta_leaderboard.py --protocol protocols/CTA_LEADERBOARD_20261005_V1.json --run-dir /home/xflops/coin-state/cta-independent-reproduction --output reports/fast_research/CTA_INDEPENDENT_REPRODUCTION.json',
        '```']
    with a.document.open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    print(json.dumps(dict(status=accepted['status'],complete=accepted['complete_accounts'],stopped=accepted['stopped_accounts'],best=accepted['base_pct_descriptive_ranking'][:3])))

if __name__=='__main__':main()
