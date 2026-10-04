# D069 independent saved-exit episode review

Status: PASS endpoint/Decimal journal bridges and actual signal/inventory scope; not a counterfactual or alpha certification.

Actual task `f295a3d81a9042bfbfa2e4559a9bfa5d`; closure actual completed, exit 0, confirmed from the closed progress task and captured command output.
Helper `/home/xflops/coin-state/d069-exit-wait-independent-20261005-v1/independent_review.py` SHA `f99e5922a6b83d0999f78bb57342ffa4d5c246f09129ada5586408b4185724e2`.
Protocol SHA `f7fbf68b0d5dfd8e69b88ac236351aebb9656cf5abb2e911e938216495fe107d`; actual result SHA `dfc15aff6b02e150456ed176c524f11dc8570e415bbee4bbadd4bc8c97bd637d`; main task `5069bba050ef4d4791a0153d7dec99c9` confirmed completed exit 0.

## Independent arithmetic and coverage

Verified 40 per-asset full-span pairs, four full wallet totals, 40 case months plus 400 asset-months, all 52 episodes, and 590 asset-day state assignments in fixed BASE27/fraction February/March. No main script imported; no 80 full monetary vectors or fresh account replay built.
One asset at a time, independently obtained U endpoints from saved isolated_equity minus isolated_balance using 50-digit Decimal converted from the actual stored Float64s. Original fill/funding decimal_strings were summed by scalar comparisons start < event <= end. First evaluation-boundary events were separately retained and verified zero funding. Therefore exact UTC-end funding is included in the earlier closed-minute/day; raw classifications use that day’s minute-open decision, not the next decision at the endpoint.
Gross = end U − start U + realized fill PnL + execution cost; net then subtracts fees and execution and adds signed funding. Collateral transfer/release is not revenue; execution embedded in fill PnL is added back only to report gross. A nonzero starting U is preserved at every episode/month, rather than reset.

| Maximum absolute discrepancy (50-digit Decimal comparison) | Value |
|---|---|
| asset_month_execution_USDT | 1.34454489962e-15 |
| asset_month_fees_USDT | 4.09711182147e-16 |
| asset_month_fill_legs | 0 |
| asset_month_filled_notional_USDT | 1.39975253269e-12 |
| asset_month_funding_USDT | 4.08288516228e-15 |
| asset_month_gross_USDT | 1.83178191124e-13 |
| asset_month_net_USDT | 2.01725576934e-13 |
| asset_total_execution_USDT | 5.25100724772e-15 |
| asset_total_fees_USDT | 1.23560734568e-15 |
| asset_total_fill_legs | 0 |
| asset_total_filled_notional_USDT | 2.85056734085e-12 |
| asset_total_funding_USDT | 3.93282703406e-15 |
| asset_total_gross_USDT | 1.35107755661e-13 |
| asset_total_net_USDT | 1.79756038287e-13 |
| base_FebMar_state_execution_USDT | 1.50172287754e-16 |
| base_FebMar_state_fees_USDT | 1.03978295875e-16 |
| base_FebMar_state_fill_legs | 0 |
| base_FebMar_state_filled_notional_USDT | 4.86468984011e-13 |
| base_FebMar_state_funding_USDT | 3.82212174572e-16 |
| base_FebMar_state_gross_USDT | 1.88469988821e-14 |
| base_FebMar_state_net_USDT | 5.59343186263e-14 |
| case_month_execution_USDT | 5.6447661615e-15 |
| case_month_fees_USDT | 2.07996728785e-15 |
| case_month_fill_legs | 0 |
| case_month_filled_notional_USDT | 3.43014633369e-12 |
| case_month_funding_USDT | 1.09684367578e-14 |
| case_month_gross_USDT | 9.96351078675e-12 |
| case_month_net_USDT | 1.21133496099e-11 |
| case_total_execution_USDT | 1.49564620701e-14 |
| case_total_fees_USDT | 4.76833064122e-15 |
| case_total_fill_legs | 0 |
| case_total_filled_notional_USDT | 6.32550209698e-12 |
| case_total_funding_USDT | 8.16889333433e-15 |
| case_total_gross_USDT | 3.73340623733e-13 |
| case_total_net_USDT | 2.77988392122e-13 |
| episode_execution_USDT | 8.79887022893e-16 |
| episode_fees_USDT | 3.15852029758e-16 |
| episode_fill_legs | 0 |
| episode_filled_notional_USDT | 3.36727496609e-13 |
| episode_funding_USDT | 2.57609532764e-16 |
| episode_gross_USDT | 3.96830568771e-14 |
| episode_net_USDT | 3.61120908259e-14 |
| exit_sell_quantity | 4.09388449043e-13 |
| pre_exit_quantity | 0 |
| wallet_summary_execution_USDT | 0 |
| wallet_summary_fees_USDT | 0 |
| wallet_summary_funding_USDT | 0 |
| wallet_summary_gross_USDT | 5.474335e-36 |
| wallet_summary_net_USDT | 1.7777682e-35 |

