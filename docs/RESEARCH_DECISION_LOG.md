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
