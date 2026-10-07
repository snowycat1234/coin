# Fixed SHORT collateral protection: survival versus premature exit

## Decision and actual change

**Pause the exact SHORT_HALF_COLLATERAL_SIGNAL_RESET recipe. Investment qualification NONE/CASH, stable net APR UNKNOWN.** Retain original CSMOM21/SMA200 research controls and the optional paid protective-order capability. No threshold, reentry or model search follows this failure.

One new recipe was committed before wallets, at ee163df: a held SHORT whose completed-minute isolated equity falls to50% of current collateral receives a persistent reduce-only full close through the existing account/latency/volume/fees. Original expert must cease SHORT membership at a daily decision while actually flat before unblocking. No LONG filter, leverage/topup, new financial kernel or target change. Mark/funding liquidation still acts first; gaps can defeat protection.

The original four XRP witnesses had full-close capacity under the original 1min/prior-volume rules:60.000001s, roughly37h before their historical liquidation. [Capacity probe](SHORT_EXIT_CAPACITY_20261008.json) is ex-post feasibility, not a return forecast. A complete10-new-wallet contrast followed, paired with10 saved originals. Both funding interpretations remain conditional, not independent observations.

## Complete capital economics

Each row is a separate10,000USDT account, BinanceUSD-M prices/mark/funding with Bybit5.5bp taker +4bp spread +4bp slippage per side. Funding scale.01 below; scale1 is fully retained in [the actual result](SHORT_COLLATERAL_HALF_20261008.json). These are seen development stages, notOOS or stitched wealth. Boundaries and the Aug12 data gap are preserved, not filled with zero returns.

|Seen stage|Old→new net USDT|Net delta|New LONG net|New SHORT net|Minute MDD old→new|Annualized daily vol old→new|
|---|---:|---:|---:|---:|---:|---:|
|2024 Jan2–Jul2 (182d)|-604.93→-440.25|+164.68|439.27|-879.52|10.17→8.59%|9.56→9.56%|
|2024 Jul2–Aug12 (41d)|522.95→522.95|+0.00|375.16|147.80|2.53→2.53%|12.51→12.51%|
|2024 Aug13–Jan2025 (142d)|1415.06→1593.46|+178.40|2644.71|-1051.25|5.23→5.23%|11.57→11.35%|
|2025 Jan2–Jul2 (181d)|838.90→692.24|-146.66|530.07|162.16|4.16→4.91%|9.70→9.56%|
|2025 Jul2–Jan2026 (184d)|1222.72→1222.72|+0.00|522.66|700.06|3.99→3.99%|9.39→9.39%|

All new cases finished the full calendar, paid final flattening and independent minute cash/risk audit; zero new liquidation. The original2024H2 XRP liquidation remains in the controls. 2024H1/H2 net improves by about165/178USDT(scale.01), but SHORT still loses879/1051USDT. Avoiding a liquidation and reducing a loss do not establish bear-market alpha.

**2025H1 fails the frozen adoption test:** net falls146.66/146.94USDT in the two funding scenarios; SHORT falls153.04/153.55; minute MDD rises0.7555/0.7571 percentage points. Transaction cost falls about0.339USDT and volatility slightly declines, so fees/churn do not explain the failure. No change at all in the no-trigger41d July or2025H2 cases. The all-vol<=12% failure is inherited from the untouched41d baseline(12.506/12.510%), not caused by the protection. Check recomputation and final PAUSE agree exactly.

Full gross/net exposure, margin usage, price PnL, fees/execution/funding, turnover, actual volatility/DD and gain concentration for every account are in the result. Post-fill/minute gross still reaches60.176%–60.966% under the existing delayed reduction path: this adapter does not repair the previously disclosed caps drift. No risk-matched alpha, exact intraminute cap guarantee or native Bybit qualification is claimed. Original30%asset/60%gross and1x isolated settings are unchanged.

## Actual failed episode, not another trial

[Read-only episode evidence](SHORT_COLLATERAL_HALF_EPISODE_20261008.json) identifies DOGE, not XRP, as the sole2025H1 protection trigger. It opened2025-05-05 UTC; the stop observed2025-05-11 00:06UTC and filled00:07:00.000001 at.257385744(scale.01). The original expert reset onMay12 00:00UTC and the original remaining SHORT closed after this decision, final fill.23308632.

The original continued position subsequently recovered part of its loss. Original complete episode net−538.52631 versus protected−688.33360; difference−149.80729USDT, versus whole-stage SHORT delta−153.04173. Under scale1, episode difference−150.13531 versus SHORT delta−153.55422. **Both episodes still lose.** Original had no new SHORT entry during the roughly.996-day blocked interval. This counterexample principally concerns forcing out the existing SHORT, rather than missing a separate subsequent SHORT entry. It gives no support for rescuing this recipe with a shorter cooldown.

Episode arithmetic uses actual realized fill PnL(includes execution), subtracts fees once and adds owned signed funding; execution is not double-deducted. Shared NAV changes other positions, so episode and residual differences are descriptive, not a causal simulation of any hypothetical reentry. Choosing this case after its failure is diagnosis, not new validation.

## Reuse, verification and provenance

User learning document SHA d1415bc9dc18e275740465503b8394c7ad940eff803fd7e79c1f9fa78e5f513e and existing Qlib TRA/DeePM/pysystemtrade references remain in OPEN_SOURCE_REGISTRY. Apply their lessons: separate market-state information from mature expert feedback, align utility with actual positions/cost/horizon, avoid forcing weak experts, judge complete portfolios and worst stages. No claim that a shared Ridge reproduces TRA, no new Transformer, GPL copy or upstream model kernel. This turn reuses the existing Decimal isolated account, real capacity scheduler, lossless storage and independent audit; the adapter is limited research policy.

