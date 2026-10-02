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

### D021：固定公开RSI2入场假说，先核成熟kernel后共同比较（结果前）

- 当前盈利主力NONE；hybrid跨期反转，继续搜退出周期的信息价值较低。只选固定MIT Jesse
  RSI2 long-only1h，检验趋势内回撤入场能否提供不同于突破的毛收益来源并覆盖现货成本。
  close>SMA200且RSI2≤10入场，held且close>SMA5退出；原wholebalance不移植，仍common sizing。
- 同官方example-strategies7c91原hook及Jesse417f官方RSI wrapper/kernel，依赖版本依据该pin
  requirements。未知seed/flat/warmup先通过官方成熟库实际核验，禁止手写Wilder/RSI。
  优先按官方scalar观察窗口每个完整hour调用，不以未验证fullprefix向量代替截断语义；
  连续可用预热门槛取实际官方窗口，31日过去源足够。先保存许可证/版本/工件hash。
- 第一轮最多一个配方、0fit/HPO，两段已见122/90日各3成本新账户；旧native2h和hybrid只
  复用JSON摘要。与control同source Parquet/physicalArrow、10k资金、31日预热、风险规则、
  延迟/容量/lot、Bybit非VIP10bp/side原生费用；30bp主参照与32/36bp全部保留。
  两段不拼接、不按结果挑月份/成本/threshold；非unseen或长期净APR资格。
- common只追加策略ID及薄路由，原bff源码精确归档后演进；core/native费用/旧信号和冻结
  证据不改。唯一新合成test覆盖官方目标→费用→分钟账本/前缀/非空成交；旧绿不重跑。
  固定入场信息不同可重开均值回归研究能力，不等于重启旧失败的MR配方或盈利部署。
- 新库增量放D承载STATE，clean env/uv.lock不变；共享RAM≤5GB/swap0/noGPU、每窗≤512MB
  工件/≤1hCPU、项目+整个VHD40GB及32/36GB阈值继续。无locked/key/funds。

### D022：RSI2高换手且毛优势不足，暂停固定配方并检查资金费收入机制

- 固定RSI2六新账户、一次独立金融／完整因果目标核验及根验收真实退出0。30/32/36bp：
  122日net−5.7930／−6.1457／−6.8512%，90日−7.3942／−7.5818／−7.9569%。
  主30bp同净收到库存gross−31.28／−450.81USDT、总成本548.01／288.61；7个月net全负。
  前段主要成本损耗，后段还存在明显毛损失，不能简单归因费率或把perp低费率移植Spot。
  turnover37.53／20.01、fills544／396；实现年化vol3.005／3.849%而分钟MDD5.896／7.528%。
  共同资金／约束不代表等实现风险；入场与SMA5退出联合变化不是纯入口因果消融。
- 采用MIT官方kernel与比较能力，暂停本固定RSI2配方／继续周期阈值搜索；盈利主力NONE。
  Reopen需新独立时间或信息支持毛优势与充分成本余量并事先冻结；保留能力和全部阴性证据。
  旧native2h/hybrid仅静态摘要，旧绿色不重跑；新集成只1case，市场6新，0fit/HPO。
  两段仍已见SCREENING，不拼接、不按月份挑策略、不消费locked、不推导长期净APR。
- 原官方wrapper默认240bar scalar语义实测，fullprefix反例100vs33.333；不自写RSI。
  官方1.3.0 wheel与NumPy2.5.3／Python3.12 ABI通过；D承载STATE增量约2.54MB、env/uv.lock不改。
  common原bff字节归档后仅新ID／三行路由，core/nativefee/旧信号保持。安装两次实际exit1：
  LICENSE握手超时与错误sdist rsi.rs路径假设；只恢复缺项／使用真实oscillators.rs，失败不覆盖。
  新协议10月2日UTC冻结，北京时间10月3日完成；根fcbc823e、audit36ae8d6d实际退出0。
- 下一选一次funding-only两腿成本可行性诊断，先核官方rate单位／符号／calc_time事件定义，
  再用已验收8份funding档（Binance BTC/ETH、2025年8–11月、732事件）固定全122日与分月。
  不做未来高费窗口筛选／signal／NAV回测；没有可认证availability，不能把calc_time当信号时点。
  Bybit NonVIP Spot10bp＋perp taker5.5bp每side，各开平一次名义fee-only31bp／匹配单腿金额。
  先看是否存在覆盖双腿成本的收入余量；若连门槛不足，避免建carry engine。若足够，仅支持
  补相应venue可成交basis／event-charge-mark／资本保证金信息，不证明净APR或Bybit收入。
  资金占用、hedge净数量、清算／ADL、摩擦未闭合；两腿不能双计总本金。保持5GB／40GB／GPU0边界。

### D023：固定资金费收入门槛诊断（结果前，2026-10-03）

- HEAD78d2616与实际任务核对：无研究训练任务运行，原两路只读采集／进度服务存活；
  本轮接续D022，更换收入机制。当前盈利主力NONE，冻结RSI2负结果和旧Spot控制不重跑。
- 先核官方fraction／支付方向／事件mark语义，以每币最多3条2025年8月初官方历史API与
  既有archive样本交叉核对；计算记录时间只校准字段，不认证提前availability／精确扣款时刻。
  网络或匹配失败保存，不绕TLS／网络边界；语义未闭合时必须明确条件假设或NE。
- 唯一真实诊断范围：已验收8个funding档、BTC/ETH、2025-08-01..<12-01完整122日，732事件。
  固定每事件单腿单位名义金额、全部signed rates求和及分月／负事件／连续负序列／累计coupon
  回撤，0策略选择／fit／search。它不是固定币数量的真实收款、NAV回放、价格或净APR。
