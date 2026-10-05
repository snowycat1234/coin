"""Accept fixed4h economics and maintain only the current module checkpoint."""
import argparse,hashlib,json,os,shutil,subprocess
from datetime import UTC,datetime
from pathlib import Path
from quant.paths import ROOT,STATE
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
PARENT='72e1a8b7102dba864e2b34178c93cda7a0bf5c20'
PREFIX='SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1'
BIND='reports/GITHUB_SPOT_FOUR_HOUR_SOURCE_BINDING_20261005_V1.json'
GATE='reports/GITHUB_SPOT_FOUR_HOUR_STAGED_GATE_20261005_V1.json'
POST='reports/GITHUB_SPOT_FOUR_HOUR_SYNC_VERIFIED_20261005_V1.json'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
p=argparse.ArgumentParser();p.add_argument('action',choices=['close','post']);p.add_argument('--remote-head');args=p.parse_args()
private=sha(ROOT/'state/dataset_lock.json');assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if args.action=='post':
    b=read(ROOT/BIND);assert git('rev-parse','HEAD')==args.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(b['prior_WIP_preserved'])
    for n,h in b['source_hashes'].items():assert sha(ROOT/n)==h,n
    assert read(ROOT/GATE)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    save(ROOT/POST,dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',git_commit=args.remote_head,remote_commit=args.remote_head,
        parent_commit=PARENT,source_binding_sha256=sha(ROOT/BIND),gate_sha256=sha(ROOT/GATE),task_id=os.environ['COIN_TASK_ID'],
        created_utc=datetime.now(UTC).isoformat(),prior_WIP_preserved=b['prior_WIP_preserved'],worktree_tracked_clean=True))
    print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=args.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
actual=ROOT/'reports/fast_research'/f'{PREFIX}.json';v=read(actual);protocol=ROOT/'protocols'/f'{PREFIX}.json';c=read(protocol)
assert v['status']=='COMPLETE_SPOT_4H_MARKED_COMPARISON_NOT_NATIVE_OR_APR' and v['git_commit']==PARENT and v['protocol_sha256']==sha(protocol)
for n,h in c['source_hashes'].items():assert sha(ROOT/n)==h,n
finance=read(STATE/'d080-spot-financial-independent-20261005-v1/RESULT.json')
target=read(STATE/'d080-actual-target-reference-20261005-v1/RESULT.json')
prior=read(STATE/'d080-prior-daily-reference-20261005-v1/RESULT.json')
diag=read(STATE/'d080-spot-saved-diagnostics-20261005-v1/RESULT.json')
turn=read(STATE/'d080-saved-target-turnover-20261005-v1/RESULT.json')
episodes=read(STATE/'d080-saved-signal-episodes-20261005-v1/RESULT.json')
assert finance['status']=='PASS_INDEPENDENT_SAVED_SPOT_WALLETS_NOT_NATIVE_OR_ALPHA_CERTIFICATION'
assert target['status']=='PASS_PRIOR_DAILY_MODULE_COMPATIBILITY'
assert diag['status']=='PASS_SAVED_SPOT_ASSET_MONTH_NET_AND_COST_BRIDGES'
assert all(x['input_sha256']==sha(actual) for x in (finance,diag,turn,episodes))
assert target['actual_target_reference']['input_sha256']==sha(actual)
assert target['current_source_sha256']==sha(ROOT/'scripts/investment/public_sma_perpetual.py')
assert len(v['cases'])==len(v['comparisons'])==len(v['reference_comparisons'])==2
assert v['target_artifact']['rows']==3636 and v['signal_interval_minutes']==240 and v['risk_interval_minutes']==1440
for account,f in zip(v['cases'],finance['cases'],strict=True):
    assert account['id']==f['id'] and account['risk']['observed_caps_ok'] and account['config']['discretionary_rebalance_min_notional']==0
    assert f['full_saved_minute_risk']['rows']==436320 and f['full_saved_minute_risk']['gross_above_cap_rows']==f['full_saved_minute_risk']['any_asset_above_cap_rows']==0
    assert not account['terminal_cash_realized'] and account['liquidated_return']=='NOT_EVALUABLE' and 0<account['terminal_marked_inventory_USDT']<.01
