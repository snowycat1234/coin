# Research decisions

## 2026-10-02 D001：先判断flow能否转成可支付成本的价格信息

- **决定**：立即执行5/15/30/60m oracle future-flow→return机制诊断，使用已验收的30日开发数据。
  同时将未完历史获取转为官方monthly优先。暂停额外的完整60结果验收框架准备。
- **证据**：连续14日XGB-S研究proxy gross +0.4702%、成本0.6294%、net −0.1591%；
  flow IC约BTC .1899/ETH .1057。没有合格长期APR候选，不能从14日结果可靠推算长期APR。
- **替代**：立即再跑十模型全六fold；继续救River-1；先增加深度模型。它们目前不能回答
  “flow即使预测完善是否足以产生价格edge”，预期信息增益较低。
- **信息增益/APR相关性**：区分flow信息不足、条件impact缺失和5m成本障碍；若oracle也弱，
  优先换target/horizon/信息源；若oracle强而实际预测弱，优先OOF flow→impact。
- **预算**：一个固定oracle-impact模型配置，四个指定horizon，无HPO。使用原5GB限制。
  研究分配60%主线、20%相邻、20%frontier；条件impact与cross-market信息诊断占frontier份额。
- **成功/失败条件**：共同样本的oracle关联及条件impact有一致结构则推进两阶段；
  关联弱或效应远低于成本则将其作为失败机制证据，转向更长horizon/流动性信息。
  oracle收益只作不可交易的机制诊断，不计入最佳APR。
- **暂停与重开**：River-1为RETIRED_CONFIG，不再调救；adaptive learning为ACTIVE_FRONTIER。
  完整旧60结果验收准备为PAUSED_WITH_REOPEN_CONDITION：三fold筛选产生需继续的方向、
  或实际模型留存缺口阻碍下一实验时重开。序列/representation/LOB能力不永久删除；
  family筛选仍需三个预登记、时间分散的真正unseen fold和残差信息检查。
- **边界**：旧冻结证据不覆盖，locked不消费，原价格proxy的BBO缺失和成本假设继续明示。

## 2026-10-02 D002：oracle强关联后，测试OOF误差能否保留经济edge

- **决定**：固定XGB-S配方执行四流 M1→两资产M2，四个horizon；M2仅使用chronological
  OOF预测flow和past-state，同OOF训练行的direct return作为对照，不做HPO。
- **依据**：已查看July开发窗口的ETH未来永续flow/现货return rank关联约 .71–.76；
  固定35bp oracle选择的15/30/60m平均毛edge50.42/58.34/72.52bp，高于5m35.01bp。
  这只证明该条件样本存在关联，未来区间重叠、regime与未来有效筛选限制均保留。
- **为什么可能提高长期APR**：直接测量可预测flow误差对impact/可支付成本edge的损失，
  区分M1信息、M2条件映射、horizon和交易成本障碍。弱预测时先分析机制，再决定
  历史状态、cross-market、adaptive或L1信息；不靠加杠杆/降成本/事后阈值救结果。
- **预算与freeze**：一个固定配方、3 expanding OOF blocks、四周期，最多24个fit；
  30分钟CPU/新增≤2GB、共用原5GB RAM，无GPU。原20bp fee＋8bp slippage＋
  2/4/8bp spread、35bp决策、原风险预算保持。相同dataset/split/label/normalization/economics。
- **成功/失败判据**：预测flow、return、经济proxy相对于direct control的差异能定位失败
  机制；开发窗口的正proxy也不能晋级。筛选要进入三个预登记unseen fold，不能看过后重定义。
- **能力状态**：OOF/horizon/cross-market主线ACTIVE_CORE；conditional impact与信息源
  诊断ACTIVE_FRONTIER；adaptive与ensemble后续按残差证据推进。序列/representation能力
  保留，三个unseen folds后再按净成本结果/残差价值决定继续。旧大批量入口审计不阻塞本实验。

## 2026-10-02 D003：筛价格相关的可预测组件，不按flow IC继续堆容量

