# Two legal-origin shared-selector diagnostic

Completed exactly two prespecified 15-parameter fits on October 15, 2026. The November 12 and December 10, 2023 origins are simulated availability clocks, not claims of historical issuance. The old July/October plan remains blocked; its full history is retained under protocol/.

The five primary dates are a tiny conditional known-development diagnostic. All figures below are native source utility, not returns or APR. No advantage, significance, statistical independence, clean causal attribution, fresh out-of-sample, risk certification or deployment claim is supported.

## Primary and secondary results

### primary_5

| Scope | Dates | Chosen utility mean | Oracle utility mean | Regret mean |
|---|---:|---:|---:|---:|
| pooled | 5 | -0.000441805984 | 0.008457635612 | 0.008899441596 |
| 2023-11-12 | 4 | 0.000000000000 | 0.007381970108 | 0.007381970108 |
| 2023-12-10 | 1 | -0.002209029921 | 0.012760297627 | 0.014969327548 |

All means weight dates equally; pooled means are computed directly over dates. Paired differences subtract each control on the same date before averaging.

| Scope | Control | Mean utility | Chosen minus control | Available | CASH fallbacks |
|---|---|---:|---:|---:|---:|
| pooled | CASH | 0.000000000000 | -0.000441805984 | 5 | 0 |
| pooled | VOL_MANAGED_HOLD | -0.002618323527 | 0.002176517543 | 5 | 0 |
| pooled | PUBLIC_SMA50_200_SIGNED | -0.001586073642 | 0.001144267657 | 5 | 0 |
| pooled | DONCHIAN_EXIT10 | -0.002738382579 | 0.002296576595 | 5 | 0 |
| pooled | CSMOM21 | 0.002476987435 | -0.002918793419 | 5 | 0 |
| pooled | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.011276961334 | 0.010835155350 | 5 | 0 |
| 2023-11-12 | CASH | 0.000000000000 | 0.000000000000 | 4 | 0 |
| 2023-11-12 | VOL_MANAGED_HOLD | -0.002720646928 | 0.002720646928 | 4 | 0 |
| 2023-11-12 | PUBLIC_SMA50_200_SIGNED | -0.001430334572 | 0.001430334572 | 4 | 0 |
| 2023-11-12 | DONCHIAN_EXIT10 | -0.002870720744 | 0.002870720744 | 4 | 0 |
| 2023-11-12 | CSMOM21 | -0.000093840113 | 0.000093840113 | 4 | 0 |
| 2023-11-12 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.008201900263 | 0.008201900263 | 4 | 0 |
| 2023-12-10 | CASH | 0.000000000000 | -0.002209029921 | 1 | 0 |
| 2023-12-10 | VOL_MANAGED_HOLD | -0.002209029921 | 0.000000000000 | 1 | 0 |
| 2023-12-10 | PUBLIC_SMA50_200_SIGNED | -0.002209029921 | 0.000000000000 | 1 | 0 |
| 2023-12-10 | DONCHIAN_EXIT10 | -0.002209029921 | 0.000000000000 | 1 | 0 |
| 2023-12-10 | CSMOM21 | 0.012760297627 | -0.014969327548 | 1 | 0 |
| 2023-12-10 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.023577205618 | 0.021368175697 | 1 | 0 |

Choice counts: {"pooled": {"CASH": 4, "VOL_MANAGED_HOLD": 0, "PUBLIC_SMA50_200_SIGNED": 0, "DONCHIAN_EXIT10": 1, "CSMOM21": 0, "PRICE_ONLY_PATCH_CAUSAL_RANK": 0}, "2023-11-12": {"CASH": 4, "VOL_MANAGED_HOLD": 0, "PUBLIC_SMA50_200_SIGNED": 0, "DONCHIAN_EXIT10": 0, "CSMOM21": 0, "PRICE_ONLY_PATCH_CAUSAL_RANK": 0}, "2023-12-10": {"CASH": 0, "VOL_MANAGED_HOLD": 0, "PUBLIC_SMA50_200_SIGNED": 0, "DONCHIAN_EXIT10": 1, "CSMOM21": 0, "PRICE_ONLY_PATCH_CAUSAL_RANK": 0}}

### secondary_36

| Scope | Dates | Chosen utility mean | Oracle utility mean | Regret mean |
|---|---:|---:|---:|---:|
| pooled | 36 | 0.000537621042 | 0.010052729496 | 0.009515108454 |
| 2023-11-12 | 28 | 0.000000000000 | 0.008909837916 | 0.008909837916 |
| 2023-12-10 | 8 | 0.002419294688 | 0.014052850028 | 0.011633555340 |

All means weight dates equally; pooled means are computed directly over dates. Paired differences subtract each control on the same date before averaging.

