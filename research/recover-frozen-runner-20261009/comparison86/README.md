# Completed continuous 86-day fixed baseline comparison

Three independent fresh 10,000-USDT wallets, July 15–October 9 exclusive, 2026.
The execution plan was published and remote-verified before any wallet started
at commit `9ffbada3c6f80fc5c1d1ee0c12764228c3163a0f`.

| Policy | Net USDT | Maximum observed drawdown | Realized annualized daily volatility |
| --- | ---: | ---: | ---: |
| VOL_MANAGED_HOLD | +798.55 | 2.13% | 11.74% |
| CSMOM21 | −772.40 | 9.92% | 7.83% |
| Fixed 50/50 allocation | −63.55 | 3.48% | 6.04% |

All three completed 123,840 minutes, finished paid-flat and recorded zero
liquidations. The independent Decimal minute-NAV, wallet, cost and signed-funding
reconciliations passed, with maximum errors below 2e-12 USDT. Separate checks
against actual source inputs passed for fill prices, fees, marks and shared
prior-minute quote capacity. These checks do not independently rebuild order
intents or certify historical exchange rules.

The exact original engine SHA256 remains
`318a0ae63056775db4e24c09abc1831de0dd166f9117b0ce0240630de6aad585`.
Guard OFF, BASE27, signed actual funding scale 1, original target eligibility,
weekly anchor, daily L1 budget ramp, delayed partial fills and paid terminal
closure were preserved. No model fit, recipe tuning or new market download ran.
The prior 44-day and 41-day fresh accounts were not stitched or rerun.

The API-only full-window readiness remains false. The selected complete window
uses exactly one retained official SOL August 28 08:30 trade archive record in
precedence over the preserved API confirm=0 record. `SOURCE_REFERENCES.json`
binds that policy and the existing complete public data commit. Raw market
archives are not duplicated in this package.

`RESULTS86.json` contains complete descriptive results and actual timing/memory
receipts. `ARTIFACT.json` describes 768-KiB ordered ZIP byte parts; reassemble
with the parent `reassemble_results.py`. All 64 included result/helper files are
hashed in `RESULT_MEMBER_HASHES.json`; account journals retain their original
bytes. The standalone `verify_portable.py` needs only NumPy and Polars, and
reconciles the restored accounts without raw market data. Original run receipts
retain the audit state at execution completion; separate post-run audit files
and `RESULTS86.json` give the final passed audit status.

Runtimes were 75.01 / 82.59 / 123.14 seconds, with maximum observed RSS 427 MB.
One CPU, 6 GB address-space cap, 600 seconds per wallet and 15 GiB disk reserve
were enforced. VOL's 11.74% realized volatility exceeds the 10% covariance target;
CSMOM21's gross drift reached 60.78% against the 60% target cap. These original
behaviors are preserved. Annualized statistics describe this 86-day sample;
they are not long-term APR or actual exchange settlement certification.
