# Fixed daily RSI2 native61 diagnostic

Exactly one fresh $10,000 CORE5 wallet covers May 1 through July 1 exclusive, 2024. This is an explicitly new scope port of the old signal, on already-seen development data. No thresholds, periods, allocation, covariance target, budget ramp, fees, funding or native execution behavior were tuned. The source/config/readiness plan was published at `c28ad4e5ffd06929df700066a729e485fcb68c59` and publicly read back before account creation.

The official PyPI CPython3.12/Linux `jesse-rust==1.3.0` wheel was recovered with SHA256 `65c0e9edd3af5397642ca417da2ef7c23f311d6fa2bf6a2d46c729f656528cee`. Its extension is exactly `4ca1bc482f53650842817901ce8a1199d302db93242949fdaeffcb9384c8b2eb`, and package initializer/METADATA also match the historical binding. The old `RSI2_GATE.json` describes the earlier missing-dependency state; this recovery supersedes that blocker. No wheel or raw market archive is redistributed.

Only the wrapper's installation-location resolution changed. Set `COIN_RSI2_KERNEL_TARGET` to the explicitly recovered directory. The historical binding, version, indicator/strategy/vendor bytes and compiled kernel remain pinned. Three tests compare scalar/sequential numeric output and daily long/short behavior against the unchanged old wrapper with only its filesystem location remapped, plus rejection of an unverified installation. All passed. The indicator AST identity is unchanged. All 305 actual asset/decision contexts have240 real completed bars; the named CASH/RSI bridge has zero error against the original E5 budget/mixture math.

Rules remain: RSI2 long at completed close>SMA200 and RSI2<=10, short at close<SMA200 and RSI2>=90; long exit close>SMA5, short exit close<SMA5; held exit first and no same-day reentry. Initial signal state is flat at May1. The original equal .6/5 allocation, no redistribution of inactive budgets, past30 covariance10% scale-down, fresh CASH dailyL1.1 ramp, isolated1x/MMR.005, BASE27, actual signed funding1, engine-owned quantities, delayed/partial shared-capacity fills, final-day zero and paid closure apply. Financial engine SHA256 remains `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.

| Native result | USDT |
| --- | ---: |
| Gross price PnL, same quantities | -9.949753 |
| Fees | 15.868746 |
| Execution cost | 23.081806 |
| Signed funding PnL | -11.851022 |
| Net | **-60.751327** |
| Long net contribution | -70.658442 |
| Short net contribution | +9.907115 |

There were92 actual fill legs, 87,840 completed minutes and915 original funding events. The account paid to close flat and had zero liquidations. Mean/peak gross exposure was7.84%/29.07%, maximum per-asset exposure and turnover are in the result JSON, and all-observation drawdown was3.41%. Independent Decimal reconciliation and actual-source fill/capacity/fee/mark/funding checks passed; maximum NAV/wallet discrepancy was1.82e-12 USDT.

The recipe failed economically and stops here. No parameter retuning, pool promotion, model training or further RSI wallet is justified by this seen window.

## Actual month and daily attribution

| Separate native wallet | May net | June net | May mean gross | June mean gross |
| --- | ---: | ---: | ---: | ---: |
| SMA50/200 signed | +254.78 | -265.28 | 14.42% | 26.25% |
| Donchian exit10 | +85.58 | -213.99 | 7.04% | 10.50% |
| RSI2 long/short | +61.74 | -122.49 | 1.70% | 14.19% |
| Shared VOL/CSMOM50/50 | -56.32 | -132.69 | 18.05% | 27.73% |

SMA had positive combined price PnL22.74, erased by fees/execution13.82 and net funding19.41. Donchian already lost100.58 before costs/funding. RSI had slightly negative combined price PnL plus50.80 of costs/funding. Their losses do not establish that the whole market fell over the combined period. All three carried more exposure in June; RSI had no short exposure in June. Donchian's first actual entry was May16, versus May1 for SMA/RSI. Those timing/exposure facts are distinct from a causal claim about the ramp.

The 20-day CASH deployment differs from continuously running accounts. Actual first20-day net was+314.97 SMA,+170.44 Donchian,+20.71 RSI. No matched no-ramp or continuously running same-expert counterfactual has been run, so these figures neither measure nor dismiss missed opportunity from the ramp.

RSI gained on4 SMA loss days,1 Donchian loss day and10 shared50/50 loss days. It gained on only1 of25 days when both trend wallets lost, and lost387.35 in aggregate on those25 days. SMA gained while Donchian lost on only1 day, and the reverse also occurred on1 day. Separate wallets have different ramp, holding, fills and cost paths: these counts are factual co-occurrence, not a realizable switching payoff. No ex-post best-expert sum was calculated.

Standalone May-June VOL and CSMOM native journal bodies were not recovered here. The shared50/50 ledger cannot be decomposed into separately funded expert returns. The other saved standalone VOL/CS accounts cover2026July-October, not this2024regime. `NATIVE61_ATTRIBUTION.json` preserves exact scopes, dates, monthly price/cost/funding bridges, entry times and exposure.

## Smallest hold comparison proposal; no extra wallet run

The fully matched neutral long reference is the existing `VOL_MANAGED_HOLD` recipe: fixed CORE5 raw long weights .12 each, original daily past30 covariance10% mapper, May1 fresh10k with the same20-day CASH ramp, native daily rebalancing, identical costs/funding and paid terminal closure. It measures a risk-managed equal-weight hold signal. It does not measure fixed quantities or an already-running full-exposure account. Recover its same-scope original journal first; otherwise one separately authorized exact native61 reference would supply that missing evidence.

A true fixed-quantity buy-and-hold comparator would instead predeclare all five assets, use equal-dollar initial quantities scaled by the April30 causal risk context, pay native entry and terminal fees, and hold quantities between those boundaries. Its immediate entry and absence of daily covariance rebalancing would differ from the current ramp/risk controller. It cannot be called a matched ramp counterfactual, and no such wallet has been launched. No asset is selected after observing returns.

## Recovery

Reuse `requirements-native61.txt`, recovered original H1 bytes and published sources. Recover the official binary into external STATE, without a package-version resolver:

```bash
python recover_rsi_kernel.py --destination EXTERNAL_STATE/rsi2-kernel-recovery
export COIN_RSI2_KERNEL_TARGET=EXTERNAL_STATE/rsi2-kernel-recovery/installed
export QUANT_ROOT=COIN_SOURCE
python rsi61.py check --state EXTERNAL_STATE --output CHECK.json
```

The completed wallet and independent audit are preserved in the small-part `comparison-rsi61` archive, verified with `reassemble_results.py`. Do not rerun completed wallets. The recovery helper uses only official PyPI/pythonhosted URLs and refuses mismatched bytes before loading any extension. Historical publication, contract and account rules remain conditional and uncertified.
