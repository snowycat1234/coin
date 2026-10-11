# 保存策略的固定成本可行性核对

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

最小复现（不同未存在的output路径；所有Python沿用有界launcher）：

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
