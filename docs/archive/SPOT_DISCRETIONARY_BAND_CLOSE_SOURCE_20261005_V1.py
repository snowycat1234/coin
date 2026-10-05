"""Accept actual finite band economics, record non-adoption and exact Git binding."""
import argparse,hashlib,json,os,shutil,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
PARENT='6ef22565d61f0771493f2e91a8bf1bc42e00b3d6';PREFIX='SPOT_DISCRETIONARY_BAND50_20261005_V1'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
p=argparse.ArgumentParser();p.add_argument('action',choices=['close','post']);p.add_argument('--remote-head');a=p.parse_args()
proof=ROOT/'reports/GITHUB_SPOT_DISCRETIONARY_BAND_SOURCE_BINDING_20261005_V1.json'
private=sha(ROOT/'state/dataset_lock.json');assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if a.action=='post':
    b=read(proof);assert git('rev-parse','HEAD')==a.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(b['prior_WIP_preserved'])
    for n,h in b['source_hashes'].items():assert sha(ROOT/n)==h,n
    gate=ROOT/'reports/GITHUB_SPOT_DISCRETIONARY_BAND_STAGED_GATE_20261005_V1.json';assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    save(ROOT/'reports/GITHUB_SPOT_DISCRETIONARY_BAND_SYNC_VERIFIED_20261005_V1.json',dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',
        git_commit=a.remote_head,remote_commit=a.remote_head,parent_commit=PARENT,source_binding_sha256=sha(proof),gate_sha256=sha(gate),
        task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),prior_WIP_preserved=b['prior_WIP_preserved'],worktree_tracked_clean=True))
    print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=a.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
actual=ROOT/'reports/fast_research'/f'{PREFIX}.json';v=read(actual);protocol=ROOT/'protocols'/f'{PREFIX}.json';c=read(protocol)
assert v['status']=='COMPLETE_SPOT_BAND_MARKED_COMPARISON_NOT_NATIVE_OR_APR' and v['git_commit']==PARENT and v['protocol_sha256']==sha(protocol)
for n,h in c['source_hashes'].items():assert sha(ROOT/n)==h,n
finance=read(STATE/'d079-spot-financial-independent-20261005-v1/RESULT.json')
target=read(STATE/'d079-target-independent-20261005-v1/RESULT.json')
band=read(STATE/'d079-band-independent-20261005-v1/RESULT.json')
diag=read(STATE/'d079-spot-saved-diagnostics-20261005-v1/RESULT.json')
assert finance['status']=='PASS_INDEPENDENT_SAVED_SPOT_WALLETS_NOT_NATIVE_OR_ALPHA_CERTIFICATION'
assert target['status']=='PASS_SAVED_COMPONENT_BLEND_PAST_COVARIANCE_AND_FUTURE_BAR_PERTURBATION'
assert band['status']=='PASS_UNCHANGED_TARGETS_EXPLICIT_PROTECTION_AND_NO_FILL_BAND_ORDERS'
assert diag['status']=='PASS_SAVED_SPOT_ASSET_MONTH_NET_AND_COST_BRIDGES'
assert all(x['input_sha256']==sha(actual) for x in (finance,target,band,diag))
assert target['future_perturbation_early_target_max_error']==target['manual_component_mix_max_error']==0
assert target['later_target_rows_actually_changed']>0 and band['target_rows_checked']==606
assert len(v['cases'])==len(v['comparisons'])==len(v['reference_comparisons'])==2
for account,f,b in zip(v['cases'],finance['cases'],band['cases'],strict=True):
    assert account['id']==f['id']==b['id'] and account['risk']['observed_caps_ok']
    assert f['full_saved_minute_risk']['rows']==436320 and f['full_saved_minute_risk']['gross_above_cap_rows']==f['full_saved_minute_risk']['any_asset_above_cap_rows']==0
    assert account['config']['discretionary_rebalance_min_notional']==50 and account['summary']['trade_count']==b['actual_fills']
    assert not account['terminal_cash_realized'] and account['liquidated_return']=='NOT_EVALUABLE' and 0<account['terminal_marked_inventory_USDT']<.01
assert v['owned_bytes']<=c['budget']['owned_bytes'] and v['elapsed_seconds']<=c['budget']['wall_seconds']
adopt=all(x['net_delta_USDT']>0 and x['challenger_daily_vol']<=x['control_daily_vol'] and
          x['challenger_minute_MDD']<=x['control_minute_MDD'] for x in v['comparisons'])
