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
### D036运行前：公开策略互补性，固定独立547／122／90日（2026-10-03）

当前HEAD89a305d，D035已实际验收／远程一致。当前主力候选NONE、长期净APR未建立。最高信息问题：2h入口相同、退出速度不同的两个公开策略，历史排名反转是否来自可用的亏损／持仓分散，而不是相同暴露上的样本噪声。

仅读五份已接受producer中固定spread8、BybitVIP0收到资产扣费的P/H日净值和分钟marked inventory，三窗口分别547／122／90日、账户各10k；共12文件约72.90MB。不重放行情／资金循环，不读fills、不拼接账户、不输出平均净值为可交易组合。日损益NAV差额首日前值10k；收益率差额除前日NAV；worst10%采用ceil、同值按UTC日期稳定排序；实际标记持仓重合按分钟／币种min/max金额权重诊断，正dust单列限制。共同风险意图相同，实际风险不同。

代码、来源、fee／env、计算与下一步预算判断规则在任何数组读取前写入新protocol；小输出／STATE合计<=5MB，单进程RSS<=1GB、主体wall<=300s，共享5GB／swap0／GPU0继续。独立验收仅检查新统计／对齐与预登记决策，不重复旧资金数学、QA和绿测。已见历史全部SCREENING，不用locked；无fit/HPO/orders/native认证。

此轮只决定是否值得下一唯一固定50/50目标共享账户实跑，不能从诊断取得投资资格。足够互补才固定且重算真实共同资本／成本；高同质则暂停该组合，保留单策略能力并给不同因果入口或新的时间外损失分散证据作为reopen。结果后只追加选择理由；不修改既有冻结证据或事后调筛选阈值。
### D036统计闭合与D037选择（2026-10-03）

actualV2 888f230b（session48238/chunk53589f）、独立4964e6f3（session7464/chunkf1f6cf）、根10fe6b4c（chunk949fc5）真实exit0。759独立period日／1518account日／2185920分钟投影；12已接受旧账本文件，只重算新统计。3窗净PnL Pearson .9030869256／.8464414955／.8376036937；fixed tail counterpart净亏损6个方向全部负，90日weighted exposure .8486806791；两个后窗tail日期交集/k虽<.7仍未避损。事前四条件AND budgetfalse，统计PASS独立，采用诊断能力、暂停本50/50组合；不把暂停推广为所有ensemble无效。

下一D037最高信息选择：固定一个原开源Donchian日线（不新增信号公式／HPO），用不同物理入场期限与更低换手检验当前同质和成本瓶颈。原SMA200／20日channel需要>=200个已完成日的因果warmup，先解决来源／数据角色和同评分区间，不消费locked。统一risk/capital/36bp，不做事后vol匹配，真正共享账户能力与旧所有负结果保留；现在未冻结该日线研究、未下载或运行。

D036科学启动V1因Progress AST visitor扫到动态update.total，在STATE／registry／array前真实18ecbb…exit1。原7cac/source124c协议保留，新3084088薄入口只限定__init__显示字面量；科学循环未改。原PS H别名首行失败保存原factory；新命名替换造成说明P/TaskHash误字，以5a76f9独立erratum解释结构化P/H（一直正确），不覆盖协议或改变筛选。二目录1,064,080B≤5MB，5GB／swap0／GPU0。预算暂停reopen=不同过去可得入场信息或合法未来同成本尾部分散。投资NONE／长期APR NE。
### D037实际运行前选择（2026-10-03）

HEAD=d8f6c3fbc6df919f1a68e30415df09e0e666b3c5，实际8765无遗留研究运行；原两采集进程仅存活，不补健康资格。日线公开Donchian采用同一MIT原hook（prior20 channel/current-inclusive SMA200），固定UTC1d，不搜索参数。问题：不同物理入场期限能否降低同类亏损和成本、在三个既有评分窗增加净损益。对照引用已验收2h/hybrid/VM保存结果，旧账户不重放；547/122/90日均SCREENING，独立10k，统一原风险和36bp代理成本，BybitSpot收到资产扣费10bp/side，不混永续5.5bp。

新增来源固定官方Spot monthly1d，2023-06-01..<2026-03-01，33月×BTC/ETH共66ZIP及CHECKSUM，每币1004日；首次评分前214完整UTC日预热。只预热指标，不带仓位／交易，每窗fresh flat；200连续已完成日、available<=decision、缺日/延迟拒绝，原下一分钟close+1us成交。分钟执行/风险来源复用既有绑定Parquet，日线收盘从官方1d档输入，不下载额外1m、不消费locked。

运行前分别冻结source/新薄adapter/唯一新增边界验收/3窗口经济协议。新增source硬10MB，三经济及独立工件合计预期<=400MB（各角色协议单列硬预算），共享原5GB RAM/swap0/GPU0；actualscan记录时间，未知进度不造百分比。采用或暂停根据同成本净损益、实际风险／成本贡献及后窗稳定性；不以历史最高APR挑参数，失败保留与reopen，长期APR和真钱资格仍NE/NONE。

D037经济协议冻结前预算修正：只读原547日VM实际receipt，旧单账户STATE264,486,229B，原240MB单角色估计不足。新547硬280MB／122硬70MB／90硬60MB，来源10MB／唯一case10MB／独立10MB，合计硬450MB；预期仍<400MB。现已实际source62/66元数据，无新经济数组读入，预算在经济运行前修正。D盘40GB／32GB预警／36GB停新增与1GB临时总预算不变，不改科学、成本、评分、原账户或资源守卫。

### D037经济验收与D038选择（2026-10-03）

3固定daily账户实际closed0，独立f49cc375（session81108/chunkdc1406）759日/1092960分钟/25月与原金融AST39ffd914实际PASS，保存比较cd128eeb真实closed0；rootV2闭合，无市场/旧QA重放。net547+577.024120/122−598.097288/90现金0；122同净收到数量gross−558.338202、成本39.759086，gross机制是当前最高瓶颈。547被hybrid、122被2h/hybrid在net/实现vol/分钟DD描述性支配；90零成交不能当盈利信号或未来资格。

采用官方daily源/因果薄adapter/核算能力，暂停本固定Donchian投资采用和参数重复；不同过去可得、事前固定机制或真正未来同成本风险有效证据可reopen。两source startup失败与rootV1内部pytest alias误拒绝留存；V2只接受精确同owned测试链接，不改金融或磁盘guard，原文件/实际exit1不覆盖。

下一D038固定 Jesse原SMA50/200日线long-only（同MITrepo/commit7c91e0a）：fast>slow可入场、fast<slow退出、相等维持；不限恰当日交叉。此为不同慢趋势状态，信息价值高于Donchian20/200/exit再搜索；同时改变入场退出，不能声称纯入场消融，亦未证明低相关alpha。复用66日档/分钟parquet/共同10k/风险/36bp，零HPO；三独立seenSCREENING只作新机制筛选，不拼NAV/碰locked，源码和单新case/协议将在新数组前固定。未来原生/稳定性若仍不成立继续现金候选NONE；长期APR NE，普通自主研究无需逐项批准。

### D038运行前：固定公开SMA50/200趋势状态（2026-10-03）

当前HEAD7da8e0202874d50a6c00651312c261e65811772b，D037实际/独立/根/远程一致已核，8765无遗留研究任务。投资候选NONE、长期APR NE。122日日线Donchian gross−558.338202而成本39.759086，最高信息问题是不同慢趋势入场/持有机制能否改善价格收益稳定性；不继续同Donchian参数/退出搜索。

固定Jesse example-strategies MIT commit7c91e0a37bf62165790120d730442e4f6eb00364的SMACrossover50/200，UTC1d long-only移植：fast>slow可入场、fast<slow退出、相等保持，不限当日交叉；原short/wholebalance不移植。一次改变入场和退出，不称纯入场消融，未证明独立alpha。只一配置/零HPO/零fit，用三个独立10k账号547/122/90完整评分窗，全部已见SCREENING，不拼净值、不以其证明未来资格。

复用D037封存66官方日档/2008行/每币1004日、每窗200完成日仅warmup/fresh flat；复用原已接受分钟Parquet与下一分钟+1us执行/容量/风险，旧行情QA/账本不重放。BybitVIP0Spot收到资产费10bp/side、spread8bpRT、slip4bp/side，固定36bp往返；仍Binance行情代理，不放宽成本或杠杆。新原hookvendor/license预绑定与registry归档登记、薄adapter/唯一新增贯穿1case/三个经济协议将在市场数组前冻结。

预期专属STATE<400MB，硬450MB：547账户280M、122账户70M、90账户60M、新case10M、独立10M、vendor/provenance与元数据20M；不再下载市场数据或安装环境。共享5GB/swap0/GPU0和D总40GB、32预警/36停新增/1GB临时预算不变；各长任务在8765显示真实状态，缺内部总量不造百分比。独立核验只核新增SMA targets和三新账户；金融AST/费用/执行守卫原字节保持。净收益、gross与成本贡献/实际vol和分钟DD共同描述筛选，零交易只记现金，无长期APR/真钱认证。

### D038经济闭合与下一研究选择（2026-10-03）

固定SMA50/200三实际closed0：547日net+940.611246/gross979.538133/成本38.926887，122日net−531.707290/gross−521.729329/成本9.977961，90日零成交现金0。实现vol13.174393%/14.749935%/0与分钟DD13.765712%/11.339604%/0；547末1662.260412USDT实质MTM库存、BTC被动漂移34.491194%披露，不当dust或已变现，不从利润扣库存本金。独立V2/保存比較/根实际验收闭合，原caseV1错误补买断言与独立V1新registry路径兼容失败留存，V2只新断言/精确路径bridge，原金融/target/容差不变。

采用开源hook/因果日线/核算能力，暂停固定SMA投资采用和周期HPO；不同事前固定过去可得信息/机制，或真正未来同原生成本合理风险净稳定证据可reopen。候选NONE/长期APR NE；已见独立账户不拼接，相同caps非同实际风险，费用不放宽。

下一最高信息研究选择：固定三窗保存SMA、VM、2h账本的分币gross、实际持有时长与权重、被动超cap时段、成本和terminal桥。检验SMA正收益是否主要来自更集中/更长BTC beta与漂移，从该证据决定风险控制或signal方向；只新归因、不新账户/旧QA/挑月/择赢家组合或参数搜索。尚未读取本项数组/实现归因，运行前另冻结精确输入与小预算，不写大规划；D40GB/共享5GB/swap0/GPU0与locked/真钱/keys边界不变。

### D039运行前：固定保存账本的分币资金贡献与暴露归因（2026-10-03）

HEAD4bf2bc1c521835c22598482900329c96a0564d4f，D038已验收/推送/远程一致；无遗留研究任务，candidateNONE/APRNE。SMA122成本9.98而gross−521.73，547风险更高且实质terminal1662.26USDT；下一最高信息问题是按币资金贡献和实际暴露能否解释价格收益、集中风险与策略差异，从证据再决定signal或风险控制。

只取固定SMA50/200、VOL_MANAGED_BUY_AND_HOLD、公开2h Donchian三族，在原547/122/90三个独立seenSCREENING窗口保存的9账户18工件（trades/minute_nav_inventory）。每币gross=−Σ(position_delta×mid_price)+terminalmarked；net=gross−fee_USDT_mid−execution_cost，共同36bp固定分解4bp/side spread与4bp/side slip；basefee不再扣第二次。独立用cash_delta总和+terminal核net桥，复用旧accepted结算来源，不重新模拟旧交易或原QA。

暴露按完整分钟快照统一计平均/最大权重、weight>.3样本数与≥10USDT material活动样本/最长连续样本（>0含dust辅助）。这是分钟投影描述，不冒称精确事件持有时长；.3是目标，不称硬分钟cap或新增违规。终端库存保留MTM，不当已清仓/不从净利润扣其本金；贡献与暴露不足识别可交易alpha或因果beta。不挑币赢家、不筛月份、不组合NAV、不新账户/HPO、fees/杠杆/locked/真钱不变。

先固定recon/源/新薄数学/唯一合成case/协议再读真实18 arrays；一次仅1case，成熟Polars/Numpy/Decimal与原registry/resources/Progress优先复用，不建framework。主体STATE≤5MB/峰RSS≤1GB/600s、独立≤5MB，合计≤10MB，市场复制0；共享5GB/swap0/GPU0、D40GB/32预警/36停新增/1GB总临时预算保持。验收后依据全窗gross与实际暴露差异决定唯一下一研究，不以最高历史APR择参，固定SMA投资暂停与原reopen保持。

## D039 实际停止与主任务切换（2026-10-03）

V1合成新归因数学真实PASS，task fdf7588dde7a4d0d88465707511cd476／exit0、receipt803485fd1b9bd38f3e578889ffc9939c31bdea161eadf6b2e8d18cbe8db79a42；actual V1 task d53db01b68e2404088f12ce7f54eaf52／exit1、receiptf84d1699d6486c930f9db625144411078efd4b76a2c418ce34342356f3ef4964，0账本数组。metadata诊断33346464c9aa4c4497c9c22e83e872b9／exit0，仅9原summary的start_utc/end_utc共18字符串被PowerShell自动转换至+08:00，其余金融字段/目录精确相等。不是亏损归因结果，也不放宽guard；原recon/协议/源码/失败保留。用户最新多空指令切换主任务，D039实际归因暂停；reopen为今后确需分币诊断时精确复制原JSON摘要修复时区序列化，依赖未变的新数学不重复绿色测试。未运行V2草案保留，不作为已完成能力。

## D040 运行前：最小线性永续多空链路与方向对照（2026-10-03）

HEAD4bf2bc1；D039失败已终止，无后台研究在跑。用户新指令生效：Spot clip/库存保护是真实产品限制，旧SMA明确为long-only适配；carry短腿不是通用方向引擎。问题是同一固定双向SMA50/200信号在同一USDT永续价格/资金费/费用/完整资本/绝对风险下，做空有无净增量。主任务为新产品最小会计与真正负目标成交，不改变Spot/旧carry或冻结证据；公共MIT hook与已有金融语义优先复用，禁止再造平台。

默认10k共享钱包、逐仓单向1倍、每币绝对名义<=.3NAV/全部腿gross<=.6NAV，无自动补margin；BybitVIP0永续taker5.5bp/side，执行代理固定4bp halfspread+4bp slip/side及明确成本压力，不把Spot费用换算成合约回测。新手算/独立账本先核signed持仓、现金/抵押、cost basis、反手两腿、部分成交/reduce-only、资金费符号/归属和保证金/跳空halt；风险降仓优先持有约束。缺原生历史MMR/filters只能条件筛选，不认证安全清算或可执行APR。

先核已有完整未封存合约来源，固定已见122日及90日可行性，不挑跌日。缺trade-price/资金费单位或事件覆盖时，先最薄官方来源补足，不拿mark/index假装成交或unknown funding补零。四方向账户独立不拼NAV；信号不用未来最终rate、因果可得时间和旧locked边界不变。first capability新代码/合成/独立工件工作预算<=20MB；既有来源metadata仅读、后续增量行情最多2GB且联合<32GB含1GBtemp预留；共享RAM5GB/swap0/GPU0。数据输入不满足则保留能力和明确缺口，不制造经济PASS。完成有意义版本后依据净贡献/风险/成本瓶颈自主选择下一项。

### D040 条件方向对照运行前补充（2026-10-03）

官方USD-M trade source42档已真实closed0，新56,817,312B，仅读原mark/index/funding接线metadata；新source独立待闭合。账户恢复request/实际legs绑定的静态blocker修正后，唯一账户10项手算真实通过；没有把旧测试当新入口。仍没有原始funding CSV单位到官方API字段的认证桥，不能形成无条件经济主结论。

因此固定条件敏感性，而非unknown补零：同一真实有符号funding事件分别按原值是fraction（scale1）及原值是percent（scale.01），两者全部完整保留，不根据胜负挑单位。两个独立已见122/90窗口，各四方向、两成本、两单位共32名义case；每窗完整10k共享BTC/ETH钱包，账户间不共享或拼接资本。base往返27bp，压力仅spread/slippage各翻倍，费用仍5.5bp/side，往返43bp。先固定所有选择再读新经济数组，零HPO/fit；单位/原生场所输入未证时，只采用有限条件方向诊断能力，APR与投资候选仍NE/NONE。

原SMA50/200双向hook复用，统一daily/past30 signed covariance/.10年度vol目标；目标乘一致.99保守buffer以满足成交后NAV绝对.3/.6，不调高风险或容差。trade.open为明确K线成交代理，下一分钟+1us、前一完整分钟quote_volume*.001容量、最多5分钟、减仓先于增仓；风险漂移优先于alpha持有。首settlement缺过去mark但fresh-flat真实零持仓事件保留原time/rate/quantity0及不适用原因，其他owned事件缺价格硬失败，不伪造mark/资金费。所有清算/破产假设触发即停止并保留，不在其后拼现金或删除日期；终端不免费清仓，残仓仅MTM。

经济与独立工作目录合计预期<=250MB、硬400MB，单任务RSS<=1.5GB，共享5GB/swap0/GPU0；不重新下载或重复旧QA。验收关注short真实净增量、long/short贡献、费用/funding、gross/net暴露、保证金占用、实现vol/分钟MDD/收益集中度及窗口/成本/单位一致性。相同caps不当相同实际风险；有限已见筛选不声称unseen/稳定APR或原生Bybit回测。

### D040 实际结果与数值正确性修复前（2026-10-03）

原32选择器actual ffc696e06eb249d893552aad42e9a8d6真exit0，报告c643c6ae5542dc049595a8c2e21b7281ef5ce46ac7f026a3c845126f05bfb445；独立030a2b570edb40eb98a1b1ea56bdac70真exit0，报告876fce2558757f797e1d0f9d5b923c5858427ecfd721926afe4926355ffef53d。30全窗、2误停前缀严格区分。122日base/rawfraction：long−331.535281、short+91.674267、LS−302.486646；LS增量29.048635=短腿42.323889+多腿改变−13.275254。90日base/rawfraction短/LS+641.540294、long/cash0，实现vol12.157697%高于10%事前目标。单位、原生MMR/成交未认证；相同caps非相同实现风险，不选胜单位、不拼NAV、不称稳定APR/投资资格。

两90日BASE27/rawpercent SHORT_ONLY/LS在末5分钟中 false BANKRUPT_HALT：仍NAV10624.590897、free9639.837525、ETH equity984.753372>MM2.917803，但exact unpaid liability=1.000E−37。独立Decimal50债0，而producer40精度full-close的 margin×qty/abs(q) 数学恒等链有舍入，暂负margin传入_debit min并造债。先修 correctness blocker，非放宽风险规则；原source2bae/报告/2prefix/独立审核原字节保留。

下一唯一本轮工作：完整平仓直接释放原保证金的数学恒等值，_debit防止负抵押物被当债务抵扣；不引入epsilon/债豁免。只新增可重现旧失败+手算partial/full/debit真实不足的必要case，然后原547 controller函数不改，由薄wrapper新跑同90日BASE27/rawpercent两受影响账户，再独立逐腿/全部129600分钟和原停止前prefix。其余30金融/旧QA/绿测不重跑，参数/日期/成本/资金费单位/风险/信号不改。新市场STATE≤60MB/RSS≤1.5GB/1200s；新独立≤5MB/RSS≤1.5GB/1200s；共享5GB/GPU0/swap0/锁/资金权限保持。复测后决定保留双向能力，固定SMA是否投资采用仍取决于跨窗净结果和独立证据。
### D040 结果决策：采用有符号能力，暂停固定SMA投资采用（2026-10-03）

原actual32/独立32、数学恒等修复新1case、新2完整90日实际/独立、来源与10roles薄根验收已真closed0。原30全窗+新2全窗是独立证据引用，原2 false-halt前缀保留不覆盖；无NAV拼接/旧30金融重放。新source cf47ae9b889eab4506be2b22929322976a6833235eaab6459399bdec53de2261只改_debit/_leg，旧2bae原额archive；不用epsilon/提高精度/债务豁免，真实微债和资金费不足仍HALT。唯一新case dcd321c3/session99073/chunkf386b9，修复新actual4a9dbcef/session5906/chunkda7439，独立0132514a/session13722/chunk675328，根5b6fa633/session78036/chunkec583c都实际exit0。新两独立prefix129legs/540funding/180targets/129595分钟政策/量/价/时序exact且金额误差0，全90日/129600分钟/3月flat/no-debt，各net623.779740。

投资判断不变：122日两成本/两单位LS始终负，虽比只做多改善但空头和多头路径改变须分开；90日short/LS净615.473077..641.540294主要pricePnL，不能事后择方向/单位成为主力。新90实现年vol12.164324%、allobsDD4.831646%、minute峰gross35.194046%，与10%目标/30%资产cap之间的漂移和延迟公开；不把配置cap当瞬时保证或实现风险相同。完整10k作分母，无杠杆/自动补margin提升。单位、Bybit原生price/funding/MMR/filters/可成交与未来独立证据未认证。能力采用，固定SMA投资采用/HPO暂停；reopen为新事前因果信息/机制、同产品强基准和合理实现风险下跨窗净增量，然后真正未来验证，不永久删short能力。

下一唯一主任务选择同永续产品的原公开2h Donchian LONG_ONLY强基准，复用SMA保存结果。理由：目前改善相对于负gross的弱多头基线，尚不知是否胜过已有强公开参照；直接复用已验收MIT策略比新模型/HPO信息价值更高。保持两独立窗口/完整10k/绝对.3/.6/1x、27/43bp成本、两个资金费单位条件、时钟和past-only风险。先仅补July2025 BTC/ETH官方USD-M 2h两档保证SMA200需400h同产品预热，不能用Spot/daily或截短评分；原should_short=False保持，不镜像称官方完整双向。之后新8case对原32保存摘要比较，不重跑SMA；共同风险约束但实际vol/DD/gross应另报，不能预称匹配风险。停止条件为来源/完整日历/因果/成本/资本/风险出现blocker或事前资源上限，无大型搜参/锁/真钱。该下一项尚未启动，执行窗口结束交接点是已验收cf47账户、现perp来源、原2hMIT hooks与最小July预热缺口；无虚报后台研究。
## D041 运行前：同产品公开2h参照（2026-10-03）

当前HEAD09d6a7a278710a799228148b77a9b661c4b5161a已验收多空；只保留4份post-push状态文档待下一模块入库，无遗留市场研究在跑。现在实际启动D041，三agent并行最小July暖源、原MIT hook适配与独立参考，根负责私有接线/统一新入口验收和经济对照。问题：SMA多空相对自身多头的改善，是否也超过具体公开2h Donchian同产品强参照？这不是宣称公开市场完整最强策略。

固定原should_short=False/LONG_ONLY，通道prior20+SMA200只用于entry，held仅lowerbreak exit；不镜像假冒双向。补July2025 BTC/ETH官方USD-M2h两档372根各，SMA200预热不借Spot/daily、不截评分；其余沿accepted AugFeb分钟合成2h，90日需要AugNov过去暖源，但freshflat不继承暖仓。30日协方差继续真正completed UTCdaily；同已见122/90各完整10k共享BTCETH，绝对.3/.6、单向逐仓1x/.99buffer，无自动补margin。新增8账户=2窗×27/43bp×F/P资金费单位条件，只复用保存SMA结果，旧30/修2/CASH不重放，不选择获利单位。

新wrapper仅原547 simulate私有AST四锚：signal clock2h、signal/daily-risk双输入、冻结quantity分母已闭合2hclose、诊断orderkind；原金融/容量/mark/资金费/终端/日月评价不改。成熟public.closed_hours/Polars/Numpy/Decimal/pytest复用，无下载框架/模型搜参/新dashboard。先统一2个新causal+接线合成case、July2档真实source+独立必要QA，冻结协议后才读经济数组。8账户新STATE硬200MB/RSS1.5GB/1800s，source20MB/512MB/300s，独立5MB/1.5GB/1200s；共享5GB、swap0/GPU0、D40GB/32warn/36stop+1GB临时继续。

停止条件是源/完整日历/因果/真实资本/成本/资金费归属/金融/风险或资源blocker，不为正收益调阈值/删日期。共同caps不称实现风险匹配，独立报vol/DD/gross/net/margin/收益集中度；有限两个seen窗口只筛选，funding单位/Bybit原生MMR/filters/成交和长期APR仍NE。验收后依据真正净差和实际风险决定保留主力或下步；不把实验数量作成果。
## D041 结果决策（2026-10-03）

源bca7/独立2754、新2case90c45、八金融bc89/独立bf13、根b50b全真closed0。能力采用，固定Donchian投资暂停：122日gross约90，但base fee+spread+slip约93，fund另外负；90 gross约−85，不能只归成本。两cost×两unit八净均负。完整10k各独立，122净−75.4066..−3.5811，90净−212.8846..−159.7839；旧32只引用原30+纠错新2，不重演/拼NAV。实现vol约6.1%/6.5%，gross均值约7.74%/7.72%、峰30.07%/32.99%，与SMA不同；共同caps不能消除实现风险差别。source已独立raw12/normalized16完整744行新两档，无旧42QA。独立max cash1.09e−11/ratio3.51e−14；order intent sizing scope仍pinned controller+新causal case。基金单位/原生venue/清算未证、候选NONE/APRNE；audit真实后登记明确，不伪装START。

下一唯一主任务：核现有授权USD-M输入并补上涨/震荡完整共同窗，以固定SMA方向对照+公开参照检查空头跨状态净增量。近期两个窗口short均正，但122集中November、90更高实际风险；比围绕近零毛edge调参数更能排除“跌市收益即长期alpha”错误。不将已见/相关旧Spot历史改称unseen，不换手续费假装合约，不放宽成本/caps/锁/资金资源。Donchian投资/HPO暂停，reopen为预固定机制或新共同窗经济增量＋未来验证；SMA投资/HPO暂停而方向能力/研究挑战保留，reopen跨状态/合理风险/真正未来证据。此下一项未启动；模块验收/document/blob/Git闭合后继续。
### D042 运行前：固定完整547日合约输入（2026-10-03）

当前HEAD f1fafea，D041八账户净负、SMA short近期正收益集中于下跌期，当前现金/候选NONE/长期APR NE。问题：同产品完整更长窗口是否推翻近期空头优势，而非追加模型/HPO。评分日期在新合约行情和PnL前固定2024-01-01..<2025-07-01（547日、每币787680分钟）；这个日历已有Spot参考，不标unseen，也不依据bull/bear收益挑日期。后续固定SMA四方向与原公开2h Donchian，使用同10k、1x、.3/.6绝对敞口与既有27/43bp成本/两funding单位条件，账户独立不拼NAV；本模块只解除实际合约输入阻塞，不计算收益。

新官方月档固定148：trade1m36、mark1m36、funding36、2023-06..2024-12 daily38、2023-12 2h两档；已有2025-01..06 USD-M daily12档按旧接受凭证复用，旧QA/绿测不重跑。日档从June2023起足够200完成日，2h December372根足够200根；不借Spot/mark作成交暖源。仅复用已钉官方download_file、CHECKSUM及既有转换/独立audit_one，薄orchestration，没有新依赖。先实际HEAD/CHECKSUM，sizes/rows当前未知；封存源协议后下载，再独立逐原CSV/Parquet格式、全UTC日历及跨月实际funding间隔。资金费按真实有符号事件，不猜8h/补零/选单位，单位和charge/publication仍UNCONFIRMED。

停止条件：任何缺档/限制/校验/完整月历/时间类型/来源字节/资源错误立即保留失败，不替代主机、规避限制、删日期或覆盖旧证据。新源owned≤1GB、单CSV≤128MB、RSS≤1GB、wall≤1800s；联合实际ROOT+VHD+1GB新源+1GB工作预算须≤32GB，D40GB/shared5GB/swap0/GPU0保持。独立只新148，≤5MB输出/≤1GB RSS/1200s；不发单/keys/paid/locked。达到source-only接受后下一入口是固定全547日同产品经济对照，source完成不能当净收益或投资资格。
### D042 实际来源失败后的决定（2026-10-03）

官方148对象HEAD/CHECKSUM真实完成（task8b31107bb5c847d3a2636968f9bba9d8、报告cbfde5a12c27613666ef5d45a71963000a6b0b0e5e6f3fcef6cf0227e70101bf、session47091/chunkc4cd9e/0）；compressed104,898,965B/maxZIP1,986,381B，不是格式/全月历或资金费单位接受。后续source taskc1f09725d84349068d0cfff9327c3033真实exit1（session99178/chunke73f5e），completed83/ZIP84，于BTC markPriceKlines2024-08 Missing/shifted minute守卫终止。165,967,471B原工件、失败receipt/partialPQ/原ZIP和源码c088完整保留，RSS170,442,752B/265.703s，未运行经济或宽松重试。

此结果推翻“官方对象存在即可保证547日全分钟输入完整”的假设。先独立只读该raw月档时间/CRC/缺口，随后核相同官方host的日档是否提供缺失原记录；不是根据收益选日期，不能删坏日、补零funding/returns或降低缺口守卫。恢复路线只许可真实官方记录及明确新来源凭证，若日档同缺则保留缺失并自主选择下一有限可靠对照，原547承诺不伪报完成；这是data信息完整性瓶颈，不能靠新模型解决。148全源QA/根接受和新547经济仍未执行，未运行草稿不当进展或后台任务。
### D042 根接受与研究决策（2026-10-03）

独立单月c0be5f1e真实exit0，官方日档ce6bfef6真实exit0：月44638/44640与日1438/1440同缺2024-08-12 UTC10:02、10:03，SHA/CRC正确，没有恢复记录。根ed248a0b/chunk96d769真0只接受失败诊断，source仍拒绝；原83工件/84ZIP/partialPQ保持。未运行148全QA、source根或经济；已准备但未执行code不当进展。采纳严格日历守卫和负证据，暂停完整547分钟，reopen合法真实记录或独立验证缺失风险方法。

下一主任务事前固定Jan1..<Aug1 2024（213日），依输入完整性边界决定，未看新PnL；ETH mark和14个funding月档须补和独立接受，不能先称来源完整。若后续Sep2024..<Jul2025的303日完整，另独立10k账户；August缺失和原547失败公开，不删日期拼NAV或伪造547长期记录。SMA四方向＋Donchian共同产品/资金/风险/27/43bp/两unit保持，优先排除近期short熊市依赖，零新模型/HPO。当前现金/候选NONE/长期APR NE。
## D043 — 213日共同合约对照：运行前简记

问题：近期固定SMA空头的净正结果是否依赖近期跌市？当前投资仍NONE/现金，长期APR不可评估。
对照：固定2024-01-01 UTC..<2024-08-01 UTC（213日），SMA LONG_ONLY/SHORT_ONLY/LONG_SHORT/CASH＋原公开Donchian LONG_ONLY；每账户完整10,000USDT、原1x/绝对.3/.6、过去30日有符号cov与10%年波动缩放。BASE27/STRESS43bp和RAW_AS_FRACTION/PERCENT仅条件敏感性，20选择器/16交易账户/1共享恒定现金工件，无搜索、无选后日期/阈值；Binance代理价格与BybitVIP0成本，不称原生。
指标：完整资本净PnL、已实现/mark/funding/fee/spread/slippage桥、方向贡献、换手、gross/net/保证金、实际vol/MDD、月/日收益集中度与方向净增量；完整日历/全原事件与halt前缀分开，不年化稳定APR。
输入：72官方USD-M档，显式复用D042 failed父中的51逐文件完整工件＋新21档（ETH mark7/funding14）。父83/148真实exit1、8月缺口不变，不重下载旧51；全72首次独立raw/normalized calendar核验后才经济。旧547失败与所有影响选择的尝试保留，213已见开发筛选，不叫unseen/完整547。资金费未知不能零填/漏掉负值。
预算/停止：source原1GB新工件预算/RSS1GB；源启动联合2GB容量预留（含1GB工作）。共享5GB/swap0/GPU0/D40GB、32GB预警/36GB停新增不变；HTTP/格式/时钟缺口/未知事件导致source不完整即停止经济，保留失败；新research/audit数组前另冻结≤1GB研究输出、≤3GB单进程RSS与明确wall，不放宽原金融容差。任何真实halt保留债/残仓，不补后续现金。
选择依据：213边界在新合约PnL前依据官方源完整性决定；更早的牛/横盘段能高价值否证单窗口short优势。主力保持现金，挑战者少量固定，不开新模型/HPO。所有新长期任务走实时8765。源码/小协议/验收后才正常模块提交推送。

### D043验收后的自主决定

213实际20全/独立17调用＋3恒定cash等价通过；SMA LO/LS净10.11..12.25%、SO0，Donchian6.04..8.57%，两者各4/7正月且Feb盈利集中。SMA净额更大伴更大暴露/vol/MDD，不能把原caps相同当实际风险匹配；本窗做空增量0，不永久删除做空能力，也不否定旧D040真实short。主力研究保留固定SMA，投资仍现金/NONE，长期APR NE。

下一主任务选择同USD-M固定波动管理持有强基准，复用原past30cov/账户/成本/资金费/风险层，在213/122/90独立完整窗口对保存SMA/Donchian比较；少量一个策略/4条件，无HPO或新栈。问题是是否存在受控beta之外的净增量，指标完整资本net、实际vol/MDD/暴露/成本与月集中；预算沿用1GB owned/3GB RSS/3600s/shared5GB，任何来源/因果/金融/资源错误停止保留、不填零。具体源/参数在新运行前冻结，不将本决定当已运行结果。

本版接受能力与真实配对结果，不认证稳定APR、Bybit原生、单位或投资资格；原547缺口、三metadata失败和全部负结果保留。投资/HPO reopen须强基准跨状态增量及真正未来证据；完整547 reopen须真实合法缺记录或事前独立验证方法。原20%frontier原则保留，当前低成本强基准优先避免在错误alpha假设上花训练预算。

## D044 — 同产品受控持有强基准：运行前简记

