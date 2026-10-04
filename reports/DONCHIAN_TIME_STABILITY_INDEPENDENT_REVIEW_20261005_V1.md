# D068 saved-wallet independent review

Status: PASS independent arithmetic and fixed calendar scope; no independent alpha, OOS or APR claim.

Actual bounded task: `53d0d5303c7b445cbae54d11fea690e4`. Execution closure: actual completed, exit 0, confirmed from the closed progress task and command output.
Helper: `/home/xflops/coin-state/d068-time-stability-independent-20261005-v1/independent_review.py`; SHA256 `ea8adbff7a558d24ab8fb30decc599ba6c2b8bd1683827b25dfeff969efec882`.
Protocol SHA256 `2eab7066727257284ef7cce2b66e2e97a5b98b7bc5feb6f9144555e744aeda14`; actual main result SHA256 `5c1f0937b5a2082e676f2160358b791249f13db56749a8e2f193fb5809994f89`. Main task `5c73a02b49ad46f9bd01dced77177469` confirmed completed exit 0.

## Independent calculations

Opened only eight saved daily_nav Parquets (2 columns), exact SHA and complete ordered 303 UTC endpoints. Independently built dates by scalar timedelta, first previous NAV 10000, Decimal.from_float plus 50-digit scalar ln differences and direct end-minus-start wallet PnL. No producer summary functions, replay, target factory or main script imported.
Fixed 101-day slices: 2024-09-01–2024-12-10, 2024-12-11–2025-03-21, 2025-03-22–2025-06-30. Verified all 12 slices, 40 month slices and 4 totals against actual preceding and endpoint NAV; no reset to 10000. Eight final daily endpoints reconcile to the full Decimal wallet NAV and net PnL with zero terminal inventory.

Reported numerical discrepancies below compare the independent 50-digit Decimal result after conversion to float against saved numerical fields; a displayed zero is not a claim of bitwise Decimal wallet equality. Exact Decimal telescoping for adjacent NAV differences is checked separately.

| Maximum independent discrepancy | Value |
|---|---|
| log_telescoping | 0 |
| terminal_decimal_wallet_bridge_USDT | 0 |
| terminal_decimal_PnL_bridge_USDT | 6.8212102633e-13 |
| reported_real_PnL_increment_USDT | 0 |
| reported_paired_log_increment | 2.89698820488e-15 |
| actual_start_end_NAV_USDT | 0 |
| actual_segment_PnL_USDT | 0 |
| reported_account_log | 2.02615701994e-15 |
| actual_segment_return | 2.1371793224e-15 |
| paired_terminal_log_bridge | 0 |
| reported_mean_daily_log | 9.57486043576e-18 |
| month_out_arithmetic_USDT | 0 |
| toy_circular_percentile | 4.16333634234e-17 |

## Financial interpretation

| condition | net increment USDT | fixed 101-day increments USDT | primary 60-day mean log CI |
|---|---:|---|---|
| LIQUIDITY_TEN_BASE27_RAW_AS_FRACTION | 156.667941 | [2.747584, -75.494281, 229.414638] | [-0.000105500458, 0.000188040668] |
| LIQUIDITY_TEN_BASE27_RAW_AS_PERCENT | 156.891255 | [2.835407, -76.187333, 230.243181] | [-0.000105853275, 0.000187932266] |
| LIQUIDITY_TEN_STRESS43_RAW_AS_FRACTION | 159.817128 | [0.481923, -74.049053, 233.384257] | [-0.000104505055, 0.000189144252] |
| LIQUIDITY_TEN_STRESS43_RAW_AS_PERCENT | 160.042796 | [0.560406, -74.736399, 234.218789] | [-0.000104637087, 0.00018902901] |