- Bybit普通费率分腿：Spot10bp与perp taker5.5bp每side；各开平一次名义fee-only31bp。
  固定假设每腿slip4bp/side、RTspread2/4/8bp给51/55/63bp，全部报告，不选赢档。
  这些是收入余量门槛，非已验证perp成本；basis、event charge mark、资本／保证金、数量与
  融资摩擦尚未闭合。无positive-future assumption，不选事后高费窗口，不借库存造收益。
- 复用官方PyArrow／Polars与原source QA，最小薄科学计算及独立原CSV Decimal核验；
  不建carry engine、重下载／全24档QA、读取价格arrays或locked。语义／新math／真732
  各按实际凭证记录，失败保留。新工件≤20MB，共享5GBRAM／40GB盘／swap0／GPU0。
  结果只决定暂停harvest或补可成交basis／资本信息；模块验收修文档后正常commit/push。

### D024：单位桥接受限后，仅做显式条件收入诊断（读取732事件前，2026-10-03）

- 官方V1真实exit1为WSL网络不可达；V2使用已有Windows系统HTTPS通道，唯一BTC请求返回
  HTTP451，按冻结规则停止，ETH未请求，0/6匹配。两失败原字节／实际task／来源保留；
  不再换通道、代理、域名、TLS设置或重试来规避交易所限制。单位仍UNCONFIRMED。
- 不把网络失败改名成功。可继续不依赖单位认证的描述性研究：在新协议中明确假设
  原始last_funding_rate为fraction，固定乘10000，完成唯一全期732事件的条件式coupon
  与31/51/55/63bp门槛数学比较；主报告／独立核验均标记UNCERTIFIED_UNIT_NOT_APR。
  该新分支必须显式选择且绑定真实HTTP451报告，runner不能自动fallback。
- 原coupon统计／成本／全122日／币种／负事件口径不变，原strict PASS单位分支保留。
  未运行的strict准备源码／测试按原字节归档后，仅增加明确条件分支和针对性case断言；
  条件实验不能放行真实收入、账户净PnL、净APR、执行或候选资格。
- 若条件收入不足，仅否定此假设下的成本余量；若足够，也只支持下一步核Bybit原生公开
  funding单位／同期间收入和可成交basis／资本。不能把Binance条件coupon当Bybit收入。
  保持真钱／locked／5GB RAM／40GB盘／GPU0边界，所有实际计算仍在bounded WSL。

### D025：条件收入有余量，优先核Bybit原生输入（验收后，2026-10-03）

- 实际唯一主诊断exit0、732/732事件，BTC／ETH原rate和0.01796165／0.01536858；假定fraction
  coupon179.6165／153.6858bp，扣最高63bp名义全期一次门槛仍余116.6165／90.6858bp。
  全部负事件45／57、最长负run10／4，不假定一直正；四个月全部报告，无selection/HPO。
- 采用条件统计与负事件证据，保留carry研究方向，不采用投资候选。盈利主力NONE，净APR
  仍NE。单位V1/V2真实failed1／0matched保留；条件会计通过不是fraction或Bybit收入认证。
- 独立原CSV Decimal全期／月／run／DD／门槛已过，首轮因Arrow large_string兼容断言
  失败。原FAIL643ac6/source3fd保留；仅新prefix补验732条，最大差1.4188e−14假定bp
  低于1e−9容差，不重算已过汇总。组合审计a943e7、根af9399实际0，未称一轮新绿。
- 下一选Bybit官方V5 funding/history固定BTC/ETH各2025-08-01一日小窗口，先核原生单位／
  历史覆盖，成功才按有限固定窗口补全同122日；已锁httpx／既有小来源凭证薄复用，不引
  新SDK／下载framework。固定双边毫秒边界，不读latest／locked；访问限制即停，不绕过。
- 这是当前最大信息差距：已换Bybit成本却仍用Binance funding条件率。先核对应venue比
  新模型或建carry engine更能改变投资判断。原生率有余量后，才补basis／收费mark／净
  对冲数量／费用资产／总资本及保证金，统一风险后净经济比较；31bp是名义费率门槛，
  不是已闭合received-asset／实际成交成本。完整carry资格须这些输入闭合后重开。
  固定RSI2／更多阈值与旧分钟配方按旧reopen条件暂停，能力及阴性证据保留。

### D026：Bybit原生历史资金费固定小窗口（请求前，2026-10-03）

- HEAD `6d46fc8bb9d90a65f2262fb544f1de1a328dc4aa`；盈利主力／候选仍NONE，净APR NE。
  D025的条件coupon支持核对应venue，但不能直接宣称Bybit收入。旧源／经济／单位失败不重跑。
- 最多2个公开只读请求：官方 `api.bybit.com/v5/market/funding/history`，linear BTCUSDT、
  ETHUSDT各2025-08-01 UTC `[1754006400000,1754092800000)`，双边ms参数、limit200。
  固定先BTC再ETH；任一网络／HTTP／业务／格式失败停止，限制状态不重试／换通道／换域。
- 官方integration文档说明部分IP地域返回403；仅采用既有系统HTTPS路径，验证TLS、
  无重定向、无账户头、每响应20s／64KB。Windows只传字节与HTTP元数据，解析／校验在
  bounded WSL，Windows进程peak单列，不谎称纳入Linux共享cgroup。
- 校验原始JSON／SHA、retCode、category、symbol、字符串时间／有限Decimal率、逐条边界、
  重复、返回数小于200及非空。文档不保证保留期／完整历史结算日历；不预填8h或3事件。
  fundingRate仅按官方文档的ratio convention解释，不认证Binance单位、publication或账户入账。
