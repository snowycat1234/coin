# Frozen v2 cash-arm native61 results

The two remaining real frozen terminal exports at `df1bc4b875e02c860d8c369ce01bdf03dee6ca43` were evaluated once each on independent fresh10,000 USDT May–June2024 wallets. Request-specific plans were published and read back at `75ef6a9b17efb88af06418cfcac7606da693185d` before either run. GRU was audited and its same-target proxy reported first, then preserved at `d68f727c80adaed9b3296ec63dcae3ab59a54848` before archive packaging. No completed no-cash or static wallet was rerun; no model was loaded or trained.

| Arm | Native net USDT | May | June | Minute DD | Mean/max gross | v2 reference | Native minus reference |
|---|---:|---:|---:|---:|---:|---:|---:|
| GRU64 with cash, new | -472.96 | -256.28 | -216.68 | 6.94% | 25.80% / 58.67% | -543.89 | +70.92 |
| Latest MLP with cash, new | -477.73 | -244.19 | -233.54 | 6.96% | 28.75% / 58.82% | -551.83 | +74.11 |
| GRU64 no cash, reused | -511.39 | -268.80 | -242.59 | 7.38% | 27.80% / 60.04% | -592.18 | +80.79 |
| Latest MLP no cash, reused | -288.59 | -257.13 | -31.46 | 4.95% | 33.31% / 60.03% | -365.41 | +76.83 |
| Static50, reused | -189.01 | -56.32 | -132.69 | 3.08% | 22.81% / 32.80% | — | — |
| Cash50, reused | -110.89 | -45.51 | -65.38 | 1.58% | 12.51% / 17.35% | — | — |

All four frozen v2 models lost more than both static controls over this full seen development wallet. Cash-enabled GRU lost less than its no-cash arm, while cash-enabled MLP lost more. Realized risk and completed update counts differ, so these are descriptive comparisons rather than isolated causal effects of admitting CASH. GRU-with-cash completed431 additional v2 updates, cumulative Adam780; MLP-with-cash1024, cumulative1546. Both remain `CAPPED_NOT_CONVERGED`. No convergence, negative feasibility, out-of-sample alpha or long-term APR conclusion follows.

Both exporters retain the old contract SHA256 `bc6f1a475c0df8c65d1aa04975bd3b70996d58048ef457f283b6a8c6d73463eb`. The plans explicitly bind corrected contract SHA256 `9e29ad31a3c795e531e556c2da2f04dfa30d2d71e8df74111731360fc4ca07b2`, with adapter SHA256 `948f496f6307576832fa47afcfcd7161b0d855456b49ae511da5066d09f2efbd`. The reviewer fix exempts mandatory eligibility release to CASH from discretionary L1 turnover. All305 canonical E5 eligibility cells are true in this period; release is therefore identical to prior budget. Both old and corrected adapters were executed for mapping only, with exact full61-day target and budget byte equality. Original export provenance was preserved; no semantic mismatch was ignored. The corrected adapter previously passed37 tests, including both original-native-mapper parity checks.

The unchanged financial engine is `scripts/investment/resumable_perpetual.py`, SHA256 `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`: guard off; original five assets, E5 slots, daily L1 and covariance mapper; isolated1x/MMR.005; BASE27 fee/spread/slippage; actual signed funding; previous-minute quote capacity; lot/min-notional, delayed/partial orders and paid closure. Each account completes87,840 minute observations and915 original funding events. Both paid terminal-flat, with zero liquidations and zero native risk-reduction signals. Historical publication, filters, contract and account rules remain uncertified cross-venue research assumptions.

The v2 comparison reuses the exact original daily prices and funding coefficients. The original producer mapper matches saved native target bytes exactly. The independent NumPy reference follows bound v2 objective SHA256 `c438a85a1853f7b8cef02dede194dd3c905d93f74bbb2882b5ae0fd8d50ad040`; each path has one charged boundary reduction and paid final cash. Separate50-digit Decimal checks of all61 boundaries have maximum NAV error below7e-12 USDT. Torch was not executed in this worker. Constant daily-boundary full fills, continuous quantities and coarse risk reduction omit minute latency, intra-interval marks, actual volume capacity, lots, filters, isolated margin and liquidation. The reported discrepancies are between these economic/execution scopes, not proof of a coding defect.

`RESULTS.json` includes both new accounts and reused references. `ARTIFACT.json` orders transport parts no larger than768 KiB. Concatenate them to the named ZIP, then verify every part hash, ZIP SHA256/CRC and `RESULT_MEMBER_HASHES.json`. All original account journal bytes remain unchanged. Model/optimizer weights, raw market archives, credentials and private runtime inventories are excluded.

After installing the pinned `requirements-native61.txt`, portable journal reconciliation is:

```sh
python verify_native61.py --directory accounts/V2_GRU64_WITH_CASH
python verify_native61.py --directory accounts/V2_LATEST_MLP_WITH_CASH
```

The retained original audits additionally check actual fills, fee calculations, prior-minute capacity, strictly prior completed marks and all funding events against the original local tapes. The portable commands check journal/accounting identities without those market files. This package preserves only the two new cash accounts; the previous no-cash package remains unchanged.
