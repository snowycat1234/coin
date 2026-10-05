# D074：固定组合的时间与回撤代价

D074保存四条件八份303日连续日账本已核验；固定组合相对HOLD8三个101日段BASE/F净增−10.04/+158.98/−163.84USDT，四条件同样反转，7/30/60日块全部12描述区间含零。两者最深日终回撤同为2024-12-16峰至2025-04-08谷：8.30→6.34%，到2025-06-30仍未恢复，真实endpoint持续196日、右删失；分钟MDD仍9.06→7.02%，不能混用。组合降低这段跌幅但未证明缩短最长水下期或稳定净增量；HOLD8收益参照/固定组合防御挑战者/十币能力保留，投资NONE/CASH、长期APR不可评价。0新市场/fit/HPO/API/下载/QA，实际主1.03s/RSS91.65MB/共享采样241.81MB，独立0.85s/RSS82.20MB；实扫沿用D073 28.281GB@2026-10-04T20:09:07.247934+00:00，非新扫描。硬5GB/swap0/GPU0不变。下一优先保存两路公开采集退出后的日志/检查点与有限恢复，随后一次资金费原字段→解析→归一化→结算的有限来源核对，减少F/P双情景的不确定性；已有403/451不重试绕过。先查既有官方归档/定义及同timestamp证据，无法确认则给出具体缺口；不继续混合权重/退出网格。尚未启动。详情docs/HOLD_EXIT_BLEND_TIME_20261005.md。

## 钱与风险：没有新投资晋级

沿用同一个303日、同两币、完整10,000 USDT共享钱包的已接受真实模拟路径。BASE/F：HOLD8净541.09USDT，固定组合526.20USDT；gross多10.70、费用及执行多11.55、资金费负担多14.05，合净少14.90。组合实际年波动8.04% vs 8.39%、分钟MDD7.02% vs 9.06%，换手2.60 vs 1.74。毛正但净差不佳，既有成本与资金解释仍是条件代理；不是削去成本保留旧毛收益的新回放。

| 条件 | Sep1–Dec10增量USDT | Dec11–Mar21增量USDT | Mar22–Jun30增量USDT |
|---|---:|---:|---:|
| TWO_ASSET_BASE27_RAW_AS_FRACTION | -10.04 | +158.98 | -163.84 |
| TWO_ASSET_BASE27_RAW_AS_PERCENT | -1.78 | +164.28 | -163.19 |
| TWO_ASSET_STRESS43_RAW_AS_FRACTION | -13.45 | +157.60 | -165.87 |
| TWO_ASSET_STRESS43_RAW_AS_PERCENT | -5.21 | +162.89 | -165.28 |

分段使用各钱包真实上一日NAV，不重置为10k，不相加独立账户。BASE/F各月增量：November+102.21、January+80.17、February+122.53，June−143.82、September−79.88、December−53.00；后段失去的收益抵消防御贡献。交易原因不是因果证据，不能据此删除资产、日期或改权重。D073 November组合自身收益661.46超过全期526.20仍是集中度警示。

## 回撤片段和正确的时钟

HOLD8日终最深回撤8.300749%，组合6.344530%，同峰日/谷日（显示日期为完成UTC计分日）。实际peak_endpoint_us=1734393600000000、trough_endpoint_us=1744156800000000、末端=1751328000000000；真实时钟持续196日，尚未恢复。日终片段不是分钟MDD；本次没有声明所有回撤均改善。末端清仓也不等于净值恢复历史峰值。

正常活动时间诊断仅增加已知D073接受状态与可选episodes接口。起始完整10k在start_us，日NAV在次日UTC endpoint；相等恢复并更新最新峰，恢复日不计水下观察，未恢复保留right_censored与实际末NAV。历史D068默认输出不新增episodes，旧实验依其Git提交复现。

## 时间依赖与证据限度

四条件×7/30/60日圆形块，每项2000样本，共24k描述抽样。全部12区间含零；BASE/F主要60日平均日log增量区间[-0.000191213, 0.000166747]。303日仅约5个60日块尺度，抽样不是新历史，不校正已发生策略选择；看过的开发数据不能称unseen。高度共享多头beta、实际risk不同，不证明独立信号分散、匹配风险alpha或长期APR。

单位F/P未认证、Binance USD-M行情配Bybit当前截图费率仍跨场所代理；原生BBO/历史费区/数量规则/维持保证金未完整认证。并未读取locked或新市场输入。本轮最初读验原两路采集仍存在，验收后段实际PID890567/890568已消失，退出原因UNKNOWN；不将旧running JSON当存活或补健康日数。

## 验证与决定

主体task 862ddde9234e408ab7db8e608c6c1279真实exit0；独立task c67e3900f7e04d929e476d369d1202f2真实exit0。独立Scalar/60位Decimal从8份保存日NAV重建资金/log桥、40月/12段、全部片段、实际日波动与日终MDD；另以手算初始峰/相等恢复/未恢复末端及3×37小样本核圆形bootstrap索引和分位数。未重复24k经验区间端点，不能声称独立重估统计优势。独立作者和活动模块作者不同；root仅运行、核验和封存helper。脚本准备2次失败（编码/外部PowerShell模块路径）均保留任务记录，配置成功冻结后主体与独立各运行一次。

保留HOLD8研究收益参照、固定50/50防御挑战者、原纯择时与十币挑战者；投资NONE/CASH。暂停混合权重搜索、退出/reentry网格；重新打开需要具体机制、新独立时间证据或合法外生执行信息。下一先处理新发现的原两路采集退出：日志/检查点/数据库备份和来源核对后有限恢复，再做有限资金费来源核对；已有HTTP限制不重试规避，不无限跑F/P替代调查，不因此冻结无关研究。单次核对若证据不足，明确缺少官方单位定义或同symbol/settlement timestamp匹配证据，然后再选经济研究任务。

## 复现

原市场路径按D071/D073 Git提交及冻结协议复现。本次在父提交748b4bc1d80fdba5c2f9b794b91f1ada9ed82810与新source绑定下：

```bash
scripts/with_task_progress.sh --title 'D074保存账本时间诊断' -- env POLARS_MAX_THREADS=2 OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONPATH=src:.:tools/task_progress /home/xflops/coin-state/v8-clean-env-20261002-v2/bin/python -B scripts/investment/donchian_time_stability.py --protocol protocols/HOLD_EXIT_BLEND_TIME_20261005_V1.json --output reports/fast_research/HOLD_EXIT_BLEND_TIME_20261005_V1.json
```

输出拒绝覆盖；需隔离Git历史回放环境与新独占输出，不能在当前HEAD绕过父提交/哈希检查。无新增Python库或观察平台；D074 STATE仅独立小结果，无复制市场账本。真实磁盘值沿用上述扫描时刻，后续Git/采集增长不包含。Git交付成功只按后验SYNC_VERIFIED，不提前宣称推送完成。
