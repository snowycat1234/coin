# D067：更早退出的真实经济检验

## 本版改变与结果

只把已固定COIN日线Donchian的持仓退出从previous20低点改为previous10低点；原previous20上沿突破/SMA200入场过滤、ACTIVE_EQUAL、过去30日协方差10%下缩、July十币、连续303日、完整10k、abs.3/gross.6/逐仓1x、费用/摩擦/两资金费解释及5次末退出均不变。200日连续预热/缺失重置/有序身份保留。支持多空的平台保持，当前配方仍long/cash。新增正常keyword接口，不复制账户或交易引擎。vendor类/指标/许可证字节保持；10日退出是COIN变体，不冒称原Jesse配方。

四完整436320分钟新账户、四独立直接目标和资金核账、四保存控制配对均真实closed0，末仓全部清空，未实现盈亏/终末名义为0。旧D065退出20四账本只读，不重播、不后验放大NAV。当前规则研究配置采用退出10，保留20控制和HOLD_TWO收益参照；投资NONE/CASH，长期APR NOT_EVALUABLE。

303日全资本收益不是年化APR。表中vol为实际日收益年化波动，MDD为分钟净值回撤；各成本/单位解释是同市场敏感情景，不能作为独立OOS。

| policy | cost/unit | gross | fee | execution | funding | net USDT | vol% | MDD% | turnover |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| EXIT20 | BASE27/RAW_AS_FRACTION | 476.59 | 26.17 | 38.07 | -71.86 | 340.50 | 9.908 | 9.103 | 4.758 |
| EXIT10 | BASE27/RAW_AS_FRACTION | 625.97 | 23.53 | 34.22 | -71.06 | 497.16 | 8.362 | 7.427 | 4.278 |
| EXIT20 | BASE27/RAW_AS_PERCENT | 474.11 | 26.29 | 38.24 | -0.72 | 408.86 | 9.918 | 8.868 | 4.779 |
| EXIT10 | BASE27/RAW_AS_PERCENT | 624.44 | 23.62 | 34.35 | -0.71 | 565.76 | 8.374 | 7.315 | 4.294 |
| EXIT20 | STRESS43/RAW_AS_FRACTION | 477.60 | 26.13 | 76.00 | -71.77 | 303.69 | 9.908 | 9.322 | 4.750 |
| EXIT10 | STRESS43/RAW_AS_FRACTION | 626.31 | 23.49 | 68.34 | -70.97 | 463.51 | 8.368 | 7.599 | 4.271 |
| EXIT20 | STRESS43/RAW_AS_PERCENT | 475.14 | 26.24 | 76.34 | -0.72 | 371.84 | 9.918 | 9.088 | 4.771 |
| EXIT10 | STRESS43/RAW_AS_PERCENT | 624.78 | 23.58 | 68.60 | -0.71 | 531.88 | 8.380 | 7.445 | 4.288 |

BASE/F净增156.667941 = 毛价格+149.376889 − 成本增(-6.490599) + 资金费改善0.800453 USDT。主要是持仓价格路径改善；不能把整笔平仓利润归给订单原因。更早退出实际减少了总换手，费用与执行成本同时减少，未通过删除成本、降低费率或关闭风险减仓制造结果。四条件方向一致，净增156.67–160.04。

BASE/F平均/峰值gross（亦net，因为此配方仅多/现金）11.2845/28.1274%→9.0878/23.4280%；平均/峰值逐仓抵押物/NAV10.7784/27.8098%→8.5974/21.7669%。实际vol9.9076→8.3624%、MDD9.1025→7.4271%、完整资本换手4.7584→4.2776。相同caps未匹配实际风险，不宣称同风险alpha。347目标行/91决策日改变，144信号状态行改变；入场规则不变不代表实际入场交易相同。

## 钱在哪里赚、在哪里亏

BASE/F资产净贡献：BTC+371.26、DOGE+331.88、XRP+182.80、PEPE+64.45、WIF+10.56；ETH−261.53、SOL−96.90、ORDI−76.92、WLD−28.44，SATS0。它们是同一共享账户的可核对分拆，不按贡献事后洗币池。

|连续月份|exit20 net|exit10 net|增量USDT|
|---|---:|---:|---:|
|2024-09|67.88|67.88|0.00|
|2024-10|90.42|86.02|−4.40|
|2024-11|967.99|987.56|+19.57|
|2024-12|−349.01|−342.85|+6.16|
|2025-01|314.86|317.33|+2.47|
|2025-02|−570.52|−203.71|+366.81|
|2025-03|248.42|−181.02|−429.45|
|2025-04|−34.64|8.19|+42.82|
|2025-05|49.96|39.87|−10.10|
|2025-06|−444.86|−282.09|+162.77|

月份是一个持续钱包的资金增量，不是独立满资金账户，也不据月份赢家切换。二月/六月防御改善与三月反向损失并存；更早退出可能错过后续恢复，具体交易/重新入场机制尚需诊断，不把相关性写成已证实因果。November净987.56大于全期497.16，集中性仍明显；top5正收益日份额22.03→19.55%只是描述。

