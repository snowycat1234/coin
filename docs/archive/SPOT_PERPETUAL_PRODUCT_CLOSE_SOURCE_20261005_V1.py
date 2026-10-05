"""Accept actual product economics and normal Spot interface evidence."""
import argparse, hashlib, json, os, shutil, subprocess
from datetime import UTC, datetime
from pathlib import Path
from quant.paths import ROOT, STATE
from quant import resources
from scripts.research_v8.registry import FIELDS, append_event
PARENT='4246975340b1b0debdb57bc25c4d16cd8c1077a3'
PREFIX='SPOT_PERPETUAL_PRODUCT_20261005_V1'
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
def git(*a):return subprocess.check_output(['git',*a],cwd=ROOT,text=True).strip()
p=argparse.ArgumentParser();p.add_argument('action',choices=['close','post']);p.add_argument('--remote-head');a=p.parse_args()
proof=ROOT/'reports/GITHUB_SPOT_PERPETUAL_PRODUCT_SOURCE_BINDING_20261005_V1.json'
private=sha(ROOT/'state/dataset_lock.json');assert private=='29d930063842e9b1666869b4e5f9e3c8cd629313e57b9dadc328c6131b92f45d'
if a.action=='post':
    b=read(proof);assert git('rev-parse','HEAD')==a.remote_head and git('rev-parse','HEAD~1')==PARENT
    assert not git('status','--porcelain=v1','--untracked-files=no')
    assert sorted(git('ls-files','--others','--exclude-standard').splitlines())==sorted(b['prior_WIP_preserved'])
    for n,h in b['source_hashes'].items():assert sha(ROOT/n)==h,n
    gate=ROOT/'reports/GITHUB_SPOT_PERPETUAL_PRODUCT_STAGED_GATE_20261005_V1.json'
    assert read(gate)['status']=='STAGED_MODULE_CHECKPOINT_PASS'
    save(ROOT/'reports/GITHUB_SPOT_PERPETUAL_PRODUCT_SYNC_VERIFIED_20261005_V1.json',dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',git_commit=a.remote_head,remote_commit=a.remote_head,parent_commit=PARENT,
        source_binding_sha256=sha(proof),gate_sha256=sha(gate),task_id=os.environ['COIN_TASK_ID'],created_utc=datetime.now(UTC).isoformat(),prior_WIP_preserved=b['prior_WIP_preserved'],worktree_tracked_clean=True))
    print(json.dumps(dict(status='GITHUB_MAIN_EXACT_REMOTE_VERIFIED',head=a.remote_head)));raise SystemExit
assert git('rev-parse','HEAD')==PARENT
protocol=ROOT/'protocols'/f'{PREFIX}.json';config=read(protocol)
actual=ROOT/'reports/fast_research'/f'{PREFIX}.json';result=read(actual)
ref_path=STATE/'d077-spot-financial-independent-20261005-v1/RESULT.json';reference=read(ref_path)
quote_path=STATE/'d077-quote-prior-reference-20261005-v1/RESULT.json';quote=read(quote_path)
assert result['status']=='COMPLETE_SPOT_PRODUCT_MARKED_COMPARISON_NOT_NATIVE_OR_APR'
assert result['protocol_sha256']==sha(protocol) and reference['input_sha256']==sha(actual)
assert reference['status']=='PASS_INDEPENDENT_SAVED_SPOT_WALLETS_NOT_NATIVE_OR_ALPHA_CERTIFICATION'
assert quote['current_source_sha256']==config['source_hashes']['src/quant/backtest.py']==sha(ROOT/'src/quant/backtest.py')
assert quote['accepted_eight_test_source_sha256']==sha(ROOT/'tests/test_spot_received_asset_interface.py')
assert all(x['max_absolute_float_error']==0 for x in quote['prior_quote_cases']) and quote['new_N_asset_case']['actual_trades']==6
for name,h in config['source_hashes'].items():assert sha(ROOT/name)==h,name
assert len(result['cases'])==len(reference['cases'])==2 and len(result['comparisons'])==4
for c,ind in zip(result['cases'],reference['cases'],strict=True):
    assert c['id']==ind['id'] and c['risk']['observed_caps_ok']
    assert ind['full_saved_minute_risk']['rows']==436320
    assert ind['full_saved_minute_risk']['gross_above_cap_rows']==ind['full_saved_minute_risk']['any_asset_above_cap_rows']==0
    assert c['liquidated_return']=='NOT_EVALUABLE' and not c['terminal_cash_realized']
    assert 0<c['terminal_marked_inventory_USDT']<.01
    assert c['config']['terminal_exit_minutes']==5 and c['config']['fee_settlement']=='RECEIVED_ASSET'
