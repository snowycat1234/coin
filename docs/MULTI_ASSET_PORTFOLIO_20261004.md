# D050：可配置多币共享资本组合

## 问题与当前状态

问题：同一固定的过去30日协方差管理HOLD规则，在评价期之前按流动性/历史可用性选出的约十币池中，是否改善净收益或风险分散？投资候选仍为NONE，投资选择CASH，长期净几何APR未评估。

10是本轮事前登记的起步规模，不是账户/风险/策略能力的永久币种数上限；后续可依据数据与实测资源决定池规模。

评价窗预先固定2024-09-01至2024-10-01前，共30天，已查看历史仍为开发筛选。两币/十币各四条件已经实际完成。历史目录880个候选仅按2024年7月官方日线quote volume排名，选池和200日预热先于新增9月价格读取；100份独立来源格式验收完成。不是按评价期收益挑币，不用今天的上市池。有限历史目录与603条UNKNOWN阻止全市场Top10声明。

## 本版实际实现

- 有序可配置symbols贯穿目标、协方差、账户、成交、资金费、恢复和净值列。目标行用标的身份映射，不排序后盲目zip。
- 账户在一个完整10,000 USDT钱包中同步处理所有标的，先执行各币必要减仓，再竞争增加仓位。abs单币30%、组合gross60%、逐仓1倍、不自动追加保证金保持。
- 正常账户接收逐币数量步长/开仓最小额，并将产品、结算资产、base数量单位、乘数与顺序写入恢复身份。当前真实历史仍用未认证代理规则，不将接口可配置称为已获得历史交易所规格。
- 规则目标逐币200个连续已完成日预热；未合格/缺失标的零新目标，其余标的继续。退出标的保留身份并实际清仓；持仓缺执行价或mark、五次尝试仍无法退出，输出不可评价原因，不丢日期或补零收益。
- 每个UTC日最多1440分钟的价格/mark/成交容量块进入同一账户；日线特征与分钟执行分离。金额和数量仍Decimal，行情float64；无全币aggTrades/LOB、逐币训练或高频张量复制。
- 活动关闭规则直接调用正常账户，活动HOLD直接使用目标接口；删除该路径的金融函数复制/AST改写依赖。历史实验按Git `d5f17f1`及其此前提交复现，旧证据保持。

## 必要验收与失败保留

目标病例已实际完成：有序N3/N10、N1协方差、零净敞口风险、未来扰动、缺预热与成员退出。首次环境入口缺ROOT失败保留，仅修PYTHONPATH后通过，不改金融。

账户首次回归为12通过/1失败，其中10个旧默认两币兼容病例已经通过。失败是新测试把含Decimal字符串元数据的字典当作纯数值遍历，非账本错误。正常修复为按account.symbols读取，旧失败源/任务/报告保持。旧runner通用`old_tests_replayed=false`在这次账户回归不适用，以实际命令/JUnit为准：确实运行过10个相关旧兼容病例，不再重复。

随后3个新账户病例和1个独立组合回放病例实际全部通过，报告[新入口独立验收](../reports/fast_research/MULTI_ASSET_REPLAY_SYNTHETIC_20261004.json)，真实任务5875afad28c647eb844a0bef715e6349/exit0。独立Decimal账本检查真实合成多空成交、费用/正负资金费、反手、共享资本/gross、退出/无法退出和破产停机；整段读取与UTC日块的目标/成交/资金/NAV一致，包含跨块前一分钟容量与部分平仓。金额1e-7/比例1e-10容差保持。这是能力验证，不是行情盈利证据。

两币实际首任务b827c074b39b4251bdfbc3a284c8ed13/exit1在第一笔账户调用前遇到进度接口unit关键字重复，0账户。原源码保存在独立STATE，原protocol/失败报告保持。仅正常修关键字为funding_unit并加reader日期身份检查，金融、日期、成本、risk不改；新任务297cdfd34aac4b1880cd27697fd5a60c/exit0实际完成四账户，每个43,200分钟，terminal实际付费清仓。

### 原两币控制结果

| 情景 | 毛价格损益USDT | 手续费+执行USDT | 资金费USDT | 净USDT | 分钟MDD | 实际年化波动 |
|---|---:|---:|---:|---:|---:|---:|
| BASE/F | 153.18 | 7.39 | -5.07 | 140.72 | 2.014% | 7.810% |
| BASE/P | 153.18 | 7.39 | -0.05 | 145.74 | 2.009% | 7.814% |
| STRESS/F | 153.14 | 11.77 | -5.07 | 136.30 | 2.016% | 7.836% |
| STRESS/P | 153.15 | 11.77 | -0.05 | 141.32 | 2.011% | 7.839% |

