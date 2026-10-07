# Oracle-policy development comparison

CONDITIONAL_MINUTE_MARK_BYBIT_STYLE; NATIVE_RISK_SNAPSHOT_UNAVAILABLE

Complete calendar and paid terminal cash: 1782/1788 rows. Stopped accounts remain N/E in the full row table.
Independent reset wallets and overlapping windows are never added into one return. Fixed three-seed prediction ensembles are used.

|Model|Profile|Mapping|Worst funding median net %|Paired delta strongest static pct|Gate|
|---|---|---|---:|---:|---|
|PATCH_CROSS_ASSET_MULTITASK|FULL|DIRECTIONAL|-4.9956|-6.3796|False|
|PATCH_CROSS_ASSET_MULTITASK|FULL|NEUTRAL|1.5914|-3.1354|False|
|PATCH_CROSS_ASSET_MULTITASK|FULL|COMBINED|1.3596|-4.6905|False|
|ORACLE_POLICY_CROSS_ASSET|FULL|DIRECTIONAL|0.8354|-4.1833|False|
|ORACLE_POLICY_CROSS_ASSET|FULL|NEUTRAL|4.1398|-4.9645|False|
|ORACLE_POLICY_CROSS_ASSET|FULL|COMBINED|0.6426|-5.0782|False|
|ORACLE_POLICY_PATCH_CROSS_ASSET|FULL|DIRECTIONAL|1.4800|-6.1650|False|
|ORACLE_POLICY_PATCH_CROSS_ASSET|FULL|NEUTRAL|-2.1246|-7.7615|False|
|ORACLE_POLICY_PATCH_CROSS_ASSET|FULL|COMBINED|1.5343|-6.6707|False|
|PATCH_CROSS_ASSET_MULTITASK|HALF|DIRECTIONAL|-2.5985|-3.4089|False|
|PATCH_CROSS_ASSET_MULTITASK|HALF|NEUTRAL|-0.3348|-1.8856|False|
|PATCH_CROSS_ASSET_MULTITASK|HALF|COMBINED|0.3653|-2.5888|False|
|ORACLE_POLICY_CROSS_ASSET|HALF|DIRECTIONAL|0.4713|-2.4260|False|
|ORACLE_POLICY_CROSS_ASSET|HALF|NEUTRAL|2.0065|-2.2794|False|
|ORACLE_POLICY_CROSS_ASSET|HALF|COMBINED|0.3786|-2.7824|False|
|ORACLE_POLICY_PATCH_CROSS_ASSET|HALF|DIRECTIONAL|0.3710|-3.3034|False|
|ORACLE_POLICY_PATCH_CROSS_ASSET|HALF|NEUTRAL|-1.1039|-3.9138|False|
|ORACLE_POLICY_PATCH_CROSS_ASSET|HALF|COMBINED|0.7824|-3.5951|False|
|CROSS_ASSET_MULTITASK|FULL|DIRECTIONAL|-3.1555|-6.4842|False|
|CROSS_ASSET_MULTITASK|FULL|NEUTRAL|N/E|N/E|False|
|CROSS_ASSET_MULTITASK|FULL|COMBINED|-0.0900|-3.9402|False|
|CROSS_ASSET_MULTITASK|HALF|DIRECTIONAL|-1.6332|-3.5033|False|
|CROSS_ASSET_MULTITASK|HALF|NEUTRAL|N/E|N/E|False|
|CROSS_ASSET_MULTITASK|HALF|COMBINED|0.0763|-2.2330|False|

Frozen candidate: {"family": "ORACLE_POLICY_CROSS_ASSET", "mapping": "NEUTRAL", "profile": "FULL"}
Development gate: False; a failed gate carries into the final decision.
FULL/HALF matched differences, every seed/window/cost/liquidation/reentry, long/short net, MDD/vol/Sharpe and actual gross are in DEV_RESULTS.json.
Prediction IC/rank/hit/spread and mature daily-proxy regret are separate from actual wallet net. No causal inference consumes future labels.
Locked economics has not yet been read. Investment state: NONE/CASH.