- **决定**：冻结5/15m×Ridge/XGB-S/TCN-S六个recipe、1seed，执行三个已预登记unseen
  folds。A数据已有即开始，B/C到齐且独立QA后同配置继续，首fold结果后不改配方。
  共同四流flow＋两Spot return目标；保留Perp目标，TCN只复用官方encoder＋小head。
  原费用、阈值、风险不变；共同dataset/split/labels/normalization/metrics/economics。
- **证据**：OOF两阶段15/30/60m净−0.4221%/−2.0994%/−5.8463%，DIRECT15m微正
  仅3往返且36bp成本净负。零fit组件诊断中，SpotBTC5/15m预测flow本身IC .177/.176，
  但预测组件与return Pearson仅−.0034/.0054；真实futureflow与return .492/.516。
  M1未来flow残差仍有强关系，它是相对当前M1的未来误差，不是可用输入或结构因果创新。
- **信息增益/APR价值**：验证序列保留了tabular统计丢失的价格相关信息与否、flow组件是否
  在新regime仍可预测且对价格有意义。若只改进已弱价格相关的flow IC，不能据此晋级。
  三fold还提供残差/ensemble独立性；均不是正式连续长期账户或候选未来证据。
- **预算**：最多12个tabular＋6个TCN fit；TCN沿原max10/patience3，预计30–90分钟
  CPU墙时；新增缓存估计≤1GB，不落全部[N,256,F]序列。原5GB/swap0/GPU0。
  序列信息/价格相关性探索保留至少20%科研份额；并行官方Spot/USD-M成本映射。
- **暂停/重开**：当前long-horizon两阶段HPO暂缓，新unseen的M1/残差/净成本增益或新
  信息集支持时重开。TLOB/TS2Vec更大批量暂缓；TCN出现独立价格信息、三fold说明
  表示损失，或周转资源改善时重开。adaptive保留，流组件漂移/残差结构明确时优先。
  不以这个July短窗淘汰整个能力，不重新启动旧全十模型六fold大循环。
- **协议**：`protocols/research_v7_family_screen_20261002_v1.json`。评估不使用locked、
  不把未来有效性筛选当在线过滤，不通过换venue费用改写既有Spot结果。

## 2026-10-02 D004：V8纠偏，先证伪非重叠增量alpha

- 用户直接提供V8，冲突处覆盖v7。目标改为risk-constrained net CAGR；候选NONE，
  <=180日仅SCREENING。旧oracle只标SAME_WINDOW_IMPACT_DIAGNOSTIC，无预测上限声明。
- 原V7队列先停止并保存146工件SHA：A6/B2完成，其他中止，执行污染不因根未读而抹去。
  旧源码/模型/负结果保持；locked和真钱边界不变。
- 下一信息增益最高路线为非重叠标签/strict OOF surprise与matched direct及最强风险基准；
  四个预注册月份分散OOS不等于四独立经济regime，需如实统计依赖。P1未过不得深度扩展。
- 只追加登记所有历史成功/失败/中断工件，未知元数据不伪造；工件数不是trial count。
  bootstrap/DSR/PBO/SPA输入不足则NOT_EVALUABLE，不通过省略结果或假0制造通过。
- P1失败：aggTrades-only directional alpha PAUSED；仅真实L1/L5/BBO新信息或carry/basis/
  慢速组合重开。maker缺queue/真实fills，carry缺mark/资金费/保证金输入时不可评价。
- 8765实际修復已接受保持WSL连接；显式shutdown和时钟跳变仍如实保留，不扩工程观察器。

## 2026-10-02 D005：独立反例决定修复顺序

- V1首轮反例在V2被修复；V2独立审计又发现导出／split锁定日期入口及时间／单位
  守卫缺口，保留两版源码、绿色与失败输出，第三版独立修复。真实locked数据未读取。
- 优先把非重叠标签、共同固定特征和匹配direct／风险基准的入口修正确，再用最低预算
  判断早期流量影响是否延续到后续窗口；不通过新增模型掩盖错误或成本问题。
- 完整CPU依赖锁／独立clean复现和append-only ledger控制已验收；历史trial元数据未知
  不变成0，统计及完整研究集成门槛仍未通过。深度方向依P1经济统计结果才允许重开。

## 2026-10-02 D006：先检验非重叠机制，保留完整时间日历