assert v['owned_bytes']<=c['budget']['owned_bytes'] and v['elapsed_seconds']<=c['budget']['wall_seconds']
adopt=all(x['net_delta_USDT']>0 and x['challenger_daily_vol']<=x['control_daily_vol'] and x['challenger_minute_MDD']<=x['control_minute_MDD'] for x in v['comparisons'])
assert not adopt
dest=ROOT/'docs/archive/SPOT_FOUR_HOUR_USED_METADATA_20261005_V1';dest.mkdir()
for n,value in [('FINANCIAL_RESULT.json',finance),('TARGET_RESULT.json',target),('PRIOR_DAILY_RESULT.json',prior),('DIAGNOSTIC_RESULT.json',diag),('TURNOVER_RESULT.json',turn),('SIGNAL_EPISODES_RESULT.json',episodes)]:save(dest/n,value)
for n in ['d080_prepare.py','d080_reference.py','d080_turnover.py','d080_signal_episodes.py','d080_source_review.md']:shutil.copyfile(ROOT/'.cache'/n,dest/n)
for n in ['used_public_target_2581b7b8.py','used_reference.py']:shutil.copyfile(STATE/'d080-prior-daily-reference-20261005-v1'/n,dest/n)
shutil.copyfile(STATE/'d080-fixtures-20261005-v1.xml',ROOT/'reports/SPOT_FOUR_HOUR_TESTS_20261005_V1.xml')
assert sha(dest/'used_public_target_2581b7b8.py')==prior['current_source_sha256']
roles={'primary':v['task_id'],'fixture':'fb20a1428e524c3caa3e5e859cb7ff38','prior':'a629c2b88ae34f12992fde3d4ee7bceb',
    'target':'979e505eada9446c94b1435a544dfed1','prepare':'3d2fd11df4294806959a1738187a8662','turnover':turn['task_id'],'episodes':episodes['task_id']}
all_tasks=[read(p) for p in (STATE/'task-progress').glob('task-*.json')]
for role,title in [('finance','独立金额核验4小时钱包'),('diagnostics','4小时组合保存损益与时间诊断')]:
    matched=[t for t in all_tasks if t['title']==title];assert len(matched)==1;roles[role]=matched[0]['id']
tasks={}
for role,identity in roles.items():
    t=read(STATE/'task-progress'/('task-'+identity+'.json'));assert t['ended_at'] and t['exit_code']==0 and t['status']=='completed'
    tasks[role]=t;save(dest/('task-'+identity+'.json'),t)
live=[]
for path in Path('/proc').iterdir():
    if not path.name.isdecimal():continue
    try:
        argv=[x.decode() for x in (path/'cmdline').read_bytes().split(b'\0') if x]
        if len(argv)==5 and argv[0]==str(ROOT/'.venv/bin/python') and argv[1:3]==['-u','-m'] and argv[3] in ('quant.microstructure','quant.collector_public_v3'):
            cg=(path/'cgroup').read_text();assert 'coin-quant.slice' in cg;live.append(dict(pid=int(path.name),argv=argv,cgroup=cg.strip()))
    except (OSError,UnicodeError):pass
assert len(live)==2
summary=('D080正常N资产接口新增显式240min信号/独立200日资格与过去30日日风险，原1440默认与Git72e1a8b逐字段一致；'
 'HOLD10日target前向携带，EXIT10/R20原hook+COIN退出在4h上，整组合4h刷新，一个共享10k钱包。'
 '两成本303日真实回放：基础net642.13 vs日组合630.73多11.40，压力562.38 vs609.23少46.84；'
 'gross多141.34/139.68而费用执行多129.94/186.53，分钟DD7.997%/8.143%高于6.823%/6.862%，日vol7.849%/7.844%稍低。'
 '交易899/895 vs337，换手9.814/9.765 vs2.593/2.589；不采用4h当前配方，保留日线防御组合/HOLD8，投资NONE/CASH。'
 '约78%新总成本在信号component变化，重复intraday同target成本仅14.65/20.99（约8%），不是主要压力缺口；'
 '40完整component片段median96h/无<24h，不编造高频whipsaw，也不把片段当独立账户。'
 '3636目标scalar信号/centered日cov/手mix误差<6e-17；4008缓存4hOHLCV独立归约、1794成交Decimal/872640分钟/606日核账通过。'
 '旧测试7pass当时2581源码/当前ac19的两描述字段修订分别绑定，当前reference实跑通过，不冒用旧绿测。'
 '正残仓0.001065/0.000420USDT保留，liquidated return NE；缺组件资格不同整体STOP，未证明native/连续分钟风险/独立OOS/APR。'
 '主69.65s/RSS740.08MB/共享采样1.192GB，新owned27.43MB；整盘28.651GB@2026-10-05T04:26:47.474579Z（工件前）。'
 '本版不支持更快必然更好或重复调仓为主要失败机制。下一只一个COIN日SMA200宏观入场过滤对照，保留4h通道20/exit10/执行、过去日risk/成本/caps；'
 '比较本次4h控制，检验短趋势入场与费用失效，不改退出减仓、不搜周期网格；尚未实施/启动。'
 '暂停未过滤4h采用，reopen仅该明确macrofilter新证据或独立窗口，不永久删除方向。N/signed/十币/现货库存及40GB/5GB/swap0/GPU0/locked资金权限保持。')
