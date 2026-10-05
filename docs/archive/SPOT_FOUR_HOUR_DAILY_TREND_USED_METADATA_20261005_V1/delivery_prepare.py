import json,hashlib,subprocess
from pathlib import Path
from quant.paths import ROOT,STATE
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip();assert head=='7a239eb7121885070147133fe2dfca72e857472e'
files=['AGENTS.md','README.md','docs/GOALS.md','docs/PROGRESS.md','docs/FAST_RESEARCH_TASK_CHECKLIST.md','docs/RESEARCH_STATUS.md']
before={n:dict(bytes=(ROOT/n).stat().st_size,sha256=sha(ROOT/n),prior_git=head) for n in files}
(ROOT/'AGENTS.md').write_text('''# COIN：当前有效执行规则

用户2026-10-05已采纳快速研究工作流，精确原文 `docs/archive/COIN_FAST_RESEARCH_WORKFLOW_USER_20261005.md`。它覆盖重复文档、逐小任务发布和固定多agent要求。投资质量与资金/数据/资源边界保持；旧指令与结果按Git和既有archive复现，当前状态只看 `docs/RESEARCH_STATUS.md`。

## 权限与资源

- 普通研究自主：先核HEAD/diff、实际任务和必要经济结果，再选有限高价值问题；不重做已完成修复、不覆盖他人WIP、不无限搜参。
- 所有Python/测试/训练在hpc_linux WSL，经 `scripts/with_task_progress.sh` → `scripts/bounded.sh`；D盘ROOT `/mnt/d/codex/coin` 与STATE `/home/xflops/coin-state`，数据/缓存/临时不占C盘。
- 共享RAM最多5,000,000,000B（当前守卫4,999,999,488B），swap0、GPU0。项目+整个D盘WSL VHD合计40GB；32GB预警、36GB停止新增，保留守卫预留空间。不改硬规则、不拿旧扫描伪作当前值。
- 完整共享资本10k，单币abs名义30%/组合gross60%，累计各资产/产品/策略腿；永续单向逐仓1x、无自动加保证金。不得自行增资本/caps/杠杆。
- 不读取账户密钥、真钱、Testnet/mainnet发单、付费、规避交易所限制、启封locked或扩预算。`state/dataset_lock.json`仅核SHA，不解析正文。
- 现货库存保护保留；永续signed多空/现金、N资产能力保持。保证金非PnL、空头名义卖款非现金；价格/mark/index/资金费单位和时钟必须明确，不确认则UNKNOWN，不补零掩盖。

## 当前正常入口

- `scripts/investment/spot_perpetual_product_comparison.py`：Spot规则/HOLD组合与保存控制对照；`src/quant/backtest.py`：owned Spot、received-asset手续费、订单和NAV。
- `scripts/investment/multi_asset_portfolio.py`：N资产共享永续组合；正常targets为public_sma_perpetual、donchian_daily_pool_target、hold_donchian_blend_target等。
- Binance行情配Bybit用户费用是跨场所代理，费用profile/SHA/产品/费用资产显式绑定；未经核对不得称Bybit原生成交。
- `accept_spot_research.py`复用本族历史账户/参考验收，`checkpoint_spot_research.py`做薄归档/状态/manifest，`run_research_steps.py`顺序批处理和单调计时；采用规则在新实验前明确，不把工程验收绑定盈亏方向。

## 研究与验证

- REUSE FIRST → ADAPTER SECOND → CUSTOM MODEL LAST。第三方来源/commit/version/license/本地修改登记OPEN_SOURCE_REGISTRY；不重写成熟内核。
- 运行前短记假设、对照、数据角色、指标、预算与停止条件。新经济语义完整重跑受影响账户；只读诊断读旧账本，不删成本保留旧毛收益。
- 因果时间、标签成熟、共同时间切分/适用OOF与独立数据角色保持；已见历史不重命名unseen，不拼接独立满资金账户/事后赢家，不放松成本造APR。
- 按风险验证：只读检查输入/计算/引用；新配方用目标因果/身份顺序、真实账户及现有独立资金/风险核验；金融/可得性修改加相关反例与旧默认golden。REUSED需范围与身份绑定，未运行写NOT_RUN。
- 标的顺序必须贯通targets/cov/账户/成交。缺失与退出保留原因，缺成交/mark或不能清仓按规则停止或有限诊断；marked NAV与liquidated return分别验收，正残仓不能删除/免费平仓。
- 真实风险减仓不得因低换手关闭，净抵消不是gross消失。报告完整资本、gross/net、资金费/费用/执行、实际vol/DD与集中度。
- frozen数据/协议/证据不覆盖；活动代码可正常维护，旧实现依Git复现，不日常复制V1/V2/V3或AST绕过旧源码绑定。已有FrozenPredictor/ExecutionContractV2/STOP_v2/A07/holdout工程和负结果保留。

## 运维、进度与交付

- 先核 `http://localhost:8765/api/status`，沿用服务；未运行再按现有授权bounded启动。长任务显示真实阶段/完成数，未知总量不造百分比，磁盘注明实际扫描时刻。
- 合法采集不停止/注入；异常先保存日志/checkpoint/audit head/必要闭合备份、查实际退出与断档再有限恢复。不拼健康时间。独立历史输入有效时collector存活单独报告，不阻塞离线账本；若影响数据/资源/安全则阻塞相关任务。
- 默认主agent做短任务，必要独立只读审阅才委派；避免重复读写/重复账户。子agent失败只接管未完成部分，不扩大权限。
- 负面测试/pytest basetemp在STATE独立目录，不能污染实际ROOT/source/store或为迁就测试改守卫。只清自己可证明的工件。
- 只维护一份RESEARCH_STATUS，registry/decision log只追加；详细工件路径/SHA引用。README/GOALS/PROGRESS是入口，不继续八份摘要。记录实际阶段计时；并行取区间并集、父子不双计，未知间隔/模型配置写UNKNOWN。
- 一个有限相关模块完成并验收后正常commit/push `https://github.com/snowycat1234/coin.git`，核远端，不按小时、不force push。代码/协议/小证据入库，行情/模型/db/env/cache/log/VHD留D。检查源码字节/敏感信息/文件大小，保留无关WIP。
''')
(ROOT/'README.md').write_text('''# COIN：量化研究与共享资本模拟

当前投资资格为 **NONE/CASH**，项目仍在历史研究和前向证据建设阶段。支持现货库存约束、USDT线性永续多空/空仓、可配置N资产与共享资本；支持能力不等于采用某个配方或授权真钱。

- [当前研究、结果与下一决策](docs/RESEARCH_STATUS.md)
- [长期目标与阶段位置](docs/GOALS.md)
- [实验记录](reports/experiment_registry.jsonl) / [决策日志](docs/RESEARCH_DECISION_LOG.md)
- [开源来源与适配](docs/OPEN_SOURCE_REGISTRY.md)
- [有效执行规则](AGENTS.md)

运行在D盘hpc_linux WSL，共享RAM≤5GB、swap0/GPU0，项目加整个D盘WSL VHD≤40GB。通过scripts/with_task_progress.sh包装科学任务，已有进度窗口http://localhost:8765/。具体受SHA配置/复现命令见各结果文档；旧实验按其Git提交复现。

Binance行情配Bybit用户费用时明确为代理；完整资本、真实成本、因果与封存数据隔离继续。测试通过和历史正收益不认证长期APR、交易所真实成交或真钱资格。
''')
(ROOT/'docs/GOALS.md').write_text('''# 长期目标与阶段位置

当前步骤与投资决定只维护在 [RESEARCH_STATUS](RESEARCH_STATUS.md)。以下是完整目标范围，不将能力实现当作盈利或前向资格完成。

| 目标 | 当前证据/仍需完成 |
|---|---|
| 原方案审核与可实施纠偏 | 历史方案/审计按Git和archive保留；当前按投资质量自主迭代 |
| D盘WSL运行与数据隔离 | bounded共享5GB/swap0/GPU0；整项目+VHD40GB守卫沿用 |
| 官方历史来源与CHECKSUM | 已接受来源按SHA复用；新增源需合法权限与QA |
| 分钟执行与小时/日线信号分离 | 正常接口已有，当前4h与日风险因果核验见最新报告 |
| 可配置N币池 | 能力保留；历史两币/十币对照按各原Git，不永久限两币 |
| 同时共享资本与跨币风险 | ordered targets/cov/account、abs.3/gross.6；不同实际风险单独报告 |
| 现货真实库存与费用资产 | received-asset及QUOTE兼容；终止正dust不能免费消失 |
| 永续多头/空头/现金 | signed能力保留；资金费单位/产品规则未确认部分限制经济结论 |
| 成交、反手、部分成交与恢复 | 相关原验收保留，新语义需针对性验证，不能用旧绿测代替 |
| 完整资本、钱包、PnL与NAV | 每个新账本继续低成本独立金融/风险核验 |
| 开源策略公平比较 | 已有共同产品/日期/成本对照；不声称教学样例代表市场最强 |
| 共享ML与复用内核 | 能力/历史结果按registry保留；没有已认证投资优势 |
| 交易原因/换手/损益机制 | 保存账本诊断；不把原因统计当整笔利润的因果证明 |
| 研究主力与少量挑战者 | 当前具体采用/暂停/reopen在权威状态；不强救负配方 |
| 独立历史验证 | 必须核授权与是否曾参与选择；locked不启封 |
| 真实未来资格与采集有效日 | 按实际质量/断档审计，不以进程或回放代替天数 |
| 候选冻结后的真正未来记录 | 尚无合格候选；不能把此前历史拼作未来业绩 |
| 场所原生行情/经济规则 | 代理证据与原生资格分开，UNKNOWN不能伪造精确值 |
| 实时进度与运维恢复 | 8765沿用；运维故障单独报告，离线有效账本不无关重跑 |
| 研发开销与发布 | 批处理真实退出/单调计时，集中状态；按模块验收push核远端 |
| 最终部署/真钱 | 需要真实质量与独立经济门槛及用户另行资金授权，当前未达成 |

完整历史进展在Git、[registry](../reports/experiment_registry.jsonl)和[决策日志](RESEARCH_DECISION_LOG.md)。具体经济/资源证据引用结果路径，避免复制多份当前摘要。
''')
for n,title in [('docs/PROGRESS.md','进度入口'),('docs/FAST_RESEARCH_TASK_CHECKLIST.md','研究任务入口')]:
    (ROOT/n).write_text('# '+title+'\n\n当前状态与步骤： [RESEARCH_STATUS](RESEARCH_STATUS.md)。长期范围： [GOALS](GOALS.md)。全部尝试与负结果保留在 [registry](../reports/experiment_registry.jsonl) / [决策日志](RESEARCH_DECISION_LOG.md)，旧长清单按Git复现。\n')
