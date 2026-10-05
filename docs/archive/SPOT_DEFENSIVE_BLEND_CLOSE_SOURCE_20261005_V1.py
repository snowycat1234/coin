"""Close a finite same-product defensive research module; preserve old evidence."""
import argparse,hashlib,json,os,shutil,subprocess
from datetime import UTC,datetime
from pathlib import Path
import polars as pl
from quant.paths import ROOT,STATE
from quant import resources
from scripts.research_v8.registry import FIELDS,append_event
PARENT='c7898815e8dacb7726627d6da6035afa4f32975e'
PREFIX='SPOT_DEFENSIVE_BLEND_20261005_V1'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
p=argparse.ArgumentParser();p.add_argument('action',choices=['close','post']);p.add_argument('--remote-head');a=p.parse_args()
proof=ROOT/'reports/GITHUB_SPOT_DEFENSIVE_BLEND_SOURCE_BINDING_20261005_V1.json'
private=sha(ROOT/'state/dataset_lock.json');assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if a.action=='post':
    b=read(proof);assert git('rev-parse','HEAD')==a.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(b['prior_WIP_preserved'])
    for n,h in b['source_hashes'].items():assert sha(ROOT/n)==h,n
    gate=ROOT/'reports/GITHUB_SPOT_DEFENSIVE_BLEND_STAGED_GATE_20261005_V1.json';assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    save(ROOT/'reports/GITHUB_SPOT_DEFENSIVE_BLEND_SYNC_VERIFIED_20261005_V1.json',dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',git_commit=a.remote_head,remote_commit=a.remote_head,parent_commit=PARENT,
        source_binding_sha256=sha(proof),gate_sha256=sha(gate),task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),prior_WIP_preserved=b['prior_WIP_preserved'],worktree_tracked_clean=True))
    print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=a.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
protocol=ROOT/'protocols'/f'{PREFIX}.json';config=read(protocol)
actual=ROOT/'reports/fast_research'/f'{PREFIX}.json';result=read(actual)
assert result['status']=='COMPLETE_SPOT_DEFENSIVE_MARKED_COMPARISON_NOT_NATIVE_OR_APR' and result['git_commit']==PARENT
assert result['protocol_sha256']==sha(protocol)
for n,h in config['source_hashes'].items():assert sha(ROOT/n)==h,n
ref=read(STATE/'d078-spot-financial-independent-20261005-v1/RESULT.json')
target=read(STATE/'d078-target-independent-20261005-v1/RESULT.json')
diag=read(STATE/'d078-spot-saved-diagnostics-20261005-v1/RESULT.json')
assert ref['status']=='PASS_INDEPENDENT_SAVED_SPOT_WALLETS_NOT_NATIVE_OR_ALPHA_CERTIFICATION'
assert target['status']=='PASS_SAVED_COMPONENT_BLEND_PAST_COVARIANCE_AND_FUTURE_BAR_PERTURBATION'
assert diag['status']=='PASS_SAVED_SPOT_ASSET_MONTH_NET_AND_COST_BRIDGES'
assert all(v['input_sha256']==sha(actual) for v in (ref,target,diag))
assert target['manual_component_mix_max_error']==target['manual_raw_mix_max_error']==0
assert target['future_perturbation_early_target_max_error']==0 and target['later_target_rows_actually_changed']>0
assert len(result['cases'])==len(ref['cases'])==len(result['comparisons'])==2
for c,r in zip(result['cases'],ref['cases'],strict=True):
    assert c['id']==r['id'] and c['risk']['observed_caps_ok'] and r['full_saved_minute_risk']['rows']==436320
    assert r['full_saved_minute_risk']['gross_above_cap_rows']==r['full_saved_minute_risk']['any_asset_above_cap_rows']==0
    assert c['config']['fee_settlement']=='RECEIVED_ASSET' and not c['terminal_cash_realized']
    assert c['liquidated_return']=='NOT_EVALUABLE' and 0<c['terminal_marked_inventory_USDT']<.01
assert result['owned_bytes']<=config['budget']['owned_bytes'] and result['elapsed_seconds']<=config['budget']['wall_seconds']
erratum=read(ROOT/'protocols/SPOT_DEFENSIVE_BLEND_20261005_METADATA_ERRATUM_V1.json')
assert erratum['original_protocol_sha256']==sha(protocol) and not erratum['actual_result_exists_at_annotation']
dest=ROOT/'docs/archive/SPOT_DEFENSIVE_BLEND_USED_METADATA_20261005_V1';dest.mkdir()
for n,v in [('FINANCIAL_RESULT.json',ref),('TARGET_RESULT.json',target),('DIAGNOSTIC_RESULT.json',diag)]:save(dest/n,v)
for n in ['d078_target_reference.py','d078_source_review.md','d078_prepare.py','d078_protocol_annotation.py','d078_inspect.py']:
    shutil.copyfile(ROOT/'.cache'/n,dest/n)