dest=ROOT/'docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1';dest.mkdir()
task_ids={'market':result['task_id'],'independent':'5f6c8bf855e74208b00b292a41966d08',
    'final_eight_fixtures':'2a94de01ccdd488e91fc5cef8cb1e144','prior_quote_and_N':'ba1a0cc1ced0427094a1e4242ec1d165',
    'source_footer_review':'2cf85526f1b94bc992bb84ae3c38aefa','earlier_six_fixtures':'a9d776241f8a462ab3cc677508189fca'}
tasks={}
for role,identity in task_ids.items():
    t=read(STATE/'task-progress'/('task-'+identity+'.json'))
    assert t['status']=='completed' and t['exit_code']==0 and t['ended_at']
    tasks[role]=t;save(dest/('task-'+identity+'.json'),t)
save(dest/'INDEPENDENT_RESULT.json',reference);save(dest/'QUOTE_PRIOR_RESULT.json',quote)
for src in ('d077_spot_independent.py','d077_quote_prior_reference.py','d077_source_review.md','d077_source_schema_review.py'):
    shutil.copyfile(ROOT/'.cache'/src,dest/src)
live=[]
for path in Path('/proc').iterdir():
    if not path.name.isdecimal():continue
    try:
        argv=[x.decode() for x in (path/'cmdline').read_bytes().split(b'\0') if x]
        if len(argv)==5 and argv[0]==str(ROOT/'.venv/bin/python') and argv[1:3]==['-u','-m'] and argv[3] in ('quant.microstructure','quant.collector_public_v3'):
            cg=(path/'cgroup').read_text();assert 'coin-quant.slice' in cg
            live.append(dict(pid=int(path.name),argv=argv,cgroup=cg.strip()))
    except (OSError,UnicodeError):pass
assert len(live)==2
summary=('D077正常Spot账户接入RECEIVED_ASSET及显式末5分钟有限退出，QUOTE默认原三夹具全字段实际差0、N=3共享钱包6实成交、最终8必要回归通过；'
    '旧AST入口不作为新活动依赖，旧报告按Git保留。36原源/244预热/303已见日、2真实Spot钱包与4保存永续完成产品比较，独立Decimal核714成交、'
    '872640分钟/606日现金库存NAV与gross/net，无实际close观测caps越界；仍非分钟强制减仓能力或intraminute风险认证。'
    'Spot基础marked净633.09，vs永续F541.09增92.00，vsP632.72仅增0.37；压力618.40，vsF增91.47/vsP减0.018，'
    '产品优势依赖未确认资金费单位，不能全归因资金费或认定稳健优胜。Spot实际vol8.469%、日DD8.158%/分钟DD8.926%，'
    '残仓0.00104/0.000464USDT真实保留，liquidated return NE，不免费清零。采用正常Spot/N/费用接口、保留SpotHOLD8产品参照，'
    '永续HOLD8/固定组合/十币能力保持；投资NONE/CASH、长期APR NE。主87.39s/RSS803.39MB/共享实采1.303GB、STATE59.15MB，'
    '实际整盘28.496GB@2026-10-05T03:10:44.713535+00:00（创建本轮工件前），5GB/swap0/GPU0/40GB与源锁资金边界不变。'
    '下一主任务复用现有固定50/50 HOLD10+EXIT10规则，在同Spot正常钱包/同输入/完整资本完成一项防御组合对照，'
    '隔离永续资金费单位不确定性之后检验防御收益/risk，不搜索权重或退出周期；尚未启动。')