问题：D043 SMA盈利是否只是上行beta，而非优于受控市场暴露？固定一个始终多头raw(.3,.3)参考，复用原日线calendar/200已完成可用warm guard、past30 signedcov/365、.10年波动缩放和原perp完整账户/时钟/capacity/部分成交/资金费/fees/terminal。此为同风险层的恒定alpha reference，不把D034旧Spot EWMA收益改产品或声称复制原EWMA。
对照：213/122/90三个已见完整USD-M窗口，各独立10k；BASE27/STRESS43×RAW_AS_FRACTION/PERCENT，同四条件跨3日期共12新账户。只读取已接受输入，不重跑来源QA或旧金融；旧SMA四方向/现金/原Donchian用保存且已接受的canonical摘要，不拼NAV/择赢家月份。投资仍NONE/现金/APRNE，无新模型/HPO。
指标：net/gross/funding/fee/spread/slippage、完整资本收益、signed/gross/保证金、实际vol和全观察MDD、换手与月集中，以及对同产品公开参照的配对增量；共同caps不称相同实现风险，不按事后vol放大。
预算与停止：新账户owned≤1GB、RSS≤3GB、wall≤3600s，共享5GB/swap0/GPU0/D40GB；磁盘联合含1GB工作须≤32GB。唯一新目标因果/共享风险case、原数值容差、12新账户的独立金融后才比较。任何来源/时间/会计/实际资源错误保留失败并停止，真实halt仅完整实际前缀，不补后续零收益；不触及locked/keys/paid/orders。
当前AGENTS中的用户自主投资原则覆盖旧固定frontier配额与模型清单；后续按实际信息价值决定主任务，保留能力及明确reopen，不把历史20%配额当执行门槛。
### D044验收后自主判断

三窗新12HOLD／独立12原金融体、72摘要60对／根V2真实closed0。213 HOLD=原SMA LO/LS全经济及风险字段，确认该窗利润是受控beta，未显示择时增量；122 LS－HOLD仅38.98..49.18且全期仍负、更高gross/margin/turnover；90增量1268.32..1302.98，vol近同、MDD更低，说明short方向有研究价值，但两月贡献95.67%、窗口SEEN不升级长期alpha。资金现金/NONE/APR NE；固定SMA研究主力保留，HOLD成为必要强基准，Donchian仅少量挑战，不拼SO/LO窗口赢家。

比较单位桥、补更长独立窗口与模型/HPO三条路径：先核官方文档及可合法公开验证的funding archive↔历史API单位/事件身份；当前倍率100差不能凭PnL推断，真实charge mark／发布时间仍各自未知。若已有同endpoint451且无访问条件变化，不重复或替代host绕限制；保持conditional两scale，下一转预固定完整独立窗口source边界与强基准增量，而非换成本制造收益。仅必要小metadata/事件对照，预算/锁/资金边界不变；新研究前另短记范围/预算/停止条件。

真实3任务失败和1host metadata失败保留：numeric PS keys／缺STATE启动、extra-unused index role metadata、旧exact pinned模块文档路径。只新版本metadata例外和独立路径，原金融数值体/费用/风险/容差保持；旧市场/QA和新12 market未重跑。122旧LS单币mark漂移30.0664%、4减仓/最大首次延迟60.000001秒如实记录，不宣称全时绝不越限或分钟内/native安全。

投资/HPO reopen须强基准跨状态/合理风险/真正未来证据；完整547 reopen合法真实缺记录或事前验证缺失方法；新模型需已有基准之外的明确信息价值。固定frontier配额已被用户长期自主原则覆盖，按实际瓶颈自主决定，不新增大路线图。模块闭合后才普通Git提交/push，核真实远程HEAD。

### D044官方语义核查后的下一选择（未新请求／未运行303）

官方primary文档说明REST fundingTime/fundingRate与charge关联markPrice，未给archive last_funding_rate/calc_time倍率桥；FAQ当前日期和结算偏差不能追认历史。已有FUNDING_SEMANTICS_PROBE_20261003_V2.json SHA54febc06b7815e521715c8d70c3e930929a489c7e2a84d1ddae9507a03e4da4d、task94a04f7ca7a3407e9905109fea9feb4c真实451/exit1、0matched/0retry，沿D024禁绕限制；无环境变化证据，不浪费无差别API重试。单位桥暂停/reopen官方archive语义或合法原历史响应；保持两条件、不凭收益选倍率/不漏负资金费。

因此下一唯一主任务选择固定2024-09-01..<2025-07-01 303日完整独立USD-M窗口source边界，再原SMA four方向/cash与HOLD强基准。这在新PnL前确定，已见开发筛选，独立10k不补缺Aug/不拼547NAV；优先检查转折/持续增量，优于新模型HPO。精确来源清单/现有逐文件复用/预算将在新任务前短冻结，不将本选择当已运行。共享5GB/swap0/GPU0/D40GB/caps/费用/locked/资金权限保持。

### D045运行前固定：303日来源闭环

问题：原SMA短窗净增量是否能跨转折状态延续；先完成已预定2024-09-01..<2025-07-01 303日完整USD-M输入，后固定四方向/CASH与HOLD经济比较。原547缺August分钟仍FAILED，不补齐、不删该缺口日期后改称547，不消费locked；303为SEEN开发筛选、独立10k账户不拼接旧NAV。来源94：trade1m20、daily34（Feb2024..<Jul2025，213日预热+303评分）、mark1m20、fund20；原54完整producer工件中24已有独立QA，30首次QA，新增40首次QA。旧metadata148+42只凭证投影。source预算1GB新工件/RSS1GB/1800s，2GB联合容量含1GB临时；QA5MB/RSS1GB/1200s，共享5GB/swap0/GPU0。真实新扫描+2GB≤32GB、单月行历/CHECKSUM/CRC/跨月完整与真实任务closed0才接受；任何缺口/限制/预算立即停止且保存失败，无收益前日期或单位改动。经济协议仍需来源接受后另冻结，当前仅source，0模型/订单/资金权限。
### D045来源实际闭合后，运行前经济对照固定

303来源真实94完成/40下载exit0；独立70首次+24复用exit0；ROOT已closed0，INPUT8b665b28…、ROOT3df702c3…。现在固定原SMA50/200四方向+CASH与D044恒定多头HOLD，20成本/单位选择器、16真实交易账户+1恒定CASH工件/3别名，全部独立10k/1x/.3单币abs/.6组合gross/过去30日signedcov目标10%/原200闭合daily。Bybit VIP0 taker5.5bp单边，RT27/43两固定成本、F1/P.01两未认证单位条件；不基于新PnL选成本/方向/倍率，统一原账户/容量/.99sizing/资金费事件和terminal成本平仓。source-only通过不证明会计或盈利；一个新合成因果接线用例后原financial body实跑，独立原Decimal/audit_case/容差、新303日期和独立HOLD目标。预算1GB工件/RSS3GB/3600s，共享5GB/swap0/GPU0，固定全303不删亏损日；缺日/无法完成/不对账停止、保存原失败新版本修复，不伪造稳定APR。以gross/net、方向贡献、fund/fee/execution、turnover/实际risk/MDD与月集中度筛选；不同窗口账户只并列不拼接，研究采用不改变现金/NONE投资。Donchian与HPO暂停：重开需现基准以外的新信息价值；资金费单位桥reopen须合法官方语义/历史响应。
### D045实际结果后的选择：先修风险减仓正确性（2026-10-03）

303完整LO−2.20..−1.18%、SO−12.45..−11.71%、HOLD+6.55..+7.88%、CASH0；SMA单独short在这窗拖累，不能将之前90日跌市赢家拼接成主力。HOLD实际波动较高，相同caps不视为风险相同。4个LS都在95229/436320分钟以NOT_EVALUABLE_UNEXECUTABLE_RISK_REDUCTION停止，独立账本正确但全期收益NE。目标q*scale未量化，向下取整留下<1e−8尾差，pending阻止重新risk_schedule，5次仍真实超限；负债0、非清算/资金耗尽。保留原停止前缀及全部旧结果，不据缺损303报告淘汰整个多空能力。

下一唯一主任务D046 correctness blocker：仅RISK_REDUCTION在实际合法attempt时点按原方向fill价、step和10USDT最小量向减仓方向取整，clip现有abs(q)，reduce_only及原核心capacity/minnotional/fee/时序/caps不变；pending完成以向零达到原目标而非要求不可表示尾差精确相等。不放宽容差、不把真实超限当合格、不动DAILY_TARGET；无法满足真实最小量/容量仍停止。先对称手算、真实不足/未来扰动新病例，再四LS同303价格/资金费/两成本/两单位/10k复测，其他16只保存引用。预算新输出500MB/RSS3GB/3600s，若合法成交后仍停或独立不对账/资源缺口，保存失败并按机制重新判断，不改成功标准。它直接恢复可信方向增量比较，比新模型HPO信息价值高。投资现金/NONE、长期APRNE；资金费桥/Bybit原生/独立未来不足仍保留，暂停路线与reopen沿当前状态。

### D046实际闭合后的选择：固定公开Turtle兼容性，非SMA搜索

仅两私有风险AST锚：请求量按step/min10实际方向成交价向减仓方向量化、risk完成按向零达到目标；原DAILY_TARGET/TERMINAL/fee/capacity/mark/caps/时序/资金费/core源不变。首freeze f0a835c...真1/0arrays；V2保留原if/elif expiry、只表达式精确锚，solecase手算/partial/真实不足/future-prefix真PASS。四LS实际72d2真0、全部303/436320分钟/506legs；independent d537/ROOT053f真0。净−9.76..−9.32%，gross−859..−857USDT、成本约74..118；BASEF short−784.07/long−150.00，较LO−733.60中long路径+50.47，不声称纯short效应。当前正确性能力采用，SMA投资/HPO暂停，NONE/CASH/APRNE；原D045四prefix与16完整、旧窗口负结果保留，不拼曲线。

只比较两官方primary源码：同jesse-ai/example-strategies/MIT已固定7c91e0a37bf62165790120d730442e4f6eb00364的TurtleRules与DUAL_THRUST。选唯一下一主任务TurtleRules固定4h：双向20-bar突破/10退出、ATR20×2止损、最多4层0.5ATR加仓、真实fill callback。原实现没有固定周期，4h是新实验事前选择；文字S1盈利过滤没有完整落实，不误称完整经典Turtle。先小型真实entry/partial/fill-recovery/stop/pyramid与共享abs caps/完整capital兼容性，只忠实薄复用原代码；无法保留则保存scope失败/暂停，reopen明确解决回调会计语义后再开。通过后才冻结同产品/价格/cost/unit/日期/HOLD比较，禁止改成本/事后阈值/HPO；它检验更快突破与止损能否改善SMA负gross，优于堆模型。DUAL_THRUST暂缓：down_max_high实际取candles[:,4] low，需厘清高周期anchor/cache与作者语义，不自行修成想要的收益。公开策略并不证明行业最高水平。

原策略代码： https://raw.githubusercontent.com/jesse-ai/example-strategies/7c91e0a37bf62165790120d730442e4f6eb00364/TurtleRules/__init__.py 与同pin DUAL_THRUST/__init__.py，许可证同pin LICENSE；primary-source静态核查完成，当前没有Turtle市场运行或盈利证据。资金费/原生/未来证据边界及各暂停reopen保持，40GB/共享5GB/swap0/GPU0/locked/资金权限不变。

## D047 prospective：一个固定公开Turtle4h双向挑战者（未看新PnL）

问题：D046固定SMA303日负gross，公开breakout+stop+pyramid能否在同产品/资本/风险/成本下改善投资质量？选MIT TurtleRules7c91e0a37bf62165790120d730442e4f6eb00364唯一主任务；固定4h为本地事前选择，原20/10 channel含当前完成bar、ATR20/2、4层/0.5ATR、原branch/S1状态，成熟Jesse/Rust kernel复用不自写indicator。先实际order/callback/partial/恢复/stop优先兼容病例；通过才同2024-09-01..<2025-07-01独立303日四预固定费用×单位条件账户，与保存D046 SMA LS及D045 HOLD/CASH参考比较。10k共享资本、1x逐仓、abs30%/gross60%、过去30日cov10%target及.99/原成本/执行延迟/容量保持，不搜参或择优资金费倍率。

303 score官方1m来源复用；4h只取完整分钟聚合。新增少量官方USD-M4h2024-07/08两币档案仅作240过去bar预热，独立CHECKSUM/日历/格式核验；不把日线插值或Spot作perp预热、不补原547缺口、缺资料即NE。stop按已可用分钟OHLC触发，下一eligible open+1us延迟成交代理，不回填理想stop价。原单位请求与cap/vol裁剪披露，partial每逻辑ADD首正fill一次原callback、fragment只补保护量；全零拒绝恢复提交副作用并记录，stop/exit/risk取消增加风险残单，恢复完整bridge状态。市场预算≤4配置/3600s/3GB RSS/500MB owned，共享5GB/swap0/GPU0/D40GB保持；vendor≤1MB180s、预热≤20MB300s。兼容失败先最小修复/独立新版本保留失败；不能保留核心语义则暂停并列明确reopen。无资金/locked/keys/paid/native或稳定APR资格；本条是前瞻选择，尚未运行新市场。
### D047固定Turtle实际结果后的选择（2026-10-03）

四固定cost/unit新账户与独立金融已真实exit0，但只有BASE27/PERCENT完整303：净−555.346、同量gross+393.442，交易手续费386.459/点差281.061/滑点281.061/fund−.2074/turnover70.265倍；long−77.075、short−478.271，9.0195%实际vol/11.1595%分钟DD。相同条件旧SMA LS−932.355、HOLD+788.240、CASH0；Turtle少亏不是正alpha，也不是做空单独因果增量。另3停在342005/342725分钟，holdingBTC<10USDT导致5次无法risk减仓；完整收益NE，不选唯一完成的资金费解释，不以停止前缀排名。V1controller接线与saved comparison CASH可选stop_us的失败均原字节保留，后者V2仅完整known-zero CASH可None，未填市场收益。采用填充/stop/恢复能力，投资仍现金/NONE/APRNE。

下一唯一主任务选择公开Bybit产品过滤语义与最小适配，而非改Turtle参数或降成本。官方FuturesTradingRules（2026-07-03）明确平仓豁免minimum notional但仍受min qty；当前core10USDT适用于所有fills/统一1e-8qty只代理假设，实际三NE与极小持仓直接暴露场所映射瓶颈。先核BTC/ETH合法公开spec，当前snapshot只用于明示目标场所代理profile，不能追認2024历史native；文档example数值不当作live返回。公开只读probe≤两symbol/每URL一次/100KB/60s/128MB；限制即保存原失败、不换host/区域/proxy/keys。后续独立版本保持原fees/资本/caps/price source/资金费两条件与所有旧结果，通过必要手算/spot兼容后再固定经济对照。Turtle与SMA投资/HPO暂停/reopen为正确可执行过滤、完整成本压力对照及强基准之外独立增量；funding bridge仍等合法官方archive语义/原响应。研究强基准保持past-vol HOLD，真实投资CASH；没有永久删除空头或条件失败方向。
### D048 prospective：先纠正已知平仓语义，再检验经济影响

公开spec V1实际WSL NetworkUnreachable，V2复用现有正常HTTPS同api.bybit.com实际403，立即停止，BTC1请求/0 profile，未请求ETH，不换地址／区域／proxy／TLS／keys。两失败原字节、任务、响应hash保留。没有获得当前或历史Bybit quantity/价格filter认证，文档例数不当作实际参数。

官方当前平仓minimum-notional豁免足以修已知语义，而非等待认证时停止所有科研。新薄account沿原cf47全部金融／config／费用／risk／1e-8 proxy step，唯一私有execute predicate豁免实际减仓，原反手opening-leg minimum仍守卫；profile/snapshot VERSION分离，旧Spot原字节不改。先唯一新手算case（小额部分／全平、reduce-only、反手小开仓拒绝、恢复与独立钱包），通过才固定Turtle LS与HOLD两recipe各4cost/unit共8个新账户，同完整303价格／mark／资金费／10k／1x／abs.3/.6／past30cov.10／.99／延迟／容量／原成本；无新HPO，无旧QA或账户重放。比较净/gross、direction contribution、fees/fund/turnover、realizedrisk/MDD/集中度与4条件执行完整性，不能把单个有利单位拿作采用结论。预算新工件500MB/RSS3GB/3600s；缺数据、原金融不对账、无法减仓即保留NE并按机制选择下一项。currentclosingsemantics不是2024nativecert，qty/minqty1e-8未认证仍明示。

append-only experiment registry已3998265B接近原单blob4MB检查；为保留所有原记录及新attempt，新增独立Git preflight版本仅允许reports/experiment_registry.jsonl≤8MB，其他文件仍4MB，秘密／源SHA／运行目录规则保持。原preflight/source/history/diskguard不改，不删／覆写原registry；D40GB/共享5GB预算仍原硬门槛。这是可追加证据文件体积修正，不是扩大科研磁盘或权限。
D048独立V1实际19e3a3f...failed1：原financial_journals旧所有leg≥10 guard拒了合法closing，小额case未完成核算；原report2f966a.../源码/ACTUAL_BINDING保持。新独立V2只该唯一predicate允许CLOSE豁免，规范化整函数AST证明其余step/held/no-cross/capacity/时序/fee/margin/math/tols全不变，原audit_case仅之前五SMA oracle去除保持。独占V2绑定/输出，重核本轮8新账本，不重跑市场或旧测试。旧原金融assert不是新account盈利失败；尚待实际V2闭合，不追认通过。

### D048实际结果后的选择：方向消融，非参数搜索
8全303/market0、独立V2原容差全部8/true0，净Turtle−11.18..−5.55%、HOLD+6.53..+7.86%，CASH0。closing正确性修复解除原小额停机，未改变成本或制造正收益；V1 independent all-leg min10失败保留，V2唯一closing谓词。Turtle turnover68..70倍/HOLD2.2，long毛431..466而short毛−72..−64，成本压过总gross；LS方向归因不能决定long-only是否实际改善。下一唯一主任务选择同Turtle固定signal/callback的LO/SO薄mode mask（对照已存LS/HOLD/CASH），原303/caps/past-risk/full10k/fee两条件资金费保持，先唯一方向隔离/partial/callback/未来因果兼容再8新账户；预算500MB/RSS3GB/3600s，缺源/不对账/不可执行立即保留NE；结果不升级future/native/APR。真实投资CASH，研究强基准HOLD；HPO/复杂模型/资金费与nativeprofiles各reopen沿当前状态。先闭合本版ROOT/Git再消费新协议，不等待用户工单。

### D049结果、原因与用户新任务（2026-10-04）

八新LO/SO全部303日、财务和ROOT真实completed0，四成本/资金费条件完整保留：LO净−4.25..−.83%、SO−7.34..−4.70%，保存LS−11.18..−5.55%、HOLD+6.53..+7.86%。同caps不匹配实际vol/DD，LS−LO不能全部归为空头纯因果作用。12保存账本36JSON原因诊断与唯一手算病例真0：UNKNOWN0/费用与exec不重复、桥3.41e-12USDT；BASE/F LS ENTRY362.33、ADD109.44、EXIT100.21、STOP142.10、RISK228.77USDT。LO BTC净+297.66/ETH−426.30，SO两币均负。LO正gross被换手成本抵消，SO负gross另有信号问题；不因此事后删币/停止必要风控或宣称禁ADD已测试盈利。

最新用户指令将下一主任务改为可配置约10币、同一共享资本组合。先只读核来源、许可与现有资产/交易链硬编码，再预登记最薄完整组合研究；本条无已运行多币收益。总资本10k、单币abs30%/共享gross60%、逐仓1x、真实成本、D40GB/共享5GB/swap0/GPU0与locked/资金/keys/付费/限制边界保持；不将独立10k账户净值均值当组合。旧禁ADD/日线RSI2建议让位此任务，Turtle/SMA投资暂停、HOLD强基准、CASH/NONE/长期APR不可评估。

失败与维护：solecase V1缺括号/collection失败原字节保留，canonical活动测试修正并与已验V2同SHA；ROOT首次把pytest code2要求1的metadata失败保留，只精确元数据修正，未重复市场/金融/QA。原因诊断未登记事前START，完成后追记真实RESULT并标明时序，不补造科研前登记。普通源码正常维护，历史结果依Git与来源/配置/工件复现。

### D050控制组完成后的进度与下一项（2026-10-04）

正常N资产目标/账户/输出与UTC日块链路通过独立必要验收，原两币四条件30日实际完成并独立核账；净+136.30..145.74USDT，完整本金10k，实际vol7.81..7.84%/分钟DD2.01..2.02%，换手0.547倍。只是开发窗口控制，不是长期APR/独立候选。

下一项继续原事前问题：固定HOLD规则、成本/单位情景与共享风险不变，比较过去July流动性与200日资格选出的10币。880目录/279 July rank/603UNKNOWN保留，选池真实任务34b895...已closed0，SHA9b8df895...；不是全市场Top10。新September source必须先独立格式/完整性验收后进入新账户。sourceV1目录角色冲突truefailed1/仅1完成，正常修kind dirname、精确继承唯一完成档并首次独立QA；不重选币/不改费用/不重跑旧账户。

已跑控制任务/资源与失败全部纳入预算；0拟合/0参数搜索。采用N资产能力，HOLD保留研究强基准，投资CASH/NONE。十币结果未测，不能预言扩池提高收益；之后按净增量、真实risk/cost与来源限制决定保留/暂停或扩大到其他事前时间窗。

### D050真实十币配对后的决策（2026-10-04）

相同固定past30-cov HOLD、完整10k、Sep30日、BASE27/STRESS43及两个未认证资金费单位条件：两币净136.30..145.74USDT，十币282.05..290.70USDT；两池各四完整分钟账户并独立原容差核账，ten143155.../exit0、cash误差1.09e-11。毛价格增量约142.7USDT占主要改善，成本少2.2..3.5USDT而资金费略更负；非策略/方向/费用变更。十币平均gross12.68%低于两币18.16%，分钟DD约2.02%降1.43%，实际vol7.81..7.84%升8.14..8.17%，不能据共同caps叫风险完全匹配。WIF/1000PEPE约占净利45.7%，五最大正日占正日收益46.65%；不是稳定分散证明。

采用正常N资产单一共享资本、逐币规格和日块读取；保留十币HOLD研究基准与BTC/ETH/CASH对照。投资候选NONE/投资CASH/长期APR未评估，单位、历史Bybit规格与仅一月阻止晋级，不阻止预算内开发。无需增RAM：两币到十币回放23.9→69.4秒、RSS270.9→321.9MB、输出16.3→51.2MB，共享实采峰1.020GB；瓶颈为分钟账本/I/O/扫描，不是张量或内存。

少量下一路径中，选择同规模跨月份与当时可知流动性更新池：它能以较低成本检验收益集中/市场状态/持仓退出是否主导，比继续扩到几十币或模型搜索更直接。下一实验先固定月份、过去选池、风险和真实成本，保留所有失败，已见历史不改unseen；不按本月收益筛掉或保留赢家，不拼接事后赢家曲线。当前只完成本版，不虚报下一轮在后台。

暂停更大池/HPO/复杂模型，reopen为跨月份的集中度、暴露或信号缺陷证据；Turtle/SMA配方暂停采用，reopen为真实完整成本下对HOLD的跨状态净增量。原生Bybit/资金费认证待合法公开桥与历史规则明确重开，不绕403或取keys。source目录、采集时间QA与concat的真实失败均保留，正常修活动类型/目录不改变价格、金融、费用与旧证据。
独立经济复核后收窄下一首控：固定本次July池与规则、资本/成本/单位，评价紧邻完整2024年10月，保留BTC/ETH与CASH；先只改评价时间，检验前三币60..61%净贡献集中是否持续或反转。历史更新池另做配对，不同时变时间与成员后误归因。该下一轮尚未启动；本版先真实闭合/推送。
### D051事前：固定July池的October持续性对照（2026-10-04）

当前HEAD b00183d、D050两池各4组合均30日及独立/root/Git已完成；本条仅新实验预登记，不重跑旧证据。8765无活跃研究任务，共享实际RAM约806.5MB/5GB、swap0/GPU0；旧无关未提交文件保持。September net增量主要约142.7USDT价格收益，top3净贡献约60..61%，不是native/资金费认证或长期APR。

问题：同一July预选固定池、相同HOLD/full10k/abs.3/gross.6/逐仓1x/past30cov目标10%/原27与43bp两成本及F/P两未知单位，紧邻完整2024-10-01..<2024-11-01的31日是否仍改善净收益或风险，而高集中收益是否反转？保留同月BTC/ETH共享账户控制与CASH，不按September收益筛/换币/换权，无逐币拟合/新模型/参数搜索。

只正常参数化日期及既有源/验收/账本入口：官方October三角色30档中24新增、6旧BTCETH exact接受复用；旧70 FebAug daily与已接受September trade1m10档用于200连续已完成日warmup，按日因果聚合小daily，不下载新daily、不复做旧QA。0资金/密钥/交易所订单/付费/GPU/locked，沿用同源合法HTTPS，不绕限制。

预算本模块新STATE≤500MB（输入200MB、临时100MB、账本及独立小工件200MB），总盘仍40GB/32预警/36停止新增；共享5GB守卫，输入phase1800s、每池4账户1800s、独立每报告1200s，底层0拟合/0HPO。完整31日净/gross、费用/执行/funding、实际vol/DD/gross/net/margin、turnover与逐币/逐日集中为主要指标；单位与native仍条件代理。缺档/不可成交持仓/不对账/预算即保留NE，不零填或改窗。两个月独立满资金账户分开报告，不拼接成61日连续NAV或稳定APR。

采用条件是最小日期能力正确+可信31日配对及能改变下一选择的机制证据，不要求正收益。若新月净增量逆转，按集中度/暴露/成本机制判断，保留能力而不机械扩币/搜参；普通下一选择自主，不以固定模型roadmap替代结论。

### D051原始10月末持仓与分类修正（不改费用/成交政策）

新两币与十币四账户均实际跑满31日；保存比较5ec7cf...真实exit1，因为十币1000SATS末5次真实0.1%前分钟quote容量减仓后余约8.65..8.79USDT，四账户terminal_cash_realized=false。原producer COMPLETE仅按分钟数判断；不追认现金完成或原事前无法退出停止条件。账本已含末未实现约−1.93..−1.96USDT，原数据、account数学、容量/五次policy/成本不改，不删库存/免费平仓/延长attempt。

本轮收窄为完整31日marked-NAV经济诊断，liquidated return维持NOT_EVALUABLE，先按原独立参考核钱包、数量、保证金、未实现和NAV，再修活动完成分类与保存分币归因的未实现项。只必要手算残仓病例及新保存比较，不重跑价格或旧QA。原四源/账本和failed comparison任务/旧源码保持，scope修正独立报告MULTI_ASSET_OCTOBER_TERMINAL_SCOPE_CORRECTION_20261004_V1.json；不能据marked结果晋级投资。下一是否修改未来退出policy须是新事前实验，不把原退出失败包装为通过。

### D051实际配对后自主选择

两币四31日cash完整及十币四31日marked各原容差独立exit0，ten fef347aa...误差1.46e−11/4.99e−14，0清仓完成；唯一残仓手算255cdcf3...与保存配对200b6f10...真0。十币marked0.64..13.85USDT、两币95.31..118.47，相同条件净少94.66..104.62。gross少108.36..108.53主导，成本反少3.83..6.10，fund负担反少0.076..7.607；不是降低费用就能挽回。ten实际vol10.46..10.48%略低，但DD2.93..2.94%高于两币2.44..2.47%，共同caps不等于风险匹配。

BASE/F前月前三WIF/PEPE/ORDI173.23净贡献在本月同三币为−25.25；DOGE50.34被SATS−31.46/XRP−26.53/PEPE−15.47抵消。采用N资产能力与marked/现金分类，BTCETH HOLD稳定控制、固定十币挑战者但暂停晋级，投资CASH/NONE/APRNE。原排序metadata失败保存，V2只source catalog unique+同集合，账户/spec/rank有序守卫及金融/tols不动；失败前仅创建时间网格，0行情数组/0金融调用。

少量可行路径中选下一唯一主任务：同一池、过去30日逆波动定权vs原等权，保持同两个完整开发月份/资本/caps/过去协方差vol目标/两成本两单位，0模型/HPO。不按本月亏损删币，不事后缩放，不同时更新池/日期/执行政策。它以已有日线与风险输入区分配置风险与资产池规模，比继续扩币或搜模型信息价值高。未来退出能力和单位/原生认证分别保留独立边界；不将本版末仓强平收益补造。这项下一实验尚未启动；预算将在运行前简记，当前模块先Git闭合。固定十币投资reopen为跨月份净收益/实际risk/cost与可靠退出增量；更大池/模型reopen为该配置对照暴露明确剩余机制，能力不删除。

### D052事前：只改变过去风险分配，保留完整经济口径

当前HEAD/remote abc901fcaa785d26172a0065915af7f64d312216，D051本地/远端核验已闭合；本轮重新核HEAD/WIP、8765无active研究、原collector540仍存活。前轮属实际进展（8新31日账本与独立复核、marked配对、必要修正及推送），不是仅计划；全部旧无关WIP保持，未启封/发单/GPU。

问题：固定July10池在9月有效、10月gross与集中逆转，按过去30日波动率分配风险能否在同两个开发月份提高净几何收益或降低实际DD，相对于等权与BTCETH/HOLD/CASH？唯一改变raw allocation，使用共享normal target接口+NumPy std(ddof1)，raw=.6*(1/σ)/Σ(1/σ)、逐币clip.3且不把被clip预算再分配，再原过去30 signed-cov10%scaleonlydown；非ERC、收益优化、alpha或事后风险缩放。默认equal保留原语义，新strategy身份单列。当前成员缺200连续完成日或σ异常，inverse整组合flat并标UNKNOWN原因，不补收益或提高其他预算；真实退出和持仓缺口守卫保持。

数据：只既有accepted Sep30D与Oct31D同July10池、同200暖启/UTC日块成交/mark与实际资金费；不新下载或重复格式QA。两个月各4原成本27/43bp与F/P未知单位，共8个新的共享10k账户；原等权及两币保存账本只比较，不重算。绝对单币.3/共享gross.6/逐仓1x/no topup、分钟延迟/0.1%前分钟容量/5次退出不改，marked与liquidated scope分别报告。各月独立完整10k，不拼为连续61日NAV；已见开发数据不改unseen。

预算：新STATE合计≤300MB（两market各≤100MB、独立各≤5MB、必要case/小证据≤20MB，余量计临时与失败），每market≤1800s/RSS≤3GB、每独立≤1200s/RSS≤1GB；共享守卫仍实际5GB/swap0/GPU0、D盘40GB/32预警/36停止新增，0模型/0HPO/仅1 allocation recipe，底层8账户和全部必要修复均算本轮。先1新独立手算/顺序/因果/异常病例；真通过后冻结各月新协议执行。主指标完整资本net/gross/cost/funding、实际vol/DD/gross/net/margin/turnover、资产/日期集中与退出完整性。缺数据/不对账/风险或资源守卫即保留失败/NE，不降成本/调阈值/延长原退出policy。

采用需两个已见开发月份的可信机制与经济对照，不要求每月盈利或以测试数代替投资质量；明显净劣势或换手成本抵消即保留原控制/暂停此配方，风险改善但收益不增只作取舍，不宣布更高长期APR。无独立未来/原生证据仍阻止资格。实验结束依据实际结果再选下一任务，不扩大搜索预算。

D052入口尝试记录：唯一synthetic首e92b106...真实exit1/collection0，是RULES字典语法；原源/测试/任务与报告保持。normal仅改dict语法并按原.6/3浮点恒等核默认值，V2 d94a...真实exit0/1病例，手算1e−13和金融1e−7/1e−10未放宽。根元数据冻结助手首调用因预期synthetic状态标签少`_NOT_MARKET_RESULT`拒绝，0新协议/0行情/0账户；改为实际已接受状态后才写两份新协议（14ecb5.../28f414...）。没有重做旧QA、green病例或原账户。

### D052实际之后：定权不是当前主要收益瓶颈

8新共享账户及8独立金融真closed0，全部按原五次容量退出清仓。9月inverse净281.54..291.17、较equal−0.506..+0.475，gross+约1.42被成本/资金费抵消，DD约1.43→1.55%；10月inverse净22.09..37.72、较旧完整marked净+21.44..23.87，gross+约25主导、成本与资金费反更高，DD2.93..2.94→2.915..2.923%，平均gross反14.20→16.58%。收益增加不等于同实际风险或永久分散改善；旧末残仓NE保持，两个独立月不拼NAV。独立maxcash1.10e−11/ratio5.07e−14，原容差；新主体输出103.481MB/RSS≤322.10MB/共享实采≤1.246GB，0旧QA/账户重算/新数据/模型/HPO。

采用N资产能力和normal可选inverse API，保留两个挑战者，inverse不升级主力/投资。当前稳定控制BTCETH HOLD，投资NONE/CASH，证据仅已见开发筛选+独立账本（不是独立市场优势）。Sep净微小且压力差/回撤大，Oct改善仍显著弱于两币；XRP过去低vol加权后负贡献变大表明仅风险大小不能解决收益方向。费用不是主要补救空间；不按此结果删币或放大风险。

少量下一路线：继续定权/扩池缺跨月净增量证据，搜模型暂缺具体信息假设；选择复用已登记固定公开日线趋势规则的同池多头/空仓vsHOLD，保持池/资本/成本/风险和完整开发窗，以小改动检验是否能避免负价格暴露，不强迫空头。下轮运行前再记有限预算与固定规则，不另写大规划或启动治理平台。暂停inverse晋级/更多参数及扩池，reopen为更多事前固定窗口的净/实际风险/成本与容量增量；ML reopen为该信号对照明确尚缺的预测信息，双向能力一直保留。未来独立验证与官方历史单位/native规则分别限制声明，不冻结无关开发。本版按真实验收修文档后正常提交/push，下一趋势尚未后台执行。

