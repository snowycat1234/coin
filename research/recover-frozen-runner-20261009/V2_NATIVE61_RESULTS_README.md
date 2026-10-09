# Frozen v2 no-cash native61 results

Two real terminal frozen exports from commit `2bf2dc03e1ca3f0594b7b15dcff0cdb5651c5f1d` were evaluated once each on fresh independent 10,000 USDT May–June2024 wallets. Request-specific plans were public at `974fedd7502829fac557475a9b71a85ffaf5d65e` before either wallet began. The GRU result was reported and preserved first at `d2682ced22efedde0ca6fb1e1336b8ca2cb3f634`; its proxy dependency was then recovered. Neither model was loaded or trained here.

| Arm | Native net USDT | May | June | Minute drawdown | Mean gross | v2 boundary reference | Native minus reference |
|---|---:|---:|---:|---:|---:|---:|---:|
| GRU64 no cash | -511.39 | -268.80 | -242.59 | 7.38% | 27.80% | -592.18 | +80.79 |
| Latest MLP no cash | -288.59 | -257.13 | -31.46 | 4.95% | 33.31% | -365.41 | +76.83 |
| Static50, reused | -189.01 | -56.32 | -132.69 | 3.08% | 22.81% | — | — |
| Cash50, reused | -110.89 | -45.51 | -65.38 | 1.58% | 12.51% | — | — |

Both v2 arms lost more than both static controls in the full seen development wallet. MLP's June loss was smaller, with greater mean gross exposure. Caps do not equalize realized risk. GRU completed321 v2 updates, cumulative Adam453; MLP completed1024, cumulative1167. Both remain `CAPPED_NOT_CONVERGED`. This is not an out-of-sample or convergence result.

The native engine is unchanged `scripts/investment/resumable_perpetual.py`, SHA256 `318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`: guard off, original E5 slots, original covariance and daily L1 mapper, isolated1x/MMR.005, BASE27 costs, actual signed funding, prior-minute quote capacity, delayed/partial fills, reduction priority and paid terminal closure. Each account contains87,840 minute observations and915 original funding events. Fresh first funding has no held quantity. Both paid flat with zero liquidations. Maximum recorded gross drift was60.03975%/60.03392%, with1/2 risk-reduction signals; caps are not instantaneous guarantees. Historical filters, publication and Bybit contract/account rules remain uncertified cross-venue research assumptions.

The exact original H1 development fragment was recovered from the previously published small recovery ZIP, not from a market provider. `PROXY_RECOVERY.json` pins the archive/index/fragment and v2 objective. The original NumPy producer mapper and saved native target path are exactly equal for both arms. `v2_same_path_diagnostic.py` is an independent NumPy numerical reference for the bound v2 Torch equations; Torch was not executed here. It uses exactly the saved native target bytes and original daily prices/funding coefficients. A separate50-digit Decimal calculation checked all61 boundaries, costs, quantity changes and charged reductions; maximum NAV error was below1.5e-11 USDT. Four economic counterexample tests passed. Its full-fill continuous daily-boundary assumptions omit minute latency, intra-interval marks, actual liquidity, lots, historical filters, isolated margin and liquidation. It is a diagnostic, not another native wallet.

`RESULTS.json` includes source identities, monthly costs/funding, exposure, reused controls and both discrepancies. `ARTIFACT.json` orders parts no larger than768 KiB. Concatenate them to the named ZIP and check every part, ZIP SHA256, CRC and `RESULT_MEMBER_HASHES.json`. All original account journal bytes are retained unchanged. Raw market archives, optimizer/model weights, credentials and private runtime inventories are excluded.

For portable journal reconciliation, install the pinned `requirements-native61.txt` and run:

```sh
python verify_native61.py --directory accounts/V2_GRU64_NO_CASH
python verify_native61.py --directory accounts/V2_LATEST_MLP_NO_CASH
```

Omitting `--state` checks account journals and accounting. The original saved audits additionally checked all actual fills, fees, capacity, prior completed marks and the funding calendar against retained input bytes. No static account was rerun and no fit or provider download occurred.