- 四个预登记时间段的153日共同来源已验收，原492份前缀及失败／不完整来源凭证保留。
  来源完整不代表P1通过；标签和特征的新独立反例继续修复，旧绿色检查不抹去反例。
- 下一最低预算实验是全部三个固定非重叠标签、四fold、全部预先声明流量／收益配对的
  一次机制诊断。方向只由train描述性相关确定，OOS不得翻转、挑配对或调参数。
  保留每分钟日历及无效／未成熟行，未知不补零，不以未来有效性当在线资格。
- 观测flow的后续相关及signed response仅诊断，不构造交易ledger、不声明可成交
  edge、成本上限或净CAGR；IID显著性丢弃。经济统计及最强风险基准仍须单独验证。

## 2026-10-02 D007：弱非重叠证据后，有限OOF证伪与新信息并行

- 候选NONE；四段主要配对OOS Spearman绝对值最大0.0626013，冻结TRAIN方向下平均响应
  −0.122768～+0.429106bp。17／24方向同号不是独立试验支持，也不是交易收益或成本上限。
  更正此前“均<0.06”的近似表述，不抹去原始输出。P1经济统计仍NOT_READY。
- 日历20分钟／fold／variant缺口已另版补齐，独立复审核原行／浮点位／96及672统计不变；
  不把 correctness 修复计为新 alpha 阴性，也不 retro-PASS 旧 FAIL。
- 下一最低预算为一套固定478／完整TRAIN-VAL-OOS缓存、严格OOF第一层surprise与matched
  DIRECT；新表示只能说明固定模型利用特征的效果，不能声称产生新增市场信息。模型和
  成本配方在新预测前冻结；本选择受已见机制结果影响，明确登记，不假装新clean-room研究。
- 至少20%研究预算保留frontier：官方funding+mark/index小来源QA及carry／慢速组合经济
  映射。历史bookDepth只为百分比汇总，不能重命名L5以重开执行资格；OHLC不能替代BBO。
- 先识别信息不足／模型表示／周转成本各自作用；不换手续费救Spot结果，不调OOS阈值、
  不增加杠杆、不消费locked。若P1失败，只按真实新盘口信息或carry/basis/慢组合重开。
- 深度／TCN、maker、正式TLOB继续暂停，重开分别需要P1、真实queue/fill、真实L1/L5；
  carry仍待资金费因果时点／历史成本／风险资本映射，元数据存在不产生经济资格。

## 2026-10-02 D008：投资质量原则，立即优先共同收益闭环

- 用户明确采纳新长期原则；实际HEAD73546402，比附件参考1031e28更新。已核工作区
  ledger增量／未提交缓存和资金费源、运行任务及实际机制与旧经济结果，不重复入口修复。
- 当前没有共同策略净值比较；主力研究方案NONE，真钱候选NONE。最大阻碍为经济比较
  未接成闭环，不是缺478特征或未跑够模型。暂不启动84日特征缓存或strictOOF模型队列。
- 主任务改为复用冻结quant.backtest＋已有固定持仓意图，把cash／BH／VM／trend／MR
  接真实订单、成交、未平仓估值、日净值与相同成本风险；具体公开策略并行做最薄语义接入。
  新比较前冻结共同风险／周期／成本，保留旧V8合同，语义改变另命名，不冒称原策略复现。
- 已启动且小预算的24 funding/mark/index来源QA可以闭合，不因此阻塞Spot简单对照；
  缓存tiny独立审计也保留结果。均不扩来源/模型/生产平台。
- 已看过的四时间段只为SCREENING；不复用作独立泛化证据。旧非重叠机制阴性只限该
  假设，不禁止全部flow/ML；不变更旧结果的费用、样本和成功定义。新方案依真实净值差距取舍。

## 2026-10-02 D009：收益比较前固定公开规则与研究参照

- 主参照预先指定VOL_MANAGED_BUY_AND_HOLD：选择理由是低换手、简单可解释、共同风险下
  的市场暴露；不是先看四段结果再选择冠军。它目前只是研究参照，不是合格候选。
- 公共challenger选择jesse-ai/example-strategies的MIT Donchian，固定commit
  `7c91e0a37bf62165790120d730442e4f6eb00364`。复用原signal hook和官方Donchian20指标；
  完成小时线、SMA200、上一20小时通道、仅long；与common资金风险／分钟执行对接。
  上游源码未指定timeframe，1h为本轮预先选择；原全仓改0/30%共同配置，如实命名adapter。
