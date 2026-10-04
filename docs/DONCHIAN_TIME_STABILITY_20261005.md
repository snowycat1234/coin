# D068：退出改进的时间稳定性

## 本轮实际结果与决定

新增保存账本分析入口 `scripts/investment/donchian_time_stability.py`。读取 D065 EXIT20 与 D067 EXIT10 的八份日终净值，核对四种固定成本／资金费解释下的完整303日。无新账户、模型、调参、行情下载或回放；策略、仓位、风险、成本没有改变。

**全期改善有效，但跨时间稳定优势尚未得到确认。** 四种情景的7／30／60日圆形块区间全部包含零；事前固定的三个101日区间均为第一段小幅改善、第二段变差、第三段改善。保留 EXIT10 为开发研究配置、EXIT20为控制、HOLD_TWO为收益参照；投资候选NONE，保持CASH，长期APR不可评价。

BASE/F 原净340.50→497.16 USDT、实际年化波动9.91%→8.36%、分钟MDD9.10%→7.43%的D067完整回放仍有效。本轮没有产生新策略收益。完整资本仍10k；下面每段使用各自持续钱包的实际段前NAV，不能理解为三个新的满资本账户。

|固定时间段（含首尾日）|EXIT20净增额|EXIT10净增额|差额USDT|
|---|---:|---:|---:|
|2024-09-01—2024-12-10|1068.52|1071.27|+2.75|
|2024-12-11—2025-03-21|−214.93|−290.42|−75.49|
|2025-03-22—2025-06-30|−513.10|−283.69|+229.41|
|全期303日|340.50|497.16|+156.67|

其他三个情景的段差依次为：BASE/P +2.84/−76.19/+230.24；STRESS/F +0.48/−74.05/+233.38；STRESS/P +0.56/−74.74/+234.22。它们共用同一市场，不是四次独立验证，也没有匹配实际风险。

## 不确定性与集中度

复用未修改的 `quant.metrics.block_bootstrap_mean_ci`，每情景／块长2000次，固定seed20261005，共24,000次描述性重抽样。事前固定60日为主要描述，7／30日为敏感性，不在看到结果后选区间。BASE/F平均日对数收益差为 **0.4963bp**，区间如下（单位为日对数收益差×10,000）：

|圆形块长|2.5%分位|97.5%分位|包含零|
|---|---:|---:|---|
|7日|−2.8828|+3.1336|是|
|30日|−1.5491|+2.3897|是|
|60日|−1.0550|+1.8804|是|

60日对应303/60约5个完整块的数量尺度，不是估计得到的有效独立样本数。圆形首尾拼接、平稳性和块长适用性未经充分认证；短滞后相关较小不能排除长依赖。区间没有校正已有策略探索与选择，不作为显著性晋级、概率alpha、稳定APR或独立OOS证据；重抽样次数不会增加实际历史。

BASE/F 126日钱包增量改善、115日变差、62日无变化。二月增量366.81超过全期156.67；仅作算术集中诊断，减去二月贡献后为−210.15，减去六月后为−6.10 USDT；减去三月负贡献则为+586.12。**这些减法没有重新模拟资金和持仓，不是删日期后可交易的收益，也不会用于按月份选择赢家。** 月份、固定段与资产解释都是开发描述。

## 核对范围与限制

日终时间严格覆盖2024-09-02 00:00Z至2025-07-01 00:00Z，分别代表Sep1至Jun30；303行按UTC连续顺序相等。首日前值各自10000，不删除第一日。分别核对：

- 每账户日PnL累计 = 末NAV−10000 = 保存最终现金净损益，容差1e−7 USDT；末仓全清，日终与最终清仓桥一致。
- 每账户log收益累计 = log(末NAV/10000)；配对累计 = log(末NAV10/末NAV20)，容差1e−12。
- 月份PnL差与固定段log差分别累计回全期，不重置资本或拼接新的NAV。
- 保存报告、八份日账本、两个金融验收报告和D067配对报告均核对实际SHA；SOURCE/协议和现有环境绑定在运行前记录。

