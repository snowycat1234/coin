"""Update existing state and append the actual D065 decision after closure."""
import json, os
from pathlib import Path
from quant.paths import ROOT
assert os.environ['COIN_TASK_ID']
STEM='DONCHIAN_ACTIVE_ALLOCATION_20261004_V1'
r=json.loads((ROOT/'reports/fast_research'/(STEM+'_DIAGNOSTIC.json')).read_bytes())
a=json.loads((ROOT/'reports/fast_research'/(STEM+'.json')).read_bytes())
f=json.loads((ROOT/'reports/fast_research'/(STEM+'_FINANCIAL.json')).read_bytes())
disk=json.loads((ROOT/'reports/DONCHIAN_ACTIVE_ALLOCATION_RESOURCE_20261004_V1.json').read_bytes())
assert len(r['paired_cases'])==f['financial_case_calls']==4 and all(p['net_increment_USDT']>0 for p in r['paired_cases'])
base=next(row for row in r['rows'] if row['allocation']=='ACTIVE_EQUAL' and row['cost']=='BASE27' and row['funding_unit']=='RAW_AS_FRACTION')
control=next(row for row in r['rows'] if row['allocation']=='EQUAL' and row['cost']=='BASE27' and row['funding_unit']=='RAW_AS_FRACTION')
summary='D065已完成：同原日线Donchian信号/July十币/连续303日/10k共享资本，仅raw改为激活预算。四新账户与四独立核账完整、末全清；净收益提高67.62–88.34USDT，全部固定成本/资金费解释同向。BASE/F净259.53→340.50，实际年波动8.18%→9.91%，分钟MDD9.34%→9.10%，换手3.01→4.76倍完整资本；不是匹配风险alpha。112未风险饱和日改变目标，131饱和日不变，信号/协方差成员一致。采用ACTIVE_EQUAL为研究挑战者、保留原EQUAL及两币HOLD主参照；投资NONE/CASH、长期APR不可评价。主要毛收益缺口与独立证据仍在，不按收益删币。D064旧预算失败及此次inline身份/首次CLI失败保留。当前下一优先恢复已授权但实际丢失的两路只读采集：已确认无进程、退出原因UNKNOWN，先三件套保存与断档核对；尚未恢复，不把旧running JSON当活任务。恢复闭环后选择入场不变、仅10日退出的有限COIN变体检验，尚未运行；不搜参/改成本/caps/启封。Git按实际SYNC_VERIFIED，未预造成功。'
for name in ['README.md','docs/RESEARCH_STATUS.md','docs/GOALS.md','docs/PROGRESS.md']:
    path=ROOT/name;old=path.read_text();head,rest=old.split('\n',1)
    path.write_text(head+'\n\n'+summary+'\n\n### D064及以前的历史状态（旧下一步按原时点阅读）\n'+rest)
with (ROOT/'docs/FAST_RESEARCH_TASK_CHECKLIST.md').open('a') as out:
    out.write('\n\n### D065当前模块位置\n\n'+summary+'\n\n- [x] 激活预算正常接口、完整四账户和独立目标/资金核验\n- [x] 同信号/协方差与131饱和日不变机制，四实际经济配对\n- [x] 原失败、代理/资金单位/实际风险边界及资源记录\n- [ ] 原公开采集恢复闭环（D066保存准备，尚未恢复）\n- [ ] 后续10日退出单因素完整账本（尚未开始）\n')