doc='# D080：4小时信号、日线风险与真实成本对照\n\n'+summary+'\n\n## 同产品真实经济结果\n\nBinance Spot价格配用户Bybit VIP0费用是跨场所代理；303已见开发日/完整10k/abs30%与gross60%。不做原生/稳定APR声明。\n\n'
doc+='| 指标 | 日线BASE | 4h BASE | 日线STRESS | 4h STRESS |\n|---|---:|---:|---:|---:|\n'
ctrl=read(c['spot_control']['path']);columns=[ctrl['cases'][0],v['cases'][0],ctrl['cases'][1],v['cases'][1]]
for label,fn in [('marked净USDT',lambda x:x['summary']['final_nav']-10000),('成本加回gross诊断',lambda x:x['summary']['gross_pnl_before_costs']),('费用USDT',lambda x:x['summary']['fees']),('执行成本USDT',lambda x:x['summary']['execution_costs']),('日收益年化波动%',lambda x:100*x['summary']['annual_volatility']),('日MDD%',lambda x:100*x['summary']['max_drawdown']),('分钟MDD%',lambda x:100*x['risk']['minute_max_drawdown']),('成交数',lambda x:x['summary']['trade_count']),('换手/完整本金',lambda x:x['turnover_over_full_initial_capital']),('平均gross/net%',lambda x:100*x['risk']['minute_mean_gross_weight']),('峰gross/net%',lambda x:100*x['risk']['minute_max_gross_weight']),('峰单币%',lambda x:100*x['risk']['minute_max_asset_weight'])]:doc+='| '+label+' | '+' | '.join(f'{fn(x):.6f}' for x in columns)+' |\n'
doc+='\nHOLD8额外参照净633.094422/618.402147；新4h分别多9.033134/少56.021186USDT。旧两币/十币/多空能力和负结果保留，不将本次long-flat配方推广为平台永久方向限制。\n\n## 钱赚亏在哪里\n\n'
for case in diag['cases']['BLEND']:
    doc+=case['id']+'资产净贡献：'+ '；'.join(f"{x['symbol']}净{x['net_USDT']:.6f}/成本{x['fees_USDT']+x['execution_USDT']:.6f}USDT" for x in case['assets'])+'。\n\n'
for pair in diag['pairs']:doc+=pair['cost_id']+'三连续101日真实NAV净增量：'+', '.join(f'{x:.6f}' for x in pair['continuous_block_net_deltas_USDT'])+'USDT。并非三份重置资金；排序反转不是稳定优势。\n\n'
doc+='| 成本情景 | 实际目标意图 | 成交数 | 名义USDT | 费用+执行USDT |\n|---|---|---:|---:|---:|\n'
for case in turn['cases']:
    for reason,z in case['groups'].items():doc+=f"| {case['id']} | {reason} | {z['trades']} | {z['notional_USDT']:.6f} | {z['fee_USDT']+z['execution_USDT']:.6f} |\n"
