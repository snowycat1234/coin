# Paired five-minute source discriminator

One fixed, pure-array implementation of a constrained joint empirical stress
assumption. Original independent maxima are conservative, not an established
bug. Joint observed scenarios may miss unseen simultaneous extremes. This
package does not classify removed alerts as false positives or estimate profit.

The original HEADROOM window is rolling at every completed minute, not a
midnight-anchored thirty-UTC-calendar-day window. Exact alignment, population
difference, clipping and formula are in PROTOCOL.json. The original buffer is
vendored without edits and supplies readiness, rolling extrema, fee, friction
and maintenance constants. No original strategy or financial file was changed.

Runnable synthetic preparation, from this directory:

    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 -m unittest -v test_paired_buffer
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 run_toy.py
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 preflight.py

For one bounded receipt-producing run, use python3 run_bounded_checks.py. It
requires toy_receipts not to exist and runs the same three fixed commands with
source preflight first, one CPU, one math thread, 4GB address space, a sampled
2GB RSS stop, 60 CPU seconds and 120 wall seconds per command. It also runs
benchmark_toy.py at three fixed
generated sizes. Use --receipt-dir toy_receipts_attempt002 for an additional
explicit run; existing receipts are never overwritten. No historical launch
argument is accepted.

All arrays in these commands are generated toy data in memory. There is no
historical data path argument, source loader, wallet adapter or automatic scan.
SOURCE_PINS.json and SOURCE_MANIFEST.json provide exact source/code identities.
Source preflight reads code/metadata only. Future historical source or wallet
work needs the staged review/authorization in SOURCE_PREFLIGHT_PLAN.json.

Legacy-independent, aligned-independent and paired outputs are kept together:
legacy versus aligned measures endpoint/alignment effects, aligned versus
paired measures coupling. The latter control uses the exact candidate pair
population. This decomposition does not itself establish an economic advantage.

The scenario deficit factors as abs(q)*current_mark*K_pair-E. Two normalized
rolling maxima are therefore exact sufficient statistics. Production is O(N)
per symbol and O(1) per assessment, with the original monotone-deque routine;
there is no per-minute 43,195-pair rescan or dropped scenario. Direct original
assessment over every eligible pair is checked independently on synthetic
fixtures. Roundoff comparisons do not introduce a trigger tolerance.
See NORMALIZATION_DERIVATION.md for the algebra and the retained extreme LONG
coefficient counterexample. No unconditional hurdle-subset claim is made.

2021 remains pending its original three-document provenance binding. No proof
was substituted or waived. 2023/2024/2025 are proposed later source scopes after
review, not an admission certificate from this synthetic package. Locked and
unknown holdouts remain closed.

Risk/cost/terminal mechanics are untouched because no financial adapter exists
in this stage. A later adapter must preserve the exact existing own-ledger
clock, persistent paid full exit, cap priority, direction lock, actual shared
capacity and terminal60 semantics; this package does not certify that adapter.
