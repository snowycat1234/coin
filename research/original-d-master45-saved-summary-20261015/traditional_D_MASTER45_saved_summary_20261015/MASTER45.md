# Original D MASTER45: saved-only descriptive summary

**2021 is April 2–December 31 only: 274 days. Its period return is never annualized.** The other four periods are full calendar years (2024: 366 days; others: 365). Each of the 45 separately approved/executed claims uses a fresh 10,000-USDT wallet. No annual-return product, CAGR or synthetic continuous wallet is calculated.

45 actual claims are retained. There are 15 post-hoc same-period/same-tier H090↔STATIC50 duplicate groups and 30 distinct realized paths: two realized families × three tiers × five periods. These are not 30 strategies, independent confirmations or OOS validations. No aliases, pruning or execution-reuse authority is created.

## Definitions and interpretation

- Current STATIC50 means the CS+HOLD blend. H090 is the fixed alternate wrapper that realizes the same 15 financial/minute paths here. VOL_MANAGED_HOLD is the other realized family. Legacy pure CS/CS+SMA name collisions and the planned unexecuted 15-cell CSMOM21_COMMON_TIER baseline are excluded.
- All periods are adaptive seen-development evidence. 2023/24 returns are positive and 2022/25 returns are negative across the nine cells. This does not establish cross-cycle profitability, alpha or investable risk-matched excess returns.
- Nominal 5%/10%/15% volatility budgets are not equal realized risk. Held forecast maxima and overshoot minutes are preserved below and in the CSV. They are distinct from realized daily volatility. Admission limits need not hold continuously as marks drift.
- Daily descriptive volatility: sample std(ddof=1) of complete UTC daily endpoint NAV simple returns, including initial 10,000 as the first denominator, multiplied by sqrt(365) for every period (also partial 2021 and leap 2024). The return itself is never annualized. Saved float64 NAV telemetry is not the exact native40 ledger.
- 2021 and 2023/24 volatility reuse already independent-reviewed saved metrics. 2022/25 volatility is derived only from 12 hash-pinned saved MINUTE arrays, 365 saved daily endpoints per donor; H090 inherits its same-tier STATIC50 metric solely through the exact full-path proof. SAVED_DAILY_NAV_DERIVATION.json and derive_saved_daily_nav.py contain exact arrays, hashes and reproducible arithmetic.
- Primary financial columns in MASTER45.csv preserve source decimal strings exactly. Human percentage displays below are separately rounded for readability; they are not replacements for the primary values. Native all-observation MDD covers initial NAV, minute marks and scheduler fill/funding observations; it does not certify an intraminute high/low path.
- Execution cost is execution-price friction, separate from fees. Signed funding is positive for receipts, negative for payments. Net results already include these effects; do not subtract fees/execution cost/funding again. Same-quantity accounting bridges are not counterfactual strategies.
- Original D uses conditional collateral-forfeiture settlement assumptions; zero modeled settlements/support/debt here is not actual-venue no-liquidation certification. Native venue filters, actual fills/liquidity, funding publication/units, insurance/ADL and historical arrival/installation remain uncertified.

## Source-quality and reporting scope

- 2022 retains 27 causal July carry points (8 asset runs, 11 distinct open clocks, longest 7 minutes), with UNKNOWN held valuation. Across nine cells the saved audits show no direct same-gap paid fills or owned funding. That does not show negligible counterfactual cashflow, quantity or terminal-return impact. 243 held asset-minute-case cells remain exposed to the qualification.
- 2025 binds the genuine complete 2025 source with an empty quality source. Its cold start preserves 5475 raw source funding events and 5470 native account events; five initial unowned events at +15 ms cause no pre-owned funding charge. It does not inherit 2022 carry provenance. Funding units and historical actual arrival/installation remain uncertified.
- 2024 retains its original bound causal carry/unknown mark-quality sidecar. 2021 coverage is shorter; source identities, runtime cost and risk-report conventions differ across periods.
- 2022/25 report both before-same-clock and including-same-clock covariance conventions. Primary forecast columns use CLOSE_BEFORE_SAMECLOCK_DAILY_DECISION. 2021 and 2023/24 keep their original frozen-report conventions without claiming identical midnight treatment.
- Original execution runtime is kept per cell. The reused 2024 STATIC50 MID runtime is taken from its exact saved original case receipt. Reporting/assembler runtime is not financial-case runtime.
- Source references reuse pinned prior publication receipts without any new network verification. 2022/25 use local review-bound code checkpoint SHA identities; no new publication claim is made. Root exit evidence for 2021/22 and 2025 companion is pinned.

