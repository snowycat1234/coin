# Completed frozen native61 validation and causal daily coverage

Four independent fresh10,000-USDT accounts, May1–July1 exclusive2024, under
the exact318a engine, original E5 mapper and unchanged guard-OFF financial
contract. This is already-seen chronological development, with no new fit,
recipe search, model implementation or exchange download.

| Policy | Net USDT | Maximum observed drawdown |
|---|---:|---:|
| NO_CASH frozen1024 head | −196.72 | 3.90% |
| WITH_CASH frozen1024 head | −159.50 | 2.89% |
| Fixed VOL.5/CSMOM.5 | −189.01 | 3.08% |
| CASH.5/VOL.25/CSMOM.25 | −110.89 | 1.58% |

Both frozen heads underperformed the cash reference. NO_CASH also
underperformed50/50 by7.71USDT. No parameter changed in response.
All four completed87,840 minutes, ended paid-flat and had zero liquidations.
Independent Decimal NAV/wallet/cost/funding audits passed below2e-12USDT;
source checks passed actual fills, prior-minute shared quote capacity, fee,
mark and915 signed funding observations each. The five fresh first events
were unheld;910 were account-applied. Actual settlement millisecond offsets
remain intact. Order intents are not independently reconstructed, and
historical venue/account rules remain conditional and uncertified.

Plan645c5c7 was published and remote-verified before the first wallet. The
read-only funding source auditor was corrected for actual millisecond event
times at3912aef before the remaining wallets. Engine, mapper, financial
parameters and completed journals were unchanged. The four runtimes were
44.77/40.82/46.44/34.52seconds; peak RSS423MB, with one CPU,6GB address-space
cap,600seconds per wallet and15GiB disk reserve. `EXECUTION.json` retains the
audit state at engine completion; `INDEPENDENT_AUDIT.json` is the final check.

Original H1 archive and60 regenerated minute Parquets match every published
hash. May–June input coverage is305 asset-days,878,400 trade+mark minute rows,
915 actual funding events. The separately committed request handoff is
referenced only; its cancelled branch update was not retried and its payload
is not reuploaded. Original controls' audited bodies were unavailable, so
the two explicitly authorized references above are new full-capital wallets.

The original10-asset V2/V3 feature/label bodies are not in their checked public
branches; published source/protocol/hash reports remain available. Recovered
CORE5 daily prefixes support a derived24-feature/24-mask panel using those
verified formulas, with market aggregates recomputed on CORE5. It is not
claimed byte-equivalent to the original10-asset panel. The recipe is
`../inspect_daily_coverage.py`; generated panel bytes remain outside Git.

There are1,581 calendar decisions before May1. All five assets have64
consecutive actual prices on1,162 decisions:2020Nov17–2022Feb26 and
2022Jun6–2024Apr30. Missing history is kept on its original calendar with
masks. All61 validation decisions have complete price warmup; the first
window covers actual observation days2024Feb27–Apr30, with all24 features
finite for all five assets. `DAILY_FEATURE_COVERAGE.json` enumerates per-asset
dates and feature masks. Fully valid mom200 on those64 steps is backed by264
actual completed closes,2023Aug11–2024Apr30. The derived NPZ uses completed_us,
available_us, values, valid and step_valid, with a verified producer manifest,
matching the published temporal input schema. Calendar bar starts are never
treated as feature availability, and no future label fields are exported.
These are observation candidates, not certified
mature wallet-objective training labels or continuous native wallet periods.
The wallet-label maturity, training-only scaler and chronological split
contract remain prerequisites for the later temporal-model task. No13k
temporal model, capacity-matched rich baseline or1M training run occurred.

Reassemble the ordered public result ZIP parts using the parent
`reassemble_results.py --root comparison61 --destination NEW_PACKAGE`.
All included members are hashed. The restored standalone
`verify_native61.py --directory results61/NO_CASH` needs only NumPy/Polars
and independent helpers; repeat for each policy, without replaying wallets.
Raw market archives and runtime/private inventories are excluded.