- 现金、BH、VM、现有trend／MR、公开Donchian，共6策略×4已见7日段×3固定成本
  =72账本、0拟合；所有配置同市场、账户10k、30/60%上限、10%波动风险、分钟执行合同。
  原30日risk warmup/至少20日沿用，新增公开规则只使用已完成小时线，不改原engine。
- 数据直接复用冻结Jul–Nov官方1m源的10个月文件及既有QA链，完整153日／两币。
  不重新下载／合成分钟、不先跑84日478cache、不把这些已见日期称真正unseen OOS。
- 公共adapter仅关键合成因果／缺分钟核验实际exit0；下一经济结果尚未产生。
  缓存独立probe已发现contract冲突与导出maturity守卫缺口，保留FAIL并暂停全cache；
  不把它扩成普通策略的阻塞门槛。重开限于确有模型特征复用需求且先解决两个blocker。

## 2026-10-02 D010：只修已实测的批量计算与未知可用性问题

- 原共同收益run已实际完成9个账本（A段cash/BH/VM各3成本），耗321.16s；
  BH目标阶段117s来自逐分钟重排整个历史。精准停止原PID，原FAIL／退出／snapshot／
  partial账本和只追加registry都保留，不追溯改成成功或新的策略结果。
- 下一版仅用官方Polars EWM／rolling一次计算相同固定规则及旧持仓状态，不改变阈值、
  样本、成本、风险或研究参照。与旧固定规则逐端点等价及future perturbation后重启72账本。
  一行Polars对NumPy索引类型兼容失败也独立留证；只重跑受影响的新增等价检查。
- 独立probe发现公开adapter小时聚合会忽略NULL可用性，旧FAIL保留。共同minute_view
  已标无效并拒整fold，未穿透原完整账本；仍补导出API最小NULL守卫，不以主路径安全
  代替修复。原Jesse字节／退出规则不变，未知不补零，不重写策略框架。
- 原费用／时序／低容量／现金数量和未平仓估值核验不重复全套；源码发生普通Git增量，
  新协议／输出独立绑定，旧source按既有snapshot和历史binding核对。

## 2026-10-02 D011：共同收益实测后选择连续公开策略对照

- 72/72实际账本退出0。30bp名义往返下，四独立七日账户平均净值：public Donchian
  +0.473%、BH+0.421%、预选VM+0.188%、minute trend−2.907%、MR−9.101%、cash0。
  不年化、不拼接；已见窗口不是unseen。当前phase预选VM不改。
- Donchian仅7闭合往返，B约占正净收益78%，D终端约1135USDT持仓按市价计；
  明确下一阶段研究主力选它，不赋予Candidate/真钱资格。模型数量不是当前瓶颈。
- 下一最高价值实验选已有Aug1..<Dec1连续122日，cash/BH/VM/public四固定策略×三成本，
  独立新协议与报告；同冻结engine/risk/source，无调参/新seed/新market输入。
  解决四段重置/收益集中/短期余仓是否扭曲优势。范围由已验收完整覆盖确定，仍SCREENING。
- 当前minute trend/MR暂停固定配方：同数量毛收益很弱，费用换手是主因；以新信息或有理由
  降低换手机制重开，不通过降费或事后阈值制造改善。旧ML/flow阴性限旧假设，不永久删除。
- 478cache未启动，2审计blocker保留；只有下一实验依赖该能力才修复。BBO/maker/carry
  缺真实经济输入继续限资格。独立经济复核72账本无blocker；校验器Arrow chunk、float比值
  以及numpy计数JSON导出问题独立留证，最终恢复只导出既有72结果，不重跑市场账本。

## 2026-10-02 D012：连续122日推翻公开1h策略盈利主力假设

- 2025Aug1..<Dec1四固定方向×三成本12连续账户已actual exit0、独立12账本exit0。
  30bp下cash0、BH−5.6438%、VM−4.0601%、public1h−0.2673%；public36bp−0.7053%。
  本期描述性年化为负，不能称长期净APR证明。没有正净收益合格候选，cash仅零收益对照。
