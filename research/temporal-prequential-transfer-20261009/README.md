# Fresh chronological own-path transfer — three fixed research folds

One fixed 13,699-parameter GRU with the existing expanded action pool and 18 current-expert inputs. Each fold starts with identical fresh seeded parameters and Python/NumPy/Torch RNG, empty Adam, and its own prefix-fitted scaler. No global780 model or 907-row scaler is loaded. These are historical prequential research folds using previously seen project data.

| Forward start | Decisions scored | Earlier training decisions | Unique scaler rows |
|---|---:|---:|---:|
| 2023-07-03 | 63 | 476 | 605 |
| 2023-10-02 | 63 | 567 | 696 |
| 2024-01-01 | 63 | 658 | 787 |

`READY.json` binds exact inputs, sources, counts and initial snapshots. Exactly512 updates per fold; deterministic TRAIN diagnostics at0/128/256/512. No forward checkpoint selection or parameter search.

Actual maturity determines purging. At midnight cutoff C, the C−1day row is retained only as forced paid CASH at its producer execution clock, C−1day+60,000,001us. The preceding active interval ends at that same observed close. Every training outcome and paid close must precede C. There are no rolling63-day training labels. Already published feature history may overlap; no extra63/64-day embargo is imposed. A neutral flat-CASH suffix repeats the observed terminal price and has known zero funding, consuming no following interval. Focused tests verify exact loss/NAV/gradient equality with the original mapped objective and rejection of immature closes.

Each registered forward wallet starts with10k CASH and remains continuous across63 decisions, including ramp, costs, funding and paid terminal closure. Keep all ramp days: a full simplex allocation switch requires at least20 decisions at L1<=0.1. Preserve separate natural training episodes and gaps. Same mapper/caps/endogenous wallet; no observed wallet features.

Fixed controls: CASH, VOL, CS, SHORT, VOL50/CS50 and CASH50/VOL25/CS25. Primary screen requires mean block utility excess>0 and worst-block excess>=0 versus fixed VOL50/CS50. Report all controls and individual wallets; do not sum bankrolls or claim APR. Evidence is an approximate full-fill daily-boundary surrogate until independently replayed.

The January2024 export preserves original native fresh startup: previous_quote=None, initial quote capacity0, no external prior quote. Missing2023 native tapes do not block fitting. `REQUESTS.npz`, `CURRENT_CONTEXT63.npz`, paired budgets/targets/NAV and exact model/Adam/RNG are exported after each frozen terminal. At most two workers use existing resource guards. Every completed optimizer update is checkpointed atomically; wall slices resume unchanged. Numeric failures retain their precise issue and allow independent admissible folds to continue.

No provider downloads, purchases, trading or deployment. Installed Torch2.6.0+cpu, numpy2.5.3 and pytest9.1.1; dependency recipe and exact recovered objective remain in the earlier temporal module. Executable entry: `python -m modules.temporal_prequential_transfer {check,run,fold,export,aggregate}` with explicit `--state`, `--output`, and published producer/destination for run/export, under the existing bounded launchers.

This authorized protocol supersedes the diagnostic proposal's lookback-based64-day embargo; the old proposal remains preserved as history.

Completed in 2026: all three models reached exactly 512 updates, with no numerical/path failures. These are absolute paid-flat PnLs in USDT on separate 10,000-USDT wallets, using approximate daily execution:

| Policy | July 2023 | October 2023 | January 2024 |
|---|---:|---:|---:|
| Fresh GRU | +581.84 | +736.40 | −29.39 |
| CASH | 0.00 | 0.00 | 0.00 |
| VOL | −317.02 | +1,168.18 | +877.40 |
| CS | −523.44 | +722.70 | −82.69 |
| SHORT | −30.89 | −162.91 | −313.56 |
| VOL50/CS50 (fixed primary) | −405.67 | +950.33 | +394.72 |
| CASH50/VOL25/CS25 | −218.47 | +472.43 | +189.03 |

Model excess over the primary was +987.51/−213.94/−424.11 USDT; excess is distinct from profit. Mean block utility excess +0.012645 and worst −0.043231 fail the predeclared screen. The favorable July transfer does not establish stable cross-period performance; the other two blocks do not establish that learning is impossible. Fixed 512 updates do not prove convergence.

| Model measure | July | October | January |
|---|---:|---:|---:|
| Maximum drawdown | 0.765% | 0.954% | 2.223% |
| Maximum allocated gross before netting | 32.488% | 35.624% | 57.284% |
| Maximum allocated per-asset gross | 10.673% | 8.202% | 14.242% |
| Mean CASH request | 10.145% | 3.800% | 4.654% |
| Mean SHORT request | 35.560% | 49.079% | 7.650% |

`RESULT.json` preserves all policy costs, signed funding, drawdown, allocation and wallet counts. `RECEIPT.json` records exact update/initialization/provenance checks; `FORWARD_EXPORT_CHECK.json` records bitwise request reproduction and mapper/source/clock/mask checks. All 21 paired paths paid terminal closure. Mean requests are policy requests, not account cash or actual position exposure. Existing execution and data-publication limits remain. January's original native fresh startup is exported; native replay is separate, and the two 2023 native tape sets remain unavailable here. No further fits, downloads or wallets were launched during verification.
