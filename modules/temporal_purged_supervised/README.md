# Purged supervised timing control

This is one fresh fixed-seed fit on previously seen project history. It is an internal chronological development control, not a pristine holdout or a trading-profit test.

- TRAIN: 744 fixed-policy labels from 2020-10-15 to 2022-12-10, available strictly before 2023-01-01.
- SELECT2023: 344 labels from 2023-01-01 to 2023-12-10, available strictly before 2024-01-01.
- AUDIT2024: 100 labels from 2024-01-01 to 2024-04-09, available strictly before 2024-05-01.
- 42 crossing labels are purged. Original episode-terminal exclusions remain unchanged.

The existing causal 64-day GRU and expert-state input are unchanged. Standardization uses only the sliced windows associated with mature TRAIN labels. Counts, balanced-CE weights, class prior, and constant utility action use only TRAIN. There are exactly 20/100-epoch snapshots from one 100-epoch trajectory (1,200 total updates), with no parameter grid. The corrected 2023 multiclass logloss selects the epoch; exact ties select 20. Raw balanced outputs are retained only as diagnostics. The selected checkpoint and selection report must be frozen before the selected-only 2024 audit.

The IO guard rejects all paths containing `2025`. No trading replay, credentials, network changes, or external writes occur here. Frozen inputs use the existing state layout and verified episode/label identities; source hashes include all loaded project modules and this entire package.

## Reproduction

Run from the repository with the existing `coin_runtime` environment and `coin_single_state`. All Python execution, including tests, is wrapped by `coin_single_state/bounded_cloud.py` using a fresh report filename. The wrapper enforces one CPU/thread, no GPU/swap, RSS 2 GB, address space 4 GB, host memory 8 GB, and wall/CPU 1,200 seconds. Each command below is the inner command to that wrapper.

1. `python -m pytest -q modules/temporal_purged_supervised/test_control.py --basetemp STATE/purged-test-unique`
2. `python -m modules.temporal_purged_supervised.experiment ready --state STATE --out NEW_OUT`
3. Persist PLAN and source before fitting. Supply an externally verified JSON receipt with `status=PURGED_SUPERVISED_PREFIT_PUBLIC_VERIFIED` and the exact `plan_SHA256`.
4. `python -m modules.temporal_purged_supervised.experiment train --state STATE --out OUT --publication PREFIT_RECEIPT`
5. `python -m modules.temporal_purged_supervised.experiment select --state STATE --out OUT`
6. Persist SELECTION before auditing. Supply a receipt with `status=PURGED_SUPERVISED_SELECTION_PUBLIC_VERIFIED` and its exact `selection_SHA256`.
7. `python -m modules.temporal_purged_supervised.experiment audit --state STATE --out OUT --selection-frozen SELECTION_RECEIPT`

The training command resumes the latest exact model/Adam/RNG/permutation checkpoint without restarting. It writes atomic checkpoints each minibatch and stops before its bounded slice ends. No checkpoint is overwritten. Completed training is idempotent; selection and audit refuse to overwrite completed evidence.

Scores include multiclass logloss/Brier, accuracy, SHORT precision/recall/prevalence, and opportunity regret against the train prior and constant training-mean-utility action. These utility regrets describe hindsight fixed-policy labels, not the return of a tradable switching portfolio. The calendar-anchored phase-0 21-day grid is primary for the small-sample view; all 21 phase grids are descriptive and must not be pooled or selected. Wilson and phase-0 paired bootstrap intervals do not remove residual serial dependence. The selected 2024 audit has only five phase-0 observations, so it cannot establish reliable deployment skill.
