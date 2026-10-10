Proposed initial tuning: three recipes across two chronological development folds,
six fresh fits maximum. Every fit uses at least600 actual distinct eligible active
training dates. No fits, model inference, economic wallets or market downloads
were performed for this plan. [PLAN.json](PLAN.json) contains exact tasks/settings,
causal/mask counts, curve evidence and bound source identities.

| Fold | Training decisions / eligible active dates | Prefix scaler rows | Development interval, exclusive end |
|---|---:|---:|---|
| January2024 | 658 / **653** | 787 | January1–March4,2024 |
| April2024 | 749 / **744** | 878 | April1–June3,2024 |
| Later selected final refit | 778 / **773** | 907 | October1,2024–January1,2025 reserved |

Five paid-close decisions are excluded from active-date counts in each prefix.
Scaler rows and repeated epochs are not economic training dates. The first
600-date cutoff is November9,2023; November8 has599. July1/October1,2023
prefixes have469/561 and are excluded. Cached2020–2021 observations provide
feature history, with no economic training labels in this packet.

All prefixes include early2022 bear53dates, midyear crisis87, August–December
sideways/autumn crisis151,2023 rebound88,2023 midyear sideways183. January
adds91 late2023 bull dates; April adds182 late2023/early2024 dates; full adds211.
These are descriptive calendar partitions, not return-derived regime labels.
Coverage remains incomplete: February25–May3,2022 is absent68days, plus
July31/October2,2022 and February24,2023. The producer excluded61 covariance
rows at a different admission stage; do not add those counts. Preserve five
natural wallets and every gap. No artificial sequences or minibatch wallet resets.
January/April have625/716 fully observed64-step windows out of658/749;33
partly missing windows per prefix remain with original masks. VOL/SHORT eligible
SOL/XRP active dates are488/579 versus BTC/ETH/DOGE653/744; CS covers all.

| Recipe | Adam learning rate | Whole-wallet coefficient | Single change |
|---|---:|---|---|
| BASE_DATE_LR1E3 | .001 | n_i/N | Baseline with common1024-update cap |
| LOW_LR3E4 | .0003 | n_i/N | Learning rate |
| MIXED_WALLET_HALF | .001 | .5*n_i/N+.5/5 | Wallet weighting |

n_i counts original decisions including paid closure; N is658 or749, matching
the original mean-normalized economic loss. Exact coefficients are serialized.
All recipes retain13,699parameters: CORE5 BTC/ETH/SOL/XRP/DOGE,64completed
days,24causal values+24validity masks, sharedGRU32,160→32 joint head with18
current expert inputs. CanonicalE6 actions are CASH/VOL/CS/SHORT; unused
SMA/DONCHIAN slots stay zero. No architecture, features or risk/cost changes.

Fresh parameters, emptyAdam and Python/NumPy/Torch RNG, seed20261009, matched
within each fold. Adam betas(.9,.999), epsilon1e−8, weight_decay0, foreachFalse;
dropout.1, gradient norm clip1. Neural window chunks32; each update accumulates
all five complete own paths in chronology. Dropout RNG is replayed exactly;
evaluation disables dropout. Atomic checkpoints bind model/scaler/source/recipe,
Adam and all RNG. Preserve latest resume, initial/best/matched512/terminal
snapshots and all scheduled metrics. Original strict loaders remain unchanged.
Own-path objective/covariance/eligibility/continuous10k capital/funding/costs,
L1≤.1/gross≤.6/asset≤.3 and paid terminal flattening remain unchanged.

Original January loss0/256/512:−.00003810/−.00103071/−.00112390; April
−.00006870/−.00102076/−.00112662. April gradient norm at512 is.0009984,
far below clip1, and loss still improves:512updates do not prove convergence.
Lower learning rate tests abrupt/saturated request movement. Mixed weighting
tests shorter crisis wallets: April's401-decision wallet has53.54% date weight
and91.44% initial signed gradient projection, a signed additive share rather
than a norm fraction. Earlier warm mixed512 lost18.69USDT more than date
weighting on seen May–June; preserve that negative evidence.

Evaluate256/384/512/640/768/896/1024. Primary is deterministic development
own-path utility excess over already frozen prefix-static VOL; also report
Static50/Cash50. Early stop only at≥512 after three scheduled checks without
improvement>1e−5; retain the best checkpoint, ties earlier. Report actual
updates plus matched512 diagnostics. Rank recipes by mean best-checkpoint
utility excess over the two fixed folds; ties within1e−5 use the worst fold,
then baseline/lowLR/mixed order. Preserve all failures; no rescue refits or
automatic promotion. Development outcomes are project-seen historical data.

After selection, propose one additional fresh refit on full773active dates.
Freeze its step count to the rounded-down median of the selected recipe's two
best development steps (minimum256), then score the fixed October–December
reserve once without reserve-based stopping. This reserve overlaps old native
HGB/teacher/student TAIL development; it is reserved for this study, **not
pristine project OOS**. No reserved returns or strategy results were inspected.

Read-only coverage finds155/155 required daily primitive rows for all10context
assets and45 accepted CORE5 trade/mark/funding monthly source records. Actual
92execution prices and91event-funding intervals are absent in this cache.
Before final scoring, restore only small derived economics from existing
accepted sources, rebuild missing serialized features with original builder,
verify strict clocks/masks/paid closure, and fit no reserved scaler. Source
metadata is not native/funding/publication certification. Separate native
validation remains outside this plan.

Historical speed2.12–2.47seconds/update implies3.62–4.22CPU-hours for six1024
fits, about1.81–2.11wall-hours at two workers plus validation. Max two one-CPU
workers,2GB resident each/shared8GB,swap0/GPU0;1200-second exact-resume slices,
3600seconds cumulative per fit (three-hour maximum at two workers).

The executable is a cached-input audit/settings emitter; **the candidate training
adapter is still required before fitting**. It must explicitly bind these two
overrides without altering old strict contracts or snapshots. Audit dependencies
are pinned in [requirements-audit.txt](requirements-audit.txt), no Torch needed.
Run with the existing bounded recovery guard:

```bash
PYTHONPATH="$REPO:$REPO/src" taskset -c 3 "$PYTHON" \
  "$REPO/research/two-expert-exact-recovery-20261009/runtime-delta/source/bounded_recovery.py" \
  --seconds 60 --report "$STATE/tuning-plan/NEW_RESOURCE.json" "$PYTHON" \
  "$REPO/research/temporal-small-tuning-plan-20261010/AUDIT_AND_PLAN.py" \
  --state "$STATE" --repo "$REPO" --tail-metadata "$CACHED_TAIL_MANIFEST" \
  --output "$STATE/tuning-plan/NEW_PLAN.json"
```

Use an exclusive output path; original packet/manifest identities are verified.
The cached TAIL metadata identity/source is in PLAN.json; the audit downloads
nothing. [RECEIPT.json](RECEIPT.json) records three focused readiness/chronology
tests, source preservation and resource results. Plan awaits settings review;
no new fits start here. Completed July attribution is
[here](../temporal-july-frozen-transfer-20261010/attribution/README.md).