after={n:dict(bytes=(ROOT/n).stat().st_size,sha256=sha(ROOT/n)) for n in files if n!='docs/RESEARCH_STATUS.md'}
save(ROOT/'reports/FAST_RESEARCH_CONTEXT_CLEANUP_20261005_V1.json',dict(status='CURRENT_CONTEXT_CONSOLIDATED',prior_git=head,before=before,after=after,
 user_directive_SHA=sha(ROOT/'docs/archive/COIN_FAST_RESEARCH_WORKFLOW_USER_20261005.md'),historical_results_deleted=False,
 permissions_resources_risk_unchanged=True,unrelated_WIP_touched=False,status_file_finalized_by_publisher=True))
def ids(prefix,post):
    tasks={}
    for p in (ROOT/prefix).glob('task-*.json'):
        t=read(p);title=t['title'];phase='validation'
        if '回放' in title or '对照' in title:phase='experiment_combined'
        if '绑定' in title:phase='binding_preparation'
        tasks[t['id']]=phase
    tid=read(ROOT/post)['task_id'];tasks[tid]='publication_remote_verification'
    return tasks
v=read(ROOT/'reports/fast_research/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json')
accept=read(ROOT/'reports/SPOT_FOUR_HOUR_DAILY_TREND_ACCEPTED_20261005_V1.json')
tasks={'primary':v['task_id'],'fixture_failed':'9d6bc462e79d426694ac7e49538327e5','fixture_corrected':'b01df5f1f518413a952569f245957713',
 'fixture_final':'60fe485ff8ea478a91ee124b07271b18','prior':'83d5ef4f88614a108fcd3ec9add57fde','target':'c2eb252e8a1b4088a3b2a4588c50e6cc','prepare':'003be49ac49e48be83d04eefb2d7d908','acceptance':accept['task_id']}
