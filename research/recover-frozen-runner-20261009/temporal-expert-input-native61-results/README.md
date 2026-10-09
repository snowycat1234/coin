# Expert-target/eligibility input ablation: completed native61 comparison

The active-input GRU finished at **−484.14 USDT**, versus its matched control's
**−474.26 USDT**: **active minus control = −9.87 USDT**. Both new fresh 10,000
USDT shared wallets completed the same 2024 May 1–July 1 exclusive 61-day native
calendar, paid to finish flat, and passed independent actual-input and financial
audits with zero liquidations. The control result was reported, published and
read back before active execution began.

| Native outcome | Control | Active input | Active minus control |
|---|---:|---:|---:|
| Full net PnL, USDT | −474.26 | −484.14 | **−9.87** |
| May net PnL | −262.04 | −264.97 | −2.94 |
| June net PnL | −212.23 | −219.17 | −6.94 |
| Price PnL, same actual quantities | −422.02 | −433.54 | −11.53 |
| Actual signed funding | −12.46 | −12.68 | −0.22 |
| Fees charged | 16.21 | 15.45 | −0.76 |
| Spread/slippage execution costs charged | 23.58 | 22.47 | −1.11 |
| Full minute maximum drawdown | 6.47% | 6.47% | effectively equal |
| Mean actual gross / NAV | 22.45% | 21.42% | −1.03 percentage points |
| Maximum actual gross / NAV | 44.20% | 41.88% | −2.32 percentage points |
| Mean actual net signed / NAV | +7.69% | +7.79% | +0.10 percentage points |
| Native risk-reduction signals / liquidations | 0 / 0 | 0 / 0 | — |

The observed price shortfall of 11.53 and extra funding cost of .22 were partly
offset by 1.87 of lower trading costs. Both financial bridges retain every
cost. Full maximum drawdowns are 6.465009% and 6.465940%; rounding to the same
6.47% is not evidence of exact equal risk.

| Recorded monthly risk | Control May | Active May | Control June | Active June |
|---|---:|---:|---:|---:|
| Mean gross / NAV | 23.91% | 22.48% | 20.94% | 20.31% |
| Maximum gross / NAV | 44.20% | 41.88% | 32.33% | 29.26% |
| Mean net signed / NAV | −0.92% | −1.07% | +16.59% | +16.94% |
| Maximum minute drawdown from month-start NAV | 3.52% | 3.38% | 4.05% | 4.12% |

Monthly drawdown resets its running peak to that month's starting NAV; the
full-wallet drawdown does not reset at June 1. Exposure uses all recorded
minute snapshots, including the paid final flat day.

## Frozen request-weight diagnosis

Mean expert simplex weights are CASH / VOL / CS / MOM30 short. They are not
literal NAV allocations. Covariance-scaled targets, expert netting, the original
daily L1 ramp, quantities and actual fills determine observed exposure.

| Arm and month | Requested weights | Ramped budget weights |
|---|---|---|
| Control May | 0.12 / 11.49 / 64.37 / **24.01%** | 33.08 / 4.24 / 47.46 / **15.22%** |
| Active May | 0.19 / 12.81 / 60.07 / **26.93%** | 33.22 / 4.70 / 44.19 / **17.89%** |
| Control June | 0.28 / **90.06** / 9.65 / **0.020%** | 0.22 / 80.51 / 19.18 / 0.092% |
| Active June | 0.28 / **91.34** / 8.36 / **0.025%** | 0.33 / 82.87 / 16.22 / 0.584% |

Both policies requested appreciable short weight in May and almost none in
June. The active policy requested slightly more May short and June VOL, and
less CS in both months. Their maximum May requested short weights were 77.92%
and 79.20%; June maxima were only .183% and .240%. The ramp retained some short
budget into June. Active had lower June gross but slightly higher June net long
exposure. These are observations of two frozen policies, not evidence that the
input block caused any particular trade or that the models learned useful
downside timing. All 61 requests are included; final-day execution targets are
forced flat under the common contract.

## Exact information and execution contracts

Frozen exports are pinned at
`bd0d1d4b9b50fb8547f75f28c166bc445a09e073`, under
`research/temporal-expert-input-20261009/native61-requests`.
Control request SHA256 is
`9180bf41fb4b137163ffdfc3c549ca61d13f4372d6bcb62e53243b7adaf820af`;
active request SHA256 is
`79bb6a38fb180e53422c4fd33f937abd7f08dac56c5a58a11a87e947aa1ce688`.
Plans and readiness were published and read back before either wallet at
`55f0087dee39fb7fde234d6f43e6fa60083e5a69`.

Both bundles contain the same 61×18 expert-state packet, SHA256
`129d7f188005f65684052cbfa5dc58017c8995453fe85081f9379241a6adf6be`.
It exactly matches canonical slots 1/4/5's signed targets divided by fixed .3,
then their eligibility values. Unavailable targets are masked before scaling;
flat remains distinguishable from ineligible. Every saved input and target
clock matches the retained source and does not exceed its decision or reported
feature availability. Training expert-input clocks remain within the original
pre-May cutoff. Control disables the block; active enables it. The producer's
bound model/architecture sources declare **13,699 parameters in each arm**;
model tensors are never loaded here.

Original E5 slots and appended MOM30 short slot 5 are preserved. Both actual
request paths give **bit-identical budgets and targets** through source-bound
producer mapping and canonical native E6 mapping. Corrected adapter contract:
`9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2`.
Unchanged guard-OFF financial engine:
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.

Both native wallets use the original cached actual trade/mark/funding tapes,
CORE5, conditional isolated 1x/MMR .005 account, fee 5.5 bp each side,
halfspread 4 bp, slippage 4 bp, gross/asset target caps .6/.3, past-30-day
covariance/10% annual risk contract, daily budget L1 .1 after mandatory release,
original sizing, previous-minute quote capacity .1%, lot 1e−8, minimum notional
10, delayed/partial orders, reductions first, five-attempt expiry, funding
before fills on strictly prior completed marks, first fresh funding unheld,
and paid terminal-flat closure. Each completed 87,840 minutes and 915 actual
funding events. Historical publication and venue/account rules remain
uncertified conditional assumptions.

## Interpretation and preservation

Control completed **403** additional updates; active completed **350**. Both
are **CAPPED_NOT_CONVERGED** and share parent checkpoint, scaler, dataset and
training plan. Unequal updates and realized risk prevent labeling this small
observed difference a causal input benefit or failure. May–June is already
seen development, not OOS; no alpha or overfitting conclusion follows. Daily
surrogate proxy outcomes are not native outcomes or acceptance/tuning targets.
No independent accounts are stitched, added or treated as executable switching
regret. Existing baselines and the parent GRU are reused references only.

[RESULTS.json](RESULTS.json) contains exact monthly accounting, minute risk,
request/ramped-budget summaries and source bindings. Arm directories contain
original summaries, request gates, independent audits and compact results.
`ARTIFACT.json` binds the ordered small byte parts of the full simulation archive;
`RESULT_MEMBER_HASHES.json` binds every member. Original account journals are
under `accounts/ARM/account` in the archive, together with execution receipts,
plans, source/verification helpers and dependency recipes. Raw market tapes,
model weights, private runtime inventories and credentials are not duplicated.
`PUBLIC_READBACK.json` records public-byte, ZIP/member, original-journal and
portable financial auditing. Use `package_short_expansion61.py --profile
expert-input` for this already completed pair; existing outputs are immutable.

**Two new wallets ran once each. Zero fits, model inference, provider downloads,
older-wallet reruns, live actions, new expert recipes or weighting updates.**