| Scope | Control | Mean utility | Chosen minus control | Available | CASH fallbacks |
|---|---|---:|---:|---:|---:|
| pooled | CASH | 0.000000000000 | 0.000537621042 | 36 | 0 |
| pooled | VOL_MANAGED_HOLD | 0.000481968520 | 0.000055652522 | 36 | 0 |
| pooled | PUBLIC_SMA50_200_SIGNED | 0.001001785622 | -0.000464164580 | 36 | 0 |
| pooled | DONCHIAN_EXIT10 | 0.000594989029 | -0.000057367987 | 36 | 0 |
| pooled | CSMOM21 | 0.003371074222 | -0.002833453181 | 36 | 0 |
| pooled | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.010125580867 | 0.010663201908 | 36 | 0 |
| 2023-11-12 | CASH | 0.000000000000 | 0.000000000000 | 28 | 0 |
| 2023-11-12 | VOL_MANAGED_HOLD | 0.001178558076 | -0.001178558076 | 28 | 0 |
| 2023-11-12 | PUBLIC_SMA50_200_SIGNED | 0.001846894350 | -0.001846894350 | 28 | 0 |
| 2023-11-12 | DONCHIAN_EXIT10 | 0.001323870160 | -0.001323870160 | 28 | 0 |
| 2023-11-12 | CSMOM21 | 0.000435286123 | -0.000435286123 | 28 | 0 |
| 2023-11-12 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.006272209683 | 0.006272209683 | 28 | 0 |
| 2023-12-10 | CASH | 0.000000000000 | 0.002419294688 | 8 | 0 |
| 2023-12-10 | VOL_MANAGED_HOLD | -0.001956094927 | 0.004375389615 | 8 | 0 |
| 2023-12-10 | PUBLIC_SMA50_200_SIGNED | -0.001956094927 | 0.004375389615 | 8 | 0 |
| 2023-12-10 | DONCHIAN_EXIT10 | -0.001956094927 | 0.004375389615 | 8 | 0 |
| 2023-12-10 | CSMOM21 | 0.013646332569 | -0.011227037880 | 8 | 0 |
| 2023-12-10 | PRICE_ONLY_PATCH_CAUSAL_RANK | -0.023612380011 | 0.026031674699 | 8 | 0 |

Choice counts: {"pooled": {"CASH": 31, "VOL_MANAGED_HOLD": 0, "PUBLIC_SMA50_200_SIGNED": 0, "DONCHIAN_EXIT10": 5, "CSMOM21": 0, "PRICE_ONLY_PATCH_CAUSAL_RANK": 0}, "2023-11-12": {"CASH": 28, "VOL_MANAGED_HOLD": 0, "PUBLIC_SMA50_200_SIGNED": 0, "DONCHIAN_EXIT10": 0, "CSMOM21": 0, "PRICE_ONLY_PATCH_CAUSAL_RANK": 0}, "2023-12-10": {"CASH": 3, "VOL_MANAGED_HOLD": 0, "PUBLIC_SMA50_200_SIGNED": 0, "DONCHIAN_EXIT10": 5, "CSMOM21": 0, "PRICE_ONLY_PATCH_CAUSAL_RANK": 0}}

## All 36 daily choices

The five primary dates are marked Yes. Global disjoint admission is not reset on December 10. Four primary dates use the first model and just one uses the second.

