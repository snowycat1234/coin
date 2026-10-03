# D049：固定Turtle方向对照与交易成本诊断

当前投资选择CASH/NONE，研究强基准HOLD。方向能力已验收；下面均为已见历史、Binance输入配Bybit VIP0费用的条件代理筛选，不是原生Bybit执行、独立未来资格或长期APR。

## 实际经济对照

共同UTC窗口2024-09-01至2025-07-01前，303日/436320分钟，每账户完整资本10000USDT，BTC/ETH、逐仓单向1倍，无追加保证金；abs单币30%/共享gross60%、过去30日有符号协方差目标10%、.99buffer、原延迟和容量。新LO/SO各4费用/资金费条件共8完整账户；对照D048保存LS/HOLD，CASH理论独立空仓0。不重放旧账户/QA、不拼NAV、不选择更盈利资金费单位。

|成本|资金费条件|方向|净收益%|毛价格PnL|fee USDT|spread+slip USDT|funding USDT|换手倍|实际vol%|分钟MDD%|
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
|BASE27|RAW_AS_FRACTION|LONG_ONLY|-1.2864|452.1687|215.2525|313.0949|-52.4598|39.1368|7.3671|6.5390|
|BASE27|RAW_AS_FRACTION|SHORT_ONLY|-4.6961|-114.0926|157.6622|229.3267|31.4736|28.6658|5.4340|7.9937|
|BASE27|RAW_AS_FRACTION|LONG_SHORT|-5.7669|388.0339|384.6755|559.5282|-20.5242|69.9410|9.0104|11.1215|
|BASE27|RAW_AS_FRACTION|HOLD_LONG_ONLY|6.7063|816.4775|12.0518|17.5304|-116.2646|2.1912|10.4896|11.2296|
|BASE27|RAW_AS_PERCENT|LONG_ONLY|-0.8313|447.1497|215.8238|313.9258|-0.5267|39.2407|7.3713|6.4459|
|BASE27|RAW_AS_PERCENT|SHORT_ONLY|-5.0490|-118.8993|157.3861|228.9252|0.3143|28.6157|5.4297|8.1179|
|BASE27|RAW_AS_PERCENT|LONG_SHORT|-5.5535|393.4424|386.4588|562.1222|-0.2074|70.2652|9.0195|11.1595|
|BASE27|RAW_AS_PERCENT|HOLD_LONG_ONLY|7.8636|817.2955|12.1261|17.6385|-1.1690|2.2047|10.4941|10.9495|
|STRESS43|RAW_AS_FRACTION|LONG_ONLY|-4.2534|457.1675|212.5098|618.2115|-51.7862|38.6381|7.3837|8.0245|
|STRESS43|RAW_AS_FRACTION|SHORT_ONLY|-7.0002|-124.0586|155.2807|451.7253|31.0445|28.2328|5.4432|9.2340|
|STRESS43|RAW_AS_FRACTION|LONG_SHORT|-11.1837|366.9294|374.8904|1090.5912|-19.8205|68.1619|9.0638|14.2722|
|STRESS43|RAW_AS_FRACTION|HOLD_LONG_ONLY|6.5277|816.0216|12.0416|35.0323|-116.1819|2.1894|10.4912|11.2733|
|STRESS43|RAW_AS_PERCENT|LONG_ONLY|-3.8551|443.8930|212.0396|616.8437|-0.5224|38.5527|7.3664|7.8983|
|STRESS43|RAW_AS_PERCENT|SHORT_ONLY|-7.3446|-128.6713|155.0482|451.0491|0.3098|28.1906|5.4486|9.5693|
|STRESS43|RAW_AS_PERCENT|LONG_SHORT|-10.9792|374.1195|376.5150|1095.3173|-0.2027|68.4573|9.0824|14.1885|
|STRESS43|RAW_AS_PERCENT|HOLD_LONG_ONLY|7.6831|816.8382|12.1159|35.2483|-1.1681|2.2029|10.4957|10.9933|