- 本pilot不计算coupon／成本／收益／APR、不读价格或locked、不发单、不启用GPU。
  新工件预算2MB、墙钟180s、当前共享5GBRAM；盘依据最近实际扫描19,413,115,004B
  （2026-10-02 17:00:09.997777UTC），不是新扫描。独立审计后才决定完整122日source采集。
  若限制／覆盖失败，保留失败并暂停原生carry投资映射，重开需合规可达原生来源；不绕过。

### D027：原生接口受限后，转已有来源的基差风险排除检查（2026-10-03）

- 唯一实际BTC请求HTTP403、96B，host session76274关闭exit1，task
  `5ac8dbb781d849ce8a42e51d162fbd65`；报告`eac907e1…9d2765`。ETH／样本均0，
  原生单位／完整性未确认，0经济计算。不重试或另找通道；未启动完整122日Bybit采集。
- 暂停Bybit原生carry投资映射及income adapter，能力／阴性证据保留，重开需合规可达
  的对应原生输入。费用profile保持普通Spot10bp／perp taker5.5bp，不以失败改低成本。
- 下一信息价值最高的是既有全122日Spot与mark/index的基差风险尺度：同币、固定历史
  时间、固定单位数量，所有月份／全部期间的不利变化，零下载／fit／HPO；结果只作
  mark／last-trade代理风险诊断，不称可成交basis／收费mark／账户NAV或APR。
  开始前先明确Spot价格字段／时间语义并冻结源路径／SHA；缺可比价源则不虚构。
- 原条件事件名义coupon余量116.6165／90.6858bp很薄；资金占用和不利价差都可能消耗它。
  因coupon不是恒qty实际现金，这只是待检查的尺度，不与basis简单相加伪造净收益。
  若风险接近该尺度，暂停进一步条件carry工程；若较小，也只支持保留方向补真实输入。
  盈利主力／候选仍NONE、净APR NE。其他暂停路线沿原reopen，完整目标继续。
- 并行只读接线已确认Spot为官方1m kline Close原值cast，而非自行last-trade重建。
  `BASIS_RISK_SOURCE_OPTIONS_20261003_V1.json`（`fd1b4c56…aaee7de7`）列明8Spot＋8mark＋
  8index准确路径及既有SHA；open timestamp join、proxy inclusive close+1ms与Spot逻辑bar end
  对齐。只是元数据，不读／hash价数组、重QA或算basis；尚无basis经济证据。

### D028：固定全期基差风险定义，纠正单项自动STOP（价数组／新数学运行前，2026-10-03）

- HEAD `1fdfd7d6ef23610ee7d1202646a6eb0fab4ad75d`、24价源接线只读已核；当前无盈利候选、
  净APR NE。采用现成Polars／PyArrow／Decimal，不建carry framework或重做原source QA。
- 固定同币q=1：B=M−S，change=(B_t−B0)/S0×10000；正change是longSpot／shortMark的不利
  变化，valuation=−change只是标记价诊断。全期及四个全部月各自取首Spot close S0；
  报告终点变化、最大不利／有利、valuation含initial0的prefix峰谷回撤与极值见证。
  分解M−I及I−S使用同S0和各自初值。月rebase仅描述，不能相加、拼月或每月扣完整成本。
- open严格Aug1..<Dec1，共同逻辑bar end，175680分钟／币、351360总分钟，不填补／删缺。
  原price SHA只核本次绑定；旧CRC／ZIP／24档QA／绿测试／coupon数学不重做。
  仅close／对齐列、0新API／fit／HPO／joined大工件；独占新STATE≤10MB／600s，
  当前共享5GBRAM／swap0／GPU0，D盘40GB保持。独立Decimal容差事前1e−7bp。
- 修正D027的粗暂停判断：max adverse是中途资本／保证金需求，不能仅因接近coupon就自动
  STOP。旧coupon为固定事件名义∑r；本次为固定q／S0价格变化，只比粗尺度，不能相加成净收益。
- 本次之后直接进行一版固定、明确假设的连续条件carry账本，避免更多碎片诊断。
  统一总资本、净qty、Spot received-asset费／Perp quote费、全部正负funding q×M_e×r_e、
  cash／margin reserve、期初期末及dust。Aug1首事件早于首共同闭合价，合法开仓前事件
  不能收，不能未来close回填收费mark。事前固定过去close proxy／成本／风险，不择月或HPO。
  该后续需另冻结协议再跑；Binance价格／条件rate＋Bybit当前费用只作CONDITIONAL_PROXY，
  不解锁历史、不产生原生交易／真钱候选或长期APR证明。若完整固定账本净负，暂停该配方；
  若净正而资本／成交未知，下一步验证真实可成交basis与保证金，不以杠杆／低成本放大APR。

### D029：条件carry固定账户口径（新carry合成／市场回放前，2026-10-03）

- basis主体全122日完成，尚待独立审计；终点变化BTC3.0661／ETH2.1805bp与中途回撤
  114.5151／344.1374bp不同，不能把风险直接扣旧coupon。原生输入仍未取得、候选NONE。
  下一项只跑一个全期连续条件账户，不追加更多单项hurdle或参数搜索。
- C0=10000USDT；首次共同闭合价产生订单，下一分钟闭合价代理fill，每币事前定额
  q=1250/首signal Spotclose。Spot买gross=q/(1−0.001)，复用received-asset结算，
  perp short精确匹配净base；fractional qty、真实filters／capacity未知，dust0仅条件假设。
  每币预存1250USDT独立保证金，其余freecash；short卖出名义金额不进入cash。
  单成本：每腿RTspread8bp、每side slip4bp，即fill相对mid±8bp；Spot10／perp5.5bp
  taker每side。保持最高既有成本假设，不降费用、不加杠杆或期末择窗。
