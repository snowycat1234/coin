# Cached training coverage and episode weights

One moderate episode-weighting comparison is warranted **after the fixed-pool comparison**. Keep all winning and rebound-loss dates and the five full chronological wallets. Training only on short winners would change the problem and remove its main failure mode. No training, model inference, new proxy rollout, wallet, provider download or development-outcome access occurred in this diagnostic.

Momentum short is eligible on778/778 dates;3556/3890 asset-dates are eligible, with334 original warmup exclusions. It has nonzero targets on587 dates and is cash on191. Availability is distinct from profitability. The audited cached fresh paid daily proxy has256 positive-utility dates,331 losses and191 zero dates. It beats VOL on377 dates, CS on441, and both on294; only203 of those294 also beat CASH. The others are cash or smaller losses. On242 dates where VOL and CS both lose, short is positive on125.

| Original continuous episode | Dates | Short positive | Short loss | Positive and beats VOL/CS/CASH | Loses on CORE5 rebound | Current loss weight |
|---|---:|---:|---:|---:|---:|---:|
| 2022-01-02–2022-02-24 | 54 | 29 | 25 | 21 | 24 | 6.94% |
| 2022-05-04–2022-07-30 | 88 | 35 | 43 | 32 | 40 | 11.31% |
| 2022-08-01–2022-10-01 | 62 | 19 | 27 | 15 | 25 | 7.97% |
| 2022-10-03–2023-02-23 | 144 | 49 | 59 | 34 | 53 | 18.51% |
| 2023-02-25–2024-04-29 | 430 | 124 | 177 | 101 | 152 | 55.27% |

Rebound means the ex-post equal-weight CORE5 execution-price return is positive. Short loses on294 such dates;304 of its331 loss dates also have adverse price contribution from its held short basket. VOL/CS/momentum all lose on46 dates across all five episodes; adding Donchian as a fourth risky comparator gives32 dates. CASH utility is zero and never loses. These labels overlap and cannot be summed as distinct opportunities.

The alternative cached continuous single-expert panel has281 positive,328 negative and169 zero short dates;201 positive dates beat VOL/CS/CASH,109 rescue VOL/CS joint losses, and22 dates have losses in all three risky experts. Carry and paid turnover change labels. Both panels have negative mean short utility in **every** episode. Their old diagnostic utility is `log1p(r)-.5*max(0,-r)`, with unramped expert targets; neither panel is the current v2 shared-wallet loss or minute execution. The five final decisions are forced CASH in the current v2 mapper: excluding these gives254 fresh positive dates and202 positive dates beating all existing actions. Full-wallet closure costs remain included.

Source-bound v2 training uses episode mean loss `L_e=-sum(utility_e)/n_e` and weights `n_e/778`, giving `L=-sum(all path utilities)/778`. The table reports those exact coefficients, **not measured model loss or gradient shares**. The exports contain aggregate training loss but do not expose those per-episode contributions; no checkpoint was loaded to infer them. Momentum short is not yet an action in the current fixed VOL/CS±CASH training pool.

Propose one fixed length-only blend `w_e=.5*(n_e/778)+.5*(1/5)`: episode weights13.47%,15.66%,13.98%,19.25%,37.63%. Per-day multipliers are1.94,1.38,1.75,1.04,.68. This bounds the change and reduces the longest episode's dominance without selecting outcomes. Preserve causal inputs, costs, masks, covariance/budget mapping, full ordered wallets, paid final closure and fixed architecture/LR/budget. Freeze using training-only rules, then evaluate the full declared development wallet; never select weights or checkpoints on June. It may worsen performance, and length balancing does not balance market regimes.

The778 outcome intervals do not overlap;773 consecutive pairs share only a boundary. Adjacent64-day feature windows share63 days, and three episode boundaries still share62 feature days. There are161 positive-outcome runs, longest6 days, across the same five economic wallets; these are not161 independent trials or new episodes. Wallet resets do not prove statistical independence of the market samples.

`COVERAGE.json` provides bound hashes, definitions, both panels, terminal-day caveats and coefficients. `TRAIN778_DESCRIPTIVE_LABELS.csv` records every actual date; `CONTIGUOUS_OUTCOME_RUNS.csv` records selected condition ranges. These are retrospective diagnostics, not causal features or a replacement training packet. `CHECK.json` verifies calendar, counts and run partitions. No original frozen input bytes changed.
