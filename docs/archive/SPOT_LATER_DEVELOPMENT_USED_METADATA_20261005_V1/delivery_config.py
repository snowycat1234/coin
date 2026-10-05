import hashlib,json,subprocess
from pathlib import Path
from quant.paths import ROOT,STATE
def read(p):return json.loads(Path(p).read_bytes())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    with Path(p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
v=read(ROOT/'reports/fast_research/SPOT_LATER_BLEND_20261005_V1.json');h=read(ROOT/'reports/fast_research/SPOT_LATER_HOLD8_20261005_V1.json')
accept=read(ROOT/'reports/SPOT_LATER_ACCEPTED_20261005_V1.json');mechanism=read(STATE/'d082-later-spot-20261005-v1/MECHANISM.json')
batch=read(ROOT/'reports/SPOT_LATER_BATCH_STAGES_20261005_V1.json');assert batch['status']=='COMPLETE'
tasks=dict(wallets_and_independent=batch['task_id'],acceptance=accept['task_id'],source_pass=read(ROOT/'reports/fast_research/SPOT_LATER_SOURCE_WINDOW_20261005_V1.json')['task_id'])
for role,title in [('source_failed','核已有来源角色与两币完整预热'),('mechanism','核90日防御增量来自何处')]:
    match=[read(p) for p in (STATE/'task-progress').glob('task-*.json') if read(p).get('title')==title]
    assert len(match)==1;tasks[role]=match[0]['id'] if 'id' in match[0] else match[0]['task_id']
archive='docs/archive/SPOT_LATER_DEVELOPMENT_USED_METADATA_20261005_V1'
copies=[('.cache/d082_prepare.py','prepare.py'),('.cache/d082_resolve_and_batch.py','resolve_batch.py'),('.cache/d082_resolve_challenger.py','resolve_challenger.py'),
 ('.cache/d082_batch.json','batch_config.json'),('.cache/d082_mechanism.py','mechanism.py'),('.cache/accepted_spot_window_used_V1.py','SOURCE_FAILED_USED.py')]
for n in ('HOLD8_FINANCIAL.json','BLEND_FINANCIAL.json','HOLD8_TARGETS.json','BLEND_TARGETS.json','DIAGNOSTIC.json','MECHANISM.json'):
    copies.append((str(STATE/'d082-later-spot-20261005-v1'/n),n))
summary=('D082复用已接受May2025-Feb2026两币月源，完整200日预热；Dec2025-Feb2026为已见90日开发验证。'
 f"固定HOLD8净{h['cases'][0]['summary']['final_nav']-10000:.2f}/{h['cases'][1]['summary']['final_nav']-10000:.2f}USDT，"
 f"日线防御组合净{v['cases'][0]['summary']['final_nav']-10000:.2f}/{v['cases'][1]['summary']['final_nav']-10000:.2f}，"
 '少亏194.88/196.91、分钟DD约9.00%→5.71%；但两者均落后同USDT资本CASH0。'
 '两币Donchian90日零入场/零敞口，防御组合只是半份HOLD10，降低暴露不是新增alpha。保留研究参照、投资NONE/CASH；不拼接此前303日钱包。')
next_task=('不在当前窗口继续调风险/退出/周期。下一先核现有永续资金费单位、原始官方来源与解析链，排除signed经济比较的成本歧义；不改旧报告、不读取locked、不新增下载或发单。'
 '如单位正确则保留其原限制，再选择机制不同的有限策略验证或真实前向证据。4h/宏观SMA过滤继续暂停，reopen需新信息机制或合法独立证据；多空/N币/模型能力保留。')
notes='''来源20个唯一月文件（May2025-Feb2026）来自三份已接受Spot来源；Oct/Nov重复catalog成员核SHA一致，未拼接钱包。私有lock只核SHA，正文未读。源QA标REUSED，当前完整字节SHA与footer重验；V1因旧凭证没有normalized_bytes停止第三文件、没有回放；修复只把大小记为当前测量值，旧SHA仍逐个匹配，失败源码/任务和未运行模板V1保留，实际两模板绑定V2。没有download/API/模型训练/参数搜索，源报告和旧协议证明这些日期已有选择使用；无法据此认证任何unused或unseen历史。

正常Spot runner去掉303日/36源/两币账户硬编码，按配置整UTC日、唯一来源/有序标的计算，旧默认仍303日/原窗口、4h研究仍限已有单独warmup路径。HOLD8可作无永续peer的完整Spot参照，第二配方复用其SHA缓存；原现货库存、received-asset fee、quant backtest字节、5次末退出/1e-8数量/min10、abs.3/gross.6保持。日信号与完整分钟成交/mark分开；两资产并行身份进入同一10k钱包。四钱包是对照而非叠加40k组合，日账连续分三30日，不平均/事后缩放原NAV。

独立Decimal逐成交、费用一次与末库存/完整分钟风险，以及独立scalar prior20/SMA200/prior10、centered past30日Gram、两种预算/组合目标全部真实执行。未来扰动在正常producer也执行，早期目标不变。信号计算没有调用producer生成期望值；未来扰动才单独调用producer。日线防御90日EXIT10 raw与scaled全零，保存目标与数学派生5%过去风险HOLD的差6.94e-18；这是只读目标机制诊断，HOLD5钱包NOT_RUN，不提供其净值/收益。改善约189USDT来自不同持仓价格损益，约5.36/7.72来自低成本；不把不同实际风险称匹配alpha。原gross为同数量成本加回诊断，不是可交易无成本收益。

四账户皆marked、未完整cash清仓；防御末库存约9.51/8.96USDT仍在NAV，liquidated return=NOT_EVALUABLE，未免费删除或延长退出。CASH是相同USDT资本、无利息/无交易参考，不是实际账户资格。实际日vol约HOLD8 9.82%/防御6.14%，预算不是实际波动保证；保存分钟close无观测caps违约不认证intraminute或连续漂移风险控制。Bybit用户成本配Binance Spot价格、min/lot未原生历史认证，投资/APR仍NONE/NOT_EVALUABLE。

批次八阶段全0/单调时间343.11s，仅此命令；主wallet内部73.54/79.56s包含守卫/hash/save，最大阶段112.55s（防御账户）。来源成功87.61s另计，源首次失败与上下文/实现/文档未包含，不宣称整轮5.72分钟。主进程RSS410.22/405.97MB、共享采样932.17MB；最后账户前整盘28,779,163,108B@2026-10-05T05:48:44.806157Z是实测pre-scan，不冒充当前值。collector只运维快照，不是历史通过门槛。Git核验改为可选既有native binary、一次tracked清单、60s单调用超时；新post耗时待实际测量，不先声称提速。'''
selected=['scripts/investment/accepted_spot_window.py','scripts/investment/audit_daily_spot_targets.py','scripts/investment/spot_perpetual_product_comparison.py','scripts/investment/spot_saved_economic_diagnostics.py','scripts/investment/accept_spot_research.py','scripts/investment/checkpoint_spot_research.py','scripts/investment/verify_research_push.py',
 'docs/RESEARCH_STATUS.md','docs/RESEARCH_DECISION_LOG.md','docs/SPOT_LATER_DEVELOPMENT_20261005.md','reports/experiment_registry.jsonl','reports/SPOT_LATER_BATCH_STAGES_20261005_V1.json','reports/SPOT_LATER_ACCEPTED_20261005_V1.json','reports/GITHUB_SPOT_DAILY_TREND_SYNC_VERIFIED_20261005_V1.json']
selected.extend('protocols/'+n+'.json' for n in ['SPOT_LATER_SOURCE_WINDOW_20261005_V1','SPOT_LATER_DEVELOPMENT_20261005_V1','SPOT_LATER_DEVELOPMENT_20261005_V2','SPOT_LATER_HOLD8_20261005_V1','SPOT_LATER_BLEND_20261005_V1'])
selected.extend('reports/fast_research/'+n+'.json' for n in ['SPOT_LATER_SOURCE_WINDOW_20261005_V1','SPOT_LATER_HOLD8_20261005_V1','SPOT_LATER_BLEND_20261005_V1'])
config=dict(module='D082_BLEND',title='来源角色与固定后段开发经济验证',parent_commit=head,acceptance='reports/SPOT_LATER_ACCEPTED_20261005_V1.json',archive=archive,archive_copies=copies,
 task_ids=tasks,expected_exit_codes=dict(source_failed=1),attempts=dict(source_failed='SOURCE_FAILED_USED.py'),attempt_model_family='SOURCE_METADATA_ADAPTER_NOT_MODEL',attempt_reason='Old accepted source omitted file size; keep accepted SHA and label new size as current measurement. No account ran before failure.',
 decision=dict(adopted=accept['development_recipe_adopted'],summary=summary,next=next_task),notes=notes,report_document='docs/SPOT_LATER_DEVELOPMENT_20261005.md',progress_entry_paths=[],
 reproducible_command="scripts/with_task_progress.sh --title '固定后段账户及独立核验' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/run_research_steps.py --config docs/archive/SPOT_LATER_DEVELOPMENT_USED_METADATA_20261005_V1/batch_config.json --output reports/NEW_BATCH.json",
 prior_sync_proof='reports/GITHUB_SPOT_DAILY_TREND_SYNC_VERIFIED_20261005_V1.json',source_binding='reports/GITHUB_SPOT_LATER_SOURCE_BINDING_20261005_V1.json',selected_paths=selected)
save(ROOT/'.cache/d082_checkpoint.json',config)
print('CONFIG_READY_FOR_GENERIC_CHECKPOINT')
