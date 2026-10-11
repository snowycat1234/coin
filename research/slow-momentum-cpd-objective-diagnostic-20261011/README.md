# CPD目标一致性：只读诊断，未训练

用户要求先核既有成本训练，再分解保存2048策略换手与近零仓位，
至多冻结一个有依据的下一方案等待核对。旧毛Sharpe配方仍STOP。
本轮模型推断/训练更新/钱包/新策略验证查询/下载0。

新数学只分解旧策略，不改变策略：相邻两日均eligible时，把目标变化按对称恒等式
分为signal和vol scaling，再加上前日持仓的价格漂移；边界/mask退出独立收费。
同时按真实交易量归类sign flip和same-sign amplitude。各分量可相互抵消，
不把其绝对值当成各自应付成本，也不称归因是反事实或oracle盈利。
近零统计阈值.001/.01/.05仅描述，不作为交易dead-zone。
BASE27完整费用逐项一致的Tensor数学通过有限差分，abs(0)明确采用子梯度0；
原生最低单/舍入/延迟/风险/资金费仍不由此变成可微或已认证。

预发表7focused测试PASS（此前6项记录保留），包括掩码退出、现金NaN、
符号反转、波动缩放、费用成交价交叉项/终端平仓及全部6个非kink坐标有限差分。
仓库检索覆盖27个现有本地分支tip SHA、152种匹配源码版本；
包括direct_path真实2fit和temporal真实4fit的own-cost路径目标，及v2/v3扣费teacher。
检索范围/所有对象OID见prefit/SOURCE_CATALOG.json；不是未恢复账本或全部历史正文的认证。

预算沿用1CPU/4GBAS/2GBRSS停止/共享8GB/GPU0/swap0/hard1200秒，
state输出2MiB、磁盘保留15GiB。先发布源码再作保存策略诊断。
