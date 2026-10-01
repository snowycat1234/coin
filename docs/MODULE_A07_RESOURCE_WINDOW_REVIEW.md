# A07 已闭合资源观察窗口的只读结构审查

## 作用与边界

`scripts/audit_a07_resource_window.py` 审查冻结观察器产生的 `REPORT.json` 与
`samples.jsonl`。它不打开采集数据库、不检查或恢复进程、不接网络、不训练或下单。
所有入口在 `hpc_linux` 通过 `scripts/bounded.sh` 运行，共享 RAM≤5GB、swap0、无 GPU。

终报不存在时返回 `TERMINAL_REPORT_NOT_AVAILABLE`，表示终报尚未取得；不推断采集器或
观察器已退出、窗口已完成。已失败或中断窗口即使结构一致也保持未合格。冻结观察器若在
未捕获的资源/最终磁盘错误中退出，stderr 是另一份故障证据，不能以缺少终报自动重启。

完整 86400 秒窗口的结构审查最多产生 `SAMPLED_24H_RESOURCE_EVIDENCE_REVIEW_REQUIRED`。
该状态只证明收到的采样记录与终报一致，不能证明采样之间的精确资源峰值或连续资源覆盖。
`actual_24h_capacity_accepted`、`actual_24h_quality_accepted`、14/30 天研究审查资格、alpha、
训练许可始终为 false，健康时间 credit 为 0。终末冻结质量审查与独立资源审查仍须另外完成。

## 输入绑定与有界读取

默认固定工程验收 SHA
`79342daab8e447817a6e0120b1d1d4631ae90b9111ccc863c16af55f67c7a873`，逐份核对该凭证绑定的
观察器/采集器源码、既有冻结文件及工程测试/实际短测凭证，结束时复核冻结绑定和终报字节。
输入必须位于 D 项目 `reports/generated`，来源相对路径不得逃出 ROOT。

JSON 拒绝重复键、NaN/Infinity 与浮点溢出。报告≤2MB，每份冻结文件≤4MB；采样流≤10MB、
每行≤32000 字节、最多 5000 条。逐行规范序列化并核对 seq、previous SHA、记录 SHA、
全流 SHA、首末记录及终报摘要；只保留首两条、首末样本和固定规模的峰值/计数。
这些 SHA 属于本地完整性绑定，不是外部签名或真实行情来源的独立证明。

每个样本核对同一 PID/start_ticks/live session/完整来源 binding、单调 CPU/事件/特征/
manifest/audit/时钟计数，验证短 SQL 读已释放、采样时检查点年龄、数值类型与界限。
重新计算 CPU 差值、单调跨度、已提交特征字节增量、最大间隔、各采样峰值、raw 未知数。
raw 预算耗尽必须为 None；部分已知字节不能当作一个完整样本、0 或精确峰值。

RAM 校验有效限额/当前量/历史峰值≤5GB、swap0、无 GPU 和完整 OOM 三项计数均为 0。
磁盘逐份验证端点的完整项目＋整个 VHD 加和、40GB 硬界/36GB 停止新增及 D 盘 4GB 应急
余量；中间样本只有整个 VHD，不能冒称每个时点均扫描了完整项目。
采样间隔超过预定 period 的数量、最大实际间隔和超出秒数明确列出，不设置未经登记的
稀疏样本合格阈值，也不借端点和 period 宣称连续覆盖。

## 可选凭证与入口

`--launch` 关联启动凭证，核对工程验收 SHA、窗口路径、预定跨度/频率以及完整首两条
记录与起始两条跨度。`--quality` 只固定质量报告原始 SHA 和状态用于后续关联，不读取或
提升其 coverage 资格。所有输出均独占创建，不覆盖此前成功或失败证据。

```sh
scripts/bounded.sh .venv/bin/python scripts/audit_a07_resource_window.py \
  --directory reports/generated/A07_RESOURCE_OBSERVER_SHORT_20261001_V5 \
  --output reports/A07_RESOURCE_WINDOW_REVIEW_新的UTC时间.json
```

实际 24h 窗口仍运行期间可以取得“终报未取得”报告；它不会检查进程是否停止。
闭合后可追加 `--launch reports/A07_RESOURCE_WINDOW_START_20261001.json`，保存另一个新报告。

## 工程验证

测试全部在 `/home/xflops/coin-state` 的独立临时目录创建显式合成夹具，只替换本测试隔离
加载模块的 ROOT。工程验收哈希 override 仅允许 ROOT 在 native STATE 内并明确标记
`engineering_fixture_hook=true`；默认生产入口固定真实凭证 SHA，合成夹具无真实资格。
测试不污染实际 ROOT、数据库、来源或运行中观察窗口。

覆盖重算摘要、链损坏/非规范/重复键/读取上限、已重算 SHA 的来源/会话拼接和计数回退、
RAM/swap/GPU/OOM/raw/feature/磁盘界限、全未知 raw、零样本失败、无终报、真实资格错误
提升、稀疏合成 24h 及启动首两条污染。逐次调用核对全部夹具输入字节保持不变。
聚焦测试与实际短测/当前窗口的核验报告由主代理独立保存和验收；合成测试不代替实测。