### D053事前：同币池固定公开趋势是否改善价格损益

上一轮为实际进展：8新账户/8独立金融/两保存对照及normal定权接入已完成并推送/核远端0a61e25。重新核当前HEAD、无tracked差异/保留旧untracked、8765无活动研究、collector540存活；不重复旧修复/QA/账本。投资NONE/CASH，BTCETH HOLD保持稳定控制，不按月份择赢家。

唯一问题：在同July10池上，固定已登记MIT Jesse SMA50/200日线原long entry/exit hook所形成的多头/空仓信号，能否避开负价格暴露、改善完整资本净收益或DD，相对等权constant-long HOLD？旧两币SMA负结果保持；新币池的方向状态是新机制对照，不以教学策略代表全部公开策略水平，也不将结果要求改为正收益。与继续定权/扩大池/盲搜模型相比，此对照直接检验当前gross瓶颈。

唯一改变方向信号：等权raw .6/N配置成员、未active预算不重分配、过去30完成日signed cov×365/.10只缩小、abs.3/gross.6/逐仓1x/10k、费用/资金费两条件/分钟延迟和quote容量/五次退出均保持。固定50/200、200连续完成日预热、>入多/<平多/=保持，退出当日不重入，下一日可重新入场；原hook不改，原wholebalance/Jesse执行未移植，新ID明确COIN adapter。双向能力保留，本轮不强制空头。

只读取原accepted Sep30日/Oct31日相同manifest、信号日线与分钟/mark/funding日块，共8新共享账户/8独立核账；原等权/两币/inverse保存结果仅作参考，不重跑。两月分别fresh flat/完整10k，已见开发筛选不改unseen、不拼NAV；缺数据/不可成交风险退出/破产/预算失败保留prefix/NE，不补零/降费用/放宽caps。原marked与cash范围分别报告。

预算新STATE≤300MB（两market各100MB/1800s/RSS3GB，两独立各5MB/1200s/RSS1GB，唯一必要手算/因果/顺序case≤20MB，余量含失败/临时），共享实际5GB/swap0/GPU0、D40GB/32预警/36停止新增不变；0下载/模型/HPO，1固定signal recipe。先验收一个新薄adapter入口病例再冻两个协议；normal共享目标、账户、engine和来源不重建，独立参考只新增signal状态算术。

主要指标完整资本net/gross/fee+execution/funding、实际vol/DD/gross/net/margin/turnover/持仓覆盖与分币/日期集中。若方向屏蔽减少亏损但损失主要上涨或成本吞噬gross即保留HOLD并暂停此配方，不调50/200找赢家；若同两开发月有真实机制增量仍只研究保留，独立未来/native/单位认证另限投资。结束按证据选下一项，不无限换示例/搜参。

### D053实际决定：固定SMA方向未修复毛收益

8新账户/8独立资金calls和2保存配对真closed0，原对照/QA未重跑。9月SMA已清仓net−74.07..−67.41 vsHOLD+282.05..290.70USDT；10月SMA marked−246.44..−233.61 vsHOLD+0.64..13.85。gross差约−356.9/−245.9，额外成本1.14..1.81/1.53..2.44，资金费反改善；主要瓶颈是固定趋势状态的价格选择，非费用。实际vol更低、DD更高，同caps不等同风险；原规则十月XRP/SATS约309USDT末持仓/约−60未实现完整计NAV，现金清仓收益NE。两月独立账户不拼长APR。独立scalar SMA状态300/310与目标、钱包/marked账户核对，金额7.28e−12/ratio8.58e−14原容差；完整订单意图/原生/资金费单位未认证。另一agent只读小结果复核机制，不新增数组或拟合。

采用N资产与公开hook能力，固定50/200配方及调参暂停；BTCETH HOLD稳定控制，equal/inverse10保持研究参照，投资NONE/CASH。不能永久否定趋势能力或事后删亏损币。首选下一固定November完整月、同July池的三既有HOLD配置（BTCETH/equal10/inverse10）同四条件真实净/风险/容量对照，预期信息是现有主力跨状态是否成立及是否可实际退出；少量扩池/新信号/ML路径先不搜，因为两个开发月不足长期采用且现有退出有实质缺口。规则和日期事前固定，不按月赢家切换、不拼独立账户，不调原SMA。下一任务尚未启动，后续运行前只追加具体输入/实际预算/停止条件，不新平台。

Reopen：SMA需新事前机制或独立跨状态净增量；inverse/扩池需更多固定窗净/风险/成本/退出增量；ML需明确剩余信息假设。样本/Bybit原生/资金费单位限制声明，不冻结无关开发。进度writer tempfile争抢已正常最小修复、唯一case真0；root磁盘进度metadata外层漏写KeyError保留并正确恢复，API实测无错、无服务重启/行情重跑。主体合计34.865MB/RSS319.66MB/共享实采1.281GB，资源未扩大，原扫描时刻保留。模块验收修现有文档后正常commit/push，仅后验凭证证明同步。
D053 Git元数据首次导出原生host e5ca0a/exit1：PS参数拼接导致Git cat-file多一个参数，发生于source binding/暂存之前；已复制的真实任务原字节保留，失败helper/凭证独立保留，仅修显式参数并复用逐字节一致metadata，不重市场/金融或放宽容差。

### D054事前：固定November跨月份检验既有HOLD配置

D053实际完成并推送/远端核354967542958004c59a7f8e4b3d2fececf036b63，上一turn属于progress。重新读取HEAD/WIP/API与运行任务，tracked clean、旧37untracked完整保留、8765健康且无活动研究、collector540 live；不重原SMA失败、旧QA或账户。投资NONE/CASH，BTCETH HOLD稳定控制，equal10/inverse10为挑战者。SMA两月gross弱且风险/容量未改善后不救活配方，不按月底赢家切换。

唯一问题：既有三配方在固定连续下一2024-11-01至12-01前30日、原July池/完整10k/同abs.3-gross.6-逐仓1x/费用/资金费情景/分钟容量退出下，净收益与实际风险/清仓性是否延续？选11月依据连续日历，不依据收益；0新模型/信号/HPO/币池/风险额度变更。控制BTCETH HOLD、equal10、inverse10每个四条件共12新shared账户及12独立金融调用；用一个相同已接受十币来源manifest取控制子集，避免并列source路径差异。三账户独立起始完整10k，不叠加满资金资本或拼90日伪NAV；已見历史开发筛选不改unseen/APR。CASH保持，各旧月保存结果只引用。

来源最短增量：原官方USD-M Nov trade1m/mark1m/funding30个档，6BTCETH已有303D接受元数据复用，24新档只一次新格式/CRC/CSV检查。原FebAug70daily与已接受Sep/Oct20trade构成完整90暖源，不新下载daily或高频tick/LOB；暖源只metadata/sha复用，不再次rows/CRC，不能把8月跳到11月。July原9b8池/603UNKNOWN/10ordered身份不变，传输仅原默认Windows同official主机/URL/CHECKSUM，无新代理/重试/规避。

预算本模块新STATE总≤1GB，source≤300MB（input200MB+raw/temp100MB）/1800s/RSS1GB、首次QA≤10MB/1800s/RSS1GB、3main各100MB/1800s/RSS3GB、3financial各5MB/1200s/RSS1GB，余量含必要失败/temp。source24×zip≤16MB不是要求全上限同时驻盘，守卫实际≤300MB；预计联合D约24.8GB低32warn，保留36stop/40hard与shared实限4,999,999,488B/swap0/GPU0。所有Python通过WSL progress-wrapper，重工作串行或在实测守卫下有限并行，不改observer/已有collector。无keys/orders/locked/paid。正常source calendar/reader与独立入口有限加Nov，不复制整套版本或新平台；依赖未变不重旧green，必要输入正确性由首次新QA和独立targets/账本验证。

指标fullcapital净/gross/fee+spread/slip/fund、实际vol/minuteDD、mean/max净/gross/保证金、turnover/资产日期集中、实际末数量与marked未实现，cash收益单独。无法完整行情/mark/资金费或退出/破产/预算则原prefix/NE保留，不删除日期、补零、放宽成本/caps/退出尝试制造通过。清仓不合格只阻止依赖清仓/投资结论，不抹去marked研究。

停止条件完成固定12accounts/12finance及必要保存配对或实际correctness/budget blocker，不追加参数/币池变体。若三窗增量不稳则保留稳定控制/暂停扩池晋级；若Nov改善仍限开发机制并要求原生/单位与独立样本，不因单月上涨采用投资。若主要风险是容量退出，下一再预登记过去可知容量限仓/退出政策对照，不能事后修本轮收益；若是signal则提出明确新信息问题后才引新策略/ML。本版结束再自主选择，而非无限例程轮转。
### D054实际决定：扩池有条件增量，先核连续资本路径

原fixed July池、Nov完整30日、共同accepted manifest77881/QA877a，12新shared10k账户+12新独立金融及两保存配对真实closed0，全部按原五次容量退出清仓。两币net678.34..709.67USDT、equal10 739.46..763.02、inverse10 829.25..855.99；最大金额1.46e−11/ratio9.24e−14原tols，inverse微小unpaid1e−48原始保留，不改为精确0。原Sep/Oct、SMA失败与末仓NE未重算/覆写；新24首次源QA、6旧/90暖meta复用，0模型/HPO/旧账户或QA重放。QA首次startup98e4/host33711 true1发生于run/registry/arrays之前，仅旧小源路径前缀拒tools sampler；原源9fe818/proto8c7386/任务/失败保持。Normal唯一公开已pin路径适配后V2首次新QA true0，原CSV/CRC/math不动；后通过原append_event追加真实POST_RESULT，不伪造START。Pool比较还核真实成员set不同，源/数学不改。

钱的增量：扩池net+53.35..61.12，gross+约50.7、成本少2.67..4.26、fund少0.061..6.068；实际vol较低但DD更大。inverse net+89.79..92.97主要gross+约94.3，成本/fund反更多，平均gross11.85→13.60%、vol10.94→11.09%、DD只微降；不能以相同caps声称实际risk匹配。BASE/F XRP净166.25→238.84主要解释本月配置增量；不按结果换币/单位。另一agent小JSON复核八delta桥≤9.95e−14，无额外市场调用。完整30日正净收益是开发筛选与代理条件，不是未来优势/长期APR或真钱资格。

采用N资产共同source/资金/正常账户与可选配置能力；BTCETH HOLD稳定控制，equal10基准、inverse10优先挑战者，投资NONE/CASH。9月改善、10月落后、11月再改善，不追扩币数/均线参数/新模型。主体RSS321.47MB/共享实采1.449GB/输出120.270MB；source+QA+主体约171MB，RAM非瓶颈，时间主要原磁盘守卫及分钟账本。最新actual scan23,943,243,063B@2026-10-03T23:12:44.803992Z先于inverse输出/后续metadata/Git，正确ledger已原UTC发布8765，API无错；collector540保留。shared实限5GB/swap0/GPU0/D40及无keys/orders/locked边界保持。

下一唯一主任务：已接受9–11月91日真正连续一个wallet/每recipe完整10k、原三recipe四条件，只初始一次fresh flat，跨Oct/Nov不全平/清库存entry/margin/freewallet/funding计数，仅最终原5次有容量退出。月表只从连续账本分段，不能拼三个fresh NAV；与旧独立月的差异包含复利资本/连续仓位/边界funding和成本，非纯成本消融。信息价值高于第4fresh月/扩池/搜模型，因为当前最大证据缺口是持续资本与风险/容量路径，且复用已合法接受源无新下载。尚未启动，新运行前短记有限预算，不新增平台。

暂停扩池/投资晋级，reopen为连续路径净/实际risk/可退出增量；inverse不按Nov赢家直接晋级。SMA/ML能力保留，reopen须明确信息/机制假设和有限对照，不要求在研究之前先证明强alpha。Bybit原生/单位/独立未来样本限制声明，不冻结无关研发。本模块通过实际验收修现有文档后正常Git闭合，推送只据独立后验凭证。

### D055事前：三个月真正连续资本路径

重新核HEAD90c60204ad9fcd86a3e90c8d318bda8cad7eb0c1/工作区/8765实际任务；tracked clean、37旧untracked保留、collector540 live、0活动研究。D054完成实际12账户/12核账与远端同步，上一turn为progress，不重算既有月度账户或源QA。当前投资NONE/CASH，BTCETH HOLD控制、equal10基准、inverse10挑战者。

本轮唯一问题：在已接受Sep1至Dec1前91个真实UTC日，同一钱包跨月保留仓位/成本基础/保证金/现金/资金费归属后，三固定配方的净收益、实际风险和容量退出是否支持继续保留扩池/配置方向？三配方×四原成本/资金费情景共12新账户及12独立金融核账；一次初始化10k、一次simulate、只Nov最终原5次有容量退出，Oct1/Nov1真实持仓的事件资金费不得按fresh-flat排除。0下载/新QA/模型/训练/HPO/币池/信号/费用/风险额度改变；原July选择与70暖daily、90评分trade/mark/funding来自三个已接受manifest，metadata组合不自授新格式认证。

新STATE总≤1GB；两币主体≤100MB、十币主体各≤250MB，各wall1800秒/RSS3GB；三个独立checker各≤100KB/wall1800秒/RSS1.5GB，合成验证/temp与meta占余量。共享5GB/swap0/GPU0与D40/32warn/36stop继续，预计D约24.7GB；所有长Python用原WSL progress wrapper，主体串行，不先要求资源增加。资料角色为已见开发筛选，91真实日不能以12调用变成1092独立日期，不能按case挑单位/方向/成本。

指标完整资本净/gross/手续费/执行成本/资金费、逐月连续NAV贡献、逐币/方向、实际日波动/minuteDD、平均峰值net/gross/保证金、换手与集中度、末仓/未实现/可清仓性、边界资金费与真实资源。停止在12账户/12核账和两保存配对或实际缺失/破产/风险/容量/预算错误；原失败/停机/残仓完整保存，不放宽五次退出、补零或删日期。与旧独立月的差异含资本路径、持仓延续、边界资金费与成本，不能归为纯成本消融，也不拼接旧NAV。完成后依据连续结果决定保留/暂停；原生Bybit、资金费单位与独立证据仍限制投资声明。

### D055实际决定：连续钱包验证完成，先增加跨状态证据，不增加币数

三原配方×四条件在Sep1→Dec1前91个UTC日一次钱包初始化/一次simulate/仅最终原5次退出，12新账户/12新独立金融与两保存配对实际closed0。两币net953.42..1013.61、equal10 1059.77..1103.50、inverse10 1178.02..1227.60USDT；全部真实末quantity/notional/unreal0，原1e−47/1e−48债尾差保留，F/P单位两情景不选择。Oct1/Nov1逐币q与前月endpoint一致，所有原边界coupon owned、strictpastmark；月表按close−1us端点标签，不冒充UTC事件月汇总。1092case-days≠1092真实独立日期。

最大cash2.55e−11/ratio3.11e−14原tols；独立核记录成交/金融与有序目标，完整frozen sizing未全市场独立重建。两个必要小病例真0：同engine跨月前mark/未来扰动与独立手钱包拒reset/漏coupon。首case只因自有temp父目录缺失fixture前true1，未变case只修启动后真0；首金融候选339行与冻结池70warm身份不匹配在市场数组/金融调用前true1，原源210975/报告1d676/planf5c5/task189保持。正常仅daily候选一行按frozen symbols筛选，当前db1332与原financial/target/HandLedger/tolsbody相同，V2计划原pre210+修正db13调用前绑定；三marketprotocol/source/账本不改、不重跑。根首次copy后的byte-proof因错误旧行literal断言true1，0金融/market，后正确exactliteral证明才继续绑定，不隐藏失败。

扩池净+89.89..106.34，BASE/F毛+86.4087/成本省3.9896/fund省13.4517，日波动10.538→9.961%但minuteDD3.071→3.495%；inverse再净+118.26..124.10，BASE/F毛+126.4916/成本反+2.2804/fund反−4.4724，平均gross12.93→14.90%、日波动9.961→10.054%、DD3.495→3.503%。因此不是相同实际风险胜者或低费率制造改善。八摘要delta桥≤2.56e−13，逐币归因来自同一wallet；約72%..73%净利来自Nov，选择的主要瓶颈是独立/跨市场状态证据，非交易成本、算力或缺币数。

采用N资产/共享资本/连续钱包能力，BTCETH HOLD稳定控制，equal10透明基准、inverse10优先挑战者，投资NONE/CASH/APR未建立。不按新胜者改池/阈值/模型。下一唯一研究选择：同原July十池与三固定配置在下个完整2024-12-01至2025-03-01前连续季度检验净/风险/可退出增量，先核合法已有源/补必要trade1m+mark1m+funding，按日块，无tick/LOB/逐币训练。选连续日历不是收益，已看过范围仍development，不拼两季度独立钱包；新任务尚未启动，运行前另记总预算/必要QA和停止条件。信息价值高于扩币/搜参，若增量不延续保留能力而暂停配置晋级，若延续仍须单位/native与真正独立样本才能晋级。

暂停更多币与参数/模型搜索，reopen须已存在对照发现明确覆盖/信息机制瓶颈且有限对照；SMA本50/200配方暂停、能力保留，reopen具体新signal而非救活旧配方。INV/扩池投资晋级reopen须更长跨状态净/实际risk/容量证据、场所/单位语义与独立验证，不因本轮正净利放权。官方低成本≤4页探测确认−q×mark×rate/支付方向，未确认public-data last_funding_rate archive单位及2024publication；原API451/matched0和F/P UNKNOWN不改，不按利润选单位。

来源847d composite仅meta组合既有三accepted/160身份，0下载/新格式QA/旧金融重放/模型/安装。主体RSS≤442.81MB、共享实采2.048GB、输出357.152MB；financialRSS≤585.74MB/共21.900KB，1GB新STATE边界保持；分钟账本时间/输出是真瓶颈，无需增加RAM。最新actual pre-inverse scan24,214,764,427B@2026-10-04T00:28:22.126279Z未含随后输出/metadata/Git，8765已发布准确ledger和原时间；collector540不中止，shared5GB/swap0/GPU0/D40与0keys/orders/locked/paid保持。正常模块小metadata/源码字节与敏感门槛后提交推送，实际远端一致仅由后验凭证确认。

### D056事前：固定池的后续完整季度，检验十一月依赖

本turn核HEAD1f40239706162eb92daa8a1e2fa0abb9b59299ed、tracked clean/39untracked（36旧WIP+3真实后验凭证）、8765健康/0running研究，collector540 PID实活约42h。上一goal turn为progress：D055实际12连续账户/12独立金融/八保存配对/必要失败保持、文档和67路径模块正常推送核远端一致，不重旧市场/QA。D055后验V1原task_id nullable元数据保留，V2仅按已核同closed文件id字段修正，观察的远端/金融不变；最终原guard实际扫描24,384,593,509B@2026-10-04T01:03:44.459589Z/期间ROOT+整个WSLVHD增371,315,040B（含collector/Git，不能全归本实验），后验小凭证本模块入库。

本轮唯一问题：原July固定十币/三HOLD配置在连续下一完整2024-12-01至2025-03-01前90UTC日，净/风险/容量增量是否仍存在？D055约72–73%净利润来自Nov，inverse较equal增加净但gross/波动/DD也增加；已有摘要诊断不能回答下一市场状态，故选此比新增币/模型/参数更有信息价值。三配置TWO_CONTROL/equal10/inverse10各四BASE27/STRESS43×F/P情景=12新市场账户+12独立金融，初始一次完整10k/fresh flat、一个simulate连续DecJanFeb、只最后原5次有容量退出；Jan1/Feb1不reset，Dec1不借D055库存。独立两季度不拼成连续NAV或长期APR。日期按后续完整日历，已看范围仍SEEN_DEVELOPMENT，0pool/信号/风险/成本/单位选择/训练/HPO变化。

来源静态metadata核18 BTCETH trade1m/mark1m/fund角色已有D045接受8b665/a72c/3df70（只stat/身份，未payload重QA）；固定另8币×3个月×3角色=72新对象，遠端存在/尺寸/事件数尚UNKNOWN，不能预设每币8h或资金费计数。不新daily/aggTrades/LOB；暖源复用D055 composite847d：FebAug70daily+SepNov30trade因果reduce91daily，Dec前last200从May15，past30完整Nov。70旧daily与30旧trade只必要columns/identity，不重CRC/格式QA。90score角色新72只一次官方CHECKSUM/原CSVparser/独立格式完整日历和真实fund事件QA，old18只沿原接受身份和sha准入；不将D042父FAIL改PASS。0锁定集/密钥/发单/paid/规避限制，原BybitVIP0跨场所代理/F-P单位未认证/历史filters/MMR/publication限制保持。

新STATE联合硬1,000,000,000B（含失败/temp）：source≤300MB（input≤200/temp≤100）/1800秒/RSS1GB，单ZIP16MB/CSV128MB/档30秒/原默认transport/不重试，72对象144GET；QA≤5MB/1200秒/RSS1GB；main两币≤100MB/十币各≤250MB、各1800秒/RSS3GB；financial三目录各≤100KB/1800秒/RSS1.5GB；余量约94MB给必要case/meta/temp。source72估算约151MB不是已测尺寸/ETA，超边界真FAIL不放宽。共享内核4,999,999,488B/swap0/GPU0，线程2，D40/32warn/36stop、初始约24.385GB/联合新增1GB低32继续。全部长任务WSL原progress/bounded，source与QA依赖串行，main串行；已实测允许仅完成一组后financial与下一main有限并行，预计共享<3GB，不保护性中断collector。

普通活动代码最小正常修改：data/默认transport增加一个有限winter90 profile并复用原acquire/format/dayblocks；source_acceptance只单次72新+18oldmeta+100旧warm；runner与auditor/comparer加explicit季度身份，保留D055接口。静态已发现Dec first.replace(month=month+1)产生month13，修正常跨年next-month；不得仅改91为90。金融/HandLedger/target/原容差和核心账户/执行完全保持。一个必要新calendar/暖接线拒绝反例，D055已验月界/手钱包不重跑；不复制整套V1/V2/V3为活动依赖或建新治理平台。

事前主要指标fullcapital net/gross/fee/exec/fund、月份/资产/方向贡献、actual annual daily vol/minuteDD、mean/max net/gross/保证金、turnover/集中度、terminalq/未实现/是否cash、资源真实峰/耗时/文件与物理盘增量。相同caps非同实际风险，不事后缩放。四条件净增且vol/DD都不更差才提升研究优先级；净增但风险高只保留权衡；全条件不胜且无风险改善暂停对应配置；cost/unit改变结论则UNKNOWN不挑档。仍NONE/CASH/APRNE，positive只支持开发保留而非投资采用。

停止在12新account/12independent、两保存pairs和必要新source/yearcase，或真实缺失/格式/破产/容量/预算错误；缺口不填零，不按结果换币/删日/延长退出/弱化风险减仓。末未flat保留完整marked与unreal，cashNE不抹数据。再决定保留、暂停或换策略；更多币/ML reopen须明确覆盖/信息机制问题与有限同产品对照，不因保持所有能力而机械算力。资料获取、因果财务、原生/独立投资资格分别验收。

### D056结果决定：配置增量未跨季度延续，下一检验方向/现金

12main/12financial与八保存配对真实closed0，各90UTC日/129600分钟/一次完整10k钱包。TWO净-593.83..-638.61，EQ10 marked-732.17..-761.39，INV10 marked-748.99..-780.98；十币SATS残仓5.64..5.97/24.14..24.56名义与浮亏纳NAV，cashNE，未延长5次退出。最大独立cash3.64e-11/ratio3.02e-14、原tols；全frozen sizing未另完整重建，单位/native/APR不认证。190身份/3510真实fund，未补Jan1 exactcoupon。

价格gross是主亏损（BASE/F TWO-580.63/EQ-723.79/INV-738.10），成本10.36/7.23/8.89较小。扩池四档净少122.78..138.35，毛少143.16/成本省3.13/fund省15.45；波动略低/DD更深。INV再净少16.81..19.59且gross/实际vol/DD更高。9/10币负，只XRP正，不按收益换池。D055正结果与Nov集中保持，两个独立季度不拼NAV/APR。主要瓶颈是持续多头价格暴露，非成本/内存/缺币数。

采用N资产/共享资本/连续账本/marked能力；BTCETH HOLD稳定控制、EQ10基准/INV10挑战者保留，暂停十币配方投资晋级，投资NONE/CASH/APRNE。失败一个季度不删除能力，也不机械耗算力维持方向。

下一唯一任务未运行：固定July10等权，仅加已完成过去30日绝对收益>0做多、否则现金门。30日取已有risk信息期限，为未测事前选择，不扫期限/阈值、无short、闲置raw预算不再分配，200warm/past30cov/.10、abs.3/gross.6/同费用F-P/容量/原退出保持；实际暴露需报告。直接复用fixed_targets(direction_factory=...)和正常runner/account，两个完整季度各一完整10k钱包，与已保存HOLD/CASH比较，0旧市场/QA重跑；运行前简记有限预算/病例/停止条件，不加平台/金融loop。

选择它比扩币/换allocation/省小额成本更有价值，因为它直接检验是否可以因果地减少恒多头下跌毛亏，同时保留前季收益。两个季度四档均净增、实际vol/DD不更差、非单月救回且退出诚实才提高研究优先级；一季胜/仅少暴露避损/单位成本反转，保留机制诊断或暂停，不搜参救活。十币投资reopen仍须更长独立跨状态/实际风险、单位/native/可退出资格；更多币/ML需明确覆盖/信息机制及有限共同对照，SMA50/200仍暂停，重开需具体新机制。原生资格gap不能解释当前gross负，暂非救亏主实验。

source148.389MB/main352.811MB/financial40.564KB，RSS≤432.382MB/shared实采2.558GB、内核历史3.263GB非本版峰，原hard5GB/swap0/GPU0/D40/1GB增量保持。原guard最终实扫24,890,287,979B@2026-10-04T02:33:52.261086Z（preGit），区间全ROOT+VHD增336,855,622B含collector等，不是实验文件量。五真实失败和最小正常修复、旧源/task保留，registry不放宽；0旧QA/市场/绿测/模型/HPO/依赖/keys/orders/locked/paid。collector540真活、8765准确，模块源码/敏感门槛后正常push，精确结果仅按后验同步凭证，不预造后台研究。

### D057事前：固定30日方向/现金门，检验价格暴露而非再扩币

上一goal turn为progress：D056真实90D/12新账户/12独立金融/八配对、五真实失败与正常修复、文档/门槛/正常推送核远端1459b2d完成。当前HEAD1459b2d17cc669a736e2caebf90cd2734c82a835，tracked clean/37untracked（旧36WIP+1实际D056后验），0研究running、collector540真实PID活、8765 errors[]/hard4,999,999,488B/swap0/GPU0；末scan24,890,287,979B@2026-10-04T02:33:52.261086Z为preGit实际点，不伪造当前容量。后验同步fc91fe38本正常模块入库。

唯一问题：固定July10等权，把恒多改为已完成过去30日close[-1]>close[-31]才入多、持多<=退出/否则现金，能否减少冬季价格毛亏且保留前季上涨收益？30取既有risk信息期限，零阈值一次固定选择，未测不是最优期。原shared目标200warm/过去30协方差/.10仅缩小/单币abs.3-总gross.6/逐仓1x/no topup/完整10k/BASE27-STRESS43×F-P/上一分钟.001容量/原5次末退出不变；inactive raw预算不再分配，risk缩小比例与实际暴露可能不同，完整报告不宣称同风险。无short，原close-then-wait下个日决策才重入，与HOLD单一方向因素对照，不同时改变池/配置/费用。

仅Sep1-Dec1前91D与Dec1-Mar1前90D，各新策略4账户=8新连续钱包/8独立金融，各季度fresh一次完整10k，季度内跨月不reset；不拼两个独立钱包或改历史unseen。复用两原已接受manifest847d/56f1及已登记July池9b8d，旧HOLD/CASH只读保存比较，0源下载/CRC/旧QA/旧账户重跑/模型/fit/训练/HPO/新依赖。新正常薄direction adapter、现有runner/comparer和独立target分支，金融/HandLedger/成本/账户/目标risk数学不重造。两个必要小病例合并验证方向状态/过去可得性/未来扰动/成员与顺序/raw不再分配，以及独立拒错误等号/提前day；与新入口有关的必要测试 בלבד，不用旧绿测充数。

有限预算全部含底层calls：8main/8financial/两保存配对，两main串行，只已完成组金融可与下一main有限并行；总新STATE≤800,000,000B含失败/temp，各main≤250MB/1800秒/RSS3GB、financial≤100KB/1800秒/RSS1.5GB、tests≤10MB/1200秒/RSS1GB、meta≤5MB。预计main约308MB是预算预估非已测，实际超限真停止；原shared5GB/线程2/D40-32warn-36stop/swap0/GPU0/collector保护。每长任务原progress/bounded、新专属STATE，不覆盖旧报告。0keys/真钱/orders/testnet/mainnet/locked/paid/杠杆风险资本增加，不绕场所限制。

指标：完整资本净/gross/费用/资金费、actual vol/minuteDD、净/gross与保证金均/峰、换手/交易原因、资产/月/日集中、残仓/浮亏/退出、实际resource。主要判定：两个完整季度四情景都净增且actual vol/DD不更差、非单月救回才提升研究优先级，依然NONE/CASH/APRNE；仅少暴露避亏/一季有效/成本单位反转只保留机制诊断或暂停，不继续扫30周边期限/阈值。停止8+8+2及必要病例，或真实缺口/金融/破产/容量/预算错误；原marked/cash分类不放宽、不延退出或删亏币/日期。负结果后依据机制自主换路，更多币/ML仍需明确覆盖/信息问题及有限共同对照。

### D057结果决定：方向门仅防御权衡，暂停晋级，转不同收益机制

两个完整季度8main/8financial/两保存pair真实closed0，财务最大cash2.001e-11/ratio2.665e-14，原tols；另一次独立只读审阅确认新30日reference与冬季cash=false/残仓桥一致。秋季net965.08..1037.19，比原EQ少65.75..95.36，BF gross少21.67/cost多44.88/fund省.80；turnover.668→3.992、vol9.961→10.319%、DD3.495→3.518%。冬季marked-604.60..-561.53，比EQ少亏152.19..175.23，BF gross少亏202.67/cost多31.76/fund省4.32；gross仍-521，三个整月/十币net负，meanGross11.61→8.82%、vol9.77→7.37/DD10.02→8.44。未识别同风险alpha，两个独立账户不拼APR。冬季SATS库存460.12..462.67/浮亏-12.45..-12.83保留，4清仓NE；秋4实际flat。不改变成本/单位/原五次退出或删币。

事前双季净/实际risk改善门槛未通过。采用N资产共享资本/正常cash门能力，暂停固定30日门晋级和参数救援；投资NONE/CASH/APRNE。稳定两币HOLD控制、EQ10基准与inverse挑战者保留，扩币净增量状态依赖，更多币/逐币模型当前没有覆盖或信息缺陷依据。现有原因journal缺口记UNKNOWN，不将新增成本全部归某类退出，也不把平仓gross归订单原因。

下一唯一主问题转已登记公开固定低换手均值回归机制，先核RSI2完整周期/entry/exit与正常接口兼容，再选一个事前固定日线对照；旧1h负结果保持，日线未测且无胜率承诺。它比救30日期限、缩费用、按收益换币更有信息价值，因为本轮pricegross与turnover代价不能由risk caps相同解释。忠实语义不兼容或无明确有限对照则停止该配方，不搭平台；有净/真实风险/可退出跨状态优势才提高研究优先级。30日门reopen须新机制/独立跨状态净与risk/退出证据，非本两季事后搜参；native/unit在合法来源可核时重开。

新main187936950B、finance26390B，主RSS≤423.444MB/独立≤565.846MB，共享实采峰2.767GB；累计峰3.263GB不是新精确峰。末guard实际25,128,987,214B@2026-10-04T03:28:17.470050Z为preGit，区间增长202,858,429含collector；800MB STATE总预算待metadata出口精确合计，D40/shared5/swap0/GPU0不变。两个metadata启动失败127/1为0market/QA/protocol保留，原helper与经济source保持。0fits/HPO/download/newQA/旧账户或旧绿测/orders/keys/locked/paid。模块按原源码/字节/敏感门槛后正常push，以实际远端核对为准，不预造后台实验。

## D058 — 2026-10-04 运行前：日线RSI2不同收益机制

D057固定30日正动量门已实际两季度失败：秋季各场景落后等权HOLD，冬季少亏但仍负；该配方暂停晋级，保留能力。当前投资候选NONE/CASH，长期APR不可评价。本轮只测试一个不同机制：固定MIT Jesse RSI2原多头入/出规则，日线5/200/2/10；不调阈值/周期/择币/费用/风险。使用同July10池和完整10k账户、原abs.3/gross.6/逐仓1x、原分钟成交与mark/真实事件资金费、两成本与两个UNKNOWN单位情景。新日线周期为显式新假设，不追认旧1h失败。

对照保存D055 Sep-Nov91日与D056 Dec-Feb90日等权HOLD/CASH及原两币结果，旧钱包不重跑、不拼接两个满资金季度成长期NAV。RSI官方scalar需240日，旧213日秋季暖源不足；先单独补January2024同池1d暖源（尽可能复用已验BTCETH2条、只下载/独立QA其余8条），旧pool200日资格/来源manifest/评价起点不变。预热不足/缺口如实现金而非补值。普通源码增加明确warmup参数和闭合price上下文，默认200逻辑保持，原经济证据按Git保留。

