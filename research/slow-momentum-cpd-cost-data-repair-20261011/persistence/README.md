# 模型公开持久保存

用户已明确授权在公开 GitHub 保存项目代码、模型、模拟研究结果与公开行情档案，并要求推送。本次模型保存的具体授权优先于 AGENTS 一般的 STATE 存放约定。只在 `research/slow-momentum-cpd-20261011` 保存；不覆盖 STATE、旧结果或主分支，不强推、不使用 Library。

公开包：[MODEL_STATE_RECOVERY.zip](MODEL_STATE_RECOVERY.zip)，1,067,209 字节，SHA256 `eea641c4cc965ff3d04a93b7aa259874d81bd6cfa2d5711ac7f45dc74a7ab454`。

包内有 18 个完整 model/Adam/RNG 检查点：原 MSE 六个256步模型、原 gross Sharpe 六个1024步模型、本次修复数据成本目标六个64步模型；另有14个已公开模拟研究收据/CSV及自含索引。每个检查点 SHA、参数量、Adam年龄、框架版本和安全加载核验见 [发布前检查](PUBLICATION_PRECHECK.json)；每个载荷的 SHA/字节数见 [原恢复索引](../results/MODEL_STATE_RECOVERY_INDEX.json)。旧索引的 STATE_ONLY 标记保留为当时历史记录；本目录是用户追加授权后的公开保存版本。

发布前完成 ZIP CRC/成员 SHA、路径白名单、18 个 `weights_only=True` 安全加载和张量有限性检查。载荷只包含研究模型、优化器/RNG与已公开模拟结果；严格检查序列化类型、键以及文本凭证/邮件模式，无发现。未包括账户对象、账户密钥、凭证文件、真实账户资料、无关隐私或其他研究目录。

冷验证会从本次不可变公开提交 URL 下载该包到全新目录，使用远端公开行情 parts、冻结 GP/scaler、源码和保存预测；禁止原 STATE 或行情缓存回退。验证只加载并重放现有模型，不拟合 GP、不训练、不选择策略或重新评估研究配方。冷验证结果将追加到本目录；解释器和第三方运行库沿用已记录环境，不称全新机器安装验证。

已下载公开包后，先核验上述 SHA256。按原绝对路径保护检查要求，在新环境以 `unzip -n MODEL_STATE_RECOVERY.zip -d /workspace` 恢复；禁止覆盖现存状态。公开旧价格来源仍使用固定 Git `e0d3400b` 的三个 parts 或既有 Git 对象，模型不再依赖仅本地的不可下载文件。完整训练复现说明仍见 [原实验 README](../README.md)，原 STOP 与全部科学计数保持不变。
