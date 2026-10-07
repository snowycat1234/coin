# Transformer v2 development report



Seen development history; these independent reset-wallet returns are never added into one APR. Locked 2026-03 through 2026-08 has not been read.

Native new cases: 720; reused baseline cases: 72. Every seed and ensemble is retained.

## Fixed ranking

|Architecture|Mapping|Worst funding median net %|Worst funding paired delta strongest static pct|Development gate|

|---|---|---:|---:|---|

|TRANSFORMER_SHARED|DIRECTIONAL|-5.4753|-4.0308|False|

|TRANSFORMER_SHARED|NEUTRAL|NOT_EVALUABLE|NOT_EVALUABLE|False|

|TRANSFORMER_SHARED|COMBINED|NOT_EVALUABLE|NOT_EVALUABLE|False|

|CROSS_ASSET_UTILITY|DIRECTIONAL|-1.7914|-4.2592|False|

|CROSS_ASSET_UTILITY|NEUTRAL|NOT_EVALUABLE|NOT_EVALUABLE|False|

|CROSS_ASSET_UTILITY|COMBINED|NOT_EVALUABLE|NOT_EVALUABLE|False|

|CROSS_ASSET_MULTITASK|DIRECTIONAL|-3.1555|-6.4842|False|

|CROSS_ASSET_MULTITASK|NEUTRAL|NOT_EVALUABLE|NOT_EVALUABLE|False|

|CROSS_ASSET_MULTITASK|COMBINED|NOT_EVALUABLE|NOT_EVALUABLE|False|

|PATCH_CROSS_ASSET_MULTITASK|DIRECTIONAL|-4.9956|-6.3796|False|

|PATCH_CROSS_ASSET_MULTITASK|NEUTRAL|NOT_EVALUABLE|NOT_EVALUABLE|False|

|PATCH_CROSS_ASSET_MULTITASK|COMBINED|NOT_EVALUABLE|NOT_EVALUABLE|False|



## Frozen locked candidate

{"family": "CROSS_ASSET_UTILITY", "mapping": "DIRECTIONAL", "seed_rule": "FIXED_THREE_SEED_AVERAGE", "pool_rule": "FIXED_THREE_READOUT_AVERAGE"}

The development gate does not change the architecture or locked protocol. A failed gate is carried into the final decision; locked evidence cannot silently erase it.

## Costs, participation and regimes

Full per-seed/per-window net, price gross, fee, spread, slippage, funding, turnover, daily Sharpe/volatility, minute MDD, actual exposure and long/short contribution are in DEV_RESULTS.json and DEV_SUMMARY.csv.

Paired SMA, strongest static and unchanged old Transformer deltas are retained in DEV_RESULTS.json. Prediction losses, IC, Spearman, hit rate and utility rank are in PREDICTION_METRICS.json.

CLS/attention/last ensemble readouts are diagnostics only and are not candidate rankings.

## Oracle qualification

NONCAUSAL_NONDEPLOYABLE_FUTURE_PROXY_DIAGNOSTIC_NOT_GLOBAL_OPTIMAL_MINUTE_WALLET_BOUND

Missing 60d/30d future labels never bridge locked boundary; oracle is cash on such dates and cannot certify a tight full-window ceiling

No oracle is deployable; no oracle enters causal selection. Futures-dependent validity never becomes a candidate availability filter.

## Remaining mandatory phase

Locked evaluation and final decision are not complete. Investment status remains NONE/CASH.
