# COIN 当前研究状态

投资资格：**NONE/CASH**；长期APR **NOT_EVALUABLE**。

研究参照：Spot HOLD8与固定50/50 HOLD10+EXIT10，多空/N资产能力保持；模型方向暂未成为投资主力。

## 最新经济证据与决定

D088仅改变同一固定趋势门控的方向mask为SHORT_ONLY，新增4个完整122日10币共享10k账户，零拟合/搜索；20个旧账户按SHA复用，未拼接钱包。BASE27/RAW_AS_PERCENT净43.56USDT（完整资本0.4356%），原固定LONG_SHORT净-259.85，GMM净-48.06，HOLD净140.16。SHORT_ONLY毛75.42、费用/执行31.87、资金费0.01；LONG=0且独立核每分钟q<=0，新4账户实付平仓/残仓0。分钟DD 1.95%、实际vol 2.90%、平均gross 1.62%；caps相同不代表与HOLD实际风险相同。四成本/资金费解释净+24.50至+45.03，BEAR桶均负（BASE/PCT -20.86），SIDEWAYS +65.95、BULL -1.52。每情景9个零目标平空请求FIVE_ATTEMPTS_EXPIRED，正收益日仅16/122，top5正日占正日利润69.7%；状态日归因不是因果alpha。全1220预测和三方向默认目标golden精确一致；独立资金/NAV/目标核验及只读复核通过，new4/reused20范围分开。

保留SHORT_ONLY为研究挑战者（RETAIN_FOR_RESEARCH_NOT_INVESTMENT），暂停固定LONG_SHORT配方，能力保留。投资候选NONE/CASH、长期APR NOT_EVALUABLE；已见开发、跨场所代理、未知资金费单位和退出超时仍限制声明，不宣称稳定熊市alpha。暂停方向reopen需不同可得机制在固定成本下出现可信净/风险改善并补独立证据，不靠无限调参。

报告：[D088](TREND_SHORT_20261005.md)；验收：`reports/TREND_SHORT_ACCEPTED_20261005_V1.json`。D085/D086原结果与D076单位审计按Git保留。

## 下一有限研究选择

下一有限主任务：同一SHORT_ONLY信号的零目标平仓持续重试对照，检验5次过期后继续留空是否影响小幅正收益。先固定协议，仅改变该退出重试机制；最多新增4个完整账户，零模型拟合/搜索。保留费用、成交容量、必要风控、资本及caps，用相关平仓反例和旧默认golden复核，不删除旧交易/成本或免费平仓。若退出修正后无增量则暂停配方；正结果也只保留研究，独立/native资格仍未满足。

## 边界与运行

市场账户回放已结束；原两个采集任务保持，存活与有效独立证据天数分开报告。Binance USD-M行情/mark/funding配Bybit用户费用为跨场所代理；funding两单位解释均报告。已见历史、相同caps非相同实际风险；未清仓liquidated return NOT_EVALUABLE。无账户密钥/发单/真钱/Testnet/mainnet/付费/GPU/locked正文；5GB RAM、swap0、D40GB、10k资本/abs30%/gross60%/逐仓1x不变。资源及当前磁盘扫描见本模块收尾凭证；不以本轮收益年化长期APR。