- 公开1h same-quantity gross+1.9355%，成本2.2028%，158fills/38闭合往返。
  盈亏平衡26.36bp不足原30bp。真实122日连续minuteMDD公3.691%、VM9.449%、BH12.381%；
  实现年化vol公6.50%、VM10.31%、BH14.92%，共同机制不保证相同风险。末仓仅浮点dust。
- 接受共同比较能力，放弃1h盈利主力假设，保留它为防御参照。短七日正结果不是晋级理由。
  当前主因是cost/horizon/弱gross edge；publicBTC被动漂移超30%目标0.167pp并非2.20%成本主因。
- 下一信息增益最高选择仅一个固定2h public换手/horizon诊断，沿同一31日预热、122日历、
  原费用/执行/风险，与已固定1h和现金/VM/BH参照比较。预登记后再运行，不加seed、HPO、
  调阈值、降费或杠杆；判断换手下降是否保住毛优势，而不是只追较少交易。
- 分钟trend/MR及当前1h盈利部署暂停；以低换手因果变体达到原成本门槛且后续真正未见
  验证才重开候选路线。深度/flow未永久删除，下一实验确有信息增益才分配预算。
  不修改冻结engine、旧正负工件或locked边界。本turn不再扩第三套模型/执行框架。

## 2026-10-02 D013：固定2h规则，区分换手成本与毛优势流失

- 接手实际HEAD `bcd35b0`，工作区仅上一推送后状态元数据；8765已连接、没有进行中的
  历史研究任务。上一turn完成84账本与来源格式证据，属于progress；当前无盈利候选。
- D012已选择的唯一新配置为MIT Jesse规则的2h COIN适配。通道20根/SMA200保持，因此
  同时改变物理时间跨度和决策频率，不能描述为只降低交易频率。原1h默认语义需保持。
- 问题：在原30/32/36bp成本下，减少交易是否保住gross edge并提高net；不能仅用换手下降
  宣告成功。统一比较实际暴露/波动/MDD、月贡献和终端估值；共同机制不保证同实现风险。
- 固定Aug1..<Dec1连续122日，July31日预热。仅新2h×3成本账户，复用旧1h/VM/BH/cash
  已验收账本和来源/参数/完整分钟输入哈希，不重跑旧12、旧green或原行情QA。
  全部是已见开发SCREENING，当前比较不是unseen，正结果也不自动形成部署候选。
- 新源码/协议/失败/实际退出和审计独立留证，不覆盖旧报告；≤512MB新增工作预算，
  当前共享5GB RAM/swap0/GPU0/D盘40GB。必要新增聚合因果检查后直接真实账户回放。
  无阈值搜索/新seed/降费/杠杆/新下载/locked/密钥/真钱。结果后自主重新判断瓶颈。

## 2026-10-02 D014：采用固定2h作研究主力，先检验时间段外稳定性

- 唯一新增2h×三成本、连续122日实际exit0，独立3账本和边界核验exit0；原12账户仅
  exact来源/配置/日期/成本/引擎及工件绑定复用。30/32/36bp net+0.6580/+0.5958/+0.4692%。
  采用2h为主力研究方案，1h为参照；NO_QUALIFIED_CANDIDATE，不证明长期APR。
- 30bp同数量gross160.62USDT较1h193.55保留83.0%，成本94.82较220.28下降57.0%；
  69/158fills、17/38往返。分钟MDD4.709%较3.691%变差；实现vol6.20%较6.50%。
  只2/4正月，Sep/Nov gross均负且较1h更差，Oct占正gross月58.96%。不能只用全期正数
  宣告跨状态改善，也不能视为纯降频：20/200根物理跨度随2h同步翻倍。
- 下一最高价值选择固定Dec1 2025..<Mar1 2026连续90日、Oct31..<Dec1的31日预热，
  cash/BH/VM/1h/2h五方向×原30/32/36bp；0新参数/拟合/费用放松，先验收推送本模块。
  只读Oct2025..Feb2026明确十月档并复用原来源QA，薄扩输入边界，不能使用全盘行情loader。
- Dec–Feb已被旧A05/A06正式CV fold7/8消费；新窗口只检验本规则相对Aug–Nov的时间外推，
  不称项目级unseen，不因新版本洗白。全部日期早于locked2026Mar1；现有封存不启封。