F/P是两种未知档案单位的完整情景，不选其一。完整资本10k，净1.36..1.46%，换手约0.547倍；BASE/F平均gross/net18.159%、峰gross22.823%、平均保证金/完整初始资本17.844%。钱来自持仓价格收益，成本和资金费减少净值。独立实际账本复核已完成，见下；30日不作长期优势结论。

四账户回放/保存23.923秒（含容量扫描任务总97.031秒），新进程RSS峰270,925,824B，实采共享RAM峰935,829,504B，内核历史累计峰3,263,008,768B分开记录；新增账户输出16,311,339B。不重置或误称本轮内核峰。首失败/磁盘扫描额外开销另记，不能用成功24秒代替全部执行成本。

独立实际复核e0754872d1e542888d03196db96db311/exit0已完成，[报告](../reports/fast_research/MULTI_ASSET_TWO_CONTROL_INDEPENDENT_20261004.json) SHA955cd50658f17200eeda9519b1990f271f5f50e39e675fb86d1b6d61278f1b76；四金融调用/172,800分钟，金额误差≤7.28e-12 USDT/比例≤7.86e-14。过去协方差目标、共享钱包/逐分钟/日/月/回撤核对通过，不将4独立账户的120“账户日”写成120实际日；评价历史仍30天。没有重跑旧账户/旧QA，21.692秒/RSS258,793,472B。

历史目录首次WSL无网络路由失败保持。正常Windows系统HTTPS访问同一官方索引/桶成功，880历史目录；未改代理、未绕403/451/429、未访问私有账户。正式来源脚本首次只因旧目录guard拒绝正常脚本路径失败，0网络/0价格，保留真实失败后仅修路径guard，再独立任务运行。

### 选池与实际市场来源

选池真实34b895e76e5b4ef188587a4f1b346af3/exit0，报告9b8df895...；279个July排名、603条UNKNOWN（含资格阶段），不能称全市场Top10。冻结顺序BTCUSDT、ETHUSDT、SOLUSDT、1000PEPEUSDT、XRPUSDT、WIFUSDT、WLDUSDT、DOGEUSDT、1000SATSUSDT、ORDIUSDT。按源交易对价格单位记数量，例如1000PEPE为源报价的一个1000PEPE单位，不能当作未换算PEPE个数；normalized multiplier=1不认证Bybit历史原生规格。

首September来源809fbc2b803c4a60b9e9b2a91ff36e1a/exit1在首档完成后遇到trade/mark job目录同名，原档/失败/旧6f10源保持。正常修job加入kind，并按原ZIP/CHECKSUM/receipt/PQ逐SHA继承唯一完成档；不称失败父任务整体通过。新39c8e095dde04d849315cbda32d8dd27/exit0实际30/30角色：23新HTTP下载、6原BTC/ETH接受复用、1失败父完成档精确继承；432,000 trade分钟、432,000 mark分钟、1,170实际fund事件，不假设统一8h、不补零。156.148秒/新来源43,663,788B，WSL RSS199,462,912B/native Windows峰92,909,568B分开记录。

来源独立V1真实fe29b82c.../exit1：8份新资金费QA和旧两份元数据接受后，在日线采集时间字段拒绝Int32全零UNKNOWN；原失败和源码保持。V2只允许该字段的确切未知默认类型，其余CRC/CHECKSUM/EOF、数值、时钟与完整性守卫不改；8份已通过前缀按原SHA复用，不重做绿QA。f5e4c3aa.../exit0完成100唯一来源角色（80新首次QA、20原接受元数据），[来源验收](../reports/fast_research/MULTI_ASSET_SOURCE_ACCEPTANCE_20261004_V2.json) SHA86d44507...、STATE输入manifest SHA48ff8dcd...。这是格式/完整性接受，不能认证原始资金费单位、交易所历史规格或历史发布时间。

### 十币实际结果与池贡献

首十币任务4f6dd1d5.../exit1在账户之前遇到旧日线Int64与新日线Int32采集时间合并错误，0账户；[失败报告](../reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_20261004.json)及旧ecf26e源保存。正常reader仅将此采集元数据统一Int64，新数据仍零值UNKNOWN，原价格、日期、行情、输入验收、资金费、成本、风险与账户不改。未重做选池、来源QA或两币回放。

修后真实task4deb6122266e45339729d9751a3ba9ed/session3602/chunk05c584/exit0，四个共享资本组合分别完整43,200分钟并实际付费末平。[十币实际结果](../reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json) SHA301fa1f0...。

