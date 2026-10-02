# D036 public pair：只读工件接线（2026-10-03）

scope=SMALL_JSON_AND_STAT_ONLY。无数组／Python／QA／重放／互补性计算。SHA来自已接受小报告；18文件当前stat大小=producer，未重新hash数据。

## 固定selectors与精确目录

S=/home/xflops/coin-state；P=COIN_JESSE_DONCHIAN_2H_SPOT_ADAPTER；H=COIN_JESSE_DONCHIAN_2H_ENTRY_1H_EXIT_SPOT_ADAPTER。下列D为精确绝对目录，文件完整路径=D/表内filename；仅spread8／名义36bp。

| ID | D（S/之后） | 评分UTC／warmup |
|---|---|---|
| 547P | public-long-547d-actual-20261003-v1/CONT547-P/spread8 | 2024Jan1..<2025Jul1／Dec2023 |
| 547H | public-long-547d-actual-20261003-v1/CONT547-H/spread8 | 同547P |
| 122P | bybit-spot-2h-122d-actual-20261002-v2/CONT122-P/spread8 | 2025Aug1..<Dec1／Jul1..<Aug1 |
| 122H | public-donchian-hybrid-bybit-122d-actual-20261002-v1/CONT122-H/spread8 | 同122P |
| 90P | bybit-spot-2h-90d-actual-20261002-v2/CONT90-P/spread8 | 2025Dec1..<2026Mar1／Oct31..<Dec1 |
| 90H | public-donchian-hybrid-bybit-90d-actual-20261002-v1/CONT90-H/spread8 | 同90P |

P/H须替换完整strategy字符串。窗口独立10k、不拼账户／择窗赢家；locked不读。

## 工件（rows复用旧核算，非新检查）

N=daily_nav.parquet；I=minute_nav_inventory.parquet；F=trades.parquet。N为日净值，I含每币持仓，F为实际fills。各行SHA均完整64位。

| ID/file | rows | bytes（当前stat=producer） | SHA256 |
|---|---:|---:|---|
| 547P/N | 547 | 21567 | 50e625ca1e4d7d1cc7424cde6c50ed290f83faf75d437d518634f64d47ebb9a3 |
| 547P/I | 787680 | 26818880 | b26adf238a1dc0c6fc2ed0d6edd02b6342d9043defcdcdf4657f099f3f416845 |
| 547P/F | 395 | 60633 | 4560d67dcec6545713ece5273398e156c63c22bcc0dec25f086c7f225a158c25 |
| 547H/N | 547 | 23316 | 6a57a6d151090fcc62779e2a52982aec3d4cb4f4ef138079d6b33bd327b39f25 |
| 547H/I | 787680 | 26421662 | a3c746ad53e8fef65834ba4dea12bab9ea749155f6f60f45bdec0b5d7b807497 |
| 547H/F | 578 | 83717 | ffce02bad9b8401a0dde701b297c631209fabb61939ed256429c1abe8612b406 |
| 122P/N | 122 | 7308 | 05d0ae3382626e8f3015292ef41284335b591b9af462478b2a2b80d61880ba11 |
| 122P/I | 175680 | 5654727 | 974acf8cb3e1cb999fe91d4587d050900849db0b3b35e9ee08b01e5eb8dccd8b |
| 122P/F | 69 | 17891 | a38f1a6c8a023935a47aef1cac18fb4e4cd3d298e9214731b7214eae1e6daeb2 |
| 122H/N | 122 | 7559 | c8f1f390356b2dc570b5ff2d4d926954f5c82eeee1963a35b03c615283a8fa0c |
| 122H/I | 175680 | 5553494 | 8b59f847567d581eadcebbf17235b924873cfd95e92cb151061bb834b86d9d6f |
| 122H/F | 99 | 21846 | 07e04616df9cb39843b79df9de05d8e0668c7900e156872a57989b111efe5935 |
| 90P/N | 90 | 6503 | 06044a03aa105111b53dca6702bfab1e344a239e35807258c2266095564f9329 |
| 90P/I | 129600 | 4184884 | 596743062ad34230eee946489df8b7c498e5dd874fe2ea41e94533a7a27df313 |
| 90P/F | 65 | 17269 | 0f433bc26a1c15df9c9956f8073a1d621ce8c4babbaf12ff553dbec6a7a20bc5 |
| 90H/N | 90 | 6439 | 4b9d9c7091da4a8af7eab23f22c1db2c6ee33e8ea9c6f92a0c3b3ce667dd2894 |
| 90H/I | 129600 | 4190859 | c82d852ec17a0b1b18a1e9129b67b7a303db242e7c92241f0fdee16ec0bd8dce |
| 90H/F | 64 | 17135 | 01aba32dbf1be0eb9d17bf9e469c1a09cb544772bc7791bfd48f533c1b7402ea |