doc+='''
信号变化时的全部组合成交是实际目标意图分组；不能把整笔平仓PnL归因某原因，也不能删除这些cost保留原gross。同目标重复成交不保证可免费删除：需要风险、真实库存和partial状态。其14.65/20.99成本即使全假想节省也不是主要压力缺口，故不直接重开重复调仓门槛网格。组件40闭合信号片段中BTC21/ETH19，median均96h、<24h均0、<48h分别2/4，BTC末片段右删失。不宣称快速whipsaw已经证明，也不视其为真实独立账户贡献。

## 活动接口与因果

正常public_sma_perpetual.fixed_targets新增signal_interval_minutes=1440默认、240显式与risk_bars。240要求200连续信号bar及独立200连续日bar：决策d风险结束日floor(d/DAY)*DAY，全部available<=d，最近31日close产生30日returns，centered sample covariance×365、原10%只下缩。缺口/迟到重置该信号并flat；blend两组件资格不一致直接STOP整比较，不声称一般缺失组合flatten已完成。N身份与协方差顺序一致，不重建平台。Donchian复用登记MIT原prior20通道/SMA200入场，COINprior10退出/R20再入场；本版周期200×4h约33日，HOLD日risk权重前向携带。目标刷新包含HOLD重复再平衡，因此变动是信号跨度+组合执行cadence，不是signal-only或相同实际风险alpha。

已接受36月Spot源SHA保持；仅多读既有July BTC/ETH两个暖期月，不新增下载或私有lock解析。July+August共3724h暖bar，原minute缓存继续执行/mark，原daily缓存日risk。归约逐block240分钟、first/last/available完整、OHLCV按首高低末和；warm/scoring不删日期、不补收益或资金费。换成4h完整bars建立决策资格而非日线bar冒充4h时钟。原received-asset fee/5minute退出/min10/quantity1e-8研究profile/容量/迟延/caps/完整资本不变，band0。

## 必要验收与局限

7fixtures通过/24.21s，覆盖N3/reverse顺序、200signal/200daily双暖、intraday日cov常量与独立Gram、未来未完成日价扰动、late日线flat、信号和日risk缺口/reset、独立dailyrisk必需。原fixture/prior运行绑定当时2581源码；后来只改240等待时钟的两描述字段，精确旧bytes/SHA保留并说明重建来源。当前ac19源码增强reference新实际运行5.441823s/RSS460.71MB，原日默认3allocation/各18target与Git72e1a8b所有旧meta逐字段一致，当前240描述字段通过；不重复整个旧测试集。

真实3636目标由独立scalar prior20/SMA200、持有prior10低退出/下一4h才再入场、每日centeredGram、manual .5日HOLD+.5四小时Donchian核对；max target误差2.78e-17、sigma5.55e-17/raw0。4008个缓存minute×240 reshape独立OHLCV块一致，volume累加顺序误差9.313e-10在事前rtol1e-12/atol1e-10内；July暖期仍依已接受原SHA/QA，不冒充fresh全源QA。独立Decimal60无producer账户import核1794成交/606日及872640分钟cash/basefee/USDTfee/exec/NAV；费用一次扣、点差已进fill不再次debit。全minute-close无caps违规，不认证盘中尖峰或连续漂移减仓实现。marked与cash清仓分别评价，正dust不归零，清仓收益NOT_EVALUABLE。诊断旧通用输出键HOLD8本次实际是spot_control日线组合，当前报告明确该映射，不冒充HOLD8重新回放。

主任务69.645563s（不含进程启动/import外层等待）、RSS740081664B、共享采样1192181760B、新owned27431466B；disk_before28650749911B在2026-10-05T04:26:47.474579Z，早于工件增长。不使用GPU/swap/keys/orders/paid/newAPI/locked；两采集关闭验收时动态实际进程确认，仅证明当时存活，不伪称72h前向资格。全部必要任务真实exit0。参考/诊断不是新市场样本。

## 采用与下一选择

事前双成本net改善且vol/分钟DD不恶化标准失败：基础略好但压力净差/两个DD均高，未过滤4h配方不采用。保留原Spot日线防御组合与HOLD8收益/风险参照，投资NONE/CASH/长期APR未建立；已看历史不改unseen，不搜索周期/权重/阈值，不按资产收益改池。旧D079及以前按原Git源码/协议/工件复现。

下一主任务由本次信号变化成本主导选择：只一个COIN宏观入场过滤假设，将4h Donchian入场SMA200从200个4h改为200个已完成日，保持4h通道20/退出10、4h执行、日risk/成本/10k/caps，完整新钱包对照当前未过滤4h。问题是较短趋势入场是否产生高成本且跨月份不稳的参与；这还未被证明。无需关闭任何必要退出/减仓，不声明过滤必赚钱，不做周期网格；两成本risk与net核后自行采用/暂停。尚未实现或启动，未声称后台任务。该有限单因素实验是4h方向reopen condition；无证据继续保留日线主力，不永久删除微观/ML/多空/十币能力。

## 可复现

使用本版Git、原受SHA绑定缓存和独占新STATE/output；不覆盖历史工件。

```bash
scripts/with_task_progress.sh --title '4h日风险完整回放' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_ACCOUNT_DIRECTORY --output reports/fast_research/NEW_RESULT.json
scripts/with_task_progress.sh --title '独立金额' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/NEW_RESULT.json --output /home/xflops/coin-state/NEW_FINANCE_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立4h信号与日风险' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_FOUR_HOUR_USED_METADATA_20261005_V1/d080_reference.py --input reports/fast_research/NEW_RESULT.json --output-dir /home/xflops/coin-state/NEW_TARGET_DIRECTORY
```
'''
with (ROOT/'docs/SPOT_FOUR_HOUR_DAILY_RISK_20261005.md').open('x') as f:f.write(doc)
for n in ['README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md']:
    path=ROOT/n;head,body=path.read_text().split('\n',1);path.write_text(head+'\n\n'+summary+'\n\n### D079及以前历史状态（旧下一步按原时点阅读）\n'+body)