doc='# D077：真实现货/永续产品对照与正常现货接口\n\n'+summary+'\n\n'
doc+='''## 实际改变与经济解释

正常`src/quant/backtest.py`新增fee_settlement，默认QUOTE原算术/字段保持；RECEIVED_ASSET直接按收到的资产记费用。BUY只支出gross×fill USDT，收到gross×(1−fee)基础币；SELL库存减少gross，收到gross×fill×(1−fee) USDT。基础币费用按mid标价用于报告，不再另扣USDT；执行成本已在fill中，不重复扣。目标/现金/风险分母与周期成本一起修正，正tiny库存不自动清零。N资产固定两币禁止已去除，USDT产品身份/同一共享现金和caps仍保持。旧AST adapter不改但不用于本轮活动，旧原绑定必须按旧Git运行，不能拿旧绿测替代新入口。

新增terminal_exit_minutes默认1保持原默认；本轮事前固定5，与永续已有末5次容量尝试对齐。后续alpha不会在终止窗口重开仓，仍受原容量、min-notional/lot、时间和真实库存约束。现货两账户末各约1e−8 BTC/ETH，价值0.00104362/0.00046384USDT，不能执行满额清仓，marked收益与现金严格分开；liquidated return=NOT_EVALUABLE。独立银行式账本保留全部基础币、quote现金与未实现净值，不免费注销余额。

| 同完整10k/303开发日 | Spot BASE36 | Perp BASE27/F | Perp BASE27/P | Spot STRESS52 | Perp STRESS43/F | Perp STRESS43/P |
|---|---:|---:|---:|---:|---:|---:|
'''
perp=read(config['perpetual_report']['path']);sc=result['cases'];pc=perp['cases']
values=[sc[0]['summary']['final_nav']-10000,pc[0]['summary']['net_PnL'],pc[1]['summary']['net_PnL'],sc[1]['summary']['final_nav']-10000,pc[2]['summary']['net_PnL'],pc[3]['summary']['net_PnL']]
doc+='| 期末净USDT（Spot marked含真实残仓） | '+' | '.join(f'{v:.8f}' for v in values)+' |\n'
values=[sc[0]['summary']['annual_volatility'],pc[0]['summary']['daily_metrics']['annual_volatility'],pc[1]['summary']['daily_metrics']['annual_volatility'],sc[1]['summary']['annual_volatility'],pc[2]['summary']['daily_metrics']['annual_volatility'],pc[3]['summary']['daily_metrics']['annual_volatility']]
doc+='| 实际日收益年波动 | '+' | '.join(f'{v*100:.5f}%' for v in values)+' |\n'
values=[sc[0]['summary']['max_drawdown'],pc[0]['summary']['daily_metrics']['max_drawdown'],pc[1]['summary']['daily_metrics']['max_drawdown'],sc[1]['summary']['max_drawdown'],pc[2]['summary']['daily_metrics']['max_drawdown'],pc[3]['summary']['daily_metrics']['max_drawdown']]
doc+='| 日终最大回撤 | '+' | '.join(f'{v*100:.5f}%' for v in values)+' |\n\n'
doc+='''Spot BASE gross664.25、fee17.31、exec13.85、fund0→marked净633.09；vsPerp/F价格/实际仓位毛增7.76、fee多7.72、exec少0.095、fund少付91.87，桥合+92.00。vsPerp/P原资金费仅0.923，净差收窄至+0.370；压力下净差−0.018。不要选更盈利的单位解释，也不能删除旧资金费后保留旧价格PnL当作Spot。本轮价格、过去协方差目标、收到资产库存、现金/逐仓机制、目标数量冻结时点与mark均属于产品差异，不是资金费单因素或相同实际风险alpha估计。

Spot基础实际vol8.469%、分钟MDD8.926%，相对Perp/F8.394%/9.064%，不是收益/risk完全共同占优。两Spot共享全本金账户各357成交、turnover1.73125/1.72838倍本金，平均gross/net14.648/14.634%、峰gross/net22.158/22.137%、单币峰11.170/11.159%。Spot无保证金贷款/合约仓位，已付基础币库存占用约这些gross比例而不是虚构逐仓保证金。现货不借币不卖空；平台永续signed路径继续保留。

## 数据、因果与费用口径

仅复用原38份Spot源验收中的Jan2024..Jun2025共36文件，当前bytes/SHA精确匹配后读取；JanAug244个真实完整日作200日预热，SepJun303日评分。现货自身past30简单日收益协方差只下缩到8%，同一正常目标数学接口返回的USDM strategy_id仅表示复用来源，并不是Spot变成合约；本轮常多HOLD8/每日决策/下一分钟open代理成交，capacity使用先前完整minute quote_volume×.001。每日日期标签与真实day_end_us一并保存，按真实UTC次日00端点核606个日NAV，不从标签猜持仓归属。

行情来源分别是Binance Spot和USD-M，目标Bybit费用场景：用户快照Spot10bp/perp5.5bp每侧、无MNT；BASE摩擦4+4bp/side，合计36/27bp；STRESS8+8bp合计52/43bp。[Bybit官方说明](https://www.bybit.com/en/help-center/article/Bybit-Spot-Fees-Explained)支持按收到资产收费。本轮没有查询账户或修改快照，费率仍是当前用户场景用于历史代理，不证明历史账户/Bybit原生盘口、过滤器或成交；1e−8数量步长、10USDT开/平最低金额仍显式研究假设。永久holdout、keys/真实资金/orders/付费/GPU均未使用。

保存成交重建全分钟净值用于实际risk诊断，旧Spot账户无全分钟价格漂移强制减仓，不能冒称与永续完整risk实现相同；本轮两个轨迹在全部436320 close观测均未超abs.3/gross.6，若超限事前规则将其标为有限失败诊断，不删除日期/豁免上限。intraminute高低价、native risk/liquidation/BBO、精确历史publication仍未认证。

## 验收、资源与采用

三个子agent分别正常费用维护、独立参考、数据/时钟审查；根实际运行2钱包一次，独立真实2钱包一次。独立Decimal60从BUY/SELL gross与费用公式重建库存/cash/全部分钟与每日NAV，末NAV误差约1e−11USDT，无account/AST/主函数导入；市场mark值来源由主显式SHA源匹配与完整minute映射支持，独立复核不重做市场源QA。实际8必要fixtures通过，新增三币合成共享钱包6成交；精确import原4246975旧默认QUOTE三夹具，订单/成交/日NAV/cycle/原summary所有字段实际差0，容差1e−10。早先6项测试实际closed0元数据保存，其未保存旧6项测试源码哈希UNKNOWN，不拿它代替最终8项。

主87.386945s/RSS803393536B/共享采样1302818816B，STATE59152281B（约59.15MB），独立0.267388s；源schema/footer另一次小读，0新下载/API/模型/HPO/市场重复回放。整盘实扫28495712004B在03:10:44.713535Z，早于新工件与实时采集增长，不当作完成后精确总量；project+整个D VHD32warn/36stop/40hard与共享4999999488B/swap0/GPU0保持。8765仍显示实际任务进度，未新增观察器。

采用正常Spot接口和已有输入复用能力，新增SpotHOLD8产品收益参照，原PerpHOLD8/固定组合/十币挑战者保留；投资仍NONE/CASH、长期APR未建立。产品增益在小资金费假设和压力成本下近零，不能宣布Spot稳定优胜。下一唯一研究任务：已固定50/50 HOLD10+EXIT10规则在同Spot钱包上完整重放，与SpotHOLD8比较真实net/成本/风险及残仓；它去掉永续资金费单位这个输入不确定性，检验固定防御组合的实际价值，不搜索混合权重或退出参数。尚未启动，也不代表投资采用。

## 复现

本模块Git提交下使用原协议和新独占STATE/output即可；正常活动入口无旧日期AST依赖。旧D076及以前回放需按各原Git源码，历史证据不覆盖。

```bash
scripts/with_task_progress.sh --title '现货产品对照' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_PERPETUAL_PRODUCT_20261005_V1.json --run-dir /home/xflops/coin-state/OWN_NEW_DIRECTORY --output reports/fast_research/OWN_NEW_RESULT.json
scripts/with_task_progress.sh --title '独立现货金融复核' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/SPOT_PERPETUAL_PRODUCT_USED_METADATA_20261005_V1/d077_spot_independent.py --input reports/fast_research/OWN_NEW_RESULT.json --output /home/xflops/coin-state/OWN_NEW_REVIEW/RESULT.json
```

真实task结束凭证、小源、独立报告与QUOTE/N参考随本模块保存；正常模块验收后才Git push，精确远端核验按后验凭证。原两路采集验收时实际存活，不将本轮有限观察认作72h或有效未来天。
'''
with (ROOT/'docs/SPOT_PERPETUAL_PRODUCT_20261005.md').open('x') as f:f.write(doc)
for n in ('README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md'):
    path=ROOT/n;head,body=path.read_text().split('\n',1);path.write_text(head+'\n\n'+summary+'\n\n### D076及以前历史状态（旧下一步按原时点阅读）\n'+body)