- 预先判断：比较原成本净/gross/换手/分钟MDD/月贡献；若gross弱则缩小2h为防御参照，
  自主转向有具体经济理由的新因果方向。不给事后阈值/新周期搜索补救；原正负证据保持。
  1h盈利部署、分钟trend/MR固定配方和更多周期尝试暂停，重开需新机制或独立证据。

### D014 实施补记：同步和合法期末时间戳

- 本地2h模块`1519a61`验收提交后，WSL的GitHub主域TCP两次超时；不让外部同步故障
  阻塞只读来源/普通研究。复用本机已存在网络和Git、原WSL bounded认证后push实际0，
  GitHub API确认main精确为`1519a61b1398bba0f6a4f2793f50a39aae4126ac`。失败尝试保存。
- 90d来源复用10文件/151日/434880行实际exit0。唯一actualV1在3个CASH账本后exit1：
  bulk signal-close输入包含最后minute的exclusiveclose=Mar1，被旧日期守卫拒绝。
  这不是读取March价格，也不是经济阴性结论；原FAIL/START-RESULT/snapshot/工件保留。
- 只在bulk signal-close视图排除晚于最后decision的close，和public既有past-only输入一致；
  不clamp时间、不放宽March guard、不删除任何完整execution/valuation价格或收益行。
  新增边界case针对复测，旧source/public/engine已绿核验按依赖复用；新V2独立15账本恢复。

### D015：90日外推否定2h盈利主力，保留能力并缩小下一假设

- V2 actual4852/task73a916…真实exit0、15/15；独立R2 88702真实exit0、15账本数学核验。
  30bp现货COIN代理净1h−0.7497%、2h−1.8175%。2h毛−104.26USDT、成本77.49，
  1h毛+52.62、成本127.59；2h只是低成本，不能作为本段盈利主力。部署候选NONE。
- 原122日2h+0.6580%不撤销，但两段fresh账户不拼接、不挑各期赢家；Dec–Feb已被A05/A06看过。
  三个月只有Jan正gross和net，收益集中与信号状态失效已超过手续费问题。
- 独立初次checker实际exit1、0数学账本：Parquet回读不能重现原memoryIPC物理指纹。
  FAIL保留；R2限定精确Parquet SHA+单fold逻辑日历/schema/值+自身IPC回读与15资金账本，
  原指纹明确NOT_REPRODUCED，未改经济门槛/成本/market source，不把序列化限制写成字节通过。
- 本版根验收只读报告和SHA，未重跑旧行情/绿测；首个根metadata builder缺失failed报告字段exit1，
  使用已保存实际退出/部分工件归档凭证修复，未修改原失败或运行市场。
- 下一策略假设仅固定2h入场/1h退出，复用原MIT hooks，检验联合退出尺度的gross/net/成本/
  月贡献/分钟MDD/实际暴露。尚未证明慢退出原因；退出物理回看与检查频率同时改变。
  若无共同经济增量则暂停该hybrid；更多周期/HPO暂停，新因果信息或独立证据可以重开。

### D016：用户指定Bybit普通用户标准，先补产品和费用资产兼容

- 2026-10-02用户明确允许平台标准改为Bybit nonVIP。核实官方2026Sep2费用表：global常规crypto
  Spot maker/taker均0.1%（10bp/side）；perpetual/futures maker0.02%/taker0.055%（2/5.5bp）。
  官方Sep10 Spot说明：费用扣收到的资产，buy扣base、sell扣quote；地区/账户实际费率未验证。
- 当前Spot十bp数值不变，不重复15账本或把旧Binance数据报告改写为Bybit成交。旧common引擎按
  quote扣费，不等同Bybit原生持仓。未来费用profile单独登记，保留历史Binance research输入；
  Bybit价格/BBO/过滤器/资金费需产品对应来源，永续较低费率不得拿来计算Spot盈利。
- 此用户方向优先于D015下一策略实验：先做最薄费用资产兼容并针对账本独立核验，之后再hybrid。
  不重建执行平台、不启用账户或真钱；仅在真实接入依赖需要时推进必要Bybit公开输入。