独立作者的标量／日期核对见[独立复核](../reports/DONCHIAN_TIME_STABILITY_INDEPENDENT_REVIEW_20261005_V1.md)。采用50位Decimal独立核对八钱包、12固定段和40月份，末PnL最大差6.82e−13 USDT、配对log最大差2.90e−15，实际任务53d0d530...closed0，0.416s/RSS77.70MB。只用3×37合成抽样独立核对圆形索引／分位规则，未重复实际24k区间端点估计。本轮不新增无关回归；源账户的金融验收范围仍见D067，不把日账本核对扩大成成交量、历史交易所规则或清算全面认证。

Binance USD-M数据加Bybit当前VIP0成本仍为跨场所代理，资金费单位UNKNOWN、F/P条件同时保留；历史费用区、原生数量/MMR规则与独立市场优势仍未认证。HOLD_TWO基础情景净670.63且风险较高，当前EXIT10仍少赚173.47；不能用本轮区间证明风险匹配超额。

实际主任务 `5c73a02b49ad46f9bd01dced77177469` closed0；24k抽样耗时0.941s，RSS97,591,296B、共享组采样398,954,496B，硬限4,999,999,488B、swap0/GPU0。八份原账本只读，没有复制行情。最近物理扫描仍是D067的27,557,747,504B@2026-10-04T16:21:37.233593Z，不冒称本轮新扫描或当前物理总量。

## 下一项自主选择

暂停继续搜索退出周期；重新开启需要新的退出机制或独立区间证据。保留EXIT10的实际全期经济改善，暂停其“稳定投资优势”声明；重开须独立历史／真实未来与可认证产品经济输入，不能靠增加抽样确认。

下一项选择：**只读现有成交、目标和净值，解释提前退出后再入场的机会损益与费用。** 以全303日所有可识别的EXIT10提前退出片段为范围，观察两版实际持仓状态差、退出后等待再入场与风险调整，专门解释二月防御和三月损失；不把旧多头曲线取反、不按亏币选池、不宣称任意平仓原因是因果。先建立有限机械解释，再决定是否值得单因素完整回放。相较新模型或退出网格，这能以低资源排除“更早退出普遍改善”及“亏损全是成本”的错误假设。下一项尚未启动。

## 可复现

确认已有原始STATE日账本仍在。以下命令保留原协议／报告，复制协议只更换运行ID与当前Git父提交，并写新输出；算法、数据、切分与随机种子不变。协议源哈希必须仍匹配，否则需明确新实验，不绕过核对。

```bash
cd /mnt/d/codex/coin
scripts/with_task_progress.sh --title 'D068新ID协议副本' -- env PYTHONPATH=src:. \
 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -c \
 'import json,subprocess,uuid;from pathlib import Path;p=json.loads(Path("protocols/DONCHIAN_TIME_STABILITY_20261005_V1.json").read_bytes());p["experiment_id"]="D068-REPRO-"+uuid.uuid4().hex;p["git_parent"]=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip();f=Path("protocols/DONCHIAN_TIME_STABILITY_REPRO.json");f.open("x").write(json.dumps(p,indent=2)+"\n")'
scripts/with_task_progress.sh --title '保存账本时间稳定性复现' -- \
 env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 PYTHONPATH=src:. \
 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python \
 scripts/investment/donchian_time_stability.py \
 --protocol /mnt/d/codex/coin/protocols/DONCHIAN_TIME_STABILITY_REPRO.json \
 --output /mnt/d/codex/coin/reports/fast_research/DONCHIAN_TIME_STABILITY_REPRO.json
```

原协议及小型实际结果位于 `protocols/DONCHIAN_TIME_STABILITY_20261005_V1.json` 与 `reports/fast_research/DONCHIAN_TIME_STABILITY_20261005_V1.json`；新ID避免重复registry事件。跨机器复现需原D盘STATE工件，Git不包含行情或账户原始文件。
