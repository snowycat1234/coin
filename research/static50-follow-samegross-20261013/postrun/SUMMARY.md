# Fixed same-target-gross pool comparison

All six new fine cases and three reused original fine S wallets are retained. Report creates zero wallets, advances zero financial steps and reruns zero controls.

New control depends on FOLLOW through G=min(gross(S),gross(.5S+.5F)); it is a new risk-timing control. Equal daily target gross does not establish equal actual gross or realized risk.

## 2023

| Path | Class | Minutes | Marked PnL USDT | Paid PnL USDT | Daily vol | Mean/max actual gross | Residual gross USDT |
|---|---|---:|---:|---:|---:|---:|---:|
| new_control | FULL_PAID_FLAT | 525600/525600 | 556.539615 | 556.539615 | 5.941948% full-calendar | 0.212121/0.453145 | 0.000000 |
| pool_candidate | FULL_PAID_FLAT | 525600/525600 | 1147.629999 | 1147.629999 | 6.438619% full-calendar | 0.211529/0.447819 | 0.000000 |
| reused_original_S | FULL_PAID_FLAT | 525600/525600 | 1159.692494 | 1159.692494 | 10.354854% full-calendar | 0.384193/0.623302 | 0.000000 |

pool_minus_new_control: paid cash delta 591.090383 USDT; same-full-calendar marked delta 591.090383 USDT.
pool_minus_reused_original_S: paid cash delta -12.062496 USDT; same-full-calendar marked delta -12.062496 USDT.
new_control_minus_reused_original_S: paid cash delta -603.152879 USDT; same-full-calendar marked delta -603.152879 USDT.
Pool daily volatility is higher than the new control on the same full calendar: difference 0.496671%; volatility decreased=false.

## 2024

| Path | Class | Minutes | Marked PnL USDT | Paid PnL USDT | Daily vol | Mean/max actual gross | Residual gross USDT |
|---|---|---:|---:|---:|---:|---:|---:|
| new_control | PARTIAL_HALTED | 461654/527040 | 746.345357 | null | 6.271087% observed-prefix annualized | 0.196942/0.431913 | 833.109462 |

new_control halted at 1731766500000000 us; the marked halt endpoint is separate from the last completed-minute prefix.

new_control exact residual quantity: BTCUSDT=0.00091600, DOGEUSDT=694.58611584, ETHUSDT=-0.03186046, SOLUSDT=1.21342937, XRPUSDT=-110.38164094. No free terminal flattening.
| pool_candidate | FULL_PAID_FLAT | 527040/527040 | 971.259446 | 971.259446 | 6.998747% full-calendar | 0.185082/0.430046 | 0.000000 |
| reused_original_S | PARTIAL_HALTED | 461448/527040 | 1512.479478 | null | 10.882834% observed-prefix annualized | 0.362642/0.604024 | 1775.628346 |

reused_original_S halted at 1731754140000000 us; the marked halt endpoint is separate from the last completed-minute prefix.

reused_original_S exact residual quantity: BTCUSDT=0.00195815, DOGEUSDT=1488.70058163, ETHUSDT=-0.06828626, SOLUSDT=2.60073296, XRPUSDT=-236.58004288. No free terminal flattening.

pool_minus_new_control: paid cash delta null USDT; same-full-calendar marked delta null USDT.
Common completed-minute prefix 461654 (close_us=1731766440000000), excluding post-minute halt mark: a marked 747.994987, b marked 948.711271, b−a 200.716284 USDT; observed-prefix annualized daily vol a/b 6.271087%/7.158961%. No annual paid return or cross-horizon endpoint delta.
pool_minus_reused_original_S: paid cash delta null USDT; same-full-calendar marked delta null USDT.
Common completed-minute prefix 461448 (close_us=1731754080000000), excluding post-minute halt mark: a marked 1514.994097, b marked 967.736615, b−a -547.257481 USDT; observed-prefix annualized daily vol a/b 10.882834%/7.158961%. No annual paid return or cross-horizon endpoint delta.
new_control_minus_reused_original_S: paid cash delta null USDT; same-full-calendar marked delta null USDT.
Common completed-minute prefix 461448 (close_us=1731754080000000), excluding post-minute halt mark: a marked 1514.994097, b marked 766.672427, b−a -748.321670 USDT; observed-prefix annualized daily vol a/b 10.882834%/6.271087%. No annual paid return or cross-horizon endpoint delta.
Pool daily volatility is higher than the new control on the same completed-minute prefix, complete UTC days only: difference 0.887875%; volatility decreased=false.

## 2025

| Path | Class | Minutes | Marked PnL USDT | Paid PnL USDT | Daily vol | Mean/max actual gross | Residual gross USDT |
|---|---|---:|---:|---:|---:|---:|---:|
| new_control | FULL_PAID_FLAT | 525600/525600 | 757.887931 | 757.887931 | 5.550901% full-calendar | 0.237539/0.460415 | 0.000000 |
| pool_candidate | FULL_MARKED | 525600/525600 | 990.258332 | null | 5.897814% full-calendar | 0.237422/0.457314 | 3.371376 |

pool_candidate exact residual quantity: XRPUSDT=-1.83117484. No free terminal flattening.
| reused_original_S | FULL_MARKED | 525600/525600 | 1612.841014 | null | 10.135159% full-calendar | 0.446703/0.606422 | 1304.437581 |

reused_original_S exact residual quantity: DOGEUSDT=-5165.64825394, XRPUSDT=-379.11600436. No free terminal flattening.

pool_minus_new_control: paid cash delta null USDT; same-full-calendar marked delta 232.370401 USDT.
pool_minus_reused_original_S: paid cash delta null USDT; same-full-calendar marked delta -622.582682 USDT.
new_control_minus_reused_original_S: paid cash delta null USDT; same-full-calendar marked delta -854.953083 USDT.
Pool daily volatility is higher than the new control on the same full calendar: difference 0.346913%; volatility decreased=false.

Pool volatility did not fall in any of the three matched observed comparisons: it is higher on the 2023/2025 full calendars and the 2024 common observed prefix. The 2024 pool full-year volatility is not directly compared with the halted control’s partial volatility.

## Interpretation

UTC completed-day NAV simple returns, initial NAV 10000; sample std ddof=1 times sqrt(365). Prefix volatility uses complete UTC days only and is not a full-year estimate.
2025 marked-only residue remains marked-only even when small. Same-gross target matching does not remove different fills, costs, funding, actual exposure or covariance.
Original FOLLOW cash-confidence STOP and other strategy STOP decisions remain. These are conditional seen-path observations, not alpha, selection-adjusted/OOS evidence, venue-validated fills or promised APR.
Half-spread and slippage split the existing execution cost equally under the unchanged BASE27 4bp+4bp assumption; this is arithmetic attribution, not additional charging.
Binance observations, derived-mark overlay and assumed Bybit costs/fine grid retain their existing qualifications.
