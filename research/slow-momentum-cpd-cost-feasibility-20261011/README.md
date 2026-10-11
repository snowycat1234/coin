# 保存策略的固定成本可行性核对

结果：`NO_FIXED_COST_PROXY_MARGIN`，按冻结条件停止经济后续，未运行原生钱包。
2048 CPD等种子组合毛价格收益代理0.071561%，固定成本0.250928%，
成本后−0.179366%；成本消耗毛收益的3.506倍，盈亏平衡单边3.850019bp，
低于既有BASE27单边13.5bp。相对趋势臂成本后仍改善0.564526个百分点，
但不能作为绝对可投资优势。以下均为483日静态参考资本的加总代理，非净APR/真实钱包收益。

|2048政策|毛价格代理%|固定成本%|成本后代理%|漂移换手/参考资本|盈亏平衡单边bp|
|---|---:|---:|---:|---:|---:|
|trend2001|−0.181663|0.273389|−0.455051|2.025102|−8.970538|
|CPD2001|−0.178030|0.204233|−0.382264|1.512840|−11.767962|
|trend2002|−1.058326|0.394132|−1.452458|2.919490|−36.250374|
|CPD2002|−0.316767|0.367020|−0.683787|2.718669|−11.651540|
|trend2003|−0.125134|0.267557|−0.392691|1.981901|−6.313844|
|CPD2003|0.709481|0.259422|0.450059|1.921643|36.920527|
|trend等种子|−0.455041|0.288852|−0.743893|2.139642|−21.267153|
|CPD等种子|0.071561|0.250928|−0.179366|1.858724|3.850019|

3/3种子成本后相对增量均正，但仅CPD2003绝对为正，未据此选取。
原始目标敞口很小：趋势/CPD等种子平均gross0.903676%/0.727372%，
峰值3.263043%/2.374184%，单资产峰值1.468151%/1.094338%；原始目标无cap超限。
这些是保存策略意向目标，不是原生实成交敞口。按10kUSDT参考名义，CPD的
1562/2224非零调仓量小于10USDT；尚未模拟最低单/数量步长/延迟/partial fill。
把目标变大或忽略最低单会改变政策，本轮未这样处理。

停止对象是本次加密货币CPD适配的固定费用价格代理，不能据此否定论文传统期货结果、
证明已测资金费的真实钱包亏损，或把正相对Sharpe称为净收益。

用户授权只读保存策略的经济核对；不再训练、不作新模型推断、不运行钱包。
主结果为共同2048步终点，趋势/CPD两臂和2001/2002/2003全部成对。
等种子组合在目标敞口层先平均再计换手。1024仅另存历史参考，不选择模型、步数或日期。
三个既有开发验证区块合计483日，各自收费进入/退出；不称全新样本外。

运行前冻结[协议](PROTOCOL.json)，SHA
`75bf5b62e8495808ea0763e22669e97f5834c83af88f20323e391049553582da`。
只用保存position与决策时波动率还原原始目标；下一日收益仅作成熟标签。
计算固定参考资本下价格漂移后的持仓变化，终端以最后标签收益后的名义收费平仓。
BASE27每边5.5bp手续费+4bp半价差+4bp滑点，13.5bp名义单边。
手续费按不利成交名义计收，执行摩擦只扣一次。
盈亏平衡成本是毛价格收益/漂移换手的有符号单边bp；现金无换手为未定义。
输出加总价格收益代理和成本，不复利、不把Sharpe换算净APR。
资金费未测，不能视为已知零；真实共享钱包资金/风险/可成交量/最低单未绑定。

首个可运行里程碑：9项金融反例PASS，四份旧manifest154文件、原拟合4源码及12旧外部模型字节保持。
prefit清单是预发表checkout元数据收据，其HEAD不等于未提交执行源码的发布SHA；
发布后另存有执行源码SHA的清单，保留此前收据。独立只读源码审阅未见阻塞。
恢复清单核114既有Git分片本地OID/type/大小；无大blob正文提取或新下载。
2023H2月度交易/标记分钟包、2024H1归一化数据身份与每日/资金费包可定位。
2023H1完整分钟覆盖未定位；旧native61只证明2024May-Jun分钟网格，未证明本次Jan-Apr。
资金费当前区间行覆盖/时钟、CPD→原生targets适配及收费终端闭合仍待绑定。
清单的July3–10六成对钱包范围仅说明最小潜在可核验范围与预算，不是执行方案或授权。
若主2048 CPD等种子组合在固定成本后无价格收益余量，按冻结条件停止经济后续。

