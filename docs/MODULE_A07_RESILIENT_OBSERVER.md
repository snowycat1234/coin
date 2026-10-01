# A07 冻结资源观察器的独立异常凭证包装器

## 缺陷与处理范围

已冻结观察器的原异常捕获不包含 `RuntimeError`；实时 `resources.status()` 的资源拒绝和
初始化/结束时 `disk.check()` 的异常可能导致原 `REPORT.json` 未生成。新增
`scripts/observe_a07_resources_resilient.py` 保持原文件、PS 启动器、工程凭证和正在运行的
24h 窗口字节不变，为今后明确启动的新观察尝试保存独立异常凭证。

包装器先通过 `open('x')` 独占保留另外一个 `ROOT/reports/*.json` 输出句柄，再核验来源并
调用原观察器 `main`。原目录、原 REPORT 和 samples 从不被修补、覆盖或删除。输出不能在
采样目录内。包装器不预建采样目录，不改现有 owner 路径，不检查、终止或重启采集器，
不接网络、不训练、不读取锁定价格，不增添 PS 启动器。

正常返回也只产生 `RESILIENT_WRAPPER_ENGINEERING_RETURN_ONLY`，错误统一保存未合格
`RESILIENT_WRAPPER_FAILURE_UNQUALIFIED`。全部真实容量/质量、alpha、训练、健康时间资格
保持未授予。此模块未授权替换已运行的冻结观察器或重新开始当前 24h 计时。

## 来源与生命周期

默认工程凭证固定 SHA
`79342daab8e447817a6e0120b1d1d4631ae90b9111ccc863c16af55f67c7a873`，核对凭证固定的八个
源码/测试/文档来源和既有冻结文件。原 main 从再次核验 SHA 的源字节直接编译，使用完整
原函数；不依赖缓存字节码。实际委托参数为原入口的 `--directory`、`--seconds`、`--period`，
结束后恢复调用方 argv，并再次保存包装器自身及原来源的字节绑定。

初始化、中途或终末异常保存类型、最多 2048 字符原因和最后八个 traceback 位置；不保存
环境变量或帧局部数据。`SystemExit` 保留退出码，`OSError` 和中断也留下独立未合格凭证。
当前 RAM 状态能读取时保留首末资源记录；资源读取失败仍保存错误，不转为成功。

原 main 的冻结控制流在独占 `folder.mkdir()` 成功之后才赋值 started/head/count/
bytes_written。异常时只核对该函数 traceback 中这组局部标记是否已存在，作为该调用已
创建目录的保守判断；不序列化局部值、不改变原函数。成功返回则依赖原冻结 main 的完整
控制流。初始化失败、原目录已存在或 mkdir 竞争失败都不读取或归属其他窗口工件。

确定本调用已创建目录后，原 REPORT≤2MB、samples≤10MB，逐块有界只读保存字节数及 SHA；
过大或不可读工件保持 `NOT_VERIFIED`，不被截断或替换。原终报不存在明确记
`NOT_AVAILABLE`，包装器异常凭证不会伪造一个原终报或宣称该进程已停止。原终报已失败
并抛 SystemExit 时，两份旧工件保留原字节，另存独立错误凭证。

工件存在性检查与 stat、读取均在工件级捕获范围内。PermissionError/EIO 属于未验证读取，
不能冒称工件不存在。整个工件捕获和结果处理另有外层防护：意外框架异常保存
`artifact_capture_framework_error`、工件 `NOT_VERIFIED`，继续结束来源/资源检查并写出独立
未合格凭证；此类读取/框架错误不被误标为来源损坏。原 21 项保留，新增隔离 Path 别名的
exists/stat × EACCES/EIO 四项和外层框架异常一项，合计 26 项；实际结果以独立 V3 XML 为准。

初版真实 V1 的原样本/终报、独立包装器凭证及 V1/V2 测试均保留；初版三文件的旧字节
保存在 `legacy/a07_resilient_before_io_guard_20261001/INDEX.json` 所绑定路径。初版短测成功
不能代替修缮版的最终验收，修缮版须使用新实际 V2 和独立凭证，不覆盖真实 V1。

独占预留文件不能防止强制 kill、OS/磁盘写失败：这种情况下可能剩下空预留文件，空文件
不是闭合报告或工程通过。采样哈希关联仍需原结构审查器另验，不能代替24h真实验收。

## 入口与测试

所有运行通过 D 盘 `hpc_linux` 的 `scripts/bounded.sh`，共享 RAM≤5GB、swap0、无 GPU。
新目录与独立报告示例：

```sh
scripts/bounded.sh .venv/bin/python scripts/observe_a07_resources_resilient.py \
  --directory reports/generated/A07_RESILIENT_新的UTC时间 \
  --seconds 60 --period 10 \
  --output reports/A07_RESILIENT_新的UTC时间.json
```

测试仅在 `/home/xflops/coin-state` 的新目录中创建明确合成来源、回调和工件；只替换隔离
加载的包装器模块 ROOT。哈希 override 与合成 delegate 须成对出现并限制在 STATE，明确
标记工程夹具；CLI 不暴露这些 hook。测试没有调用真实采样 main 或接触当前在线窗口。

聚焦验证三个阶段 RuntimeError、原失败/SystemExit、成功原参数、旧目录/竞争/输出冲突、
来源不符与执行中来源变动、路径逃逸、读取界限、异常文字/trace 界限及旧工件字节保留。
真实短测和最终工程验收由主代理另存独立凭证，合成测试不代替实测。
