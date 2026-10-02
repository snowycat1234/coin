# D036独立方法短评（未执行，2026-10-03）

仅阅读保存的小JSON、目标/账本源码与artifact recon；未读Parquet、运行Python、重放账户或重做QA。三窗547/122/90分别是已见SCREENING，各账户初始10k、36bp、同风险规则但实际风险不同。排名翻转不是分散化证据。P/H共用2h入口、BTC/ETH多头；hybrid改变退出频率及40h→20h物理lookback，并非仅延迟变化。

## 事前预算筛选建议

保留root提出的阈值，不增加优化网格：122与90两窗各自daily signed net USDT Pearson<0.80且worst10% overlap<0.70；至少两窗存在一方固定tail日期内另一方signed净PnL总和>=0；三窗各自实际仓位overlap<0.80。全部满足仅支持消耗一次固定50/50配方的共享资本回放预算，不取得投资/统计资格。任何失败或UNKNOWN即暂停此配方，不事后改阈值、权重、窗口或尾部比例。

必须在读数组前冻结口径：

- 净日delta=NAV_t−NAV_prev，首日prev=10000；费用/执行成本已经扣除。return相关仅辅助披露，不代替USDT主指标，不进行事后vol匹配。
- 当窗N日，k=ceil(0.10N)。按signed净USDT delta升序选k日，UTC日期破同序；必须有k个真实负日，否则tail UNKNOWN。overlap=交集日数/k，不能误用Jaccard。零方差相关UNKNOWN，不能填0。
- tail保护使用另一方在已固定T_i日期的signed净delta总和；不累计正收益、毛收益或另选对方尾期。另一方接近现金/零损失是防御性降暴露，不是正收益对冲；近零结果记录rounding sensitivity，不能借EPS翻转正负。
- 每窗独立O=Σ分钟,币种 min(wP,wH)/Σ分钟,币种 max(wP,wH)，w=实际marked_notional/NAV。双方现金自然不贡献分母；分母0为UNKNOWN。不平均逐分钟0/0、不合并三窗让547日掩盖后窗；dust与实质暴露分开说明。
- 日期、完整日数、时间轴和币种必须exact对齐；不inner-join后丢缺日。daily.date对应该UTC日最后一分钟，接minute.close_us需映射次日00:00。保存的terminal持仓保持MTM，不能都称dust或现金收入。

三窗仓位均<0.80是最苛刻条件：高仓位重合仍可能有退出尾部差异。可作为保守预算选择，但失败只表示当前固定50/50缺少足够证据，不证明所有组合无效。均应披露共同负日数量/损失额、tail共同损失额、各策略gross/net/费用/换手、实际vol与minute/daily MDD；相关或仓位重合单独不能构成采用理由。

## 真正下一回放的边界

仅当上述预登记筛选通过，固定原始因果目标w=0.5wP+0.5wH，在单一10k账户、同caps/30day风险层/native费用/latency/lot/capacity下执行；明确共同风险层只作用一次。同币intent先净合并，不能平均旧NAV、旧已缩放持仓或旧成交，也不能把两套10k账户当共同资本。成本、现金可负担性、净收base及terminal再由真实账本决定；不能预设成本等于旧成本均值或组合已赚钱。

源/日期/成本错配属于工程FAIL，经济未计算；正确统计但筛选失败则保存经济阴性、暂停固定组合。重开需要不同因果信号/信息或新的合法未来证据，不重训同标签或择月赢家。Candidate NONE、长期净APR未证明、Binance价格/Bybit费用代理与native执行限制保持。