本次已触发该停止条件，未制作可执行钱包方案。恢复清单的条件范围为
已有最早验证折叠的2023July3–10七个日历日、两臂×三seed六独立10k钱包，
同BASE27/1x/caps/分钟容量/真实资金费与收费平仓；7日只是预算上限，成熟决策/终端时钟尚待绑定。
条件预算1CPU、4GBAS、2GBRSS/共享8GB停止、1200秒总时限、无下载，
旧Git原始包≤37,957,161B、归一化工作≤200MiB、账本≤64MiB、15GiB磁盘保留。
该预算未启用，也未扩张当前2MiB诊断输出预算；成本条件不支持启动。

执行源码[cf9f2bd5](https://github.com/snowycat1234/coin/commit/cf9f2bd5cc675dd53ef4ebc2a39b984aa8c35976)
已先发布并核远端SHA，14公开文件字节逐项PASS后运行唯一成本核对。
[主结果](results/RESULT.json)、[全3864日级记录](results/DAILY.csv)、
[单独1024历史](results/HISTORY_REFERENCE.json)、[独立审计](results/AUDIT.json)、
[已发布源码恢复清单](results/SOURCE_RECOVERY.json)均保存。
独立Decimal循环580核对PASS，最大残差2.842e−14；复核原毛价格代理一致。
本次完整测试为9focused金融反例；全仓NOT_RUN，旧实现未修改。
主算术0.204秒，guard含启动0.612秒；截至审阅完成的9次bounded调用无资源停止，
最大采样RSS45,871,104B/host870,699,008B，state实际1,271,109B，
扫描时磁盘剩余29,588,533,248B。采样不是内核峰值；云护栏为已授权恢复实现，未冒充旧WSL字节。

最小复现（不同未存在的output路径；所有Python沿用有界launcher）：

只需公开Git文件即可独立重算两checkpoint全部成本汇总、原毛代理和日级一致性，
无需恢复模型或下载行情（生成独立新审计文件）：

```bash
audit_dir=$(mktemp -d /workspace/coin-cost-audit.XXXXXX)
cp research/slow-momentum-cpd-cost-feasibility-20261011/results/{RESULT.json,HISTORY_REFERENCE.json,DAILY.csv} "$audit_dir/"
COIN_CPD_STATE="$audit_dir" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python -m modules.slow_momentum_cpd.audit_cost_feasibility --output "$audit_dir"
```

完整原runner额外核实际工作区旧12模型字节，故以下需保留原模型state；
它们仍按仓库规则留state，未伪称由Git重新恢复。公共算术复现可用上段独立审计。

```bash
export COIN_CPD_STATE=/workspace/slow-momentum-cost-state
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
  -m pytest modules/slow_momentum_cpd/test_cost_feasibility.py \
  --basetemp="$COIN_CPD_STATE/tests" -q
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
  -m modules.slow_momentum_cpd.cost_feasibility --output "$COIN_CPD_STATE/results"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
  -m modules.slow_momentum_cpd.audit_cost_feasibility --output "$COIN_CPD_STATE/results"
bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
  -m modules.slow_momentum_cpd.cost_recovery_inventory --output "$COIN_CPD_STATE/recovery-new.json"
```

当前冻结预算：1CPU/4GB地址空间/2GBRSS停止/共享8GB停止/GPU0/swap0，
hard1200秒，当前新state输出2MiB，磁盘保留15GiB。
科学尝试仍3/12freshfit/累计13824updates；本轮新增训练/模型推断/钱包/下载均0。
collector2026Mar–Sep保留锁未打开，2026Q1/Q2账本仍不可访问，另一收益分布研究未编辑。
