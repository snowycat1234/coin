# Frozen-selector decision-quality falsification

## Finding

On 22 chronologically selected, nonoverlapping seven-day reference-label intervals in already-seen 2024H1 development history, adding the frozen 13-field market context did not improve the forecast’s highest-ranked expert choice. Market-plus-state beat state-only in 2 blocks, lost in 6, and tied in 14. The argmax choices differed in 8 blocks. This is a new forecast diagnostic, not a new portfolio backtest or a rerun of the actual soft-budget selector.

Reference opportunities were present: the unattainable best eligible expert had positive utility in 21 of 22 blocks. Neither frozen model captured positive average utility through its argmax choices. This falsifies a lack-of-opportunity explanation on this particular reference-label sample; it does not establish that those opportunities were predictable or executable.

## Results

| Metric | State only | Market + state |
|---|---:|---:|
| Mean chosen utility | -0.002061853 | -0.004648959 |
| Mean oracle regret | 0.013269923 | 0.015857029 |
| Positive / zero / negative utility blocks | 11 / 5 / 6 | 7 / 7 / 8 |
| Pooled pairwise ordering accuracy | 62.54% | 54.92% |

Market minus state mean chosen utility: −0.002587106. Cash utility: exactly zero. Mean unattainable oracle utility: +0.011208070. These are dimensionless utility values, not percentages, USDT, net portfolio returns or APR.

Utility = log(1 + seven-day net reference return) − 0.5 × daily reference maximum drawdown. Original reference labels use quantity accounting, 13.5 basis points per side, funding under the original conditional source interpretation, and paid terminal exit. They are standalone expert-reference labels. No additive mixture of their profits is asserted.

## Frozen procedure

- The protocol was written before inspecting prediction/utility values. No fit, parameter search, new download or historical wallet was run.
- Existing two-model predictions cover 182 scoring dates, January 1 through June 30, 2024. Original complete/mature support is 176 dates through June 24. June 25–30 are excluded, not filled or scored.
- Greedy chronological selection starts with the earliest eligible common date, then requires the next decision to occur strictly after the preceding label-availability clock. Labels mature seven days plus 120.000001 seconds after decision. The resulting starts are eight calendar days apart; 22 blocks are retained, with no phase search.
- Nonoverlapping intervals are not asserted to be statistically independent. There are no p-values or significance claims.
- Both forecasts use exactly the same original eligible-expert masks. All six experts are available in each retained block. Actual target availability, original state feedback, market features, learned-ranker metadata and saved selector fit clocks were checked.
- Saved forecasts do not have a separate per-row publication timestamp. Availability is supported by saved model metadata and the original causal input conditions; historical real-time issuance is not certified.
- Highest forecast wins; exact forecast ties average the tied experts’ realized utility and assign fractional choice counts. There were no top forecast ties. This diagnostic choice rule differs from the original soft allocation and its turnover limit.
- Pairwise ordering: correct order gets 1; forecast tie gets 0.5; wrong order gets 0. Equal realized-utility pairs are excluded. There were 315 compared pairs, 15 actual ties excluded and zero forecast pair ties. Pairs within dates and dates within a regime are dependent.
- Cash is also the genuine pre-cutoff train-best-single baseline: all five noncash mean utilities are negative across the original 40 disjoint training rows. Training labels precede the December 25, 2023 cutoff; the saved fits become available January 1, 2024. The diagnostic did not select a baseline using 2024 outcomes.
- The oracle is an ex-post ceiling calculated only for diagnostic comparison. It is not fitted, tradable, a recommended strategy, or a causal model.

## Chosen experts

| Expert | State only | Market + state |
|---|---:|---:|
| CASH | 5 | 6 |
| VOL_MANAGED_HOLD | 5 | 7 |
| PUBLIC_SMA50_200_SIGNED | 1 | 0 |
| DONCHIAN_EXIT10 | 0 | 2 |
| CSMOM21 | 7 | 7 |
| PRICE_ONLY_PATCH_CAUSAL_RANK | 4 | 0 |

## Every retained block

