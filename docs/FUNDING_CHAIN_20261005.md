# D076：资金费原字段到保存钱包的有限核对

D076已独立读20份BTC/ETH原资金费归档、1818原事件，与HOLD8/固定组合8保存钱包14544条资金费/真实先前成交逐项核对；缩放一次、ms原clock、符号、event前仓位与严格过去mark时间/总资金费及净桥一致。另按BUY/SELL gross量/首持仓clock重建quantity，10k+成交cash_delta+资金费重建8末NAV，未将抵押物记利润。未发现错误，原账户/策略不改；单位物理定义/官方结算发布clock仍UNCONFIRMED，source校验与条件账本通过不能升级原生/单位认证，已有403/451不重试。BASE/F组合比HOLD8多付14.05USDT资金费，四情景净仍低，非重复入账或符号问题。保留HOLD8收益参照/组合防御挑战者，投资NONE/CASH、长期APR不可评价。主0.817s/RSS75.37MB，独立0.351s/RSS29.74MB；0新回放/fit/HPO/API/下载，原5GB/swap0/GPU0/40GB保持。停止无新来源证据的单位调查；下一先核对同窗BTC/ETH Spot源与现有库存/收到资产扣费入口，齐全后以真实产品价格和完整本金做一组有限Spot/永续HOLD对照，判断资金费负担与额外现货成本/基差影响，不把旧永续账本删除资金费改叫现货。尚未启动。

## 问题、改变与结论

新增一个直接读取已接受原CSV与保存账本的小型审计入口，未复制账户或修改策略。原20份资金源校验和/SHA、1818数值/事件逐项一致；calc_time按ms×1000，保留归档毫秒偏移而不强制移回整点。原始数值转换为float64后未换单位；本样本Decimal原文本与float round-trip文本差最大0，不代表binary float在数学上精确保留所有十进制小数。两种条件scale只在结算入口应用一次。

主核对从早于event的实际position_delta重建quantity，子agent独立实现另以BUY/SELL gross_quantity与首次持仓clock重建，资金费在同刻成交之前。1816持仓事件/每钱包、2无过去mark零仓事件均一致；负rate给多头正收入、正rate给多头支出，所有金额按保存Decimal字符串计算。独立重建10k+成交cash_delta+资金费=末NAV，保证金内部划转不进入利润。本样本只有实际多头/现金；参考中正负q手算不宣称重新验收活动空头入口。

| 完整10k、303已见开发日 | HOLD8资金费 USDT | 组合资金费 USDT | 组合−HOLD8净 USDT |
|---|---:|---:|---:|
| BASE27_RAW_AS_FRACTION | -91.86681501 | -105.91514868 | -14.89524981 |
| BASE27_RAW_AS_PERCENT | -0.92268854 | -1.06450136 | -0.69273958 |
| STRESS43_RAW_AS_FRACTION | -91.81451474 | -105.81938697 | -21.72360130 |
| STRESS43_RAW_AS_PERCENT | -0.92216234 | -1.06353775 | -7.60633853 |

BASE/F组合原gross多10.70、fee/exec多11.55、资金费多付14.05，净少14.90。单位假设显著影响绝对净值，两条情景为各自重新模拟的真实完整钱包，不能把F资金费后验乘.01替代P回放；本轮只核保存结果，不制造新收益。配对排序在原四条件一致，足以保留防御用途判断，不能据此确认任一单位或长期alpha。

## 官方证据与剩余缺口

本轮有限检索的[官方binance-public-data README](https://github.com/binance/binance-public-data)描述CHECKSUM保证归档完整性，未给出本次fundingRate CSV字段单位定义。[Binance官方资金费说明](https://www.binance.com/en/support/faq/detail/360033525031)说明资金费现金方向与按持仓价值计算的一般公式；该公式不是CSV字段与API同事件数值对应的证明。此前正式API parity请求受访问限制终止，本轮0 API请求、不使用镜像或替代端点绕过。缺口是官方archive物理单位定义，或可合法访问的同币同结算事件官方API/归档值对应；拿到其中明确证据才reopen单位认证。不能根据量级或哪条收益更高选解释。

严格过去mark时间和保存值的计算已核，市场mark原数值QA复用原已接受金融报告，本轮不重读分钟价格，不认证精确官方charge clock、publication、Bybit原生行情/filters/MMR或可交易盈亏。旧F/P报告、失败/API限制及原单位UNKNOWN全部保留，未改写其成功标准。

## 实际运行与复现

主审计与独立复核各一次实际closed0；首次元数据验收把含采集参数的两个进度父进程也计入而拒绝，修正为原.venv准确argv后另行验收，原失败源/closed1任务保存，不重跑科研；输入无新数据/训练/回放。20源zip+CHECKSUM+normalized合计读取65,586B，另读取保存JSON账本；该值不含receipt与wallet文件，也不是磁盘增长。共享峰是当前boot资源组观测366,342,144B而不是隔离本任务峰。最近真实整盘测量28,451,150,938B@2026-10-05T02:17:18.163809+00:00，早于本轮，不将其当新扫描；本轮小报告/代码增长另据selected文件统计，采集增长未精确重扫。

```bash
scripts/with_task_progress.sh --title '资金费来源链路核对' -- env POLARS_MAX_THREADS=2 PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/audit_saved_funding_chain.py --protocol protocols/FUNDING_CHAIN_20261005_V1.json --output reports/fast_research/FUNDING_CHAIN_REPLAY_NEW.json
scripts/with_task_progress.sh --title '独立成交现金复核' -- env PYTHONPATH=/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B docs/archive/FUNDING_CHAIN_USED_METADATA_20261005_V1/independent_review.py --protocol protocols/FUNDING_CHAIN_20261005_V1.json --primary-result reports/fast_research/FUNDING_CHAIN_REPLAY_NEW.json --output /home/xflops/coin-state/OWN_NEW_DIRECTORY/RESULT.json
```

历史复现须checkout协议parent_commit，并从本模块提交恢复审计源及协议，形成与本轮相同的运行前工作区；output必须新路径、STATE目录预先新建。主/独立报告及task实际元数据另保存于本模块metadata目录。投资现金、研究参照保持；下一产品对照先验证可用源，不假定已开始或数据齐全。原两路采集本轮验收时实际存活，但该有限观测不是连续健康天或72h保证。Git同步仅按实际远端后验宣布。