for n in ('docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md'):
    with (ROOT/n).open('a') as f:f.write('\n## D077真实产品对照已验收\n\n'+summary+'\n')
with (ROOT/'AGENTS.md').open('a') as f:f.write('\n'+summary+'\n')
report=ROOT/'reports/SPOT_PERPETUAL_PRODUCT_ACCEPTED_20261005_V1.json'
save(report,dict(status='NORMAL_SPOT_INTERFACE_AND_ACTUAL_MARKED_PRODUCT_COMPARISON_ACCEPTED_NOT_INVESTMENT',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
    result_sha256=sha(actual),independent_sha256=sha(ref_path),quote_reference_sha256=sha(quote_path),closed_actual_tasks=tasks,
    earlier_six_fixture_source_sha256='UNKNOWN_NOT_PRESERVED_NOT_USED_FOR_CURRENT_ACCEPTANCE',live_collectors=live,resources=resources.status(),
    liquidation_cash_return='NOT_EVALUABLE',candidate='NONE',investment='CASH',next_experiment_started=False))
event=dict.fromkeys(FIELDS);event.update(event_id='D077:ACCEPTED',event_type='OPERATIONAL_RESEARCH_RESULT',experiment_id=config['experiment_id'],git_commit=PARENT,
    model_family='NORMAL_SPOT_HOLD8_PRODUCT_CONTRAST',fits=0,success_failure='COMPLETE_MARKED_ECONOMICS_NO_ROBUST_PRODUCT_SUPERIORITY',
    artifact_path=report.relative_to(ROOT).as_posix(),artifact_sha256=sha(report),reason_for_next_experiment='Fixed existing defensive blend in same Spot account; no unit/grid search',result_influenced_later_choice=True)
