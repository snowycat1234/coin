# Fixed-student state labels (one day)

Hypothesis: oracle training visits its own wallet states, while deployment
visits the fixed student's states. The reported roughly 42% teacher/self-state
action agreement establishes state sensitivity, not the cause of all losses.
This module supplies a falsifiable sampling interface; no model improvement,
historical training or market-data acquisition was performed here. Existing
wallet/budget features are reused, not presented as new holding memory.

Base: `cc1829b3c8b5aa0bcf18ec70c1c669975b5343a5`, plus availability
`94286155072ead9705c448b087cc8677a9a7fd35`. `NativeDailySimulator` financial
logic is unchanged. This is independent of the concurrent seven-day labels.

`modules.native_action.student_labels.collect_pass` consumes `NativeExperiment`,
`FixedStudent` and `TrainingWindow`. The student returns its exact `Proposal`
from a detached current observation before any outcome probe. Every selected
training decision reuses `replay_candidates` for the available five/six one-hot
requests **and** that exact proposal, including mixed budgets/custom targets.
The original main wallet advances with the student proposal, never the oracle
winner, and must match the exact-proposal branch hash and net increment.
Unsampled days still advance the same policy and wallet. Local regrets cannot
be added to form realizable NAV.

Rows record main before/after hashes, exact proposal, causal features, model,
adapter/configuration, feature builder/schema and complete source bindings,
action mask, maturity, fees/execution/funding/turnover, and the global terminal
rule. Missing actions have null rewards and are not simulated. The simulator's
actual applied targets are distinct from submitted targets. Both final-day-zero
and charged end-minus-six-minutes conventions retain native fees and liquidity.

The entire wallet replay must be inside declared training, with a fresh start;
the collection window and optional unique `sample_decisions_us` only control
sampling, not account start or liquidation. Every sample needs
`feature_available <= decision`, `interval_end = decision + DAY`, and
`interval_end <= label_available <= label_asof <= training_end <= evaluation_start`.
Both fit entry points check new student contracts **before** date filtering,
so an evaluation or delayed-maturity row cannot silently flow back into fitting.
Forced-zero final days are saved for audit and excluded by existing fit rules.

This intentionally permits a fixed artifact trained on the same training
interval to revisit that interval retrospectively. Its latest fitted label and
artifact as-of must be within training; it is explicitly not a historical
deployment claim. A generic HGB/existing-selector adapter can implement
`FixedStudent.propose(observation)`. Its fingerprint callbacks must hash the
actual model and complete adapter/configuration, not return a constant digest.
The included ridge adapter also binds the real mapper source/configuration.
Opaque/stateful mappers should use the generic interface with explicit hashes.

Offline entry point (already-bound local inputs only):

```bash
bash scripts/cloud_research.sh .venv/bin/python -m modules.native_action.student_labels \
  --adapter MODULE:FACTORY --options LOCAL_OPTIONS.json --model FROZEN.npz \
  --window TRAIN_WINDOW.json --output NEW_DIRECTORY --limit-seconds 900
```

Add `--availability-aware` for the existing masked ridge artifact. Window JSON
uses integer UTC microseconds for `training_start_us`, `training_end_us`,
`evaluation_start_us`, `label_asof_us`, `collect_start_us`, `collect_end_us`, and
optionally an array `sample_decisions_us`. Use this entry point for exact-student
sampling; the older runner's `--relabel-training` hook is a separate legacy path.
Outputs are exclusive JSONL labels/decisions and RUN/summary JSON; failures
preserve only a prefix with `FAILED.json`. No refit or iterative DAgger is run.

Cost: for D main days and S sampled days with K available actions, about
`D + (K + 1) * S` native day replays; K is 5 or 6. Full sampling thus costs about
7x/8x one fixed-student replay, plus history-copy/hash overhead. Minute tape is
shared, not downloaded repeatedly. The existing cloud wrapper bounds one CPU,
6 GB address space, no swap/GPU, and at most 900 seconds; exhausted runs fail
with a prefix. Tests use synthetic three-day inputs only.

Validation command:

```bash
bash scripts/cloud_research.sh .venv/bin/python -m pytest -q \
  tests/test_native_student_labels.py tests/test_native_action_teacher.py \
  tests/test_native_action_availability.py tests/test_native_action_inputs.py \
  tests/test_resumable_perpetual.py \
  --basetemp=/workspace/coin-state/tests/student-state-labels-final
```

Cloud validation: **53 passed in 49.01s**, peak process RSS 278,339,584 bytes;
ruff `F` and `git diff --check` passed. Only synthetic data and fixed numeric
models were created. `.agents/skills` was absent in the selected workspace.

Smallest empirical comparison for the parent task: preregister one training
date subset and one frozen student. Collect equal-count teacher-state and
student-state labels on those dates, with identical one-day costs/actions and
feature/model recipe. Reuse original teacher labels where available, replacing
the same-date rows rather than increasing sample count. Permit at most one
student-label refit against the already frozen original student; use the same
declared evaluation wallet/calendar/terminal rule for each frozen policy.
Compare complete-wallet net NAV, drawdown, fees/turnover and action agreement;
report local label regret separately. Seen evaluation history remains seen,
and neither evaluation labels nor seven-day targets tune this experiment.