### D017：只改变结算规则，验证Bybit费用资产对经济结果的实际影响（结果前）

- 当前盈利方案NONE，2h是防御研究参照。普通Spot费率仍10bp，不预期仅更换平台名称能恢复APR。
  真正待核是买入扣base导致的净可用仓位、买单资金/风险分母及卖出数量。
- 保留原backtest ee333d/合同b7fc/public169d字节；新薄adapter按完整原SHA与精确唯一AST锚点
  派生研究函数，不复制完整引擎、不调用DB/network。新fee/derived AST分别绑定，旧合同只代表
  继承的时序/风险来源。复用现有execution.py双资产成交及commissionAsset扣费语义。
- 先验有针对性的合成入口/cash/qty/上限/分钟NAV/终端dust和source复用守卫；独立核对限定变更。
  经该验收后只跑固定2h×原3成本×两个完整已见账户段（122/90日），最多6新账户/0fit。
  如果确有影响后续公平比较的1h缺口，预算最多另6native费用账户；不重复旧quote绿测或市场。
- 直接复用旧验收共享Parquet和2h目标的既有审计SHA，不重下数据/全source QA，不改变信号。
  三成本/资金/过去波动目标/资本上限/容量/延迟/lot不放宽；当前Bybit公开费率用于历史反事实
  proxy，仍为Binance历史价格与过滤器，不能称Bybit真实市场/地区账户已验证。
- 费用资产改动只在实际成交gross quantity上扣一次；新分钟净值用cash_delta/position_delta。
  gross归因为同净收到持仓的shadow，base费以成交时mid记USDT，另保留原生fee_asset/amount。
  原内存IPC指纹不可跨Parquet重现的限制保留；新native费用回放先保存精确ArrowIPC，再从该
  不可变文件读入信号/执行，file SHA直接绑定实际输入，不用重新序列化去追一个未知chunk哈希。
  不混入永续5.5bp或额外杠杆；旧正负证据保持，新结果只判断结算影响和下一假设是否仍值得。
- 共享RAM≤5GB/swap0/noGPU，单次STATE工件预留≤512MB、每账户窗CPU≤1h；整个项目+VHD40GB。
  correctness blocker保存失败后最小修复复测；资源超预留即停止新增。locked/key/funds不启用。

### D018：采用Bybit现货费用资产，亏损瓶颈继续指向信号（六个新账户结果）

- 固定2h目标/参数/资金/风险/三成本不改，两个独立连续账户段各3实际exit0。
  原122/90参照不重跑，原行情QA不重做；复用已绑定的Parquet与目标SHA，新Arrow保存后读入。
  122日新net30/32/36bp为+0.6570/+0.5932/+0.4671%；90日−1.8173/−1.8680/−1.9705%。
- 费用资产语义采用。Spot10bp没有下降，最低成本与旧quote账本仅差−0.1022/+0.0168USDT；
  不把平台名称、永续较低费率或dust删除当APR提升。90日毛诊断仍约−104.24USDT，亏损不是
  买入费用资产这个错误所制造；盈利主力NONE，2h继续仅为防御研究参照。
- 真实失败保存：单位V1两summary浮点消减失败，仅16ULP容差修两失败用例，另外3PASS复用；
  集成V1缺线程环境在0tests/0market/0disk时拒绝，补显式2线程后4新增用例PASS，源不改。
  原core与合同字节继续保护，新fee/derivedAST独立绑定；实际逐fill/分钟/日/月数学以六账本独立
  审计及根验收凭证为准，结果只SCREENING，不是Bybit原生历史或unseen盈利证据。
- 独立checker首次完成122日3金融块后，expected入参被目标重建列表覆盖导致末尾SHAguard
  exit1；保留FAIL，元数据恢复与90日3新数学块补齐，122数学不重跑，不称一次六全PASS。
- 下一项仅固定2h入场/1h退出（同原MIT hooks、已7项信号合成验收），共同native费用/风险下
  两段独立比较。它联合改变退出20bar物理窗口40h→20h和检查频率，不称纯延迟因果。
  无需额外6个native1h参照重跑；直接与新native2h控制账户比较，以gross/net/MDD/成本判断。
  若无改善，停止扫周期，从公开策略/经济映射真实缺口自主选下步。hybrid经济尚未启动。

