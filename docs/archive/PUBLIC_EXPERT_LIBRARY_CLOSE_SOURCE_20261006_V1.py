import json,subprocess
from pathlib import Path
from quant.paths import ROOT,STATE
from scripts.investment.reuse_cycle_controls import sha
def read(p):return json.loads((ROOT/p).read_bytes())
def save(p,v):
    with (ROOT/p).open('x') as f:json.dump(v,f,indent=2,ensure_ascii=False,allow_nan=False);f.write('\n')
head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
review='reports/PUBLIC_SMA50_200_REVIEW_20261006_V1.json';r=read(review)
oracle='reports/FROZEN_EXPERT_ORACLE_OPPORTUNITY_20261006_V2.json';o=read(oracle)
assert r['economic_accounts_referenced']==6 and o['real_accounts_new']==o['models_fit']==0
assert o['protocol']['source_sha256']==o['source_sha256']==sha(ROOT/'scripts/investment/oracle_expert_opportunity.py')
paths=['reports/fast_research/PUBLIC_SMA50_200_DIRECTIONS_20261006_V1.json','reports/fast_research/PUBLIC_SMA50_200_LONG_SHORT_20261006_V1.json','reports/fast_research/FROZEN_EXPERT_LIBRARY_COMPLETE_20261006_V1.json']
producers=[read(p) for p in paths];assert all(v['binding']['git_commit']==head for v in producers)
pct=next(v for v in r['rows'] if v['mode']=='LONG_SHORT' and v['unit']=='RAW_AS_PERCENT')
raw=next(v for v in r['rows'] if v['mode']=='LONG_SHORT' and v['unit']=='RAW_AS_FRACTION')
gates=all(v['pass_opportunity_gate'] for v in o['results'])
next_action=('冻结expert60日近似机会增量足够，先将同一oracle路径在既有共享资本账户真实重放，补equal/static合集真实成本对照；诊断不作为投资证据。随后只用过去slow×fast×vol少量状态、非重叠60日标签做排名可预测性与常数/错位/打乱/同频随机placebo，0交易模型拟合，不扫分类器。仅12个完整60日标签，尾部10日保留收益但不能充作60日训练标签；单BTC旧周期仅机制筛选，稳定性/独立证据不足，不晋级。' if gates else
    '单一60日切换成本后机会增量未达事前门槛，暂停本selector配方，保留最强冻结单expert参照与SHORT能力。reopen需新的合法完整周期/多资产证据或不同可解释收益来源；不在已见窗口换horizon/参数救结果。')
summary=f"D103公开完整SMA50/200多空：BASE/PCT净{pct['net_USDT']:.2f}，毛价格{pct['gross_USDT']:.2f}，费用+执行{pct['fees_USDT']+pct['execution_USDT']:.2f}，SHORT{pct['direction']['SHORT']['net_contribution']:.2f}，vol{pct['daily_metrics']['annual_volatility']*100:.2f}%、DD{pct['drawdown_percent']:.2f}%；RAW净{raw['net_USDT']:.2f}。两情景不满足替换原SMA200的门槛；保留为冻结expert，不加exit/filter搜参。"
lines=['','## D103/D104：完整公开50/200与冻结expert机会诊断','',summary,'',
    '10新完整730日账户（50/200三方向×2、DC20/10和双通道各×2）；4原Cash/Hold完整账户严格复用，不相加钱包。下表是实际完整账户，收益分母10k；与归一化oracle诊断分开。',
    '|冻结expert / BASE-PCT|净USDT|LONG|SHORT|费+执行|vol%|分钟DD%|','|---|---:|---:|---:|---:|---:|---:|']
all_cases={}
for entry in o['producers']:
    for c in read(entry['path'])['cases']:
        if c['unit']=='RAW_AS_PERCENT' and (c['strategy'],c['unit']) in {(v['expert'],v['unit']) for v in o['library']}:
            mode='CASH' if c['strategy']=='CASH' else 'LONG_ONLY' if c['strategy']=='HOLD' else 'LONG_SHORT'
            if c['mode']==mode:all_cases[c['strategy']]=c
assert set(all_cases)==set(o['protocol']['experts'])
for name in o['protocol']['experts']:
    s=all_cases[name]['summary'];d=s['long_short_marked_contribution']
    lines.append('|'+name+'|'+'|'.join(f'{v:.2f}' for v in (s['net_PnL'],d['LONG']['net_contribution'],d['SHORT']['net_contribution'],s['fees_USDT']+s['execution_cost_USDT'],s['daily_metrics']['annual_volatility']*100,s['minute_max_drawdown']*100))+'|')
