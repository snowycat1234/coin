# 共同输入的D盘WSL工作副本

实际D挂载文件元数据检查成为重复样本访问瓶颈。使用stdlib `shutil.copy2`
将当前fold所需、已SHA绑定的Parquet复制到D盘WSL STATE；每次工作副本上限1GB，
复制前仍调用原完整磁盘守卫，原始长期特征仍受8GB限制。
仅替换ShardSpec.path，dataset/split/labels/scalers/sample IDs全部沿用原实现。

实际八文件22,096,957B完成原文件及副本SHA核对；24个真实样本的输入、标签、
ID、价格、时间及整个QA字典精确相同，dataset合同SHA不变。
同一24个暖缓存样本访问实测D挂载0.977845秒、D盘WSL副本0.002873秒，
本次约340倍。该数值只描述此访问段，不是训练或下载整体提速承诺。
凭证`reports/fast_research/FR64_NATIVE_INPUT_SNAPSHOT_20261001_V1.json`。

这是每fold临时文件复制；没有重新实现loader、特征或下载框架。
不得把全体180天巨大窗口张量化。工作目录必须是独占新STATE目录，
结束清理前核对归属；失败副本保留诊断。不修改冻结dataset或缓存源码。