- 全账户实际NAV=sum freecash＋两isolated权益＋Spot库存；funding全部signed，
  q×严格过去closed mark×未认证fraction rate，只归属entry<event<exit；首开仓前事件不收。
  复核官方Bybit文档：funding先available cash，不足才减isolated余额；fee以USDT结算。
  开平fundtime±5秒实际归属不保证，报告近边界见证而不声称真实平台到账。
  所有事件现金前后进入峰谷／DD，转账与realized/unrealized不双算。
- 复用原更严gross≤0.6／每underlier两腿≤0.3；任一触顶或isolated权益≤初始50%
  触发一次下一分钟全平，之后永久CASH，不再入场／重平衡／事后调门槛。被动漂移和
  下一fill gap的实际超限如实报告；这是自设保守guard，不是Bybit维护保证金或清算模型。
  固定最终端点只做模拟平仓，结清两边费和资金，不按月重开账户。
- 同C／费用／exposure caps可对照旧Spot研究，旧30d covariance/10%vol、真实perp容量、
  MMR／ADL／venue历史及实际收费mark均NE，不能称完整风险等价／原生投资回测。
  新独占STATE≤50MB／900s，共享5GB／swap0／GPU0／D40GB；来源继续固定既有
  Aug1..<Dec1全部24价档＋8funding档，无新API／locked／HPO／旧绿重跑。

### D030：完整负结果后检验持有截断机制（新减仓数学／数组运行前，2026-10-03）

- D029主体／独立金融／根验收真实closed0；10k资本条件净亏11.011349USDT，funding5.621259，
  总成本16.680241。ETH名义cap而非margin触发约11.65日后永久CASH；全部732事件中68计入。
  暂停该ALL_FLAT配方的盈利采用，保留账本及固定控制；不据短持有负结果删除carry能力。
- 下一项仅一个相同122日的matched pair减仓机制：原gross0.6／每币0.3、费用／spread／slip、
  C0／初始q／1250reserve／625margin阈值不变。敞口触发时冻结q_keep=0.25×signalNAV/(signalS+M)，
  下一严格较晚closed分钟仅减该币等量Spot／short，保留另一币；无增仓、重入、补资或参数搜索。
  partial realized只结一次，reserve不返还；margin触发仍全部退出，isolated≤0仍明确FAIL。
  exact funding与partial退出同时则closing chunk排除，continuing chunk继续持有；事件优先级事前固定。
- 复用冻结d29账本的精确AST薄适配，不复制整个循环／新建框架、不改旧证据。独立手算应核
  partial钱包／费用／funding ownership／signal sizing因果性；另冻结独立协议后唯一完整回放。
  同窗为已见机制控制，不叫unseen OOS或长期APR；原native单位／price／filters／MMR缺口继续披露。
- 预期信息价值：区分“收入不足”与“单币cap使两币收入截断”，直接衡量延长持有的额外funding
  是否超过减仓维护成本。原全平配方reopen需新独立时间／原生信息在同风险成本下显示净稳定性；
  Bybit原生映射仍需合规可达原生输入。新STATE≤50MB／600s、共享5GBRAM／swap0／GPU0／D40GB。
- 新减仓代码运行前补充钱包正确性：partial realized为正只credit freecash；为负复用
  freecash-first→本币isolated debit，禁止负freecash信用或跨币救援。reserve不返还指不按
  减仓比例释放／重置／补足余额，不阻止实际损失扣余额；原625阈值不变，剩余entryfill不重置。

### D031：小正净值后固定时间否证（新90日源／carry数学之前，2026-10-03）

- D030完整主体／独立／根验收真实closed0，10k资本净+24.744852USDT／122d，fund39.512100，
  最高既有成本14.390056，仅一次ETH减仓维持730事件。采用研究机制但候选NONE、长期APR NE。
  全观察DD0.387572%比原全平0.110113%高，机械样本年化0.742143%仍小，不以daily Sharpe选赢家。
- 下一项冻结原pair-trim与ALL_FLAT规则／资本／费用／caps／margin，跑2025-12-01..<2026-03-01
  两个固定账户；不调target、不择月、加杠杆或降成本。旧Spot6档复用原accepted SHA与真实exit，
  缺funding／mark／index18月档，先复用已有官方薄download_archive／convert_source并核新来源，
  不另造downloader，不重复旧source QA。另协议冻结后才新数学，新增源预算先≤200MB／共享5GB／D40GB。
- 12–2月此前用于Spot研究，称固定时间稳定性SCREENING而非真正unseen OOS；核心要否证正funding
  与basis能否跨时段支撑小净利。原UNCONFIRMED／Bybit403／REST451证据保留，不重试绕过限制。
  官方一般费率公式不能认证archive last_funding_rate映射，单位／native仍门槛，不覆盖旧失败。
- 不继续pair-target HPO；旧flow的perp低费映射暂后排，缺过去可得优势及matched perp经济证据。
  全平配方reopen需新独立时间／原生信息同成本caps下净稳定性；maker需真实BBO/queue。
  普通科研继续，locked／真钱／密钥／新付费／GPU权限不变；无需等待固定roadmap或时间规划。

### D031来源闭合（2026-10-03）