lines += ['','### 非可交易oracle诊断：只测机会，不计投资证据','',
    '|资金费条件|事后best single|oracle增量USDT|切换数|额外切换成本|shadow LONG|shadow SHORT|','|---|---|---:|---:|---:|---:|---:|']
for v in o['results']:
    c=v['oracle_variants']['TARGET_DISTANCE_SWITCH_COST_13_5BP']
    lines.append('|'+v['unit']+'|'+v['best_single']['expert']+'|'+'|'.join(f'{x:.2f}' for x in (v['cost_aware_oracle_minus_best_single_USDT'],c['switches'],c['extra_switch_cost_USDT'],c['LONG'],c['SHORT']))+'|')
lines += ['',
    '仅60日、13段（尾部10日保留），无horizon搜索。各expert完整账户日收益只归一化到一个10k诊断财富，未相加满资金钱包；已付内部费用保留，仅另扣13.5bp/side×边界目标距离。独立穷举验证DP与单资本归因、费用不二扣。包含日历年/过去趋势状态winner、LONG/SHORT贡献与选中expert的内部费用/执行/换手。',
    '**它不是实际切换账户，也不是严格认证的全局可交易收益上界。** 边界实际持仓、拒单/最低金额/资本路径未重新模拟，真实oracle/静态ensemble/可行selector/placebo收益全部NOT_RUN。不可宣称regime alpha或稳定APR。',
    next_action,'',
    f'工件 `{review}`、`{oracle}`。复现：progress/bounded下 `run_cta_leaderboard.py --protocol protocols/PUBLIC_SMA50_200_DIRECTIONS_20261006_V1.json`、`PUBLIC_SMA50_200_LONG_SHORT_20261006_V1.json`、`FROZEN_EXPERT_LIBRARY_COMPLETE_20261006_V1.json`，每次明确未使用STATE目录/reports输出。统一复核 `review_short_cycle.py --strategy PUBLIC_SMA50_200 --producer <directions> --producer <long-short> --output <新文件>`；oracle使用 `oracle_expert_opportunity.py --protocol protocols/FROZEN_EXPERT_ORACLE_20261006_V3.json --producer <D099完整10账户> --producer <D100多空> --producer <D103多空> --producer <D104expert补齐> --producer <D101多空> --output <新文件>`。', '']
with (ROOT/'docs/SHORT_SELECTION.md').open('a') as f:f.write('\n'.join(lines))
with (ROOT/'docs/CTA_LEADERBOARD.md').open('a') as f:f.write('\n'.join(lines[:lines.index('### 非可交易oracle诊断：只测机会，不计投资证据')])+'\n\n完整方向、RAW情景与非交易oracle另见 [SHORT研究](SHORT_SELECTION.md)。未把oracle加入实际账户leaderboard。\n')
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as f:f.write('\n## D103/D104结果与自主决定\n\n'+summary+' 用户新优先级：冻结expert条件优势/selector为主候选，SHORT研究保持。'+o['decision']+'；'+next_action+' 工件 '+oracle+' SHA '+sha(ROOT/oracle)+'。不把单策略或过滤失败推广为SHORT无alpha。\n')
with (ROOT/'docs/OPEN_SOURCE_REGISTRY.md').open('a') as f:f.write('\n- D103/D104：复用jesse-ai/example-strategies MIT commit7c91e0a37bf62165790120d730442e4f6eb00364，third_party/jesse_example_smacrossover/smacrossover_original.py SHA453440d7b934c494934a1c56b3826d94638594f79ad4e4c7faaff36b96d33fae，原should_long/short/update_position不修改。现有public_sma_perpetual仅替换整余额sizing为共享10k/caps/past-vol，并使用COIN分钟成交；不是Jesse/Bybit原生复现。DC20/10、DC55/20、D096与SMA200参数不变；oracle DP/归一化分析是薄OWN_DIAGNOSTIC，不是新公开交易内核。NumPy/Polars沿登记版本，无新库、训练或行情下载。\n')
old=(ROOT/'docs/RESEARCH_STATUS.md').read_text();boundary=old[old.index('## 数据、账户与资源边界'):]
elapsed_text=','.join(format(p['elapsed_seconds'],'.1f') for p in producers)
boundary=boundary[:boundary.index('上一经济版本D101：')]+f"本轮10新完整账户、8冻结expert×2资金费条件；最多2并行，各2线程/1.2GB守卫；实际账户时间{elapsed_text}秒，RSS峰值{max(p['peak_RSS_bytes'] for p in producers)/1e6:.1f}MB、共享采样峰值{max(p['shared_RAM_sampled_peak_bytes'] for p in producers)/1e9:.2f}GB，新增账户目录{sum(p['owned_bytes'] for p in producers)/1e6:.1f}MB。区间并集计时和最新真实扫描见本轮close，未把历史peak/扫描当本轮。\n\n## 运维与证据\n\n8765沿用，原public/micro采集存活另报，不拼断档72h资格。无真钱/密钥/发单/付费/GPU/封存正文。完整公开hook状态、标的顺序、未来扰动、独立Decimal资金/NAV及原SMA200汇总逐行兼容已验。oracle为非因果机会诊断，真实切换回测/静态对照/placebo NOT_RUN，投资NONE。\n"
opportunity='；'.join(f"{v['unit']}增量{v['cost_aware_oracle_minus_best_single_USDT']:.2f}" for v in o['results'])
(ROOT/'docs/RESEARCH_STATUS.md').write_text('# COIN 当前研究状态\n\n投资资格 **NONE/CASH**；长期净APR **NOT_EVALUABLE**。\n\n## 最新实际经济结果\n\n'+summary+'\n\n## 当前研究主问题与下一项\n\n冻结趋势experts是否有足够大、可由过去信息预测的条件优势，能否成本后优于单expert与静态ensemble？八expert同BTC730日已补齐；60日近似oracle机会：'+opportunity+'。它保留已付成本并额外扣目标切换成本，但没有真实切换账户，不能称可交易业绩/独立证据。\n\n'+next_action+'\n\n当前仍保留原SMA200仅多风险效率参照及正SHORT多空挑战者；完整公开50/200不替换。D101硬过滤、D102无重入定义的CE与ML/4h网格暂停；reopen需具体新机制或独立数据，不让SHORT能力降级。\n\n[实际榜单](CTA_LEADERBOARD.md)；[完整经济证据与复现](SHORT_SELECTION.md)。\n\n'+boundary)
selected=read('.cache/d103_selected_snapshot.json')
for name in ('docs/RESEARCH_STATUS.md','docs/SHORT_SELECTION.md','docs/CTA_LEADERBOARD.md','docs/RESEARCH_DECISION_LOG.md','docs/OPEN_SOURCE_REGISTRY.md'):
    if name not in selected:selected.append(name)
