# 同一保存决策的资金费遗漏检查

**原STOP、标签和七门槛保持；本轮拟合/新预测/开发读取/wallet均0。** 负资金费系数只否定本轮预设正方向，不能据此否定资金费输入的全部预测价值；此前训练MSE改善1.41%保持。

固定2022的248条保存预测、50市场周：对照43个short，增强52个，其中43个相同，只有9个新增探针贡献成对资金费。数量严格沿用原价格成本公式隐含的 `.12/Pentry` 个币/参考资本，入退场费用不重算或改变。short现金为 `q_abs × sum(rate_fraction × charge_mark)`；正率收款、负率付款，不按小时再乘，不用卖空名义收入当本金，不随mark再平衡。

| 全2022，固定假设 | 原价格成本差值 | 资金费贡献边界 | 价格成本+资金费差值边界 |
|---|---:|---:|---:|
| 原率按小数比例 | −4.163982bp | [−0.464642,−0.150130]bp | [−4.628624,−4.314112]bp |
| 原率按百分数再×.01 | −4.163982bp | [−0.004646,−0.001501]bp | [−4.168628,−4.165483]bp |

单位均为每市场周初始参考资本的基点，非APR/NAV或原生利润。表中假设：有值的前一分钟mark与真实收费mark偏差最多±20%；缺mark时收费mark落在入场价±20%；入/退场±60秒结算可计或不计，用逐事件保守上下包络。1%/5%范围及两个原半年度完整结果也保存，未据结果挑范围。**这些条件边界不跨0，遗漏资金费在这些假设内不足以逆转负成对经济增量；没有无条件真实现金结论。**

原率从官方CSV数值保留到Parquet，归一化代码不做比例换算。官方API `interestRate=.0001` 与FAQ每8小时`.01%`相符，支持小数比例惯例，这是来源推断，未完成旧档案逐事件API交叉认证；故另列×.01而不静默选单位。[官方API字段](https://developers.binance.com/en/docs/catalog/core-trading-derivatives-trading-usd-s-m-futures/api/rest-api/market-data) 与 [官方资金费公式](https://www.binance.com/en/support/faq/detail/360033525031) 说明资金费取决于结算时持仓数量×mark×率，仅持仓才收费；当前文档的时间偏差并不认证2022实际持有边界。

档案有真实事件率，但 `past_mark_price` 只是严格早于事件、年龄不超过60秒的已完成分钟close，**不等于收费mark**。9个差异探针共198候选事件，原描述区间 `(D,D+7日]` 内189事件：3个缺分钟mark；连同可选边界共5个缺mark，未补零，精确/中央现金点值均为UNKNOWN。共同持仓另3个缺mark在同数量同结算规则下精确抵消，但两臂绝对资金费现金仍UNKNOWN。事件唯一性、名义间隔及窗口双侧括号核验通过，不删坏月份。

一次官方 `/fapi/v1/fundingRate` 小查询返回 **HTTP451地区限制**，响应已保存；没有改域名/代理、重试或用凭证。该接口提供每笔收费mark，但本环境未取得。最小后续是在合法可访问环境取得这198个候选事件的收费mark并核对率单位，明确9个探针的边界持有次序；仍使用保存决策、不重拟合。真实账户另外需要执行后的实际数量/订单与保证金风险路径，本检查不能充当原生钱包。

5个相关测试通过；独立Decimal50审计从原2022Parquet重新核对198事件率/mark、9固定数量和72边界标量（81标量总计），最大误差1.067e−17。独立算例：1200参考名义、入价100得到12币固定short，mark110/90、率+.0001/−.0002，收付合计−.0840；随mark改变名义不是再平衡数量。审计首次读取Arrow空值None的类型错误已修正，失败收据保留，现金结果没改。全仓测试NOT_RUN。

## 最小无拟合复现

在当前研究分支checkout和已有Python/NumPy/PyArrow环境，用新STATE复用已有Git对象恢复小档案，然后核算、独立审计：

```bash
task_state=/workspace/short-funding-economic-reproduction
revision="$(git rev-parse HEAD)"
COIN_CPD_STATE="$task_state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python research/short-funding-residual-20261011/experiment.py \
  --mode preflight --state "$task_state"
COIN_CPD_STATE="$task_state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python research/short-funding-residual-20261011/funding_cash_check.py \
  --state "$task_state" --archive "$task_state/source/features.zip" --source-commit "$revision" \
  --protocol-sha256 42633ccce70a45063883103adaf629aaf8888d4069580d906d0f1cfcbc61c461
COIN_CPD_STATE="$task_state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python research/short-funding-residual-20261011/audit_funding_cash.py \
  --state "$task_state" --archive "$task_state/source/features.zip"
```

预检不拟合、输出预测或读开发值；若当前Git对象没有数据来源e0d3400b，先常规fetch包含它的研究分支。核算实际执行于已公开并读回的 `dc8a1bc3a826e31ae7185a958cb1231766dc151f`，冻结协议先发布于a7ca8984。沿用1CPU/4GB地址/2GBRSS/1200秒/GPU0/swap0守卫；各步骤完整耗时与真实采样峰值见收据。原模型、结果、数据补丁与collector锁未变。
