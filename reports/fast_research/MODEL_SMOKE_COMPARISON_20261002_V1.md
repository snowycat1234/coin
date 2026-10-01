# Ten-configuration common real-data engineering comparison

Two days of sources, one short engineering fold, 982 common test endpoints. Not first-round research or production evidence.

| model | BTC flow IC | ETH flow IC | BTC return rank | ETH return rank | net proxy | trades |
|---|---|---|---|---|---|---|
| RIDGE-1 | 0.07942 | 0.06810 | -0.01770 | 0.02842 | -0.530777% | 28 |
| XGB-S | -0.00052 | 0.02722 | 0.04472 | -0.05774 | 0.000000% | 0 |
| XGB-M | 0.01408 | -0.05227 | 0.07628 | -0.03432 | 0.000000% | 0 |
| TCN-S | 0.06480 | 0.04967 | -0.06199 | 0.09454 | 0.000000% | 0 |
| TCN-M | 0.10036 | 0.07465 | -0.04126 | 0.07540 | 0.000000% | 0 |
| MLPLOB-1 | 0.02186 | 0.01409 | -0.02124 | -0.07450 | 0.000000% | 0 |
| TLOB-1 | -0.01091 | -0.04696 | 0.00751 | 0.08986 | 0.000000% | 0 |
| TS2VEC-LINEAR-1 | -0.19380 | -0.12497 | -0.13653 | -0.08977 | -0.437386% | 10 |
| TS2VEC-LGB-1 | -0.06869 | -0.02024 | -0.03079 | -0.07258 | 0.000000% | 0 |
| RIVER-1 | -0.00811 | 0.01975 | -0.02390 | 0.09813 | -14.327113% | 566 |

All models share one batch/scalers/labels and 20bp fees+8bp extra slippage+2bp assumed spread roundtrip.
TCN/TLOB/MLPLOB use one engineering epoch; formal preregistered max10 and six complete OOS folds remain pending.
Predictive ICs cover conditional fully observable future labels. Economic proxy is not actual executable BBO.
No top-3 selection and no locked-history consumption.