roles={'primary':result['task_id'],'finance':'04304dc33a8340e6b28ca0a09c6a84b4','target':'0031c2a6099f4601adc96968324256d6',
    'diagnostic':'406985eeb6dc476ebec30cf73fdccb35','metadata_erratum':erratum['task_id']}
tasks={}
for role,identity in roles.items():
    t=read(STATE/'task-progress'/('task-'+identity+'.json'));assert t['status']=='completed' and t['exit_code']==0 and t['ended_at']
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
control=read(config['spot_control']['path']);bands=[]
for name,v in [('BLEND',result),('HOLD8',control)]:
    for c in v['cases']:
        t=pl.read_parquet(c['artifacts']['trades']['path']);small=t.filter(pl.col('notional')<50)
        bands.append(dict(recipe=name,cost=c['id'],median_notional_USDT=t['notional'].median(),under50_count=small.height,
            under50_cost_USDT=float(small.select((pl.col('fee')+pl.col('execution_cost')).sum()).item()),
            scope='Post-result descriptive probe, not saved-cost-deletion counterfactual'))
summary=('D078同Spot固定50/50 HOLD10+EXIT10/REENTRY20实际2共享10k钱包完成303已见日；缓存SHA复用不复制，'
    '正常recipe/Spot身份保留原mathID，无新模型/参数搜索。基础组合marked净630.73 vs HOLD8 633.09少2.37，'
    'gross增13.14而fee/exec多15.51；压力净609.23 vs618.40少9.18。实际日vol8.118% vs8.469%，'
    '分钟DD6.823% vs8.926%，turnover2.593 vs1.731，峰gross27.664%，全部close caps内；'
    '不是同风险alpha（原组件预算10% vs HOLD8 8%）。BTC净633.30/ETH净−2.57；101日差−4.01/+165.79/−164.14，'
    '不宣称时间稳定。独立核674成交/872640分钟/606日，606目标混合与过去cov/未来扰动通过；'
    '残仓0.000097/0.000804USDT保留，liquidated return NE。保留SpotHOLD8收益参照和Spot固定防御挑战者，投资NONE/CASH/APR NE。'
    '主79.38s/RSS756.94MB/采样共享1.253GB，新STATE26.90MB；整盘实扫28.568GB@2026-10-05T03:34:50.584997Z（新工件前）。'
    '旧protocol问题/parent文案误带D077，原件保存并在结果前补erratum，执行配方/预算未变。'
    '下一一项50USDT主动再平衡不交易区间完整新回放，保留信号退出/终止/风险强制减仓与caps；'
    '不能删旧成本保留旧毛收益，当前尚未启动。原N/signed/现金/源锁/资金/资源边界不变。')
doc='# D078：现货防御组合的真实收益、风险和成本\n\n'+summary+'\n\n'
doc+='## 实际经济比较\n\n同Spot价格/费率/库存账户/303日期/10k本金，只换为既有固定组合配方；组件各10%过去协方差先下缩再50/50组合，对照HOLD8为8%。这不是严格信号单因素或实际风险匹配。没有独立账户NAV平均、额外本金或后验倍乘。目标用自己的Spot过去日线，决策下一分钟open代理成交，资金费为0是自有现货无需借币的产品语义。\n\n'
doc+='| 指标 | HOLD8 BASE | 固定组合 BASE | HOLD8 STRESS | 固定组合 STRESS |\n|---|---:|---:|---:|---:|\n'
cases=[control['cases'][0],result['cases'][0],control['cases'][1],result['cases'][1]]
for label,fn in [('期末marked净USDT',lambda c:c['summary']['final_nav']-10000),('成本加回gross诊断USDT',lambda c:c['summary']['gross_pnl_before_costs']),
    ('费用USDT',lambda c:c['summary']['fees']),('执行成本USDT',lambda c:c['summary']['execution_costs']),('实际日波动%',lambda c:100*c['summary']['annual_volatility']),
    ('日终MDD%',lambda c:100*c['summary']['max_drawdown']),('分钟MDD%',lambda c:100*c['risk']['minute_max_drawdown']),
    ('成交名义/完整本金',lambda c:c['turnover_over_full_initial_capital']),('成交数',lambda c:c['summary']['trade_count']),
    ('平均gross/net%',lambda c:100*c['risk']['minute_mean_gross_weight']),('峰gross/net%',lambda c:100*c['risk']['minute_max_gross_weight'])]:
    doc+='| '+label+' | '+' | '.join(f'{fn(c):.6f}' for c in cases)+' |\n'