同caps不是相同实际风险：LO约7.37%、SO5.43%、LS9.01%–9.08%、HOLD10.49%–10.50%；没有事后缩放匹配/可执行风险相同声明。方向净贡献只指同条件独立账户差，LS−LO依次−448.0555、−472.2194、−693.0325、−712.4028USDT；共享风险/资金与持仓状态不同，不等于从LS账本逐腿抽出的纯空头因果利润。空头净增量在本四条件均负；屏蔽空头减少亏损和实现风险，但LO仍不盈利。

## 成交原因与分币损益

12保存Turtle账本（本轮LO/SO八个、D048 LS四个）共36个trades/target_meta/funding JSON已实际诊断，无新增账户或市场回放。全部成交映射UNKNOWN=0，重复通知只去重映射，真实CLOSE/OPEN两腿分别保留；费用加execution一次，execution已包含spread/slip。小于10USDT仅尺寸附加标签，不能再次加到原因总数。

BASE27/RAW_AS_FRACTION的手续费+执行成本（USDT）：

|原因|LO|SO|保存LS|
|---|---:|---:|---:|
|ENTRY|203.80|145.80|362.33|
|ADD|60.16|47.55|109.44|
|EXIT|55.49|44.94|100.21|
|STOP|76.49|67.80|142.10|
|RISK_REDUCTION|130.97|80.89|228.77|
|TERMINAL|1.44|0.00|1.36|

LS成本944.20，其中加仓109.44并非全部成本。必要止损/风险减仓不能为了减少换手关闭；这张表不能证明删去某类成交后的净收益。按资产独立拆价格毛现金流、资金费、费用和执行成本：LO BTC净+297.66、ETH−426.30；SO BTC−134.03、ETH−335.58。LO BTC毛+651.85而ETH毛−199.68，SO BTC毛+70.29而ETH毛−184.38；同一10k账户贡献相加，不使用分币资本重新制造收益率。所有末持仓为实际保存值0；此分解不把退出realized收益归给reason，不证明资产选择或方向的纯因果效果。

[诊断](../reports/fast_research/TURTLE_TURNOVER_DIAGNOSTIC_20261004.json) task74615d9614f44e62a568eb92c6c7d58e真实exit0，SHA bdeddcde308211908208a5e69f38474148212e21415c091cd0f34f25bea95922，0.986597s/RSS49512448B；[独立手算病例](../reports/fast_research/TURTLE_TURNOVER_SYNTHETIC_20261004.json) task739defd7e89e4a93b6757b637d76c0fe真实exit0/1case，SHA2fb1109f4b12e49858a641151f7c2f5b432e6bda286c43e0f273d751fc352d04。覆盖BUY回补归SHORT、UNKNOWN保留金额、重复防计费、严格小额标签和分币gross/funding桥。真实诊断只完成后补RESULT，明确无事前START。

## 实现与证据

本版只限制原raw should_long/should_short与ENTRY/ADD方向许可；原EXIT/STOP/RISK_REDUCTION/TERMINAL、callbacks、原完整金融代码与qty/cost/funding/risk保持。实际SO账户生成负头寸与SELL开仓、BUY回补；不是收益曲线取反，不把“不做多”自动当作做空。mode快照隔离且禁止重标识恢复；CASH仍独立选择。原Spot库存保护未改。

