# 熊市训练样本恢复：实际观测修补，不是新投资策略

## 改变与决定

投资资格 **NONE/CASH**，净收益/APR本轮 **NOT_RUN**。定位旧selector失败的一个重要输入限制：月档缺少官方日档已有的整日行情。复用现有官方URL/CHECKSUM下载及规范化内核，26个日档核SHA/CRC，只补30,240个真实分钟行，另建派生视图，原manifest/数据/实验均不覆盖。零拟合、零钱包。

|训练支持（两资金费条件解释相同）|修补前|修补后|
|---|---:|---:|
|2024 seen开发窗前合规训练日|266|516|
|2025 seen开发窗前合规训练日|632|882|
|2022完全成熟熊市日|0|157|
|2022固定不重叠周块|0|22|
|共同完整特征/反馈首日|2022-12-27|2022-07-21|

157日是重叠日标签，不是157个独立样本；22周仍不足以证明稳定投资优势。2022夏季之前长特征仍处于自然预热，不伪造早期训练支持。资金费单位仍未认证，两尺度1/.01同时保留。Binance USD-M行情配Bybit成本仍为跨场所代理。

## 可核对的来源

- SOL/XRP原月档遗漏2022-02-26..28与04-01..02，10个对应官方trade日档均完整。
- BTC07-31、五币10-02及2023-02-24的缺失mark观测可由日档恢复；原共有11个不完整资金区间变为0。严格过去mark/原结算事件/费率均沿用，没有放宽整点或猜资金单位。
- 官方日档仍有5个不完整mark日，共缺27分钟：ETH07-12缺10、07-13缺1；SOL07-12缺6、XRP/DOGE07-12各缺5。新视图保留这些缺口和complete_mark=False；不能据此认证完整分钟风险/清算回测。
- 初次固定全日要求在第14个档案处停止，实际完成13/34，失败工件保留。随后另冻OBSERVED协议，只接纳真实观测，复用14个已核验缓存；未改旧协议或失败结果。没有追加URL、插值、补零、拟合或钱包。

旧2024/2025已评分参考效用保持≤1e-12一致，旧源SHA与原有限资金事件mark保持精确。独立只读复核核官方ZIP/SHA、残余缺口、特征/标签golden与成熟/purge计数；30,240补行来源依赖冻结修补凭证，复核不再次重建全部月表或标签。首次特征1e-12断言失败，诊断最大差1.725e-12（SOL vol_z）；所有评分滚动窗的原始close/high/low/quote_volume/complete_kline精确相同，属于滚动累计舍入差。保留初次审阅失败与差异工件，特征按1e-10数值容差复核，**金融标签1e-12门槛没有改变**。

## 验证与资源

9个相关反例2.780秒通过（merge真实缺行、精确重叠/1ULP冲突、身份/可得时钟、资金整点）；直接金融内核没有重写。独立复核见[结果](BEAR_SUPPORT_INDEPENDENT_REVIEW_20261008.json)，成功复核0.329秒；[特征舍入诊断](BEAR_SUPPORT_FEATURE_DELTA_20261008.json)零拟合。成功源修补/派生/标签耗时30.898秒；第一次退出进程26.510秒，保留失败开销。新状态目录实测28,047,124B，第一次保留736,056B（复核前扫描时刻）；不是全服务器磁盘用量。

单worker/单线程，8,000,000,000B硬限、swap0/GPU0；旧内核峰值RAM **UNKNOWN**。服务器当次可用24,542,121,984B，保持16GiB预留。本机D项目+整WSL VHD最近实际扫描45.430GB（2026-10-07 19:13:47UTC，非本次新扫）。任务34/34，服务器已success/inactive/dead；没有后台训练。

## 下一步选择

采用新派生输入视图；暂停旧“无主要熊市训练”的Ridge负结果对策略能力的泛化解释，保留其实际失败结论。新输入满足此前reopen condition，下一项只注册一次**同容量、同专家/特征/成本/日期/门槛**的条件信息复验，隔离训练支持修正的作用；不扫描模型/参数。仍不稳定则不救Ridge，转向固定绝对/相对趋势共享钱包组合对照。不能把恢复样本称为恢复alpha；投资NONE/CASH不变。

## 复现与工件

运行源commit `6dc8bbc660bab9d4f16e35c1efb98cbe3e706a3c`；事前[原协议](../protocols/BEAR_SUPPORT_REPAIR_20261008.json)及[保留缺口协议](../protocols/BEAR_SUPPORT_OBSERVED_REPAIR_20261008.json)。[原始结果](BEAR_SUPPORT_REPAIR_20261008.json)、[来源追踪](BEAR_SUPPORT_SOURCE_TRACE_20261008.json)、[旧缺口](BEAR_SUPPORT_OLD_HOLES_20261008.json)、[首次停止](BEAR_SUPPORT_FIRST_STOP_20261008.json)、[回归](BEAR_SUPPORT_TESTS_20261008.xml)。数据/ZIP/面板留服务器外部STATE，路径/SHA在结果中，不入Git。复用[Binance官方数据说明](https://github.com/binance/binance-public-data)的档案与CHECKSUM机制。

原bounded服务完整环境见commit与日志；核心入口（须新state且继承8GB/swap0/GPU0/cgroup及WORK_DIR/RAW_CACHE_DIR守卫）：

```text
python -B scripts/research/repair_bear_support.py --protocol protocols/BEAR_SUPPORT_OBSERVED_REPAIR_20261008.json --state /home/ubuntu/coin/execution-state/NEW_UNIQUE_STATE
```

已完成状态不可重跑/覆盖；后续应直接复用绑定的派生输入。本模块未消费locked、未用账户密钥、未发单。
