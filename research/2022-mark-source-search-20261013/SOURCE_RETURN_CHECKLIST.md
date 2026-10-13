# 2022 mark 原始源带回清单

结论：完整12月 mark 月档仍缺5个，July12/13真实 mark 分钟仍缺27个。2022原生源门继续关闭。已知December31的5个官方mark日档现已本地恢复并通过SHA、CHECKSUM、CRC和分钟网格检查；这不替代月档，也不属于新的全年覆盖提升。

## 必须带回的月档原字节

- BTCUSDT: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-2022-12.zip
  CHECKSUM: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/BTCUSDT/1m/BTCUSDT-1m-2022-12.zip.CHECKSUM
  旧receipt SHA256: 03fe4fa0293236aba29e603e4bafcb128c3703f82bc7ef59bb385eb165f0b58a; ZIP bytes: 1062630; 预期44,640分钟
- ETHUSDT: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/ETHUSDT/1m/ETHUSDT-1m-2022-12.zip
  CHECKSUM: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/ETHUSDT/1m/ETHUSDT-1m-2022-12.zip.CHECKSUM
  旧receipt SHA256: 9a9a48993d63f868d30d6a985bdb15033745507caa1e6cf8ed45bbd752c4a9a9; ZIP bytes: 1001888; 预期44,640分钟
- SOLUSDT: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/SOLUSDT/1m/SOLUSDT-1m-2022-12.zip
  CHECKSUM: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/SOLUSDT/1m/SOLUSDT-1m-2022-12.zip.CHECKSUM
  旧receipt SHA256: 88f85dce2ea7596a33f04a71ea563f2f8eb3716c747267bf924f6e7fe6a820b6; ZIP bytes: 897269; 预期44,640分钟
- XRPUSDT: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/XRPUSDT/1m/XRPUSDT-1m-2022-12.zip
  CHECKSUM: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/XRPUSDT/1m/XRPUSDT-1m-2022-12.zip.CHECKSUM
  旧receipt SHA256: 87eece4fa2891ca2b7e2f0186236e6f3ffef3be6a661cc72a33a2a7a81cd4f32; ZIP bytes: 750015; 预期44,640分钟
- DOGEUSDT: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/DOGEUSDT/1m/DOGEUSDT-1m-2022-12.zip
  CHECKSUM: https://data.binance.vision/data/futures/um/monthly/markPriceKlines/DOGEUSDT/1m/DOGEUSDT-1m-2022-12.zip.CHECKSUM
  旧receipt SHA256: 71fac5bfe807208ed476908e9c7203048fb560b919f6bea8d8faf9ef970fbad9; ZIP bytes: 763762; 预期44,640分钟

## 仍缺的真实分钟（UTC）

- BTC：无July缺口
- ETH：July12 12:57、13:07、13:15–13:21、13:52；July13 06:59，共11分钟
- SOL：July12 13:16–13:21，共6分钟
- XRP：July12 13:17–13:21，共5分钟
- DOGE：July12 13:17–13:21，共5分钟

逐个open-ms见JULY_MARK_ROWS_TO_RETURN.csv。既有官方July月/日档并集仍包含同样27个缺口。相同日档重新下载不能补洞；需要带原字节、同venue/合约/mark语义、时间戳、真实观测证据以及可核的重叠记录。

## 验收步骤

1. Return each complete original same-venue Binance USD-M markPriceKlines 1m ZIP together with its actual official CHECKSUM file; names alone and hash receipts do not supply original bodies.
2. Verify SHA256 and size against both the official checksum and the old receipt. A changed official source is a revision needing a separate explicit provenance/overlap review, never silent substitution.
3. Check ZIP CRC, the correct CSV member, 12 columns, duplicate-free timestamps, finite positive consistent OHLC, and exact 44,640-row UTC December minute grid for each contract.
4. Check the recovered December31 daily observations against the same monthly 1m bars field by field when monthly originals are brought back.
5. Return actual observed 1m mark rows for all 27 July timestamps with source bytes, source URL/accountless official provenance, checksum/retrieval evidence and same-instrument semantics; verify overlap with existing bars and preserve any conflicting rows.
6. The already archived July daily files have the same 27 holes. A fresh copy of identical files is not a repair. Trade, index, premium, 5m aggregate, sparse daily checkpoint and modeled mark are not genuine 1m mark replacements.
7. Recheck the complete 2022 trade/mark grid, frozen original Y2023 trade-daily-close parity, funding chronology and actual strictly-prior mark completeness before any financial admission. Completing this checklist does not itself authorize targets, wallets or a new fit.
8. Use only an already authorized source route. If access is refused, stop; do not change host, region, identity or provider to bypass the refusal.

## 已查范围与停止条件

本次查92个公开分支、1,027个可达commit、6,364个Git tree、21,599个历史blob/path版本、46个相关源索引；本地175个ZIP、30,583个目录成员。未找到目标5个月档或额外27个真实分钟。只从明确引用的983,659-byte包复原已知December31日档，未发provider请求、未读受保护2026原始body、未运行目标/fit/钱包。

8个本地thin bundle缺delta base，不能称其全部body已排除；/tmp的一处系统目录无读取权限。公开可达Git完整历史元数据独立补充了路径查找，但不证明不可达对象/旧机器/外部存储中没有原字节。没有更多明确可下载的目标body候选后，停止本轮扫描。
