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

## 最新定位与下一有限工作

D097只读诊断：五个最大BEAR分类亏损日40个资产日期，旧10日退出线仅3个触发；默认原生Chandelier22/3仅1个，4月9日均未触发。独立旧线与新组件因果核对PASS。暂停单纯提高原线检查频率；补核24次原持仓的CE状态保护，11次可更早触发，但4月9日八仓此前仍未触发。完整CE净/风险及再入场NOT_RUN，保留备用，五日截面不能淘汰其整体能力；没有新钱包或策略收益。全303日初开/后续加空净496.38/+76.21，不能断言加空整体有害，更不能删除加仓费用保留毛收益。关键问题转为长周期看空与短周期反弹的冲突，详见 [SHORT研究](SHORT_SELECTION.md)。

下一有限主任务：在D096稳定SHORT确认上，只选择一个公开快慢周期冲突规则：单币已完成4h趋势转为上涨时把short降为现金，长周期仍共同看空才重新允许short；先固定公开周期与成本、核对可得性/清仓语义，再两个BASE完整账户，只有净/SHORT/实际风险门槛通过才补压力情景。避免只按BTC慢状态，也不因为五个最差日事后删交易。零模型搜索，不调ATR倍数；当前新规则及经济指标NOT_RUN。

## 数据、风险与资源

Binance行情/funding配Bybit用户费用是跨场所代理；funding单位UNKNOWN保留两解释、MMR假设未原生认证。全部已见开发，不启封locked，不拼接独立账户，不把少数天年化成长期APR。完整资本10k、abs单币30%/gross60%、逐仓1x、无自动加保证金；新平均/峰值gross 15.31%/40.36%，同caps并不等风险。

共享RAM8,000,000,000B、CPU多核、D项目+整个WSL VHD150GB（120预警/135停新增/15预留）、swap0/GPU0；全部Python在hpc_linux经现有progress/bounded，新账户每任务2线程。真实运行区间/内存峰值/工件增长及整盘最新实扫见模块close。无真钱/密钥/发单/封存正文/付费服务。

## 运维

8765服务沿用，原public/micro断档已保存证据后有限恢复；旧public库不改，新collector_public_v3_20261006.sqlite3，micro同实现新会话RESTART_GAP；两采集任务存活需按当下状态核验。恢复不是72h连续或alpha证据，退出原因UNKNOWN。 见 `reports/CTA_COLLECTOR_RECOVERY_ACCEPTED_20261006_V1.json`；本次收尾将附当下PID/start_ticks。