预算：1配方0fit0HPO；最多8新账户+8独立记录账本核对、2保存工件配对，不重验旧市场；新暖源owner<=10MB/900s/RSS1GB，每quarterowner<=250MB/1800s/RSS3GB，合计STATE<=800MB，共享5GB/swap0/GPU0与D40GB原守卫。必要受影响小合成测试与独立官方kernel序列参考，不造平台。停止条件：真实日历/账本/来源不符即停止修正确切问题并保留失败；负毛收益或成本耗尽/跨状态无价值则暂停固定配方。采用需要同时有净收益/成本余量与实际风险可解释，开发历史正值不产生独立优势或真钱资格。
### D058结果决定：均值回归long低暴露但无跨状态收益，检验原选择性short

两原完整季度8新共享账户、8独立核账与8保存配对真实闭合/终端库存零，独立只读复核无实质矛盾。秋net44.10..57.93USDT，冬−485.16..−459.01；相比equalHOLD秋少1012..1049、冬少亏257..293。BASE/F秋gross73.33/cost15.37/fund−4.67，冬gross−423.27/cost35.45/fund−6.06；冬即使免费交易仍毛亏，February约73%损失，只有January小gross被成本吞噬。actual vol3.152/6.229%与minuteDD1.641/6.700%主要低暴露权衡，非同riskalpha。秋WIF最初13日240成熟cash的配对差异如实披露，冬0；未来未授权/独立证据不自授。

采用正常N资产/暖源/日线适配能力，暂停固定RSI2 LONG_ONLY晋级，投资NONE/CASH/APRNE；原两HOLD、equal10/inversechallenger保留，固定30日仍暂停。不能因用户要short强行short，也不把教学策略代表市场上限。下一选择已登记原RSI2明确超买逆趋势short分支增量，对照savedlong/CASH，固定5/200/2/90，无阈值/周期HPO、同完整账户/费用/单位/risk/data。先核原entry/exit和实际恢复状态，必要最小正常signed参考与病例后完整跑LS账本；long与short争同资本/有符号协方差/总gross，不能加两个独立满资金结果。机制为利用部分下跌趋势中的超买回撤，而非只靠少暴露；若无跨状态净/实际risk/成本余量则保留能力/暂停该配方，不自动救参。相比扩币/降低费用/加ML，它更直接回答冬季gross方向瓶颈且现有数据和成熟实现成本低。

Reopen：long与30日配方需要新因果信息/机制或独立跨状态净与actualrisk/退出证据，不在已见两季挖参数；扩池/逐币ML需明确覆盖/信息问题，当前无；native/unit在合法官方archive定义或历史响应可得时。三真实失败startup1/argparse2(host1)/sourceguard1原字节/计划/task保存，V2只正常来源守卫修复两明确pin文本，金融四函数体同pre-market cefd，不再做额外QA/市场/旧绿测。主RSS400MB/共享采样2.652GB，独立RSS≤593MB；最终物理25,200,014,390B@04:45:44.347845Z、增68.685MB包括collector，不是纯输出。0fit/HPO/真钱/keys/orders/locked/GPU/paid；D058科研已结束，下一未启动。模块按正常小证据/字节/敏感门槛提交推送，成功只按真实后验远端一致。

### D059事前：原选择性空头的共享资本净增量

上一goal turn实际完成D058真实经济/独立核账/最小来源守卫修复/文档/正常推送与远端61316ff，是progress。当前HEAD61316ff1865437b8cc7a286e0e2aad95bdc67340，tracked clean/36旧WIP+1实际D058后验；8765 errors[]/无研究running，collector540实活，原硬5GB/swap0/GPU0/D40GB保持。前次实际磁盘25,200,014,390B@2026-10-04T04:45:44.347845Z，非此刻新测。

唯一主问题：同日线RSI2规则加入原选择性short（完成price<SMA200且RSI2>=90入空，持空price<SMA5退出）后，在同一完整10k组合账户，是否比已保存LONG_ONLY/CASH增加净收益且实际风险/成本/退出可接受？只一主要因素direction_mode LONG_ONLY→LONG_SHORT，原5/200/2/10/90/240warm/池/未来数据/费用/单位/资本/risk不变；不把“不多”全变空、不强行正负对称，不按收益另挑币。Signed covariance和共享gross/隔离margin会改变多头路径，贡献必须分short与long改变、不能加独立账户。退出后下一日才重入，不无成本瞬间反手。

数据：原July固定十币池、已接受Jan日暖源（秋首13日WIF不足240如实cash）与两原scoring manifest，Sep-Nov91日/Dec-Feb90日，各情景fresh10k钱包季度内连续、不拼独立季度NAV。已看开发筛选、未来/locked未启封。复用原MIT Jesse long/short/exit hooks、官方已装jesse-rust1.3.0和正常N目标/账户/分钟日块/独立账本；不新增数据/QA/依赖/模型/HPO/平台。历史D058默认long目标/metadata严格兼容，旧protocol/source由Git保存，正常源码用明确mode接口。

有限预算包含必要底层calls：1规则/0fit/HPO、8新main+8独立finance+2保存配对；唯一新受影响合成fixture，原long默认精确对Git、selective-short状态与账户signed语义/共享caps/因果/顺序。两main串行，金融只有完成组可受5GB组限并行；新STATE总<=800MB，各main<=250MB/1800s/RSS3GB，finance<=100KB/1800s/RSS1.5GB，test<=10MB/1200s/RSS1GB，metadata<=5MB。既有progress/bounded与线程2；保护collector，不增加CPU/RAM/GPU/网络/资本/风险权限。

指标：完整资本gross/net、long/short价损益和原long路径变化、fund/cost/turnover，平均/峰值gross/net/margin、日波动/分钟DD、资产/月/日集中、部分成交与末库存/未实现/退出、实际RAM/耗时/磁盘。采用提高研究优先级需两季四情景净增、实际风险解释与可退出、非单季/单位事后胜；仍不授APR/投资资格。一个季度正或仅低暴露防御则保留机制/暂停，毛亏或成本反转则暂停配方，不搜参救活。真实来源/账本/破产/日历/预算错误立即保存失败修最小具体问题；标记marked/清仓NE不放宽原5次退出、不免费删除仓位。结果后自主决定继续/切换，当前候选NONE/CASH。
## D059结果与下一选择（2026-10-04，原事前条件不变）

固定原RSI2选择性short已真正接入N资产共享完整10k账户，两原季度各四费用/单位场景、8独立金融/8保存方向pair真实完成；原多头不重跑，0新下载/模型/HPO。秋净-104.43..-147.54、比多头-157.71..-196.30；冬marked净-43.80..-75.60、比多头+407.52..417.24。BASE/F空头净贡献-156.44/+416.86，多头路径差-1.27/+.38；总桥<=1.308e-12USDT。秋gross本身负，冬short防御收益被long毛亏抵消、总gross近零后真实成本使净负；冬vol升/DD降，非同实际风险alpha。冬所有成本情景SATS空头残仓407.75..409.31/浮利11.45..11.78计NAV，清仓收益NE，不能虚构退出。

采用真实N资产双向能力，投资仍NONE/CASH/APRNE，暂停固定RSI2配方投资晋级与旧窗参数救援；不由一秋季short失败删除做空能力。恢复条件为新因果信息/机制或真正独立跨状态、完整成本/风险/退出证据，扩池/逐币ML需明确覆盖或信息缺陷。已见日期不改名unseen，两个季度不拼APR；Bybit+Binance/资金费unit/native仍条件代理。

下一选固定Turtle LONG_ONLY单层/禁主动加仓消融。对照依据D049完整303日gross+443.89..457.17/net-83.13..-425.34、turnover38.55..39.24；BASE/F总成本528.35/ADD60.16，直接ADD费用不足解释亏损，需新完整目标/成交/资金/NAV路径检验是否降低后续换手。原BTC/ETH、资本、四成本/单位、止损/退出/必要风险保持，不删ETH、不相减旧费用伪反事实。旧bridge/currentN与finance接口兼容须直接正常修复，避免AST包装；尚未运行，运行前再记有限预算。少交易却gross损失更大、风险恶化或全成本仍负，则暂停配方，而非无限搜参。

独立核账最大cash2.183e-11/ratio3.253e-14、原容差、只读同行复核未发现矛盾，范围限制不扩大。最终原实扫25.304GB@05:47:45.669212Z、本轮shared实采峰2.703GB，硬5GB/swap0/GPU0/D40GB保持。小结果/协议与源纳入正常模块Git；实际远端一致另由后验凭证确认，0真钱/keys/orders/locked/paid。详见MULTI_ASSET_PORTFOLIO_20261004.md的D059。

### D060事前：固定Turtle多头的单层成本消融（2026-10-04）

问题：D049原Turtle多头303日gross+443.89..457.17但net-83.13..-425.34USDT，换手38.55..39.24倍；禁主动ADD是否产生完整账本净增量，而不是仅删除旧成本？只比较PYRAMID4(defaultTrue)与SINGLE_LAYER(False)，同一正常共享N账户入口、原BTC/ETH、完整10k、2024-09-01至2025-07-01前303日、四原成本/单位情景。两者均LONG_ONLY，保留原entry/channelEXIT/STOP/必要风险减仓/部分ENTRY碎片/容量五次/末退出。原20/10/ATR20/2/4/.5规则不搜参，False仅在收集原ADD后、协方差候选前清除提案与暂存副作用。

先正常维护活动bridge/事件接口，去掉旧两币/失效来源常量/运行时财务AST包装。一个必要合成病例后先运行新default四账户，对旧D049保存的成交/资金费/目标/分钟NAV与仓位/末库存做语义一致核对，cash1e-7/ratio1e-10；版本/profile/snapshot新字段不冒认旧字节一致。通过才运行新False四账户。最终只将同新loop的True/False作为单因素经济对照，旧数据只参考、0旧模拟重跑；禁ADD效果包括资本/止损/暴露/资金费路径变化，不能都归因省ADD费用。

数据角色SEEN_DEVELOPMENT；复用已接受94来源+4官方4h预热，信号4h/成交mark1m/资金费事件分开，0下载/旧源QA/fit/HPO/扩币/locked/keys/orders/GPU。最多8新主账户+8独立记录金融、一个新合成病例与两必要保存比较；若兼容核对失败，停止新False市场并先保留失败、定位最小正确性问题。每主任务owned<=250MB/RSS<=3GB/wall<=1800s；独立owner<=100KB/RSS<=1.5GB/wall<=1800s；整个新增STATE<=700MB，原sharedhard5GB/swap0/D40GB与资金/caps不变。必要预检/失败/复测另如实登记，不将重抽样当历史长度。

主指标：完整资本gross/net、费用/执行/资金费、按订单原因的名义额/成本、成交腿/换手、gross/net/margin实际暴露、波动/MDD、完整日数/终端库存及收益集中度。0未知原因伪归因，所有成本/单位都报告，不删ETH挑赢家。少交易但gross损失更大、风险恶化或四条件仍负，则暂停该配方，不无限救参数。资格仍NONE/CASH/APR不可评价；只有同产品完整成本下可复现净增量并理解实际风险/退出，才保留挑战者，独立/原生证据另限晋级。

D060事后新增有限诊断：单层BASE/F在83,285分钟后因五次必要BTC风险减仓无法成交真实停止；其余单层情景未运行，完整303日对照NE。禁止删缺口/增加尝试/松容量或风险救结果。保留失败V1，下一只调用既有独立财务体核该记录prefix（1次，原容差），读取相同金融必要列核五次真实前一分钟容量，0新账户/QA/拟合；单次RSS<=1.5GB/wall<=1800s，仍总新STATE<=700MB。依据实际输入判断是正当容量停机还是正确性问题，不能将prefix净亏当同窗经济差。

D060最终：default四303日保存迁移数值误差0/独立四PASS；single首BASE/F五次0容量止于83285分钟，其余三与完整paired未运行。prefix独立PASS，raw五行quote/base/count真0；但20:00 riskweights==raw、vol<.1/caps未触发，Decimal回转1.21e-18变成1%减仓，确认correctness blocker。原账本保留，Turtle旧投资解释标记待修正，不能据prefix否定single。下一最小修未缩放数量身份+必要反例，真风险/STOP/EXIT不关闭，原容量5次不变；随后新版本相同8情景判断。当前NONE/CASH/APRNE，不进入其他调参。D060作为正确性发现验收，Git同期后验核。

D061事前：D060真实同权重数量回转反例已确认，普通correctness修复不再要求复现已知错误。正常bridge只记录逐币原Decimal candidate；权重严格==raw时保留其数量，其余缩放沿原路径/.99。VERSION绑定新映射，旧snapshot拒绝，不复制V3文件。保持原风控/账户/成本/容量/五次/STOP/EXIT，禁止epsilon豁免caps。先一个真实hook与账本的新固定反例：scale1不造减仓，实际scaled仍reduce-only成交付费，N3币序/STOP/EXIT/恢复保护；原D060旧test不重跑。预算1新case/RSS<=1.5GB/wall<=120s，STATE独占，0市场/旧QA/fit/HPO/download/locked；通过后下一新两方案同条件8账户/8金融，经济指标目前未测。

D061实际新反例PASS（1f985b7a.../金额原容差，50.87s，旧case未重跑）及独立只读8行复核后，选择继续同固定303日True/False八主账户/八金融。D060数学错误允许目标/成交轨迹变化，不执行要求旧错误完全等价的migration；已接受来源94+4/原资本费用风险/真实容量5次保持。两个主任务可并行，仍共享hard5GB，每任务RSS3GB/owned250MB/wall1800s，总STATE700MB，0新QA/download/fit/HPO。若真实HALT/不完整，保留失败、全期delta NE并核真实必要原因；不提高caps或扩末尝试。

D061事后决定：修正后8个完整303日/末全平账户与8独立金融均closed0，四同loop配对全负且禁ADD比原再少107.65–182.85USDT。BASE/F毛少311.44、成本省129.14、funding再多付.208，换手约减24.4%但MDD6.640%→9.158%、vol7.468%→7.488%。采用无epsilon数量身份修复；暂停固定禁ADD配方投资晋级/HPO，原P4也NONE/CASH。旧错误调度财务保留，投资解释由D061替代，不据归因事后删ETH；N资产/多空/现金能力与两币HOLD/十币基准保留。当前主要缺口是稳定收益机制和独立证据，费用/单位/原生仍条件化。新机制或真正独立净/实际风险增量才reopen，细表/资源/失败见MULTI_ASSET_PORTFOLIO_20261004.md的D061。

D061下一唯一研究选择（尚未运行）：保留原July10与固定past30多头/现金门，在第三个自然完整2025-03-01至2025-07-01前122日开发窗口，与同窗口十币HOLD、两币HOLD及CASH比较。D057秋增量负、冬防御增量正但仍亏/有残仓，跨第三状态的信息价值高于对负Turtle扩币或加过滤救参。只补必要OHLC/mark/实际funding，日块读取，先核现有覆盖和来源；不全量aggTrades/LOB、不换池/阈值/资本/caps/费用/单位。最多3配方×4情景=12新账户/12必要独立金融，0fit/HPO，shared5GB、D40GB、新增源和工件目标≤1.5GB且新增前需守卫核余量。数据不足/缺mark/funding或真实无法退出不补零、不改次数；停止依赖的收益评价。完整同成本下能跨状态改善净/实际risk、收益不集中且退出诚实才保留挑战者；否则暂停这个配方，不追加参数网格。各窗口fresh完整10k，绝不拼NAV或称unseen/APR。主要next交接：核当前multi_asset_data已接受Mar–Jun源覆盖，事前固定同口径有限manifest再执行。此决定由root与独立只读复核一致支持；后续任务未在本模块后台启动。

D062事前（HEAD a98ceb45178d445b78a2cac113956f0408ac07fe）：D061已真实同步/远端一致；前轮为progress，已修正确性并得到完整负经济结论。当前无科研后台，collector保留。已有metadata coverage真PASS：Mar–Jun122D score120，原BTCETH24接受复用、新96可得性UNKNOWN；warm daily70+SepFeb trade60=130，目标manifest250唯一身份。普通normal四月日期/源guard/四月独立核账接线并行维护，核心账本、目标、风险、容差不改；只有现有official URL/CHECKSUM薄包装。有限最多3配方×4=12新主体+12独立金融、0fit/HPO，源/工件联合1.5GB、shared5GB/swap0/D40GB，每主体300MB/RSS3GB/wall1800s，source400MB/wall1800s。明确missing不补零/locked不触/read-only不发单；评价期已见不称unseen。采用门：固定30日门若第三状态还不能改善净/实际风险/可靠退出，则暂停该配方，保留能力和真实负结果；不搜阈值/换池/拼季度NAV。

D062来源真实闭合：V1在48档遇到Polars整数前缀推断volume列随后6701.80失败；修复正常src/quant/data.py读取浮点价格/量，timestamp/count仍Int64，无ignore_errors/null填充。原337f/d657/861b源码精确哈希另存档。恢复36原完整未接受行+12旧接受控制+1原ZIP，仅59新下载，source120/QA96+24/manifest250真实闭合；新日历与小数尾行反例各一次实际PASS。一次relative-protocol启动错误和一次account元数据旧HEAD pin不匹配都在科学调用前，保留真实task，不视为市场尝试。

新费用附件输入复核：标准合约taker .00055原本已正确，8类display/100=fraction=bps/10000全部核对，未观看两原截图/未知生效期/费区仍不能认证。D0618条保存摘要Decimal gross-fee-exec+fund-net误差<1e-7；BASE/F原加仓不扣额外execution旧数量敏感度+206.15，禁ADD-52.88。原额外execution313.67，约5.26bp/侧盈亏平衡仅调查门槛，非可执行新回测/数学上界/基准费用目标。既定第三窗口不改变成本；下一主问题选择独立spread/impact及同timestamp资金单位来源，不继续轮换教学策略名称。尚未拆账户通用4+4下限，待当前冻结研究闭合后正常维护；新附件不扩资金/产品权限。

D062十二122日账户/十二独立金融/八保存pair真实闭合。两币net377.46..405.99，全末清；十币marked124.36..140.16/残仓192.62..193.15，低波动但DD更大，cash return NE；past30net66.46..101.12全末清，较十币少35.78..61.20且gross几乎相同、主要增成本。BASE/F meanGross15.758→10.300→6.408%，vol10.749→10.559→7.641、DD6.054→6.582→3.909；相同caps不等实际risk。采用多币/读入/parser能力，暂停扩池和fixed30投资晋级，保留两币HOLD/十币参照及多空，不按结果删币或调阈值。下一唯一主问题选择独立执行摩擦与fund单位校准，之后有来源的成本配置/少量完整回放；不由旧加回execution直接晋级。硬5GB/swap0，本轮组实采1.831GB/生命周期3.263GB分列；物理26,175,152,059B@11:46:44.089669Z，未来文件不在该扫描内。模块科学已结束，Git尚待真实同步。此次goal turn为progress：真实修复/来源/经济/独立证据改变决策；完整总目标仍active。

### D063运行前选择：成本来源与活动账户有限修正（2026-10-04）
D062已push并精确验证f895f4b32e3c2e6e61b15b022ce46736982e9865，36无关WIP保持；post-sync初版误要求已保存source失败也exit0，未出凭证，第二版按原expected exit1核对，未改原失败。当前瓶颈是未校准摩擦/产品代理，而非需再换策略名称。用户附件作为费用来源和纠偏参考，已有自主权限内执行普通修正；没有新增账户/资金/产品权限。
问题：去除通用账户把旧5.5bp/4+4当自然下限，同时旧BASE27/STRESS43目标/成交/现金/NAV不变；修正STRESS合同元数据43与非等额摩擦报告，新增成本来源/产品/按symbol显式费区/TAKER接线及恢复逐腿费用验证。maker无排队证据不执行，未知fee-zone不能按symbol自动用最低费；单账户目前仅支持同一声明费区，混费区拒绝，不假装已全类计费。
对照：精确parent账户在两旧摩擦下的相同手算序列；独立2+1bp手算；同一活动runner两日有符号目标、实际多空模拟成交与共享10k账本，2+1bp及0额外摩擦仅合成正确性，绝非市场成本估计/新历史投资结果。保留8类来源快照，普通线性账户只接已有加密线性范围；无新HPO、市场历史回放或API。
预算：6个针对变化测试，两个2880分钟合成完整账户，120秒test子进程/1GB RSS/5MB owned；共享5GB/swap0/GPU0/40GB/锁/caps不变。失败则保留新记录并有限修，费用/风险不事后调为盈利。验收观察逐腿手续费、实际资金流、反手/partial/reduce-only、终末NAV、按实际摩擦比例月报、来源绑定和恢复篡改拒绝；不重跑无关旧测试。
更正D062结尾“原始HTTP待执行”：资金单位核对早已实际执行FUNDING_SEMANTICS_PROBE_20261003_V2(task94a04f7ca7a3407e9905109fea9feb4c，HTTP451/exit1/matched0/retry0)。Bybit profile probe V2亦已有403/停止一请求；无访问条件变化，不再次API/换host绕限制。单位桥与目标场所盘口校准暂停，reopen合法官方archive单位说明/同历史响应或合法原生数据可得；当前网页只提供字段定义和VIP0通用费率，不认证历史盘口/费区/费率。

D063首测真实task c0ba9e385668428e8954b0b07a61a0e6 / exit1：6项中5pass；唯一failure是测试期待的异常文案，实际已拒绝不匹配来源。没有会计误差或收益失败被改标准。修正反例让期望上下文仅变execution-source（同fee），保留原源/报告/任务。独立子agent同时查出CASH缓存仍携BASE27合同元数据且首次CASH未走来源接口；真实活动main改用同一正常account_for_cost/cash_cost_summary，重建零账户摘要而复用工件，不重放行情。新的有限7项复验覆盖这项实质剩余风险和新接线，明确实际执行总次数，非复验旧历史；scope仍合成两个2日账户，无市场成本校准或新策略收益。

D063主V2真实7pass/exit0/225,239,040B RSS/51.09s、178,279B owned。结束检查发现实际多币使用的closing specialization构造器尚未转发新增cost_context，会破坏其snapshot恢复/非默认cost接线；正常增加一个转发参数，主账户和runner七项已验收源码不变，仅再运行一个对应活动specialization恢复/费用/旧默认用例，不重跑七项或历史。只读汇总两次失败：pytest current链接重复/误认save_case输出层级；没有新账户/测试调用，去重自有STATE真实路径及读取artifacts子键后汇总通过，失败helper原源与任务保留。

D063真实结束：主V2 7pass/0da14.. closing单项pass，2个完整2日合成10k账户多空4腿、gross0，2+1净-6.7314/0+0净-4.3558（非市场摩擦证据）。采用成本身份/合同/CASH/恢复/closing正常修复，标准taker原正确；投资NONE/CASH/APR NE。暂停原生执行校准/单位桥须合法来源重开，固定30与noADD晋级须新机制及跨状态净增量。下一唯一选择原规则与日线活动时序小核对，然后低换手连续HOLD对照；尚未启动。不存在新市场账户/HPO/模型/API/订单/锁消费。最近物理26,211,488,033B@12:24:36.211990Z，未来小文件/Git未含。本模块科学/正确性任务已闭合，Git待真实推送。

D064事前（HEAD2939301，成本修复已验收同步）：已有来源够Sep2024–Jun2025连续303日，370唯一源、0新下载/源QA。单一问题：previous20日突破+SMA200入场过滤、破previous20下沿退出的较慢持有机制，是否比同池稳定HOLD减少无效交易并改善钱/风险？复用已登记原MIT Donchian，不把4h20根称20日，不新增空头规则；全平台多空能力保留。原公开class无周期且whole-balance，本地明确日线/共享caps变体，非完整Jesse/native复现。先独立窗口语义反例，再3配方（两币HOLD、十币HOLD、十币日线Donchian）×原4条件=12完整303日共享账户/12金融复核；一个初始10k持仓钱包连续推进，十个月不得拼季度赢家。seen开发/资金单位和原生规则仍UNKNOWN，不降低摩擦或猜单位；之前403/451证据无条件变化不重复API。预算0fit/HPO/下载，新STATE≤1.5GB，每主体owned400MB/RSS3GB/wall1800s，组hard5GB/swap0/D40GB，guard预期<32GB。原5退出尝试/caps/.1%容量不放松，残仓marked与cash不同，失败保留。若净/风险改善不一致保留参照或暂停配方，不追加周期网格；稳定投资NONE/CASH。策略/池增量与实际risk分开报告，不因小收益宣布APR。

D064事后：12完整303日保存轨迹/12独立资金核验/8保存pair已实际完成，十币HOLD主体末超400MB输出预算为failed1保留，不假装主任务success；只对现存轨迹独立核账，不重跑或抬旧预算。十币较两币net少302.04–348.06/MDD13.20–13.41%更深；Donchian较同池HOLD少103.48–129.00，BASE/F gross差-94.88/成本+19.84/fund改善11.24，vol10.24→8.18%、DD13.37→9.34%，不称riskmatched alpha。低换手假设否定（3.01 vs1.54）；平均激活2.75、60cash日、meanraw.165→risk目标.0911→actual.0899，资金机会是更直接问题。预评分30收益paircorr.7213/主成分76.51%只作依赖描述，不按亏币洗池。采用正常连续来源/原entryfilter/独立诊断，研究参照HOLD2不变，投资NONE/CASH/APR NE；当前全源跨场所proxy/unitsUNKNOWN/nativeUNKNOWN。下一唯一选择active-only预算 min(.3,.6/Nactive)，0activeCASH，原信号/成本/风险10%过去下缩及caps保持，必须新完整账本判断收益与实际risk，不把旧NAV后验放大。最多两配方8主体/8金融、0HPO，新事前600MB/主体联合1.4GB，依据本次真实工件量，旧预算失败不追认；本轮未后台启动。固定N配方/扩池优越性暂停，reopen明确同条件净/风险证据；原生/单位合法来源桥未变不重复403/451探测。

### D065 事前：日线Donchian激活预算单因素检验（2026-10-04）
当前HEAD55798a1，D064已推送、远端一致。问题：固定十个成员分配预算是否压低净参与？仅改变raw=min(.3,.6/N_active)，0active=CASH；prior20/SMA200日线信号、同July池、303日、过去30日协方差10%缩减、完整10k、abs.3/gross.6/逐仓1x、原成交/末5次退出和成本/资金费双解释均不变。D064四已保存Donchian账户作为同口径控制；新四个ACTIVE_EQUAL完整账户及四次独立核账，0模型/HPO/下载/QA/发单/locked。看过的历史仍开发筛选。先用原日线用例与一个新active用例核信号/目标/因果、caps和协方差，再事前冻结源码/协议。预算：新市场STATE≤600MB/1800秒/RSS≤3GB，独立≤1.5GB RSS，新增STATE合计≤800MB；共享硬5GB、磁盘40GB与32/36GB守卫不变。停止保留缺失/破产/预算/无法清仓，不延长末退出次数、不重估成本、不搜参数。主要指标完整资本net、价格gross/费用/执行/资金费、实际波动/MDD、平均峰值敞口、换手、残仓及分月连续贡献。仅净改善且实际风险差清楚、四情景一致才保留研究挑战者；不在开发阶段投资晋级。方向能力保留，本原公开配方仍long/cash。预计约10分钟市场回放、分钟块读取，现阶段尚未开始市场任务。

### D065后验决定

D065已完成：同原日线Donchian信号/July十币/连续303日/10k共享资本，仅raw改为激活预算。四新账户与四独立核账完整、末全清；净收益提高67.62–88.34USDT，全部固定成本/资金费解释同向。BASE/F净259.53→340.50，实际年波动8.18%→9.91%，分钟MDD9.34%→9.10%，换手3.01→4.76倍完整资本；不是匹配风险alpha。112未风险饱和日改变目标，131饱和日不变，信号/协方差成员一致。采用ACTIVE_EQUAL为研究挑战者、保留原EQUAL及两币HOLD主参照；投资NONE/CASH、长期APR不可评价。主要毛收益缺口与独立证据仍在，不按收益删币。D064旧预算失败及此次inline身份/首次CLI失败保留。当前下一优先恢复已授权但实际丢失的两路只读采集：已确认无进程、退出原因UNKNOWN，先三件套保存与断档核对；尚未恢复，不把旧running JSON当活任务。恢复闭环后选择入场不变、仅10日退出的有限COIN变体检验，尚未运行；不搜参/改成本/caps/启封。Git按实际SYNC_VERIFIED，未预造成功。
BASE/F桥毛+111.337974−cost23.595362−fund6.782429=net+80.960183USDT。改变112未风险饱和日，131饱和日无变。净与回撤改善但波动、成本、换手及集中度增，不宣称同risk alpha；毛与两币参照仍有差距。下一实际任务恢复丢失采集，后续单一10日退出假设；均不是新的永久路线。

### D066事前：恢复实际丢失的原公开采集（2026-10-04）
D065已验收/推送并核远端b6b5177，净增量四情景+67.62..88.34但实际风险/换手更高，研究挑战者保留、投资NONE/CASH。常规核对发现原public_v3和microstructure_l1_v1均无实际进程，也无替代服务，旧running JSON是过期记录；真实退出原因/代码UNKNOWN，不推断OOM或正常停止。已有45.64MB STATE留证保存原DB/WAL/SHM、空日志、旧任务/hostrecord、原启动命令与闭合副本，原件前后SHA稳定，审计链/quick_check/代码/环境绑定通过。public末heartbeat13:32:43Z、L1checkpoint12:48:58Z；只是下界，不当精确退出时间。当前仅核已有2008feature清单的实际payload SHA，不重跑数据QA或读取locked；完成后单次按原.venv/source/defaultDB/store端点恢复，new独占日志/任务且detached，保留v1、不启v2、不改被冻结源码、不加observer/service、不读keys/发单/付费/绕访问。原启动已具备UNGRACEFUL_PREVIOUS_SESSION与RESTART_GAP，检验真实新session/heartbeat/accepted数据推进、资源、日志；两次观测，UNKNOWN/失败如实留存，不无条件循环重启或拼健康资格。容量实扫27.327GB加约1.053GB预留低于32GB，共享hard5GB/swap0/GPU0不变。闭环后更新既有状态、模块验收再Git。此为阻塞独立前向证据的实际最小恢复，不是新平台；后续10日退出单因素研究仍未开始。
### D066后验决定
D066已实际恢复原public_v3与L1 v1两路公开采集：数据库三件套/旧日志/任务/审计链已保存，2008份原清单payload SHA精确一致；原退出原因UNKNOWN。单次原环境/defaultDB/store/端点启动，两次实际新会话观测通过：BTC/ETH各增3根闭合分钟线、L1检查点前进163秒/增7361事件，同真实PID与资源组。public断档约119分钟、L1约165分钟明确不记连续资格；未认证72h/有效天/alpha，feature持久化增长本轮未证明。最新实扫27.363GB为启动前时刻，共享硬5GB/swap0/GPU0不变。8765可见新实际任务。D065研究挑战者ACTIVE_EQUAL保留、两币HOLD仍收益主参照；投资NONE/CASH、长期APR不可评价。下一科学问题为入场不变、仅10日退出的单因素COIN变体，尚未启动；Git成功仅按后验SYNC_VERIFIED。恢复证据见docs/PUBLIC_COLLECTOR_RESTORE_20261004.md。
恢复是保障未来证据的实际运维修复，不是投资晋级；采集退出原因仍UNKNOWN。原V1启动检查把wrapper argv也识别为采集句柄，仅验证helper V2加实际Python路径过滤，原报告保留，无重复启动/采集源码修改。新数据检查点推进与旧文件身份分别成立，未从几分钟观测推断持久化质量或健康天。恢复后回到D065毛损益/风险问题，固定10日退出检验在新协议事前记录后完整回放，当前无后台研究任务。

### D067事前：只缩短退出通道的完整经济机制检验
当前HEAD c67a06f；D066实际恢复与远端一致已验收，两个真实采集PID890567/890568在本轮ps核对存活，不重启。D065激活预算四条件增净67.62..88.34，但毛损益仍主要受ETH/SOL与部分连续月份下跌影响，且风险/换手增；研究挑战者保留，投资NONE/CASH。选择单因素exit20→10，prior20入场/SMA200、ACTIVE_EQUAL/过去30协方差10%下缩、July十币、完整10k、303日、原abs.3/gross.6/逐仓1x、成本/两资金费解释及5次末退出保持。该变体另命名COIN_EXIT10，不冒称完整上游复现。旧D065四账户只作保存控制，不重播，不删除费用或事后倍乘NAV。先一个直接窗口/状态/风险/未来扰动新反例，再四个完整账户与四独立直接目标/金融核账，0fit/HPO/新QA/下载/locked/发单。新market≤600MB/1800s/RSS3GB，金融RSS1.5GB，新增STATE合计≤800MB；现有shared5GB/swap0/GPU0/40GB与32/36GB守卫保持。主要看完整资本net/gross/成本/资金费、实际波动/MDD、平均峰值gross/net、换手、残仓、分月/资产贡献；若各条件净/风险无实用改善保留原挑战者或暂停该变体，不搜索其他退出周期。未完成/缺失/破产/末清失败如实停止或marked限定，不追认失败。保存所有尝试，普通研究自主决定下一项。市场在测试与源码事前绑定通过后才启动。