assert not adopt and all(x['net_delta_USDT']<0 for x in v['comparisons'])
dest=ROOT/'docs/archive/SPOT_DISCRETIONARY_BAND_USED_METADATA_20261005_V1';dest.mkdir()
for n,value in [('FINANCIAL_RESULT.json',finance),('TARGET_RESULT.json',target),('BAND_RESULT.json',band),('DIAGNOSTIC_RESULT.json',diag)]:save(dest/n,value)
for n in ['d079_prepare.py','d079_band_independent.py','d079_source_review.md','d079_test_used_v1.py']:
    shutil.copyfile(ROOT/'.cache'/n,dest/n)
roles={'primary':v['task_id'],'finance':'2bd98912cffc4ce6b5dab50f6f571c98','target':'b885a20c4195472aa98201f0f4de619a',
    'band':band['task_id'],'diagnostic':'5f003f5567254374b67e25552fb9579e',
    'fixture_failed':'f384d5c4e33e404b8df134bd08badb7e','fixture_accepted':'3b94bd6b58314007873407cb42b6e9f5'}
tasks={}
for role,identity in roles.items():
    t=read(STATE/'task-progress'/('task-'+identity+'.json'));assert t['ended_at'] and t['exit_code']==(1 if role=='fixture_failed' else 0)
    assert t['status']==('failed' if role=='fixture_failed' else 'completed');tasks[role]=t;save(dest/('task-'+identity+'.json'),t)
assert sha(dest/'d079_test_used_v1.py')=='33dfc42315fc5e899e919efef03302fb2e933e84385542bbba27e3eb9e7b8d72'
live=[]
for path in Path('/proc').iterdir():
    if not path.name.isdecimal():continue
    try:
        argv=[x.decode() for x in (path/'cmdline').read_bytes().split(b'\0') if x]
        if len(argv)==5 and argv[0]==str(ROOT/'.venv/bin/python') and argv[1:3]==['-u','-m'] and argv[3] in ('quant.microstructure','quant.collector_public_v3'):
            cg=(path/'cgroup').read_text();assert 'coin-quant.slice' in cg;live.append(dict(pid=int(path.name),argv=argv,cgroup=cg.strip()))
    except (OSError,UnicodeError):pass
assert len(live)==2
summary=('D079正常Spot主动调仓门槛默认0，显式50只允许同信号/资格且组件风险target未下降的主动调整；'
    '原入场/信号变化/必要减仓/实际caps/终止/已开始partial保持。真实2共享10k/303日账户，606原目标值不变；'
    '每账户246成交/246拒主动goal，独立核492成交/872640分钟/606日及全部拒单/无费用桥。'
    '基础净626.52 vs原组合630.73少4.21，省费用执行2.26而gross少6.47；压力净605.60 vs609.23少3.62，'
    '省3.26而gross少6.88。日vol8.077%/分钟DD6.676%略降，但事前双成本net提升标准失败，不采用BAND50。'
    '保留原Spot防御组合/HOLD8收益参照和门槛默认关闭能力，投资NONE/CASH/APR NE。'
    '原失败fixture顺序14pass/1fail与旧字节保留，修正仅测试身份后15pass，账户源未变，QUOTE/received默认逐字段同旧Git。'
    '残仓0.000486/0.000299USDT保留，liquidated return NE；无分钟自动漂移减仓/原生/独立OOS认证。'
    '主79.41s/RSS767.59MB/共享采样1.252GB，新STATE26.86MB，整盘实扫28.608GB@2026-10-05T04:01:56.827989Z（工件前）。'
    '停止门槛网格；reopen需新的具体成本或执行证据。下一有限4h信号Donchian挑战者，沿用同Spot价格/成本/共享本金与过去日协方差，'
    '比较现日线防御组合，回答信号节奏是否为主要阻碍；只一个固定配方/两成本，无新池/下载/HPO，尚未启动。'
    '原N/signed/风险caps/资源/锁数据/资金边界保持，两采集验收时实际存活。')
