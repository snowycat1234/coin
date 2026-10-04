# D067 首次测试调用失败（保留）

首次任务 `D067直接窗口退出20与10因果反例` 实际退出1；测试尚未启动、没有市场/账本读取或输出工件。调用传入相对protocol路径，既有runner在 `a.protocol.relative_to(ROOT)` 拒绝该路径：

```text
ValueError: 'protocols/DONCHIAN_EXIT10_20261004_V1_SYNTHETIC.json' is not in the subpath of '/mnt/d/codex/coin'
```

复测V2只把protocol/output参数写为真实绝对路径，保持同一已冻结协议、源码、测试、预算与实验目的，不重写runner、不改通过标准。首次进程任务原字节在STATE保留，模块关闭时将归档并登记真实失败。V2通过与否按其实际结果，不追认首次通过。