### D067后验决定
D067已完成：同July十币/连续303开发日/共享10k/ACTIVE_EQUAL/原prior20入场+SMA200，仅退出20→10。四完整新账户与四独立目标/资金核账通过，末全清。四条件净提高156.67–160.04USDT；BASE/F净340.50→497.16，毛+149.38、成本少6.49、资金费改善0.80，波动9.91%→8.36%、分钟MDD9.10%→7.43%、换手4.76→4.28。平均/峰值gross11.28/28.13%→9.09/23.43%，不是匹配风险alpha。二月增366.81、六月增162.77、三月反减429.45，历史/区间优势不足。采用EXIT10为当前规则研究配置、保留EXIT20控制及HOLD_TWO收益主参照；投资NONE/CASH，长期APR不可评价。代理/资金单位UNKNOWN/已见历史与原失败保持。下一先验证配对日收益的时间稳定性与依赖下不确定性，不继续搜退出周期、不重播旧账本；尚未启动。最近实扫27.558GB@2026-10-04T16:21:37.233593Z，新增STATE185.22MB，共享实采峰1.488GB/硬5GB/swap0/GPU0，原采集保护。Git同步仅按实际后验。细节见docs/DONCHIAN_EXIT10_20261004.md。
当前研究配置EXIT10只是开发筛选主力，不是投资候选。它相对20同时增净并降实际risk/成本，但相对HOLD_TWO(BASE/F670.63、vol10.49%、DD11.23%)仍少赚173.47且risk不同。更直接瓶颈为时间状态与选择后的独立证据；November净987.56大于全期497.16，March由+248.42→-181.02，不能从四个成本解释推出四独立市场优势。下一选有限保存配对daily log-return/固定时间段稳定性及依赖敏感区间，0新市场账户/模型/HPO，不把重抽样当新历史/alpha或可执行重新拼接NAV。退出周期搜索暂停，reopen新退出机制/独立区间证据；无来源的成本优化/资金单位选择/按亏损删币暂停，reopen合法原生及单位/分散信息。原失败CLI9a461...和原协议保持，V2仅调用绝对路径通过。全目标active，本轮为progress。

### D068事前：保存配对日收益的时间稳定性
HEAD33fa0de，D067已提交/推送并精确核远端；本轮ps核对原采集两PID仍在，8765健康，36无关WIP保留。四成本/资金费条件是同一市场，不是四独立证据。只读303连续日钱包：首日各自10k、日终有序身份/正NAV/清仓桥核对；log收益差与真实钱包PnL增量分别telescoping，固定[0,101)/[101,202)/[202,303)三段及完整月份，不重置资金。复用现有quant.metrics圆形块，7/30/60日各2000次固定seed20261005（24k描述性抽样、0fit/回放/HPO）；60日为主描述但只有约5个完整块，敏感性不择优，可能不满足平稳性/长依赖。去一月只作算术集中诊断，非可执行删日期。所有历史已看/后选择，区间不校正研究选择、不产生alpha/稳定APR/新OOS，实际风险仍不同。预算120s/RSS600MB/输出1MB，硬共享5GB/swap0/GPU0/D40GB不变；不新QA/下载/封存/费用选择/发单。日期/资金桥错即停止结论；区间含零或固定段反转则不宣称稳定优势，保留原有效经济证据与研究配置、投资NONE/CASH。独立作者另核固定分段/资金与几何桥；结果后自主决定下一项，不扫退出参数。

### D068后验决定
D068已完成保存303日配对时间诊断：四情景7/30/60日块区间全部含零；固定101日段BASE/F增量+2.75/-75.49/+229.41USDT。二月贡献超过全期，减去二月的算术余量-210.15，不是删日期回放。D067净改善与较低实际risk保留，稳定优势尚未确认；研究EXIT10/控制EXIT20/参照HOLD_TWO，投资NONE/CASH、长期APR不可评价。0新市场/fit/HPO；24k描述抽样实际0.941s/RSS97.59MB/共享采样398.95MB，硬5GB/swap0/GPU0。最近物理扫仍D067的27.558GB@16:21:37Z，非新扫描。下一只读全期提前退出片段与再入场机会损益，未启动，不搜退出网格；独立复核与Git以实际凭证为准。详见docs/DONCHIAN_TIME_STABILITY_20261005.md。
本轮区间/分段未认证稳定优势，不把包含零当证明无alpha；不增加参数/重抽样追显著。退出10保持开发配置，但三个101日段中一段变差，说明统一提前退出的收益来源与状态转移需解释。下一只读全303日可识别提前退出片段，对照已实现成交/目标/实际NAV、等待再入场机会损益及费用，范围不只挑二月/三月；不按结果重编触发条件或宣称交易原因因果。明确符号、各钱包实际资本与状态路径，无法归类UNKNOWN。相比新模型/多参数，先识别过早退出后等待20日新高的机制是否真实，再决定一个有依据的完整单因素实验。403/451条件未变、不再次探测；原采集保护，当前科学任务已经退出。全目标active，本轮progress。

### D069事前：全期提前退出/再入场片段的真实损益机制
HEAD9bfeef0，D068已验收/推送精确一致；主策略未变，原采集两真实PID仍在，36无关WIP保护。全303日十资产四解释只读minute/U、target、fill、fund，逐币串行；U=equity-collateral，gross=全轨迹diff U+已实现+exec；net=gross-fee-exec+fund，不把抵押划转作盈利。事件left归closed minute，raw按minute open对应每日决定；恰UTC边界资金费保持旧分钟归属。逐分钟NAV与累计fee/exec/fund/turnover分别核对、duplicate身份拒绝、全期/资产/月份/state桥合。所有raw旧long/newflat连续片段列出，仅eligible priorbothlong转移命名提前退出，其余UNKNOWN/左右删失。真实库存/卖出/部分成交/首次零库存/raw再入场/实际OPEN分别记录，不把rawflat当已平仓或账户价差当取消退出的可执行收益。全期范围不只挑2/3月、不按亏币删池，0新回放/fit/HPO/QA/API/locked。预算180s/RSS600MB/结果2MB；现有硬共享5GB/swap0/GPU0/D40GB不变，最近物理扫描仍D067时点非当前值。输入/预算/金融桥失败即停止结论，保留实失败；无固定成功收益门槛。独立参考另以端点U与Decimal事件账核区间。结果用于判断成本、提前退出期间价格还是其他联动仓位为主瓶颈，再选择一个有依据的完整单因素实验；普通研究不逐项请示，投资NONE/CASH。

### D069后验选择
D069保存全303日退出/等待诊断完成：四条件各13个真实提前退出片段。BASE/F旧long新flat净+200.16、两版long-45.74、两版flat+2.25，合原+156.67；三月全差-429.45来自XRP，旧long新flat毛-417.93/净-419.17，主要价格恢复参与缺口而非费用。9段改善/4段变差，10次观察再入场等待13–155日、3次右删失，真实减仓/延迟库存保留。原EXIT10研究/EXIT20控制/HOLD_TWO参照保留，投资NONE/CASH、APR不可评价；代理/单位UNKNOWN/时间不稳定保持。0新市场/fit/HPO，主4.653s/RSS587.76MB/共享采样1.249GB/结果646KB，硬5GB/swap0/GPU0。下一仅一个固定的退出后prior10恢复再入场新假设：首次prior20与SMA200不变，必须完整新回放，不按币选规则；尚未实施/运行。独立复核与Git按实际凭证，详见docs/DONCHIAN_EXIT_WAIT_20261005.md。
确认实际ACCOUNT价差而非取消退出因果效应；raw按minute open、事件按closed桶，所有月与state核账通过。新假设只改变退出后的再入场，初入场20/SMA200、退出10与caps保持；退出后等待恢复时prior10高，所有资产同规则，eligibility/gap重置arm，下一日才允许，0额外周期搜索。只有完成因果反例/一个配置4完整账户与独立参考才决定采用，不能拿52片段价差拼成新收益。若提高净同时不制造不可接受risk/成本则保留研究挑战者；否则暂停此有限配方、保持现研究，不追搜索显著。触发来自已见结果，不能标unseen/alpha；原投资NONE/CASH/权限边界与负结果保持。全目标active，本轮progress，下一实际未启动。

### D070事前：一次退出后更快恢复再入场完整检验
HEAD1b3987e，D069已验收推送/核远端，原两采集真实PID存活/8765健康，36无关WIP保留。D069提示13早退段既避跌也错过恢复（BASE/F新flat/旧long净+200.16，三月该组-419.17；XRP全月-429.45），主体价格不是费用，不能按亏币特判。只一个新的COIN变体：初始prior20高+SMA200，held prior10低退出arm，下一日armed flat以prior10高+同SMA200恢复，成功cleararm，eligibility/gap/CASH reset；默认reentry20/旧20不变。新可选正常reset hook接口仅有该方法的direction使用，不复制账户/平台，不改vendor/费用/风险caps/首次entry/exit10/资本/July十币/303日/末退出5次。先独立直接3币因果/window/risk/重置反例，再唯一一个配置的4完整新账户+4独立直接arm/window/金融参考calls，D0674保存control只读不重播。0fit/HPO/新QA/下载/API/locked/密钥/发单；市场owned600MB/1800s/RSS3GB，独立RSS1.5GB，新STATE总800MB，shared5GB/swap0/GPU0/D40GB不变，磁盘运行前实扫。净/gross/fees/exec/fund、实际vol/MDD/gross/net/保证金、交易/turnover、月/币集中与末清分别验收；若无有用净/风险改善保持原配置、暂停该配方，不扫更多周期。结果由已见历史提出，非unseen/独立alpha/稳定APR，代理/资金单位UNKNOWN并列解释不择优。新源码/协议事前绑定，旧证据依Git原版本；实际金融/预算/末清失败明确限结论，不追认成功。

D070准备V1实际closed0，但OWN/diagnostic绑定仍指D067旧辅助路径，root在测试前拒绝来源工件；没有运行测试/市场，不能称绿测或经济失败。原源码/协议/任务完整保留，V2仅纠正own/diagnostic路径与独占run ID，策略/反例/预算不变。新V2协议事前再绑定，不覆盖V1。

D070市场V2误启动：漏显式--pool-id导致default TWO_ASSET先跑，root为落实事前4新账户预算对精确自有PID892223发SIGINT；实际task31b55392..closed failed -2/host1，保存2完整两币与第三前缀，198.99s/42.949MB。没有十币新结果，不升级成功、不删工件。V3独占身份/协议记录误启动SHA并要求明确LIQUIDITY_TEN，策略/成本/caps/日期及已pass测试V2保持，0测试重跑；新完整十币四账户仍待运行。实际消耗和总STATE预算包含误启动。

D070金融V3 task00d746b7..真实failed1：遍历四case后finally报告超过旧2MB小文件限，未保存金融result，不能算验收。原checker f8a753..逐字节保存；当前正常checker仅reentry10报告将重复键无损编码为schemas+rows，并assert精确还原与logicalSHA，不改direct targets/reference/金融数学/容差。新V4绑定/独占金融目录与报告，原市场V3零重跑、测试V2零重跑；market旧checker针由原副本核对，其他针严格不变。失败任务/run bindings与具体阻塞保留，资源包含两次核账。

D070金融V4 task0d90958..failed1：old checker SHA在actual used source检查拒绝，0金融输入/调用。检查发现现有正常source_archives接口已支持精确旧源，无须修改生产绑定逻辑；V5仅plan映射CHECKER到原f8a753副本，正常checker仍684166..（只有无损输出修正），0市场/测试重跑。原V4计划/source/失败和run binding保留；不把拒绝改称成功。

D070金融V5 task057725..failed1：source_archives同映射作用两source map，plan独立旧计划digest仍设new684而archive为f8，before input/calls0。V6仅metadata source_hashes[CHECKER]回绑定旧f8，checker_sha256仍精确current684并显式current_evaluator_source；接口已分别校验原计划来源与当前运行source，没有放宽检查/新源码变化。原V5报告/任务/绑定保留；市场和反例仍零重跑。


## D070后验决定

D070完成唯一退出后prior10恢复再入场完整对照：首次20/SMA200、exit10/十币/连续303日/共享10k与原成本风险保持。四条件净增均-316.18至-335.01USDT；BASE/F净497.16→180.98，毛-280.75、成本增33.61、资金费少1.83；vol8.36→8.48%、MDD7.43→10.24%、换手4.28→6.77。三月未修好且少22.27，一月/四月/六月主要拖累；暂停该固定REENTRY10，保留EXIT10/REENTRY20研究、EXIT20控制/HOLD_TWO参照，投资NONE/CASH、APR NE，不搜再入场网格。四436320分钟账户/末全清、四最终金融/四保存pair通过，3030状态全字段无损输出；误启动2两币+前缀、准备拒绝、金融输出失败和两绑定拒绝均保留，实际8金融calls。主体621.76s/RSS728MB/共享采样1.544GB；实扫27.835GB@18:20:13Z/STATE245.949MB/硬5GBswap0GPU0。下一只固定过去风险下缩8%HOLD_TWO新完整对照以解释当前收益/risk差，尚未启动。独立只读复核/Git以实际后验；详情docs/DONCHIAN_REENTRY10_20261005.md。

主要缺口为价格参与和基准risk差，快恢复此配方未改善而非只多费。下一固定8%过去协方差风险预算HOLD_TWO对照，不高杠杆/后验NAV缩放/新网格/封存或native认证；重新模拟净值与实际风险后判断择时增量。尚未运行，不将四资金/成本解释当独立证据。

## D071事前选择（2026-10-05）
D070快恢复失败已保留，主研究EXIT10/REENTRY20、投资NONE/CASH。单项问题：过去协方差8%预算的HOLD_TWO是否保留更强净收益同时接近择时风险？同两币/303已见开发日/全10k/原fees-friction/F与P/五次末退出，唯一8%而非网格；保存D064 HOLD10控制，十币EXIT10仅不同池的描述参照，禁止称匹配风险alpha。四新市场+四独立核账、一个实质合成fixture、0fit/HPO/API/新QA/封存；STATE400MB、主体1800s/RSS3GB、金融1800s/RSS1.5GB，共享硬5GB。完整重跑，不后验倍乘NAV。正确性/缺失/预算/未清保留后停止；依net/实际vol/MDD/成本判断是否保留低风险参照，不认证长期APR。


## D071后验决定

D071完成固定8%过去协方差预算HOLD_TWO的四个303日完整账户/独立核账/保存配对，末全清。BASE/F净670.63→541.09USDT，实际vol10.49→8.39%、分钟MDD11.23→9.06%、换手2.19→1.74。四条件HOLD8净526.93–632.72，均低于HOLD10但risk下降；同条件十币EXIT10净497.16/vol8.36%/MDD7.43%，HOLD8净更多而回撤更高，币池不同不能认择时alpha或风险匹配。采用HOLD8为低风险收益参照，保留HOLD10控制与十币EXIT10挑战者，快REENTRY10暂停；投资NONE/CASH、长期APR不可评价。主体301.71s/RSS419.72MB/共享采样1.293GB，金融4calls/28.32s，实扫28.006GB@2026-10-04T18:59:20.334608+00:00；硬5GB/swap0/GPU0。下一优先同两币EXIT10完整对照，分离币池与择时贡献，尚未启动；不是永久缩回两币。详情docs/HOLD_RISK8_20261005.md，Git仅按真实后验。

## D072事前选择（2026-10-05）
D071低风险HOLD_TWO net541.09/vol8.39/DD9.06与十币EXIT10 net497.16/vol8.36/DD7.43混有池/策略效应。单项：同BTCETH/303已见日/full10k/原cost/fund/caps/10%过去risk预算，固定EXIT10/REENTRY20 ACTIVE_EQUAL新四账户；与保存HOLD10隔离同池策略，与HOLD8仅不同预算描述，与原十币EXIT10隔离同策略池变化。共同BTCETH信号需一致，不能宣称actualrisk matched。仅金融入口旧len10限制按正常配置放开并拒绝空池，原reference/财务/信号不改。一个直接两币target/reference因果fixture，4市场+4金融，0新配方/fit/HPO/API/QA/locked，STATE400MB、主体1800s/RSS3GB、金融1800s/RSS1.5GB/共享硬5GB。缺失、破产、预算或末清失败保留并停止，不后验缩放NAV、成本、日期、退出次数或风险预算网格；以实际净/毛/cost/月/币/风险决定保留或暂停配方，十币能力不撤销，投资NONE/CASH。


## D072后验决定

D072完成原固定EXIT10/REENTRY20/ACTIVE_EQUAL同两币四个303日账户、四独立金融、16保存账户/12pair与Decimal复核，末全清。BASE/F两币择时净371.34/vol7.10%/MDD4.85%；同两币HOLD10净670.63/vol10.49/MDD11.23，HOLD8净541.09/vol8.39/MDD9.06。择时比HOLD10净少299.29，毛少308.20、成本多11.70、资金改善20.61，主要少价格参与，同时回撤减6.38个百分点。扩池到原十币同规则净增125.83但vol/MDD升1.26/2.58个百分点；BTCETH signal逐日相同，份额/实际risk不同仍披露。保留两币择时为防御对照、十币挑战者、HOLD8风险收益参照/HOLD10控制；纯择时未证明替代主力，投资NONE/CASH、APR不可评价。正常金融入口去旧十币写死且校验非空同序池；无新策略配方/模型/HPO/API/QA/封存。主体283.99s/RSS411.39MB/共享采样1.221GB；实扫28.109GB@2026-10-04T19:29:52.255438+00:00，硬5GB/swap0/GPU0。下一固定50/50持有与择时目标混合、同两币共享账户完整回放检验收益/防御互补，未启动；不拼NAV/搜混合权重/按亏币删池。详情docs/DONCHIAN_TWO_20261005.md，Git仅真实后验。

## D073 运行前决定：固定目标组合，不拼接净值

问题：D072同池择时少价格参与但降低回撤，HOLD8保留收益而回撤较高。一次固定50/50 HOLD10 + EXIT10/REENTRY20 ACTIVE_EQUAL，组件均使用当时可得日线和过去30收益风险缩减，组合各自风险缩减后的目标，在同BTC/ETH、同一个完整10k钱包重跑。不得相加满资本账户NAV或事后调权重；必要硬风险减仓保持，abs.3/gross.6/逐仓1x不变。
对照：保存HOLD10、HOLD8、两币EXIT10，原已见303日连续来源，Bybit标准合约taker5.5bp与既有BASE27/STRESS43、资金F/P均保留。只变目标混合，实际risk不假称匹配。
预算：1配方固定权重，无模型/HPO/下载/API/新QA；4新市场账户+4独立金融，12保存控制账户；STATE总<400MB、主体wall1800s/RSS3GB，仍共享5GB/swap0/GPU0及D40GB。先新合成反例，再完整账户。账本/目标错误或资源达到预算即保留失败并停止。
指标/决定：净损益及gross/fee/exec/fund桥、vol/MDD/turnover/gross/net/抵押物、连续月和资产贡献；只有在所有预定成本与资金单位情景中不被同池既有控制以净收益及vol/MDD共同支配，才保留为有价值挑战者。真实风险不同仍只能描述；能力验收不代表独立alpha/APR或资金授权。没有效果则保留主力和旧负结果，不搜索混合权重。

## D073后验决定

D073固定50/50 HOLD10+EXIT10目标组合真实接入同两币/同一10k钱包，四303日账户及四独立金融/16实际账户12pair/Decimal通过，末付费全清。BASE/F净526.20，相对HOLD8少14.90、gross多10.70但费用/执行多11.55、资金费负担多14.05；实际vol8.39→8.04%、MDD9.06→7.02%，换手1.74→2.60。四条件均净低于HOLD8而vol/MDD也低，原事前不被控制以net/vol/MDD共同支配标准成立，仅保留防御挑战者，不宣称净alpha或风险匹配。vs纯择时净多154.86但risk更高；真实单账户净比两旧账户net算术平均多5.21，不能平均NAV替代回放。HOLD8收益参照/HOLD10控制/EXIT10防御控制/十币挑战者保留，投资NONE/CASH、APR不可评价。新正常薄adapter/runner/独立reference，没有新账户/模型/权重搜索；N能力与多空保持。主体307.88s/RSS420.53MB/共享采样1.291GB/owned161.86MB；实扫28.281GB@2026-10-04T20:09:07.247934+00:00，硬5GB/swap0/GPU0。下一仅保存连续日账本配对/回撤区间/时间稳定性一次诊断，核防御改善集中度与不确定性，未启动；不调混合权重/选币/拼NAV。详情docs/HOLD_EXIT_BLEND_20261005.md。

## D074运行前决定：保存连续日账本的配对回撤与时间依赖

D073固定组合比HOLD8略少收益、较低实际波动与回撤，但November贡献超过全期净收益。只读四条件八份已接受日NAV，复用既有时间诊断和块bootstrap，加入真实endpoint时钟、起始10k及未恢复右删失的每日回撤片段。对照HOLD8；固定三段101日、十月、7/30/60日块（60为主要描述）、每条件每块2000抽样、seed20261005。24k抽样不增加历史，不修正此前选择偏差；实际risk不同，不宣称匹配风险alpha或稳定APR。
预算：0新市场账户/模型/HPO/API/下载/QA，8×303行；主体RSS600MB/wall120s/output1MB，共享5GB/swap0/GPU0与D40GB不变。仅一次保存账本诊断及独立Scalar/Decimal/边界核验；遇日期/身份/现金桥/positiveNAV/资源错误即保留失败停止。原303日已见开发历史、资金单位F/P和跨场所代理条件保持，不搜索混合权重或挑日期。
决定：区间含零或固定段反转则不声称持续净增量；较低历史回撤只保留防御挑战者，不能当稳定独立收益。依据实际结果决定下一主任务，不再机械新增参数实验。

## D074后验决定

D074保存四条件八份303日连续日账本已核验；固定组合相对HOLD8三个101日段BASE/F净增−10.04/+158.98/−163.84USDT，四条件同样反转，7/30/60日块全部12描述区间含零。两者最深日终回撤同为2024-12-16峰至2025-04-08谷：8.30→6.34%，到2025-06-30仍未恢复，真实endpoint持续196日、右删失；分钟MDD仍9.06→7.02%，不能混用。组合降低这段跌幅但未证明缩短最长水下期或稳定净增量；HOLD8收益参照/固定组合防御挑战者/十币能力保留，投资NONE/CASH、长期APR不可评价。0新市场/fit/HPO/API/下载/QA，实际主1.03s/RSS91.65MB/共享采样241.81MB，独立0.85s/RSS82.20MB；实扫沿用D073 28.281GB@2026-10-04T20:09:07.247934+00:00，非新扫描。硬5GB/swap0/GPU0不变。下一优先保存两路公开采集退出后的日志/检查点与有限恢复，随后一次资金费原字段→解析→归一化→结算的有限来源核对，减少F/P双情景的不确定性；已有403/451不重试绕过。先查既有官方归档/定义及同timestamp证据，无法确认则给出具体缺口；不继续混合权重/退出网格。尚未启动。详情docs/HOLD_EXIT_BLEND_TIME_20261005.md。

## D075原采集恢复已验收

D075原两路公开采集再次退出后已保存49.37MB原文件/两闭合库，2256来源文件108.03MB streaming SHA全同；单次原.venv/defaultDB/store/source恢复，新两次实际观测同PID、新session、闭合bars/heartbeat与L1检查点推进，errors[]。断档约public31.3分钟/L130.6分钟，不拼健康时间；原退出UNKNOWN。保存与恢复间boot_id变化已证实，systemd服务本身不维持WSL实例存活是官方限制，闲置退出仅可能机制；新增一个正常Windows隐藏WSL前台客户端，内部sleep仍经原bounded共享5GB，重复调用复用同客户端树，未改系统电源/资源/自动登录，未声称跨Windows重启或72h可靠。N/signed/共享账户与D074负增量结论保持；投资NONE/CASH、APR不可评价。最近实扫采用启动前容量检查，细节见docs/PUBLIC_COLLECTOR_RUNTIME_RESTORE_20261005.md。下一有限资金费来源/解析/归一化/结算核对，未启动，不继续混合权重网格。

## D076运行前：有限资金费链路核对

问题：当前两币HOLD8与固定组合净差中资金费负担是否源于单位缩放/符号/持仓归属/重复入账？仅复用已见303日20份资金源、8已完成钱包；0新市场回放/fit/HPO/API/下载，预期60秒，结果上限5MB；原5GB共享/40GB/风险/locked边界不变。独立CSV/Decimal与实际先前成交重建逐条核对，任何不一致停止，原工件不覆盖。即使通过也只认证条件链路；官方archive单位及结算/publication缺证不因数值量级猜定。已有403/451不重试绕过。若无错误，停止本轮单位调查；继续保留HOLD8与防御组合，投资NONE/CASH，不跑权重/退出网格。


## D076资金费链路已验收

D076已独立读20份BTC/ETH原资金费归档、1818原事件，与HOLD8/固定组合8保存钱包14544条资金费/真实先前成交逐项核对；缩放一次、ms原clock、符号、event前仓位与严格过去mark时间/总资金费及净桥一致。另按BUY/SELL gross量/首持仓clock重建quantity，10k+成交cash_delta+资金费重建8末NAV，未将抵押物记利润。未发现错误，原账户/策略不改；单位物理定义/官方结算发布clock仍UNCONFIRMED，source校验与条件账本通过不能升级原生/单位认证，已有403/451不重试。BASE/F组合比HOLD8多付14.05USDT资金费，四情景净仍低，非重复入账或符号问题。保留HOLD8收益参照/组合防御挑战者，投资NONE/CASH、长期APR不可评价。主0.817s/RSS75.37MB，独立0.351s/RSS29.74MB；0新回放/fit/HPO/API/下载，原5GB/swap0/GPU0/40GB保持。停止无新来源证据的单位调查；下一先核对同窗BTC/ETH Spot源与现有库存/收到资产扣费入口，齐全后以真实产品价格和完整本金做一组有限Spot/永续HOLD对照，判断资金费负担与额外现货成本/基差影响，不把旧永续账本删除资金费改叫现货。尚未启动。

## D077运行前：真实现货/永续产品对照

原资金费条件链路无错，HOLD8资金费BASE/F负担91.87USDT，现货可能避开该现金流但交易费用更高，产品价格与库存不同。唯一新配方：同BTCETH/303已见日/10k/.08过去风险/abs.3 gross.6，现货自身过去日close定权、原正常Spot账户收到资产扣费；2实际现货36/52bp情景配已保存4永续27/43情景，0新下载/API/fit/HPO。正常terminal_exit_minutes事前=5，各自原窗口内有限5次，不免费清残仓、不延长后追认。显式原源Jan2024..Jun2025共36文件身份核、244预热，锁正文不读；最大200MB新STATE/1800秒/共享5GB/swap0/GPU0/D40不变。全分钟保存成交重建净值/库存/实际风险，任何数据/钱/超caps问题失败或有限诊断。产品差不能全归因funding，不宣称风险匹配/原生/稳定APR。完成后按经济/实际risk是否共同占优决定产品研究方向，不选P/F收益更高单位。


## D077真实产品对照已验收

D077正常Spot账户接入RECEIVED_ASSET及显式末5分钟有限退出，QUOTE默认原三夹具全字段实际差0、N=3共享钱包6实成交、最终8必要回归通过；旧AST入口不作为新活动依赖，旧报告按Git保留。36原源/244预热/303已见日、2真实Spot钱包与4保存永续完成产品比较，独立Decimal核714成交、872640分钟/606日现金库存NAV与gross/net，无实际close观测caps越界；仍非分钟强制减仓能力或intraminute风险认证。Spot基础marked净633.09，vs永续F541.09增92.00，vsP632.72仅增0.37；压力618.40，vsF增91.47/vsP减0.018，产品优势依赖未确认资金费单位，不能全归因资金费或认定稳健优胜。Spot实际vol8.469%、日DD8.158%/分钟DD8.926%，残仓0.00104/0.000464USDT真实保留，liquidated return NE，不免费清零。采用正常Spot/N/费用接口、保留SpotHOLD8产品参照，永续HOLD8/固定组合/十币能力保持；投资NONE/CASH、长期APR NE。主87.39s/RSS803.39MB/共享实采1.303GB、STATE59.15MB，实际整盘28.496GB@2026-10-05T03:10:44.713535+00:00（创建本轮工件前），5GB/swap0/GPU0/40GB与源锁资金边界不变。下一主任务复用现有固定50/50 HOLD10+EXIT10规则，在同Spot正常钱包/同输入/完整资本完成一项防御组合对照，隔离永续资金费单位不确定性之后检验防御收益/risk，不搜索权重或退出周期；尚未启动。

## D078现货防御组合已验收

D078同Spot固定50/50 HOLD10+EXIT10/REENTRY20实际2共享10k钱包完成303已见日；缓存SHA复用不复制，正常recipe/Spot身份保留原mathID，无新模型/参数搜索。基础组合marked净630.73 vs HOLD8 633.09少2.37，gross增13.14而fee/exec多15.51；压力净609.23 vs618.40少9.18。实际日vol8.118% vs8.469%，分钟DD6.823% vs8.926%，turnover2.593 vs1.731，峰gross27.664%，全部close caps内；不是同风险alpha（原组件预算10% vs HOLD8 8%）。BTC净633.30/ETH净−2.57；101日差−4.01/+165.79/−164.14，不宣称时间稳定。独立核674成交/872640分钟/606日，606目标混合与过去cov/未来扰动通过；残仓0.000097/0.000804USDT保留，liquidated return NE。保留SpotHOLD8收益参照和Spot固定防御挑战者，投资NONE/CASH/APR NE。主79.38s/RSS756.94MB/采样共享1.253GB，新STATE26.90MB；整盘实扫28.568GB@2026-10-05T03:34:50.584997Z（新工件前）。旧protocol问题/parent文案误带D077，原件保存并在结果前补erratum，执行配方/预算未变。下一一项50USDT主动再平衡不交易区间完整新回放，保留信号退出/终止/风险强制减仓与caps；不能删旧成本保留旧毛收益，当前尚未启动。原N/signed/现金/源锁/资金/资源边界不变。

## D079主动调仓门槛能力与负增量已验收

D079正常Spot主动调仓门槛默认0，显式50只允许同信号/资格且组件风险target未下降的主动调整；原入场/信号变化/必要减仓/实际caps/终止/已开始partial保持。真实2共享10k/303日账户，606原目标值不变；每账户246成交/246拒主动goal，独立核492成交/872640分钟/606日及全部拒单/无费用桥。基础净626.52 vs原组合630.73少4.21，省费用执行2.26而gross少6.47；压力净605.60 vs609.23少3.62，省3.26而gross少6.88。日vol8.077%/分钟DD6.676%略降，但事前双成本net提升标准失败，不采用BAND50。保留原Spot防御组合/HOLD8收益参照和门槛默认关闭能力，投资NONE/CASH/APR NE。原失败fixture顺序14pass/1fail与旧字节保留，修正仅测试身份后15pass，账户源未变，QUOTE/received默认逐字段同旧Git。残仓0.000486/0.000299USDT保留，liquidated return NE；无分钟自动漂移减仓/原生/独立OOS认证。主79.41s/RSS767.59MB/共享采样1.252GB，新STATE26.86MB，整盘实扫28.608GB@2026-10-05T04:01:56.827989Z（工件前）。停止门槛网格；reopen需新的具体成本或执行证据。下一有限4h信号Donchian挑战者，沿用同Spot价格/成本/共享本金与过去日协方差，比较现日线防御组合，回答信号节奏是否为主要阻碍；只一个固定配方/两成本，无新池/下载/HPO，尚未启动。原N/signed/风险caps/资源/锁数据/资金边界保持，两采集验收时实际存活。

## D080四小时信号与日风险完成、当前配方不采用

D080正常N资产接口新增显式240min信号/独立200日资格与过去30日日风险，原1440默认与Git72e1a8b逐字段一致；HOLD10日target前向携带，EXIT10/R20原hook+COIN退出在4h上，整组合4h刷新，一个共享10k钱包。两成本303日真实回放：基础net642.13 vs日组合630.73多11.40，压力562.38 vs609.23少46.84；gross多141.34/139.68而费用执行多129.94/186.53，分钟DD7.997%/8.143%高于6.823%/6.862%，日vol7.849%/7.844%稍低。交易899/895 vs337，换手9.814/9.765 vs2.593/2.589；不采用4h当前配方，保留日线防御组合/HOLD8，投资NONE/CASH。约78%新总成本在信号component变化，重复intraday同target成本仅14.65/20.99（约8%），不是主要压力缺口；40完整component片段median96h/无<24h，不编造高频whipsaw，也不把片段当独立账户。3636目标scalar信号/centered日cov/手mix误差<6e-17；4008缓存4hOHLCV独立归约、1794成交Decimal/872640分钟/606日核账通过。旧测试7pass当时2581源码/当前ac19的两描述字段修订分别绑定，当前reference实跑通过，不冒用旧绿测。正残仓0.001065/0.000420USDT保留，liquidated return NE；缺组件资格不同整体STOP，未证明native/连续分钟风险/独立OOS/APR。主69.65s/RSS740.08MB/共享采样1.192GB，新owned27.43MB；整盘28.651GB@2026-10-05T04:26:47.474579Z（工件前）。本版不支持更快必然更好或重复调仓为主要失败机制。下一只一个COIN日SMA200宏观入场过滤对照，保留4h通道20/exit10/执行、过去日risk/成本/caps；比较本次4h控制，检验短趋势入场与费用失效，不改退出减仓、不搜周期网格；尚未实施/启动。暂停未过滤4h采用，reopen仅该明确macrofilter新证据或独立窗口，不永久删除方向。N/signed/十币/现货库存及40GB/5GB/swap0/GPU0/locked资金权限保持。

## D081

D081日SMA200替换4hSMA200入场过滤（非双SMA AND），退出/risk/4h执行/本金/cost保持；两303日账户净350.81/281.85USDT，比原4h少291.31/280.53，省成本18.58/26.75却毛损益少309.89/307.28；分钟DD升至8.908%/9.118%，不采用。原日线防御组合/HOLD8保留，投资NONE/CASH；新配方不是低成本改善。当前工作流已按用户采纳收拢为单状态/薄证据引用与复用收尾，旧结果按Git/工件保留。 停止在同303日上继续SMA过滤或周期网格；下一先核授权且未参与选择的共同Spot证据窗口/数据角色，只读来源与实验登记，不解析locked、不先下载或称unseen。用独立证据可得性决定两研究参照的有限验证或继续前向采集；未启动新市场回放。4h配方暂停，reopen需明确新信息机制或合法独立证据。