## Human-rounded result display

Return and MDD/volatility are percentages; max gross is NAV-relative. Exact native financial values and full provenance are in MASTER45.csv and INPUT_PINMAP.json.

| Period | Core | Tier | Return% | Native MDD% | Daily vol% | Max gross | Forecast max% | Overshoot min | Guard50 warnings |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | STATIC50 | LOW | 9.8160 | 2.4636 | 4.6309 | 0.119614 | 8.6757 | 67639 | 0 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | STATIC50 | MID | 15.6636 | 5.0813 | 8.9948 | 0.265388 | 15.7223 | 76986 | 1 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | STATIC50 | HIGH | 19.8217 | 8.4890 | 12.9532 | 0.466278 | 29.7873 | 53431 | 2 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | H090 | LOW | 9.8160 | 2.4636 | 4.6309 | 0.119614 | 8.6757 | 67639 | 0 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | H090 | MID | 15.6636 | 5.0813 | 8.9948 | 0.265388 | 15.7223 | 76986 | 1 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | H090 | HIGH | 19.8217 | 8.4890 | 12.9532 | 0.466278 | 29.7873 | 53431 | 2 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | VOL_MANAGED_HOLD | LOW | 7.2350 | 7.6137 | 8.6749 | 0.112704 | 30.0652 | 369449 | 1 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | VOL_MANAGED_HOLD | MID | 15.6893 | 9.5755 | 12.4432 | 0.175223 | 29.0501 | 239519 | 0 |
| 2021 Apr 2–Dec 31 (274 d PARTIAL) | VOL_MANAGED_HOLD | HIGH | 23.4323 | 11.4582 | 17.0375 | 0.259515 | 38.6196 | 227574 | 0 |
| 2022 | STATIC50 | LOW | -5.4926 | 7.6259 | 3.9249 | 0.242410 | 6.9976 | 34964 | 1 |
| 2022 | STATIC50 | MID | -9.5230 | 14.7211 | 7.2097 | 0.584019 | 14.5246 | 31107 | 3 |
| 2022 | STATIC50 | HIGH | -18.2241 | 25.1824 | 10.2396 | 0.833461 | 19.4750 | 25162 | 2 |
| 2022 | H090 | LOW | -5.4926 | 7.6259 | 3.9249 | 0.242410 | 6.9976 | 34964 | 1 |
| 2022 | H090 | MID | -9.5230 | 14.7211 | 7.2097 | 0.584019 | 14.5246 | 31107 | 3 |
| 2022 | H090 | HIGH | -18.2241 | 25.1824 | 10.2396 | 0.833461 | 19.4750 | 25162 | 2 |
| 2022 | VOL_MANAGED_HOLD | LOW | -6.3284 | 6.8215 | 5.2448 | 0.139219 | 8.8879 | 153620 | 6 |
| 2022 | VOL_MANAGED_HOLD | MID | -12.7490 | 13.8588 | 10.6881 | 0.256812 | 15.9695 | 199802 | 6 |
| 2022 | VOL_MANAGED_HOLD | HIGH | -19.0584 | 20.7321 | 16.1292 | 0.369010 | 23.2506 | 218851 | 6 |
| 2023 | STATIC50 | LOW | 7.5833 | 5.1873 | 4.7057 | 0.289557 | 7.8933 | 56963 | 2 |
| 2023 | STATIC50 | MID | 24.0536 | 6.4342 | 9.5888 | 0.558300 | 17.6378 | 68425 | 0 |
| 2023 | STATIC50 | HIGH | 27.4472 | 6.1399 | 11.1011 | 0.464668 | 25.9785 | 40141 | 3 |
| 2023 | H090 | LOW | 7.5833 | 5.1873 | 4.7057 | 0.289557 | 7.8933 | 56963 | 2 |
| 2023 | H090 | MID | 24.0536 | 6.4342 | 9.5888 | 0.558300 | 17.6378 | 68425 | 0 |
| 2023 | H090 | HIGH | 27.4472 | 6.1399 | 11.1011 | 0.464668 | 25.9785 | 40141 | 3 |
| 2023 | VOL_MANAGED_HOLD | LOW | 12.7234 | 4.6582 | 5.8756 | 0.177720 | 13.9684 | 298479 | 0 |
| 2023 | VOL_MANAGED_HOLD | MID | 24.5047 | 7.6587 | 11.1725 | 0.329967 | 24.3046 | 245098 | 0 |
| 2023 | VOL_MANAGED_HOLD | HIGH | 38.2715 | 10.4294 | 16.7153 | 0.490971 | 37.7204 | 199277 | 0 |
| 2024 | STATIC50 | LOW | 10.5811 | 3.0692 | 5.0453 | 0.290092 | 11.2621 | 91093 | 2 |
| 2024 | STATIC50 | MID | 16.2540 | 5.8912 | 8.6894 | 0.434812 | 17.4351 | 91872 | 3 |
| 2024 | STATIC50 | HIGH | 17.9518 | 12.5076 | 13.1449 | 0.549261 | 25.1860 | 74606 | 4 |
| 2024 | H090 | LOW | 10.5811 | 3.0692 | 5.0453 | 0.290092 | 11.2621 | 91093 | 2 |
| 2024 | H090 | MID | 16.2540 | 5.8912 | 8.6894 | 0.434812 | 17.4351 | 91872 | 3 |
| 2024 | H090 | HIGH | 17.9518 | 12.5076 | 13.1449 | 0.549261 | 25.1860 | 74606 | 4 |
| 2024 | VOL_MANAGED_HOLD | LOW | 11.3864 | 4.2534 | 6.0994 | 0.147747 | 10.6047 | 280778 | 0 |
| 2024 | VOL_MANAGED_HOLD | MID | 24.6802 | 8.0001 | 11.1768 | 0.300604 | 15.8447 | 252443 | 0 |
| 2024 | VOL_MANAGED_HOLD | HIGH | 38.9940 | 10.7524 | 16.4504 | 0.456955 | 22.2013 | 242940 | 0 |
| 2025 | STATIC50 | LOW | -2.5473 | 4.9885 | 5.0488 | 0.294043 | 8.0678 | 80264 | 2 |
| 2025 | STATIC50 | MID | -2.5635 | 9.4075 | 9.6686 | 0.601363 | 23.4457 | 71286 | 2 |
| 2025 | STATIC50 | HIGH | -8.9282 | 16.7475 | 16.0680 | 0.904886 | 34.9244 | 65892 | 2 |
| 2025 | H090 | LOW | -2.5473 | 4.9885 | 5.0488 | 0.294043 | 8.0678 | 80264 | 2 |
| 2025 | H090 | MID | -2.5635 | 9.4075 | 9.6686 | 0.601363 | 23.4457 | 71286 | 2 |
| 2025 | H090 | HIGH | -8.9282 | 16.7475 | 16.0680 | 0.904886 | 34.9244 | 65892 | 2 |
| 2025 | VOL_MANAGED_HOLD | LOW | -1.2431 | 5.5334 | 4.8971 | 0.126428 | 8.3328 | 215583 | 0 |
| 2025 | VOL_MANAGED_HOLD | MID | -2.5296 | 9.6362 | 10.8785 | 0.261075 | 15.1778 | 252580 | 1 |
| 2025 | VOL_MANAGED_HOLD | HIGH | -4.6843 | 15.0185 | 16.8808 | 0.333708 | 25.4925 | 293069 | 2 |

## Reproduction

Run taskset -c 0 python assemble_master45.py from this folder. It verifies the fixed input pinmap and every directly used saved JSON hash, validates 45 exact ordered identities and 15 duplicate groups, then writes deterministic CSV/MD plus field-level bindings. It never opens accounts, providers, targets or raw sources. Optional deeper saved-array rederivation: taskset -c 0 python derive_saved_daily_nav.py --rederive-from-pinned-saved-arrays. This reads only the 12 pinned saved arrays, one case at a time with a temporary mmap and numerical pools 1.

Focused positive/negative binding tests are in test_master45.py and fixtures/NEGATIVE_BINDING_CASES.json. No financial replay, new GO, claim, tuning, network or publication is performed.
