# Pre-May economic transfer audit

The three public parts at `d901f130993b6f00ad6479dcc6a04b77627192b8`, `research/temporal-feature-data-20261009/INDEX.json`, were recovered once and retained outside Git. Concatenation is 2,246,454 bytes, SHA256 `bdbcdc488fc4245c1fb6b433df1fc4bf806a120433db71e180816119cebbcc30`; all 26 members, ZIP CRC and 25 non-self member hashes verify. No raw public payload is uploaded again here.

`inspect_economic_transfer.py` freshly parses the ten economic Parquets using an explicit whitelist. All seven stored daily funding fields recompute exactly from the original signed event rates, intervals and strictly past mark evidence. Raw millisecond settlement offsets remain unchanged. Absent prior marks remain absent. The audit separately checks actual complete trade-day metadata, positive OHLC/execution prices, completed-day clocks, and 605 January-April H1 asset-days against retained hash-verified minute Parquets, including actual April 30 00:01 endpoint prices.

There are **839 economic-only mature one-day decision dates in six gap-separated runs**:

| First decision | Last decision | Decisions |
| --- | --- | ---: |
| 2022-01-02 | 2022-02-24 | 54 |
| 2022-03-01 | 2022-03-30 | 30 |
| 2022-04-03 | 2022-07-30 | 119 |
| 2022-08-01 | 2022-10-01 | 62 |
| 2022-10-03 | 2023-02-23 | 144 |
| 2023-02-25 | 2024-04-29 | 430 |

These are candidate economic intervals, not certified input-ready training dates. The earlier provisional 745 count included a separate 64-bar price-history gate. The temporal worker owns that gate, per-feature masks and window construction. Intersect independent causal input/past-covariance readiness with these dates, split on every gap, and freeze the training plan before fitting. Do not bridge missing days or stitch independent wallets.

For decision midnight t, the observation starts t-1 day and completes at t under the historical availability proxy. The outcome starts at t+00:01:00.000001 and ends at t+1 day+00:01:00.000001. Owned funding events satisfy start < actual event <= end, using actual signed raw rate scale 1 and strictly prior completed marks. Funding settles before boundary rebalancing. Fresh first funding has no previously held position. Endpoint maturity is strictly before May 1, 2024. Both-sided funding chronology evidence remains required. April 30 decision outcomes mature after the cutoff and are excluded.

`PRE_MAY_ECONOMIC_OUTCOMES.npz` contains only the 839 decision/observation dates, episode IDs, start/end execution clocks, five-asset actual start/end prices and funding-per-unit outcomes. It contains no features, labels, trained weights, simulated profits or label-conditioned masks. It must never become a model input or feature-availability mask. Its hash and exact boundaries are in `ECONOMIC_READINESS.json`.

The original feature NPZ retains ten-asset aggregate semantics and per-feature missingness. No CORE5 aggregate redefinition was made here. Raw official archive ZIPs are absent from this new transfer: prior checksum/CRC receipts are historical producer evidence, distinct from this fresh outer transport and numerical Parquet audit. This certifies conditional daily proxy economic dependencies, not complete historical native minute execution, publication time, instrument/account rules or unseen validation. No exchange downloads, training or wallets for these episodes occurred.

## Input and original expert-context intersection

`TRAIN_CONTEXT_READY.json` binds the exact input index at `256f6fd8206b1616d59eb3129145bfa74ebde924`. All 839 economic dates intersect its 1,518 valid calendar windows. Requiring actual complete CORE5 31-close/30-return past covariance context and unchanged original VOL/CS eligibility leaves **778 dates in five runs**:

| First decision | Last decision | Decisions |
| --- | --- | ---: |
| 2022-01-02 | 2022-02-24 | 54 |
| 2022-05-04 | 2022-07-30 | 88 |
| 2022-08-01 | 2022-10-01 | 62 |
| 2022-10-03 | 2023-02-23 | 144 |
| 2023-02-25 | 2024-04-29 | 430 |

The 61 excluded economic dates have incomplete actual past covariance context. No all-64-prices, ready256 or globally complete-feature gate is imposed; missing feature history stays masked. Original VOL per-asset 200-bar eligibility is retained, including genuine partial-pool eligibility after historical gaps. CSMOM keeps the original weekly January 1, 2024 anchor and past21 rank/past30 covariance rules.

`bind_temporal_economics.py` calls the hash-verified original `bar_frame` and `existing_targets` functions for VOL and CSMOM only. The full original close matrix matches the actual OHLC source exactly with NaNs preserved. Targets, raw targets, expert eligibility and per-asset eligibility match all 182 available saved reference dates exactly: 121 pre-May H1 dates, 30 November 2022 dates and 31 January 2023 dates. No teacher utility/label, feedback, scaler, search or training function is invoked.

`PRE_MAY_TWO_EXPERT_ECONOMIC_CONTEXTS.npz` is the compact outcome/context handoff: 778 dates, five episode IDs, real completed prices and30 returns, unchanged targets/eligibility, actual start/end prices, funding and clocks. Its three named slots are CASH/VOL/CS, explicitly mapped to original E5 indices0/1/4. It does not pad or admit other experts. The consumer must preserve that identity and freeze fresh CASH budget ramp, conditional financial costs and paid episode terminal closure in its training plan. This is ready for that plan; no scaler or model has been fitted. Pool expansion is separate from the two-expert comparison.