| 情景 | 毛价格损益USDT | 手续费+执行USDT | 资金费USDT | 净USDT | 分钟MDD | 实际年化波动 | 相对两币净增量USDT |
|---|---:|---:|---:|---:|---:|---:|---:|
| BASE/F | 295.88 | 5.18 | -5.55 | 285.15 | 1.427% | 8.139% | 144.44 |
| BASE/P | 295.93 | 5.18 | -0.06 | 290.70 | 1.425% | 8.147% | 144.95 |
| STRESS/F | 295.83 | 8.24 | -5.54 | 282.05 | 1.428% | 8.163% | 145.75 |
| STRESS/P | 295.88 | 8.24 | -0.06 | 287.59 | 1.426% | 8.171% | 146.26 |

[保存账本配对](../reports/fast_research/MULTI_ASSET_PAIRED_COMPARISON_20261004.json)真实task507539380c5c4336a4146ebcdf728a5b/chunk5415fe/exit0，SHAa4dfb946...：策略、风险、金融、成本/单位条件相同，只改变池及其权重/过去协方差输入；CASH0为无风险对照，两个池的HOLD是各自适用的风险管理持有基准。不将这些独立条件账户相加，不事后风险缩放。

钱主要赚在这段市场的多头价格收益：约142.7USDT新增毛价格损益占主要净增量，成本少2.22..3.53USDT，资金费反而多付0.005..0.471USDT。不是调低成本、做空或新策略的改善。BASE/F十币平均gross/net12.683%、峰gross16.276%、平均保证金/完整资本12.059%、峰13.831%；两币对应18.159%/22.823%/17.844%/20.954%。十币名义敞口较低但实际波动8.14..8.17%略高于两币7.81..7.84%，相同caps与10%过去波动目标不能称实际风险完全匹配。

BASE/F分币净贡献：WIF75.44、1000PEPE54.74、ORDI43.05、WLD38.83、DOGE18.65、SOL18.40、XRP13.35、BTC10.74、ETH7.13、1000SATS4.83USDT。WIF/1000PEPE约占净盈利45.7%，不是分散稳定性的证明；五个最大正收益日占全部正日收益46.65%，最大绝对单日占绝对日收益7.98%。逐币贡献来自同一账户账本，完整10k分母，末平已核，不是独立满资金收益曲线相加。

十币独立task143155f69140458bb598df24fd5b45f7/session27066/chunk08cd7f/exit0，[独立实际账本](../reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_INDEPENDENT_20261004.json) SHA05d705e4...。4金融调用/172,800分钟/120账户日（仍30实际日），每条件184成交腿、1,170原资金事件/1,160持仓事件、terminal零。最大金额误差1.0914e-11USDT/比例7.7272e-14，小于原1e-7/1e-10容差；23.744秒/RSS344,961,024B。检查过去协方差目标、有符号共享钱包、逐分钟/日/月/NAV/回撤及已记录订单/资金流水；不把记录账本核对称为真实交易所下单规格或全部市场下单量认证。未重跑两币、旧QA或经济任务，真实exit原元数据另存。

### 小规模与目标规模资源对照

| 同一四条件回放 | 两币 | 十币 |
|---|---:|---:|
| 组合回放/保存秒（不含前置容量扫描） | 23.923 | 69.373 |
| 含扫描总任务秒 | 97.031 | 150.008 |
| 新进程峰RSS字节 | 270,925,824 | 321,875,968 |
| 共享组实采峰字节（含同期合法任务） | 935,829,504 | 1,020,481,536 |
| 内核组历史累计峰字节（非本轮独占） | 3,263,008,768 | 3,263,008,768 |
| 新组合输出字节 | 16,311,339 | 51,187,877 |

五倍标的规模带来约2.9倍回放时间/3.1倍输出、约19%额外进程RSS，当前瓶颈是逐分钟同步账本与输出I/O及容量扫描，未遇内存瓶颈。无需增RAM；仍按UTC日读取，不下载LOB/aggTrades。上述成功阶段之外还实际发生池选择1992.56秒、新来源156.15秒、首次来源验收10.81秒和失败任务，均保留原记录，不能称整轮研究只69秒。下载期native Windows公开HTTP峰92.91MB单列，不伪称在WSL守卫组内。

## 采用与下一步

最终只读工件核对完成：[ROOT](../reports/fast_research/MULTI_ASSET_ROOT_ACCEPTANCE_20261004_V2.json) SHAdd1853ab...，真实task0547eae18fee426f9c7f1c87df221a4d/session44421/chunkd20a75/exit0。核对10个成功角色、8个失败角色、168公开文件/源码绑定与5份D049历史Git源码；19明确STATE目录合计121,220,154B，未读行情数组或重放账本/QA。首次ROOT12d632.../exit1误拒pytest自身latest引用，原报告与源码保持；正常活动核对入口只允许声明的确切同目录指针、不跟随、计93字节自身且不重复计目标，其余链接仍拒绝，冻结磁盘守卫不改。[真实退出](../reports/fast_research/MULTI_ASSET_ROOT_ACTUAL_EXIT_20261004_V2.json)另从已完成任务读取，不由运行中任务自证结束。