table=['| allocation | cost/unit | gross | fee | execution | funding | net USDT | vol% | MDD% | turnover |',
       '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
for x in r['rows']:
    table.append(f"| {x['allocation']} | {x['cost']}/{x['funding_unit']} | {x['gross_USDT']:.2f} | {x['fees_USDT']:.2f} | {x['execution_USDT']:.2f} | {x['funding_USDT']:.2f} | {x['net_USDT']:.2f} | {x['actual_daily_annualized_volatility']*100:.2f} | {x['minute_MDD']*100:.2f} | {x['turnover_full_capital']:.2f} |")
body='''

## D065 — 激活信号预算：完整单因素回放

### 改变与证据范围

只修改raw分配：EQUAL=min(.3,.6/N_members)；ACTIVE_EQUAL=min(.3,.6/N_active)，0active=CASH，未用满的单币cap预算不再重分。目标生成、活动runner、独立参考直接接入原正常模块；没有复制整套账户。prior20/SMA200、long/cash状态与严格退出、日线完成时钟、200预热、过去30日有符号协方差10%缩减、配置顺序与缺失/退出处理不变。平台多空能力仍保留，不将原无做空公开配方硬变双向。

2024-09-01至2025-07-01前303日、10k完整共享资本，abs.3/gross.6/逐仓1x、分钟成交/mark/事件资金费、原末5次退出不变。D064四保存控制按Git55798a1/source pins和全部工件哈希核对，没有重跑旧控制；新增仅四完整账户、四直接参考核账。Binance USD-M与Bybit当前用户费用仍跨场所代理；资金F/P解释、native filters/MMR/publication认证限制不变，已见开发不是unseen/APR/真钱。

### 实际经济结果

'''+ '\n'.join(table)+'''

四条件净增量分别80.96/88.34/67.62/74.93USDT，均末全清。BASE/F增量=毛+111.34−新增手续费/执行23.60−额外资金费6.78=净+80.96；不是删除旧成本后保留毛收益。实际年波动高1.73个百分点、平均gross/net8.99%→11.28%、峰gross/net20.00%→28.13%，平均逐仓抵押/NAV8.44%→10.78%、峰18.93%→27.81%。相同硬caps不代表风险匹配。

信号仍平均2.75/10、60全现金日；raw平均16.50%→40.99%，风险目标9.11%→11.43%，实际11.28%。3030目标行中167行、112日发生大于1e−12变化；131个原风险饱和日没有变化，协方差成员顺序全部一致。raw统一倍率在波动饱和时被缩回，改善只来自未饱和机会。top5正收益日占比19.95%→22.03%，集中度略高，不当分散优势。

BASE/F主要净贡献XRP413.91/BTC274.46/DOGE220.88；ETH−327.68/SOL−135.29/WIF−68.42。十一月+967.99、二月−570.52、六月−444.86，完整月桥见报告；不将月份拼赢家、不删除亏币。新的毛476.59仍低于同条件两币HOLD816.48；两币净670.63仍最高研究参照。十币HOLD marked363.02仍有原201.09USDT残仓与预算失败，不能把其marked优势说成现金收益。

### 验收、资源与真实失败

'''+f"单一新合成用例通过，含EQUAL直接对照/原信号/0-3激活/raw caps/过去协方差/未来扰动/顺序/缺失/CASH。独立四账户核验最大cash误差{f['maximum_errors']['cash']:.3g}USDT、ratio{f['maximum_errors']['ratio']:.3g}，原1e−7/1e−10容差；scope不扩大为全部冻结order sizing或原生执行。市场主体{a['elapsed_seconds']:.2f}秒、RSS{a['peak_RSS_bytes']}B、STATE{a['owned_bytes']}B，预算600MB/1800秒通过；共享实采peak{a['shared_RAM_sampled_peak_bytes']}B，金融RSS{f['peak_RSS_bytes']}B，hard4999999488/swap0/GPU0。模块STATE{disk['owned_d065_STATE_bytes']}B<800MB。物理scan{disk['ledger']['total_bytes']}B@{disk['ledger']['measured_utc']}，ROOT+整个D WSL VHD，间隔增长{disk['interval_total_growth_bytes']}B含其他任务，不称独占研究增长；Git后来新增不计此时刻。\n"+'''
失败保存：agent inline用了无USDT后缀的夹具，exit1，未完成比较且未重试；root首次金融CLI漏protocol/output，argparse exit2、未开始核账，V2补参数后同账本通过，没有改金融数学或重跑市场。原始任务与取证见FAILED_INLINE_PROBE和TASK_METADATA；旧D064十币输出预算失败未覆盖。

### 自主决定与下一项

采用ACTIVE_EQUAL为可配置研究挑战者；EQUAL留作控制、两币HOLD保留稳定最高净参照。投资NONE/CASH，开发证据不足以认证长期APR或alpha。固定成员预算作为主力暂停，reopen须新净/实际风险证据；保留能力。盲目扩币/调费/去掉亏币暂停，reopen须外生数据、成本或分散机制。Maker/原生费用与资金单位优势暂停，reopen须合法对应来源与实际成交证据；403/451不绕过。

实际发现两路原授权公开采集都无活进程，旧running JSON过期，退出原因UNKNOWN；当前先保存三件套/日志/checkpoint/audit与断档，再有限恢复，不启动v2、不拼健康资格。保存准备由D066独立STATE处理，不把它作为D065经济验收或已恢复。研究下一候选只改变20日退出为10日退出（20日入场/SMA200和预算/风险/成本均不动），用于检验持仓失效后的毛损益，而非靠降费或事后删ETH；COIN变体、四固定情景、新完整账本，尚未运行，不自动采用。

### 工件与复现

- protocol/market/financial/saved diagnosis：`DONCHIAN_ACTIVE_ALLOCATION_20261004_V1*.json`。
- 独立静态复核：`reports/DONCHIAN_ACTIVE_ALLOCATION_INDEPENDENT_REVIEW_20261004_V1.md`。
- 原接受370个来源不新增下载/QA；4市场账户/4金融调用/4保存控制/4配对、0model/HPO/locked/orders。

WSL通过`with_task_progress.sh → bounded.sh`使用原v8 Python和2线程；市场复现入口`multi_asset_portfolio.py --protocol protocols/DONCHIAN_ACTIVE_ALLOCATION_20261004_V1.json --pool-id LIQUIDITY_TEN --run-dir STATE/NEW_EXCLUSIVE --output reports/fast_research/NEW_EXCLUSIVE.json`。必须使用绝对路径、PYTHONPATH、同接受来源与Git/源码字节；新目录/报告/登记不得覆盖旧结果。独立核账须预绑定ACTUAL_BINDING，并完整提供protocol/actual/run-dir/output四参数。实际命令、环境与任务SHA见保存绑定。
'''
with (ROOT/'docs/MULTI_ASSET_PORTFOLIO_20261004.md').open('a') as out:out.write(body)
with (ROOT/'docs/RESEARCH_DECISION_LOG.md').open('a') as out:
    out.write('\n\n### D065后验决定\n\n'+summary+'\nBASE/F桥毛+111.337974−cost23.595362−fund6.782429=net+80.960183USDT。改变112未风险饱和日，131饱和日无变。净与回撤改善但波动、成本、换手及集中度增，不宣称同risk alpha；毛与两币参照仍有差距。下一实际任务恢复丢失采集，后续单一10日退出假设；均不是新的永久路线。\n')
with (ROOT/'docs/OPEN_SOURCE_REGISTRY.md').open('a') as out:
    out.write('\n\nD065沿用D064 pinned MIT Jesse Donchian原代码、license与commit，不修改vendor；仅COIN共享raw分配增加ACTIVE_EQUAL。原日线入场/过滤/退出未变，仍不是Jesse原生整个平台或Bybit成交复现。\n')
with (ROOT/'AGENTS.md').open('a') as out:
    out.write('\nD065活动日线Donchian新增EQUAL/ACTIVE_EQUAL正常raw接口；同信号/过去协方差/共享账户与风险caps不变。四303日账户+独立参考完整，采用激活预算研究挑战者，投资NONE/CASH。原EQUAL与D064失败/残仓保持Git可复现，不包装或覆写证据；当前下一优先原两路公开采集丢失后的三件套保存/断档与有限恢复。10日退出是尚未运行的下一单因素COIN假设，不自动把原配方变双向、不永久固定路线。\n')
print(json.dumps(dict(status='D065_EXISTING_DOCS_UPDATED_ACTUAL_DECISION_APPENDED',files=9)),flush=True)