for n in ['docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','AGENTS.md']:
    with (ROOT/n).open('a') as f:f.write('\n## D080四小时信号与日风险完成、当前配方不采用\n\n'+summary+'\n')
report=ROOT/'reports/SPOT_FOUR_HOUR_ACCEPTED_20261005_V1.json'
save(report,dict(status='ACTUAL_FOUR_HOUR_CAPABILITY_ACCEPTED_RECIPE_NOT_ADOPTED',parent_commit=PARENT,task_id=os.environ['COIN_TASK_ID'],result_sha256=sha(actual),
 protocol_sha256=sha(protocol),financial=finance,targets=target,prior_daily=prior,diagnostics=diag,turnover=turn,episodes=episodes,
 actual_closed_tasks=tasks,live_collectors=live,resources=resources.status(),candidate='NONE',investment='CASH',development_adopted=False,
 liquidated_return='NOT_EVALUABLE',next_experiment_started=False))
event=dict.fromkeys(FIELDS);event.update(event_id='D080:ACCEPTED',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id=c['experiment_id'],git_commit=PARENT,
 model_family='SPOT_FOUR_HOUR_SIGNAL_DAILY_RISK_FIXED_BLEND',fits=0,success_failure='BASE_NET_POSITIVE_STRESS_NET_NEGATIVE_DD_HIGHER_NOT_ADOPTED',artifact_path=report.relative_to(ROOT).as_posix(),artifact_sha256=sha(report),
 reason_for_next_experiment='Signal-state turnover dominates, test one daily macro entry filter without changing necessary exit/risk',result_influenced_later_choice=True)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
ledger=v['disk_before'];tmp=STATE/'d080-spot-four-hour-20261005-v1/last-disk-publication.tmp'
tmp.write_text(json.dumps(dict(ledger=ledger,measured_at=datetime.fromisoformat(ledger['measured_utc']).timestamp(),source='D080 actual pre-replay full scan before owned artifacts; publication only')));tmp.replace(STATE/'task-progress/last-disk.json')
lastproof=ROOT/'reports/GITHUB_SPOT_DISCRETIONARY_BAND_SYNC_VERIFIED_20261005_V1.json';wip=read(lastproof)['prior_WIP_preserved'];assert len(wip)==36
selected={'README.md','AGENTS.md','scripts/investment/public_sma_perpetual.py','scripts/investment/donchian_daily_pool_target.py','scripts/investment/hold_donchian_blend_target.py',
 'scripts/investment/spot_perpetual_product_comparison.py','tests/test_four_hour_signal_daily_risk.py','protocols/'+PREFIX+'.json','reports/fast_research/'+PREFIX+'.json',
 'reports/SPOT_FOUR_HOUR_ACCEPTED_20261005_V1.json','reports/SPOT_FOUR_HOUR_TESTS_20261005_V1.xml','docs/SPOT_FOUR_HOUR_DAILY_RISK_20261005.md',
 'docs/archive/SPOT_FOUR_HOUR_CLOSE_SOURCE_20261005_V1.py','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md',
 'docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl',lastproof.relative_to(ROOT).as_posix()}
selected.update(x.relative_to(ROOT).as_posix() for x in dest.iterdir());assert not selected.intersection(wip)
save(ROOT/BIND,dict(status='D080_ACTUAL_FOUR_HOUR_CAPABILITY_AND_COST_RISK_RESULT_ACCEPTED',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
 selected_module_paths=sorted(selected),source_hashes={n:sha(ROOT/n) for n in sorted(selected)},prior_WIP_preserved=wip,private_SHA_only=private,private_body_read=False,
 development_adopted=False,candidate='NONE',investment='CASH'))
print(json.dumps(dict(status='D080_ACCEPTED_RECIPE_NOT_ADOPTED',paths=len(selected),net_deltas=[x['net_delta_USDT'] for x in v['comparisons']])))
