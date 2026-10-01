# FR64：共同数据集的容量受限缓存

原Arrow/Polars数据合同及8项测试、四路真实两日验收保持，原源码不改。
实测24次带额外标签回算的访问耗时20.51秒，因此为正式训练增加单一公共缓存。

`CachedSequenceDataset`继承已验收共同dataset，直接调用同一source验证、
feature_matrix、label_table、split、sklearn scaler和Torch桥接。
使用stdlib functools.lru_cache最多24天；仅缓存`[5s rows,68]`特征与标签表，
不缓存`[samples,256,68]`巨大重叠窗口。所有normalized views共享只读源缓存，
每个样本复制其过去窗口；train-only normalization仍在取窗口后应用。
每次访问核对对应原文件size/mtime；不能用缓存掩盖来源变更。

3项隔离测试/22.62秒通过：reference逐字段、normalized共同scaler/缓存共享、
源变化拒绝。实测比较进一步发现4个QA原始净USDT流量字段存在约1e-9浮点求和差异；
初始“所有dict字节同值”检查实际失败，报告保存，依赖的首轮短smoke停止，未发布结果。

修缮比较合同仅允许原始净USDT流量QA relative<=1e-12或absolute<=1e-6 USDT；
模型float32输入/八标签、sample IDs、价格、时间戳保持bit exact，不能放宽这些字段。
V2真实24样本比较与冷/暖耗时另存独立凭证；该容差不改变任何模型的labels或经济价格。
所有模型共用此缓存版本；没有新pipeline、scaler、representation/online框架。
