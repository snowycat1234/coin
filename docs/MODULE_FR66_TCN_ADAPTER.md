# FR66：直接复用 pytorch-tcn

状态：工程smoke已通过，根侧来源绑定验收收尾；没有市场训练结果。

固定包 `pytorch-tcn==1.2.3`，MIT；上游repo/commit/license见
`OPEN_SOURCE_REGISTRY.md`。独立研究环境 `/home/xflops/coin-state/research-env-v6`
位于D盘WSL，Torch2.7.1+cpu、无CUDA；旧`.venv`、pyproject、uv.lock和执行来源保留。

`adapters/tcn_adapter.py`只构造官方`TCN`，不实现TemporalBlock或causal conv。
S/M固定channels、kernel3、dropout.1、causal、lookahead0、skip connections、NLC。
共同历史输入`[B,256,68]`，末时刻representation接共同`MultiTaskHead`输出`[B,2,4]`。
缺口由共同dataset排除；adapter拒绝不完整mask，不另造scaler、label或split。

四项smoke在S/M各执行一次：形状、修改未来输入不影响过去输出、确定性eval、
同batch另一条样本不能改变本条归一化结果；恒定输入有限值、无BatchNorm。
原真实XML `reports/fast_research/FR66_TCN_SMOKE_20261001_V1.xml`：8 PASS/25.74秒。
Ruff通过。最终共同适配验收会绑定安装metadata、来源与独立终报。

复用范围：官方包零修改，head为本研究新任务的薄预测层。第一轮TCN-S/M仅一个seed，
同一dataset/folds/labels/train-only normalization/metrics/economic proxy；正式运行须
首180个完整共同UTC日。没有消耗locked、GPU、真钱或新执行工程。
