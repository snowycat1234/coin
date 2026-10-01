# 正式 10×6 入口独立只读复核与换手口径补充

复核对象为提交 `1251dd5b8f5aa9cb4cd89a6b0fd550b0e383753f`，UTC
`2026-10-01T16:58:37Z`（北京时间2026-10-02）。这是新的复核记录；
已验收源码、旧模块文档和旧报告保持原字节。对应凭证为
`reports/fast_research/FR_FORMAL_RUNNER_INDEPENDENT_REVIEW_20261002_V1.json`。

本次未发现需要改变正式运行入口源码的实际 correctness blocker。
结论来自只读源码、协议、验收收据和实际文件SHA复核，不是正式60项训练通过。
验收收据登记的12项文件SHA全部一致，当前HEAD仍为上述提交。

## 已核路径

- 入口事前固定10配置、seed20261001和6个fold；协议SHA固定。仅显式访问
  2025-07-01至2025-12-28前的720个日档，先查缺失，再核官方manifest/schema/
  CHECKSUM、原始字节和跨日观察编号边界。复核没有读取市场数据或locked文件。
- 共同dataset合同不含工作副本路径；native副本改路径后合同和endpoint ID不变。
  唯一index按所有目标共同有效性和60秒步长建立；各适配器返回的test indices
  必须与共同test indices完整、同序一致。
- `dataset.py:639`、`cached_dataset.py:72`的输入止于decision闭合bar；
  `labels.py:18`的未来5m/30s flow、entry/exit与RV独立留在标签/QA。
  输入窗口不含decision之后的观测。共同端点对未来标签有效性有条件筛选，
  评价已明确标成CONDITIONAL proxy，不产生可实施策略或候选资格。
- 六fold为事前索引`[0,4,9,13,18,22]`。输入scaler仅拟合available不晚于
  fit cutoff的独有训练行；target scaler仅拟合标签完整成熟不晚于fit cutoff
  的训练端点。train/validation/test另核各自标签成熟边界和300秒embargo。
- Ridge/XGB、四个序列模型、TS2Vec两probe和River使用同一数据接口和两套
  train-only scaler；所有预测inverse到原单位后才评价。TS2Vec仅用fit cutoff
  前训练行预训练600迭代；两probe同encoder。River先预测，再释放当时已经
  完整成熟的旧标签，validation标签不学习。
- 完成凭证核dataset、binding、预测文件SHA、原单位float64预测SHA、预测形状、
  完整test indices、sample IDs和EVALUATION副本；经济工件和共享encoder亦在
  artifacts中核SHA。TS2Vec先发表含两probe完整凭证的GROUP_COMPLETE，再独占
  发表各COMPLETE；中断在两COMPLETE之间可核原工件并补齐，不重新预训练。
- parent持有文件锁并将同一锁fd传给worker，worker继承共同5GB cgroup；CPU
  串行、swap0。输入副本单fold≤1GB，新增副本及worker前调用既有磁盘守卫。
  系统只读快照显示MemoryMax=5,000,000,000、MemorySwapMax=0；当时当前RAM
  770,547,712，累计peak 1,935,953,920字节。该peak不是本次复核或单模型峰值。
- 首轮仅接受全部60项同batch truth/QA/估值绑定完成。IC/收益/成本/换手/Sharpe
  按六fold等权，MDD取最差fold，时间求和，RAM取fold进程峰值最大值。TS2Vec
  两probe共享时间/RSS在输出文字中标明。top-3按模型方向去重。
- 成本为每侧10bps fee和`(8+spread)/2`bps额外成本；基准spread=2bps。
  排行榜fee/spread/slippage列分别为初始NAV占比，额外成本按2:8拆分；
  gross-minus-cost=net使用相同成交数量，不把孤立测试周拼成连续收益。

## 换手文字口径补充

`docs/MODULE_FR_FIRST_ROUND_RUNNER.md:48`的“相同初始10,000 USDT账户的reference
成交额”容易被读作USDT成交额，或总成交额除以初始NAV。实际实现与既有
`docs/MODULE_FR70_SHARED_EVALUATION.md:68`一致：

`fold turnover = Σ日(当日双侧reference成交额 / 上次日末净NAV)`，首日分母是
初始10,000；排行榜再对六fold turnover等权平均。它是无量纲换手倍数，
既不是USDT金额，也不是`总reference成交额 / 初始10,000`。

定位为`evaluation.py:306`、`metrics.py:42`、`fr_run_first_round.py:464`。
排行榜表头仅写`turnover`，没有错误标成USDT，因此只补充文字口径，保持已验收源码。
算术反例：两日reference成交额各6,000，分母分别10,000和11,000时，实际换手
为`0.6 + 6000/11000 = 1.1454545…`，总成交额/初始NAV则是1.2。
这只是口径反例，没有使用市场数据或生成正式结果。

## 实跑范围与恢复边界

本次没有执行Python、pytest、模型fit、正式preflight、数据下载或observer；
只读取原验收两项测试及其源码，不能把它们记成本次复测。未核720份实际日档，
未独立执行60项训练、正式排行榜或整个运行的峰值/磁盘容量实测。

已完成job与已有完整TS2Vec group的恢复路径已静态核对；训练中断且尚无COMPLETE
的attempt会留证据并在新attempt从头拟合，入口不提供epoch中途恢复。
若初始化在RUN_BINDING发表前中断，或native拷贝在SOURCE_SNAPSHOT发表前中断，
同run会拒绝而保留残留，不能声称这两个不完整阶段已经自动恢复通过。
既有工程验收仅证明缺历史拒绝、共享pair发表中断恢复和checkpoint变化拒绝，
不替代尚未完成的正式研究结果。
