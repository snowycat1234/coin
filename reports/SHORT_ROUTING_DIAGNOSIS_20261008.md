# SHORT 路由机制诊断：盈利组合尚未解决熊市做空

## 本版决定

投资候选仍为 **NONE/CASH**。保留 FAMILY_EW 为低暴露的 long/cash 研究参照，暂停现有 Hedge/FixedShare 配方的参数搜索；SHORT 继续作为主要研究问题。新工作是只读经济诊断，不是新策略业绩，不改变旧专家参数、交易、账户或证据。

接手后核对实际服务器，发现本机 e17e113 状态已落后：公开主分支为 2b04122，已完成专家组合分支为 **5346a5c**。本轮从后者继续；没有重复旧 28 账户回放、Transformer 训练或访问原始封存数据。服务器原有未提交报告测试保持。

## 钱赚在哪里，亏在哪里

下表复核的是旧 2023 年完整 365 日账户，每个独立共享本金 10,000 USDT，不能相加。Binance USD-M 数据配 Bybit 费用仍是跨场所代理。RAW/PCT 为未认证资金费单位的两种条件解释，不能选择更盈利的一列作为事实。

|旧 BASE27 配方|净 USDT RAW / PCT|SHORT 净贡献 RAW / PCT|实际空头开仓成交腿|分钟 MDD RAW / PCT|日收益年化波动 RAW / PCT|平均 gross RAW / PCT|
|---|---:|---:|---:|---:|---:|---:|
|FAMILY_EW|749.20 / 859.62|0 / 0|0|4.25% / 3.90%|5.27% / 5.27%|11.42% / 11.42%|
|FIXED_SHARE|762.98 / 904.09|0 / 0|0|4.67% / 4.32%|5.91% / 5.97%|12.79% / 12.94%|
|HEDGE|239.54 / 399.45|−274.47 / −253.60|28|5.44% / 5.03%|5.93% / 6.00%|13.37% / 13.37%|
|SMA200_SIGNED|440.77 / 601.25|−830.52 / −845.80|40|9.69% / 9.54%|10.42% / 10.43%|23.76% / 23.76%|

FAMILY_EW 和 FIXED_SHARE 在全部登记压力情景也都没有实际空头。FixedShare 相对 EW 多赚的 13.78 / 44.47 USDT，伴随更大 gross、波动和回撤，不能解释为做空改善或稳定路由优势。

HEDGE 的空头毛价格损益已为 **−266.60 / −243.12 USDT**，手续费及执行成本仅 11.07 / 10.51 USDT，资金费 +3.21 / +0.028 USDT。主要失败机制是方向选择，降低费用无法修复毛亏。三个实际空头 episode 均亏；2023 年初一段亏 −167.58 / −153.42，占全年空头净亏约 61%。SMA200 同期亏 −541.81 / −547.61，占全年空头净亏约 65%。这只有三段已见空头事件，不能当作大量独立熊市样本。

交易归属使用实际 signed 数量和闭合持仓；一段中的加减仓腿不计为独立机会。反转必须拆平旧/开新，资金费归属为开仓之后、平仓当时之前持有的数量。此处归因不是“删空头后保持旧多头利润”的反事实策略。

## 一个结构性事实

冻结 FAMILY_EW prior 为 CASH=1/3、HOLD=1/3、六个趋势 expert 各 1/18。旧共同风险包络满足每个趋势目标绝对值不大于 HOLD 目标，所以：

```
combined_target >= HOLD/3 - sum(abs(six trend targets))/18 >= 0
```

两种资金费解释的全部 730 日共同时间轴均验证这一条件，浮点容差 1e−12。因此这个冻结等权配方不能净做空，即使六个趋势 expert 都看空。结论只限该 prior 和该风险包络；动态权重可以形成负目标，不能据此称 FixedShare 或整个 N 资产系统不支持 SHORT。

## SHORT 机会不能由一个总 Oracle gap 证明

预先固定 60 日决策块、切换距离每侧 13.5bp，只复用旧连续专家净收益，比较未来已知的 SMA/HOLD/CASH 与 HOLD/CASH 路径。每年六个完整 60 日块加一个 **5 日尾块**，不扫描周期。

|已见年份|加入 signed SMA 的 shadow 净增量 RAW / PCT|含 SMA 路径的 SHORT 目标日数|两路径切换次数|
|---|---:|---:|---:|
|2022|+2049.48 / +1985.12 USDT|305|2 / 2|
|2023|+0.05 / +0.07 USDT|0|4 / 3|

