# Remaining original E5 pool diagnostics

Two independent fresh $10,000 wallets cover May 1 through July 1 exclusive, 2024. `pool61.py` consumes the exact original H1 E5 target arrays, eligibility, target clocks and past covariance context. It requests only the original SMA50/200 signed expert or original long-only Donchian exit10 expert through the unchanged original E5 mapper, starting from CASH with daily budget L1 ramp 0.1. No definition, threshold, risk, sizing, cost or terminal convention was changed. The exact guard-OFF financial engine remains SHA256 `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.

The bounded plan and executable were published and read back at commit `c027eef280d3e2cbbb37e7d91795ff90d6d1d999` before either wallet ran. Reuse the dependency recipe, H1 recovery helper and independently verified H1 inputs described in `NATIVE61_README.md`; then run `pool61.py check` and the explicit fixed policy. Never rerun a completed wallet or overwrite its directory.

| Original expert | Gross PnL, same quantities | Fees | Execution | Signed funding PnL | Net | Mean / peak gross | All-observation drawdown |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SMA50/200 signed | 22.74 | 5.63 | 8.19 | -19.41 | -10.50 | 20.23% / 38.62% | 4.92% |
| Donchian exit10 | -100.58 | 4.76 | 6.93 | -16.13 | -128.40 | 8.74% / 17.15% | 3.01% |

SMA long net contribution was -57.64 and short contribution +47.14. Donchian is the original long-only expert: long net contribution -128.40, short 0. Turnover relative to initial capital was 1.0240 and 0.8662. All amounts are USDT. Both completed 87,840 minutes, paid to close flat and had zero liquidations. Decimal financial reconciliation and actual-source fill, capacity, fee, mark and funding audits passed; maximum NAV/wallet discrepancy was approximately 1.82e-12 USDT. Full unchanged journals, standalone verification and exact metrics are in `comparison-pool61`.

Both paid net results are negative. Against the saved static VOL/CSMOM 50/50 wallet, SMA was positive on 8 of its 37 loss days, but lost 417.16 in aggregate on those days; Donchian was positive on 3 and lost 434.35 in aggregate. These are descriptive comparisons of separate wallets with different realized exposure. Both mechanisms are trends, and these results do not establish a profitable complement. This is already-seen chronological development, with no fitting, search, parameter tuning or promotion.

The optional RSI2 signal is an explicitly new scope port of an old signal, not a novel or proven strategy. Its target source exactly matches the requested main commit, and all five assets have real contiguous 240-bar warmup at every validation decision. No exact current-scope prior result was located. The exact official `jesse-rust==1.3.0` compiled binary is absent and the unchanged wrapper binds its historical installation. `RSI2_GATE.json` records the narrow dependency gap and pinned wheel/extension identities. No RSI substitute or candidate wallet was run.

The separate temporal transfer check is in `temporal-economics`. It contains economic outcomes and clocks only. The other worker owns feature windows/masks and must intersect their readiness with these economic dates before any training plan is frozen. No training has been run.
