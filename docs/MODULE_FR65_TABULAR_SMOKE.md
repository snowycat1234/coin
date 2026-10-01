# FR65：共同数据上的三基线接线验收

实际输入为2025-07-01/02 BTC/ETH × Spot/Perp八份官方归档。
共同dataset共有2,355个有效端点；固定短段工程fold的train为1,113个，test为982个。
Ridge(alpha1)、XGB-S(depth3/100树)、XGB-M(depth5/200树)各完成一次拟合，
共享时间划分、204维过去窗口摘要、训练归一化、八目标及测试样本编号。
预测已逆变换为原标签单位，真实预测文件留D盘WSL，不推送Git。

报告`reports/fast_research/FR65_ACTUAL_BASELINE_SMOKE_20261001_V2.json`记录实际参数、
两币IC、各阶段耗时和资源快照。上一轮中断单独保存，未冒充完成。
三项完成耗时约211/254/145秒；该短段处理仍使用D挂载输入。
进程峰值RSS是同一smoke进程累计值，不能冒充各模型独立峰值。

本次验收仅涵盖`trainer.fit_tabular`和真实共同接线。
同一文件中的sequence训练路径尚未市场运行，不计TCN/TLOB正式完成。
没有进行经济评价，没有六个正式OOS fold；两日IC不能说明稳定可预测，
不生成首轮leaderboard，不调参、不消费locked、不产生alpha候选。