doc='# D079：50USDT主动调仓区间，能力通过但配方不采用\n\n'+summary+'\n\n'
doc+='## 真实净收益与风险\n\n同Spot固定50/50 HOLD10+EXIT10/REENTRY20，所有606原目标值与D078精确相同，只换主动执行区间。对照保存原完整钱包；HOLD8额外参照，两者不重跑、不平均独立NAV。完整本金10k/303已见日，Binance Spot价格配用户Bybit VIP0 10bp/侧费用。\n\n'
doc+='| 指标 | 原组合 BASE | BAND50 BASE | 原组合 STRESS | BAND50 STRESS |\n|---|---:|---:|---:|---:|\n'
ctrl=read(c['spot_control']['path']);cases=[ctrl['cases'][0],v['cases'][0],ctrl['cases'][1],v['cases'][1]]
for label,fn in [('marked净USDT',lambda x:x['summary']['final_nav']-10000),('成本加回gross诊断USDT',lambda x:x['summary']['gross_pnl_before_costs']),
    ('费用USDT',lambda x:x['summary']['fees']),('执行成本USDT',lambda x:x['summary']['execution_costs']),
    ('实际日收益年化波动%',lambda x:100*x['summary']['annual_volatility']),('日终MDD%',lambda x:100*x['summary']['max_drawdown']),
    ('分钟MDD%',lambda x:100*x['risk']['minute_max_drawdown']),('成交数',lambda x:x['summary']['trade_count']),
    ('成交名义/完整本金',lambda x:x['turnover_over_full_initial_capital']),('平均gross/net%',lambda x:100*x['risk']['minute_mean_gross_weight']),
    ('峰gross/net%',lambda x:100*x['risk']['minute_max_gross_weight']),('峰单币%',lambda x:100*x['risk']['minute_max_asset_weight'])]:
    doc+='| '+label+' | '+' | '.join(f'{fn(x):.6f}' for x in cases)+' |\n'
doc+='\n### 损益、原因与时间解释\n\n'
for case in diag['cases']['BLEND']:
    doc+='**'+case['id']+'**资产贡献：'+ '；'.join(f"{x['symbol']}净{x['net_USDT']:.6f}USDT、成本{x['fees_USDT']+x['execution_USDT']:.6f}" for x in case['assets'])+'。\n\n'
    groups={}
    for g in case['trade_groups']:
        r=g['reason'];z=groups.setdefault(r,dict(count=0,notional=0.,cost=0.));z['count']+=g['count'];z['notional']+=g['notional'];z['cost']+=g['fees']+g['execution']
    doc+='| 已保存目标原因 | 成交数 | 名义USDT | 费用+执行USDT |\n|---|---:|---:|---:|\n'
    for r,z in groups.items():doc+=f"| {r} | {z['count']} | {z['notional']:.6f} | {z['cost']:.6f} |\n"
    doc+='\n'
for pair in diag['pairs']:
    doc+=pair['cost_id']+' 三连续101日净增量：'+', '.join(f'{x:.6f}' for x in pair['continuous_block_net_deltas_USDT'])+'USDT；起点为各账户真实当时NAV，不重置/拼接。\n\n'
