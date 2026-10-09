# OKX 44-day native control results

Conditional simulation research on actual public OKX inputs, with three independent fresh 10,000 USDT accounts. UTC scoring period: **2026-07-15 00:00 through 2026-08-28 00:00 exclusive**, 44 days and 63,360 minute observations per account. Assets: BTC, ETH, SOL, XRP and DOGE USDT swaps.

## Results

| Frozen control | Net USDT | Minute maximum drawdown | Annualized realized daily volatility | Mean gross exposure | Maximum recorded minute gross |
|---|---:|---:|---:|---:|---:|
| FIXED_VOL_HOLD | +708.17 | 1.710% | 13.995% | 21.355% | 39.6453% |
| FIXED_CSMOM21 | -703.22 | 7.702% | 9.481% | 43.221% | 60.7837% |
| STATIC50 | -46.29 | 2.568% | 7.131% | 23.988% | 37.2851% |

FIXED_VOL_HOLD requests the volatility-managed long hold expert; FIXED_CSMOM21 requests the cross-sectional momentum expert; STATIC50 requests a fixed 50/50 mix of those experts. Requests pass through the frozen budget mapper and common covariance/risk controls, so a 50/50 expert request does not imply equal realized positions or risk. All three accounts have zero recorded liquidations and finish flat through paid closes, with no forced free fill.

### Costs and funding

| Control | Fees USDT | Execution cost USDT | Signed funding USDT |
|---|---:|---:|---:|
| FIXED_VOL_HOLD | 4.799340006 | 6.981327791 | -13.799664497 |
| FIXED_CSMOM21 | 21.166733821 | 30.787557319 | +3.651641745 |
| STATIC50 | 11.410036695 | 16.596408516 | -5.013324858 |

BASE27 assumes a 0.00055 fee fraction per side, 4 bps half-spread and 4 bps slippage per side (27 bps nominal round trip). Execution price effects are already embedded in fill prices, without a second cash debit. Signed funding uses the actual realizedRate as a dimensionless fraction at scale 1, a held position opened strictly before the event, and the last eligible mark close strictly before the event; equal-clock marks are excluded. Each account has five first-clock zero-position funding rows, one per instrument, with no invented preceding mark. Funding units, historical publication timing and native exchange settlement remain conditional, not certified.

## Interpretation and limits

- The original **86-day study remains NOT_RUN**. Its actual coverage was incomplete, including quarantined SOL 2026-08-28 confirmation=0 data; nothing is interpolated or substituted.
- This is a separately selected complete 44-day calendar. It is not pristine out-of-sample validation, live performance, an APR promise, or certification of native OKX settlement or historical rules.
- Account assumptions are Bybit-style isolated 1x, 0.005 maintenance margin, no automatic margin addition, 1e-8 base quantity step and 10 USDT minimum opening notional. Current instrument metadata and a historical execution-clock proxy are used.
- Frozen controls use a 30-day completed-history covariance, 10% annual volatility budget, 60% target gross cap, 30% target asset cap and 0.10 daily L1 budget-change cap; risk guard is off. Realized exposure can drift beyond target caps. CSMOM's recorded gross maximum is 60.7837%, so common caps do not equalize realized risk.
- Reported annualized volatility is a descriptive risk statistic, not annual return. Legacy annual-return/Sharpe fields remain in unchanged account summaries solely for journal integrity and are not forward guarantees.
- Independent audits reconcile recorded signed fills, funding, minute-marked NAV and wallet identity; they do not independently certify order sizing or native rules. A short-side contribution is not the return of a counterfactual strategy with shorts removed.
- No trained selector, new model fit, threshold tuning, or student evaluation is claimed.

## Source and recovery

Underlying public market bundles are referenced in SOURCE_REFERENCES.json rather than uploaded again. Pinned dataset commit: d15b7beb01ab8d111b5037c86062e0b74f4eb7cc. The corrected recoverable transport is at [this immutable INDEX](https://github.com/snowycat1234/coin/blob/4a560b8d1123c4c655e7a1770b435a06eb796469/research/okx-forward-coverage-20261009/minute-intake/transport-prefix-d15-768k/INDEX.json).

This small result package includes byte-identical account JSON/Parquet journals and independent audits. RESULTS.json and ECONOMICS.json retain economic values while excluding process runtime and irrelevant receipt references. FINANCIAL_CONFIG.json contains financial assumptions only. Original engine sources, normalized market inputs, proposal state metadata, local cache/workspace inventories, logs, private notes, credentials and authorization/runtime receipts are excluded. It is a result-and-audit package, not a complete simulation rerun environment.

MANIFEST.json lists original-versus-public hashes for each included source member and the original archive SHA256. No original simulation source code was edited or included. Path portability is supplied by relative result_root='results' and verify_results.py's configurable --root argument; the verifier performs local read-only journal checks without network or trading.

Reassemble artifact parts in the numeric order in ARTIFACT.json, verify each SHA256 and the full ZIP SHA256, then extract. The included standard-library verifier runs with: python verify_results.py --root .