| Date | Origin | Primary | Choice | Chosen utility | Oracle utility | Regret |
|---|---|---|---|---:|---:|---:|
| 2023-11-12 | 2023-11-12 | Yes | CASH | 0.000000000000 | 0.000000000000 | 0.000000000000 |
| 2023-11-13 | 2023-11-12 |  | CASH | 0.000000000000 | 0.000226715218 | 0.000226715218 |
| 2023-11-14 | 2023-11-12 |  | CASH | 0.000000000000 | 0.000000000000 | 0.000000000000 |
| 2023-11-15 | 2023-11-12 |  | CASH | 0.000000000000 | 0.005494563906 | 0.005494563906 |
| 2023-11-16 | 2023-11-12 |  | CASH | 0.000000000000 | 0.009019223923 | 0.009019223923 |
| 2023-11-17 | 2023-11-12 |  | CASH | 0.000000000000 | 0.002890419720 | 0.002890419720 |
| 2023-11-18 | 2023-11-12 |  | CASH | 0.000000000000 | 0.004486786391 | 0.004486786391 |
| 2023-11-19 | 2023-11-12 |  | CASH | 0.000000000000 | 0.002359834955 | 0.002359834955 |
| 2023-11-20 | 2023-11-12 | Yes | CASH | 0.000000000000 | 0.003229449208 | 0.003229449208 |
| 2023-11-21 | 2023-11-12 |  | CASH | 0.000000000000 | 0.000000000000 | 0.000000000000 |
| 2023-11-22 | 2023-11-12 |  | CASH | 0.000000000000 | 0.010959734330 | 0.010959734330 |
| 2023-11-23 | 2023-11-12 |  | CASH | 0.000000000000 | 0.004533229098 | 0.004533229098 |
| 2023-11-24 | 2023-11-12 |  | CASH | 0.000000000000 | 0.008138840765 | 0.008138840765 |
| 2023-11-25 | 2023-11-12 |  | CASH | 0.000000000000 | 0.005749199579 | 0.005749199579 |
| 2023-11-26 | 2023-11-12 |  | CASH | 0.000000000000 | 0.007391780141 | 0.007391780141 |
| 2023-11-27 | 2023-11-12 |  | CASH | 0.000000000000 | 0.010586763256 | 0.010586763256 |
| 2023-11-28 | 2023-11-12 | Yes | CASH | 0.000000000000 | 0.019558541316 | 0.019558541316 |
| 2023-11-29 | 2023-11-12 |  | CASH | 0.000000000000 | 0.018868840465 | 0.018868840465 |
| 2023-11-30 | 2023-11-12 |  | CASH | 0.000000000000 | 0.017998945527 | 0.017998945527 |
| 2023-12-01 | 2023-11-12 |  | CASH | 0.000000000000 | 0.022315412482 | 0.022315412482 |
| 2023-12-02 | 2023-11-12 |  | CASH | 0.000000000000 | 0.027703045665 | 0.027703045665 |
| 2023-12-03 | 2023-11-12 |  | CASH | 0.000000000000 | 0.016310070128 | 0.016310070128 |
| 2023-12-04 | 2023-11-12 |  | CASH | 0.000000000000 | 0.018090732824 | 0.018090732824 |
| 2023-12-05 | 2023-11-12 |  | CASH | 0.000000000000 | 0.009325340769 | 0.009325340769 |
| 2023-12-06 | 2023-11-12 | Yes | CASH | 0.000000000000 | 0.006739889906 | 0.006739889906 |
| 2023-12-07 | 2023-11-12 |  | CASH | 0.000000000000 | 0.007694265828 | 0.007694265828 |
| 2023-12-08 | 2023-11-12 |  | CASH | 0.000000000000 | 0.009803836236 | 0.009803836236 |
| 2023-12-09 | 2023-11-12 |  | CASH | 0.000000000000 | 0.000000000000 | 0.000000000000 |
| 2023-12-10 | 2023-12-10 |  | CASH | 0.000000000000 | 0.007158874304 | 0.007158874304 |
| 2023-12-11 | 2023-12-10 |  | CASH | 0.000000000000 | 0.000000000000 | 0.000000000000 |
| 2023-12-12 | 2023-12-10 |  | CASH | 0.000000000000 | 0.000884812545 | 0.000884812545 |
| 2023-12-13 | 2023-12-10 |  | DONCHIAN_EXIT10 | -0.004853781838 | 0.001997082129 | 0.006850863967 |
| 2023-12-14 | 2023-12-10 | Yes | DONCHIAN_EXIT10 | -0.002209029921 | 0.012760297627 | 0.014969327548 |
| 2023-12-15 | 2023-12-10 |  | DONCHIAN_EXIT10 | 0.001740860461 | 0.026439406807 | 0.024698546347 |
| 2023-12-16 | 2023-12-10 |  | DONCHIAN_EXIT10 | 0.012394515097 | 0.028682830969 | 0.016288315873 |
| 2023-12-17 | 2023-12-10 |  | DONCHIAN_EXIT10 | 0.012281793707 | 0.034499495841 | 0.022217702133 |

## Fit and provenance checks

Both solves used one CPU, one BLAS thread, lambda 1, separate date-weighted prefix scalers, and five penalized expert biases plus ten shared weights. CASH has score zero. Missing vectors remain null. No full-506 fit, later-trained Ridge model, new download, held-out period, 2024 outcome scoring, or optimization restart was used. Models were sealed before forecast choices and metric calculation. The 506-row source fixture was stripped of its global scaler and standardized z values before use. Only prefix observations enter each fold design.

Source extraction previously checked the learned expert’s causal prediction receipt and model/scaler timing against its cutoff and decision. This run inherits that source audit; those original receipts are not exported or independently re-derived here. Exported target/feedback clocks were rechecked before each solve. The literal November 4 pool gate was enforced separately.

Training support: November origin 456 dates, 2,042 noncash observations, 64 disjoint admissions; December origin 484 dates, 2,182 observations, 68 admissions. These counts do not establish independent samples or sufficiency relative to parameter count.

Nine structural tests passed before real fits. Post-fit checks verify saved coefficient gradients, direct mean arithmetic, all controls and all 36 choices without refitting. Actual timestamps, versions, objective values and gradient norms are in receipts/fit_receipts.json.

Static controls and all availability masks are included in results/all_36_dates.json and .csv; summaries include every control per fold and pooled for both reporting sets. No control was selected retrospectively.

The full historical protocol files retain their original NO FIT preparation status. The current run authorization and completion are recorded separately in receipts/RUN_AUTHORIZATION.md; these archival statuses are not current execution status.

An independent read-only reconstruction also passed: prefix moments, saved-coefficient normal equations, scores, all 36 choices, all summary arithmetic and controls. Its portable checker and sanitized receipt are included. The artifacts record exactly two fits; absence of unrecorded activity cannot be independently proved from artifacts alone.
