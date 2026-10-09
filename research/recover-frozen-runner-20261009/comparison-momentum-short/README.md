# One fixed momentum short challenge

Freeze one new short/cash mirror of the existing fixed30-day absolute-momentum long/cash source, predating June inspection at commit713618686ac2208f52e9b15fe072a9d5149b25b9. The original long source is unchanged. This is a new COIN hypothesis selected after seeing June, not a reproduced public strategy or pristine out-of-sample result.

A flat asset enters short when its completed daily close is below its close30days earlier. A held short exits on equality or reversal. Exit occurs before entry; no same-day re-entry. Genuine200completed contiguous daily bars are required. No SMA filter. Each active CORE5 asset receives raw−.12, with inactive budget in cash. Keep the original30-day covariance10%annual scale-down mapper, cash-to-expert dailyL1≤.1 ramp, unchanged guard-OFF account and all costs/execution/funding rules.

Freeze four separate fresh10k accounts: May1–July1exclusive2024 (continuous61days), November2022, January2023 and OKXJuly15–October9exclusive2026. May/June are separate monthly attribution within one account, never a June capital reset. All inputs are retained, verified public bytes; no provider downloads. No horizon search, risk increase, additional variant, model fit or automatic promotion. The requested June2%–5% is a research target only.

The hypothesis is that a fixed return-sign test can react to persistent downside without waiting for a fresh20-day low. It may retain shorts through rebounds; earlier response and profit are not guaranteed. Mechanical acceptance uses causal target identity and independent account/source reconciliation, regardless of profit sign. Report net/price/cost/funding, realized exposure/volatility/drawdown, entries/exits and paid terminal closure across all four regimes.

`MOMENTUM_SHORT_PLAN.json` binds source hashes and `MOMENTUM_SHORT_PREFLIGHT.json` binds exact inputs/targets before wallets. Three focused state/equality/future-and-warmup tests pass; all four preflights pass with zero wallets. Publish and verify the remote plan commit before invoking `momentum_short_challenge.py run --case CASE --state STATE --output NEW_DIRECTORY --plan-commit COMMIT`; then run `verify_momentum_short.py --directory NEW_DIRECTORY --state STATE --write`. Use the existing dependency recipe. Each wallet is sequential, one CPU,6GB address space and600seconds; preserve failed prefixes and never duplicate completed wallets.

Input publication times and historical exchange/account rules remain uncertified. Binance/OKX market inputs with the frozen Bybit-style isolated1x account are conditional research proxies. Keep paused hold diagnostics unstarted.

## Completed audited results

All four accounts completed once and passed the unchanged independent financial and actual-market-source audits. Native target arrays numerically match every frozen preflight; only signed zero serialization can differ. Original engine SHA remains318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585. No liquidation, long inventory, provider download, fit, sweep or hold wallet.

| Window | Net USDT | Price PnL | Fees | Execution | Signed funding | Mean / peak gross | Daily annual vol | Minute MDD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| MAYJUN2024 | -64.63 | -47.57 | 13.95 | 20.29 | +17.19 | 11.30% / 29.32% | 7.35% | 3.52% |
| NOV2022 | +92.26 | +146.74 | 2.44 | 3.55 | -48.48 | 4.91% / 7.25% | 8.87% | 1.71% |
| JAN2023 | -210.35 | -204.56 | 2.38 | 3.46 | +0.04 | 3.07% / 12.30% | 2.38% | 2.60% |
| OKX86 | -588.87 | -564.74 | 14.46 | 21.03 | +11.36 | 8.43% / 42.73% | 7.41% | 6.89% |

May net−257.35USDT; June+192.73USDT on June opening NAV9742.65 (1.9782%), leaving the continuous61-day account−64.63USDT. June price+198.68, fees8.02, execution11.66, signed funding+13.73. June actual mean/peak gross17.91%/29.32%, daily annual vol8.01%, within-June minute MDD2.43%. This remains below the2%–5% research target; no retuning.

Earlier response is asset-specific: June momentum entries include XRPJune3, DOGEJune4, BTCJune15, SOLJune15 and ETHJune20. Compared with the saved Donchian short account, BTC/DOGE respond earlier and XRP becomes active, while SOL/ETH respond later. This is a different exposure path, not a uniform faster or risk-matched strategy. Whole-period mean gross11.30% versus saved Donchian6.88%; June17.91% versus11.62%. Do not attribute the larger June payoff entirely to better timing or add independent wallet payoffs.

November gain accompanies a January rebound loss and an OKX86 loss larger than the saved Donchian challenge. The evidence does not establish robust complementarity or justify pool promotion. These periods are known development/conditional robustness history. Stop after this single recipe; no additional variant, model fit or selector comparison authorized by these results.

Full unchanged journals, entry/exit and order-expiry witnesses, monthly economics and independent audits are preserved in `comparison-momentum-short/ARTIFACT.json`. Reassemble with `reassemble_results.py --root comparison-momentum-short --destination NEW_DIRECTORY`; audit each `accounts/CASE` using the included `verify_momentum_short.py`. Omitting `--state` verifies portable journals; actual-source checks additionally need the recovered market inputs. `EXECUTION.json` retains its original pending-audit receipt; the separate `INDEPENDENT_AUDIT.json` is the completed audit evidence.