c=dict(parent_commit=head,module='D103_D104_FROZEN_EXPERT_LIBRARY_AND_OPPORTUNITY',family='FROZEN_PUBLIC_EXPERT_LIBRARY',recipe=o['protocol'],
    references={review:r['status'],oracle:o['status'],'reports/SMA200_REVIEW_DEFAULT_GOLDEN_PUBLIC_EXPERT_20261006_V1.json':read('reports/SMA200_REVIEW_DEFAULT_GOLDEN_PUBLIC_EXPERT_20261006_V1.json')['status'],
        'reports/FROZEN_EXPERT_ORACLE_INDEPENDENT_20261006_V1.json':read('reports/FROZEN_EXPERT_ORACLE_INDEPENDENT_20261006_V1.json')['status'],
        'reports/FROZEN_EXPERT_ORACLE_SERIALIZATION_FAILURE_20261006_V1.json':read('reports/FROZEN_EXPERT_ORACLE_SERIALIZATION_FAILURE_20261006_V1.json')['status']},
    additional_tasks=[dict(id='76d5fe66e68140ed85c7a84aaacad7b8',expected_exit_code=0),dict(id='caab20de00ce463faff912df6e557627',expected_exit_code=0),dict(id='d718ccd72a394904b44355526d7f612f',expected_exit_code=0),dict(id='418208d509a94bdeae922f736fe20cbf',expected_exit_code=1)],
    source_paths=[p for p in selected if p.endswith('.py')],decision=o['decision'],next_action=next_action,primary_reference=oracle,
    economic_producers=paths,complete_accounts=10,runtime_directories=[p['run_dir'] for p in producers],
    closed='reports/FROZEN_EXPERT_LIBRARY_MODULE_CLOSED_20261006_V1.json',binding='reports/GITHUB_FROZEN_EXPERT_LIBRARY_SOURCE_BINDING_20261006_V1.json',
    prior_binding='reports/GITHUB_SMA200_CE_TRACE_SOURCE_BINDING_20261006_V2.json',selected_paths=selected,stage_script='.cache/stage_selected_frozen_experts.ps1')
save('protocols/FROZEN_EXPERT_LIBRARY_CLOSE_20261006_V1.json',c)
print(json.dumps(dict(status='FIXED_EXPERT_EVIDENCE_READY_FOR_EXISTING_CLOSE',summary=summary,opportunity=opportunity,next_action=next_action)))
