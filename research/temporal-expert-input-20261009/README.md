One matched current-expert-input ablation, frozen before fitting. Both arms have
13,699 parameters, use the same original v2 GRU WITH_CASH snapshot/Adam/RNG at
step780, and admit CASH/VOL/CS/MOMENTUM30_SHORT_ONLY. The inherited64-day,
five-asset,24-value-plus24-mask input and907-row train-only scaler stay fixed.

The active arm adds exact signed current targets for canonical experts1/4/5 in
CORE5 order (15 values divided by fixed0.3), then three eligibility bits. An
18→32 bias-free, zero-initialized projection adds this block before joint tanh.
The control has identical parameters and receives a zero block. Both append the
same short readout initialized at1%. No wallet state, future utility, weighting,
indicator recipe, SOL processing or architecture sweep changes.

Saved target clocks are preserved: available at or before the decision, strictly
before execution at decision+60,000,001µs. Equality at the decision is intentional
under the existing completed-daily-bar publication proxy; this is not a measured
exchange release guarantee. No source timestamp is backdated.

Same778 pre-May dates/five complete chronological wallets, charged objective-v2,
date-weighted loss, caps/cost/funding/paid flattening. Budget per arm:1024 extra
updates or1200s; two one-CPU/2GB workers, shared8GB/swap0/GPU0. Save every completed
update. Training-only stop; both terminal before seen May–June economic scoring.
Terminal native61 requests may be exported immediately; native executor remains
separate. Weighting has0 updates and its unpublished draft is preserved.

Use Python3.12 and the existing CPU dependency recipe
[`requirements.txt`](../../modules/temporal_two_expert/requirements.txt), installing
Torch only from its official CPU index as documented in that module. No package
installation was needed. Entrypoint: `python -m modules.temporal_expert_input`
with `check`, `arm`, `run`, `score`, or `export`; pass `--state` and `--output`.
Use the existing `temporal_two_expert.bounded_comparison` worker launcher and
`temporal_surrogate_resume_v2.bounded_controller` for the pair. `run` additionally
requires a full published producer SHA and a new `--request-directory`.

`CURRENT_EXPERT_INPUTS61.npz` preserves inference inputs/clocks alongside each
strict seven-field `REQUESTS.npz`; model/Adam/RNG, scaler, plan and executable
sources are byte-bound. Seen history is not unseen validation or an alpha claim.
