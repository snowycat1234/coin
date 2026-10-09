# Frozen short expansion: two complete native61 results

The short-enabled terminal GRU lost **488.51 USDT**, versus its matched continued
control's **474.59 USDT**: **short minus control = −13.92 USDT**. This is the
primary comparison. Both fresh 10,000 USDT shared wallets completed the same
2024 May 1–July 1 exclusive 61-day native calendar, paid to end flat, and passed
the unchanged independent audit with zero liquidations. The control result was
reported and publicly preserved before the short wallet started.

| Native outcome | Matched control | Momentum-short enabled | Short minus control |
|---|---:|---:|---:|
| Full net PnL, USDT | −474.59 | −488.51 | **−13.92** |
| May net PnL | −262.59 | −275.53 | −12.94 |
| June net PnL | −212.00 | −212.98 | −0.98 |
| Price PnL, same actual quantities | −413.02 | −438.63 | −25.61 |
| Actual signed funding | −13.88 | −12.09 | +1.79 |
| Fees charged | 19.43 | 15.40 | −4.03 |
| Spread/slippage execution costs charged | 28.26 | 22.40 | −5.87 |
| Minute maximum drawdown | 7.04% | 6.33% | −0.71 percentage points |
| Mean actual gross / NAV | 26.52% | 20.75% | −5.77 percentage points |
| Maximum actual gross / NAV | 60.09% | 40.76% | −19.33 percentage points |
| Mean actual net signed / NAV | +8.71% | +7.34% | −1.36 percentage points |
| Native risk-reduction signals | 1 | 0 | — |
| Liquidations | 0 | 0 | — |

The observed price shortfall of 25.61 was partly offset by 1.79 of better
funding and 9.90 of reduced trading costs. Lower exposure and drawdown did not
produce a better ending NAV in this seen wallet. The control's observed gross
can drift above its unchanged 60% **target** cap before native risk reduction;
the reduction remains enabled and its charges are retained.

## What the frozen heads requested

Mean expert simplex weights are CASH / VOL / CS / MOM30 short. These are not
literal capital allocations. Individual covariance-scaled targets, netting,
the original daily ramp, sizing and actual execution determine exposure.

| Arm and month | Requested weights | Ramped budget weights |
|---|---|---|
| Control, May | 0.46 / 12.10 / 87.43 / 0% | 30.82 / 4.05 / 65.13 / 0% |
| Control, June | 0.09 / 90.21 / 9.70 / 0% | 0.11 / 80.66 / 19.23 / 0% |
| Short arm, May | 0.17 / 12.90 / 56.25 / **30.68%** | 32.71 / 4.25 / 42.15 / **20.90%** |
| Short arm, June | 0.28 / 87.08 / 12.60 / **0.036%** | 0.38 / 80.44 / 17.95 / **1.23%** |

The short arm assigned substantial short budget in May and almost none in
June. Its maximum daily requested short weight was 79.99% in May and 0.325%
in June. The ramp carried some short budget into June. Final-day native targets
are forced flat in both arms; request summaries retain all 61 frozen decisions.

## Comparison limits

Both arms share the parent checkpoint, scaler, training plan, datasets and
native contract. Control completed 395 expansion updates; short completed 374.
Both exports are **CAPPED_NOT_CONVERGED**, and realized risk is unequal. These
two trained policies differ in all their requests, so their observed account
difference is not an isolated causal effect of adding the short slot.
It is not executable switching regret, a stitched wallet or OOS alpha.
May–June was already seen development. Daily surrogate proxy outcomes are not
native outcomes and were not used as tuning or acceptance targets here.

Previously completed accounts are references only, with no reruns: Cash50
−110.89, Static50 −189.01, and the parent v2 GRU withCash −472.96 USDT. The
matched continued control remains the expansion comparison; none of these
full-capital account results are added together.

## Exact execution and evidence

Public exports are pinned at
`7059e955306a5285316b58f7d38a26f917cdb116`, under
`research/temporal-short-expansion-20261009/native61-requests`.
Control request SHA256 is
`2c61c428f2f08e34ac79195b3c0b2557d683c5d752926dc629ab66ffed7f922e`;
short request SHA256 is
`7514bb2d9b0f92995bdf2f5b00b7ad2a191894996a1ab187608a8375bce4ec43`.
Both plans were published and read back before execution at
`51a2482a992287b013d5c6ff48d5f9eaaba3c228`.

The original E5 slots, targets, masks and clocks are preserved; slot 5 is the
exact `MOMENTUM30_SHORT_ONLY` context, development SHA256
`89183eb92bd45b65a1209aa139f80964cc013c62015a803336db7a7bbd90840d`.
The producer's private-coordinate mapping and native canonical E6 mapping
produce **bit-identical budgets and targets for both actual request paths**.
The corrected contract is SHA256
`9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2`.
The guard-OFF financial engine is unchanged, SHA256
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.

The native engine uses the retained actual tapes and signed funding events,
five CORE5 assets, conditional Bybit-style isolated 1x/MMR .005, fee 5.5 bp
each side, halfspread 4 bp, slippage 4 bp, gross target cap .6, asset cap .3,
past-30-day covariance/10% annual risk check, and daily budget L1 .1 after
mandatory eligibility release. Original sizing, previous-minute quote capacity
.1%, lot 1e−8, minimum notional 10, delayed/partial orders, reductions first,
five-attempt expiry, funding before fills using strictly prior completed marks,
fresh first funding unheld and paid terminal-flat closure are retained.
Historical publication and exchange/account rules remain uncertified.

[RESULTS.json](RESULTS.json) records the complete comparison, allocation
summaries and source bindings. Each arm directory contains its original
summary, request gate, independent audit and compact result. `ARTIFACT.json`
lists ordered byte parts of the full simulation-results archive and exact
hashes; `RESULT_MEMBER_HASHES.json` binds every original member. The archive
contains original journals under `accounts/ARM/account`, audits, execution
receipts, plans, verifier helpers and dependency recipes. Market tapes and model
weights are not duplicated. `PUBLIC_READBACK.json` records public-byte,
archive-member, original-journal and portable financial verification.

**Two new wallets ran once each. Zero fits, model inference, provider downloads,
completed-wallet reruns, live actions or new recipes.** Both retained outputs
and unique request ledgers are complete and audited. Recover the archive by
concatenating its manifest-ordered parts, verifying each part and whole SHA256,
then checking ZIP CRC and member hashes. Portable journal auditing uses
`verification_helpers/modules/transformer_v3/isolated_audit.py` with CORE5 and
unit scale 1; full actual-input audits are preserved in each original audit.