## D082_BLEND

D082复用已接受May2025-Feb2026两币月源，完整200日预热；Dec2025-Feb2026为已见90日开发验证。固定HOLD8净-525.58/-530.83USDT，日线防御组合净-330.70/-333.92，少亏194.88/196.91、分钟DD约9.00%→5.71%；但两者均落后同USDT资本CASH0。两币Donchian90日零入场/零敞口，防御组合只是半份HOLD10，降低暴露不是新增alpha。保留研究参照、投资NONE/CASH；不拼接此前303日钱包。 不在当前窗口继续调风险/退出/周期。下一先核现有永续资金费单位、原始官方来源与解析链，排除signed经济比较的成本歧义；不改旧报告、不读取locked、不新增下载或发单。如单位正确则保留其原限制，再选择机制不同的有限策略验证或真实前向证据。4h/宏观SMA过滤继续暂停，reopen需新信息机制或合法独立证据；多空/N币/模型能力保留。

## D083_ORIGINAL

D083在相同10k本金/费用/执行/日期下完成半份HOLD10组件的四个新钱包。303日完整组合相对半HOLD净多230.25/217.43USDT，但实际日波动5.30%→8.12%、分钟DD5.65%→6.82%；11月增量333.48/330.97，其余月份合计-103.23/-113.53，不能证明稳定择时alpha。另90日组合与半HOLD逐笔成交、全部分钟NAV完全相同，净-330.70/-333.92USDT，Donchian零参与。保留半HOLD诊断控制/日线组合防御参照/HOLD8，半HOLD不替换主力；投资NONE/CASH，长期APR不可评价。 下一主任务只验证HOLD腿过去日线SMA200趋势门控：低于过去趋势时转现金、恢复趋势时允许持有，复用现有正常SMA/风险/Spot账本，固定一个规则，完整原303与后90日同成本配对，不搜索周期/阈值/币种或缩放旧NAV。主要瓶颈是HOLD下跌敞口和收益状态集中，费用不是本轮主要解释；该对照检验是否能减少下跌损失而不过度错失恢复。新协议在运行前登记取舍；当前未启动。4h/宏观Donchian过滤/重入网格继续暂停，reopen需不同信息机制或合法独立证据；RSI2旧失败不机械重跑。资金费链D076已通过，不重复审计；物理单位UNKNOWN，仅新官方归档单位定义或合法同事件证据可重开，不重试既有403/451。多空/N资产/ML能力保留。

## D084_ORIGINAL

D084完成唯一HOLD腿过去close>SMA200门控的四个真实Spot钱包。原303日净330.09/307.83USDT，比原日线组合少300.64/301.40；日vol约8.12%→6.33%、分钟DD约6.82%→4.64%（stress4.75%）。后90日HOLD及Donchian皆零目标，真实全程CASH：净/fee/turnover/vol/DD均0，比原组合少亏330.70/333.92，但这不是新增价格alpha。事前两窗联合净改善标准未通过，不替换日线组合/HOLD8；门控能力保留、固定配方暂停，投资NONE/CASH。两路采集在WSL进程丢失后已保存三件套并单次恢复，新会话/断档真实记录，两次观测推进，非有效天认证。 停止当前两币SMA/退出/门槛网格。下一主任务评估Spot资产分散：先核已有永续池与Spot产品身份差异（如1000PEPE不能直接充作PEPE），按评价前官方Spot流动性/上市与200日预热确定约10币候选池；优先同已见Dec2025-Feb2026的90日窗口、原日线组合与HOLD8固定规则、同资本/cost/caps和BTCETH控制。只取必要daily预热与评分分钟，不取aggTrades/LOB；数据增长预估最多1GB、含临时预留整盘须低于32GB，失败就保留缺口/减少批次，不扩权限。来源可用后同单账户完整回放，不合并独立NAV；目前尚未启动。它检验分散能否改善单一BTCETH暴露及机会集中，优先于再调已否定时序门槛；不是保证正收益。HOLD200门控重开须不同信息机制或合法独立证据，不试周期网格；4h/宏观Donchian/RSI2固定失败继续按原reopen条件暂停。资金费单位UNKNOWN，D076链不重复审计，不重试403/451；多空/N币/ML能力保持。


## D085 — shared direction baseline, 2026-10-05

D085已完成一个共享10币XGBoost三分类fit和20配对账户（May–Jun2025共61日、资本10k）。BASE27/RAW_AS_PERCENT：双向净-944.78、同模型多头-270.34、HOLD 164.49、DonchianEXIT10 -224.35USDT；双向SHORT净-430.37，vol9.40%/DD11.20%高于同模型多头7.46%/7.51%。四成本/资金费口径均未通过任一净/DD/风险调整改善；固定配方暂停，不作为研究主力或投资候选。45日BULL、16日SIDEWAYS、0日BEAR/CRASH；CASH预测0，不称已学会现金或稳定熊市short alpha。账户有真实空头成交、部分成交与资金费；实际残仓保留，净值为marked，未清仓账户liquidated return NOT_EVALUABLE。首次终值断言与重复registry启动失败保留，原唯一模型及首账户复用、概率/预测完全相同；独立全部分钟NAV/钱包/费用/funding验收通过。

采用：真实signed共享账户/共享三分类能力；不采用本次固定预测配方。瓶颈为信号/现金决策与熊市覆盖，费用不是主亏损源。下一Phase2固定clustering条件对照，先核足够熊市覆盖；不永久删除short，不重建账户，不开展模型网格。资金费两解释、跨场所代理和残仓仅marked均阻止投资晋级；完整对照和数字见D085报告及结构化验收。


## D086 — train-only regime gate, 2026-10-05

D086连续Mar–Jun2025共122日、10币同资本10k，完成16账户。BASE27/RAW_AS_PERCENT：原双向净-921.57，GMM门控净-48.06USDT；原毛损益-646.23、费用/点差/滑点合计275.37；门控毛损益1.03、成本49.10，原信号亏损与门控后成本吞噬分别成立。门控SHORT净-48.06，相对BEAR桶SHORT净-63.88。原/门控DD 12.03%/2.13%，vol 9.80%/4.27%，实际平均gross 16.46%/2.12%。HOLD净140.16、DonchianEXIT10净-353.58。四成本/资金费解释配对检验，门控保留为防御研究组件，未证明short alpha，也未达到投资资格。GMM相对BULL0/BEAR32/SIDEWAYS90/CRASH0；BEAR中心20d -5.18%但SMA200距离+22.05%，非绝对熊市真值。90日零目标不等于全部实际平仓，分钟gross/净仓与真实残仓保留。方向模型无重拟合，新GMM/Scaler各1；相关测试各2拟合；旧概率和三方向targets精确golden及独立目标/NAV/钱包复算通过。

采用：正常状态门控能力；保留GMM防御性研究组件；暂停其熊市short-alpha配方和原argmax方向配方。reopen：不同可得信息或状态机制在固定成本下产生可信净short增量/风险收益改善，并补足独立证据；不以换seed/调后验阈值重跑。投资候选仍NONE/CASH；元标签未运行，锁集未动，proxy与未知funding单位仍阻止晋级。

下一有限主任务是同一固定XGB的绝对过去趋势门控对照：用已有BTC SMA200/20d状态替代相对GMM状态，保留同账户、日期、成本和caps，最多新增4个账户、零direction fit/零搜索。本轮GMM全窗BULL=0，无法分辨过滤错误牛市空头与长期排除全部多头；此对照优先排除状态语义/覆盖错误，之后再决定是否值得做共享execute/reject meta-labeling。状态不是收益真值，过去BEAR桶中的short也不保证赚钱，不据结果改规则。


## D087 — direction regime comparison, 2026-10-05

D087固定既有过去BTC SMA200/20d状态，新增4个连续122日10币共享账户；16个D086对照按报告/全部artifacts SHA复用，不重跑或拼接钱包。BASE27/RAW_AS_PERCENT：固定趋势门控净-259.85，GMM净-48.06，未门控净-921.57USDT。新配方毛-155.36，费用/执行104.46，funding -0.03；LONG贡献-303.11、SHORT贡献43.26，BEAR桶SHORT -19.90，归因不是独立short账户收益。固定/GMM分钟DD 5.20%/2.13%，实际vol 5.44%/4.27%，平均gross 4.41%/2.12%。HOLD 140.16、Donchian -353.58；固定状态BULL56/BEAR25/SIDEWAYS41/CRASH0。预先配对决定 PAUSE_THIS_FIXED_RECIPE；新4情景SHORT均正=True，没有新unseen证据。所有新fit=0，2项新状态回归fit=0；全1220行预测及旧3方向目标精确golden，独立新目标/分钟NAV/钱包验收通过。

采用门控能力，保留GMM防御参照；本固定双向趋势配方 PAUSE_THIS_FIXED_RECIPE，未晋级投资。有成本后正SHORT归因只支持下一独立short反事实，不证明可投资alpha。暂停配方reopen需不同可得机制带来固定成本下可复现净/风险改善；无独立证据不晋级。投资候选仍NONE/CASH；UNKNOWN资金费两解释与proxy、真实残仓保留。

下一有限主任务：同固定BTC趋势规则/同XGB预测仅切SHORT_ONLY，对照当前LONG_SHORT/GMM/HOLD/CASH。新增4个真实共享账户、零拟合/零搜索，判断组合内正SHORT贡献能否成为独立、完整资本、真实风险与成本后的净增量。只改变方向mask，既有必要风控、费用、容量和残仓规则不变；不能把LONG_SHORT中的SHORT贡献当作独立收益。


## D088 — direction regime comparison, 2026-10-05

D088仅改变同一固定趋势门控的方向mask为SHORT_ONLY，新增4个完整122日10币共享10k账户，零拟合/搜索；20个旧账户按SHA复用，未拼接钱包。BASE27/RAW_AS_PERCENT净43.56USDT（完整资本0.4356%），原固定LONG_SHORT净-259.85，GMM净-48.06，HOLD净140.16。SHORT_ONLY毛75.42、费用/执行31.87、资金费0.01；LONG=0且独立核每分钟q<=0，新4账户实付平仓/残仓0。分钟DD 1.95%、实际vol 2.90%、平均gross 1.62%；caps相同不代表与HOLD实际风险相同。四成本/资金费解释净+24.50至+45.03，BEAR桶均负（BASE/PCT -20.86），SIDEWAYS +65.95、BULL -1.52。每情景9个零目标平空请求FIVE_ATTEMPTS_EXPIRED，正收益日仅16/122，top5正日占正日利润69.7%；状态日归因不是因果alpha。全1220预测和三方向默认目标golden精确一致；独立资金/NAV/目标核验及只读复核通过，new4/reused20范围分开。

保留SHORT_ONLY为研究挑战者（RETAIN_FOR_RESEARCH_NOT_INVESTMENT），暂停固定LONG_SHORT配方，能力保留。投资候选NONE/CASH、长期APR NOT_EVALUABLE；已见开发、跨场所代理、未知资金费单位和退出超时仍限制声明，不宣称稳定熊市alpha。暂停方向reopen需不同可得机制在固定成本下出现可信净/风险改善并补独立证据，不靠无限调参。

下一有限主任务：同一SHORT_ONLY信号的零目标平仓持续重试对照，检验5次过期后继续留空是否影响小幅正收益。先固定协议，仅改变该退出重试机制；最多新增4个完整账户，零模型拟合/搜索。保留费用、成交容量、必要风控、资本及caps，用相关平仓反例和旧默认golden复核，不删除旧交易/成本或免费平仓。若退出修正后无增量则暂停配方；正结果也只保留研究，独立/native资格仍未满足。


## D089 — direction regime comparison, 2026-10-05

D089只改变日常零目标的平仓重试，4个新完整122日/10币共享10k账户，24旧控制逐artifacts SHA复用；zero fit/search。BASE27/PCT净-22.69（旧5次过期43.56），毛9.59、费用/执行32.29、资金费0.01USDT；旧/新DD 1.95%/1.98%，vol 2.90%/2.65%，平均gross 1.62%/1.50%。四解释净范围-41.85至-21.50；新BEAR桶SHORT -20.85。零目标仍持仓的资产分钟旧13059/新210，新超五分钟真实平仓腿86；新零目标平空5次过期0，全部新q<=0/LONG=0；新4账户实付清仓=True。容量/费用/风险/终止覆盖不变；改动前默认完整账户golden、4项实际相关回归以及每分钟独立NAV/钱包/目标复核通过。第一次2项合成测试失败已保留，修正风险例未满仓及旧stub缺N资产关键字后4项通过；未按收益修改验收。

采用可选持续平仓重试能力，不因它比过期退出少赚钱而退回旧机制；短策略决定 PAUSE_THIS_FIXED_RECIPE。已见开发/跨场所代理/资金费UNKNOWN及小样本收益集中保留，投资资格NONE/CASH、长期APR NOT_EVALUABLE。旧延迟退出结果不篡改，状态和现金成交归因仅关联描述，含风险/终止替代可能，不能作因果alpha。

下一有限研究选择：共享execute/reject元标签，对既有固定双向公开信号作成本可交易性过滤；主问题是原方向模型未预测CASH和价格信号净收益弱，而非继续改变执行以挑利润。先核已登记公开信号完整语义与数据成熟，再预登记一个配置、共同时间切分、成本一致的完整账户对照。元模型只用闭合特征与固定公开signal，若使用方向模型概率须时间OOF/out-of-fit，不把训练内概率当独立链路；所有标签先成熟，已见评价仍是开发。不无限扫本XGB/state阈值；现固定多空配方暂停，reopen需不同可得预测机制带来真实净/风险改善并补独立证据。


## D090 冻结公开意图与有限meta结论

D090固定公开SMA50/200原双向意图+一个共享execute/reject拟合；4原SMA账户均在103804分钟逐仓清算要求处停止，全122日净收益NOT_EVALUABLE，不补零。4过滤账户完整122日，净-84.26至-14.44USDT，BASE/PCT净-21.06、毛88.12、成本109.25、资金费0.07，DD5.48%、vol8.17%；同口径HOLD净140.16。原fit1次，恢复阶段fit0；最终恢复只新增2账户、10账本按SHA复用，整个实验实际独立账户12，未拼钱包。V1完整性断言错误和V2工件250MB停止保留，V3在同预算仅补缺两项。固定intent独立窗口参考、目标/每分钟NAV/资金费/钱包及停止参考通过；停止mark只核声明价格。

暂停本拟合配方与旧固定XGB门控配方，保留模型、多空和退出能力；本轮没有合格投资方案NONE/CASH。旧XGB负结果不能外推short无alpha，更不能外推所有公开CTA。重新开放ML需经典benchmark明确且提出可证伪的净/风险增量假设。

当前主线转为公开、冻结参数、零训练经典CTA leaderboard：真calendar12m TSMOM、SMA200 signed trend、Donchian20/10与20/10+55/20+12m等权forecast。各币独立信号，past30 inverse-vol和原signed covariance缩放进入同一个10币/10k账户。同Mar–Jun122日、两成本与两资金费解释，LONG_ONLY/SHORT_ONLY/LONG_SHORT/CASH/HOLD，最多56真实账户，零拟合/零搜参。有预热不足则UNKNOWN，不冒充短窗12m；本金/caps/逐仓1x/持续平仓/风险停止保持。先验证short增量与状态机制，再允许ML挑战。


## D091 冻结公开CTA leaderboard

D091公开、冻结参数、零训练经典CTA：4family×3方向+共同实际CASH/HOLD，2成本×2未知funding单位，共56真实共享账户；40完整122日、16显式停止前缀。完整资本10k/10币，无钱包拼接；TSMOM12M（仅多/仅空/多空）：418.58/NOT_EVALUABLE_STOPPED/NOT_EVALUABLE_STOPPED USDT；SMA200_SIGNED（仅多/仅空/多空）：96.09/NOT_EVALUABLE_STOPPED/NOT_EVALUABLE_STOPPED USDT；DONCHIAN20_10（仅多/仅空/多空）：-225.91/62.50/-22.71 USDT；DC_TSMOM_ENSEMBLE（仅多/仅空/多空）：68.00/-67.65/183.44 USDT。BASE/PCT描述排名首位TSMOM12M/LONG_ONLY净418.58。每币past30 inversevol+signedcov仅scale-down，原caps/逐仓1x/持续零目标平仓/真实成本和风险停止保持。仅空与多空short腿不等价，配对表同时报告DD、实际vol和成本，状态归因非因果证明。ensemble多空BASE/PCT真实SHORT净贡献120.72，其中过去SIDEWAYS+505.20、BEAR-220.01、BULL-164.47；Donchian仅空同样主要赚在过去SIDEWAYS。状态为滞后的BTC描述标签，不能包装为已证明完整crypto熊市short盈利。

保留全部4冻结规则与共同CASH/HOLD为公开benchmark；当前冻结CTA研究参照 TSMOM12M/LONG_ONLY（仅已见开发，按四情景最差净收益作描述选择，未匹配全部实际风险、未晋级投资）。投资NONE/CASH；模型配方继续暂停；没有把旧XGB失败外推short无alpha。缺少完整独立周期/native规则/已确认funding单位，长期APR NOT_EVALUABLE。

下一有限主任务：优先验证经典趋势策略的单腿退出风险，而非恢复ML门控。TSMOM12M慢速空头在WIF反弹中触发逐仓权益/维持保证金停止，组合NAV仍为正；这阻止全窗口评价，不能当作short无alpha或总资本破产。复用已登记原Turtle ATR20/2ATR保护逻辑，给固定TSMOM12M多空配方只增加一个过去信息保护退出因素；先核其实际成交、延迟、持仓状态和独立反例，再跑两成本×两funding解释至多4个新共享账户。当前四个原多空停止账本按SHA复用作为停止前共同前缀对照，完整结果另与HOLD/TSMOM仅多比较；不得把不同终点直接相减。若仍停止或真实成本后无经济/风险改善则暂停这个保护配方，不搜止损倍数；保持原caps、逐仓1x、不加保证金，不改旧证据。这项实验先排除慢信号与逐仓风险不兼容的重要假设；完整独立周期与原生规则仍是后续证据缺口。ML重新开放条件为稳定公开benchmark上有明确可证伪的净/风险增量假设；其余停止家族reopen需过去信息风险退出机制或不同完整窗口对照。


## 用户授权资源扩容 2026-10-05

用户2026-10-05明确扩容已应用：共享8GB RAM/CPU多核/D150GB，swap0/GPU0；coin.slice统一父组8GB覆盖新研究与原采集5GB子组。18逻辑CPU affinity/no quota，新任务默认4线程并尊重冻结2线程；后续并行账户从2路起步，预算与结果仍按实际记录。150GB/120预警/135停止新增/15预留的新实扫32.135GB；两collector同PID/起点保持，8765显示全项目父组与新实扫。D091历史5GB/40GB、全部56账户/负结果/停止/参数保持；本模块0账户/拟合/市场下载/发单，资本、风险、GPU、密钥和锁集权限不扩。已完成6项相关边界/实际cgroup测试与独立只读层级复核；不为预算变更重跑金融账户。证据：`reports/RESOURCE_POLICY_ACCEPTED_20261005_V1.json`。


## D092固定初始2ATR保护退出

D092固定2ATR保护+次月冷却，4账户/4完整；BASE/PCT净-423.50 USDT，多头-149.40、空头-274.10。停止与成本敏感性见报告。暂停该固定2ATR+次月冷却配方；能力保留，不搜倍数。TSMOM12M/LONG_ONLY仍为稳定冻结开发参照；qualified investment NONE/CASH，长期APR NOT_EVALUABLE。

下一有限问题：保留TSMOM仅多/公开ensemble参照，核已有未封存数据能否支持另一完整窗口与12m预热；优先扩大周期证据而非救此止损配方。


## D093固定Donchian303日连续对照

D093同10币303日连续共享资本，20账户/20完整/0停止。BASE/PCT Donchian LO/SO/LS净927.09/-182.93/924.38 USDT。保留固定Donchian为公开方向benchmark；该303日配方未达到稳健多空投资晋级条件。 BASE/PCT仅多净927.09、DD6.96%/vol8.53%，HOLD净573.08、DD12.99%/vol10.44%；多空净924.38、DD6.62%/vol10.27%，费用加执行140.81（仅多65.52）。多空真实SHORT累计-205.97：SEP_NOV -829.34、DEC_FEB +487.02、MAR_JUN +136.36；空头能在部分下跌段赚钱，但前段损失占主导。四情景LS-LO仅1正/3负，且每个LS空头腿负；唯一正增量伴随LONG贡献变化，不能称short alpha。SHORT毛价格-135.55、手续费加执行70.81、资金费+0.40，交易成本加剧已为负的毛收益。整个多空账户DOGE贡献477.72、WIF308.05，收益集中度仍需另一个时期核验；这些是同一钱包的逐币归因，不是独立账户收益相加。多空终值仍有121.62名义残仓，HOLD173.12，都是marked NAV而非已付费全平收益；仅多已真实付费平仓。过去BTC状态不是未来牛熊标签，不能直接拿事后日期做交易gate。 Donchian20/10仅多为303日透明开发参照；TSMOM12M/LONG_ONLY仍保留原122日参照，不同起点与窗口不能直接排名或拼收益，投资NONE/CASH、长期APR NOT_EVALUABLE。

下一有限任务：复用现有公开20/10、55/20通道，固定等权平均forecast的双周期趋势挑战者；沿用303日价格、账户和成本，与现有20/10对照，只改变趋势速度组合，不搜索权重或止损。假设是减少快速空头在上涨/反弹阶段的错误持仓，同时保留下跌阶段捕捉能力；若四情景净增量和实际风险不稳，保留仅多/空仓开发参照、暂停该组合配方。short主力reopen需这一明确新机制或另一个有效周期的真实净/风险证据，不能由本窗失败永久删除short能力。


## D094运行前问题与有限预算

D093空头SEP_NOV净-829.34、后两段+487.02/+136.36，毛价格损失不能只靠费用修复。只改变一个因素：公开20/10+55/20固定等权forecast，保留同303日已见10币、共享10k/caps/1x和两成本/未知资金费解释。12新完整方向账户，2个并行成本任务各最多2400秒/1.8GB RSS/1.2GB工件，8 CASH/HOLD按SHA和全窗口targets复用。净损益、SHORT贡献、vol/DD、成本、敞口、连续预定日期段和集中度为指标；不搜索权重、止损或事后状态gate。仅多/现金现有开发参照保留；双周期多空晋级研发挑战者要求四情景净改善且实际vol/DD不劣于原多空，否则暂停此配方。投资资格始终NONE/CASH。


## D094双周期实际结果与决定

D094一个固定20/10+55/20等权forecast配方，12新方向账户/12完整，8控制REUSED。BASE/PCT LO/SO/LS净879.98/-174.74/1058.97 USDT；LS对原20/10四情景净变化126.09/134.59/145.02/150.52。双周期多空未满足四情景净/实际风险晋级条件，暂停该配方晋级，保留公共benchmark及双向能力。 BASE/PCT双周期多空净1058.97、vol9.76%/DD7.04%，原多空924.38、vol10.27%/DD6.62%；成本140.81降112.39。四情景同向净改善126.09..150.52、vol约降0.51百分点，但DD升0.38..0.52百分点，事前风险不劣条件未通过。多空LONG1212.21、SHORT-153.24；比原多空LONG改善81.86、SHORT改善52.73，两者共同贡献净增量134.59，不能全部归为空头alpha。自身LS相对自身LO四情景均正，但SHORT累计仍负，signedcov/持仓竞争改变LONG暴露。连续日期段SHORT为-708.58/+708.73/-153.39，原20/10为-829.34/+487.02/+136.36；早段损失减轻、中段捕捉改善，但最后122日空头从盈利转亏，多空整段从-26.15恶化到-224.63。合计改善不代表各阶段稳定改善，不能用事后日期拼接赢家。双周期仅多879.98、DD6.60%/vol8.47%，原仅多927.09、DD6.96%/vol8.53%；这是收益与风险取舍，未出现所有指标占优的配方。多空残仓186.86，HOLD173.12，均为marked NAV；两种仅多已付费平仓。 新旧均为303日已见跨场所代理；价格、资金费未知解释、用户费用、共享10k、caps/1x保持。双周期多空保留为较高净收益的开发比较工件，不声称已通过晋级；原仅多保持稳定较低波动参照。投资NONE/CASH、长期APR NOT_EVALUABLE。

下一有限主任务：核对现有授权Binance funding原始来源、解析链与官方单位/结算时钟，争取把目前两UNKNOWN情景转为有来源支持的自洽资金费口径；不根据更高盈利选择解释，不改写D093/D094历史结果。若无法确认，仅保留UNKNOWN和有限筛选；之后再依据固定公开benchmark差距选择新机制或独立合法窗口。固定双周期配方reopen需另一个有效周期或新失效机制证据，不搜索period/权重救本窗。


## D095运行前：SMA200同窗公开对照

D095运行前：D094之后核对发现资金费来源链已由D076审核，官方单位/时钟仍UNCONFIRMED，403/451不重试；无新官方证据就不重复调查。主问题改为补齐已有公开SMA200 signed同303日方向证据，原122日HALT与负结果保持。现有日线sign/200窗口/past30 inversevol/signedcov、10币、10k/abs30/gross60/逐仓1x/费用和两UNKNOWN资金费解释全不变；12新账户或显式HALT，8 CASH/HOLD经SHA+全窗口target golden复用。两个成本任务并行，各2线程、2400秒/1.8GB RSS/0.5GB工件，总新工件预算1GB，运行前给活采集旧36GB intake留80MB余量。原3规则回归按完全相同源/XML复用，新账户逐一独立财务与ordered-target验收。仅当完整方向在四情景净超过同方向20/10及HOLD且实际vol/DD均不高于两者才保留为研发挑战者；不满足则只保留benchmark/能力，投资NONE/CASH。零fit/搜参/下载。


## D095结果与自主决定

D095复用已有SMA200 signed，完成同303日12个新方向账户（完整4、停止8），另8现金/HOLD控制严格REUSED，0训练/搜参/下载。LONG_ONLY净126.32；价格毛损益220.75，费用+执行93.61，资金费-0.82，vol/DD9.49%/10.39%；SHORT_ONLY净NOT_EVALUABLE；停止前净-190.55，不是完整收益；停止见证{"event_us": 1747031040000000, "phase": "MARK_OBSERVATION", "symbol": "WIFUSDT", "isolated_equity": 0.5883377932590951, "maintenance_margin": 0.5908088549102142, "mark_price": 1.17500765, "quantity": -100.56255462, "NAV": 9809.454681853047, "unpaid_liability": 0.0, "decimal_strings": {"isolated_equity": "0.58833779325909506016759051128975354665", "maintenance_margin": "0.5908088549102142150", "mark_price": "1.17500765", "quantity": "-100.56255462", "NAV": "9809.454681853047142004399703960000000008", "unpaid_liability": "0"}}；LONG_SHORT净NOT_EVALUABLE；停止前净114.00，不是完整收益；停止见证{"event_us": 1747016460000000, "phase": "MARK_OBSERVATION", "symbol": "WIFUSDT", "isolated_equity": 0.40196231058527915, "maintenance_margin": 0.8408884561091301, "mark_price": 1.04434312, "quantity": -161.03681635, "NAV": 10113.995411039576, "unpaid_liability": 0.0, "decimal_strings": {"isolated_equity": "0.40196231058527912628133523789099442063", "maintenance_margin": "0.8408884561091300600", "mark_price": "1.04434312", "quantity": "-161.03681635", "NAV": "10113.99541103957585165469914878999999998", "unpaid_liability": "0"}}；事前四成本/单位情景净/风险均不劣于同方向20/10及HOLD门槛：{"LONG_ONLY": false, "SHORT_ONLY": false, "LONG_SHORT": false}。全部为已见开发、Binance价格配Bybit成本代理，funding单位仍UNKNOWN，MMR假设；marked残仓不当作免费清仓。投资NONE/CASH、长期APR NOT_EVALUABLE。

下一有限主任务：先盘点已授权历史中覆盖完整牛熊周期的 trade/mark/funding 可用性，不触及 locked 正文、不下载、不重试受限API；确定可执行共同窗口和当时上市/流动性可知的池规则，再让固定20/10（稳定参照）与双周期（挑战者）及 CASH/HOLD 在完整共享资本下对照。当前303日和122日结果均已见且起始持仓不同，不能回答长期熊市空头是否稳定获利。暂停这套SMA200配方晋级；reopen需新的独立周期或有证据支持的有限风险机制对照，不调参救同窗。先完成采集断档恢复验收与本模块发布，以上历史盘点尚未运行。


表中停机行的LONG/SHORT、毛损益、费用、资金费与残仓均为停止前缀，不是完整303日收益。有限独立复核：保存的原子agent机制证据核对共同122日1220行目标完全相同；但303日起始持仓、成本基础和NAV不同。原122日WIF空头于05-12 02:02触及假设MMR，新账户同分钟equity18.72高于MMR0.50，仍在06:24停机，只延后262分钟。不得称作规避清算。原机制stdin源码NOT_RETAINED；有限只读源本轮真实运行，复核公式、目标、四LO净桥和八停机范围，不重跑账户。子agent最终复核因额度失败，主agent只接管未完成有限核验；两次检查失败（时间列名、REUSED元标签）保留任务记录，成功task f49cdc8de1294e67bfe02eb80b47e512。源码默认静态核对与synthetic golden不证明完整历史代码因果相等。

采集恢复已保留原库/WAL/SHM、checkpoint、audit head及闭合备份；旧public库绑定扩容前源码，原库不重写，新独立collector_public_v3_20261006.sqlite3绑定现行8GB/150GB并沿用原公开来源范围。micro原库按同一实现新会话续写，RESTART_GAP保留；实际前后两次同PID/start_ticks、heartbeat/事件进展见 reports/CTA_COLLECTOR_RECOVERY_ACCEPTED_20261006_V1.json。退出原因UNKNOWN，断档不计健康时间；8765服务已恢复。不是连续72h/alpha资格。


## D096 SHORT机制与单一改变（运行前）

用户要求优先什么时候short，暂停未运行的旧数据扩窗draft。已有dual LS BASE/PCT实际40个空头episode：FAST_ONLY34净-654.75、BOTH_SHORT5净369.85、SLOW_ONLY1净131.66；SHORT_ONLY同向-502.17/+220.08/+107.35，包含未平仓mark，合计与旧真实SHORT账本桥接。全episode按入场信号分组是关联，非删除旧成本后的可实现收益；过去BTC BEAR标签不证明未来熊市，禁止机械BEAR gate。采用唯一候选DC_CONFIRMED_SHORT：负forecast须两个旧通道同时负，否则cash；正forecast原样，真实资本竞争/cov/延迟/清仓/费用全部重跑。两BASE单位解读先行；只有两者通过事前经济/实际风险/状态门槛才再跑两STRESS，总计最多4账户0训练/新数据/搜参。具体协议 `protocols/SHORT_CONFIRMATION_BASE27_20261006_V1.json`。


## D096结果与决定

RETAIN_DEVELOPMENT_SHORT_CHALLENGER_NOT_INVESTMENT；4/4完整账户、1固定配方、0训练/搜参/行情下载，事前四情景通过=True。BASE/PCT净1578.24（原1058.97）；SHORT 572.59（原-153.24）；vol 9.67% DD 5.39%。SHORT增量725.83、LONG增量-206.55，不把全部变化当独立short alpha。BEAR分类SHORT仍-206.17，最大单日-192.06；8/10币增量正，未换池。保留DC_CONFIRMED_SHORT为已见开发主挑战者、原20/10仅多为稳定参照；投资NONE/CASH。下一有限工作先只读检查熊市分类下急反弹亏损的信号/订单时点，使用当时已知的单币价格而非BTC慢状态，识别每日确认退出是否过迟及可执行的有限改善空间；确认机制后才决定一个保护退出对照，不扫描倍数、不强制每段都做空。新的独立周期/原生规则仍是晋级证据缺口；不在当前303日继续优化入场阈值。 工件 `reports/SHORT_SELECTION_ACCEPTED_20261006_V1.json` SHA 500e81bd0cb24531601270bcafaee83e17b8ba0874f28de19d4cd3f2d34586fd。


## D097退出瓶颈纠偏

旧prior10线3/40、公开默认CE1/40、4月9日均0/8，停止盲目提高检查频率或调ATR倍数，默认CE完整钱包NOT_RUN。D096研究主候选保留；全窗口初开/后续增加short按真实逻辑订单归因净496.38/76.21，不是无加仓反事实。旧线独立公开核对与新线未来扰动PASS，五个事后亏损日不算unseen。两技术失败保留。下一有限主任务：在D096稳定SHORT确认上，只选择一个公开快慢周期冲突规则：单币已完成4h趋势转为上涨时把short降为现金，长周期仍共同看空才重新允许short；先固定公开周期与成本、核对可得性/清仓语义，再两个BASE完整账户，只有净/SHORT/实际风险门槛通过才补压力情景。避免只按BTC慢状态，也不因为五个最差日事后删交易。零模型搜索，不调ATR倍数；当前新规则及经济指标NOT_RUN。

D097范围补核：24原空头episode中11个CE22/3状态保护可更早触发，3月11/19三个BTC/ETH/SOL仓已有前期信号；4月9日八仓此前仍0触发。五日1/40当日原始线不能淘汰完整CE策略。其完整经济/再入场NOT_RUN，能力列备用；优先单币4h快慢冲突。点截面V1 receipt保留，最终V2补核不改旧收益。


## D098运行前：一次快慢冲突对照