- [实际8完整账户](../reports/fast_research/TURTLE_DIRECTION_ABLATION_ACTUAL_20261003_V1.json)：task dcd81fc4ee0943d188e8d2d98624d63c，host43399a/exit0，SHA1cc509ceeaeba68489e3b903615620360fbb16da1fb3f175a68d6031b2c91aab。460.496s/RSS681332736B/新输出160753834B。
- [独立8记录财务调用](../reports/fast_research/TURTLE_DIRECTION_FINANCIAL_INDEPENDENT_20261003_V1.json)：task c23e2069c3d44b038041033816b84564，3411af/exit0，SHAf16f80777c9f6dd870ea9c14dae1e6d2a83c27cbe22ccfbb462129cf4a209e49。25.348s/RSS662822912B，原cash1e-7/ratio1e-10，实际最大2.1827872842550278e-11/1.609823385706477e-14；额外核所有OPEN持仓方向。独立金融不是重建完整策略意图或native认证。
- [保存同条件比较](../reports/fast_research/TURTLE_DIRECTION_SAVED_COMPARISON_20261003_V1.json)：task e1785937c05845d1b43d9019af40bcc7，7cff80/exit0，SHA6a3cbf7deafcf11e518de4efb8ec779f171ff56b69b67bc6b66c493983949ec8，4组/新8+旧8，不读行情/账本、不重跑旧结果。
- synthetic V1真实failed1（test collection缺1括号，0执行），report4ea046.../task46166b.../37373d保留；V2仅补1个ASCII`)`，同断言与原容差，taskd8776a.../4aaed7真实exit0/1case，report8e96e4...。
- metadata冻结独立金融接线已741175/0：task266150abc35d48c59134bc033be7a1e4/proto88284e6...，0arrays/0ledger。准备器V1未消费且因指失败smoke保持原稿；V2正确路径，非覆写失败。
- comparison binder已实际写计划782475...；外层PowerShell误读先前残留LASTEXITCODE而报7aaf35/1，未启动比较；随后使用同一原计划直接运行，实际7cff80/0，无新绑定/重复经济运行。

## 资源和边界

最近完整项目+整D盘WSL VHD实扫23185567152B@2026-10-03T16:10:08.625291Z（2026-10-04 00:10:08Asia/Shanghai），先于本轮160.75MB输出；185b7e/0只发布已完成测量到8765，没有再扫描/伪造当前总量。共享RAM硬4999999488B，swap0/GPU0，collector540保留。数量/minqty1e-8、open min10及MMR.005仍未认证代理；官方当前closing免minnot不追认2024历史native。资金费单位UNCONFIRMED两条件完整保留，403限制不重试绕过，未locked/keys/订单/真钱。

用户10月4日允许正常维护活动代码后，canonical tests/test_turtle_direction_mask.py同步同一括号修正，当前32e9d1...与实际已验V2完整字节相同；原失败7fdfd0...逐字节在archive/TURTLE_DIRECTION_MASK_TEST_SOURCE_20261003_V1.py，原失败报告与协议不改。旧失败声明路径在ROOT通过明确历史source resolution对archive验hash，不把坏语法永久留在活动tests，也不追认旧测试通过。

最终[ROOT](../reports/fast_research/TURTLE_DIRECTION_ROOT_ACCEPTANCE_20261003_V1.json) task08b0badf72a44d9d9c99a2cb07244d22/chunk6f9c8f真实exit0，SHA60ba693490d5c04f1e55bc3016c6ea646f40e3fee6fc2cf0566b52947e652817：7完成角色/124源pins/36JSON原字节，诊断桥最大3.41e-12USDT≤原1e-7。ROOT首次d16ddeca...实际failed1是旧草稿把pytest collection code2错要求1，外层本来failed1；修精确元数据后只复核metadata，未重跑测试/金融。原失败源与小凭证保持。

## 下一步与复现

用户最新任务为可配置约10币、单一共享10k资本组合；先来源/兼容性只读核查再固定实验，尚未多币市场运行。原abs30%/gross60%、1x、真实成本/资源和权限保持，不平均旧独立NAV，不以BTC这一个有利贡献事后选币。原禁ADD/RSI2建议让位新任务；HOLD仍强基准，Turtle/SMA投资暂停，CASH/NONE/APR不可评估。

历史运行可用保存protocol与对应入口复现；以下命令只用于必要复现，不是本模块追加运行：

```sh
bash scripts/with_task_progress.sh --title 'Turtle 方向研究' -- env PYTHONPATH=.:src POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/investment/turtle_direction_research.py --protocol protocols/TURTLE_DIRECTION_ABLATION_20261003_V1.json
```

实际SHA、原独占目录和失败保持；若重复运行必须新工件路径，不覆盖原报告。当前资金费单位、历史过滤/MMR/Bybit原生、完整市场意图重建均未认证，已见303日筛选不能给长期或未来资格。