这是**非因果的旧净收益重定基诊断**，不是新的真实共享钱包、不是全局钱包上界，也不是纯 SHORT alpha：SMA 还会改变多头暴露。2023 的优选段里，SMA 被选中时均为正仓位；大 Oracle 机会主要可由 HOLD/CASH 择时解释。2022 下跌与 2023 反弹提供的信息不同，不能把总 Oracle gap 直接当作可预测的空头机会。

## 实际实现与验证

- 新增 `scripts/research/diagnose_short_routing.py`，复用已冻结账户、缓存和原 Oracle DP；零 fit、零新账户、零参数扫描。
- 112 份交易/资金费/目标/NAV 工件 SHA、旧 cache 身份及源文件绑定通过。独立 Decimal 现金桥复核 28 账户，最大误差 **3.18e−12 USDT**。完整分钟 NAV 证明复用旧最终核验，不冒称本轮重跑。
- 服务器 hand-check 三项测试通过：100 开空至 90/110 平仓、部分平仓、资金费正负和同时间归属，以及固定权重包络/动态反例；独立子 agent 只读复核未发现阻止本轮限定结论的错误。
- reviewed 运行 **0.746 秒**，单进程峰值 RSS **92,540,928 B**；2 线程、8GB 上限、swap0/GPU0、300 秒超时。该 RSS 不是整个服务器共享组历史峰值。新诊断只读取已经批准的旧开发工件。
- [机器结果](SHORT_ROUTING_DIAGNOSIS_20261008.json)，SHA `842840d974e43d13ab9f871d0d6939c00583046dc12235b1ec0e7e58b18e01de`；[测试](SHORT_ROUTING_DIAGNOSIS_TESTS_20261008.xml)；[协议](../protocols/SHORT_ROUTING_DIAGNOSIS_20261008.json)。服务器保留首次及 reviewed 工件，不覆盖旧结果。

## 下一步选择与 reopen condition

先检验冻结 SHORT 信号的**下跌延续与反弹是否能由过去信息区分**，优先复用已有合法多币开发数据及公开趋势方法，先核熊市事件覆盖再运行有限对照。不能只靠 BTC 三段亏损继续堆复杂度，也不能回到人工退出规则扫描。D106 人工 map 的失败保留，不重复当新方法。

文献线索：[Garg 等《Momentum turning points》作者公开论文](https://people.duke.edu/~charvey/Research/Published_Papers/P158_Momentum_turning_points.pdf)研究慢/快动量在转折的差异；它支持先诊断延续/反弹机制，未证明本项目或 crypto 存在可交易优势。不复制代码，也不在本轮添加深度模型。

下一模块 **NOT_RUN**：只注册少量 past-only 状态与一个固定评价窗口，先检查跨资产、跨阶段的方向信息，再决定是否值得一对真实账户对照。不能按本轮看到的亏损日期挑样本；所有已见历史继续标开发。新假设若无稳定方向信息，则保留强公开单策略/静态参照，暂停新的 selector 拟合。

Hedge/FixedShare reopen：存在跨阶段成熟反馈的稳定条件优势或已验证投影瓶颈，且能在同钱包对照里取得成本后增量。ML selector reopen：预测排名/方向胜强静态与 placebo，不能仅凭训练分数。SHORT 方向不因旧配方失败永久删除。金融认证、独立证据及多资产验证仍不足，投资资格 NONE/CASH。

## 可复现命令

在服务器上使用新建独占输出目录；旧外部 STATE 必须存在且 SHA 一致：

```bash
cd /home/ubuntu/coin/expert-aggregation-v1-repository
systemd-run --user --scope --quiet -p MemoryMax=8000000000 -p MemorySwapMax=0 \
  env PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 \
  PYTHONPATH="$PWD:$PWD/src" timeout 300 \
  /home/ubuntu/coin/coin_collector_v3_fixed/work/research-venv/bin/python -B \
  scripts/research/diagnose_short_routing.py --repo "$PWD" \
  --state /home/ubuntu/coin/execution-state/expert-aggregation-v1-20261007 \
  --protocol protocols/SHORT_ROUTING_DIAGNOSIS_20261008.json \
  --output /home/ubuntu/coin/execution-state/short-routing-diagnosis-REPRO-NEW
```

已部署运行时脚本/协议在 execution-state；发布本版源码后以上路径可直接使用。命令不需要模型 API、账户密钥或交易所发单。
