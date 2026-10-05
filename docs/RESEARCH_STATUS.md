# COIN 当前研究状态

投资资格 **NONE/CASH**；长期净APR **NOT_EVALUABLE**。

## 当前SHORT主线与实际结果

D096完成一个固定适配：每币20/10和55/20通道共同确认才允许SHORT，任一确认消失退出；多头forecast保持原规则，实际资本/covariance完整重跑。4个303日10币共享10k账户、0训练/搜参/新行情下载；两BASE门槛通过才补两STRESS，不扩大配方。四情景通过事前开发挑战者门槛=True。

|BASE/PCT 同产品/日期|净USDT|SHORT贡献|实际vol%|分钟DD%|
|---|---:|---:|---:|---:|
|原双周期多空|1058.97|-153.24|9.76|7.04|
|双通道SHORT确认|1578.24|572.59|9.67|5.39|

SHORT增量725.83，实际LONG减少206.55；不是删除交易保留毛收益。8/10币SHORT增量正；新账户付费平仓残仓0，旧双周期为含marked残仓NAV。BEAR过去BTC标签下SHORT仍-206.17，改进不等于解决熊市赚钱；BULL/BEAR/SIDEWAYS只是滞后描述，不是每币状态。

采用为已见开发SHORT主挑战者，原20/10仅多保留透明稳定参照；HOLD/CASH及旧负结果保留。不能从SMA200或ML失败推断所有SHORT无alpha。

[SHORT结果与复现](SHORT_SELECTION.md)；[统一经典榜单](CTA_LEADERBOARD.md)。实际账本/独立资金与目标核对、规则测试、日历/状态与逐币来源由 `reports/SHORT_SELECTION_ACCEPTED_20261006_V1.json` 及其SHA引用。

## 最新结果与下一有限工作

D098完成固定4h short确认的2个实际303日账户，0训练/搜索/新行情。PAUSE_FAST4H_RECIPE_RETAIN_D096；BASE/PCT新净1004.43（原1578.24），SHORT 191.81（原572.59），vol 9.11%、分钟DD 7.13%。不是旧账本删交易；完整资本、方向/成本、过去状态与实际风险见 [SHORT研究](SHORT_SELECTION.md)。

停止本303日的快线周期/阈值调整；将已固定最佳SHORT规则移至另一个完整下跌及随后反弹周期，优先补最小必要历史与透明基准；先核已授权/已有输入、当时可知标的资格与费用，保留两币对照。目的是检验跨周期有效性，不能按当前303日事后赢家声称独立收益。不改变资金/数据封存/风险权限。

D097已证明：旧10日线提高频率不能覆盖主要反弹，Chandelier默认完整24次持仓11次可更早触发但4月9日八仓仍未覆盖，保留备用、完整新CE经济账户NOT_RUN。能力不删除；暂停4h配方时reopen需新独立周期或具体噪音/持仓语义机制，不能同窗扫周期救参。

## 数据、风险与资源

Binance行情/funding配Bybit用户费用是跨场所代理；funding单位UNKNOWN保留两解释、MMR假设未原生认证。全部已见开发，不启封locked，不拼接独立账户，不把少数天年化成长期APR。完整资本10k、abs单币30%/gross60%、逐仓1x、无自动加保证金；新平均/峰值gross 15.31%/40.36%，同caps并不等风险。

共享RAM8,000,000,000B、CPU多核、D项目+整个WSL VHD150GB（120预警/135停新增/15预留）、swap0/GPU0；全部Python在hpc_linux经现有progress/bounded，新账户每任务2线程。真实运行区间/内存峰值/工件增长及整盘最新实扫见模块close。无真钱/密钥/发单/封存正文/付费服务。

## 运维

8765服务沿用，原public/micro断档已保存证据后有限恢复；旧public库不改，新collector_public_v3_20261006.sqlite3，micro同实现新会话RESTART_GAP；两采集任务存活需按当下状态核验。恢复不是72h连续或alpha证据，退出原因UNKNOWN。 见 `reports/CTA_COLLECTOR_RECOVERY_ACCEPTED_20261006_V1.json`；本次收尾将附当下PID/start_ticks。
