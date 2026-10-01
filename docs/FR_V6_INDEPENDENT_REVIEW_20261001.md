# FR v6 独立只读复核（2026-10-01 UTC）

复核时间：2026-10-01T16:00:07.2775605Z。本报告独立新增；详细字节绑定见
`reports/fast_research/FR_V6_INDEPENDENT_REVIEW_20261001.json`。
根代理提供的 main SHA 为 `d07afb64449f1a16c55d66474cee741a762b1adb`；
本复核没有运行 Git，故本报告不重复证明远程提交一致性。

结论：未发现阻止当前工程 smoke 的实质模型正确性 blocker。
尚有一个来源文档字段缺口和两个需明确处置的 v6 后续事项。
本结论仅为源码/来源复核，不是 180 日、六个 OOS fold、模型效果或经济门槛验收。

## 固定预算与共同输入

- `protocols/fast_research_v6.json` 精确保持
  `a51adea6ff382128c9d4632280ad31d00c486b165f2ef4019b0a4f508e2e03bd`，
  与 FR63/64 原验收凭证一致。固定 Ridge1/XGB2/TCN2/MLPLOB1/TLOB1/
  TS2Vec 两 probe/River1，共 10 配置、1 seed；没有看到隐含模型搜索。
- 六个 rolling fold 的索引为预定的 0/4/9/13/18/22。两个 primary 和两个
  auxiliary、8 输出、共同目标标准化、深度训练权重 [1,1,.1,.1] 与协议一致。
- TS2Vec `fitting_rows` 从共同 fitting-period 四路同步行逐日取唯一行，
  只含训练截止前已可得观测；行数必须等于共同 feature scaler 的拟合行数。
  官方 `fit` 对此单一历史序列做 segmentation/cropping，不重复物化重叠窗口。
- 两个 TS2Vec probe 共用一个冻结编码器、共同 feature/target scaler、
  `split_indices(fold,"test")` 和 256×68 输入。不同模型重新计算同一个 scaler
  的确定性统计，未使用模型专属输入或测试终点。
- 官方双向 TS2Vec、BiN 和 TLOB 只读取给定的完整过去窗口。末端/整窗表示用于
  预测未来；源码和 adapter 没有宣称各内部 token 逐时刻因果。没有看到未来 token、
  validation/test 自监督拟合或 locked 日期读取。
- 完整 180 日/真实 OOS 和经济评价仍须按清单验收；短段结果继续标记 SMOKE_ONLY。

## Trainer 与资源

`trainer.py` 约 130 行，复用官方 DataLoader/AdamW/gradient clipping；
CPU 2 threads、batch16、accumulation4、最多10epoch/patience3 与协议一致。
验证阶段 `eval/no_grad`，按实际样本数汇总标准化 weighted MSE；
最佳 state 独立保存，恢复最佳 state 后才按相同 test 顺序推理，
再 inverse-transform 到原标签单位。未见验证拟合、shuffle test 或边界泄漏。

末个不足4批的累积组已按实际 microbatch 数量缩放，未发生固定除4导致的小组
系统性缩小。最后 microbatch 不足16行时仍按 batch mean 等权，和严格按组内
样本数求平均略有差别；应记录此尾批约定，不声称它精确等于64样本一次求平均。
当前没有证据表明这个小尾组差异阻止工程 smoke，也不因此改写已冻结 trainer。

数据路径仅缓存至多24日二维 feature/label 表，tabular 为204维、TS2Vec probe
为320维数组，sequence batch 为16×256×68，没有全历史三维窗口数组。
此结构在5GB共享上限内合理；正式 CPU 时间和 peak RAM 仍需实际每阶段凭证。
本复核通过 hpc_linux `bounded.sh` 只读查看 slice 上限为5,000,000,000字节、
swap0。本次小 memory snapshot 出现在根代理确认的 WSL 重启后，不能用来
替代重启前训练峰值或累计资源证据。本复核没有运行训练或开启新观察器。

## 必须落实的记录

1. **来源字段**：`third_party/ts2vec/UPSTREAM.md` 尚缺 v6 §4 要求的
   retrieval date。其 `SOURCE_INDEX.json` 已有精确值
   `2026-10-01T14:41:09.729453+00:00`，补入该日期即可；没有许可证/源码身份不明。
2. **Fine-tune 处置**：v6 §14 有单次 fine-tune，§22/FR68 的第一轮只列两个
   frozen probe。根代理已明确：第一轮不增加第11配置；若 TS2Vec 进入 top-3，
   后续仅允许一个 fine-tune config。应在长清单或模块说明明确“未执行、待晋级门槛”。
3. **FR69 对比范围**：Static linear / River online linear / weekly XGB refit
   必须在同一个 chronological replay 比较；weekly XGB 复用固定 XGB-S 参数，
   预定每7日 refit，成熟标签后拟合。现有六个孤立 OOS 测试周不构成已完成的
   连续 weekly adaptation benchmark，应保留该项待验收，完整完成后再出结论。

AMP 在当前CPU路径关闭与v6资源约束一致；PatchTST、增量树和Hawkes为条件/可选项，
不是当前主线缺少的额外必跑模型。没有提出新增 framework、observer 或 dashboard。

## 冻结与开源来源

- 从 A07/A09/A10、FR63/64 和 FR61 A11草稿凭证合并的97个唯一文件绑定，
  SHA256全部匹配，无绑定冲突；A05 preflight 的17项 source 另行全匹配，
  A06独立审计脚本摘要也与原凭证匹配。此数量范围以JSON列出的精确来源为准，
  不扩称已复核全部磁盘数据或旧市场结果。
- TS2Vec7个、TLOB4个保留 original 文件均精确匹配各 SOURCE_INDEX 的官方摘要。
  两套 LICENSE 与 original/LICENSE 字节一致，copyright 保留。
- TS2Vec adapted `ts2vec.py` 精确等于原文件仅替换三处相对导入；
  encoder/dilated_conv/losses 为原字节。实际调用官方 `TS2Vec.fit/encode`，
  没有新增对比框架。TLOB 保留上游 backbone/attention/BiN，CPU、
  无用绘图导入和BiN必要修正已有来源记录。
- 当前 registry 将包版本与repo HEAD分开列，pytorch-tcn/River 原包修改为0；
  sklearn/XGBoost/LightGBM/Arrow/Polars/SciPy/httpx/NumPy/Torch/einops/narwhals
  均有repo/version/license/用途。已有installed RECORD/LICENSE元数据保留；
  LOBFrame为方法参考、LOBench许可未确认禁止vendor。未发现新增实际import
  的第三方未登记缺口。

本复核仅新增本报告及小JSON，不改源码、registry、overview、protocol、冻结凭证或Git。

