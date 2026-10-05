# COIN 当前研究状态

投资资格：**NONE/CASH**；长期APR **NOT_EVALUABLE**。

## 最新经济证据与决定

D090固定公开SMA50/200原双向意图+一个共享execute/reject拟合；4原SMA账户均在103804分钟逐仓清算要求处停止，全122日净收益NOT_EVALUABLE，不补零。4过滤账户完整122日，净-84.26至-14.44USDT，BASE/PCT净-21.06、毛88.12、成本109.25、资金费0.07，DD5.48%、vol8.17%；同口径HOLD净140.16。原fit1次，恢复阶段fit0；最终恢复只新增2账户、10账本按SHA复用，整个实验实际独立账户12，未拼钱包。V1完整性断言错误和V2工件250MB停止保留，V3在同预算仅补缺两项。固定intent独立窗口参考、目标/每分钟NAV/资金费/钱包及停止参考通过；停止mark只核声明价格。

暂停本拟合配方与旧固定XGB门控配方，保留模型、多空和退出能力；本轮没有合格投资方案NONE/CASH。旧XGB负结果不能外推short无alpha，更不能外推所有公开CTA。重新开放ML需经典benchmark明确且提出可证伪的净/风险增量假设。

报告：[D090](SHARED_META_20261005.md)；验收：`reports/SHARED_META_ACCEPTED_20261005_V1.json`。

## 当前主线

当前主线转为公开、冻结参数、零训练经典CTA leaderboard：真calendar12m TSMOM、SMA200 signed trend、Donchian20/10与20/10+55/20+12m等权forecast。各币独立信号，past30 inverse-vol和原signed covariance缩放进入同一个10币/10k账户。同Mar–Jun122日、两成本与两资金费解释，LONG_ONLY/SHORT_ONLY/LONG_SHORT/CASH/HOLD，最多56真实账户，零拟合/零搜参。有预热不足则UNKNOWN，不冒充短窗12m；本金/caps/逐仓1x/持续平仓/风险停止保持。先验证short增量与状态机制，再允许ML挑战。

## 边界

已见开发/跨场所代理，不是unseen/Bybit原生；资金费UNKNOWN、历史规则假设和停止账户独立范围保留。5GB RAM、swap0/GPU0、D40GB、abs30%/gross60%不变；不读取钥匙/锁集正文、不发单。采集存活单独报告。当前磁盘收尾扫描见module closed凭证。