for role,title in [('finance','独立金额核验日线趋势过滤钱包'),('diagnostic','日线趋势过滤保存损益与时间诊断')]:
    matching=[read(p) for p in (STATE/'task-progress').glob('task-*.json') if read(p).get('title')==title]
    assert len(matching)==1;tasks[role]=matching[0]['id']
timing={
 'D079':dict(tasks=ids('docs/archive/SPOT_DISCRETIONARY_BAND_USED_METADATA_20261005_V1','reports/GITHUB_SPOT_DISCRETIONARY_BAND_SYNC_VERIFIED_20261005_V1.json'),result='reports/fast_research/SPOT_DISCRETIONARY_BAND50_20261005_V1.json'),
 'D080':dict(tasks=ids('docs/archive/SPOT_FOUR_HOUR_USED_METADATA_20261005_V1','reports/GITHUB_SPOT_FOUR_HOUR_SYNC_VERIFIED_20261005_V1.json'),result='reports/fast_research/SPOT_FOUR_HOUR_DAILY_RISK_20261005_V1.json'),
 'D081':dict(tasks={tid:('experiment_combined' if role=='primary' else 'validation') for role,tid in tasks.items()},result='reports/fast_research/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json')}
save(ROOT/'.cache/recent_research_timing_sources.json',timing)
py='/home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python'
common=[py,'-B'];arg=['--result','reports/fast_research/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json','--protocol','protocols/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json',
 '--financial',str(STATE/'d081-spot-financial-independent-20261005-v1/RESULT.json'),'--targets',str(STATE/'d081-actual-target-reference-20261005-v1/RESULT.json'),
 '--diagnostic',str(STATE/'d081-spot-saved-diagnostics-20261005-v1/RESULT.json'),'--output','reports/SPOT_FOUR_HOUR_DAILY_TREND_ACCEPTED_BATCH_20261005_V1.json']
