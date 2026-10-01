# FR69：官方 River 薄适配与共同时间顺序回放

## 固定来源与模型

直接使用发行包 `river==0.26.1`，官方仓库
`https://github.com/online-ml/river`；FR61登记的repo核验commit为
`8fc69a836badf855ccda9e6db157eb9e3819ebdd`，许可证BSD-3-Clause。
发行包与repo HEAD分别记录，不声称二者字节相同。原包没有本地修改；
安装元数据、关键实际源码、LICENSE及RECORD摘要另由本模块凭证绑定。

仅实现固定 `RIVER-1`：一个官方 `preprocessing.StandardScaler`、八个官方
`linear_model.LinearRegression`、八个官方 `drift.ADWIN`，均采用0.26.1默认参数。
八输出采用共同 `[1,1,0.1,0.1]×2` loss权重传入官方 `learn_one(w=...)`。
ADWIN只记录漂移，不触发重置、调参或新候选。没有增量树、自己实现的scaler、
漂移算法、优化器或online framework。

## 数据、归一化与成熟顺序

`fit_river`只接受共同 `CachedSequenceDataset` 与 `Fold`；原dataset、labels、
split与协议均未修改。输入由共同 `dataset.tabular_view`将归一化后的过去256×68
汇总为204维。外部feature/target scaler继续使用同一train-only sklearn实现，
绑定dataset/fold与完整scaler receipt。八输出预测在返回前统一逆标准化为原单位。

官方River scaler属于模型内部组件；它处理已经经过共同外部归一化的204维输入，
仅在完整标签成熟时学习一个例子一次，不能替代或重新拟合共同外部scaler。
不使用可能隐式更新transformer的Pipeline，而是显式调用官方API。

预测时队列只保存共同sample ID、decision、`label_available_us`、不可变原输入副本和
当时预测；不保存目标。完整标签可得时间必须等于decision+310秒。
当前tick先预测，再释放此前已成熟的队列项；八维标准化label完整且有限、
队首顺序及单调clock通过校验后，才允许scaler/regressor `learn_one`。
ADWIN接收当时已保存预测与成熟label之间的绝对标准化误差，不用当前重算预测。

warm-up使用与batch baselines相同的train endpoints，外部scaler已在共同train cutoff
冻结，因此warm-up预测不作为真正在线OOS记录。validation labels不参与在线学习。
test仍按共同chronological endpoints逐条预测；split末尾只释放该split成熟边界以内的标签。

checkpoint只保存于新显式路径，包含官方组件、待成熟队列和时钟；恢复时核dataset、
fold、外部normalization SHA和River版本。使用stdlib pickle，仅从本项目可信、
任务拥有的checkpoint恢复；真实模型不入Git。

## Static / River / weekly XGB比较

v6原文FR69指定 `static linear / River online linear / weekly XGB refit`。
`replay_comparison`直接复用同一fold既有 `RIDGE-1`、`RIVER-1`与固定 `XGB-S`
三组结果，核对test indices、八输出shape与两套外部scaler receipt完全一致。
没有新增模型配置、超参数或搜索。

weekly节奏按共同train cutoff拟合、随后最多七个UTC日test；每个预登记fold分别
使用其共同train/validation cutoff。标准七日test内没有第二次refit，明确记录
`in_test_refit_count=0`。跳过的周没有伪造模型状态或结果，不能把六个选定fold说成
连续180日在线覆盖。历史预测及其共同经济指标仍由统一evaluator验收。

## 实际验收与限制

独立STATE测试目录内的小型合成数据完成六项检查：官方组件与预测先行、
成熟前零统计/label更新；原输入和原预测副本、完整八label及最旧队列顺序；
待成熟队列中途保存/恢复与不中断回放精确一致；未来label在成熟前不能影响预测；
错误shape/NaN/ID/maturity/clock拒绝；实际共同CachedSequenceDataset、外部scaler、
逆标准化和固定Ridge/XGB-S的同indices接线。

首次六项通过，38.33秒，V1 XML保留。运行期间修复Ruff指出的闭包绑定，
用独立V2报告重新绑定最终源码。最终测试凭证为
`reports/fast_research/FR69_RIVER_SMOKE_20261001_V2.xml`；
独立来源及资源凭证为 `reports/fast_research/FR69_ADAPTER_ACCEPTANCE_20261001_V1.json`。

仅工程接入与合成共同回放验收；尚未执行River真实市场fit/replay、180日六fold正式比较
或成本/预测稳定性验收。没有GPU、locked历史消费、真钱、生产或alpha候选资格。
