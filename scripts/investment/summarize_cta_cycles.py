"""Thin read-only join of two cost tasks; never joins independent wallets."""
import argparse,json
from datetime import datetime,UTC
from pathlib import Path
import numpy as np
import polars as pl
from quant.paths import ROOT,STATE
from scripts.investment.run_cta_leaderboard import sha,write,stamp
from scripts.investment.turtle_turnover_diagnostic import asset_attribution

PERIODS=(('SEP_NOV',stamp('2024-09-01'),stamp('2024-12-01')),
         ('DEC_FEB',stamp('2024-12-01'),stamp('2025-03-01')),
         ('MAR_JUN',stamp('2025-03-01'),stamp('2025-07-01')))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--actual',type=Path,action='append',required=True)
    for k in ('output','document'):ap.add_argument('--'+k,type=Path,required=True)
    a=ap.parse_args();assert len(a.actual)==2 and not a.output.exists() and not a.document.exists()
    inputs=[];tasks=[];rows=[];identities=set();source=None;common_protocol=None
    for path in a.actual:
        r=json.loads(path.read_bytes());assert r['status']=='COMPLETE_FROZEN_CTA_10_ACTUAL_ACCOUNTS_OR_EXPLICIT_HALTS'
        assert len(r['cases'])==r['required_accounts']==10 and r['actual_days']==303 and r['models_fit']==r['search_configurations']==0
        assert r['protocol']['families']==['DONCHIAN20_10'] and r['protocol']['economics_start']=='2024-09-01'
        assert r['protocol']['economics_end_exclusive']=='2025-07-01'
        common={k:r['protocol'][k] for k in ('symbols','data_manifest','locked_sha256','preparation_start',
            'economics_start','economics_end_exclusive','rules','cost','resources')}
        if common_protocol is not None:assert common==common_protocol,'Same inputs, financial caps and fixed rules across cost tasks'
        common_protocol=common
        assert common['resources']['capital_USDT']==10000 and common['resources']['abs_asset_cap']==.3 and common['resources']['gross_cap']==.6
        assert r['signal_reference']['status'].startswith('PASS')
        if source is not None:assert r['binding']['source_hashes']==source
        source=r['binding']['source_hashes']
        for p,h in source.items():assert sha(ROOT/p)==h
        taskpath=STATE/'task-progress'/('task-'+r['binding']['task_id']+'.json')
        t=json.loads(taskpath.read_bytes());assert t['status']=='completed' and t['exit_code']==0
        tasks.append(t);inputs.append(dict(path=str(path),sha256=sha(path),binding=r['binding'],
            elapsed_seconds=r['elapsed_seconds'],peak_RSS_bytes=r['peak_RSS_bytes'],
            shared_RAM_sampled_peak_bytes=r['shared_RAM_sampled_peak_bytes'],owned_bytes=r['owned_bytes'],
            disk_before=r['disk_before'],task_sha256=sha(taskpath)))
        for c in r['cases']:
            key=(c['strategy'],c['mode'],c['cost'],c['unit']);assert key not in identities;identities.add(key)
            for art in c['artifacts'].values():assert sha(art['path'])==art['sha256']
            s=c['summary'];checked=c['independent'];complete=s['completed_minutes']==s['required_minutes']
            assert s['symbols']==r['protocol']['symbols'] and s['cost_scenario']['id']==c['cost'] and s['unit_scenario']['id']==c['unit']
            assert s['cost_scenario']['provenance']['fee_source_sha256']=='a406d4bd0e47ff4ae4895fda0a2f2698b5763667d82b22b7f264d6220e27e8bd'
            assert s['required_minutes']==303*1440 and checked['minutes']==s['completed_minutes']
            assert checked['status'].startswith('PASS') and checked['target_reference']['status'].startswith('PASS')
            assert abs(s['gross_PnL_same_quantities']-s['fees_USDT']-s['execution_cost_USDT']+s['funding_USDT']-s['net_PnL'])<1e-7
            assert abs(sum(v['net'] for v in checked['by_past_regime'].values())-s['net_PnL'])<1e-7
            if c['mode']=='LONG_ONLY':assert abs(s['long_short_marked_contribution']['SHORT']['net_contribution'])<1e-7
            if c['mode']=='SHORT_ONLY':assert abs(s['long_short_marked_contribution']['LONG']['net_contribution'])<1e-7
            trades=json.loads(Path(c['artifacts']['trades.json']['path']).read_bytes())
            funding=json.loads(Path(c['artifacts']['funding.json']['path']).read_bytes())
            assets=asset_attribution(trades,funding,s)
            minute=pl.read_parquet(c['artifacts']['minute_nav_inventory.parquet']['path'])
            periods=[]
            for name,start,end in PERIODS:
                f=minute.filter((pl.col('close_us')>start)&(pl.col('close_us')<=end))
                days=[v for v in checked['daily_direction_contributions'] if start<v['day_end_us']<=end]
                full=f.height==(end-start)//60_000_000
                if full:
                    previous=10000. if start==PERIODS[0][1] else float(minute.filter(pl.col('close_us')==start)['nav'][0])
                    nav=np.r_[previous,f['nav'].to_numpy()]
                    net=float(nav[-1]-previous);direction={label:sum(v[label] for v in days) for label in ('LONG','SHORT')}
                    assert abs(sum(direction.values())-net)<1e-7
                    daily_nav=f.filter(pl.col('close_us')%86_400_000_000==0)['nav'].to_numpy()
                    ret=np.diff(np.r_[previous,daily_nav])/np.r_[previous,daily_nav[:-1]]
                    periods.append(dict(id=name,days=len(days),net_USDT=net,**direction,
                        conditional_DD=float(np.max(1-nav/np.maximum.accumulate(nav))),
                        actual_vol=float(np.std(ret,ddof=1)*np.sqrt(365)),
                        mean_gross=float(f['gross_weight'].mean()),mean_net=float(f['net_signed_weight'].mean()),
                        scope='SAME_CONTINUOUS_WALLET_CONTRIBUTION_NOT_FRESH_FUNDED_SUBACCOUNT'))
                else:periods.append(dict(id=name,days=len(days),net_USDT=None,scope='NOT_EVALUABLE_INCOMPLETE_NO_ZERO_AFTER_HALT'))
            dm=s['daily_metrics'] or {};ex=s.get('realized_exposure',{})
            rows.append(dict(id=c['id'],strategy=c['strategy'],mode=c['mode'],cost=c['cost'],unit=c['unit'],complete=complete,
                completed_minutes=s['completed_minutes'],stop_us=s['stop_us'],completion=s['completion'],
                net_USDT=s['net_PnL'] if complete else None,stopped_prefix_net_USDT=s['net_PnL'] if not complete else None,
                gross_USDT=s['gross_PnL_same_quantities'],fees_USDT=s['fees_USDT'],execution_USDT=s['execution_cost_USDT'],
                spread_USDT=s['spread_cost_USDT'],slippage_USDT=s['slippage_cost_USDT'],funding_USDT=s['funding_USDT'],
                LONG=s['long_short_marked_contribution']['LONG']['net_contribution'],SHORT=s['long_short_marked_contribution']['SHORT']['net_contribution'],CASH=0.,
                vol=dm.get('annual_volatility'),DD=s.get('minute_max_drawdown'),Sharpe=dm.get('sharpe') if c['strategy']!='CASH' else None,
                turnover=s.get('normalized_total_turnover'),risk=ex,residual=s['terminal_marked_notional'],paid_flat=s['terminal_cash_realized'],
                asset_attribution=assets,periods=periods,by_past_regime=checked['by_past_regime'],
                concentration=s.get('daily_net_gain_concentration'),artifact_directory=str(Path(c['artifacts']['trades.json']['path']).parent)))
            del minute
    expected={(f,m,c,u) for f,m in [('DONCHIAN20_10',m) for m in ('LONG_ONLY','SHORT_ONLY','LONG_SHORT')]+[('CASH','CASH'),('HOLD','LONG_ONLY')]
        for c in ('BASE27','STRESS43') for u in ('RAW_AS_FRACTION','RAW_AS_PERCENT')}
    assert identities==expected
    pairs=[]
    for cost in ('BASE27','STRESS43'):
        for unit in ('RAW_AS_FRACTION','RAW_AS_PERCENT'):
            choose=lambda mode:next(v for v in rows if v['strategy']=='DONCHIAN20_10' and v['mode']==mode and v['cost']==cost and v['unit']==unit)
            lo=choose('LONG_ONLY');ls=choose('LONG_SHORT');sh=choose('SHORT_ONLY');full=lo['complete'] and ls['complete']
            pairs.append(dict(cost=cost,unit=unit,full_pair=full,
                incremental_net_USDT=ls['net_USDT']-lo['net_USDT'] if full else None,
                DD_delta=ls['DD']-lo['DD'] if full else None,vol_delta=ls['vol']-lo['vol'] if full else None,
                changed_LONG=ls['LONG']-lo['LONG'] if full else None,actual_LS_SHORT=ls['SHORT'],
                actual_LS_SHORT_scope='FULL303D' if ls['complete'] else 'STOPPED_PREFIX_NOT_COMPARABLE',SHORT_ONLY=sh['net_USDT'],
                scope='POLICY_DIRECTION_PLUS_SIGNED_COV_AND_SHARED_CAPITAL_COMPETITION_NOT_RISK_MATCHED_SHORT_ALPHA'))
    intervals=sorted((t['started_at'],t['ended_at']) for t in tasks);merged=[]
    for x,y in intervals:
        if merged and x<=merged[-1][1]:merged[-1][1]=max(y,merged[-1][1])
        else:merged.append([x,y])
    result=dict(status='ACCEPTED_FIXED_DONCHIAN_303D_TWO_COST_TASKS_NO_WALLET_JOIN',inputs=inputs,
        tasks=tasks,rows=rows,paired_direction=pairs,complete_accounts=sum(v['complete'] for v in rows),
        stopped_accounts=sum(not v['complete'] for v in rows),actual_days=303,initial_capital_per_counterfactual_USDT=10000,
        models_fit=0,parameter_search=0,orders_sent=0,locked_consumed=False,
        task_intervals_union_seconds=sum(y-x for x,y in merged),sampled_shared_peak_bytes=max(v['shared_RAM_sampled_peak_bytes'] for v in inputs),
        max_process_RSS_bytes=max(v['peak_RSS_bytes'] for v in inputs),owned_bytes=sum(v['owned_bytes'] for v in inputs),
        data_role='SEEN_DEVELOPMENT_OVERLAPS_D091_NOT_INDEPENDENT_FULL_MARKET_CYCLE',
        qualified_investment='NONE/CASH',long_term_APR='NOT_EVALUABLE',
        source_hashes=source,diagnostic_source_sha256=sha(__file__),created_utc=datetime.now(UTC).isoformat())
    write(a.output,result)
    fmt=lambda x,scale=1:'NOT_EVALUABLE' if x is None else f'{x*scale:.2f}'
    lines=['# 固定Donchian20/10：303日连续方向对照','',
        '已见2024-09-01至2025-07-01，共303日，10币固定历史池、完整10k共享钱包、abs30/gross60/逐仓1x。两个成本任务并行仅用于不同反事实账户，不相加账户。原122日结果仍为不同起点的独立回测工件，不能拼接或声称本窗unseen。','',
        '固定日线前20高低突破、前10退出，过去30日inversevol与signedcov仅降低超过10%年化目标的仓位。开源Jesse通道核与现有财务/分钟执行原入口，无新止损、拟合、阈值或资产收益挑选。BinanceUSD-M配Bybit用户成本是跨场所代理，funding单位UNKNOWN两情景，MMR假设未成为native认证。','',
        '|策略|方向|BASE/PCT净|LONG|SHORT|毛价格|手续费+执行|资金费|vol%|DD%|换手|残仓|','|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    primary=[v for v in rows if v['cost']=='BASE27' and v['unit']=='RAW_AS_PERCENT']
    for v in primary:lines.append('|'+ '|'.join([v['strategy'],v['mode'],fmt(v['net_USDT']),fmt(v['LONG']),fmt(v['SHORT']),fmt(v['gross_USDT']),fmt(v['fees_USDT']+v['execution_USDT']),fmt(v['funding_USDT']),fmt(v['vol'],100),fmt(v['DD'],100),fmt(v['turnover']),fmt(v['residual'])])+'|')
    lines+=['','## 两成本、两未知单位解释配对','',
        '|情景|完整配对|LS-LO净|DD差百分点|vol差百分点|LS内SHORT|仅空净|','|---|---|---:|---:|---:|---:|---:|']
    for v in pairs:lines.append('|'+ '|'.join([v['cost']+'/'+v['unit'],str(v['full_pair']),fmt(v['incremental_net_USDT']),fmt(v['DD_delta'],100),fmt(v['vol_delta'],100),fmt(v['actual_LS_SHORT']),fmt(v['SHORT_ONLY'])])+'|')
    lines+=['','## 同一连续钱包的预定日历段（BASE/PCT）','',
        '|策略|方向|日期段|完整日数|净USDT|LONG|SHORT|vol%|DD%|mean gross%|','|---|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for v in primary:
        for p in v['periods']:lines.append('|'+ '|'.join([v['strategy'],v['mode'],p['id'],str(p['days']),fmt(p['net_USDT']),fmt(p.get('LONG')),fmt(p.get('SHORT')),fmt(p.get('actual_vol'),100),fmt(p.get('conditional_DD'),100),fmt(p.get('mean_gross'),100)])+'|')
    lines+=['','日历段不是事后择日或未来牛熊标签；起点资本为连续账户当时NAV，没有重新投入10k。过去BTC状态归因仅描述，结构化工件保留。same caps不等于risk matched；LS内short与独立SO账户不同。停止保持前缀，完整净指标NOT_EVALUABLE；残仓包含真实mark，非付费平仓的liquidated return不可评价。','',
        '## 资源与复现','',f"20账户完整任务区间并集{result['task_intervals_union_seconds']:.2f}秒；采样共享RAM峰值{result['sampled_shared_peak_bytes']/1e9:.3f}GB；最大进程RSS{result['max_process_RSS_bytes']/1e9:.3f}GB；新工件{result['owned_bytes']/1e9:.3f}GB；GPU0。不是两个任务耗时相加；未单独计时的阶段UNKNOWN。",'',
        '原规则测试按精确sourceSHA复用；本次每个账户都运行独立目标/逐分钟NAV/钱包/funding/方向参考验收，不以旧绿测替代303日入口。','',
        '```bash','for cost in BASE27 STRESS43; do',
        '  scripts/with_task_progress.sh --title "Donchian303日 $cost" -- env OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_cta_leaderboard.py --protocol protocols/CTA_DONCHIAN_303D_${cost}_20261005_V1.json --run-dir /home/xflops/coin-state/<fresh-${cost}-run> --output reports/fast_research/<fresh-${cost}-result>.json',
        'done','```','']
    with a.document.open('x',encoding='utf-8') as f:f.write('\n'.join(lines))
    print(json.dumps(dict(status=result['status'],complete=result['complete_accounts'],stopped=result['stopped_accounts'],pairs=pairs)))

if __name__=='__main__':main()