save(ROOT/'.cache/d081_batch.json',dict(steps=[dict(title='核对既有账户与独立证据',argv=common+['scripts/investment/accept_spot_research.py']+arg),
 dict(title='优化前后结果一致与资产损益诊断',argv=common+['.cache/d081_saved_diagnosis.py']),dict(title='近三轮实际任务计时元数据',argv=common+['.cache/recent_research_timing.py'])]))
archive='docs/archive/SPOT_FOUR_HOUR_DAILY_TREND_USED_METADATA_20261005_V1'
copies=[('.cache/d081_prepare.py','d081_prepare.py'),('.cache/d081_reference.py','d081_reference.py'),('.cache/d081_source_review.md','source_review.md'),
 ('.cache/d081_saved_diagnosis.py','saved_diagnosis.py'),('.cache/recent_research_timing.py','recent_research_timing.py'),('.cache/recent_research_timing_sources.json','recent_timing_sources.json'),
 ('.cache/d081_batch.json','batch_config.json'),('.cache/d081_delivery_prepare.py','delivery_prepare.py')]
for ver in (1,2,3):
    copies.append((str(STATE/f'd081-macro-fixtures-20261005-v{ver}.xml'),f'fixtures_V{ver}.xml'))
    if ver<3:copies.append((str(STATE/f'd081-reference-used-source-20261005-v{ver}/test_four_hour_daily_trend_filter.py'),f'fixture_used_V{ver}.py'))