18文件合计73,115,689B，日表72,692B／fills218,491B。以后按列投影，无需行情或账户重放。

## saved schema与日损益口径

N：date(Date),nav,return,cash,fees,execution_costs,turnover,gross_weight,stale_prices,stale_exposure。date来自UTC评分日最后分钟（23:59）mark，I.close_us为该分钟exclusive close；跨表join需把N.date映射下一UTC00:00，不能同日期直接误接前一天。

I：close_us(Int64),cash,nav,gross_marked_nav_same_quantities,cumulative_fee,cumulative_execution_cost,gross_weight，BTCUSDT/ETHUSDT_quantity及各_marked_notional。N没有逐币持仓；仓位重合从I投影这些字段或按UTC日末抽样，注明时间尺度。

F：execution_us,signal_us,capacity_open_us,symbol,side,quantity,mid_price,fill_price,notional,fee,execution_cost及gross_quantity,position_delta,cash_delta,fee_asset,fee_amount,fee_USDT_mid。quantity是gross订单数，position_delta才是净收持仓变化；不得按quantity假设买入全额进仓。

未来净return相关与USDT日delta须分开；delta=NAV_t−NAV_prev，首日prev=10000。gross=delta＋日fees＋execution_costs，仅同数量诊断。turnover=日notional/前日NAV，不是fills。窗口分别评分；平均旧return不是真实共同资本ensemble。

## 已接受来源／金融匹配

各窗P/H完整config相同：10k、fee10/halfspread4/slip4、倍率1、latency1、caps .3/.6、vol .1、30/min20、participation .001、maxwait5、liquidateTrue、min10、lot BTC1e-5/ETH1e-4；实际risk可不同。finance AST均39ffd9142be81285b3a6b460c73b1c7799c7621a1c34a2f1faa845d290608b73；fee profile均d6c1e2f5b25dabf4d088edfbccbc35d7154684287ff477c2fc16a14ee5f96b3f。Binance代理／Bybit费用，native=false。

相同窗IPC SHA：547=1d1a2e49…／122=e5e00c54…／90=887cc080…；PQ SHA69ee7e5b…／116448dd…／96adcfe7…，P/H一致。source receipt SHA64dc9474…／a8b5389e…／388d3be0…；原SOURCE日历578/153/151，实际PQ含578/153/121日，不能把90的source151日当评分151日。

proof均在reports/fast_research/（完整SHA在原接受绑定）：
- 547 producer PUBLIC_LONG_547D_ACTUAL_20261003_V1.json（c70e3011…）；independent PUBLIC_LONG_547D_THREE_LEDGER_INDEPENDENT_AUDIT_20261003_V3.json（c7033ef2…）。
- 122/90 P producer BYBIT_SPOT_2H_{122D,90D}_ACTUAL_20261002_V2.json（53447ac3…／329f9f92…）；audit BYBIT_SPOT_NATIVE_FEE_SIX_LEDGER_COMPOSITE_AUDIT_20261002_V1.json（70fc1568…）：122复用exit1通过块＋90恢复，非fresh六账本。
- 122/90 H producer PUBLIC_DONCHIAN_HYBRID_BYBIT_{122D,90D}_ACTUAL_20261002_V1.json（9e7727b4…／3b6e1f58…）；independent PUBLIC_DONCHIAN_HYBRID_NATIVE_SIX_LEDGER_INDEPENDENT_AUDIT_20261002_V1.json（a1af8448…）。

仅inventory，D036未执行、无新经济／APR资格。
