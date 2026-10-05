# D079 source and safety review

Observed parent HEAD: 6ef22565d61f0771493f2e91a8bf1bc42e00b3d6. Main account and runner were reviewed from current bytes, not old status or prior green tests. Child source review delivered partial findings before its session network permission failure; root completed this record locally. This is not represented as an independently completed child audit.

## Exact change

BacktestConfig.discretionary_rebalance_min_notional defaults to0 and validates finite/nonnegative. Band declarations validate Boolean/String only when enabled; missing fields defaultFalse/UNKNOWN. Default0 leaves historical account arithmetic, saved trade/order/daily/roundtrip schemas and summary unchanged; direct Git6ef2256 normal module reference confirms both QUOTE and RECEIVED_ASSET synthetic wallet equivalence. The old source is a small test reference only, not activity dependency or AST clone.

The target builder keeps all existing values and component states. New flags are added causally from only current and previous published target contexts: first decision protected; per-asset eligibility loss/change protected; any whole-portfolio component raw vector change protects all assets; any strictly lower risk-scaled component target for the current asset protects that asset. There is no tolerance exemption for small decreases. Remaining decisions are marked discretionary. This conservative flag does not prove a skipped order causes a return benefit; that requires the complete replay.

The full requested dollar delta uses actual execution-open mid/NAV and real received-asset inventory. Band runs only after original expiry/gap/minimum-hold/strict availability checks. Initial inventory, zero/terminal, forced exits, generic covariance/gross risk-limited goal, any asset/gross actual cap breach and a started partial fill exempt the goal. A capacity-limited40USDT fill of a130USDT initial instruction is not refused, and its final sub50 remainder still executes. Skip saves an order status but has no trade/fee/cash/quantity mutation. Sub-lot inventory remains marked and cannot become free cash.

## Necessary evidence and known failed fixture

First tests:14passed/1failed. The added other-asset-cap test let BTC sell first, restoring the cap before ETH's small goal. Its expected exemption was false for that sequential account state. Preserved source33dfc42315fc5e899e919efef03302fb2e933e84385542bbba27e3eb9e7b8d72/XML/task; changed only fixture identity toZZZ so ETH is checked while the other cap is still breached. Second tests15passed including actual BUY/SELL skips with unchanged wallet, protected reasons, forcedexit, current/other-asset breach, firstentry, partialcompletion, zero/terminal, absent/invalid flags, target-pool changes/tinycov shrink, exact prior default behavior. Account source unchanged between attempts. Both attempts retained/registered before market results.

Main uses saved D078 fixedblend as control, original D077HOLD8 as additional reference, accepted exact SHA daily/minute artifacts read-only, identical costs/capital/calendar/account except band parameter. Comparisons ignore only the new band key; all other financial config equality is mandatory. No nativeBybit/filter certification, no funds/keys/API/download/locked-body/HPO. Sourceprivate file hashes only.

## Scope and decision

Spot remains without a continuous minute price-drift reduction scheduler; the band protects currently observed mandatory reductions but does not implement that separate capability. Actual full saved minute-close caps must be verified for each new wallet; breach fails acceptance, not waived. Cash/marked/calendar/liquidation evidence remain separate. New target values must exactly match old D078, and skip reason/source-open/amount/no-fill evidence is independently checked without the flag function. Previous child D078 manual covariance and future perturbation reference is reused on the actual D079 target artifact.

One50USDT value/two costs/303seen development days only, no search. Protocol adopts for development only if both net outcomes improve and realized daily volatility/minute drawdown do not worsen versus fixedblend; no investment or stableAPR claim. Negative result keeps old recipe, retains band capability with reopen condition based on new targeted evidence rather than threshold grid. Two child sessions failed permissions before runs; root checked no live D079 test handles and ran the necessary local verification, without claiming their failed turns completed.
