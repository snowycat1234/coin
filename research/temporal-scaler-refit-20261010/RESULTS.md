# Single normalization ablation: completed, limited improvement

Frozen model commit: 2d280cbba43158157890fd9280a9e1038724696e. Explicit import-only scoring launcher: 2f2ffc8fad197b77302f25b9a90c88c17a27ce74. Training: 1137 active daily intervals, six separate wallets, 256 updates, one seed, 13,699 parameters; 667.09 seconds on one CPU, peak RSS 819 MB. Only standardizer changes from 907 to 1273 unique training-window dates. Training ends before May 2024. No clipping or deletion of legitimate 2021 extremes.

| Historical development period | old 1137/907 net USDT | new 1137/1273 net USDT | new cumulative | old/new daily DD | old/new mean opening gross |
|---|---:|---:|---:|---:|---:|
| 2024 July 1–September 1 paid close, 62 active intervals | -22.98 | -9.05 | -0.0905% | 3.973% / 3.978% | 9.976% / 10.139% |
| 2024 October 1–December 31 paid close, 91 active intervals | 1168.87 | 1263.71 | 12.6371% | 1.188% / 2.005% | 9.154% / 11.508% |

Both fresh 10,000 USDT CORE5 wallets: BTC, ETH, SOL, XRP, DOGE. Fee 5.5 bp, half-spread 4 bp, slippage 4 bp each side; signed archived funding; paid terminal flattening. July total execution costs 9.262892, funding -8.093871, price PnL 8.303944. Q4 costs 15.188074, funding -43.585047, price PnL 1322.479518. Isolated 1x context, 60% target gross / 30% asset cap, but daily full-fill surrogate; this candidate has not passed native minute wallet/liquidation validation. July archived minute marks remain incomplete.

Improvement versus same-history old normalizer: +13.92 USDT in July and +94.83 in Q4. Q4 drawdown and exposure rise. This is not established risk-adjusted selector improvement. New July mean applied SHORT weight is only 0.1438%; Q4 is largely long exposure. Normalization alone has not solved regime selection.

Reused controls, no reruns: July Static50 +137.07, Cash50 +104.64; Q4 Static50 +1446.98 (DD 1.812%, gross 16.748%), VOL +1266.22 (DD 3.200%, gross 15.139%), Cash50 +732.28. These are reproducible strategy controls, not a sample of all Bybit robots. New model is 183.28 USDT below Q4 Static50 and 146.13 below July Static50; risks differ, so no same-risk superiority claim. Older 773/907 model July +40.26 remains better than this candidate, while Q4 was +984.82.

Verification: 155 saved rows independently reconcile quantities, returns, costs, funding, NAV and drawdown with maximum PnL error 2.38e-12; zero verification wallet or model reruns. Exactly two model inferences and two fresh historical wallets after public terminal freeze; model, Adam and RNG unchanged. An initial import error occurred before any output directory or inference and is preserved; separate launcher repairs only the import, leaving frozen sources unchanged.

All periods have already informed development. These are cumulative historical returns, not APR, CAGR, untouched OOS, simulated live or live returns. Reliable live APR cannot be estimated. Neither majority-Bybit outperformance nor production readiness is established.

Next useful action: inspect saved daily decisions and expert-relative advantages by regime, then test whether prior-only volatility/trend/position information predicts the relative strategy advantage with temporal held-out blocks. Do not repeat this fit or expand a parameter grid based on these two outcomes. Distinguish deliberate risk exposure from predictive allocation skill; current larger Q4 profit is accompanied by more long exposure and drawdown. Preserve negative evidence and source-bound accounting tests.
