# OKX 41-day suffix control results

Conditional simulation research on actual public OKX inputs. **2026-08-29 00:00 UTC through 2026-10-09 00:00 UTC exclusive**, 41 days and 59,040 minutes per simulated account. Three independent **fresh 10,000 USDT** accounts start flat with a fresh cash budget; no position, PnL or budget state is carried from the earlier 44-day study. Assets: BTC, ETH, SOL, XRP and DOGE USDT swaps.

## Results

| Frozen control | Net USDT | Minute maximum drawdown | Annualized realized daily volatility | Mean gross exposure | Maximum recorded minute gross |
|---|---:|---:|---:|---:|---:|
| FIXED_VOL_HOLD | +108.46 | 1.709% | 7.528% | 12.076% | 20.4458% |
| FIXED_CSMOM21 | +25.29 | 1.941% | 4.043% | 40.326% | 60.2394% |
| STATIC50 | +43.33 | 1.130% | 3.791% | 21.432% | 33.9607% |

FIXED_VOL_HOLD requests the volatility-managed long hold expert; FIXED_CSMOM21 requests the cross-sectional momentum expert; STATIC50 requests a fixed 50/50 mix of them. Frozen budget mapping and covariance/risk controls mean a 50/50 expert request does not imply equal realized positions or risk. All three simulated accounts record zero liquidations and finish flat through paid closes, without forced free fills.

### Costs and funding

| Control | Fees USDT | Execution cost USDT | Signed funding USDT |
|---|---:|---:|---:|
| FIXED_VOL_HOLD | 2.398081240 | 3.488196161 | -7.520053715 |
| FIXED_CSMOM21 | 16.348448908 | 23.779601699 | +3.465385689 |
| STATIC50 | 7.911769387 | 11.508069549 | -1.863860228 |

BASE27 assumes a 0.00055 fee fraction per side, 4 bps half-spread and 4 bps slippage per side: 27 bps nominal round trip. Execution costs are embedded in fill prices, without a second cash debit. Funding treats actual realizedRate as a dimensionless fraction at scale 1, using signed held quantity and the last eligible completed mark strictly before the event; position ownership is also strictly prior and equal-clock marks are excluded. All five first-clock events per fresh account have zero position and zero funding. The input source has four actual first-event mark witnesses and one missing mark, for SOL; no missing mark is invented. Funding units, publication timing and native settlement are uncertified.

## Interpretation and limits

- **The 44-day and 41-day accounts cannot be stitched into an 86-day account or return.** They total 85 separately scored calendar days and exclude August 28; each account reset changes exposures and path dependence. The original 86-day study remains NOT_RUN because full native coverage is incomplete, including quarantined SOL 2026-08-28 confirmation=0 data. No interpolation or substitution is used.
- This is separately funded suffix research, not pristine out-of-sample validation, live performance, an APR promise, or native OKX settlement/historical-rule certification.
- Account assumptions remain Bybit-style isolated 1x, 0.005 maintenance margin, no automatic margin addition, 1e-8 base quantity step and 10 USDT minimum opening notional, using current instrument metadata and a historical execution-clock proxy.
- Frozen controls use 30-day completed-history covariance, a 10% annual volatility budget, 60% target gross cap, 30% target asset cap and 0.10 daily L1 budget-change cap; risk guard is off. Actual exposure can drift beyond target caps; CSMOM's recorded gross maximum is 60.2394%. Common caps do not equalize realized risk.
- Annualized volatility is a descriptive risk measure, not annual return. Legacy annual-return/Sharpe fields remain in unchanged account summaries for integrity and are not forward guarantees.
- Preserved independent audits report signed-journal, minute-marked NAV, funding and wallet checks. The included verifier independently checks file integrity and recorded aggregate costs/funding; it does not rerun order sizing or the complete minute risk/exposure path. Referenced public market bundles are needed for that replay. Short attribution is not the return of a counterfactual strategy with shorts removed.
- No trained selector, new fit, threshold tuning, or student evaluation is claimed.

## Source and recovery

Actual source commit: 67e3f94ff23c0699e270484b2fcea350032fa3e7. Existing public market bundles and their pinned prefix dependency are referenced in SOURCE_REFERENCES.json, without duplicate uploads. [Immutable suffix/delta transport INDEX](https://github.com/snowycat1234/coin/blob/67e3f94ff23c0699e270484b2fcea350032fa3e7/research/okx-forward-coverage-20261009/minute-intake/transport-delta-after-d15-768k/INDEX.json).

The package includes byte-identical account JSON/Parquet journals and independent audits. RESULTS.json and ECONOMICS.json retain economic values while excluding runtime and irrelevant source receipts. FINANCIAL_CONFIG.json contains financial assumptions only. Engine code, market data, proposals, cache/workspace inventories, logs, private notes, credentials and authorization/runtime receipts are excluded. This is a result-and-audit package, not a full simulation rerun environment.

MANIFEST.json records original-versus-public member hashes and the original archive hash. No original simulation source code was edited or included. Portability uses relative result_root='results' and the local verifier's configurable --root argument.

Download the files listed in ARTIFACT.json, then run python reassemble.py --root . to validate parts and reconstruct the ZIP. After extraction, run python verify_results.py --root . for local read-only integrity and aggregate checks; neither script uses the network or trades.
