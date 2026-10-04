# D063 独立静态复核（2026-10-04）

复核者：本轮 cost_scope_review 子agent。范围为当前正常账户、bybit_cost_inputs、活动perpetual_directional的交易及CASH分支；未编辑源码、未跑测试或历史账户、未访问API。

初审发现四处问题：通用cost硬下限、STRESS合同RT27误标、非等额摩擦一律除2、恢复不核配置与每腿费用。第二次审查发现CASH首次与缓存尚未更新cost identity。最终当前源码：交易/首次CASH/缓存CASH已统一入口；缓存仅允许无交易无持仓无资金费/NAV10000现金账户，重建摘要而复用零工件。RT43与来源更新，不等额月报/总額按实际比例且不重复扣款。risk abs30%/gross60%、1x/MMR/filter/no topup不变；新cost需context/显式费区/TAKER，均匀区标为未认证。

恢复检查逐腿拒绝改费率/摩擦与contract而保留原journal；旧snapshot仅缺cost_context时允许已知RT27元数据误标迁移，保留旧journal。最后未发现新的实质问题。此结论是静态复核，真实验收引用V2结果；V1异常文案匹配失败保留，不能称全绿或配置篡改已通过。费用来源身份/接口不代表历史盘口、真实费区或投资优势已认证。