复用原Jesse MIT Donchian20/10，固定已完成4h负状态与日线20/10、55/20负状态三者共识才允许short，未知/中性/正状态short空仓；非负日线forecast不改。先mask再daily signed covariance，日内只退出，下一日再入场，费用/延迟/容量/硬风险不改。公开周期的4h是COIN适配，不声称完整论文或Turtle复现。既有303日开发历史和固定July池，影响选择的D097损失诊断保留；0拟合/搜参/新行情。两BASE单位解释完整账户，净与SHORT增、BEAR SHORT改善、BULL SHORT非负、vol/DD不增且付费全平才补两STRESS；失败即暂停本配方、不救参。资本10k/caps30abs60gross/隔离1x/8GB150GB不增。预计约8分钟，1200秒/进程1.2GB/新工件300MB停止。协议SHA 95b15d0c7006f6996482725c3b72391d0b00e3d695874ee6b344cb23c98d33f1，实际登记 2026-10-05T18:01:09.271242+00:00。首个回归只因比较全局fill_id/共享现金而失败，按独立资产成交经济字段修正后3通过；V1失败XML保留，财务实现未为测试修改。


## D098结果与决定

PAUSE_FAST4H_RECIPE_RETAIN_D096；一配方、2真实账户、0拟合/搜参/新行情；BASE/PCT净1004.43（变化-573.81），SHORT 191.81（变化-380.78），vol 9.11% DD 7.13%。毛价格变化-523.54，费用+执行变化50.12。投资NONE/CASH，当前窗口仍开发、单位/原生规则假设保留。停止本303日的快线周期/阈值调整；将已固定最佳SHORT规则移至另一个完整下跌及随后反弹周期，优先补最小必要历史与透明基准；先核已授权/已有输入、当时可知标的资格与费用，保留两币对照。目的是检验跨周期有效性，不能按当前303日事后赢家声称独立收益。不改变资金/数据封存/风险权限。 工件 reports/SHORT_FAST4H_ACCEPTED_20261006_V1.json SHA 2d78b365b63dd4b80623b1516211d34a54ebcb1404128334d3e29dddcd51285f。


## D099运行前：旧周期来源兼容性

D098已完成并推送598af94，属于PROGRESS：4h配方两完整账户失败，停止而非调参；D096保留。现有验收10币只有303日执行/12m仅122日，缺完整2022周期。先固定BTC/ETH Jan2022的6个官方成交/mark/funding文件，HEAD/CHECKSUM后才能下载，复用原official transport+convert+独立CSV audit，600秒/进程1GB/新增100MB，0账户/拟合/阈值搜索。无缺失补0/行情+成本伪原生/封存读取；不是完整年度或10币选池，更不是1月APR。全部角色通过才扩固定下跌+反弹期；失败先定位来源不机械扩大下载。协议SHA 9d47d7835eb696e2799d20ebc91e4badfe6541f0877782a32a35679125f0ab5c，实际登记 2026-10-05T18:26:10.301737+00:00。

### D099 来源选择与公开研究核对

