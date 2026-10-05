# COIN 当前研究状态

投资资格：**NONE/CASH**；长期APR **NOT_EVALUABLE**。

研究参照：Spot HOLD8与固定50/50 HOLD10+EXIT10，多空/N资产能力保持；模型方向暂未成为投资主力。

## 最新经济证据与决定

D086连续Mar–Jun2025共122日、10币同资本10k，完成16账户。BASE27/RAW_AS_PERCENT：原双向净-921.57，GMM门控净-48.06USDT；原毛损益-646.23、费用/点差/滑点合计275.37；门控毛损益1.03、成本49.10，原信号亏损与门控后成本吞噬分别成立。门控SHORT净-48.06，相对BEAR桶SHORT净-63.88。原/门控DD 12.03%/2.13%，vol 9.80%/4.27%，实际平均gross 16.46%/2.12%。HOLD净140.16、DonchianEXIT10净-353.58。四成本/资金费解释配对检验，门控保留为防御研究组件，未证明short alpha，也未达到投资资格。GMM相对BULL0/BEAR32/SIDEWAYS90/CRASH0；BEAR中心20d -5.18%但SMA200距离+22.05%，非绝对熊市真值。90日零目标不等于全部实际平仓，分钟gross/净仓与真实残仓保留。方向模型无重拟合，新GMM/Scaler各1；相关测试各2拟合；旧概率和三方向targets精确golden及独立目标/NAV/钱包复算通过。

采用：正常状态门控能力；保留GMM防御性研究组件；暂停其熊市short-alpha配方和原argmax方向配方。reopen：不同可得信息或状态机制在固定成本下产生可信净short增量/风险收益改善，并补足独立证据；不以换seed/调后验阈值重跑。投资候选仍NONE/CASH；元标签未运行，锁集未动，proxy与未知funding单位仍阻止晋级。

报告：[D086](MARKET_REGIME_20261005.md)；验收：`reports/MARKET_REGIME_ACCEPTED_20261005_V1.json`。D085原负结果与D076单位审计按Git保留。

## 下一有限研究选择

下一有限主任务是同一固定XGB的绝对过去趋势门控对照：用已有BTC SMA200/20d状态替代相对GMM状态，保留同账户、日期、成本和caps，最多新增4个账户、零direction fit/零搜索。本轮GMM全窗BULL=0，无法分辨过滤错误牛市空头与长期排除全部多头；此对照优先排除状态语义/覆盖错误，之后再决定是否值得做共享execute/reject meta-labeling。状态不是收益真值，过去BEAR桶中的short也不保证赚钱，不据结果改规则。

## 边界与运行

市场账户回放已结束；原两个采集任务保持，存活与有效独立证据天数分开报告。Binance USD-M行情/mark/funding配Bybit用户费用为跨场所代理；funding两单位解释均报告。已见历史、相同caps非相同实际风险；未清仓liquidated return NOT_EVALUABLE。无账户密钥/发单/真钱/Testnet/mainnet/付费/GPU/locked正文；5GB RAM、swap0、D40GB、10k资本/abs30%/gross60%/逐仓1x不变。资源及当前磁盘扫描见本模块收尾凭证；不以本轮收益年化长期APR。