- 主体18档actual0、独立QA actual0、根验收actual0：实际540资金事件／518400价行，新增30.8MB；原官方download／转换／audit_one精确复用，未重做旧QA。首次启动参数错误在source执行前失败，保留。
- 采用新来源格式，单位仍UNCONFIRMED、没有新账户收益。下一固定90日ALL_FLAT／PAIR_TRIM共用输入与BybitVIP0原费用／caps／margin；新周期和端点协议先冻结、0调参，标签SCREENING，不叫unseen。原native／盈利资格缺口与暂停reopen保持。

### D031经济闭合（2026-10-03）

- 固定90日两控制实际exit0、独立V3和根验收exit0：均10k→10003.988973，净+0.039890%、fund17.573984／最高既有成本13.362536。0减仓，minute／daily净值SHA相同，不能将相同结果当减仓再次胜出。
- 2月net−9.373282／fund−3.189198，gross-cost-addback亦−3.877301；收益源变号而非仅期末手续费。全观察DD0.198205%、daily0.094190%分别保留。122日+0.247449%与90日分别报告，不拼接为连续APR。
- 接受薄周期／来源／端点与条件账本能力；暂停静态配方投资采用，候选NONE／长期APR NE。独立区段定位与不存在的PAIR_TRIM旧literal guard导致两次真实exit1，失败／partial均保留；最终V3两case闭合，不将失败改PASS。

### D032：固定过去资金费永久退出假设（新状态控制／数组数学前，2026-10-03）

- 不继续调减仓target或挑2月退出；新增一个无拟合假设，完整原122日与90日各一个新账户，对照已保存pair-trim。C0=10k、初始q／1250reserve／625guard、gross0.6／单币0.3、BybitVIP0 fee／spread／slip、延迟／ownership规则完全保持；不新下载、改旧源码证据或重跑控制。
- 原开仓不变，持有满8×24h后，在每日00:00 UTC用决策前完整7UTC日、结束于决策前1UTC日的已归属signed funding合计；窗口首时刻须晚于entry。合计≤0则下一严格较晚closed分钟全平、永久CASH。原margin全平优先，已经排定的cap partial照固定事件优先级处理；无重入／增仓／补保证金／按币赢家选择。
- 一日滞后是显式未认证publication假设；raw archive event time／fraction／真实平台到账仍未证明，不能把历史已实现coupon视为即时可交易信号。新协议／费用钱包／退出ownership因果边界先冻结验收，再一次完整运行，7日窗／1日滞后不因结果更改。
- 预期信息：过去负coupon是否持续、提前永久退出损失多少后续正收入及两腿退出成本；从两完整窗口净值／事件DD／费用／放弃coupon判断，不以单月或Sharpe采用。两窗改善不一致或主要正收入被截断，则暂停这一固定gate；不接着扫3／14／30日，重开需新过去可得状态信息或真正时间外证据。原静态carry能力及负结果保留。
- 新模型拟合0／HPO0；预算共享5GB、swap0、GPU0、D40GB，新STATE两账户合计≤50MB／每任务≤600s。Bybit native重开仍须合规可达原生输入／filters／MMR；locked／真钱／密钥／付费／冻结覆盖须另获授权，普通研究继续。

### D032实施时序澄清（新gate数学前，2026-10-03）

- 日界锚点D=00:00 UTC，观察窗口精确为[D−8day,D−1day)，排除最近完整日，window_start>entry；合计为实际OWNED的两币signed funding现金，不用raw rate之和、不按币选择，真≤0且不加数值零带。复用原closed+1μs观察阶段判定，记decision_price_close_us=D及decision_observation_us=D+1；新退出在(D+60s)+1μs，原事件／fill循环不拆写。来源整数ms×1000不能在D+1μs发生事件，日界coupon输入仍严格滞后；原margin/full与已due partial优先规则保持。该时序明确实现口径，没有依据新结果改窗口／阈值；publication单位资格仍未认证。

### D032比较口径冻结（新gate正确性／行情数学前，2026-10-03）

- 两完整窗口分别对照已保存PAIR_TRIM；研究机制采用需每窗netΔ>1e−7USDT、all-observation MDD≤各自control+1e−10且原成本／risk／wallet检查闭合。阈值只是沿用会计误差判可分辨增量，不称为经济显著性、长期APR或完整风险等价。
- “主要正收入被截断”明确为退出后放弃的saved-control实际OWNED正coupon超过其全期OWNED正coupon总额50%；任一窗出现即暂停这个永久退出配方。负coupon避免额、净放弃额、暴露／费用／月度净值完整并列；这些均为结果后条件归因，不进入交易signal／NAV或倒选月份。0触发／两窗无一致净改善同样无新增采用依据。
- 门槛不会因本轮结果改变；Candidate仍NONE、长期APR仍NE。失败只否定固定7日／1日滞后永久退出，不永久删除adaptive learning或资金费能力，重开须新过去可得状态信息或真正时间外证据。
- 数值谓词事前明确为math.fsum已实际credited且逐事件独立核验的Float64 ledger cash≤0，无零带。Decimal钱包只核金额，不替换该决策符号；另报告Decimal.from_float精确和／独立钱包Decimal和及符号分歧。触发若对舍入敏感，保留ROUNDING_SENSITIVE_TRIGGER_WITNESS并暂停本固定gate采用，不把数值边界当稳定经济信号。

### D032经济闭合（2026-10-03）