| Start UTC | State choice | State utility | Market choice | Market utility | Market − state | Oracle utility |
|---|---|---:|---|---:|---:|---:|
| 2024-01-01 | CASH | 0.00000000 | CSMOM21 | 0.00486339 | 0.00486339 | 0.00548884 |
| 2024-01-09 | VOL_MANAGED_HOLD | -0.00796220 | VOL_MANAGED_HOLD | -0.00796220 | 0.00000000 | 0.00692180 |
| 2024-01-17 | CASH | 0.00000000 | CASH | 0.00000000 | 0.00000000 | 0.00431418 |
| 2024-01-25 | PUBLIC_SMA50_200_SIGNED | 0.00209756 | DONCHIAN_EXIT10 | 0.00000000 | -0.00209756 | 0.00209756 |
| 2024-02-02 | VOL_MANAGED_HOLD | 0.00418226 | VOL_MANAGED_HOLD | 0.00418226 | 0.00000000 | 0.00511974 |
| 2024-02-10 | VOL_MANAGED_HOLD | 0.01677683 | VOL_MANAGED_HOLD | 0.01677683 | 0.00000000 | 0.01677683 |
| 2024-02-18 | CASH | 0.00000000 | CASH | 0.00000000 | 0.00000000 | 0.02058396 |
| 2024-02-26 | CSMOM21 | -0.02595578 | CSMOM21 | -0.02595578 | 0.00000000 | 0.06968578 |
| 2024-03-05 | CSMOM21 | -0.01640088 | CSMOM21 | -0.01640088 | 0.00000000 | 0.00175994 |
| 2024-03-13 | CSMOM21 | -0.05157658 | CSMOM21 | -0.05157658 | 0.00000000 | 0.00000000 |
| 2024-03-21 | CSMOM21 | 0.00857963 | CSMOM21 | 0.00857963 | 0.00000000 | 0.00857963 |
| 2024-03-29 | CSMOM21 | -0.01701425 | CSMOM21 | -0.01701425 | 0.00000000 | 0.00569416 |
| 2024-04-06 | CSMOM21 | 0.00882329 | DONCHIAN_EXIT10 | -0.01084418 | -0.01966748 | 0.00882329 |
| 2024-04-14 | VOL_MANAGED_HOLD | 0.00415223 | VOL_MANAGED_HOLD | 0.00415223 | 0.00000000 | 0.00415223 |
| 2024-04-22 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.01381897 | VOL_MANAGED_HOLD | -0.01030955 | -0.02412852 | 0.01381897 |
| 2024-04-30 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.04069430 | VOL_MANAGED_HOLD | 0.00180979 | 0.04250409 | 0.00372567 |
| 2024-05-08 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.00687669 | CSMOM21 | -0.01791568 | -0.02479236 | 0.00687669 |
| 2024-05-16 | VOL_MANAGED_HOLD | 0.01533788 | VOL_MANAGED_HOLD | 0.01533788 | 0.00000000 | 0.01847628 |
| 2024-05-24 | CASH | 0.00000000 | CASH | 0.00000000 | 0.00000000 | 0.00090720 |
| 2024-06-01 | CASH | 0.00000000 | CASH | 0.00000000 | 0.00000000 | 0.00169733 |
| 2024-06-09 | CSMOM21 | 0.00212744 | CASH | 0.00000000 | -0.00212744 | 0.00960700 |
| 2024-06-17 | PRICE_ONLY_PATCH_CAUSAL_RANK | 0.03147046 | CASH | 0.00000000 | -0.03147046 | 0.03147046 |

## Reproduction and limits

The small derived input fixture includes all 176 approved mature dates, both saved forecasts, original utilities, common masks and checked availability summaries. It omits source private locations, source-data fingerprints, model binaries and unrelated arrays. Run: python diagnostic.py derived_inputs.json RESULTS_REPRODUCED.json. Tests: python -m unittest -v test_diagnostic.py.

Twenty-two synthetic tests pass. The private source reader independently reconstructed all 1,056 mature utility cells from the original net-return/drawdown fields within absolute 1e-15. Original artifact contents remain unchanged. Independent arithmetic review is supplied separately.

This reuses previously seen development history; it is not fresh OOS. It does not test the blocked annual partial-admission wallet, certify funding archive units, establish live execution, or imply a validated annual return. A positive reference oracle cannot establish learnability. Changes to a model would need a separately frozen past-only training experiment, without selection on this 2024H1 result.
