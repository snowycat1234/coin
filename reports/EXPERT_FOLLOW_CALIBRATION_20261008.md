# 七日专家跟随：日频代理与真实共享钱包校准

决定：RETAIN_DAILY_PROXY_FOR_LIMITED_SCREENING_ONLY；零训练，投资资格NONE/CASH。

|资金费解释|真实净PnL|代理收费终平净PnL|差额|价格PnL差|成本差|资金差|
|---|---:|---:|---:|---:|---:|---:|
|0.01|102.898330|105.911231|-3.012901|-3.245351|-0.232388|-0.000061|
|1|103.188475|106.193336|-3.004861|-3.243366|-0.232394|-0.006112|

前七日按原冻结专家跟随，第八日清仓。对齐七个延迟执行区间；额外平仓日不是额外策略持有收益。
代理marked值与收费终平值分开；后续可延续selector不应被强制每周平仓。旧连续60日标签没有改名为7日标签。
标签成熟按执行结束后1微秒。周整点尚未成熟的上一周结果不能作为反馈。

One fixed already-seen week cannot validate error stability, ranking fidelity or annual return.
This is Binance USD-M with Bybit fee assumptions, not native Bybit evidence; funding units remain conditional1/.01.
Closed calibration does not certify marked continuation utility, exact current-position switch cost, intraminute risk caps or future selector efficacy.
No new strategy adopted; original losing windows and full recipe pause preserved.

复现：python -B scripts/research/calibrate_expert_following.py --protocol protocols/EXPERT_FOLLOW_CALIBRATION_20261008.json --state /home/ubuntu/coin/execution-state/expert-follow-NEW，8GB/swap0/GPU0受限scope。

## 独立复核、采用范围与下一步

独立只读复核由short_evidence_review完成：净值桥、多空合计、协议SHA、7/8日区间与成熟时钟均核对。原始报告/JSON保持服务器来源，本文追加解释。

真实净收益约102.90/103.19，SHORT净187.99/195.24，LONG净−85.10/−92.05；这是固定首周能力/语义核对，不是新策略改进或稳定APR。成本约16.185，资金费净现金+0.00289/+0.28903。主要proxy差来自价格损益−3.24，成本差约−0.232抵回；没有证据把差额进一步单独归因于0.99缓冲或某个成交规则。

真实分钟MDD约1.557%，proxy日频MDD约0.504%；proxy不能认证分钟风险。首成交2024-01-02 00:01:00.000001 UTC，最终成交2024-01-09 00:02:00.000001，比proxy名义终点晚60秒。原生闭合结果反馈须等实际最后成交后，另须满足源数据可用时钟。当前活动helper已支持传入实际末成交延长成熟；新反例已通过，未重跑已完成钱包。

JSON里的marked_net仅为执行价格端点估值加回终平成本，不是observed mark NAV，也不是可直接采用的持续仓位训练标签。首次切换诊断也不等于NAV路径校正；CASH需收费退出，soft组合应按合成净目标收费一次。未来marked与当前仓位标签须另注册。

保留既有日频内核作廉价条件筛选；完整经济/风险判断仍用原分钟共享钱包。投资NONE/CASH，无新model或策略采用。下一项选择：以固定专家、单个7日选择问题，低容量共享多输出Ridge比较成熟反馈/市场与意图/联合输入；先注册marked可得性、purge/embargo和有限拟合预算。没有新的训练或回放在后台运行。

实际账户阶段10.749秒、两worker各一线程、新工件约1.42MB；进度relay终态延迟显示15.4秒是客户端显示估计，不是账户计时。8GB/swap0/GPU0，RAM峰值UNKNOWN。两账户完整11520分钟；engine子进度文件最终10081是周期快照，完整性由summary与独立账户审计确认。