读取 Man AHL《In Crypto We Trend》(2024-12-19，https://www.man.com/insights/in-crypto-we-trend)：均线交叉示例50/200日、波动率缩放、有限跨币分散及交易/short成本，未发布可直接复用的完整账户代码；不将其简化图表收益当本地经济证据。另核对《The Need for Speed in Trend-Following Strategies》(https://www.man.com/insights/need-for-speed-trend-following)：快慢速度有换手/反转风险取舍，不能据一套4h失败淘汰快趋势能力。当前已有SMA与Donchian核，保持D096固定配方；不新增模型/技术栈或速度搜索。

2022-01两币成交/mark/funding六档真实原CSV/EOF/CRC与normalized逐行核对完成；目录重名与重复registry ID技术失败原日志/协议保留。已完成BTC成交档按SHA复用，没有重新下载或重复QA。随后冻结完整2022下跌+2023反弹来源范围与2021日线预热，另162档先HEAD/CHECKSUM，只用两个预定透明控制资产，不伪称当时10币池或独立投资OOS。原303日10币结果保持；原funding单位与历史产品规则不确认则继续条件情景，未知不补零。此阶段尚无新周期经济账户。
## D099：区分单币弱趋势与BTC慢标签

复用原303日D096账本和已绑定的SMA200信号，3030资产日期只读资金桥接误差2.39e-12 USDT，0新钱包/训练。BTC BULL标签/单币自身低于SMA200：SHORT净529.02；BTC BULL/自身高于SMA200：53.91；SIDEWAYS/自身低于SMA200：156.21；SIDEWAYS/自身高于SMA200：39.62；BTC BEAR/自身低于SMA200：-206.17。这些相加572.59，只是同钱包归因，不是各桶独立策略或删除交易后的收益。

因此不能把BULL标签下的SHORT盈利解释为一贯逆势空强币，也不能据BTC慢BEAR桶亏损推断所有持续下跌周期不能赚。暂停“BTC牛市禁止所有SHORT”的全局gate构想，保留每币双通道确认；reopen需完整真实钱包证明该全局限制有净/风险增量。单币低于SMA200也不证明次日继续下跌，标签仍是过去状态，当前急反弹损失保留。

新2022–2023来源核对中：BTC2022-07月mark缺Jul31整日，已用官方原生日档补齐；2022-10和2023-02的缺口也用有CHECKSUM日档补齐，所有原月/日重叠字段数值一致、derived文件明确非官方完整月ZIP。原档与失败结果不覆盖。ETH2022-07日档仍不完整，停止其全周期依赖，不插值/补0、不通过删日期凑完整年度。普通公开FAPI请求遇WSL网络不可达，没有改主机/IP或读取账户权限。

下一经济检验改用预定BTC透明参照的完整730日，按数据完整性缩小范围、未查看新净收益；资本10k/单币abs30%/gross60%/1x及真实费用不增。BTC证据不能代表10币组合；原10币303日对照继续保留。ETH路径reopen为合法官方完整mark或有明确适用定义的原生替代输入，不据当前账本输赢选择修复日期。

D099经济运行前 2026-10-05T19:10:03.563479+00:00：来源完整后固定D096，不新增策略参数；2022-01至2024-01一个连续730日BTC参照完整10k钱包，各方向为独立对照不能相加，10账户含两资金费解释与HOLD/CASH；单币仍abs30%不提高暴露；2线程/进程1.2GB/新增800MB/2400秒。按年只分解同一钱包贡献，不重置/拼接。采用规则与费用事前固定，失败停配方搜索；投资仍NONE。协议SHA cf4c94e2fbdef461ba3685eebcd8dc7391f751c2f8b331cffe0afdd8996983fd。

## D099结果与下一选择

NO_PROMOTION_RETAIN_ORIGINAL_SCOPE_ANALYZE_FAILURE；10个完整固定730日BTC钱包、0拟合/搜参。BASE/PCT LS净-507.95，SHORT-505.35，DD14.74%、vol7.70%；同规则LO净39.33、DD8.47%、vol5.83%。2022SHORT+169.58、2023-674.93，SMA200下方仍亏-393.80，单纯上方禁空不能解决主要机制。选择独立经典慢趋势参照，暂停当前BTC配方晋级，旧10币D096仅保留原已见范围；投资NONE。复用现有SMA200_SIGNED经典规则，先在相同BTC730日/产品/费用/资本/风险下比较三个方向，复用本轮CASH/HOLD完整控制；0训练/参数搜索/新行情。检验慢趋势持仓是否捕捉了Donchian反复进出漏掉的2022下跌，不先增加新gate或继续调快线。 工件 reports/SHORT_FIXED_CYCLE_REVIEW_20261006_V1.json SHA 2964779be260bbf71987bafab110e1fcb500895a183af7efff9255532074bbfe。

## D100运行前 2026-10-06T02:25:22.055269+00:00

Does frozen public-family price-vs-SMA200 signed trend capture2022 bear movement and reduce2023 short whipsaw versus fixed Donchian confirmation? Same730d capital/cost/product; no fitting, period choice or new gate. 公共既有200日规则，不调参；6新账户+4实际同窗控制复用，2进程各2线程/1.2GB/新增600MB/1800秒，共享8GB/150GB/0GPU。所有标的/时钟/资本/风险/费用及资金费解释沿D099固定，原730日已见开发，不称unseen。采用规则：DEVELOPMENT_CHALLENGER_ONLY_BOTH_UNIT_SCENARIOS: complete730d, wholeSHORT>0, 2022SHORT>0, LS net>ownLO and>D099LS, LS Sharpe>ownLO, LS minuteDD<=D099LS. Report actual vol/DD vs ownLO/HOLD; higher risk cannot be called matched or investment proof. If fail no rescue parameters; investmentNONE.

## D100结果与下一选择

D100复用固定SMA200：6新730日BTC完整账户、4同窗完整控制复用；两资金费解释SHORT总贡献均正、多空均提高净收益。BASE/PCT LS净2413.34、SHORT718.25、vol10.68%、分钟DD9.54%；同规则LO净1563.48、vol6.68%、DD6.23%。原Donchian确认LS净-507.95、vol7.70%、DD14.74%。净收益改善并伴随更高实际风险，不能说风险匹配。RAW通过、PCT仅Sharpe比LO低（1.065<1.121）使事前门槛未全部通过，不事后改成功标准、不晋级投资。 SHORT2022+1703.98、2023-985.73，1月-636.53；下一项优先检验反弹时短线确认解除，非再搜模型。保留SMA200仅多为本BTC窗口研究参照、正贡献多空为有条件挑战者；下一有限实验仅改变SHORT：200日弱势仍需50日价格趋势确认，确认解除去CASH，LONG保持200日原规则。50是预先指定经典尺度，0拟合/网格/新数据；针对2023年1月快速反弹损失，完整重跑实际账本，不用删旧交易的假想收益。阶段门槛不改，失败保留负结果。 结果 reports/SMA200_FIXED_CYCLE_REVIEW_20261006_V1.json SHA 8cebd052853d5317caa7c2f0278f6595048d47638b9801015de68e3566ca4047。

## D101运行前 2026-10-06T02:55:51.560732+00:00

One-factor rebound exit: keep SMA200 positive signals unchanged; short only below completed200-day AND50-day means, otherwise cash. Does this reduce2023 short loss without sacrificing net quality? Four complete accounts, no period search. 固定50日不是网格。沿用BTC730日已见开发、10k、abs30/gross60/1x、原分钟成交与mark及两资金费解释。4新账户+6已绑定完整控制；两任务各2线程/1.2GB/1800s/600MB，共享8GB/150GB、0GPU。门槛：Both units complete730d, SHORTtotal>0, SHORT2022>0, LSnet>unchangedLO and>D100LS, LSSharpe>unchangedLO, LSminuteDD<=D100LS, SHORT2023loss less thanD100. These tighten original gate; actual risk not equalized. Failure retains old research reference, no same-window rescue search; investmentNONE. 原信号所有列与D099保存字节逐日相等，原仅多目标与D100完整730日逐项相等；必要减仓与真实费用不改。

## D101结果与决定

D101固定50日空头确认未通过两资金费情景门槛：BASE/PCT多空净1661.82（原2413.34），分钟DD9.25%（原9.54%）、vol9.64%、Sharpe0.846（原1.065/仅多1.121）。SHORT2022 292.02（原1703.98），2023 -214.61（原-985.73）；两年SHORT净77.42。 50日硬过滤更易切断熊市收益且增加换手；公开Man快慢趋势研究只作方法参考，不是本地复现/收益承诺。暂停SMA200_SHORT50硬过滤，保留原SMA200仅多参照与有条件多空挑战者。下一项只读检查已登记pandas-ta-classic CE22/3有状态空头保护在本BTC周期的触发和重入语义；只有明确提前保护反弹且未破坏主要熊市持仓的机制证据才接完整账户。固定公开默认，不扫ATR倍数/周期；影子触发不代表净收益。该不同授权周期检验满足D097 reopen条件。 工件 reports/SMA200_SHORT50_REVIEW_20261006_V1.json SHA 2dd17c4c53299defcdbf7c5a3e1795676ad67a7a5cebc1f68f0100dcd2f1d987。

## D102运行前

固定pandas-ta-classic0.8.32 CE22/3、原SMA200 BTC2022–2023完整持仓影子时点；所有原始SHORT，不挑最差日期。核首次保护和下一日原负信号重入意图，180秒/800MB/0拟合/0新钱包/0下载，不计算删交易的假想PnL。原财务代码、成本、风险与证据不改。只有机制有依据才考虑完整新账户；当前研究参照仍为原SMA200。

## D102结果与决定

D102公开CE22/3只读轨迹：原SMA200 BTC730日3段SHORT均有更早触发，其中2段下一日原趋势仍要求SHORT；不能把退出线直接挂入账户宣称净改善。第一段2022-01-01入空，2022-02-04已触发，原仓直到2023-01-14才平；第三段2023-08-31几乎开仓即触发，原负趋势仍在。 原24段提取、独立CE值及未来扰动核对通过；V1/V2实际episode逐项相等，V2只加源码执行绑定与UNKNOWN表达，无新经济运行。不接无重入规则的CE保护，也不靠优化ATR周期/倍数救配方。下一主任务复用已登记MIT Jesse SMA50/200完整多空入/退出hook，在相同BTC730日、资本、成本与风险下做固定公共family对照；优先直接复用现有public_sma_perpetual接口，先核完整策略语义/标的顺序，再跑有限方向账户。它是独立公开family，不把全部变化归因于SHORT退出；0训练/网格/新行情。原SMA200研究参照保持，投资NONE。 工件 reports/SMA200_CHANDELIER_TRACE_20261006_V2.json SHA 29d4e2ba6cdde149361487dfe6de8c1baa6645bea99f91b1af7d513559f7238d。

## D103/D104运行前 2026-10-06T03:38:41.049998+00:00

用户将regime-aware冻结expert组合提升主候选；SHORT优先级保持，不继续exit/filter网格。完成公开50/200原hook6账户及DC20/10、双通道2family各2资金费账户，合计10新钱包，顺序两批、最多2并行各2线程/1.2GB/1800秒/600MB，0训练/下载/参数扫描。原4Cash/Hold控制严格字节绑定复用，不相加资本。Both units: complete730d; LSnet>ownLO and>D100LS; SHORTwhole>0 and2022>0;2023SHORTloss reduced; LSminuteDD<=D100LS; LSSharpe>=D100LS. Different actual risk reported, no equal-risk/native/investment claim. Failure retains strongest existing reference. These are fixed family comparisons, not selector tuning. 下一阶段只冻结60日oracle诊断：Both funding conditions: switching-cost-aware informed wealth minus best full-window single expert >=500USDT per10k, with positive LONG and SHORT contribution in selected segments. Only permits predictability screening, not candidate promotion. If fail pause selector; no horizon scan. 归一化单10k财富诊断保留各expert已付成本并另扣边界换仓估计；不是真实可交易oracle，也不能据此宣称ensemble alpha。通过后需同一共享账户真实重放与过去特征可预测性、placebo对照；只读诊断120秒/700MB。全部已见开发、原风险/资源/封存/资金边界保持。

## D104 oracle运行前补充expert

2026-10-06T03:50:52.133304+00:00：7→8专家，额外保留D101固定SMA200_SHORT50（自有修改，非完整公开family）。用户条件优势假设以慢趋势熊市收益/快确认反弹保护为核心，故纳入已完成负结果配方；参数不变、0新账户，未查看任何oracle结果。V1保留并由V2在运行前supersede，仅60日horizon与500USDT门槛不变。

## D104输出修复

Oracle任务418208d509a94bdeae922f736fe20cbf已在JSON导出失败退出1；计算/归因断言通过但不得消费不完整输出。V1 partial与原源码SHA保留；V3只修NumPy标量JSON导出，周期/费用/专家/门槛不改，不重跑账户。恢复只读诊断，不把失败发布为成功。

## D103/D104结果与自主决定

D103公开完整SMA50/200多空：BASE/PCT净-1.62，毛价格93.96，费用+执行95.12，SHORT-360.32，vol10.70%、DD17.29%；RAW净-48.03。两情景不满足替换原SMA200的门槛；保留为冻结expert，不加exit/filter搜参。 用户新优先级：冻结expert条件优势/selector为主候选，SHORT研究保持。ADVANCE_PREDICTABILITY_SCREEN_ONLY_NEEDS_ACTUAL_SHARED_WALLET_REPLAY；冻结expert60日近似机会增量足够，先将同一oracle路径在既有共享资本账户真实重放，补equal/static合集真实成本对照；诊断不作为投资证据。随后只用过去slow×fast×vol少量状态、非重叠60日标签做排名可预测性与常数/错位/打乱/同频随机placebo，0交易模型拟合，不扫分类器。仅12个完整60日标签，尾部10日保留收益但不能充作60日训练标签；单BTC旧周期仅机制筛选，稳定性/独立证据不足，不晋级。 工件 reports/FROZEN_EXPERT_ORACLE_OPPORTUNITY_20261006_V2.json SHA c98dc7748159c9a4616ad33d6e6a322550bda42d130c8a72ee1efc1b8837fce9。不把单策略或过滤失败推广为SHORT无alpha。

D104机会结构追加：PCT未来路径仅SMA200/HOLD/CASH、2023 SHORT=0；RAW有1段公开50/200，四个DC/快确认expert均未入选。过去BEAR仍可能未来HOLD胜出，大上界不是可预测性证明。下一步优先成本后真实重放与简单方向/静态配置，八专家classifier暂停；reopen需稳定过去特征对条件排名的信息和独立证据。不是降低SHORT优先级，也不永久删除未选expert。

## D105运行前 2026-10-06T04:15:55.067291+00:00

Does the fixed60day informed path preserve its opportunity in actual shared-wallet execution? Compare with equal8 and one fixed soft direction allocation, sameBTC730d capital/cost/risk. No learning, no strategy parameter or winner-path retuning. 只冻结3配方：ORACLE60D沿D104两单位路径不改（未来知情、不能投资）；全部8expert等权；SMA200/HOLD/CASH=.5/.25/.25作为事后D104提出但运行前固定的开发静态参照，不是优化权重。无独立/unseen声明。6新730日实际账户、最多2并行各2线程/1.2GB/1800s/600MB，共享8GB、150GB，0训练/搜参/新数据。实际成交、资金、费用一次记账，不沿用诊断净收益或二扣shadow切换费用。Oracle remains NONCAUSAL and never candidate. Opportunity persists only if both units actual oracle net minus fixed best single>=500USDT. Static ensemble research challenger only if both units net>=D100 ownLO, Sharpe>=D100 LO and minuteDD<=D100 LO; report actual risk and price/funding/cost/concentration, no risk-matched or investment claim. Retain all negative results and do not rescue weights. 必要减仓、标的顺序、完整资本和原封存边界保持。

## D105结果与自主决定

D105把冻结expert目标放入真实单10k钱包。两资金费条件oracle相对最佳单expert增量3335.69/3386.30，比shadow诊断低27.93/28.69，机会门槛保留，但oracle未来知情始终不算候选。八expert等权弱于原仅多；固定SMA200/HOLD/CASH=.5/.25/.25降低实际波动/回撤、提高Sharpe，但净收益低于原仅多，两条件均未达替换门槛。投资NONE/CASH，原SMA200仅多风险效率参照及多空正SHORT挑战者保留。 STATIC_DIRECTION3保留为低风险控制，不替换主参照、不扫权重；EQUAL_EXPERTS暂停主力，reopen需独立互补收益源。真实oracle机会足够，但仍非因果/不能投资。下一有限主任务只用过去slow-trend×fast-trend×vol状态检验60日未来expert相对排名/赢家可预测性，先固定可解释状态映射，再chronological walk-forward与标签成熟，12个完整非重叠60日标签、尾部10日不充样本；固定/错位/打乱/同频随机placebo与oracle可行差距必须报告。0交易模型拟合、参数扫描或权重救配方。若不优于静态/placebo则暂停本selector配方，保留单策略与SHORT能力；reopen需新独立周期/合法多币机制。 工件 reports/FROZEN_EXPERT_MIXTURE_REVIEW_20261006_V1.json SHA dfc134c7cff3fd05c37bda79874633d9f069fe0a3db65c31f037c9ce64627208。

## D106运行前 2026-10-06T04:46:25.206660+00:00

Is one interpretable past slow/fast/vol soft state map informative about60day frozen expert net relative ranks beyond static/lag/shuffle/samefrequency random? No trading model training or PnL optimization. 固定特征price/SMA200、price/SMA50符号及vol30>vol200(sampleddof1)，映射bothdown=.75SMA+.25CASH；down/rebound=.5HOLD+.5CASH；bothup=.5SMA+.5HOLD；up/pullback=.25SMA+.75CASH；equalCash；highvol将非现金减半。60日权重更新，从CASH起每次L1≤.5，不扫描。只用12完整非重叠标签，前4成熟后评价8，尾部10日不充标签。官方SciPy rankdata；先评价净relative排名，不生成收益/Sharpe/APR。过去均值排名仅统计对照、16更新，0交易模型拟合；64固定seed placebo路径×2单位及静态/错位对照全部保留。Only retain this fixed-map mechanism probe if BOTH units weightedrank>=strongeststatic/past reference+.05, above shuffle/random95th and lag, positiveincrement inbothdecisionyears with>=3evalfolds each. EvenPASS does not permit trading classifier or investment: only8oldcycle labels, independent ranking evidence still needed. FAIL pauses this map, no same-window threshold/weight/horizon rescue. SHORT capability and otherregime hypotheses remain. 120s/700MB/0GPU/0新账户/0行情。

## D106结果与自主决定

D106单一slow×fast×vol固定软映射未通过事前排名门槛：RAW/PCT平均加权排名0.67049/0.69400，静态三expert0.63839/0.66518，最佳单expert与只用成熟过去排名均0.64286/0.69643；虽胜同频随机和滞后60日特征，未超过打乱状态95%对照0.67637/0.70124，两年相对优势也不一致。仅8个评价标签，不声称regime alpha；暂停这个映射，保留SHORT与专家库。 D105真实oracle机会仍大，当前最大瓶颈是过去信息的条件排名与跨周期证据，不是执行成本消灭机会。不能用初筛失败永久否定regime-aware方向。不再在BTC同窗口改状态/阈值/权重，也不训练交易classifier。下一主任务先只读核现有授权历史manifest、完整专家账本及选择影响记录，明确可增加哪些合法完整周期或多币横截面标签；只在授权非locked范围补足有效样本，冻结专家原样做跨窗口条件优势迁移核对，已看历史仍标开发，不冒称unseen。当前映射reopen需多个周期的稳定相对排名信息或新增可解释past-only信息；仅8标签不足升级学习控制器。既有资金费单位/数量/MMR不确定继续限制投资结论。 工件 reports/REGIME_RANKING_SCREEN_20261006_V1.json SHA 5319ed4a130f4e06dc6927128bfb3493ee6874ceb6edb307368c7ca0b586c4c0。

## D108 ML selector运行前授权与冻结

2026-10-06T05:45:06.283842+00:00：用户明确允许有限ML，覆盖D106未开放classifier的暂缓。只用SMA200/HOLD/CASH，参数不变。所有2157历史metadata/manifest/选择记录审计已生成DATA_SPLIT_AUDIT；2022–23已见，内部时间验证不叫OOS，final封存正文不读。26past-only特征，H30/60/90固定，Ridgealpha30与单一小XGB80depth2，MLP因样本不足不跑。5expandingfolds，purge后H额外embargo，初折H90仅94训练日，重叠日标签非独立样本。60主CV组+320shuffleCV组，最多1080底层fit（故障保留最多1retry，总预算2160），64placebo路径，两资金费条件，158完整共享钱包对照；0Optuna/密扫/调温度/改成本。成功门槛BOTHfundingconditions: completeallnecessaryaccounts; net>beststatic; >95th ofEACHlabelshuffle/featureshuffle/random; positive netincrement2022Q4 AND2023; capture>=.15 matchingH oracle; realizedriskwithin fixedlimits. Passed seen screen only, notstablealpha/investment. Failure no complexityincrease. 2022shortcapture只评价Q4的92日，不冒称全年。2worker各2线程/1.5GB，8小时、12GB新增空间上界、D150GB/RAM8GB/swap0/GPU0。正式fit之前必须commit这套config/source/split，runner逐字核Git；后台Python自行完成，全程0LLM/API。

D108启动纠正：首个systemd后台进程在进入Python前被bounded WSL身份守卫拒绝（实测32ms、exit1、日志Use D-hosted hpc_linux）；最初短暂active不算存活。修复仅为外层核真实hpc后传入WSL_DISTRO_NAME与持久日志，0fit；原冻结配置不覆盖，runtime_fix只变启动器SHA/新目录，所有训练/经济/验收协议逐字段一致，旧2日共享钱包QA有效保留。需先commit再正式启动。

D108实际启动验收：修复commit 6e41645已push并核远端，2026-10-06 14:06后原生service持续active、runner PID13164已进入DATA，progress持续更新；实际running证明见reports/SELECTOR_ML_RUNNING_VERIFIED_20261006_V1.json。后台自行跑完整固定DAG，模型经济结果未读，不逐轮由Codex执行。

## D108：有限ML selector完成后的投资判断

预登记0dc2f2f，后台启动修复6e41645只改launcher/新目录；所有模型、数据、成本、horizons、门槛保持。Python独立运行6363秒，440底层fit/350scaler/158共享10k账户，最终rank选LINEAR_H60而非事后PnL更高的H30。BTC2022Q4–2023的457日全部已见开发：RAW/PCT净1446.38/1614.65，胜SMA827.62/971.38及经验placebo95，但低HOLD1842.31/2080.75；oracle capture−31.29%/−38.47%，2023方向失败。2022Q4 short+367.93/+350.23；2023 short−553.21/−558.07，全部费用+执行仅约50；主要缺口是反弹期short和long参与，非交易成本。DD6.41%/6.20%低HOLD7.32%/7.31%但Sharpe1.088/1.198低1.323/1.473，vol10.42%/10.43%与HOLD10.64%/10.63%接近。

独立参考复核4026成熟标签、训练scaler均值、所有fit成熟/embargo和158实际账本SHA/资金桥接/日指标，最大资金NAV误差1.82e−12。训练R²高、H60全部季度验证R²负；小近常量label使幅度不稳，结合净收益/跨阶段门槛拒绝晋级。16shuffle经验95分位非p<.05，模型选择与验证共用池，仍无regimealpha/投资声明。ROI上界仍有但过去信息模型尚未转化；不从这个窗口永久否定SHORT。

决定：投资NONE/CASH；learned selector暂停，保留冻结专家和全部能力，禁止追加复杂度/事后调阈值。下一有限主任务零MLfit，先复用D043已完成2024年1–7月213d历史来源，核冻结三expert的条件优势/成本后oracle机会跨窗口是否存在。所有2024已见，不叫unseen。reopen learned方向仅在多个完整阶段稳定条件排名或可靠新增因果信息；不是换种classifier继续枚举。详细账户、版本/单位/成本/风险/日期/工件SHA见SELECTOR_ML_RESULTS及INDEPENDENT_REVIEW。

补充同H60/368个共同成熟日期的常量ranking对照：LINEAR_H60 RAW/PCT0.56697/0.56899，恒定HOLD0.63995，模型连relative-ranking目标也未胜强常量基准；16+16shuffle均无更高净收益，有限尾概率1/17=0.0588，32随机1/33=0.0303，都未选择偏差校正。冻结success仍按原经验95判，不能另包装显著alpha。


## 2026-10-07：归档采集与完整数据窗口验证模块

新增 [collector_research 模块](../modules/collector_research/README.md)。服务器上的四类模型研究已完成，验证复用40个模型折与372项产物；新原生账户验证先按输入完整性分段，788天排除UTC2024-08-12一个缺口日，6段787天，共96/96独立10k账户完整且真实平仓，独立NAV/钱包最大误差5.46e-12 USDT。最后24小时采用原持续、容量受限的收费平仓规则；缺口不补造，段间收益不相加或拼成一个钱包。

这不是D108原数据复现，也不是未见OOS。四类模型在两资金费条件下的共同窗口收益中位数均为负；原日频筛查的基线门槛均未通过，最终模型未拟合，不晋级、不部署，投资资格仍NONE/CASH。后验完整数据窗口不能解释为当时能够预知并避开未来缺口。详见 [实际结果](../reports/COLLECTOR_COMPLETE_WINDOWS_20261007.md) 与 [小型验收摘要](../reports/COLLECTOR_COMPLETE_WINDOWS_20261007.json)。旧D108判断与证据保留。

用户2026-10-07明确区分资源：服务器按实际配置，无项目CPU/RAM/swap/墙钟限制；本机限制继续。模块默认local，必须hpc_linux及8GB/swap0/GPU0；server需显式选择且拒绝WSL。当前服务器10CPU/33.65GB，性能切换复用76例、只继续20例。行情、模型、环境和大账本留在外部STATE。


## 2026-10-07：Transformer v2 预注册研究

独立 research/transformer-v2 分支，协议在首次新fit前固定。旧证据和NONE/CASH保留。四个架构、三seed、两资金费条件、五时间fold；共同完整窗口沿用原787天。跨资产轴、显式可得性掩码、三种readout固定平均、8天patch、多任务与固定K=2中性组合是有限比较；所有经济策略仍走原分钟账户与独立账本。2026-03至08开发期间不读取，最终规则和开发报告冻结后只开一次。当前状态：环境/源SHA核验通过、训练前11测试通过，经济结果未产生。详见 reports/transformer_v2/TRANSFORMER_V2_PROTOCOL.json，SHA 8f7cdc763cd068b3c0ff1a4030fa0edc8d65838dd276c047427848f08378f4c7。


2026-10-07 Transformer v2：当前状态：120/120个CUDA开发fit完成，全部权重/预测SHA、inner与outer train-only scaler、标签成熟边界和固定epoch已独立核验，零fit失败；正在生成并运行720个原生开发账户及24个注册past-only最终fit。服务器20项模块测试与旧冻结权重预测复用检查通过。封存数据尚未读取，完整研究尚未结束。 协议与gate保持，审计见 reports/transformer_v2/TRANSFORMER_V2_FIT_AUDIT.json。


## 2026-10-07：Transformer v2 开发报告已冻结

120个开发fit和24个最终past-only fit均审计通过；720个开发原生账户已完成，旧控制账户复用。固定候选 CROSS_ASSET_UTILITY/DIRECTIONAL，development gate=False。三seed固定平均，未选择赢家seed或pool。开发报告与候选清单已提交后才允许一次2026-03~08封存评估；当前投资状态仍NONE/CASH。详见 reports/transformer_v2/TRANSFORMER_V2_DEV_REPORT.md。


## 2026-10-07：Transformer v2 完整研究

最终决定 B. CONTINUE RESEARCH, NOT YET PROMOTED。投资状态 NONE/CASH，不部署。120个开发fit、24个过去数据最终fit审计通过；开发账户保留全部seed/ensemble/方向/中性/组合与oracle，冻结开发候选后只开一次184日封存实验。Full locked experiment is NOT_EVALUABLE or has preserved engineering failures; no post-outcome rerun。详见 reports/transformer_v2/TRANSFORMER_V2_FINAL_REPORT.md 与 FINAL_DECISION.json，全部旧证据保留。


Transformer v2 最终证据复核：当前B/不晋级，投资NONE/CASH。120开发fit、24past-only最终fit、720开发任务与36暴露对照已完成；764唯一新账户重新逐SHA验收，653完整/111风险停机前缀。封存只有一次data gate检查，预测0、经济账户0；三币2026-06-24 04:00资金费事件仍缺，官方最新月档未补、日档404、历史接口451。20份官方日mark/premium文件可补价格缺口，但不掩盖资金费未核实。完整封存经济目标仍未实现；保存原正式N/E结果与首次报告，不选子窗口、不改模型或门槛。详见reports/transformer_v2/COMPLETION_AUDIT.md及FINAL_REVIEW_EVIDENCE.json。


## 2026-10-07 Transformer v3 preregistered frozen-wallet replay

Before any v3 fit or new economics: protect old v2 0350589 and locked N/E; preserve all111 halted reasons; preregister five missing-funding bridges and FULL .60/HALF .30 K2 risk comparison. Change isolated liquidation semantics, never increase capital/caps/leverage or choose outcomes. 27 relevant server tests pass. Run two actual probes then864 frozen-target wallet rows under committed source binding; old complete nonliquidating economics must match1e-7. Native tier API403 means conditional Bybit-style financial replay, not historical native exchange certification. No fit until replay/neutral analysis, no locked result before development model/weights/risk freeze. Remain NONE/CASH.


## 2026-10-07 Transformer v3 finite policy implementation before fitting

Current864 frozen replay is live under d8c47a1 source binding. Do not edit its financial/replay sources or re-run valid old work. Implemented60 dev and12 final past-only policy fits,348 fixed HALF controls,576 policy dev and400 five-bridge locked comparisons, mature teachers and all11-answer reporting. Actual teacher chronology30 rows passed with no new fit.23 relevant prefit policy/storage/report tests passed plus2 actual source-content mutation tests; one failed timestamp-cache assumption is preserved and corrected by hashing actual contents before/after each new native wallet. Same-clock Mark-liquidation/funding legacy-auditor counterexample preserved; fix only after current frozen batch completes and validate default golden. Full replay and neutral analysis must precede protocol generation/commit and any fit. Architecture/profile/weights freeze before locked economics; no best bridge, winner seed, new risk scan or locked tuning. New storage only applies to newly generated owned files; protected old artifacts immutable. Research is not complete; NONE/CASH.

## 2026-10-07 autonomous follow-through and hardware parallel execution

User asks to close Codex while server continues and questions parallel throughput. Actual measurement:10 CPU cores,10 native workers each98.7%,96-99% aggregate userCPU, I/O wait0 and no CPU/RAM/runtime quota; current frozen financial source cannot be changed mid-run. New isolated execution worktree permits the validated same-clock auditor extension without changing that batch.23 financial/order/default tests and26 policy/storage/report/capacity tests pass on the server. Authorized protocol metadata commits happen automatically only after864 replay+neutral analysis; runtime never edits source. GPU fit process concurrency follows actual VRAM/CPU (4090=>2), fixed60-fit algorithm/seed/batch budget unchanged. Where oldneutral stability does not require priority HALF risk check, GPU fits and HALF CPU wallets overlap; final past-only fits and policy-development CPU wallets overlap. No locked economics before all weights/profile/development freeze. All failure receipts and valid checkpoint/task outputs retained.

## 2026-10-07 Transformer v3 completed finite research and final publication

Actual completed budget:864 frozen v2 replay rows,348 HALF controls,60 development fits,12 fixed past-only final fits,576 new development wallets,400 five-bridge/two-unit locked wallets. Development1782/1788 and locked395/400 full-calendar paid-cash complete; stopped prefixes remain N/E, not execution errors or full returns. Original111 restored108=96liquidation+12oldbankruptcy,3capacity risk reductions remain N/E;753 previously complete nonliquidating economic parity checks. Protocolbdfe816 follows complete replay/analysis and precedes fitting; model/profile/weights frozen before locked economics. Fixed selected ORACLE_POLICY_CROSS_ASSET/NEUTRAL/FULL development gatefalse; selected locked net approximately-4.41%/-6.58% across two funding interpretations, all five bridges economicFAIL, longpositive/shortnegative,one1000SATS liquidation and normal reentry per selected wallet. B.CONTINUE RESEARCH follows preregistered descriptive rank signal; no promotion,investmentNONE/CASH,no paper/live orders. New daily-expert proxy regret improvement fails registered crossfold gate. Conditional MMR.005/MMD0 and imputed funding do not certify official exchange risk tiers/events; original v2 formal N/E preserved. Background exits normally after actualSHAcheck ofall16025oldfiles/33182604674bytes unchanged. Publication verifies all2188summary/audit/target identities and allfrozen released weights/scalers, preserves old190/576snapshot, exports raw generated final/dev reports/results plusCSV/freeze/N_E/manifest; no training or economic replay during publication. See reports/transformer_v3/FINAL_DELIVERY_SUMMARY.md and FINAL_PUBLICATION_MANIFEST.json. No post-locked tuning or additional model search.

## 2026-10-08 BTC expert aggregation preregistration

User adopted the supplied 20261007 plan. First finite round: reuse exact old BTC expert targets/net feedback; 364 mature 2022 intervals freeze scale and one-hot static benchmark, 2023 seen historical 365-day independent 10k wallet. HEDGE eta=.05 and FIXED_SHARE alpha=.01 only two dynamic wallets; EWMA diagnostic only. Base CASH/family EW/static train/SMA200; two conditional funding interpretations. 28 wallets total with separately declared execution54bp and adverse payments2/receipts0.5; identical frozen base weights across stress. GPU0/no new expert pool/model/oracle grid. Shared Decimal isolated engine and independent auditor reused. Original accepted-manifest/report SHA anchored; read-only relocation retains producer scopes and does not fabricate old task receipts. Optional second round only if a demonstrated projection bottleneck justifies one same-path ablation. Tests/scripts/protocol precede new economics; resource limits apply to actual server and 15GiB free guard, no scientific local execution.

## 2026-10-08 BTC expert aggregation completed: STATIC_EDGE_ONLY

Protocol committed before economics (5e9ace9; deployed source49869f7). All28 registered accounts completed525600minutes/365days with paid terminal cash and independentNAV/wallet audits; maxNAVerror1.82e-12USDT. Actual workflow8processes about492seconds, GPU0. BASE familyEW7.49/8.60percent, FixedShare7.63/9.04, Hedge2.40/3.99, train-frozenSMA2004.41/6.01 across two unconfirmed funding units. FixedShare incremental13.78/44.47USDT vsfamilyEW below100 threshold, largerMDD/gross/beta and unstablequarters; allseparateEXECUTION_X2/FUNDING_ADVERSE pressures completed. Registered gatesfalse; stoproutingrecipe, secondroundNOT_TRIGGERED, no newexpert/ML or deployment. Historical seenBTC scope cannot qualifyfreshOOS, conditionalfunding/risk assumptions retained.31pre-executiontests plus1synthetic report-incomplete-calendar counterexample passed onserver. Allaccount/input/target/sourceSHA checked afterrun; originalsuntouched. RawgeneratedREPORT/RESULTS/CSV/chart/cacheindex/finalverification published underreports/expert_aggregation. Missing repository-declaredhttpx repaired beforefirstwallet, failure preserved; no economic rerun dueenvironment issue.


## 2026-10-08 SHORT routing mechanism diagnosis

From actual latest research HEAD5346a5c, not stale local e17e113. Read-only 28-account ledger diagnosis: FAMILY_EW/FixedShare have zero short fills; frozen EW prior HOLD/3 plus six trends/18 has nonnegative bound for all730 observed days, not a theorem for dynamic weights. HEDGE short gross−266.60/−243.12 and net−274.47/−253.60; three losing episodes, January rebound≈61% of short loss. No new fits/wallets/parameter search. 60d noncausal rebased feedback diagnostic adds signed expert vsHOLD/CASH: 2022+2049.48/+1985.12, 2023+.05/+.07 with no negative winner targets. This is neither shared-wallet opportunity nor isolated short alpha. All112 artifactSHA and cache binding checks, independent Decimal maxerror3.18e−12, three actual server tests and independent read-only source review pass. Runtime .746sec/RSS92.54MB under8GB/swap0/GPU0. Keep EW long/cash risk reference only; pause current Hedge/FixedShare tuning, SHORT remains primary. Next: test past-only bear continuation versus rebound information on approved seen multi-asset history, first coverage then one finite mechanism, NOT_RUN. Reopen controller only after stable cross-stage direction/rank information or demonstrated projection bottleneck, not another eta/gate grid. NONE/CASH. Original results, remote WIP and locked permissions untouched. See reports/SHORT_ROUTING_DIAGNOSIS_20261008.md.


## 2026-10-08 SHORT breadth: stop failed filter, prioritize published relative factor

Frozen prereg3e9ebf1: 49 nonoverlap30d blocks, 25 own bearish-confirmed blocks; broad-down short price-cost mean -6.145%, broad-up/tie +6.776%, spread -12.922pp, all5 gates false. Not wallet performance; no funding/intraday risk included. Early peer maturity omits major2022bear, insufficient2upblocks in2022-23; do not generalize noSHORTalpha or invert failed breadth threshold. 64 availability-stratified joint-date shuffles preserve label support; independent pre-run coverage fix preserved in Git. Runtime.259s/RSS86.82MB,0fits0wallets. Stop this factor and all threshold scans; reopen only new past information with independent full-bear coverage. User emphasizes positive investment information/efficiency. Next finite candidate is publicly documented3week cross-sectional momentum, weekly top2long/bottom2short with existing10% covariance risk and true shared wallet, not another gate/controller. NONE/CASH. reports/SHORT_BREADTH_PROBE_20261008.md.


## 2026-10-08 Fixed public CSMOM preregistration before any new wallet

One published3week cross-sectional momentum adaptation, weeklycalendar top2long/bottom2short, daily past-only10%cov sizing. Restore prewindow scheduled rank, missingheld clears until nextrank; existing hard risk remains. Two pre-existing seenDEV firsthalf2024/2025 contiguous windows, original5/6active pools in10dim identity; not2022bear or newOOS. Exactly4wallets=2windows*2conditionalfundingunits,0fits/parametersearch. Reuse16savedHOLD/SMA200/static/CASH controls only after identical economic/input/financial-source/SHA/paidterminal identity. Report actual risk difference, LONG/SHORT separately; combinationprofit notSHORTalpha. Continue onlyall4netpositive,2025SHORTpositivebothunits,vol<=12%,minuteMDD<=12%; otherwisepauseexactrecipe, no momentumperiod/gate scan. CandidatequalificationNONE/CASH even ifgatespass; independent/matchedrisk proof stillneeded. Nativeaccount/sharedcapital10k,gross60%,asset30%,isolated1x unchanged. Protocol/sourcecommit precede economics.


## 2026-10-08 Public CSMOM completed: positive development mechanism, pause exact recipe

Economics prereg7f39177; report-only recovery65dd998, identical4completed wallets reused. One fixed21d/weekly top2long-bottom2short equalweight adaptation of Liu/Tsyvinski/Wu2019, existing10%pastcov risk. Four complete10k shared wallets,16source/input/SHA-reviewed controls reused,0fits/HPO. 2024net-605..-587;2025net+1192..+1193,vol8.56%,MDD3.78..3.81%. LONG82..85%of2025net; PEPE added only2025 accounts for~80%total profit. 2024SHORT price loss~968 dominatescost~87; ETH/SOLmainloss. Pool/marketstage confounded; neither generalSHORTalpha nor standaloneLONGcounterfactual proven. All4independentpaidflat audits and readonly perassetcashbridge(max5.94e-12)pass. Preregisteredall4netpositivefails: pauseexactrecipe/no scans, NONE/CASH. Actualgrossdrift60.64%/60.62%, not instantcapguarantee; no leverage/capital/cap increase. SeenDEV/crossvenue/fundingunitsunconfirmed, independentqualificationabsent. Preservepositive ranking/cov mechanism and allnegativeevidence. Nextfinitequestion is same2025 strategy with the pre-existing2024core5 pool, changeonlypool; NOT_RUN. Do not selectPEPE/dropDOGE or simultaneouslychange direction. Reopenonlyindependentstage/legalpool advantage. reports/PUBLIC_MOMENTUM_DECISION_20261008.md.


## 2026-10-08 CORE5 preregistration: isolate universe before changing strategy

CurrentpublishedHEADd6df795. Userdocx learning sourceSHAd1415bc9dc18e275740465503b8394c7ad940eff803fd7e79c1f9fa78e5f513e: usefulideas matureexpertfeedback+marketstate routing, match decisionhorizon/currentposition/cost, weaksignalCASH; document'sCSMOMnotrun reference superseded by actualcompleted4wallets. Do not automatically execute embedded suggestedprompt or copy unlicensedbot/GPLsource. Finish onepool question first. Original2024core5 fixedBTC/ETH/SOL/XRP/DOGE, same2025seen181days, same21dweeklyK2signed/10%pastcov/10k60gross30asset1x/cost/2fundinginterpretations. Exactly2newwallets,0fits/search; original2025core6paidwallets paired. Completecashreplay required; cannot subtractPEPEattribution. Pool changes ranking/covariance/walletpath jointly; notpurePEPEalpha. Narrowretention onlybothnetpositive+bothSHORTpositive+vol/MDD<=12%; anyfailstops corepoolgeneralization, no lookback/pool/direction scan. Fullrecipepause/NONE remain evenifpass. Source+protocolcommitted before economics. protocols/CSMOM_CORE5_POOL_20261008.json.


## 2026-10-08 CORE5 completed and open-source mechanisms learned

Preregistered253c718/golden635f326 before anynewwallet. Two complete2025seen181d10kwallets,0fits/scans, paired6coinwallets reused. CORE5net+838.90/+842.85;SHORT+315.21/+349.32;vol9.70/9.68%,minuteMDD4.16/4.11%,fee~73.98/execution~107.61,turnover13.45. Retains~70%originalprofit, excludes completePEPEdependence onthiswindow only. Higheractualgross45.59%vs34.36%,vol/turnoverhigher; notriskmatchedalpha. All4gatestrue/2independentpaidflat audits/200shortopeninglegspercase, maxNAVerror1.82e-12. Goldenparent6targets/clock/orderexact before2wallets;sharedloader extraction nofinancialchange. Actualgrosspeak60.966%, noinstantcapguarantee;RAMpeakUNKNOWN,observedsample1.596GB,8GB/swap0/GPU0 enforced duringrun. 140.399sec/20.64MB newowned. SameCORE5 2024negative remains: retainstage-dependent research expert, no realtimeregime selection proven, fullrecipepause/NONE unchanged. No newpool/lookback/gatescan.

Userdocx sourceSHA=d1415bc9dc18e275740465503b8394c7ad940eff803fd7e79c1f9fa78e5f513e. Suggestions read as references, not automatic instructions. Fixed QlibTRA MIT sources confirm market+past-error routing, hardGumbel/argmax notreadysofttradeensemble, sample/daily maturitycutsdiffer. Existingv3market->60dteacher and oldpastfeedback->Hedge do not cover their jointconditional information; currentpositions/cost/horizon mismatch remains a new research question, not a proven financial bug. SharedmultioutputRidge or explicitexpert×market interaction is needed (additive commonmarket cancels expertcomparison); only trulyforwardpredictions can create causalresidual memory. DeePM netportfolio/worstwindow goals and pysystemtrade continuousforecasts/buffer are conditional laterdirections, notsimultaneous changes. Next: align samepool/samerisk frozenexperts' decision/follow/refentry/funding/switch costs and one horizon before a small combinedinformation gate versus market-only/feedback-only. Do notaverageindependentnetPnL into sharedwallet utility or forceweak experts. Next protocol/fits/wallets NOT_REGISTERED_NOT_RUN; no backgroundjob. Core5 reports/CSMOM_CORE5_POOL_20261008.json.


## 2026-10-08 Expert-follow semantic calibration before joint routing

Preregistrationeacdf06, explicitmicrosecondclock4cc312b, monetarytoleranceac0621b before anynewwallet. Frozen originalfirst2024date/CORE5/CSMOMtargets prefix verified,7ownedintervals+8thdaypaidflat,2fundingunits/2wallets/0fits. Native+102.898/+103.188 vsdailyproxy+105.911/+106.193, neterror−3.013/−3.005<5USDT prereg screentolerance. LONG−85.096/−92.053,SHORT+187.994/+195.241; no newrecipe or annualqualification. PricePnLdiff−3.245/−3.243 dominates, costdiff−0.232 offsets, fundingchargediffsmall; no singlemechanismcausality claim. Both independentpaidflat audits,11520minutes,10SHORTopeninglegs, maxNAVerror1.82e−12. Runtime10.749s,~1.42MB,8GB/swap0/GPU0,peakRAMUNKNOWN. Native minuteMDD1.557% vsproxyday0.504%: proxydoesnotcertifyrisk. Actualexit60slaterthanproxyend; c20c077activityhelper extends maturity through supplied lastfill+1us, final11hand/clocktests2.63s pass without wallet rerun. Initial1float-exactassertfailure preserved, amount difference3.7e−13 notledgerbug. marked_net onlyexecution-price valuation, notobservedmark label. Independentreadonlyreview confirmsbridge/scope/limitations. RetainexistingproxyonlycheapseenDEVscreen, no newmodel/strategy adoption/NONE unchanged. Nextregisteredlowcapacityjointinformation test mustdefine marked/currentposition/funding/matureclock/purge explicitly; NOT_RUN. No weeklyforceflatlabels or independentwallet-netaveraging. reports/EXPERT_FOLLOW_CALIBRATION_20261008.md.


## 2026-10-08 JOINT_EXPERT_INFORMATION_20261008 completed

Preregistered fd56bae, retention correction89f0059 and conservative source-bar maturity/symbol-order2c4980c before fits. Same CORE5/four frozen experts, seven-day zero-entry execution-valued reference utility, common rows, full label purge+7day embargo, 3 input ablations/one Ridgealpha10. 12main+12 shifted-label fits,0 wallets,3.362sec server. COMBINED2024 mean40.31/45.84bp vsbest38.69/44.88;2025−.92/−.43 vsbest39.48/39.31. All prereg gatesfalse; no joint increment, pause exactrecipe/NONE. Not sharedwalletPnL/APR/nativeBybit. One placebo cannot imply95pct significance. 7relevanttests2.757s and independent readonly recomputation pass.

Most useful finding: common train starts2022-12-27,266/632 overlapping days,25 weekly validation blocks each seenwindow; major2022bear absent. SOL/XRP eightfeature support starts10-21; seven missing2023-02-18..24 labels cause84days completefeedback loss02-28..05-22. Savedcoef reconstruction(no fits/error<1e-8) confirms2024 CORE5mom200 maxtrainZ10.83, differential contribution−452/−405bp, not causal attribution.2025COMBINED HOLD19/25,CSMOM1;CSMOM−HOLD forecast−104/−105bp vsactual+49/+48. Do not infer noSHORT/regimealpha or addcapacity.

Next finite task: trace only these two source-support holes, separate officialsignal daily OHLCV from minuteexec/mark/funding completeness; count actually recoverable bear mature rows/weeklyblocks. No interpolation/unknownfundingzero/lockedread. Reopen Ridgeonly after genuine support andnewprereg, no alpha/featuregrid. Frozen50/50same-riskabsolute+relative sharedwallet is notcovered byoldBTCaggregation butsecondary untildata cause understood. Mainfit unit success/inactive/dead; no backgroundwork. reports/JOINT_EXPERT_INFORMATION_20261008.md.


## 2026-10-08 BEAR_SUPPORT_REPAIR_20261008 completed

Original26 daily full1440 guard stopped13/34 at ETHmark2022-07-12; keep failed source/state/protocol. New OBSERVED prereg6dc8bbc admits verified actuallyobserved subset only, reuse14 checksumcache, same26URLs,0fits/0wallets.30,240 missingminute additions,21complete+5partialdays(total27missing), oldfinitefundingmarks/oldfiles exact; daily fundingincomplete11->0. Bear2022 mature0->157daily/0->22fixedweeks,train266/632->516/882; old2024/25labels golden unchanged. Source stage30.898s, firstunit26.510s,9tests2.780s; independent actualreadonly review. Adopt derivedinput, noPnL/APR/qualification change. Reopen condition genuinebearsupport met; prereg one originalcapacity originalrule informationrepeat, no model/feature/hyperparameter search. If inconsistent pauseRidge and choose staticabsolute+relative sharedwallet, not blameSHORT. Reports BEAR_SUPPORT_REPAIR_20261008.md/.json.


## 2026-10-08 JOINT_REPAIRED_20261008 completed

事前commit3ee34b3，只有已核官方派生输入改变；原专家/标签/日期/alpha10/7d/purge/门槛/12+12fit预算不变。成熟熊市157日/22周，train516/882，score25周/窗。12主+12错位fit0.710秒，0钱包。联合2024仅+1.192/+1.021bp、capture1.75%/1.57%，2025−45.012/−43.645bp；全部门槛false。独立只读算术及10反例通过。暂停原容量Ridge，不通过扩大模型/改阈值救结果；缺熊市样本不是充分解释。保留修补及SHORT方向。下一固定50/50 SMA200(10%过去波动downscale)＋CORE5 CSMOM真实共享钱包对照；两个seen窗、两资金解释，新增同风险SMA控制，不平均独立收益。新钱包NOT_RUN，投资NONE/CASH。reports/JOINT_REPAIRED_20261008.md。


## 2026-10-08 FIXED_TREND_BLEND_20261008 completed

事前32c4f8e、运行前9de28b2仅lazyimport使目标测试不依赖torch；参数/门槛未改。固定半权SMA200_10pct/CSMOM CORE5、同一10k原caps/成本/2资金解释，8新钱包/4核身份控制，0fit，581.840秒。2024mix净+95.90/+156.68、SHORT−361/−442；2025mix+164.49/+160.66、SHORT+219/+200。所有mix净正且vol/DD<12%，但逐cell净或DD胜每single失败；SMA在2024、CSMOM在2025更强。NO_ALL_STAGE_BLEND_QUALIFICATION不改写；保留透明静态研究对照/风险分散线索，无投资晋级、无regimealpha、无权重搜索。独立12账户算术/8分钟钱包核验及收费终平通过。实际净收益接近两single半权算术，但此算术不是组合回测；净单成本节省约11–19USDT。下一先核其他既有合法阶段源/缺口/币池，再冻结原3条规则延展；PANEL止2025-07-02不可ffill，未注册/运行下一账户。docs/RESEARCH_STATUS.md与reports/FIXED_TREND_BLEND_20261008.md。


## 2026-10-08 FIXED_TREND_EXTENSION_20261008 completed

事前8718a3a；source-defined41/142/184日已见窗口，CORE5/原10列/同10k/成本/caps/2资金解释，18钱包/0fit/搜索。原12target exact golden、未来suffix/列顺序通过。mix净−74..−71/+1087..+1107/+583..+599，6cell全净正与逐cell对两single净/DD门槛失败，原失败不改：PAUSE_UNCONDITIONAL_FIXED_BLEND_RECIPE。CSMOM新3窗净正但原2024H1负仍在，研究候选不是投资资格。2024后半盈利来自多头，mixSHORT−521..−487、XRP清算损失106.72；CSMOMSHORT−1223..−1156、清算损失约398.2，双资金是同事件条件而非独立样本。完整收费终平/18分钟audit与独立桥通过；实际gross小额越60%与MMR/单位假设明确保留。546.106秒、state70.538MB、4worker，peakRAM未知，观察unit2.892GB/parent3.128GB；父coin.slice按原授权补runtime8GB/swap0。下一只读重建XRP目标/保证金/订单/风险时钟再决定最多一个复用风险退出对照，不调权重或模型；NOT_RUN，NONE/CASH。


## 2026-10-08 CSMOM_ABSOLUTE_SHORT_20261008 completed

事前cc02d62403d61c4c6c75f1ef511eb2d85119a46e；XRP相对弱而绝对上涨的已核反例，原weekly21day/K2/CORE5/多头保持，只增加daily own21d<0允许SHORT，释放预算留cash并二次cov仅下缩。5seen窗×2资金解释，10实钱包/10核身份控制、0fit/搜索，343.294秒。冻结gate {"no_liquidation": true, "all_vol_at_most12pct": true, "all_MDD_at_most12pct": true, "each_pair_net_or_DD_improves": false, "at_least8_of10_net_positive": true, "both2025_stages_SHORT_positive": true}，决定PAUSE_EXACT_CONFIRMATION_RECIPE；NONE/CASH。原默认target5窗exact、suffix/列顺序/逐腿不放大、11回归和20行JSON独立桥通过。完整资本、风险/费用/资金和方向增量见reports/CSMOM_ABSOLUTE_SHORT_20261008.md；原亏损/清算/静态mix失败保留。不同资金解释非独立，低gross或更高netbeta不等于同风险alpha。下一依据该配方决定继续固定规则跨熊市源核验或暂停精确配方，不扫exit/模型容量。


## 2026-10-08 CSMOM_CONFIRMATION_DIAGNOSIS completed

0新钱包/fit/搜索，5seen窗/20旧账户真实fills与targets只读。daily gate移除对冲触发额外signed covariance下缩，多头weight-days−9.75%至−14.08%；实付同周全平重开10/2/5/5/7。2024H2 SHORTgross+446.34被LONGgross−474.19抵消；Jul主要丢SHORTgross，2025H2额外cost44.83。不能把关联gatecost或weight-days当美元因果。维持PAUSE_EXACT_CONFIRMATION_RECIPE/NONE_CASH；保留原CSMOM/SMA及SHORT能力，不再扫此类gate。独立review发现LONG首次entry误标ADD，39795e1修正且v1保留，两次只读3.356秒/0钱包。来源/账本SHA及有限桥见reports/CSMOM_CONFIRMATION_DIAGNOSIS_20261008.md。下一优先原相对SHORT逐仓尾部生存/合法退出可行性，只读先核capacity/费用再冻结一个对照；不以避免一次清算宣称盈利。原ATR/selector/mix负结果与各reopen保持。


## 2026-10-08 SHORT_COLLATERAL_HALF completed

Fixed before wallets at ee163df,1recipe/10newwallets/10originalcontrols/0fit/search, five seen stages/two conditional units. Full10k/targets/native binding identity preserved, liquidation-first/paid persistence/normal hard risk. 2024H1/H2 net improves butSHORT negative;2025H1 net−146.66/−146.94,MDD+.7555/.7571pp despite costs down;allvol gate inherited from untouched41d original. PAUSE_EXACT_TAIL_PROTECTION_RECIPE/NONE_CASH. Readonly actualDOGEepisode shows stopMay11→normalexpertresetMay12, originalepisode−538.53 vsprotected−688.33, no originalnewSHORT opens inblock: no evidence cooldown is bottleneck. Preserve capability/history, do not tune threshold/reentry. Main report reports/SHORT_COLLATERAL_HALF_20261008.md contains full inputs/SHA/risk/resources/repro. Next choose structural hedge concentration/beta diagnosis before any single market-hedge contrast; not another exit scan or larger selector. New experiment NOT_REGISTERED_NOT_RUN; no background work. Existing caps drift, funding/MMR/proxy limitations remain.


## 2026-10-09 Temporal two-expert implementation only

One fixed comparison implemented, no economic optimizer updates/native wallets/sweeps: CORE5 real64×existing24+24 masks; shared GRU32 vs matched latest48→96→32, same160→32 head, paired CASH option. Parameters13057/13090 vs12993/13026. Reuse exact own-path objective/request VJP, mapper/risk/costs and paid terminal; 29 causal/gradient/output/serialization/optimizer/atomic-resume tests pass, existing bounded1CPU/1GB launcher reused. Connection notifications followed by successful fresh shells with same PID1 start/boot identity and zero readable OOM counters; causeUNKNOWN, no network/settings changes. Decision CODE_READY_DATA_NOT_READY; restore broader pre-May2024 coverage/real warmup before fitting, preserve seen validation/negative old results and NONE/CASH. Runnable contract and minimal receipt: modules/temporal_two_expert/README.md, TEST_RECEIPT.json.


2026-10-09 temporal source-contract correction: retain original10 aggregate semantics instead of the initially documented CORE5 rebuild; input adapter shifts daily bar start to completion+1day, preserves shorter-history features with per-feature masks, and rejects ready/future relative/regime/eligible_ranker_indices arguments. 35 tests pass; parameter counts/objective unchanged, economic fitting NOT_RUN.


2026-10-09 temporal INPUT_READY: feature bundle d901f130 verified3parts/2246454bytes/concatSHA bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30/CRC. 1581 rows produce1518 real64-day masked windows 2020-03-05..2024-04-30, including365 input dates each2022/2023; no oldready256/future label/economic completeness filter. Input identity8c82406c392b7764ca124028045180cfc63157852fc02b1f8cfcb3c53f549e7f, compact index and full-window audit research/temporal-input-windows-20261009. 46 tests; real-data scaler/model/nativewallet0. Economic episodes/not input dates must be frozen by the separate task before fitting; rich May-June inputs still missing. Named output contract prepared, only existing pair allowed until complementary evidence; NONE/CASH unchanged.


2026-10-09 temporal single comparison: freeze GRU64/latestMLP x NO/WITH_CASH, seed20261009, Adam.001; 778 train dates in5 real complete wallets,61 seen dev; train-only stop and atomic Adam/RNG resume; CPU1/RAM2GB/1024steps/1200s each. Caps are NOT_CONVERGED. READY gates passed; execute exactly4 authorized fits, freeze all terminal heads before seen scoring. See research/temporal-four-fit-20261009/READY.json. Native replay and pool expansion remain separate.


2026-10-09 temporal4fit terminal: exactly4 starts,0 refits; completed steps132/143/349/522. Three unchanged-proxy mark-boundary STOPs, one1200s NOT_CONVERGED. Native classification diagnostic identifies mark drift, not target/opening cap violation: native requires charged capacity-limited reduction, proxy immediately halts. Preserve all original runs; no cap relaxation/restart. Revise boundary semantics and risk-reduction VJP before further affected fitting. Seen61day full PnL exists only for MLP NO_CASH (-517.3883 USDT), others unavailable. All4 snapshots precede seen scoring; no unseen/native or selector-impossibility conclusion. research/temporal-four-fit-20261009/results/RESULT.json.


2026-10-09 charged boundary proxy: keep allfour originals/checkpoints byte-exact,0 resumed/fresh updates. Separate daily continuous surrogate adds explicitly charged mandatory reductions with unchanged caps/costs/mapper and own-path feedback; 15 correction+62 original tests,182-date parity, saved witness and request FD pass. Actual unchanged native scheduler/account synthetic tests cover latency, funding tie, partial capacity, priority and five-attempt expiry. Witness gross.600508086→.594005219 with paid.088131118USDT reduction, not minute-native certification. Daily endpoints/funding tables cannot identify intermediate risk orders; no minute tape in verified transfer. Native-exact resume blocked pending source-bound tape and differentiated bridge; existing Adam/RNG can support a versioned warm restart without a clean-comparison claim. No cap relaxation, oracle, grid or repeated historical wallet. Evidence research/temporal-risk-proxy-v2-20261009; original result/negative seen scores unchanged.


2026-10-09 V2 authorized continuation: allfour saved model/Adam/RNG warm starts pass finite train-only loss/gradient and RNG checks;8 new synthetic safeguards pass. Original sources/checkpoints remain immutable. Same1024 additional updates/1200s per v2 stage, cumulative Adam steps, fresh objective-v2 convergence history, maximum2 independent1CPU/2GB arms/shared8GB/swap0/GPU0. Charged boundary full-fill surrogate explicitly conditional/not minute-native; all4 terminal heads before seen scoring; export frozen requests for the separate complete-tape native task. No June selection or action-pool expansion during this continuation.


2026-10-09 V2 terminal: new321/1024/431/1024 updates, cumulative453/1167/780/1546 Adam steps, all CAPPED_NOT_CONVERGED,0 worker failures. All4 terminal before seen economic scoring. Lost-console coordinator exit120 recovered by score-only export,0 optimizer restarts. Exact terminal checkpoints and canonical native61 requests published. Conditional daily surrogate is not native execution; do not use seen scores to choose extension. One separate matched GRU WITH_CASH short expansion remains authorized. research/temporal-surrogate-resume-v2-20261009/results/RECEIPT.json.


2026-10-09 matched short pair frozen: select GRU WITH_CASH using pre-May loss -.00094994541144 versus MLP -.00091677655390, single MOMENTUM30_SHORT_ONLY using public1291857 training-only recommendation. Both start exact frozenv2 parent model/Adam/RNG at780; matching33 added parameters, newhead age0, control short0, expansion initialr.01. Same778 dates/five whole wallets and unweighted objective-v2, no June choice/winning-day oversampling. Public E5 slots unchanged, short appended5; private active-coordinate adapter proven by zero-append objective/VJP parity and short finite differences. Forced release precedes discretionaryL1.1.34 tests and real preflight pass; exactly2 finite1024-update/1200s stages maximum2x1CPU/2GB/shared8GB. research/temporal-short-expansion-20261009/PROTOCOL.json.


2026-10-09 short pair terminal:395control/374shortupdates,1200s caps,0failures; terminal trainloss-.000963019964/-.001099602080, no convergence/alpha claim. Seen daily surrogate -548.88/-517.07 paidflat is diagnostic, native handled separately. Both E6 request exports public08f1b50,112byte-readbacks pass; prior artifacts preserved. Actual training longest430-day episode measured78.3985% signed projection onto fullgradient (coefficient55.2699%); not a norm fraction. Authorised moderate comparison therefore warranted: one weighted candidate0.5date+0.5equalepisode (longest37.63496%), from identical originalv2parent/Adam/RNG/newhead as frozenunweightedshortbaseline, same1024update/1200s limits, no baseline refit or removed/resampled dates. No June choice.

2026-10-09: Parent steers next comparison from unstarted episode weighting to matched current expert-target/eligibility input ablation; zero weighting preflight/updates, draft preserved outside repo. Review96b917f establishes price-history calendar aliasing. Same four-action pool/unweighted objective; protocol and clock tests before fit. Receipt research/temporal-expert-input-20261009/PRIORITY_CHANGE.json.

2026-10-09: Matched current-expert-input ablation implemented/preflight passed: both13699parameters, same originalv2GRU CASH parent780/model/Adam/RNG; same four-action pool; control18inputblock0 vs canonical VOL/CS/SHORT targets15/.3 + eligibility3 projected18to32. 35focusedtests passed5.69s, source audit confirms savedclocks<=decision andbeforeexecution+60000001us; clockequality retained, no backdating. Frozen45sourcefiles and all three prior checkpointarchives byteequal. Protocol/READY/PRESERVATION/TEST_RECEIPT in research/temporal-expert-input-20261009;0historicalupdates before publication; SOLscale unchanged per7282bc1.

2026-10-09: Expert-input ablation completed: control403/active350 newupdates; both CAPPED_NOT_CONVERGED at1200s, no failures. Identical13699parameter budgets but unequal updatecounts. Finaltrainloss -.001104357671/-.001095256852; seen charged daily surrogate PnL -512.826086/-517.718438, active-control -4.892352; paidflat. Both frozen native61 bundles published51cdac4 with exact18currentexpertinputs/clock provenance; all133changedfiles readbackmatch. 35focusedtests/2actualtransportchecks pass. Previous three checkpointarchives and runtimecode/scaler byteequal. No nativewallets/downloads/weighting/scalingchange/newstrategysearch; separate nativeexecutor remains pending. Results research/temporal-expert-input-20261009/results/RECEIPT.json.

2026-10-09: user authorized one matched exact512-update weighting comparison after unequal capped input ablation. Both explicit expert inputs/pool/model and one preserved pre-ablation model/Adam/allRNG snapshot; only n/778 versus0.5*n/778+0.1 coefficients differ. Resume wall slices until512 each; predetermined train diagnostics0/128/256/512; both frozen before seen scoring; no June-guided variants. See research/temporal-episode-weighting-v2-20261009/PROTOCOL.json.

2026-10-09 weighting v2 completed exact512/512 newupdates, same13699parameter active-input model/pool and byte-pinnedinitial model/Adam/allRNG; two1200s slices auto-resumed, no reset/failure. Commontrainloss date -0.001113022/-0.001113676 and mixed -0.001090355/-0.001093076 (date-trained/mixed-trained); seencharged daily proxy PnL -502.47/-521.17, delta -18.70 USDT, paidflat. No seen benefit in this pair; no convergence or impossibility claim. Both native61 bundles publicde0d594 and147changedbytesverified; nativeexecutor separate. Prior61sourcebytes/65archive members/scaler unchanged. See research/temporal-episode-weighting-v2-20261009/results/RECEIPT.json.