- 两完整新账户、独立Decimal、经济比较及根验收均真实exit0；122日净12.138169，对控制−12.606683USDT，观察DD0.387572%→0.416530%；90日净6.567334，对控制+2.578361，DD0.198205%→0.121545%。不拼两账户，不择月／改阈值／费用／杠杆。
- 122日永久早退避免负coupon0.707383却放弃正12.164115USDT；90日避免3.862038、放弃1.649367。这是saved-control实际OWNED结果后归因，不是新钱包现金流。单段改善不抵消另一段净值及风险变差，固定门槛false；舍入敏感计数0，会计最大误差1.42027e−11只认证计算。
- 暂停固定7日／滞后1日永久退出配方，保留因果gate、carry、已见控制和负结果；不接着扫窗口。重开须新过去可得状态或真正时间外证据。单位／Bybit原生／MMR／availability仍未认证，候选NONE／长期APR NE。
- 初次freeze import启动真实exit1且无行情／数学，原失败保留，后改子进程绝对路径。比较／根metadata的浮点一致性与类型guard均在执行前薄修，无旧金融／QA／绿测重跑或冻结覆盖。完整验收／源码与实际task绑定见D032报告。

### D033：较长固定公开策略开发否证（新范围适配／数组数学前，2026-10-03）

- D032不稳定且净余量小，不继续carry退出窗HPO。此前公开2h与hybrid在122／90日的胜负也不一致，尚无统一赢家；现金继续为防御基准。下一唯一问题是原公开配方的较长经济路径是否仍有费用后优势，而非增加模型／更低费用。
- 固定2024-01-01..<2025-07-01全部547日，2023-12仅31日warmup；使用既有CASH／COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER／COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER三个账户。直接复用MIT Jesse pin与原fixed_targets/native账户，原10k／30%单币／60%gross／10%目标波动／30日min20日历史risk、延迟／容量／lot保持；只用已接受36bp档（Spot10bp/side、slip4bp/side、spread8bp完整）。0拟合／HPO／配方选择，旧30／32bp账户不重跑。
- 这段历史曾用于旧训练／测试，明确项目级SCREENING，不能称真正unseen／投资资格。locked2026-03..<09价格不消费，也不借其warmup。38档旧QA／lock metadata具备，但新专属source receipt和当前文件SHA核对尚未完成；静态笔记不冒充source accepted。
- 最薄实现是隔离新period namespace/date guards及一个固定成本subset，复用共享入口、targets、回测和费用资产守恒；不改冻结labels／core或复制策略。旧源helper的2025／微秒假设不能套到混合毫秒／微秒新档，保留原QA元数据。新protocol/必要边界case先冻结，明确38路径，禁止全库加载／locked fallback／重跑旧QA。
- 预期价值是以完整长账户分辨少数月份贡献、信号稳定性和换手成本。全期间净值、事件DD、费用与风险暴露并列，月表只诊断不挑月／拼curve。若无净优势或只由少数月份支撑，则暂停原配方投资采用，重开需真正未来证据／新信息；保留公开benchmark能力。
- 普通研究继续，预算先新STATE≤100MB、共享5GB／swap0／GPU0／D40GB，后续执行前按实际scope固定wall预算；无原生认证／真钱／密钥／付费／冻结覆盖权限扩张。2h／hybrid只重开冻结配方长开发否证，不重开参数搜索；RSI2／分钟／1h／maker依原reopen。

### D033执行前容量修正（来源哈希／数组数学前，2026-10-03）

- 只读旧122日已验收物理IPC metadata为440640行／42,471,691B；按新1664640行比例，原不可变IPC单文件约160.45MB，原100MB不足。保留原IPC读取与金融循环，不为预算重写IO／压缩或丢弃账本。新source＋研究＋独立审计的专属STATE合计固定≤400,000,000B，来源子任务≤10MB；研究wall固定1800s、来源300s，独立审计600s。共享5GB／swap0／GPU0、整个D项目＋VHD40GB／36GB停止新增保持，启动复用原磁盘预算守卫。
- 这项修正依据已存在文件大小，未读新价格行或按结果改策略／成本／风险。新元数据来源通过只证明38档当前字节与旧QA绑定，不称新QA或经济通过；三个账户各自完整547日，不重复旧绿色用例和旧收益。

### D033独立验收修正（2026-10-03）

- 三新账户实际closed0，新增333,111,127B／主体RSS2.246GB；无策略或费用修改。独立大frame在运行前明确自身RSS上限3.5GB、共享内核仍5GB、600s；原512MB草稿未执行，完整578日源和逐分钟意图不适合该旧小窗口RSS数值。
- 唯一独立V1真实exit1、0金融账户：CASH理由断言漏掉原benchmark最后一行固定COMMON_TERMINAL_EXIT_INTENT_NEEDS_FEASIBLE_FILL。现金权重全零，生产源码／收益／费用／会计误差均不改。V1失败、实际task和source字节保留；V2只修首至倒数第二行为CASH、末行为该精确标记，独立新报告重新验收同3账本；不重跑生成器／策略收益或旧绿用例。

### D033经济闭合与D034选择（2026-10-03）