for name in ('public_sma_perpetual.py','donchian_daily_pool_target.py','hold_donchian_blend_target.py'):
    copies.append((str(STATE/'d081-reference-used-source-20261005-v3'/name),'actual_used_'+name))
for directory,filename,name in [('d081-spot-financial-independent-20261005-v1','RESULT.json','FINANCIAL_RESULT.json'),('d081-actual-target-reference-20261005-v1','RESULT.json','TARGET_RESULT.json'),
 ('d081-prior-default-reference-20261005-v1','RESULT.json','PRIOR_DEFAULT_RESULT.json'),('d081-spot-saved-diagnostics-20261005-v1','RESULT.json','DIAGNOSTIC_RESULT.json'),
 ('d081-fast-workflow-saved-diagnosis-20261005-v1','RESULT.json','SAVED_DIAGNOSIS_RESULT.json'),('d081-fast-workflow-timing-20261005-v1','RESULT.json','RECENT_TIMING_RESULT.json')]:copies.append((str(STATE/directory/filename),name))
copies.append(('reports/FAST_RESEARCH_BATCH_STAGES_20261005_V1.json','BATCH_STAGES.json'))
net=[x['summary']['final_nav']-10000 for x in v['cases']];delta=[x['net_delta_USDT'] for x in v['comparisons']]
summary=(f"D081日SMA200替换4hSMA200入场过滤（非双SMA AND），退出/risk/4h执行/本金/cost保持；两303日账户净{net[0]:.2f}/{net[1]:.2f}USDT，比原4h少{-delta[0]:.2f}/{-delta[1]:.2f}，省成本18.58/26.75却毛损益少309.89/307.28；分钟DD升至8.908%/9.118%，不采用。原日线防御组合/HOLD8保留，投资NONE/CASH；新配方不是低成本改善。当前工作流已按用户采纳收拢为单状态/薄证据引用与复用收尾，旧结果按Git/工件保留。")
next_task='停止在同303日上继续SMA过滤或周期网格；下一先核授权且未参与选择的共同Spot证据窗口/数据角色，只读来源与实验登记，不解析locked、不先下载或称unseen。用独立证据可得性决定两研究参照的有限验证或继续前向采集；未启动新市场回放。4h配方暂停，reopen需明确新信息机制或合法独立证据。'
notes='''本次替换trend property上下文，原filter_trend/entry/channel及COIN exit10保持。hook只在200连续4h与200连续已完成日资格/availability核对后读daily6col，floor日端排除未完日；HOLD日target向前携带，全部risk用30日日收益，N身份顺序保持。默认None日/4h目标及完整旧meta与Git7a239eb一致。7最终fixtures通过；V1 5fail/1pass为synthetic prior20未严格突破，producer未改，V2 6pass、V3 7pass及各used字节/退出码保留。当前3636目标独立scalar日SMA/通道进出场/centered日cov/mix最大误差2.8e-17，BTC23入22出、ETH11/11；独立金融1669成交/872640分钟/606日通过。已接受日/4h/分钟缓存按SHA复用、不复制新行情，无新增数据/API/fits/HPO/资金权限。

实际源与参考/诊断由路径/SHA绑定，只归档一次，验收JSON不再嵌入完整多个结果。新通用收尾不要求正/负收益才能接受工程结果；现有研究采用标准仍是事前“双成本净改善且vol/分钟DD不恶化”，本轮保持，不为新提示词回改。其他取舍要在未来新实验前明确。collector仅当时进程运维快照，不是独立历史账户通过条件；两现有进程未停止。

新批处理单调时间只覆盖该命令；旧三轮按真实task时间区间并集汇总，不复造单调历史或全会话端到端，也不把未归因时间叫模型思考。精确model/推理配置UNKNOWN，未更改全局设置。该批验证原收尾与批收尾核心完全一致，再读资产经济桥，不重放市场。当前real-time进度服务沿用。硬资源规则不改：主84.43s/RSS765.28MB/共享采样1.265GB、新owned27.26MB；整盘28.697GB@2026-10-05T04:53:03.328414Z为工件前扫描，不是当前精确值。

代理Spot的数量/min10/末5次退出与原生历史过滤器仍未认证，positive dust保留，清仓收益NOT_EVALUABLE。无连续分钟漂移减仓或原生执行认证；全部保存minute-close未超caps。源已见开发角色不改，未启封holdout/keys/真钱/发单/付费/GPU。macro失败仅否定本配方/窗口，不能永久取消多周期/短仓/N币/开源模型能力。
'''
selected=set(files+['docs/OPEN_SOURCE_REGISTRY.md','docs/RESEARCH_DECISION_LOG.md','reports/experiment_registry.jsonl',
 'scripts/investment/public_sma_perpetual.py','scripts/investment/donchian_daily_pool_target.py','scripts/investment/hold_donchian_blend_target.py','scripts/investment/spot_perpetual_product_comparison.py',
 'scripts/investment/accept_spot_research.py','scripts/investment/checkpoint_spot_research.py','scripts/investment/run_research_steps.py','scripts/task_progress_api.py','tests/test_four_hour_daily_trend_filter.py',
 'protocols/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json','reports/fast_research/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json','reports/SPOT_FOUR_HOUR_DAILY_TREND_ACCEPTED_20261005_V1.json',
 'reports/SPOT_FOUR_HOUR_DAILY_TREND_ACCEPTED_BATCH_20261005_V1.json','reports/FAST_RESEARCH_BATCH_STAGES_20261005_V1.json','reports/FAST_RESEARCH_CONTEXT_CLEANUP_20261005_V1.json',
 'docs/SPOT_FOUR_HOUR_DAILY_TREND_20261005.md','docs/archive/COIN_FAST_RESEARCH_WORKFLOW_USER_20261005.md','reports/GITHUB_SPOT_FOUR_HOUR_SYNC_VERIFIED_20261005_V1.json'])
