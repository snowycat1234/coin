原始 SMA200_10PCT 的两个完整历史 native 基准已补齐，均亏损、均有终端残仓；模块完成，不采纳为投资候选。项目继续，旧 CS、CS＋HOLD、FOLLOW 研究证据及所有失败保留。

每年独立10,000USDT共享钱包、CORE5，2023-01-01至2024-01-01与2025-01-01至2026-01-01各365天/525,600分钟。它们都是已见的开发历史，不是新样本外。两年账户各运行一次，没有重跑既有 CS，也没有拼接年度资金。

| 同期账户 | marked净值变化USDT | 全资本累计% | 价格毛PnL | 手续费 | 执行成本 | 实际条件资金费 | 终端残仓USDT |
|---|---:|---:|---:|---:|---:|---:|---:|
| SMA2023 | −661.748659 | −6.617487 | −309.318400 |92.781763|134.955037|−124.693460|89.58|
| 原有CS2023 REUSED |+108.794760|+1.087948|+413.868700|113.367090|164.897850|−26.808999|0|
| SMA2025 |−382.282329|−3.822823|−211.305800|63.967717|93.043934|−13.964879|184.11|
| 原有CS2025 REUSED |+2115.817670|+21.158177|+2431.349600|123.426161|179.532404|−12.573365|2948.39|

执行成本由等额spread/slippage组成。SMA2023各67.47751832，SMA2025各46.52196704USDT。资金费是保存的真实历史费率乘原假设单位1、按实际持仓和past mark结算；单位及发布可得性未获原生场所认证。正负资金费均保留。

SMA2023留下多仓1000DOGE，SMA2025留下空仓100XRP。只有CS2023在原端点paid-flat；其他三者paid现金累计收益为NOT_AVAILABLE。未免费清仓、删残仓、追加终端时间，也未把d046的不同端点尾部拼入全年。净值与净PnL使用原账户完整成本桥，并与独立Decimal重建一致，SMA最大误差6E−36/2E−36USDT。

| 同期账户 | 日收益年化vol% | 全分钟DD% | 最差30日% | 平均/最大actual gross% | 平均/最大绝对signed net% |
|---|---:|---:|---:|---:|---:|
| SMA2023 |12.3558|16.5061|−6.8873|35.7006 /61.6801|6.5479 /41.0972|
| CS2023 |12.2686|14.5362|−7.9511|43.2385 /61.4343|0.0352 /25.0471|
| SMA2025 |10.0906|10.8758|−7.4504|24.3906 /60.1685|1.2242 /25.2292|
| CS2025 |9.4693|4.4668|−2.0926|47.2990 /60.4697|0.0838 /25.3183|

SMA相对CS的marked净值差2023为−770.543420USDT/−7.705434百分点，2025为−2498.099999USDT/−24.981000百分点。2023 SMA的优点是费用较少、最差30日损失略小；年度价格收益、资金费、总收益和DD更差。2025 SMA费用与平均gross较低，年度收益、实际vol、DD及最差30日更差。这是描述性对照；实际风险、方向构成和预算控制规则不同，不能称纯预测alpha的成对收益检验。两年都不能给出同端点paid收益差。

SMA多/空净贡献2023为+1706.150027 /−2367.898687USDT；2025为−178.934173 /−203.348157USDT。COMPARISON.json保留原CS方向明细、全部24个连续月度差异、同期每日配对差异及来源身份。未按年度/方向挑选赢家或删成本。全gross超过60%的短时漂移仍按旧真实风险减仓和容量限制记录，不冒称瞬时caps保证或10%实现波动保证。

实现直接调用main ef67d636中的signed_intents，仅取SMA列：最新已完成且可得close与包含该close的200日Pandas算术均值比较，long/short/equal-CASH。所有200个历史日必须连续、有限且正；raw .6/Keligible，完整CORE5为每币.12，包括方向零的可用资产。过去31个completed closes生成30个simple returns，样本cov(ddof1)×365，.3asset/.6gross caps，10%年风险只downscale，不scale-up。源代码与main字节相同；不是Jesse SMA50/200 hook，没有训练或标签，故本模块无拟合/标签成熟/purge计算。三项合成测试覆盖未来扰动、未知warmup、方向零及风险只降预算；它们不作为真实收益证据。

保留318a原NativeDailySimulator、94b2238条件QuantityGridClosing、BASE27(每边fee5.5bp/spread4bp/slip4bp)、rawfund单位1、one-way isolated1x/no-auto-topup/MMR.005、.99冻结NAV sizing、previous-quote .001容量、可用掩码/风险/真实费用平仓。persist_cash_close=false /final_day_target_zero=false；end−6min五次原生尝试。Binance历史配条件Bybit费用/量格/风险规则仍是跨场所代理，历史原生filters、funding单位、PIT和MMR适用性未认证。