Every fixed condition reverses sign across time slices; third slice supplies more than the full-period net increment, while the middle slice loses incremental money. This rejects a stable advantage claim for this evaluated recipe/window. It does not prove that all exit10 rules or all trend strategies fail.
All 12 reported 7/30/60-day intervals include zero. Main block-bootstrap loop is the unchanged existing circular paired-mean function, seed and blocks bound before this diagnostic. Independently checked circular wrapping/truncation and interpolated percentiles on only 3×37 synthetic draws; did not repeat the 24,000 empirical draws. The empirical percentile numerical endpoints were not independently re-estimated.
Intervals assume block resampling is a useful dependence approximation; circular end-to-start stitching and changing regimes limit inference. About five complete 60-day blocks is a descriptive scale, not an effective sample-size certification. Bootstrap replication does not increase historical length; parameter choice followed prior seen results, and the diagnostic does not correct strategy-selection bias. Four friction/funding scenarios are paired sensitivities of the same history, not four independent studies.
Log-return differences compare each evolving wallet denominator; dollar increments use actual shared wallets, not a sum of separately reset accounts. Actual risks remain unmatched; this is not risk-normalized alpha. Data are Binance/Bybit-fee proxy, funding units remain scenarios, no native fills or historical venue rules are certified. Daily endpoints retain the previously accepted same-timestamp funding convention; this review verifies arithmetic, not new market-time semantics.

Resource: elapsed 0.415940s; process peak RSS 77697024 bytes; eight Parquet payloads 76599 bytes. Shared RAM guard: `{"aggregate_cgroup": "/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/coin.slice/coin-quant.slice", "ram_limit_bytes": 4999999488, "ram_current_bytes": 385916928, "ram_peak_bytes": 3263008768, "swap_bytes": 0, "memory_events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0", "gpu_used": false}`.
No fit/HPO, download, market replay, locked data, credential use, orders, leverage/caps change or evidence overwrite. Investment remains NONE/CASH; this only supports keeping exit10 as a research configuration with independent evidence required for promotion.

## Saved NAV identities

- `/home/xflops/coin-state/d065-active-allocation-market-20261004-v1/LIQUIDITY_TEN_BASE27_RAW_AS_FRACTION/daily_nav.parquet` SHA `6bf917c70a8f0b35b89de959e547b38ffc943a13a3dbf81842caf456a80b04ef`, 10072 bytes, 303 rows.
- `/home/xflops/coin-state/d067-exit10-market-20261004-v1/LIQUIDITY_TEN_BASE27_RAW_AS_FRACTION/daily_nav.parquet` SHA `2ab2a05147c201d3ced98c8868c38616484ea17aea38d2017196e9a61870800b`, 9067 bytes, 303 rows.
- `/home/xflops/coin-state/d065-active-allocation-market-20261004-v1/LIQUIDITY_TEN_BASE27_RAW_AS_PERCENT/daily_nav.parquet` SHA `258637c9f8db681006d86338d8d38742babaff1838aed38583ab3733417e1124`, 10085 bytes, 303 rows.
- `/home/xflops/coin-state/d067-exit10-market-20261004-v1/LIQUIDITY_TEN_BASE27_RAW_AS_PERCENT/daily_nav.parquet` SHA `5b1623ce54fc0e5776f83fba5e9850080abc1c1a6c9289b192effbb9bbbfd45f`, 9063 bytes, 303 rows.
- `/home/xflops/coin-state/d065-active-allocation-market-20261004-v1/LIQUIDITY_TEN_STRESS43_RAW_AS_FRACTION/daily_nav.parquet` SHA `9c5410c213bd8836ed7fce002b6cb6b8a32d139fdbafb811d40f09e5916298a2`, 10102 bytes, 303 rows.
- `/home/xflops/coin-state/d067-exit10-market-20261004-v1/LIQUIDITY_TEN_STRESS43_RAW_AS_FRACTION/daily_nav.parquet` SHA `0a7980b037d016a4fadb1b401fc5b363d7941c1d5561030e31f4d3bb564f8630`, 9060 bytes, 303 rows.
- `/home/xflops/coin-state/d065-active-allocation-market-20261004-v1/LIQUIDITY_TEN_STRESS43_RAW_AS_PERCENT/daily_nav.parquet` SHA `1e167e0755c5993801bbfda009ea83cf9acc8c7920c4a7ecc503a9a38d185274`, 10086 bytes, 303 rows.
- `/home/xflops/coin-state/d067-exit10-market-20261004-v1/LIQUIDITY_TEN_STRESS43_RAW_AS_PERCENT/daily_nav.parquet` SHA `5abbd04a6c7aeef6d085e3fa27f2ee5b73909d91d7d6b410f5b9b2e33ff67fda`, 9064 bytes, 303 rows.
