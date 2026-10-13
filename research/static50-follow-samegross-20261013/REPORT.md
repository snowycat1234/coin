# Fixed STATIC50 + FOLLOW pool: audited conditional result

Six fresh 10,000-USDT fine-grid accounts were run once, two fixed arms for each of 2023/2024/2025. All six saved accounts subsequently passed an independently reviewed, resource-bounded, zero-financial-advance cold restore. Three original STATIC50 fine accounts were reused read-only.

## Result

The pool improves observed PnL against the **new FOLLOW-dependent same-gross risk-timing control**, but its matched daily volatility is higher in all three observed comparisons. The original STATIC50 comparator remains unfavorable to the pool in every year on the valid comparison horizon. This does not reverse the prior FOLLOW cash-confidence or other strategy STOP decisions.

| Year | Pool minus new risk-timing control | Pool minus reused original STATIC50 | Matched pool/control daily vol |
|---|---:|---:|---:|
| 2023 |+591.090383 USDT paid cash|−12.062496 USDT paid cash|6.438619% / 5.941948%, full year|
| 2024 |+200.716284 USDT minute-marked, common 461,654 minutes|−547.257481 USDT minute-marked, common 461,448 minutes|7.158961% / 6.271087%, common observed prefix only|
| 2025 |+232.370401 USDT marked, full year; no paid cash delta|−622.582682 USDT marked, full year; no paid cash delta|5.897814% / 5.550901%, full year|

2024 pool completes 527,040 minutes and is paid-flat at +971.259446 USDT. The new control halts after 461,654 minutes with marked +746.345357 USDT and 833.109462 USDT gross inventory; original STATIC50 halts 206 minutes earlier. Neither halted endpoint is a full-year cash comparator. The shared-prefix numbers above exclude marks after the last completed minute.

2025 pool completes 525,600 minutes but remains marked-only: XRP quantity −1.83117484, gross notional 3.371375997924 USDT. No free close, paid-PnL promotion or tail extension is applied. Its marked PnL is +990.258332 USDT; the new control is paid-flat at +757.887931 USDT. 2023 both new arms are paid-flat: pool +1147.629999 and new control +556.539615 USDT.

## Frozen question and limits

S is frozen STATIC50; F is frozen FOLLOW. C=.5S+.5F; G=min(sumabs(S),sumabs(C)). Candidate=C×G/gross(C); new control=S×G/gross(S), zero G means exact cash. Scaling only reduces gross. The control depends on F through G and must not be relabeled original S. Equal daily target gross does not imply equal actual exposure, covariance, fills or costs. No protective policy, training or allocation search is used.

2024 passed the mandatory actual trade high/low/close gate for all five symbols, all 366 days and all 31 December2023 warmup days. All 397×5 daily closes match the frozen clock/close context bitwise. 2023/2025 reuse saved FOLLOW targets. Existing ten-derived-mark-cell and funding/venue-certification qualifications remain. No new provider or retained 2026-03–09 data is used.

The unchanged conditional account uses isolated 1x/no top-up, one-way positions, opening-only 10-USDT minimum notional, 1e−8 assumed quantity grid, native paid reductions, finite terminal attempts, real funding under the frozen assumption and BASE27 costs. Fees 5.5bp/side and half-spread 4bp+slippage 4bp remain; report cost splitting attributes the already charged execution cost and does not charge twice. These are assumptions, not certified historical venue filters or liquidation rules.

Daily vol is completed UTC-day NAV simple-return sample std(ddof=1)×sqrt365. 2024 prefix volatility is not a full-year estimate and is not compared with the pool's full-year volatility. No alpha, OOS, selection-adjusted evidence or live-trading conclusion is claimed.

## Evidence and budget

[Full compact results](postrun/RESULTS_COMPACT.json), [unaltered observer summary](postrun/SUMMARY.md), [postrun independent review](postrun/POSTRUN_REVIEW_RECEIPT.json), [postresult review](postrun/POSTRESULT_REVIEW_RECEIPT.json), [six cold receipts](postrun/receipts), [execution bindings](results), and [pre-execution protocol](PROTOCOL.md) retain exact identities and all unfavorable comparisons. This compact publication is not a lossless wallet backup; original 2025 full-backup publication remains outside scope.

Historical execution used exactly six wallets, at most two 1-CPU workers with 4GB AS/2GB sampled RSS each, shared 8GB host cap, zero swap/GPU and 15GiB disk reserve. Cold audit used one observer at a time: maximum sampled RSS710,176,768 bytes, 104.58 aggregate observer seconds. Report used 96,837,632 bytes and 30.67 seconds. No resource stop occurred. Cgroup enforcement was unavailable and is not claimed; RSS peaks are sampled.

Pre-execution commit: 6eccc22a23420f52d92f1303be6d7731087be81e. No historical rerun, old-control restore, extra wallet, free residual close, credential creation, Library or live order occurred during postprocessing.
