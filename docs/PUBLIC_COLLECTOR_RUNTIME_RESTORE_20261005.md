# D075：恢复原公开采集并保留WSL会话

D075原两路公开采集再次退出后已保存49.37MB原文件/两闭合库，2256来源文件108.03MB streaming SHA全同；单次原.venv/defaultDB/store/source恢复，新两次实际观测同PID、新session、闭合bars/heartbeat与L1检查点推进，errors[]。断档约public31.3分钟/L130.6分钟，不拼健康时间；原退出UNKNOWN。保存与恢复间boot_id变化已证实，systemd服务本身不维持WSL实例存活是官方限制，闲置退出仅可能机制；新增一个正常Windows隐藏WSL前台客户端，内部sleep仍经原bounded共享5GB，重复调用复用同客户端树，未改系统电源/资源/自动登录，未声称跨Windows重启或72h可靠。N/signed/共享账户与D074负增量结论保持；投资NONE/CASH、APR不可评价。最近实扫采用启动前容量检查，细节见docs/PUBLIC_COLLECTOR_RUNTIME_RESTORE_20261005.md。下一有限资金费来源/解析/归一化/结算核对，未启动，不继续混合权重网格。

## 实际修复与限定

D074验收发现PID890567/890568不存在。保存前boot_id=f499bfa6-33f9-47dc-bf1b-7ed18c73c203，恢复后实际boot_id=6857a40e-5d70-45e1-aa5c-7bd1d116d519，证明期间WSL实例启动身份改变，但原退出码/唯一原因仍UNKNOWN。微软官方说明systemd服务不能单独保持WSL实例存活：[原文来源](https://learn.microsoft.com/en-us/windows/wsl/systemd)（本轮只公开文档检索，无API限制重试）。常驻前台客户端是针对该机制的有限修复，未证明所有重启/崩溃都已解决。

Windows helper `scripts/keep_wsl_research_runtime.ps1`启动或复用一棵隐藏wsl.exe客户端树，内部仅原bounded.sh + sleep；Store版System32 launcher与packaged child按父子身份算一棵，Linux实际仅一个sleep。首次复用检查把父子误判为两份而拒绝，修正后复用同host PID40608，没有重复启动或杀别的进程。Windows启动侧仅控制WSL客户端，Python/采集仍在D承载hpc_linux及原5GB/swap0/GPU0守卫内。不创建登录/计划任务、不改电源或用户全局WSL配置；Windows退出/显式终止后的自动恢复未测。

## 保存、来源与独立核对

保存原main/WAL/SHM及可用日志、task、host记录；缺失项按原PRESERVATION清单保留，不捏造文件。SQL只打开衍生副本；两闭合库SQLite backup及quick_check通过，原始文件复核未变化。2256目录成员、bytes与SHA按流式独立核对完全相同；不重复数据QA、不把身份当有效天。330.83s/RSS19247104B。旧2008清单历史不覆盖，新增源仍为L1 v1，不切v2、不重写来源/数据库。

主恢复复用已验收D066薄编排，只改新独占输出/实际2256清单与task匹配的PID+start_ticks，避免新boot复用PID时把旧task当新task。两次采样使用既有状态与直接lifecycle/audit记录核对新会话、源绑定和断档；源哈希与闭合库catalog另独立核对。行情/模型/账户/执行数学未重写，keys/orders/paid/locked/GPU=0。

## 新实时证据

同PID[483, 484]两次存在于原coin-quant.slice；public新session 7，heartbeat推进240312ms；L1 checkpoint推进237102169us、accepted events增52830。两币闭合接收时间均推进。UNGRACEFUL_PREVIOUS_SESSION/RESTART_GAP原记录保留，约31.3/30.6分钟不计连续资格。仅采样证明恢复与推进，feature持久化/健康天/72h/alpha全部不据此认证。

启动前guard总28451150938B，另reserve1GB，预计<32GB；这是原容量实扫时刻2026-10-05T02:17:18.163809+00:00，后续live/Git增长未纳入。当前共享资源{"aggregate_cgroup": "/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/coin.slice/coin-quant.slice", "ram_limit_bytes": 4999999488, "ram_current_bytes": 175656960, "ram_peak_bytes": 351543296, "swap_bytes": 0, "memory_events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0", "gpu_used": false}。原硬5GB/swap0/GPU0和D40/32warn/36stop不变，无新增观察平台。

## 科研决定与交接

D074实际对照仍为HOLD8收益参照/固定组合防御挑战者，三连续段−10.04/+158.98/−163.84USDT、12区间含零；无合格投资候选，保持现金。本模块恢复公开未来输入能力，不制造新收益或资格。下一一次有限资金费单位来源核对，既有HTTP403/451不重试或绕过；未启动市场/训练/HPO。

复现恢复编排见本模块used metadata四阶段脚本及实际清单。不可在现有live数据库重做preserve/launch或重放旧初始化；采集正在真实运行，应先按源码/当前进程接手。正常模块提交推送与精确remote只按后验凭证宣布。