源码/协议/失败/小验收报告入Git，原行情、账户大工件、环境、日志和模型仍在D承载STATE。同步以独立后验`GITHUB_MULTI_ASSET_PORTFOLIO_SYNC_VERIFIED_20261004_V1.json`为准；该凭证生成于提交之后，随下一已完成模块入库，不重复改写旧报告。

采用正常N资产、单一共享资本/风险、日块读取和逐币规格能力；保留十币past-risk HOLD为研究基准、BTC/ETH控制及CASH。不晋级任何投资候选，实际投资仍CASH，长期净几何APR未评估。

本轮确认扩池能改变开发窗口经济结论，收益和分钟回撤改善，而日波动略升；不能据此声称长期分散收益。最大的障碍是仅一月、收益集中于高波动标的，以及资金费/Bybit原生规格未知。下一首对照选择紧邻完整2024年10月，保持本次July预选池、规则、资本、风险与四种成本/单位条件不变，保留两币/CASH；先检验价格收益与前三币集中是否持续，不同时换池混淆归因。其后历史流动性更新池是单独对照，检验新入池/退出，最后依据证据决定扩币或改分配。不先扩到几十币/训练模型。已见历史继续标开发，不把新币或新月份称unseen。

Turtle/SMA盈利采用暂停；reopen为完整真实成本下对HOLD的跨状态净增量，能力保留。更大币池/复杂模型暂停，reopen为跨月份暴露、集中度或信号缺陷的具体证据。Bybit原生比较在合法公开输入及历史规则/资金费单位能够核实时重开，不绕限制。

## 事前经济与资源口径

同一固定HOLD规则，不搜索模型/参数。两个池分别在新进程运行四条件：BASE27/STRESS43总往返bp，以及RAW_AS_FRACTION/RAW_AS_PERCENT两种未知资金费单位情景。每个比较账户完整10k，不相加或平均独立满资金账户制造组合。

Bybit VIP0 taker每边5.5bp，Binance USD-M价格/mark/资金费是跨场所代理。资金费档案单位、历史数量规则/MMR及Bybit原生适用性未认证；两个单位都报告，不选盈利解释。相同caps和过去目标波动不代表实际风险相同；分别报告实际波动、MDD、gross/net、保证金、成本、换手与分币贡献。30天不能证明稳定APR。

沿用5GB共享cgroup、swap0/GPU0及D盘40GB守卫。最近实际扫描23,450,954,816字节@2026-10-03T19:00:45.539152Z，按原测量时刻发布8765；随后51.19MB回放输出及复核工件不在该时刻。距离32GB预警尚有空间，40GB硬上限与36GB停止新增保持。

## 可复现入口

```bash
bash scripts/with_task_progress.sh --title '两币控制组：修正进度入口后历史回放' -- env PYTHONPATH=/mnt/d/codex/coin/tools/task_progress:/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/investment/multi_asset_portfolio.py --protocol protocols/MULTI_ASSET_TWO_CONTROL_REPAIRED_20261004.json --run-dir /home/xflops/coin-state/d050-two-asset-control-repaired-20261004 --output reports/fast_research/MULTI_ASSET_TWO_CONTROL_REPAIRED_20261004.json --pool-id TWO_ASSET
```

以上为原实际命令，报告也保存完整绑定。重跑须复制协议并使用新的experiment_id、独立STATE目录与新输出，登记新尝试；旧run/结果不覆盖，不能重复登记旧event ID。复制协议只更换运行身份，经济规则若变化则是另一实验。

十币原实际入口使用`MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json`、`--pool-id LIQUIDITY_TEN`、STATE `d050-ten-asset-portfolio-repaired-20261004`及同名结果报告。配对命令：

```bash
bash scripts/with_task_progress.sh --title '两币与十币保存账本比较' -- env PYTHONPATH=/mnt/d/codex/coin/tools/task_progress:/mnt/d/codex/coin/src:/mnt/d/codex/coin /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python scripts/investment/compare_multi_asset_portfolios.py --control reports/fast_research/MULTI_ASSET_TWO_CONTROL_REPAIRED_20261004.json --pool reports/fast_research/MULTI_ASSET_TEN_PORTFOLIO_REPAIRED_20261004.json --output reports/fast_research/MULTI_ASSET_PAIRED_COMPARISON_20261004.json --experiment-id D050-SAVED-PAIRED-PORTFOLIO-20261004
```

同样只在新运行身份/新输出下重做；本命令说明已实际发生的调用，不能覆盖原报告。