Relevant regression:4new +3existing ATR tests passed in17.61s, [XML](SHORT_COLLATERAL_TESTS_20261008.xml). Actual old35minute/two-asset golden SHA ec67a87c5c57602e2f5fb262d42f0d4b5b476e0c262a0b6a5461bb7f38062887 matches default and no-trigger paths; partial/zero-capacity persistence, causal future perturbation, actual-flat reset, liquidation-first gap and hard-risk priority covered. Initial fixture expected2fills despite capacity requiring3; expected clocks corrected, failed local XML retained(.cache/short_collateral_initial_fixture_failure.xml). No scientific parameter changed. This does not mean all old historical wallets reran.

[Independent review](SHORT_COLLATERAL_HALF_REVIEW_20261008.json) verifies every old/new native input file/manifest binding, exact unchanged target path/SHA,20capital/NAV/cost/direction bridges, complete minute paths, actual protective BUY/CLOSE fills/costs/60.000001s delay and frozen decisions. Run wallet source ee163df; post-run identity review source7540683, diagnosis sourcee281259. Later extra orchestration assertions were not retroactively claimed to have run before wallets. Full native minute accounting audit remains the bound existing auditor; the new reviewer is not an independently simulated second wallet. A separate agent reviewed code, gates, risk changes and the failed-episode interpretation.

## Decision and next direction

Adopt the survival/episode diagnosis and retain the optional close mechanism; **pause this exact trading recipe**, reopen only on independent tail-risk/utility evidence, not threshold or cooldown scanning here. Preserve original CSMOM/SMA controls, relative hedges, all signed directions and existing negative results. Do not replace them with a new stop-based investment candidate.

Next selected question is **whether separating the profitable relative LONG book from the squeeze-prone altcoin SHORT book can preserve hedge utility more efficiently using a liquid market hedge**. First inspect saved targets/actual SHORT episodes for concentration, beta and hedge loss; no new wallet or fitted model is preregistered yet. Prefer this structural comparison to another SHORT exit. A future contrast must share full capital, use only past risk estimates, keep caps/costs/units and demonstrate actual costs/risks; BTC also has squeeze/1x collateral risk, so this is a hypothesis, not a safer or profitable claim. If concentration/hedge evidence is absent, retain the strongest frozen strategy rather than manufacture another filter. Complex selectors remain paused pending stable ranking information; funding certification requires an official definition or lawful parity source, not a more profitable guessed unit.

## Reproducibility and actual resource use

Original protocol protocols/SHORT_COLLATERAL_HALF_20261008.json, SHA7b92a38cebc3a3ea29cc20d17a9a6e5061d0718f864f8f0128c657cdbfed758b, frozen before economics. On the existing server repository, use fresh state/output paths and the unchanged protocol/source:

```bash
systemd-run --user --unit=coin-short-collateral-replay --slice=coin-research.slice \
  -p MemoryMax=8000000000 -p MemorySwapMax=0 \
  -p WorkingDirectory=/home/ubuntu/coin/short-research-repository \
  env PYTHONDONTWRITEBYTECODE=1 POLARS_MAX_THREADS=1 OMP_NUM_THREADS=1 \
  OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  PYTHONPATH=/home/ubuntu/coin/short-research-repository:/home/ubuntu/coin/short-research-repository/src \
  timeout 2400 /home/ubuntu/coin/coin_collector_v3_fixed/work/research-venv/bin/python -B \
  scripts/research/run_short_collateral_protection.py \
  --protocol protocols/SHORT_COLLATERAL_HALF_20261008.json \
  --state /home/ubuntu/coin/execution-state/short-collateral-replay
```

The same8GB/swap0 bounded environment runs read-only scripts/research/review_short_collateral_protection.py and scripts/research/inspect_short_protection_failure.py, both accepting --result STATE/RESULTS.json --output FRESH.json. The episode inspector intentionally binds this exact original result SHA; it is not a generic evaluator for modified experiments. Local related tests run via scripts/with_task_progress.sh → scripts/bounded.sh with pytest basetemp under /home/xflops/coin-state, never source/store.

Actual server accounts10/10, failed0, exit0,346.077049s; capacity probe.237125s; independent review1.392719s; episode diagnosis 0.341199s,0additionalwallets/fits. These stage timings are internal, not total session or transfer/publication time; uninstrumented intervals/model configuration UNKNOWN. Main state83,408,554B +capacity16,260B measured2026-10-07T23:38:01Z, no new market downloads. Largest observed task RAM sample2,993,672,192B; true peak unavailable, not inferred from samples. Verified shared parent8GB/swap0, GPU0; no surviving short research unit at this observation, collector health not recertified. UI relay completed10/10, not a continuing background experiment; its first import failure was repaired without touching science.

D project+entireWSLVHD latest real scan45,455,143,069B@1791408013.8738086 predates this small addition, not a current scan. D budget150GB/warn120/stop135/reserve15 unchanged. Server run reserved15GiB and actual owned state stayed below250MB. Funding-unit/MMR/filter/source-clock assumptions, CORE5 selection, seen data and actual-risk differences still prevent promotion. No keys, real/Testnet/mainnet orders, paid service, GPU or locked body used.