doc+='''减少91笔成交并没有删除245笔旧小额交易，也没有省下旧小额cost全部9.53USDT。目标执行改变了整个库存路径；本次实际成本只省2.262434/3.259170USDT，价格/实际数量毛损益少6.472615/6.880339，净桥−4.210180/−3.621169。gross为同净收到数量路径成交时成本加回诊断，不是另外的无费用策略。新账户BTC仍贡献主要收益、ETH贡献按真实金额保留，不按结果删币。目标原因是当时策略意图/风险类别，不能把一笔平仓利润全归给原因；第一实际入场可重新标记FIRST_ENTRY，其余以真实target_reason或UNKNOWN汇总。没有声称原因统计证明因果alpha。

## 变化与护栏

正常BacktestConfig新增discretionary_rebalance_min_notional，默认0关闭。开启时只接受显式Boolean discretionary_rebalance/String target_reason，缺失为False/UNKNOWN保护。目标flags仅依赖当前/上一可用组件：首次、资格变化/丢失、任一整个池组件raw向量变化、当前资产任一组件风险target严格下降均不允许skip。实际606flags：INITIAL2/SIGNAL20/RISK292/DISCRETIONARY292。所有原target/raw/时间身份值与D078完全一致。

执行时先遵守原expiry/gap/min-hold/因果，再对当前open价格/NAV及真实base数量计算完整请求，只有严格<50的明确主动goal可不交易。首次真实库存、零目标/终止、risk_forced、当前risk_limited、任何当前asset/gross超cap、已开始partial均豁免；容量截断的小fill不是small-goal。skip写order但无trade/fee/cash/inventory变化，等待下一原目标，不延长退出次数。0门槛保留原字段/数值，实际两费用模式小输入与精确Git6ef2256旧源码所有trades/orders/daily/roundtrips/summary相等；旧源码仅小型独立测试reference，活动实现没有版本/日期AST包装。

## 实际验收、失败与限制

第一次fixtures14pass/1fail：新增另一资产超限反例让BTC先完成减仓，轮到ETH时cap已恢复，错误预期ETH仍豁免。原source/XML/实际exit1保留；只换测试identity为ZZZ，使ETH先处理时其他币仍超cap。第二次15pass/33.59s，账户source8672bcd8保持；反例包括skip不变现金库存、protected小额减仓、自己/其他币caps、首次entry、partial残额继续、zero/terminal、unknown/非法声明、全池signal变化/1e−15风险缩减和旧默认精确一致。未重跑无关旧验收。

实际2新账户一次完整回放。独立Decimal核492成交、872640分钟/606日资金与NAV、fees/execution一次扣款；旧D078组件手动mix/cov/未来OHLC×1.17扰动reference在新目标上实跑通过，早406目标不变/晚106改变。独立band检查不调用活动flag/account：读取受SHA固定原minute open、保存order/trade顺序，逐条重建当时现金/数量/NAV、拒单<50/无fill/未越cap/非started，两个账户各246拒goal和200受保护/已开始fill，末NAV误差0。target值全同旧D078。金融/timing通过不是native/alpha认证。

Spot仍没有连续minute漂移主动减仓调度，不能把本轮band保护冒称新能力；两个全minute-close轨迹均未超abs.3/gross.6。数据缺口/实际caps超限依事前规则停止投资评价。quantity/min10仍历史研究假设，Bybit原生盘口/过滤器未认证。真实正残仓0.000485758/0.000298608USDT保留，marked账户日历完整而现金清仓收益NOT_EVALUABLE。不启封heldout，不使用keys/เงินจริง/交易所订单/API/下载/付费/GPU；维持5GB/swap0/40GB。

主79.405424s、RSS767594496B、共享实际采样1251946496B，新owned26863220B；独立金融0.273243s、target0.551513s、band0.218482s。全ROOT+整个D VHD实扫28607639240B在2026-10-05T04:01:56.827989Z，早于本轮工件与采集增长，不当作结束后的精确总量。8765实际进度和扫描时刻沿用原服务，两采集验收时真实存活；未认证72h/真实有效前向日。两个子agent权限中断后root接手其未完成的小验证，未声称它们完成全部审查，也未重新启动市场任务。

## 采用与下一步

事前要求两成本净提高且波动/minuteDD不恶化。风险略降但净均降低，BAND50不采用；保留正常门槛能力默认关闭、旧防御组合和HOLD8。拒绝网格寻找事后赢家；reopen需新的具体执行/成本证据或独立窗口先验假设，不因这个单窗口删除整个低换手能力方向。投资NONE/CASH、长期APR未建立。

主要阻碍继续是价格参与时机与时间稳定性，成本局部优化不足以解释长时段差距。下一项只选一个固定4h Donchian信号挑战者，复用已登记公开hook和原分钟缓存，完整同Spot账户对照日线防御组合/HOLD8；过去日协方差/总资本/成本/caps不变，日risk与4h信号/分钟执行明确分开。4h改变的是信号信息节奏，事前固定一个配方/两成本，禁止周期网格/按币选择/新数据资格。旧Turtle结果保存，不把这个研究宣称全市场bot水平；若成本/风险/净无有价值增量就保留主力。下一尚未实现或启动，无后台科研承诺。

## 可复现

本模块Git与原协议，原受SHA缓存可用，使用独占新STATE/output。旧D078及以前按各原Git，历史证据不覆盖。

```bash
scripts/with_task_progress.sh --title '50USDT主动调仓' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_DISCRETIONARY_BAND50_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_ACCOUNT_DIRECTORY --output reports/fast_research/NEW_RESULT.json
scripts/with_task_progress.sh --title '独立金额' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_FINANCE_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立目标与拒单' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_DISCRETIONARY_BAND_USED_METADATA_20261005_V1/d079_band_independent.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_BAND_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立过去目标' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_DEFENSIVE_BLEND_USED_METADATA_20261005_V1/d078_target_reference.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_TARGET_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '保存经济诊断' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_saved_economic_diagnostics.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_DIAGNOSTIC_DIRECTORY/RESULT.json
```
'''
with (ROOT/'docs/SPOT_DISCRETIONARY_BAND50_20261005.md').open('x') as f:f.write(doc)
for n in ['README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md']:
    path=ROOT/n;head,body=path.read_text().split('\n',1);path.write_text(head+'\n\n'+summary+'\n\n### D078及以前历史状态（旧下一步按原时点阅读）\n'+body)
