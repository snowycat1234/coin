# Matched512 episode-weighting: completed native61 comparison

The mixed-weighted frozen GRU finished at **-500.49 USDT**, versus date weighting's **-467.42 USDT**: **mixed minus date = -33.07 USDT**. Both new fresh 10,000 USDT shared wallets completed the same 2024 May 1–July 1 exclusive 61-day native calendar, paid to finish flat, and passed independent actual-input and financial audits with zero liquidations. The first date result was reported, publicly preserved and read back at `5bf87b5cf102f58df5afb15d889ae6cdb357cbd7` before mixed execution.

| Native outcome | Date weighting | Half-date / half-equal-episode | Mixed minus date |
|---|---:|---:|---:|
| Full net PnL, USDT | -467.42 | -500.49 | -33.07 |
| May net PnL | -259.29 | -283.99 | -24.70 |
| June net PnL | -208.13 | -216.50 | -8.37 |
| Price PnL, same actual quantities | -415.69 | -452.83 | -37.14 |
| Actual signed funding | -11.60 | -11.51 | 0.09 |
| Fees charged | 16.35 | 14.73 | -1.62 |
| Spread/slippage costs charged | 23.78 | 21.42 | -2.36 |
| Full minute maximum drawdown | 6.37% | 6.46% | +0.09 pp |
| Mean actual gross / NAV | 23.21% | 20.70% | -2.51 pp |
| Maximum actual gross / NAV | 45.45% | 39.24% | -6.21 pp |
| Mean actual net signed / NAV | 7.36% | 7.25% | -0.11 pp |
| Native risk reductions / liquidations | 0 / 0 | 0 / 0 | — |

Mixed incurred 37.14 more price loss; funding improved 0.09 and fees plus execution costs declined 3.98. All costs remain in the financial bridge. Mixed lost 24.70 more in May and 8.37 more in June.

| Recorded monthly risk | Date May | Mixed May | Date June | Mixed June |
|---|---:|---:|---:|---:|
| Mean gross / NAV | 24.05% | 20.61% | 22.33% | 20.79% |
| Maximum gross / NAV | 45.45% | 39.24% | 35.51% | 29.80% |
| Mean net signed / NAV | -1.27% | -1.83% | 16.28% | 16.63% |
| Minute drawdown from month-start NAV | 3.53% | 3.39% | 4.00% | 4.07% |

Monthly drawdown starts from that month's initial NAV; full-wallet drawdown does not reset at June 1. Minute exposure includes the paid final flat day.

## Frozen request-weight observations

Mean expert simplex weights below are CASH / VOL / CS / MOM30 short, rather than literal NAV allocations. Covariance scaling, netting, daily L1 ramp and actual fills determine realized exposure.

| Arm and month | Requested weights | Ramped budget weights |
|---|---|---|
| Date May | 0.079 / 9.311 / 65.436 / 25.175% | 33.267 / 2.799 / 47.828 / 16.106% |
| Date June | 0.231 / 91.387 / 8.371 / 0.010% | 0.175 / 78.304 / 21.411 / 0.110% |
| Mixed May | 0.090 / 11.942 / 54.539 / 33.428% | 33.201 / 3.595 / 39.651 / 23.552% |
| Mixed June | 0.318 / 91.078 / 8.593 / 0.011% | 0.482 / 81.075 / 17.016 / 1.427% |

Both frozen policies request appreciable MOM30 short in May and almost none in June. Mixed requests more short and less CS in May; June is dominated by VOL in both. These observations do not establish trade-level causes or learned downside timing. All 61 requests are retained; common terminal-day execution targets are forced flat.

## Matched training and information contract

Exports are pinned at `d3d57332ca45b7a4443108db21f46abad0e1ac99`, under `research/temporal-episode-weighting-v2-20261009/native61-requests`. Plans and source were published and read back before either wallet at `db0ec81f5b504cb82154a402c521d36f7ef4e8b8`. Both source-bound arms have **13,699 parameters**, the same enabled causal 61×18 current expert target/eligibility input packet SHA256 `129d7f188005f65684052cbfa5dc58017c8995453fe85081f9379241a6adf6be`, the same expanded action pool, scaler and training plan, identical model/Adam/RNG initialization SHA256 `0f51bd3316f6e1100de518e8283ef3afb1c1148007bbb4d5fa7e3d1375acaddb`, and **exactly 512 additional updates each**. Both finish at base Adam step 1292 / new parameter step 512. Their full specifications differ only in `algorithm.arm` and `algorithm.mixing`; normalized common spec SHA256 is `bc4a3daac16e5933eda04b2763aaa2ede7e5626be7fbab55f345fba5e7fd44ca`. Status is **FIXED_512_UPDATES_COMPLETED**, with no convergence claim. Actual recorded fitting completed retrospectively on 2026-10-09 at 20:20:43.601003 UTC (date) and 20:21:32.571545 UTC (mixed); causal feature clocks do not certify historical model publication.