### D019：固定hybrid退出机制共同费用比较（新经济结果前）

- 问题是固定2h入场/1h退出能否减少亏损月份gross而保留趋势收益；不选择新周期/阈值。
  只生成122日与90日各3成本新账户，与已验收native2h六个摘要比较；旧行情QA、目标测试、
  原控制账本不重复跑。入口相同但早退出可能改变后续入场集合，退出物理回看40h→20h与
  检查频率联合改变，不声称隔离纯延迟因果。
- 同原Parquet SHA、BTC/ETH、31日预热、10k资金、过去波动风险规则、容量、延迟和lot。
  Bybit非VIP Spot10bp/side原生收到资产扣费，30bp主参考、32/36bp压力档全部保留；
  两段独立连续现金/NAV，不拼接或宣称unseen/长期APR。Binance分钟成交仍是代理。
- 逐段及逐月比较net/gross/费用/价差滑点/换手/分钟MDD/实际波动和暴露；若减少暴露带来
  改善须称防御效果。若额外成本吃掉gross或损伤趋势收益、两段均变差，暂停这个固定配方。
  改善但仍亏损不能成为盈利主力；混合结果不能宣称统一赢家。原生dust使严格全库存归零
  RT计数可能为0，不能拿它充当无卖出或独立交易数；以fills/成交金额/净库存/MTM核验。
- 新接口只增加一个target→nativefee→common分钟账本的合成用例，旧4及7项已验收凭证
  保持静态复用；common/原core/fee/hybrid代码不改。最大6新账户、0fit、每窗≤512MB工件/
  ≤1hCPU，共享5GBRAM、swap0/noGPU及40GB磁盘边界继续。无locked/key/funds。
- 失败保存后只补阻断项；完成依据结果自主选择高信息增益下一项。更多退出周期/HPO暂停，
  reopen需新未消费时期或明确新信息支持的机制假设，并事先冻结协议。

### D020：hybrid跨期反转，暂停该配方并改变公开入场信息假说

- 六新账户实际退出0，根验收a4623a与独立六新账本核验a1af84接受proxy资金/费用/目标因果；
  旧控制与旧4+7测试只静态复用，新联合合成仅1case。common/core/native/hybrid源未改。
  最低30bp成本下122日net−1.1585%对控制+0.6570%，90日+0.8667%对−1.8173%。
  全32/36bp保留，前段仍负后段仍正，不事后挑成本、拼段或按时期选策略。
- 122日gross32.62/成本148.47USD对控制160.53/94.83，九月net差−193.22USD占主要损伤；
  90日gross162.73/成本76.06对−104.24/77.49，Dec/Jan/Feb分别net改善143.48/47.73/77.19。
  退出提速并非普遍改善，入口规则同但机会集合可变化；40h→20h回看与检查频率联合改变。
  MDD与实现波动亦不同，不把共同约束说成等风险。仍NO_QUALIFIED_CANDIDATE/盈利主力NONE。
- 采用Bybit费用资产结算和已核研究能力；暂停这个hybrid固定配方的盈利路线及更多周期HPO。
  Reopen需新未消费时间或明确新信息的机制假说并事前冻结；保留突破、退出及阴性证据。
  不能基于已见两段回头造一个regime selector，或用更低永续费率解释Spot收益。
- 下一项选同MIT Jesse pin公开RSI2 long-only1h：close>SMA200且RSI2≤10入场，held且
  close>SMA5退出；只保留long，与common资金/风险/native费用映射。趋势内回撤是不同于
  追突破的公开入场信息假说，检验是否有成本后稳定增量；短持仓可能损于成本，收益未知。
  先核成熟官方RSI依赖与原输出兼容；禁止手写Wilder/RSI kernel、阈值搜索或原全仓移植。
  当前只浏览官方源，未安装/vendor/跑新市场；普通研究授权继续，locked/资金/资源边界不变。
- 协议冻结helper首次因旧报告字段KeyError在0协议写/0价格读取时exit1，V2仅修metadata字段；
  双源码与退出保留。审计出口两次Windows invocation/JSON解码失败无金融复测，原checker
  字节及最终真实exit0凭证保留；不重写原失败或把元数据失败当策略数学失败。