保存D064同BASE/F强参照HOLD_TWO net670.6307、vol10.4896%、MDD11.2296%、meanGross18.1307%、turnover2.1912；本版仍少赚173.47但暴露/实际risk更低，未认证优越性。HOLD_TEN同情景旧marked363.0158且有末201.09名义残仓、原预算失败不变；只能比较marked NAV，不能称其清仓投资收益。CASH固定USDT0收益为无仓条件参照，不包含现金生息。

## 采用与下一步

采用exit10为当前规则研究配置，20为控制；所有研究配置都不是真钱候选。最重要瓶颈转为跨时间状态稳定性、反复选择后的独立证据，以及跨场所/资金单位/历史规则认证。下一只用已保存配对日收益做固定时间段与依赖敏感的不确定性诊断，验证是否由少数月份支撑。0新策略/市场账户/HPO，不重新拟合、选日期或拼NAV。重抽样只是假设下描述，不增加历史长度、不能认证独立市场/alpha。

退出参数搜索暂停，reopen需新的退出机制或独立区间证据；按亏币删池、无来源的低成本/资金费单位选优暂停，reopen须合法单位/原生摩擦或外生分散来源。当前403/451限制无条件变化，不再次访问或绕行。能力保持，不永久否定趋势或空头方向。

## 实际验证、资源与失败

新直接窗口反例passed1，涵盖10日该退出而20日保留、严格等号/排除当前日、next-day reentry、SMA只入场、ACTIVE预算/协方差/caps、未来扰动/orderedN/缺失reset/CASH。首次相对protocol路径调用真exit1发生在测试之前，V2只修绝对调用；原失败/源/任务保留，不追认通过。

独立金融直接previous20 high/previous10 low/SMA200状态参考，不调用生产target/hook；原金融数学与容差保持。四金融调用最大cash1.4552e−11USDT/ratio1.7097e−14，容差1e−7/1e−10。完整市场冻结订单quantity sizing未全部独立重建，独立已成交腿/钱包/分钟NAV/资金费与目标核验范围如实限定。另有[只读复核](../reports/DONCHIAN_EXIT10_INDEPENDENT_REVIEW_20261004_V1.md)，复核作者也是新反例作者，此身份已披露。

市场600.446秒/RSS727.409MB/owned185.207MB/shared实采峰1.488GB；独立37.891秒/RSS1.241GB，GPU0。新增STATE合计185.218MB，低于800MB预算。最近物理ROOT+整个D盘WSLVHD27,557,747,504B@2026-10-04T16:21:37.233593Z，区间整体增长203,950,271B包括原采集/Git，非专属市场输出；shared生命周期峰3.263GB非模块峰。守卫5GB/swap0/40GB与32/36GB阈值保持，最终扫描时间已发布8765，后续文件不在该时刻。两路原公开采集保护，没有新API、下载、QA、模型/密钥/发单/locked。

Binance USD-M行情+Bybit当前VIP0成本仍为跨场所代理，真实费区/数量/MMR历史认证与资金单位仍UNKNOWN；fraction/percent两解释并列，不按收益选单位。已见303日只是开发筛选，不是独立长期APR或投资资格。

## 复现与工件

协议/市场/金融/保存诊断：`protocols/DONCHIAN_EXIT10_20261004_V1*.json`、`reports/fast_research/DONCHIAN_EXIT10_20261004_V1*.json`；原370来源接受链复用。确切环境/命令/任务SHA保存在run bindings及模块task archives。历史研究在本模块Git源码、相同接受清单与新独占目录重现，原结果不覆盖。

```bash
scripts/with_task_progress.sh --title 'D067创建独占复现身份' -- /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python - <<'PY'
import json, uuid
from pathlib import Path
root = Path('/mnt/d/codex/coin')
spec = json.loads((root/'protocols/DONCHIAN_EXIT10_20261004_V1.json').read_bytes())
spec['experiment_id'] += ':REPLAY-' + uuid.uuid4().hex
with (root/'protocols/D067_REPLAY_EXCLUSIVE.json').open('x') as stream:
    json.dump(spec, stream, indent=2)
PY
scripts/with_task_progress.sh --title 'D067新独占目录复现' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin:/mnt/d/codex/coin/tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python /mnt/d/codex/coin/scripts/investment/multi_asset_portfolio.py --protocol /mnt/d/codex/coin/protocols/D067_REPLAY_EXCLUSIVE.json --pool-id LIQUIDITY_TEN --run-dir /home/xflops/coin-state/NEW_EXCLUSIVE --output /mnt/d/codex/coin/reports/fast_research/NEW_EXCLUSIVE.json
```

复制协议只改变登记身份，源/市场/参数/预算不变，防止使用旧experiment_id覆盖或重复既有START。`D067_REPLAY_EXCLUSIVE.json`和`NEW_EXCLUSIVE`必须是新的协议/目录/报告；已存在就改用另一新名称，禁止覆盖。独立核账须先以新actual与新task冻结ACTUAL_BINDING，然后完整给protocol/actual/run-dir/output四绝对参数，不能直接复用已执行金融目录。本版正常Git push/远端一致仅以事后SYNC_VERIFIED为凭证。