- 独立V2真实exit1：原非现金财务段np.char.replace遇零成交空字符串数组，0金融账户；全部3意图检查已过。V3只对这一精确表达式添加空成交空数组分支，非空原式、完整资金公式及容差不改。V1/V2失败与源码保留；V3实际closed0，3×787680分钟／547日／18个月及逐成交Decimal结算闭合。根actual closed0，未重放策略收益、原始38源QA或旧绿测试。
- 2h净760.184608USDT（+7.601846%，样本描述年化5.010455%）／minute DD12.664746%，hybrid净583.999316（+5.839993%，描述年化3.859977%）／DD8.796848%；资金10k、36bp与风险规则相同，实际vol8.90%／7.59%不同，不宣称统一风险已胜。后者gross多108.124396却多284.309688成本，net少176.185292。
- 2h8/18正月、hybrid6/18，最大正月份贡献36.76%／52.93%；两者2025前半年亏损。期末602.035934／1134.522099USDT仍是实质持仓市值，保留可行性不足，不删持仓／假清仓／把标记利润叫已变现。长期净APR仍NE、候选NONE；原配方留研究参照，hybrid未获主力升级。重开投资采用须真正未来／原生执行下净稳定优势，不因长窗口正数就认定可持续。
- 下一唯一高信息问题D034：公开主动交易是否胜过同样受控的简单市场暴露。直接复用原VOL_MANAGED_BUY_AND_HOLD，固定同547日／31日warmup、同源／10k／原common风险／BybitVIP0 received asset／36bp，一新账户；原三个D033保存结果只作比较、不重跑。先冻结新子集适配与独立意图验收，0 HPO／新阈值／费用或杠杆放松。若简单基准在相近或更低实际风险下至少匹配净收益，则原主动配方缺少增加复杂度的经济依据；比较完整暴露／成本／回撤，不凭一个Sharpe或月度赢家采用。D034尚未运行，不改D033预登记。

- D033 Git元数据边界：实际preflight session33053／chunk84d8b8 exit1，唯一缺失为本机state/dataset_lock.json（原绑定哈希29d930…92f45d）。不改完整闭合报告或标准守卫；执行新的portable投影，保留本机哈希、原来源报告哈希及失败任务实际元数据，所有可入库冻结文件继续逐字节核验。此决定先于修正投影运行，无新价格、数学或协议变更。

- D033 portable投影实际chunk105955 exit0，d48ccd…271911，保存原失败task709480…/sha95cb15…与2ef32c…失败凭证；只有本机state锁从Git用途pins排除，独立校验锁字节，标准guard2f709f…未改。重跑标准提交门槛仍必须通过；不以投影成功代替Git验收。

## D034运行前接线与预算（2026-10-03，HEAD cc2f2df）

- 主问题仍为公开主动交易是否胜过受控市场暴露；只新增原VOL_MANAGED_BUY_AND_HOLD一个547日账户，同2024-01-01..<2025-07-01／Dec2023预热／10k／原风险及36bp received-asset费用，0fit/HPO。三D033账户仅保存结果比较，不重跑；所有历史已见，非unseen／盈利资格。
- 复用原common.reused_minute_input的父shared_source_minutes.parquet；不重读38档源数据、不下载、不重做旧QA。按原research写新Parquet与IPC，未造新IO框架。实际只读stat显示这两输入分别50,992,557／160,444,779B，合计211,437,336B，初步200MB设想不足且从未运行；先固定本轮总STATE300,000,000B（research280MB、唯一synthetic10MB、独立与根等10MB）再开始新市场数组IO。共享RAM5GB、单科研／审计RSS3.5GB、CPU2、swap0/GPU0；research1800s、audit600s。沿原磁盘守卫核D盘总量，不改守卫。
- 具体新增correctness接线：D033无VM调用，未克隆v2.causal_vol_multiplier，继承函数globals仍绑旧2025范围。只在新D034私有namespace克隆该原wrapper并绑定已隔离时间／v1；原7完整日EWMA、10%意图cap和common30日／最少20日risk均不改。唯一新case覆盖这条2024日度availability路由、单账户／单成本／终端规则及共享globals未变，旧绿例／金融循环不重跑。
- 采用判断：仅核新账户意图／账本与完整547日／18月，和三份冻结D033并列net、cost、turnover、actualvol、minute/daily DD、持仓。若简单基准在相近或更低实际风险下至少匹配主动净收益，则暂停原主动配方新增复杂度研究；不以共同caps宣称实际风险相同，不事后缩放收益或选月。新协议与exactsource冻结后才执行；locked／真钱／密钥仍不消费。

- D034唯一case第一次实际session7560／chunka429aa exit1：daily group_by表未承诺行序，测试daily[0]最早日假设错误；原causal_vol_multiplier先sort，未见策略错误，无市场回放。失败协议685ecb…、原test be56…和report ；新test_v2仅在构造daily后sort(day_end_us)，新protocol V2记录preceding_failure及旧原字节。费用／规则／预算不变，针对该新增边界复测，不重旧绿／金融。

### D034 — 原波动管理持有共同547日证据与下一科研选择（2026-10-03）

实际b56cb8／独立469514／比较10e1ef／根32f166均真实closed0；独立1账户×787680分钟／547日／18月。VM净+1606.234069USDT（16.062341%）、机械CAGR10.450318%仅描述，vol10.163562%／minuteDD9.254981%，总成本147.284759、turnover7.376604，terminalMTM698.732589。旧2h/hybrid只读D033保存结果，未重放。两组严格Pareto均false；不以本轮实测vol事后缩放或标为同风险赢家，CandidateNONE／长期APRNE。12正月／18；2025H1净+21.443850，正月份集中度分母仍为正net月之和。

采用固定VM benchmark／独立时序与核算能力；暂停VM／2h／hybrid投资采用，未来／原生同成本风险净稳定优势为reopen。D035优先固定原VM配方，在已有122日与90日不同市场窗口各新增1完整账户，同36bp/风险/资本/两层vol、旧保存控制不再执行。目的检验长上涨窗口暴露与成本节约能否跨状态成立；不新增HPO、阈值／杠杆、资金权限或locked访问。保留20%frontier方向，数据映射／执行信息未改善前不盲目重训旧负模型。