save(ROOT/'.cache/d081_checkpoint.json',dict(module='D081',title='日线趋势过滤负结果与快速工作流',parent_commit=head,acceptance='reports/SPOT_FOUR_HOUR_DAILY_TREND_ACCEPTED_20261005_V1.json',
 archive=archive,archive_copies=copies,task_ids=tasks,expected_exit_codes=dict(fixture_failed=1),attempts={f'fixture_{x}':f'fixtures_V{i}.xml' for i,x in [(1,'failed'),(2,'corrected'),(3,'final')]},
 decision=dict(adopted=accept['development_recipe_adopted'],summary=summary,next=next_task),notes=notes,
 report_document='docs/SPOT_FOUR_HOUR_DAILY_TREND_20261005.md',progress_entry_paths=[],
 reproducible_command="scripts/with_task_progress.sh --title '固定macro回放' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/spot_perpetual_product_comparison.py --protocol protocols/SPOT_FOUR_HOUR_DAILY_TREND_20261005_V1.json --run-dir /home/xflops/coin-state/NEW_RUN --output reports/fast_research/NEW_RESULT.json",
 prior_sync_proof='reports/GITHUB_SPOT_FOUR_HOUR_SYNC_VERIFIED_20261005_V1.json',source_binding='reports/GITHUB_SPOT_DAILY_TREND_SOURCE_BINDING_20261005_V1.json',selected_paths=sorted(selected)))
print(json.dumps(dict(status='CONTEXT_AND_BATCH_CONFIGURATION_READY',context_bytes_before=sum(x['bytes'] for n,x in before.items() if n!='docs/RESEARCH_STATUS.md'),context_bytes_after=sum(x['bytes'] for x in after.values()))))
