# FR67：官方 MIT MLPLOB/TLOB 的薄适配

状态：工程smoke已通过，根侧来源绑定验收收尾；没有市场训练结果。

上游 `LeonardoBerti00/TLOB` 固定commit
`f1c0af4d81067978914361766db0457a7d8b6a46`，完整MIT LICENSE保留。
仅vendor三核心；原字节在`third_party/tlob/original/`，每个官方URL/SHA/大小在
`SOURCE_INDEX.json`，实际兼容修缮在`UPSTREAM.md`。

没有重写Transformer、attention、MLP或引入上游trainer。修改只有包内相对导入、
显式CPU device、移除无用绘图导入、BiN负y原地重置为上游.01（保留Parameter及optimizer
身份）、feature-axis std<1e-4保护（与上游time-axis保护相同）。
adapter只移除最后3类线性head，连接所有sequence模型共用的8输出head。

固定MLPLOB/TLOB各一配置：256过去桶、68特征、hidden64、layers2；TLOB四heads、
learned positional embedding。研究称trade-flow transfer；不宣称原论文LOB实验复现。
BiN和attention读取已提供的完整过去窗口，没有token级因果声明；端点后的值不能进入dataset。

每方向四项smoke：shape/常量输入/负BiN权重与optimizer身份、过去窗口边界拒绝、
deterministic eval/state_dict恢复、无未来或外部样本归一化。实际8 PASS/25.70秒，
`reports/fast_research/FR67_TLOB_SMOKE_20261001_V1.xml`；测试后仅Ruff格式修缮。
最终共同适配验收绑定vendor原字节、修改后字节、最终测试与共享资源约束。

所有正式模型共用FR64的数据、标签、split、normalization与评价；历史首180个共同日
尚未完成，未训练、未消费locked、未用GPU或真钱。LOBFrame仍只作方法参考。