失败保留：V1合成行序假设失败session7560/a429aa/1、报告a09f；新V2只对测试日表排序（生产本来排序），session95898/64cfe9/0；协议V1/V2与源原字节保存。主体81.55s/RSS2.147GB、独立27.76s/RSS974MB，共享5GB/swap0/GPU0，五新增STATE268476489B≤事前300MB。实际扫描19.773GB时刻06:06:46.642795+08保留，随后工件不计入旧扫描。
### D035运行前 — 固定原VM跨两个后来市场窗口（2026-10-03）

实际HEAD6ce25c0115ff24ce1dc97ed0115eb9dea522535d，D034上一轮为progress（实际／独立／根验收／Git精确同步409d0e凭证）。本轮查到仅原公开分钟／L1采集及8765服务活着，无正在科学回放；不重启采集，不把进程存活记资格。

问题：D034较高net主要由上涨暴露与低周转贡献，是否在后来不同既定窗口仍保持？两个固定账户 CONT122=2025-08-01..<2025-12-01（31d暖启动Jul1）、CONT90=2025-12-01..<2026-03-01（31d暖启动Oct31）；都为已见SCREENING。原VOL_MANAGED_BUY_AND_HOLD span7/min7/allpastseed及30day/min20两层10%风险／资本10k／.6/.3caps／36bp BybitVIP0收到资产扣费原参数不变。仅复用已接受native2h parent Parquet四字段；旧2h/hybrid/cash保存控制不重放，不重QA或拟合，不访问locked。

来源元数据确认：122旧source153d/10档、衍生440640行；90旧source151d/10档，派生仅Oct31后121d/348480行。两旧SOURCE没有taskid，不伪造closed任务；按原接受SHA及父实际绑定复用。现金对照为旧quote-fee零交易0fills/flat参照，费用作用为空，不重标Bybit原生认证。旧parent冻结common bff与当前已接受3dfa差异在新协议显式记录，仅薄成本计数改变，不改旧字节／金融数学。

事前预算：两原输入新副本PQ+IPC100490893B；research122≤75000000B、90≤60000000B、唯一新synthetic≤10000000B、独立/根/metadata≤5000000B，模块总≤150000000B。每市场≤900s、独立≤600s；每进程RSS≤3.5GB且共用5GB/swap0/GPU0，D40GB继续。源码/test/两协议实际冻结前不启动市场IO；原disk guard在启动时真实扫描，须32GB以内新增且留1GB工作临时余量。固定严格Pareto沿D034：净不少、actualvol不高、minuteDD不高且一严格；两对照分别比较，不事后缩放波动、不拼接选择月份、不把年化当持续APR。
### D035独立验收接线修正（2026-10-03）

两新市场账户已实际closed0，未改策略/费用/风险。唯一独立V1报告fdc4cb0683cc224943ca4ec7bbe018f452f21bb77221c230cf86f38f359a1bcc实际session81113/chunk05f254 exit1，0金融账户、runtime_inputs为空：旧native父协议没有显式source_scope键，新增独立metadata守卫错误要求此键直接存在。不是金额/策略失败，不重跑市场账户或旧QA/绿测。保持V1报告/任务/源码752c/绑定原字节；新V3仅按两既定CASE、父实际和旧接受SOURCE凭证核三个来源字段，其他parent固定条件不变。独立成功另写V2新报告与新STATE，原数学/金融AST/Decimal/容差不改。模块6个自有目录合计仍≤事前150MB，新增V2元数据计入原5MB余额，不放宽成本/资源/采用标准。
- D035根元数据首次真实task0cba169a35f14dd7a4e7f041a2838652/session72876/chunk363ae6 exit1：比较pin集合含Python源码，ROOT错误默认JSON解析它；五科学角色已完成，未重放任何金融。小失败凭证de0e4b原字节/任务/code7df/binding7e036保留。新ROOT helperV4仅该混合pin循环按字节/SHA验证parse=False，自身档案名另定；V3未执行草稿通用路径替换问题另以906954短凭证记录。新close-binding另写V2，不覆盖V1；费用/源/数学/容差/150MB采用标准保持。

### D035经济闭合与D036选择（2026-10-03）

两个新账户实际a58b6936/0bf3fbf2，独立成功V2 2ce85bfa、比较60c499a2、根244e15ea均真实closed0；唯一新case，无旧市场/QA/绿色复测。122/90净−412.710118/−563.381606、gross−369.558668/−533.515250，成本43.151450/29.866356。原公开2h/混合各在两个后窗严格Pareto支配VM（net更高，actualvol/分钟DD更低）；不据此宣称所有历史胜者或长期APR。旧547日VM正16.062341%原样保留，后三账户不拼收益。90日terminalMTM612.394894实质仓位仍marked。

采纳共同基准/时序和资金核算能力，暂停VM投资升级；原2h/hybrid也无跨状态稳定资格，长期APR NE/Candidate NONE。两个失败均仅metadata，根字节parse修正版V4完成，独立V3完成212d/305280min/7月和每成交Decimal桥；原金融AST、容差、源/策略/36bp规则未改。六STATE127021300B≤150M，共享5GB/swap0/GPU0，旧source资格不得伪造task。

最高信息下步D036：两个公开策略排名翻转不自动构成分散化，它们共享2h入口且四个保存月份共同负。先按三个固定独立窗口547/122/90，仅读已接受日损益/仓位/成交工件，诊断日收益相关、共同负日、尾部损失和暴露重合、成本贡献；不重放旧账户、拼NAV、选月赢家或改阈值。互补充分才事前固定唯一50/50目标组合并按共同10k/风险/36bp真实重算，不能平均旧净值冒充可交易组合。若同质则暂停组合，需不同因果信号/执行信息再重开。公开策略能力保留；所有普通研究自主，locked/真钱/keys/paid/GPU及资源边界保持。