Five chronological training-wallet lengths are 54/88/62/144/430. Date loss coefficients are `n/778`: 6.94/11.31/7.97/18.51/55.27%. Mixed uses `.5*n/778+.5/5`: 13.47/15.66/13.98/19.25/37.63%. No dates are resampled or discarded. These are whole-wallet loss coefficients, not gradient, alpha or capital shares. No fit, model loading or inference occurs here.

Original E5 slots and appended MOM30-short slot 5 remain exact; all source targets, masks and clocks match. Unavailable expert targets are masked before fixed .3 scaling; flat remains distinct from ineligible. All saved input clocks are causal relative to reported decision/execution clocks. Both request paths produce **bit-identical budgets and targets** through source-bound producer and corrected canonical E6 mapping.

Unchanged guard-OFF engine SHA256: `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`. Corrected E6 adapter contract SHA256: `9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2`. Native adapter source SHA256: `948f496f6307576832fa47afcfcd7161b0d855456b49ae511da5066d09f2efbd`.

## Original execution and reused controls

Each wallet uses original cached actual trade/mark/funding tapes, CORE5, conditional isolated 1x/MMR .005 account, fees 5.5 bp each side, halfspread 4 bp and slippage 4 bp, signed funding scale 1, gross/asset targets .6/.3, causal past 30-day covariance/10% annual risk mapper, original weekly rank anchor 2024 Jan 1, budget daily L1≤.1 after mandatory eligibility release, original .99*currentNAV sizing, previous-minute quote-USDT capacity .1%, lot 1e−8, minimum opening notional 10, delayed/partial orders, risk reductions first and five-attempt expiry. Funding occurs before fills on strictly prior completed marks; first fresh funding is unheld; terminal closure is paid. Each completed 87,840 minutes and 915 actual funding events. Historical publication and venue/account/filter rules remain uncertified conditional assumptions.

| Reused native reference | Full PnL, USDT | May | June | Full DD | Mean gross |
|---|---:|---:|---:|---:|---:|
| CASH50 | -110.89 | -45.51 | -65.38 | 1.58% | 12.51% |
| STATIC50 | -189.01 | -56.32 | -132.69 | 3.08% | 22.81% |
| Parent GRU with cash | -472.96 | -256.28 | -216.68 | 6.94% | 25.80% |

Reference journals are reused without reruns. Cash50 and Static50 lost substantially less, at different actual risks. The parent GRU has different training history. References are not the matched weighting ablation. The matched512 pair improves identification over previous unequal-update experiments, but this single already-seen May–June development pair, with unequal realized exposures, does not establish OOS efficacy, alpha, convergence or executable switching gain. Daily surrogate proxy values −502.47/−521.17 remain distinct from these native outcomes and were not acceptance or tuning targets.

## Preservation and verification

[RESULTS.json](RESULTS.json) records exact accounting, monthly minute risk, request/ramped budget summaries, matched training provenance and reused controls. Arm directories retain original summaries, request gates, independent audits and compact results. `ARTIFACT.json` binds ordered small byte parts of the complete simulation archive; `RESULT_MEMBER_HASHES.json` binds every member. Original account journals, execution receipts, plans, verification helpers, unchanged adapter and dependency recipes are retained. Market tapes, model weights, private runtime inventories and credentials are not duplicated. Public-byte, ZIP/member, original-journal checks and portable financial audits are recorded in `PUBLIC_READBACK.json`. The original actual-input audits are retained byte-identically; portable financial audits do not repeat tape validation.

Use `package_short_expansion61.py --profile weighting512` only against these already completed immutable outputs. **Exactly two new native wallets ran once each; zero fits, model inference, provider downloads, old-wallet reruns, independent-account stitching, live actions or new recipes.**