74公开heads/2131去重source/protocol/report blobs未发现等价完整CORE5两年原SMA账户；旧半年度、分段、单BTC或10币303日样本不能拼接补全年。父侧新common-budget agreement每日proxy与本次原downscale-only native边界不同，其结果在freeze前已披露，不改变本规则。原论文Slow Momentum with Fast Reversion的LSTM＋变点机制及传统期货结果已在slow-momentum-cpd-20261011独立适配实验保存；本模块是仓库传统趋势基准补全，不是论文原样复现、Transformer重训或加密收益证明。

来源复用：小历史输入packet来自53357f33，SHA0d2cf51769f2c9444c83b1715c5a6fd730d282e96cc4e84d1feaecf482ffdcd2，只读取completed-close/availability/decision/symbol字段；原生2023/2025源f38617c5/534a18fb，沿用已经独立公开恢复、再次SHA核对的12月度minute NPZ及events/diary缓存。本次0 provider下载/0 raw重新解析。CS2023摘要2c551f86及原账户2ca59d91，CS2025摘要af6d8e14及原账户1ce56127；后者DAILY从原公开packet恢复，不补造缺失摘要文件。四个financial代码字节、完整calendar、source-index、inception config、费用/单位、quantity profile及原terminal flags均核对；CS缺失的BINDING字段由其真实公开snapshot验证。

两份原账户包63,204,609 /62,251,107B，各374members，位于e9f50eab/e79ddb4b。公开冷恢复两次均PASS，保存365原NPZ列码与37分钟字段位身份、genuine账户/调度快照、目标/成交/拒单/资金费/清算/extrema、日序列和独立NAV，0 financial advance/0 original STATE opens。仅RAM解码公开Git transport，不伪称全新机器fresh clone或本次raw重解析。全部23旧真实snapshot＋旧FOLLOW2023＋2新SMA＝26份金融状态保存，所有旧负结果保留。已验证公开副本的reclaim/hardlink及自己公开parts的sparse排除均有证据，Git对象和原账户仍在。

钱包方法计时160.817558/142.612328s，公开cold19.273450/21.346999s；各阶段计时分别报告，不把父子时间双计或解释为整个任务总耗时。预算沿用1CPU/1thread、4GBAS、2GB命令后代sampledRSS stop、8GBhost stop、swap0/GPU0、15GiB预留；共享cgroup未启用的限制显式保留。详细实际采样、磁盘时刻、97条源SHA和26snapshot检查见evidence/COMPLETION.json及GUARDS。一次synthetic fixture失败、一次只读import失败完整保留；源准备一次、金融钱包两次、nativecold两次、0fits/RNG/旧钱包replay，见ATTEMPTS.md。完整仓库测试NOT_RUN。

最小复现：在该研究分支、Python3.12.14及已恢复项目venv中，运行 `bash research/sma200-native-20261013/reproduce.sh`。它仅执行3项相关测试、两次公开native恢复和只读CS对照，不重跑钱包，输出到独立验证STATE。需要全部固定Git对象和上述source缓存；新机器缓存缺失时可加 `--rebuild-source`，调用旧独立进程public-source脚本，拒绝覆盖现有source，这次并未运行。原钱包运行命令和实际source-commit/PID保留在STARTED/binding/log；若研究复跑应使用新空STATE及干净HEAD，不覆盖OBSERVED。首次可运行里程碑代码/protocol e368dedb、目标eacfcaa2、2023完整账户e9f50eab均已及时发布并核远端。

需要独立重新计算钱包时，以下命令在干净HEAD和新空STATE中运行，当前实验未再次执行；原有OBSERVED不覆盖。新source-commit属于重复计算的身份元数据，完整原结果的精确恢复使用上面的publiccold路径。

```bash
science_commit="$(git rev-parse HEAD)"
export COIN_CPD_STATE=/workspace/sma200-repeat-state
export QUANT_ROOT="$PWD" QUANT_STATE="$COIN_CPD_STATE"
for year in 2023 2025; do
  bash research/slow-momentum-cpd-20261011/launch.sh /workspace/coin/.venv/bin/python \
    research/sma200-native-20261013/driver.py --window "Y$year" \
    --state "$COIN_CPD_STATE/Y$year" --source-commit "$science_commit"
done
```

下一个最有价值的问题是对已经两年较好的固定CS＋HOLD/FOLLOW/CS候选完成同端点paid终端闭合与持仓时间、实际风险和已有置信证据核验；SMA保留为传统趋势对照。当前模块没有启动该后续账户、组合配方或调参。保护集2026-03-01至09-01未打开，丢失的2026账本未宣称恢复；无Library、凭证、付费、实盘、部署或force push。
