# FR68：直接复用官方 TS2Vec

## 来源与实际修改

官方仓库 `https://github.com/zhihanyue/ts2vec`，固定commit
`b0088e14a99706c05451316dc6db8d3da9351163`，MIT。
七个原文件、完整LICENSE、官方API URL、Git blob与SHA256绑定保存在
`third_party/ts2vec/original/`及`SOURCE_INDEX.json`。
本地仅改变`ts2vec.py`的三个包相对导入，增加包导出；编码器、卷积、层级对比损失和
上游fit/encode/save/load原样复用。没有自写CPC或masked representation框架。

第一轮采用官方默认320维、hidden64、depth10、lr0.001、batch16，固定CPU。
每fold仅共同fitting段唯一归一化行进行600次上游迭代；同一冻结encoder用于
Ridge(alpha1)与固定LightGBM两个probe。600次是大数据时上游默认迭代预算，
不能把本次smoke的2次迭代记为正式训练。

输入为同一dataset过去256×68窗口。上游双向编码仅能读取这段已观察历史，
不声称内部每个token因果。全窗口池化输出320维，共同labels/scalers/evaluator另行复用。
两个probe及完整市场训练尚未完成。

## 已完成验收

实际三项smoke通过，20.52秒：官方合成fit、输出形状/冻结参数、保存恢复精确一致；
eval确定性/另一批样本不改变本样本归一化；255/257长度和非有限窗口拒绝。
凭证`reports/fast_research/FR68_TS2VEC_SMOKE_20261001_V1.xml`。
根侧来源、原字节/修改范围、NumPy别名和Ruff核验另绑定独立验收JSON。
仅工程接入通过，无市场预测、盈利或候选资格。