doc+='''
gross是同净收到库存轨迹在成交时加回费用/执行成本的诊断，不能称作独立无成本策略重跑。BUY费用扣base、SELL扣USDT一次，执行成本已含fill；共享NAV包括现金和真实库存。资产贡献是各资产现金流加终点库存价值之和，能桥到同一共享钱包，不能称为独立满资金账户组合。基础组合BTC净633.2964、ETH−2.5682；不因此事后删ETH。成交337少于HOLD357，但名义换手更大，不能用交易次数代替成本。

### 时间与原因诊断

三段真实连续101日相对HOLD8净变化−4.0145/+165.7861/−164.1379USDT，压力−7.4442/+164.1803/−165.9125；不重置资金、不拼赢家。基础月份差二月+122.54、六月−147.86，变化不是均匀优势。保存asset/month/cost桥全部通过；首入场和终止信号可以可靠识别，其余日调仓/组件信号/风险混合无法逐笔可靠拆解，明确UNKNOWN，不能把平仓整笔利润归给订单原因。

基础组合245/337成交名义小于50USDT、直接成本9.5335USDT，压力13.7501；这是描述分布，不是删除这些成本仍保留原毛收益的可执行结果。它支持下一项有限机制检验：固定50USDT主动再平衡区间，保留信号退出/终止与所有必要风险减仓，重新跑完整策略与账本。只有真实新净/risk/成本才能决定采用；不搜阈值、不提高caps。若不能安全区分主动再平衡和必要减仓，先做最小正常reason接口修复，而不盲删订单。

### 验收与限制

实际独立Decimal从674新成交重建cash/base/收到资产fee、872640分钟与606日NAV，全部close资产abs.3/gross.6内；不是新增连续minute漂移减仓实现或intraminute安全认证。独立目标复核手动50/50 target/raw差0，606过去centeredGram协方差误差<1.2e−16；未来OHLC×1.17扰动后早406目标不变、晚106实际改变。复用normal信号组件，不伪称独立重写vendor。正常account源码和成本不改，旧8项不重复全套，新入口由真实2账户+目标/金额/时钟独立证据覆盖。

两个末端残仓仍真实标价，现金清仓收益NOT_EVALUABLE；日历/marked NAV完成不能改叫现金已清仓。价格是Binance Spot，费用是用户Bybit VIP0当前场景10bp/侧，数量步长1e−8/minimum10仍研究假设，未取得Bybit历史原生过滤器/盘口/账户认证。已见历史不是unseen，长期APR/投资优势资格未建立。无下载/API/fit/HPO/locked body/keys/真钱/发单/GPU。

主79.377172s、RSS756944896B、共享采样1252630528B、新STATE26899470B；输入minute/daily缓存只读复用，独立额外小工件另计。整盘28567806550B实扫03:34:50.584997Z，早于新工件及采集增长，不称完成后精确总量。原5GB/swap0/GPU0/D40GB守卫仍启用，两原采集验收时实际存活；不把有限观察升级72h或未来有效日。

准备协议误带两旧文案字段question/parent，运行配方/控制/假设/预算正确。保留原protocol，结果出现前写独立metadata erratum；actual git_commit正确c789881，不用后验改写掩盖原错误。归档原准备脚本与审查。

### 采用与下一决策

固定组合两成本都净略低但波动/回撤较低，保留为开发防御挑战者；HOLD8仍收益参照，投资NONE/CASH。未知永续资金费输入从这项同Spot比较中移除后，防御效果仍存在，但时间反转和成本阻碍没有消失。暂停权重/退出网格和无新官方证据的资金费单位调查；reopen分别是具体可验证机制/新完整验证窗口，以及明确归档单位定义或合法官方同事件来源。保留十币/N资产与signed永续能力，不按当前BTC结果改资产池。

下一主任务是单一50USDT主动调仓区间的同配方完整重放；从真实小额成本与15.51USDT额外总成本出发检验，而非继续增加策略族。若净未改善或防御破坏则不采用，保留本版配方。尚未启动，无后台科研运行承诺。

### 复现

本模块Git代码、原协议加metadata说明，保持原受SHA缓存可用；用独占新STATE/output运行。旧D077及以前按对应原Git字节，不用本版替换原源哈希。

```bash
scripts/with_task_progress.sh --title '固定Spot防御组合' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_DEFENSIVE_BLEND_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_EXCLUSIVE_DIRECTORY --output reports/fast_research/NEW_EXCLUSIVE_RESULT.json
scripts/with_task_progress.sh --title '独立Spot金额核对' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/NEW_EXCLUSIVE_RESULT.json --output /home/xflops/coin-state/NEW_INDEPENDENT_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '独立目标核对' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_DEFENSIVE_BLEND_USED_METADATA_20261005_V1/d078_target_reference.py --input reports/fast_research/NEW_EXCLUSIVE_RESULT.json --output /home/xflops/coin-state/NEW_TARGET_DIRECTORY/RESULT.json
scripts/with_task_progress.sh --title '现货经济诊断' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_saved_economic_diagnostics.py --input reports/fast_research/NEW_EXCLUSIVE_RESULT.json --output /home/xflops/coin-state/NEW_DIAG_DIRECTORY/RESULT.json
```
'''
with (ROOT/'docs/SPOT_DEFENSIVE_BLEND_20261005.md').open('x') as f:f.write(doc)
for n in ['README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md']:
    path=ROOT/n;head,body=path.read_text().split('\n',1);path.write_text(head+'\n\n'+summary+'\n\n### D077及以前历史状态（旧下一步按原时点阅读）\n'+body)