append_event(ROOT/'reports/experiment_registry.jsonl',event)
prior=ROOT/'reports/GITHUB_FUNDING_CHAIN_SYNC_VERIFIED_20261005_V1.json';wip=read(prior)['prior_WIP_preserved'];assert len(wip)==36
selected={'README.md','AGENTS.md','src/quant/backtest.py','scripts/investment/spot_perpetual_product_comparison.py','tests/test_spot_received_asset_interface.py',
    'protocols/'+PREFIX+'.json','reports/fast_research/'+PREFIX+'.json','reports/SPOT_PERPETUAL_PRODUCT_ACCEPTED_20261005_V1.json',
    'docs/SPOT_PERPETUAL_PRODUCT_20261005.md','docs/archive/SPOT_PERPETUAL_PRODUCT_CLOSE_SOURCE_20261005_V1.py','docs/RESEARCH_STATUS.md','docs/GOALS.md',
    'docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/MULTI_ASSET_PORTFOLIO_20261004.md','docs/RESEARCH_DECISION_LOG.md',
    'reports/experiment_registry.jsonl',prior.relative_to(ROOT).as_posix()}
selected.update(x.relative_to(ROOT).as_posix() for x in dest.iterdir());assert not selected.intersection(wip)
save(proof,dict(status='D077_NORMAL_SPOT_MARKED_COMPARISON_ACCEPTED',task_id=os.environ['COIN_TASK_ID'],parent_commit=PARENT,
    selected_module_paths=sorted(selected),source_hashes={n:sha(ROOT/n) for n in sorted(selected)},prior_WIP_preserved=wip,
    private_SHA_only=private,private_body_read=False,candidate='NONE',investment='CASH',long_term_APR='NOT_EVALUABLE'))
print(json.dumps(dict(status='D077_ACCEPTED_NOT_INVESTMENT',paths=len(selected),spot_marked_net=result['comparisons'][0]['spot_net_USDT'])))