for n in ['docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','AGENTS.md']:
    with (ROOT/n).open('a') as f:f.write('\n## D079主动调仓门槛能力与负增量已验收\n\n'+summary+'\n')
report=ROOT/'reports/SPOT_DISCRETIONARY_BAND_ACCEPTED_20261005_V1.json'
save(report,dict(status='ACTUAL_BAND_CAPABILITY_ACCEPTED_RECIPE_NOT_ADOPTED',parent_commit=PARENT,task_id=os.environ['COIN_TASK_ID'],
    result_sha256=sha(actual),protocol_sha256=sha(protocol),financial=finance,targets=target,band_protection=band,diagnostics=diag,
    actual_closed_tasks=tasks,live_collectors=live,resources=resources.status(),candidate='NONE',investment='CASH',
    development_band_adopted=adopt,liquidated_return='NOT_EVALUABLE',next_experiment_started=False))
event=dict.fromkeys(FIELDS);event.update(event_id='D079:ACCEPTED',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id=c['experiment_id'],git_commit=PARENT,
    model_family='NORMAL_SPOT_FIXED_DISCRETIONARY_BAND',fits=0,success_failure='NET_INCREMENT_NEGATIVE_RECIPE_NOT_ADOPTED_CAPABILITY_VALIDATED',
    artifact_path=report.relative_to(ROOT).as_posix(),artifact_sha256=sha(report),reason_for_next_experiment='Cost saving insufficient, one fixed4h signal horizon on same Spot path',result_influenced_later_choice=True)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
ledger=v['disk_before'];tmp=STATE/'d079-spot-band50-20261005-v1/last-disk-publication.tmp'
tmp.write_text(json.dumps(dict(ledger=ledger,measured_at=datetime.fromisoformat(ledger['measured_utc']).timestamp(),source='D079 actual pre-replay scan before owned artifacts; publication only')))
tmp.replace(STATE/'task-progress/last-disk.json')
prior=ROOT/'reports/GITHUB_SPOT_DEFENSIVE_BLEND_SYNC_VERIFIED_20261005_V1.json';wip=read(prior)['prior_WIP_preserved'];assert len(wip)==36
selected={'README.md','AGENTS.md','src/quant/backtest.py','scripts/investment/spot_perpetual_product_comparison.py','scripts/investment/spot_saved_economic_diagnostics.py',
    'tests/test_spot_discretionary_band.py','protocols/'+PREFIX+'.json','reports/fast_research/'+PREFIX+'.json','reports/SPOT_DISCRETIONARY_BAND_ACCEPTED_20261005_V1.json',
    'reports/SPOT_DISCRETIONARY_BAND_TESTS_20261005_V1.xml','reports/SPOT_DISCRETIONARY_BAND_TESTS_20261005_V2.xml',
    'docs/SPOT_DISCRETIONARY_BAND50_20261005.md','docs/archive/SPOT_DISCRETIONARY_BAND_CLOSE_SOURCE_20261005_V1.py',
    'docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md',
    'docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
selected.update(x.relative_to(ROOT).as_posix() for x in dest.iterdir());assert not selected.intersection(wip)
save(proof,dict(status='D079_BAND_CAPABILITY_AND_NEGATIVE_INCREMENT_ACCEPTED',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
    selected_module_paths=sorted(selected),source_hashes={n:sha(ROOT/n) for n in sorted(selected)},prior_WIP_preserved=wip,
    private_SHA_only=private,private_body_read=False,development_band_adopted=False,candidate='NONE',investment='CASH'))
print(json.dumps(dict(status='D079_ACCEPTED_RECIPE_NOT_ADOPTED',paths=len(selected),net_deltas=[x['net_delta_USDT'] for x in v['comparisons']])))
