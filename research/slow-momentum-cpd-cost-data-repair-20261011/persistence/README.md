# 模型公开持久保存

用户已明确授权在公开 GitHub 保存项目代码、模型、模拟研究结果与公开行情档案，并要求推送。本次模型保存的具体授权优先于 AGENTS 一般的 STATE 存放约定。只在 `research/slow-momentum-cpd-20261011` 保存；不覆盖 STATE、旧结果或主分支，不强推、不使用 Library。

公开包：[MODEL_STATE_RECOVERY.zip](MODEL_STATE_RECOVERY.zip)，1,067,209 字节，SHA256 `eea641c4cc965ff3d04a93b7aa259874d81bd6cfa2d5711ac7f45dc74a7ab454`。

包内有 18 个完整 model/Adam/RNG 检查点：原 MSE 六个256步模型、原 gross Sharpe 六个1024步模型、本次修复数据成本目标六个64步模型；另有14个已公开模拟研究收据/CSV及自含索引。每个检查点 SHA、参数量、Adam年龄、框架版本和安全加载核验见 [发布前检查](PUBLICATION_PRECHECK.json)；每个载荷的 SHA/字节数见 [原恢复索引](../results/MODEL_STATE_RECOVERY_INDEX.json)。旧索引的 STATE_ONLY 标记保留为当时历史记录；本目录是用户追加授权后的公开保存版本。

发布前完成 ZIP CRC/成员 SHA、路径白名单、18 个 `weights_only=True` 安全加载和张量有限性检查。载荷只包含研究模型、优化器/RNG与已公开模拟结果；严格检查序列化类型、键以及文本凭证/邮件模式，无发现。未包括账户对象、账户密钥、凭证文件、真实账户资料、无关隐私或其他研究目录。

冷验证已从不可变公开提交 `3d19d879bf4e8466246f9cfd9347acd5b51fc83e` 下载到全新目录。公开 ZIP 与全部32载荷 SHA/字节数、CRC 通过；18个完整检查点严格加载，54个模型×区间重放共42,234个已保存预测值，全部逐位一致，最大绝对误差0。Python打开文件审计未出现原工作区源码、STATE或行情缓存读取尝试。远端下载42个文件、4,764,551B；公开旧行情仅下载三份小型 Git parts，无行情提供方下载。见 [冷重放结果](verification/COLD_MODEL_REPLAY.json)、[逐文件远端来源](verification/REMOTE_DOWNLOAD.json) 与 [完成记录](verification/COMPLETION.json)。

验证只加载并重放现有模型，不拟合 GP/scaler、不训练、不运行钱包、不选择策略或重新评分。模型、源码、价格、十个已核对价格修补值、冻结参数和保存预测均从公开 Git 恢复；解释器和第三方运行库沿用已记录环境，不称全新操作系统或依赖安装验证。全命令18.539秒，重放9.284秒；守卫退出0，无停止，GPU/swap0。RSS是守卫采样值，未认证为推断工作进程的完整峰值；资源收据原样保留。

最小冷恢复命令（先使用该研究分支；`cold_state` 必须是从未恢复过的新目录）：

```bash
cold_state=/workspace/coin-public-cold-example
COIN_CPD_STATE="$cold_state" bash research/slow-momentum-cpd-20261011/launch.sh \
  /workspace/coin/.venv/bin/python \
  research/slow-momentum-cpd-cost-data-repair-20261011/persistence/verify_public_models.py \
  --state "$cold_state" --commit 3d19d879bf4e8466246f9cfd9347acd5b51fc83e
```

Python3.12.14、PyTorch2.6.0+cpu、NumPy2.5.3、SciPy1.18.1、PyArrow23.0.1、pandas2.3.3、polars1.44.2；版本也保存在冷验证结果和发布前检查内。首次命令误填提交SHA，首个HTTP请求404，未下载/恢复模型或执行预测；失败收据与纠正后全新目录的成功收据分别保留，不计新科学尝试。

已下载公开包后，先核验上述 SHA256。按原绝对路径保护检查要求，在新环境以 `unzip -n MODEL_STATE_RECOVERY.zip -d /workspace` 恢复；禁止覆盖现存状态。公开旧价格来源仍使用固定 Git `e0d3400b` 的三个 parts 或既有 Git 对象，模型不再依赖仅本地的不可下载文件。完整训练复现说明仍见 [原实验 README](../README.md)，原 STOP 与全部科学计数保持不变。
