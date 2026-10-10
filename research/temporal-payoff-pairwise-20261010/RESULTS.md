# Rejected: payoff-sensitive loss did not improve timing

The one prespecified four-way payoff-pairwise control failed all four 2023 adoption checks. It is stopped. No new 2024 inference/scoring, 2025 IO, threshold tuning or further fit was performed. The matched CE20 candidate remains untouched.

Only the training objective and its associated score interpretation changed: six pairwise logistic losses weighted by each corresponding fixed-policy utility gap, with one TRAIN-only scale and no class-weight correction. The model, 744 mature TRAIN labels, causal inputs, prefix scaler, seed, 240 updates, Adam, dropout and gradient clip matched CE20. Raw outputs are preference scores, so proper probability losses were not claimed.

- TRAIN: pairwise loss fell from 1.1084 to .4764. Action regret was .004363; SHORT precision 53.63%, recall 85.16%.
- 2023, 344 overlapping labels: regret .029951 versus CE20 .017649 and constant VOL .015272. SHORT precision 44/186 = 23.66%, below 29.94% prevalence; recall 42.72%. CE20 precision/recall were 48.62%/85.44%.
- CASH/CS choices became available in practice: predicted counts [5,83,70,186]. CASH had zero correct picks and CS six correct picks. Their appearance did not improve overall action quality.
- Fixed phase 0, 17 disjoint horizons: regret .033556 versus CE20 .012974 and VOL .015661. Paired utility-difference bootstrap intervals still span zero; small samples and residual dependence prevent strong statistical claims. All 21 phases are preserved without pooling or selection.

TRAIN-only target-weight diagnosis does not establish a cause. Top 1%/5% of the 4,464 pair cells carried 6.23%/22.06% of absolute-gap weight; top 1%/5% of dates carried 3.88%/16.72%. SHORT pairs carried 47.39%, the other pairs 52.61%. Year shares were 2021 47.76%, 2022 42.89%, late 2020 9.35%. The largest year/regime group, 2021/UP, carried 22.08%. SHORT-favoring/opposing weight was 8.91/19.79 in 2021, compared with 17.21/8.82 in 2022. Economic label direction shifts across years, but these are target weights rather than realized loss/gradient attribution. Changing representations and clipping also affect influence; a causal explanation would require a separate matched experiment.

This loss substitution learned on TRAIN and generalized poorly into 2023. It is not evidence that every payoff-sensitive selector is impossible. A binary SHORT/VOL collapse would discard 250 TRAIN CASH/CS winners and .004203 mean oracle opportunity, so four-way preservation remains defensible.

All values are continuing fixed-policy daily-boundary diagnostic utility, not tradable switching returns or profits. Dates are previously seen development history. Eleven focused tests, Ruff, exact model/Adam/RNG validators, saved-score recomputation and IO/resource checks passed. Training used one CPU and 21.49 seconds; full trading wallet validation was NOT_RUN. Frozen plan, complete scores, weight diagnosis and final exact-recovery archive accompany this result.
