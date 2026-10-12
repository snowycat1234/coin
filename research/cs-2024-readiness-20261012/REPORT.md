# 2024 全年固定 CS21／同风险 HOLD：去重与实际来源阻塞

没有找到等价完整2024两钱包，但全年原行情档案已存在于旧公开Git对象；不能据已有分段或不同风险账户声称问题已充分回答。实际新核验确认必须保留的mark缺口仍未修复，因此完整366日经济结果 **NOT_RUN**。没有调参、选择盈利月份、伪造完整清仓或新增重复钱包。

| 2024 来源范围 | 可恢复原档 | 实际验证边界 |
|---|---|---|
| Jan–Jun | d69e9ac9 H1包，60个trade/mark月档 | parts、整个包SHA及目录已核；本模块未重新解析全年CSV |
| Jul–Aug | 001024ce July包，20个trade/mark月档及边界日档 | 已有校验；本模块重放Aug五币月／日mark与真实双洞 |
| September | d69e9ac9 native_20261008三个包，15个trade/mark/funding月档 | 全包SHA及成员目录已核，未冒称新完整分钟校验 |
| Oct–Dec | 152606ad Q4包／原档引用，30个trade/mark月档 | 已发表每币132480分钟完整网格证据，未当作全年账户 |

具体索引、成员路径、整个包SHA及已有账户区别见 [HISTORY_REUSE.md](evidence/HISTORY_REUSE.md)。这避免了原以为缺少Jan–Jun／September而重复下载。仍需的后续工作是全年实际网格、资金费连续性及366日因果目标上下文；当前不在关键缺口未闭合时盲目批量准备。

已有Jan2–Jul2纯CS182日已付费清仓，净亏损−587.381441 USDT；但使用旧Bybit账户，HOLD为gross .6且未共同过去协方差风险匹配，不是当前318a默认USDT的等价全年控制。其他Jan／Apr／MayJune／Q4多为模型、VOL或CS50混合及独立分段钱包，未拆收益、未拼接。

## 实际启动结果

运行代码与协议先发布到 `185b1380a64f432e352a365920a2366b41490ed4`，再启动新来源准入模块：

- 从公开Git恢复已有July包37分片，核整个包SHA与CRC；没有交易所ZIP下载。
- 每币Aug mark月档 **44638行**，Aug12日档 **1438行**。五币均缺 `1723456920000`、`1723456980000`，即 **2024-08-12 10:02／10:03 UTC**；全部1438日／月重叠数值精确一致。
- 实际读取 **10个官方CHECKSUM**，全部与已发布原档SHA相同，所以不是可以靠重复下载修好的旧缓存。
- 历史官方fapi补查已HTTP451地区拒绝；本轮没有重试该API、换host/地区/proxy或使用凭证。记录存在性仍UNKNOWN，拒绝不等于API记录不存在。
- 状态 **`STOP_UNCHANGED_REQUIRED_NATIVE_MARK_GAPS`**；实际8.062195秒，新钱包0、拟合0、旧钱包重跑0、交易所档案下载0，三个准入反例测试PASS0.20秒。

这是针对2024明确问题新增的运行前能力：以原始数值及新官方哈希确认必须来源缺口，阻止错误“全年ready”、重复钱包和无关大档采集。它不是2024经济结果、收益预测器或对所有信息空头的结论。[机器结果](result/RESULT.json) 已发布于 `e8c557255fb0e2c524651f10aefccf584a099418`。

## 公开恢复

新空STATE公开Git恢复已 **PASS**，3.101278秒；原始数值、缺口向量、保存的官方CHECKSUM观察及准入决定精确一致，官方请求／钱包／拟合均0。冷恢复没有重新查询实时metadata，因此不能冒称未来时点档案仍未更新。[PUBLIC_RESTORE.json](evidence/PUBLIC_RESTORE.json) 与guard／日志保存。

最小复现：在干净本分支、既有依赖与公开Git对象存在时，`--state` 换成不存在的路径。

```bash
COIN_CPD_STATE=/workspace/cs-2024-readiness-state \
QUANT_ROOT=/workspace/coin-tail-risk QUANT_STATE=/workspace/cs-2024-readiness-state \
bash research/slow-momentum-cpd-20261011/launch.sh \
/workspace/coin/.venv/bin/python research/cs-2024-readiness-20261012/readiness.py \
  --state /workspace/cs-2024-readiness-state/PUBLIC_COLD \
  --source-commit 185b1380a64f432e352a365920a2366b41490ed4 \
  --expected-commit e8c557255fb0e2c524651f10aefccf584a099418
```

源码SHA绑定与1CPU/4GBAS/2GB采样RSS/8GBhost/无GPUswap/15GiB保留guard不变。STATE总量57435895字节，完成后磁盘17427517440字节，满足固定边界。

剩余实际阻塞是十根必要mark，而不是缺少原始月档或没有启动。完整2024同口径问题尚未得到可认证全年答案；不以旧不等价账户假称已完成，也不因来源缺失否定CS全部能力。保留2023失败、旧456日正面对冲及负面分期、旧短腿强平/残仓/费用资金费条件。锁定2026数据、丢失账本、Library、另一研究、实盘与账户密钥均未使用。