for n in ['docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md','AGENTS.md']:
    with (ROOT/n).open('a') as f:f.write('\n## D078现货防御组合已验收\n\n'+summary+'\n')
report=ROOT/'reports/SPOT_DEFENSIVE_BLEND_ACCEPTED_20261005_V1.json'
save(report,dict(status='ACTUAL_SPOT_DEFENSIVE_MARKED_ACCOUNTS_ACCEPTED_NOT_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
    result_sha256=sha(actual),independent_financial_result=ref,independent_target_result=target,saved_diagnostics_result=diag,
    small_trade_probe=bands,closed_tasks=tasks,live_collectors=live,resources=resources.status(),
    investment='CASH',candidate='NONE',long_term_APR='NOT_EVALUABLE',cash_liquidated_return='NOT_EVALUABLE',next_experiment_started=False))
event=dict.fromkeys(FIELDS);event.update(event_id='D078:ACCEPTED',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id=config['experiment_id'],git_commit=PARENT,
    model_family='NORMAL_SPOT_FIXED_DEFENSIVE_BLEND',fits=0,success_failure='DEFENSIVE_TRADEOFF_RETAINED_NOT_ALPHA',closed_tasks=roles,
    artifact_path=report.relative_to(ROOT).as_posix(),artifact_sha256=sha(report),reason_for_next_experiment='Fixed50USDT discretionary band, full new accounting, no forced reduction waiver',result_influenced_later_choice=True)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
ledger=result['disk_before'];tmp=STATE/'d078-spot-defensive-blend-20261005-v1/last-disk-publication.tmp'
tmp.write_text(json.dumps(dict(ledger=ledger,measured_at=datetime.fromisoformat(ledger['measured_utc']).timestamp(),source='D078 actual pre-replay scan before owned artifacts; publication only')))
tmp.replace(STATE/'task-progress/last-disk.json')
prior=ROOT/'reports/GITHUB_SPOT_PERPETUAL_PRODUCT_SYNC_VERIFIED_20261005_V1.json';wip=read(prior)['prior_WIP_preserved'];assert len(wip)==36
selected={'README.md','AGENTS.md','scripts/investment/spot_perpetual_product_comparison.py','scripts/investment/spot_saved_economic_diagnostics.py',
    'protocols/'+PREFIX+'.json','protocols/SPOT_DEFENSIVE_BLEND_20261005_METADATA_ERRATUM_V1.json','reports/fast_research/'+PREFIX+'.json',
    'reports/SPOT_DEFENSIVE_BLEND_ACCEPTED_20261005_V1.json','docs/SPOT_DEFENSIVE_BLEND_20261005.md','docs/archive/SPOT_DEFENSIVE_BLEND_CLOSE_SOURCE_20261005_V1.py',
    'docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md',
    'docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
selected.update(x.relative_to(ROOT).as_posix() for x in dest.iterdir());assert not selected.intersection(wip)
save(proof,dict(status='D078_ACTUAL_SPOT_DEFENSIVE_TRADEOFF_ACCEPTED',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
    selected_module_paths=sorted(selected),source_hashes={n:sha(ROOT/n) for n in sorted(selected)},prior_WIP_preserved=wip,
    private_SHA_only=private,private_body_read=False,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE'))
print(json.dumps(dict(status='D078_ACCEPTED_NOT_INVESTMENT',paths=len(selected),net=result['cases'][0]['summary']['final_nav']-10000)))
