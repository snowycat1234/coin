实证已完成：STOP_FIXED_REJECTED_BREAK_SCREEN。当前固定假突破反向规则在两个已见开发年均亏损、劣于方向对照且回撤门槛失败；不进入原生验证，不调20日窗口或其他阈值。

| 完整decision年 | FADE净值变化USDT | FOLLOW净值变化 | FADE增量 | 日均增量14日块95%区间 |
|---|---:|---:|---:|---|
| 2023 | −1990.991290 | +1082.045206 | −3073.036496 | [−.00161192442,−.00018745683] |
| 2025 | −1026.919777 | +315.771497 | −1342.691275 | [−.00096427880,+.00020331216] |

FADE以完成日HIGH/LOW刺穿过去20日高低区间、但CLOSE严格收回区间内为事件，次日00:01反向；FOLLOW是**同一拒绝事件的相反方向对照**，不是完整Donchian/Turtle。双边刺穿时不虚构盘中先后，CASH；缺源也CASH并记录UNKNOWN。实际两年双边歧义和输入UNKNOWN均0。原始.12每事件资产，沿用原past30协方差/risk.scale10%/.30/.60。

二者每个目标严格互为相反数，所以同期权重绝对值、活动、预测风险与gross位完全相等；**独立10k复利NAV下美元仓位、交易成本和实现风险不相等**。FADE年化日频vol7.983639%/5.740350%、DD20.497786%/12.246932%；FOLLOW分别7.971113%/5.704412%、4.062098%/2.915754%。FADE价格损益−1508.026826/−686.554606，交易成本509.276513/349.547889，资金费现金+26.312049/+9.182718；FOLLOW分别+1704.267706/+702.546911、590.855943/376.889787、−31.366558/−9.885626。FOLLOW的正点结果保留，不能事后替换假设或作为已选赢家推广。

2023/2025均365个自然decision日。2023活跃组合日120、资产事件164（上破拒绝102/下破62），CASH245日；2025分别100/172（80/92）、CASH265日。两年的>=50组合日/>=100资产事件支持门槛通过，来源/成熟/因果/完整期间门槛通过；FADE净值、增量、CI下界、12%回撤门槛均失败。bootstrap1000次/14日圆形块，种子811744/811745，无训练随机数或参数搜索。

66个公开heads全部可读；有界去重526个相关文本path/blob、199策略源码（28447树路径出现），未识别等价实跑，未展开所有历史压缩blob。旧Donchian/Turtle顺向突破，无收回区间反向；RSI2已有原生61日净−60.751327，dual-speed反转排名已有6钱包负结果，均未重复。父线程对0ef61f5连接器只读审阅没有发现重大信号/方向/资金费/终端算术阻塞；它不是本方测试或来源验证的替代。

源预检直接投影e0d3400b/2023与be48f551/2025真实daily_features的OHLC，均395连续完成日×5=1975实际资产bar。所有成员SHA/CRC和完成日期验证、accepted收盘对真实risk cube位一致，缺口/冲突0。没有从close造high/low。OPEN/p1/实际资金费系数从53357f33公开INPUTS_FINAL复用，包括既有官方Feb24恢复及Jan1已准许边界；不是重新下载或旧金融回放。

事件bar于decision已完成，prior20排除该bar。entry为实际00:01分钟OPEN在decision+60s+1us的全填报价；持有24h，标签保守成熟decision+2日。两年末尾分别延至**2024/2026 Jan1 00:01:00.000001**并收取假定全填终端成本；均为已见开发历史，不称新OOS。bar结束时间是因果可得代理，历史真实到达/原生场所价格可执行性未认证。

这是同成本profile的日频数量代理，每臂独立10k、BASE27每侧.00135、实际原rate/strictly-past mark/事件时间的funding coefficient，终端收费；不是原生共享逐仓/容量/minQty/MMR/实时执行模拟。不得把标记NAV、代理终端或FOLLOW点收益称原生可支付收益。

一固定配方、一source/target准备、4个真正全年参考（.246715s），0fit/原生钱包/旧回放/provider GET。source预检.157930s、目标准备.585321s；4针对性合成因果/歧义/边界/risk测试PASS1.06s，不计作真实市场结果。真实两年未来OHLC与NaN、risk价格与NaN前缀不变和源/符号/目标/risk公共SHA门槛都通过；首次评分前公开0ef61f5。

完整SOURCE/TARGETS/RESULTS三个packet469478B公开16e7784dc77537eab7975bd15cc22cac8de335be。全新Git-only cold .130630s PASS：全部11字节成员/SHA/CRC、来源与目标链、1460保存日记录、独立Decimal现金/price/funding/cost最大误差3.090269085478e−12USDT；0参考计算/fit/provider/原STATE打开。原21真实native快照保持SHA，完成核验见COMPLETION。只回收了已公证的上个融资public clone，不删失败准备或原金融/来源记录。

最小恢复：

```bash
bash research/failed-breakout-rejection-20261012/reproduce.sh restore /workspace/rejected-break-new
```

从相同公开输入重算四个参考（新目录，明确增加4次计算）：

```bash
bash research/failed-breakout-rejection-20261012/reproduce.sh score /workspace/rejected-break-score-new
```

独立分支普通push/远端SHA验证，无强推或其他研究文件改动。守卫/15GiB预留不变；锁缺失不授权，封存2026Mar–Sep和未知保留体未开；没有复原丢失2026Q1/Q2账本、账户/凭证/Library/付费/实盘/部署。项目继续：下一独立候选选择calendar-only weekday条件均值；旧模型已有weekday sin/cos，不能称新原始输入，但66head去重没有发现35个asset×weekday均值对5常数的独立实跑。它需2021/22成熟训练、两年预测增量门槛先行，不能借本模块FOLLOW结果调整参数。
