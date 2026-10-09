# One matched short expansion

Two GRU64 WITH_CASH continuations start from the identical frozen objective-v2 terminal model, Adam moments and saved RNG. The control admits CASH/VOL_MANAGED_HOLD/CSMOM21; the expansion adds only MOMENTUM30_SHORT_ONLY. Both have **13,123 parameters**, including the same new 33-parameter readout. Its weights start at zero and bias at logit(.01); the control multiplies its output by zero. Existing Adam ages remain cumulative; the new head starts at age zero. This is a matched continuation, not a clean initialization comparison.

Pre-May training loss chooses the GRU parent; the supplied training-only complementarity recommendation chooses momentum short. No development-selected epoch, architecture search, winning-day oversampling or new labels/features are used. Inputs retain CORE5 order, 64 completed daily steps, 24 causal values plus 24 validity masks, time masks and the original train-only scaler. All 778 mature dates remain in the same five whole chronological wallets. Wallet state stays endogenous to the economic rollout and absent from the model input.

Each arm receives at most 1,024 additional full-wallet updates or 1,200 seconds, with the original Adam/dropout/batch/risk/cost/funding/paid-close settings and train-only stopping rule. At most two 1CPU/2GB workers run under the existing shared8GB/swap0/GPU0 controller. Caps remain NOT_CONVERGED. Terminal request inference may export immediately; both heads must be terminal before seen May–June economic scoring.

Public request order is the original E5 order plus short at **slot5**; original SMA and long Donchian slots2/3 stay zero. To reuse the unchanged five-coordinate financial mapper and exact VJP, the private ABI carries canonical coordinates `[0,1,2,4,5]`. Public slot3 is omitted because it always has zero allocation; the remaining dormant coordinate stays ineligible. This preserves every admitted leg, the L1 norm, allocated gross before netting, covariance check and reverse adjoint. Canonical source targets, names and exported slots are preserved separately. Tests prove zero-short parity against the original mapped objective, active-short finite differences and full-graph/dropout replay. Forced eligibility release to CASH precedes the discretionary L1≤.1 ramp.

Objective v2 is the explicitly declared **continuous daily-boundary charged full-fill diagnostic surrogate**, with the original own-path utility. It does not reproduce native minute capacity, lots, orders, margin or liquidations. Native validation belongs to the existing source-bound executor. Seen May–June is not unseen evaluation and the short hypothesis was proposed retrospectively.

Use the already installed dependencies in [the v2 recipe](../temporal_risk_proxy_v2/requirements.txt); no new package is required. Restore the two small immutable context NPZs from public commit `1291857d53360e4e06a4dd50540c130886deffbf`, directory `research/recover-frozen-runner-20261009/short-candidate-contexts`, into `STATE/short-source`. Their exact hashes are in `adapter.py`. Producer object-array reason strings are never deserialized; numeric causal masks/clocks and public producer checks are retained.

```bash
PYTHONPATH=.:src python -m modules.temporal_two_expert.bounded_comparison \
  --report STATE/short-tests-resources.json python -m pytest \
  modules/temporal_short_expansion -q --basetemp STATE/short-tests

PYTHONPATH=.:src python -m modules.temporal_two_expert.bounded_comparison \
  --report STATE/short-check-resources.json python -m modules.temporal_short_expansion check \
  --state STATE --output STATE/short-expansion

PYTHONPATH=.:src python -m modules.temporal_surrogate_resume_v2.bounded_controller \
  --report STATE/short-expansion/CONTROLLER_RESOURCES.json \
  python -m modules.temporal_short_expansion run \
  --state STATE --output STATE/short-expansion \
  --producer-commit FULL_PUBLISHED_CODE_COMMIT \
  --request-directory research/temporal-short-expansion-20261009/native61-requests \
  > STATE/short-expansion/CONTROLLER.log 2>&1
```

The console log is owned storage so disconnecting a display cannot terminate the coordinator. Atomic snapshots bind model/data/source/protocol identities, exact parameter births, Adam/RNG and stopping history. An interrupted arm resumes its last completed generation. Earlier four-arm artifacts remain immutable.
