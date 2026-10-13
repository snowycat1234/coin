用户指定的固定组合目标已经生成并发布：已单独风控的原 STATIC50（CS＋HOLD）目标乘0.5，加原始只向下缩放的 SMA200 目标乘0.5。两个完整年度各365天、CORE5同一币序/UTC决策时钟，组合后没有再放大。它是一个钱包的 signed 目标，方向相反的资产在下单前按目标净额合并；实际费用和持仓路径只能由该钱包的 native 账户确定。

原始四份 NPZ **逐字节不变**，可从 `public/ORIGINAL_TARGETS/TARGETS.zip.b64` 或四个独立 `.npz.b64` UTF‑8 文件解码。`INDEX.json` 给出原commit/path/原始字节数/SHA、Base64 SHA和原STATIC50风险证明SHA。导出脚本直接用公开Git对象，未读取大行情、重算任何原目标或使用账户。精确原SHA：STATIC50_2023 `e81bf92d3599a6d3059ab462ac984ed9cc066647b1ea839d6147d2e10c40359f`；STATIC50_2025 `5e525cf65a5519a739d7ce2baf9c83809af44a1b9722f37fcf9891ede79bbf4e`；SMA_2023 `2047463e7be0ea4f086de744018d65924568dbd2e37f5960e75951c32746abf7`；SMA_2025 `595425c86df274c6c6105d058d478d772c75ae75cb9c6d2c3ca8c5b9b4c1d968`。公开原字节在 `5939173c516c9d96f6d23cce6c82160310cba178`，四源与协议绑定。

冻结的目标代码在 `5146a2b04909cf1eb132b913713ba8ffde32c4dd` 先于新数组发布；目标在 `42d5e5c0d4c8845b455134e3a9d8ec2955cabd28`。`input/READINESS.json` 给每年源、风险证明、生成目标SHA。2023目标 `5a1a99b9651320f752347853399d293c27723c25e457335a5759e2e1733c85ad`，2025目标 `c2c4ec2597eac6a0e177b6890ba20391a63dec70572ddd31e6902ce5f5c3e0e3`。全365日历史源时间、币序、合约class、quantity profile、native financial code四文件字节、fee/unit/account contract一致。三项针对反向净额、错误日期/币序、错误值与不放大的合成测试通过。真实目标的组合均值gross 2023为29.0272%、2025为26.5511%，反向币日706/841；这是目标性质，不是收益。已分别受控的 STATIC50 可曾被原控制器向上统一缩放，故公式不得简写成未经该缩放的`.25CS+.25HOLD+.5SMA`。

只读去重覆盖75个当时可读公开head；没有发现完全同CORE5、full2023/full2025、同318a/94Closing/BASE27 RAW1的固定账户。旧BTC三专家、半年度CS＋SMA和分段账户范围不同。一个父侧近期代理head未在本地读取，该边界保留。旧STATIC50与SMA真实账户均保存并作为后续同历史合约的控制路径；两份独立半本金账户的净值数学均值不能代替新组合真实交易成本。

**原生账户在资源门槛处停止，未启动。** 2026-10-13T07:15:48Z实测可用16,206,467,072B；15GiB预留之外100,339,712B。已保存的同类SMA账户最大82,039,556B，公开包最大63,204,609B。按原普通Git提交时工作树数据和Git对象两个副本、1MiB缓冲，首个新钱包连同公开验证预计需要209,497,350B预留外空间，差109,157,638B；两年即使首包公开冷验后对自己checkout部分作sparse排除也至少差254,401,803B。这是保守入场估算，非新组合包大小预测。父侧独立日级代理筛查尚未收到，当前0新组合钱包、0fit/下载/旧钱包重播，不为启动而删原账本或突破预留。`RESOURCE_GATE.json`保存实测/方法；第一次两年合计估算漏算首包Git对象，已修正并保留先前日志，首钱包STOP结论不变。

原生执行入口 `native_wallet.py` 已预备，读取冻结两年 `COMBINED` 而非重新合成原始目标；实际启动前先检查空间、不创建STATE，复用现有源窗口/NativeDailySimulator/Closing和真实目标工厂。它会保留0/90天等genuine checkpoint、完整37位分钟指纹、账本和独立Decimal桥；一个参考门槛合成测试通过。此代码尚未进入真实财务运行，也未完成新组合自身的公开打包/冷恢复，因此不能把它称为已验证的新native结果。`NATIVE_PLAN.json`是后续固定范围，资源和父侧筛查通过后仍需单独正常发布完整原账户与冷证明。

最小可迁移执行包 `public/EXECUTION/EXECUTION.zip.b64` 是108,303B UTF‑8，解码ZIP SHA `74e46ef224145c3348039b219f402032c84c5960714664027a32c16411a949e1`。它装两年冻结 `COMBINED` NPZ、来源/范围协议、未运行的guarded native入口、资源报告和原目标INDEX；其 `INDEX.json`逐文件SHA并列出需从已固定coin Git读取的318a/94等内核字节。真正的12月度minute源缓存约束仍需按已公开来源恢复，不在这个小包里。打包成功后，对原生CLI做一次真实前置门槛检查：`RESOURCE_STOP: reserve margin 99598336, need 209497350; no state created`，退出码1是预期的资源拒绝，`OBSERVED_Y2023/Y2025`均不存在。`NATIVE_PREFLIGHT_01.log`保留实际错误；该检查未打开真实行情/建账户/前进分钟。

父侧后续通报其独立日级代理（同一冻结目标、6/6 Decimal核对）两年均为正：组合2023 +2.57256%/DD9.51094%，2025 +6.00725%/DD6.51659%。这是父侧代理的报告值，本执行环境未复跑或读取其最终报告；原生费用、离散量格、容量、资金费及残仓检验仍是NOT_RUN，不据代理数字改权重。原SMA完整报告准确提交为 `52bd252fe7d26499ea571d77e4ec3de81aecebb3`，路径 `research/sma200-native-20261013/REPORT.md`，两年原native及公开cold已完成。

后续只有在父侧固定代理筛查证明值得运行、且复核有足够预留后，才能使用原完整共享10k钱包：318a NativeDailySimulator/94Closing、BASE27费用及spread/slippage、原实际资金费条件单位1、容量/可用掩码/逐仓1x/MMR、冻结NAV.99 sizing、end−6分钟五次平仓尝试；分别fresh2023/fresh2025，不重新跑旧STATIC50/SMA，不补现金关闭或免费平仓。要报告真实marked与paid、未平仓、费用/滑点/资金费/毛价PnL、实际波动/DD和同端点控制口径。历史场所和资金费可得性仍有条件代理限制。

复核紧凑输入：`git show 5939173c:research/static50-sma-20261013/public/ORIGINAL_TARGETS/INDEX.json`；各 `.npz.b64` 可 `base64 -d` 到独立临时目录，解码SHA应等于INDEX中的原始SHA。生成目标的最小命令是在代码冻结提交的干净检出中，经项目 `research/slow-momentum-cpd-20261011/launch.sh` 调用 `python -m pytest -q research/static50-sma-20261013/test_targets.py` 后调用 `python research/static50-sma-20261013/targets.py`，输出新的 `input/Y2023.npz`、`input/Y2025.npz`。现有目录已有这些文件，不能在其上重复运行；真实目标文件和READINESS已直接公开。所有四源原对象在对应提交可恢复；无Library、凭证、付费、实盘、部署、force push或2026锁访问。