## Actual episode boundaries and inventory

All 13 episodes per condition (52 total) are eligible preceding BOTH_LONG → OLD_LONG_NEW_FLAT transitions, rather than inferred from a profitable interval. Independently rebuilt contiguous states, ending state, censorship, subsequent positive raw signal and separately subsequent actual flat-to-OPEN fill. Verified matched signal SELL leg quantities, pre-signal actual quantity, first observed minute-end zero inventory and old/new positive-inventory minute counts; partial inventory remains real. State classification does not imply the order reason caused a profit.
Base fraction reference episodes (symbol, start day index, exclusive end day index, actual two-account asset net increment): `[('BTCUSDT', 31, 45, -33.02826159458761), ('BTCUSDT', 155, 177, 60.154172010290836), ('BTCUSDT', 272, 278, 80.44475410066626), ('ETHUSDT', 293, 294, 74.82177380925243), ('SOLUSDT', 32, 50, -58.315931830944095), ('SOLUSDT', 154, 171, 124.78242324762125), ('1000PEPEUSDT', 109, 110, 37.175922095044314), ('XRPUSDT', 32, 33, 8.446697805201223), ('XRPUSDT', 155, 183, -254.76419996113955), ('XRPUSDT', 209, 214, 73.07336077058427), ('WIFUSDT', 52, 64, 52.251521743986395), ('DOGEUSDT', 149, 155, 79.5815688726332), ('ORDIUSDT', 81, 94, -44.46656450343881)]`.

## Conclusions and limits

Bridges explain where the already simulated paired wallet difference occurred. They do not answer what returns cancelling an exit, changing reentry timing, ignoring risk reductions or redistributing capital would have produced; those require a new complete strategy/account experiment. A per-asset matched-period flow difference is not an independent full-capital portfolio result.
All five raw signal categories retain BOTH_FLAT, BOTH_LONG, divergent long/flat and INELIGIBLE accounting. The fixed February/March subcheck independently validates the important recovery-period state split; full all-month state monetary rederivation and per-minute NAV/event bridges were not repeated here. Main recorded bridges and previous independent financial ledger evidence are separate scope. This check does not revalidate market QA, labels, exchange fills or historical margin rules.
Four conditions share the same selected history and signals; funding fractions/percent remain scenarios and Binance price plus Bybit fees is proxy. No unseen/OOS/selection-bias correction, risk matching, APR or deployable alpha qualification results. Original earlier-exit gains and recovery losses remain preserved, investment NONE/CASH.

Resource: 3.837024s, peak RSS 217210880 bytes; shared guard `{"aggregate_cgroup": "/sys/fs/cgroup/user.slice/user-1000.slice/user@1000.service/coin.slice/coin-quant.slice", "ram_limit_bytes": 4999999488, "ram_current_bytes": 845721600, "ram_peak_bytes": 3263008768, "swap_bytes": 0, "memory_events": "low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0", "gpu_used": false}`.
UTC-day-boundary funding journal rows inspected: 18320; first start-time zero-funding rows: 80. Zero model fits/HPO/API/new data QA/replays, no keys/locked/orders/GPU/Git or existing source edits.
